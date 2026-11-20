#!/usr/bin/env python3
"""
Offboard Controller (erste Fassung) fuer PX4 v1.17 + ROS 2 Jazzy.

Ablauf: warten auf gueltige Position -> Setpoints vorab streamen -> Offboard + Arm
        -> Start auf ALT m -> Wegpunkte abfliegen -> Landen -> warten bis entwaffnet.

Einziger Node, der PX4 steuert. Schickt mit 10 Hz OffboardControlMode + TrajectorySetpoint
(Lebenszeichen). Verlaesst PX4 den Offboard-Modus waehrend des Flugs (Pilot uebernimmt,
Failsafe), gibt der Node sofort auf und schickt keine Befehle mehr.

Start (VM, Agent + SITL laufen lokal):
    source /opt/ros/jazzy/setup.bash
    source ~/<dein_ws>/install/setup.bash      # Workspace mit px4_msgs release/1.17
    python3 offboard_controller.py
    # Parameter z. B.:  --ros-args -p alt:=8.0 -p square:=10.0

Koordinaten: PX4 lokal NED (x = Nord, y = Ost, z = unten). 5 m Hoehe => z = -5.
"""

import math
from enum import Enum, auto

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleLocalPosition,
    VehicleStatus,
)


class State(Enum):
    WAIT_POSITION = auto()
    PRESTREAM = auto()
    ENGAGE = auto()        # Offboard schalten + armen
    TAKEOFF = auto()
    WAYPOINTS = auto()
    LAND = auto()
    DONE = auto()
    ABORTED = auto()


class OffboardController(Node):
    RATE_HZ = 10.0

    def __init__(self):
        super().__init__("offboard_controller")

        # --- Parameter ---------------------------------------------------------
        self.declare_parameter("alt", 5.0)                  # Flughoehe in m ueber Start
        self.declare_parameter("square", 5.0)               # Kantenlaenge Testquadrat in m
        self.declare_parameter("accept_radius", 0.5)        # Wegpunkt erreicht, wenn naeher als ... m
        self.declare_parameter("hold_s", 1.0)               # so lange am Wegpunkt stehen bleiben
        self.declare_parameter("engage_timeout_s", 15.0)    # max. Zeit fuer Offboard + Arm
        # Topic-Namen: in PX4 1.17 teils versioniert. Mit `ros2 topic list | grep fmu` pruefen.
        self.declare_parameter("topic_status", "/fmu/out/vehicle_status_v1")
        self.declare_parameter("topic_local_pos", "/fmu/out/vehicle_local_position_v1")
        self.declare_parameter("topic_offboard_mode", "/fmu/in/offboard_control_mode")
        self.declare_parameter("topic_setpoint", "/fmu/in/trajectory_setpoint")
        self.declare_parameter("topic_command", "/fmu/in/vehicle_command")

        p = lambda name: self.get_parameter(name).value
        self.alt = float(p("alt"))
        self.square = float(p("square"))
        self.accept_radius = float(p("accept_radius"))
        self.hold_s = float(p("hold_s"))
        self.engage_timeout_s = float(p("engage_timeout_s"))

        # PX4 erwartet diese QoS (wie im offiziellen px4_ros_com-Beispiel).
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.pub_mode = self.create_publisher(OffboardControlMode, p("topic_offboard_mode"), qos)
        self.pub_sp = self.create_publisher(TrajectorySetpoint, p("topic_setpoint"), qos)
        self.pub_cmd = self.create_publisher(VehicleCommand, p("topic_command"), qos)
        self.create_subscription(VehicleStatus, p("topic_status"), self._on_status, qos)
        self.create_subscription(VehicleLocalPosition, p("topic_local_pos"), self._on_pos, qos)

        self.status = None
        self.pos = None

        self.state = State.WAIT_POSITION
        self.state_since = self._now_s()
        self.ticks = 0
        self.last_cmd_s = 0.0
        self.home = None          # (x, y, z, yaw) beim Start
        self.target = None        # (x, y, z) aktueller Setpoint
        self.waypoints = []
        self.wp_index = 0
        self.reached_since = None
        self.was_offboard = False

        self.create_timer(1.0 / self.RATE_HZ, self._tick)
        self.get_logger().info(
            f"Offboard Controller gestartet: Hoehe {self.alt} m, Quadrat {self.square} m"
        )

    # --- Callbacks ----------------------------------------------------------------
    def _on_status(self, msg: VehicleStatus):
        self.status = msg

    def _on_pos(self, msg: VehicleLocalPosition):
        self.pos = msg

    # --- Hilfsfunktionen ------------------------------------------------------------
    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _ts_us(self) -> int:
        return int(self.get_clock().now().nanoseconds / 1000)

    def _set_state(self, new: State):
        self.get_logger().info(f"Zustand: {self.state.name} -> {new.name}")
        self.state = new
        self.state_since = self._now_s()
        self.reached_since = None

    def _armed(self) -> bool:
        return self.status is not None and self.status.arming_state == VehicleStatus.ARMING_STATE_ARMED

    def _offboard(self) -> bool:
        return self.status is not None and self.status.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD

    def _dist_to(self, t) -> float:
        return math.dist((self.pos.x, self.pos.y, self.pos.z), t)

    def _send_heartbeat(self):
        m = OffboardControlMode()
        m.timestamp = self._ts_us()
        m.position = True
        m.velocity = False
        m.acceleration = False
        m.attitude = False
        m.body_rate = False
        self.pub_mode.publish(m)

    def _send_setpoint(self, x, y, z, yaw):
        sp = TrajectorySetpoint()
        sp.timestamp = self._ts_us()
        sp.position = [float(x), float(y), float(z)]
        nan = float("nan")
        sp.velocity = [nan, nan, nan]
        sp.acceleration = [nan, nan, nan]
        sp.yaw = float(yaw)
        self.pub_sp.publish(sp)

    def _send_command(self, command, p1=0.0, p2=0.0, p3=0.0):
        c = VehicleCommand()
        c.timestamp = self._ts_us()
        c.command = command
        c.param1 = float(p1)
        c.param2 = float(p2)
        c.param3 = float(p3)
        c.target_system = 1
        c.target_component = 1
        c.source_system = 1
        c.source_component = 1
        c.from_external = True
        self.pub_cmd.publish(c)

    def _engage_offboard(self):
        # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1, PX4 custom main mode OFFBOARD = 6
        self._send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)

    def _arm(self):
        self._send_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)

    def _land(self):
        self._send_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)

    # --- Hauptschleife (10 Hz) --------------------------------------------------
    def _tick(self):
        now = self._now_s()
        in_state = now - self.state_since

        if self.state in (State.DONE, State.ABORTED):
            return

        # Lebenszeichen + Setpoint immer senden, solange wir aktiv sind (ausser beim Landen)
        if self.target is not None and self.state != State.LAND:
            self._send_heartbeat()
            self._send_setpoint(*self.target, self.home[3])

        # Pilot oder Failsafe hat uebernommen -> nicht dagegen ankaempfen
        if self._offboard():
            self.was_offboard = True
        elif self.was_offboard and self.state in (State.TAKEOFF, State.WAYPOINTS):
            nav = self.status.nav_state if self.status else "?"
            self.get_logger().warn(f"Offboard verlassen (nav_state={nav}). Node gibt auf.")
            self.target = None
            self._set_state(State.ABORTED)
            return

        if self.state == State.WAIT_POSITION:
            if self.pos is not None and self.pos.xy_valid and self.pos.z_valid and self.status is not None:
                self.home = (self.pos.x, self.pos.y, self.pos.z, self.pos.heading)
                hx, hy, hz, _ = self.home
                self.target = (hx, hy, hz - self.alt)
                s = self.square
                self.waypoints = [
                    (hx + s, hy, hz - self.alt),
                    (hx + s, hy + s, hz - self.alt),
                    (hx, hy + s, hz - self.alt),
                    (hx, hy, hz - self.alt),
                ]
                self.get_logger().info(f"Startposition NED: x={hx:.2f} y={hy:.2f} z={hz:.2f}")
                self._set_state(State.PRESTREAM)
            elif in_state > 5.0 and int(in_state * self.RATE_HZ) % 50 == 0:
                self.get_logger().info("Warte auf gueltige Position und Status ... (Topic-Namen pruefen?)")

        elif self.state == State.PRESTREAM:
            # PX4 nimmt Offboard nur an, wenn schon Setpoints ankommen (>1 s).
            self.ticks += 1
            if self.ticks >= int(1.5 * self.RATE_HZ):
                self._set_state(State.ENGAGE)

        elif self.state == State.ENGAGE:
            if self._offboard() and self._armed():
                self.get_logger().info("Offboard aktiv und bewaffnet. Start.")
                self._set_state(State.TAKEOFF)
            elif in_state > self.engage_timeout_s:
                self.get_logger().error("Offboard/Arm nicht geklappt (Preflight-Checks? QGC-Meldungen ansehen).")
                self.target = None
                self._set_state(State.ABORTED)
            elif now - self.last_cmd_s > 1.0:   # Befehle 1x pro Sekunde wiederholen
                self.last_cmd_s = now
                if not self._offboard():
                    self._engage_offboard()
                if not self._armed():
                    self._arm()

        elif self.state == State.TAKEOFF:
            if self._at_target(now):
                self.wp_index = 0
                self.target = self.waypoints[0]
                self.get_logger().info(f"Hoehe erreicht. Wegpunkt 1/{len(self.waypoints)}")
                self._set_state(State.WAYPOINTS)

        elif self.state == State.WAYPOINTS:
            if self._at_target(now):
                self.wp_index += 1
                if self.wp_index >= len(self.waypoints):
                    self.get_logger().info("Alle Wegpunkte erreicht. Landen.")
                    self._set_state(State.LAND)
                    self._land()
                    self.last_cmd_s = now
                else:
                    self.target = self.waypoints[self.wp_index]
                    self.reached_since = None
                    self.get_logger().info(f"Wegpunkt {self.wp_index + 1}/{len(self.waypoints)}")

        elif self.state == State.LAND:
            landing = self.status is not None and self.status.nav_state == VehicleStatus.NAVIGATION_STATE_AUTO_LAND
            if not self._armed():
                self.get_logger().info("Gelandet und entwaffnet. Fertig.")
                self._set_state(State.DONE)
            elif not landing and now - self.last_cmd_s > 1.0:
                self.last_cmd_s = now
                self._land()

    def _at_target(self, now) -> bool:
        if self.pos is None or self.target is None:
            return False
        if self._dist_to(self.target) < self.accept_radius:
            if self.reached_since is None:
                self.reached_since = now
            return now - self.reached_since >= self.hold_s
        self.reached_since = None
        return False


def main():
    rclpy.init()
    node = OffboardController()
    try:
        while rclpy.ok() and node.state not in (State.DONE, State.ABORTED):
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        node.get_logger().warn("Abbruch per Strg+C. PX4-Failsafe uebernimmt (kein Offboard-Signal mehr).")
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
