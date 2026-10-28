"""
Lance ce script UNE SEULE FOIS pour créer les tables et l'utilisateur admin.
  python db/init_db.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import bcrypt
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_tables():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print("✅ Tables créées avec succès.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur création tables : {e}")
        raise
    finally:
        cur.close()
        conn.close()


def create_admin_user(username="admin", password="admin2025"):
    hash_pw = hash_password(password)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO utilisateurs (username, password_hash, profil)
            VALUES (%s, %s, 'admin')
            ON CONFLICT (username) DO NOTHING
        """, (username, hash_pw))
        conn.commit()
        print(f"✅ Utilisateur admin créé : {username} / {password}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur création admin : {e}")
    finally:
        cur.close()
        conn.close()


def create_responsable_user(username="responsable", password="resp2025"):
    hash_pw = hash_password(password)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO utilisateurs (username, password_hash, profil)
            VALUES (%s, %s, 'responsable')
            ON CONFLICT (username) DO NOTHING
        """, (username, hash_pw))
        conn.commit()
        print(f"✅ Utilisateur responsable créé : {username} / {password}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur création responsable : {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("=== Initialisation de la base de données ===")
    print(f"Connexion à : {DB_NAME} sur {DB_HOST}:{DB_PORT}")
    create_tables()
    create_admin_user()
    create_responsable_user()
    print("\n=== Initialisation terminée ===")
    print("Tu peux maintenant lancer le pipeline ETL.")
