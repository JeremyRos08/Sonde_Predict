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
