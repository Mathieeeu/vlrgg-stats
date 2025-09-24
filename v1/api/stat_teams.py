import json
import matplotlib.pyplot as plt
import pandas as pd

data_file = 'examples/vct-2023-2025_matches_raw.json'
with open(data_file, 'r') as file:
    data = json.load(file)

print(f"Number of matches loaded: {len(data)}")

team_data_file = 'data/teams.json'
with open(team_data_file, 'r', encoding='utf-8') as file:
    teams_data = json.load(file)

game_count = 0
teams = {}
for i, match in enumerate(data):
    for game in match.get("games", []):
        game_count += 1
        for team in game["scoreboard"].keys():
            if team in teams_data["regions"]["cn"]:
                continue
            compo = {}
            if team not in teams:
                teams[team] = {"games": 0, "wins": 0, "losses": 0, "pistol": {"played": 0, "won": 0, "lost": 0}}
            teams[team]["games"] += 1
            if game["win"] == team:
                teams[team]["wins"] += 1
            else:
                teams[team]["losses"] += 1
            # teams[team]["eco"]["played"] += game["economy"].get(team, {"eco": {"played": 0}})["eco"]["played"]
            teams[team]["pistol"]["played"] += 2
            teams[team]["pistol"]["won"] += game["economy"].get(team, {"pistol": 0})["pistol"]
            teams[team]["pistol"]["lost"] += 2 - game["economy"].get(team, {"pistol": 0})["pistol"]

print(f"Number of games processed: {game_count} ({game_count / len(data) if len(data) > 0 else 0:.2f} games/match)")    


pistol_win_rate = sorted(teams.items(), key=lambda item: item[1]["pistol"]["won"] / item[1]["pistol"]["played"], reverse=True)
print("\nTeams with highest pistol win rate:")
for team, stats in pistol_win_rate:
    print(f"{team}: {stats['pistol']['won']} pistol won out of {stats['pistol']['played']} played ({stats['pistol']['won'] / stats['pistol']['played']:.2%})")