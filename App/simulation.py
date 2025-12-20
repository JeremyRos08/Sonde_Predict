"""
simulation.py

Moteur de simulation principal de Sonde_Predict.

Ici je gère :
- la descente seule d’un objet sous parachute / chute libre
- le vol complet ballon : montée → rupture → descente
- l’intégration temporelle avec vent dépendant de l’altitude

Le but n’est pas une simulation CFD parfaite,
mais un modèle robuste, stable et lisible,
adapté à la prévision de trajectoire.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from App.profiles import DescentProfile, AscentProfile, WindProfile

# Rayon moyen de la Terre (m)
EARTH_RADIUS_M = 6_371_000.0


# ============================================================
# STRUCTURE D'ÉTAT
# ============================================================

@dataclass
class State:
    """
    État instantané de la sonde / objet.

    Chaque State représente un point temporel de la trajectoire.
    """
    t_s: float            # temps écoulé depuis le début (s)
    alt_m: float          # altitude (m)
    lat_deg: float        # latitude (°)
    lon_deg: float        # longitude (°)
    descent_ms: float     # vitesse verticale (m/s)
    wind_u_ms: float      # vent zonal (est-ouest, m/s)
    wind_v_ms: float      # vent méridien (nord-sud, m/s)
    phase: str = "DESCENT"  # ASCENT ou DESCENT


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
    """
    Simule uniquement une descente depuis une altitude initiale.

    Utilisé lorsque :
    - on ne simule pas la montée
    - on connaît déjà l’altitude de largage

    Intégration simple, robuste, avec vent dépendant de l’altitude.
    """

    states: List[State] = []

    # Temps et position initiale
    t = 0.0
    alt = alt0_m
    lat = math.radians(lat0_deg)
    lon = math.radians(lon0_deg)

    for _ in range(max_steps):

        # Fin de simulation au sol
        if alt <= 0.0:
            break

        # ------------------------
        # Vitesse verticale
        # ------------------------
        v_desc = descent_profile.value(alt)

        # Ajustement du pas de temps pour ne pas passer sous le sol
        if alt - v_desc * dt_s < 0:
            dt = alt / max(v_desc, 1e-6)
        else:
            dt = dt_s

        # ------------------------
        # Vent (milieu de couche)
        # ------------------------
        alt_mid = alt - 0.5 * v_desc * dt
        wind_u, wind_v = wind_profile.value(alt_mid)

        # ------------------------
        # Intégration position
        # ------------------------
        alt -= v_desc * dt
        lat += (wind_v * dt) / EARTH_RADIUS_M
        lon += (wind_u * dt) / (EARTH_RADIUS_M * math.cos(lat))

        # Sauvegarde de l’état
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

    return states


# ============================================================
# VOL COMPLET : MONTÉE + DESCENTE
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
    """
    Simule un vol complet de ballon :

    - montée contrôlée jusqu’à l’altitude de burst
    - rupture (optionnelle à une altitude définie)
    - descente sous parachute ou chute libre accélérée

    Le modèle est volontairement simple mais stable,
    et cohérent avec les données météo (GFS).
    """

    states: List[State] = []

    # Conditions initiales
    t = 0.0
    alt = alt_start_m
    lat = math.radians(lat0_deg)
    lon = math.radians(lon0_deg)

    phase = "ASCENT"
    rupture = False

    for _ in range(max_steps):

        # ======================
        # Détection rupture ballon
        # ======================
        if ff_start_alt is not None and not rupture:
            if alt >= ff_start_alt:
                rupture = True
                phase = "DESCENT"

        # ======================
        # Calcul vitesse verticale
        # ======================
        if phase == "ASCENT":

            v_vert = ascent_profile.value(alt)

            # Arrivée au burst
            if alt + v_vert * dt_s >= alt_burst_m:
                dt = (alt_burst_m - alt) / max(v_vert, 1e-6)
                alt_next = alt_burst_m
                phase = "DESCENT"
            else:
                dt = dt_s
                alt_next = alt + v_vert * dt

            alt_mid = alt + 0.5 * v_vert * dt

        else:
            # DESCENTE
            v_vert = descent_profile.value(alt)

            # Accélération post-burst (zone critique haute altitude)
            if alt > 18_000:
                v_vert *= 1.3

            # Chute libre forcée
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
        # Vent (milieu de couche)
        # ======================
        wind_u, wind_v = wind_profile.value(alt_mid)

        lat += (wind_v * dt) / EARTH_RADIUS_M
        lon += (wind_u * dt) / (EARTH_RADIUS_M * math.cos(lat))

        # ======================
        # Sauvegarde état
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
