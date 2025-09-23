from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import re
import datetime
import logging
import json
import os

from .baseScraper import BaseScraper
from ..database.database import get_db_connection


class EventScraper(BaseScraper):
    """Scraper pour récupérer les matches d'un événement"""
    
    def __init__(self,
                 logger: logging.Logger,
                 delay: float = 1.0, 
                 full_log: bool = False
                ):
        super().__init__(
            base_url="https://www.vlr.gg", 
            logger=logger,
            delay=delay, 
            full_log=full_log
        )
        
        # données des équipes (noms courts et régions))
        self.teams_data = self._load_teams_data()
    

    def scrape(self, event_id: str) -> List[Dict[str, Any]]:
        """Scrap les matches pour un événement"""
        url = f"{self.base_url}/event/matches/{event_id}?group=completed"
        self.logger.info(f"Collecting matches for event {event_id}: {url}")
        
        self.wait()
        soup = self.get_page(url)
        if not soup:
            self.logger.error(f"Failed to fetch page: {url}")
            return []
        
        return self.parse_data(soup, event_id)
    
    def parse_data(self, soup: BeautifulSoup, event_id: str) -> List[Dict[str, Any]]:
        matches = []
        
        # collecte des ids et urls des matches sur la page
        for match in soup.select('.match-item'):
            match_id = match['href'].split('/')[1]
            match_data = {
                'match_id': match_id,
                'url': f'{self.base_url}/{match_id}',
                'event_id': event_id
            }
            matches.append(match_data)
        
        self.logger.info(f"Found {len(matches)} matches for event {event_id}")
        
        return matches
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """Save les données dans la base de données"""
        
        if not data:
            self.logger.warning("No data to save")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for match in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO matches (match_id, event_id, url)
                    VALUES (?, ?, ?)
                """, (match['match_id'], match['event_id'], match['url']))
            
            conn.commit()
            self.logger.info(f"Saved {len(data)} matches to the database") if self.full_log else None
            return True
        except Exception as e:
            self.logger.error(f"Error saving data to database: {e}")
            return False
        finally:
            conn.close()