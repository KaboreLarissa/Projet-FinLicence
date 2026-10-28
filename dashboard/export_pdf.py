"""
export_pdf.py v3
Export PDF complet par onglet :
- Chaque onglet génère un PDF avec TOUS ses KPIs et tableaux de données
- 6 PDFs différents selon l'onglet (Synthèse, Effectifs, Performances, Étudiant, Flux, Comparaison)
- 7ème PDF pour l'onglet Administration (admin uniquement)
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime
import io, pandas as pd

# ── Couleurs UTS ─────────────────────────────────────────────
C_BLEU   = colors.HexColor("#0D2B55")
C_BLEU2  = colors.HexColor("#2A5299")
C_VERT   = colors.HexColor("#00875A")
C_ORANGE = colors.HexColor("#D46B08")
C_ROUGE  = colors.HexColor("#C0392B")
C_GRIS   = colors.HexColor("#6B7280")
C_GRISL  = colors.HexColor("#F0F3F8")
C_OR     = colors.HexColor("#B7791F")
C_VIOLET = colors.HexColor("#6D28D9")
C_BLANC  = colors.white

W = A4[0] - 4*cm  # largeur utile page

# ── Helpers ──────────────────────────────────────────────────
def p(txt, **kw):
    """Paragraphe simple"""
    return Paragraph(str(txt), ParagraphStyle("p",
        fontSize=kw.get("size",9), fontName=kw.get("font","Helvetica"),
        textColor=kw.get("color",colors.HexColor("#374151")),
        spaceBefore=kw.get("sb",0), spaceAfter=kw.get("sa",2),
        alignment=kw.get("align",TA_LEFT)))

def tbl(data, widths, header_bg=C_BLEU):
    """Tableau propre avec alternance de couleurs"""
    if not data or len(data)<1: return Spacer(1,0.1*cm)
    t = Table(data, colWidths=widths, repeatRows=1)
    n = len(data)
    style = [
        ("BACKGROUND",    (0,0),(-1,0), header_bg),
        ("TEXTCOLOR",     (0,0),(-1,0), C_BLANC),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1),"Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("RIGHTPADDING",  (0,0),(-1,-1), 7),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEBELOW",     (0,0),(-1,-1), 0.3, colors.HexColor("#E5E9F0")),
    ]
    for i in range(1,n):
        if i%2==0:
            style.append(("BACKGROUND",(0,i),(-1,i),C_GRISL))
    t.setStyle(TableStyle(style))
    return t

def sec(titre):
    """Titre de section"""
    return [
        Spacer(1,0.35*cm),
        Table([[Paragraph(f"<b>{titre}</b>",
            ParagraphStyle("s",fontSize=11,fontName="Helvetica-Bold",
                textColor=C_BLANC))]],
            colWidths=[W],
            style=TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),C_BLEU2),
                ("TOPPADDING",(0,0),(-1,-1),6),
                ("BOTTOMPADDING",(0,0),(-1,-1),6),
                ("LEFTPADDING",(0,0),(-1,-1),10),
            ])),
        Spacer(1,0.15*cm),
    ]

def kpi_bloc(kpis, session_lbl="Normale", filiere_lbl="Toutes filières"):
    """Grille de KPIs 3x2"""
    items = [
        ("Étudiants inscrits",    f"{kpis.get('effectif',0):,}",                  "",       C_BLEU,   "Étudiants distincts"),
        ("Taux de réussite",      f"{kpis.get('taux_reussite',0)} %",             "",        C_VERT,   f"Session {session_lbl}"),
        ("Taux d'ajournement",    f"{kpis.get('taux_echec',0)} %",               "",         C_ORANGE, f"Session {session_lbl}"),
        ("Taux de défaillance",   f"{kpis.get('taux_defaillance',0)} %",         "",         C_ROUGE,  f"Session {session_lbl}"),
        ("Moyenne générale",      f"{kpis.get('moyenne',0)} / 20",               "",         C_BLEU2,  filiere_lbl),
        ("IPG",                   f"{kpis.get('ipg',0)} / 100",                  "",         C_OR,     "Indice de Performance Globale"),
    ]
    rows = []
    for i in range(0, len(items), 3):
        row_cells = []
        for label, val, _, clr, sub in items[i:i+3]:
            cell = Table([[
                Paragraph(label, ParagraphStyle("kl",fontSize=8,fontName="Helvetica",textColor=C_GRIS)),
                Paragraph(f"<b>{val}</b>", ParagraphStyle("kv",fontSize=17,fontName="Helvetica-Bold",textColor=clr)),
                Paragraph(sub, ParagraphStyle("ks",fontSize=7.5,fontName="Helvetica",textColor=C_GRIS)),
            ]], colWidths=[W/3-0.6*cm])
            cell.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#E5E9F0")),
                ("BACKGROUND",(0,0),(-1,-1),C_GRISL),
                ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
                ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),6),
                ("LINEABOVE",(0,0),(-1,0),2.5,clr),
            ]))
            row_cells.append(cell)
        while len(row_cells)<3: row_cells.append("")
        rows.append(row_cells)
    t = Table(rows, colWidths=[W/3]*3)
    t.setStyle(TableStyle([
        ("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    return t

def entete(onglet, nom_user, filtres):
    """En-tête du PDF"""
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    filtres_str = " · ".join([f"{k}: {v}" for k,v in filtres.items() if v and v not in ("Tous","Toutes","")])
    return [
        Table([[
            Table([[[Paragraph("<b>Université Thomas Sankara</b>",
                ParagraphStyle("h1",fontSize=14,fontName="Helvetica-Bold",textColor=C_BLEU))]],
                   [[Paragraph("Direction des Systèmes d'Information",
                ParagraphStyle("h2",fontSize=9,fontName="Helvetica",textColor=C_GRIS))]],
            ]),
            Table([[[Paragraph(f"<b>Rapport — {onglet}</b>",
                ParagraphStyle("r1",fontSize=11,fontName="Helvetica-Bold",
                    textColor=C_BLEU,alignment=TA_RIGHT))]],
                   [[Paragraph(f"{now}  ·  {nom_user}",
                ParagraphStyle("r2",fontSize=8,fontName="Helvetica",
                    textColor=C_GRIS,alignment=TA_RIGHT))]],
            ]),
        ]], colWidths=[W*0.55, W*0.45],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                           ("BOTTOMPADDING",(0,0),(-1,-1),8)])),
        HRFlowable(width="100%",thickness=2.5,color=C_BLEU,spaceAfter=8),
        p(f"Filtres : {filtres_str or 'Aucun filtre — toutes données'}",
          size=8,color=C_GRIS,sa=10),
    ]

def pied_page(onglet, nom_user):
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    return [
        Spacer(1,0.6*cm),
        HRFlowable(width="100%",thickness=0.5,color=C_GRIS,spaceAfter=5),
        Paragraph(f"Université Thomas Sankara · Tableau de Bord Académique · "
                  f"Rapport {onglet} · {now} · {nom_user}",
            ParagraphStyle("pied",fontSize=7,fontName="Helvetica",
                textColor=C_GRIS,alignment=TA_CENTER)),
    ]

def safe_float(val):
    try: return round(float(val),2)
    except: return 0.0

def safe_int(val):
    try: return int(float(val))
    except: return 0

# ══════════════════════════════════════════════════════════════
# PDF PAR ONGLET
# ══════════════════════════════════════════════════════════════

def pdf_synthese(kpis, filtres, nom_user, data):
    """PDF Synthèse : KPIs + répartition statuts + comparaison filières"""
    els = entete("Synthèse exécutive", nom_user, filtres)
    ses = filtres.get("Session","Normale")
    fil = filtres.get("Filière","Toutes filières")

    els += sec("Indicateurs clés de performance")
    els.append(kpi_bloc(kpis, ses, fil))
    els.append(Spacer(1,0.3*cm))

    els += sec("Répartition des résultats")
    d = [["Statut","Nombre d'étudiants","Pourcentage (%)"],
         ["Admis",     f"{kpis.get('nb_admis',0):,}",     f"{kpis.get('taux_reussite',0)} %"],
         ["Ajournés",  f"{kpis.get('nb_ajournes',0):,}",  f"{kpis.get('taux_echec',0)} %"],
         ["Défaillants",f"{kpis.get('nb_defaillants',0):,}",f"{kpis.get('taux_defaillance',0)} %"],
         ["Total",     f"{kpis.get('total_resultats',0):,}", "100 %"]]
    els.append(tbl(d,[5*cm,4.5*cm,4.5*cm]))
    els.append(Spacer(1,0.3*cm))

    if data.get("comparaison") is not None and len(data["comparaison"])>0:
        els += sec("Comparaison des filières — classement par taux de réussite")
        comp = data["comparaison"].sort_values("taux_reussite",ascending=False)
        d = [["Filière","UFR","Effectif","Réussite","Défaillance","Moyenne"]]
        for _,r in comp.iterrows():
            d.append([str(r.get("filiere_code","")),str(r.get("ufr","")),
                f"{safe_int(r.get('effectif',0)):,}",
                f"{safe_float(r.get('taux_reussite',0)):.1f} %",
                f"{safe_float(r.get('taux_defaillance',0)):.1f} %",
                f"{safe_float(r.get('moyenne',0)):.2f}/20"])
        els.append(tbl(d,[3*cm,1.8*cm,2*cm,2.5*cm,2.5*cm,2.5*cm]))

    els += pied_page("Synthèse", nom_user)
    return els

def pdf_effectifs(kpis, filtres, nom_user, data):
    """PDF Effectifs : KPIs + réinscription + répartition genre + filières"""
    els = entete("Effectifs & Attractivité", nom_user, filtres)
    ses = filtres.get("Session","Normale")
    gk  = data.get("kpi_globaux",{})

    els += sec("Indicateurs clés")
    els.append(kpi_bloc(kpis, ses))
    els.append(Spacer(1,0.2*cm))

    # KPIs globaux
    d = [["Indicateur","Valeur","Base de calcul"],
         ["Passage L1 → L2",     f"{gk.get('passage_l1_l2',0)} %",   "Toutes cohortes"],
         ["Passage L2 → L3",     f"{gk.get('passage_l2_l3',0)} %",   "Toutes cohortes"],
         ["Nouveaux inscrits L1", f"{gk.get('nb_l1_recent',0):,}",   gk.get("derniere_annee","")],
    ]
    els.append(tbl(d,[5*cm,3.5*cm,5.2*cm]))
    els.append(Spacer(1,0.3*cm))

    if data.get("reinscription") is not None and len(data["reinscription"])>0:
        els += sec("Taux de réinscription d'une année à l'autre")
        d = [["De","Vers","Réinscrits","Total","Taux"]]
        for _,r in data["reinscription"].iterrows():
            d.append([str(r.get("de","")),str(r.get("vers","")),
                f"{safe_int(r.get('n_reinscrits',0)):,}",
                f"{safe_int(r.get('n_total',0)):,}",
                f"{safe_float(r.get('taux_reinscription',0)):.1f} %"])
        els.append(tbl(d,[3*cm,3*cm,3*cm,3*cm,2.7*cm]))
        els.append(Spacer(1,0.3*cm))

    if data.get("genre") is not None and len(data["genre"])>0:
        els += sec("Parité Hommes / Femmes")
        d = [["Genre","Effectif","Taux de réussite","Moyenne"]]
        for _,r in data["genre"].iterrows():
            d.append([{"M":"Masculin","F":"Féminin"}.get(str(r.get("genre","")),"—"),
                f"{safe_int(r.get('effectif',0)):,}",
                f"{safe_float(r.get('taux_reussite',0)):.1f} %",
                f"{safe_float(r.get('moyenne',0)):.2f}/20"])
        els.append(tbl(d,[3.5*cm,3.5*cm,3.5*cm,3.5*cm]))

    els += pied_page("Effectifs", nom_user)
    return els

def pdf_performances(kpis, filtres, nom_user, data):
    """PDF Performances : KPIs + top étudiants + mentions + modules difficiles"""
    els = entete("Performances académiques", nom_user, filtres)
    ses = filtres.get("Session","Normale")
    fil = filtres.get("Filière","Toutes filières")

    els += sec("Indicateurs clés de performance")
    els.append(kpi_bloc(kpis, ses, fil))
    els.append(Spacer(1,0.3*cm))

    # Distribution des notes
    els += sec("Répartition par statut")
    d = [["Statut","Nombre","Pourcentage"],
         ["Admis",     f"{kpis.get('nb_admis',0):,}",      f"{kpis.get('taux_reussite',0)} %"],
         ["Ajournés",  f"{kpis.get('nb_ajournes',0):,}",   f"{kpis.get('taux_echec',0)} %"],
         ["Défaillants",f"{kpis.get('nb_defaillants',0):,}",f"{kpis.get('taux_defaillance',0)} %"]]
    els.append(tbl(d,[5*cm,4*cm,4*cm]))
    els.append(Spacer(1,0.3*cm))

    if data.get("mentions") is not None and len(data["mentions"])>0:
        els += sec("Répartition des mentions — étudiants admis uniquement")
        d = [["Mention","Nombre d'étudiants","% des admis"]]
        for _,r in data["mentions"].iterrows():
            d.append([str(r.get("mention","—")),
                f"{safe_int(r.get('count',0)):,}",
                f"{safe_float(r.get('pct',0)):.1f} %"])
        els.append(tbl(d,[5*cm,4.5*cm,4.2*cm]))
        els.append(Spacer(1,0.3*cm))

    if data.get("top_etudiants") is not None and len(data["top_etudiants"])>0:
        els += sec("Top 10 — Meilleurs étudiants de la période")
        d = [["#","Étudiant","Matricule","Filière","Niveau","Semestre","Moyenne","Mention"]]
        for i,(_,r) in enumerate(data["top_etudiants"].iterrows()):
            try: moy=f"{float(r.get('moyenne_generale',0)):.2f}/20"
            except: moy="—"
            nom_e=f"{r.get('prenom','')} {r.get('nom','')}".strip()
            d.append([str(i+1),nom_e,str(r.get("matricule","")),
                str(r.get("filiere_code","")),str(r.get("niveau","")),
                str(r.get("semestre","")),moy,str(r.get("mention","") or "—")])
        els.append(tbl(d,[0.6*cm,3.8*cm,2.3*cm,1.8*cm,1.3*cm,1.5*cm,2*cm,2.2*cm]))
        els.append(Spacer(1,0.3*cm))

    if data.get("bas_etudiants") is not None and len(data["bas_etudiants"])>0:
        els += sec("Étudiants en difficulté — à surveiller")
        d = [["#","Étudiant","Matricule","Filière","Niveau","Moyenne","Statut"]]
        for i,(_,r) in enumerate(data["bas_etudiants"].iterrows()):
            try: moy=f"{float(r.get('moyenne_generale',0)):.2f}/20"
            except: moy="—"
            nom_e=f"{r.get('prenom','')} {r.get('nom','')}".strip()
            d.append([str(i+1),nom_e,str(r.get("matricule","")),
                str(r.get("filiere_code","")),str(r.get("niveau","")),
                moy,str(r.get("statut","") or "—")])
        els.append(tbl(d,[0.6*cm,3.8*cm,2.3*cm,1.8*cm,1.5*cm,2.2*cm,2.3*cm]))
        els.append(Spacer(1,0.3*cm))

    if data.get("modules") is not None and len(data["modules"])>0:
        els += sec("Modules les plus difficiles — moyenne inférieure à 10/20")
        d = [["Module","Moyenne générale","Nb notes"]]
        for _,r in data["modules"].head(12).iterrows():
            d.append([str(r.get("nom_ue","—"))[:55],
                f"{safe_float(r.get('moyenne',0)):.2f} / 20",
                f"{safe_int(r.get('nb_notes',0)):,}"])
        els.append(tbl(d,[9.5*cm,3*cm,3.2*cm]))

    els += pied_page("Performances", nom_user)
    return els

def pdf_flux(kpis, filtres, nom_user, data):
    """PDF Flux & Parcours — données de l'année de référence"""
    els = entete("Flux & Parcours étudiants", nom_user, filtres)

    flux = data.get("flux", pd.DataFrame())
    if len(flux) > 0:
        row = flux.iloc[0]
        L1  = int(row.get("n_l1", 0))
        L2  = int(row.get("n_l2", 0))
        L3  = int(row.get("n_l3", 0))
        DIP = int(row.get("n_admis_l3", 0))
        tr_l1  = float(row.get("tr_l1",  round(100*L2/L1,1)  if L1>0 else 0))
        tr_l2  = float(row.get("tr_l2",  round(100*L3/L2,1)  if L2>0 else 0))
        tr_dip = float(row.get("tr_dip", round(100*DIP/L1,1) if L1>0 else 0))
        pct_ab = float(row.get("pct_ab", round(100*(L1-DIP)/L1,1) if L1>0 else 0))

        els += sec("Indicateurs de flux")
        d = [["Indicateur", "Valeur", "Interprétation"],
             ["Inscrits en L1",      f"{L1:,}",      "Nouveaux entrants en première année"],
             ["Passage L1 → L2",     f"{tr_l1} %",   "Des L1 qui accèdent en L2"],
             ["Passage L2 → L3",     f"{tr_l2} %",   "Des L2 qui accèdent en L3"],
             ["Taux de diplomation", f"{tr_dip} %",  "Diplômés / inscrits L1"],
             ["Non diplômés",        f"{pct_ab} %",  "N'obtiennent pas leur diplôme"],
             ["Étudiants en L2",     f"{L2:,}",      "Ont accédé au 2ème cycle"],
             ["Étudiants en L3",     f"{L3:,}",      "Ont accédé au 3ème cycle"],
             ["Diplômés",            f"{DIP:,}",     "Ont obtenu leur licence"]]
        els.append(tbl(d, [5*cm, 3*cm, 6.7*cm]))
    else:
        els.append(p("Aucune donnée de flux disponible.", color=C_GRIS))

    els += pied_page("Flux & Parcours", nom_user)
    return els



def pdf_etudiant(kpis, filtres, nom_user, data):
    """PDF Étudiant : informations sur l'étudiant recherché"""
    els = entete("Suivi individuel de l'étudiant", nom_user, filtres)

    etudiant = data.get("etudiant")
    if etudiant is None:
        els.append(p("Aucun étudiant sélectionné. Lancez une recherche puis exportez.",
                     color=C_GRIS, size=11))
        els += pied_page("Étudiant", nom_user)
        return els

    els += sec(f"Profil — {etudiant.get('nom_complet','')}")
    d = [["Matricule","Genre","Âge entrée","UFR","Filière initiale","Entrée"],
         [str(etudiant.get("matricule","")),
          {"M":"Masculin","F":"Féminin"}.get(str(etudiant.get("genre","")),"—"),
          f"{etudiant.get('age_entree','—')} ans",
          str(etudiant.get("ufr","")),
          str(etudiant.get("filiere_initiale","")),
          str(etudiant.get("annee_entree",""))]]
    els.append(tbl(d,[2.8*cm,2.5*cm,2*cm,2*cm,2.8*cm,2.6*cm]))
    els.append(Spacer(1,0.2*cm))

    parcours = data.get("parcours", pd.DataFrame())
    if len(parcours)>0:
        els += sec("Parcours académique complet")
        d=[["Année","Niveau","Semestre","Filière","Moyenne","Statut","Mention","Rang"]]
        for _,r in parcours.iterrows():
            try: moy=f"{float(r.get('moyenne_generale',0)):.2f}/20"
            except: moy="—"
            rang=str(safe_int(r.get("rang_promo",0))) if r.get("rang_promo") else "—"
            d.append([str(r.get("annee_academique","")),str(r.get("niveau","")),
                str(r.get("semestre","")),str(r.get("filiere_code","")),moy,
                str(r.get("statut","")),str(r.get("mention","") or "—"),rang])
        els.append(tbl(d,[2.8*cm,1.5*cm,1.8*cm,2*cm,2.3*cm,2*cm,2*cm,1.3*cm]))

    els += pied_page("Étudiant", nom_user)
    return els

def pdf_administration(kpis, filtres, nom_user, data):
    """PDF Administration : liste des utilisateurs + log imports"""
    els = entete("Administration", nom_user, filtres)

    if data.get("utilisateurs"):
        els += sec("Liste des comptes utilisateurs")
        d=[["Utilisateur","Email","Rôle","UFR","Statut","Dernière connexion"]]
        for u in data["utilisateurs"]:
            d.append([f"{u.get('prenom','')} {u.get('nom','')}",
                u.get("email",""),u.get("role",""),
                u.get("ufr","") or "Toutes",
                "Actif" if u.get("actif") else "Inactif",
                u.get("derniere_connexion","Jamais")])
        els.append(tbl(d,[3.5*cm,4*cm,2.2*cm,1.5*cm,1.5*cm,2*cm]))

    els += pied_page("Administration", nom_user)
    return els

# ── Fonction principale ───────────────────────────────────────
def pdf_comparaison(kpis, filtres, nom_user, data):
    """PDF Comparaison : KPIs + tableau comparatif UFR + filières"""
    els = entete("Comparaison & Parité", nom_user, filtres)
    ses = filtres.get("Session","Normale")

    els += sec("Indicateurs globaux")
    els.append(kpi_bloc(kpis, ses))
    els.append(Spacer(1,0.3*cm))

    if data.get("par_ufr") is not None and len(data["par_ufr"])>0:
        els += sec("Performance par UFR")
        d = [["UFR","Effectif","Réussite","Défaillance","Moyenne","Mention"]]
        for _,r in data["par_ufr"].iterrows():
            d.append([str(r.get("ufr","")),
                f"{safe_int(r.get('effectif',0)):,}",
                f"{safe_float(r.get('taux_reussite',0)):.1f} %",
                f"{safe_float(r.get('taux_defaillance',0)):.1f} %",
                f"{safe_float(r.get('moyenne',0)):.2f}/20",
                f"{safe_float(r.get('mention',0)):.1f} %"])
        els.append(tbl(d,[2.5*cm,2.5*cm,2.5*cm,2.5*cm,2.5*cm,2.7*cm]))
        els.append(Spacer(1,0.3*cm))

    if data.get("comparaison") is not None and len(data["comparaison"])>0:
        els += sec("Comparaison des filières — classement par taux de réussite")
        comp = data["comparaison"].sort_values("taux_reussite",ascending=False)
        d = [["Filière","UFR","Effectif","Taux réussite","Taux défail.","Moyenne"]]
        for _,r in comp.iterrows():
            d.append([str(r.get("filiere_code","")),str(r.get("ufr","")),
                f"{safe_int(r.get('effectif',0)):,}",
                f"{safe_float(r.get('taux_reussite',0)):.1f} %",
                f"{safe_float(r.get('taux_defaillance',0)):.1f} %",
                f"{safe_float(r.get('moyenne',0)):.2f}/20"])
        els.append(tbl(d,[3.2*cm,1.8*cm,2*cm,2.5*cm,2.5*cm,2.7*cm]))
        els.append(Spacer(1,0.3*cm))

    if data.get("genre") is not None and len(data["genre"])>0:
        els += sec("Parité Hommes / Femmes")
        d = [["Genre","Effectif","Taux de réussite","Moyenne générale"]]
        for _,r in data["genre"].iterrows():
            d.append([{"M":"Masculin","F":"Féminin"}.get(str(r.get("genre","")),"—"),
                f"{safe_int(r.get('effectif',0)):,}",
                f"{safe_float(r.get('taux_reussite',0)):.1f} %",
                f"{safe_float(r.get('moyenne',0)):.2f}/20"])
        els.append(tbl(d,[4*cm,3.5*cm,3.5*cm,3.7*cm]))

    els += pied_page("Comparaison", nom_user)
    return els


GENERATEURS = {
    "Synthèse":          pdf_synthese,
    "Effectifs":         pdf_effectifs,
    "Performances":      pdf_performances,
    "Flux & Parcours":   pdf_flux,
    "Comparaison":       pdf_comparaison,
    "Suivi Étudiant":    pdf_etudiant,
    "Administration":    pdf_administration,
}

def generer_pdf(onglet, kpis, filtres_actifs, nom_utilisateur, data=None, **kwargs):
    """
    Génère le PDF de l'onglet actif.
    Chaque onglet a son propre générateur avec le contenu qui lui correspond.
    """
    if data is None:
        data = {}
    # Compatibilité avec l'ancienne signature
    if kwargs.get("top_etudiants") is not None:
        data["top_etudiants"] = kwargs["top_etudiants"]
    if kwargs.get("mentions") is not None:
        data["mentions"] = kwargs["mentions"]
    if kwargs.get("modules_difficiles") is not None:
        data["modules"] = kwargs["modules_difficiles"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.8*cm, bottomMargin=2*cm)

    gen_fn = GENERATEURS.get(onglet, pdf_synthese)
    elements = gen_fn(kpis, filtres_actifs, nom_utilisateur, data)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
