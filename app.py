import streamlit as st
import requests
from main import DraftRecommender 
import lcu_reader # Import de notre nouveau script de lecture du client

st.set_page_config(page_title="LoLPickWizz", layout="wide")

# 1. Chargement du Moteur
@st.cache_resource
def load_engine():
    return DraftRecommender("league_matchups.csv", "league_synergies_completes.csv", C_bayesian=10)

# 2. Chargement des Champions et du Traducteur d'ID
@st.cache_data
def load_champions_data():
    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    version = versions[0]
    data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/fr_FR/champion.json").json()
    
    name_to_img_id = {info['name']: info['id'] for info in data['data'].values()}
    
    # NOUVEAU : Dictionnaire pour traduire l'ID numérique de Riot (ex: 62) en Nom (ex: "Wukong")
    id_to_name = {int(info['key']): info['name'] for info in data['data'].values()}
    
    noms_tries = [""] + sorted(list(name_to_img_id.keys()))
    
    return noms_tries, name_to_img_id, id_to_name, version

moteur = load_engine()
liste_champions, name_to_img_id, id_to_name, version = load_champions_data()
roles = ["Top", "Jungle", "Mid", "ADC", "Support"]

def get_champ_img(nom):
    if not nom:
        return "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png" 
    champ_id = name_to_img_id[nom]
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_id}.png"

# --- NOUVEAU : BOUTON DE SYNCHRONISATION ---
if st.button("🔄 Synchroniser avec le client LoL", use_container_width=True):
    live_draft = lcu_reader.get_live_draft()
    
    if "error" in live_draft:
        st.error(live_draft["error"])
    else:
        # Mise à jour du Rôle (si détecté correctement)
        if live_draft["role_recherche"] in roles:
            st.session_state["role_recherche_key"] = live_draft["role_recherche"]
            
        # Traduction et mise à jour des Bans
        bans_noms = [id_to_name[champ_id] for champ_id in live_draft["bans"] if champ_id in id_to_name]
        st.session_state["bans_key"] = bans_noms
        
        # Traduction et mise à jour des Alliés
        allies_noms = [id_to_name[champ_id] for champ_id in live_draft["allies"] if champ_id in id_to_name]
        for i in range(4):
            st.session_state[f"a_c_{i}"] = allies_noms[i] if i < len(allies_noms) else ""
            
        # Traduction et mise à jour des Ennemis
        ennemis_noms = [id_to_name[champ_id] for champ_id in live_draft["ennemis"] if champ_id in id_to_name]
        for i in range(5):
            st.session_state[f"e_c_{i}"] = ennemis_noms[i] if i < len(ennemis_noms) else ""
            
        st.success("Draft synchronisée avec succès ! Les champs ont été remplis automatiquement.")

st.title("🎯 Analyseur de Draft LoL")

# --- INTERFACE UTILISATEUR ---
col1, col2, col3 = st.columns(3)
with col1:
    type_partie = st.selectbox("Type de Partie", ["Solo Q", "Flex", "Clash"])
with col2:
    # On ajoute une 'key' pour que la synchronisation puisse modifier ce champ
    role_recherche = st.selectbox("Rôle Recherché", roles, key="role_recherche_key")
with col3:
    joueur_pool = st.multiselect("Vos champions (optionnel)", liste_champions[1:], help="Affiche le score de ces champions même s'ils ne sont pas dans le Top 5")

# On ajoute une 'key' pour les bans
bans_selection = st.multiselect("🚫 Champions Bannis", liste_champions[1:], key="bans_key")

st.markdown("---")

col_allies, col_ennemis = st.columns(2)
equipe_alliee = []
equipe_ennemie = []

# --- DRAFT : ÉQUIPE ALLIÉE ---
with col_allies:
    st.subheader("🛡️ Équipe Alliée")
    for i in range(4):
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
        c_img, c_champ, c_role = st.columns([1, 5, 4])
        champ = c_champ.selectbox(f"Ennemi {i+1}", liste_champions, key=f"e_c_{i}", label_visibility="collapsed")
        role = c_role.selectbox(f"Rôle {i+1}", roles, key=f"e_r_{i}", label_visibility="collapsed")
        
        c_img.image(get_champ_img(champ), width=45)
        if champ:
            equipe_ennemie.append((champ, role))

st.markdown("---")

with st.expander("ℹ️ Comment ces pourcentages sont-ils calculés ?"):
    st.markdown("""
    Le score affiché n'est pas un simple taux de victoire global, mais une prédiction mathématique basée sur 4 piliers :

    * **Le Lissage Bayésien :** Pour éviter qu'un champion ayant 1 victoire sur 1 partie n'affiche un score biaisé de 100%, l'algorithme tire artificiellement les statistiques vers 50% lorsque l'échantillon de données est trop faible.
    * **L'Évaluation du Vis-à-vis (Moyenne Pondérée) :** Le moteur donne beaucoup plus d'importance à votre adversaire direct. Si vous cherchez un Toplaner, vos statistiques historiques contre le Top ennemi pèseront **2.5 fois plus lourd** dans la note finale que vos statistiques contre le Support ennemi.
    * **Les Synergies & le Bonus Premade :** Le système calcule le différentiel de victoire de votre champion lorsqu'il est joué avec vos alliés actuels. Si la case **Premade** est cochée, le poids de cette synergie augmente de 50% et reçoit un micro-bonus pour refléter l'avantage de la communication vocale.
    * **L'Ajustement de la Meta :** En *Solo Q*, le moteur diminue le poids des synergies d'équipe pour prioriser les victoires d'affrontements individuels (counters). À l'inverse, le mode *Clash* donne la priorité aux compositions d'équipe fortement synergiques.
    """)

# --- RÉSULTATS ---
if st.button("Choose your fighter", use_container_width=True):
    moteur.synergy_weight = 0.5 if type_partie == "Solo Q" else 1.5 if type_partie == "Clash" else 1.0
    tous_sauf_vide = [c for c in liste_champions if c]
    
    recos_globales = moteur.recommander(
        role_recherche=role_recherche, ennemis=equipe_ennemie, allies=equipe_alliee,
        bans=bans_selection, joueur_pool=tous_sauf_vide, top_n=5
    )
    
    st.subheader("Les meilleurs champions")
    cols_top = st.columns(5)
    for idx, (champ, score) in enumerate(recos_globales):
        with cols_top[idx]:
            st.image(get_champ_img(champ), width=70)
            st.metric(label=f"#{idx+1} {champ}", value=f"{score*100:.1f}%")
            
    if joueur_pool:
        st.markdown("---")
        st.subheader("Parmi vos champions")
        recos_pool = moteur.recommander(
            role_recherche=role_recherche, ennemis=equipe_ennemie, allies=equipe_alliee,
            bans=bans_selection, joueur_pool=joueur_pool, top_n=len(joueur_pool)
        )
        
        cols_pool = st.columns(min(len(joueur_pool), 6))
        for idx, (champ, score) in enumerate(recos_pool):
            with cols_pool[idx % 6]:
                st.image(get_champ_img(champ), width=60)
                st.metric(label=champ, value=f"{score*100:.1f}%")
