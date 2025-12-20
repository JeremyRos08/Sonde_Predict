# montecarlo.py
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from profiles import AscentProfile, DescentProfile, WindProfile, DescentPoint, WindPoint
from simulation import simulate_flight, EARTH_RADIUS_M


# ============================================================
# Données de sortie
# ============================================================

@dataclass
class ImpactSample:
    lat_deg: float
    lon_deg: float
    x_m: float   # +Est
    y_m: float   # +Nord


@dataclass
class EllipseResult:
    cx_m: float
    cy_m: float
    a_m: float
    b_m: float
    angle_rad: float


# ============================================================
# Outils géométriques
# ============================================================

def _compute_local_xy(
    lat0_deg: float,
    lon0_deg: float,
    lat_deg: float,
    lon_deg: float,
) -> Tuple[float, float]:
    """
    Projection locale plate (OK pour quelques dizaines de km).
    """
    lat0_rad = math.radians(lat0_deg)
    dlat = math.radians(lat_deg - lat0_deg)
    dlon = math.radians(lon_deg - lon0_deg)

    x = EARTH_RADIUS_M * dlon * math.cos(lat0_rad)
    y = EARTH_RADIUS_M * dlat
    return x, y


def _compute_ellipse_from_samples(
    samples: List[ImpactSample],
    k_sigma: float = 2.4477,   # ~95%
) -> Optional[EllipseResult]:

    if len(samples) < 3:
        return None

    xs = [s.x_m for s in samples]
    ys = [s.y_m for s in samples]
    n = float(len(xs))

    mx = sum(xs) / n
    my = sum(ys) / n

    sxx = sum((x - mx) ** 2 for x in xs) / n
    syy = sum((y - my) ** 2 for y in ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n

    trace = sxx + syy
    det = sxx * syy - sxy * sxy
    root = math.sqrt(max(0.0, trace * trace / 4.0 - det))

    l1 = trace / 2.0 + root
    l2 = trace / 2.0 - root

    angle = 0.5 * math.atan2(2.0 * sxy, sxx - syy) if (sxx != syy or sxy != 0.0) else 0.0

    a = math.sqrt(max(l1, 0.0)) * k_sigma
    b = math.sqrt(max(l2, 0.0)) * k_sigma

    return EllipseResult(
        cx_m=mx,
        cy_m=my,
        a_m=a,
        b_m=b,
        angle_rad=angle,
    )


# ============================================================
# Monte Carlo principal
# ============================================================

def run_monte_carlo(
    n_runs: int,
    alt0_m: float,
    lat0_deg: float,
    lon0_deg: float,
    dt_s: float,
    base_ascent: AscentProfile,
    base_descent: DescentProfile,
    base_wind: WindProfile,
    sigma_desc_rel: float = 0.10,
    sigma_wind_ms: float = 2.0,
    k_sigma: float = 2.4477,
    seed: Optional[int] = None,
) -> Tuple[List[ImpactSample], Optional[EllipseResult]]:

    rng = random.Random(seed)
    impacts: List[ImpactSample] = []

    for _ in range(n_runs):

        # --------- bruit descente ---------
        f_desc = 1.0 + rng.gauss(0.0, sigma_desc_rel)
        desc_points = [
            DescentPoint(
                alt_m=p.alt_m,
                descent_ms=max(0.3, p.descent_ms * f_desc),
            )
            for p in base_descent.points
        ]
        descent_profile = DescentProfile(desc_points)

        # --------- bruit vent ---------
        wind_points = [
            WindPoint(
                alt_m=p.alt_m,
                wind_u_ms=p.wind_u_ms + rng.gauss(0.0, sigma_wind_ms),
                wind_v_ms=p.wind_v_ms + rng.gauss(0.0, sigma_wind_ms),
            )
            for p in base_wind.points
        ]
        wind_profile = WindProfile(wind_points)

        # --------- simulation complète ---------
        states = simulate_flight(
            alt_start_m=0.0,
            alt_burst_m=alt0_m,
            lat0_deg=lat0_deg,
            lon0_deg=lon0_deg,
            dt_s=dt_s,
            ascent_profile=base_ascent,
            descent_profile=descent_profile,
            wind_profile=wind_profile,
            ff_start_alt=None,
            free_fall_factor=1.0,
        )

        if not states:
            continue

        impact = states[-1]

        x_m, y_m = _compute_local_xy(
            lat0_deg=lat0_deg,
            lon0_deg=lon0_deg,
            lat_deg=impact.lat_deg,
            lon_deg=impact.lon_deg,
        )

        impacts.append(
            ImpactSample(
                lat_deg=impact.lat_deg,
                lon_deg=impact.lon_deg,
                x_m=x_m,
                y_m=y_m,
            )
        )

    ellipse = _compute_ellipse_from_samples(impacts, k_sigma=k_sigma)
    return impacts, ellipse
