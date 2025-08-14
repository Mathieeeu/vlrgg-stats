import json
import pandas as pd

def generate_player_team_stats_csv(json_file_path, output_csv_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        matches = json.load(file)

    team_data_file = 'data/teams.json'
    with open(team_data_file, 'r', encoding='utf-8') as file:
        teams_data = json.load(file)

    player_team_stats = {}

    for match in matches:
        for game in match.get("games", []):
            scoreboard = game.get("scoreboard", {})
            for team, players in scoreboard.items():
                for player in players:
                    player_key = (player.get("name"), player.get("team"))
                    stats = player.get("stats", {})

                    if player_key not in player_team_stats:
                        player_team_stats[player_key] = {
                            "player_name": player.get("name"),
                            "team": player.get("team"),
                            "region": next(
                                (region for region, teams in teams_data["regions"].items() if player.get("team") in teams),
                                "unknown"
                            ),
                            "rounds": 0,
                            "acs_both": 0,
                            "k_both": 0,
                            "d_both": 0,
                            "a_both": 0,
                            "kddiff_both": 0,
                            "kast_both": 0,
                            "adr_both": 0,
                            "hs_both": 0,
                            "fk_both": 0,
                            "fd_both": 0,
                            "fkddiff_both": 0,
                            "2k": 0,
                            "3k": 0,
                            "4k": 0,
                            "5k": 0,
                            "1v1": 0,
                            "1v2": 0,
                            "1v3": 0,
                            "1v4": 0,
                            "1v5": 0,
                            "eco": 0,
                            "plant": 0,
                            "defuse": 0,
                            "games_played": 0
                        }

                    keys = {
                        "acs_both": ["acs", "both", '0'],
                        "k_both": ["k", "both", '0'],
                        "d_both": ["d", "both", '0'],
                        "a_both": ["a", "both", '0'],
                        "kddiff_both": ["kddiff", "both", '0'],
                        "kast_both": ["kast", "both", '0%'],
                        "adr_both": ["adr", "both", '0'],
                        "hs_both": ["hs", "both", '0%'],
                        "fk_both": ["fk", "both", '0'],
                        "fd_both": ["fd", "both", '0'],
                        "fkddiff_both": ["fkddiff", "both", '0'],
                        "2k": ["multikills", "2k", '0'],
                        "3k": ["multikills", "3k", '0'],
                        "4k": ["multikills", "4k", '0'],
                        "5k": ["multikills", "5k", '0'],
                        "1v1": ["clutches", "1v1", '0'],
                        "1v2": ["clutches", "1v2", '0'],
                        "1v3": ["clutches", "1v3", '0'],
                        "1v4": ["clutches", "1v4", '0'],
                        "1v5": ["clutches", "1v5", '0'],
                        "eco": ["eco", '0'],
                        "plant": ["plant", '0'],
                        "defuse": ["defuse", '0']
                    }

                    for key, values in keys.items():
                        try:
                            stat_key = values[0]
                            default_value = values[-1]
                            sub_key = values[1] if len(values) > 2 else None
                            value = stats.get(stat_key, {})
                            if sub_key:
                                value = value.get(sub_key, default_value)
                            player_team_stats[player_key][key] += int(value.replace('%', '').replace('+', '')) if isinstance(value, str) else value
                        except (ValueError, TypeError):
                            player_team_stats[player_key][key] += 0
                    player_team_stats[player_key]["rounds"] += len(game.get("history", []))
                    player_team_stats[player_key]["games_played"] += 1

    consolidated_stats = []
    for (player_name, team), stats in player_team_stats.items():
        keys = [
            "acs_both",
            "k_both",
            "d_both",
            "a_both",
            "kddiff_both",
            "kast_both",
            "adr_both",
            "hs_both",
            "fk_both",
            "fd_both",
            "fkddiff_both",
            "2k", "3k", "4k", "5k", 
            "1v1", "1v2", "1v3", "1v4", "1v5",
            "eco", "plant", "defuse"
        ]
        games_played = stats.get("games_played", 0)
        for key in keys:
            if key in stats and games_played > 0:
                stats[key] /= games_played
                stats[key] = round(stats[key], 8)        
        consolidated_stats.append(stats)

    df = pd.DataFrame(consolidated_stats)

    df.to_csv(output_csv_path, index=False, encoding='utf-8')
    print(f"Fichier CSV regroupé généré : {output_csv_path}")

generate_player_team_stats_csv(
    json_file_path="examples/vct-2023-2025_matches_raw.json",
    output_csv_path="output/player_stats.csv"
)