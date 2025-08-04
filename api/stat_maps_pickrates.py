import json
import matplotlib.pyplot as plt
import pandas as pd

# Import data
data_file = 'examples/vct-2023-2025_matches_raw.json'
with open(data_file, 'r') as file:
    data = json.load(file)

print(f"Number of matches loaded: {len(data)}")

# Extracting picks and bans from the data
picks = []
bans = []
deciders = []
number_of_matches = len(data)
for i, match in enumerate(data):
    try: 
        picks.extend(match["picks"])
        bans.extend(match["bans"])
        deciders.append(match["decider"])
    except KeyError:
        print(f"Skipping match {i} due to missing keys: {match.get('id', 'Unknown ID')}")

print(f"Number of bans:  {len(bans)} : {bans[:10]} ...\nNumber of picks: {len(picks)} : {picks[:10]} ...\nNumber of deciders: {len(deciders)} : {deciders[:10]} ...")

# Count how many times each map is picked, banned, or used as a decider
counts = {}
for map_name in set(picks + bans + deciders):
    counts[map_name] = picks.count(map_name) + bans.count(map_name) + deciders.count(map_name)

# Print the counts for each map
print("Map counts:")
for map_name, count in counts.items():
    print(f"{map_name}: {count}")

# unique picks and bans
unique_picks = set(picks)
unique_bans = set(bans)
unique_deciders = set(deciders)

# Compute pick and ban rates
pick_rate = {pick: picks.count(pick) / counts[pick] * 100 for pick in unique_picks}
ban_rate = {ban: bans.count(ban) / counts[ban] * 100 for ban in unique_bans}
decider_rate = {decider: deciders.count(decider) / counts[decider] * 100 for decider in unique_deciders}

# Combine pick and ban rates into a single dictionary for each map
map_stats = {}
for map_name in unique_picks.union(unique_bans):
    map_stats[map_name] = {
        "pick_rate": pick_rate.get(map_name, 0),  # 0 si la map n'est pas dans les picks
        "ban_rate": ban_rate.get(map_name, 0),    # 0 si la map n'est pas dans les bans
        "decider_rate": decider_rate.get(map_name, 0)  # 0 si la map n'est pas dans les deciders
    }

# Sort the maps by pick rate
map_stats = dict(sorted(map_stats.items(), key=lambda item: item[1]['pick_rate'], reverse=True))

# Show the results
for map_name, stats in map_stats.items():
    print(f"Map: {map_name}\t- Pick: {stats['pick_rate']:.2f}% - Ban: {stats['ban_rate']:.2f}% - Decider: {stats['decider_rate']:.2f}%")





# Convertir les données en DataFrame pour faciliter le tracé
map_stats_df = pd.DataFrame.from_dict(map_stats, orient='index').reset_index()
map_stats_df.rename(columns={'index': 'Map', 'pick_rate': 'Pick Rate', 'ban_rate': 'Ban Rate', 'decider_rate': 'Decider Rate'}, inplace=True)

# Créer le graphique
plt.figure(figsize=(10, 5))

# Barres pour les picks (vers le haut)
plt.bar(
    map_stats_df["Map"], 
    map_stats_df["Pick Rate"], 
    color="#187d6f", 
    label="Pick%",
    alpha=0.8,
    width=0.4
)

# Barres pour les bans (vers le bas, valeurs négatives)
plt.bar(
    map_stats_df["Map"], 
    -map_stats_df["Ban Rate"], 
    color="#713343", 
    label="Ban%",
    alpha=0.8,
    width=0.4
)

# Barres pour les deciders (vers le haut, mais avec une couleur différente)
plt.bar(
    map_stats_df["Map"], 
    map_stats_df["Decider Rate"],
    color="#f0a500",
    label="Decider%",
    alpha=0.8,
    width=0.1
)

# Ajouter des annotations pour les valeurs
for index, row in map_stats_df.iterrows():
    plt.text(index, row["Pick Rate"] + 1, f"{row['Pick Rate']:.2f}%", ha='center', color="#187d6f", fontsize=7, fontweight='bold')
    plt.text(index, -row["Ban Rate"] - 3, f"{row['Ban Rate']:.2f}%", ha='center', color="#713343", fontsize=7, fontweight='bold')
    plt.text(index, -3, f"{row['Decider Rate']:.2f}%", ha='center', color="#f0a500", fontsize=7, fontweight='bold')

# Ajouter des labels et une légende
plt.axhline(0, color="black", linewidth=0.5)  # Ligne horizontale pour séparer les picks et bans
plt.title("Pick/Ban/Decider Rates by map", fontsize=16)
plt.xlabel("Map", fontsize=10)
plt.ylabel("Rate (%)", fontsize=10)
plt.xticks(fontsize=12)
plt.legend(title="Rates", fontsize=8, loc="center right")
# plt.annotate(
#     "Percentages are calculated based on the presence of each map in the map pool. Here, 30% pick would mean that the map was chosen 30% of the times *it was available*.", 
#         xy=(0.5, -50), 
#         xycoords="axes fraction", 
#         fontsize=8, 
#         color="gray", 
#         ha="center"
# )

# Ajuster la mise en page et afficher le graphique
plt.tight_layout()
plt.savefig('output/vct-2023-2025_picks_bans_stacked.png', dpi=300)
# plt.show()
