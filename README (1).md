# Dashboard UTS — Performances Académiques UVBF Génie Logiciel

## Prérequis
- Python 3.11+
- PostgreSQL 14+ installé et démarré
- VSCode

---

## Installation — étapes dans l'ordre

### 1. Créer et activer l'environnement virtuel

```bash
# Dans le dossier du projet
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Créer la base de données PostgreSQL

Ouvrir un terminal et lancer psql :

```bash
psql -U postgres
```

Dans psql, taper :

```sql
CREATE DATABASE dashboard_uts;
CREATE USER dashboard_user WITH PASSWORD 'dashboard2025';
GRANT ALL PRIVILEGES ON DATABASE dashboard_uts TO dashboard_user;
\q
```

### 4. Configurer le fichier .env

Créer un fichier `.env` à la racine avec :

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dashboard_uts
DB_USER=dashboard_user
DB_PASSWORD=dashboard2025
SECRET_KEY=dashboard_uts_secret_key_2025_uvbf_gl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
SEUIL_DIFFICULTE=8.0
```

### 5. Créer les tables et les utilisateurs

```bash
python db/init_db.py
```

Résultat attendu :
```
✅ Tables créées avec succès.
✅ Utilisateur admin créé : admin / admin2025
✅ Utilisateur responsable créé : responsable / resp2025
```

### 6. Copier les fichiers de données dans data/raw/

Copier tous les fichiers Excel et PDF dans le dossier `data/raw/` :
- S1_GL.xlsx
- S2.xlsx
- _Pour_signature__PV_L3_-_Genie_Logiciel.pdf
- PV_-L2-S3_S4_pure_developer_-2023-2024-03-11-25-Rattrapage--.pdf
- PV-L2-Pure-DEV-pour_Signature-VF-2023-2024-1.pdf
- Rattrapage-De_liberation_-_S1-L1__pure_developer_-2022-2023-V1.pdf
- Rattrapage-De_liberation_-_S2-L1__pure_developer_-2022-2023-V1.pdf

### 7. Lancer le pipeline ETL (charge toutes les données mock)

```bash
python etl/pipeline.py
```

### 8. Lancer le dashboard

```bash
python dashboard/app.py
```

Ouvrir http://localhost:8050 dans le navigateur.

---

## Flux de fonctionnement

```
Admin uploade un CSV
      ↓
FastAPI /upload reçoit le fichier
      ↓
etl/pipeline.py → charger_depuis_csv()
      ↓
etl/load.py → UPSERT dans PostgreSQL
      ↓
Dashboard Dash → mise à jour automatique
```

## Format CSV pour l'upload admin

Le fichier CSV doit avoir ces colonnes (dans n'importe quel ordre) :

| Colonne | Obligatoire | Exemple |
|---------|-------------|---------|
| MATRICULE | Oui | N05124620221 |
| NOM | Oui | SECK |
| PRENOM | Oui | Cheick Omar |
| GENRE | Oui | M ou F |
| FILIERE | Oui | GL_AD |
| SEMESTRE | Oui | S5 |
| SESSION | Oui | Normale |
| ANNEE_ACADEMIQUE | Oui | 2024-2025 |
| MOYENNE | Oui | 13.96 |
| STATUT | Oui | Validé |
| MENTION | Non | Assez Bien |
