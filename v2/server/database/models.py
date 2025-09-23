from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import date as date_type, datetime

@dataclass
class Event:
    id: int
    url: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    prize_pool: Optional[int] = None
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None
    region: Optional[str] = None
    event_name: Optional[str] = None
    location: Optional[str] = None
    thumbnail: Optional[str] = None

@dataclass 
class Team:
    id: int
    name: Optional[str] = None
    short_name: Optional[str] = None
    region: Optional[str] = None
    logo_url: Optional[str] = None
    team_url: Optional[str] = None

@dataclass
class Player:
    id: int
    name: Optional[str] = None

@dataclass
class Match:
    match_id: int
    url: Optional[str] = None
    event_id: Optional[int] = None
    series: Optional[str] = None
    date: Optional[date_type] = None
    time: Optional[str] = None
    patch: Optional[str] = None
    picks: Optional[str] = None  # (JSON string pour garder l'ordre)
    bans: Optional[str] = None   # (JSON string pour garder l'ordre)
    decider: Optional[str] = None

@dataclass
class Game:
    game_id: int
    match_id: Optional[int] = None
    url: Optional[str] = None
    map: Optional[str] = None
    pick: Optional[str] = None
    win: Optional[str] = None
    duration: Optional[str] = None

@dataclass
class MatchTeam:
    """Relation many2many entre matches et équipes"""
    id: Optional[int] = None
    match_id: Optional[int] = None
    team_id: Optional[int] = None  # clé étrangère vers teams.id
    score: Optional[int] = None
    is_winner: Optional[bool] = None
    picks: Optional[str] = None  # (JSON array des picks de l'équipe dans l'ordre)
    bans: Optional[str] = None   # (JSON array des bans de l'équipe dans l'ordre)

@dataclass
class GameScore:
    """Scores de parties par équipe"""
    id: Optional[int] = None
    game_id: Optional[int] = None
    team_id: Optional[int] = None
    score: Optional[int] = None
    t_score: Optional[int] = None   # t = score en tant qu'attaquant
    ct_score: Optional[int] = None  # ct = score en tant que def

@dataclass
class EconomyStats:
    """statistiques économiques par équipe et par partie"""
    id: Optional[int] = None
    game_id: Optional[int] = None
    team_id: Optional[int] = None
    pistol: Optional[int] = None
    eco_played: Optional[int] = None
    eco_won: Optional[int] = None
    semi_eco_played: Optional[int] = None
    semi_eco_won: Optional[int] = None
    semi_buy_played: Optional[int] = None
    semi_buy_won: Optional[int] = None
    full_buy_played: Optional[int] = None
    full_buy_won: Optional[int] = None

@dataclass
class RoundHistory:
    """Historique des rounds d'une partie"""
    id: Optional[int] = None
    game_id: Optional[int] = None
    round_number: Optional[int] = None
    winner: Optional[str] = None
    score: Optional[str] = None
    win_type: Optional[str] = None

@dataclass
class PlayerStats:
    """Statistiques complètes par joueur par partie"""
    id: Optional[int] = None
    game_id: Optional[int] = None
    player_id: Optional[int] = None
    team_id: Optional[int] = None
    agent_name: Optional[str] = None
    agent_icon_url: Optional[str] = None
    
    # Ratios de vlrgg
    ratio_both: Optional[float] = None
    ratio_t: Optional[float] = None
    ratio_ct: Optional[float] = None
    
    # ACS
    acs_both: Optional[int] = None
    acs_t: Optional[int] = None
    acs_ct: Optional[int] = None
    
    # K
    k_both: Optional[int] = None
    k_t: Optional[int] = None
    k_ct: Optional[int] = None
    
    # D
    d_both: Optional[int] = None
    d_t: Optional[int] = None
    d_ct: Optional[int] = None
    
    # A
    a_both: Optional[int] = None
    a_t: Optional[int] = None
    a_ct: Optional[int] = None
    
    # KD diff
    kddiff_both: Optional[int] = None
    kddiff_t: Optional[int] = None
    kddiff_ct: Optional[int] = None
    
    # KAST
    kast_both: Optional[float] = None
    kast_t: Optional[float] = None
    kast_ct: Optional[float] = None

    # ADR
    adr_both: Optional[float] = None
    adr_t: Optional[float] = None
    adr_ct: Optional[float] = None
    
    # HS%
    hs_both: Optional[float] = None
    hs_t: Optional[float] = None
    hs_ct: Optional[float] = None
    
    # FK
    fk_both: Optional[int] = None
    fk_t: Optional[int] = None
    fk_ct: Optional[int] = None
    
    # FD
    fd_both: Optional[int] = None
    fd_t: Optional[int] = None
    fd_ct: Optional[int] = None
    
    # FKFD diff
    fkddiff_both: Optional[int] = None
    fkddiff_t: Optional[int] = None
    fkddiff_ct: Optional[int] = None
    
    # multikills
    multikills_2k: Optional[int] = None
    multikills_3k: Optional[int] = None
    multikills_4k: Optional[int] = None
    multikills_5k: Optional[int] = None
    
    # clutches
    clutches_1v1: Optional[int] = None
    clutches_1v2: Optional[int] = None
    clutches_1v3: Optional[int] = None
    clutches_1v4: Optional[int] = None
    clutches_1v5: Optional[int] = None
    
    # autres
    eco: Optional[int] = None
    plant: Optional[int] = None
    defuse: Optional[int] = None



# mapping des modèles vers les noms de tables
MODEL_TO_TABLE = {
    Event: 'events',
    Team: 'teams',
    Player: 'players',
    Match: 'matches',
    MatchTeam: 'match_teams',
    Game: 'games',
    GameScore: 'game_scores',
    EconomyStats: 'economy_stats',
    RoundHistory: 'round_history',
    PlayerStats: 'player_stats'
}

# mapping inverse pour faciliter les requêtes
TABLE_TO_MODEL = {v: k for k, v in MODEL_TO_TABLE.items()}



# Modèles avec clés primaires auto-incrémentées
AUTO_INCREMENT_MODELS = {
    MatchTeam, GameScore, EconomyStats, RoundHistory, PlayerStats
}
# Modèles avec clés primaires définies par l'utilisateur
USER_DEFINED_KEY_MODELS = {
    Event, Team, Player, Match, Game
}



# Champs de clés étrangères pour validation
FOREIGN_KEY_FIELDS = {
    'match_teams': {
        'match_id': ('matches', 'match_id'),
        'team_id': ('teams', 'id')
    },
    'games': {
        'match_id': ('matches', 'match_id')
    },
    'game_scores': {
        'game_id': ('games', 'game_id'),
        'team_id': ('teams', 'id')
    },
    'economy_stats': {
        'game_id': ('games', 'game_id'),
        'team_id': ('teams', 'id')
    },
    'round_history': {
        'game_id': ('games', 'game_id')
    },
    'player_stats': {
        'game_id': ('games', 'game_id'),
        'player_id': ('players', 'id'),
        'team_id': ('teams', 'id')
    },
    'matches': {
        'event_id': ('events', 'id')
    }
}



def get_table_name(model_class) -> str:
    """obtenir le nom de table pour un modele donné"""
    return MODEL_TO_TABLE.get(model_class, model_class.__name__.lower())

def get_model_class(table_name: str):
    """ Obtenir la classe de modèle pour un nom de table donné"""
    return TABLE_TO_MODEL.get(table_name)

def is_auto_increment_model(model_class) -> bool:
    """Vérif si un modèle utilise une clé primaire auto incrémentée"""
    return model_class in AUTO_INCREMENT_MODELS

def get_foreign_keys(table_name: str) -> Dict[str, tuple]:
    """Obtenir les clés étrangères pour une table donnée"""
    return FOREIGN_KEY_FIELDS.get(table_name, {})
