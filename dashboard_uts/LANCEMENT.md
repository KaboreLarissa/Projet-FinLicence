# Dashboard UTS — Guide de lancement

## Installation (une seule fois)
```
pip install -r requirements.txt
```

## Lancement
```
python app.py
```
Puis ouvrir : http://localhost:8050

## Structure
```
dashboard_uts/
├── app.py              # Application principale Dash
├── data_loader.py      # Chargement données + calcul KPIs
├── assets/style.css    # Design complet
├── requirements.txt    # Dépendances Python
└── LANCEMENT.md        # Ce fichier
```

## Données
Placer les CSV du dataset dans /home/claude/dataset_35k/
ou modifier DATA_PATH dans data_loader.py
