# Autonome Waldsuche mit Drohnenschwarm

Drohnenschwarm kartiert ein unbekanntes Waldstück dezentral und kollaborativ,
teilt die Suche gelernt-koordiniert auf und lokalisiert einen versteckten
Gegenstand per Multi-View-Triangulation.

## Status
🚧 Monat 1 — Cloud-Setup läuft, parallel: ROS-freie Kernlogik in Entwicklung.

## Projektstruktur

```
drone-swarm-forest-search/
├── README.md
├── notizen.md              # laufendes Bautagebuch, ab Tag 1
├── requirements.txt
├── src/
│   └── logic/
│       ├── __init__.py
│       ├── mission_planning.py   # Boustrophedon-Routenplanung aus Polygon
│       ├── triangulation.py      # 3D-Position aus mehreren Sichtstrahlen
│       └── deduplication.py      # mehrere Sichtungen -> ein Kartenpunkt
└── tests/
    ├── test_mission_planning.py
    ├── test_triangulation.py
    └── test_deduplication.py
```

## Warum diese Trennung?

Alles unter `src/logic/` ist **reine Python-Logik ohne ROS-2-Abhängigkeit**.
Sie nimmt einfache Datentypen (Listen, Tupel, NumPy-Arrays) entgegen und gibt
ebensolche zurück — kein `rclpy`, keine Message-Typen, keine Nodes.

Später (Monat 2+) entstehen dünne ROS-2-Node-Wrapper, die:
1. Daten aus einem Topic abonnieren (z.B. Pose, Kamerabild),
2. sie in die einfachen Datentypen umwandeln,
3. die *hier* geschriebene Funktion aufrufen,
4. das Ergebnis in ein Topic zurück publizieren.

Der Node ist dann nur noch "Klebstoff" — die eigentliche Logik ist bereits
geschrieben, getestet und verstanden, bevor ROS überhaupt im Spiel ist.

## Setup lokal (Mac)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## Nächste Schritte
- [ ] Boustrophedon-Planer mit echtem Waldpolygon (aus QGIS/GeoJSON) testen
- [ ] Triangulation mit realistischem Kamera-Rauschen simulieren
- [ ] Deduplizierung mit Clustering-Parametern gegen Fehlalarme abstimmen
