"""
Extraction d’un profil de vent depuis un GRIB2 GFS.

Ce module :
- ouvre un GRIB GFS avec xarray + cfgrib
- extrait U/V sur niveaux isobares
- convertit pression → altitude
- retourne un WindProfile exploitable par le moteur

Auteur : Jeremy
"""

from __future__ import annotations

import math
import os
from typing import List

import xarray as xr

from App.profiles import WindPoint


def pressure_hpa_to_alt_m(p_hpa: float) -> float:
    """
    Approximation altitude (m) à partir de la pression (hPa).

    Atmosphère standard (formule aviation).
    Suffisant pour de la prédiction ballon.
    """
    p_hpa = max(p_hpa, 1.0)  # sécurité
    return 44307.693 * (1.0 - (p_hpa / 1013.25) ** 0.190284)


def extract_wind_profile_from_gfs_grib(
    grib_path: str,
    lat_deg: float,
    lon_deg: float,
) -> List[WindPoint]:
    """
    Extrait un profil vent (alt_m, u, v) depuis un fichier GFS GRIB2.

    Hypothèses :
    - vent sur niveaux isobares (isobaricInhPa)
    - coordonnées latitude / longitude standards
    - interpolation au point de grille le plus proche
    """

    # ⚠️ cfgrib peut garder un index obsolète → on le supprime
    idx_path = grib_path + ".idx"
    if os.path.exists(idx_path):
        os.remove(idx_path)

    ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                "typeOfLevel": "isobaricInhPa",
            }
        },
    )

    # Gestion robuste des noms de variables
    if "u" in ds:
        u_var = ds["u"]
    elif "u_component_of_wind" in ds:
        u_var = ds["u_component_of_wind"]
    else:
        raise ValueError("Vent U introuvable dans le GRIB.")

    if "v" in ds:
        v_var = ds["v"]
    elif "v_component_of_wind" in ds:
        v_var = ds["v_component_of_wind"]
    else:
        raise ValueError("Vent V introuvable dans le GRIB.")

    # Coordonnées
    if "latitude" not in ds.coords or "longitude" not in ds.coords:
        raise ValueError("Coordonnées lat/lon absentes du GRIB.")

    # Sélection du point de grille le plus proche
    u_point = u_var.sel(latitude=lat_deg, longitude=lon_deg, method="nearest")
    v_point = v_var.sel(latitude=lat_deg, longitude=lon_deg, method="nearest")

    if "isobaricInhPa" not in u_point.coords:
        raise ValueError("Dimension verticale isobaricInhPa absente.")

    levels_hpa = u_point["isobaricInhPa"].values
    u_vals = u_point.values
    v_vals = v_point.values

    points: List[WindPoint] = []

    for p_hpa, u, v in zip(levels_hpa, u_vals, v_vals):
        if math.isnan(u) or math.isnan(v):
            continue

        alt_m = pressure_hpa_to_alt_m(float(p_hpa))
        points.append(
            WindPoint(
                alt_m=alt_m,
                wind_u_ms=float(u),
                wind_v_ms=float(v),
            )
        )

    # Tri altitude croissante (logique moteur)
    points.sort(key=lambda wp: wp.alt_m)

    return points
