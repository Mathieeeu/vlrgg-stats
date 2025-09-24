from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re
import datetime
import logging
import json
import os

from .baseScraper import BaseScraper
from ..database.database import get_db_connection


class MatchScraper(BaseScraper):
    """Scraper pour récupérer un match (et ses games (sans les détails))"""
    
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
        
        # Charger les données des équipes
        self.teams_data = self._load_teams_data()
    

    def scrape(self, match_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """collecte les détails d'un match et return (match_details, games)"""
        url = f"{self.base_url}/{match_id}"
        self.logger.info(f"Scraping match details for {match_id}: {url}")
        
        self.wait()
        soup = self.get_page(url)
        if not soup:
            self.logger.error(f"Failed to fetch page: {url}")
            return None, []
        
        return self.parse_data(soup, match_id)
    
    def parse_data(self, soup: BeautifulSoup, match_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse les données du match depuis la page"""
        try:
            # infos de base du match
            match_data = {
                'match_id': match_id,
                'url': f'{self.base_url}/{match_id}',
                'series': '',
                'date': '',
                'time': '',
                'patch': '',
                'picks': [],
                'bans': [],
                'decider': '',
                'teams': []
            }
            
            # si c'est un showmatch, on skip
            series_elem = soup.select_one('.match-header-event-series')
            if series_elem:
                series_text = series_elem.get_text(strip=True).replace('\n', '').replace('\t', '')
                if 'showmatch' in series_text.lower():
                    self.logger.info(f"Skipping showmatch: {match_id}")
                    return {'series': 'showmatch'}, []
                match_data['series'] = series_text
            
            # extraction données (date, heure, patch, équipes, scores, picks/bans, games)
            self._parse_date_time_patch(soup, match_data)
            teams = self._parse_teams_and_scores(soup)
            match_data['teams'] = teams
            self._parse_picks_bans(soup, match_data, teams)
            games = self._parse_games(soup, match_id, teams)
            # print(match_data)
            
            return match_data, games
            
        except Exception as e:
            self.logger.error(f"Error parsing match data for {match_id}: {e}")
            return None, []
    
    def _parse_date_time_patch(self, soup: BeautifulSoup, match_data: Dict[str, Any]):
        """Parse la date, l'heure et le patch d'un match"""
        date_patch_elem = soup.select_one('.match-header-date')
        
        if date_patch_elem:
            # date/heure/patch ensemble dans l'attribut "data-utc-ts"
            date_elem = date_patch_elem.select_one('.moment-tz-convert[data-utc-ts]')
            if date_elem and date_elem.has_attr('data-utc-ts'):
                timestamp = date_elem['data-utc-ts']
                try:
                    parsed_datetime = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    match_data['date'] = parsed_datetime.strftime('%Y-%m-%d')
                    match_data['time'] = parsed_datetime.strftime('%H:%M:%S')
                except Exception as e:
                    self.logger.warning(f"Failed to parse timestamp '{timestamp}': {e}")
                    date_text = date_elem.get_text(strip=True)
                    match_data['date'] = date_text
            
            patch_elem = date_patch_elem.select_one('div[style*="font-style: italic"]')
            if patch_elem:
                patch_text = patch_elem.get_text(strip=True)
                # regex pour seulement le numéro de version du patch (sinon c'est "Patch 11.05")
                patch_match = re.search(r'(\d+\.\d+)', patch_text)
                patch_text = patch_match.group(1) if patch_match else patch_text
                match_data['patch'] = patch_text
            else:
                match_data['patch'] = ''
        else:
            match_data['date'] = ''
            match_data['time'] = ''
            match_data['patch'] = ''
    
    def _parse_teams_and_scores(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse les équipes et leurs scores (dans le bo, le score des maps est dans gameScraper)"""
        teams = []
        
        match_result_soup = soup.select_one('.match-header-vs')
        if not match_result_soup:
            return teams
        
        team_links = match_result_soup.select('.match-header-link')
        score_elements = match_result_soup.select('.match-header-vs-score span')
        
        # scores du BO !! (pas des maps)
        first_team_score = ''
        second_team_score = ''
        if len(score_elements) >= 2:
            first_team_score = score_elements[0].get_text(strip=True)
            second_team_score = score_elements[-1].get_text(strip=True)
        
        for i, team_link in enumerate(team_links):
            team_name_elem = team_link.select_one('.wf-title-med')
            team_logo_elem = team_link.select_one('img')
            
            if i == 0:  # score 1re équipe
                team_score = first_team_score
                is_winner = (first_team_score and second_team_score and 
                            int(first_team_score) > int(second_team_score))
            else:  # score 2e équipe
                team_score = second_team_score
                is_winner = (first_team_score and second_team_score and
                            int(second_team_score) > int(first_team_score))
            
            team_name = team_name_elem.get_text(strip=True) if team_name_elem else ''
            team_short_name = self.teams_data['short_names'].get(team_name, '')
            team_region = self._get_team_region(team_short_name)
            
            team_info = {
                'name': team_name,
                'short_name': team_short_name,
                'region': team_region,
                'logo_url': 'https:' + team_logo_elem['src'] if team_logo_elem and team_logo_elem.has_attr('src') else '',
                'team_url': f"{self.base_url}{team_link['href']}" if team_link.has_attr('href') else '',
                'score': int(team_score) if team_score.isdigit() else 0,
                'is_winner': is_winner
            }
            teams.append(team_info)
        
        return teams
    
    def _get_team_region(self, team_short_name: str) -> str:
        """région d'une équipe à partir de son nom"""
        if not team_short_name:
            return 'unknown'
        for region, teams in self.teams_data.get('regions', {}).items():
            if team_short_name in teams:
                return region
        return 'unknown'
    
    def _parse_picks_bans(self, soup: BeautifulSoup, match_data: Dict[str, Any], teams: List[Dict[str, Any]]):
        """Parse les picks et bans d'un match (format json pour garder l'ordre)"""
        picks_bans_elems = soup.select('.match-header-note')
        if not picks_bans_elems:
            return
        
        picks_bans_text = picks_bans_elems[-1].get_text(strip=True)
        
        for pb in picks_bans_text.split('; '):
            pb_parts = pb.split(' ')
            if len(pb_parts) < 3:
                if len(pb_parts) == 2 and pb_parts[1].lower() == 'remains':
                    match_data['decider'] = pb_parts[0]
                continue
            
            team_short = pb_parts[0]
            action = pb_parts[1].lower()
            map_name = ' '.join(pb_parts[2:])
            
            if action == 'ban':
                match_data['bans'].append({'team': team_short, 'map': map_name})
            elif action == 'pick':
                match_data['picks'].append({'team': team_short, 'map': map_name})
    
    def _parse_games(self, soup: BeautifulSoup, match_id: str, teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse les games (pas les détails, juste id, url, map, pick, win, durée, scores)"""
        games = []
        game_soups = soup.select('.vm-stats-game')
        
        # mapping : shortname -> team_id
        team_id_mapping = {}
        for team in teams:
            team_short = team['short_name']
            team_id = hash(team_short) % (2**31 - 1) if team_short else None # id hashé comme dans save_team
            team_id_mapping[team_short] = team_id
        
        for game_soup in game_soups:
            game_id = game_soup.get('data-game-id')
            if game_id == 'all':
                continue
            
            game_data = {
                'game_id': game_id,
                'match_id': match_id,
                'url': f'{self.base_url}/{match_id}?game={game_id}',
                'map': '',
                'pick': None, # (id de l'équipe pick la map)
                'win': None, # (id du gagnant)
                'duration': '',
                'scores': {}
            }
            
            # Map
            map_elem = game_soup.select_one('.map')
            if map_elem:
                map_text = map_elem.get_text(strip=True).replace(' ', '')
                # Prendre uniquement les premiers caractères avant un caractère spécial ou un chiffre
                cleaned_map = re.split(r'[^a-zA-Z]', map_text)[0]
                if cleaned_map.upper().endswith("PICK"):
                    cleaned_map = cleaned_map[:-4]
                cleaned_map = cleaned_map.strip()
                game_data['map'] = cleaned_map
            
            # Pick
            if game_soup.select_one('.picked.mod-1'):
                game_data['pick'] = team_id_mapping.get(teams[0]['short_name']) if teams else None
            elif game_soup.select_one('.picked.mod-2'):
                game_data['pick'] = team_id_mapping.get(teams[1]['short_name']) if len(teams) > 1 else None
            
            # Win
            score_elems = game_soup.select('.score')
            if len(score_elems) >= 2:
                if 'mod-win' in score_elems[0].get('class', []):
                    game_data['win'] = team_id_mapping.get(teams[0]['short_name']) if teams else None
                elif 'mod-win' in score_elems[1].get('class', []):
                    game_data['win'] = team_id_mapping.get(teams[1]['short_name']) if len(teams) > 1 else None
            
            # Duration
            duration_elem = game_soup.select_one('.map-duration')
            if duration_elem:
                game_data['duration'] = duration_elem.get_text(strip=True)
            
            # Scores (par équipe, score final, scores t/ct)
            if len(teams) >= 2 and len(score_elems) >= 2:
                team_elems = game_soup.select('.team')
                
                for i, team in enumerate(teams[:2]):
                    team_short = team['short_name']
                    score = score_elems[i].get_text(strip=True) if i < len(score_elems) else ''
                    
                    # Scores t/ct
                    t_score = ''
                    ct_score = ''
                    if i < len(team_elems):
                        t_elems = team_elems[i].select('.mod-t')
                        ct_elems = team_elems[i].select('.mod-ct')
                        t_score = t_elems[0].get_text(strip=True) if t_elems else ''
                        ct_score = ct_elems[0].get_text(strip=True) if ct_elems else ''
                    
                    game_data['scores'][team_short] = {
                        'score': int(score) if score.isdigit() else 0,
                        't': int(t_score) if t_score.isdigit() else 0,
                        'ct': int(ct_score) if ct_score.isdigit() else 0
                    }
            
            games.append(game_data)
        
        return games
    
    def save_data(self, match_data: Dict[str, Any]) -> bool:
        """Save les données dans la base de données"""
        
        if not match_data:
            self.logger.warning("No match data to save")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Sauvegarder ou update les équipes
            team_ids = {}
            for team in match_data.get('teams', []):
                team_id = self._save_team(cursor, team)
                if team_id:
                    team_ids[team['short_name']] = team_id
            
            # recup event_id existant si le match est déjà dans la bdd
            cursor.execute("SELECT event_id FROM matches WHERE match_id = ?", (match_data['match_id'],))
            existing_match = cursor.fetchone()
            existing_event_id = existing_match[0] if existing_match else None
            
            # sauvegarde le match en gardant l'event_id
            cursor.execute("""
                        INSERT OR REPLACE INTO matches 
                        (match_id, url, event_id, series, date, time, patch, picks, bans, decider)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                match_data['match_id'],
                match_data['url'],
                existing_event_id,  # garder l'event_id existant
                match_data['series'],
                match_data['date'],
                match_data['time'],
                match_data['patch'],
                json.dumps(match_data['picks']),
                json.dumps(match_data['bans']),
                match_data['decider']
            ))
            
            # Save les relations match-équipes dans la table match_teams
            for team in match_data.get('teams', []):
                team_id = team_ids.get(team['short_name'])
                if team_id:
                    # picks et bans de l' équipe
                    team_picks = [item['map'] for item in match_data.get('picks', []) if item.get('team') == team['short_name']]
                    team_bans = [item['map'] for item in match_data.get('bans', []) if item.get('team') == team['short_name']]
                    
                    cursor.execute("""
                                INSERT OR REPLACE INTO match_teams 
                                (match_id, team_id, score, is_winner, picks, bans)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                        match_data['match_id'],
                        team_id,
                        team['score'],
                        team['is_winner'],
                        json.dumps(team_picks),  # liste des picks de l'équipe
                        json.dumps(team_bans)    # liste des bans de l'équipe
                    ))
            
            conn.commit()
            self.logger.info(f"Saved match {match_data['match_id']} to database") if self.full_log else None
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving match data to database: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _save_team(self, cursor, team_data: Dict[str, Any]) -> Optional[int]:
        """Save une équipe et return son id"""
        try:
            # id = hash du short_name  (comme pour les ids des joueurs)
            team_id = hash(team_data['short_name']) % (2**31 - 1)
            
            cursor.execute("""
                        INSERT OR REPLACE INTO teams 
                        (id, name, short_name, region, logo_url, team_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                team_id,
                team_data['name'],
                team_data['short_name'],
                team_data['region'],
                team_data['logo_url'],
                team_data['team_url']
            ))
            
            return team_id
            
        except Exception as e:
            self.logger.error(f"Error saving team {team_data['name']}: {e}")
            return None
    
    def save_games_data(self, games: List[Dict[str, Any]]) -> bool:
        """Save les données des games dans la base de données"""
        
        if not games:
            self.logger.warning("No games data to save")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for game in games:
                cursor.execute("""
                            INSERT OR REPLACE INTO games 
                            (game_id, match_id, url, map, pick, win, duration)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                    game['game_id'],
                    game['match_id'],
                    game['url'],
                    game['map'],
                    game['pick'],
                    game['win'],
                    game['duration']
                ))
                
                # scores par équipe
                for team_short, score_data in game.get('scores', {}).items():
                    # recup id de l'équipe
                    cursor.execute("SELECT id FROM teams WHERE short_name = ?", (team_short,))
                    team_result = cursor.fetchone()
                    if team_result:
                        team_id = team_result[0]
                        cursor.execute("""
                                    INSERT OR REPLACE INTO game_scores 
                                    (game_id, team_id, score, t_score, ct_score)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (
                            game['game_id'],
                            team_id,
                            score_data['score'],
                            score_data['t'],
                            score_data['ct']
                        ))
            
            conn.commit()
            self.logger.info(f"Saved {len(games)} games to database") if self.full_log else None
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving games data to database: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
