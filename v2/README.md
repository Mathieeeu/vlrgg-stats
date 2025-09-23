

## TODO

- [x] Structure de la base de données
- [x] Base de donnée et API Python pour la gérer
- [x] Base du scraper
- [x] Collecte d'une saison
    - [x] Scraping des events d'une saison (ex: https://www.vlr.gg/vct-2025 pour la saison "vct-2025")
    - [x] Stockage des events dans la base
    - [x] Mise en place d'une date limite pour scraper uniquement les nouveaux évenements
- [x] Collecte d'un event
    - [x] Scraping des matches d'un event (ex: https://www.vlr.gg/event/matches/2283)
    - [x] Stockage des matches dans la base
- [x] Collecte d'un match
    - [x] Vérification si le match a déjà été scrappé
    - [x] Scraping des stats d'un match (ex: https://www.vlr.gg/542195)
    - [ ] Gestion des erreurs et données manquantes (pas grand chose à faire, tant que ça crash pas c'est bon)
    - [x] Stockage des stats d'un match dans la base
    - [x] Scraping des équipes du match si non existantes dans la base
    - [x] Stockage des équipes dans la base
- [x] Stats d'une map
    - [x] Scraping des stats globales (ex: https://www.vlr.gg/542195/?game=233397&tab=overview)
    - [x] Scraping des stats de performance (ex: https://www.vlr.gg/542195/?game=233397&tab=performance)
    - [x] Scraping des stats d'économie (ex: https://www.vlr.gg/542195/?game=233397&tab=economy)
    - [x] Stockage des stats d'une map dans la base
- [ ] Scraping manuel des évenements inter 2021 et 2022 (avec les équipes qui vont avec, histoire d'avoir quelques données pré-2023) (jugé pas utile finaleemnt)
- [x] Interface web de gestion (style phpMyAdmin)
    - [x] GROS PB DE DUPLICATION SI LE MATCH/GAME EST DEJA DANS LA BASE (corrigé)
    - [x] Page d'exécution de requêtes SQL
    - [x] Exportation CSV de la requête
- [ ] API REST pour le scraper
- [ ] Petit dashboard sympatique avec quelques stats
    - [ ] Nombre de matchs/joueurs/teams/events
    - [ ] Top 10 des joueurs par un critère changeable (ACS, K, D, K/D, KAST, ADR, HS%, FK Diff, etc)
    - [ ] Graphique du nombre de victoires pour chaque région dans chaque tournoi inter (pour voir l'évolution dans le temps)
- [ ] Automatisation quotidienne du scraper
- [ ] PHP client pour le site 
- [ ] Jeu VCTdle (style valodle avec des joueurs et des vraies stats (nombre d'équipes, nombre d'inters, kills, morts...))