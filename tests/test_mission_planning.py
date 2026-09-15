import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.mission_planning import plan_boustrophedon_path, sweep_spacing_from_camera


def test_sweep_spacing_reasonable():
    # 20m Höhe, 60° FOV, 20% Overlap -> Bahnabstand sollte im Bereich
    # weniger Meter bis niedriger zweistelliger Meter liegen
    spacing = sweep_spacing_from_camera(altitude=20.0, fov_deg=60.0, overlap=0.2)
    assert 10.0 < spacing < 25.0


def test_boustrophedon_covers_square():
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    waypoints = plan_boustrophedon_path(square, altitude=15.0, lane_spacing=10.0)

    assert len(waypoints) > 0
    # Alle Wegpunkte müssen innerhalb (oder auf dem Rand) des Quadrats liegen
    for wp in waypoints:
        assert -0.5 <= wp.x <= 100.5
        assert -0.5 <= wp.y <= 100.5
        assert wp.altitude == 15.0


def test_boustrophedon_alternates_direction():
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    waypoints = plan_boustrophedon_path(square, altitude=15.0, lane_spacing=20.0)

    # Erste Bahn: links -> rechts, zweite Bahn: rechts -> links
    first_lane_start_x = waypoints[0].x
    first_lane_end_x = waypoints[1].x
    second_lane_start_x = waypoints[2].x

    assert first_lane_start_x < first_lane_end_x
    assert second_lane_start_x > first_lane_end_x - 1  # zweite Bahn startet "rechts"


def test_rejects_invalid_polygon():
    import pytest

    with pytest.raises(ValueError):
        plan_boustrophedon_path([(0, 0), (1, 1)], altitude=10.0, lane_spacing=5.0)
