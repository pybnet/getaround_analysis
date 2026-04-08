import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# Config

st.set_page_config(
    page_title="GetAround — Analyse des retards",
    page_icon="🚗",
    layout="wide"
)

DATA_URL = "https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_delay_analysis.xlsx"
API_URL  = "https://pybnet/getarounda_api.hf.space"   # ← URL du Space Hugging Face de l'API

#Initilisation

@st.cache_data
def load_data():
    data = pd.read_excel(DATA_URL)
    data = data[[
        "rental_id", "car_id", "checkin_type", "state",
        "delay_at_checkout_in_minutes",
        "previous_ended_rental_id",
        "time_delta_with_previous_rental_in_minutes",
    ]]

    # Jointure : location suivante ← location précédente (terminée)
    df_next = data[data["previous_ended_rental_id"].notna()].copy()
    df_next["previous_ended_rental_id"] = df_next["previous_ended_rental_id"].astype(int)

    prev_info = data[data["state"] == "ended"][
        ["rental_id", "delay_at_checkout_in_minutes", "checkin_type"]
    ].copy()
    prev_info.columns = ["prev_rental_id", "prev_delay", "prev_checkin_type"]

    merged = df_next.merge(
        prev_info,
        left_on="previous_ended_rental_id",
        right_on="prev_rental_id",
        how="inner",
    )
    return data, merged


data, merged = load_data()

# Sidebar

st.sidebar.title("GetAround")
st.sidebar.markdown("Analyse des retards au checkout")
st.sidebar.markdown("---")
st.sidebar.markdown("""
- [Vue globale](#vue-globale)
- [Retards au checkout](#retards-au-checkout)
- [Impact sur la location suivante](#impact-sur-la-location-suivante)
- [Simulation de seuils](#simulation-de-seuils)
- [Estimation du prix](#estimation-du-prix)
""")
st.sidebar.markdown("---")

# Titre

st.title("GetAround — Analyse des retards")
st.markdown("""
Aide à la décision pour le Product Manager : quel **seuil minimum** imposer entre deux locations,
et quel **périmètre** d'application choisir (tous les types ou Connect uniquement) ?
""")

if st.checkbox("Afficher les données brutes"):
    st.dataframe(data)

st.markdown("---")

# Global

st.header("Vue globale")

# KPIs
total        = data.shape[0]
n_mobile     = (data["checkin_type"] == "mobile").sum()
n_connect    = (data["checkin_type"] == "connect").sum()
n_canceled   = (data["state"] == "canceled").sum()
n_consec     = merged.shape[0]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total locations",    f"{total:,}")
col2.metric("Mobile",             f"{n_mobile:,}", f"{100*n_mobile/total:.1f}%")
col3.metric("Connect",            f"{n_connect:,}", f"{100*n_connect/total:.1f}%")
col4.metric("Annulées",           f"{n_canceled:,}", f"{100*n_canceled/total:.1f}%")
col5.metric("Locations consécutives", f"{n_consec:,}")

st.markdown("")

col_left, col_right = st.columns(2)

with col_left:
    # Répartition par type et statut
    counts = data.groupby(["checkin_type", "state"]).size().reset_index(name="count")
    fig = px.bar(
        counts,
        x="checkin_type", y="count", color="state",
        barmode="group", text="count",
        title="Répartition des locations par type de checkin et statut",
        labels={"checkin_type": "Type de checkin", "count": "Nombre de locations", "state": "Statut"},
        color_discrete_map={"ended": "#2ecc71", "canceled": "#e74c3c"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Taux d'annulation par type
    cancel_rate = (
        data.groupby("checkin_type")
        .apply(lambda x: round(100 * (x["state"] == "canceled").sum() / len(x), 1))
        .rename("Taux d'annulation (%)")
        .reset_index()
    )
    cancel_rate.columns = ["Type de checkin", "Taux d'annulation (%)"]

    fig = px.bar(
        cancel_rate,
        x="Type de checkin", y="Taux d'annulation (%)",
        text="Taux d'annulation (%)",
        title="Taux d'annulation par type de checkin",
        color="Type de checkin",
        color_discrete_map={"mobile": "#3498db", "connect": "#e67e22"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False, yaxis_range=[0, 25]
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Le taux d'annulation est similaire entre connect et mobile.")

st.markdown("---")

# Retards Checkout

st.header("Retards au checkout")

delays = data["delay_at_checkout_in_minutes"].dropna()
pct_late  = round(100 * (delays > 0).sum() / len(delays), 1)
pct_early = round(100 * (delays < 0).sum() / len(delays), 1)

col1, col2, col3, col4 = st.columns(4)
col1.metric("En retard (delay > 0)",   f"{pct_late}%")
col2.metric("En avance (delay < 0)",   f"{pct_early}%")
col3.metric("Retard médian (mobile)",  "+14 min")
col4.metric("Retard médian (connect)", "-9 min")

st.markdown("")
col_left, col_right = st.columns(2)

with col_left:
    # Distribution des retards
    delays_filtered = delays[(delays >= -300) & (delays <= 600)]
    fig = px.histogram(
        delays_filtered,
        nbins=80,
        title="Distribution des retards au checkout (en minutes)",
        labels={"value": "Retard (min)", "count": "Nombre de locations"},
        color_discrete_sequence=["#3498db"],
    )
    fig.add_vline(x=0, line_dash="dash", line_color="red",
                  annotation_text="À l'heure")
    fig.add_vline(x=delays.median(), line_dash="dot", line_color="orange",
                  annotation_text=f"Médiane ({delays.median():.0f} min)")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Boxplot par type de checkin
    fig = px.box(
        data[data["delay_at_checkout_in_minutes"].between(-300, 600)],
        x="checkin_type", y="delay_at_checkout_in_minutes",
        color="checkin_type",
        title="Distribution des retards par type de checkin",
        labels={
            "checkin_type": "Type de checkin",
            "delay_at_checkout_in_minutes": "Retard (min)",
        },
        color_discrete_map={"mobile": "#3498db", "connect": "#e67e22"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "57.5% des chauffeurs rendent la voiture en retard. "
    "Connect est nettement plus ponctuel : le chauffeur ouvre la voiture seul, sans contrainte de rendez-vous."
)

st.markdown("---")

# Impact loc suivante

st.header("Impact sur la location suivante")

impacted     = merged[merged["prev_delay"] > 0]
not_impacted = merged[merged["prev_delay"] <= 0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Locations consécutives",     f"{len(merged):,}")
col2.metric("Next driver impacté",        f"{len(impacted):,}",  f"{100*len(impacted)/len(merged):.1f}%")
col3.metric("→ Location suivante annulée",f"{(impacted['state']=='canceled').sum():,}")
col4.metric("→ Chauffeur a attendu",      f"{(impacted['state']=='ended').sum():,}")

st.markdown("")
col_left, col_right = st.columns(2)

with col_left:
    # Distribution du délai entre deux locations consécutives
    fig = px.histogram(
        merged,
        x="time_delta_with_previous_rental_in_minutes",
        nbins=50,
        color="checkin_type",
        barmode="overlay",
        opacity=0.7,
        title="Distribution du délai entre deux locations consécutives",
        labels={
            "time_delta_with_previous_rental_in_minutes": "Délai (min)",
            "checkin_type": "Type de checkin",
        },
        color_discrete_map={"mobile": "#3498db", "connect": "#e67e22"},
    )
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Scatter retard précédent vs délai prévu
    plot_data = merged[
        (merged["prev_delay"].between(-200, 600)) &
        (merged["time_delta_with_previous_rental_in_minutes"] <= 720)
    ].copy()
    plot_data["impact"] = plot_data["prev_delay"] > plot_data["time_delta_with_previous_rental_in_minutes"]

    fig = px.scatter(
        plot_data,
        x="time_delta_with_previous_rental_in_minutes",
        y="prev_delay",
        color="impact",
        title="Retard précédent vs délai prévu entre locations",
        labels={
            "time_delta_with_previous_rental_in_minutes": "Délai prévu (min)",
            "prev_delay": "Retard location précédente (min)",
            "impact": "Chevauchement",
        },
        color_discrete_map={True: "#e74c3c", False: "#2ecc71"},
        opacity=0.5,
    )
    fig.add_shape(
        type="line", x0=0, y0=0, x1=720, y1=720,
        line=dict(color="black", dash="dash")
    )
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Points rouges : le retard du précédent dépasse le délai prévu → chevauchement réel.")

st.markdown("---")

# Simulation seuils

st.header("Simulation de seuils")

# Tableau comparatif tous seuils
thresholds = [0, 30, 60, 120]
results = []

for sc in ["Tous", "Connect uniquement"]:
    if sc == "Connect uniquement":
        sub = merged[merged["checkin_type"] == "connect"]
        tot = data[data["checkin_type"] == "connect"].shape[0]
    else:
        sub = merged
        tot = data.shape[0]

    for t in thresholds:
        bl = sub[sub["time_delta_with_previous_rental_in_minutes"] < t].shape[0]
        sv = sub[
            (sub["prev_delay"] > 0) &
            (sub["prev_delay"] > (t - sub["time_delta_with_previous_rental_in_minutes"]))
        ].shape[0]
        results.append({
            "Scope": sc,
            "Seuil (min)": t,
            "Locations bloquées": bl,
            "% bloquées": round(100 * bl / tot, 2),
            "Cas résolus": sv,
            "Ratio (résolus / bloqués)": round(sv / bl, 2) if bl > 0 else None,
        })

df_results = pd.DataFrame(results)

col_left, col_right = st.columns(2)

with col_left:
    # Trade-off bloquées vs résolues
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Locations bloquées", "Cas problématiques résolus"]
    )
    colors_scope = {"Tous": "#3498db", "Connect uniquement": "#e67e22"}

    for sc in ["Tous", "Connect uniquement"]:
        sub = df_results[df_results["Scope"] == sc]
        fig.add_trace(
            go.Bar(
                x=sub["Seuil (min)"].astype(str), y=sub["Locations bloquées"],
                name=sc, marker_color=colors_scope[sc],
                text=sub["Locations bloquées"], textposition="outside",
                showlegend=True,
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Bar(
                x=sub["Seuil (min)"].astype(str), y=sub["Cas résolus"],
                name=sc, marker_color=colors_scope[sc],
                text=sub["Cas résolus"], textposition="outside",
                showlegend=False,
            ),
            row=1, col=2,
        )

    fig.update_layout(
        title="Trade-off : seuil minimum entre deux locations",
        barmode="group",
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="Seuil (min)", xaxis2_title="Seuil (min)",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Ratio par seuil
    df_ratio = df_results[df_results["Seuil (min)"] > 0].copy()
    fig = px.line(
        df_ratio,
        x="Seuil (min)", y="Ratio (résolus / bloqués)",
        color="Scope",
        markers=True,
        title="Ratio d'efficacité selon le seuil",
        labels={"Ratio (résolus / bloqués)": "Cas résolus / Locations bloquées"},
        color_discrete_map={"Tous": "#3498db", "Connect uniquement": "#e67e22"},
    )
    fig.add_hline(y=1, line_dash="dash", line_color="red",
                  annotation_text="Ratio = 1 (seuil d'équilibre)")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

# Tableau récapitulatif
st.subheader("Tableau récapitulatif")
st.dataframe(
    df_results[df_results["Seuil (min)"] > 0].style.highlight_max(
        subset=["Ratio (résolus / bloqués)"], color="#d5f5e3"
    ),
    use_container_width=True,
)

st.markdown("---")

# Recommandation

st.header("Recommandation")

st.markdown("""
### Recommandation

| Seuil | Scope | Locations bloquées | Cas résolus | Ratio |
|-------|-------|-------------------|-------------|-------|
| 30 min | Tous | 279 (1.3%) | 805 | 2.88 |
| 60 min | Tous | 401 (1.9%) | 754 | 1.88 |
| 60 min | Connect | 181 (4.2%) | 260 | 1.44 |
| 120 min | Tous | 666 (3.1%) | 653 | 0.98 |

**Un seuil de 60 minutes sur tous les types de checkin** offre le meilleur équilibre :
- Il résout **754 cas problématiques** tout en bloquant seulement **1.9% des créneaux**
- Au-delà de 120 min, le ratio s'inverse : on bloque plus de locations qu'on ne résout de problèmes
- Appliquer le seuil aux seules voitures Connect serait insuffisant car les retards sont majoritairement sur le **parc mobile** (61.4% en retard vs 42.9% pour Connect)
""")

st.markdown("---")

# Estimation Prix -> Fast API

st.header("Estimation du prix")
st.markdown(
    "Renseigne les caractéristiques d'une voiture pour obtenir une estimation "
    "du prix de location journalier via le modèle ML."
)

MODEL_KEYS  = ["Alfa Romeo","Audi","BMW","Citroën","Ferrari","Fiat","Ford","Honda",
               "KIA Motors","Lamborghini","Lexus","Maserati","Mazda","Mercedes",
               "Mini","Mitsubishi","Nissan","Opel","PGO","Peugeot","Porsche",
               "Renault","SEAT","Subaru","Suzuki","Toyota","Volkswagen","Yamaha"]
FUELS       = ["diesel","petrol","hybrid_petrol","electro"]
COLORS_CAR  = ["beige","black","blue","brown","green","grey","orange","red","silver","white"]
CAR_TYPES   = ["convertible","coupe","estate","hatchback","sedan","subcompact","suv","van"]

col_form1, col_form2 = st.columns(2)

with col_form1:
    st.subheader("Caractéristiques")
    model_key   = st.selectbox("Marque",          MODEL_KEYS, index=MODEL_KEYS.index("Renault"))
    car_type    = st.selectbox("Type de carrosserie", CAR_TYPES, index=CAR_TYPES.index("sedan"))
    fuel        = st.selectbox("Carburant",        FUELS, index=0)
    paint_color = st.selectbox("Couleur",          COLORS_CAR, index=COLORS_CAR.index("black"))
    mileage     = st.number_input("Kilométrage",   min_value=0, max_value=1_000_000, value=85_000, step=1_000)
    engine_power= st.number_input("Puissance (ch)",min_value=0, max_value=500,       value=120,    step=5)

with col_form2:
    st.subheader("Équipements")
    has_gps                    = st.toggle("GPS",                    value=True)
    has_air_conditioning       = st.toggle("Climatisation",          value=True)
    automatic_car              = st.toggle("Boîte automatique",      value=False)
    has_getaround_connect      = st.toggle("GetAround Connect",      value=True)
    has_speed_regulator        = st.toggle("Régulateur de vitesse",  value=True)
    private_parking_available  = st.toggle("Parking privé",          value=False)
    winter_tires               = st.toggle("Pneus hiver",            value=False)

st.markdown("")

if st.button("💰 Estimer le prix journalier", type="primary", use_container_width=False):
    payload = {
        "input": [{
            "model_key":                  model_key,
            "mileage":                    mileage,
            "engine_power":               engine_power,
            "fuel":                       fuel,
            "paint_color":                paint_color,
            "car_type":                   car_type,
            "private_parking_available":  private_parking_available,
            "has_gps":                    has_gps,
            "has_air_conditioning":       has_air_conditioning,
            "automatic_car":              automatic_car,
            "has_getaround_connect":      has_getaround_connect,
            "has_speed_regulator":        has_speed_regulator,
            "winter_tires":               winter_tires,
        }]
    }

    try:
        response = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
        response.raise_for_status()
        price = response.json()["prediction"][0]
        st.success(f"### Prix estimé : **{price:.0f} €/jour**")

    except requests.exceptions.ConnectionError:
        st.error(
            "Impossible de joindre l'API. "
            "Vérifiez que `API_URL` est correctement renseigné en haut du fichier "
            f"(valeur actuelle : `{API_URL}`)."
        )
    except requests.exceptions.Timeout:
        st.error("L'API n'a pas répondu dans le délai imparti (10s).")
    except Exception as e:
        st.error(f"Erreur inattendue : {e}")
