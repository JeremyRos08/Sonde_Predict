# map_widget.py
from __future__ import annotations

from typing import List, Optional

import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView

from simulation import State



class MapWidget(QWebEngineView):
    def __init__(
        self,
        parent=None,
        default_lat: float = 49.75,
        default_lon: float = 4.92,
        default_zoom: int = 6,
    ):
        super().__init__(parent)
        self.default_lat = default_lat
        self.default_lon = default_lon
        self.default_zoom = default_zoom

        # Affiche une carte dès le démarrage
        self.show_base_map()

    def show_base_map(self, lat: Optional[float] = None, lon: Optional[float] = None, zoom: Optional[int] = None):
        """
        Affiche juste un fond de carte OSM centré sur (lat, lon)
        (sans trajectoire).
        """
        if lat is None:
            lat = self.default_lat
        if lon is None:
            lon = self.default_lon
        if zoom is None:
            zoom = self.default_zoom

        m = folium.Map(location=(lat, lon), zoom_start=zoom)
        html = m.get_root().render()
        self.setHtml(html)

    def clear_map(self):
        """
        Reset -> on réaffiche juste la carte de base.
        """
        self.show_base_map()

    def show_trajectory(self, states: List[State]):
        """
        Affiche la trajectoire si elle existe, sinon retombe sur la carte de base.
        """
        if not states:
            self.show_base_map()
            return

        lats = [s.lat_deg for s in states]
        lons = [s.lon_deg for s in states]

        start = (lats[0], lons[0])
        end = (lats[-1], lons[-1])

        # Carte centrée sur le point de départ
        m = folium.Map(location=start, zoom_start=7)

        # Polyline trajectoire
        folium.PolyLine(
            list(zip(lats, lons)),
            weight=3,
            opacity=0.9,
        ).add_to(m)

        # Marqueur départ
        folium.Marker(
            location=start,
            popup=f"Lancement<br>lat={start[0]:.5f}, lon={start[1]:.5f}",
        ).add_to(m)

        # Marqueur impact
        folium.Marker(
            location=end,
            popup=f"Impact<br>lat={end[0]:.5f}, lon={end[1]:.5f}",
            icon=folium.Icon(color="red"),
        ).add_to(m)

        html = m.get_root().render()
        self.setHtml(html)
