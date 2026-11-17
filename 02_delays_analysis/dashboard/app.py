import streamlit as st #pour le dashboard
import requests #pour l'API
import analysis #pour les calculs dans le dashboard
import plotly.express as px #pour les graphiques
from plotly.subplots import make_subplots 
import plotly.graph_objects as go 

### CONFIG
st.set_page_config(
    page_title="Getaround",
    page_icon="🚗",
    layout="wide"
)
### API
API_URL = "https://sandrine-dsfs36-getaround-api.hf.space/predict"

### CHOIX PROPOSES DANS LES LISTES (vus dans les data price)
inconnu = "Non renseigné"
marques = ['Alfa Romeo', 'Audi', 'BMW', 'Citroën', 'Ferrari', 'Fiat', 'Ford', 'Honda', 'KIA Motors',
           'Lamborghini', 'Lexus', 'Maserati', 'Mazda', 'Mercedes', 'Mini', 'Mitsubishi', 'Nissan',
           'Opel', 'PGO', 'Peugeot', 'Porsche', 'Renault', 'SEAT', 'Subaru', 'Suzuki', 'Toyota',
           'Volkswagen', 'Yamaha']
carburants = ['diesel', 'electro', 'hybrid_petrol', 'petrol']
couleurs = ['beige', 'black', 'blue', 'brown', 'green', 'grey', 'orange', 'red', 'silver', 'white']
types_voiture = ['convertible', 'coupe', 'estate', 'hatchback', 'sedan', 'subcompact', 'suv', 'van']
oui_non = {inconnu: None, "Oui": True, "Non": False}

### CHARGEMENT DES DONNEES (data delays)
@st.cache_data
def get_data():
    df = analysis.load_data()
    return analysis.prepare_rentals(df)

### MENU A GAUCHE
page_prix = "Prédiction de prix"
page_delais = "Délais entre deux locations"
page = st.sidebar.radio(
    "Choisir une page",
    [page_prix, page_delais],
    captions=["Pour les utilisateurs", "Pour le product manager"],
)

### PAGE 1 : API DE PREDICTION (pour les utilisateurs)
if page == page_prix:
    st.title("Prédiction de prix de location")
    st.markdown("Vous mettez en location votre voiture ? Cet outil vous permet d'estimer le prix de location par jour.")


    with st.form("formulaire_prix"):

        st.subheader("A remplir obligatoirement", anchor=False)
        with st.container(border=True):
            col1, col2 = st.columns(2)
            mileage = col1.number_input("Kilométrage (km)", min_value=0, value=141080, step=1000)
            engine_power = col2.number_input("Puissance du moteur (chevaux)", min_value=1, value=120, step=5)

        st.subheader("Informations optionnelles", anchor=False)
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(4)
            model_key = col1.selectbox("Marque", [inconnu] + marques)
            fuel = col2.selectbox("Carburant", [inconnu] + carburants)
            paint_color = col3.selectbox("Couleur", [inconnu] + couleurs)
            car_type = col4.selectbox("Type de véhicule", [inconnu] + types_voiture)

            col1, col2, col3, col4 = st.columns(4)
            private_parking_available = col1.selectbox("Parking privé disponible", list(oui_non))
            has_gps = col2.selectbox("GPS", list(oui_non))
            has_air_conditioning = col3.selectbox("Climatisation", list(oui_non))
            automatic_car = col4.selectbox("Boîte automatique", list(oui_non))

            col1, col2, col3, col4 = st.columns(4)
            has_getaround_connect = col1.selectbox("Getaround Connect", list(oui_non))
            has_speed_regulator = col2.selectbox("Régulateur de vitesse", list(oui_non))
            winter_tires = col3.selectbox("Pneus hiver", list(oui_non))

        submit = st.form_submit_button("Prédire le prix")

    if submit:
        voiture = {
            "model_key": None if model_key == inconnu else model_key,
            "mileage": mileage,
            "engine_power": engine_power,
            "fuel": None if fuel == inconnu else fuel,
            "paint_color": None if paint_color == inconnu else paint_color,
            "car_type": None if car_type == inconnu else car_type,
            "private_parking_available": oui_non[private_parking_available],
            "has_gps": oui_non[has_gps],
            "has_air_conditioning": oui_non[has_air_conditioning],
            "automatic_car": oui_non[automatic_car],
            "has_getaround_connect": oui_non[has_getaround_connect],
            "has_speed_regulator": oui_non[has_speed_regulator],
            "winter_tires": oui_non[winter_tires],
        }
        st.json(voiture, expanded=False)
        try:
            with st.spinner("Calcul en cours..."):
                reponse = requests.post(API_URL, json={"input": [list(voiture.values())]}, timeout=60)
                reponse.raise_for_status()
            prix = reponse.json()["prediction"][0]
            st.success(f"Prix de location suggéré : {prix:.0f} € par jour")
        except requests.exceptions.HTTPError as erreur:
            st.error(f"L'API a répondu avec une erreur : code {erreur.response.status_code}")
        except Exception as erreur:
            st.error(f"L'API n'a pas répondu ({type(erreur).__name__}). Réessayez dans quelques instants.")

### PAGE 2 : DELAIS (pour le product manager)
if page == page_delais:
    st.title("Délai minimum entre deux locations")
    st.markdown("Page pour le product manager : choisir le délai minimum à imposer entre deux locations.")


    rentals_with_known_delay = get_data()
    sans_delai = analysis.indicateurs(rentals_with_known_delay, 0)

    with st.container(border=True):
        st.subheader("Situation actuelle")
        col1, col2 = st.columns(2)
        col1.metric("Retard de la location précédente", f"{sans_delai['% retards']:.1f} %")
        col2.metric("Retards problématiques", f"{sans_delai['% problematiques']:.1f} %")
        col2.caption(f"soit {sans_delai['% problematiques sur retards']:.1f} % des retards")

    with st.container(border=True):
        st.subheader("Avec un délai minimum")
        col1, col2 = st.columns(2)

        with col2.container(border=True):
            threshold = st.slider("Choix du délai (minutes)", min_value=0, max_value=720, value=120, step=30)

        avec_delai = analysis.indicateurs(rentals_with_known_delay, threshold)

        col1.metric(
            "Locations bloquées (donc manque à gagner)",
            f"{avec_delai['locations bloquées']} ({avec_delai['% locations bloquées']:.1f} %)"
            )

        
        col1, col2 = st.columns(2)
        col1.metric(
            "Retard de la location précédente",
            f"{avec_delai['% retards']:.1f} %",
            delta=f"{avec_delai['% retards'] - sans_delai['% retards']:.1f} points",
            delta_color="inverse",
        )
        col2.metric(
            "Retards problématiques",
            f"{avec_delai['% problematiques']:.1f} %",
            delta=f"{avec_delai['% problematiques'] - sans_delai['% problematiques']:.1f} points",
            delta_color="inverse",
        )
        col2.caption(f"soit {avec_delai['% problematiques sur retards']:.1f} % des retards")

        
        graph = analysis.statut_locations(rentals_with_known_delay, threshold)

        fig = px.histogram(
            graph,
            x='time_delta_with_previous_rental_in_minutes',
            color='statut',
            color_discrete_map={
                'Sans problème non bloquée': 'lightblue',
                'Problématique non bloquée': 'royalblue',
                'Sans problème bloquée': '#FDBA74',
                'Problématique bloquée': '#EA580C',
            },
            category_orders={'statut': ['Sans problème non bloquée', 'Sans problème bloquée', 'Problématique non bloquée', 'Problématique bloquée']},
            title="Nombre de locations en fonction de l'écart avec la location précédente",
        )
        fig.update_traces(xbins=dict(start=-15, end=735, size=30))
        fig.update_layout(
            bargap=0.1, 
            xaxis_title="Écart avec la location précédente (min)", 
            yaxis_title="Nombre de locations", legend_title_text="",
            height=350,
            margin=dict(t=30, b=10)
            )
        st.plotly_chart(fig, use_container_width=True)


    tableau = analysis.tableau_seuils(rentals_with_known_delay)

    with st.container(border=True):
        st.subheader("Effet du délai")
        col1, col2 = st.columns([2, 1])

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Scatter(x=tableau['threshold'], y=tableau['locations bloquées'],
                       name="Locations bloquées", mode="lines+markers", line=dict(color="darkorange")),
            secondary_y=False,
        )
        fig2.add_trace(
            go.Scatter(x=tableau['threshold'], y=tableau['problématiques'],
                       name="Cas problématiques restants", mode="lines+markers", line=dict(color="royalblue")),
            secondary_y=True,
        )
        fig2.update_layout(xaxis_title="Délai minimum (min)", legend_title_text="", height=350, margin=dict(t=30, b=10))
        fig2.update_yaxes(title_text="Locations bloquées", title_font=dict(color="darkorange"), secondary_y=False)
        fig2.update_yaxes(title_text="Cas problématiques restants", title_font=dict(color="royalblue"), secondary_y=True)
        col1.plotly_chart(fig2, use_container_width=True)

        gain = analysis.gain_par_tranche(tableau)
        col2.dataframe(
            gain, 
            hide_index=True, 
            use_container_width=True,
            height=350,
            column_config={
                "de": st.column_config.NumberColumn("de", alignment="left"),
                "à": st.column_config.NumberColumn("à", alignment="left"),
                "locations bloquées en plus": st.column_config.NumberColumn("Bloquées +", help="Locations bloquées en plus sur cette tranche", alignment="left"),
                "problèmes évités en plus": st.column_config.NumberColumn("Évités +", help="Problèmes évités en plus sur cette tranche", alignment="left"),
            },
            )

        
    
    st.caption(
        f"Calculs faits sur les {len(rentals_with_known_delay)} locations qui suivent une autre location "
        "de moins de 12 h et dont on connaît l'heure de retour de la location précédente.  \n"
        "Hypothèse : une location bloquée est perdue (elle n'est pas décalée)."
    )
