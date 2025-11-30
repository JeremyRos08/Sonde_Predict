> Version actuelle : **v1.0.0**

# Sonde_Predict
Sonde_Predict est une app creer en PyQt5 pour prédire le point d'impact d'une sonde meteo en parachute ou chute libre.

# Sonde Predict – Prévision de descente de ballon

Application Python / Qt pour simuler la descente d’un ballon sonde (ou de n’importe quel objet) en 3D, avec vent, GFS, Monte Carlo et carte.

## ✨ Fonctionnalités

- Profil de **descente** paramétrable via table ou CSV (`alt_m;descent_ms`)
- Profil de **vent** via CSV ou directement depuis **GFS (GRIB2 / NOMADS)**
- Simulation de la descente en 3D :
  - table de résultats (t, alt, lat, lon, vitesses)
  - graphiques 2D (alt vs temps, distance vs temps, trajectoire au sol, vue polaire)
  - carte (OpenStreetMap) avec trajectoire
  - **Trajectoire 3D animée** (timeline + lecture)
- Mode **Monte Carlo** :
  - N runs avec bruit sur vent / descente
  - nuage d’impacts + ellipse ~95 %
  - histogramme des distances sol
- Prise en compte :
  - de la **masse** de l’objet
  - de la **chute libre** sous une certaine altitude (facteur configurable)
- Thème sombre (dark mode) par défaut

## 🧱 Techno

- Python 3.11+ recommandé
- Qt : **PyQt5**
- Matplotlib (graph 2D/3D)
- Folium / Leaflet (carte web intégrée)
- xarray + cfgrib + eccodes (lecture GRIB GFS)
- requests (téléchargement NOMADS)

---

## 📦 Installation (recommandé : conda)

Sous Windows / Linux, avec `conda` (miniconda/anaconda) :

```bash
git clone https://github.com/JeremyRos08/Sonde_Predict.git
cd Sonde_Predict

conda env create -f environment.yml
conda activate sonde_predict

python main.py
