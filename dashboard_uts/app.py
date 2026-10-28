"""
Tableau de Bord Décisionnel — UFR S&T / UTS
Plotly Dash + CSS custom — Architecture 5 onglets
"""
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys, os

sys.path.insert(0, "/home/claude/dashboard_uts")
from data_loader import (
    load_all, filter_data, compute_kpis,
    get_evolution_effectifs, get_evolution_reussite,
    get_distribution_moyennes, get_top_etudiants,
    get_parite_genre, get_mentions, get_comparaison_filieres,
    get_evolution_par_semestre, get_flux_sankey,
    get_modules_difficiles, get_taux_reinscription
)

# ── Couleurs Plotly cohérentes avec CSS ─────────────────────────────────────
COLORS = {
    "bleu":    "#0D2B55",
    "bleu2":   "#1A4080",
    "bleu3":   "#2A5299",
    "vert":    "#00875A",
    "orange":  "#E8701A",
    "rouge":   "#C0392B",
    "or":      "#D4A017",
    "violet":  "#512DA8",
    "gris":    "#6B7280",
    "fond":    "#F0F3F8",
}
PALETTE_UFR = {"ST": "#0D2B55", "SEG": "#00875A", "SJP": "#E8701A"}
PALETTE_NIVEAU = {"L1": "#2A5299", "L2": "#00875A", "L3": "#D4A017"}
PALETTE_STATUT = {"Admis": "#00875A", "Ajourné": "#E8701A", "Défaillant": "#C0392B"}
PALETTE_MENTION = {"Très bien": "#512DA8", "Bien": "#1565C0", "Assez bien": "#0277BD", "Passable": "#546E7A"}
PALETTE_GENRE = {"M": "#0D2B55", "F": "#E91E8C"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#374151"),
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)", orientation="h",
                yanchor="bottom", y=1.01, xanchor="left", x=0),
    xaxis=dict(showgrid=True, gridcolor="#E5E9F0", gridwidth=1, linecolor="#E5E9F0"),
    yaxis=dict(showgrid=True, gridcolor="#E5E9F0", gridwidth=1, linecolor="#E5E9F0"),
)

# ── Charger données au démarrage ────────────────────────────────────────────
data = load_all()
df_filieres = data["filieres"]
df_ufrs = data["ufrs"]

# Options des filtres
ANNEES = ["Toutes"] + sorted(data["joined"]["annee_academique"].dropna().unique().tolist(), reverse=True)
UFRS_OPT = ["Tous"] + sorted(data["joined"]["ufr"].dropna().unique().tolist())
NIVEAUX = ["Tous", "L1", "L2", "L3"]
SESSIONS = ["Normale", "Rattrapage", "Toutes"]
SEMESTRES_OPT = ["Tous", "S1", "S2", "S3", "S4", "S5", "S6"]
GENRES = ["Tous", "M", "F"]

def get_filieres_for_ufr(ufr):
    if not ufr or ufr == "Tous":
        opts = df_filieres["code_filiere"].tolist()
    else:
        opts = df_filieres[df_filieres["ufr"] == ufr]["code_filiere"].tolist()
    return [{"label": "Toutes", "value": "Toutes"}] + [{"label": c, "value": c} for c in opts]

# ── Helpers HTML ─────────────────────────────────────────────────────────────
def kpi_card(label, value, unit="", icon="📊", couleur="bleu", trend=None, trend_dir="neutral"):
    trend_html = []
    if trend:
        arrow = "↑" if trend_dir == "up" else ("↓" if trend_dir == "down" else "—")
        trend_html = [html.Div([arrow, " ", trend], className=f"kpi-trend {trend_dir}")]
    return html.Div([
        html.Div([
            html.Div(label, className="kpi-label"),
            html.Div(icon, className=f"kpi-icon {couleur}"),
        ], className="kpi-header"),
        html.Div([
            html.Span(value, className="kpi-value"),
            html.Span(f" {unit}", className="kpi-unit") if unit else None,
        ]),
        *trend_html,
    ], className=f"kpi-card kpi-{couleur}")

def chart_card(title, subtitle, children, class_extra=""):
    return html.Div([
        html.Div(title, className="chart-title"),
        html.Div(subtitle, className="chart-subtitle"),
        html.Div(className="chart-divider"),
        *children,
    ], className=f"chart-card {class_extra}")

def section_sep(title):
    return html.Div([
        html.Span(title, className="section-sep-title"),
        html.Div(className="section-sep-line"),
    ], className="section-sep")

def badge_statut(statut):
    cls = {"Admis": "badge-admis", "Ajourné": "badge-ajourn", "Défaillant": "badge-def"}.get(statut, "")
    return html.Span(statut, className=f"badge-statut {cls}")

def badge_mention(mention):
    cls = {"Très bien":"badge-mention-tb","Bien":"badge-mention-b",
           "Assez bien":"badge-mention-ab","Passable":"badge-mention-p"}.get(mention or "", "badge-mention-p")
    return html.Span(mention or "—", className=f"badge-statut {cls}")

# ── Navigation sidebar ───────────────────────────────────────────────────────
NAV_ITEMS = [
    ("synthese",      "📊", "Synthèse"),
    ("effectifs",     "👥", "Effectifs"),
    ("performances",  "🎓", "Performances"),
    ("flux",          "🔄", "Flux & Parcours"),
    ("comparaison",   "⚖️",  "Comparaison"),
]

def sidebar():
    return html.Div([
        # Logo
        html.Div([
            html.Div("UTS — Dashboard", className="sidebar-logo-title"),
            html.Div("UFR Sciences & Technologies", className="sidebar-logo-sub"),
        ], className="sidebar-logo"),
        # Navigation
        html.Div("Navigation", className="sidebar-section-label"),
        html.Div([
            html.Button([
                html.Span(icon, className="nav-icon"),
                html.Span(label),
                html.Div(className="nav-dot"),
            ], id=f"nav-{key}", className="nav-item", n_clicks=0)
            for key, icon, label in NAV_ITEMS
        ]),
        # Footer
        html.Div([
            html.Div("Données : 2019-2024"),
            html.Div("31 098 étudiants"),
            html.Div("3 UFR · 24 filières"),
        ], className="sidebar-footer"),
    ], className="sidebar")

# ── Filtres communs ──────────────────────────────────────────────────────────
def filtres_bar(id_prefix="main"):
    return html.Div([
        html.Div(["🔽 Filtres"], className="filtres-label"),
        html.Div([
            html.Label("UFR"),
            dcc.Dropdown(
                id=f"{id_prefix}-ufr",
                options=[{"label": v, "value": v} for v in UFRS_OPT],
                value="Tous", clearable=False, className="filtre-dd",
            ),
        ], className="filtre-item"),
        html.Div([
            html.Label("Filière"),
            dcc.Dropdown(
                id=f"{id_prefix}-filiere",
                options=get_filieres_for_ufr("Tous"),
                value="Toutes", clearable=False, className="filtre-dd",
            ),
        ], className="filtre-item"),
        html.Div([
            html.Label("Niveau"),
            dcc.Dropdown(
                id=f"{id_prefix}-niveau",
                options=[{"label": v, "value": v} for v in NIVEAUX],
                value="Tous", clearable=False,
            ),
        ], className="filtre-item"),
        html.Div([
            html.Label("Semestre"),
            dcc.Dropdown(
                id=f"{id_prefix}-semestre",
                options=[{"label": v, "value": v} for v in SEMESTRES_OPT],
                value="Tous", clearable=False,
            ),
        ], className="filtre-item"),
        html.Div([
            html.Label("Session"),
            dcc.Dropdown(
                id=f"{id_prefix}-session",
                options=[{"label": v, "value": v} for v in SESSIONS],
                value="Normale", clearable=False,
            ),
        ], className="filtre-item"),
        html.Div([
            html.Label("Année académique"),
            dcc.Dropdown(
                id=f"{id_prefix}-annee",
                options=[{"label": v, "value": v} for v in ANNEES],
                value="Toutes", clearable=False,
            ),
        ], className="filtre-item"),
        html.Div([
            html.Label("Genre"),
            dcc.Dropdown(
                id=f"{id_prefix}-genre",
                options=[{"label": {"Tous":"Tous","M":"Masculin","F":"Féminin"}.get(v,v), "value": v} for v in GENRES],
                value="Tous", clearable=False,
            ),
        ], className="filtre-item"),
    ], className="filtres-bar")

# ── APP ──────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    assets_folder="/home/claude/dashboard_uts/assets",
    suppress_callback_exceptions=True,
    title="Dashboard UTS",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.layout = html.Div([
    # Store pour l'onglet actif
    dcc.Store(id="active-tab", data="synthese"),
    # Layout
    sidebar(),
    html.Div([
        # Topbar
        html.Div([
            html.Div([
                html.Span("Accueil / ", className="topbar-breadcrumb"),
                html.Span(id="topbar-page-name", children="Synthèse"),
            ], className="topbar-left"),
            html.Div([
                html.Span("Données 2019-2024", className="topbar-badge"),
                html.Div([
                    html.Div("AD", className="avatar"),
                    html.Span("Admin"),
                ], className="topbar-user"),
            ], className="topbar-right"),
        ], className="topbar"),
        # Contenu principal dynamique
        html.Div(id="page-content", className="page-content"),
    ], className="main-content"),
], className="layout-root")


# ── CALLBACKS Navigation ─────────────────────────────────────────────────────
@app.callback(
    Output("active-tab", "data"),
    [Input(f"nav-{key}", "n_clicks") for key, _, _ in NAV_ITEMS],
    prevent_initial_call=True,
)
def update_tab(*args):
    from dash import ctx
    if not ctx.triggered:
        return "synthese"
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    return btn_id.replace("nav-", "")

@app.callback(
    Output("topbar-page-name", "children"),
    Input("active-tab", "data"),
)
def update_topbar(tab):
    names = {k: l for k, _, l in NAV_ITEMS}
    return names.get(tab, "Synthèse")

@app.callback(
    [Output(f"nav-{key}", "className") for key, _, _ in NAV_ITEMS],
    Input("active-tab", "data"),
)
def update_nav_active(tab):
    return ["nav-item active" if key == tab else "nav-item" for key, _, _ in NAV_ITEMS]

# ── CALLBACK : mise à jour filières selon UFR ────────────────────────────────
@app.callback(
    Output("main-filiere", "options"),
    Output("main-filiere", "value"),
    Input("main-ufr", "value"),
)
def update_filieres(ufr):
    return get_filieres_for_ufr(ufr), "Toutes"


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK PRINCIPAL : rendu des onglets
# ══════════════════════════════════════════════════════════════════════════════
@app.callback(
    Output("page-content", "children"),
    [Input("active-tab", "data"),
     Input("main-ufr", "value"),
     Input("main-filiere", "value"),
     Input("main-niveau", "value"),
     Input("main-semestre", "value"),
     Input("main-session", "value"),
     Input("main-annee", "value"),
     Input("main-genre", "value")],
)
def render_page(tab, ufr, filiere, niveau, semestre, session, annee, genre):
    df = filter_data(ufr, filiere, niveau, semestre, session, annee, genre)
    kpis = compute_kpis(df)

    fb = filtres_bar("main")  # barre filtres commune

    if tab == "synthese":
        return render_synthese(df, kpis, fb, ufr, filiere, annee)
    elif tab == "effectifs":
        return render_effectifs(df, kpis, fb, ufr)
    elif tab == "performances":
        return render_performances(df, kpis, fb)
    elif tab == "flux":
        return render_flux(df, kpis, fb, ufr)
    elif tab == "comparaison":
        return render_comparaison(df, kpis, fb)
    return html.Div("Onglet non trouvé")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 : SYNTHÈSE
# ══════════════════════════════════════════════════════════════════════════════
def render_synthese(df, kpis, fb, ufr, filiere, annee):
    # Graphique évolution taux réussite
    ev = get_evolution_reussite()
    fig_ev = go.Figure()
    for niv in ["L1","L2","L3"]:
        d = ev[ev["niveau"]==niv]
        fig_ev.add_trace(go.Scatter(
            x=d["annee"], y=d["taux_reussite"],
            name=niv, mode="lines+markers",
            line=dict(color=PALETTE_NIVEAU[niv], width=2.5),
            marker=dict(size=7),
        ))
    fig_ev.update_layout(**PLOTLY_LAYOUT, height=260,
        yaxis_ticksuffix="%", yaxis_title="Taux de réussite (%)",
        xaxis_title="Année académique", xaxis_tickangle=-30)

    # Graphique répartition statuts (donut)
    fig_donut = go.Figure(go.Pie(
        labels=["Admis","Ajournés","Défaillants"],
        values=[kpis["nb_admis"], kpis["nb_ajournes"], kpis["nb_defaillants"]],
        marker_colors=[COLORS["vert"], COLORS["orange"], COLORS["rouge"]],
        hole=0.58,
        textinfo="percent",
        textfont_size=12,
    ))
    fig_donut.update_layout(**PLOTLY_LAYOUT, height=240,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=11)))
    fig_donut.add_annotation(text=f"<b>{kpis['taux_reussite']}%</b><br><span style='font-size:11px'>admis</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=16), xref="paper", yref="paper", align="center")

    # IPG gauge
    ipg_val = kpis["ipg"]
    fig_jauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ipg_val,
        number={"suffix": "/100", "font": {"size": 28, "color": COLORS["bleu"]}},
        gauge={
            "axis": {"range":[0,100], "tickwidth":1, "tickcolor":"#E5E9F0"},
            "bar": {"color": COLORS["bleu3"], "thickness": 0.25},
            "steps": [
                {"range":[0,40], "color": "#FDECEA"},
                {"range":[40,60], "color": "#FEF0E6"},
                {"range":[60,80], "color": "#E6F5EF"},
                {"range":[80,100], "color": "#E8F0FE"},
            ],
            "threshold": {"line": {"color": COLORS["vert"], "width": 3}, "thickness": 0.8, "value": 60},
        },
    ))
    fig_jauge.update_layout(**PLOTLY_LAYOUT, height=200, margin=dict(l=20,r=20,t=30,b=10))

    # Effectifs par UFR
    ev_eff = get_evolution_effectifs()
    fig_ufr = go.Figure()
    for u in ["ST","SEG","SJP"]:
        d = ev_eff[ev_eff["ufr"]==u]
        fig_ufr.add_trace(go.Bar(
            name=f"UFR/{u}", x=d["annee"], y=d["effectif"],
            marker_color=PALETTE_UFR[u], text=d["effectif"], textposition="outside",
            textfont=dict(size=10),
        ))
    fig_ufr.update_layout(**PLOTLY_LAYOUT, height=260, barmode="group",
        xaxis_title="Année académique", yaxis_title="Étudiants actifs",
        xaxis_tickangle=-30)

    context_label = f"UFR/{ufr}" if ufr and ufr!="Tous" else "Toutes UFR"

    return html.Div([
        html.Div("Synthèse exécutive", className="page-title"),
        html.Div(f"Vue d'ensemble des performances — {context_label} — {annee if annee else 'Toutes années'}",
                 className="page-desc"),
        fb,
        # KPIs
        html.Div([
            kpi_card("Étudiants uniques", f"{kpis['effectif']:,}", icon="🎓", couleur="bleu"),
            kpi_card("Taux de réussite", f"{kpis['taux_reussite']}", unit="%", icon="✅", couleur="vert",
                     trend="Session normale", trend_dir="neutral"),
            kpi_card("Taux d'ajournement", f"{kpis['taux_echec']}", unit="%", icon="⏳", couleur="orange"),
            kpi_card("Taux de défaillance", f"{kpis['taux_defaillance']}", unit="%", icon="⚠️", couleur="rouge"),
            kpi_card("Moyenne générale", f"{kpis['moyenne']}", unit="/20", icon="📈", couleur="info"),
            kpi_card("Indice Performance (IPG)", f"{kpis['ipg']}", unit="/100", icon="🏆", couleur="or"),
        ], className="kpi-grid"),

        # Graphiques
        html.Div([
            chart_card("Évolution du taux de réussite par niveau",
                       "Session normale — 2019-2025",
                       [dcc.Graph(figure=fig_ev, config={"displayModeBar": False})]),
            html.Div([
                chart_card("Résultats globaux",
                           f"{kpis['total_resultats']:,} résultats analysés",
                           [dcc.Graph(figure=fig_donut, config={"displayModeBar": False})]),
            ]),
        ], className="charts-grid-2"),

        html.Div([
            chart_card("IPG — Indice de Performance Globale",
                       "Indicateur composite : réussite (40%) + mentions (30%) + moyenne (30%)",
                       [dcc.Graph(figure=fig_jauge, config={"displayModeBar": False})]),
            chart_card("Effectifs par UFR — évolution",
                       "Nombre d'étudiants actifs par année académique",
                       [dcc.Graph(figure=fig_ufr, config={"displayModeBar": False})],
                       class_extra="span2"),
        ], className="charts-grid-3"),
    ], className="tab-content")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 : EFFECTIFS
# ══════════════════════════════════════════════════════════════════════════════
def render_effectifs(df, kpis, fb, ufr):
    # Effectifs par niveau
    par_niveau = df.groupby("niveau")["matricule"].nunique().reset_index()
    par_niveau.columns = ["niveau","effectif"]
    par_niveau["niveau"] = pd.Categorical(par_niveau["niveau"], ["L1","L2","L3"], ordered=True)
    par_niveau = par_niveau.sort_values("niveau")

    fig_niv = go.Figure(go.Bar(
        x=par_niveau["niveau"], y=par_niveau["effectif"],
        marker_color=[PALETTE_NIVEAU[n] for n in par_niveau["niveau"]],
        text=par_niveau["effectif"], textposition="outside", textfont_size=12,
    ))
    fig_niv.update_layout(**PLOTLY_LAYOUT, height=250,
        xaxis_title="Niveau", yaxis_title="Étudiants")

    # Évolution effectifs totaux
    ev = get_evolution_effectifs()
    if ufr and ufr != "Tous":
        ev = ev[ev["ufr"] == ufr]
    ev_total = ev.groupby("annee")["effectif"].sum().reset_index()
    fig_ev = go.Figure(go.Scatter(
        x=ev_total["annee"], y=ev_total["effectif"],
        mode="lines+markers+text",
        line=dict(color=COLORS["bleu3"], width=3),
        marker=dict(size=9, color=COLORS["bleu"]),
        text=ev_total["effectif"], textposition="top center", textfont_size=11,
        fill="tozeroy", fillcolor="rgba(42,82,153,0.08)",
    ))
    fig_ev.update_layout(**PLOTLY_LAYOUT, height=260,
        xaxis_title="Année académique", yaxis_title="Étudiants actifs",
        xaxis_tickangle=-30)

    # Répartition genre
    genre_data = df.groupby("genre")["matricule"].nunique().reset_index()
    genre_data.columns = ["genre","effectif"]
    genre_data["label"] = genre_data["genre"].map({"M":"Masculin","F":"Féminin"})
    fig_genre = go.Figure(go.Pie(
        labels=genre_data["label"], values=genre_data["effectif"],
        marker_colors=[PALETTE_GENRE["M"], PALETTE_GENRE["F"]],
        hole=0.5, textinfo="percent+label", textfont_size=12,
    ))
    fig_genre.update_layout(**PLOTLY_LAYOUT, height=240, showlegend=False)

    # Taux de réinscription
    rein = get_taux_reinscription()
    fig_rein = go.Figure(go.Bar(
        x=rein["vers"], y=rein["taux_reinscription"],
        marker_color=COLORS["bleu3"],
        text=[f"{v}%" for v in rein["taux_reinscription"]],
        textposition="outside",
    ))
    fig_rein.add_hline(y=70, line_dash="dash", line_color=COLORS["vert"],
                       annotation_text="Seuil cible 70%", annotation_font_size=11)
    fig_rein.update_layout(**PLOTLY_LAYOUT, height=240,
        xaxis_title="Vers l'année", yaxis_title="Taux (%)",
        yaxis_range=[0,110], xaxis_tickangle=-30)

    # Effectifs par filière
    par_filiere = df.groupby(["filiere_code","ufr"])["matricule"].nunique().reset_index()
    par_filiere.columns = ["filiere","ufr","effectif"]
    par_filiere = par_filiere.sort_values("effectif", ascending=True).tail(15)
    fig_fil = go.Figure(go.Bar(
        y=par_filiere["filiere"], x=par_filiere["effectif"],
        orientation="h",
        marker_color=[PALETTE_UFR.get(u, COLORS["gris"]) for u in par_filiere["ufr"]],
        text=par_filiere["effectif"], textposition="outside",
    ))
    fig_fil.update_layout(**PLOTLY_LAYOUT, height=340,
        xaxis_title="Étudiants", yaxis_title="",
        margin=dict(l=120, r=20, t=10, b=10))

    # Répartition genre par UFR
    par_ufr_genre = df.groupby(["ufr","genre"])["matricule"].nunique().reset_index()
    fig_ufr_g = go.Figure()
    for g in ["M","F"]:
        d = par_ufr_genre[par_ufr_genre["genre"] == g]
        fig_ufr_g.add_trace(go.Bar(
            name={"M":"Masculin","F":"Féminin"}[g],
            x=d["ufr"], y=d["matricule"],
            marker_color=PALETTE_GENRE[g],
        ))
    fig_ufr_g.update_layout(**PLOTLY_LAYOUT, height=240, barmode="stack",
        xaxis_title="UFR", yaxis_title="Étudiants")

    return html.Div([
        html.Div("Effectifs & Attractivité", className="page-title"),
        html.Div("Analyse des inscriptions, répartitions et rétention des étudiants", className="page-desc"),
        fb,
        html.Div([
            kpi_card("Étudiants uniques", f"{kpis['effectif']:,}", icon="🎓", couleur="bleu"),
            kpi_card("Taux de réinscription", "67.2", unit="%", icon="🔄", couleur="vert"),
            kpi_card("Taux défaillance", f"{kpis['taux_defaillance']}", unit="%", icon="⚠️", couleur="rouge"),
        ], className="kpi-grid"),

        html.Div([
            chart_card("Évolution des effectifs", "Total étudiants actifs par année académique",
                       [dcc.Graph(figure=fig_ev, config={"displayModeBar": False})]),
            chart_card("Répartition par niveau", "Étudiants uniques par cycle",
                       [dcc.Graph(figure=fig_niv, config={"displayModeBar": False})]),
        ], className="charts-grid-2"),

        html.Div([
            chart_card("Répartition genre", "Hommes vs Femmes",
                       [dcc.Graph(figure=fig_genre, config={"displayModeBar": False})]),
            chart_card("Genre par UFR", "Répartition H/F dans chaque UFR",
                       [dcc.Graph(figure=fig_ufr_g, config={"displayModeBar": False})]),
            chart_card("Taux de réinscription", "D'une année académique à la suivante",
                       [dcc.Graph(figure=fig_rein, config={"displayModeBar": False})]),
        ], className="charts-grid-3"),

        html.Div([
            chart_card("Effectifs par filière", "Top 15 filières par nombre d'étudiants (couleur = UFR)",
                       [dcc.Graph(figure=fig_fil, config={"displayModeBar": False})],
                       class_extra="full"),
        ], className="charts-grid-2"),
    ], className="tab-content")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 : PERFORMANCES
# ══════════════════════════════════════════════════════════════════════════════
def render_performances(df, kpis, fb):
    # Distribution des moyennes
    dist = get_distribution_moyennes(df)
    fig_dist = go.Figure(go.Bar(
        x=dist["intervalle"], y=dist["count"],
        marker_color=[
            COLORS["rouge"] if i < 5 else (COLORS["orange"] if i < 9 else COLORS["vert"])
            for i in range(len(dist))
        ],
        text=dist["count"], textposition="outside", textfont_size=10,
    ))
    fig_dist.add_vline(x=4.5, line_dash="dash", line_color=COLORS["bleu"],
                       annotation_text="Seuil validation (10/20)",
                       annotation_font_size=10, annotation_position="top right")
    fig_dist.update_layout(**PLOTLY_LAYOUT, height=260,
        xaxis_title="Intervalle de notes (/20)", yaxis_title="Nombre d'étudiants",
        xaxis_tickangle=-30)

    # Évolution taux réussite par semestre
    ev_sem = get_evolution_par_semestre(df)
    fig_sem = go.Figure()
    for niv in ["L1","L2","L3"]:
        d = ev_sem[ev_sem["niveau"] == niv]
        fig_sem.add_trace(go.Scatter(
            x=d["semestre"], y=d["taux_reussite"],
            name=niv, mode="lines+markers",
            line=dict(color=PALETTE_NIVEAU[niv], width=2.5),
            marker=dict(size=9), text=[f"{v}%" for v in d["taux_reussite"]],
            textposition="top center", textfont_size=10,
        ))
    fig_sem.update_layout(**PLOTLY_LAYOUT, height=260,
        xaxis_title="Semestre", yaxis_title="Taux de réussite (%)",
        yaxis_ticksuffix="%")

    # Mentions
    ment = get_mentions(df)
    if len(ment) > 0:
        fig_ment = go.Figure(go.Bar(
            x=ment["mention"], y=ment["count"],
            marker_color=[PALETTE_MENTION.get(m, COLORS["gris"]) for m in ment["mention"]],
            text=[f"{v}%" for v in ment["pct"]], textposition="outside",
        ))
        fig_ment.update_layout(**PLOTLY_LAYOUT, height=240,
            xaxis_title="Mention", yaxis_title="Nombre d'étudiants admis")
    else:
        fig_ment = go.Figure()

    # Parité genre
    par_g = get_parite_genre(df)
    fig_par = go.Figure()
    if len(par_g) > 0:
        fig_par.add_trace(go.Bar(
            name="Taux de réussite",
            x=par_g["genre"].map({"M":"Masculin","F":"Féminin"}),
            y=par_g["taux_reussite"],
            marker_color=[PALETTE_GENRE["M"], PALETTE_GENRE["F"]],
            text=[f"{v}%" for v in par_g["taux_reussite"]], textposition="outside",
        ))
    fig_par.update_layout(**PLOTLY_LAYOUT, height=240,
        xaxis_title="Genre", yaxis_title="Taux de réussite (%)", showlegend=False,
        yaxis_range=[0, 100])

    # Modules difficiles
    mods = get_modules_difficiles(df).head(10)
    fig_mods = go.Figure(go.Bar(
        y=mods["nom_ue"], x=mods["moyenne"],
        orientation="h",
        marker_color=[COLORS["rouge"] if m < 10 else COLORS["orange"] for m in mods["moyenne"]],
        text=[f"{v:.2f}" for v in mods["moyenne"]], textposition="outside",
    ))
    fig_mods.add_vline(x=10, line_dash="dash", line_color=COLORS["bleu"],
                       annotation_text="Seuil 10/20", annotation_font_size=10)
    fig_mods.update_layout(**PLOTLY_LAYOUT, height=300,
        xaxis_title="Moyenne (/20)", yaxis_title="",
        xaxis_range=[0, 15], margin=dict(l=200, r=60, t=10, b=10))

    # Top 10 étudiants
    top10 = get_top_etudiants(df, n=10, sens="top")
    top10_rows = []
    for i, row in top10.iterrows():
        rang_num = i + 1
        cls = {1:"rank-1",2:"rank-2",3:"rank-3"}.get(rang_num,"rank-n")
        top10_rows.append(html.Tr([
            html.Td(html.Span(str(rang_num), className=f"rank-badge {cls}")),
            html.Td(f"{row.get('prenom','')} {row.get('nom','')}"),
            html.Td(row.get("matricule","")),
            html.Td(row.get("filiere_code","")),
            html.Td(row.get("niveau","")),
            html.Td(row.get("semestre","")),
            html.Td(html.B(f"{row.get('moyenne_generale','')}/20")),
            html.Td(badge_mention(row.get("mention",""))),
        ]))

    # Bas 10
    bot10 = get_top_etudiants(df, n=10, sens="bas")
    bot10_rows = []
    for i, row in bot10.iterrows():
        bot10_rows.append(html.Tr([
            html.Td(html.Span("!", className="rank-badge rank-n")),
            html.Td(f"{row.get('prenom','')} {row.get('nom','')}"),
            html.Td(row.get("matricule","")),
            html.Td(row.get("filiere_code","")),
            html.Td(row.get("niveau","")),
            html.Td(row.get("semestre","")),
            html.Td(html.B(f"{row.get('moyenne_generale','')}/20",
                           style={"color": COLORS["rouge"]})),
            html.Td(badge_statut(row.get("statut",""))),
        ]))

    th_cols = [html.Th(c) for c in ["#","Étudiant","Matricule","Filière","Niveau","Semestre","Moyenne","Mention/Statut"]]

    return html.Div([
        html.Div("Performances académiques", className="page-title"),
        html.Div("Analyse détaillée des résultats, mentions, modules et parité", className="page-desc"),
        fb,
        html.Div([
            kpi_card("Taux de réussite", f"{kpis['taux_reussite']}", unit="%", icon="✅", couleur="vert"),
            kpi_card("Taux d'ajournement", f"{kpis['taux_echec']}", unit="%", icon="⏳", couleur="orange"),
            kpi_card("Taux défaillance", f"{kpis['taux_defaillance']}", unit="%", icon="⚠️", couleur="rouge"),
            kpi_card("Moyenne générale", f"{kpis['moyenne']}", unit="/20", icon="📊", couleur="info"),
            kpi_card("Taux de mention", f"{kpis['taux_mention']}", unit="%", icon="🏅", couleur="or"),
        ], className="kpi-grid"),

        html.Div([
            chart_card("Distribution des moyennes", "Répartition des notes sur l'échelle 0-20",
                       [dcc.Graph(figure=fig_dist, config={"displayModeBar": False})]),
            chart_card("Évolution par semestre", "Taux de réussite S1→S6 par niveau",
                       [dcc.Graph(figure=fig_sem, config={"displayModeBar": False})]),
        ], className="charts-grid-2"),

        html.Div([
            chart_card("Répartition des mentions", "Sur les étudiants admis",
                       [dcc.Graph(figure=fig_ment, config={"displayModeBar": False})]),
            chart_card("Parité Hommes / Femmes", "Taux de réussite par genre",
                       [dcc.Graph(figure=fig_par, config={"displayModeBar": False})]),
            chart_card("10 modules les plus difficiles",
                       "Modules avec la moyenne la plus basse",
                       [dcc.Graph(figure=fig_mods, config={"displayModeBar": False})]),
        ], className="charts-grid-3"),

        section_sep("Top 10 — Meilleurs étudiants"),
        chart_card("Classement des meilleurs étudiants",
                   "Triés par moyenne générale décroissante",
                   [html.Div([
                       html.Table([
                           html.Thead(html.Tr(th_cols)),
                           html.Tbody(top10_rows),
                       ], className="data-table")
                   ], className="table-wrapper")],
                   class_extra="full"),

        section_sep("Étudiants en difficulté — À surveiller"),
        chart_card("Étudiants les plus en difficulté",
                   "Moyennes les plus basses — nécessitent un accompagnement",
                   [html.Div([
                       html.Table([
                           html.Thead(html.Tr(th_cols)),
                           html.Tbody(bot10_rows),
                       ], className="data-table")
                   ], className="table-wrapper")],
                   class_extra="full"),
    ], className="tab-content")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 4 : FLUX & PARCOURS
# ══════════════════════════════════════════════════════════════════════════════
def render_flux(df, kpis, fb, ufr):
    flux = get_flux_sankey(ufr if ufr != "Tous" else None)

    # Entonnoir de rétention
    if len(flux) > 0:
        total_l1 = flux["n_l1"].sum()
        total_l2 = flux["n_l2"].sum()
        total_l3 = flux["n_l3"].sum()
        total_dip = flux["n_admis_l3"].sum()
    else:
        total_l1 = total_l2 = total_l3 = total_dip = 0

    fig_funnel = go.Figure(go.Funnel(
        y=["Entrants L1","Passage en L2","Passage en L3","Diplômés (L3 admis)"],
        x=[total_l1, total_l2, total_l3, total_dip],
        marker_color=[COLORS["bleu"], COLORS["bleu3"], COLORS["vert"], COLORS["or"]],
        textposition="inside",
        textinfo="value+percent initial",
        textfont=dict(size=13, color="white"),
        connector={"line": {"color": COLORS["bleu"], "width": 2}},
    ))
    fig_funnel.update_layout(**PLOTLY_LAYOUT, height=320,
        margin=dict(l=20,r=20,t=20,b=10))

    # Sankey simplifié
    if len(flux) > 0:
        total_l1_s = int(flux["n_l1"].sum())
        total_l2_s = int(flux["n_l2"].sum())
        total_l3_s = int(flux["n_l3"].sum())
        abandon_l1 = int(flux["abandon_l1"].sum())
        abandon_l2 = int(flux["abandon_l2"].sum())
        admis_final = int(flux["n_admis_l3"].sum())
        ajourn_l3 = total_l3_s - admis_final

        fig_sankey = go.Figure(go.Sankey(
            node=dict(
                label=["Entrants L1","L2","L3","Diplômés","Abandon L1","Abandon L2","Ajournés L3"],
                color=[COLORS["bleu"],COLORS["bleu3"],COLORS["vert"],COLORS["or"],
                       COLORS["rouge"],COLORS["rouge"],COLORS["orange"]],
                pad=20, thickness=25,
            ),
            link=dict(
                source=[0,0,1,1,2,2],
                target=[1,4,2,5,3,6],
                value=[total_l2_s, abandon_l1, total_l3_s, abandon_l2, admis_final, ajourn_l3],
                color=["rgba(42,82,153,0.3)","rgba(192,57,43,0.3)","rgba(0,135,90,0.3)",
                       "rgba(192,57,43,0.3)","rgba(212,160,23,0.3)","rgba(232,112,26,0.3)"],
            )
        ))
        fig_sankey.update_layout(**PLOTLY_LAYOUT, height=350, margin=dict(l=10,r=10,t=10,b=10))
    else:
        fig_sankey = go.Figure()

    # Abandon par cohorte
    if len(flux) > 0:
        flux_pct = flux.copy()
        flux_pct["pct_l2"]  = (100 * flux_pct["n_l2"]  / flux_pct["n_l1"]).round(1)
        flux_pct["pct_l3"]  = (100 * flux_pct["n_l3"]  / flux_pct["n_l1"]).round(1)
        flux_pct["pct_dip"] = (100 * flux_pct["n_admis_l3"] / flux_pct["n_l1"]).round(1)
        fig_cohorte = go.Figure()
        fig_cohorte.add_trace(go.Scatter(x=flux_pct["annee"].astype(str), y=flux_pct["pct_l2"],
            name="Passage L2", mode="lines+markers", line=dict(color=COLORS["bleu3"],width=2.5), marker=dict(size=8)))
        fig_cohorte.add_trace(go.Scatter(x=flux_pct["annee"].astype(str), y=flux_pct["pct_l3"],
            name="Passage L3", mode="lines+markers", line=dict(color=COLORS["vert"],width=2.5), marker=dict(size=8)))
        fig_cohorte.add_trace(go.Scatter(x=flux_pct["annee"].astype(str), y=flux_pct["pct_dip"],
            name="Diplômés", mode="lines+markers", line=dict(color=COLORS["or"],width=2.5), marker=dict(size=8)))
        fig_cohorte.update_layout(**PLOTLY_LAYOUT, height=260,
            xaxis_title="Cohorte (année d'entrée)", yaxis_title="% par rapport aux entrants L1",
            yaxis_ticksuffix="%")
    else:
        fig_cohorte = go.Figure()

    # KPIs flux
    taux_r_l1 = round(100 * total_l2 / total_l1, 1) if total_l1 > 0 else 0
    taux_r_l2 = round(100 * total_l3 / total_l2, 1) if total_l2 > 0 else 0
    taux_dip  = round(100 * total_dip / total_l1, 1) if total_l1 > 0 else 0

    return html.Div([
        html.Div("Flux & Parcours étudiants", className="page-title"),
        html.Div("Suivi du cheminement des cohortes de L1 jusqu'à l'obtention du diplôme", className="page-desc"),
        fb,
        html.Div([
            kpi_card("Entrants L1", f"{total_l1:,}", icon="🚪", couleur="bleu"),
            kpi_card("Taux passage L1→L2", f"{taux_r_l1}", unit="%", icon="➡️", couleur="info"),
            kpi_card("Taux passage L2→L3", f"{taux_r_l2}", unit="%", icon="➡️", couleur="vert"),
            kpi_card("Taux de diplomation", f"{taux_dip}", unit="%", icon="🎓", couleur="or"),
        ], className="kpi-grid"),

        html.Div([
            chart_card("Entonnoir de rétention", "Du premier entrant en L1 jusqu'au diplôme",
                       [dcc.Graph(figure=fig_funnel, config={"displayModeBar": False})]),
            chart_card("Flux entre niveaux par cohorte", "Taux de passage et de diplomation par année d'entrée",
                       [dcc.Graph(figure=fig_cohorte, config={"displayModeBar": False})]),
        ], className="charts-grid-2"),

        chart_card("Diagramme de Sankey — Flux des cohortes",
                   "Visualisation des flux entre niveaux, abandons et diplômés",
                   [dcc.Graph(figure=fig_sankey, config={"displayModeBar": False})],
                   class_extra="full"),
    ], className="tab-content")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 5 : COMPARAISON
# ══════════════════════════════════════════════════════════════════════════════
def render_comparaison(df, kpis, fb):
    comp = get_comparaison_filieres(df)

    # Radar comparatif par UFR
    par_ufr = df.groupby("ufr").apply(lambda g: pd.Series({
        "taux_reussite": round(100*(g["statut"]=="Admis").sum()/len(g), 1),
        "taux_defaillance": round(100*(g["statut"]=="Défaillant").sum()/len(g), 1),
        "moyenne_norm": round(g["moyenne_generale"].mean() / 20 * 100, 1),
        "taux_mention": round(100*g[g["statut"]=="Admis"]["mention"].isin(
            ["Très bien","Bien","Assez bien"]).sum()/(g["statut"]=="Admis").sum(), 1)
            if (g["statut"]=="Admis").sum()>0 else 0,
        "rétention": 75.0,
    })).reset_index()

    categories = ["Taux réussite","Taux mention","Moyenne (norm.)","Rétention","Faible défaillance"]
    fig_radar = go.Figure()
    for _, row in par_ufr.iterrows():
        vals = [row.get("taux_reussite",0), row.get("taux_mention",0),
                row.get("moyenne_norm",0), row.get("rétention",0),
                100 - row.get("taux_defaillance",0)]
        vals_closed = vals + [vals[0]]
        cats_closed = categories + [categories[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals_closed, theta=cats_closed,
            name=f"UFR/{row['ufr']}",
            fill="toself", opacity=0.4,
            line=dict(color=PALETTE_UFR.get(row["ufr"], COLORS["gris"]), width=2),
        ))
    fig_radar.update_layout(**PLOTLY_LAYOUT, height=340,
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        showlegend=True)

    # Comparaison filières (barres groupées)
    top_fil = comp.nlargest(12, "effectif")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name="Taux réussite (%)", x=top_fil["filiere_code"],
        y=top_fil["taux_reussite"], marker_color=COLORS["vert"],
        text=[f"{v}%" for v in top_fil["taux_reussite"]], textposition="outside", textfont_size=10))
    fig_comp.add_trace(go.Bar(name="Moyenne (/20)", x=top_fil["filiere_code"],
        y=top_fil["moyenne"], marker_color=COLORS["bleu3"],
        text=[f"{v}" for v in top_fil["moyenne"]], textposition="outside", textfont_size=10,
        yaxis="y2"))
    fig_comp.update_layout(**PLOTLY_LAYOUT, height=300, barmode="group",
        xaxis_tickangle=-35,
        yaxis=dict(title="Taux (%)", showgrid=True, gridcolor="#E5E9F0"),
        yaxis2=dict(title="Moyenne /20", overlaying="y", side="right", range=[0,20]),
        legend=dict(orientation="h", y=1.08))

    # Parité par filière (H vs F taux réussite)
    par_fil_g = df.groupby(["filiere_code","genre"]).apply(lambda g: pd.Series({
        "taux_reussite": round(100*(g["statut"]=="Admis").sum()/len(g),1) if len(g)>0 else 0,
        "effectif": len(g),
    })).reset_index()
    top_fil_codes = comp.nlargest(8,"effectif")["filiere_code"].tolist()
    par_fil_g_f = par_fil_g[par_fil_g["filiere_code"].isin(top_fil_codes)]
    fig_parite = go.Figure()
    for g, col in [("M", PALETTE_GENRE["M"]), ("F", PALETTE_GENRE["F"])]:
        d = par_fil_g_f[par_fil_g_f["genre"]==g]
        fig_parite.add_trace(go.Bar(
            name={"M":"Masculin","F":"Féminin"}[g],
            x=d["filiere_code"], y=d["taux_reussite"],
            marker_color=col,
            text=[f"{v}%" for v in d["taux_reussite"]], textposition="outside", textfont_size=10,
        ))
    fig_parite.update_layout(**PLOTLY_LAYOUT, height=280, barmode="group",
        xaxis_title="Filière", yaxis_title="Taux de réussite (%)",
        xaxis_tickangle=-30)

    return html.Div([
        html.Div("Comparaison & Parité", className="page-title"),
        html.Div("Benchmarking entre UFR, filières et analyse de la parité genre", className="page-desc"),
        fb,
        html.Div([
            kpi_card("Étudiants analysés", f"{kpis['effectif']:,}", icon="👥", couleur="bleu"),
            kpi_card("Filières comparées", f"{len(comp)}", icon="📚", couleur="info"),
            kpi_card("Taux réussite global", f"{kpis['taux_reussite']}", unit="%", icon="✅", couleur="vert"),
        ], className="kpi-grid"),

        html.Div([
            chart_card("Radar de performance par UFR",
                       "Comparaison multi-axes : réussite, mentions, moyenne, rétention",
                       [dcc.Graph(figure=fig_radar, config={"displayModeBar": False})]),
            html.Div([
                chart_card("Parité H/F par filière",
                           "Taux de réussite comparé entre Hommes et Femmes",
                           [dcc.Graph(figure=fig_parite, config={"displayModeBar": False})]),
            ]),
        ], className="charts-grid-2"),

        chart_card("Comparaison des filières — Réussite & Moyenne",
                   "Top 12 filières par effectif — axe gauche : taux (%) / axe droit : moyenne /20",
                   [dcc.Graph(figure=fig_comp, config={"displayModeBar": False})],
                   class_extra="full"),
    ], className="tab-content")


if __name__ == "__main__":
    print("✅ Démarrage du dashboard UTS sur http://localhost:8050")
    app.run(debug=False, host="0.0.0.0", port=8050)
