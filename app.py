import streamlit as st
import requests
# Importez la classe que nous avons créée précédemment depuis votre fichier
from main import DraftRecommender 

st.set_page_config(page_title="Analyseur de Draft LoL", layout="wide")

# 1. Mise en cache pour des performances instantanées
@st.cache_resource
def load_engine():
    return DraftRecommender("league_matchups.csv", "league_synergies_completes.csv", C_bayesian=10)

@st.cache_data
def load_champions():
    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/fr_FR/champion.json").json()
    return [""] + sorted([info['name'] for info in data['data'].values()])

moteur = load_engine()
liste_champions = load_champions()
roles = ["Top", "Jungle", "Mid", "ADC", "Support"]

# 2. Interface Utilisateur
st.title("🎯 Analyseur de Draft LoL")

col1, col2 = st.columns(2)
with col1:
    type_partie = st.selectbox("Type de Partie", ["Solo Q", "Flex", "Clash"])
with col2:
    role_recherche = st.selectbox("Rôle Recherché", roles)

st.markdown("---")

col_allies, col_ennemis = st.columns(2)
equipe_alliee = []
equipe_ennemie = []

# Génération dynamique des sélecteurs
with col_allies:
    st.subheader("Équipe Alliée")
    for i in range(4):
        c1, c2 = st.columns(2)
        champ = c1.selectbox(f"Allié {i+1}", liste_champions, key=f"a_c_{i}")
        role = c2.selectbox(f"Rôle {i+1}", roles, key=f"a_r_{i}")
        if champ:
            equipe_alliee.append((champ, role))

with col_ennemis:
    st.subheader("Équipe Ennemie")
    for i in range(5): # 5 ennemis possibles maximum
        c1, c2 = st.columns(2)
        champ = c1.selectbox(f"Ennemi {i+1}", liste_champions, key=f"e_c_{i}")
        role = c2.selectbox(f"Rôle {i+1}", roles, key=f"e_r_{i}")
        if champ:
            equipe_ennemie.append((champ, role))

# 3. Logique de Calcul
if st.button("Calculer les Recommandations", use_container_width=True):
    # Ajustement du poids selon le type de partie
    moteur.synergy_weight = 0.5 if type_partie == "Solo Q" else 1.5 if type_partie == "Clash" else 1.0
    
    # Appel au moteur
    recos = moteur.recommander(
        role_recherche=role_recherche,
        ennemis=equipe_ennemie,
        allies=equipe_alliee,
        bans=[], 
        joueur_pool=[c for c in liste_champions if c], # On exclut le choix vide ""
        top_n=5
    )
    
    st.success("Analyse terminée !")
    for i, (champ, score) in enumerate(recos):
        st.write(f"**#{i+1} {champ}** : Score estimé = {score*100:.2f}%")
