# vlrgg-stats
v2

## Schéma de la base de données des matches

```json
[
    {
        "match_id": "string",
        "url": "string",
        "event_id": "string",
        "series": "string",
        "date": "string",
        "time": "string",
        "patch": "string",
        "picks": ["string"],
        "bans": ["string"],
        "decider": "string",
        "teams": [
            {
                "name": "string",
                "short_name": "string",
                "region": "string",
                "logo_url": "string",
                "team_url": "string",
                "score": "string",
                "is_winner": "boolean",
                "picks": ["string"],
                "bans": ["string"]
            },
            // ... (for team2)
        ],
        "games": [
            {
                "game_id": "string",
                "url": "string",
                "map": "string",
                "pick": "string",
                "win": "string",
                "duration": "string",
                "scores": {
                    "<team1_shortname>": {
                        "score": "string",
                        "t": "string",
                        "ct": "string"
                    },
                    // ... (for team2)
                },
                "economy": {
                    "<team1_shortname>": {
                        "pistol": "integer",
                        "eco": {
                            "played": "integer",
                            "won": "integer"
                        },
                        "semi_eco": {
                            "played": "integer",
                            "won": "integer"
                        },
                        "semi_buy": {
                            "played": "integer",
                            "won": "integer"
                        },
                        "full_buy": {
                            "played": "integer",
                            "won": "integer"
                        }
                    },
                    // ... (for team2)
                },
                "history": [
                    {
                        "round": "string",
                        "winner": "string",
                        "score": "string",
                        "win_type": "string"
                    },
                    // ... (for each round)
                ],
                "scoreboard": {
                    "<team1_shortname>": [
                        {
                            "name": "string",
                            "team": "string",
                            "agent": {
                                "name": "string",
                                "icon_url": "string"
                            },
                            "stats": {
                                "ratio": {
                                    "both": "string",
                                    "t": "string",
                                    "ct": "string"
                                },
                                "acs": {
                                    "both": "integer",
                                    "t": "integer",
                                    "ct": "integer"
                                },
                                "k": {
                                    "both": "integer",
                                    "t": "integer",
                                    "ct": "integer"
                                },
                                // ... (other stats : d, a, kddiff, kast, adr, hs, fk, fd, fkddiff)
                                "multikills": {
                                    "2k": "integer",
                                    "3k": "integer",
                                    "4k": "integer",
                                    "5k": "integer"
                                },
                                "clutches": {
                                    "1v1": "integer",
                                    "1v2": "integer",
                                    "1v3": "integer",
                                    "1v4": "integer",
                                    "1v5": "integer"
                                },
                                "eco": "integer",
                                "plant": "integer",
                                "defuse": "integer"
                            }
                        },
                        // ... (for each player in team1)
                    ],
                    // ... (for team2)
                }
            },
            // ... (for each game of the match)
        ]
    },
    // ... (for each match)
]