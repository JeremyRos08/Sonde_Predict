from __future__ import annotations

"""
Gestion du téléchargement des données GFS depuis NOMADS (NOAA).

Ce module me sert à :
- construire proprement une URL GFS 0.25° filtrée (zone, niveaux, variables)
- télécharger un fichier GRIB2 en gérant les cas d'erreur (404, réseau)
"""

from typing import List
from urllib.parse import urlencode, quote_plus

import requests


# URL de base NOMADS pour GFS 0.25°
BASE_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"


def build_gfs_url(
    date_yyyymmdd: str,
    cycle_hour: int,
    fhour: int,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    vars_: List[str],
    levels_hpa: List[int],
    all_levels: bool,
) -> str:
    """
    Construit l'URL NOMADS pour télécharger un sous-ensemble GFS 0.25°.

    Je filtre directement côté serveur :
    - la zone géographique
    - les niveaux de pression
    - les variables météo (UGRD, VGRD, TMP, etc.)

    Exemple de fichier ciblé :
      gfs.t12z.pgrb2.0p25.f003
    """

    # Nom du fichier GFS (run + échéance)
    file_name = f"gfs.t{cycle_hour:02d}z.pgrb2.0p25.f{fhour:03d}"

    # Répertoire NOMADS correspondant
    dir_path = f"/gfs.{date_yyyymmdd}/{cycle_hour:02d}/atmos"

    # Paramètres géographiques de base
    params = {
        "file": file_name,
        "dir": dir_path,
        "leftlon": lon_min,
        "rightlon": lon_max,
        "toplat": lat_max,
        "bottomlat": lat_min,
    }

    # ----- NIVEAUX -----
    # Soit je prends tous les niveaux, soit une liste précise en hPa
    if all_levels:
        params["all_lev"] = "on"
    else:
        for lev in levels_hpa:
            params[f"lev_{int(lev)}_mb"] = "on"

    # ----- VARIABLES -----
    # Ex : UGRD, VGRD, TMP…
    for var in vars_:
        params[f"var_{var}"] = "on"

    # Encodage propre de l'URL
    query = urlencode(params, doseq=True, quote_via=quote_plus)
    return f"{BASE_URL}?{query}"


def download_gfs(url: str, output_path: str, timeout: int = 120) -> bool:
    """
    Télécharge un fichier GRIB2 GFS depuis NOMADS.

    Je retourne :
    - True  → téléchargement OK
    - False → fichier non disponible (404 ou erreur réseau)

    Le téléchargement est fait en streaming pour éviter de charger
    tout le fichier en mémoire.
    """

    print(f"[GFS] URL : {url}")

    try:
        with requests.get(url, stream=True, timeout=timeout) as response:

            # Cas classique NOMADS : fichier pas encore publié
            if response.status_code == 404:
                print("[GFS] ❌ 404 – fichier non disponible sur NOMADS")
                return False

            # Autres erreurs HTTP
            response.raise_for_status()

            total_size = int(response.headers.get("Content-Length", "0")) or None
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 Mo

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)

                    # Affichage progression lisible
                    if total_size:
                        pct = 100.0 * downloaded / total_size
                        print(
                            f"\r[GFS] {downloaded/1e6:6.1f} / {total_size/1e6:6.1f} Mo ({pct:5.1f}%)",
                            end="",
                        )
                    else:
                        print(
                            f"\r[GFS] {downloaded/1e6:6.1f} Mo téléchargés",
                            end="",
                        )

        print("\n[GFS] ✅ Téléchargement terminé")
        return True

    except requests.RequestException as e:
        print(f"\n[GFS] ❌ Erreur réseau : {e}")
        return False
