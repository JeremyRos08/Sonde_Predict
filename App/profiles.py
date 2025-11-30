# profiles.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DescentPoint:
    alt_m: float
    descent_ms: float  # >0 vers le bas


@dataclass
class WindPoint:
    alt_m: float
    wind_u_ms: float  # Est-Ouest (+E, -W)
    wind_v_ms: float  # Nord-Sud (+N, -S)


class DescentProfile:
    """Profil alt -> vitesse de descente (m/s) avec interpolation linéaire."""

    def __init__(self, points: List[DescentPoint]):
        if not points:
            raise ValueError("Profil de descente vide")
        self.points = sorted(points, key=lambda p: p.alt_m)

    def value(self, alt_m: float) -> float:
        if alt_m <= self.points[0].alt_m:
            return self.points[0].descent_ms
        if alt_m >= self.points[-1].alt_m:
            return self.points[-1].descent_ms

        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            if p1.alt_m <= alt_m <= p2.alt_m:
                ratio = (alt_m - p1.alt_m) / (p2.alt_m - p1.alt_m)
                return p1.descent_ms + ratio * (p2.descent_ms - p1.descent_ms)

        return self.points[-1].descent_ms


class WindProfile:
    """Profil alt -> vent (u,v) m/s avec interpolation linéaire."""

    def __init__(self, points: List[WindPoint]):
        if not points:
            raise ValueError("Profil de vent vide")
        self.points = sorted(points, key=lambda p: p.alt_m)

    def value(self, alt_m: float) -> Tuple[float, float]:
        if alt_m <= self.points[0].alt_m:
            p = self.points[0]
            return p.wind_u_ms, p.wind_v_ms
        if alt_m >= self.points[-1].alt_m:
            p = self.points[-1]
            return p.wind_u_ms, p.wind_v_ms

        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            if p1.alt_m <= alt_m <= p2.alt_m:
                ratio = (alt_m - p1.alt_m) / (p2.alt_m - p1.alt_m)
                u = p1.wind_u_ms + ratio * (p2.wind_u_ms - p1.wind_u_ms)
                v = p1.wind_v_ms + ratio * (p2.wind_v_ms - p1.wind_v_ms)
                return u, v

        p = self.points[-1]
        return p.wind_u_ms, p.wind_v_ms
