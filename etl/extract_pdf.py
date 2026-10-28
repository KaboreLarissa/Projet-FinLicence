"""
Extraction des données depuis les PV PDF UVBF Génie Logiciel.
Gère les PDFs S3→S6 (sessions normale et rattrapage).

La structure d'une ligne de données dans ces PDFs est :
  N° Nom Prénom INE [date_naiss] [lieu_naiss] [Statut] SEXE UE1...UEN Total Moyenne Résultat Mention Rang
"""
import re
import pdfplumber
import pandas as pd
from etl.extract_excel import normaliser_genre, normaliser_statut


def lire_pdf_gl(filepath: str, semestre: str, filiere: str, annee: str, session: str) -> list[dict]:
    """
    Lit un PV PDF UVBF GL et retourne une liste de dicts étudiants.
    Utilise la proclamation des résultats (liste admis) pour les données fiables.
    """
    resultats = []

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # On cherche les lignes qui commencent par un numéro suivi d'un nom
                # Pattern : numéro + NOM + prénom + INE (commence par N ou E suivi de chiffres)
                # Ex: "1 BOUGOUMA ABDOUL AZIZ n00030620221 31/12/2001 OUAGADOUGOU Masculin 11,16 ..."
                match = re.match(r'^(\d+)\s+([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ][A-ZÀÂÄÉÈÊËÏÎÔÙÛÜ\s\-\.\']+?)\s+((?:N|n|E|e)\d{11})', line)
                if not match:
                    continue

                numero = match.group(1)
                nom_prenom_raw = match.group(2).strip()
                ine = match.group(3).upper()

                # Extraire le reste de la ligne après l'INE
                rest = line[match.end():].strip()

                # Essayer de séparer nom et prénom
                # Dans les PDFs, le format est souvent NOM PRÉNOM en majuscules
                parts_nom = nom_prenom_raw.split()
                # Heuristique : le premier mot(s) en majuscules = nom de famille
                nom = parts_nom[0] if parts_nom else nom_prenom_raw
                prenom = " ".join(parts_nom[1:]).title() if len(parts_nom) > 1 else ""

                # Parser le reste : [date] [lieu] [statut] [sexe] notes... total moyenne résultat mention [rang]
                tokens = rest.split()

                # Détecter le genre
                genre = "M"
                genre_idx = None
                for i, t in enumerate(tokens):
                    if t.lower() in ("masculin", "féminin", "feminin"):
                        genre = normaliser_genre(t)
                        genre_idx = i
                        break

                # Après le genre, on a les notes numériques
                notes_start = (genre_idx + 1) if genre_idx is not None else 0

                # Extraire tous les tokens numériques (notes en format XX,XX ou XX.XX)
                numeric_tokens = []
                remaining_tokens = tokens[notes_start:]

                statut_result = "Non Validé"
                mention = None
                rang = None

                for i, t in enumerate(remaining_tokens):
                    t_clean = t.replace(",", ".")
                    try:
                        val = float(t_clean)
                        numeric_tokens.append(val)
                    except ValueError:
                        # Peut être Validé, Non Validé, Mention, Rang
                        if t.lower() in ("validé", "valide", "non", "ajourné", "ajourne", "défaillant"):
                            # Capturer le statut (peut être 2 mots "Non Validé")
                            statut_str = t
                            if t.lower() == "non" and i + 1 < len(remaining_tokens):
                                statut_str = t + " " + remaining_tokens[i + 1]
                            statut_result = normaliser_statut(statut_str)
                        elif t.lower() in ("bien", "assez", "très", "passable", "insuffisant", "inssufisant"):
                            if mention is None:
                                mention = t.title()
                                # "Assez Bien", "Très Bien"
                                if t.lower() in ("assez", "très", "tres") and i + 1 < len(remaining_tokens):
                                    mention = t.title() + " " + remaining_tokens[i + 1].title()
                        elif re.match(r'^\d+$', t) and rang is None:
                            try:
                                rang = int(t)
                            except ValueError:
                                pass

                if not numeric_tokens:
                    continue

                # Les derniers tokens numériques sont : ... Total Moyenne
                # La moyenne est l'avant-dernier ou dernier token numérique significatif (≤ 20)
                moyenne = None
                total = None

                # Chercher la moyenne (valeur ≤ 20) en partant de la fin
                for v in reversed(numeric_tokens):
                    if 0 <= v <= 20:
                        moyenne = round(v, 2)
                        break

                # Le total est la somme des notes × crédits (valeur >> 20)
                for v in reversed(numeric_tokens):
                    if v > 20:
                        total = round(v, 2)
                        break

                # Les notes UE sont les valeurs avant le total
                notes_brutes = []
                if total is not None:
                    for v in numeric_tokens:
                        if v == total:
                            break
                        notes_brutes.append(v)
                else:
                    notes_brutes = numeric_tokens[:-1] if len(numeric_tokens) > 1 else numeric_tokens

                # Construire les notes UE sans noms de colonnes (les noms seront ajoutés via mapping)
                notes_ue = []
                nb_validees = 0
                nb_echouees = 0
                for i, note in enumerate(notes_brutes):
                    notes_ue.append({
                        "nom_ue": f"UE_{i+1:02d}",
                        "credits": None,
                        "note": note,
                    })
                    if note >= 10:
                        nb_validees += 1
                    else:
                        nb_echouees += 1

                etudiant = {
                    "matricule": ine,
                    "nom": nom.upper(),
                    "prenom": prenom,
                    "genre": genre,
                    "lieu_naissance": None,
                    "statut_inscription": "Etudiant",
                    "annee_premiere_inscription": None,
                    "semestre": semestre,
                    "filiere": filiere,
                    "annee": annee,
                    "session": session,
                    "moyenne_generale": moyenne,
                    "total_points": total,
                    "statut": statut_result,
                    "mention": mention,
                    "rang_promo": rang,
                    "nb_ue_validees": nb_validees,
                    "nb_ue_echouees": nb_echouees,
                    "notes_ue": notes_ue,
                }
                resultats.append(etudiant)

    # Dédupliquer par matricule (garder le premier)
    seen = set()
    unique = []
    for r in resultats:
        if r["matricule"] not in seen:
            seen.add(r["matricule"])
            unique.append(r)

    print(f"  [{semestre} | {filiere} | {annee} | {session}] {len(unique)} étudiants extraits depuis {filepath.split('/')[-1]}")
    return unique
