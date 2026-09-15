"""
Missionsplanung: berechnet eine flächendeckende Abflugroute (Boustrophedon /
"Mäander"-Muster) für ein gegebenes Suchgebiet.

Reine Geometrie, keine ROS-Abhängigkeit. Nimmt ein Polygon (Liste von
(x, y)-Punkten in Metern, lokales ENU-Koordinatensystem) und gibt eine
geordnete Liste von Wegpunkten zurück, die das Gebiet mit einem gegebenen
Bahnabstand abdeckt.

Später in ROS 2: ein Node liest das Suchgebiet (z.B. aus einem Parameter
oder einem Service-Call), ruft `plan_boustrophedon_path()` auf und
publiziert die Wegpunkte als `nav_msgs/Path` oder schickt sie einzeln an
MAVSDK/PX4.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import LineString, Polygon


@dataclass(frozen=True)
class Waypoint:
    x: float
    y: float
    altitude: float


def sweep_spacing_from_camera(altitude: float, fov_deg: float, overlap: float = 0.2) -> float:
    """
    Berechnet den Bahnabstand aus Flughöhe und Kamera-Sichtfeld, mit
    Overlap-Sicherheitsmarge (z.B. 0.2 = 20% Überlappung zwischen
    benachbarten Bahnen, damit nichts durchrutscht).

    fov_deg: horizontales Sichtfeld der Kamera in Grad.
    """
    import math

    footprint_width = 2 * altitude * math.tan(math.radians(fov_deg) / 2)
    return footprint_width * (1 - overlap)


def plan_boustrophedon_path(
    polygon_points: list[tuple[float, float]],
    altitude: float,
    lane_spacing: float,
) -> list[Waypoint]:
    """
    Erzeugt ein Mäander-Muster über das gegebene Polygon.

    Ansatz: das Polygon wird in achsparallele Streifen der Breite
    `lane_spacing` zerlegt. Für jeden Streifen wird die Schnittlinie mit dem
    Polygon berechnet; die Richtung wechselt abwechselnd (daher
    "Boustrophedon", wie ein Ochse beim Pflügen).

    Funktioniert für konvexe UND einfache nicht-konvexe Polygone, solange
    sie sich nicht selbst überschneiden.
    """
    if len(polygon_points) < 3:
        raise ValueError("Ein Polygon braucht mindestens 3 Punkte")

    poly = Polygon(polygon_points)
    if not poly.is_valid:
        raise ValueError("Polygon ist ungültig (z.B. selbstüberschneidend)")

    min_x, min_y, max_x, max_y = poly.bounds
    waypoints: list[Waypoint] = []

    y = min_y + lane_spacing / 2
    left_to_right = True

    while y <= max_y:
        scan_line = LineString([(min_x - 1.0, y), (max_x + 1.0, y)])
        intersection = poly.intersection(scan_line)

        segments = _extract_segments(intersection)

        for seg_start_x, seg_end_x in segments:
            if not left_to_right:
                seg_start_x, seg_end_x = seg_end_x, seg_start_x
            waypoints.append(Waypoint(seg_start_x, y, altitude))
            waypoints.append(Waypoint(seg_end_x, y, altitude))

        left_to_right = not left_to_right
        y += lane_spacing

    return waypoints


def _extract_segments(intersection) -> list[tuple[float, float]]:
    """Wandelt das Ergebnis von poly.intersection(scan_line) in eine Liste
    von (x_start, x_end)-Paaren um. Robust gegen leere oder mehrteilige
    Schnittmengen (z.B. bei nicht-konvexen Polygonen mit Löchern/Einbuchtungen)."""
    if intersection.is_empty:
        return []

    geom_type = intersection.geom_type
    if geom_type == "LineString":
        xs = [p[0] for p in intersection.coords]
        return [(min(xs), max(xs))]
    if geom_type == "MultiLineString":
        result = []
        for line in intersection.geoms:
            xs = [p[0] for p in line.coords]
            result.append((min(xs), max(xs)))
        return result
    # Punkt-Berührung (Polygon-Ecke) o.ä. -> ignorieren, kein Flugsegment
    return []
