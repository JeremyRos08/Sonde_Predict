# gfs_utils.py
from __future__ import annotations

import math
from typing import List

import xarray as xr

from profiles import WindPoint


def pressure_hpa_to_alt_m(p_hpa: float) -> float:
    """
    Approximation altitude (m) à partir de la pression en hPa
    (atmosphère standard, formule aviation).
    """
    # Évite division par 0
    p_hpa = max(p_hpa, 1.0)
    return 44307.693 * (1.0 - (p_hpa / 1013.25) ** 0.190284)


def extract_wind_profile_from_gfs_grib(
    grib_path: str,
    lat_deg: float,
    lon_deg: float,
) -> List[WindPoint]:
    """
    Extrait un profil vent (alt_m, u, v) à partir d'un fichier GFS GRIB2 local.
    On suppose :
      - variables 'u' et 'v' en composantes de vent
      - dimension verticale 'isobaricInhPa'
      - coords 'latitude', 'longitude'

    On interpole sur le point de grille le plus proche de (lat_deg, lon_deg).
    """

    # On ouvre le jeu de données avec cfgrib via xarray
    ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                "typeOfLevel": "isobaricInhPa"
            }
        },
    )

    # Selon les fichiers, les noms peuvent être 'u', 'v' ou 'u_component_of_wind'
    # / 'v_component_of_wind'. On gère les deux cas.
    if "u" in ds:
        u_var = ds["u"]
    elif "u_component_of_wind" in ds:
        u_var = ds["u_component_of_wind"]
    else:
        raise ValueError("Variable de vent U introuvable dans le GRIB (u / u_component_of_wind).")

    if "v" in ds:
        v_var = ds["v"]
    elif "v_component_of_wind" in ds:
        v_var = ds["v_component_of_wind"]
    else:
        raise ValueError("Variable de vent V introuvable dans le GRIB (v / v_component_of_wind).")

    # Coordonnées lat/lon
    lat_name = "latitude"
    lon_name = "longitude"
    if lat_name not in ds.coords or lon_name not in ds.coords:
        raise ValueError("Coordonnées latitude/longitude introuvables dans le GRIB.")

    # Sélection du point de grille le plus proche
    u_point = u_var.sel({lat_name: lat_deg, lon_name: lon_deg}, method="nearest")
    v_point = v_var.sel({lat_name: lat_deg, lon_name: lon_deg}, method="nearest")

    # Niveau de pression (en hPa)
    if "isobaricInhPa" not in u_point.coords:
        raise ValueError("Dimension verticale 'isobaricInhPa' introuvable dans le GRIB GFS.")
    levels_hpa = u_point["isobaricInhPa"].values  # ex: [1000, 950, 900, ...]

    u_vals = u_point.values
    v_vals = v_point.values

    # On fabrique une liste de WindPoint avec altitude approx
    points: List[WindPoint] = []
    for p_hpa, u, v in zip(levels_hpa, u_vals, v_vals):
        alt_m = pressure_hpa_to_alt_m(float(p_hpa))
        points.append(
            WindPoint(
                alt_m=alt_m,
                wind_u_ms=float(u),
                wind_v_ms=float(v),
            )
        )

    # On les trie par altitude croissante (0 -> max) pour la logique interne,
    # l'affichage dans la table pourra les remettre en décroissant.
    points.sort(key=lambda wp: wp.alt_m)

    return points
