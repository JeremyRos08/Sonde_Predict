from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


# ============================================================
# Points unitaires (issus CSV / table UI / GFS)
# ============================================================

@dataclass
class DescentPoint:
    """
    Point du profil de descente.

    alt_m       : altitude en mètres
    descent_ms  : vitesse verticale positive vers le bas (m/s)
    """
    alt_m: float
    descent_ms: float


@dataclass
class AscentPoint:
    """
    Point du profil de montée.

    alt_m      : altitude en mètres
    ascent_ms  : vitesse verticale positive vers le haut (m/s)
    """
    alt_m: float
    ascent_ms: float


@dataclass
class WindPoint:
    """
    Point du profil de vent.

    alt_m      : altitude en mètres
    wind_u_ms  : composante Est-Ouest (+Est / -Ouest)
    wind_v_ms  : composante Nord-Sud (+Nord / -Sud)
    """
    alt_m: float
    wind_u_ms: float
    wind_v_ms: float


# ============================================================
# Profils interpolés
# ============================================================

class DescentProfile:
    """
    Profil de descente altitude → vitesse verticale (m/s).

    J'utilise une interpolation linéaire entre les points.
    En dehors de la plage définie, je sature aux valeurs extrêmes.
    """

    def __init__(self, points: List[DescentPoint]):
        if not points:
            raise ValueError("Profil de descente vide")

        # Je trie toujours par altitude croissante
        self.points = sorted(points, key=lambda p: p.alt_m)

    def value(self, alt_m: float) -> float:
        """
        Retourne la vitesse de descente interpolée à l'altitude donnée.
        """
        # Sous le premier point → saturation basse
        if alt_m <= self.points[0].alt_m:
            return self.points[0].descent_ms

        # Au-dessus du dernier point → saturation haute
        if alt_m >= self.points[-1].alt_m:
            return self.points[-1].descent_ms

        # Interpolation linéaire
        for p1, p2 in zip(self.points[:-1], self.points[1:]):
            if p1.alt_m <= alt_m <= p2.alt_m:
                ratio = (alt_m - p1.alt_m) / (p2.alt_m - p1.alt_m)
                return p1.descent_ms + ratio * (p2.descent_ms - p1.descent_ms)

        # Sécurité (ne devrait jamais arriver)
        return self.points[-1].descent_ms


class AscentProfile:
    """
    Profil de montée altitude → vitesse verticale (m/s).

    Même logique que la descente :
    interpolation linéaire + saturation hors plage.
    """

    def __init__(self, points: List[AscentPoint]):
        if not points:
            raise ValueError("Profil de montée vide")

        self.points = sorted(points, key=lambda p: p.alt_m)

    def value(self, alt_m: float) -> float:
        """
        Retourne la vitesse de montée interpolée à l'altitude donnée.
        """
        if alt_m <= self.points[0].alt_m:
            return self.points[0].ascent_ms

        if alt_m >= self.points[-1].alt_m:
            return self.points[-1].ascent_ms

        for p1, p2 in zip(self.points[:-1], self.points[1:]):
            if p1.alt_m <= alt_m <= p2.alt_m:
                ratio = (alt_m - p1.alt_m) / (p2.alt_m - p1.alt_m)
                return p1.ascent_ms + ratio * (p2.ascent_ms - p1.ascent_ms)

        return self.points[-1].ascent_ms


class WindProfile:
    """
    Profil de vent altitude → (u, v) en m/s.

    u : Est-Ouest
    v : Nord-Sud

    Les valeurs sont interpolées linéairement sur l'altitude.
    """

    def __init__(self, points: List[WindPoint]):
        if not points:
            raise ValueError("Profil de vent vide")

        self.points = sorted(points, key=lambda p: p.alt_m)

    def value(self, alt_m: float) -> Tuple[float, float]:
        """
        Retourne (u, v) interpolés à l'altitude donnée.
        """
        if alt_m <= self.points[0].alt_m:
            p = self.points[0]
            return p.wind_u_ms, p.wind_v_ms

        if alt_m >= self.points[-1].alt_m:
            p = self.points[-1]
            return p.wind_u_ms, p.wind_v_ms

        for p1, p2 in zip(self.points[:-1], self.points[1:]):
            if p1.alt_m <= alt_m <= p2.alt_m:
                ratio = (alt_m - p1.alt_m) / (p2.alt_m - p1.alt_m)
                u = p1.wind_u_ms + ratio * (p2.wind_u_ms - p1.wind_u_ms)
                v = p1.wind_v_ms + ratio * (p2.wind_v_ms - p1.wind_v_ms)
                return u, v

        p = self.points[-1]
        return p.wind_u_ms, p.wind_v_ms
