import psutil
import requests
import urllib3

# Désactive les alertes de sécurité (le certificat local de Riot est auto-signé)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_lcu_credentials():
    """Cherche le processus de LoL et extrait le port et le mot de passe."""
    for process in psutil.process_iter(['name', 'cmdline']):
        if process.info['name'] == 'LeagueClientUx.exe':
            cmdline = process.info['cmdline']
            port = None
            token = None
            
            for arg in cmdline:
                if arg.startswith('--app-port='):
                    port = arg.split('=')[1]
                elif arg.startswith('--remoting-auth-token='):
                    token = arg.split('=')[1]
                    
            if port and token:
                return {"port": port, "token": token}
    return None

def get_live_draft():
    """Se connecte au client pour récupérer l'état exact de la draft."""
    creds = get_lcu_credentials()
    if not creds:
        return {"error": "Client League of Legends non détecté. Le jeu est-il lancé ?"}

    url = f"https://127.0.0.1:{creds['port']}/lol-champ-select/v1/session"
    
    try:
        # Auth HTTP Basic avec l'utilisateur 'riot' et le token extrait
        response = requests.get(url, auth=('riot', creds['token']), verify=False)
        
        if response.status_code == 404:
            return {"error": "Vous n'êtes pas actuellement en phase de sélection des champions."}
            
        if response.status_code == 200:
            return parse_draft_data(response.json())
            
        return {"error": f"Erreur inattendue (Code {response.status_code})"}
        
    except requests.exceptions.RequestException:
        return {"error": "Impossible de communiquer avec le client LoL."}

def parse_draft_data(data):
    """Décode le JSON complexe de Riot en listes simples d'IDs de champions."""
    
    # 1. Récupération des Picks
    equipe_alliee = [player['championId'] for player in data.get('myTeam', []) if player['championId'] != 0]
    equipe_ennemie = [player['championId'] for player in data.get('theirTeam', []) if player['championId'] != 0]
    
    # 2. Récupération des Bans (cachés dans les 'actions')
    bans = []
    for action_row in data.get('actions', []):
        for action in action_row:
            if action['type'] == 'ban' and action['championId'] != 0:
                bans.append(action['championId'])
                
    # 3. Récupération du rôle assigné au joueur local (si dispo)
    local_player_cell = data.get('localPlayerCellId')
    role_recherche = "Inconnu"
    for player in data.get('myTeam', []):
        if player['cellId'] == local_player_cell:
            role_recherche = player.get('assignedPosition', 'Inconnu')
            # Riot utilise parfois des termes comme "UTILITY" pour Support ou "BOTTOM" pour ADC
            if role_recherche == "UTILITY": role_recherche = "Support"
            elif role_recherche == "BOTTOM": role_recherche = "ADC"
            break

    return {
        "success": True,
        "role_recherche": role_recherche,
        "allies": equipe_alliee,     # Ce sont des IDs numériques (ex: 62)
        "ennemis": equipe_ennemie,   # Ce sont des IDs numériques
        "bans": bans                 # Ce sont des IDs numériques
    }
