# Dataset Synthétique UTS — Version Complète 35 000 étudiants
# Université Thomas Sankara — 3 UFR — 6 cohortes (2019-2024)
# Généré par script Python calibré sur statistiques officielles

## Contexte
Dataset généré pour le tableau de bord décisionnel académique UTS (mémoire fin de cycle,
Licence Génie Logiciel, UVBF). Données synthétiques calibrées sur :
- MESRI Burkina Faso (Annuaire statistique 2022-2023)
- UNESCO 2023 : femmes = ~35% diplômés STEM en Afrique subsaharienne
- WEF 2021 : part femmes STEM < 30% en Afrique de l'Ouest
- Cornet et al. 2024 : taux abandon F=48%, H=35% avant fin licence (universités Afrique de l'Ouest)

## Chiffres clés
- 31 098 étudiants uniques (6 cohortes 2019-2024, cible 35 000 atteinte à ~89%)
- 167 250 enregistrements de résultats (sessions normale + rattrapage)
- 943 766 notes de modules individuelles
- 3 UFR : ST, SEG, SJP
- 9 filières L1-L2 (troncs communs) + 15 filières L3 (spécialisations)
- 6 semestres S1→S6 / 6 années académiques 2019-2020 → 2024-2025

## Fichiers
| Fichier | Description | Lignes |
|---------|-------------|--------|
| dim_etudiant.csv | Données personnelles (noms burkinabè fictifs) | 31 098 |
| fact_resultats.csv | Résultats par semestre/session avec tous les KPIs | 167 250 |
| fact_notes_ue.csv | Notes détaillées par module (avec contexte complet) | 943 766 |
| dim_filiere.csv | Référentiel des 24 filières (3 UFR) | 24 |
| dim_ufr.csv | Description des 3 UFR avec effectifs référence | 3 |
| dim_semestre.csv | S1→S6 avec niveau et période | 6 |
| dim_annee_academique.csv | Années 2019-2025 | 6 |
| vue_complete_etudiants.csv | BONUS : vue SQL jointe (CSV plat, toutes colonnes) | 167 250 |

## Colonnes principales de fact_resultats.csv
matricule, ufr, filiere_code, niveau, semestre, annee_academique, session,
moyenne_generale, total_points, nb_ue_validees, nb_ue_echouees, statut, mention, rang_promo

## Règle sur les valeurs manquantes
- moyenne_generale = VIDE uniquement si statut = Défaillant (absent aux examens)
- rang_promo = VIDE si défaillant
- mention = VIDE si ajourné ou défaillant
- Tout le reste est TOUJOURS renseigné

## Validation statistique
UFR/ST  : 7 152 étudiants | 31.3% F | L1: 29% admis | L2: 50% | L3: 74%
UFR/SEG : 15 860 étudiants | 28.0% F | L1: 48% admis | L2: 69% | L3: 88%
UFR/SJP : 8 086 étudiants  | 45.3% F | L1: 44% admis | L2: 62% | L3: 84%

## Schéma en étoile (modèle Kimball)
Table centrale : fact_resultats (mesures : moyenne, statut, rang)
Dimensions : dim_etudiant + dim_filiere + dim_ufr + dim_semestre + dim_annee_academique
Extension UE : fact_notes_ue (notes individuelles par module, liées par id_resultat)

Pour obtenir une vue complète : jointure SQL ou pandas sur la colonne matricule
Le fichier vue_complete_etudiants.csv contient déjà cette jointure pour consultation rapide.

## Note sur le script de génération
Le script Python generate_dataset.py (fourni séparément) est entièrement paramétrable.
Il peut être ré-exécuté pour intégrer les vraies données UTS sans modifier la structure.
