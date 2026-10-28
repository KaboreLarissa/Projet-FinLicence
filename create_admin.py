"""
create_admin.py
Cree le premier compte administrateur dans uts_dashboard_v2
A executer UNE SEULE FOIS depuis la racine du projet :
    python create_admin.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from auth.auth import creer_utilisateur

print("=" * 45)
print("CREATION DU COMPTE ADMINISTRATEUR")
print("=" * 45)
print()

nom     = input("Nom       : ").strip() or "Admin"
prenom  = input("Prenom    : ").strip() or "UTS"
email   = input("Email     : ").strip() or "admin@uts.bf"
password= input("Mot de passe : ").strip() or "Admin@UTS2024"

print()
result = creer_utilisateur(nom, prenom, email, password, role="admin", ufr=None)

if result["ok"]:
    print(f"Compte admin cree avec succes (id={result['id']})")
    print(f"  Email    : {email}")
    print(f"  Role     : admin (acces complet)")
    print(f"  UFR      : Toutes UFR")
    print()
    print("Vous pouvez maintenant vous connecter au dashboard.")
else:
    print(f"Erreur : {result['message']}")
