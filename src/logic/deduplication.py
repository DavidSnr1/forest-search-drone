"""
Deduplizierung: fasst mehrere unabhängig triangulierte Sichtungen desselben
Gegenstands zu einem einzelnen Kartenpunkt zusammen.

Reine Logik, keine ROS-Abhängigkeit. Später in ROS 2: ein Node sammelt
über Zeit alle triangulierten Punkte (aus mehreren Drohnen, mehreren
Frames), ruft `deduplicate()` regelmäßig auf und publiziert die bereinigte
Punktliste auf ein Karten-Topic.

Ansatz: einfaches Greedy-Clustering nach Abstand. Kein vollständiges
DBSCAN nötig — bei einer überschaubaren Zahl von Detektionen (einzelner
Gegenstand pro Mission) reicht das, ist leicht nachvollziehbar und einfach
zu testen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Detection:
    position: np.ndarray  # Shape (3,)
    confidence: float = 1.0


@dataclass
class ClusteredPoint:
    position: np.ndarray
    num_detections: int
    mean_confidence: float
    member_positions: list[np.ndarray] = field(default_factory=list)


def deduplicate(
    detections: list[Detection],
    distance_threshold: float,
) -> list[ClusteredPoint]:
    """
    Gruppiert Detektionen, die näher als `distance_threshold` an einem
    bestehenden Cluster liegen, in denselben Cluster. Der Cluster-Punkt ist
    der konfidenzgewichtete Mittelpunkt aller Mitglieder.

    Reihenfolge-unabhängig für den Normalfall gut getrennter Objekte;
    bei Ketten von Detektionen, die jeweils knapp unter der Schwelle
    aneinanderhängen, kann Reihenfolge das Ergebnis beeinflussen — für
    einen einzelnen gesuchten Gegenstand pro Mission unkritisch.
    """
    if distance_threshold <= 0:
        raise ValueError("distance_threshold muss positiv sein")

    clusters: list[ClusteredPoint] = []

    for det in detections:
        best_cluster = None
        best_distance = distance_threshold

        for cluster in clusters:
            dist = float(np.linalg.norm(cluster.position - det.position))
            if dist <= best_distance:
                best_distance = dist
                best_cluster = cluster

        if best_cluster is None:
            clusters.append(
                ClusteredPoint(
                    position=det.position.copy(),
                    num_detections=1,
                    mean_confidence=det.confidence,
                    member_positions=[det.position.copy()],
                )
            )
        else:
            _merge_into_cluster(best_cluster, det)

    return clusters


def _merge_into_cluster(cluster: ClusteredPoint, det: Detection) -> None:
    cluster.member_positions.append(det.position.copy())
    n = cluster.num_detections

    # Laufender Mittelwert für Position und Konfidenz
    cluster.position = (cluster.position * n + det.position) / (n + 1)
    cluster.mean_confidence = (cluster.mean_confidence * n + det.confidence) / (n + 1)
    cluster.num_detections = n + 1
