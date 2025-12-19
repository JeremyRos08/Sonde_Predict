from __future__ import annotations

from typing import List, Optional
import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView
from simulation import State

# Styles disponibles
MAP_STYLES = {
    "Sombre (recommandé)": "CartoDB dark_matter",
    "Sombre doux": "CartoDB positron",
    "OpenStreetMap": "OpenStreetMap",
    "Satellite": "Esri.WorldImagery",
    "Gris sobre": "Esri.WorldGrayCanvas",
}

class MapWidget(QWebEngineView):
    def __init__(
        self,
        parent=None,
        default_lat: float = 48.00,
        default_lon: float = 2.00,
        default_zoom: int = 6,
    ):
        super().__init__(parent)

        self.default_lat = default_lat
        self.default_lon = default_lon
        self.default_zoom = default_zoom

        self._tile_style = "CartoDB dark_matter"
        self._last_states: List[State] = []

        self.show_base_map()

    # -----------------------------------------------------
    # Base map
    # -----------------------------------------------------
    def show_base_map(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        zoom: Optional[int] = None,
    ):
        if lat is None:
            lat = self.default_lat
        if lon is None:
            lon = self.default_lon
        if zoom is None:
            zoom = self.default_zoom

        m = folium.Map(
            location=(lat, lon),
            zoom_start=zoom,
            tiles=None,
            control_scale=True,
        )

        folium.TileLayer(
            tiles=self._tile_style,
            name="Base",
            control=False,
        ).add_to(m)

        self.setHtml(m.get_root().render())

    def clear_map(self):
        self._last_states = []
        self.show_base_map()

    # -----------------------------------------------------
    # Style
    # -----------------------------------------------------
    def set_map_style(self, tile_style: str):
        self._tile_style = tile_style

        if self._last_states:
            self.show_trajectory(self._last_states)
        else:
            self.show_base_map()

    #-------------------------------------------------------
    # Fallback
    #-------------------------------------------------------
    def set_map_style(self, tile_style: str):
        try:
            self._tile_style = tile_style
            if self._last_states:
                self.show_trajectory(self._last_states)
            else:
                self.show_base_map()
        except Exception:
            self._tile_style = "CartoDB dark_matter"
            self.show_base_map()

    # -----------------------------------------------------
    # Trajectoire
    # -----------------------------------------------------
    def show_trajectory(self, states: List[State]):
        self._last_states = states

        if not states:
            self.show_base_map()
            return

        ascent = [s for s in states if s.phase == "ASCENT"]
        descent = [s for s in states if s.phase == "DESCENT"]

        center = (
            (ascent[-1].lat_deg, ascent[-1].lon_deg)
            if ascent
            else (states[0].lat_deg, states[0].lon_deg)
        )

        m = folium.Map(
            location=center,
            zoom_start=7,
            tiles=None,
            control_scale=True,
        )

        folium.TileLayer(
            tiles=self._tile_style,
            name="Base",
            control=False,
        ).add_to(m)

        # ---------------- Montée ----------------
        if ascent:
            folium.PolyLine(
                [(s.lat_deg, s.lon_deg) for s in ascent],
                color="#00bfff",
                weight=4,
                opacity=1,
            ).add_to(m)

            launch = ascent[0]
            burst = ascent[-1]

            self._add_label(m, launch, "🚀 Lancement", "#00ff88")
            self._add_label(m, burst, "💥 Burst", "#ff4444")

        # ---------------- Descente ----------------
        if descent:
            folium.PolyLine(
                [(s.lat_deg, s.lon_deg) for s in descent],
                color="#ffa500",
                weight=4,
                opacity=1,
                dash_array="6,6",
            ).add_to(m)

            impact = descent[-1]
            self._add_label(m, impact, "🎯 Impact", "#ffa500")

        self.setHtml(m.get_root().render())

    # -----------------------------------------------------
    # Label helper
    # -----------------------------------------------------
    def _add_label(self, m, s: State, title: str, color: str):
        folium.Marker(
            location=(s.lat_deg, s.lon_deg),
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    background:#000;
                    color:{color};
                    padding:6px 8px;
                    border-radius:6px;
                    font-size:12px;
                    font-weight:bold;
                    box-shadow:0 0 8px {color};
                    white-space:nowrap;
                ">
                    {title}<br>
                    Lat {s.lat_deg:.4f}°<br>
                    Lon {s.lon_deg:.4f}°
                </div>
                """
            ),
        ).add_to(m)
