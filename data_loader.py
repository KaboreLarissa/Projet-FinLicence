"""
data_loader.py v2 — Chargement données UTS
Lit depuis PostgreSQL ou CSV selon la configuration
Compatible pandas 3.x
"""
import pandas as pd
import numpy as np
from functools import lru_cache

# ── Configuration ─────────────────────────────────────────────
# Changer ce chemin pour pointer vers vos CSV
DATA_PATH = r"C:\Users\HP\Desktop\ProjetUTS\data"

# ── Connexion PostgreSQL (optionnel) ──────────────────────────
DB_URL = "postgresql://uts_admin:admin123@localhost:5432/uts_dashboard_v2"

def _load_from_csv():
    """Charge depuis les fichiers CSV"""
    import os
    df_et  = pd.read_csv(os.path.join(DATA_PATH, "dim_etudiant.csv"))
    df_res = pd.read_csv(os.path.join(DATA_PATH, "fact_resultats.csv"))
    df_ue  = pd.read_csv(os.path.join(DATA_PATH, "fact_notes_ue.csv"))
    df_fil = pd.read_csv(os.path.join(DATA_PATH, "dim_filiere.csv"))
    df_ufr = pd.read_csv(os.path.join(DATA_PATH, "dim_ufr.csv"))
    return df_et, df_res, df_ue, df_fil, df_ufr

def _load_from_pg():
    """Charge depuis PostgreSQL"""
    from sqlalchemy import create_engine
    engine = create_engine(DB_URL, pool_pre_ping=True)
    df_et  = pd.read_sql("SELECT * FROM dim_etudiant",       engine)
    df_res = pd.read_sql("SELECT * FROM fact_resultats",     engine)
    df_ue  = pd.read_sql("SELECT * FROM fact_notes_ue",      engine)
    df_fil = pd.read_sql("SELECT * FROM dim_filiere",        engine)
    df_ufr = pd.read_sql("SELECT * FROM dim_ufr",            engine)
    return df_et, df_res, df_ue, df_fil, df_ufr

@lru_cache(maxsize=1)
def load_all():
    """Charge toutes les données (mis en cache)"""
    try:
        df_et, df_res, df_ue, df_fil, df_ufr = _load_from_pg()
        print(" data_loader — données depuis PostgreSQL")
    except Exception as e:
        print(f"  PostgreSQL indisponible ({e}) — lecture CSV")
        df_et, df_res, df_ue, df_fil, df_ufr = _load_from_csv()
        print(" data_loader — données depuis CSV")

    # Forcer les colonnes numeriques (evite dtype object)
    for col in ["moyenne_generale","total_points","note","rang_promo"]:
        if col in df_res.columns:
            df_res[col] = pd.to_numeric(df_res[col], errors="coerce")
        if col in df_ue.columns:
            df_ue[col] = pd.to_numeric(df_ue[col], errors="coerce")

    # Jointure principale fact_resultats + dim_etudiant
    df = df_res.merge(
        df_et[["matricule","nom","prenom","genre","age_entree","annee_entree"]],
        on="matricule", how="left"
    )
    # Renommer ufr_x si doublon
    if "ufr_x" in df.columns:
        df = df.rename(columns={"ufr_x":"ufr"})
    if "ufr_y" in df.columns:
        df = df.drop(columns=["ufr_y"])

    return {
        "etudiants": df_et,
        "resultats": df_res,
        "notes_ue":  df_ue,
        "filieres":  df_fil,
        "ufrs":      df_ufr,
        "joined":    df,
    }

def filter_data(ufr=None, filiere=None, niveau=None, semestre=None,
                session="Normale", annee=None, genre=None):
    """Retourne le dataframe filtré"""
    df = load_all()["joined"].copy()
    if ufr      and ufr      != "Tous":    df = df[df["ufr"]              == ufr]
    if filiere  and filiere  != "Toutes":  df = df[df["filiere_code"]     == filiere]
    if niveau   and niveau   != "Tous":    df = df[df["niveau"]           == niveau]
    if semestre and semestre != "Tous":    df = df[df["semestre"]         == semestre]
    if session  and session  != "Toutes": df = df[df["session"]          == session]
    if annee    and annee    != "Toutes":  df = df[df["annee_academique"] == annee]
    if genre    and genre    != "Tous":    df = df[df["genre"]            == genre]
    return df

def compute_kpis(df):
    """Calcule les KPIs sur le dataframe filtré"""
    total = len(df)
    if total == 0:
        return {"effectif":0,"taux_reussite":0,"taux_echec":0,
                "taux_defaillance":0,"moyenne":0,"taux_mention":0,"ipg":0,
                "nb_admis":0,"nb_ajournes":0,"nb_defaillants":0,"total_resultats":0}
    admis    = int((df["statut"]=="Admis").sum())
    ajournes = int((df["statut"]=="Ajourné").sum())
    def_     = int((df["statut"]=="Défaillant").sum())
    avec_moy = df["moyenne_generale"].dropna()
    mentions = int(df[df["statut"]=="Admis"]["mention"].isin(
                   ["Assez bien","Bien","Très bien"]).sum())
    taux_r   = round(100*admis/total,1)
    taux_e   = round(100*ajournes/total,1)
    taux_d   = round(100*def_/total,1)
    moy      = round(float(avec_moy.mean()),2) if len(avec_moy)>0 else 0
    taux_m   = round(100*mentions/max(admis,1),1)
    ipg      = round((taux_r*0.4)+(taux_m*0.3)+(min(moy/20*100,100)*0.3),1)
    return {
        "effectif":         int(df["matricule"].nunique()),
        "taux_reussite":    taux_r,
        "taux_echec":       taux_e,
        "taux_defaillance": taux_d,
        "moyenne":          moy,
        "taux_mention":     taux_m,
        "ipg":              ipg,
        "nb_admis":         admis,
        "nb_ajournes":      ajournes,
        "nb_defaillants":   def_,
        "total_resultats":  total,
    }

def get_kpis_globaux():
    """KPIs calculés sur TOUTES les données — pour les indicateurs fixes"""
    data = load_all()
    norm = data["joined"][data["joined"]["session"]=="Normale"]
    l1_mats = set(norm[norm["niveau"]=="L1"]["matricule"].unique())
    l2_mats = set(norm[norm["niveau"]=="L2"]["matricule"].unique())
    l3_mats = set(norm[norm["niveau"]=="L3"]["matricule"].unique())
    derniere_annee = sorted(norm["annee_academique"].unique())[-1]
    nb_l1_recent = int(norm[
        (norm["niveau"]=="L1")&
        (norm["annee_academique"]==derniere_annee)
    ]["matricule"].nunique())
    return {
        "passage_l1_l2": round(100*len(l1_mats&l2_mats)/max(len(l1_mats),1),1),
        "passage_l2_l3": round(100*len(l2_mats&l3_mats)/max(len(l2_mats),1),1),
        "nb_l1_recent":  nb_l1_recent,
        "derniere_annee": derniere_annee,
    }

def get_evolution_effectifs():
    data = load_all()
    norm = data["joined"][data["joined"]["session"]=="Normale"]
    rows = []
    for (annee,ufr),g in norm.groupby(["annee_academique","ufr"]):
        rows.append({"annee":str(annee),"ufr":str(ufr),"effectif":int(g["matricule"].nunique())})
    return pd.DataFrame(rows).sort_values("annee")

def get_evolution_reussite():
    data = load_all()
    norm = data["joined"][data["joined"]["session"]=="Normale"]
    rows = []
    for (annee,niv),g in norm.groupby(["annee_academique","niveau"]):
        t=len(g)
        rows.append({"annee":str(annee),"niveau":str(niv),
            "taux_reussite":round(100*(g["statut"]=="Admis").sum()/t,1) if t>0 else 0})
    return pd.DataFrame(rows).sort_values("annee")

def get_evolution_reussite_filtre(df):
    """Évolution taux réussite sur données filtrées"""
    rows = []
    for (annee,niv),g in df.groupby(["annee_academique","niveau"]):
        t=len(g)
        rows.append({"annee":str(annee),"niveau":str(niv),
            "taux_reussite":round(100*(g["statut"]=="Admis").sum()/t,1) if t>0 else 0})
    if not rows: return pd.DataFrame(columns=["annee","niveau","taux_reussite"])
    return pd.DataFrame(rows).sort_values("annee")

def get_distribution_moyennes(df):
    # Forcer float pour éviter le bug dtype object depuis PostgreSQL
    avec_moy = pd.to_numeric(df["moyenne_generale"], errors="coerce").dropna()
    avec_moy = avec_moy[(avec_moy >= 0) & (avec_moy <= 20)]  # Valeurs valides uniquement
    bins=list(range(0,22,2))
    labels=[f"{b}-{b+2}" for b in bins[:-1]]
    counts,_=np.histogram(avec_moy,bins=bins)
    return pd.DataFrame({"intervalle":labels,"count":counts})

def get_top_etudiants(df, n=10, sens="top"):
    avec_moy = df[df["moyenne_generale"].notna()].copy()
    # Forcer le type float pour eviter l erreur nlargest avec dtype object
    avec_moy["moyenne_generale"] = pd.to_numeric(avec_moy["moyenne_generale"], errors="coerce")
    avec_moy = avec_moy[avec_moy["moyenne_generale"].notna()]
    cols=["matricule","filiere_code","niveau","semestre","annee_academique",
          "moyenne_generale","statut","mention","genre","prenom","nom"]
    cols=[c for c in cols if c in avec_moy.columns]
    if sens=="top": return avec_moy.nlargest(n,"moyenne_generale")[cols].reset_index(drop=True)
    else:           return avec_moy.nsmallest(n,"moyenne_generale")[cols].reset_index(drop=True)

def get_parite_genre(df):
    if "genre" not in df.columns: return pd.DataFrame()
    rows=[]
    for g,grp in df[df["genre"].isin(["M","F"])].groupby("genre"):
        t=len(grp)
        rows.append({"genre":g,"effectif":int(grp["matricule"].nunique()),
            "taux_reussite":round(100*(grp["statut"]=="Admis").sum()/t,1) if t>0 else 0,
            "moyenne":round(float(grp["moyenne_generale"].mean()),2),
            "nb_admis":int((grp["statut"]=="Admis").sum())})
    return pd.DataFrame(rows)

def get_mentions(df):
    admis=df[df["statut"]=="Admis"]
    if len(admis)==0: return pd.DataFrame()
    ordre=["Très bien","Bien","Assez bien","Passable"]
    counts=admis["mention"].value_counts()
    result=[]
    for m in ordre:
        if m in counts:
            result.append({"mention":m,"count":int(counts[m]),
                "pct":round(100*counts[m]/len(admis),1)})
    return pd.DataFrame(result)

def get_comparaison_filieres(df):
    rows=[]
    for fil,g in df.groupby("filiere_code"):
        t=len(g)
        if t<5: continue
        rows.append({"filiere_code":str(fil),
            "effectif":int(g["matricule"].nunique()),
            "taux_reussite":round(100*(g["statut"]=="Admis").sum()/t,1) if t>0 else 0,
            "taux_defaillance":round(100*(g["statut"]=="Défaillant").sum()/t,1) if t>0 else 0,
            "moyenne":round(float(g["moyenne_generale"].mean()),2) if g["moyenne_generale"].notna().any() else 0,
            "ufr":str(g["ufr"].iloc[0]) if len(g)>0 else "",})
    return pd.DataFrame(rows)

def get_evolution_par_semestre(df):
    rows=[]
    for (sem,niv),g in df.groupby(["semestre","niveau"]):
        t=len(g)
        rows.append({"semestre":sem,"niveau":niv,
            "taux_reussite":round(100*(g["statut"]=="Admis").sum()/t,1) if t>0 else 0})
    grouped=pd.DataFrame(rows)
    if len(grouped)==0: return grouped
    order=["S1","S2","S3","S4","S5","S6"]
    grouped["semestre"]=pd.Categorical(grouped["semestre"],categories=order,ordered=True)
    return grouped.sort_values("semestre")

def get_flux_sankey(ufr=None):
    data=load_all()
    norm=data["joined"][data["joined"]["session"]=="Normale"]
    if ufr: norm=norm[norm["ufr"]==ufr]
    rows=[]
    for annee in sorted(norm["annee_entree"].dropna().unique()):
        cohorte=data["etudiants"][data["etudiants"]["annee_entree"]==annee]["matricule"].tolist()
        n_l1=len(cohorte)
        if n_l1==0: continue
        in_l2=norm[(norm["matricule"].isin(cohorte))&(norm["niveau"]=="L2")]["matricule"].nunique()
        in_l3=norm[(norm["matricule"].isin(cohorte))&(norm["niveau"]=="L3")]["matricule"].nunique()
        admis3=norm[(norm["matricule"].isin(cohorte))&(norm["niveau"]=="L3")&
                    (norm["statut"]=="Admis")]["matricule"].nunique()
        rows.append({"annee":int(annee),"n_l1":n_l1,"n_l2":int(in_l2),
            "n_l3":int(in_l3),"n_admis_l3":int(admis3),
            "abandon_l1":n_l1-int(in_l2),"abandon_l2":int(in_l2)-int(in_l3)})
    return pd.DataFrame(rows)

def get_modules_difficiles(df):
    data=load_all()
    notes=data["notes_ue"]
    if "filiere_code" in df.columns and len(df)>0:
        filieres=df["filiere_code"].unique()
        notes=notes[notes["filiere_code"].isin(filieres)] if "filiere_code" in notes.columns else notes
    result=notes.groupby("nom_ue").agg(
        moyenne=("note","mean"),nb_notes=("note","count"),
        groupe=("groupe_ue","first")).reset_index()
    result["moyenne"]=result["moyenne"].round(2)
    return result[result["nb_notes"]>=50].sort_values("moyenne")

def get_taux_reinscription():
    data=load_all()
    norm=data["joined"][data["joined"]["session"]=="Normale"]
    result=[]
    annees=sorted(norm["annee_academique"].unique())
    for i in range(len(annees)-1):
        a_n=annees[i]; a_n1=annees[i+1]
        e_n=set(norm[norm["annee_academique"]==a_n]["matricule"])
        e_n1=set(norm[norm["annee_academique"]==a_n1]["matricule"])
        if len(e_n)>0:
            result.append({"de":a_n,"vers":a_n1,
                "taux_reinscription":round(100*len(e_n&e_n1)/len(e_n),1),
                "n_reinscrits":len(e_n&e_n1),"n_total":len(e_n)})
    return pd.DataFrame(result)
