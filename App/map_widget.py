from __future__ import annotations

from typing import List, Optional

import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Import du State de la simulation
from App.simulation import State


# =========================================================
# Styles de cartes disponibles (Folium / Leaflet)
# =========================================================
MAP_STYLES = {
    "Sombre (recommandé)": "CartoDB dark_matter",
    "Sombre doux": "CartoDB positron",
    "OpenStreetMap": "OpenStreetMap",
    "Satellite": "Esri.WorldImagery",
    "Gris sobre": "Esri.WorldGrayCanvas",
}


class MapWidget(QWebEngineView):
    """
    Widget carte basé sur Folium + QWebEngineView.

    - Affiche une carte centrée sur la position initiale
    - Trace la trajectoire montée / descente
    - Marque les points clés : lancement, burst, impact
    - Permet de changer dynamiquement le style de carte
    """

    def __init__(
        self,
        parent=None,
        default_lat: float = 48.0,
        default_lon: float = 2.0,
        default_zoom: int = 6,
    ):
        super().__init__(parent)

        # Paramètres par défaut
        self.default_lat = default_lat
        self.default_lon = default_lon
        self.default_zoom = default_zoom

        # Style de carte actif
        self._tile_style: str = "CartoDB dark_matter"

        # Dernière trajectoire affichée
        self._last_states: List[State] = []

        # Affiche la carte vide au démarrage
        self.show_base_map()

    # =====================================================
    # Carte de base
    # =====================================================
    def show_base_map(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        zoom: Optional[int] = None,
    ):
        """
        Affiche une carte vide centrée sur les coordonnées données.
        """
        lat = lat if lat is not None else self.default_lat
        lon = lon if lon is not None else self.default_lon
        zoom = zoom if zoom is not None else self.default_zoom

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
        """
        Efface la trajectoire et revient à la carte de base.
        """
        self._last_states = []
        self.show_base_map()

    # =====================================================
    # Gestion du style de carte
    # =====================================================
    def set_map_style(self, tile_style: str):
        """
        Change le style de carte (tiles).
        """
        try:
            self._tile_style = tile_style
            if self._last_states:
                self.show_trajectory(self._last_states)
            else:
                self.show_base_map()
        except Exception:
            # fallback de sécurité
            self._tile_style = "CartoDB dark_matter"
            self.show_base_map()

    # =====================================================
    # Affichage de la trajectoire
    # =====================================================
    def show_trajectory(self, states: List[State]):
        """
        Affiche la trajectoire complète sur la carte.
        """
        self._last_states = states

        if not states:
            self.show_base_map()
            return

        # Séparation montée / descente
        ascent = [s for s in states if s.phase == "ASCENT"]
        descent = [s for s in states if s.phase == "DESCENT"]

        # Centre de la carte
        if ascent:
            center = (ascent[-1].lat_deg, ascent[-1].lon_deg)
        else:
            center = (states[0].lat_deg, states[0].lon_deg)

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

        # ------------------------
        # Montée
        # ------------------------
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

        # ------------------------
        # Descente
        # ------------------------
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

    # =====================================================
    # Helpers
    # =====================================================
    def _add_label(self, m, s: State, title: str, color: str):
        """
        Ajoute une étiquette HTML stylée sur la carte.
        """
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
