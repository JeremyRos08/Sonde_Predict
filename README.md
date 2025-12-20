> Version actuelle : **v1.0.0**

# Sonde_Predict

**Sonde_Predict** est une application Python développée en **PyQt5** permettant de simuler et prédire la trajectoire et le point d’impact d’un ballon sonde météorologique (ou de tout objet porté par le vent), en **parachute ou chute libre**.

L’application propose une visualisation **2D / 3D**, une **carte interactive**, des profils physiques réalistes et un mode **Monte Carlo** avancé.

---

## 🎯 Objectif

Fournir un outil **précis, visuel et interactif** pour :

- prévoir une zone d’impact réaliste  
- analyser l’influence du vent, de la masse et des profils  
- explorer la trajectoire temporelle complète d’un vol ou d’une chute  

---

## ✨ Fonctionnalités principales

### 📈 Profils physiques

- **Profil de montée**
  - Édition directe via table
  - Import CSV (`alt_m;ascent_ms`)
  - Effet de masse progressif

- **Profil de descente**
  - Édition directe via table
  - Import CSV (`alt_m;descent_ms`)
  - Effet de masse réaliste dépendant de l’altitude

- **Profil de vent**
  - Manuel (table)
  - Import CSV (`alt_m;u_ms;v_ms`)
  - Import **GFS GRIB2**
  - Téléchargement automatique depuis **NOMADS**

---

### 🧮 Simulation

- Simulation complète **montée + descente** ou **descente seule**
- Paramètres configurables :
  - latitude / longitude initiales
  - altitude de burst
  - pas de temps
  - masse de l’objet
- **Chute libre configurable**
  - altitude de déclenchement
  - facteur multiplicatif de vitesse

---

### 📊 Visualisation 2D (interactive)

- 4 graphes synchronisés :
  - Altitude vs temps
  - Altitude vs distance sol
  - Trajectoire au sol (latitude / longitude)
  - Vue polaire (boussole)
- **Curseur temporel interactif**
  - ligne verticale + points synchronisés
  - affichage des infos :
    - temps
    - altitude
    - distance
    - azimut
    - latitude / longitude
- Zoom / pan Matplotlib
- Coordonnées formatées (lisibles, sans notation scientifique)

---

### 🧭 Carte

- Carte intégrée (Leaflet / OpenStreetMap)
- Affichage de la trajectoire complète
- Sélecteur de style de carte (clair / sombre)

---

### 🛰️ Visualisation 3D

- Trajectoire 3D Est / Nord / Altitude
- Séparation montée / descente
- **Animation temporelle**
  - lecture / pause
  - slider de position
  - marqueur synchronisé
- Orientation verrouillée pour une lecture stable

---

### 🎯 Mode Monte Carlo

- N simulations avec bruit :
  - vent (σ en m/s)
  - descente (σ relatif)
- Résultats :
  - nuage d’impacts au sol
  - ellipse de probabilité (~kσ, 95 % par défaut)
  - histogramme des distances
- Zoom automatique sur la zone pertinente
- Tooltips interactifs sur les impacts

---

### 🎨 Interface

- Thème sombre par défaut
- Interface claire et orientée usage terrain
- Informations contextuelles affichées **sous les graphes**
- Icônes personnalisées
- Application prête pour le packaging (PyInstaller)

---

## 🧱 Stack technique

- Python **3.11+** recommandé
- **PyQt5** (interface graphique)
- **Matplotlib** (graphes 2D / 3D interactifs)
- **Folium / Leaflet** (carte)
- **xarray + cfgrib + eccodes** (lecture GFS GRIB2)
- **requests** (téléchargement NOMADS)

---

## 📦 Installation (recommandé : Conda)

### Windows / Linux

```bash
git clone https://github.com/JeremyRos08/Sonde_Predict.git
cd Sonde_Predict

conda env create -f environment.yml
conda activate sonde_predict

python main.py
