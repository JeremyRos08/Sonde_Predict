# simulation.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from profiles import DescentProfile, WindProfile

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


def simulate_descent(
    alt0_m: float,
    lat0_deg: float,
    lon0_deg: float,
    dt_s: float,
    descent_profile: DescentProfile,
    wind_profile: WindProfile,
    max_steps: int = 20000,
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
