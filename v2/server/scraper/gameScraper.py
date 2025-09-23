from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re
import datetime
import logging
import json
import os

from .baseScraper import BaseScraper
from ..database.database import get_db_connection


class GameScraper(BaseScraper):
    """Scraper pour récupérer les statistiques d'une game"""
    
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
  

    def scrape(self, game_id: str, match_id: str) -> Dict[str, Any]:
        """Scrape les statistiques d'une game"""
        base_url = f"{self.base_url}/{match_id}?game={game_id}"
        self.logger.info(f"Scraping game stats for game {game_id} in match {match_id}")
        
        # Récupérer l'overview (onglet par défaut)
        self.wait()
        overview_soup = self.get_page(base_url)
        if not overview_soup:
            self.logger.error(f"Failed to fetch overview page: {base_url}")
            return {}
        
        return self.parse_data(overview_soup, game_id, match_id, base_url)
    
    def parse_data(self, overview_soup: BeautifulSoup, game_id: str, match_id: str, base_url: str) -> Dict[str, Any]:
        """Parse toutes les données de la game depuis les différents onglets (overview,performance,économy) + l'historique des rounds"""
        try:
            game_data = {
                'game_id': game_id,
                'match_id': match_id,
                'players': [],
                'round_history': [],
                'economy_stats': {},
                'team_ids': {}
            }
            
            game_soup = overview_soup.select_one(f'.vm-stats-game[data-game-id="{game_id}"]')
            if not game_soup:
                self.logger.error(f"Game {game_id} not found in page")
                return game_data
            
            self._get_team_ids(game_data)
            
            self._parse_overview(game_soup, game_data)
            self._parse_round_history(game_soup, game_data)
            self._parse_performance_tab(game_id, match_id, base_url, game_data)
            self._parse_economy_tab(game_id, match_id, base_url, game_data)
            
            return game_data
            
        except Exception as e:
            self.logger.error(f"Error parsing game data for {game_id}: {e}")
            return {}
    
    def _get_team_ids(self, game_data: Dict[str, Any]):
        """Récup les IDs des équipes participants au match depuis la bdd"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # recup les équipes du match
            cursor.execute("""
                            SELECT t.id, t.short_name 
                            FROM teams t
                            INNER JOIN match_teams mt ON t.id = mt.team_id
                            WHERE mt.match_id = ?
                            ORDER BY mt.id
                        """, (game_data['match_id'],))

            teams = cursor.fetchall()
            
            if len(teams) >= 2:
                # eremière équipe = team1, deuxième équipe = team2
                game_data['team_ids']['team1'] = teams[0][0]  # id team1
                game_data['team_ids']['team2'] = teams[1][0]  # id team2
                game_data['team_ids']['team1_short'] = teams[0][1]  # nom court team1
                game_data['team_ids']['team2_short'] = teams[1][1]  # nom court team2
            else:
                self.logger.warning(f"Could not find teams for match {game_data['match_id']}")
                
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error getting team IDs: {e}")
    
    def _parse_overview(self, game_soup: BeautifulSoup, game_data: Dict[str, Any]):
        """Parse les statistiques de base des joueurs depuis l'onglet overview (joueurs, agents & scoreboard en gros)"""
        scoreboard_soup = game_soup.select('.wf-table-inset tr')
        
        for player_elem in scoreboard_soup:
            stats = player_elem.select('.mod-stat')
            
            #( condition pour ignorer la ligne entête)
            if not stats:
                continue
            
            try:
                player = {
                    'name': '',
                    'team_short_name': '',
                    'agent_name': '',
                    'agent_icon_url': '',
                    'stats': {}
                }
                
                # joueur et équipe du joueur
                name_elem = player_elem.select_one('.mod-player .text-of')
                if name_elem:
                    player['name'] = name_elem.get_text(strip=True)
                
                team_elem = player_elem.select_one('.mod-player .ge-text-light')
                if team_elem:
                    player['team_short_name'] = team_elem.get_text(strip=True)
                
                # agent du joueur
                agent_elem = player_elem.select_one('.mod-agent img')
                if agent_elem:
                    player['agent_name'] = agent_elem.get('title', '')
                    if agent_elem.has_attr('src'):
                        player['agent_icon_url'] = self.base_url + agent_elem['src']
                
                # scoreboard du joueur
                if len(stats) >= 12:
                    player['stats'] = {
                        'ratio_both': self._safe_float(stats[0].select_one('.mod-both')),
                        'ratio_t': self._safe_float(stats[0].select_one('.mod-t')),
                        'ratio_ct': self._safe_float(stats[0].select_one('.mod-ct')),
                        'acs_both': self._safe_int(stats[1].select_one('.mod-both')),
                        'acs_t': self._safe_int(stats[1].select_one('.mod-t')),
                        'acs_ct': self._safe_int(stats[1].select_one('.mod-ct')),
                        'k_both': self._safe_int(stats[2].select_one('.mod-both')),
                        'k_t': self._safe_int(stats[2].select_one('.mod-t')),
                        'k_ct': self._safe_int(stats[2].select_one('.mod-ct')),
                        'd_both': self._safe_int(stats[3].select_one('.mod-both')),
                        'd_t': self._safe_int(stats[3].select_one('.mod-t')),
                        'd_ct': self._safe_int(stats[3].select_one('.mod-ct')),
                        'a_both': self._safe_int(stats[4].select_one('.mod-both')),
                        'a_t': self._safe_int(stats[4].select_one('.mod-t')),
                        'a_ct': self._safe_int(stats[4].select_one('.mod-ct')),
                        'kddiff_both': self._safe_int(stats[5].select_one('.mod-both')),
                        'kddiff_t': self._safe_int(stats[5].select_one('.mod-t')),
                        'kddiff_ct': self._safe_int(stats[5].select_one('.mod-ct')),
                        'kast_both': self._safe_float(stats[6].select_one('.mod-both')),
                        'kast_t': self._safe_float(stats[6].select_one('.mod-t')),
                        'kast_ct': self._safe_float(stats[6].select_one('.mod-ct')),
                        'adr_both': self._safe_float(stats[7].select_one('.mod-both')),
                        'adr_t': self._safe_float(stats[7].select_one('.mod-t')),
                        'adr_ct': self._safe_float(stats[7].select_one('.mod-ct')),
                        'hs_both': self._safe_float(stats[8].select_one('.mod-both')),
                        'hs_t': self._safe_float(stats[8].select_one('.mod-t')),
                        'hs_ct': self._safe_float(stats[8].select_one('.mod-ct')),
                        'fk_both': self._safe_int(stats[9].select_one('.mod-both')),
                        'fk_t': self._safe_int(stats[9].select_one('.mod-t')),
                        'fk_ct': self._safe_int(stats[9].select_one('.mod-ct')),
                        'fd_both': self._safe_int(stats[10].select_one('.mod-both')),
                        'fd_t': self._safe_int(stats[10].select_one('.mod-t')),
                        'fd_ct': self._safe_int(stats[10].select_one('.mod-ct')),
                        'fkddiff_both': self._safe_int(stats[11].select_one('.mod-both')),
                        'fkddiff_t': self._safe_int(stats[11].select_one('.mod-t')),
                        'fkddiff_ct': self._safe_int(stats[11].select_one('.mod-ct'))
                    }
                
                game_data['players'].append(player)
                
            except Exception as e:
                self.logger.error(f"Error parsing player overview stats: {e}")
                continue
    
    def _parse_round_history(self, game_soup: BeautifulSoup, game_data: Dict[str, Any]):
        """Parse l'historique des rounds"""
        try:
            round_history_soup = game_soup.select('.vlr-rounds-row-col')
            
            for round_elem in round_history_soup:
                # (conditions piur ignorer les éléments non pertinents)
                if round_elem.select_one('.team'):
                    continue
                if 'mod-spacing' in round_elem.get('class', []):
                    continue
                if not round_elem.get('title'):
                    continue
                
                round_squares = round_elem.select('.rnd-sq')
                winner_team_id = None
                
                if len(round_squares) >= 2:
                    # verif quelle équipe a gagné selon .mod-win
                    if 'mod-win' in round_squares[0].get('class', []):
                        winner_team_id = game_data['team_ids'].get('team1')  # team1 gagnante
                    else:
                        winner_team_id = game_data['team_ids'].get('team2')  # team2 gagnante
                
                round_number_elem = round_elem.select_one('.rnd-num')
                round_number = round_number_elem.get_text(strip=True) if round_number_elem else ''
                
                # type de victoire (selon l'icone utilisée mdr) (defuse, elim, boom, time sinon unknown)
                win_type_elem = round_elem.select_one('.mod-win img')
                win_type = 'unknown'
                if win_type_elem and win_type_elem.has_attr('src'):
                    win_type = win_type_elem['src'].split('/')[-1].split('.')[0]
                
                round_info = {
                    'round_number': int(round_number) if round_number.isdigit() else 0,
                    'winner': winner_team_id,
                    'score': round_elem.get('title', ''),
                    'win_type': win_type
                }
                
                game_data['round_history'].append(round_info)
                
        except Exception as e:
            self.logger.error(f"Error parsing round history: {e}")
    
    def _parse_performance_tab(self, game_id: str, match_id: str, base_url: str, game_data: Dict[str, Any]):
        """Parse les statistiques depuis l'onglet performance (multikills, clutches, plants, defuses, éco)"""
        try:
            performance_url = f"{base_url}&tab=performance"
            self.wait()
            performance_soup = self.get_page(performance_url)
            
            if not performance_soup:
                self.logger.warning(f"Failed to fetch performance tab for game {game_id}")
                return
            
            game_perf_soup = performance_soup.select_one(f'.vm-stats-game[data-game-id="{game_id}"]')
            if not game_perf_soup:
                return
            
            stats_soup = game_perf_soup.select_one('.mod-adv-stats')
            if not stats_soup:
                return
            
            for player_elem in stats_soup.select('tr'):
                player_name_elem = player_elem.select_one('.team > div')
                if not player_name_elem or not player_name_elem.contents:
                    continue
                
                player_name = player_name_elem.contents[0].strip() if player_name_elem.contents else ''
                player_team_short = ''
                if len(player_name_elem.contents) > 1:
                    player_team_short = player_name_elem.contents[1].get_text(strip=True)
                
                stats = player_elem.select('.stats-sq')
                if not stats or len(stats) < 13:
                    continue
                
                # un peu chiant mais c'est le seul moyen de faire le lien entre les stats et le joueur
                # je cherche le joueur dans game_data['players'] par son nom et son équipe
                for player in game_data['players']:
                    if player['name'] == player_name and player['team_short_name'] == player_team_short:
                        # Ajouter les stats de performance
                        player['stats'].update({
                            'multikills_2k': self._safe_int_from_content(stats[1]),
                            'multikills_3k': self._safe_int_from_content(stats[2]),
                            'multikills_4k': self._safe_int_from_content(stats[3]),
                            'multikills_5k': self._safe_int_from_content(stats[4]),
                            'clutches_1v1': self._safe_int_from_content(stats[5]),
                            'clutches_1v2': self._safe_int_from_content(stats[6]),
                            'clutches_1v3': self._safe_int_from_content(stats[7]),
                            'clutches_1v4': self._safe_int_from_content(stats[8]),
                            'clutches_1v5': self._safe_int_from_content(stats[9]),
                            'eco': self._safe_int_from_content(stats[10]),
                            'plant': self._safe_int_from_content(stats[11]),
                            'defuse': self._safe_int_from_content(stats[12])
                        })
                        break
                        
        except Exception as e:
            self.logger.error(f"Error parsing performance stats for game {game_id}: {e}")
    
    def _parse_economy_tab(self, game_id: str, match_id: str, base_url: str, game_data: Dict[str, Any]):
        """Parse les statistiques économiques depuis l'onglet economy"""
        try:
            economy_url = f"{base_url}&tab=economy"
            self.wait()
            economy_soup = self.get_page(economy_url)
            
            if not economy_soup:
                self.logger.warning(f"Failed to fetch economy tab for game {game_id}")
                return
            
            game_econ_soup = economy_soup.select_one(f'.vm-stats-game[data-game-id="{game_id}"]')
            if not game_econ_soup:
                return
            
            stats_soup = game_econ_soup.select_one('.mod-econ')
            if not stats_soup:
                return

            # les statistiques économiques sont par équipe
            # ex: nb de pistols (played/won), nb d'écos, nb de fullbuys...
            for team_elem in stats_soup.select('tr'):
                team_name_elem = team_elem.select_one('.team')
                if not team_name_elem:
                    continue
                
                team_short_name = team_name_elem.get_text(strip=True)
                stats = team_elem.select('.stats-sq')
                
                if not stats or len(stats) < 5:
                    continue
                
                # pistols = int classique car aucun interet à mettre played/won car il y a tjrs 2 pistols joués
                pistols_won = self._safe_int_from_content(stats[0])

                # eco, semi_eco, semi_buy, full_buy au format "played (won)" sur le site
                eco_text = stats[1].contents[0].strip() if stats[1].contents else '0 (0)'
                semi_eco_text = stats[2].contents[0].strip() if stats[2].contents else '0 (0)'
                semi_buy_text = stats[3].contents[0].strip() if stats[3].contents else '0 (0)'
                full_buy_text = stats[4].contents[0].strip() if stats[4].contents else '0 (0)'
                
                economy_stats = {
                    'pistol': pistols_won,
                    'eco_played': self._extract_played_from_text(eco_text) - 2,  # les pistols ne comptent pas comme eco
                    'eco_won': self._extract_won_from_text(eco_text) - pistols_won,
                    'semi_eco_played': self._extract_played_from_text(semi_eco_text),
                    'semi_eco_won': self._extract_won_from_text(semi_eco_text),
                    'semi_buy_played': self._extract_played_from_text(semi_buy_text),
                    'semi_buy_won': self._extract_won_from_text(semi_buy_text),
                    'full_buy_played': self._extract_played_from_text(full_buy_text),
                    'full_buy_won': self._extract_won_from_text(full_buy_text)
                }
                
                game_data['economy_stats'][team_short_name] = economy_stats
                
        except Exception as e:
            self.logger.error(f"Error parsing economy stats for game {game_id}: {e}")
    
    def _safe_float(self, elem) -> Optional[float]:
        """Convertit un élément en float"""
        if not elem:
            return None
        text = elem.get_text(strip=True)
        if text == '\u00a0' or not text:
            return None
        try:
            # Gérer les pourcentages
            if text.endswith('%'):
                return float(text[:-1]) / 100.0
            return float(text)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, elem) -> Optional[int]:
        """Convertit un élément en int"""
        if not elem:
            return None
        text = elem.get_text(strip=True)
        if text == '\u00a0' or not text:
            return None
        try:
            return int(text)
        except (ValueError, TypeError):
            return None
    
    def _safe_int_from_content(self, elem) -> Optional[int]:
        """Convertit le contenu d'un élément en int"""
        if not elem or not elem.contents:
            return None
        text = elem.contents[0].strip() if elem.contents else ''
        if not text:
            return None
        try:
            return int(text)
        except (ValueError, TypeError):
            return None
    
    def _extract_played_from_text(self, text: str) -> int:
        """Extrait le nombre de rounds joués du format 'played (won)'"""
        try:
            return int(text.replace('\t', '').partition('(')[0].strip())
        except (ValueError, TypeError):
            return 0
    
    def _extract_won_from_text(self, text: str) -> int:
        """Extrait le nombre de rounds gagnés du format 'played (won)'"""
        try:
            won_part = text.replace('\t', '').partition('(')[2].replace(')', '').strip()
            return int(won_part)
        except (ValueError, TypeError):
            return 0
    
    def save_data(self, game_data: Dict[str, Any]) -> bool:
        """Save les données dans la base de données"""
        
        if not game_data:
            self.logger.warning("No game data to save")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # save les joueurs et leurs statistiques
            for player in game_data.get('players', []):
                # id unique du joueur (hash du nom + équipe pour eviter les collisions)
                player_id = hash(f"{player['name']}_{player['team_short_name']}") % (2**31 - 1)
                
                # recup id team
                team_id = None
                if player['team_short_name']:
                    cursor.execute("SELECT id FROM teams WHERE short_name = ?", (player['team_short_name'],))
                    team_result = cursor.fetchone()
                    if team_result:
                        team_id = team_result[0]
                
                cursor.execute("""
                    INSERT OR IGNORE INTO players (id, name)
                    VALUES (?, ?)
                """, (player_id, player['name']))
                
                # Statistiques du joueur
                stats = player.get('stats', {})
                cursor.execute("""
                                INSERT OR REPLACE INTO player_stats 
                                (game_id, player_id, team_id, agent_name, agent_icon_url,
                                ratio_both, ratio_t, ratio_ct, acs_both, acs_t, acs_ct,
                                k_both, k_t, k_ct, d_both, d_t, d_ct, a_both, a_t, a_ct,
                                kddiff_both, kddiff_t, kddiff_ct, kast_both, kast_t, kast_ct,
                                adr_both, adr_t, adr_ct, hs_both, hs_t, hs_ct,
                                fk_both, fk_t, fk_ct, fd_both, fd_t, fd_ct,
                                fkddiff_both, fkddiff_t, fkddiff_ct,
                                multikills_2k, multikills_3k, multikills_4k, multikills_5k,
                                clutches_1v1, clutches_1v2, clutches_1v3, clutches_1v4, clutches_1v5,
                                eco, plant, defuse)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                    game_data['game_id'], player_id, team_id,
                    player['agent_name'], player['agent_icon_url'],
                    stats.get('ratio_both'), stats.get('ratio_t'), stats.get('ratio_ct'),
                    stats.get('acs_both'), stats.get('acs_t'), stats.get('acs_ct'),
                    stats.get('k_both'), stats.get('k_t'), stats.get('k_ct'),
                    stats.get('d_both'), stats.get('d_t'), stats.get('d_ct'),
                    stats.get('a_both'), stats.get('a_t'), stats.get('a_ct'),
                    stats.get('kddiff_both'), stats.get('kddiff_t'), stats.get('kddiff_ct'),
                    stats.get('kast_both'), stats.get('kast_t'), stats.get('kast_ct'),
                    stats.get('adr_both'), stats.get('adr_t'), stats.get('adr_ct'),
                    stats.get('hs_both'), stats.get('hs_t'), stats.get('hs_ct'),
                    stats.get('fk_both'), stats.get('fk_t'), stats.get('fk_ct'),
                    stats.get('fd_both'), stats.get('fd_t'), stats.get('fd_ct'),
                    stats.get('fkddiff_both'), stats.get('fkddiff_t'), stats.get('fkddiff_ct'),
                    stats.get('multikills_2k'), stats.get('multikills_3k'), 
                    stats.get('multikills_4k'), stats.get('multikills_5k'),
                    stats.get('clutches_1v1'), stats.get('clutches_1v2'), 
                    stats.get('clutches_1v3'), stats.get('clutches_1v4'), stats.get('clutches_1v5'),
                    stats.get('eco'), stats.get('plant'), stats.get('defuse')
                ))
            
            # save historique des rounds
            for round_info in game_data.get('round_history', []):
                cursor.execute("""
                            INSERT OR REPLACE INTO round_history 
                            (game_id, round_number, winner, score, win_type)
                            VALUES (?, ?, ?, ?, ?)
                            """, (
                    game_data['game_id'],
                    round_info['round_number'],
                    round_info['winner'],
                    round_info['score'],
                    round_info['win_type']
                ))
            
            # save stats eco par équipe
            for team_short, econ_stats in game_data.get('economy_stats', {}).items():
                # recup id team
                cursor.execute("SELECT id FROM teams WHERE short_name = ?", (team_short,))
                team_result = cursor.fetchone()

                if team_result:
                    team_id = team_result[0]
                    cursor.execute("""
                                    INSERT OR REPLACE INTO economy_stats 
                                    (game_id, team_id, pistol, eco_played, eco_won,
                                    semi_eco_played, semi_eco_won, semi_buy_played, semi_buy_won,
                                    full_buy_played, full_buy_won)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                        game_data['game_id'], team_id,
                        econ_stats['pistol'],
                        econ_stats['eco_played'], econ_stats['eco_won'],
                        econ_stats['semi_eco_played'], econ_stats['semi_eco_won'],
                        econ_stats['semi_buy_played'], econ_stats['semi_buy_won'],
                        econ_stats['full_buy_played'], econ_stats['full_buy_won']
                    ))
            
            conn.commit()
            self.logger.info(f"Saved game {game_data['game_id']} stats to database") if self.full_log else None
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving game data to database: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
