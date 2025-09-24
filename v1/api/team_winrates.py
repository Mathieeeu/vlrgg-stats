import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

with open('examples/vct-2023-2025_matches_raw.json', 'r', encoding='utf-8') as f:
    matches = json.load(f)

def calculate_winrate_heatmap(team_short_name, specific_score: tuple[int, int] = None):
    score_matrix_wins = np.zeros((13, 13))  # wins
    score_matrix_counts = np.zeros((13, 13))  # games

    if specific_score is not None:
        if type(specific_score) is not tuple:
            raise ValueError("specific_score must be a tuple of (team_score, opponent_score)")
        if len(specific_score) != 2:
            raise ValueError("specific_score must be a tuple of (team_score, opponent_score)")

    for match in matches:
        try:
            if match.get("teams", [])[0].get("short_name") != team_short_name and \
            match.get("teams", [])[1].get("short_name") != team_short_name:
                continue
        except IndexError:
            continue
        for game in match.get("games", []):
            history = game.get("history", [])
            is_winner = game.get("win") == team_short_name

            team_score = 0
            opponent_score = 0

            for round_data in history:
                round_winner = round_data.get("winner")

                # afficher les urls des games où il y a eu un score spécifique
                if specific_score:
                    if team_score == specific_score[0] and opponent_score == specific_score[1]:
                        print(f"https://www.vlr.gg/{match.get('match_id')}?game={game.get('game_id')}")
                

                if round_winner == team_short_name:
                    team_score += 1
                else:
                    opponent_score += 1

                if team_score < 13 and opponent_score < 13:  # limite = 12-12
                    score_matrix_counts[team_score][opponent_score] += 1
                    if is_winner:
                        score_matrix_wins[team_score][opponent_score] += 1

            # 0-0 = global win%
            if len(history) > 0 and is_winner:
                score_matrix_wins[0][0] += 1
            score_matrix_counts[0][0] += 1

    # win%
    winrate_matrix = np.divide(
        score_matrix_wins,
        score_matrix_counts,
        out=np.full_like(score_matrix_wins, np.nan),  # NaN si jamais arrivé
        where=score_matrix_counts != 0
    )

    # matrice avec toutes les occurences de chaque score
    score_matrix = {}
    for team_score in range(13):
        for opponent_score in range(13):
            total = int(score_matrix_counts[team_score][opponent_score])
            wins = int(score_matrix_wins[team_score][opponent_score])
            losses = total - wins
            score_matrix[f"{team_score}-{opponent_score}"] = {
                "wins": wins,
                "losses": losses,
                "total": total
            }

    with open(f"output/score_matrix_{team_short_name}.json", "w", encoding="utf-8") as f:
        json.dump(score_matrix, f, indent=4, ensure_ascii=False)

    return winrate_matrix, score_matrix


def create_heatmap(winrate_matrix, team_short_name, save_path, display=True):
    # (cacher les annotations pour les cellules avec NaN)
    annot_matrix = np.where(~np.isnan(winrate_matrix), winrate_matrix * 100, np.nan)

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        winrate_matrix,
        annot=annot_matrix,
        fmt=".0f",
        cmap="Greens",
        cbar=False,
        xticklabels=range(13),
        yticklabels=range(13),
        mask=np.isnan(winrate_matrix)
    )
    plt.title(f"win% for {team_short_name}")
    plt.xlabel("Opponent Score")
    plt.ylabel("Team Score")
    plt.savefig(save_path)
    if display:
        plt.show()


team_short_name = "M8"
winrate_matrix, score_matrix = calculate_winrate_heatmap(
    team_short_name, 
    # specific_score=(12, 6)
)

create_heatmap(winrate_matrix, team_short_name, f"output/winrate_heatmap_{team_short_name}.png", display=False)