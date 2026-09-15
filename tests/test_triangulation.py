import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.triangulation import make_ray, residual_error, triangulate


def test_triangulate_exact_intersection():
    # Gegenstand liegt bei (5, 5, 0). Zwei Drohnen schauen von
    # verschiedenen Positionen exakt darauf.
    true_point = np.array([5.0, 5.0, 0.0])

    ray1 = make_ray(origin=(0.0, 0.0, 10.0), direction=(5.0, 5.0, -10.0))
    ray2 = make_ray(origin=(10.0, 0.0, 10.0), direction=(-5.0, 5.0, -10.0))

    estimated = triangulate([ray1, ray2])

    assert np.allclose(estimated, true_point, atol=1e-6)
    assert residual_error([ray1, ray2], estimated) < 1e-6


def test_triangulate_with_three_rays_is_more_robust():
    true_point = np.array([3.0, 4.0, 0.0])

    rays = [
        make_ray(origin=(0.0, 0.0, 8.0), direction=(3.0, 4.0, -8.0)),
        make_ray(origin=(8.0, 0.0, 8.0), direction=(-5.0, 4.0, -8.0)),
        make_ray(origin=(0.0, 8.0, 8.0), direction=(3.0, -4.0, -8.0)),
    ]

    estimated = triangulate(rays)
    assert np.allclose(estimated, true_point, atol=1e-6)


def test_rejects_too_few_rays():
    ray = make_ray(origin=(0, 0, 5), direction=(0, 0, -1))
    with pytest.raises(ValueError):
        triangulate([ray])


def test_rejects_parallel_rays():
    ray1 = make_ray(origin=(0, 0, 5), direction=(0, 0, -1))
    ray2 = make_ray(origin=(1, 0, 5), direction=(0, 0, -1))
    with pytest.raises(ValueError):
        triangulate([ray1, ray2])


def test_rejects_zero_direction():
    with pytest.raises(ValueError):
        make_ray(origin=(0, 0, 0), direction=(0, 0, 0))
