"""Location report model shared by the transit detector and optional home feature."""

from dataclasses import dataclass


@dataclass
class Fix:
    position: tuple[float, float]
    timestamp: float
    accuracy: float = 0
