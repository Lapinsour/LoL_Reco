import streamlit as st
import requests
from main import DraftRecommender 

st.set_page_config(page_title="Analyseur de Draft LoL", layout="wide", page_icon="⚔️")

# 1. Chargement du Moteur
@st.cache_resource
def load_engine():
    return DraftRecommender("league_matchups.csv", "league_synergies_completes.csv", C_bayesian=10)

# 2. Chargement des Champions et des Images (Data Dragon)
@st.cache_data
def load_champions_data():
    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    version = versions[0]
    data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/fr_FR/champion.json").json()
    
    # Dictionnaire pour lier le nom du champion à l'ID de son image (ex: Wukong -> MonkeyKing)
    name_to_img_id = {info['name']: info['id'] for info in data['data'].values()}
    noms_tries = [""] + sorted(list(name_to_img_id.keys()))
    
    return noms_tries, name_to_img_id, version

moteur = load_engine()
liste_champions, name_to_img_id, version = load_champions_data()
roles = ["Top", "Jungle", "Mid", "ADC", "Support"]

# Fonction utilitaire pour récupérer l'URL de l'image
def get_champ_img(nom):
    if not nom:
        # Image par défaut transparente/vide
        return "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png" 
    champ_id = name_to_img_id[nom]
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_id}.png"

# --- INTERFACE UTILISATEUR ---
st.title("🎯 Analyseur de Draft LoL")

col1, col2, col3 = st.columns(3)
with col1:
    type_partie = st.selectbox("Type de Partie", ["Solo Q", "Flex", "Clash"])
with col2:
    role_recherche = st.selectbox("Rôle Recherché", roles)
with col3:
    # Nouveau : Sélection du Champion Pool
    joueur_pool = st.multiselect("Vos champions (optionnel)", liste_champions[1:], help="Affiche le score de ces champions même s'ils ne sont pas dans le Top 5")

st.markdown("---")

col_allies, col_ennemis = st.columns(2)
equipe_alliee = []
equipe_ennemie = []

# --- DRAFT : ÉQUIPE ALLIÉE ---
with col_allies:
    st.subheader("🛡️ Équipe Alliée")
    for i in range(4):
        # 4 colonnes : Image, Champion, Rôle, Premade
        c_img, c_champ, c_role, c_premade = st.columns([1, 4, 3, 2])
        champ = c_champ.selectbox(f"Allié {i+1}", liste_champions, key=f"a_c_{i}", label_visibility="collapsed")
        role = c_role.selectbox(f"Rôle {i+1}", roles, key=f"a_r_{i}", label_visibility="collapsed")
        premade = c_premade.checkbox("Premade", key=f"a_p_{i}")
        
        c_img.image(get_champ_img(champ), width=45)
        
        if champ:
            equipe_alliee.append((champ, role, premade))

# --- DRAFT : ÉQUIPE ENNEMIE ---
with col_ennemis:
    st.subheader("⚔️ Équipe Ennemie")
    for i in range(5):
        # 3 colonnes : Image, Champion, Rôle
        c_img, c_champ, c_role = st.columns([1, 5, 4])
        champ = c_champ.selectbox(f"Ennemi {i+1}", liste_champions, key=f"e_c_{i}", label_visibility="collapsed")
        role = c_role.selectbox(f"Rôle {i+1}", roles, key=f"e_r_{i}", label_visibility="collapsed")
        
        c_img.image(get_champ_img(champ), width=45)
        
        if champ:
            equipe_ennemie.append((champ, role))

st.markdown("---")

# --- RÉSULTATS ---
if st.button("🚀 Calculer les Recommandations", use_container_width=True):
    moteur.synergy_weight = 0.5 if type_partie == "Solo Q" else 1.5 if type_partie == "Clash" else 1.0
    tous_sauf_vide = [c for c in liste_champions if c]
    
    # 1. Calcul du Top 5 Global
    recos_globales = moteur.recommander(
        role_recherche=role_recherche, ennemis=equipe_ennemie, allies=equipe_alliee,
        bans=[], joueur_pool=tous_sauf_vide, top_n=5
    )
    
    st.subheader("🏆 Top 5 Recommandations Globales")
    cols_top = st.columns(5)
    for idx, (champ, score) in enumerate(recos_globales):
        with cols_top[idx]:
            st.image(get_champ_img(champ), width=70)
            st.metric(label=f"#{idx+1} {champ}", value=f"{score*100:.1f}%")
            
    # 2. Calcul du Champion Pool (si renseigné)
    if joueur_pool:
        st.markdown("---")
        st.subheader("⭐ Scores de vos Champions")
        recos_pool = moteur.recommander(
            role_recherche=role_recherche, ennemis=equipe_ennemie, allies=equipe_alliee,
            bans=[], joueur_pool=joueur_pool, top_n=len(joueur_pool) # top_n s'adapte à la taille du pool
        )
        
        # Affichage dynamique selon le nombre de champions choisis (max 6 par ligne)
        cols_pool = st.columns(min(len(joueur_pool), 6))
        for idx, (champ, score) in enumerate(recos_pool):
            with cols_pool[idx % 6]:
                st.image(get_champ_img(champ), width=60)
                # Affichage sous forme de 'metric' pour un design Dashboard propre
                st.metric(label=champ, value=f"{score*100:.1f}%")
