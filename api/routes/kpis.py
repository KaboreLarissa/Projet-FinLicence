from fastapi import APIRouter
from api.database import query_df

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("/global")
def kpis_global(filiere: str = None, semestre: str = None, session: str = None, annee: str = None, genre: str = None):
    """KPIs globaux : taux réussite, taux échec, moyenne, nb admis, nb ajournés."""
    where, params = _build_where(filiere, semestre, session, annee, genre)
    sql = f"""
        SELECT
            COUNT(*) AS nb_total,
            COUNT(*) FILTER (WHERE r.statut = 'Validé')     AS nb_admis,
            COUNT(*) FILTER (WHERE r.statut = 'Non Validé') AS nb_ajournes,
            COUNT(*) FILTER (WHERE r.statut = 'Ajourné')    AS nb_ajournes2,
            COUNT(*) FILTER (WHERE r.statut = 'Défaillant') AS nb_defaillants,
            ROUND(AVG(r.moyenne_generale) FILTER (WHERE r.moyenne_generale IS NOT NULL AND r.moyenne_generale > 0), 2) AS moyenne_generale,
            ROUND(
                COUNT(*) FILTER (WHERE r.statut = 'Validé') * 100.0 / NULLIF(COUNT(*), 0), 1
            ) AS taux_reussite,
            ROUND(
                (COUNT(*) FILTER (WHERE r.statut IN ('Non Validé','Ajourné'))) * 100.0 / NULLIF(COUNT(*), 0), 1
            ) AS taux_echec
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
    """
    df = query_df(sql, params)
    row = df.iloc[0].to_dict() if not df.empty else {}
    # Consolider nb_ajournes
    row["nb_ajournes"] = (row.get("nb_ajournes", 0) or 0) + (row.get("nb_ajournes2", 0) or 0)
    row.pop("nb_ajournes2", None)
    return row


@router.get("/par_filiere")
def kpis_par_filiere(semestre: str = None, session: str = None, annee: str = None, genre: str = None):
    """KPIs agrégés par filière — pour le tableau comparatif et le radar."""
    where, params = _build_where(None, semestre, session, annee, genre)
    sql = f"""
        SELECT
            f.code_filiere,
            f.nom_filiere,
            COUNT(*) AS nb_total,
            COUNT(*) FILTER (WHERE r.statut = 'Validé') AS nb_admis,
            ROUND(AVG(r.moyenne_generale) FILTER (WHERE r.moyenne_generale IS NOT NULL AND r.moyenne_generale > 0), 2) AS moyenne,
            ROUND(COUNT(*) FILTER (WHERE r.statut = 'Validé') * 100.0 / NULLIF(COUNT(*), 0), 1) AS taux_reussite
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
        GROUP BY f.code_filiere, f.nom_filiere
        ORDER BY taux_reussite DESC NULLS LAST
    """
    return query_df(sql, params).to_dict(orient="records")


@router.get("/evolution")
def kpis_evolution(filiere: str = None, session: str = None, annee: str = None, genre: str = None):
    """Évolution des performances semestre par semestre."""
    where, params = _build_where(filiere, None, session, annee, genre)
    sql = f"""
        SELECT
            s.code_semestre,
            s.numero_semestre,
            f.code_filiere,
            COUNT(*) AS nb_total,
            COUNT(*) FILTER (WHERE r.statut = 'Validé') AS nb_admis,
            ROUND(AVG(r.moyenne_generale) FILTER (WHERE r.moyenne_generale IS NOT NULL AND r.moyenne_generale > 0), 2) AS moyenne,
            ROUND(COUNT(*) FILTER (WHERE r.statut = 'Validé') * 100.0 / NULLIF(COUNT(*), 0), 1) AS taux_reussite
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
        GROUP BY s.code_semestre, s.numero_semestre, f.code_filiere
        ORDER BY s.numero_semestre
    """
    return query_df(sql, params).to_dict(orient="records")


@router.get("/distribution")
def distribution_notes(filiere: str = None, semestre: str = None, session: str = None, annee: str = None):
    """Distribution des moyennes par tranche."""
    where, params = _build_where(filiere, semestre, session, annee, None)
    sql = f"""
        SELECT
            CASE
                WHEN r.moyenne_generale < 5   THEN '0-5'
                WHEN r.moyenne_generale < 10  THEN '5-10'
                WHEN r.moyenne_generale < 12  THEN '10-12'
                WHEN r.moyenne_generale < 14  THEN '12-14'
                WHEN r.moyenne_generale < 16  THEN '14-16'
                ELSE '16-20'
            END AS tranche,
            COUNT(*) AS nb_etudiants
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
        AND r.moyenne_generale IS NOT NULL
        GROUP BY tranche
        ORDER BY tranche
    """
    return query_df(sql, params).to_dict(orient="records")


@router.get("/parite_genre")
def parite_genre(filiere: str = None, semestre: str = None, session: str = None, annee: str = None):
    """Taux de réussite par genre."""
    where, params = _build_where(filiere, semestre, session, annee, None)
    sql = f"""
        SELECT
            e.genre,
            COUNT(*) AS nb_total,
            COUNT(*) FILTER (WHERE r.statut = 'Validé') AS nb_admis,
            ROUND(AVG(r.moyenne_generale) FILTER (WHERE r.moyenne_generale IS NOT NULL AND r.moyenne_generale > 0), 2) AS moyenne,
            ROUND(COUNT(*) FILTER (WHERE r.statut = 'Validé') * 100.0 / NULLIF(COUNT(*), 0), 1) AS taux_reussite
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
        GROUP BY e.genre
        ORDER BY e.genre
    """
    return query_df(sql, params).to_dict(orient="records")


@router.get("/top_etudiants")
def top_etudiants(filiere: str = None, semestre: str = None, session: str = None, annee: str = None, n: int = 10):
    """Top N étudiants par moyenne."""
    where, params = _build_where(filiere, semestre, session, annee, None)
    params["n"] = n
    sql = f"""
        SELECT
            e.nom, e.prenom, e.genre, e.matricule,
            f.code_filiere, s.code_semestre,
            r.moyenne_generale, r.mention, r.rang_promo, r.statut
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
        AND r.moyenne_generale IS NOT NULL AND r.moyenne_generale > 0
        ORDER BY r.moyenne_generale DESC
        LIMIT :n
    """
    return query_df(sql, params).to_dict(orient="records")


@router.get("/etudiants_difficulte")
def etudiants_difficulte(filiere: str = None, semestre: str = None, session: str = None, annee: str = None, seuil: float = 8.0):
    """Étudiants en difficulté (moyenne < seuil)."""
    where, params = _build_where(filiere, semestre, session, annee, None)
    params["seuil"] = seuil
    sql = f"""
        SELECT
            e.nom, e.prenom, e.genre, e.matricule,
            f.code_filiere, s.code_semestre,
            r.moyenne_generale, r.statut, r.mention
        FROM fact_resultats r
        JOIN dim_filiere  f ON f.id_filiere  = r.id_filiere
        JOIN dim_semestre s ON s.id_semestre = r.id_semestre
        JOIN dim_annee_academique a ON a.id_annee = r.id_annee
        JOIN dim_etudiant e ON e.id_etudiant = r.id_etudiant
        {where}
        AND r.moyenne_generale IS NOT NULL
        AND r.moyenne_generale < :seuil
        ORDER BY r.moyenne_generale ASC
        LIMIT 50
    """
    return query_df(sql, params).to_dict(orient="records")


def _build_where(filiere, semestre, session, annee, genre):
    """Construit la clause WHERE dynamiquement selon les filtres actifs."""
    conditions = ["1=1"]
    params = {}
    if filiere:
        conditions.append("f.code_filiere = :filiere")
        params["filiere"] = filiere
    if semestre:
        conditions.append("s.code_semestre = :semestre")
        params["semestre"] = semestre
    if session:
        conditions.append("r.session = :session")
        params["session"] = session
    if annee:
        conditions.append("a.code_annee = :annee")
        params["annee"] = annee
    if genre:
        conditions.append("e.genre = :genre")
        params["genre"] = genre
    return "WHERE " + " AND ".join(conditions), params
