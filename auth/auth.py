"""
auth/auth.py — Version finale
Authentification JWT + gestion utilisateurs + log imports/exports
"""
import bcrypt
import psycopg2
from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY         = "uts_dashboard_secret_key_2024_changez_en_production"
ALGORITHM          = "HS256"
TOKEN_EXPIRE_HOURS = 8

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "uts_dashboard_v2",
    "user":     "uts_admin",
    "password": "admin123",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ── Mots de passe ────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# ── JWT ──────────────────────────────────────────────────────
def create_token(user_id, email, role, nom, prenom, ufr=None) -> str:
    payload = {
        "sub":    str(user_id),
        "email":  email,
        "role":   role,
        "nom":    nom,
        "prenom": prenom,
        "ufr":    ufr,
        "exp":    datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# ── Authentification ─────────────────────────────────────────
def get_user_by_email(email: str) -> dict:
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT id, nom, prenom, email, mot_de_passe_hash, role, ufr, actif
            FROM utilisateurs WHERE email = %s
        """, (email,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            return {"id":row[0],"nom":row[1],"prenom":row[2],"email":row[3],
                    "hash":row[4],"role":row[5],"ufr":row[6],"actif":row[7]}
        return None
    except Exception as e:
        print(f"Erreur get_user : {e}")
        return None

def authenticate(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if not user or not user["actif"]: return None
    if not verify_password(password, user["hash"]): return None
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("UPDATE utilisateurs SET derniere_connexion=NOW() WHERE id=%s",(user["id"],))
        conn.commit(); cur.close(); conn.close()
    except Exception: pass
    return user

# ── Gestion utilisateurs ─────────────────────────────────────
def lister_utilisateurs() -> list:
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT id, nom, prenom, email, role, ufr, actif, cree_le, derniere_connexion
            FROM utilisateurs ORDER BY role, nom
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [{"id":r[0],"nom":r[1],"prenom":r[2],"email":r[3],"role":r[4],
                 "ufr":r[5],"actif":r[6],
                 "cree_le":str(r[7])[:10] if r[7] else "",
                 "derniere_connexion":str(r[8])[:10] if r[8] else "Jamais"} for r in rows]
    except Exception as e:
        print(f"Erreur lister_utilisateurs : {e}"); return []

def creer_utilisateur(nom, prenom, email, password, role, ufr=None) -> dict:
    if role not in ("admin","responsable"):
        return {"ok":False,"message":"Rôle invalide"}
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id FROM utilisateurs WHERE email=%s",(email,))
        if cur.fetchone():
            cur.close(); conn.close()
            return {"ok":False,"message":f"Email {email} déjà utilisé"}
        cur.execute("""
            INSERT INTO utilisateurs (nom,prenom,email,mot_de_passe_hash,role,ufr,actif)
            VALUES (%s,%s,%s,%s,%s,%s,TRUE) RETURNING id
        """,(nom,prenom,email,hash_password(password),role,ufr))
        new_id = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return {"ok":True,"id":new_id}
    except Exception as e:
        return {"ok":False,"message":str(e)}

def modifier_utilisateur(user_id, nom=None, prenom=None, email=None,
                          role=None, ufr=None, actif=None, new_password=None) -> dict:
    try:
        conn = get_connection(); cur = conn.cursor()
        updates=[]; values=[]
        if nom        is not None: updates.append("nom=%s");              values.append(nom)
        if prenom     is not None: updates.append("prenom=%s");           values.append(prenom)
        if email      is not None: updates.append("email=%s");            values.append(email)
        if role       is not None: updates.append("role=%s");             values.append(role)
        if ufr        is not None: updates.append("ufr=%s");              values.append(ufr)
        if actif      is not None: updates.append("actif=%s");            values.append(actif)
        if new_password:
            updates.append("mot_de_passe_hash=%s")
            values.append(hash_password(new_password))
        if not updates: return {"ok":False,"message":"Rien à modifier"}
        values.append(user_id)
        cur.execute(f"UPDATE utilisateurs SET {', '.join(updates)} WHERE id=%s",values)
        conn.commit(); cur.close(); conn.close()
        return {"ok":True}
    except Exception as e:
        return {"ok":False,"message":str(e)}

def supprimer_utilisateur(user_id) -> dict:
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM utilisateurs WHERE id=%s",(user_id,))
        conn.commit(); cur.close(); conn.close()
        return {"ok":True}
    except Exception as e:
        return {"ok":False,"message":str(e)}

# ── Log imports ──────────────────────────────────────────────
def log_import(email, nom_user, role, ufr, semestre, annee, fichier_nom,
               nb_inseres, nb_maj, nb_erreurs):
    """Enregistre un import dans log_imports"""
    try:
        conn = get_connection(); cur = conn.cursor()
        statut = "succès" if nb_erreurs == 0 else "erreur"
        message = f"{nb_inseres} insérés, {nb_maj} mis à jour, {nb_erreurs} erreurs"
        cur.execute("""
            INSERT INTO log_imports
                (fichier_nom, ufr, semestre, annee_academique,
                 nb_etudiants, nb_resultats, statut, message)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (fichier_nom, ufr, semestre, annee,
              nb_inseres+nb_maj, nb_inseres+nb_maj, statut, 
              f"[{nom_user} / {email}] {message}"))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"Erreur log_import : {e}")

def lister_imports() -> list:
    """Retourne l'historique des imports pour l'admin"""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT id, fichier_nom, ufr, semestre, annee_academique,
                   nb_etudiants, statut, message, importe_le
            FROM log_imports
            ORDER BY importe_le DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [{"id":r[0],"fichier":r[1],"ufr":r[2],"semestre":r[3],
                 "annee":r[4],"nb":r[5],"statut":r[6],
                 "message":r[7],"date":str(r[8])[:16] if r[8] else ""} for r in rows]
    except Exception as e:
        print(f"Erreur lister_imports : {e}"); return []

# ── Log exports ──────────────────────────────────────────────
def log_export(email, nom_user, role, onglet, filtres_str, type_export="PDF"):
    """Enregistre un export dans log_exports"""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_exports
                (utilisateur, email, role, onglet, type_export, filtres)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (nom_user, email, role, onglet, type_export, filtres_str))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"Erreur log_export : {e}")

def lister_exports() -> list:
    """Retourne l'historique des exports pour l'admin"""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT id, utilisateur, email, role, onglet, type_export, filtres, exporte_le
            FROM log_exports
            ORDER BY exporte_le DESC
            LIMIT 100
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [{"id":r[0],"utilisateur":r[1],"email":r[2],"role":r[3],
                 "onglet":r[4],"type":r[5],"filtres":r[6],
                 "date":str(r[7])[:16] if r[7] else ""} for r in rows]
    except Exception as e:
        print(f"Erreur lister_exports : {e}"); return []

def lister_mes_imports(email) -> list:
    """Imports d'un responsable spécifique"""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT fichier_nom, ufr, semestre, annee_academique,
                   nb_etudiants, statut, importe_le
            FROM log_imports
            WHERE message LIKE %s
            ORDER BY importe_le DESC LIMIT 20
        """, (f"%{email}%",))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [{"fichier":r[0],"ufr":r[1],"semestre":r[2],"annee":r[3],
                 "nb":r[4],"statut":r[5],"date":str(r[6])[:16] if r[6] else ""} for r in rows]
    except Exception as e:
        print(f"Erreur lister_mes_imports : {e}"); return []
