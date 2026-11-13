# VM-Neuaufbau Ubuntu 22.04 → 24.04 – Log

Anleitung: „VM-Neuaufbau-Ubuntu-24.04.md“ (Teil 1 vorher, Teil 2 David von Hand, Teil 3 danach).

## Teil 1 – Inventar vor dem Upgrade (2026-11-13)

### Ausgangsstand

| Punkt | Wert |
|---|---|
| OS | Ubuntu 22.04.5 LTS (jammy), Kernel 5.15.0-191-generic |
| NVIDIA | nvidia-driver-580 580.178.04, Quadro M4000 (Bus 00000000:00:05.0), CUDA 13.0 |
| Gazebo | gz-harmonic 1.0.0, gz-sim 8.15.0 (OSRF-Quelle `gazebo-stable`) |
| PX4 | `main` @ 3309f497d8 (`v1.18.0-beta1-678-g3309f497d8`, Commit vom 2026-09-15) |
| PX4-Submodul `Tools/simulation/gz` | bb0b9cf (lokal geändert, siehe unten) |
| VirtualGL | 3.1.1 (`.deb` von GitHub-Releases, keine apt-Quelle) |
| VNC | tightvncserver 1.3.10, Desktop :1, xstartup → `startxfce4`, Fenstermanager xfwm4 |
| noVNC / websockify | novnc 1.0.0, websockify 0.10.0 (apt) |
| GPU-X-Server | `Xorg :0 -config xorg-vgl.conf` (von `scripts/sim.sh` gestartet, keine `xorg.conf`) |
| QGC | `~/QGroundControl.AppImage` (Datei vom 2026-09-06) |
| Python-venv | Python 3.10.12, numpy 2.2.6, shapely 2.1.2, pytest 9.2.0 |
| ROS 2 / MicroXRCEAgent | nicht installiert |
| Tailscale | nicht installiert |
| ufw | inaktiv |
| sudo | ohne Passwort |
| Platte `/` | 97 G, 25 G belegt, **69 G frei** |

### Schritt 1 – Repo gesichert
- Einzige Änderung war `scripts/sim.sh` (Gazebo-GUI via VirtualGL, noVNC, Fenster `gazebo` und `fotos`).
- Commit a2b0a7f, gepusht.

### Schritt 2 – PX4-Änderungen gesichert
- `git describe --tags` → `v1.18.0-beta1-678-g3309f497d8`, Branch `main`.
- Hauptrepo: keine eigenen Änderungen, nur das Submodul `Tools/simulation/gz` ist „dirty“
  → `infra/px4-local.patch` enthält nur diesen Marker (kein Inhalt zum Anwenden).
- Submodul `Tools/simulation/gz`: `models/gimbal/model.sdf`, Kameraauflösung 1280×720 → 1920×1080
  → `infra/px4-gz-submodule.patch`. Anwenden **im Submodul-Ordner**:
  `cd PX4-Autopilot/Tools/simulation/gz && git apply ../../../../infra/px4-gz-submodule.patch`
- **Hinweis für Teil 3:** Die VM lief bisher auf `main` (1.18-Entwicklung), das Ziel v1.17.x ist also
  ein Schritt *zurück*. Modelle/Welten (`gz_x500_gimbal`, `baylands`) in 3.3 gegen v1.17.x prüfen.
- Lokal vorhandene Tags: v1.17.0 (stabil), v1.17.0-rc2 usw. – neuere 1.17.x-Patches erst nach `git fetch --tags` sichtbar.

### Schritt 3 – Konfiguration gesichert (`infra/vm-config/`)
Siehe `infra/vm-config/README.md`. Nicht gesichert (Geheimnisse): `~/.vnc/passwd`, `~/.config/gh`.

### Weitere Beobachtungen
- `~/.bashrc` eigene Zeile: `export PATH=$PATH:/opt/xtensa-esp-elf/bin/` (ESP-Toolchain in `/opt/xtensa-esp-elf`).
- `~/fotos` (878 MB) liegt außerhalb des Repos und übersteht das In-Place-Upgrade; bei Neuanlage einer VM ginge es verloren.
- VNC (5901) lief zum Zeitpunkt der Inventur nicht. `sim.sh` startet `vncserver :1` **ohne** `-localhost` → in 3.2 ändern.
- Fremde Quellen nach dem Upgrade: `gazebo-stable.list` (jammy → durch `ubuntu.sh` neu), `paperspace.list` (Paperspace-Agent, distributionsunabhängig).

## Teil 2 – Upgrade (David, von Hand)
- Ergebnis: Ubuntu 24.04.5 LTS (noble), Kernel 6.8.0-149-generic. Alter Kernel 5.15.0-203 noch installiert.
- Fremdquellen wurden als `*.distUpgrade` deaktiviert, NVIDIA-Treiber war entfernt.

## Teil 3 – Neuaufbau (2026-11-13)

### 3.1 Basis und NVIDIA
- `/etc/apt/sources.list.d/*.distUpgrade` (gazebo-stable jammy, paperspace) nach
  `/etc/apt/sources.list.d.jammy-backup/` verschoben (nicht gelöscht).
- `paperspace.list` wieder aktiviert (Quelle ist nicht an die Ubuntu-Version gebunden). Gazebo-Quelle kommt mit `ubuntu.sh`.
- `apt-get update && full-upgrade` (`--force-confold`), `autoremove`: ohne Fehler.
- `ubuntu-drivers devices`: M4000 (GM204GL), empfohlen wäre 470, verfügbar 580 / 580-server.
  Installiert: `nvidia-driver-580` 580.178.04-0ubuntu0.24.04.1 (voller Treiber, für Xorg :0).
- DKMS: `nvidia/580.178.04, 6.8.0-149-generic: installed`. Kein EFI → kein Secure Boot, keine MOK-Signierung nötig.
- **Neustart nötig.** Danach weiter mit Check `nvidia-smi`, dann 3.2.
- Nach Neustart: `nvidia-smi` → Quadro M4000, Treiber 580.178.04, CUDA 13.0. ✔

### 3.2 Anzeige
- Bereits per Upgrade vorhanden: tightvncserver 1.3.10-8, novnc 1.3.0-2, websockify 0.10.0-5build2, xfce4 4.18,
  xserver-xorg-core 21.1.12. `/etc/X11/xorg-vgl.conf` und `/usr/share/novnc/index.html` (Weiterleitung) überstanden.
- VirtualGL aus offizieller Quelle (virtualgl.org/Downloads/YUM): Key `/etc/apt/trusted.gpg.d/VirtualGL.gpg`
  (packagecloud dcommander, ABB9F2DE…FF482D), `/etc/apt/sources.list.d/VirtualGL.list` → **virtualgl 3.1.5-20260814**. `mesa-utils` dazu.
- `vglserver_config` war vorher nicht gelaufen (kein `/etc/opt/VirtualGL`) → wie vorher nicht ausgeführt.
- **Fehler:** `Xorg :0` → `(EE) Failed to load module "nvidia"`. Ursache: Unter 24.04 liegt `nvidia_drv.so` in
  `/usr/lib/x86_64-linux-gnu/nvidia/xorg`; `10-nvidia.conf` setzt den ModulePath nur per `MatchDriver "nvidia-drm"`,
  und `nvidia_drm` ist ohne Monitor/Display-Manager nicht geladen.
  **Lösung:** `ModulePath` (NVIDIA-Ordner + `/usr/lib/xorg/modules`) im `Files`-Abschnitt von `/etc/X11/xorg-vgl.conf`
  (alte Datei: `xorg-vgl.conf.bak-2204`). `sim.sh` trägt das beim Neuerzeugen per `sed` ein (getestet: identisches Ergebnis).
  Kopie in `infra/vm-config/xorg/xorg-vgl.conf` aktualisiert.
- VNC: `sim.sh` startet jetzt `vncserver :1 -geometry 1920x1080 -localhost -nolisten tcp`
  (ohne `-nolisten tcp` lauschte Xtightvnc auf 0.0.0.0:6001).
- `ss -tlnp`: 5901 und 6080 nur auf 127.0.0.1, kein 6001. noVNC `/vnc.html` → HTTP 200.
- Check: `DISPLAY=:1 vglrun -d :0 glxinfo` → `Quadro M4000/PCIe/SSE2`, OpenGL 4.6.0 NVIDIA 580.178.04. ✔
  (Ohne `DISPLAY=:1` nimmt vglrun über SSH die Client-IP als DISPLAY und scheitert.)

### 3.3 PX4 v1.17.0 und Gazebo Harmonic
- GitHub-Releases (2026-11-13): neuester stabiler 1.17-Release ist **v1.17.0** (2026-05-13); danach nur 1.18-Vorabversionen.
- Gimbal-Änderung im Submodul `gz` vorher per `git stash` abgelegt ("gimbal 1920x1080 vor v1.17.0", bleibt in `.git/modules`).
- `git fetch --tags`, `git checkout v1.17.0`, `git submodule sync --recursive && git submodule update --init --recursive`, `make distclean`.
  Warnung beim Fetch: `Could not access submodule 'src/lib/ulog_cpp' at commit af006cf1c3` (betrifft `main`, nicht v1.17.0).
- Übrig von `main` (unversioniert, nicht gelöscht): `boards/modalai/voxl2/src/lib/`, `src/lib/rl_tools/`, `src/modules/mc_raptor/`,
  `src/modules/simulation/gz_plugins/optical_flow/PX4-OpticalFlow/`, `src/modules/uxrce_dds_client/Micro-XRCE-DDS-Client-v3/`.
  Stören den Build nicht. Können bei Gelegenheit mit `git clean -fd` im PX4-Ordner weg (nach Rückfrage).
- `bash Tools/setup/ubuntu.sh` → Exit 0. Gazebo-Quelle jetzt `noble`, gz-harmonic 1.0.0-1~noble, gz-sim 8.15.0,
  cmake 3.28.3, gcc-arm-none-eabi 13.2. Python-Pakete per `pip --break-system-packages` (offizieller PX4-Weg).
- `infra/px4-gz-submodule.patch` sauber angewendet (gimbal-Kamera 1920×1080). `infra/px4-local.patch` enthält nur den Submodul-Marker, nichts anzuwenden.
- Modelle: `gz_x500_gimbal` (Airframe 4019) und Welt `baylands.sdf` existieren in v1.17.0 → `make sim`-Standard bleibt.
- `make px4_sitl` → 1141/1141, ohne Fehler. `HEADLESS=1 make px4_sitl gz_x500` startet; `ver all`:
  `PX4 version: Release 1.17.0`, git-hash d6f12ad1c4, GCC 13.3.0. ✔
- Stolperstein beim Testen: `pkill -f "gz sim"` aus einer Shell, deren Kommandozeile selbst "gz sim" enthält, beendet die Shell.
  In `sim.sh` unkritisch (Skript-Kommandozeile enthält den Text nicht).

### 3.4 QGroundControl und Kamera-Pipeline
- QGC-Doku (docs.qgroundcontrol.com, Download & Install): AppImage unterstützt 24.04. Pakete:
  `libfuse2t64 libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor0` (waren schon da).
- `modemmanager` 1.23.4 entfernt (`apt remove --purge`, wie in der Anleitung). `dialout` war schon gesetzt.
- GStreamer 1.24.2: plugins-base/good/bad/ugly, libav, tools (+ gl, x) – alle schon vorhanden.
  Alle 11 Elemente der Pipeline in `sim.sh` per `gst-inspect-1.0` gefunden.
- QGC **v5.1.5** (GitHub-Release 2026-10-01, neuester stabiler) → `~/QGroundControl.AppImage` (195332600 Bytes, wie Asset).
  Alte Datei als `~/QGroundControl.AppImage.old` behalten.
- `sim.sh`: QGC-Pfad unverändert passend, keine Python-Version im Skript.

### 3.5 ROS 2 Jazzy, px4_msgs, MicroXRCEAgent
- docs.ros.org blockiert automatischen Abruf (Anubis) → Anleitung aus `ros2/ros2_documentation` (Branch `jazzy`) gelesen.
- Locale `en_US.UTF-8` war gesetzt. `universe` aktiviert, `ros2-apt-source` **1.3.0~noble** (latest GitHub-Release).
- Installiert: `ros-jazzy-desktop` 0.11.0 (Build 2026-10-06), `ros-dev-tools` 1.0.3, rclpy 7.1.12, colcon-common-extensions 0.3.0.
- `~/ros2_ws/src`: `px4_msgs` **release/1.17** @86d8239 (2026-03-22); `px4_ros_com` **main** @86e9aeb
  (es gibt keinen release/1.17-Branch; PX4-Doku v1.17 nutzt `main`).
- Abgleich: alle 235 `.msg` in px4_msgs/release/1.17 byteidentisch mit `PX4-Autopilot/msg` (inkl. `versioned/`) von v1.17.0.
- `colcon build` → 2 Pakete, 6 min 45 s, ohne Fehler.
- MicroXRCEAgent **v2.4.3** aus Quellcode (`~/Micro-XRCE-DDS-Agent`, laut docs.px4.io/v1.17): `cmake .. && make -j8`,
  `sudo make install`, `sudo ldconfig /usr/local/lib/` → `/usr/local/bin/MicroXRCEAgent`.
- `~/.bashrc`: `source /opt/ros/jazzy/setup.bash` und `source ~/ros2_ws/install/setup.bash` ergänzt.

### 3.6 Python
- `python3 -m venv` scheiterte: `ensurepip is not available` → `sudo apt install python3.12-venv`.
- Altes venv gelöscht, neu: `python3 -m venv --system-site-packages venv` → Python **3.12.3**, `pip install -r requirements.txt`.
  Sichtbar im venv: numpy 2.5.4 (aus `~/.local`, von PX4 `ubuntu.sh`), shapely 2.2.0, pytest 7.4.4 (apt, via ros-dev-tools).
  `import rclpy, px4_msgs.msg` funktioniert (nach `source` von ROS + Workspace). ✔
- `pytest` ohne Ziel sammelte auch Tests im PX4-Ordner (83 Fehler) → neue `pytest.ini` mit `testpaths = tests`.
- **Offen (nicht Umgebung):** `tests/test_triangulation.py` importiert `make_ray` und `residual_error`;
  `src/logic/triangulation.py` hat nur `make_Ray` (großes R) und kein `residual_error`. Stand seit Commit 4b6440d (2026-09-15),
  also schon vor dem Upgrade. Nicht angefasst. Rest: 8 passed.
