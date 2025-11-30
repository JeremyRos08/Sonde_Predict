# gfs_download.py
from __future__ import annotations

from typing import List
from urllib.parse import urlencode, quote_plus

import requests


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
    Construit l'URL NOMADS pour GFS 0.25°.
    Ex:
      file=gfs.t12z.pgrb2.0p25.f000
      dir=/gfs.YYYYMMDD/12/atmos
    """
    file_name = f"gfs.t{cycle_hour:02d}z.pgrb2.0p25.f{fhour:03d}"
    dir_path = f"/gfs.{date_yyyymmdd}/{cycle_hour:02d}/atmos"

    params = {
        "file": file_name,
        "dir": dir_path,
        "leftlon": lon_min,
        "rightlon": lon_max,
        "toplat": lat_max,
        "bottomlat": lat_min,
    }

    # Niveaux
    if all_levels:
        params["all_lev"] = "on"
    else:
        for lev in levels_hpa:
            key = f"lev_{int(lev)}_mb"
            params[key] = "on"

    # Variables (UGRD, VGRD, TMP, etc.)
    for v in vars_:
        key = f"var_{v}"
        params[key] = "on"

    query = urlencode(params, doseq=True, quote_via=quote_plus)
    return f"{BASE_URL}?{query}"


def download_gfs(url: str, output_path: str, timeout: int = 120):
    """
    Télécharge le GRIB2 depuis NOMADS et l'enregistre dans output_path.
    """
    print(f"[GFS] URL : {url}")
    print(f"[GFS] Téléchargement vers : {output_path}")

    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", "0")) or None
        downloaded = 0
        chunk_size = 1024 * 1024

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = 100.0 * downloaded / total
                    print(f"\r[GFS] {downloaded/1e6:6.1f} / {total/1e6:6.1f} Mo ({pct:5.1f}%)", end="")
                else:
                    print(f"\r[GFS] {downloaded/1e6:6.1f} Mo téléchargés", end="")

    print("\n[GFS] Téléchargement terminé.")
