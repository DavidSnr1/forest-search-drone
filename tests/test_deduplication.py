import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.deduplication import Detection, deduplicate


def test_nearby_detections_merge_into_one_cluster():
    detections = [
        Detection(position=np.array([5.0, 5.0, 0.0]), confidence=0.8),
        Detection(position=np.array([5.2, 5.1, 0.0]), confidence=0.9),
        Detection(position=np.array([4.9, 4.8, 0.0]), confidence=0.7),
    ]

    clusters = deduplicate(detections, distance_threshold=1.0)

    assert len(clusters) == 1
    assert clusters[0].num_detections == 3
    assert np.allclose(clusters[0].position, [5.0, 4.97, 0.0], atol=0.1)


def test_distant_detections_stay_separate():
    detections = [
        Detection(position=np.array([0.0, 0.0, 0.0])),
        Detection(position=np.array([50.0, 50.0, 0.0])),
    ]

    clusters = deduplicate(detections, distance_threshold=1.0)

    assert len(clusters) == 2


def test_confidence_is_averaged():
    detections = [
        Detection(position=np.array([0.0, 0.0, 0.0]), confidence=1.0),
        Detection(position=np.array([0.1, 0.0, 0.0]), confidence=0.0),
    ]

    clusters = deduplicate(detections, distance_threshold=1.0)

    assert len(clusters) == 1
    assert clusters[0].mean_confidence == pytest.approx(0.5)


def test_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        deduplicate([Detection(position=np.array([0.0, 0.0, 0.0]))], distance_threshold=0)
