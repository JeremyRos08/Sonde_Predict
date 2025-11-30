# Tuto d'installation – Sonde Predict

## 1. Prérequis

- Python 3.11+
- Conda (miniconda/anaconda) recommandé
- Connexion Internet si tu utilises l’option GFS / NOMADS

## 2. Installation avec conda (recommandé)

```bash
git clone https://github.com/<TON_USER>/<TON_REPO>.git
cd <TON_REPO>

conda env create -f environment.yml
conda activate sonde_predict

python main.py

////////////////////////////////////////////////////////////////////////
## ▶️ Utilisation rapide

Lancer python main.py

Dans la colonne de gauche :

régler l’altitude initiale

régler la position (lat/lon)

choisir le pas de temps Δt

régler la masse de la sonde

optionnel : activer Chute libre + altitude de bascule + facteur

Onglets de profils :

Profil descente :

éditer à la main ou

charger un CSV (format alt_m;vitesse_ms)

Profil vent :

éditer à la main,

charger un CSV (alt_m;u_ms;v_ms) ou

charger/ télécharger un fichier GFS GRIB2 (NOMADS).

Cliquer sur “Lancer la simulation” :

onglet Résultats : table complète

onglet Trajectoire 2D : graph 2D

onglet Trajectoire 3D : vue 3D + timeline (Play / Stop)

onglet Carte : trajectoire sur carte

Onglet Monte Carlo :

cliquer sur “Monte Carlo (zone d’impact)”

choisir :

N runs

σ descente (relatif)

σ vent (m/s)

tu obtiens :

nuage d’impacts

ellipse ~95 %

histogramme des distances sol
