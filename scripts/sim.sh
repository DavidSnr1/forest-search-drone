#!/usr/bin/env bash
# Startet die komplette Drohnen-Simulation in einer tmux-Sitzung.
# Nutzung: ./scripts/sim.sh start [welt] [modell]   |   ./scripts/sim.sh stop

PX4_DIR="$HOME/forest-search-drone/PX4-Autopilot"
SESSION="drone"
SELF="$(realpath "$0")"

stop_all() {
  tmux kill-session -t "$SESSION" 2>/dev/null
  pkill -f QGroundControl
  pkill -f gst-launch-1.0
  pkill -f "px4_sitl_default/bin/px4"
  pkill -f "gz sim"
  sleep 2
}

case "${1:-start}" in
  start)
    WORLD="${2:-baylands}"
    MODEL="${3:-gz_x500_gimbal}"
    stop_all
    # VNC-Desktop nur starten, wenn er nicht schon läuft
    if ! pgrep -f "Xtightvnc :1" > /dev/null; then
      rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
      vncserver :1 > /dev/null 2>&1
    fi
    tmux new-session -d -s "$SESSION" -n sim    "$SELF _sim $WORLD $MODEL; bash"
    tmux new-window     -t "$SESSION" -n kamera "$SELF _kamera; bash"
    tmux new-window     -t "$SESSION" -n qgc    "$SELF _qgc; bash"
    tmux select-window  -t "$SESSION:sim"
    tmux attach -t "$SESSION"
    ;;

  stop)
    stop_all
    echo "Alles beendet."
    ;;

  # --- interne Teile, werden von tmux aufgerufen ---
  _sim)
    cd "$PX4_DIR" && PX4_GZ_WORLD="$2" HEADLESS=1 make px4_sitl "$3"
    ;;

  _kamera)
    echo "Warte auf Kamerabild ..."
    until gz topic -l 2>/dev/null | grep -q image; do sleep 2; done
    FOTO_DIR="$HOME/fotos/$(date +%Y-%m-%d_%H-%M)"
    mkdir -p "$FOTO_DIR"
    echo "Fotos landen in $FOTO_DIR"
    DISPLAY=:1 gst-launch-1.0 -e udpsrc port=5600 \
      caps="application/x-rtp,media=video,encoding-name=H264" \
      ! rtph264depay ! avdec_h264 ! videoconvert ! tee name=t \
      t. ! queue ! ximagesink \
      t. ! queue ! videorate ! video/x-raw,framerate=1/2 \
      ! jpegenc quality=95 ! multifilesink location="$FOTO_DIR/bild_%04d.jpg"
    ;;

  _qgc)
    echo "Warte auf PX4 ..."
    until pgrep -f "px4_sitl_default/bin/px4" > /dev/null; do sleep 2; done
    sleep 10
    DISPLAY=:1 "$HOME/QGroundControl.AppImage"
    ;;

  *)
    echo "Nutzung: $0 start [welt] [modell] | stop"
    ;;
esac
