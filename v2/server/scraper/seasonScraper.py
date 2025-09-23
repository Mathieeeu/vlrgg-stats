from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import re
import datetime
import logging
import os

from .baseScraper import BaseScraper
from ..database.models import Event
from ..database.database import get_db_connection

class SeasonScraper(BaseScraper):
    """Scraper pour récupérer les evenements d'une saison"""
    
    def __init__(self,
                 logger: logging.Logger,
                 delay: float = 1.0, 
                 full_log: bool = False, 
                 oldest_date: str = None
                ):
        super().__init__(
            base_url="https://www.vlr.gg", 
            logger=logger,
            delay=delay, 
            full_log=full_log
            )
        
        # date limite pour le scraping (format YYYY-MM-DD)
        self.oldest_date = datetime.datetime.strptime(oldest_date, '%Y-%m-%d').date() if oldest_date else None
        
        self.REGIONS = {
            'americas': 'amer',
            'emea': 'emea',
            'pacific': 'apac',
            'china': 'cn',
        }
    

    def scrape(self, season_id: str) -> List[Dict[str, Any]]:
        """Scrape les événements pour une saison donnée"""
        url = f"{self.base_url}/{season_id}"
        self.logger.info(f"Collecting events for season {season_id}: {url}")
        
        # année en cours (pour simplifier la gestion des dates :)
        self.current_season_year = self._extract_year_from_season(season_id)
        
        self.wait()
        soup = self.get_page(url)
        if not soup:
            self.logger.error(f"Failed to fetch page: {url}")
            return []
        
        return self.parse_data(soup)
    
    def _extract_year_from_season(self, season_id: str) -> str:
        """Trouver l'année dans l'id de la saison (ça marche qu'avec les saisons vct qui s'appellent 'vct-YYYY')"""
        # TODO : trouver une solution pour avoir l'année sur des tournois hors vct
        match = re.search(r'(\d{4})', season_id)
        if match:
            return match.group(1)
        else:
            # Sinon prendre l'année courante (vrm pas une bonne solution...)
            self.logger.error(f"Could not extract year from season_id '{season_id}', defaulting to current year (could be an issue)")
            return str(datetime.datetime.now().year)
    
    def parse_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse les données des events depuis la page"""
        events = []
        filtered_events = []
    
        for event in soup.select('.event-item'):
            event_data = self._parse_event(event)
            if event_data:
                events.append(event_data)
                
                # on filtre selon la date si besoin (on garde que les evenements qui se terminent après oldest_date)
                if self.oldest_date and event_data.get('end_date'):
                    try:
                        event_end_date = datetime.datetime.strptime(event_data['end_date'], '%Y-%m-%d').date()
                        if event_end_date >= self.oldest_date:
                            filtered_events.append(event_data)
                        else:
                            self.logger.info(f"Event '{event_data.get('title', 'Unknown')}' skipped - ends before {self.oldest_date}") if self.full_log else None
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Could not parse end date for event {event_data.get('title', 'Unknown')}: {e}")
                        # date non parsable ? inclut l'event (par sécurité)
                        filtered_events.append(event_data)
                else:
                    # pas de filtre ? inclut l'event
                    filtered_events.append(event_data)
        
        total_events = len(events)
        filtered_count = len(filtered_events)
        
        if self.oldest_date:
            self.logger.info(f"Found {total_events} events, {filtered_count} events after {self.oldest_date}")
        else:
            self.logger.info(f"Found {total_events} events (no date filter)")
            
        return filtered_events
    
    def _parse_event(self, event) -> Optional[Dict[str, Any]]:
        """Parse un événement"""
        try:
            title = event.select_one('.event-item-title')
            status = event.select_one('.event-item-desc-item-status')
            prize = event.select_one('.event-item-desc-item.mod-prize')
            dates = event.select_one('.event-item-desc-item.mod-dates')
            country = event.select_one('.event-item-desc-item.mod-location .flag')
            thumb = event.select_one('.event-item-thumb img')

            event_href = event.get('href', '')
            if not event_href:
                self.logger.warning("Event without href found, skipping")
                return None
                
            event_id = event_href.split('/')[2] if len(event_href.split('/')) > 2 else None
            if not event_id:
                self.logger.warning(f"Could not extract event ID from href: {event_href}")
                return None
            
            # Parse du prix, dates, région et nom
            prize_pool = self._parse_prize(prize.get_text(strip=True) if prize else "")
            start_date, end_date = self._parse_dates(dates)
            region, event_name = self._parse_region_and_name(event_href)
            
            # dict de l'éavénement final
            event_data = {
                'id': int(event_id),
                'url': f'{self.base_url}/event/{event_id}',
                'title': title.get_text(strip=True) if title else None,
                'status': status.get_text(strip=True) if status else None,
                'prize_pool': prize_pool,
                'start_date': start_date,
                'end_date': end_date,
                'region': region,
                'event_name': event_name,
                'location': country['class'][1][4:] if country and len(country.get('class', [])) > 1 else None,
                'thumbnail': 'https:' + thumb['src'] if thumb and thumb.has_attr('src') else None
            }
            
            return event_data
            
        except Exception as e:
            self.logger.error(f"Error parsing event: {e}")
            return None
    
    def _parse_prize(self, prize_text: str) -> Optional[int]:
        """Parse le prize pool depuis le texte"""
        if not prize_text:
            return None
        match = re.search(r'([\d,]+)', prize_text.replace('$', ''))
        if match:
            return int(match.group(1).replace(',', ''))
        return None
    
    def _parse_dates(self, dates_element) -> tuple[Optional[str], Optional[str]]:
        """Parse les dates de début et fin de l'event"""
        if not dates_element:
            return None, None
        
        try:
            # utiliser année de la saison courante (sinon année courante mais pas idéal)
            # TODO : trouver une solution pour avoir l'année sur des tournois hors vct
            year = getattr(self, 'current_season_year', str(datetime.datetime.now().year))
            
            dates_text = dates_element.get_text(strip=True).replace('Dates', '')
            dates = dates_text.split('\u2014')  # '\u2014' = em dash (un tiret long —)
            dates_with_year = [date.strip() + f" {year}" if date.strip() and date.strip() != 'TBD' else '' for date in dates]
            
            # cas où la 2nde date n'a que le jour
            if len(dates_with_year) == 2 and re.match(r'^\d{1,2} \d{4}$', dates_with_year[1]):
                first_month = dates_with_year[0].split()[0]
                second_day, second_year = dates_with_year[1].split()
                dates_with_year[1] = f"{first_month} {second_day} {second_year}"
            
            #format ISO
            dates_formatted = []
            for date in dates_with_year:
                if date.strip() and date != '':
                    try:
                        formatted_date = datetime.datetime.strptime(date, '%b %d %Y').strftime('%Y-%m-%d')
                        dates_formatted.append(formatted_date)
                    except ValueError as e:
                        self.logger.warning(f"Failed to parse date: {date}, error: {e}")
            
            start_date = dates_formatted[0] if dates_formatted else None
            end_date = dates_formatted[1] if len(dates_formatted) > 1 else None
            
            return start_date, end_date
            
        except Exception as e:
            self.logger.error(f"Error parsing dates: {e}")
            return None, None
    
    def _parse_region_and_name(self, event_url: str) -> tuple[str, str]:
        """Parse la région et le nom de l'event depuis l'URL"""

        region = None
        for key in self.REGIONS:
            if f"-{key}-" in event_url:
                region = self.REGIONS[key]
                break
        
        if not region:
            # cas spéciaux pour les events inter
            # pas forcément idéal mais fonctionne pour les évenements de 2023 à 2025 (le lock-in contient le mot champions lol)
            # TODO : trouver une meilleure solution
            if 'champions' in event_url or 'masters' in event_url:
                region = 'inter'
            else:
                region = 'unknown'
        
        event_name = None
        match = re.search(r'-(' + '|'.join(self.REGIONS.keys()) + r')-(.+)', event_url)
        if match:
            event_name = match.group(2)
        else:
            # fallback: prendre la dernière partie après le dernier slash
            event_name = event_url.rstrip('/').split('/')[-1]
        
        return region, event_name
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """Save les données dans la base de données"""
        try:
            
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            saved_count = 0
            updated_count = 0
            
            for event_data in data:
                try:
                    # conversion dates : string -> date
                    start_date = datetime.datetime.strptime(event_data['start_date'], '%Y-%m-%d').date() if event_data['start_date'] else None
                    end_date = datetime.datetime.strptime(event_data['end_date'], '%Y-%m-%d').date() if event_data['end_date'] else None
                    
                    # vérifier si l'event existe déjà
                    cursor.execute("SELECT id FROM events WHERE id = ?", (event_data['id'],))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # maj event existant (à part l'id qui change pas)
                        cursor.execute("""
                            UPDATE events SET 
                                url = ?, title = ?, status = ?, prize_pool = ?,
                                start_date = ?, end_date = ?, region = ?, event_name = ?,
                                location = ?, thumbnail = ?
                            WHERE id = ?
                        """, (
                            event_data['url'], event_data['title'], event_data['status'],
                            event_data['prize_pool'], start_date, end_date,
                            event_data['region'], event_data['event_name'],
                            event_data['location'], event_data['thumbnail'],
                            event_data['id']
                        ))
                        updated_count += 1
                    else:
                        # insert un nouvel evenement
                        cursor.execute("""
                            INSERT INTO events (
                                id, url, title, status, prize_pool, start_date, end_date,
                                region, event_name, location, thumbnail
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            event_data['id'], event_data['url'], event_data['title'],
                            event_data['status'], event_data['prize_pool'], start_date, end_date,
                            event_data['region'], event_data['event_name'],
                            event_data['location'], event_data['thumbnail']
                        ))
                        saved_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error saving event {event_data.get('id', 'unknown')}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Successfully saved {saved_count} new events and updated {updated_count} existing events")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving events to database: {e}")
            return False