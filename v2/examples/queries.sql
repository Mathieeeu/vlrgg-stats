-- ============================================
-- 100 dernières parties avec gagnant et perdant
-- ============================================
SELECT
    g.game_id,
    g.url,
    m.date,
    tw.short_name AS winner,
    tl.short_name AS loser
FROM games g
JOIN matches m ON m.match_id = g.match_id
JOIN game_scores gs ON gs.game_id = g.game_id
JOIN teams tl ON tl.id = gs.team_id AND gs.team_id <> g.win -- loser
JOIN teams tw ON tw.id = g.win -- winner
ORDER BY m.date DESC, g.game_id DESC
LIMIT 100;

-- ============================================
-- 100 dernières équipes a avoir mis le 12e point en premier dans une partie
-- ============================================
SELECT
    g.game_id,
    m.date,
    t.short_name AS team_first_to_12,
    opp.short_name AS opponent,
    rh.score AS score_at_12,
    CASE WHEN g.win = t.id THEN 1 ELSE 0 END AS first_to_12_won_match
FROM games g
JOIN matches m ON m.match_id = g.match_id
JOIN (
    SELECT rh1.game_id, MIN(rh1.round_number) AS round_number_12
    FROM round_history rh1
    WHERE CAST(SUBSTR(rh1.score, 1, INSTR(rh1.score, '-') - 1) AS INTEGER) = 12
       OR CAST(SUBSTR(rh1.score, INSTR(rh1.score, '-') + 1) AS INTEGER) = 12
    GROUP BY rh1.game_id
) first12 ON first12.game_id = g.game_id
JOIN round_history rh 
    ON rh.game_id = first12.game_id 
   AND rh.round_number = first12.round_number_12
JOIN teams t ON t.id = rh.winner
JOIN game_scores gs ON gs.game_id = g.game_id AND gs.team_id <> t.id
JOIN teams opp ON opp.id = gs.team_id
ORDER BY m.date DESC, g.game_id DESC
LIMIT 100;

-- ============================================
-- Winrate de chaque équipe quand elle met le 12e point en premier dans une partie
-- ============================================
SELECT
    t.short_name AS team,
    COUNT(*) AS games_first_to_12,
    SUM(CASE WHEN g.win = t.id THEN 1 ELSE 0 END) AS wins_first_to_12,
    ROUND(AVG(CASE WHEN g.win = t.id THEN 1 ELSE 0 END), 2) AS winrate_first_to_12
FROM games g
JOIN (
    SELECT rh1.game_id, MIN(rh1.round_number) AS round_number_12
    FROM round_history rh1
    WHERE CAST(SUBSTR(rh1.score, 1, INSTR(rh1.score, '-') - 1) AS INTEGER) = 12
       OR CAST(SUBSTR(rh1.score, INSTR(rh1.score, '-') + 1) AS INTEGER) = 12
    GROUP BY rh1.game_id
) first12 ON first12.game_id = g.game_id
JOIN round_history rh 
    ON rh.game_id = first12.game_id 
   AND rh.round_number = first12.round_number_12
JOIN matches m ON m.match_id = g.match_id
JOIN teams t ON t.id = rh.winner
WHERE m.date > "2025-09-01" -- date minimale de la requête
GROUP BY team
ORDER BY winrate_first_to_12 DESC;