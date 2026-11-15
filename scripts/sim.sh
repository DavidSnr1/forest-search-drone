#!/usr/bin/env bash
# Startet die komplette Drohnen-Simulation in einer tmux-Sitzung.
# Nutzung: ./scripts/sim.sh start [welt] [modell]   |   ./scripts/sim.sh stop

PX4_DIR="$HOME/forest-search-drone/PX4-Autopilot"
SESSION="drone"
SELF="$(realpath "$0")"
BILD_PUFFER="/dev/shm/drone_kamera"

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
      vncserver :1 -geometry 1920x1080 -localhost -nolisten tcp > /dev/null 2>&1
    fi
    # Browser-Viewer für den VNC-Desktop; VS Code leitet Port 6080
    # automatisch weiter und öffnet ihn im Browser.
    # noVNC liegt unter einem Pfad mit Versionsnummer, damit der Browser nach
    # einem noVNC-Update keine alten JS-Module aus dem Cache mischt
    # (websockify sendet keine Cache-Header).
    NOVNC_VER="$(dpkg-query -W -f='${Version}' novnc | sed 's/^[0-9]*://; s/-.*//')"
    NOVNC_WEB="$HOME/.local/share/novnc-web"
    NOVNC_URL="novnc-$NOVNC_VER/vnc.html?autoconnect=true&resize=scale"
    mkdir -p "$NOVNC_WEB"
    ln -sfn /usr/share/novnc "$NOVNC_WEB/novnc-$NOVNC_VER"
    # VS Code öffnet immer "/" -> direkt zum Viewer weiterleiten
    echo "<meta http-equiv=\"refresh\" content=\"0; url=$NOVNC_URL\">" > "$NOVNC_WEB/index.html"
    if ! pgrep -f "websockify --web $NOVNC_WEB" > /dev/null; then
      pkill -f "websockify --web /usr/share/novnc"   # alte Variante vor dem Umbau
      nohup websockify --web "$NOVNC_WEB" localhost:6080 localhost:5901 > /dev/null 2>&1 &
    fi
    echo "Desktop im Browser: http://localhost:6080/$NOVNC_URL"
    # Ohne Fenstermanager liegen alle Fenster fest übereinander bei 0,0
    if ! pgrep -x xfwm4 > /dev/null; then
      DISPLAY=:1 nohup xfwm4 > /dev/null 2>&1 &
    fi
    # Unsichtbarer X-Server auf der GPU, über den VirtualGL rendert
    if [ ! -f /etc/X11/xorg-vgl.conf ]; then
      BUSID="$(nvidia-xconfig --query-gpu-info | awk '/PCI BusID/ {print $4; exit}')"
      echo "Erzeuge /etc/X11/xorg-vgl.conf für GPU $BUSID ..."
      sudo nvidia-xconfig -a --allow-empty-initial-configuration \
        --use-display-device=None --virtual=1920x1080 \
        --busid "$BUSID" -o /etc/X11/xorg-vgl.conf > /dev/null
      # Ubuntu 24.04 setzt den NVIDIA-Modulpfad nur, wenn nvidia_drm geladen
      # ist (ohne Monitor/Display-Manager nicht der Fall) -> fest eintragen
      sudo sed -i '/^Section "Files"/a\    ModulePath     "/usr/lib/x86_64-linux-gnu/nvidia/xorg"\n    ModulePath     "/usr/lib/xorg/modules"' \
        /etc/X11/xorg-vgl.conf
    fi
    if ! pgrep -f "Xorg :0" > /dev/null; then
      sudo bash -c 'nohup Xorg :0 -config xorg-vgl.conf -nolisten tcp -noreset vt7 > /var/log/xorg-vgl.out 2>&1 &'
    fi
    tmux new-session -d -s "$SESSION" -n sim    "$SELF _sim $WORLD $MODEL; bash"
    tmux new-window     -t "$SESSION" -n gazebo "$SELF _gazebo; bash"
    tmux new-window     -t "$SESSION" -n kamera "$SELF _kamera; bash"
    tmux new-window     -t "$SESSION" -n fotos  "$SELF _fotos; bash"
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

  _gazebo)
    # Der VNC-Server kann kein OpenGL -> VirtualGL rendert über den
    # GPU-X-Server :0 und schickt das Bild nach :1
    # (EGL-Modus ohne :0 reicht für Gazebo nicht, Ogre stürzt ab)
    if ! command -v vglrun > /dev/null; then
      echo "vglrun fehlt - Gazebo-Fenster wird nicht gestartet."
      echo "Installieren: https://github.com/VirtualGL/virtualgl/releases (virtualgl_*_amd64.deb)"
      exit 1
    fi
    echo "Warte auf Gazebo-Server ..."
    until gz topic -l 2>/dev/null | grep -q /clock; do sleep 2; done
    DISPLAY=:1 vglrun -d :0 gz sim -g
    ;;

  _kamera)
    echo "Warte auf Kamerabild ..."
    until gz topic -l 2>/dev/null | grep -q image; do sleep 2; done
    # Puffer im RAM: immer nur die letzten Bilder, _fotos holt sie im Flug ab
    rm -rf "$BILD_PUFFER"
    mkdir -p "$BILD_PUFFER"
    DISPLAY=:1 gst-launch-1.0 -e udpsrc port=5600 \
      caps="application/x-rtp,media=video,encoding-name=H264" \
      ! rtph264depay ! avdec_h264 ! videoconvert ! tee name=t \
      t. ! queue ! videoscale ! video/x-raw,width=640,height=360 ! ximagesink \
      t. ! queue ! videorate ! video/x-raw,framerate=1/2 \
      ! jpegenc quality=95 ! multifilesink max-files=3 location="$BILD_PUFFER/bild_%06d.jpg"
    ;;

  _fotos)
    # Speichert Bilder nur in der Luft, pro Flug ein eigener Ordner
    LISTENER="$PX4_DIR/build/px4_sitl_default/bin/px4-listener"
    FLUG_DIR=""
    LETZTES=""
    echo "Warte auf Takeoff ..."
    while true; do
      LANDED="$("$LISTENER" vehicle_land_detected -n 1 2>/dev/null | awk '$1 == "landed:" {print $2}')"
      if [ "$LANDED" = "False" ]; then
        if [ -z "$FLUG_DIR" ]; then
          FLUG_DIR="$HOME/fotos/$(date +%Y-%m-%d_%H-%M-%S)"
          NR=0
          mkdir -p "$FLUG_DIR"
          echo "Takeoff - Fotos landen in $FLUG_DIR"
        fi
        # Vorletztes Bild nehmen, das letzte wird evtl. gerade noch geschrieben
        BILD="$(ls -t "$BILD_PUFFER" 2>/dev/null | sed -n 2p)"
        if [ -n "$BILD" ] && [ "$BILD" != "$LETZTES" ]; then
          NR=$((NR + 1))
          cp "$BILD_PUFFER/$BILD" "$FLUG_DIR/$(printf 'bild_%04d.jpg' "$NR")" 2>/dev/null
          LETZTES="$BILD"
        fi
      elif [ "$LANDED" = "True" ] && [ -n "$FLUG_DIR" ]; then
        echo "Gelandet - $NR Fotos in $FLUG_DIR"
        FLUG_DIR=""
        echo "Warte auf Takeoff ..."
      fi
      sleep 0.5
    done
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
