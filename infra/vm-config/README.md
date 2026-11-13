# VM-Inventar (Stand 2026-11-13, Ubuntu 22.04)

Gesichert vor dem Upgrade auf 24.04. Enthält keine Geheimnisse (`~/.vnc/passwd` und `~/.config/gh` bewusst ausgelassen).

| Datei/Ordner | Inhalt |
|---|---|
| `xorg/xorg-vgl.conf` | Xorg-Konfiguration für den GPU-X-Server :0 (von `nvidia-xconfig` erzeugt, siehe `scripts/sim.sh`) |
| `xorg/Xwrapper.config` | `allowed_users=console` |
| `vnc/xstartup` | tightvnc-Startskript (`startxfce4 &`) |
| `config/xfce4/` | XFCE-Einstellungen des VNC-Desktops |
| `config/QGroundControl.ini` | QGC-Einstellungen |
| `apt-sources/` | `sources.list` und `sources.list.d/*` |
| `apt-manual.txt` | `apt-mark showmanual` |
| `pakete-wichtig.txt` | NVIDIA, VirtualGL, VNC, noVNC, Gazebo, GStreamer |
| `pip-freeze-venv.txt` | `pip freeze` aus dem alten venv (Python 3.10) |
| `crontab.txt`, `systemd-user-enabled.txt` | keine eigenen Einträge |
| `bashrc-eigene.txt` | eigene Zeilen in `~/.bashrc` |
| `nvidia-smi.txt`, `df.txt`, `kernel.txt` | Hardware-/Plattenstand |
