from dataclasses import dataclass
import numpy as np

@dataclass 
class Ray:
    origin: np.ndarray
    direction: np.ndarray

def make_ray(origin, direction):
    origin = np.array(origin, dtype=float)
    direction = np.array(direction, dtype=float)
    length = np.linalg.norm(direction)
    if length < 1e-9:
        raise ValueError("Nullvektor hat keine Richtung")
    return Ray(origin, direction / length)

def triangulate(rays):
    if len(rays) < 2:
        raise ValueError("Zu wenige rays für Triangulation")
    I = np.eye(3)
    A_sum = np.zeros((3,3))
    B_sum = np.zeros(3)
    for ray in rays:
        A_i = I - np.outer(ray.direction, ray.direction)
        A_sum += A_i
        B_sum += A_i @ ray.origin

    try:
        return np.linalg.solve(A_sum, B_sum)
    except np.linalg.LinAlgError as e:
        raise ValueError("Fast alle Strahlen parallel") from e


def residual_error(rays, point):
    """RMS-Abstand des Punkts zu den Strahlen (0 = alle Strahlen treffen ihn genau)."""
    point = np.asarray(point, dtype=float)
    I = np.eye(3)
    distances = [
        np.linalg.norm((I - np.outer(ray.direction, ray.direction)) @ (point - ray.origin))
        for ray in rays
    ]
    return float(np.sqrt(np.mean(np.square(distances))))