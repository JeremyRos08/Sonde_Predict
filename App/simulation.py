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

        v_desc = descent_profile.value(alt)
        wind_u, wind_v = wind_profile.value(alt)

        # Ajuster dt pour ne pas passer sous 0 d'un coup
        if alt - v_desc * dt_s < 0:
            dt = alt / max(v_desc, 1e-6)
        else:
            dt = dt_s

        alt_new = alt - v_desc * dt

        dx = wind_u * dt
        dy = wind_v * dt

        dlat = dy / EARTH_RADIUS_M
        dlon = dx / (EARTH_RADIUS_M * math.cos(lat))

        lat_new = lat + dlat
        lon_new = lon + dlon

        states.append(
            State(
                t_s=t,
                alt_m=alt,
                lat_deg=math.degrees(lat),
                lon_deg=math.degrees(lon),
                descent_ms=v_desc,
                wind_u_ms=wind_u,
                wind_v_ms=wind_v,
                phase = "DESCENT",
            )
        )

        t += dt
        alt = alt_new
        lat = lat_new
        lon = lon_new

        if alt <= 0.0:
            # dernier état sol
            states.append(
                State(
                    t_s=t,
                    alt_m=0.0,
                    lat_deg=math.degrees(lat),
                    lon_deg=math.degrees(lon),
                    descent_ms=v_desc,
                    wind_u_ms=wind_u,
                    wind_v_ms=wind_v,
                )
            )
            break

    return states


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
    rupture = False   # 🔥 événement clé

    for _ in range(max_steps):

        # ---------- RUPTURE BALLON ----------
        if ff_start_alt is not None and not rupture:
            if alt >= ff_start_alt:
                rupture = True
                phase = "DESCENT"

        # ---------- VITESSE VERTICALE ----------
        if phase == "ASCENT":
            v_vert = ascent_profile.value(alt)

            if alt + v_vert * dt_s > alt_burst_m:
                dt = (alt_burst_m - alt) / max(v_vert, 1e-6)
                alt_next = alt_burst_m
                phase = "DESCENT"
            else:
                dt = dt_s
                alt_next = alt + v_vert * dt

        else:  # DESCENT
            v_vert = descent_profile.value(alt)

            # 🔥 chute libre = accélération de la descente
            if rupture:
                v_vert *= free_fall_factor

            if alt - v_vert * dt_s < 0:
                dt = alt / max(v_vert, 1e-6)
                alt_next = 0.0
            else:
                dt = dt_s
                alt_next = alt - v_vert * dt

        # ---------- VENT ----------
        wind_u, wind_v = wind_profile.value(alt)

        dx = wind_u * dt
        dy = wind_v * dt

        lat += dy / EARTH_RADIUS_M
        lon += dx / (EARTH_RADIUS_M * math.cos(lat))

        # ---------- ÉTAT ----------
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
