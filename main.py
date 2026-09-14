from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pandas as pd
from collections import defaultdict
import os

# --- MOTEUR DE RECOMMANDATION ---
class DraftRecommender
    def __init__(self, matchups_csv_path, synergies_csv_path, C_bayesian=10, synergy_weight=1.0)
        self.C = C_bayesian
        self.global_wr = 0.50
        self.synergy_weight = synergy_weight
        
        self.matchup_weights = {
            Top {Top 2.5, Jungle 1.2, Mid 1.0, ADC 0.8, Support 0.8},
            Jungle {Top 1.0, Jungle 1.2, Mid 1.0, ADC 1.0, Support 1.0},
            Mid {Top 1.0, Jungle 1.2, Mid 2.5, ADC 1.0, Support 1.0},
            ADC {Top 0.8, Jungle 1.0, Mid 1.0, ADC 2.0, Support 2.0},
            Support {Top 0.8, Jungle 1.0, Mid 1.0, ADC 2.0, Support 2.0}
        }
        
        self.synergy_weights = {
            Top {Top 1.0, Jungle 1.2, Mid 1.0, ADC 1.0, Support 1.0},
            Jungle {Top 1.2, Jungle 1.0, Mid 1.5, ADC 1.0, Support 1.2},
            Mid {Top 1.0, Jungle 1.5, Mid 1.0, ADC 1.0, Support 1.2},
            ADC {Top 1.0, Jungle 1.0, Mid 1.0, ADC 1.0, Support 2.5},
            Support {Top 1.0, Jungle 1.2, Mid 1.2, ADC 2.5, Support 1.0}
        }
        
        self._load_matchups(matchups_csv_path)
        self._load_synergies(synergies_csv_path)

    def _load_matchups(self, path)
        self.matchups = defaultdict(lambda defaultdict(lambda defaultdict(dict)))
        if os.path.exists(path)
            df = pd.read_csv(path)
            for _, row in df.iterrows()
                self.matchups[row['champ_a']][row['role_a']][row['champ_b']][row['role_b']] = {
                    'winrate' row['winrate'], 'matches' row['matches']
                }

    def _load_synergies(self, path)
        self.synergies = {}
        if os.path.exists(path)
            df = pd.read_csv(path)
            for _, row in df.iterrows()
                key = (row['champ_1'], row['role_1'], row['champ_2'], row['role_2'])
                self.synergies[key] = {'winrate' row['winrate'], 'matches' row['matches']}

    def _get_synergy_key(self, cA, rA, cB, rB)
        duo = sorted([(cA, rA), (cB, rB)])
        return (duo[0][0], duo[0][1], duo[1][0], duo[1][1])

    def _bayesian_smoothing(self, raw_wr, matches)
        return ((self.C  self.global_wr) + (matches  raw_wr))  (self.C + matches)

    def evaluer_candidat(self, candidat_champ, candidat_role, ennemis, allies)
        score_total = 0.0
        
        if ennemis
            score_ennemis = 0.0
            poids_total_ennemis = 0.0
            for e_champ, e_role in ennemis
                poids = self.matchup_weights.get(candidat_role, {}).get(e_role, 1.0)
                try
                    stats = self.matchups[candidat_champ][candidat_role][e_champ][e_role]
                    wr_lisse = self._bayesian_smoothing(stats['winrate'], stats['matches'])
                    score_ennemis += (wr_lisse  poids)
                except KeyError
                    score_ennemis += (0.50  poids)
                poids_total_ennemis += poids
            score_total += (score_ennemis  max(poids_total_ennemis, 1.0))
        else
            score_total += 0.50

        if allies
            bonus_synergie = 0.0
            poids_total_allies = 0.0
            for a_champ, a_role in allies
                poids_syn = self.synergy_weights.get(candidat_role, {}).get(a_role, 1.0)
                poids_total_allies += poids_syn
                cle = self._get_synergy_key(candidat_champ, candidat_role, a_champ, a_role)
                if cle in self.synergies
                    stats = self.synergies[cle]
                    wr_lisse = self._bayesian_smoothing(stats['winrate'], stats['matches'])
                    bonus_synergie += ((wr_lisse - 0.50)  poids_syn)
            score_total += (bonus_synergie  max(poids_total_allies, 1.0))  self.synergy_weight

        return score_total

    def recommander(self, role_recherche, ennemis, allies, bans, joueur_pool, top_n=5)
        champions_indisponibles = set([c for c, r in ennemis] + [c for c, r in allies] + bans)
        resultats = []
        for champ in joueur_pool
            if champ in champions_indisponibles 
                continue
            score = self.evaluer_candidat(champ, role_recherche, ennemis, allies)
            resultats.append((champ, score))
        resultats.sort(key=lambda x x[1], reverse=True)
        return resultats[top_n]


# --- SCHÉMAS DE DONNÉES API ---
class ChampionRole(BaseModel)
    champion str
    role str

class DraftRequest(BaseModel)
    joueur_pool List[str]
    role_recherche str
    type_partie str
    bans List[str]
    equipe_alliee List[ChampionRole]
    equipe_ennemie List[ChampionRole]


# --- INITIALISATION API & MOTEUR ---
app = FastAPI(title=LoL Draft Recommender API)
moteur = DraftRecommender(
    matchups_csv_path=league_matchups.csv,
    synergies_csv_path=league_synergies_completes.csv,
    C_bayesian=10
)

# --- ROUTES ---
@app.post(draftrecommend)
def get_recommendations(req DraftRequest)
    poids_synergie = 1.0 
    if req.type_partie == Solo Q
        poids_synergie = 0.5
    elif req.type_partie == Clash
        poids_synergie = 1.5
    moteur.synergy_weight = poids_synergie
    
    ennemis_tuples = [(e.champion, e.role) for e in req.equipe_ennemie]
    allies_tuples = [(a.champion, a.role) for a in req.equipe_alliee]
    
    recos = moteur.recommander(
        role_recherche=req.role_recherche,
        ennemis=ennemis_tuples,
        allies=allies_tuples,
        bans=req.bans,
        joueur_pool=req.joueur_pool,
        top_n=5
    )
    
    return {
        role_recherche req.role_recherche,
        type_partie req.type_partie,
        recommandations [
            {champion champ, score round(score  100, 2)} 
            for champ, score in recos
        ]
    }