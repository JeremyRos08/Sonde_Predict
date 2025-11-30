# montecarlo.py
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from profiles import DescentProfile, WindProfile, DescentPoint, WindPoint
from simulation import simulate_descent, State, EARTH_RADIUS_M


@dataclass
class ImpactSample:
    lat_deg: float
    lon_deg: float
    x_m: float   # repère local : +x = Est
    y_m: float   # repère local : +y = Nord


@dataclass
class EllipseResult:
    cx_m: float      # centre ellipse en m (repère local)
    cy_m: float
    a_m: float       # grand axe (m)
    b_m: float       # petit axe (m)
    angle_rad: float # angle du grand axe (rad, depuis +x)


def _compute_local_xy(
    lat0_deg: float,
    lon0_deg: float,
    lat_deg: float,
    lon_deg: float,
) -> Tuple[float, float]:
    """
    Convertit (lat, lon) en x/y locaux en mètres autour du point (lat0, lon0).
    """
    lat0_rad = math.radians(lat0_deg)
    dlat = math.radians(lat_deg - lat0_deg)
    dlon = math.radians(lon_deg - lon0_deg)

    x = EARTH_RADIUS_M * dlon * math.cos(lat0_rad)  # Est-Ouest
    y = EARTH_RADIUS_M * dlat                       # Nord-Sud
    return x, y


def _compute_ellipse_from_samples(samples: List[ImpactSample],
                                  k_sigma: float = 2.4477) -> Optional[EllipseResult]:
    """
    Calcule une ellipse de covariance (~95%) à partir des échantillons.
    k_sigma ≈ 2.4477 pour ~95% pour une gaussienne 2D (chi2 2 dof).
    """
    if len(samples) < 3:
        return None

    xs = [s.x_m for s in samples]
    ys = [s.y_m for s in samples]
    n = float(len(xs))

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    sxx = sum((x - mean_x) ** 2 for x in xs) / n
    syy = sum((y - mean_y) ** 2 for y in ys) / n
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n

    trace = sxx + syy
    det = sxx * syy - sxy * sxy
    term = max(0.0, (trace * trace) / 4.0 - det)
    root = math.sqrt(term)

    lambda1 = trace / 2.0 + root
    lambda2 = trace / 2.0 - root
    if lambda1 < 0:
        lambda1 = 0.0
    if lambda2 < 0:
        lambda2 = 0.0

    # angle du grand axe
    if sxx != syy or sxy != 0.0:
        angle = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    else:
        angle = 0.0

    a = math.sqrt(lambda1) * k_sigma
    b = math.sqrt(lambda2) * k_sigma

    return EllipseResult(
        cx_m=mean_x,
        cy_m=mean_y,
        a_m=a,
        b_m=b,
        angle_rad=angle,
    )


def run_monte_carlo(
    n_runs: int,
    alt0_m: float,
    lat0_deg: float,
    lon0_deg: float,
    dt_s: float,
    base_descent: DescentProfile,
    base_wind: WindProfile,
    sigma_desc_rel: float = 0.10,
    sigma_wind_ms: float = 2.0,
    k_sigma: float = 2.4477,      # ⬅️ nouveau paramètre
    seed: Optional[int] = None,
) -> Tuple[List[ImpactSample], Optional[EllipseResult]]:

    """
    Monte Carlo : on refait la descente n_runs fois avec perturbation sur
    la vitesse de descente et le vent. On renvoie la liste des impacts
    + une ellipse de covariance approximative (~zone d'impact).
    """
    rng = random.Random(seed)

    impacts: List[ImpactSample] = []

    for _ in range(n_runs):
        # Perturbation globale du profil de descente pour ce run
        factor_desc = 1.0 + rng.gauss(0.0, sigma_desc_rel)

        desc_points = []
        for p in base_descent.points:
            v = p.descent_ms * factor_desc
            v = max(0.1, v)
            desc_points.append(
                DescentPoint(
                    alt_m=p.alt_m,
                    descent_ms=v,
                )
            )
        descent_profile = DescentProfile(desc_points)

        # Perturbation du vent
        wind_points = []
        for p in base_wind.points:
            du = rng.gauss(0.0, sigma_wind_ms)
            dv = rng.gauss(0.0, sigma_wind_ms)
            wind_points.append(
                WindPoint(
                    alt_m=p.alt_m,
                    wind_u_ms=p.wind_u_ms + du,
                    wind_v_ms=p.wind_v_ms + dv,
                )
            )
        wind_profile = WindProfile(wind_points)

        # Simulation de descente pour ce run
        states: List[State] = simulate_descent(
            alt0_m=alt0_m,
            lat0_deg=lat0_deg,
            lon0_deg=lon0_deg,
            dt_s=dt_s,
            descent_profile=descent_profile,
            wind_profile=wind_profile,
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

    ellipse = _compute_ellipse_from_samples(impacts, k_sigma=k_sigma) if impacts else None

    return impacts, ellipse
