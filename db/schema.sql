-- ============================================================
-- SCHÉMA BASE DE DONNÉES : uts_dashboard_v2
-- Université Thomas Sankara — Dashboard Académique
-- Schéma en constellation (modèle Kimball)
-- ============================================================

-- Supprimer les tables si elles existent déjà (pour relancer proprement)
DROP TABLE IF EXISTS fact_notes_ue    CASCADE;
DROP TABLE IF EXISTS fact_resultats   CASCADE;
DROP TABLE IF EXISTS dim_etudiant     CASCADE;
DROP TABLE IF EXISTS dim_filiere      CASCADE;
DROP TABLE IF EXISTS dim_semestre     CASCADE;
DROP TABLE IF EXISTS dim_annee_academique CASCADE;
DROP TABLE IF EXISTS dim_ufr          CASCADE;
DROP TABLE IF EXISTS utilisateurs     CASCADE;
DROP TABLE IF EXISTS log_imports      CASCADE;

-- ── 1. dim_ufr ──────────────────────────────────────────────
CREATE TABLE dim_ufr (
    code_ufr            VARCHAR(10)  PRIMARY KEY,
    nom_ufr             VARCHAR(150) NOT NULL,
    nb_etudiants_ref    INTEGER,
    nb_enseignants_ref  INTEGER
);

-- ── 2. dim_filiere ──────────────────────────────────────────
CREATE TABLE dim_filiere (
    code_filiere        VARCHAR(30)  PRIMARY KEY,
    nom_filiere         VARCHAR(200) NOT NULL,
    ufr                 VARCHAR(10)  REFERENCES dim_ufr(code_ufr),
    filiere_parente     VARCHAR(30),
    semestre_bifurcation VARCHAR(5),
    niveau_terminal     VARCHAR(5),
    ratio_F             DECIMAL(5,3)
);

-- ── 3. dim_semestre ─────────────────────────────────────────
CREATE TABLE dim_semestre (
    code_semestre       VARCHAR(5)   PRIMARY KEY,
    numero              INTEGER      NOT NULL,
    niveau              VARCHAR(5)   NOT NULL,
    periode             VARCHAR(30)
);

-- ── 4. dim_annee_academique ─────────────────────────────────
CREATE TABLE dim_annee_academique (
    code_annee          VARCHAR(12)  PRIMARY KEY,
    annee_debut         INTEGER      NOT NULL,
    annee_fin           INTEGER      NOT NULL
);

-- ── 5. dim_etudiant ─────────────────────────────────────────
CREATE TABLE dim_etudiant (
    matricule           VARCHAR(20)  PRIMARY KEY,
    nom                 VARCHAR(100) NOT NULL,
    prenom              VARCHAR(100) NOT NULL,
    genre               CHAR(1)      CHECK (genre IN ('M','F')),
    age_entree          INTEGER,
    annee_entree        INTEGER,
    filiere_initiale    VARCHAR(30)  REFERENCES dim_filiere(code_filiere),
    ufr                 VARCHAR(10)  REFERENCES dim_ufr(code_ufr)
);

-- ── 6. fact_resultats ───────────────────────────────────────
CREATE TABLE fact_resultats (
    id_resultat         SERIAL       PRIMARY KEY,
    matricule           VARCHAR(20)  REFERENCES dim_etudiant(matricule),
    ufr                 VARCHAR(10)  REFERENCES dim_ufr(code_ufr),
    filiere_code        VARCHAR(30)  REFERENCES dim_filiere(code_filiere),
    niveau              VARCHAR(5)   NOT NULL,
    semestre            VARCHAR(5)   REFERENCES dim_semestre(code_semestre),
    annee_academique    VARCHAR(12)  REFERENCES dim_annee_academique(code_annee),
    session             VARCHAR(20)  CHECK (session IN ('Normale','Rattrapage')),
    moyenne_generale    DECIMAL(5,2),   -- NULL si Défaillant
    total_points        DECIMAL(8,2),
    nb_ue_validees      INTEGER      DEFAULT 0,
    nb_ue_echouees      INTEGER      DEFAULT 0,
    statut              VARCHAR(20)  CHECK (statut IN ('Admis','Ajourné','Défaillant')),
    mention             VARCHAR(20),    -- NULL si pas Admis
    rang_promo          INTEGER         -- NULL si Défaillant
);

-- ── 7. fact_notes_ue ────────────────────────────────────────
CREATE TABLE fact_notes_ue (
    id_note             SERIAL       PRIMARY KEY,
    id_resultat         INTEGER      REFERENCES fact_resultats(id_resultat),
    matricule           VARCHAR(20)  REFERENCES dim_etudiant(matricule),
    ufr                 VARCHAR(10),
    filiere_code        VARCHAR(30),
    niveau              VARCHAR(5),
    semestre            VARCHAR(5),
    annee_academique    VARCHAR(12),
    session             VARCHAR(20),
    nom_ue              VARCHAR(200) NOT NULL,
    groupe_ue           VARCHAR(100),
    note                DECIMAL(5,2),
    credits             INTEGER
);

-- ── 8. utilisateurs ─────────────────────────────────────────
CREATE TABLE utilisateurs (
    id                  SERIAL       PRIMARY KEY,
    nom                 VARCHAR(100) NOT NULL,
    prenom              VARCHAR(100) NOT NULL,
    email               VARCHAR(150) UNIQUE NOT NULL,
    mot_de_passe_hash   VARCHAR(255) NOT NULL,
    role                VARCHAR(20)  NOT NULL CHECK (role IN ('admin','responsable')),
    ufr                 VARCHAR(10),     -- NULL = accès toutes UFR
    actif               BOOLEAN      DEFAULT TRUE,
    cree_le             TIMESTAMP    DEFAULT NOW(),
    derniere_connexion  TIMESTAMP
);

-- ── 9. log_imports ──────────────────────────────────────────
CREATE TABLE log_imports (
    id                  SERIAL       PRIMARY KEY,
    fichier_nom         VARCHAR(255) NOT NULL,
    ufr                 VARCHAR(10),
    semestre            VARCHAR(5),
    annee_academique    VARCHAR(12),
    nb_etudiants        INTEGER,
    nb_resultats        INTEGER,
    statut              VARCHAR(20)  CHECK (statut IN ('succès','erreur')),
    message             TEXT,
    importe_par         INTEGER      REFERENCES utilisateurs(id),
    importe_le          TIMESTAMP    DEFAULT NOW()
);

-- ── Index pour accélérer les requêtes fréquentes ────────────
CREATE INDEX idx_res_matricule   ON fact_resultats(matricule);
CREATE INDEX idx_res_filiere     ON fact_resultats(filiere_code);
CREATE INDEX idx_res_niveau      ON fact_resultats(niveau);
CREATE INDEX idx_res_session     ON fact_resultats(session);
CREATE INDEX idx_res_annee       ON fact_resultats(annee_academique);
CREATE INDEX idx_res_statut      ON fact_resultats(statut);
CREATE INDEX idx_ue_resultat     ON fact_notes_ue(id_resultat);
CREATE INDEX idx_ue_matricule    ON fact_notes_ue(matricule);
CREATE INDEX idx_et_ufr          ON dim_etudiant(ufr);

-- ── Vérification ────────────────────────────────────────────
SELECT 'Schéma créé avec succès — ' || count(*) || ' tables'
FROM information_schema.tables
WHERE table_schema = 'public';
