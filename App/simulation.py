# simulation.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from profiles import DescentProfile, AscentProfile, WindProfile

EARTH_RADIUS_M = 6371000.0


@dataclass
class State:
    t_s: float
    alt_m: float
    lat_deg: float
    lon_deg: float
    descent_ms: float
    wind_u_ms: float
    wind_v_ms: float
    phase: str = "DESCENT"


# ============================================================
# DESCENTE SEULE
# ============================================================
def simulate_descent(
    alt0_m: float,
    lat0_deg: float,
    lon0_deg: float,
    dt_s: float,
    descent_profile: DescentProfile,
    wind_profile: WindProfile,
    max_steps: int = 40000,
) -> List[State]:

    states: List[State] = []

    t = 0.0
    alt = alt0_m
    lat = math.radians(lat0_deg)
    lon = math.radians(lon0_deg)

    for _ in range(max_steps):

        if alt <= 0.0:
            break

        # --- vitesse verticale ---
        v_desc = descent_profile.value(alt)

        # --- dt ajusté sol ---
        if alt - v_desc * dt_s < 0:
            dt = alt / max(v_desc, 1e-6)
        else:
            dt = dt_s

        # --- vent (milieu de couche) ---
        alt_mid = alt - 0.5 * v_desc * dt
        wind_u, wind_v = wind_profile.value(alt_mid)

        # --- intégration ---
        alt -= v_desc * dt
        lat += (wind_v * dt) / EARTH_RADIUS_M
        lon += (wind_u * dt) / (EARTH_RADIUS_M * math.cos(lat))

        states.append(
            State(
                t_s=t,
                alt_m=max(alt, 0.0),
                lat_deg=math.degrees(lat),
                lon_deg=math.degrees(lon),
                descent_ms=v_desc,
                wind_u_ms=wind_u,
                wind_v_ms=wind_v,
                phase="DESCENT",
            )
        )

        t += dt

        if alt <= 0.0:
            break

    return states


# ============================================================
# VOL COMPLET (MONTÉE + DESCENTE)
# ============================================================
def simulate_flight(
    alt_start_m: float,
    alt_burst_m: float,
    lat0_deg: float,
    lon0_deg: float,
    dt_s: float,
    ascent_profile: AscentProfile,
    descent_profile: DescentProfile,
    wind_profile: WindProfile,
    ff_start_alt: float | None,
    free_fall_factor: float,
    max_steps: int = 40000,
) -> List[State]:

    states: List[State] = []

    t = 0.0
    alt = alt_start_m
    lat = math.radians(lat0_deg)
    lon = math.radians(lon0_deg)

    phase = "ASCENT"
    rupture = False

    for _ in range(max_steps):

        # ======================
        # RUPTURE BALLOON
        # ======================
        if ff_start_alt is not None and not rupture:
            if alt >= ff_start_alt:
                rupture = True
                phase = "DESCENT"

        # ======================
        # VITESSE VERTICALE
        # ======================
        if phase == "ASCENT":

            v_vert = ascent_profile.value(alt)

            if alt + v_vert * dt_s >= alt_burst_m:
                dt = (alt_burst_m - alt) / max(v_vert, 1e-6)
                alt_next = alt_burst_m
                phase = "DESCENT"
            else:
                dt = dt_s
                alt_next = alt + v_vert * dt

            alt_mid = alt + 0.5 * v_vert * dt

        else:  # DESCENT

            v_vert = descent_profile.value(alt)

            # 🚀 accélération post-burst (zone critique)
            if alt > 18000:
                v_vert *= 1.3

            # 🔥 chute libre forcée
            if rupture:
                v_vert *= free_fall_factor

            if alt - v_vert * dt_s <= 0:
                dt = alt / max(v_vert, 1e-6)
                alt_next = 0.0
            else:
                dt = dt_s
                alt_next = alt - v_vert * dt

            alt_mid = alt - 0.5 * v_vert * dt

        # ======================
        # VENT (MID-LAYER)
        # ======================
        wind_u, wind_v = wind_profile.value(alt_mid)

        lat += (wind_v * dt) / EARTH_RADIUS_M
        lon += (wind_u * dt) / (EARTH_RADIUS_M * math.cos(lat))

        # ======================
        # ÉTAT
        # ======================
        states.append(
            State(
                t_s=t,
                alt_m=alt,
                lat_deg=math.degrees(lat),
                lon_deg=math.degrees(lon),
                descent_ms=(-v_vert if phase == "ASCENT" else v_vert),
                wind_u_ms=wind_u,
                wind_v_ms=wind_v,
                phase=phase,
            )
        )

        t += dt
        alt = alt_next

        if phase == "DESCENT" and alt <= 0.0:
            break

    return states
