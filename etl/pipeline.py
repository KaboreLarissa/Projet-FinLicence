"""
etl/pipeline.py
Pipeline ETL pour le dashboard UTS - uts_dashboard_v2
Traite les fichiers uploades par l'admin (CSV ou Excel)

Format du fichier attendu (colonnes obligatoires) :
    MATRICULE, NOM, PRENOM, GENRE, MOYENNE, STATUT
Colonnes optionnelles :
    MENTION, RANG, NOM_UE_1, NOTE_UE_1, NOM_UE_2, NOTE_UE_2, ...

Usage en ligne de commande :
    python etl/pipeline.py --fichier data/raw/ST_S1_2024-2025.csv
                           --ufr ST
                           --filiere MPCI
                           --semestre S1
                           --annee 2024-2025
                           --session Normale
"""
import os, sys, argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.load import charger_etudiants


def extraire_csv(filepath, semestre, filiere, annee, session):
    """
    Lit un fichier CSV uploade par l'admin et retourne
    une liste de dicts compatible avec charger_etudiants().
    """
    import pandas as pd

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    # Normaliser les noms de colonnes en majuscules sans espaces
    col_map = {c.strip().upper(): c for c in df.columns}

    # Verifier les colonnes obligatoires
    required = ["MATRICULE", "NOM", "PRENOM", "GENRE", "MOYENNE", "STATUT"]
    manquantes = [r for r in required if r not in col_map]
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes dans le fichier : {', '.join(manquantes)}\n"
            f"Colonnes trouvees : {', '.join(col_map.keys())}"
        )

    etudiants = []
    for _, row in df.iterrows():

        def get(col):
            mapped = col_map.get(col.upper())
            if mapped is None:
                return None
            val = row[mapped]
            if val is None or str(val).strip() in ("", "nan", "NaN", "None"):
                return None
            return val

        # Moyenne
        try:
            moyenne = round(float(str(get("MOYENNE")).replace(",", ".")), 2) \
                      if get("MOYENNE") is not None else None
        except (ValueError, TypeError):
            moyenne = None

        # Genre
        genre_raw = str(get("GENRE") or "M").strip().upper()
        genre = "F" if genre_raw in ("F", "FEMININ", "FÉMININ", "FEMININE") else "M"

        # Rang
        try:
            rang = int(get("RANG")) if get("RANG") is not None else None
        except (ValueError, TypeError):
            rang = None

        # Notes UE — colonnes optionnelles NOM_UE_x / NOTE_UE_x
        notes_ue = []
        i = 1
        while True:
            nom_col  = f"NOM_UE_{i}"
            note_col = f"NOTE_UE_{i}"
            if nom_col not in col_map and note_col not in col_map:
                break
            nom_ue = get(nom_col)
            try:
                note = round(float(str(get(note_col)).replace(",",".")), 2) \
                       if get(note_col) is not None else None
            except (ValueError, TypeError):
                note = None
            if nom_ue:
                notes_ue.append({"nom_ue": str(nom_ue).strip(),
                                  "credits": None, "note": note})
            i += 1

        matricule = str(get("MATRICULE") or "").strip()
        if not matricule:
            continue  # Ignorer les lignes sans matricule

        etudiants.append({
            "matricule":        matricule,
            "nom":              str(get("NOM") or "").strip().upper(),
            "prenom":           str(get("PRENOM") or "").strip().title(),
            "genre":            genre,
            "semestre":         semestre,
            "filiere":          filiere,
            "annee":            annee,
            "session":          session,
            "moyenne_generale": moyenne,
            "total_points":     None,
            "statut":           str(get("STATUT") or "Ajourné").strip(),
            "mention":          str(get("MENTION")).strip() if get("MENTION") else None,
            "rang_promo":       rang,
            "nb_ue_validees":   sum(1 for n in notes_ue if n["note"] and n["note"] >= 10),
            "nb_ue_echouees":   sum(1 for n in notes_ue if n["note"] and n["note"] < 10),
            "notes_ue":         notes_ue,
        })

    print(f"  {len(etudiants)} etudiants extraits depuis {os.path.basename(filepath)}")
    return etudiants


def extraire_excel(filepath, semestre, filiere, annee, session):
    """
    Lit un fichier Excel uploade par l'admin.
    Utilise la meme logique que le CSV.
    """
    import pandas as pd

    # Lire le fichier Excel et le convertir en CSV temporaire
    df = pd.read_excel(filepath, sheet_name=0)
    temp_csv = filepath.replace(".xlsx", "_temp.csv").replace(".xls", "_temp.csv")
    df.to_csv(temp_csv, index=False, encoding="utf-8-sig")

    try:
        result = extraire_csv(temp_csv, semestre, filiere, annee, session)
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)

    return result


def run_pipeline(filepath, ufr, filiere, semestre, annee, session, id_user=None):
    """
    Fonction principale appelee par :
    - La ligne de commande (ci-dessous)
    - La route FastAPI POST /upload (etape suivante)

    Args:
        filepath  : chemin complet vers le fichier uploade
        ufr       : code UFR ('ST', 'SEG', 'SJP')
        filiere   : code filiere ('MPCI', 'HYDRO', 'DROIT', etc.)
        semestre  : 'S1' a 'S6'
        annee     : '2024-2025'
        session   : 'Normale' ou 'Rattrapage'
        id_user   : id de l'admin qui uploade (pour le log)

    Returns:
        dict { nb_inseres, nb_mis_a_jour, nb_erreurs }
    """
    print("\n" + "="*55)
    print("PIPELINE ETL — uts_dashboard_v2")
    print("="*55)
    print(f"  Fichier  : {os.path.basename(filepath)}")
    print(f"  UFR      : {ufr}")
    print(f"  Filiere  : {filiere}")
    print(f"  Semestre : {semestre}")
    print(f"  Annee    : {annee}")
    print(f"  Session  : {session}")
    print("-"*55)

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        etudiants = extraire_csv(filepath, semestre, filiere, annee, session)
    elif ext in (".xlsx", ".xls"):
        etudiants = extraire_excel(filepath, semestre, filiere, annee, session)
    else:
        raise ValueError(f"Format non supporte : {ext}. Utilisez .csv ou .xlsx")

    if not etudiants:
        print("  Aucun etudiant extrait — verifier le format du fichier")
        return {"nb_inseres": 0, "nb_mis_a_jour": 0, "nb_erreurs": 0}

    stats = charger_etudiants(etudiants, ufr=ufr, id_user=id_user)

    print("\n" + "="*55)
    print("RESULTAT")
    print("="*55)
    print(f"  Inseres     : {stats['nb_inseres']}")
    print(f"  Mis a jour  : {stats['nb_mis_a_jour']}")
    print(f"  Erreurs     : {stats['nb_erreurs']}")
    print("="*55)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline ETL UTS Dashboard — charge un fichier de resultats"
    )
    parser.add_argument(
        "--fichier",  required=True,
        help="Chemin vers le fichier CSV ou Excel a charger"
    )
    parser.add_argument(
        "--ufr",      required=True, choices=["ST","SEG","SJP"],
        help="Code UFR : ST, SEG ou SJP"
    )
    parser.add_argument(
        "--filiere",  required=True,
        help="Code filiere (ex: MPCI, HYDRO, DROIT, ECO_GES...)"
    )
    parser.add_argument(
        "--semestre", required=True, choices=["S1","S2","S3","S4","S5","S6"],
        help="Semestre : S1 a S6"
    )
    parser.add_argument(
        "--annee",    required=True,
        help="Annee academique (ex: 2024-2025)"
    )
    parser.add_argument(
        "--session",  default="Normale", choices=["Normale","Rattrapage"],
        help="Session : Normale ou Rattrapage"
    )

    args = parser.parse_args()

    if not os.path.exists(args.fichier):
        print(f"Erreur : fichier introuvable -> {args.fichier}")
        sys.exit(1)

    run_pipeline(
        filepath=args.fichier,
        ufr=args.ufr,
        filiere=args.filiere,
        semestre=args.semestre,
        annee=args.annee,
        session=args.session,
    )
