"""
Dashboard UTS v6 — Structure finale
RESPONSABLE : Synthèse·Effectifs·Performances·Étudiant·Flux·Comparaison·Import données
ADMIN       : Synthèse·Effectifs·Performances·Étudiant·Flux·Comparaison·Gestion & Suivi
"""
import dash, base64, io, os, sys, warnings, tempfile
warnings.filterwarnings("ignore")
from dash import dcc, html, Input, Output, State, ctx, ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import (
    load_all, filter_data, compute_kpis, get_kpis_globaux,
    get_evolution_effectifs, get_evolution_reussite,
    get_evolution_reussite_filtre,
    get_distribution_moyennes, get_top_etudiants,
    get_parite_genre, get_mentions, get_comparaison_filieres,
    get_evolution_par_semestre, get_flux_sankey,
    get_modules_difficiles, get_taux_reinscription,
)
from auth.auth import (
    authenticate, create_token, decode_token,
    creer_utilisateur, lister_utilisateurs,
    modifier_utilisateur, supprimer_utilisateur,
    log_import, log_export,
    lister_imports, lister_exports, lister_mes_imports,
)
from etl.pipeline import run_pipeline
from export_pdf import generer_pdf

# ── Palette ──────────────────────────────────────────────────
BLEU="#0D2B55";BLEU2="#2A5299";VERT="#00875A";ORANGE="#D46B08"
ROUGE="#C0392B";GRIS="#9CA3AF";GRIS2="#E5E9F0";GRIS3="#F0F3F8"
OR="#B7791F";VIOLET="#6D28D9"
UFR_C={"ST":"#0D2B55","SEG":"#00875A","SJP":"#D46B08"}
NIV_C={"L1":BLEU2,"L2":VERT,"L3":OR}
GENRE_C={"M":BLEU2,"F":"#C2185B"}

def ax(tickangle=0,ticksuffix="",title="",showgrid=True):
    return dict(showgrid=showgrid,gridcolor=GRIS2,gridwidth=1,linecolor=GRIS2,
                zeroline=False,tickfont=dict(size=11,color=GRIS),
                title=dict(text=title,font=dict(size=11,color=GRIS)),
                tickangle=tickangle,ticksuffix=ticksuffix)

def lay(h=None,margin=None,**kw):
    base=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
              font=dict(family="Inter,sans-serif",size=12,color="#374151"),
              margin=margin or dict(l=12,r=12,t=8,b=8),
              showlegend=False,xaxis=ax(),yaxis=ax())
    if h: base["height"]=h
    base.update(kw)
    return base

# ── Données globales ──────────────────────────────────────────
DATA=load_all(); DF_FIL=DATA["filieres"]
KPI_GLOBAUX=get_kpis_globaux()
ANNEES=["Toutes"]+sorted(DATA["joined"]["annee_academique"].dropna().astype(str).unique().tolist(),reverse=True)
UFRS=["Tous"]+sorted(DATA["joined"]["ufr"].dropna().astype(str).unique().tolist())
NIVEAUX=["Tous","L1","L2","L3"]; SEMS=["Tous","S1","S2","S3","S4","S5","S6"]
SESSIONS=["Normale","Rattrapage","Toutes"]

def opts_fil(ufr="Tous"):
    if ufr=="Tous": codes=DF_FIL["code_filiere"].astype(str).tolist()
    else: codes=DF_FIL[DF_FIL["ufr"].astype(str)==ufr]["code_filiere"].astype(str).tolist()
    return [{"label":"Toutes","value":"Toutes"}]+[{"label":c,"value":c} for c in sorted(codes)]

def s(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except: pass
    return str(v)

def dd(id_,opts,val,disabled=False):
    return dcc.Dropdown(id=id_,options=opts,value=val,clearable=False,
                        disabled=disabled,style={"fontSize":"12px"})

# ── Composants UI ─────────────────────────────────────────────
def kpi_card(label,val,unit="",couleur=BLEU,sub=""):
    return html.Div([
        html.Div(label,style={"fontSize":"11px","fontWeight":"600","color":"#6B7280",
                               "textTransform":"uppercase","letterSpacing":"0.06em","marginBottom":"8px"}),
        html.Div([
            html.Span(str(val),style={"fontSize":"26px","fontWeight":"700","color":"#111827","letterSpacing":"-0.02em"}),
            html.Span(f" {unit}",style={"fontSize":"13px","color":"#9CA3AF","fontWeight":"500"}) if unit else None,
        ]),
        html.Div(sub,style={"fontSize":"11px","color":"#9CA3AF","marginTop":"4px"}) if sub else None,
        html.Div(style={"position":"absolute","left":"0","top":"0","bottom":"0",
                        "width":"3px","background":couleur,"borderRadius":"2px 0 0 2px"}),
    ],style={"background":"white","border":"1px solid #E5E9F0","borderRadius":"10px",
               "padding":"14px 16px","position":"relative","overflow":"hidden",
               "boxShadow":"0 1px 3px rgba(13,43,85,0.06)"})

def ccard(title,sub,*children,height=None):
    return html.Div([
        html.Div(title,style={"fontSize":"13px","fontWeight":"600","color":"#111827","marginBottom":"2px"}),
        html.Div(sub,style={"fontSize":"11.5px","color":"#9CA3AF","marginBottom":"10px"}),
        html.Div(style={"height":"1px","background":"#E5E9F0","margin":"0 -18px 12px"}),
        html.Div([*children],style={"minHeight":f"{height}px"} if height else {}),
    ],style={"background":"white","border":"1px solid #E5E9F0","borderRadius":"10px",
               "padding":"16px 18px","boxShadow":"0 1px 3px rgba(13,43,85,0.06)",
               "overflow":"hidden","minWidth":"0","marginBottom":"16px"})

def sep(title):
    return html.Div([
        html.Span(title,style={"fontSize":"11px","fontWeight":"600","color":"#9CA3AF",
                                "textTransform":"uppercase","letterSpacing":"0.08em","whiteSpace":"nowrap"}),
        html.Div(style={"flex":"1","height":"1px","background":"#E5E9F0"}),
    ],style={"display":"flex","alignItems":"center","gap":"10px","margin":"18px 0 12px"})

def g(fig,h=320):
    fig.update_layout(height=h,autosize=True)
    return dcc.Graph(figure=fig,
        config={"displayModeBar":True,
                "modeBarButtonsToRemove":["select2d","lasso2d","autoScale2d",
                    "hoverClosestCartesian","hoverCompareCartesian",
                    "toggleSpikelines","sendDataToCloud"],
                "toImageButtonOptions":{"format":"png","filename":"UTS_graphique",
                    "height":h,"width":900,"scale":2},
                "responsive":True},
        style={"width":"100%","minHeight":f"{h}px"})

def badge(txt):
    colors_map={"Admis":("#E6F5EF",VERT,"#B7DFCF"),"Ajourné":("#FEF0E0",ORANGE,"#F9C87A"),
                "Défaillant":("#FDECEA",ROUGE,"#F5C0BC"),"Très bien":("#EDE7F6","#512DA8","#D1C4E9"),
                "Bien":("#E8EAF6","#283593","#C5CAE9"),"Assez bien":("#E8F0FE","#1565C0","#AECBF8"),
                "Passable":(GRIS3,GRIS,GRIS2),"succès":("#E6F5EF",VERT,"#B7DFCF"),
                "erreur":("#FDECEA",ROUGE,"#F5C0BC")}
    bg,color,border=colors_map.get(txt or "",(GRIS3,GRIS,GRIS2))
    return html.Span(txt or "—",style={"background":bg,"color":color,
        "border":f"1px solid {border}","borderRadius":"20px",
        "padding":"2px 8px","fontSize":"11px","fontWeight":"500"})

def empty_fig(msg="Aucune donnée disponible"):
    f=go.Figure()
    f.update_layout(**lay(300),annotations=[dict(text=msg,x=0.5,y=0.5,xref="paper",
        yref="paper",showarrow=False,font=dict(size=13,color=GRIS))])
    return f

def row1(a):
    """Un visuel pleine largeur"""
    return a

def row2(a,b):
    """Deux visuels côte à côte"""
    return html.Div([a,b],style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"16px"})

# ── Navigation selon rôle ─────────────────────────────────────
# Onglets communs aux deux rôles
NAV_COMMUN = [
    ("synthese",    "ti-layout-dashboard","Synthèse"),
    ("effectifs",   "ti-users",           "Effectifs"),
    ("performances","ti-chart-line",      "Performances"),
    ("etudiant",    "ti-user-search",     "Étudiant"),
    ("flux",        "ti-arrows-shuffle",  "Flux & Parcours"),
    ("comparaison", "ti-scale",           "Comparaison"),
]
# Onglet spécifique Responsable
NAV_RESPONSABLE = NAV_COMMUN + [("import_donnees","ti-upload","Import données")]
# Onglet spécifique Admin
NAV_ADMIN = NAV_COMMUN + [("gestion_suivi","ti-shield-check","Gestion & Suivi")]
# Tous les IDs possibles pour les callbacks
NAV_TOUS = NAV_COMMUN + [
    ("import_donnees","ti-upload","Import données"),
    ("gestion_suivi","ti-shield-check","Gestion & Suivi"),
]

# ── App ───────────────────────────────────────────────────────
app = dash.Dash(__name__,
    assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)),"assets"),
    suppress_callback_exceptions=True,title="UTS Dashboard",
    meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}])

app.layout = html.Div([
    dcc.Store(id="token-store",storage_type="session",data=None),
    dcc.Store(id="tab",data="synthese"),
    dcc.Store(id="selected-user-id",data=None),
    dcc.Store(id="user-action",data=None),
    dcc.Download(id="download-pdf"),
    dcc.Location(id="url"),
    # Composants statiques cachés
    html.Div([
        dcc.Input(id="search-input",type="text",debounce=False,
                  placeholder="",n_submit=0,style={"display":"none"}),
        html.Div(id="etudiant-result",style={"display":"none"}),
        html.Button(id="btn-search",n_clicks=0,children="",style={"display":"none"}),
    ],style={"position":"absolute","visibility":"hidden","pointerEvents":"none",
              "overflow":"hidden","height":"0","width":"0"}),
    html.Div(id="page-root"),
])

# ══════════════════════════════════════════════════════════════
# PAGE LOGIN
# ══════════════════════════════════════════════════════════════
def page_login(msg=""):
    return html.Div([
        html.Div([
            html.Div([
                # Logo + Nom sur la même ligne
                html.Div([
                    html.Img(
                        src="/assets/logo_uts.png",
                        style={"height":"52px","width":"auto","objectFit":"contain",
                               "marginRight":"12px","flexShrink":"0"},
                        alt="Logo UTS",
                    ),
                    html.Div("Université Thomas Sankara",
                             style={"fontSize":"18px","fontWeight":"700","color":BLEU,"lineHeight":"1.2"}),
                ],style={"display":"flex","alignItems":"center","justifyContent":"center","marginBottom":"10px"}),
                html.Div("Tableau de Bord Académique",
                         style={"fontSize":"17px","color":BLEU2,"fontWeight":"600",
                                "marginBottom":"28px","textAlign":"center"}),
            ],style={"textAlign":"center"}),
            html.Div(msg,id="login-msg",style={
                "background":"#FDECEA","color":ROUGE,"border":"1px solid #F5C0BC",
                "borderRadius":"8px","padding":"10px 14px","fontSize":"13px",
                "marginBottom":"16px","textAlign":"center",
                "display":"none" if not msg else "block"}),
            html.Div([
                html.Label("Adresse email",style={"fontSize":"12px","fontWeight":"600",
                    "color":"#374151","marginBottom":"6px","display":"block"}),
                dcc.Input(id="login-email",type="email",placeholder="email@uts.bf",
                    style={"width":"100%","padding":"10px 14px","border":"1px solid #D1D9E6",
                           "borderRadius":"8px","fontSize":"13.5px","outline":"none",
                           "marginBottom":"14px","boxSizing":"border-box"}),
                html.Label("Mot de passe",style={"fontSize":"12px","fontWeight":"600",
                    "color":"#374151","marginBottom":"6px","display":"block"}),
                dcc.Input(id="login-password",type="password",placeholder="••••••••",
                    style={"width":"100%","padding":"10px 14px","border":"1px solid #D1D9E6",
                           "borderRadius":"8px","fontSize":"13.5px","outline":"none",
                           "marginBottom":"22px","boxSizing":"border-box"},n_submit=0),
                html.Button([
                    html.I(className="ti ti-login",**{"aria-hidden":"true"},
                           style={"marginRight":"8px"}),
                    "Se connecter",
                ],id="login-btn",n_clicks=0,style={
                    "width":"100%","padding":"11px","background":BLEU,"color":"white",
                    "border":"none","borderRadius":"8px","fontSize":"14px",
                    "fontWeight":"600","cursor":"pointer"}),
            ]),
            html.Div("UTS Dashboard · DSI",style={"textAlign":"center","fontSize":"11px",
                     "color":GRIS,"marginTop":"28px"}),
        ],style={"background":"white","borderRadius":"14px","padding":"40px 36px",
                  "width":"380px","boxShadow":"0 4px 24px rgba(13,43,85,0.12)",
                  "border":"1px solid #E5E9F0"}),
    ],style={"minHeight":"100vh","display":"flex","alignItems":"center",
              "justifyContent":"center","background":GRIS3})

# ══════════════════════════════════════════════════════════════
# LAYOUT DASHBOARD
# ══════════════════════════════════════════════════════════════
def layout_dashboard(role,nom,prenom,ufr_user=None):
    # Navigation selon le rôle
    nav = NAV_ADMIN if role=="admin" else NAV_RESPONSABLE
    ini=(prenom[:1]+nom[:1]).upper() if prenom and nom else "US"
    rlbl="Administrateur" if role=="admin" else "Responsable"
    ufr_default=ufr_user if ufr_user else "Tous"
    ufr_disabled=(role=="responsable" and ufr_user is not None)

    return html.Div([
        # Sidebar
        html.Div([
            html.Div([
                html.Div([
                    # Logo aligné avec le texte
                    html.Img(
                        src="/assets/logo_uts.png",
                        style={"height":"42px","width":"42px",
                               "objectFit":"contain","objectPosition":"center",
                               "background":"white","borderRadius":"6px",
                               "padding":"3px","flexShrink":"0","marginRight":"10px"},
                        alt="Logo UTS",
                    ),
                    html.Div([
                        html.Div("UTS · Dashboard",
                                 style={"fontSize":"13px","fontWeight":"700",
                                        "color":"white","lineHeight":"1.3"}),
                        html.Div("Suivi académique décisionnel",
                                 style={"fontSize":"9px","color":"rgba(255,255,255,0.45)",
                                        "textTransform":"uppercase","letterSpacing":"0.04em",
                                        "marginTop":"2px"}),
                    ]),
                ],style={"display":"flex","alignItems":"center"}),
            ],style={"padding":"16px 16px 14px","borderBottom":"1px solid rgba(255,255,255,0.08)"}),

            html.Div("Navigation",style={"padding":"16px 16px 5px","fontSize":"10px",
                "fontWeight":"600","color":"rgba(255,255,255,0.30)","textTransform":"uppercase"}),

            # Créer TOUS les boutons mais cacher ceux qui ne correspondent pas au rôle
            html.Div([
                html.Button([
                    html.I(className=f"ti {ic}",**{"aria-hidden":"true"},
                           style={"fontSize":"15px","marginRight":"9px","opacity":"0.8"}),
                    html.Span(lbl),
                ],id=f"nav-{k}",className="nav-item",n_clicks=0,
                  style={"display":"none"} if (
                      (k=="gestion_suivi" and role!="admin") or
                      (k=="import_donnees" and role!="responsable")
                  ) else {})
                for k,ic,lbl in NAV_TOUS
            ]),

            # Bas de sidebar
            html.Div([
                html.Button([
                    html.I(className="ti ti-file-type-pdf",**{"aria-hidden":"true"},
                           style={"marginRight":"8px","fontSize":"14px"}),
                    "Exporter PDF",
                ],id="btn-export-pdf",n_clicks=0,style={
                    "width":"100%","background":"rgba(255,255,255,0.08)",
                    "color":"rgba(255,255,255,0.70)","border":"1px solid rgba(255,255,255,0.15)",
                    "borderRadius":"6px","padding":"8px 12px","fontSize":"12px",
                    "cursor":"pointer","marginBottom":"6px"}),
                html.Button([
                    html.I(className="ti ti-logout",**{"aria-hidden":"true"},
                           style={"marginRight":"8px","fontSize":"14px"}),
                    "Déconnexion",
                ],id="btn-logout",n_clicks=0,style={
                    "width":"100%","background":"rgba(255,255,255,0.08)",
                    "color":"rgba(255,255,255,0.70)","border":"1px solid rgba(255,255,255,0.15)",
                    "borderRadius":"6px","padding":"8px 12px","fontSize":"12px",
                    "cursor":"pointer","marginBottom":"8px"}),
                html.Div("Données 2019 – 2024"),
                html.Div("31 098 étudiants"),
                html.Div("3 UFR · 24 filières"),
            ],style={"marginTop":"auto","padding":"12px 16px",
                      "borderTop":"1px solid rgba(255,255,255,0.07)",
                      "fontSize":"10px","color":"rgba(255,255,255,0.28)","lineHeight":"1.8"}),
        ],className="sidebar"),

        # Main
        html.Div([
            # Topbar
            html.Div([
                html.Div([
                    html.I(className="ti ti-home",**{"aria-hidden":"true"},
                           style={"fontSize":"12px","color":"#9CA3AF"}),
                    html.Span(" / "),
                    html.Span(id="topbar-name",children="Synthèse",
                              style={"color":"#111827","fontWeight":"600"}),
                ],style={"display":"flex","alignItems":"center","gap":"4px",
                          "fontSize":"12.5px","color":"#9CA3AF"}),
                html.Div([
                    html.Span(rlbl,style={
                        "fontSize":"11px",
                        "background":"#E6F5EF" if role=="responsable" else "#EBF0FA",
                        "color":VERT if role=="responsable" else BLEU,
                        "border":f"1px solid {'#B7DFCF' if role=='responsable' else '#C5D5F0'}",
                        "borderRadius":"20px","padding":"3px 10px","fontWeight":"500"}),
                    html.Div([
                        html.Div(ini,style={"width":"28px","height":"28px","borderRadius":"50%",
                                             "background":BLEU,"color":"white","display":"flex",
                                             "alignItems":"center","justifyContent":"center",
                                             "fontSize":"11px","fontWeight":"700"}),
                        html.Span(f"{prenom} {nom}",style={"fontSize":"12px","color":"#4B5563"}),
                    ],style={"display":"flex","alignItems":"center","gap":"7px"}),
                ],style={"display":"flex","alignItems":"center","gap":"10px"}),
            ],className="topbar"),

            # Filtres
            html.Div([
                html.Div([
                    html.I(className="ti ti-adjustments-horizontal",
                           **{"aria-hidden":"true"},style={"fontSize":"13px"}),
                    html.Span(" Filtres"),
                ],style={"fontSize":"11px","fontWeight":"600","color":"#9CA3AF",
                          "textTransform":"uppercase","letterSpacing":"0.06em",
                          "whiteSpace":"nowrap","alignSelf":"flex-end","paddingBottom":"4px","flexShrink":"0"}),
                *[html.Div([
                    html.Label(lbl,style={"fontSize":"10px","fontWeight":"600","color":"#9CA3AF",
                        "textTransform":"uppercase","letterSpacing":"0.05em",
                        "marginBottom":"3px","display":"block"}),
                    dd(id_,opts,default,disabled=(id_=="f-ufr" and ufr_disabled))
                ],style={"display":"flex","flexDirection":"column","minWidth":"110px","maxWidth":"155px","flex":"1"})
                  for lbl,id_,opts,default in [
                    ("UFR","f-ufr",[{"label":v,"value":v} for v in UFRS],ufr_default),
                    ("Filière","f-fil",opts_fil(ufr_default),"Toutes"),
                    ("Niveau","f-niv",[{"label":v,"value":v} for v in NIVEAUX],"Tous"),
                    ("Semestre","f-sem",[{"label":v,"value":v} for v in SEMS],"Tous"),
                    ("Session","f-ses",[{"label":v,"value":v} for v in SESSIONS],"Normale"),
                    ("Année","f-an",[{"label":v,"value":v} for v in ANNEES],"Toutes"),
                    ("Genre","f-gen",[{"label":{"Tous":"Tous","M":"Masculin","F":"Féminin"}.get(v,v),"value":v} for v in ["Tous","M","F"]],"Tous"),
                ]],
            ],id="filtres-bar",className="filtres-wrap"),

            dcc.Loading(
                id="loading-content",
                type="circle",
                color=BLEU,
                children=html.Div(id="content",className="page-content"),
                style={"minHeight":"200px"},
            ),
        ],className="main-content"),
    ],className="layout-root")

# ── Callbacks Auth ────────────────────────────────────────────
@app.callback(Output("page-root","children"),Input("token-store","data"))
def router(token):
    if not token: return page_login()
    payload=decode_token(token)
    if not payload: return page_login("Session expirée. Veuillez vous reconnecter.")
    return layout_dashboard(payload["role"],payload["nom"],payload["prenom"],payload.get("ufr"))

@app.callback(
    Output("token-store","data"),
    Output("login-msg","children"),
    Output("login-msg","style"),
    Input("login-btn","n_clicks"),
    Input("login-password","n_submit"),
    State("login-email","value"),
    State("login-password","value"),
    prevent_initial_call=True,
)
def login(n1,n2,email,password):
    err={"background":"#FDECEA","color":ROUGE,"border":"1px solid #F5C0BC",
         "borderRadius":"8px","padding":"10px 14px","fontSize":"13px",
         "marginBottom":"16px","textAlign":"center","display":"block"}
    ok={"display":"none"}
    if not email or not password: return None,"Veuillez renseigner l'email et le mot de passe.",err
    user=authenticate(email.strip(),password)
    if not user: return None,"Email ou mot de passe incorrect.",err
    token=create_token(user["id"],user["email"],user["role"],
                       user["nom"],user["prenom"],user.get("ufr"))
    return token,"",ok

@app.callback(
    Output("token-store","data",allow_duplicate=True),
    Input("btn-logout","n_clicks"),prevent_initial_call=True)
def logout(n): return None if n else dash.no_update

# ── Navigation ────────────────────────────────────────────────
@app.callback(
    Output("tab","data"),
    [Input(f"nav-{k}","n_clicks") for k,_,_ in NAV_TOUS],
    prevent_initial_call=True,
)
def nav_click(*_):
    if not ctx.triggered: return "synthese"
    return ctx.triggered[0]["prop_id"].split(".")[0].replace("nav-","")

@app.callback(Output("topbar-name","children"),Input("tab","data"))
def topname(t): return {k:l for k,_,l in NAV_TOUS}.get(t,"Synthèse")

@app.callback(
    [Output(f"nav-{k}","className") for k,_,_ in NAV_TOUS],
    Input("tab","data"))
def nav_cls(t): return ["nav-item active" if k==t else "nav-item" for k,_,_ in NAV_TOUS]

@app.callback(Output("filtres-bar","style"),Input("tab","data"))
def toggle_filtres(tab):
    return {"display":"none"} if tab in ("gestion_suivi","import_donnees") else {}

@app.callback(Output("f-fil","options"),Output("f-fil","value"),Input("f-ufr","value"))
def upd_fil(ufr): return opts_fil(ufr),"Toutes"

# ── Recherche étudiant ────────────────────────────────────────
@app.callback(
    Output("etudiant-result","children"),
    Output("etudiant-result","style"),
    Input("btn-search","n_clicks"),
    Input("search-input","n_submit"),
    State("search-input","value"),
    prevent_initial_call=True,
)
def search_etudiant(n_btn,n_submit,query):
    visible={"display":"block"}
    if not query or len(str(query).strip())<2:
        return html.Div("Saisissez au moins 2 caractères.",
            style={"color":GRIS,"fontSize":"13px","textAlign":"center","paddingTop":"24px"}),visible
    q=str(query).strip().upper()
    et=DATA["etudiants"].copy()
    et["nom_c"]=(et["prenom"].astype(str).str.upper()+" "+et["nom"].astype(str).str.upper())
    mask=(et["matricule"].astype(str).str.upper().str.contains(q,na=False)|
          et["nom"].astype(str).str.upper().str.contains(q,na=False)|
          et["prenom"].astype(str).str.upper().str.contains(q,na=False)|
          et["nom_c"].str.contains(q,na=False))
    results=et[mask].head(5)
    if len(results)==0:
        return html.Div("Aucun étudiant trouvé.",
            style={"color":GRIS,"fontSize":"13px","textAlign":"center","paddingTop":"24px"}),visible

    cards=[]
    for _,row in results.iterrows():
        mat=str(row["matricule"])
        nom_c=f"{s(row['prenom'])} {s(row['nom'])}"
        res_e=DATA["resultats"][DATA["resultats"]["matricule"]==mat].copy()
        res_n=res_e[res_e["session"]=="Normale"].sort_values(["annee_academique","semestre"])
        nb_res=len(res_n)
        nb_adm=int((res_n["statut"]=="Admis").sum())
        moy_g=res_e[res_e["moyenne_generale"].notna()]["moyenne_generale"]
        moy_g=pd.to_numeric(moy_g,errors="coerce").mean()
        moy_s=f"{float(moy_g):.2f}/20" if pd.notna(moy_g) else "—"
        taux=round(100*nb_adm/nb_res,1) if nb_res>0 else 0
        ini=(s(row["prenom"])[:1]+s(row["nom"])[:1]).upper()

        # Graphique parcours
        moyennes=res_n.copy()
        moyennes["moyenne_generale"]=pd.to_numeric(moyennes["moyenne_generale"],errors="coerce")
        moyennes=moyennes.dropna(subset=["moyenne_generale"])
        graphique=[]
        if len(moyennes)>0:
            labels=[f"{s(r['niveau'])}{s(r['semestre'])}" for _,r in moyennes.iterrows()]
            valeurs=[float(r["moyenne_generale"]) for _,r in moyennes.iterrows()]
            clrs=[VERT if v>=10 else ROUGE for v in valeurs]
            fig_p=go.Figure(go.Bar(x=labels,y=valeurs,marker_color=clrs,
                text=[f"{v:.2f}" for v in valeurs],textposition="outside"))
            fig_p.add_hline(y=10,line_dash="dot",line_color=BLEU,line_width=1.5)
            fig_p.update_layout(**lay(220,margin=dict(l=12,r=12,t=30,b=8)),
                yaxis=ax(ticksuffix="/20"),yaxis_range=[0,22])
            graphique=[dcc.Graph(figure=fig_p,
                config={"displayModeBar":True,
                        "toImageButtonOptions":{"filename":f"parcours_{mat}"},
                        "responsive":True},
                style={"width":"100%"})]

        tbl_rows=[]
        for _,r in res_n.iterrows():
            moy_r=f"{float(pd.to_numeric(r.get('moyenne_generale'),errors='coerce')):.2f}/20" if pd.notna(r.get("moyenne_generale")) else "—"
            rang_r=str(int(r["rang_promo"])) if pd.notna(r.get("rang_promo")) else "—"
            tbl_rows.append(html.Tr([
                html.Td(s(r.get("annee_academique","")),style={"padding":"7px 10px","fontSize":"12px","borderBottom":"1px solid #E5E9F0","color":GRIS}),
                html.Td(s(r.get("niveau","")),style={"padding":"7px 10px","fontWeight":"600","borderBottom":"1px solid #E5E9F0"}),
                html.Td(s(r.get("semestre","")),style={"padding":"7px 10px","borderBottom":"1px solid #E5E9F0"}),
                html.Td(s(r.get("filiere_code","")),style={"padding":"7px 10px","color":GRIS,"fontSize":"11.5px","borderBottom":"1px solid #E5E9F0"}),
                html.Td(html.B(moy_r),style={"padding":"7px 10px","borderBottom":"1px solid #E5E9F0"}),
                html.Td(badge(s(r.get("statut",""))),style={"padding":"7px 10px","borderBottom":"1px solid #E5E9F0"}),
                html.Td(badge(s(r.get("mention","")) if s(r.get("statut",""))=="Admis" else ""),style={"padding":"7px 10px","borderBottom":"1px solid #E5E9F0"}),
                html.Td(rang_r,style={"padding":"7px 10px","color":GRIS,"fontSize":"11.5px","borderBottom":"1px solid #E5E9F0"}),
            ]))

        cards.append(html.Div([
            html.Div([
                html.Div(ini,style={"width":"48px","height":"48px","borderRadius":"50%",
                    "background":BLEU,"color":"white","display":"flex","alignItems":"center",
                    "justifyContent":"center","fontSize":"18px","fontWeight":"700","flexShrink":"0"}),
                html.Div([
                    html.Div(nom_c,style={"fontSize":"16px","fontWeight":"700","color":"#111827"}),
                    html.Div(f"{mat} · UFR/{s(row.get('ufr',''))} · {s(row.get('filiere_initiale',''))} · Entrée {s(row.get('annee_entree',''))}",
                             style={"fontSize":"12px","color":GRIS,"marginTop":"2px"}),
                ]),
            ],style={"display":"flex","alignItems":"center","gap":"14px","marginBottom":"14px",
                      "paddingBottom":"12px","borderBottom":"1px solid #E5E9F0"}),
            html.Div([
                html.Div([html.Div("Genre",style={"fontSize":"10.5px","color":GRIS,"fontWeight":"500","textTransform":"uppercase","marginBottom":"3px"}),
                    html.Div({"M":"Masculin","F":"Féminin"}.get(s(row.get("genre","")),s(row.get("genre",""))),style={"fontSize":"13px","fontWeight":"600"})],
                    style={"background":GRIS3,"borderRadius":"6px","padding":"10px 12px"}),
                html.Div([html.Div("Moyenne générale",style={"fontSize":"10.5px","color":GRIS,"fontWeight":"500","textTransform":"uppercase","marginBottom":"3px"}),
                    html.Div(moy_s,style={"fontSize":"13px","fontWeight":"600",
                        "color":VERT if pd.notna(moy_g) and float(moy_g)>=10 else ROUGE})],
                    style={"background":GRIS3,"borderRadius":"6px","padding":"10px 12px"}),
                html.Div([html.Div("Taux de réussite",style={"fontSize":"10.5px","color":GRIS,"fontWeight":"500","textTransform":"uppercase","marginBottom":"3px"}),
                    html.Div(f"{taux}%",style={"fontSize":"13px","fontWeight":"600",
                        "color":VERT if taux>=50 else ORANGE})],
                    style={"background":GRIS3,"borderRadius":"6px","padding":"10px 12px"}),
                html.Div([html.Div("Semestres complétés",style={"fontSize":"10.5px","color":GRIS,"fontWeight":"500","textTransform":"uppercase","marginBottom":"3px"}),
                    html.Div(str(nb_res),style={"fontSize":"13px","fontWeight":"600"})],
                    style={"background":GRIS3,"borderRadius":"6px","padding":"10px 12px"}),
            ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(130px,1fr))",
                      "gap":"10px","marginBottom":"16px"}),
            *([sep("Évolution de la moyenne par semestre")]+graphique if graphique else []),
            sep("Parcours détaillé"),
            html.Div(html.Table([
                html.Thead(html.Tr([html.Th(c,style={"padding":"8px 10px","fontSize":"10.5px",
                    "fontWeight":"600","color":GRIS,"textTransform":"uppercase",
                    "letterSpacing":"0.05em","borderBottom":"1px solid #E5E9F0",
                    "background":GRIS3,"whiteSpace":"nowrap"})
                    for c in ["Année","Niveau","Semestre","Filière","Moyenne","Statut","Mention","Rang"]])),
                html.Tbody(tbl_rows),
            ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px"}),
            style={"overflowX":"auto","marginBottom":"14px"}),
        ],style={"background":"white","border":"1px solid #E5E9F0","borderRadius":"10px",
                  "padding":"16px 20px","marginBottom":"14px",
                  "boxShadow":"0 1px 3px rgba(13,43,85,0.06)"}))

    intro=html.Div(f"{len(results)} résultat(s) pour « {query} »",
        style={"fontSize":"12.5px","color":GRIS,"marginBottom":"12px","fontWeight":"500"}) if len(results)>1 else None
    return html.Div([intro]+cards if intro else html.Div(cards)),visible

# ── Callback principal ────────────────────────────────────────
@app.callback(
    Output("content","children"),
    [Input("tab","data"),Input("f-ufr","value"),Input("f-fil","value"),
     Input("f-niv","value"),Input("f-sem","value"),Input("f-ses","value"),
     Input("f-an","value"),Input("f-gen","value"),Input("token-store","data")],
)
def render(tab,ufr,fil,niv,sem,ses,an,gen,token):
    if not token: return html.Div()
    payload=decode_token(token)
    if not payload: return html.Div()
    role=payload["role"]

    # Contrôle d'accès
    if tab=="gestion_suivi" and role!="admin":
        return html.Div("Accès refusé.",style={"padding":"40px","color":ROUGE})
    if tab=="import_donnees" and role!="responsable":
        return html.Div("Accès refusé.",style={"padding":"40px","color":ROUGE})

    if tab=="gestion_suivi":   return pg_gestion_suivi(token)
    if tab=="import_donnees":  return pg_import_donnees(token)
    if tab=="etudiant":        return pg_etudiant_layout()

    df=filter_data(ufr,fil,niv,sem,ses,an,gen)
    kps=compute_kpis(df)
    ses_lbl=ses or "Normale"
    fil_lbl=fil if fil and fil!="Toutes" else "Toutes filières"
    ufr_lbl=f"UFR/{ufr}" if ufr and ufr!="Tous" else "Toutes UFR"
    an_lbl=an if an and an!="Toutes" else "2019-2024"
    niv_lbl=niv if niv and niv!="Tous" else "Tous niveaux"

    fns={"synthese":pg_synthese,"effectifs":pg_effectifs,
         "performances":pg_performances,"flux":pg_flux,"comparaison":pg_comparaison}
    try:
        return fns.get(tab,pg_synthese)(df,kps,ufr,an,ses,fil_lbl,ses_lbl,ufr_lbl,an_lbl,niv_lbl)
    except Exception as e:
        import traceback
        return html.Div([
            html.Div("Erreur d'affichage",style={"fontSize":"16px","fontWeight":"600","color":ROUGE,"marginBottom":"8px"}),
            html.Pre(traceback.format_exc(),style={"fontSize":"11px","color":"#4B5563",
                "background":GRIS3,"padding":"12px","borderRadius":"6px","overflow":"auto"}),
        ],style={"padding":"20px"})

# ── Layout onglet Étudiant ────────────────────────────────────
def pg_etudiant_layout():
    """
    Onglet étudiant - utilise les IDs définis dans le layout statique
    pour éviter les conflits Dash de duplicate IDs
    """
    return html.Div([
        html.Div([
            html.Div("Suivi individuel de l'étudiant",
                     style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div("Recherchez par nom, prénom ou matricule pour voir le parcours complet",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"16px"}),
        html.Div([
            html.I(className="ti ti-search",**{"aria-hidden":"true"},
                   style={"position":"absolute","left":"13px","top":"50%",
                          "transform":"translateY(-50%)","color":"#9CA3AF",
                          "fontSize":"16px","zIndex":"1"}),
            dcc.Input(
                id="search-input",
                type="text",
                placeholder="Ex : TANKOANO Ali  ou  UTS2217885",
                n_submit=0,
                debounce=False,
                style={"width":"100%","padding":"11px 130px 11px 42px",
                       "border":"1px solid #D1D9E6","borderRadius":"10px",
                       "fontSize":"13.5px","outline":"none",
                       "boxSizing":"border-box","display":"block"},
            ),
            html.Button([
                html.I(className="ti ti-search",**{"aria-hidden":"true"},
                       style={"marginRight":"6px"}),
                "Rechercher",
            ],id="btn-search",n_clicks=0,style={
                "position":"absolute","right":"6px","top":"50%",
                "transform":"translateY(-50%)",
                "background":BLEU,"color":"white","border":"none",
                "borderRadius":"7px","padding":"7px 14px",
                "fontSize":"12px","fontWeight":"500","cursor":"pointer",
                "display":"block"}),
        ],style={"position":"relative","marginBottom":"16px"}),
        html.Div(id="etudiant-result"),
    ],className="tab-content")

# ══════════════════════════════════════════════════════════════
# ONGLET IMPORT DONNÉES (Responsable uniquement)
# ══════════════════════════════════════════════════════════════
def pg_import_donnees(token):
    payload=decode_token(token)
    if not payload:
        return html.Div("Erreur de session.",style={"padding":"40px","color":ROUGE})
    nom_user=f"{payload.get('prenom','')} {payload.get('nom','')}".strip()
    email=payload.get("email","")
    ufr_user=payload.get("ufr")

    # Historique des imports du responsable
    try:
        mes_imports=lister_mes_imports(email)
    except Exception as e:
        mes_imports=[]; print(f"lister_mes_imports: {e}")

    rows_imp=[]
    for imp in mes_imports:
        statut_b=badge(imp.get("statut",""))
        rows_imp.append(html.Tr([
            html.Td(imp.get("date",""),style={"padding":"8px 12px","fontSize":"12px","color":GRIS}),
            html.Td(imp.get("fichier",""),style={"padding":"8px 12px","fontSize":"12px","fontWeight":"500"}),
            html.Td(imp.get("ufr",""),style={"padding":"8px 12px","fontSize":"12px"}),
            html.Td(imp.get("semestre",""),style={"padding":"8px 12px","fontSize":"12px"}),
            html.Td(imp.get("annee",""),style={"padding":"8px 12px","fontSize":"12px"}),
            html.Td(f"{imp.get('nb',0):,}" if imp.get('nb') else "—",style={"padding":"8px 12px","fontSize":"12px"}),
            html.Td(statut_b,style={"padding":"8px 12px"}),
        ],style={"borderBottom":"1px solid #E5E9F0"}))

    # UFR de l'utilisateur (pré-sélectionnée si restreinte)
    ufr_options=[{"label":v,"value":v} for v in (["ST","SEG","SJP"] if not ufr_user else [ufr_user])]

    return html.Div([
        html.Div([
            html.Div("Import de données",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div(f"Chargez les fichiers de délibération — {nom_user}",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"20px"}),

        ccard("Uploader un fichier de délibération",
            "Format accepté : CSV ou Excel (.csv, .xlsx) — 1 fichier par UFR et semestre",
            html.Div([
                html.Div([
                    *[html.Div([
                        html.Label(lbl,style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dd(id_,opts,default,disabled=dsbl)
                    ],style={"flex":"1"})
                    for lbl,id_,opts,default,dsbl in [
                        ("UFR *","up-ufr",ufr_options,
                         ufr_user if ufr_user else "ST",
                         ufr_user is not None),
                        ("Filière *","up-fil",opts_fil(ufr_user or "ST"),"Toutes",False),
                        ("Semestre *","up-sem",[{"label":v,"value":v} for v in ["S1","S2","S3","S4","S5","S6"]],"S1",False),
                        ("Année académique *","up-annee",[{"label":v,"value":v} for v in ANNEES if v!="Toutes"],"2024-2025",False),
                        ("Session *","up-session",[{"label":v,"value":v} for v in ["Normale","Rattrapage"]],"Normale",False),
                    ]],
                ],style={"display":"flex","gap":"12px","flexWrap":"wrap","marginBottom":"16px"}),

                dcc.Upload(id="upload-fichier",
                    children=html.Div([
                        html.I(className="ti ti-cloud-upload",**{"aria-hidden":"true"},
                               style={"fontSize":"32px","color":GRIS,"marginBottom":"10px"}),
                        html.Div("Glissez votre fichier ici ou cliquez pour parcourir",
                                 style={"fontSize":"13px","color":"#4B5563","fontWeight":"500"}),
                        html.Div("Formats acceptés : .csv  .xlsx  .xls",
                                 style={"fontSize":"11.5px","color":GRIS,"marginTop":"6px"}),
                        html.Div("Le fichier doit contenir : MATRICULE, NOM, PRENOM, GENRE, MOYENNE, STATUT",
                                 style={"fontSize":"10.5px","color":GRIS,"marginTop":"4px"}),
                    ],style={"textAlign":"center","padding":"28px"}),
                    style={"border":f"2px dashed {GRIS2}","borderRadius":"10px",
                           "cursor":"pointer","marginBottom":"14px",
                           "transition":"border-color 0.2s"},
                    accept=".csv,.xlsx,.xls"),

                html.Div(id="upload-status"),
            ])),

        sep("Mes imports récents"),
        html.Div(html.Table([
            html.Thead(html.Tr([html.Th(c,style={"padding":"8px 12px","fontSize":"10.5px",
                "fontWeight":"600","color":GRIS,"textTransform":"uppercase",
                "letterSpacing":"0.05em","borderBottom":"1px solid #E5E9F0","background":GRIS3})
                for c in ["Date","Fichier","UFR","Semestre","Année","Étudiants","Statut"]])),
            html.Tbody(rows_imp if rows_imp else [
                html.Tr([html.Td("Aucun import effectué pour le moment",
                    colSpan=7,style={"padding":"20px","textAlign":"center","color":GRIS})])
            ]),
        ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px",
                  "background":"white","borderRadius":"10px","border":"1px solid #E5E9F0"}),
        style={"overflowX":"auto"}),

    ],className="tab-content")

# ══════════════════════════════════════════════════════════════
# ONGLET GESTION & SUIVI (Admin uniquement)
# ══════════════════════════════════════════════════════════════
def pg_gestion_suivi(token):
    try:
        utilisateurs=lister_utilisateurs()
    except Exception as e:
        utilisateurs=[]; print(f"lister_utilisateurs: {e}")
    try:
        imports=lister_imports()
    except Exception as e:
        imports=[]; print(f"lister_imports: {e}")
    try:
        exports=lister_exports()
    except Exception as e:
        exports=[]; print(f"lister_exports: {e}")

    # Responsables uniquement (admin gère les responsables)
    responsables=[u for u in utilisateurs if u["role"]=="responsable"]
    admins=[u for u in utilisateurs if u["role"]=="admin"]

    def user_rows(users):
        rows=[]
        for u in users:
            role_b=html.Span(u["role"],style={
                "background":"#EBF0FA" if u["role"]=="admin" else "#E6F5EF",
                "color":BLEU if u["role"]=="admin" else VERT,
                "border":f"1px solid {'#C5D5F0' if u['role']=='admin' else '#B7DFCF'}",
                "borderRadius":"20px","padding":"2px 8px","fontSize":"11px","fontWeight":"500"})
            actif_b=html.Span("Actif" if u["actif"] else "Inactif",style={
                "background":"#E6F5EF" if u["actif"] else "#FDECEA",
                "color":VERT if u["actif"] else ROUGE,
                "borderRadius":"20px","padding":"2px 8px","fontSize":"11px","fontWeight":"500"})
            # Boutons d'action
            btn_style_base = {
                "border":"none","borderRadius":"5px","padding":"4px 10px",
                "fontSize":"11px","fontWeight":"500","cursor":"pointer","marginRight":"4px"
            }
            actions = html.Div([
                # Bouton modifier - stocke l'ID dans data-id
                html.Button([
                    html.I(className="ti ti-edit",**{"aria-hidden":"true"},
                           style={"marginRight":"4px"}),
                    "Modifier",
                ], id={"type":"btn-modifier","index":u["id"]}, n_clicks=0,
                   style={**btn_style_base,"background":"#E8F0FE","color":BLEU2}),
                # Bouton désactiver/activer
                html.Button([
                    html.I(className=f"ti {'ti-eye-off' if u['actif'] else 'ti-eye'}",
                           **{"aria-hidden":"true"},style={"marginRight":"4px"}),
                    "Désactiver" if u["actif"] else "Activer",
                ], id={"type":"btn-toggle","index":u["id"]}, n_clicks=0,
                   style={**btn_style_base,
                       "background":"#FEF0E0" if u["actif"] else "#E6F5EF",
                       "color":ORANGE if u["actif"] else VERT}),
                # Bouton supprimer
                html.Button([
                    html.I(className="ti ti-trash",**{"aria-hidden":"true"},
                           style={"marginRight":"4px"}),
                    "Suppr.",
                ], id={"type":"btn-supprimer","index":u["id"]}, n_clicks=0,
                   style={**btn_style_base,"background":"#FDECEA","color":ROUGE}),
            ],style={"display":"flex","alignItems":"center","gap":"2px"})

            rows.append(html.Tr([
                html.Td(f"{u['prenom']} {u['nom']}",style={"padding":"9px 12px","fontWeight":"500"}),
                html.Td(u["email"],style={"padding":"9px 12px","color":GRIS,"fontSize":"12px"}),
                html.Td(role_b,style={"padding":"9px 12px"}),
                html.Td(u.get("ufr") or "Toutes",style={"padding":"9px 12px","fontSize":"12px"}),
                html.Td(actif_b,style={"padding":"9px 12px"}),
                html.Td(u["derniere_connexion"],style={"padding":"9px 12px","color":GRIS,"fontSize":"12px"}),
                html.Td(actions,style={"padding":"6px 12px"}),
            ],style={"borderBottom":"1px solid #E5E9F0"}))
        return rows

    # Tableau imports
    imp_rows=[html.Tr([
        html.Td(i.get("date",""),style={"padding":"8px 12px","fontSize":"11.5px","color":GRIS}),
        html.Td(i.get("fichier",""),style={"padding":"8px 12px","fontSize":"11.5px","fontWeight":"500"}),
        html.Td(i.get("ufr",""),style={"padding":"8px 12px","fontSize":"11.5px"}),
        html.Td(i.get("semestre",""),style={"padding":"8px 12px","fontSize":"11.5px"}),
        html.Td(i.get("annee",""),style={"padding":"8px 12px","fontSize":"11.5px"}),
        html.Td(f"{i.get('nb',0):,}" if i.get('nb') else "—",style={"padding":"8px 12px","fontSize":"11.5px"}),
        html.Td(badge(i.get("statut","")),style={"padding":"8px 12px"}),
        html.Td(str(i.get("message",""))[:60]+"..." if len(str(i.get("message","")))>60 else str(i.get("message","")),
                style={"padding":"8px 12px","fontSize":"10.5px","color":GRIS}),
    ],style={"borderBottom":"1px solid #E5E9F0"}) for i in imports] or [
        html.Tr([html.Td("Aucun import enregistré",colSpan=8,
                         style={"padding":"20px","textAlign":"center","color":GRIS})])]

    # Tableau exports
    exp_rows=[html.Tr([
        html.Td(e.get("date",""),style={"padding":"8px 12px","fontSize":"11.5px","color":GRIS}),
        html.Td(e.get("utilisateur",""),style={"padding":"8px 12px","fontSize":"11.5px","fontWeight":"500"}),
        html.Td(e.get("email",""),style={"padding":"8px 12px","fontSize":"11px","color":GRIS}),
        html.Td(html.Span(e.get("role",""),style={
            "background":"#EBF0FA" if e.get("role")=="admin" else "#E6F5EF",
            "color":BLEU if e.get("role")=="admin" else VERT,
            "borderRadius":"20px","padding":"2px 8px","fontSize":"10px"}),
            style={"padding":"8px 12px"}),
        html.Td(e.get("onglet",""),style={"padding":"8px 12px","fontSize":"11.5px"}),
        html.Td(e.get("type","PDF"),style={"padding":"8px 12px","fontSize":"11.5px"}),
        html.Td(str(e.get("filtres",""))[:50],style={"padding":"8px 12px","fontSize":"10.5px","color":GRIS}),
    ],style={"borderBottom":"1px solid #E5E9F0"}) for e in exports] or [
        html.Tr([html.Td("Aucun export enregistré",colSpan=7,
                         style={"padding":"20px","textAlign":"center","color":GRIS})])]

    th=lambda cols:[html.Th(c,style={"padding":"8px 12px","fontSize":"10.5px","fontWeight":"600",
        "color":GRIS,"textTransform":"uppercase","letterSpacing":"0.05em",
        "borderBottom":"1px solid #E5E9F0","background":GRIS3}) for c in cols]

    return html.Div([
        html.Div([
            html.Div("Gestion & Suivi",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div("Vue d'ensemble de l'activité du système — Admin uniquement",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"20px"}),

        # KPIs résumé
        html.Div([
            kpi_card("Responsables actifs",str(len([u for u in responsables if u["actif"]])),
                     couleur=VERT,sub="Comptes actifs"),
            kpi_card("Total imports",str(len(imports)),couleur=BLEU,sub="50 derniers"),
            kpi_card("Total exports",str(len(exports)),couleur=BLEU2,sub="100 derniers"),
            kpi_card("Admins",str(len(admins)),couleur=OR,sub="Comptes admin"),
        ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(150px,1fr))",
                  "gap":"12px","marginBottom":"20px"}),

        # ── Gestion comptes ───────────────────────────────────
        sep("Comptes Responsables — gestion"),
        ccard("Liste des responsables pédagogiques","Modifier, désactiver ou supprimer un compte existant",
            html.Div([
                html.Div(id="action-user-msg"),
                html.Div(id="modif-form-zone"),
                html.Table([
                    html.Thead(html.Tr(th(["Utilisateur","Email","Rôle","UFR","Dernière connexion","Actions"]))),
                    html.Tbody(user_rows(responsables) or [
                        html.Tr([html.Td("Aucun responsable créé",colSpan=6,
                                         style={"padding":"20px","textAlign":"center","color":GRIS})])]),
                ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px"}),
            ],style={"overflowX":"auto"})),

        sep("Créer un nouveau compte responsable"),
        ccard("Nouveau compte","Ajouter un responsable pédagogique ou un administrateur",
            html.Div([
                html.Div([
                    *[html.Div([
                        html.Label(lbl,style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dcc.Input(id=id_,type=typ,placeholder=ph,
                            style={"width":"100%","padding":"8px 12px","border":"1px solid #D1D9E6",
                                   "borderRadius":"6px","fontSize":"13px","boxSizing":"border-box"})
                    ],style={"flex":flex})
                    for lbl,id_,typ,ph,flex in [
                        ("Nom *","new-nom","text","Ouédraogo","1"),
                        ("Prénom *","new-prenom","text","Ibrahim","1"),
                        ("Email *","new-email","email","resp@uts.bf","2"),
                    ]],
                ],style={"display":"flex","gap":"12px","marginBottom":"12px"}),
                html.Div([
                    html.Div([
                        html.Label("Mot de passe *",style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dcc.Input(id="new-password",type="password",placeholder="••••••••",
                            style={"width":"100%","padding":"8px 12px","border":"1px solid #D1D9E6",
                                   "borderRadius":"6px","fontSize":"13px","boxSizing":"border-box"})],
                      style={"flex":"2"}),
                    html.Div([
                        html.Label("Rôle *",style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dd("new-role",[{"label":"Responsable pédagogique","value":"responsable"},
                                       {"label":"Administrateur","value":"admin"}],"responsable")],
                      style={"flex":"1"}),
                    html.Div([
                        html.Label("UFR (restreint)",style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dd("new-ufr",[{"label":"Toutes UFR (aucune restriction)","value":""},
                                      {"label":"UFR/ST uniquement","value":"ST"},
                                      {"label":"UFR/SEG uniquement","value":"SEG"},
                                      {"label":"UFR/SJP uniquement","value":"SJP"}],"")],
                      style={"flex":"1"}),
                ],style={"display":"flex","gap":"12px","marginBottom":"14px"}),

                html.Div([
                    html.I(className="ti ti-info-circle",**{"aria-hidden":"true"},
                           style={"marginRight":"6px","color":BLEU2,"flexShrink":"0"}),
                    "Si UFR est renseignée, le responsable ne verra que les données de cette UFR et son filtre UFR sera verrouillé.",
                ],style={"fontSize":"12px","color":"#4B5563","background":"#E8F0FE",
                          "borderRadius":"6px","padding":"8px 12px","marginBottom":"12px",
                          "display":"flex","alignItems":"center"}),

                html.Button([
                    html.I(className="ti ti-user-plus",**{"aria-hidden":"true"},
                           style={"marginRight":"8px"}),
                    "Créer le compte",
                ],id="btn-creer-user",n_clicks=0,style={
                    "background":BLEU,"color":"white","border":"none","borderRadius":"6px",
                    "padding":"9px 18px","fontSize":"13px","fontWeight":"500","cursor":"pointer"}),
                html.Div(id="creer-user-status",style={"marginTop":"10px","fontSize":"13px"}),
            ])),

        # ── Suivi des imports ─────────────────────────────────
        sep("Suivi des imports — tous les responsables"),
        html.Div(html.Table([
            html.Thead(html.Tr(th(["Date","Fichier","UFR","Semestre","Année","Étudiants","Statut","Message"]))),
            html.Tbody(imp_rows),
        ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px",
                  "background":"white","borderRadius":"10px","border":"1px solid #E5E9F0"}),
        style={"overflowX":"auto","marginBottom":"16px"}),

        # ── Suivi des exports ─────────────────────────────────
        sep("Suivi des exports PDF — tous les utilisateurs"),
        html.Div(html.Table([
            html.Thead(html.Tr(th(["Date","Utilisateur","Email","Rôle","Onglet","Type","Filtres"]))),
            html.Tbody(exp_rows),
        ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px",
                  "background":"white","borderRadius":"10px","border":"1px solid #E5E9F0"}),
        style={"overflowX":"auto"}),

    ],className="tab-content")

# ── Callbacks Administration ──────────────────────────────────
@app.callback(Output("up-fil","options"),Output("up-fil","value"),
              Input("up-ufr","value"),prevent_initial_call=True)
def upd_up_fil(ufr): return opts_fil(ufr),"Toutes"

@app.callback(
    Output("upload-status","children"),
    Input("upload-fichier","contents"),
    State("upload-fichier","filename"),
    State("up-ufr","value"),State("up-fil","value"),
    State("up-sem","value"),State("up-annee","value"),
    State("up-session","value"),State("token-store","data"),
    prevent_initial_call=True,
)
def handle_upload(contents,filename,ufr,filiere,semestre,annee,session,token):
    if not contents or not filename: return html.Div()
    if not filiere or filiere=="Toutes":
        return html.Div("Veuillez sélectionner une filière spécifique.",
                        style={"color":ORANGE,"fontSize":"13px"})
    try:
        _,content_string=contents.split(",")
        decoded=base64.b64decode(content_string)
        ext=os.path.splitext(filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False,suffix=ext) as tmp:
            tmp.write(decoded); tmp_path=tmp.name
        payload=decode_token(token)
        id_user=payload.get("sub") if payload else None
        stats=run_pipeline(tmp_path,ufr,filiere,semestre,annee,session,id_user)
        os.unlink(tmp_path)

        # Enregistrer dans log_imports
        if payload:
            nom_user=f"{payload.get('prenom','')} {payload.get('nom','')}".strip()
            log_import(payload.get("email",""),nom_user,payload.get("role",""),
                       ufr,semestre,annee,filename,
                       stats['nb_inseres'],stats['nb_mis_a_jour'],stats['nb_erreurs'])

        return html.Div([
            html.I(className="ti ti-check",**{"aria-hidden":"true"},
                   style={"color":VERT,"marginRight":"8px"}),
            html.B(f"✅ {filename} importé avec succès",style={"color":VERT}),
            html.Span(f" — {stats['nb_inseres']} insérés, "
                      f"{stats['nb_mis_a_jour']} mis à jour, "
                      f"{stats['nb_erreurs']} erreurs",
                      style={"color":GRIS,"fontSize":"12px"}),
        ],style={"background":"#E6F5EF","border":"1px solid #B7DFCF",
                  "borderRadius":"8px","padding":"10px 14px"})
    except Exception as e:
        return html.Div([
            html.I(className="ti ti-alert-triangle",**{"aria-hidden":"true"},
                   style={"color":ROUGE,"marginRight":"8px"}),
            html.B("Erreur : ",style={"color":ROUGE}),
            html.Span(str(e),style={"fontSize":"12px","color":ROUGE}),
        ],style={"background":"#FDECEA","border":"1px solid #F5C0BC",
                  "borderRadius":"8px","padding":"10px 14px"})

@app.callback(
    Output("creer-user-status","children"),
    Input("btn-creer-user","n_clicks"),
    State("new-nom","value"),State("new-prenom","value"),
    State("new-email","value"),State("new-password","value"),
    State("new-role","value"),State("new-ufr","value"),
    prevent_initial_call=True,
)
def creer_user(n,nom,prenom,email,password,role,ufr):
    if not all([nom,prenom,email,password,role]):
        return html.Span("Tous les champs obligatoires (*) doivent être remplis.",
                         style={"color":ORANGE})
    result=creer_utilisateur(nom.strip(),prenom.strip(),email.strip(),
                              password,role,ufr or None)
    if result["ok"]:
        return html.Span([
            html.I(className="ti ti-check",**{"aria-hidden":"true"},
                   style={"color":VERT,"marginRight":"6px"}),
            f"Compte créé : {prenom} {nom} ({role}"
            f"{f', UFR/{ufr}' if ufr else ''})",
        ],style={"color":VERT})
    return html.Span(f"Erreur : {result['message']}",style={"color":ROUGE})

# ── Export PDF ────────────────────────────────────────────────
@app.callback(
    Output("download-pdf","data"),
    Input("btn-export-pdf","n_clicks"),
    State("tab","data"),
    State("f-ufr","value"),State("f-fil","value"),
    State("f-ses","value"),State("f-an","value"),
    State("token-store","data"),
    prevent_initial_call=True,
)
def export_pdf(n,tab,ufr,fil,ses,an,token):
    if not n or not token: return dash.no_update
    payload=decode_token(token)
    if not payload: return dash.no_update
    nom_user=f"{payload.get('prenom','')} {payload.get('nom','')}".strip()
    email=payload.get("email","")
    role=payload.get("role","")

    df=filter_data(ufr,fil,None,None,ses,an,None)
    kps=compute_kpis(df)
    noms={"synthese":"Synthèse","effectifs":"Effectifs","performances":"Performances",
          "etudiant":"Suivi Étudiant","flux":"Flux & Parcours",
          "comparaison":"Comparaison","gestion_suivi":"Gestion & Suivi",
          "import_donnees":"Import données"}
    nom_onglet=noms.get(tab or "synthese","Synthèse")

    ufr_lbl=f"UFR/{ufr}" if ufr and ufr!="Tous" else "Toutes UFR"
    fil_lbl=fil if fil and fil!="Toutes" else "Toutes filières"
    filtres={"UFR":ufr_lbl,"Filière":fil_lbl,
             "Session":ses or "Normale","Année":an or "2019-2024"}

    data={}
    if tab=="synthese":
        try: data["comparaison"]=get_comparaison_filieres(df)
        except: pass
    elif tab=="effectifs":
        try:
            data["reinscription"]=get_taux_reinscription()
            data["genre"]=get_parite_genre(df)
            data["kpi_globaux"]=get_kpis_globaux()
        except: pass
    elif tab=="performances":
        try:
            data["top_etudiants"]=get_top_etudiants(df,10,"top")
            data["bas_etudiants"]=get_top_etudiants(df,10,"bas")
            data["mentions"]=get_mentions(df)
            data["modules"]=get_modules_difficiles(df).head(12)
        except Exception as e: print(f"perf PDF: {e}")
    elif tab=="flux":
        try:
            import pandas as _pd
            df_f = df[df["session"]=="Normale"].copy() if "Normale" in df["session"].values else df.copy()
            # Même logique que pg_flux : utiliser l'année de référence
            if an and an != "Toutes":
                annee_ref = an
            else:
                annees_dispo = sorted(df_f["annee_academique"].dropna().unique())
                annee_ref = annees_dispo[-1] if len(annees_dispo) > 0 else "2024-2025"
            df_ref = df_f[df_f["annee_academique"] == annee_ref]
            L1  = int(df_ref[df_ref["niveau"]=="L1"]["matricule"].nunique())
            L2  = int(df_ref[df_ref["niveau"]=="L2"]["matricule"].nunique())
            L3  = int(df_ref[df_ref["niveau"]=="L3"]["matricule"].nunique())
            DIP = int(df_ref[(df_ref["niveau"]=="L3")&(df_ref["statut"]=="Admis")]["matricule"].nunique())
            tr_l1  = round(100*L2/L1, 1)  if L1>0 else 0
            tr_l2  = round(100*L3/L2, 1)  if L2>0 else 0
            tr_dip = round(100*DIP/L1,1)  if L1>0 else 0
            pct_ab = round(100*(L1-DIP)/L1,1) if L1>0 else 0
            data["flux"] = _pd.DataFrame([{
                "annee": annee_ref,
                "n_l1": L1, "n_l2": L2, "n_l3": L3, "n_admis_l3": DIP,
                "abandon_l1": max(0,L1-L2), "abandon_l2": max(0,L2-L3),
                "tr_l1": tr_l1, "tr_l2": tr_l2, "tr_dip": tr_dip, "pct_ab": pct_ab,
            }])
        except Exception as e:
            print(f"flux export: {e}")
    elif tab=="comparaison":
        try:
            data["comparaison"]=get_comparaison_filieres(df)
            data["genre"]=get_parite_genre(df)
            rows=[]
            for ufr_,g_ in filter_data(session=ses).groupby("ufr"):
                t=len(g_); nb_adm=int((g_["statut"]=="Admis").sum())
                rows.append({"ufr":str(ufr_),"effectif":int(g_["matricule"].nunique()),
                    "taux_reussite":round(100*nb_adm/t,1) if t>0 else 0,
                    "taux_defaillance":round(100*(g_["statut"]=="Défaillant").sum()/t,1) if t>0 else 0,
                    "moyenne":round(float(g_["moyenne_generale"].mean()),2) if g_["moyenne_generale"].notna().any() else 0,
                    "mention":round(100*g_[g_["statut"]=="Admis"]["mention"].isin(["Très bien","Bien","Assez bien"]).sum()/max(nb_adm,1),1)})
            data["par_ufr"]=pd.DataFrame(rows)
        except: pass
    elif tab=="gestion_suivi":
        try: data["utilisateurs"]=lister_utilisateurs()
        except: pass

    try:
        pdf_bytes=generer_pdf(onglet=nom_onglet,kpis=kps,
            filtres_actifs=filtres,nom_utilisateur=nom_user,data=data)
        pdf_b64=base64.b64encode(pdf_bytes).decode()

        # Enregistrer dans log_exports
        filtres_str=", ".join([f"{k}: {v}" for k,v in filtres.items()])
        log_export(email,nom_user,role,nom_onglet,filtres_str,"PDF")

        from datetime import datetime
        fname=f"UTS_{nom_onglet.replace(' ','_').replace('&','et')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return dict(content=pdf_b64,filename=fname,base64=True,type="application/pdf")
    except Exception as e:
        import traceback
        print(f"Erreur export PDF:\n{traceback.format_exc()}")
        return dash.no_update

def pg_synthese(df, kps, ufr, an, ses, filiere_lbl, session_lbl, ufr_lbl, annee_lbl, niveau_lbl):
    # KPI sous-titres dynamiques
    kpi_ses_sub = f"Session {session_lbl}"

    # Graphique 1 : Évolution taux réussite sur données FILTRÉES
    ev = get_evolution_reussite_filtre(df)
    if len(ev)>0:
        fig_ev = go.Figure()
        for nv,clr in NIV_C.items():
            d = ev[ev["niveau"]==nv].sort_values("annee")
            if len(d)==0: continue
            fig_ev.add_trace(go.Scatter(
                x=d["annee"].astype(str), y=d["taux_reussite"].astype(float),
                name=nv, mode="lines+markers+text",
                line=dict(color=clr,width=2.5), marker=dict(size=8,color=clr),
                text=[None]*(len(d)-1)+[f" {nv}: {d['taux_reussite'].iloc[-1]:.0f}%"],
                textposition="middle right", textfont=dict(size=11,color=clr),
            ))
        fig_ev.update_layout(**lay(350,margin=dict(l=12,r=90,t=20,b=45),
            xaxis=ax(tickangle=-30), yaxis=ax(ticksuffix="%"),
            showlegend=False))
    else:
        fig_ev = empty_fig("Pas assez de données pour cette sélection")

    # Graphique 2 : Répartition statuts — barres horizontales
    vals_stat = [kps["nb_admis"],kps["nb_ajournes"],kps["nb_defaillants"]]
    pcts_stat = [kps["taux_reussite"],kps["taux_echec"],kps["taux_defaillance"]]
    fig_stat = go.Figure(go.Bar(
        y=["Admis","Ajournés","Défaillants"], x=vals_stat, orientation="h",
        marker_color=[VERT,ORANGE,ROUGE],
        text=[f"{p}%  ({v:,})" for p,v in zip(pcts_stat,vals_stat)],
        textposition="outside", textfont=dict(size=12),
    ))
    fig_stat.update_layout(**lay(220,margin=dict(l=90,r=140,t=12,b=12),
        xaxis=ax(showgrid=False), yaxis=dict(showgrid=False,tickfont=dict(size=13,color="#374151"))))

    # Graphique 3 : IPG Gauge
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=float(kps["ipg"]),
        number={"suffix":"/100","font":{"size":28,"color":BLEU}},
        gauge={"axis":{"range":[0,100]},"bar":{"color":BLEU2,"thickness":0.22},
               "steps":[{"range":[0,40],"color":"#FDECEA"},{"range":[40,60],"color":"#FEF0E0"},
                         {"range":[60,80],"color":"#E6F5EF"},{"range":[80,100],"color":"#E8F0FE"}],
               "threshold":{"line":{"color":VERT,"width":3},"thickness":0.8,"value":60}}))
    fig_g.update_layout(**lay(220,margin=dict(l=20,r=20,t=30,b=10)))

    # Graphique 4 : Effectifs par UFR sur données globales (pas filtrées)
    ev_e = get_evolution_effectifs()
    if ufr and ufr!="Tous":
        ev_e = ev_e[ev_e["ufr"]==ufr]
    fig_ufr = go.Figure()
    for u,clr in UFR_C.items():
        d = ev_e[ev_e["ufr"]==u].sort_values("annee")
        if len(d)==0: continue
        fig_ufr.add_trace(go.Bar(name=f"UFR/{u}",x=d["annee"].astype(str),
            y=d["effectif"].astype(int),marker_color=clr,
            text=d["effectif"].astype(int),textposition="outside",textfont=dict(size=10)))
    fig_ufr.update_layout(**lay(350,margin=dict(l=12,r=12,t=50,b=45),
        xaxis=ax(tickangle=-30),barmode="group",showlegend=True,
        legend=dict(orientation="h",y=1.12,x=0,font=dict(size=11)),
        yaxis=ax(title="Étudiants actifs")))

    # Graphique 5 : Taux réussite par filière (top 10)
    comp = get_comparaison_filieres(df)
    if len(comp)>0:
        top_f = comp.nlargest(10,"effectif").sort_values("taux_reussite",ascending=True)
        fig_fil = go.Figure(go.Bar(
            y=top_f["filiere_code"].astype(str), x=top_f["taux_reussite"].astype(float),
            orientation="h",
            marker_color=[UFR_C.get(str(u),GRIS) for u in top_f.get("ufr",[GRIS]*len(top_f))],
            text=[f"{v:.1f}%" for v in top_f["taux_reussite"].astype(float)],
            textposition="outside",textfont=dict(size=11)))
        fig_fil.add_vline(x=50,line_dash="dot",line_color=GRIS,line_width=1)
        fig_fil.update_layout(**lay(360,margin=dict(l=130,r=70,t=12,b=12),
            xaxis=ax(ticksuffix="%"),xaxis_range=[0,120],
            yaxis=dict(showgrid=False,tickfont=dict(size=11,color="#374151"))))
    else:
        fig_fil = empty_fig()

    return html.Div([
        html.Div([
            html.Div("Synthèse exécutive",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div(f"{ufr_lbl} · {annee_lbl} · Session {session_lbl}  ·  Tous les indicateurs sont calculés sur la session sélectionnée",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"16px"}),

        # KPIs — sous-titres dynamiques
        html.Div([
            kpi_card("Étudiants inscrits",      f"{kps['effectif']:,}",         "",    BLEU,   "Étudiants distincts"),
            kpi_card("Taux de réussite",        f"{kps['taux_reussite']}",      "%",   VERT,   f"Résultats 'Admis' · {kpi_ses_sub}"),
            kpi_card("Taux d'ajournement",      f"{kps['taux_echec']}",         "%",   ORANGE, f"Ajournés — {kpi_ses_sub}"),
            kpi_card("Taux de défaillance",     f"{kps['taux_defaillance']}",   "%",   ROUGE,  f"Absents — {kpi_ses_sub}"),
            kpi_card("Moyenne générale",        f"{kps['moyenne']}",            "/20", BLEU2,  filiere_lbl),
            kpi_card("IPG",                     f"{kps['ipg']}",                "/100",OR,     "Indice composite"),
        ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(150px,1fr))",
                  "gap":"12px","marginBottom":"18px"}),

        html.Div([
            html.I(className="ti ti-info-circle",**{"aria-hidden":"true"},
                   style={"marginRight":"6px","color":"#1565C0","fontSize":"13px"}),
            html.Span([
                html.B("Note : "),
                f"Les taux affichés dépendent des filtres actifs (session, UFR, filière, année). "
                f"Un taux de réussite différent entre onglets s'explique par des filtres différents — "
                f"vérifiez la barre de filtres en haut. "
                f"Le taux d'ajournement désigne les étudiants ajournés à la session sélectionnée "
                f"(à ne pas confondre avec le ajournement qui implique de recommencer l'année).",
            ],style={"fontSize":"12px","color":"#374151"}),
        ],style={"background":"#E8F0FE","border":"1px solid #BFDBFE","borderRadius":"8px",
                  "padding":"10px 14px","marginBottom":"14px","display":"flex","alignItems":"flex-start"}),

        row1(ccard(
            f"Évolution du taux de réussite — {ufr_lbl}",
            f"Session {session_lbl} · L1, L2, L3 · {annee_lbl}",
            g(fig_ev,350), height=370)),

        row1(ccard("Répartition des résultats",
            f"{kps['total_resultats']:,} résultats · Session {session_lbl}",
            g(fig_stat,220), height=240)),

        row1(ccard("Indice de Performance Globale (IPG)",
            "Réussite × 40% + Mentions × 30% + Moyenne × 30%",
            g(fig_g,220), height=240)),

        row1(ccard("Évolution des effectifs par UFR",
            "Nombre d'étudiants actifs par année académique",
            g(fig_ufr,350), height=370)),

        row1(ccard("Taux de réussite par filière",
            "Top 10 filières par effectif — couleur = UFR",
            g(fig_fil,360), height=380)),

    ],className="tab-content")

# ══════════════════════════════════════════════════════════════
# PAGE 2 — EFFECTIFS
# ══════════════════════════════════════════════════════════════
def pg_effectifs(df, kps, ufr, an, ses, filiere_lbl, session_lbl, ufr_lbl, annee_lbl, niveau_lbl):
    gk = KPI_GLOBAUX  # Indicateurs globaux non filtrés

    # Évolution effectifs filtrée
    ev = get_evolution_effectifs()
    if ufr and ufr!="Tous": ev=ev[ev["ufr"]==ufr]
    ev_t = ev.groupby("annee")["effectif"].sum().reset_index().sort_values("annee")
    fig_ev = go.Figure(go.Scatter(
        x=ev_t["annee"].astype(str),y=ev_t["effectif"].astype(int),
        mode="lines+markers+text",line=dict(color=BLEU2,width=3),
        marker=dict(size=9,color=BLEU),
        text=ev_t["effectif"].astype(int),textposition="top center",textfont=dict(size=11),
        fill="tozeroy",fillcolor="rgba(42,82,153,0.06)"))
    fig_ev.update_layout(**lay(350,margin=dict(l=12,r=12,t=30,b=45),
        xaxis=ax(tickangle=-30),yaxis=ax(title="Étudiants")))

    # Répartition par niveau
    pn = df.groupby("niveau")["matricule"].nunique().reset_index()
    pn.columns=["niveau","eff"]
    pn["niveau"]=pd.Categorical(pn["niveau"],["L1","L2","L3"],ordered=True)
    pn=pn.sort_values("niveau")
    fig_niv = go.Figure(go.Bar(
        x=pn["niveau"].astype(str),y=pn["eff"].astype(int),
        marker_color=[NIV_C.get(str(n),GRIS) for n in pn["niveau"].astype(str)],
        text=pn["eff"].astype(int),textposition="outside",textfont=dict(size=12)))
    fig_niv.update_layout(**lay(300,margin=dict(l=12,r=12,t=30,b=12),yaxis=ax(title="Étudiants")))

    # Réinscription
    rn = get_taux_reinscription()
    if len(rn)>0:
        fig_rn = go.Figure(go.Bar(
            x=rn["vers"].astype(str),y=rn["taux_reinscription"].astype(float),
            marker_color=[VERT if v>=70 else ORANGE for v in rn["taux_reinscription"].astype(float)],
            text=[f"{v:.1f}%" for v in rn["taux_reinscription"].astype(float)],
            textposition="outside"))
        fig_rn.add_hline(y=70,line_dash="dot",line_color=VERT,line_width=1.5,
            annotation_text="Cible 70%",annotation_font=dict(size=10,color=VERT))
        fig_rn.update_layout(**lay(300,margin=dict(l=12,r=20,t=30,b=45),
            xaxis=ax(tickangle=-30),yaxis=ax(ticksuffix="%"),yaxis_range=[0,120]))
    else:
        fig_rn=empty_fig()

    # Genre par niveau — dynamique selon filtre
    gdf = df[df["genre"].isin(["M","F"])].groupby(["niveau","genre"])["matricule"].nunique().reset_index()
    gdf.columns=["niveau","genre","eff"]
    gdf["niveau"]=pd.Categorical(gdf["niveau"],["L1","L2","L3"],ordered=True)
    gdf=gdf.sort_values("niveau")
    fig_genre = go.Figure()
    for g_,clr in [("M",BLEU2),("F","#C2185B")]:
        d=gdf[gdf["genre"]==g_]
        fig_genre.add_trace(go.Bar(name={"M":"Hommes","F":"Femmes"}[g_],
            x=d["niveau"].astype(str),y=d["eff"].astype(int),marker_color=clr,
            text=d["eff"].astype(int),textposition="outside",textfont=dict(size=10)))
    # Titre dynamique selon UFR
    ufr_genre_titre = f"Répartition H/F — {ufr_lbl}"
    genre_sous_titre = "Effectifs par genre et par niveau"
    fig_genre.update_layout(**lay(320,margin=dict(l=12,r=12,t=50,b=12),
        barmode="group",showlegend=True,
        legend=dict(orientation="h",y=1.12,x=0,font=dict(size=11)),
        yaxis=ax(title="Étudiants")))

    # Effectifs par filière
    pf = df.groupby(["filiere_code","ufr"])["matricule"].nunique().reset_index()
    pf.columns=["fil","ufr_f","eff"]
    pf=pf.sort_values("eff",ascending=True).tail(14)
    fig_fil = go.Figure(go.Bar(
        y=pf["fil"].astype(str),x=pf["eff"].astype(int),orientation="h",
        marker_color=[UFR_C.get(str(u),GRIS) for u in pf["ufr_f"]],
        text=pf["eff"].astype(int),textposition="outside"))
    fig_fil.update_layout(**lay(420,margin=dict(l=150,r=60,t=12,b=12),
        xaxis=ax(showgrid=True),
        yaxis=dict(showgrid=False,tickfont=dict(size=11,color="#374151"))))

    return html.Div([
        html.Div([
            html.Div("Effectifs & Attractivité",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div(f"L'UTS attire-t-elle et garde-t-elle ses étudiants ? — {ufr_lbl}",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"16px"}),

        html.Div([
            kpi_card("Étudiants inscrits",   f"{kps['effectif']:,}",               "",   BLEU,   "Étudiants distincts"),
            kpi_card("Passage L1 → L2",      f"{gk['passage_l1_l2']}",             "%",  VERT,   "Données globales"),
            kpi_card("Passage L2 → L3",      f"{gk['passage_l2_l3']}",             "%",  BLEU2,  "Données globales"),
            kpi_card("Taux d'ajournement",  f"{kps['taux_echec']}",               "%",  ORANGE, f"Session {session_lbl}"),
            kpi_card("Taux de défaillance",  f"{kps['taux_defaillance']}",         "%",  ROUGE,  f"Session {session_lbl}"),
            kpi_card("Nouveaux L1",          f"{gk['nb_l1_recent']:,}",            "",   OR,     gk["derniere_annee"]),
        ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(150px,1fr))",
                  "gap":"12px","marginBottom":"18px"}),

        row1(ccard("Évolution des effectifs",
            f"Étudiants actifs par année — {ufr_lbl}",g(fig_ev,350),height=370)),

        row1(ccard("Répartition par niveau",
            f"Étudiants distincts par cycle — {ufr_lbl} · Session {session_lbl}",
            g(fig_niv,300),height=320)),

        row1(ccard(ufr_genre_titre, genre_sous_titre, g(fig_genre,320),height=340)),

        row1(ccard("Taux de réinscription",
            "Proportion d'étudiants qui reviennent d'une année à la suivante",
            g(fig_rn,300),height=320)),

        row1(ccard("Effectifs par filière",
            f"Top 14 filières — couleur = UFR",g(fig_fil,420),height=440)),

    ],className="tab-content")

# ══════════════════════════════════════════════════════════════
# PAGE 3 — PERFORMANCES
# ══════════════════════════════════════════════════════════════
def pg_performances(df, kps, ufr, an, ses, filiere_lbl, session_lbl, ufr_lbl, annee_lbl, niveau_lbl):
    # Distribution notes
    # Distribution des moyennes - calcul direct avec conversion forcée en float
    
    moyennes_brutes = pd.to_numeric(df["moyenne_generale"], errors="coerce").dropna()
    moyennes_valides = moyennes_brutes[(moyennes_brutes >= 0) & (moyennes_brutes <= 20)]

    if len(moyennes_valides) > 0:
        # Intervalles fixes de 0 à 20 par pas de 2
        intervalles = ["0-2","2-4","4-6","6-8","8-10","10-12","12-14","14-16","16-18","18-20"]
        bornes      = [0,2,4,6,8,10,12,14,16,18,20]
        effectifs   = []
        couleurs_d  = []
        for i in range(len(bornes)-1):
            n = int(((moyennes_valides >= bornes[i]) & (moyennes_valides < bornes[i+1])).sum())
            effectifs.append(n)
            if bornes[i] < 10:  couleurs_d.append(ROUGE)
            elif bornes[i] < 14: couleurs_d.append(ORANGE)
            else:                couleurs_d.append(VERT)

        fig_dist = go.Figure(go.Bar(
            x=intervalles,
            y=effectifs,
            marker_color=couleurs_d,
            marker_line_color="white",
            marker_line_width=1,
            text=[f"{v:,}" if v>0 else "" for v in effectifs],
            textposition="outside",
            textfont=dict(size=11,color="#374151"),
            hovertemplate="<b>%{x}/20</b><br>%{y:,} étudiants<extra></extra>",
        ))
        fig_dist.add_vline(
            x=4.5, line_dash="dot", line_color=BLEU, line_width=2,
            annotation_text="Seuil 10/20",
            annotation_font=dict(size=11,color=BLEU),
            annotation_position="top left",
        )
        fig_dist.update_layout(**lay(380,
            margin=dict(l=20,r=20,t=40,b=50),
            xaxis=dict(showgrid=False,tickfont=dict(size=12,color="#374151"),
                       title=dict(text="Intervalle de moyenne /20",font=dict(size=11,color=GRIS)),
                       type="category"),
            yaxis=ax(title="Nombre d'étudiants"),
            bargap=0.12,
        ))
    else:
        fig_dist = empty_fig("Aucune note disponible pour cette sélection")

    # Taux par niveau
    rows_niv=[]
    for niv,g_ in df.groupby("niveau"):
        t=len(g_)
        if t==0: continue
        rows_niv.append({"niveau":niv,"taux":round(100*(g_["statut"]=="Admis").sum()/t,1),"n":t})
    df_niv=pd.DataFrame(rows_niv)
    if len(df_niv)>0:
        df_niv["niveau"]=pd.Categorical(df_niv["niveau"],["L1","L2","L3"],ordered=True)
        df_niv=df_niv.sort_values("niveau")
        fig_niv=go.Figure(go.Bar(
            y=df_niv["niveau"].astype(str),x=df_niv["taux"].astype(float),orientation="h",
            marker_color=[NIV_C.get(str(n),GRIS) for n in df_niv["niveau"].astype(str)],
            text=[f"{v:.1f}%" for v in df_niv["taux"].astype(float)],textposition="outside"))
        fig_niv.add_vline(x=50,line_dash="dot",line_color=GRIS,line_width=1)
        fig_niv.update_layout(**lay(260,margin=dict(l=60,r=90,t=12,b=12),
            xaxis=ax(ticksuffix="%"),xaxis_range=[0,115],
            yaxis=dict(showgrid=False,tickfont=dict(size=13,color="#374151"))))
    else:
        fig_niv=empty_fig()

    # Mentions
    ment=get_mentions(df)
    if len(ment)>0:
        fig_ment=go.Figure(go.Bar(
            y=ment["mention"].astype(str),x=ment["count"].astype(int),orientation="h",
            marker_color=[VIOLET if m=="Très bien" else ("#1565C0" if m=="Bien" else
                ("#0277BD" if m=="Assez bien" else GRIS)) for m in ment["mention"].astype(str)],
            text=[f"{v}%  ({c:,})" for v,c in zip(ment["pct"].astype(float).round(1),ment["count"].astype(int))],
            textposition="outside"))
        fig_ment.update_layout(**lay(260,margin=dict(l=110,r=130,t=12,b=12),
            xaxis=ax(showgrid=True),
            yaxis=dict(showgrid=False,tickfont=dict(size=12,color="#374151"))))
    else:
        fig_ment=empty_fig("Aucun admis dans cette sélection")

    # Parité H/F — titre dynamique
    pg_=get_parite_genre(df)
    if len(pg_)>0:
        pg_=pg_[pg_["genre"].isin(["M","F"])].copy()
        fig_par=go.Figure(go.Bar(
            x=pg_["genre"].map({"M":"Hommes","F":"Femmes"}),
            y=pg_["taux_reussite"].astype(float),
            marker_color=[BLEU2,"#C2185B"],width=0.4,
            text=[f"{v:.1f}%" for v in pg_["taux_reussite"].astype(float)],
            textposition="outside"))
        fig_par.update_layout(**lay(280,margin=dict(l=20,r=20,t=30,b=12),
            xaxis=dict(showgrid=False,tickfont=dict(size=13,color="#374151")),
            yaxis=ax(ticksuffix="%"),yaxis_range=[0,110]))
    else:
        fig_par=empty_fig()

    # Session normale vs rattrapage
    sess_rows=[]
    for ses_,g_ in df.groupby("session"):
        t=len(g_)
        if t==0: continue
        sess_rows.append({"session":ses_,"admis":round(100*(g_["statut"]=="Admis").sum()/t,1),
            "ajourn":round(100*(g_["statut"]=="Ajourné").sum()/t,1),
            "def":round(100*(g_["statut"]=="Défaillant").sum()/t,1)})
    if sess_rows:
        df_sess=pd.DataFrame(sess_rows)
        fig_sess=go.Figure()
        for lbl,col,clr in [("Admis","admis",VERT),("Ajournés","ajourn",ORANGE),("Défaillants","def",ROUGE)]:
            if col in df_sess.columns:
                fig_sess.add_trace(go.Bar(name=lbl,x=df_sess["session"].astype(str),
                    y=df_sess[col].astype(float),marker_color=clr,
                    text=[f"{v:.1f}%" for v in df_sess[col].astype(float)],
                    textposition="outside"))
        fig_sess.update_layout(**lay(300,margin=dict(l=12,r=12,t=50,b=12),
            barmode="group",showlegend=True,
            legend=dict(orientation="h",y=1.12,x=0,font=dict(size=11)),
            yaxis=ax(ticksuffix="%"),yaxis_range=[0,120]))
    else:
        fig_sess=empty_fig()

    # Modules difficiles
    mods=get_modules_difficiles(df).head(10)
    if len(mods)>0:
        fig_mods=go.Figure(go.Bar(
            y=mods["nom_ue"].astype(str),x=mods["moyenne"].astype(float),orientation="h",
            marker_color=[ROUGE if float(m)<10 else ORANGE for m in mods["moyenne"]],
            text=[f"{float(v):.2f}/20" for v in mods["moyenne"]],textposition="outside"))
        fig_mods.add_vline(x=10,line_dash="dot",line_color=BLEU,line_width=1.5,
            annotation_text="Seuil 10/20",annotation_font=dict(size=10,color=BLEU))
        fig_mods.update_layout(**lay(360,margin=dict(l=220,r=80,t=12,b=12),
            xaxis=ax(showgrid=True),xaxis_range=[0,18],
            yaxis=dict(showgrid=False,tickfont=dict(size=11,color="#374151"))))
    else:
        fig_mods=empty_fig("Pas assez de données sur les modules")

    # Top & bas étudiants
    def tbl(data_,sens="top"):
        rows=[]
        for i,(_,row) in enumerate(data_.iterrows()):
            moy=row.get("moyenne_generale","")
            try: moy_s=f"{float(moy):.2f}/20"
            except: moy_s="—"
            nom_c=f"{s(row.get('prenom',''))} {s(row.get('nom',''))}".strip()
            rn=i+1; cls={1:"rank-1",2:"rank-2",3:"rank-3"}.get(rn,"rank-n")
            rows.append(html.Tr([
                html.Td(html.Span(str(rn),className=f"rank {cls}")),
                html.Td(nom_c,style={"fontWeight":"500"}),
                html.Td(s(row.get("matricule","")),style={"color":GRIS,"fontSize":"11.5px"}),
                html.Td(s(row.get("filiere_code","")),style={"color":GRIS,"fontSize":"11.5px"}),
                html.Td(f"{s(row.get('niveau',''))}/{s(row.get('semestre',''))}",style={"fontSize":"11.5px"}),
                html.Td(html.B(moy_s,style={"color":VERT if sens=="top" else ROUGE})),
                html.Td(badge(s(row.get("mention","") if sens=="top" else row.get("statut","")))),
            ],style={"borderBottom":"1px solid #E5E9F0"}))
        return html.Div(html.Table([
            html.Thead(html.Tr([html.Th(c,style={"padding":"8px 12px","fontSize":"10.5px","fontWeight":"600",
                "color":GRIS,"textTransform":"uppercase","letterSpacing":"0.05em",
                "borderBottom":"1px solid #E5E9F0","background":GRIS3,"whiteSpace":"nowrap"})
                for c in ["#","Étudiant","Matricule","Filière","Niv/Sem","Moyenne","Statut"]])),
            html.Tbody(rows),
        ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px"}),
        style={"overflowX":"auto"})

    top10=get_top_etudiants(df,10,"top")
    bot10=get_top_etudiants(df,10,"bas")

    return html.Div([
        html.Div([
            html.Div("Performances académiques",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div(f"Les étudiants valident-ils leur année ? — {ufr_lbl} · Session {session_lbl}  ·  Taux de réussite = % de résultats 'Admis' sur la session sélectionnée",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"16px"}),

        html.Div([
            kpi_card("Taux de réussite",        f"{kps['taux_reussite']}",    "%",   VERT,   f"Admis — Session {session_lbl}"),
            kpi_card("Taux d'ajournement",      f"{kps['taux_echec']}",       "%",   ORANGE, f"Ajournés — Session {session_lbl}"),
            kpi_card("Taux de défaillance",     f"{kps['taux_defaillance']}", "%",   ROUGE,  f"Absents — Session {session_lbl}"),
            kpi_card("Moyenne générale",        f"{kps['moyenne']}",          "/20", BLEU2,  filiere_lbl),
            kpi_card("Étudiants avec mention",  f"{kps['taux_mention']}",     "%",   VIOLET, "% des admis avec mention ≥ Assez bien"),
        ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(150px,1fr))",
                  "gap":"12px","marginBottom":"18px"}),

        row1(ccard(f"Distribution des moyennes — {ufr_lbl}",
            f"Rouge : < 10/20 (échec)  ·  Orange : 10-14/20 (passable)  ·  Vert : ≥ 14/20 (mention)  ·  Session {session_lbl}",
            g(fig_dist,380),height=400)),

        row1(ccard(f"Taux de réussite par niveau — Session {session_lbl}",
            "Plus on avance dans le cursus, plus le taux de réussite augmente",
            g(fig_niv,260),height=280)),

        row1(ccard(f"Répartition des mentions — Session {session_lbl}",
            "Sur les étudiants admis uniquement",g(fig_ment,260),height=280)),

        row1(ccard(f"Parité Hommes / Femmes — {ufr_lbl}",
            f"Taux de réussite comparé — Session {session_lbl}",
            g(fig_par,280),height=300)),

        row1(ccard("Session normale vs Session de rattrapage",
            "Impact du rattrapage sur les résultats",g(fig_sess,300),height=320)),

        row1(ccard("Modules les plus difficiles",
            "Matières avec la moyenne la plus basse — ces modules nécessitent une attention pédagogique",
            g(fig_mods,360),height=380)),

        sep("Top 10 — Meilleurs étudiants"),
        ccard(f"Classement — Session {session_lbl} · {ufr_lbl}",
            "Triés par moyenne générale décroissante",tbl(top10,"top")),

        sep("Étudiants en difficulté — à surveiller"),
        ccard("Moyennes les plus basses — accompagnement recommandé",
            "Ces étudiants sont les plus exposés au risque de décrochage",tbl(bot10,"bot")),

    ],className="tab-content")

# ══════════════════════════════════════════════════════════════
# PAGE 5 — FLUX & PARCOURS
# ══════════════════════════════════════════════════════════════
def pg_flux(df, kps, ufr, an, ses, filiere_lbl, session_lbl, ufr_lbl, annee_lbl, niveau_lbl):
    # Données session Normale uniquement pour le flux
    df_f = df[df["session"]=="Normale"].copy() if "Normale" in df["session"].values else df.copy()

    # Déterminer l'année de référence
    # Si une année est sélectionnée → utiliser cette année
    # Si "Toutes" → utiliser la dernière année disponible (cohérent)
    if an and an != "Toutes":
        annee_ref = an
    else:
        annees_dispo = sorted(df_f["annee_academique"].dropna().unique())
        annee_ref = annees_dispo[-1] if len(annees_dispo) > 0 else "2024-2025"

    df_ref = df_f[df_f["annee_academique"] == annee_ref]

    # Étudiants par niveau pour l'année de référence
    L1  = int(df_ref[df_ref["niveau"]=="L1"]["matricule"].nunique())
    L2  = int(df_ref[df_ref["niveau"]=="L2"]["matricule"].nunique())
    L3  = int(df_ref[df_ref["niveau"]=="L3"]["matricule"].nunique())
    DIP = int(df_ref[(df_ref["niveau"]=="L3")&(df_ref["statut"]=="Admis")]["matricule"].nunique())

    # Taux
    tr_l1  = round(100*L2/L1, 1)  if L1>0 else 0
    tr_l2  = round(100*L3/L2, 1)  if L2>0 else 0
    tr_dip = round(100*DIP/L1,1)  if L1>0 else 0
    pct_ab = round(100*(L1-DIP)/L1,1) if L1>0 else 0

    # Abandons inter-niveaux
    AB1 = max(0, L1 - L2)
    AB2 = max(0, L2 - L3)
    AJ3 = max(0, L3 - DIP)

    # ── Entonnoir ─────────────────────────────────────────────
    if L1 > 0:
        fig_fn = go.Figure(go.Funnel(
            y=["Entrants L1", "Passage L2", "Passage L3", "Diplômés"],
            x=[L1, L2, L3, DIP],
            marker_color=[BLEU, BLEU2, VERT, OR],
            textposition="inside",
            textinfo="value+percent initial",
            textfont=dict(size=13, color="white"),
            connector={"line":{"color":GRIS2,"width":1}}))
        fig_fn.update_layout(**lay(380, margin=dict(l=20,r=20,t=20,b=15)))
    else:
        fig_fn = empty_fig("Aucune donnée pour cette sélection")

    # ── Sankey ────────────────────────────────────────────────
    if L1 > 0:
        fig_sk = go.Figure(go.Sankey(
            node=dict(
                label=["L1","L2","L3","Diplômés","Abandon L1","Abandon L2","Ajournés L3"],
                color=[BLEU,BLEU2,VERT,OR,ROUGE,ROUGE,ORANGE],
                pad=20, thickness=24),
            link=dict(
                source=[0,0,1,1,2,2], target=[1,4,2,5,3,6],
                value=[L2,AB1,L3,AB2,DIP,AJ3],
                color=["rgba(42,82,153,0.25)","rgba(192,57,43,0.25)",
                       "rgba(0,135,90,0.25)","rgba(192,57,43,0.25)",
                       "rgba(183,121,31,0.30)","rgba(212,107,8,0.25)"])))
        fig_sk.update_layout(**lay(400, margin=dict(l=10,r=10,t=15,b=30)))
    else:
        fig_sk = empty_fig()

    # ── Évolution par cohorte ─────────────────────────────────
    ufr_arg = None if ufr=="Tous" else ufr
    flux = get_flux_sankey(ufr_arg)
    if len(flux)>0:
        fp = flux[flux["n_l3"]>0].copy()
        if len(fp)>0:
            fp["p_l2"]  = (100*fp["n_l2"]/fp["n_l1"].replace(0,np.nan)).round(1)
            fp["p_l3"]  = (100*fp["n_l3"]/fp["n_l1"].replace(0,np.nan)).round(1)
            fp["p_dip"] = (100*fp["n_admis_l3"]/fp["n_l1"].replace(0,np.nan)).round(1)
            fig_co = go.Figure()
            for col_,nm,clr in [("p_l2","Passage L2",BLEU2),
                                  ("p_l3","Passage L3",VERT),
                                  ("p_dip","Diplômés",OR)]:
                fig_co.add_trace(go.Scatter(
                    x=fp["annee"].astype(str), y=fp[col_].astype(float),
                    name=nm, mode="lines+markers+text",
                    line=dict(color=clr,width=2.5), marker=dict(size=8),
                    text=[None]*(len(fp)-1)+[f" {nm}"],
                    textposition="middle right",
                    textfont=dict(size=10,color=clr)))
            fig_co.update_layout(**lay(350, margin=dict(l=12,r=100,t=20,b=45),
                xaxis=ax(tickangle=-30,title="Cohorte (année d'entrée)"),
                yaxis=ax(ticksuffix="%"), showlegend=False))
        else:
            fig_co = empty_fig("Données insuffisantes — cohortes trop récentes")
    else:
        fig_co = empty_fig()

    # ── Rendu ─────────────────────────────────────────────────
    return html.Div([
        html.Div([
            html.Div("Flux & Parcours étudiants",
                     style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div(f"Cheminement des étudiants de L1 au diplôme — {ufr_lbl}",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"16px"}),

        html.Div([
            kpi_card("Inscrits en L1",      f"{L1:,}",   "",  BLEU,
                     "Nouveaux entrants L1 · " + ufr_lbl),
            kpi_card("Passage L1 → L2",     f"{tr_l1}",  "%", BLEU2,
                     "Des L1 qui accèdent en L2"),
            kpi_card("Passage L2 → L3",     f"{tr_l2}",  "%", VERT,
                     "Des L2 qui accèdent en L3"),
            kpi_card("Taux de diplomation",  f"{tr_dip}", "%", OR,
                     "Diplômés / inscrits L1"),
            kpi_card("Non diplômés",         f"{pct_ab}", "%", ROUGE,
                     "N'obtiennent pas leur diplôme"),
        ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(150px,1fr))",
                  "gap":"12px","marginBottom":"18px"}),

        row1(ccard("Entonnoir de rétention — de L1 au diplôme",
            f"Combien d'étudiants entrent en L1 et combien obtiennent leur diplôme — {annee_ref}",
            g(fig_fn,380), height=400)),

        row1(ccard("Évolution par cohorte d'entrée",
            "Taux de passage et diplomation par année — cohortes ayant atteint L3 uniquement",
            g(fig_co,350), height=370)),

        row1(ccard("Diagramme de Sankey — Flux détaillé",
            f"Où vont les étudiants : passage, abandon, ajournement — {annee_ref}",
            g(fig_sk,400), height=420)),

    ],className="tab-content")


def pg_comparaison(df, kps, ufr, an, ses, filiere_lbl, session_lbl, ufr_lbl, annee_lbl, niveau_lbl):
    comp=get_comparaison_filieres(df)

    # Taux par filière
    if len(comp)>0:
        tf=comp.sort_values("taux_reussite",ascending=True)
        fig_taux=go.Figure(go.Bar(
            y=tf["filiere_code"].astype(str),x=tf["taux_reussite"].astype(float),
            orientation="h",
            marker_color=[UFR_C.get(str(u),GRIS) for u in tf.get("ufr",[GRIS]*len(tf))],
            text=[f"{v:.1f}%" for v in tf["taux_reussite"].astype(float)],
            textposition="outside"))
        fig_taux.add_vline(x=50,line_dash="dot",line_color=GRIS,line_width=1)
        fig_taux.update_layout(**lay(max(320,len(tf)*30),margin=dict(l=140,r=90,t=12,b=12),
            xaxis=ax(ticksuffix="%"),xaxis_range=[0,125],
            yaxis=dict(showgrid=False,tickfont=dict(size=11,color="#374151"))))
    else:
        fig_taux=empty_fig()

    # Graphique comparatif UFR — barres groupées (remplace le radar incompréhensible)
    df_global = filter_data(session=ses)
    rows_ufr=[]
    for ufr_,g_ in df_global.groupby("ufr"):
        t=len(g_)
        if t==0: continue
        nb_adm=int((g_["statut"]=="Admis").sum())
        rows_ufr.append({
            "ufr": f"UFR/{ufr_}",
            "Taux de réussite (%)": round(100*nb_adm/t,1),
            "Taux de mention (%)": round(100*g_[g_["statut"]=="Admis"]["mention"].isin(
                ["Très bien","Bien","Assez bien"]).sum()/max(nb_adm,1),1),
            "Moyenne /20": round(float(g_["moyenne_generale"].mean()),2) if g_["moyenne_generale"].notna().any() else 0,
            "Taux de défaillance (%)": round(100*(g_["statut"]=="Défaillant").sum()/t,1),
        })
    df_ufr=pd.DataFrame(rows_ufr) if rows_ufr else pd.DataFrame()

    if len(df_ufr)>0:
        indicateurs = ["Taux de réussite (%)", "Taux de mention (%)", "Taux de défaillance (%)"]
        couleurs_ind = [VERT, VIOLET, ROUGE]
        fig_rad = go.Figure()
        for ind, clr in zip(indicateurs, couleurs_ind):
            fig_rad.add_trace(go.Bar(
                name=ind,
                x=df_ufr["ufr"].astype(str),
                y=df_ufr[ind].astype(float),
                marker_color=clr,
                text=[f"{v:.1f}%" for v in df_ufr[ind].astype(float)],
                textposition="outside",
                textfont=dict(size=12),
            ))
        fig_rad.update_layout(**lay(360,
            margin=dict(l=20,r=20,t=60,b=20),
            barmode="group", showlegend=True,
            legend=dict(orientation="h",y=1.14,x=0,font=dict(size=12)),
            xaxis=dict(showgrid=False,tickfont=dict(size=14,color="#111827")),
            yaxis=ax(ticksuffix="%",title="Pourcentage (%)"),
            yaxis_range=[0,110]))

        # Graphique séparé pour la moyenne (axe différent)
        fig_moy_ufr = go.Figure()
        for _,row in df_ufr.iterrows():
            clr = UFR_C.get(row["ufr"].replace("UFR/",""), GRIS)
            fig_moy_ufr.add_trace(go.Bar(
                name=row["ufr"],
                x=[row["ufr"]],
                y=[float(row["Moyenne /20"])],
                marker_color=clr,
                text=[f"{float(row['Moyenne /20']):.2f}/20"],
                textposition="outside",
                textfont=dict(size=13),
            ))
        fig_moy_ufr.add_hline(y=10, line_dash="dot", line_color=BLEU, line_width=1.5,
            annotation_text="Seuil validation 10/20",
            annotation_font=dict(size=10,color=BLEU))
        fig_moy_ufr.update_layout(**lay(280,
            margin=dict(l=20,r=20,t=30,b=12),
            showlegend=False,
            xaxis=dict(showgrid=False,tickfont=dict(size=14,color="#111827")),
            yaxis=ax(title="Moyenne générale /20"),
            yaxis_range=[0,22]))
    else:
        fig_rad=empty_fig()
        fig_moy_ufr=empty_fig()

    # Parité H/F par filière
    par_fil=[]
    for (fil,gen),g_ in df[df["genre"].isin(["M","F"])].groupby(["filiere_code","genre"]):
        t=len(g_)
        if t<5: continue
        par_fil.append({"filiere":str(fil),"genre":gen,
            "tr":round(100*(g_["statut"]=="Admis").sum()/t,1)})
    df_par=pd.DataFrame(par_fil) if par_fil else pd.DataFrame()

    if len(df_par)>0:
        top_fils=comp.nlargest(8,"effectif")["filiere_code"].tolist() if len(comp)>=8 else comp["filiere_code"].tolist()
        pff=df_par[df_par["filiere"].isin(top_fils)]
        fig_par=go.Figure()
        for gen,clr,nm in [("M",BLEU2,"Hommes"),("F","#C2185B","Femmes")]:
            d=pff[pff["genre"]==gen]
            fig_par.add_trace(go.Bar(name=nm,x=d["filiere"].astype(str),y=d["tr"].astype(float),
                marker_color=clr,text=[f"{v:.1f}%" for v in d["tr"].astype(float)],
                textposition="outside"))
        fig_par.update_layout(**lay(320,margin=dict(l=12,r=12,t=50,b=50),
            barmode="group",showlegend=True,
            legend=dict(orientation="h",y=1.12,x=0,font=dict(size=11)),
            xaxis=ax(tickangle=-30),yaxis=ax(ticksuffix="%"),yaxis_range=[0,125]))
    else:
        fig_par=empty_fig()

    return html.Div([
        html.Div([
            html.Div("Comparaison & Parité",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div(f"Benchmarking des filières et analyse genre — {ufr_lbl} · Session {session_lbl}",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"16px"}),

        html.Div([
            kpi_card("Filières comparées",     str(len(comp)),              "",   BLEU,  "Avec ≥ 5 résultats"),
            kpi_card("Taux réussite global",   f"{kps['taux_reussite']}", "%",   VERT,  f"Session {session_lbl}"),
            kpi_card("Moyenne globale",        f"{kps['moyenne']}",       "/20", BLEU2, filiere_lbl),
        ],style={"display":"grid","gridTemplateColumns":"repeat(auto-fit,minmax(150px,1fr))",
                  "gap":"12px","marginBottom":"18px"}),

        row1(ccard(f"Taux de réussite par filière — Session {session_lbl}",
            "Trié du plus bas au plus haut — couleur = UFR",
            g(fig_taux,max(320,len(comp)*30)),height=max(340,len(comp)*32))),

        row1(ccard(f"Comparaison des performances par UFR — Session {session_lbl}",
            "Taux de réussite · Taux de mention · Taux de défaillance",
            g(fig_rad,360),height=380)),

        row1(ccard(f"Moyenne générale par UFR — Session {session_lbl}",
            "Comparaison des moyennes entre les 3 UFR · Seuil de validation : 10/20",
            g(fig_moy_ufr,280),height=300)),

        row1(ccard(f"Parité Hommes / Femmes par filière — Session {session_lbl}",
            "Les femmes réussissent-elles autant que les hommes dans chaque filière ?",
            g(fig_par,320),height=360)),

    ],className="tab-content")

# ══════════════════════════════════════════════════════════════
# ONGLET ADMINISTRATION
# ══════════════════════════════════════════════════════════════
def pg_administration(token):
    payload=decode_token(token)
    utilisateurs=lister_utilisateurs()

    rows_u=[]
    for u in utilisateurs:
        role_b=html.Span(u["role"],style={
            "background":"#EBF0FA" if u["role"]=="admin" else "#E6F5EF",
            "color":BLEU if u["role"]=="admin" else VERT,
            "border":f"1px solid {'#C5D5F0' if u['role']=='admin' else '#B7DFCF'}",
            "borderRadius":"20px","padding":"2px 8px","fontSize":"11px","fontWeight":"500"})
        actif_b=html.Span("Actif" if u["actif"] else "Inactif",style={
            "background":"#E6F5EF" if u["actif"] else "#FDECEA",
            "color":VERT if u["actif"] else ROUGE,
            "borderRadius":"20px","padding":"2px 8px","fontSize":"11px","fontWeight":"500"})
        rows_u.append(html.Tr([
            html.Td(f"{u['prenom']} {u['nom']}",style={"padding":"9px 12px","fontWeight":"500"}),
            html.Td(u["email"],style={"padding":"9px 12px","color":GRIS,"fontSize":"12px"}),
            html.Td(role_b,style={"padding":"9px 12px"}),
            html.Td(u.get("ufr") or "Toutes",style={"padding":"9px 12px","fontSize":"12px"}),
            html.Td(actif_b,style={"padding":"9px 12px"}),
            html.Td(u["derniere_connexion"],style={"padding":"9px 12px","color":GRIS,"fontSize":"12px"}),
        ],style={"borderBottom":"1px solid #E5E9F0"}))

    return html.Div([
        html.Div([
            html.Div("Administration",style={"fontSize":"18px","fontWeight":"700","color":"#111827"}),
            html.Div("Gestion des données et des utilisateurs",
                     style={"fontSize":"12.5px","color":"#6B7280","marginTop":"2px"}),
        ],style={"marginBottom":"20px"}),

        sep("Importer de nouvelles données"),
        ccard("Uploader un fichier de délibération",
            "Format : CSV ou Excel — 1 fichier par UFR et semestre",
            html.Div([
                html.Div([
                    *[html.Div([
                        html.Label(lbl,style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dd(id_,opts,default)],
                      style={"flex":"1"})
                      for lbl,id_,opts,default in [
                        ("UFR *","up-ufr",[{"label":v,"value":v} for v in ["ST","SEG","SJP"]],"ST"),
                        ("Filière *","up-fil",opts_fil("ST"),"Toutes"),
                        ("Semestre *","up-sem",[{"label":v,"value":v} for v in ["S1","S2","S3","S4","S5","S6"]],"S1"),
                        ("Année *","up-annee",[{"label":v,"value":v} for v in ANNEES if v!="Toutes"],"2024-2025"),
                        ("Session *","up-session",[{"label":v,"value":v} for v in ["Normale","Rattrapage"]],"Normale"),
                    ]],
                ],style={"display":"flex","gap":"12px","flexWrap":"wrap","marginBottom":"16px"}),
                dcc.Upload(id="upload-fichier",
                    children=html.Div([
                        html.I(className="ti ti-upload",**{"aria-hidden":"true"},
                               style={"fontSize":"28px","color":GRIS,"marginBottom":"8px"}),
                        html.Div("Glissez un fichier ici ou cliquez pour parcourir",
                                 style={"fontSize":"13px","color":GRIS}),
                        html.Div("CSV ou Excel (.csv, .xlsx)",
                                 style={"fontSize":"11.5px","color":GRIS,"marginTop":"4px"}),
                    ],style={"textAlign":"center","padding":"24px"}),
                    style={"border":f"2px dashed {GRIS2}","borderRadius":"10px",
                           "cursor":"pointer","marginBottom":"12px"},
                    accept=".csv,.xlsx,.xls"),
                html.Div(id="upload-status"),
            ])),

        sep("Gestion des utilisateurs"),
        ccard("Créer un nouvel utilisateur","Admin ou Responsable pédagogique",
            html.Div([
                html.Div([
                    *[html.Div([
                        html.Label(lbl,style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                            "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dcc.Input(id=id_,type=typ,placeholder=ph,
                            style={"width":"100%","padding":"8px 12px","border":"1px solid #D1D9E6",
                                   "borderRadius":"6px","fontSize":"13px","boxSizing":"border-box"})],
                      style={"flex":flex})
                      for lbl,id_,typ,ph,flex in [
                        ("Nom *","new-nom","text","Ouédraogo","1"),
                        ("Prénom *","new-prenom","text","Ibrahim","1"),
                        ("Email *","new-email","email","user@uts.bf","2"),
                    ]],
                ],style={"display":"flex","gap":"12px","marginBottom":"12px"}),
                html.Div([
                    html.Div([
                        html.Label("Mot de passe *",style={"fontSize":"11px","fontWeight":"600",
                            "color":GRIS,"textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dcc.Input(id="new-password",type="password",placeholder="••••••••",
                            style={"width":"100%","padding":"8px 12px","border":"1px solid #D1D9E6",
                                   "borderRadius":"6px","fontSize":"13px","boxSizing":"border-box"})],
                      style={"flex":"2"}),
                    html.Div([
                        html.Label("Rôle *",style={"fontSize":"11px","fontWeight":"600",
                            "color":GRIS,"textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dd("new-role",[{"label":"Administrateur","value":"admin"},
                                       {"label":"Responsable","value":"responsable"}],"responsable")],
                      style={"flex":"1"}),
                    html.Div([
                        html.Label("UFR (restreint)",style={"fontSize":"11px","fontWeight":"600",
                            "color":GRIS,"textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                        dd("new-ufr",[{"label":"Toutes UFR","value":""},
                                      {"label":"UFR/ST","value":"ST"},
                                      {"label":"UFR/SEG","value":"SEG"},
                                      {"label":"UFR/SJP","value":"SJP"}],"")],
                      style={"flex":"1"}),
                ],style={"display":"flex","gap":"12px","marginBottom":"14px"}),
                html.Div(html.I(className="ti ti-info-circle",**{"aria-hidden":"true"},
                    style={"marginRight":"6px","color":BLEU2}),
                    style={"fontSize":"12px","color":"#4B5563","background":"#E8F0FE",
                           "borderRadius":"6px","padding":"8px 12px","marginBottom":"12px",
                           "display":"flex","alignItems":"center"}),
                html.Div([
                    html.I(className="ti ti-info-circle",**{"aria-hidden":"true"},
                           style={"marginRight":"6px","color":BLEU2}),
                    "Si UFR est renseignée, le responsable ne verra que les données de cette UFR.",
                ],style={"fontSize":"12px","color":"#4B5563","background":"#E8F0FE",
                          "borderRadius":"6px","padding":"8px 12px","marginBottom":"12px",
                          "display":"flex","alignItems":"center"}),
                html.Button([
                    html.I(className="ti ti-user-plus",**{"aria-hidden":"true"},
                           style={"marginRight":"8px"}),
                    "Créer l'utilisateur",
                ],id="btn-creer-user",n_clicks=0,style={
                    "background":BLEU,"color":"white","border":"none","borderRadius":"6px",
                    "padding":"9px 18px","fontSize":"13px","fontWeight":"500","cursor":"pointer"}),
                html.Div(id="creer-user-status",style={"marginTop":"10px","fontSize":"13px"}),
            ])),

        sep("Utilisateurs existants"),
        ccard("Liste des comptes","Administrateurs et Responsables pédagogiques",
            html.Div(html.Table([
                html.Thead(html.Tr([html.Th(c,style={"padding":"8px 12px","fontSize":"10.5px",
                    "fontWeight":"600","color":GRIS,"textTransform":"uppercase",
                    "letterSpacing":"0.05em","borderBottom":"1px solid #E5E9F0","background":GRIS3})
                    for c in ["Utilisateur","Email","Rôle","UFR","Statut","Dernière connexion"]])),
                html.Tbody(rows_u),
            ],style={"width":"100%","borderCollapse":"collapse","fontSize":"12.5px"}),
            style={"overflowX":"auto"})),

    ],className="tab-content")


# ── Callbacks boutons Modifier / Désactiver / Supprimer ──────
@app.callback(
    Output("selected-user-id","data"),
    Output("user-action","data"),
    Input({"type":"btn-toggle","index":ALL},"n_clicks"),
    Input({"type":"btn-supprimer","index":ALL},"n_clicks"),
    Input({"type":"btn-modifier","index":ALL},"n_clicks"),
    prevent_initial_call=True,
)
def capture_action(n_toggle, n_suppr, n_modif):
    if not ctx.triggered_id: return dash.no_update, dash.no_update
    try:
        if not isinstance(ctx.triggered_id, dict):
            return dash.no_update, dash.no_update
        val = ctx.triggered[0].get("value", 0)
        if not val: return dash.no_update, dash.no_update
        return ctx.triggered_id["index"], ctx.triggered_id["type"]
    except Exception as e:
        print(f"capture_action: {e}")
        return dash.no_update, dash.no_update


@app.callback(
    Output("content","children",allow_duplicate=True),
    Input("selected-user-id","data"),
    Input("user-action","data"),
    State("token-store","data"),
    prevent_initial_call=True,
)
def execute_action(user_id, action, token):
    if not user_id or not action or not token:
        return dash.no_update
    payload = decode_token(token)
    if not payload or payload["role"] != "admin":
        return dash.no_update

    users = lister_utilisateurs()
    u = next((x for x in users if x["id"] == user_id), None)
    if not u: return dash.no_update

    def msg_ok(t):
        return html.Div([
            html.I(className="ti ti-check",**{"aria-hidden":"true"},
                   style={"color":VERT,"marginRight":"8px","fontSize":"16px"}),
            html.Span(t, style={"color":VERT,"fontWeight":"500"}),
        ],style={"background":"#E6F5EF","border":"1px solid #B7DFCF",
                  "borderRadius":"8px","padding":"12px 16px","marginBottom":"16px"})

    def msg_err(t):
        return html.Div([
            html.I(className="ti ti-alert-triangle",**{"aria-hidden":"true"},
                   style={"color":ROUGE,"marginRight":"8px","fontSize":"16px"}),
            html.Span(t, style={"color":ROUGE,"fontWeight":"500"}),
        ],style={"background":"#FDECEA","border":"1px solid #F5C0BC",
                  "borderRadius":"8px","padding":"12px 16px","marginBottom":"16px"})

    if action == "btn-toggle":
        new_actif = not u["actif"]
        result = modifier_utilisateur(user_id, actif=new_actif)
        etat = "activé" if new_actif else "désactivé"
        banner = msg_ok(f"✓ Compte de {u['prenom']} {u['nom']} {etat}.") if result["ok"] else msg_err(result["message"])
        page = pg_gestion_suivi(token)
        # Insérer le banner en haut de la page
        page.children.insert(0, banner)
        return page

    elif action == "btn-supprimer":
        nom_u = f"{u['prenom']} {u['nom']}"
        result = supprimer_utilisateur(user_id)
        banner = msg_ok(f"✓ Compte de {nom_u} supprimé définitivement.") if result["ok"] else msg_err(result["message"])
        page = pg_gestion_suivi(token)
        page.children.insert(0, banner)
        return page

    elif action == "btn-modifier":
        # Afficher la page avec le formulaire de modification pré-rempli
        form = html.Div([
            html.Div([
                html.I(className="ti ti-edit",**{"aria-hidden":"true"},
                       style={"marginRight":"8px","color":BLEU2,"fontSize":"16px"}),
                html.B(f"Modifier le compte — {u['prenom']} {u['nom']}",
                       style={"color":BLEU2,"fontSize":"14px"}),
            ],style={"display":"flex","alignItems":"center","marginBottom":"14px"}),

            html.Div([
                *[html.Div([
                    html.Label(lbl,style={"fontSize":"11px","fontWeight":"600","color":GRIS,
                        "textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                    dcc.Input(id=id_,type=typ,value=val,placeholder=ph,
                        style={"width":"100%","padding":"9px 12px","border":"1px solid #D1D9E6",
                               "borderRadius":"6px","fontSize":"13px","boxSizing":"border-box"})
                ],style={"flex":flex})
                for lbl,id_,typ,val,ph,flex in [
                    ("Nom *","edit-nom","text",u["nom"],"Nom","1"),
                    ("Prénom *","edit-prenom","text",u["prenom"],"Prénom","1"),
                    ("Email *","edit-email","email",u["email"],"Email","2"),
                ]],
            ],style={"display":"flex","gap":"12px","marginBottom":"12px"}),

            html.Div([
                html.Div([
                    html.Label("Nouveau mot de passe",style={"fontSize":"11px","fontWeight":"600",
                        "color":GRIS,"textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                    dcc.Input(id="edit-password",type="password",
                        placeholder="Laisser vide pour ne pas changer",
                        style={"width":"100%","padding":"9px 12px","border":"1px solid #D1D9E6",
                               "borderRadius":"6px","fontSize":"13px","boxSizing":"border-box"})],
                  style={"flex":"2"}),
                html.Div([
                    html.Label("UFR",style={"fontSize":"11px","fontWeight":"600",
                        "color":GRIS,"textTransform":"uppercase","display":"block","marginBottom":"4px"}),
                    dd("edit-ufr",[
                        {"label":"Toutes UFR (aucune restriction)","value":""},
                        {"label":"UFR/ST uniquement","value":"ST"},
                        {"label":"UFR/SEG uniquement","value":"SEG"},
                        {"label":"UFR/SJP uniquement","value":"SJP"},
                    ], u.get("ufr") or "")],
                  style={"flex":"1"}),
            ],style={"display":"flex","gap":"12px","marginBottom":"14px"}),

            dcc.Store(id="edit-user-id", data=user_id),

            html.Div([
                html.Button([
                    html.I(className="ti ti-check",**{"aria-hidden":"true"},
                           style={"marginRight":"6px"}),
                    "Enregistrer les modifications",
                ],id="btn-save-edit",n_clicks=0,style={
                    "background":VERT,"color":"white","border":"none","borderRadius":"6px",
                    "padding":"9px 16px","fontSize":"13px","fontWeight":"500","cursor":"pointer","marginRight":"8px"}),
                html.Button([
                    html.I(className="ti ti-arrow-left",**{"aria-hidden":"true"},
                           style={"marginRight":"6px"}),
                    "Retour à la liste",
                ],id="btn-cancel-edit",n_clicks=0,style={
                    "background":GRIS3,"color":GRIS,"border":f"1px solid {GRIS2}",
                    "borderRadius":"6px","padding":"9px 16px","fontSize":"13px","cursor":"pointer"}),
            ],style={"display":"flex","gap":"8px"}),
            html.Div(id="edit-save-msg",style={"marginTop":"10px"}),
        ],style={"background":"#EBF4FF","border":"1px solid #BFDBFE","borderRadius":"10px",
                  "padding":"20px","marginBottom":"20px"})

        page = pg_gestion_suivi(token)
        # Insérer le formulaire après les KPIs (index 1)
        page.children.insert(1, form)
        return page

    return dash.no_update


@app.callback(
    Output("content","children",allow_duplicate=True),
    Input("btn-save-edit","n_clicks"),
    State("edit-user-id","data"),
    State("edit-nom","value"),
    State("edit-prenom","value"),
    State("edit-email","value"),
    State("edit-password","value"),
    State("edit-ufr","value"),
    State("token-store","data"),
    prevent_initial_call=True,
)
def save_modification(n, user_id, nom, prenom, email, password, ufr, token):
    if not n or not user_id or not token: return dash.no_update
    payload = decode_token(token)
    if not payload: return dash.no_update

    if not all([nom, prenom, email]):
        return dash.no_update

    result = modifier_utilisateur(
        user_id,
        nom=nom.strip(), prenom=prenom.strip(), email=email.strip(),
        ufr=ufr or None,
        new_password=password.strip() if password and password.strip() else None,
    )
    page = pg_gestion_suivi(token)
    if result["ok"]:
        banner = html.Div([
            html.I(className="ti ti-check",**{"aria-hidden":"true"},
                   style={"color":VERT,"marginRight":"8px","fontSize":"16px"}),
            html.Span(f"✓ Compte de {prenom} {nom} modifié avec succès.",
                      style={"color":VERT,"fontWeight":"500"}),
        ],style={"background":"#E6F5EF","border":"1px solid #B7DFCF",
                  "borderRadius":"8px","padding":"12px 16px","marginBottom":"16px"})
    else:
        banner = html.Div([
            html.I(className="ti ti-alert-triangle",**{"aria-hidden":"true"},
                   style={"color":ROUGE,"marginRight":"8px","fontSize":"16px"}),
            html.Span(f"Erreur : {result['message']}",style={"color":ROUGE,"fontWeight":"500"}),
        ],style={"background":"#FDECEA","border":"1px solid #F5C0BC",
                  "borderRadius":"8px","padding":"12px 16px","marginBottom":"16px"})
    page.children.insert(0, banner)
    return page


@app.callback(
    Output("content","children",allow_duplicate=True),
    Input("btn-cancel-edit","n_clicks"),
    State("token-store","data"),
    prevent_initial_call=True,
)
def cancel_edit(n, token):
    if not n or not token: return dash.no_update
    return pg_gestion_suivi(token)


if __name__ == "__main__":
    print("✅ Dashboard UTS v6 — http://localhost:8050")
    print("   Admin      : Synthèse + Effectifs + Performances + Étudiant + Flux + Comparaison + Gestion & Suivi")
    print("   Responsable: Synthèse + Effectifs + Performances + Étudiant + Flux + Comparaison + Import données")
    app.run(debug=False, host="0.0.0.0", port=8050, threaded=True)
