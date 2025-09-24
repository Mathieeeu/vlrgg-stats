import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import plotly.express as px

def apply_pca_to_player_stats(input_csv_path, output_csv_path):
    df = pd.read_csv(input_csv_path)

    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    data = df[numeric_columns]

    non_relevant_columns = ['2k', '3k', '4k', '5k', '1v1', '1v2', '1v3', '1v4', '1v5', 'eco', 'plant', 'defuse',
                            "kast_both", "adr_both", "hs_both", "fk_both", "fd_both", "fkddiff_both"]
    data = data.drop(columns=non_relevant_columns, errors='ignore')

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)

    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(data_scaled)

    df['PCA1'] = pca_result[:, 0]
    df['PCA2'] = pca_result[:, 1]

    df.to_csv(output_csv_path, index=False)
    print(f"Fichier CSV avec PCA généré : {output_csv_path}")

    fig = px.scatter(
        df,
        x='PCA1',
        y='PCA2',
        hover_data={
            'player_name': True,
            'team': True,
            'games_played': True,
            'rounds': True
        },
        title='PCA des statistiques des joueurs',
        labels={'PCA1': 'PCA1', 'PCA2': 'PCA2'},
        color='region',
    )
    fig.update_traces(marker=dict(size=10, opacity=0.7))
    fig.write_html("output/player_stats_pca_visualization.html")
    print("Visualisation PCA sauvegardée dans : output/player_stats_pca_visualization.html")

apply_pca_to_player_stats(
    input_csv_path="output/player_stats.csv",
    output_csv_path="output/player_stats_pca.csv"
)