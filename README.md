# Dataset Synthétique UFR Sciences & Technologie — Université Thomas Sankara
## Version 1.0 — Juin 2026

## Description
Dataset synthétique généré pour le tableau de bord décisionnel académique UTS.
Calibré sur les statistiques officielles du MESRI Burkina Faso et de la littérature académique africaine.

## Sources de calibration
- MESRI BF (2022-2023) : Annuaire statistique de l'enseignement supérieur
- UNESCO (2023) : Women in STEM in Sub-Saharan Africa — ~35% of STEM graduates
- WEF (2021) : Share of females in STEM < 30% in many SSA countries
- Cornet et al. (2024) : Taux d'abandon F=48%, H=35% avant fin licence en Afrique de l'Ouest

## Statistiques du dataset
- 5 576 étudiants uniques (6 cohortes : 2019-2024)
- 31 347 enregistrements de résultats (sessions normale + rattrapage)
- 180 494 notes de modules individuelles
- 3 filières troncs communs (MPCI, HYDRO, LIME-LISE) + 6 filières L3
- 6 semestres (S1→S6), 6 années académiques (2019-2020 → 2024-2025)

## Indicateurs de validation (session normale)
| Niveau | Taux admis | Taux ajournés | Taux défaillants | Moyenne | Sigma |
|--------|-----------|---------------|-----------------|---------|-------|
| L1     | 27.7%     | 61.1%         | 11.2%           | 9.16    | 1.68  |
| L2     | 50.5%     | 42.6%         | 7.0%            | 10.15   | 1.46  |
| L3     | 75.2%     | 21.1%         | 3.7%            | 11.07   | 1.43  |

## Répartition genre
- Femmes : 31.4% (conforme aux statistiques STEM en Afrique subsaharienne)
- Hommes : 68.6%
- Écart taux réussite H-F en L1 : 3.4 points (conforme Cornet et al. 2024)

## Fichiers
| Fichier | Rôle | Lignes |
|---------|------|--------|
| dim_etudiant.csv | Données personnelles étudiants (noms burkinabè fictifs) | 5,576 |
| fact_resultats.csv | Résultats par semestre/session | 31,347 |
| fact_notes_ue.csv | Notes détaillées par module | 180,494 |
| dim_filiere.csv | Référentiel filières et bifurcations | 9 |
| dim_semestre.csv | Référentiel semestres | 6 |
| dim_annee_academique.csv | Référentiel années académiques | 6 |

## Noms utilisés
Prénoms et noms de famille burkinabè issus du RGPH (Geneawiki/INSEE-BF) :
Top noms : Ouédraogo, Sawadogo, Kaboré, Traoré, Diallo, Ouattara, Zongo, Sanou...
Prénoms mixtes (islam/chrétien/traditionnel) représentatifs de la diversité culturelle burkinabè.

## Schéma en étoile
Table de faits : fact_resultats
Dimensions : dim_etudiant, dim_filiere, dim_semestre, dim_annee_academique
Extension : fact_notes_ue (notes par module)

## Note méthodologique
Ce dataset est synthétique et conçu pour la démonstration du tableau de bord.
Il respecte les contraintes de la section 11 du CDC : données-agnostique, remplaçable
par les vraies données de l'UFR S&T sans modification du code de traitement.
