"""
data_loader.py — Chargement et cache des données UTS
Toutes les fonctions de calcul des KPIs et indicateurs
"""
import pandas as pd
import numpy as np
from functools import lru_cache

DATA_PATH = "/home/claude/dataset_35k"

@lru_cache(maxsize=1)
def load_all():
    """Charge tous les fichiers CSV en mémoire (une seule fois)"""
    df_et  = pd.read_csv(f"{DATA_PATH}/dim_etudiant.csv")
    df_res = pd.read_csv(f"{DATA_PATH}/fact_resultats.csv")
    df_ue  = pd.read_csv(f"{DATA_PATH}/fact_notes_ue.csv")
    df_fil = pd.read_csv(f"{DATA_PATH}/dim_filiere.csv")
    df_ufr = pd.read_csv(f"{DATA_PATH}/dim_ufr.csv")

    # Jointure principale
    df = df_res.merge(df_et, on="matricule", how="left")
    df.rename(columns={"ufr_x": "ufr"}, inplace=True)
    if "ufr_y" in df.columns:
        df.drop(columns=["ufr_y"], inplace=True)

    return {
        "etudiants": df_et,
        "resultats": df_res,
        "notes_ue": df_ue,
        "filieres": df_fil,
        "ufrs": df_ufr,
        "joined": df,
    }

def filter_data(ufr=None, filiere=None, niveau=None, semestre=None,
                session="Normale", annee=None, genre=None):
    """Retourne le dataframe filtré selon les critères"""
    data = load_all()
    df = data["joined"].copy()

    if ufr and ufr != "Tous":
        df = df[df["ufr"] == ufr]
    if filiere and filiere != "Toutes":
        df = df[df["filiere_code"] == filiere]
    if niveau and niveau != "Tous":
        df = df[df["niveau"] == niveau]
    if semestre and semestre != "Tous":
        df = df[df["semestre"] == semestre]
    if session and session != "Toutes":
        df = df[df["session"] == session]
    if annee and annee != "Toutes":
        df = df[df["annee_academique"] == annee]
    if genre and genre != "Tous":
        df = df[df["genre"] == genre]

    return df

def compute_kpis(df):
    """Calcule les 6 KPIs principaux"""
    total = len(df)
    if total == 0:
        return {"effectif": 0, "taux_reussite": 0, "taux_echec": 0,
                "taux_defaillance": 0, "moyenne": 0, "taux_mention": 0, "ipg": 0}

    admis     = (df["statut"] == "Admis").sum()
    ajournes  = (df["statut"] == "Ajourné").sum()
    def_      = (df["statut"] == "Défaillant").sum()
    avec_moy  = df["moyenne_generale"].dropna()
    mentions  = df[df["statut"] == "Admis"]["mention"].isin(
                    ["Assez bien", "Bien", "Très bien"]).sum()
    nb_admis  = admis if admis > 0 else 1

    taux_reussite = round(100 * admis / total, 1) if total > 0 else 0
    taux_echec    = round(100 * ajournes / total, 1) if total > 0 else 0
    taux_def      = round(100 * def_ / total, 1) if total > 0 else 0
    moyenne       = round(avec_moy.mean(), 2) if len(avec_moy) > 0 else 0
    taux_mention  = round(100 * mentions / admis, 1) if admis > 0 else 0

    # Indice de Performance Globale (IPG) — formule du CDC
    ipg = round((taux_reussite * 0.4) + (taux_mention * 0.3) + (min(moyenne/20*100, 100) * 0.3), 1)

    # Nombre d'étudiants uniques
    effectif = df["matricule"].nunique()

    return {
        "effectif": effectif,
        "taux_reussite": taux_reussite,
        "taux_echec": taux_echec,
        "taux_defaillance": taux_def,
        "moyenne": moyenne,
        "taux_mention": taux_mention,
        "ipg": ipg,
        "nb_admis": int(admis),
        "nb_ajournes": int(ajournes),
        "nb_defaillants": int(def_),
        "total_resultats": total,
    }

def get_evolution_effectifs():
    """Évolution des effectifs totaux par année académique et UFR"""
    data = load_all()
    df = data["joined"]
    norm = df[df["session"] == "Normale"]
    grouped = norm.groupby(["annee_academique", "ufr"])["matricule"].nunique().reset_index()
    grouped.columns = ["annee", "ufr", "effectif"]
    return grouped.sort_values("annee")

def get_evolution_reussite():
    """Évolution du taux de réussite par année et niveau"""
    data = load_all()
    df = data["joined"]
    norm = df[df["session"] == "Normale"]
    def taux(g):
        return 100 * (g["statut"] == "Admis").sum() / len(g) if len(g) > 0 else 0
    grouped = norm.groupby(["annee_academique", "niveau"]).apply(taux).reset_index()
    grouped.columns = ["annee", "niveau", "taux_reussite"]
    return grouped.sort_values("annee")

def get_distribution_moyennes(df):
    """Distribution des moyennes en intervalles de 2 points"""
    avec_moy = df["moyenne_generale"].dropna()
    bins = list(range(0, 22, 2))
    labels = [f"{b}-{b+2}" for b in bins[:-1]]
    counts, _ = np.histogram(avec_moy, bins=bins)
    return pd.DataFrame({"intervalle": labels, "count": counts})

def get_top_etudiants(df, n=10, sens="top"):
    """Top N ou Bas N étudiants selon la moyenne"""
    avec_moy = df[df["moyenne_generale"].notna()].copy()
    avec_moy["nom_complet"] = avec_moy["prenom"] + " " + avec_moy["nom"]
    cols = ["rang_promo", "nom_complet", "matricule", "filiere_code",
            "niveau", "semestre", "annee_academique", "moyenne_generale",
            "statut", "mention", "genre"]
    cols = [c for c in cols if c in avec_moy.columns]
    if sens == "top":
        result = avec_moy.nlargest(n, "moyenne_generale")[cols]
    else:
        result = avec_moy.nsmallest(n, "moyenne_generale")[cols]
    return result.reset_index(drop=True)

def get_parite_genre(df):
    """Analyse parité H/F"""
    if "genre" not in df.columns:
        return pd.DataFrame()
    groups = df.groupby("genre").agg(
        effectif=("matricule", "nunique"),
        taux_reussite=("statut", lambda x: round(100 * (x == "Admis").sum() / len(x), 1)),
        moyenne=("moyenne_generale", "mean"),
        nb_admis=("statut", lambda x: (x == "Admis").sum()),
        nb_ajournes=("statut", lambda x: (x == "Ajourné").sum()),
    ).reset_index()
    groups["moyenne"] = groups["moyenne"].round(2)
    return groups

def get_mentions(df):
    """Répartition des mentions"""
    admis = df[df["statut"] == "Admis"]
    if len(admis) == 0:
        return pd.DataFrame()
    ordre = ["Très bien", "Bien", "Assez bien", "Passable"]
    counts = admis["mention"].value_counts()
    result = []
    for m in ordre:
        if m in counts:
            result.append({"mention": m, "count": int(counts[m]),
                          "pct": round(100 * counts[m] / len(admis), 1)})
    return pd.DataFrame(result)

def get_comparaison_filieres(df):
    """Comparaison des filières"""
    def agg(g):
        t = len(g)
        return pd.Series({
            "effectif": g["matricule"].nunique(),
            "taux_reussite": round(100 * (g["statut"]=="Admis").sum() / t, 1) if t>0 else 0,
            "taux_defaillance": round(100 * (g["statut"]=="Défaillant").sum() / t, 1) if t>0 else 0,
            "moyenne": round(g["moyenne_generale"].mean(), 2),
        })
    return df.groupby("filiere_code").apply(agg).reset_index()

def get_evolution_par_semestre(df):
    """Taux de réussite par semestre"""
    def taux(g):
        t = len(g)
        return round(100 * (g["statut"] == "Admis").sum() / t, 1) if t > 0 else 0
    grouped = df.groupby(["semestre", "niveau"]).apply(taux).reset_index()
    grouped.columns = ["semestre", "niveau", "taux_reussite"]
    order = ["S1","S2","S3","S4","S5","S6"]
    grouped["semestre"] = pd.Categorical(grouped["semestre"], categories=order, ordered=True)
    return grouped.sort_values("semestre")

def get_flux_sankey(ufr=None):
    """Données pour le diagramme de Sankey (flux entre niveaux)"""
    data = load_all()
    df = data["joined"]
    norm = df[df["session"] == "Normale"]
    if ufr and ufr != "Tous":
        norm = norm[norm["ufr"] == ufr]

    # Calculer les flux L1→L2→L3 par cohorte
    flows = []
    for annee in sorted(norm["annee_entree"].dropna().unique()):
        cohorte = data["etudiants"][data["etudiants"]["annee_entree"] == annee]["matricule"].tolist()
        n_l1 = len(cohorte)
        if n_l1 == 0:
            continue
        # En L2
        in_l2 = norm[(norm["matricule"].isin(cohorte)) & (norm["niveau"] == "L2")]["matricule"].nunique()
        # En L3
        in_l3 = norm[(norm["matricule"].isin(cohorte)) & (norm["niveau"] == "L3")]["matricule"].nunique()
        # Admis final (L3)
        admis_l3 = norm[(norm["matricule"].isin(cohorte)) & (norm["niveau"] == "L3") & (norm["statut"] == "Admis")]["matricule"].nunique()

        flows.append({
            "annee": int(annee),
            "n_l1": n_l1,
            "n_l2": in_l2,
            "n_l3": in_l3,
            "n_admis_l3": admis_l3,
            "abandon_l1": n_l1 - in_l2,
            "abandon_l2": in_l2 - in_l3,
        })
    return pd.DataFrame(flows)

def get_modules_difficiles(df):
    """Moyenne par module pour identifier les matières difficiles"""
    data = load_all()
    notes = data["notes_ue"]
    # Filtrer selon le contexte du df (filière, niveau)
    if "filiere_code" in df.columns and len(df) > 0:
        filieres = df["filiere_code"].unique()
        notes_filtered = notes[notes["filiere_code"].isin(filieres)] if "filiere_code" in notes.columns else notes
    else:
        notes_filtered = notes

    result = notes_filtered.groupby("nom_ue").agg(
        moyenne=("note", "mean"),
        nb_notes=("note", "count"),
        groupe=("groupe_ue", "first")
    ).reset_index()
    result["moyenne"] = result["moyenne"].round(2)
    return result[result["nb_notes"] >= 50].sort_values("moyenne")

def get_taux_reinscription():
    """Taux de réinscription d'une année à l'autre"""
    data = load_all()
    df = data["joined"]
    norm = df[df["session"] == "Normale"]
    result = []
    annees = sorted(norm["annee_academique"].unique())
    for i in range(len(annees) - 1):
        annee_n = annees[i]
        annee_n1 = annees[i + 1]
        ets_n  = set(norm[norm["annee_academique"] == annee_n]["matricule"])
        ets_n1 = set(norm[norm["annee_academique"] == annee_n1]["matricule"])
        if len(ets_n) > 0:
            taux = round(100 * len(ets_n & ets_n1) / len(ets_n), 1)
            result.append({"de": annee_n, "vers": annee_n1, "taux_reinscription": taux,
                          "n_reinscrits": len(ets_n & ets_n1), "n_total": len(ets_n)})
    return pd.DataFrame(result)

print("✅ data_loader.py chargé")
