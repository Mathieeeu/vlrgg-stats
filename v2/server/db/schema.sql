-- Schéma généré automatiquement à partir des modèles Python
-- Ne pas modifier manuellement - utiliser schema_generator.py

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    url TEXT,
    title TEXT,
    status TEXT,
    prize_pool INTEGER,
    start_date DATE,
    end_date DATE,
    region TEXT,
    event_name TEXT,
    location TEXT,
    thumbnail TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT,
    short_name TEXT,
    region TEXT,
    logo_url TEXT,
    team_url TEXT
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY,
    url TEXT,
    event_id INTEGER,
    series TEXT,
    date DATE,
    time TEXT,
    patch TEXT,
    picks TEXT,
    bans TEXT,
    decider TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS games (
    game_id INTEGER PRIMARY KEY,
    match_id INTEGER,
    url TEXT,
    map TEXT,
    pick TEXT,
    win TEXT,
    duration TEXT,
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS match_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    team_id INTEGER,
    score INTEGER,
    is_winner BOOLEAN,
    picks TEXT,
    bans TEXT,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS game_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    team_id INTEGER,
    score INTEGER,
    t_score INTEGER,
    ct_score INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS economy_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    team_id INTEGER,
    pistol INTEGER,
    eco_played INTEGER,
    eco_won INTEGER,
    semi_eco_played INTEGER,
    semi_eco_won INTEGER,
    semi_buy_played INTEGER,
    semi_buy_won INTEGER,
    full_buy_played INTEGER,
    full_buy_won INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS round_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    round_number INTEGER,
    winner TEXT,
    score TEXT,
    win_type TEXT,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    player_id INTEGER,
    team_id INTEGER,
    agent_name TEXT,
    agent_icon_url TEXT,
    ratio_both REAL,
    ratio_t REAL,
    ratio_ct REAL,
    acs_both INTEGER,
    acs_t INTEGER,
    acs_ct INTEGER,
    k_both INTEGER,
    k_t INTEGER,
    k_ct INTEGER,
    d_both INTEGER,
    d_t INTEGER,
    d_ct INTEGER,
    a_both INTEGER,
    a_t INTEGER,
    a_ct INTEGER,
    kddiff_both INTEGER,
    kddiff_t INTEGER,
    kddiff_ct INTEGER,
    kast_both REAL,
    kast_t REAL,
    kast_ct REAL,
    adr_both REAL,
    adr_t REAL,
    adr_ct REAL,
    hs_both REAL,
    hs_t REAL,
    hs_ct REAL,
    fk_both INTEGER,
    fk_t INTEGER,
    fk_ct INTEGER,
    fd_both INTEGER,
    fd_t INTEGER,
    fd_ct INTEGER,
    fkddiff_both INTEGER,
    fkddiff_t INTEGER,
    fkddiff_ct INTEGER,
    multikills_2k INTEGER,
    multikills_3k INTEGER,
    multikills_4k INTEGER,
    multikills_5k INTEGER,
    clutches_1v1 INTEGER,
    clutches_1v2 INTEGER,
    clutches_1v3 INTEGER,
    clutches_1v4 INTEGER,
    clutches_1v5 INTEGER,
    eco INTEGER,
    plant INTEGER,
    defuse INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);
