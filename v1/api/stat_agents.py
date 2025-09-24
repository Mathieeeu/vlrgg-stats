# Pick-rate of every agent
# Win-rate of every agent
# KPR, DPR, APR, ACS, RATIO of every agent 

import json
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter

# Import data
data_file = 'examples/vct-2023-2025_matches_raw.json'
with open(data_file, 'r') as file:
    data = json.load(file)

print(f"Number of matches loaded: {len(data)}")


# Extracting compos from the data
game_count = 0
compos = []
for i, match in enumerate(data):
    for game in match.get("games", []):
        game_count += 1
        for team in game["scoreboard"].keys():
            compo = {}
            try:
                compo["team"] = team
                compo["is_winner"] = game["win"] == team
                compo["map"] = game["map"]
                for player in game["scoreboard"][team]:
                    compo["agents"] = compo.get("agents", []) + [player["agent"]["name"]]
            except KeyError:
                print(f"Skipping match {i} due to missing keys: {match.get('id', 'Unknown ID')}")
            compos.append(compo)
        # print(f"Compos for match {i}: {compos}")
        # exit()

print(f"Number of games processed: {game_count} ({game_count / len(data):.2f} games/match)")

# Clean up compos to remove empty entries
compos = [c for c in compos if c.get("agents")]

# Count how many times each agent is picked
agent_counts = {}
for compo in compos:
    for agent in compo["agents"]:
        if agent not in agent_counts:
            agent_counts[agent] = 0
        agent_counts[agent] += 1

# Sort agents by pick count
agent_counts = dict(sorted(agent_counts.items(), key=lambda item: item[1], reverse=True))

# sort by win-rate
agent_counts = dict(sorted(agent_counts.items(), key=lambda item: sum(1 for c in compos if item[0] in c['agents'] and c['is_winner']) / item[1], reverse=True))

# Print the counts for each agent
print("Agent counts:")
for agent, count in agent_counts.items():
    print(f"{agent}: {count} picks - win-rate: {sum(1 for c in compos if agent in c['agents'] and c['is_winner']) / count:.2f}")

# Make a histogram of agent counts
plt.figure(figsize=(12, 6))
bars = plt.bar(agent_counts.keys(), agent_counts.values(), color="#32a881", edgecolor="#1C5E48")
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2, height, str(height), ha='center', va='bottom', fontsize=8, fontweight='bold', color="#1C5E48")
plt.xlabel('Agents')
plt.ylabel('Pick Counts')
plt.title(f'Agent pick counts ({game_count} games)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('output/agent_pick_counts.png')
# plt.show()




maps = ["Lotus", "Abyss", "Sunset", "Corrode", "Icebox", "Haven", "Bind", "Split", "Ascent", "Pearl", "Fracture", "Breeze"]
maps.sort()
agent_counts_with_maps = {map_name: {agent: 0 for agent in agent_counts.keys()} for map_name in maps}

# agent picks per map
for compo in compos:
    map_name = compo["map"]
    if map_name in agent_counts_with_maps:
        for agent in compo["agents"]:
            agent_counts_with_maps[map_name][agent] += 1

# print("Agent counts per map:")
# for map_name, counts in agent_counts_with_maps.items():
#     print(f"Map: {map_name}")
#     for agent, count in counts.items():
#         if count > 0:
#             print(f"  {agent}: {count}")


agent_counts_df = pd.DataFrame(agent_counts.items(), columns=['Agent', 'Pick Count'])
agent_counts_df.sort_values(by='Pick Count', ascending=False, inplace=True)

# stacked bar chart for agent pick counts per map with maps as colors and agents on the x-axis
agent_names = list(agent_counts.keys())
map_names = list(agent_counts_with_maps.keys())

# prepare data for stacked bar chart
data = {map_name: [agent_counts_with_maps[map_name][agent] for agent in agent_names] for map_name in map_names}

plt.figure(figsize=(14, 8))
bottom = [0] * len(agent_names)
for map_name, counts in data.items():
    plt.bar(agent_names, counts, bottom=bottom, label=map_name)
    bottom = [sum(x) for x in zip(bottom, counts)]

plt.xlabel('Agents')
plt.ylabel('Pick count')
plt.title(f'Agent pick counts/Map ({game_count} games)')
plt.xticks(rotation=45)
plt.legend(title="Maps", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig('output/agent_pick_counts_stacked_by_map.png')
# plt.show()





# Create a list to store compositions with additional details
compositions_summary = []

# Calculate winning and losing compos for each map
compos_by_map = {map_name: [] for map_name in maps}

for compo in compos:
    map_name = compo["map"]
    if map_name in compos_by_map:
        compos_by_map[map_name].append((tuple(sorted(compo["agents"])), compo["team"], compo["is_winner"]))

# Summarize compositions with wins and losses
for map_name, compos_list in compos_by_map.items():
    compo_stats = {}
    for compo, team, is_winner in compos_list:
        if compo not in compo_stats:
            compo_stats[compo] = {"team_counts": Counter(), "wins": 0, "losses": 0}
        compo_stats[compo]["team_counts"][team] += 1
        if is_winner:
            compo_stats[compo]["wins"] += 1
        else:
            compo_stats[compo]["losses"] += 1

    # Add summarized data to the list
    for compo, stats in compo_stats.items():
        most_played_team = stats["team_counts"].most_common(1)[0][0]
        compositions_summary.append({
            "map": map_name,
            "composition": compo,
            "most_played_team": most_played_team,
            "wins": stats["wins"],
            "losses": stats["losses"]
        })

print(f"{len(compositions_summary)} compositions across all maps.")

# Create a dictionary to store the results
map_compositions_summary = {}

for map_name in maps:
    # Filter compositions for the current map
    map_compositions = [comp for comp in compositions_summary if comp["map"] == map_name]
    
    # Calculate win-rate for each composition
    for comp in map_compositions:
        comp["win_rate"] = comp["wins"] / (comp["wins"] + comp["losses"]) if (comp["wins"] + comp["losses"]) > 0 else 0

    # Keep only compositions with at least 5 games played
    map_compositions = [comp for comp in map_compositions if (comp["wins"] + comp["losses"]) >= 5]

    # Sort compositions by win-rate and total wins
    top_by_win_rate = sorted(map_compositions, key=lambda x: x["win_rate"], reverse=True)[:5]
    top_by_total_wins = sorted(map_compositions, key=lambda x: x["wins"], reverse=True)[:5]

    # Add data to the summary dictionary
    map_compositions_summary[map_name] = {
        "map_name": map_name,
        "nb_of_games": sum(comp["wins"] + comp["losses"] for comp in map_compositions),
        "top_5_by_win_rate": top_by_win_rate,
        "top_5_by_total_wins": top_by_total_wins
    }

# Print the results
for map_name, summary in map_compositions_summary.items():
    print(f"Map: {map_name}")
    print(f"Number of games: {summary['nb_of_games']}")
    print("Top 5 compositions by win-rate:")
    for comp in summary["top_5_by_win_rate"]:
        print(f"  Composition: {comp['composition']}, Win-rate: {comp['win_rate']:.2f}, Wins: {comp['wins']}, Losses: {comp['losses']} ({comp['most_played_team']})")
    print("Top 5 compositions by total wins:")
    for comp in summary["top_5_by_total_wins"]:
        print(f"  Composition: {comp['composition']}, Wins: {comp['wins']}, Losses: {comp['losses']} ({comp['most_played_team']})")
    print()

# Write the results to a txt file
with open('output/compositions_summary.txt', 'w') as f:
    for map_name, summary in map_compositions_summary.items():
        f.write(f"Map: {map_name}\n")
        f.write(f"Number of games: {summary['nb_of_games']}\n")
        f.write("Top 5 compositions by win-rate:\n")
        for comp in summary["top_5_by_win_rate"]:
            f.write(f"  Composition: {comp['composition']}, Win-rate: {comp['win_rate']:.2f}, Wins: {comp['wins']}, Losses: {comp['losses']} ({comp['most_played_team']})\n")
        f.write("Top 5 compositions by total wins:\n")
        for comp in summary["top_5_by_total_wins"]:
            f.write(f"  Composition: {comp['composition']}, Wins: {comp['wins']}, Losses: {comp['losses']} ({comp['most_played_team']})\n")
        f.write("\n")