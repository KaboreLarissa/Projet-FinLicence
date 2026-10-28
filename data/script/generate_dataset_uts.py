"""
Dataset UTS complet — 35 000 étudiants — 3 UFR — Version finale propre
UFR/ST  : MPCI, HYDRO, LIME-LISE + 6 sous-filières L3
UFR/SEG : ECO-GES tronc commun + 5 options L3 Economie/Gestion
UFR/SJP : Droit tronc commun + Droit privé, Droit public, Sciences Po, Admin publique

Règles sur les valeurs manquantes :
  - moyenne_generale = None UNIQUEMENT si statut = "Défaillant" (absent à tous les examens)
  - rang_promo = None si défaillant ou si données pas encore dispo (futur)
  - mention = None si ajourné ou défaillant
  - Tout le reste est toujours renseigné
"""
import random, csv, os, statistics
from collections import defaultdict
random.seed(2024)

# ── Noms & prénoms Burkinabè ──────────────────────────────────────────────────
NOMS = ["OUEDRAOGO","SAWADOGO","KABORE","TRAORE","DIALLO","OUATTARA","ZONGO","SANOU",
"SAVADOGO","COMPAORE","NIKIEMA","BARRY","SOME","ILBOUDO","COULIBALY","KONATE","BELEM",
"MAIGA","YAMEOGO","SANKARA","ZOUNGRANA","LOMPO","TAPSOBA","LANKOANDE","HIEN","KABRE",
"TIENDREBEOGO","SIDIBE","KAFANDO","BAMOGO","DAO","TANKOANO","CISSE","KONE","BONKOUNGOU",
"SANFO","DRABO","PODA","PALE","OUOBA","SOUDRE","GUIGMA","NIGNAN","ZOUNDI","BANDAOGO",
"KAMBIRE","BAZIE","BICABA","DAKUYO","SERE","NANA","TALL","BADO","BANDE","KOANDA",
"KAMBOU","SONDE","PARE","ZIDA","RABO","BATIONO","NACOULMA","TOUGMA","BAGUIAN","DIOP",
"SALL","TOURE","COULIBALY","DEMBELE","SANGARE","FOFANA","BERTE","KONE","BAMBA"]
POIDS = [168,102,50,37,35,29,23,21,20,19,18,17,17,16,13,12,12,12,11,11,10,10,10,10,
         8,8,8,7,7,7,7,7,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,4,4,4,4,4,4,4,4,
         4,4,4,4,4,4,3,3,3,3,3,3,3,3,3,3]
POIDS = POIDS[:len(NOMS)]

PRENOMS_M = ["Ibrahim","Moussa","Abdoulaye","Issouf","Hamidou","Seydou","Oumar","Ali",
"Boukary","Adama","Souleymane","Lassina","Inoussa","Dramane","Youssouf","Cheick",
"Aboubacar","Mahamadou","Wendyam","Romuald","Valentin","Evariste","Jean-Baptiste",
"Désiré","Arsène","Théophile","Celestin","Honoré","Pascal","Wendkouni","Rasmane",
"Idrissa","Brice","Rodrigue","Sidiki","Noel","Edouard","Gustave","Frederic","Sylvain",
"Emmanuel","Christian","Martial","Daouda","Salif","Mamadou","Boubacar","Issa","Tahirou",
"Alassane","Arnaud","Joachim","Théodore","Patrice","Serge","Juste","Simplice",
"Moustapha","Bakary","Yaya","Luc","Augustin","Narcisse","Cyprien","Alexis","Mathieu"]

PRENOMS_F = ["Mariam","Fatimata","Aminata","Rasmata","Aissata","Maimouna","Salamata",
"Fatoumata","Bintou","Coumba","Roukiatou","Kadiatou","Assiatou","Rokia","Sandrine",
"Marie","Christine","Monique","Josephine","Adèle","Sylvie","Martine","Clarisse",
"Véronique","Cécile","Angèle","Brigitte","Hélène","Wendyamita","Korotimi","Djeneba",
"Safi","Hawa","Tenin","Nafi","Germaine","Léonie","Pauline","Bernadette","Alice",
"Suzanne","Isabelle","Nadège","Chantal","Florence","Laure","Jeanne","Odile","Victorine",
"Marcelline","Pascaline","Clémentine","Delphine","Régine","Lucie","Antoinette","Thérèse"]

def g_nom(): return random.choices(NOMS, weights=POIDS, k=1)[0]
def g_prenom(g): return random.choice(PRENOMS_M if g=="M" else PRENOMS_F)
def clamp(v,lo,hi): return max(lo,min(hi,v))
def mention(m):
    if m>=16: return "Très bien"
    if m>=14: return "Bien"
    if m>=12: return "Assez bien"
    if m>=10: return "Passable"
    return "Insuffisant"
def annee_acad(ae,sem):
    n=int(sem[1]); y=ae+(n-1)//2; return f"{y}-{y+1}"

# ── Structure des 3 UFR ───────────────────────────────────────────────────────
# Chaque UFR : tronc commun L1-L2, puis spécialisations L3
# Taille cible : ST~8000, SEG~18000, SJP~9000 (proportionnel aux vrais chiffres UTS)
# UFR/SEG = 6612 étudiants (chiffres officiels site UTS), ratio F=1866/6612=28%
# On scale pour avoir ~35000 total sur 6 cohortes

UFRS = {
    "ST": {
        "nom": "Sciences et Technologies",
        "poids_uts": 0.23,  # ~8000 sur 35000
        "filieres_l1l2": [
            {"code":"MPCI","nom":"Mathématiques, Physique, Chimie, Informatique","ratio_F":0.28,"poids":0.60},
            {"code":"HYDRO","nom":"Hydrologie","ratio_F":0.35,"poids":0.25},
            {"code":"LIME_LISE","nom":"Licence Méthodes & Sciences de l'Eau","ratio_F":0.38,"poids":0.15},
        ],
        "split_l3": {
            "MPCI":  {"MATH_L3":0.20,"PHYS_L3":0.20,"INFO_L3":0.30,"CHIM_L3":0.30},
            "HYDRO": {"HYDRO_L3":1.0},
            "LIME_LISE": {"LISE_L3":1.0},
        },
    },
    "SEG": {
        "nom": "Sciences Économiques et Gestion",
        "poids_uts": 0.51,  # ~18000 sur 35000
        "filieres_l1l2": [
            {"code":"ECO_GES","nom":"Économie et Gestion (tronc commun)","ratio_F":0.28,"poids":1.0},
        ],
        "split_l3": {
            "ECO_GES": {
                "L3_EEDD":0.20,"L3_EASA":0.20,"L3_MGD":0.20,
                "L3_EGEO":0.20,"L3_SG":0.20,
            },
        },
    },
    "SJP": {
        "nom": "Sciences Juridiques et Politiques",
        "poids_uts": 0.26,  # ~9000 sur 35000
        "filieres_l1l2": [
            {"code":"DROIT","nom":"Droit (tronc commun L1-L2)","ratio_F":0.45,"poids":1.0},
        ],
        "split_l3": {
            "DROIT": {
                "L3_DROIT_PRIVE":0.35,"L3_DROIT_PUBLIC":0.30,
                "L3_SCI_PO":0.20,"L3_ADMIN_PUB":0.15,
            },
        },
    },
}

# Descriptions filières L3 pour dim_filiere
FILIERES_L3_INFO = {
    # ST
    "MATH_L3":   {"nom":"Mathématiques L3","parent":"MPCI","ufr":"ST","ratio_F":0.30},
    "PHYS_L3":   {"nom":"Physique L3","parent":"MPCI","ufr":"ST","ratio_F":0.26},
    "INFO_L3":   {"nom":"Informatique L3","parent":"MPCI","ufr":"ST","ratio_F":0.24},
    "CHIM_L3":   {"nom":"Chimie L3","parent":"MPCI","ufr":"ST","ratio_F":0.42},
    "HYDRO_L3":  {"nom":"Hydrologie L3","parent":"HYDRO","ufr":"ST","ratio_F":0.35},
    "LISE_L3":   {"nom":"LIME-LISE L3","parent":"LIME_LISE","ufr":"ST","ratio_F":0.38},
    # SEG
    "L3_EEDD":  {"nom":"Économie Environnement & Dév. Durable","parent":"ECO_GES","ufr":"SEG","ratio_F":0.35},
    "L3_EASA":  {"nom":"Économie Agricole & Sécurité Alimentaire","parent":"ECO_GES","ufr":"SEG","ratio_F":0.30},
    "L3_MGD":   {"nom":"Macroéconomie & Gestion du Développement","parent":"ECO_GES","ufr":"SEG","ratio_F":0.28},
    "L3_EGEO":  {"nom":"Économie & Gestion des Entreprises","parent":"ECO_GES","ufr":"SEG","ratio_F":0.27},
    "L3_SG":    {"nom":"Licence Professionnelle Sciences de Gestion","parent":"ECO_GES","ufr":"SEG","ratio_F":0.30},
    # SJP
    "L3_DROIT_PRIVE":  {"nom":"Droit Privé L3","parent":"DROIT","ufr":"SJP","ratio_F":0.48},
    "L3_DROIT_PUBLIC": {"nom":"Droit Public L3","parent":"DROIT","ufr":"SJP","ratio_F":0.42},
    "L3_SCI_PO":       {"nom":"Sciences Politiques L3","parent":"DROIT","ufr":"SJP","ratio_F":0.40},
    "L3_ADMIN_PUB":    {"nom":"Administration Publique L3","parent":"DROIT","ufr":"SJP","ratio_F":0.38},
}

# ── Modules par filière et semestre ──────────────────────────────────────────
MODULES = {
    # ─── UFR/ST — MPCI ───────────────────────────────────────────────────────
    ("MPCI","S1"):[("Analyse 1",3,"Mathématiques"),("Algèbre 1",3,"Mathématiques"),
        ("Mécanique classique",3,"Physique"),("Chimie générale",3,"Chimie"),
        ("Informatique 1",2,"Informatique"),("Anglais 1",1,"Langues"),("Méthodes de travail",1,"Transversal")],
    ("MPCI","S2"):[("Analyse 2",3,"Mathématiques"),("Algèbre 2",3,"Mathématiques"),
        ("Électricité",3,"Physique"),("Chimie organique",3,"Chimie"),
        ("Algorithmique",2,"Informatique"),("Anglais 2",1,"Langues"),("Environnement",1,"Transversal")],
    ("MPCI","S3"):[("Analyse 3",3,"Mathématiques"),("Algèbre linéaire",3,"Mathématiques"),
        ("Optique",3,"Physique"),("Chimie analytique",3,"Chimie"),
        ("Programmation C",2,"Informatique"),("Probabilités",2,"Mathématiques")],
    ("MPCI","S4"):[("Topologie",3,"Mathématiques"),("Thermodynamique",3,"Physique"),
        ("Électromagnétisme",3,"Physique"),("Chimie minérale",3,"Chimie"),
        ("Bases de données",2,"Informatique"),("Statistiques",2,"Mathématiques")],
    ("MATH_L3","S5"):[("Analyse réelle",4,"Mathématiques"),("Algèbre abstraite",4,"Mathématiques"),
        ("Topologie avancée",3,"Mathématiques"),("Équations différentielles",3,"Mathématiques"),("Anglais scientifique",2,"Langues")],
    ("MATH_L3","S6"):[("Analyse complexe",4,"Mathématiques"),("Géométrie différentielle",4,"Mathématiques"),
        ("Probabilités avancées",3,"Mathématiques"),("Mémoire & stage",5,"Projet")],
    ("PHYS_L3","S5"):[("Mécanique quantique",4,"Physique"),("Physique nucléaire",3,"Physique"),
        ("Électronique",3,"Physique"),("Matière condensée",3,"Physique"),("Anglais scientifique",2,"Langues")],
    ("PHYS_L3","S6"):[("Physique statistique",4,"Physique"),("Astrophysique",3,"Physique"),
        ("TP Physique avancés",3,"Physique"),("Mémoire & stage",5,"Projet")],
    ("INFO_L3","S5"):[("Réseaux informatiques",4,"Informatique"),("Systèmes d'exploitation",3,"Informatique"),
        ("Génie logiciel",3,"Informatique"),("IA & Machine Learning",3,"Informatique"),("Anglais technique",2,"Langues")],
    ("INFO_L3","S6"):[("Sécurité informatique",4,"Informatique"),("Développement web",3,"Informatique"),
        ("Projet informatique",3,"Informatique"),("Mémoire & stage",5,"Projet")],
    ("CHIM_L3","S5"):[("Chimie organique avancée",4,"Chimie"),("Chimie analytique avancée",3,"Chimie"),
        ("Spectroscopie",3,"Chimie"),("Chimie de l'environnement",3,"Chimie"),("Anglais scientifique",2,"Langues")],
    ("CHIM_L3","S6"):[("Chimie industrielle",4,"Chimie"),("Biochimie",3,"Chimie"),
        ("TP Chimie avancés",3,"Chimie"),("Mémoire & stage",5,"Projet")],
    # ─── UFR/ST — HYDRO ──────────────────────────────────────────────────────
    ("HYDRO","S1"):[("Hydraulique générale",3,"Hydrologie"),("Mathématiques appliquées",3,"Mathématiques"),
        ("Géologie 1",3,"Géosciences"),("Météorologie",3,"Géosciences"),
        ("Informatique de base",2,"Informatique"),("Anglais 1",1,"Langues"),("Géographie physique",1,"Géosciences")],
    ("HYDRO","S2"):[("Hydrologie de surface",3,"Hydrologie"),("Hydrogéologie",3,"Hydrologie"),
        ("Chimie des eaux",3,"Chimie"),("Statistiques hydrologiques",3,"Mathématiques"),
        ("SIG notions de base",2,"Informatique"),("Anglais 2",1,"Langues")],
    ("HYDRO","S3"):[("Hydraulique souterraine",4,"Hydrologie"),("Qualité des eaux",3,"Hydrologie"),
        ("Géochimie",3,"Géosciences"),("Modélisation hydrologique",3,"Mathématiques"),("SIG avancé",3,"Informatique")],
    ("HYDRO","S4"):[("Gestion des bassins versants",4,"Hydrologie"),("Irrigation & drainage",3,"Hydrologie"),
        ("Droit de l'eau",2,"Sciences humaines"),("Traitement des eaux",3,"Chimie"),("Cartographie",3,"Géosciences")],
    ("HYDRO_L3","S5"):[("Hydrologie avancée",4,"Hydrologie"),("Gestion des ressources en eau",4,"Hydrologie"),
        ("Changement climatique",3,"Géosciences"),("Modélisation numérique",3,"Mathématiques"),("Anglais technique",2,"Langues")],
    ("HYDRO_L3","S6"):[("Aménagement hydraulique",4,"Hydrologie"),("Eau et développement",3,"Sciences humaines"),
        ("TP terrain",3,"Hydrologie"),("Mémoire & stage",5,"Projet")],
    # ─── UFR/ST — LIME-LISE ──────────────────────────────────────────────────
    ("LIME_LISE","S1"):[("Mathématiques 1",3,"Mathématiques"),("Physique appliquée",3,"Physique"),
        ("Chimie de l'eau",3,"Chimie"),("Sciences de l'environnement",3,"Environnement"),
        ("Informatique 1",2,"Informatique"),("Anglais 1",1,"Langues"),("Biologie générale",1,"Biologie")],
    ("LIME_LISE","S2"):[("Mathématiques 2",3,"Mathématiques"),("Thermodynamique",3,"Physique"),
        ("Chimie analytique",3,"Chimie"),("Écologie",3,"Environnement"),
        ("Biostatistiques",2,"Mathématiques"),("Anglais 2",1,"Langues")],
    ("LIME_LISE","S3"):[("Physique des matériaux",3,"Physique"),("Chimie de l'environnement",3,"Chimie"),
        ("Biologie moléculaire",3,"Biologie"),("Géologie environnementale",3,"Géosciences"),("Traitement des déchets",3,"Environnement")],
    ("LIME_LISE","S4"):[("Énergies renouvelables",4,"Environnement"),("Évaluation environnementale",3,"Environnement"),
        ("Microbiologie",3,"Biologie"),("Droit de l'environnement",2,"Sciences humaines"),("Modélisation",3,"Mathématiques")],
    ("LISE_L3","S5"):[("Pollution & risques environnementaux",4,"Environnement"),("Méthodes analytiques",3,"Chimie"),
        ("Écotoxicologie",3,"Biologie"),("Gestion de projets environnementaux",3,"Sciences humaines"),("Anglais scientifique",2,"Langues")],
    ("LISE_L3","S6"):[("Audit environnemental",4,"Environnement"),("Métrologie & normes",3,"Chimie"),
        ("Étude d'impact environnemental",3,"Environnement"),("Mémoire & stage",5,"Projet")],
    # ─── UFR/SEG ─────────────────────────────────────────────────────────────
    ("ECO_GES","S1"):[("Microéconomie 1",3,"Économie"),("Comptabilité générale",3,"Gestion"),
        ("Mathématiques pour l'économie",3,"Mathématiques"),("Droit des obligations",2,"Droit"),
        ("Anglais des affaires 1",2,"Langues"),("Introduction aux sciences sociales",2,"Sciences sociales"),("Méthodes de travail",1,"Transversal")],
    ("ECO_GES","S2"):[("Microéconomie 2",3,"Économie"),("Macroéconomie 1",3,"Économie"),
        ("Comptabilité analytique",3,"Gestion"),("Statistiques descriptives",3,"Mathématiques"),
        ("Droit commercial",2,"Droit"),("Anglais des affaires 2",2,"Langues")],
    ("ECO_GES","S3"):[("Macroéconomie 2",3,"Économie"),("Finance d'entreprise",3,"Gestion"),
        ("Économétrie 1",3,"Mathématiques"),("Droit du travail",2,"Droit"),
        ("Marketing fondamental",3,"Gestion"),("Statistiques inférentielles",2,"Mathématiques")],
    ("ECO_GES","S4"):[("Économie internationale",3,"Économie"),("Fiscalité",3,"Gestion"),
        ("Économétrie 2",3,"Mathématiques"),("Gestion des ressources humaines",3,"Gestion"),
        ("Droit fiscal",2,"Droit"),("Informatique de gestion",2,"Informatique")],
    ("L3_EEDD","S5"):[("Économie de l'environnement",4,"Économie"),("Développement durable",4,"Économie"),
        ("Politique climatique",3,"Sciences sociales"),("Évaluation de projets",3,"Gestion"),("Anglais 3",2,"Langues")],
    ("L3_EEDD","S6"):[("Financement vert",4,"Économie"),("Gouvernance environnementale",3,"Sciences sociales"),
        ("Comptabilité environnementale",3,"Gestion"),("Mémoire & stage",5,"Projet")],
    ("L3_EASA","S5"):[("Économie agricole",4,"Économie"),("Sécurité alimentaire",4,"Économie"),
        ("Politiques agricoles",3,"Sciences sociales"),("Analyse de filières",3,"Gestion"),("Anglais 3",2,"Langues")],
    ("L3_EASA","S6"):[("Microfinance rurale",4,"Économie"),("Développement rural",3,"Sciences sociales"),
        ("Gestion de projet agricole",3,"Gestion"),("Mémoire & stage",5,"Projet")],
    ("L3_MGD","S5"):[("Macroéconomie avancée",4,"Économie"),("Politiques de développement",4,"Économie"),
        ("Finances internationales",3,"Gestion"),("Économétrie appliquée",3,"Mathématiques"),("Anglais 3",2,"Langues")],
    ("L3_MGD","S6"):[("Économie monétaire",4,"Économie"),("Gestion du développement",3,"Sciences sociales"),
        ("Analyse de politiques",3,"Économie"),("Mémoire & stage",5,"Projet")],
    ("L3_EGEO","S5"):[("Stratégie d'entreprise",4,"Gestion"),("Finance avancée",4,"Gestion"),
        ("Management des organisations",3,"Gestion"),("Marketing stratégique",3,"Gestion"),("Anglais des affaires 3",2,"Langues")],
    ("L3_EGEO","S6"):[("Gestion de projet",4,"Gestion"),("Contrôle de gestion",3,"Gestion"),
        ("Entrepreneuriat",3,"Gestion"),("Mémoire & stage",5,"Projet")],
    ("L3_SG","S5"):[("Comptabilité avancée",4,"Gestion"),("Audit et contrôle",4,"Gestion"),
        ("Systèmes d'information",3,"Informatique"),("Fiscalité avancée",3,"Droit"),("Anglais 3",2,"Langues")],
    ("L3_SG","S6"):[("Consolidation des comptes",4,"Gestion"),("Finance islamique",3,"Gestion"),
        ("Gestion de trésorerie",3,"Gestion"),("Mémoire & stage",5,"Projet")],
    # ─── UFR/SJP ─────────────────────────────────────────────────────────────
    ("DROIT","S1"):[("Introduction au droit",3,"Droit"),("Histoire du droit",3,"Droit"),
        ("Droit constitutionnel 1",3,"Droit public"),("Science politique",3,"Sciences politiques"),
        ("Sociologie générale",2,"Sciences sociales"),("Anglais juridique 1",2,"Langues")],
    ("DROIT","S2"):[("Droit civil 1 (personnes & famille)",3,"Droit privé"),("Droit administratif 1",3,"Droit public"),
        ("Droit constitutionnel 2",3,"Droit public"),("Institutions politiques",3,"Sciences politiques"),
        ("Économie politique",2,"Économie"),("Anglais juridique 2",2,"Langues")],
    ("DROIT","S3"):[("Droit civil 2 (obligations)",3,"Droit privé"),("Droit administratif 2",3,"Droit public"),
        ("Droit pénal général",3,"Droit privé"),("Relations internationales",3,"Sciences politiques"),
        ("Procédure civile",2,"Droit privé"),("Financements publics",2,"Droit public")],
    ("DROIT","S4"):[("Droit des contrats",3,"Droit privé"),("Droit de la fonction publique",3,"Droit public"),
        ("Droit pénal spécial",3,"Droit privé"),("Droit international public",3,"Droit public"),
        ("Droit du travail",2,"Droit privé"),("Libertés publiques",2,"Droit public")],
    ("L3_DROIT_PRIVE","S5"):[("Droit des sociétés",4,"Droit privé"),("Droit de la famille avancé",4,"Droit privé"),
        ("Procédure pénale",3,"Droit privé"),("Droit des affaires",3,"Droit privé"),("Anglais juridique 3",2,"Langues")],
    ("L3_DROIT_PRIVE","S6"):[("Droit commercial avancé",4,"Droit privé"),("Droit de la propriété intellectuelle",3,"Droit privé"),
        ("Droit de l'arbitrage",3,"Droit privé"),("Mémoire & stage",5,"Projet")],
    ("L3_DROIT_PUBLIC","S5"):[("Droit administratif avancé",4,"Droit public"),("Droit des collectivités",4,"Droit public"),
        ("Droit international humanitaire",3,"Droit public"),("Contentieux administratif",3,"Droit public"),("Anglais juridique 3",2,"Langues")],
    ("L3_DROIT_PUBLIC","S6"):[("Droit des marchés publics",4,"Droit public"),("Droit de l'environnement",3,"Droit public"),
        ("Finances publiques avancées",3,"Droit public"),("Mémoire & stage",5,"Projet")],
    ("L3_SCI_PO","S5"):[("Théories politiques",4,"Sciences politiques"),("Sociologie politique",4,"Sciences politiques"),
        ("Géopolitique",3,"Sciences politiques"),("Partis et systèmes politiques",3,"Sciences politiques"),("Anglais politique",2,"Langues")],
    ("L3_SCI_PO","S6"):[("Politique africaine comparée",4,"Sciences politiques"),("Communication politique",3,"Sciences politiques"),
        ("Élections et démocratie",3,"Sciences politiques"),("Mémoire & stage",5,"Projet")],
    ("L3_ADMIN_PUB","S5"):[("Management public",4,"Administration"),("Gestion budgétaire de l'État",4,"Administration"),
        ("Décentralisation",3,"Administration"),("Réforme administrative",3,"Administration"),("Anglais admin.",2,"Langues")],
    ("L3_ADMIN_PUB","S6"):[("Gouvernance et redevabilité",4,"Administration"),("Politique de développement local",3,"Administration"),
        ("Systèmes d'information publics",3,"Informatique"),("Mémoire & stage",5,"Projet")],
}

def get_mod(code,sem):
    k=(code,sem)
    if k in MODULES: return MODULES[k]
    # fallback
    for parent_key in [(c,sem) for c in ["MPCI","HYDRO","LIME_LISE","ECO_GES","DROIT"]]:
        if parent_key in MODULES: return MODULES[parent_key]
    return [("Module",3,"Général")]

# ── Paramètres de simulation calibrés ────────────────────────────────────────
# Sciences exactes (ST) : plus difficile, taux réussite plus bas
# SEG/SJP : un peu plus élevé (nature des matières, courbe de réussite différente)
# Sources : MESRI BF, Cornet 2024, UNESCO 2023

PARAMS = {
    "ST":  {"L1":(9.8,2.8,2.8,-0.35),"L2":(10.4,2.5,2.2,-0.10),"L3":(11.0,2.3,1.8,0.20)},
    "SEG": {"L1":(10.4,2.6,2.5,-0.20),"L2":(11.0,2.4,2.0,-0.05),"L3":(11.8,2.2,1.6,0.15)},
    "SJP": {"L1":(10.2,2.7,2.6,-0.20),"L2":(10.8,2.5,2.1,-0.05),"L3":(11.5,2.3,1.7,0.15)},
}
# mu, sigma_mod, sigma_talent, mu_diff_F

TAUX_DEF = {"ST":{"L1":0.11,"L2":0.07,"L3":0.04},"SEG":{"L1":0.09,"L2":0.05,"L3":0.03},"SJP":{"L1":0.10,"L2":0.06,"L3":0.03}}
TAUX_ABANDON = {
    "ST":  {"L1_L2":{"M":0.30,"F":0.38},"L2_L3":{"M":0.18,"F":0.24}},
    "SEG": {"L1_L2":{"M":0.25,"F":0.32},"L2_L3":{"M":0.15,"F":0.20}},
    "SJP": {"L1_L2":{"M":0.22,"F":0.28},"L2_L3":{"M":0.12,"F":0.18}},
}
MALUS_DIFF = {"ST":{"L1":-1.2,"L2":-0.5,"L3":0.0},"SEG":{"L1":-0.5,"L2":-0.2,"L3":0.0},"SJP":{"L1":-0.5,"L2":-0.2,"L3":0.0}}
GROUPES_DURS = {"ST":["Mathématiques","Physique"],"SEG":["Mathématiques","Économie"],"SJP":["Droit privé","Droit public"]}

# ── Génération ────────────────────────────────────────────────────────────────
records_r = []
records_ue = []
etudiants_db = {}
idx_e = 1
idx_r = 1

# Taille cohortes pour atteindre ~35000 étudiants total sur 6 ans
# 35000 / 6 ≈ 5833/an, croissance 5%/an
# Base 2019 ≈ 4600/an * facteur UFR
BASE_ANNEE = {2019:4600,2020:4800,2021:5050,2022:5300,2023:5550,2024:5800}

print("Génération dataset UTS — 3 UFR — 35 000 étudiants")
print("="*55)

for annee_entree in range(2019,2025):
    n_total_annee = BASE_ANNEE[annee_entree]
    print(f"Cohorte {annee_entree} : {n_total_annee} étudiants L1")

    for ufr_code, ufr_info in UFRS.items():
        n_ufr = int(n_total_annee * ufr_info["poids_uts"])
        params_ufr = PARAMS[ufr_code]
        taux_def = TAUX_DEF[ufr_code]
        taux_ab = TAUX_ABANDON[ufr_code]
        malus_d = MALUS_DIFF[ufr_code]
        grp_durs = GROUPES_DURS[ufr_code]

        for _ in range(n_ufr):
            # Choisir filière L1
            fls = ufr_info["filieres_l1l2"]
            poids_fl = [f["poids"] for f in fls]
            fl_obj = random.choices(fls, weights=poids_fl, k=1)[0]
            filiere_l1 = fl_obj["code"]
            ratio_f = fl_obj["ratio_F"]

            genre = "F" if random.random() < ratio_f else "M"
            mat = f"UTS{str(annee_entree)[-2:]}{idx_e:05d}"
            age = random.choices([18,18,19,19,19,20,20,21,22,23],k=1)[0]

            etudiants_db[mat] = {
                "matricule":mat, "nom":g_nom(), "prenom":g_prenom(genre),
                "genre":genre, "age_entree":age, "annee_entree":annee_entree,
                "filiere_initiale":filiere_l1, "ufr":ufr_code,
            }

            talent = random.gauss(0, 1.0)
            filiere_cur = filiere_l1
            actif = True

            for niveau, sems in [("L1",["S1","S2"]),("L2",["S3","S4"]),("L3",["S5","S6"])]:
                if not actif: break
                if niveau == "L2" and random.random() < taux_ab["L1_L2"][genre]:
                    actif = False; break
                if niveau == "L3":
                    if random.random() < taux_ab["L2_L3"][genre]:
                        actif = False; break
                    # Choisir sous-filière L3
                    split = ufr_info["split_l3"].get(filiere_l1, {filiere_l1+"_L3":1.0})
                    rng2 = random.random(); c2 = 0
                    for code_l3, p in split.items():
                        c2 += p
                        if rng2 < c2: filiere_cur = code_l3; break

                mu_b, sig_m, sig_t, mu_df = params_ufr[niveau]
                mu_g = mu_b + (mu_df if genre == "F" else 0)
                mu_ind = clamp(mu_g + talent * sig_t * 0.5, mu_b - 4.0, mu_b + 5.0)

                for sem in sems:
                    acad = annee_acad(annee_entree, sem)
                    if int(acad.split("-")[0]) > 2024: break

                    # ── Défaillance ──
                    if random.random() < taux_def[niveau]:
                        records_r.append({
                            "id_resultat":idx_r, "matricule":mat, "ufr":ufr_code,
                            "filiere_code":filiere_cur, "niveau":niveau, "semestre":sem,
                            "annee_academique":acad, "session":"Normale",
                            "moyenne_generale":"", "total_points":"",
                            "nb_ue_validees":0, "nb_ue_echouees":0,
                            "statut":"Défaillant", "mention":"", "rang_promo":"",
                        })
                        idx_r += 1
                        continue

                    mods = get_mod(filiere_cur, sem)
                    notes_m = []; tot_p = 0; tot_c = 0; uv = 0; ue_f = 0
                    malus = malus_d[niveau]

                    for (nm, cred, grp) in mods:
                        m_grp = malus if grp in grp_durs else 0
                        n = clamp(random.gauss(mu_ind + m_grp, sig_m), 0.5, 19.5)
                        n = round(n, 2)
                        notes_m.append((nm, cred, grp, n))
                        tot_p += n * cred; tot_c += cred
                        if n >= 10: uv += 1
                        else: ue_f += 1

                    moy = round(tot_p / tot_c, 2) if tot_c > 0 else 0
                    stat_n = "Admis" if moy >= 10 else "Ajourné"
                    men_n = mention(moy) if stat_n == "Admis" else ""

                    records_r.append({
                        "id_resultat":idx_r, "matricule":mat, "ufr":ufr_code,
                        "filiere_code":filiere_cur, "niveau":niveau, "semestre":sem,
                        "annee_academique":acad, "session":"Normale",
                        "moyenne_generale":moy, "total_points":round(tot_p,2),
                        "nb_ue_validees":uv, "nb_ue_echouees":ue_f,
                        "statut":stat_n, "mention":men_n, "rang_promo":"",
                    })
                    for (nm, cred, grp, nt) in notes_m:
                        records_ue.append({
                            "id_resultat":idx_r, "matricule":mat, "ufr":ufr_code,
                            "filiere_code":filiere_cur, "niveau":niveau, "semestre":sem,
                            "annee_academique":acad, "session":"Normale",
                            "nom_ue":nm, "groupe_ue":grp, "note":nt, "credits":cred,
                        })
                    idx_r += 1

                    # ── Rattrapage si ajourné ──
                    if stat_n == "Ajourné":
                        notes_r2 = []; tp_r = 0; tc_r = 0; uv_r = 0; ue_r = 0
                        for (nm, cred, grp, no) in notes_m:
                            nr = clamp(no + random.uniform(0.3, 4.0), 0.5, 18.5) if no < 10 else no
                            nr = round(nr, 2)
                            notes_r2.append((nm, cred, grp, nr))
                            tp_r += nr * cred; tc_r += cred
                            if nr >= 10: uv_r += 1
                            else: ue_r += 1

                        moy_r = round(tp_r / tc_r, 2) if tc_r > 0 else 0
                        stat_r = "Admis" if moy_r >= 10 else "Ajourné"
                        if 8.5 <= moy_r < 10 and random.random() < 0.35: stat_r = "Admis"
                        men_r = mention(moy_r) if stat_r == "Admis" else ""

                        records_r.append({
                            "id_resultat":idx_r, "matricule":mat, "ufr":ufr_code,
                            "filiere_code":filiere_cur, "niveau":niveau, "semestre":sem,
                            "annee_academique":acad, "session":"Rattrapage",
                            "moyenne_generale":moy_r, "total_points":round(tp_r,2),
                            "nb_ue_validees":uv_r, "nb_ue_echouees":ue_r,
                            "statut":stat_r, "mention":men_r, "rang_promo":"",
                        })
                        for (nm, cred, grp, nr) in notes_r2:
                            records_ue.append({
                                "id_resultat":idx_r, "matricule":mat, "ufr":ufr_code,
                                "filiere_code":filiere_cur, "niveau":niveau, "semestre":sem,
                                "annee_academique":acad, "session":"Rattrapage",
                                "nom_ue":nm, "groupe_ue":grp, "note":nr, "credits":cred,
                            })
                        idx_r += 1
            idx_e += 1

print(f"\n✅ Étudiants : {len(etudiants_db):,}")
print(f"✅ Résultats : {len(records_r):,}")
print(f"✅ Notes UE  : {len(records_ue):,}")

# ── Calcul des rangs ──────────────────────────────────────────────────────────
print("Calcul des rangs...")
grps = defaultdict(list)
for r in records_r:
    if r["moyenne_generale"] != "" and r["statut"] not in ("Défaillant",""):
        k = (r["filiere_code"], r["semestre"], r["session"], r["annee_academique"])
        grps[k].append(r)
for grp_list in grps.values():
    for rang, rec in enumerate(sorted(grp_list, key=lambda x: float(x["moyenne_generale"]), reverse=True), 1):
        rec["rang_promo"] = rang
print("✅ Rangs calculés")

# ── Export CSV ────────────────────────────────────────────────────────────────
os.makedirs("/home/claude/dataset_35k", exist_ok=True)

# 1. dim_etudiant
with open("/home/claude/dataset_35k/dim_etudiant.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["matricule","nom","prenom","genre","age_entree","annee_entree","filiere_initiale","ufr"])
    w.writeheader(); w.writerows(etudiants_db.values())

# 2. fact_resultats
CHAMPS_R = ["id_resultat","matricule","ufr","filiere_code","niveau","semestre",
            "annee_academique","session","moyenne_generale","total_points",
            "nb_ue_validees","nb_ue_echouees","statut","mention","rang_promo"]
with open("/home/claude/dataset_35k/fact_resultats.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=CHAMPS_R)
    w.writeheader(); w.writerows(records_r)

# 3. fact_notes_ue
CHAMPS_UE = ["id_resultat","matricule","ufr","filiere_code","niveau","semestre",
             "annee_academique","session","nom_ue","groupe_ue","note","credits"]
with open("/home/claude/dataset_35k/fact_notes_ue.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=CHAMPS_UE)
    w.writeheader(); w.writerows(records_ue)

# 4. dim_filiere (complète)
filieres_dim = []
# Filières troncs communs
for ufr_code, ufr_info in UFRS.items():
    for fl in ufr_info["filieres_l1l2"]:
        filieres_dim.append({"code_filiere":fl["code"],"nom_filiere":fl["nom"],
            "ufr":ufr_code,"filiere_parente":"","semestre_bifurcation":"","niveau_terminal":"L2","ratio_F":fl["ratio_F"]})
# Filières L3
for code, info in FILIERES_L3_INFO.items():
    filieres_dim.append({"code_filiere":code,"nom_filiere":info["nom"],
        "ufr":info["ufr"],"filiere_parente":info["parent"],
        "semestre_bifurcation":"S5","niveau_terminal":"L3","ratio_F":info["ratio_F"]})
with open("/home/claude/dataset_35k/dim_filiere.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["code_filiere","nom_filiere","ufr","filiere_parente","semestre_bifurcation","niveau_terminal","ratio_F"])
    w.writeheader(); w.writerows(filieres_dim)

# 5. dim_semestre
with open("/home/claude/dataset_35k/dim_semestre.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["code_semestre","numero","niveau","periode"])
    w.writeheader()
    for s,n,niv,per in [("S1",1,"L1","1er semestre"),("S2",2,"L1","2ème semestre"),
        ("S3",3,"L2","1er semestre"),("S4",4,"L2","2ème semestre"),
        ("S5",5,"L3","1er semestre"),("S6",6,"L3","2ème semestre")]:
        w.writerow({"code_semestre":s,"numero":n,"niveau":niv,"periode":per})

# 6. dim_annee_academique
with open("/home/claude/dataset_35k/dim_annee_academique.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["code_annee","annee_debut","annee_fin"])
    w.writeheader()
    for y in range(2019,2025): w.writerow({"code_annee":f"{y}-{y+1}","annee_debut":y,"annee_fin":y+1})

# 7. dim_ufr
with open("/home/claude/dataset_35k/dim_ufr.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["code_ufr","nom_ufr","nb_etudiants_ref","nb_enseignants_ref"])
    w.writeheader()
    w.writerows([
        {"code_ufr":"ST","nom_ufr":"Sciences et Technologies","nb_etudiants_ref":8000,"nb_enseignants_ref":45},
        {"code_ufr":"SEG","nom_ufr":"Sciences Économiques et Gestion","nb_etudiants_ref":18000,"nb_enseignants_ref":67},
        {"code_ufr":"SJP","nom_ufr":"Sciences Juridiques et Politiques","nb_etudiants_ref":9000,"nb_enseignants_ref":52},
    ])

# ── BONUS : fichier CSV "plat" pour consultation rapide ──────────────────────
# Jointure fact_resultats + dim_etudiant (session normale uniquement)
print("Génération du fichier plat (vue SQL)...")
et_map = {e["matricule"]:e for e in etudiants_db.values()}
champs_plat = ["matricule","nom","prenom","genre","age_entree","annee_entree",
               "ufr","filiere_initiale","filiere_code","niveau","semestre",
               "annee_academique","session","moyenne_generale","total_points",
               "nb_ue_validees","nb_ue_echouees","statut","mention","rang_promo"]
with open("/home/claude/dataset_35k/vue_complete_etudiants.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=champs_plat)
    w.writeheader()
    for r in records_r:
        e = et_map.get(r["matricule"],{})
        row = {
            "matricule":r["matricule"],"nom":e.get("nom",""),"prenom":e.get("prenom",""),
            "genre":e.get("genre",""),"age_entree":e.get("age_entree",""),
            "annee_entree":e.get("annee_entree",""),
            "ufr":r["ufr"],"filiere_initiale":e.get("filiere_initiale",""),
            "filiere_code":r["filiere_code"],"niveau":r["niveau"],"semestre":r["semestre"],
            "annee_academique":r["annee_academique"],"session":r["session"],
            "moyenne_generale":r["moyenne_generale"],"total_points":r["total_points"],
            "nb_ue_validees":r["nb_ue_validees"],"nb_ue_echouees":r["nb_ue_echouees"],
            "statut":r["statut"],"mention":r["mention"],"rang_promo":r["rang_promo"],
        }
        w.writerow(row)
print("✅ Vue complète générée")

# ── Validation statistique finale ─────────────────────────────────────────────
print("\n" + "="*60)
print("VALIDATION STATISTIQUE FINALE")
print("="*60)

genres = [e["genre"] for e in etudiants_db.values()]
nf = genres.count("F"); nm = genres.count("M")
print(f"\nGenre global : {nf:,} F ({100*nf/len(genres):.1f}%) / {nm:,} M ({100*nm/len(genres):.1f}%)")
print(f"Total étudiants : {len(etudiants_db):,}")

for ufr_c in ["ST","SEG","SJP"]:
    ets_ufr = [e for e in etudiants_db.values() if e["ufr"]==ufr_c]
    nf_u = sum(1 for e in ets_ufr if e["genre"]=="F")
    print(f"\nUFR/{ufr_c} : {len(ets_ufr):,} étudiants | {100*nf_u/len(ets_ufr):.1f}% F")
    for niv in ["L1","L2","L3"]:
        recs_niv = [r for r in records_r if r["ufr"]==ufr_c and r["niveau"]==niv and r["session"]=="Normale"]
        if not recs_niv: continue
        a = sum(1 for r in recs_niv if r["statut"]=="Admis")
        d = sum(1 for r in recs_niv if r["statut"]=="Défaillant")
        t = len(recs_niv)
        ms = [float(r["moyenne_generale"]) for r in recs_niv if r["moyenne_generale"]!=""]
        sig = f"σ={statistics.stdev(ms):.2f}" if len(ms)>1 else ""
        print(f"  {niv}: Admis={100*a/t:.1f}% | Déf={100*d/t:.1f}% | Moy={sum(ms)/len(ms):.2f} {sig}")

# Tailles fichiers
print("\nFichiers :")
for fn in sorted(os.listdir("/home/claude/dataset_35k")):
    sz = os.path.getsize(f"/home/claude/dataset_35k/{fn}")
    print(f"  {fn:45s} {sz/1024:8.0f} KB")
