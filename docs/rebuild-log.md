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
