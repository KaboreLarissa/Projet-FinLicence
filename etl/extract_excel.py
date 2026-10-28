"""
Extraction des données depuis les fichiers Excel UVBF Génie Logiciel.
Version simplifiée et robuste — lit directement par position de colonne.
"""
import pandas as pd
import numpy as np

COLONNES_A_IGNORER = {
    "Génie Logiciel", "Fondamentaux de l'informatique",
    "Fondamentaux de la programmation", "Systèmes et Réseaux",
    "Projet de Programmation", "Langues, Communication et Entrepreneuriat",
    "Langues, communication et entrepreneuriat", "Développement logiciel",
    "M0DULES DU SEMESTRE 2", "M0DULES DU SEMESTRE 3",
    "M0DULES DU SEMESTRE 4", "M0DULES DU SEMESTRE 5",
    "M0DULES DU SEMESTRE 6", "Analyse et Conception des SI",
    "Développement d'applications", "Développement d'interfaces utilisateurs",
    "Technoligie émergeante1", "Technologie émergente2",
}

COLONNES_META = {
    "N°", "Nom", "Prénom", "INE", "date de naissance",
    "Lieu de naissance", "Statut", "SEXE", "Sexe",
    "Total", "Rang",
}

def _is_resultat_col(name: str) -> bool:
    n = name.strip()
    return any(n.startswith(p) for p in [
        "Moyenne Semestre", "Résultat Semestre", "Mention",
        "Résultat Semestre", "Moyenne Semestre"
    ])

def normaliser_genre(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "M"
    v = str(val).strip().lower()
    return "F" if v in ("féminin", "feminin", "f", "female") else "M"

def normaliser_statut(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "Non Validé"
    v = str(val).strip().lower()
    if "non" in v:
        return "Non Validé"
    if "validé" in v or "valide" in v:
        return "Validé"
    if "ajourné" in v or "ajourne" in v:
        return "Ajourné"
    if "défaillant" in v or "defaillant" in v:
        return "Défaillant"
    return "Non Validé"

def lire_excel_gl(filepath: str, semestre: str, filiere: str, annee: str, session: str = "Normale") -> list:
    df = pd.read_excel(filepath, sheet_name=0, header=None)

    # Trouver la ligne d'en-tête (contient "Nom")
    header_idx = None
    for i in range(min(5, len(df))):
        vals = [str(v) for v in df.iloc[i].tolist()]
        if "Nom" in vals or "N°" in vals:
            header_idx = i
            break
    if header_idx is None:
        print(f"  ⚠️  En-tête non trouvé dans {filepath}")
        return []

    headers = [str(v).strip() if str(v) not in ("nan", "None") else "" for v in df.iloc[header_idx].tolist()]
    credits_row = df.iloc[header_idx + 1].tolist() if header_idx + 1 < len(df) else []
    data_start = header_idx + 2

    # Construire le mapping nom → index
    col_idx = {}
    ue_cols = []
    for idx, h in enumerate(headers):
        if not h:
            continue
        h_clean = h.replace("\n", " ").strip()
        if h_clean in COLONNES_META or h in COLONNES_META:
            col_idx[h_clean] = idx
            col_idx[h] = idx  # double mapping pour être sûr
        elif _is_resultat_col(h_clean):
            col_idx[h_clean] = idx
        elif h_clean not in COLONNES_A_IGNORER:
            cred_val = credits_row[idx] if idx < len(credits_row) else None
            try:
                cred = int(cred_val) if cred_val is not None and str(cred_val) != "nan" else None
            except (ValueError, TypeError):
                cred = None
            ue_cols.append({"idx": idx, "nom_ue": h_clean, "credits": cred})

    def get_val(row, *keys):
        for k in keys:
            idx = col_idx.get(k)
            if idx is not None and idx < len(row):
                v = row[idx]
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    return v
        return None

    resultats = []
    for row_idx in range(data_start, len(df)):
        row = df.iloc[row_idx].tolist()

        nom = get_val(row, "Nom")
        if nom is None or str(nom).strip() == "":
            continue
        ine = get_val(row, "INE")
        if ine is None or str(ine).strip() == "":
            continue

        matricule = str(ine).strip()
        nom_str = str(nom).strip().upper()
        prenom_raw = get_val(row, "Prénom")
        prenom_str = str(prenom_raw).strip().title() if prenom_raw else ""
        genre = normaliser_genre(get_val(row, "SEXE", "Sexe"))
        lieu = get_val(row, "Lieu de naissance")
        statut_insc = get_val(row, "Statut") or "Etudiant"

        # Moyenne : chercher la colonne du bon semestre
        sem_num = semestre[1]  # "1", "2", etc.
        moy_raw = get_val(row, f"Moyenne Semestre {sem_num}")
        if moy_raw is None:
            # Fallback : chercher n'importe quelle colonne Moyenne
            for k in [f"Moyenne Semestre {i}" for i in range(1, 7)]:
                moy_raw = get_val(row, k)
                if moy_raw is not None:
                    break
        try:
            moyenne = round(float(str(moy_raw).replace(",", ".")), 2) if moy_raw is not None else None
            if moyenne is not None and moyenne > 20:
                moyenne = None  # valeur aberrante
        except (ValueError, TypeError):
            moyenne = None

        total_raw = get_val(row, "Total")
        try:
            total = round(float(str(total_raw).replace(",", ".")), 2) if total_raw is not None else None
        except (ValueError, TypeError):
            total = None

        statut_raw = get_val(row, f"Résultat Semestre {sem_num}")
        if statut_raw is None:
            for k in [f"Résultat Semestre {i}" for i in range(1, 7)]:
                statut_raw = get_val(row, k)
                if statut_raw is not None:
                    break
        statut_res = normaliser_statut(statut_raw)

        mention_raw = get_val(row, "Mention")
        mention = str(mention_raw).strip() if mention_raw else None

        rang_raw = get_val(row, "Rang")
        try:
            rang = int(rang_raw) if rang_raw is not None else None
        except (ValueError, TypeError):
            rang = None

        notes_ue = []
        nb_val = 0
        nb_ech = 0
        for ue in ue_cols:
            note_raw = row[ue["idx"]] if ue["idx"] < len(row) else None
            try:
                note = round(float(str(note_raw).replace(",", ".")), 2) if note_raw is not None and str(note_raw) != "nan" else None
            except (ValueError, TypeError):
                note = None
            notes_ue.append({"nom_ue": ue["nom_ue"], "credits": ue["credits"], "note": note})
            if note is not None:
                if note >= 10:
                    nb_val += 1
                else:
                    nb_ech += 1

        resultats.append({
            "matricule": matricule,
            "nom": nom_str,
            "prenom": prenom_str,
            "genre": genre,
            "lieu_naissance": str(lieu).strip() if lieu else None,
            "statut_inscription": str(statut_insc).strip(),
            "annee_premiere_inscription": None,
            "semestre": semestre,
            "filiere": filiere,
            "annee": annee,
            "session": session,
            "moyenne_generale": moyenne,
            "total_points": total,
            "statut": statut_res,
            "mention": mention,
            "rang_promo": rang,
            "nb_ue_validees": nb_val,
            "nb_ue_echouees": nb_ech,
            "notes_ue": notes_ue,
        })

    print(f"  [{semestre} | {filiere} | {annee} | {session}] {len(resultats)} étudiants extraits depuis {filepath.split('/')[-1].split(chr(92))[-1]}")
    return resultats
