from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import time
import random
import re
import datetime
import json
import logging
import os

class BaseScraper(ABC):
    """Classe de base pour les scrapers"""
    
    def __init__(self, 
                 base_url: str, 
                 logger: logging.Logger,
                 delay: float = 1.0, 
                 full_log: bool = False, 
                ):
        self.base_url = base_url
        self.delay = delay # seconds between requests (±30%)
        self.full_log = full_log
        self.logger = logger

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.logger.info(f"Initialized {self.__class__.__name__} for {self.base_url}")

    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Récupère et parse une page web"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def wait(self):
        """Applique un délai aléatoire (±30%) entre les requêtes"""
        time.sleep(self.delay + (self.delay * 0.3 * (2 * random.random() - 1)))

    def _load_teams_data(self) -> Dict[str, Any]:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'teams.json')
        if os.path.exists(data_path):
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading teams data from {data_path}: {e}")
        
        self.logger.warning(f"Teams data file not found or failed to load: {data_path}. Using empty data.")
        return {
            'short_names': {},
            'regions': {}
        }
    
    @abstractmethod
    def scrape(self, *args, **kwargs) -> Dict[str, Any]:
        """méthode abstraite"""
        pass
    
    @abstractmethod
    def parse_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Méthode abstraite"""
        pass

    @abstractmethod
    def save_data(self, data: Any) -> bool:
        """Méthode abstraite"""
        pass
    
    def close(self):
        """Ferme la session"""
        self.session.close()
        self.logger.info(f"{self.__class__.__name__} session closed")