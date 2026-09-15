# Notizen / Bautagebuch

## 2026-09-02
- Repo-Struktur angelegt.
- Cloud-Anbieter gewählt: Paperspace (eingebautes Desktop-Streaming statt
  manuellem VNC/NoMachine-Setup — spart Reibung in Monat 1/3/5/6).
- GPU+/P4000-Zugang beantragt (Freigabe dauert laut Paperspace 1-2 Werktage).
- Parallel dazu: ROS-freie Kernlogik begonnen (Missionsplanung,
  Triangulation, Deduplizierung) — läuft komplett lokal auf dem Mac,
  kein Cloud-Zugang nötig.

## Nächster Schritt
- Sobald Cloud-Freigabe da ist: Monat 1, Woche 1 (Linux + Docker auf der
  Cloud-Maschine).
- Bis dahin: Tests für die drei Logik-Module schreiben und Kantenfälle
  durchdenken (z.B. was passiert bei parallelen Sichtstrahlen in der
  Triangulation, oder einem nicht-konvexen Waldpolygon).
