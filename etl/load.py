"""
etl/load.py
Chargement des donnees extraites dans PostgreSQL uts_dashboard_v2
Compatible avec le nouveau schema en constellation (cles VARCHAR)
Strategie UPSERT : insert si inexistant, mise a jour sinon
"""
import psycopg2
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "uts_dashboard_v2",
    "user":     "uts_admin",
    "password": "admin123",
}

STATUT_MAP = {
    "Validé":"Admis","valide":"Admis","Admis":"Admis",
    "Non Validé":"Ajourné","non valide":"Ajourné","Ajourné":"Ajourné",
    "ajourne":"Ajourné","Défaillant":"Défaillant","defaillant":"Défaillant",
}

NIVEAU_MAP = {
    "S1":"L1","S2":"L1","S3":"L2","S4":"L2","S5":"L3","S6":"L3",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def s(val):
    if val is None: return None
    v = str(val).strip()
    return None if v in ("","nan","None","NaN") else v

def n_int(val):
    if val is None: return None
    try:
        v = int(float(val))
        return v if -2147483647 <= v <= 2147483647 else None
    except: return None

def n_float(val):
    if val is None: return None
    try: return round(float(val), 2)
    except: return None

def normaliser_statut(val):
    if not val: return "Ajourné"
    return STATUT_MAP.get(str(val).strip(), "Ajourné")

def normaliser_mention(statut, mention, moyenne):
    if statut != "Admis": return None
    if mention and s(mention): return s(mention)
    if moyenne is None: return "Passable"
    if moyenne >= 16: return "Très bien"
    if moyenne >= 14: return "Bien"
    if moyenne >= 12: return "Assez bien"
    return "Passable"

def assurer_annee(cur, code_annee):
    if not code_annee: return
    cur.execute("SELECT code_annee FROM dim_annee_academique WHERE code_annee=%s",(code_annee,))
    if not cur.fetchone():
        try:
            parts = code_annee.split("-")
            debut,fin = int(parts[0]),int(parts[1])
        except: debut,fin = 2024,2025
        cur.execute("""
            INSERT INTO dim_annee_academique (code_annee,annee_debut,annee_fin)
            VALUES (%s,%s,%s) ON CONFLICT DO NOTHING
        """,(code_annee,debut,fin))

def assurer_etudiant(cur, etu, ufr):
    matricule = s(etu.get("matricule"))
    if not matricule: raise ValueError("Matricule manquant")
    cur.execute("SELECT matricule FROM dim_etudiant WHERE matricule=%s",(matricule,))
    if cur.fetchone():
        cur.execute("""
            UPDATE dim_etudiant
            SET nom=COALESCE(%s,nom), prenom=COALESCE(%s,prenom), genre=COALESCE(%s,genre)
            WHERE matricule=%s
        """,(s(etu.get("nom")),s(etu.get("prenom")),s(etu.get("genre")),matricule))
    else:
        cur.execute("""
            INSERT INTO dim_etudiant (matricule,nom,prenom,genre,ufr,filiere_initiale)
            VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (matricule) DO NOTHING
        """,(matricule,s(etu.get("nom")),s(etu.get("prenom")),
             s(etu.get("genre")) or "M",s(ufr),s(etu.get("filiere"))))
    return matricule

def charger_etudiants(liste_etudiants, ufr="ST", id_user=None):
    """
    Insere ou met a jour les etudiants et leurs resultats.
    Args:
        liste_etudiants : liste de dicts (produite par extract_excel ou extract_pdf)
        ufr             : code UFR — 'ST', 'SEG' ou 'SJP'
        id_user         : id utilisateur pour le log (optionnel)
    Returns:
        dict { nb_inseres, nb_mis_a_jour, nb_erreurs }
    """
    if not liste_etudiants:
        return {"nb_inseres":0,"nb_mis_a_jour":0,"nb_erreurs":0}

    conn = get_connection()
    cur  = conn.cursor()
    nb_inseres=0; nb_mis_a_jour=0; nb_erreurs=0; erreurs=[]

    premier = liste_etudiants[0]
    assurer_annee(cur, premier.get("annee"))
    conn.commit()

    for etu in liste_etudiants:
        try:
            semestre     = s(etu.get("semestre"))
            filiere_code = s(etu.get("filiere"))
            annee_acad   = s(etu.get("annee"))
            session      = s(etu.get("session")) or "Normale"
            niveau       = NIVEAU_MAP.get(semestre,"L1")
            statut       = normaliser_statut(etu.get("statut"))
            moyenne      = n_float(etu.get("moyenne_generale"))
            total_pts    = n_float(etu.get("total_points"))
            mention      = normaliser_mention(statut,etu.get("mention"),moyenne)
            rang         = n_int(etu.get("rang_promo"))
            nb_val       = n_int(etu.get("nb_ue_validees")) or 0
            nb_ech       = n_int(etu.get("nb_ue_echouees")) or 0

            matricule = assurer_etudiant(cur, etu, ufr)

            cur.execute("""
                INSERT INTO fact_resultats
                    (matricule,ufr,filiere_code,niveau,semestre,
                     annee_academique,session,moyenne_generale,total_points,
                     nb_ue_validees,nb_ue_echouees,statut,mention,rang_promo)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (matricule,filiere_code,semestre,annee_academique,session)
                DO UPDATE SET
                    moyenne_generale=EXCLUDED.moyenne_generale,
                    total_points=EXCLUDED.total_points,
                    nb_ue_validees=EXCLUDED.nb_ue_validees,
                    nb_ue_echouees=EXCLUDED.nb_ue_echouees,
                    statut=EXCLUDED.statut,
                    mention=EXCLUDED.mention,
                    rang_promo=EXCLUDED.rang_promo
                RETURNING id_resultat,(xmax::text::int > 0) AS was_update
            """,(matricule,ufr,filiere_code,niveau,semestre,
                 annee_acad,session,moyenne,total_pts,
                 nb_val,nb_ech,statut,mention,rang))

            row       = cur.fetchone()
            id_res    = row[0]
            was_upd   = row[1]

            if was_upd:
                nb_mis_a_jour += 1
                cur.execute("DELETE FROM fact_notes_ue WHERE id_resultat=%s",(id_res,))
            else:
                nb_inseres += 1

            notes = etu.get("notes_ue",[])
            if notes:
                cur.executemany("""
                    INSERT INTO fact_notes_ue
                        (id_resultat,matricule,ufr,filiere_code,niveau,
                         semestre,annee_academique,session,nom_ue,credits,note)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,[(id_res,matricule,ufr,filiere_code,niveau,
                      semestre,annee_acad,session,
                      s(n.get("nom_ue")),n_int(n.get("credits")),n_float(n.get("note")))
                     for n in notes if s(n.get("nom_ue"))])

            conn.commit()

        except Exception as e:
            nb_erreurs += 1
            erreurs.append(f"{etu.get('matricule','?')}:{e}")
            conn.rollback()

    # Log import
    try:
        cur.execute("""
            INSERT INTO log_imports
                (fichier_nom,ufr,semestre,annee_academique,
                 nb_etudiants,nb_resultats,statut,message,importe_par)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,(
            "pipeline", ufr,
            premier.get("semestre"), premier.get("annee"),
            nb_inseres+nb_mis_a_jour, nb_inseres+nb_mis_a_jour,
            "succès" if nb_erreurs==0 else "erreur",
            f"{nb_inseres} insérés, {nb_mis_a_jour} mis à jour, {nb_erreurs} erreurs"
            +(f". {'; '.join(erreurs[:3])}" if erreurs else ""),
            id_user
        ))
        conn.commit()
    except: conn.rollback()

    cur.close(); conn.close()
    if erreurs: print(f"    {nb_erreurs} erreurs : {'; '.join(erreurs[:2])}")
    return {"nb_inseres":nb_inseres,"nb_mis_a_jour":nb_mis_a_jour,"nb_erreurs":nb_erreurs}
