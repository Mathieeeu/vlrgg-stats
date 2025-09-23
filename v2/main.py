import sys
import os
import json
import logging
import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# nettoyer les anciens logs et output
if os.path.exists("logs/scraper.log"):
    os.remove("logs/scraper.log")
if os.path.exists("output"):
    for f in os.listdir("output"):
        os.remove(os.path.join("output", f))

from server.database.database import init_database, execute_query
from server.scraper.seasonScraper import SeasonScraper
from server.scraper.eventScraper import EventScraper
from server.scraper.matchScraper import MatchScraper
from server.scraper.gameScraper import GameScraper

os.makedirs("logs", exist_ok=True)
log_file = os.path.join("logs", "scraper.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8'),
        # logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main(
        oldest_date: str = "2003-07-18", 
        seasons: list = None, 
        request_delay: float = 0.5,
        overwrite_db: bool = False
    ):
    """Fonction principale"""
    logger.info("Starting vlr.gg stats scraper (v4)")

    if seasons is None:
        print("No seasons provided to scrape. Exiting.")
        logger.warning("No seasons provided to scrape. Exiting.")
        return
    
    try:
        init_database(overwrite=overwrite_db)
    except:
        print("Failed to initialize the database. Exiting.")
        logger.error("Failed to initialize the database", exc_info=True)
        return
    
    season_scraper = SeasonScraper(delay=request_delay, oldest_date=oldest_date, full_log=False, logger=logger)
    
    i=1
    for season_id in tqdm.tqdm(seasons, desc="Processing seasons"):
        logger.info(f"Processing season: {season_id} ({i}/{len(seasons)})")
        i+=1
        
        try:
            events = season_scraper.scrape(season_id)
            
            if events:
                
                os.makedirs("output", exist_ok=True)
                
                with open(f"output/{season_id}_events.json", "w", encoding="utf-8") as f:
                    json.dump(events, f, separators=(',', ':'), ensure_ascii=False, default=str)
                
                season_scraper.save_data(events)

            else:
                # logger.warning(f"No events found for season {season_id}")
                pass
                
        except Exception as e:
            logger.error(f"Error processing season {season_id}: {e}")
            continue
    
    season_scraper.close()

    event_scraper = EventScraper(delay=request_delay, full_log=False, logger=logger)

    matches_to_collect = []

    logger.info(f"{len(events)} events to process")
    for event in tqdm.tqdm(events, desc="Processing events"):
        try:
            event_id = event.get("id")
            if not event_id:
                logger.warning(f"Event without ID found: {event}")
                continue

            matches = event_scraper.scrape(event_id)

            # pas de dooublons
            matches_in_database = execute_query(f"SELECT match_id FROM matches WHERE event_id = {event_id}")
            existing_match = [match['match_id'] for match in matches_in_database]
            matches = [m for m in matches if int(m['match_id']) not in existing_match]
            # logger.warning(f"{existing_match=}")
            # logger.warning(f"{matches_in_database=}")
            # logger.warning(f"{matches=}")
            logger.info(f"Found {len(existing_match)} existing matches for event {event_id}")
            logger.info(f"{len(matches)} new matches found for event {event_id}")

            if matches:

                with open(f"output/event_{event_id}_matches.json", "w", encoding="utf-8") as f:
                    json.dump(matches, f, separators=(',', ':'), ensure_ascii=False, default=str)

                event_scraper.save_data(matches)

                matches_to_collect.extend(matches)
            else:
                logger.warning(f"No new matches found for event {event_id}")
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}")
            continue

    event_scraper.close()
    
    if not matches_to_collect:
        logger.info("No new matches to process. Exiting.")
        print("No new matches to process. Exiting.")
        return

    match_scraper = MatchScraper(delay=request_delay, full_log=False, logger=logger)

    games_to_collect = []

    logger.info(f"{len(matches_to_collect)} matches to process")
    for match in tqdm.tqdm(matches_to_collect, desc="Processing matches"):
        try:
            match_id = match.get("match_id")
            if not match_id:
                logger.warning(f"Match without ID found: {match}")
                continue

            match_details, games = match_scraper.scrape(match_id)

            if match_details['series'] == 'showmatch':
                execute_query(f"DELETE FROM matches WHERE match_id = '{match_id}'")
                logger.info(f"Ignoring showmatch: {match_id}")
                continue

            if match_details:

                combined_match_data = match_details.copy()
                combined_match_data['games'] = games

                with open(f"output/match_{match_id}_details.json", "w", encoding="utf-8") as f:
                    json.dump(combined_match_data, f, separators=(',', ':'), ensure_ascii=False, default=str)

                match_scraper.save_data(match_details)
            
                if games:
                    match_scraper.save_games_data(games)
                    
                    games_to_collect.extend(games)
            else:
                logger.warning(f"No details found for match {match_id}")
        except Exception as e:
            logger.error(f"Error processing match {match_id}: {e}")
            continue

    match_scraper.close()

    game_scraper = GameScraper(delay=request_delay, full_log=False, logger=logger)

    logger.info(f"{len(games_to_collect)} games to process")
    for game in tqdm.tqdm(games_to_collect, desc="Processing games"):
        try:
            game_id = game.get("game_id")
            match_id = game.get("match_id")
            if not game_id or not match_id:
                logger.warning(f"Game without ID found: {game}")
                continue

            game_details = game_scraper.scrape(game_id, match_id)
            if game_details:

                with open(f"output/game_{game_id}_details.json", "w", encoding="utf-8") as f:
                    json.dump(game_details, f, separators=(',', ':'), ensure_ascii=False, default=str)

                game_scraper.save_data(game_details)
            
            else:
                logger.warning(f"No details found for game {game_id}")
        except Exception as e:
            logger.error(f"Error processing game {game_id}: {e}")
            continue

    game_scraper.close()
    
    logger.info("Scraping completed!")

if __name__ == "__main__":

    # liste de saisons vct à scraper
    seasons = [
        "vct-2023", 
        "vct-2024", 
        "vct-2025"
    ]

    # # date la plus ancienne à scraper
    # query = "SELECT MAX(date) as max_date FROM matches;"
    # oldest_date = execute_query(query)[0]['max_date']
    # if not oldest_date:
    #     logger.error("No max_date found in database. Exiting.")
    #     print("No max_date found in database. Exiting.")
    #     sys.exit(1)
    # oldest_date = "2020-01-01" # année de lancement de valorant
    # oldest_date = "2025-01-01" # saison 2025 complète
    # oldest_date = "2025-07-01" # que split 2 + champs
    oldest_date = "2025-09-10" # que les champions
    print(f"Scraping events after: {oldest_date}")
    logger.info(f"Scraping events after: {oldest_date}")

    request_delay = 0.2
    overwrite_db = False

    if overwrite_db:
        input("Database will be overwritten. Press Enter to continue or Ctrl+C to abort...")
    
    main(oldest_date, seasons, request_delay, overwrite_db)