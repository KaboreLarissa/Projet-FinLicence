"""
etl/load_data.py
Charge les 7 CSV dans PostgreSQL uts_dashboard_v2
Version corrigee - compatible pandas 3.x
"""
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import os, sys, time

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "uts_dashboard_v2",
    "user":     "uts_admin",
    "password": "admin123",
}

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)

def connecter():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connexion PostgreSQL OK - uts_dashboard_v2")
        return conn
    except Exception as e:
        print(f"Erreur connexion : {e}")
        sys.exit(1)

def lire_csv(nom):
    path = os.path.join(DATA_PATH, nom)
    df = pd.read_csv(path)
    df = df.where(pd.notna(df), None)
    print(f"  {nom} : {len(df):,} lignes lues")
    return df

def nettoyer_int(val):
    """Convertit en int Python natif ou None"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        v = int(float(val))
        # Limiter aux bornes INTEGER PostgreSQL
        if v > 2147483647 or v < -2147483647:
            return None
        return v
    except:
        return None

def nettoyer_float(val):
    """Convertit en float Python natif ou None"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except:
        return None

def nettoyer_str(val):
    """Convertit en str ou None"""
    if val is None:
        return None
    s = str(val).strip()
    return None if s in ("", "nan", "None") else s

def inserer(conn, table, rows, colonnes):
    """Insertion par batch de 1000 lignes"""
    cur = conn.cursor()
    cols_str = ", ".join(colonnes)
    sql = f"INSERT INTO {table} ({cols_str}) VALUES %s ON CONFLICT DO NOTHING"
    total = len(rows)
    batch_size = 1000
    for i in range(0, total, batch_size):
        batch = rows[i:i+batch_size]
        execute_values(cur, sql, batch)
        pct = min(100, int((i + batch_size) / total * 100))
        print(f"    {pct}% ({min(i+batch_size,total):,}/{total:,})", end="\r")
    conn.commit()
    cur.close()
    print(f"    OK - {total:,} lignes inserees dans {table}          ")

def main():
    print("=" * 55)
    print("CHARGEMENT DES DONNEES -> uts_dashboard_v2")
    print("=" * 55)
    print(f"Dossier data : {DATA_PATH}")
    start = time.time()

    conn = connecter()

    # Vider les tables dans le bon ordre (contraintes FK)
    print("\nNettoyage des tables existantes...")
    cur = conn.cursor()
    cur.execute("TRUNCATE fact_notes_ue, fact_resultats, dim_etudiant, "
                "dim_filiere, dim_semestre, dim_annee_academique, dim_ufr "
                "RESTART IDENTITY CASCADE;")
    conn.commit()
    cur.close()
    print("  OK - tables videes")

    # ── 1. dim_ufr ──────────────────────────────────────────
    print("\n[1/7] dim_ufr...")
    df = lire_csv("dim_ufr.csv")
    rows = [(
        nettoyer_str(r["code_ufr"]),
        nettoyer_str(r["nom_ufr"]),
        nettoyer_int(r.get("nb_etudiants_ref")),
        nettoyer_int(r.get("nb_enseignants_ref")),
    ) for _, r in df.iterrows()]
    inserer(conn, "dim_ufr", rows,
            ["code_ufr","nom_ufr","nb_etudiants_ref","nb_enseignants_ref"])

    # ── 2. dim_filiere ──────────────────────────────────────
    print("\n[2/7] dim_filiere...")
    df = lire_csv("dim_filiere.csv")
    rows = [(
        nettoyer_str(r["code_filiere"]),
        nettoyer_str(r["nom_filiere"]),
        nettoyer_str(r.get("ufr")),
        nettoyer_str(r.get("filiere_parente")),
        nettoyer_str(r.get("semestre_bifurcation")),
        nettoyer_str(r.get("niveau_terminal")),
        nettoyer_float(r.get("ratio_F")),
    ) for _, r in df.iterrows()]
    inserer(conn, "dim_filiere", rows,
            ["code_filiere","nom_filiere","ufr","filiere_parente",
             "semestre_bifurcation","niveau_terminal","ratio_F"])

    # ── 3. dim_semestre ─────────────────────────────────────
    print("\n[3/7] dim_semestre...")
    df = lire_csv("dim_semestre.csv")
    rows = [(
        nettoyer_str(r["code_semestre"]),
        nettoyer_int(r["numero"]),
        nettoyer_str(r["niveau"]),
        nettoyer_str(r.get("periode")),
    ) for _, r in df.iterrows()]
    inserer(conn, "dim_semestre", rows,
            ["code_semestre","numero","niveau","periode"])

    # ── 4. dim_annee_academique ─────────────────────────────
    print("\n[4/7] dim_annee_academique...")
    df = lire_csv("dim_annee_academique.csv")
    rows = [(
        nettoyer_str(r["code_annee"]),
        nettoyer_int(r["annee_debut"]),
        nettoyer_int(r["annee_fin"]),
    ) for _, r in df.iterrows()]
    inserer(conn, "dim_annee_academique", rows,
            ["code_annee","annee_debut","annee_fin"])

    # ── 5. dim_etudiant ─────────────────────────────────────
    print("\n[5/7] dim_etudiant (31 098 etudiants)...")
    df = lire_csv("dim_etudiant.csv")
    rows = [(
        nettoyer_str(r["matricule"]),
        nettoyer_str(r["nom"]),
        nettoyer_str(r["prenom"]),
        nettoyer_str(r.get("genre")),
        nettoyer_int(r.get("age_entree")),
        nettoyer_int(r.get("annee_entree")),
        nettoyer_str(r.get("filiere_initiale")),
        nettoyer_str(r.get("ufr")),
    ) for _, r in df.iterrows()]
    inserer(conn, "dim_etudiant", rows,
            ["matricule","nom","prenom","genre","age_entree",
             "annee_entree","filiere_initiale","ufr"])

    # ── 6. fact_resultats ───────────────────────────────────
    print("\n[6/7] fact_resultats (167 250 resultats)...")
    df = lire_csv("fact_resultats.csv")
    rows = [(
        nettoyer_str(r["matricule"]),
        nettoyer_str(r.get("ufr")),
        nettoyer_str(r.get("filiere_code")),
        nettoyer_str(r["niveau"]),
        nettoyer_str(r["semestre"]),
        nettoyer_str(r["annee_academique"]),
        nettoyer_str(r["session"]),
        nettoyer_float(r.get("moyenne_generale")),
        nettoyer_float(r.get("total_points")),
        nettoyer_int(r.get("nb_ue_validees")) or 0,
        nettoyer_int(r.get("nb_ue_echouees")) or 0,
        nettoyer_str(r["statut"]),
        nettoyer_str(r.get("mention")),
        nettoyer_int(r.get("rang_promo")),
    ) for _, r in df.iterrows()]
    inserer(conn, "fact_resultats", rows,
            ["matricule","ufr","filiere_code","niveau","semestre",
             "annee_academique","session","moyenne_generale","total_points",
             "nb_ue_validees","nb_ue_echouees","statut","mention","rang_promo"])

    # ── 7. fact_notes_ue ────────────────────────────────────
    print("\n[7/7] fact_notes_ue (943 000+ notes - patience ~3 min)...")
    df = lire_csv("fact_notes_ue.csv")
    rows = [(
        nettoyer_int(r["id_resultat"]),
        nettoyer_str(r.get("matricule")),
        nettoyer_str(r.get("ufr")),
        nettoyer_str(r.get("filiere_code")),
        nettoyer_str(r.get("niveau")),
        nettoyer_str(r.get("semestre")),
        nettoyer_str(r.get("annee_academique")),
        nettoyer_str(r.get("session")),
        nettoyer_str(r["nom_ue"]),
        nettoyer_str(r.get("groupe_ue")),
        nettoyer_float(r.get("note")),
        nettoyer_int(r.get("credits")),
    ) for _, r in df.iterrows()]
    inserer(conn, "fact_notes_ue", rows,
            ["id_resultat","matricule","ufr","filiere_code","niveau",
             "semestre","annee_academique","session","nom_ue",
             "groupe_ue","note","credits"])

    # ── Résumé final ────────────────────────────────────────
    duree = round(time.time() - start, 1)
    print(f"\n{'='*55}")
    print(f"TERMINE en {duree}s")
    print(f"{'='*55}")
    cur = conn.cursor()
    for table in ["dim_ufr","dim_filiere","dim_etudiant",
                  "fact_resultats","fact_notes_ue"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        n = cur.fetchone()[0]
        print(f"  {table:30s} : {n:>10,} lignes")
    cur.close()
    conn.close()
    print("\nMigration terminee avec succes !")

if __name__ == "__main__":
    main()
