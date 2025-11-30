# main_window.py
from __future__ import annotations

import os
import csv
import math
import simulation

import gfs_utils
import requests
import gfs_download
import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QSlider

from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 # nécessaire pour le 3D
from PyQt5.QtWidgets import QSizePolicy

from typing import List, Optional
from montecarlo import ImpactSample, EllipseResult, run_monte_carlo
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)

from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QTabWidget,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QAction,
    QSizePolicy,  
    QCheckBox,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from profiles import DescentProfile, WindProfile, DescentPoint, WindPoint
from simulation import simulate_descent, State
from map_widget import MapWidget

# Chutte 3D
class ThreeDCanvas(FigureCanvas):
    """
    Trajectoire 3D : Est-Ouest (km), Nord-Sud (km), Altitude (m).
    """
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(7, 6))
        super().__init__(fig)
        self.setParent(parent)

        self.ax3d = fig.add_subplot(111, projection="3d")
                # Utiliser presque tout l'espace du canvas
        fig.subplots_adjust(
            left=0.02,
            right=0.98,
            top=0.97,
            bottom=0.05,
        )


        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

        # Données stockées pour l'anim
        self._xs_km: List[float] = []
        self._ys_km: List[float] = []
        self._alts: List[float] = []
        self._marker = None
        self._line = None
        self._last_states: List[State] = []

        # Élévation fixe (angle vertical) pour la vue 3D
        self._fixed_elev = 25  # tu peux changer à 20 / 30 si tu préfères

        # Bloquer la rotation en pitch/roll : on force l'elev à rester fixe
        self.mpl_connect("motion_notify_event", self._on_3d_mouse_move)

    def plot_trajectory_3d(self, states: List[State]):
        self.ax3d.clear()
        self._xs_km = []
        self._ys_km = []
        self._alts = []
        self._marker = None
        self._line = None
        self._last_states = list(states) 

        if not states:
            self.ax3d.set_title("Aucune simulation disponible")
            self.draw()
            return

        # Récupère les lat/lon/alt
        lats = [s.lat_deg for s in states]
        lons = [s.lon_deg for s in states]
        alts = [s.alt_m for s in states]

        # Référence locale = premier point
        lat0_deg = lats[0]
        lon0_deg = lons[0]
        lat0_rad = math.radians(lat0_deg)

        xs_km: List[float] = []
        ys_km: List[float] = []

        for lat_deg, lon_deg in zip(lats, lons):
            dlat = math.radians(lat_deg - lat0_deg)
            dlon = math.radians(lon_deg - lon0_deg)

            x_m = simulation.EARTH_RADIUS_M * dlon * math.cos(lat0_rad)   # Est +
            y_m = simulation.EARTH_RADIUS_M * dlat                        # Nord +

            xs_km.append(x_m / 1000.0)
            ys_km.append(y_m / 1000.0)

        self._xs_km = xs_km
        self._ys_km = ys_km
        self._alts = alts

        # Trajectoire complète
        (self._line,) = self.ax3d.plot(xs_km, ys_km, alts, marker=".", linewidth=1.0)

        # Limites Z
        zmax = max(alts)
        zmin = min(alts)
        if zmax == zmin:
            zmax = zmin + 10.0
        self.ax3d.set_zlim(zmin, zmax)

        # ----- Croix au sol + N / S / E / O -----
        r = max(
            max(abs(x) for x in xs_km + [0.0]),
            max(abs(y) for y in ys_km + [0.0]),
            0.1,
        )
        r *= 1.1
        base_z = zmin

        self.ax3d.plot([0, r], [0, 0], [base_z, base_z], linestyle="--", linewidth=1.0)
        self.ax3d.plot([0, -r], [0, 0], [base_z, base_z], linestyle="--", linewidth=1.0)
        self.ax3d.plot([0, 0], [0, r], [base_z, base_z], linestyle="--", linewidth=1.0)
        self.ax3d.plot([0, 0], [0, -r], [base_z, base_z], linestyle="--", linewidth=1.0)

        self.ax3d.text(r, 0, base_z, "E", fontsize=9)
        self.ax3d.text(-r, 0, base_z, "O", fontsize=9)
        self.ax3d.text(0, r, base_z, "N", fontsize=9)
        self.ax3d.text(0, -r, base_z, "S", fontsize=9)

        self.ax3d.set_xlabel("Est-Ouest (km)")
        self.ax3d.set_ylabel("Nord-Sud (km)")
        self.ax3d.set_zlabel("Altitude (m)")
        self.ax3d.set_title("Trajectoire 3D de la chute")

        # 👉 aspect un peu plus "écran large" pour que ça soit lisible
        try:
            self.ax3d.set_box_aspect((1.5, 1.5, 0.8))
        except Exception:
            # vieux Matplotlib : ignore si pas supporté
            pass

        self.ax3d.view_init(elev=self._fixed_elev, azim=135)

        # Marqueur initial (au début de la chute)
        self.update_marker(0) 
        
        self.draw()

        

    def reset_view(self):
        """Recalcule complètement la vue 3D à partir de la dernière simulation."""
        if not self._last_states:
            return
        self.plot_trajectory_3d(self._last_states)
    

    def update_marker(self, idx: int):
        """Déplace le marqueur 3D sur l'échantillon idx."""
        if not self._xs_km or not self._ys_km or not self._alts:
            return
        if idx < 0 or idx >= len(self._xs_km):
            return

        # Supprime l'ancien marqueur si besoin
        if self._marker is not None:
            self._marker.remove()
            self._marker = None

        x = self._xs_km[idx]
        y = self._ys_km[idx]
        z = self._alts[idx]

        self._marker = self.ax3d.scatter([x], [y], [z], s=40)

        self.draw_idle()



    def _on_3d_mouse_move(self, event):
        # On ne s'occupe que de notre axe 3D
        if event.inaxes is not self.ax3d:
            return

        # On ne réagit que quand le bouton gauche est enfoncé (rotation)
        if not hasattr(event, "button"):
            return
        # Matplotlib : 1 = bouton gauche
        if event.button != 1:
            return

        # On laisse Matplotlib mettre à jour l'azim, mais on réimpose l'elev fixe
        current_azim = self.ax3d.azim
        self.ax3d.view_init(elev=self._fixed_elev, azim=current_azim)
        self.draw_idle()


# ---------- Canvas trajectoire 2D ----------

class TrajectoryCanvas(FigureCanvas):
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(7, 7))
        super().__init__(fig)
        self.setParent(parent)

        # 4 sous-graphiques : 2 x 2
        self.ax_alt = fig.add_subplot(2, 2, 1)                        # Altitude vs temps
        self.ax_dist = fig.add_subplot(2, 2, 2)                       # Distance vs temps
        self.ax_map = fig.add_subplot(2, 2, 3)                        # Trajectoire sol
        self.ax_polar = fig.add_subplot(2, 2, 4, projection="polar")  # Vue polaire / boussole
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()
        
    def plot_trajectory(self, states: List[State]):
        # Reset
        self.ax_alt.clear()
        self.ax_dist.clear()
        self.ax_map.clear()
        self.ax_polar.clear()

        if not states:
            self.draw()
            return

        # --- Données de base ---
        t_s = [s.t_s for s in states]           # temps en secondes
        t_min = [ts / 60.0 for ts in t_s]       # temps en minutes
        alt = [s.alt_m for s in states]
        lats = [s.lat_deg for s in states]
        lons = [s.lon_deg for s in states]

        # Référence = premier point
        lat0_deg = lats[0]
        lon0_deg = lons[0]
        lat0_rad = math.radians(lat0_deg)

        # --- Distance horizontale et angle (boussole) ---
        dist_km: List[float] = []
        theta: List[float] = []

        for lat_deg, lon_deg in zip(lats, lons):
            dlat = math.radians(lat_deg - lat0_deg)
            dlon = math.radians(lon_deg - lon0_deg)

            # Approx locale : coordonnées métriques autour du point de départ
            x = simulation.EARTH_RADIUS_M * dlon * math.cos(lat0_rad)  # +x = Est
            y = simulation.EARTH_RADIUS_M * dlat                       # +y = Nord

            r = math.hypot(x, y) / 1000.0  # km
            dist_km.append(r)

            # Angle façon boussole :
            #  - 0 rad = Nord
            #  - +π/2 = Est
            #  - ±π   = Sud
            #  - -π/2 = Ouest
            angle = math.atan2(x, y)
            theta.append(angle)

        # ---------- 1) Altitude vs temps (min) ----------
        self.ax_alt.plot(t_min, alt, marker=".")
        self.ax_alt.set_xlabel("Temps (min)")
        self.ax_alt.set_ylabel("Altitude (m)")
        self.ax_alt.set_title("Altitude en fonction du temps")
        self.ax_alt.grid(True)

        # ---------- 2) Distance horizontale vs temps (min) ----------
        self.ax_dist.plot(dist_km, alt, marker=".")
        self.ax_dist.set_xlabel("Distance horizontale (km)")
        self.ax_dist.set_ylabel("Altidude (m)")
        self.ax_dist.set_title("Altitude et distance sol")
        self.ax_dist.grid(True)

        # ---------- 3) Trajectoire sol (lon/lat) ----------
        self.ax_map.plot(lons, lats, marker=".")
        self.ax_map.set_xlabel("Longitude (°)")
        self.ax_map.set_ylabel("Latitude (°)")
        self.ax_map.set_title("Trajectoire au sol (lon / lat)")
        self.ax_map.grid(True)

        # ---------- 4) Vue polaire type boussole ----------
        self.ax_polar.plot(theta, dist_km, marker=".")

        # 0° = Nord, sens horaire (comme une boussole)
        self.ax_polar.set_theta_zero_location("N")
        self.ax_polar.set_theta_direction(-1)

        # Marquage N / E / S / W
        self.ax_polar.set_thetagrids(
            [0, 90, 180, 270],
            labels=["N", "E", "S", "W"],
        )

        self.ax_polar.set_title("Vue polaire (boussole)\nDistance vs direction")
        self.ax_polar.set_rlabel_position(135)
        self.ax_polar.set_ylabel("Distance (km)", labelpad=20)
        self.ax_polar.grid(True)

        self.figure.tight_layout()
        self.draw()

class MonteCarloCanvas(FigureCanvas):
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(8, 5))
        super().__init__(fig)
        self.setParent(parent)

        # Deux graphes l'un sous l'autre : zone d'impact en haut, histo en bas
        self.ax_xy = fig.add_subplot(2, 1, 1)
        self.ax_dist = fig.add_subplot(2, 1, 2)

        fig.subplots_adjust(
            left=0.07,
            right=0.98,
            top=0.95,
            bottom=0.08,
            hspace=0.35,
        )

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

        # --- stockage pour tooltips ---
        self._samples: List[ImpactSample] = []
        self._xs_km: List[float] = []
        self._ys_km: List[float] = []
        self._rs_km: List[float] = []
        self._sc = None          # scatter
        self._annot = None       # annotation (créée dans plot_impacts)

        # Connexion événement souris
        self.mpl_connect("motion_notify_event", self._on_hover)

    def plot_impacts(self, samples: List[ImpactSample], ellipse: Optional[EllipseResult]):
        # Clear
        self.ax_xy.clear()
        self.ax_dist.clear()

        # Réinitialise les structures
        self._samples = []
        self._xs_km = []
        self._ys_km = []
        self._rs_km = []
        self._sc = None
        self._annot = None

        if not samples:
            self.ax_xy.set_title("Aucun impact Monte Carlo (pas de données)")
            self.ax_xy.grid(True)
            self.ax_dist.set_title("Distribution distance (vide)")
            self.ax_dist.grid(True)
            self.draw()
            return

        # Stocke les samples pour les tooltips
        self._samples = samples
        xs_km = [s.x_m / 1000.0 for s in samples]
        ys_km = [s.y_m / 1000.0 for s in samples]
        rs_km = [(s.x_m**2 + s.y_m**2) ** 0.5 / 1000.0 for s in samples]
        self._xs_km = xs_km
        self._ys_km = ys_km
        self._rs_km = rs_km

        # Annotation (bulle) APRÈS le clear
        self._annot = self.ax_xy.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w", alpha=0.8),
            arrowprops=dict(arrowstyle="->"),
        )
        self._annot.set_visible(False)

        # ---------- 1) Nuage XY + ellipse ----------
        self._sc = self.ax_xy.scatter(
            xs_km,
            ys_km,
            s=20,          # un peu plus gros, plus facile à viser
            alpha=0.6,
            label="Impacts",
            picker=True,   # important pour contains()
        )
        self.ax_xy.scatter([0.0], [0.0], marker="+", s=60, label="Largage")

        # Centre pour cadrer le zoom
        if ellipse is not None and ellipse.a_m > 0.0 and ellipse.b_m > 0.0:
            cx_km = ellipse.cx_m / 1000.0
            cy_km = ellipse.cy_m / 1000.0
        else:
            cx_km = sum(xs_km) / len(xs_km)
            cy_km = sum(ys_km) / len(ys_km)

        # Ellipse si dispo
        if ellipse is not None and ellipse.a_m > 0.0 and ellipse.b_m > 0.0:
            a_km = ellipse.a_m / 1000.0
            b_km = ellipse.b_m / 1000.0
            ts = [i * 2.0 * math.pi / 200 for i in range(201)]
            ex = []
            ey = []
            cos_a = math.cos(ellipse.angle_rad)
            sin_a = math.sin(ellipse.angle_rad)
            for t in ts:
                xr = a_km * math.cos(t)
                yr = b_km * math.sin(t)
                x = cx_km + xr * cos_a - yr * sin_a
                y = cy_km + xr * sin_a + yr * cos_a
                ex.append(x)
                ey.append(y)

            self.ax_xy.plot(ex, ey, linewidth=1.5, label="Ellipse ~zone")
            self.ax_xy.scatter([cx_km], [cy_km], marker="x", s=50, label="Centre ellipse")
            

        # Zoom autour du centre
        max_dx = max(abs(x - cx_km) for x in xs_km + [cx_km])
        max_dy = max(abs(y - cy_km) for y in ys_km + [cy_km])
        r = max(max_dx, max_dy, 0.2) * 1.2

        self.ax_xy.set_xlim(cx_km - r, cx_km + r)
        self.ax_xy.set_ylim(cy_km - r, cy_km + r)

        # repère croix sur le largage (0,0)
        self.ax_xy.axhline(0.0, linewidth=0.7)
        self.ax_xy.axvline(0.0, linewidth=0.7)

        self.ax_xy.set_xlabel("Est-Ouest (km)  [Est + / Ouest -]")
        self.ax_xy.set_ylabel("Nord-Sud (km)  [Nord + / Sud -]")
        self.ax_xy.set_title("Monte Carlo - zone d'impact (sol)")
        self.ax_xy.grid(True)
        self.ax_xy.legend()

        # ---------- 2) Histogramme des distances ----------
        self.ax_dist.hist(rs_km, bins=20, alpha=0.7)
        self.ax_dist.set_xlabel("Distance au largage (km)")
        self.ax_dist.set_ylabel("Nombre d'impacts")
        self.ax_dist.set_title("Distribution des distances")

        if rs_km:
            mean_r = sum(rs_km) / len(rs_km)
            self.ax_dist.axvline(mean_r, linestyle="--", label=f"moy ~ {mean_r:.1f} km")
            self.ax_dist.legend()

        self.ax_dist.grid(True)

        self.figure.tight_layout()
        self.draw()

    def _on_hover(self, event):
        # Pas de données ou pas d'annotation
        if self._sc is None or self._annot is None or not self._samples:
            return

        # On ne gère que l'axe du haut
        if event.inaxes is not self.ax_xy:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.draw_idle()
            return

        contains, info = self._sc.contains(event)
        if not contains:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.draw_idle()
            return

        idx = info["ind"][0]
        s = self._samples[idx]
        x = self._xs_km[idx]
        y = self._ys_km[idx]
        r = self._rs_km[idx]

        self._annot.xy = (x, y)
        self._annot.set_text(
            f"Lat  {s.lat_deg:.4f}°\n"
            f"Lon  {s.lon_deg:.4f}°\n"
            f"Dist {r:.1f} km"
        )
        self._annot.set_visible(True)
        self.draw_idle()


class GfsDownloadDialog(QDialog):
    """
    Petit dialog pour paramétrer le téléchargement GFS depuis NOMADS.
    """
    def __init__(self, parent: Optional[QWidget], lat0: float, lon0: float):
        super().__init__(parent)
        self.setWindowTitle("Télécharger GFS (NOMADS)")

        layout = QFormLayout(self)

        # Date par défaut = aujourd'hui (UTC)
        today = datetime.datetime.utcnow().date()
        self.date_edit = QLineEdit(today.strftime("%Y%m%d"))
        layout.addRow("Date run (YYYYMMDD) :", self.date_edit)

        # Cycle par défaut proche de l'heure UTC
        self.cycle_combo = QComboBox()
        for c in (0, 6, 12, 18):
            self.cycle_combo.addItem(f"{c:02d}z", c)

        hour_utc = datetime.datetime.utcnow().hour
        default_cycle = max([c for c in (0, 6, 12, 18) if c <= hour_utc] or [0])
        idx = (0, 6, 12, 18).index(default_cycle)
        self.cycle_combo.setCurrentIndex(idx)
        layout.addRow("Cycle :", self.cycle_combo)

        # Heure de prévision
        self.fhour_spin = QSpinBox()
        self.fhour_spin.setRange(0, 240)
        self.fhour_spin.setSingleStep(3)
        self.fhour_spin.setValue(0)
        layout.addRow("Heure de prévision (fXXX) :", self.fhour_spin)

        # Domaine autour du point de lancement
        self.lat_span = QDoubleSpinBox()
        self.lat_span.setRange(1.0, 40.0)
        self.lat_span.setValue(10.0)
        self.lat_span.setSingleStep(1.0)

        self.lon_span = QDoubleSpinBox()
        self.lon_span.setRange(1.0, 40.0)
        self.lon_span.setValue(10.0)
        self.lon_span.setSingleStep(1.0)

        layout.addRow(f"Lat centre : {lat0:.3f}°", QLabel(""))
        layout.addRow(f"Lon centre : {lon0:.3f}°", QLabel(""))
        layout.addRow("Demi-ouverture lat (°) :", self.lat_span)
        layout.addRow("Demi-ouverture lon (°) :", self.lon_span)

        # Niveaux fixes typiques ballon
        self.levels_edit = QLineEdit("1000 925 850 700 500 400 300 250 200")
        layout.addRow("Niveaux (hPa) :", self.levels_edit)

        self.vars_edit = QLineEdit("UGRD VGRD")
        layout.addRow("Variables :", self.vars_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self):
        date_str = self.date_edit.text().strip()
        cycle = self.cycle_combo.currentData()
        fhour = self.fhour_spin.value()

        try:
            datetime.datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            raise ValueError("Date invalide, format attendu : YYYYMMDD")

        levels = []
        levels_txt = self.levels_edit.text().strip()
        if levels_txt:
            for tok in levels_txt.split():
                levels.append(int(tok))

        vars_ = []
        vars_txt = self.vars_edit.text().strip()
        if vars_txt:
            for tok in vars_txt.split():
                vars_.append(tok.strip())

        if not vars_:
            vars_ = ["UGRD", "VGRD"]

        lat_span = self.lat_span.value()
        lon_span = self.lon_span.value()

        return {
            "date": date_str,
            "cycle": int(cycle),
            "fhour": int(fhour),
            "levels": levels,
            "vars": vars_,
            "lat_span": float(lat_span),
            "lon_span": float(lon_span),
        }

class MonteCarloDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Monte Carlo - paramètres")

        layout = QFormLayout(self)

        self.sb_runs = QSpinBox()
        self.sb_runs.setRange(10, 2000)
        self.sb_runs.setValue(200)
        layout.addRow("Nombre de runs :", self.sb_runs)

        self.sb_sigma_desc = QDoubleSpinBox()
        self.sb_sigma_desc.setRange(0.0, 0.5)
        self.sb_sigma_desc.setSingleStep(0.01)
        self.sb_sigma_desc.setDecimals(3)
        self.sb_sigma_desc.setValue(0.10)
        layout.addRow("σ descente (relatif, ex 0.10 = 10%) :", self.sb_sigma_desc)

        self.sb_sigma_wind = QDoubleSpinBox()
        self.sb_sigma_wind.setRange(0.0, 10.0)
        self.sb_sigma_wind.setSingleStep(0.5)
        self.sb_sigma_wind.setDecimals(2)
        self.sb_sigma_wind.setValue(2.0)

        self.sb_k_sigma = QDoubleSpinBox()
        self.sb_k_sigma.setRange(0.1, 5.0)
        self.sb_k_sigma.setSingleStep(0.1)
        self.sb_k_sigma.setDecimals(3)
        self.sb_k_sigma.setValue(2.447)  # ~95% par défaut
        layout.addRow("Facteur ellipse kσ :", self.sb_k_sigma)

        layout.addRow("σ vent (m/s) :", self.sb_sigma_wind)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_params(self):
        return {
            "n_runs": self.sb_runs.value(),
            "sigma_desc_rel": self.sb_sigma_desc.value(),
            "sigma_wind_ms": self.sb_sigma_wind.value(),
            "k_sigma": self.sb_k_sigma.value(),
        }

# ---------- Fenêtre principale ----------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prévision de descente de ballon sonde")

        self.current_states: List[State] = []

        self._build_ui()
        self._build_menu()
        self._init_default_profiles()

    # ---------- UI ----------

    def _build_ui(self):
        central = QWidget()
        main_layout = QHBoxLayout(central)

        # ---- Panneau gauche : profils + paramètres + simulation ----
        control_layout = QVBoxLayout()

        gb_files = QGroupBox("Profils")
        files_layout = QVBoxLayout()

        self.lbl_descent_file = QLabel("Profil de descente : (manuel / CSV)")
        btn_descent = QPushButton("Charger CSV descente…")
        btn_descent.setToolTip("Charge un CSV alt_m;descent_ms et remplit l'onglet 'Profil descente'.")
        btn_descent.clicked.connect(self.on_load_descent_csv)

        self.lbl_wind_file = QLabel("Profil de vent : (manuel / CSV / GFS)")
        btn_wind = QPushButton("Charger CSV vent…")
        btn_wind.setToolTip("Charge un CSV alt_m;wind_u_ms;wind_v_ms et remplit l'onglet 'Profil vent'.")
        btn_wind.clicked.connect(self.on_load_wind_csv)

        btn_gfs = QPushButton("Charger GFS (GRIB2)…")
        btn_gfs.setToolTip("Charge un fichier GFS GRIB2 et génère le profil vent pour la lat/lon courante.")
        btn_gfs.clicked.connect(self.on_load_gfs_wind)

        
        btn_gfs_dl = QPushButton("Télécharger GFS (NOMADS)…")
        btn_gfs_dl.setToolTip("Télécharge un sous-ensemble GFS 0.25° depuis NOMADS puis remplit le profil vent.")
        btn_gfs_dl.clicked.connect(self.on_download_gfs_from_nomads)

        files_layout.addWidget(self.lbl_descent_file)
        files_layout.addWidget(btn_descent)
        files_layout.addSpacing(10)
        files_layout.addWidget(self.lbl_wind_file)
        files_layout.addWidget(btn_wind)
        files_layout.addWidget(btn_gfs)
        files_layout.addWidget(btn_gfs_dl)

        gb_files.setLayout(files_layout)


        gb_params = QGroupBox("Paramètres initiaux")
        params_layout = QVBoxLayout()

        # Altitude
        row_alt = QHBoxLayout()
        row_alt.addWidget(QLabel("Altitude initiale (m):"))
        self.sb_alt0 = QDoubleSpinBox()
        self.sb_alt0.setRange(0.0, 600000.0)
        self.sb_alt0.setValue(30000.0)
        self.sb_alt0.setSingleStep(100.0)
        self.sb_alt0.setDecimals(False)
        row_alt.addWidget(self.sb_alt0)
        params_layout.addLayout(row_alt)

        # Latitude
        row_lat = QHBoxLayout()
        row_lat.addWidget(QLabel("Latitude initiale (°):"))
        self.sb_lat0 = QDoubleSpinBox()
        self.sb_lat0.setRange(-90.0, 90.0)
        self.sb_lat0.setValue(48.0)
        self.sb_lat0.setDecimals(6)
        row_lat.addWidget(self.sb_lat0)
        params_layout.addLayout(row_lat)

        # Longitude
        row_lon = QHBoxLayout()
        row_lon.addWidget(QLabel("Longitude initiale (°):"))
        self.sb_lon0 = QDoubleSpinBox()
        self.sb_lon0.setRange(-180.0, 180.0)
        self.sb_lon0.setValue(2.0)
        self.sb_lon0.setDecimals(6)
        row_lon.addWidget(self.sb_lon0)
        params_layout.addLayout(row_lon)

        # Masse sonde
        row_mass = QHBoxLayout()
        row_mass.addWidget(QLabel("Masse sonde (kg):"))
        self.sb_mass = QDoubleSpinBox()
        self.sb_mass.setRange(0.1, 5000.0)
        self.sb_mass.setDecimals(2)
        self.sb_mass.setSingleStep(0.1)
        self.sb_mass.setValue(1.0)  # profil base pour ~1 kg par défaut
        row_mass.addWidget(self.sb_mass)
        params_layout.addLayout(row_mass)

         # Chute libre activable
        self.cb_free_fall = QCheckBox("Chute libre")
        self.cb_free_fall.setToolTip(
            "Si cochée : la descente passe en chute libre en dessous d'une certaine altitude."
        )
        params_layout.addWidget(self.cb_free_fall)
                # Facteur d'accélération en chute libre
        row_ff_factor = QHBoxLayout()
        row_ff_factor.addWidget(QLabel("Facteur chute libre :"))
        self.sb_free_factor = QDoubleSpinBox()
        self.sb_free_factor.setRange(1.0, 10.0)
        self.sb_free_factor.setSingleStep(0.5)
        self.sb_free_factor.setDecimals(False)
        self.sb_free_factor.setValue(3.0)  # par défaut
        self.sb_free_factor.setToolTip(
            "Multiplicateur de vitesse en dessous de l'altitude de chute libre.\n"
            "Ex: 3.0 => v_chute = 3 × v_parachute."
        )
        row_ff_factor.addWidget(self.sb_free_factor)
        params_layout.addLayout(row_ff_factor)


        # Altitude de bascule en chute libre
        row_ff_alt = QHBoxLayout()
        row_ff_alt.addWidget(QLabel("Alt. chute libre (m):"))
        self.sb_free_fall_alt = QDoubleSpinBox()
        self.sb_free_fall_alt.setRange(0.0, 60000.0)
        self.sb_free_fall_alt.setSingleStep(500.0)
        self.sb_free_fall_alt.setDecimals(False)
        self.sb_free_fall_alt.setValue(0.0)  # 0 = full chute libre si activée
        self.sb_free_fall_alt.setToolTip(
            "0 = chute libre sur toute la descente.\n"
            ">0 = parachute au-dessus, chute libre en dessous."
        )

        row_ff_alt.addWidget(self.sb_free_fall_alt)
        params_layout.addLayout(row_ff_alt)


        # Δt
        row_dt = QHBoxLayout()
        label_dt = QLabel("Pas de temps (s). +petit -précis  :")
        label_dt.setToolTip("Intervalle de temps entre deux calculs de position.")
        row_dt.addWidget(label_dt)

        self.sb_dt = QSpinBox()
        self.sb_dt.setRange(1, 600)
        self.sb_dt.setValue(5)
        
        self.sb_dt.setToolTip("Plus il est petit, plus la simulation est fine (mais plus de points).")
        row_dt.addWidget(self.sb_dt)
        params_layout.addLayout(row_dt)

        gb_params.setLayout(params_layout)

        btn_simulate = QPushButton("Lancer la simulation")
        btn_simulate.clicked.connect(self.on_simulate)

        btn_mc = QPushButton("Monte Carlo (zone d'impact)")
        btn_mc.setToolTip("Lance N simulations avec bruit sur vent/descente et affiche la zone probable d'impact.")
        btn_mc.clicked.connect(self.on_monte_carlo)

        control_layout.addWidget(gb_files)
        control_layout.addWidget(gb_params)
        control_layout.addWidget(btn_simulate)
        control_layout.addWidget(btn_mc) 
        control_layout.addStretch()

        # ---- Onglets à droite ----
        self.tabs = QTabWidget()

        # Tableau résultat
        self.table_results = QTableWidget()
        self.table_results.setColumnCount(7)
        self.table_results.setHorizontalHeaderLabels(
            [
                "Temps écoulé (s)",
                "Alt (m)",
                "Lat (°)",
                "Lon (°)",
                "v_desc (m/s)",
                "u (m/s)",
                "v (m/s)",
            ]
        )
        header_item = self.table_results.horizontalHeaderItem(0)
        if header_item is not None:
            header_item.setToolTip("Temps depuis le début de la descente.")
        self.tabs.addTab(self.table_results, "Résultats")

        # Trajectoire 2D
        self.canvas = TrajectoryCanvas()
        self.tabs.addTab(self.canvas, "Trajectoire 2D")

        # Trajectoire 3D + contrôles animation
        self.canvas3d = ThreeDCanvas()
        self.tab_3d = QWidget()
        tab3d_layout = QVBoxLayout(self.tab_3d)
        tab3d_layout.addWidget(self.canvas3d)

        controls_layout = QHBoxLayout()
        self.btn_anim_play = QPushButton("▶ Lecture")
        self.btn_anim_stop = QPushButton("■ Stop")
        self.btn_anim_stop.setEnabled(False)

        self.btn_anim_reset = QPushButton("↺ Reset vue")
        self.btn_anim_reset.setEnabled(True)

        self.slider_anim = QSlider(Qt.Orientation.Horizontal)
        self.slider_anim.setEnabled(False)
        self.slider_anim.setMinimum(0)
        self.slider_anim.setMaximum(0)

        self.lbl_anim_time = QLabel("t = 0.0 s")

        controls_layout.addWidget(self.btn_anim_play)
        controls_layout.addWidget(self.btn_anim_stop)
        controls_layout.addWidget(self.btn_anim_reset)
        controls_layout.addWidget(self.slider_anim)
        controls_layout.addWidget(self.lbl_anim_time)


        tab3d_layout.addLayout(controls_layout)

        self.tabs.addTab(self.tab_3d, "Trajectoire 3D")
        
        # Timer anim 3D
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_index = 0

        self.btn_anim_play.clicked.connect(self.start_3d_animation)
        self.btn_anim_stop.clicked.connect(self.stop_3d_animation)
        self.btn_anim_reset.clicked.connect(self._on_reset_3d_view) 
        self.slider_anim.valueChanged.connect(self._on_anim_slider_changed)


        # Carte OSM
        self.map_widget = MapWidget(
            default_lat=self.sb_lat0.value(),
            default_lon=self.sb_lon0.value(),
        )
        self.tabs.addTab(self.map_widget, "Carte")

        # Profil descente (éditable directement)
        self.table_profile_desc = QTableWidget()
        self.table_profile_desc.setColumnCount(2)
        self.table_profile_desc.setHorizontalHeaderLabels(["Alt (m)", "Vdesc (m/s)"])
        self.table_profile_desc.setToolTip(
            "Profil de descente en fonction de l'altitude. Tu peux éditer les valeurs ici."
        )
        self.tabs.addTab(self.table_profile_desc, "Profil descente")

        # Profil vent (éditable directement)
        self.table_profile_wind = QTableWidget()
        self.table_profile_wind.setColumnCount(3)
        self.table_profile_wind.setHorizontalHeaderLabels(["Alt (m)", "u (m/s)", "v (m/s)"])
        self.table_profile_wind.setToolTip(
            "Profil de vent (u/v) en fonction de l'altitude. Tu peux éditer les valeurs ici."
        )
        self.tabs.addTab(self.table_profile_wind, "Profil vent")
        
        # Onglet Monte Carlo avec toolbar de zoom/pan
        self.mc_canvas = MonteCarloCanvas()
        self.mc_tab = QWidget()                          # ⬅️ on crée bien l'attribut ici
        mc_layout = QVBoxLayout(self.mc_tab)
        mc_toolbar = NavigationToolbar(self.mc_canvas, self)
        mc_layout.addWidget(mc_toolbar)
        mc_layout.addWidget(self.mc_canvas)
        self.tabs.addTab(self.mc_tab, "Monte Carlo")


        main_layout.addLayout(control_layout, 0)
        main_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central)
        self.resize(1300, 750)
        
    def _on_reset_3d_view(self):
        # recadre la vue 3D sur toute la trajectoire
        self.canvas3d.reset_view()

    def start_3d_animation(self):
        if not self.current_states:
            QMessageBox.information(self, "Animation 3D", "Aucune simulation disponible.")
            return

        if self.slider_anim.maximum() <= 0:
            return

        # Si on est à la fin, on repart du début
        if self.slider_anim.value() >= self.slider_anim.maximum():
            self.slider_anim.setValue(0)
            self._update_3d_frame(0)

        self.anim_index = self.slider_anim.value()
        self.anim_timer.start(50)  # 50 ms ~ 20 fps
        self.btn_anim_play.setEnabled(False)
        self.btn_anim_stop.setEnabled(True)

    def stop_3d_animation(self):
        self.anim_timer.stop()
        self.btn_anim_play.setEnabled(True)
        self.btn_anim_stop.setEnabled(False)

    def _on_anim_tick(self):
        if not self.current_states:
            self.stop_3d_animation()
            return

        idx = self.slider_anim.value() + 1
        if idx > self.slider_anim.maximum():
            # fin de la trajectoire
            self.stop_3d_animation()
            return

        self.slider_anim.blockSignals(True)
        self.slider_anim.setValue(idx)
        self.slider_anim.blockSignals(False)

        self._update_3d_frame(idx)

    def _on_anim_slider_changed(self, value: int):
        self._update_3d_frame(value)

    def _update_3d_frame(self, idx: int):
        if not self.current_states:
            return
        if idx < 0 or idx >= len(self.current_states):
            return

        self.canvas3d.update_marker(idx)
        t = self.current_states[idx].t_s
        self.lbl_anim_time.setText(f"t = {t:.1f} s")
       

    def on_monte_carlo(self):
        alt0 = self.sb_alt0.value()
        lat0 = self.sb_lat0.value()
        lon0 = self.sb_lon0.value()
        dt = float(self.sb_dt.value())

        if alt0 <= 0:
            QMessageBox.warning(self, "Paramètres", "Altitude initiale doit être > 0.")
            return

        # Profil vent
        try:
            wind_profile = self._get_wind_profile_from_table()
        except ValueError as e:
            QMessageBox.warning(self, "Profil vent invalide", str(e))
            return

        # Profil descente effectif
        try:
            descent_profile = self._build_effective_descent_profile(alt0_m=alt0)
        except ValueError as e:
            QMessageBox.warning(self, "Profil descente invalide", str(e))
            return

        dlg = MonteCarloDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        params = dlg.get_params()

        try:
            impacts, ellipse = run_monte_carlo(
                n_runs=params["n_runs"],
                alt0_m=alt0,
                lat0_deg=lat0,
                lon0_deg=lon0,
                dt_s=dt,
                base_descent=descent_profile,
                base_wind=wind_profile,
                sigma_desc_rel=params["sigma_desc_rel"],
                sigma_wind_ms=params["sigma_wind_ms"],
                k_sigma=params["k_sigma"],
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur Monte Carlo", str(e))
            return

        if not impacts:
            QMessageBox.information(
                self,
                "Monte Carlo",
                "Aucun impact n'a été calculé.\n"
                "Vérifie profil vent / descente / chute libre.",
            )
            return

        self.mc_canvas.plot_impacts(impacts, ellipse)
        self.tabs.setCurrentWidget(self.mc_tab)


    def _build_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Fichier")

        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    # ---------- Profils par défaut ----------

    def _init_default_profiles(self):
        """
        Charge un profil de descente par défaut s'il existe.
        Fichier recommandé : descent_profile_default.csv dans le répertoire courant.
        """
        default_desc_csv = "descent_profile_default.csv"
        if os.path.exists(default_desc_csv):
            try:
                points = self._read_descent_csv_points(default_desc_csv)
                self._fill_desc_table_from_points(points)
                self.lbl_descent_file.setText(
                    f"Profil de descente : {default_desc_csv} [par défaut]"
                )
            except Exception as e:
                print(f"Impossible de charger le profil de descente par défaut : {e}")
        else:
            # Si pas de fichier par défaut, on met quelques lignes vides
            self.table_profile_desc.setRowCount(5)

        # On laisse le profil vent vide / manuel
        if self.table_profile_wind.rowCount() == 0:
            self.table_profile_wind.setRowCount(5)

    # ---------- Actions UI ----------
    def on_download_gfs_from_nomads(self):
        """
        Télécharge un GRIB2 GFS 0.25° depuis NOMADS et remplit le profil vent
        pour la lat/lon initiale actuelle.
        """
        lat0 = self.sb_lat0.value()
        lon0 = self.sb_lon0.value()

        dlg = GfsDownloadDialog(self, lat0=lat0, lon0=lon0)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            cfg = dlg.get_config()
        except ValueError as e:
            QMessageBox.warning(self, "Paramètres GFS invalides", str(e))
            return

        # Domaine
        lat_min = lat0 - cfg["lat_span"]
        lat_max = lat0 + cfg["lat_span"]
        lon_min = lon0 - cfg["lon_span"]
        lon_max = lon0 + cfg["lon_span"]

        url = gfs_download.build_gfs_url(
            date_yyyymmdd=cfg["date"],
            cycle_hour=cfg["cycle"],
            fhour=cfg["fhour"],
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            vars_=cfg["vars"],
            levels_hpa=cfg["levels"],
            all_levels=(len(cfg["levels"]) == 0),
        )

        # Dossier de sortie
        os.makedirs("gfs_data", exist_ok=True)
        out_name = f"gfs_{cfg['date']}_{cfg['cycle']:02d}_f{cfg['fhour']:03d}.grib2"
        out_path = os.path.join("gfs_data", out_name)

        try:
            gfs_download.download_gfs(url, out_path)
        except requests.HTTPError as e:
            QMessageBox.critical(self, "Erreur HTTP GFS", f"Erreur HTTP lors du téléchargement :\n{e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Erreur GFS", f"Erreur lors du téléchargement GFS :\n{e}")
            return

        # Extraction du profil vent pour la lat/lon initiale
        try:
            points = gfs_utils.extract_wind_profile_from_gfs_grib(
                grib_path=out_path,
                lat_deg=lat0,
                lon_deg=lon0,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur lecture GRIB", f"Impossible d'extraire le vent GFS :\n{e}")
            return

        self._fill_wind_table_from_points(points)
        self.lbl_wind_file.setText(f"Profil de vent : GFS NOMADS {out_name}")


    def on_load_descent_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le CSV de profil de descente",
            "",
            "CSV (*.csv);;Tous les fichiers (*)",
        )
        if not path:
            return

        try:
            points = self._read_descent_csv_points(path)
        except Exception as e:
            QMessageBox.critical(self, "Erreur chargement descente", str(e))
            return

        self._fill_desc_table_from_points(points)
        self.lbl_descent_file.setText(f"Profil de descente : {path}")

    def on_load_wind_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le CSV de profil de vent",
            "",
            "CSV (*.csv);;Tous les fichiers (*)",
        )
        if not path:
            return

        try:
            points = self._read_wind_csv_points(path)
        except Exception as e:
            QMessageBox.critical(self, "Erreur chargement vent", str(e))
            return

        self._fill_wind_table_from_points(points)
        self.lbl_wind_file.setText(f"Profil de vent : {path}")

    def on_load_gfs_wind(self):
        """
        Charge un fichier GFS GRIB2 et génère le profil vent pour la lat/lon courante.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier GFS (GRIB2)",
            "",
            "GRIB2 (*.grib2 *.grb2 *.grib);;Tous les fichiers (*)",
        )
        if not path:
            return

        lat0 = self.sb_lat0.value()
        lon0 = self.sb_lon0.value()

        try:
            points = gfs_utils.extract_wind_profile_from_gfs_grib(
                grib_path=path,
                lat_deg=lat0,
                lon_deg=lon0,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur GFS", f"Impossible d'extraire le profil vent GFS :\n{e}")
            return

        # On pousse ça dans la table profil vent
        self._fill_wind_table_from_points(points)
        self.lbl_wind_file.setText(f"Profil de vent : GFS {path}")
    

    def on_simulate(self):
        alt0 = self.sb_alt0.value()
        lat0 = self.sb_lat0.value()
        lon0 = self.sb_lon0.value()
        dt = float(self.sb_dt.value())

        if alt0 <= 0:
            QMessageBox.warning(self, "Paramètre invalide", "L'altitude initiale doit être > 0.")
            return

        # Profil vent
        try:
            wind_profile = self._get_wind_profile_from_table()
        except ValueError as e:
            QMessageBox.warning(self, "Profil vent invalide", str(e))
            return

        # Profil descente effectif (parachute + éventuelle chute libre)
        try:
            descent_profile = self._build_effective_descent_profile(alt0_m=alt0)
        except ValueError as e:
            QMessageBox.warning(self, "Profil descente invalide", str(e))
            return

        try:
            self.current_states = simulate_descent(
                alt0_m=alt0,
                lat0_deg=lat0,
                lon0_deg=lon0,
                dt_s=dt,
                descent_profile=descent_profile,
                wind_profile=wind_profile,
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur simulation", str(e))
            return

        self._populate_results_table(self.current_states)
        self.canvas.plot_trajectory(self.current_states)
        self.canvas3d.plot_trajectory_3d(self.current_states)
        self.map_widget.show_trajectory(self.current_states)

        # Config timeline 3D
        n = len(self.current_states)
        self.anim_timer.stop()
        self.btn_anim_play.setEnabled(n > 1)
        self.btn_anim_stop.setEnabled(False)

        if n > 1:
            self.slider_anim.setEnabled(True)
            self.slider_anim.setMinimum(0)
            self.slider_anim.setMaximum(n - 1)
            self.slider_anim.setValue(0)
            self._update_3d_frame(0)
        else:
            self.slider_anim.setEnabled(False)
            self.slider_anim.setMinimum(0)
            self.slider_anim.setMaximum(0)
            self.lbl_anim_time.setText("t = 0.0 s")



    # ---------- Helpers profils (tables <-> objets) ----------

    def _fill_desc_table_from_points(self, points: List[DescentPoint]):
        self.table_profile_desc.setRowCount(len(points))
        for i, p in enumerate(sorted(points, key=lambda x: x.alt_m, reverse=True)):
            alt_int = int(round(p.alt_m))
            v_int = int(round(p.descent_ms))
            vals = [alt_int, v_int]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(str(v))  # plus de format float
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.table_profile_desc.setItem(i, j, item)
        self.table_profile_desc.resizeColumnsToContents()


    def _fill_wind_table_from_points(self, points: List[WindPoint]):
        self.table_profile_wind.setRowCount(len(points))
        for i, p in enumerate(sorted(points, key=lambda x: x.alt_m, reverse=True)):
            vals = [p.alt_m, p.wind_u_ms, p.wind_v_ms]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(f"{v:.3f}")
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.table_profile_wind.setItem(i, j, item)
        self.table_profile_wind.resizeColumnsToContents()

    def _get_descent_profile_from_table(self) -> DescentProfile:
        points: List[DescentPoint] = []
        rows = self.table_profile_desc.rowCount()
        for row in range(rows):
            item_alt = self.table_profile_desc.item(row, 0)
            item_v = self.table_profile_desc.item(row, 1)
            if item_alt is None or item_v is None:
                continue

            alt_text = item_alt.text().strip().replace(",", ".")
            v_text = item_v.text().strip().replace(",", ".")

            if not alt_text or not v_text:
                continue

            try:
                # on force entier
                alt = int(float(alt_text))
                v = int(float(v_text))
            except ValueError:
                continue

            points.append(DescentPoint(alt_m=float(alt), descent_ms=float(v)))

        if not points:
            raise ValueError("Aucun point valide dans le profil de descente.")
        return DescentProfile(points)


    def _get_wind_profile_from_table(self) -> WindProfile:
        points: List[WindPoint] = []
        rows = self.table_profile_wind.rowCount()
        for row in range(rows):
            item_alt = self.table_profile_wind.item(row, 0)
            item_u = self.table_profile_wind.item(row, 1)
            item_v = self.table_profile_wind.item(row, 2)
            if item_alt is None or item_u is None or item_v is None:
                continue
            alt_text = item_alt.text().strip().replace(",", ".")
            u_text = item_u.text().strip().replace(",", ".")
            v_text = item_v.text().strip().replace(",", ".")
            if not alt_text or not u_text or not v_text:
                continue
            try:
                alt = float(alt_text)
                u = float(u_text)
                v = float(v_text)
            except ValueError:
                continue
            points.append(WindPoint(alt_m=alt, wind_u_ms=u, wind_v_ms=v))

        if not points:
            raise ValueError("Aucun point valide dans le profil de vent.")
        return WindProfile(points)
    
    def _scale_descent_profile_for_mass(self, base_profile: DescentProfile) -> DescentProfile:
        """
        Adapte le profil de descente en fonction de la masse de la sonde.
        Approx : v_new = v_base * sqrt(m / m_ref), avec m_ref = 1 kg.
        """
        m = self.sb_mass.value()
        if m <= 0:
            return base_profile

        m_ref = 1.0  # masse de référence implicite du profil de base
        factor = math.sqrt(m / m_ref)

        scaled_points: List[DescentPoint] = []
        for p in base_profile.points:
            v = p.descent_ms * factor
            v = max(0.1, v)  # sécurité
            scaled_points.append(
                DescentPoint(
                    alt_m=p.alt_m,
                    descent_ms=v,
                )
            )

        return DescentProfile(scaled_points)
    
    
    def _build_effective_descent_profile(self, alt0_m: float) -> DescentProfile:
        """
        Construit le profil de descente effectif :
          - profil table + facteur masse,
          - si 'chute libre' cochée : en-dessous de ff_alt, on accélère la descente.
        """
        # 1) profil base depuis la table
        base_profile = self._get_descent_profile_from_table()
        scaled_base = self._scale_descent_profile_for_mass(base_profile)

        # 2) si pas de chute libre -> on renvoie tel quel
        if not self.cb_free_fall.isChecked():
            return scaled_base

        ff_alt = float(self.sb_free_fall_alt.value())
        # facteur d'accélération en chute libre (tu peux le régler)
        factor_free = float(self.sb_free_factor.value())


        points: List[DescentPoint] = []
        for p in scaled_base.points:
            v = p.descent_ms

            if ff_alt <= 0.0:
                # ff_alt = 0 => chute libre sur toute la descente
                v = v * factor_free
            else:
                # chute libre en-dessous de ff_alt
                if p.alt_m <= ff_alt:
                    v = v * factor_free

            # sécurité, éviter les vitesses verticales trop petites
            v = max(v, 0.5)
            points.append(DescentPoint(alt_m=p.alt_m, descent_ms=v))

        return DescentProfile(points)




    # ---------- Lecture CSV ----------

    def _read_descent_csv_points(self, path: str) -> List[DescentPoint]:
        points: List[DescentPoint] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            columns = {name.lower(): name for name in (reader.fieldnames or [])}

            def find_col(keys):
                for k in keys:
                    for c in columns:
                        if k in c:
                            return columns[c]
                raise ValueError(f"Colonne manquante dans {path}: {keys}")

            alt_col = find_col(["alt"])
            desc_col = find_col(["descent", "vit", "vitesse"])

            for row in reader:
                alt = float(row[alt_col].replace(",", "."))
                desc = float(row[desc_col].replace(",", "."))
                points.append(DescentPoint(alt_m=alt, descent_ms=desc))

        if not points:
            raise ValueError("Aucun point lu dans le CSV de descente")
        return points

    def _read_wind_csv_points(self, path: str) -> List[WindPoint]:
        points: List[WindPoint] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            columns = {name.lower(): name for name in (reader.fieldnames or [])}

            def find_col(keys):
                for k in keys:
                    for c in columns:
                        if k in c:
                            return columns[c]
                raise ValueError(f"Colonne manquante dans {path}: {keys}")

            alt_col = find_col(["alt"])
            u_col = find_col(["u"])
            v_col = find_col(["v"])

            for row in reader:
                alt = float(row[alt_col].replace(",", "."))
                u = float(row[u_col].replace(",", "."))
                v = float(row[v_col].replace(",", "."))
                points.append(WindPoint(alt_m=alt, wind_u_ms=u, wind_v_ms=v))

        if not points:
            raise ValueError("Aucun point lu dans le CSV de vent")
        return points

    # ---------- Table résultats ----------

    def _populate_results_table(self, states: List[State]):
        self.table_results.setRowCount(0)
        self.table_results.setRowCount(len(states))

        for i, s in enumerate(states):
            values = [
                s.t_s,
                s.alt_m,
                s.lat_deg,
                s.lon_deg,
                s.descent_ms,
                s.wind_u_ms,
                s.wind_v_ms,
            ]
            for j, v in enumerate(values):
                item = QTableWidgetItem(f"{v:.6f}")
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.table_results.setItem(i, j, item)

        self.table_results.resizeColumnsToContents()
