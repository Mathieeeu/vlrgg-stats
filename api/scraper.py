import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import datetime
import time
import random
from tqdm import tqdm
import os


class VLRScraper:
    def __init__(self, delay: float = 1.0):
        self.base_url = "https://www.vlr.gg"
        self.session = requests.Session()
        self.delay = delay  # seconds between requests (+- 30%)

    def fetch_page(self, url):
        """Fetch the HTML content of a page."""
        time.sleep(self.delay + (self.delay * 0.3 * (2 * random.random() - 1)))  # random delay within +-30%
        response = self.session.get(url)
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to fetch page: {url} with status code {response.status_code}")
        
    def collect_events(self, season: str):
        """Collect events for a given season."""
        url = f"{self.base_url}/{season}"
        page_content = self.fetch_page(url)
        soup = BeautifulSoup(page_content, 'html.parser')
        
        events = []
        for event in soup.select('.event-item'):
            title = event.select_one('.event-item-title')
            status = event.select_one('.event-item-desc-item-status')
            prize = event.select_one('.event-item-desc-item.mod-prize')
            dates = event.select_one('.event-item-desc-item.mod-dates')
            country = event.select_one('.event-item-desc-item.mod-location .flag')
            thumb = event.select_one('.event-item-thumb img')

            def parse_prize(prize_text):
                if not prize_text:
                    return None
                match = re.search(r'([\d,]+)', prize_text.replace('$', ''))
                if match:
                    return int(match.group(1).replace(',', ''))
                return None
            
            match = re.search(r'(\d{4})', season)
            year = match.group(1) if match else None
            dates = dates.get_text(strip=True).replace('Dates', '').split('\u2014')
            dates_with_year = [date.strip() + f" {year}" if date.strip() and date.strip() != 'TBD' else '' for date in dates]
            # Handle cases where the second date is missing the month
            if len(dates_with_year) == 2 and re.match(r'^\d{1,2} \d{4}$', dates_with_year[1]):
                # Use the month from the first date :)
                first_month = dates_with_year[0].split()[0]
                second_day, second_year = dates_with_year[1].split()
                dates_with_year[1] = f"{first_month} {second_day} {second_year}"

            dates_formatted = [
                datetime.datetime.strptime(date, '%b %d %Y').strftime('%Y-%m-%d')
                for date in dates_with_year if date.strip() and date != ''
            ]
            # print(dates_formatted)

            REGIONS = {
                'americas': 'amer',
                'emea': 'emea',
                'pacific': 'apac',
                'china': 'cn',
            }

            # Extract region from URL
            event_url = event['href']
            region = None
            event_name = None
            for key in REGIONS:
                if f"-{key}-" in event_url:
                    region = REGIONS[key]
                    break
            if not region:
                if 'champions' in event_url or 'masters' in event_url:
                    region = 'inter'
                else:
                    region = 'unknown'
            
            # Extract event_name
            match = re.search(r'-(' + '|'.join(REGIONS.keys()) + r')-(.+)', event_url)
            if match:
                event_name = match.group(2)
            else:
                # fallback: take last part after last slash
                event_name = event_url.rstrip('/').split('/')[-1]

            # print(f"{event_name=}, {region=}")

            id = event['href'].split('/')[2]
            event_data = {
                'id': id,
                'url': f'{self.base_url}/event/{id}',
                'title': title.get_text(strip=True) if title else None,
                'status': status.get_text(strip=True) if status else None,
                'prize_pool': parse_prize(prize.get_text(strip=True)) if prize else None,
                'start_date': dates_formatted[0] if dates_formatted else None,
                'end_date': dates_formatted[1] if len(dates_formatted) > 1 else None,
                'region': region,
                'event_name': event_name,
                'location': country['class'][1][4:] if country and len(country['class']) > 1 else None,
                'thumbnail': 'https:' + thumb['src'] if thumb and thumb.has_attr('src') else None
            }
            events.append(event_data)
        
        return events
    
    def collect_matches(self, event_id: str):
        """Collect matches for a given event."""
        url = f"{self.base_url}/event/matches/{event_id}?group=completed"
        page_content = self.fetch_page(url)
        soup = BeautifulSoup(page_content, 'html.parser')
        
        matches = []

        with open('data/teams.json', 'r', encoding='utf-8') as f:
            teams_data = json.load(f)
            teams_short_names = teams_data['short_names']
            teams_regions = teams_data['regions']

        # collection of ids and urls
        for match in soup.select('.match-item'):
            id = match['href'].split('/')[1]
            match_data = {
                'match_id': id,
                'url': f'{self.base_url}/{id}',
                'event_id': event_id
            }
            matches.append(match_data)

        # print(f"Found {len(matches)} matches for event {event_id}")

        # collect all match details
        for match in tqdm(matches, desc=f"Collecting matches for event {event_id}", unit="match"):
            match_url = match['url']
            match_page_content = self.fetch_page(match_url)
            match_soup = BeautifulSoup(match_page_content, 'html.parser')

            # print(match_url)

            # # write the page content to a file for debugging
            # with open(f"output/{match['match_id']}.html", "w", encoding="utf-8") as f:
            #     f.write(str(match_soup))

            # Extract match details
            match['series'] = match_soup.select_one('.match-header-event-series').get_text(strip=True).replace('\n', '').replace('\t', '') if match_soup.select_one('.match-header-event-series') else  ''
            
            # if the match is a showmatch, do not extract anything from it and delete it from the list
            if 'showmatch' in match['series'].lower():
                print(f"Skipping showmatch: {match['match_id']}")
                matches.remove(match)
                continue

            # extract date, time and patch
            date_patch_elem = match_soup.select_one('.match-header-date')
            if date_patch_elem:
                text = date_patch_elem.get_text(strip=True).replace('\n', '').replace('\t', '')
                date_text, _, patch_text = text.partition('Patch')
                m = re.match(r'([A-Za-z]+\s+\d{1,2},\s*\d{4})(\d{1,2}:\d{2}\s*[AP]M)?', date_text.strip())
                match['date'] = ''
                match['time'] = ''
                if m:
                    try:
                        match['date'] = datetime.datetime.strptime(m.group(1), '%B %d, %Y').strftime('%Y-%m-%d')
                    except Exception:
                        match['date'] = m.group(1)
                    if m.group(2):
                        try:
                            match['time'] = datetime.datetime.strptime(m.group(2).strip(), '%I:%M %p').strftime('%H:%M')
                        except Exception:
                            match['time'] = m.group(2).strip()
                else:
                    match['date'] = date_text.strip()
                match['patch'] = patch_text.strip()
            else:
                match['date'] = match['time'] = match['patch'] = ''

            # # Extract teams
            match_result_soup = match_soup.select_one('.match-header-vs')

            # # write the page content to a file for debugging
            # with open(f"output/{match['match_id']}_teams.html", "w", encoding="utf-8") as f:
            #     f.write(str(match_result_soup))

            teams = []
            team_links = match_result_soup.select('.match-header-link')
            score_elements = match_result_soup.select('.match-header-vs-score span')

            # Extract scores (based on position in the page :)
            first_team_score = ''
            second_team_score = ''
            if len(score_elements) >= 2:
                first_team_score = score_elements[0].get_text(strip=True)
                second_team_score = score_elements[-1].get_text(strip=True)

            for i, team_link in enumerate(team_links):
                team_name_elem = team_link.select_one('.wf-title-med')
                team_logo_elem = team_link.select_one('img')
                
                # Assign scores based on team position
                if i == 0:  # First team
                    team_score = first_team_score
                    is_winner = first_team_score and second_team_score and int(first_team_score) > int(second_team_score)
                else:  # Second team  
                    team_score = second_team_score
                    is_winner = first_team_score and second_team_score and int(second_team_score) > int(first_team_score)

                def get_team_region(team_short_name, teams_regions, default='unknown'):
                    for region, teams in teams_regions.items():
                        if team_short_name in teams:
                            return region
                    return default

                team_name = team_name_elem.get_text(strip=True) if team_name_elem else ''
                team_short_name = teams_short_names.get(team_name, '') if team_name else None

                team_info = {
                    'name': team_name,
                    'short_name': team_short_name,
                    'region': get_team_region(team_short_name, teams_regions, default='unknown'),
                    'logo_url': 'https:' + team_logo_elem['src'] if team_logo_elem and team_logo_elem.has_attr('src') else '',
                    'team_url': f"{self.base_url}{team_link['href']}" if team_link.has_attr('href') else '',
                    'score': team_score,
                    'is_winner': is_winner,
                    'picks': [],
                    'bans': []
                }
                teams.append(team_info)
                
            picks_bans = match_soup.select_one('.match-header-note').get_text(strip=True) # ex : FNC ban Pearl; FNC ban Fracture; FNC pick Lotus; EG pick Split; FNC pick Bind; EG pick Ascent; Haven remains
            # print(f"{picks_bans=}")
            match['picks'] = []
            match['bans'] = []
            match['decider'] = ''
            for pb in picks_bans.split('; '):
                pb = pb.split(' ')
                if len(pb) < 3 and pb[1].lower() == 'remains':
                    match['decider'] = pb[0].strip() if pb[0].strip() else ''
                elif pb[1].lower() == 'ban':
                    team_short_name = pb[0].strip()
                    teams[0 if teams[0]['short_name'] == team_short_name else 1]['bans'].append(pb[2].strip() if len(pb) > 2 else '')
                    match['bans'].append(pb[2].strip() if len(pb) > 2 else '')
                elif pb[1].lower() == 'pick':
                    team_short_name = pb[0].strip()
                    teams[0 if teams[0]['short_name'] == team_short_name else 1]['picks'].append(pb[2].strip() if len(pb) > 2 else '')
                    match['picks'].append(pb[2].strip() if len(pb) > 2 else '')
                else:
                    print(f"Unknown pick/ban format: {pb}")
                    break

            match['teams'] = teams

            # Collect game ids
            games = []

            game_soups = match_soup.select('.vm-stats-game')
            for game_soup in game_soups:
                game_id = game_soup['data-game-id']
                if game_id == 'all':
                    continue
                # print(f"{game_id=}")
                
                # #write the page content to a file for debugging
                # with open(f"output/game_{game_id}.html", "w", encoding="utf-8") as f:
                #     f.write(str(game_soup))
                
                game_data = {
                    'game_id': game_id,
                    'url': f'{self.base_url}/{match["match_id"]}?game={game_id}',
                    'map': game_soup.select_one('.map').get_text(strip=True).partition('PICK')[0] if game_soup.select_one('.map') else '',
                    'pick': teams[0]['short_name'] if game_soup.select_one('.picked.mod-1') else (teams[1]['short_name'] if game_soup.select_one('.picked.mod-2') else ''),
                    'win': teams[0]['short_name'] if 'mod-win' in game_soup.select('.score')[0].get('class', []) else (teams[1]['short_name'] if 'mod-win' in game_soup.select('.score')[1].get('class', []) else ''),
                    'duration': game_soup.select_one('.map-duration').get_text(strip=True) if game_soup.select_one('.map-duration') else '',
                    'scores': {
                        teams[0]['short_name']: {
                            'score': game_soup.select('.score')[0].get_text(strip=True) if game_soup.select('.score')[0] else '',
                            't': game_soup.select('.team .mod-t')[0].get_text(strip=True) if len(game_soup.select('.team .mod-t')) > 0 else '',
                            'ct': game_soup.select('.team .mod-ct')[0].get_text(strip=True) if len(game_soup.select('.team .mod-ct')) > 0 else '',
                        },
                        teams[1]['short_name']: {
                            'score': game_soup.select('.score')[1].get_text(strip=True) if game_soup.select('.score')[1] else '',
                            't': game_soup.select('.team .mod-t')[1].get_text(strip=True) if len(game_soup.select('.team .mod-t')) > 1 else '',
                            'ct': game_soup.select('.team .mod-ct')[1].get_text(strip=True) if len(game_soup.select('.team .mod-ct')) > 1 else '',
                        }
                    },
                    'economy': {},
                    'history': [],
                    'scoreboard': {
                        teams[0]['short_name']: [],
                        teams[1]['short_name']: []
                    }
                }

                # Collect round history
                round_history_soup = game_soup.select('.vlr-rounds-row-col')
                for round_elem in round_history_soup:
                    if round_elem.select_one('.team'):
                        continue

                    if 'mod-spacing' in round_elem.get('class', []):
                        continue
                    if not round_elem.get('title'):
                        continue

                    round_squares = round_elem.select('.rnd-sq')
                    if len(round_squares) >= 2:
                        # Check if first square has mod-win class (then first team won)
                        if 'mod-win' in round_squares[0].get('class', []):
                            winner = teams[0]['short_name']
                        else:
                            # ... then second team won
                            winner = teams[1]['short_name']
                    else:
                        winner = 'unknown'

                    round_info = {
                        'round': round_elem.select_one('.rnd-num').get_text(strip=True) if round_elem.select_one('.rnd-num') else '',
                        'winner': winner,
                        'score': round_elem['title'],
                        'win_type': round_elem.select_one('.mod-win img')['src'].split('/')[-1].split('.')[0] if round_elem.select_one('.mod-win img') else 'unknown',
                    }
                    game_data['history'].append(round_info)

                # Collect scoreboard (overview tab only)
                scoreboard_soup = game_soup.select('.wf-table-inset tr')
                players = []
                for player_elem in scoreboard_soup:
                    stats = player_elem.select('.mod-stat')

                    # skip the header row 
                    if not stats:
                        continue
                    
                    player = {
                        'name': player_elem.select_one('.mod-player .text-of').get_text(strip=True) if player_elem.select_one('.mod-player .text-of') else '',
                        'team': player_elem.select_one('.mod-player .ge-text-light').get_text(strip=True) if player_elem.select_one('.mod-player .ge-text-light') else '',
                        'agent': {
                            'name': player_elem.select_one('.mod-agent img')['title'] if player_elem.select_one('.mod-agent img') else '',
                            'icon_url': self.base_url + player_elem.select_one('.mod-agent img')['src'] if player_elem.select_one('.mod-agent img') and player_elem.select_one('.mod-agent img').has_attr('src') else ''
                        },
                        'stats': {
                            'ratio': {
                                'both': stats[0].select_one('.mod-both').get_text(strip=True) if stats[0].select_one('.mod-both') else None,
                                't': stats[0].select_one('.mod-t').get_text(strip=True) if stats[0].select_one('.mod-t') else None,
                                'ct': stats[0].select_one('.mod-ct').get_text(strip=True) if stats[0].select_one('.mod-ct') else None
                            },
                            'acs': {
                                'both': stats[1].select_one('.mod-both').get_text(strip=True) if stats[1].select_one('.mod-both') else None,
                                't': stats[1].select_one('.mod-t').get_text(strip=True) if stats[1].select_one('.mod-t') else None,
                                'ct': stats[1].select_one('.mod-ct').get_text(strip=True) if stats[1].select_one('.mod-ct') else None
                            },
                            'k': {
                                'both': stats[2].select_one('.mod-both').get_text(strip=True) if stats[2].select_one('.mod-both') else None,
                                't': stats[2].select_one('.mod-t').get_text(strip=True) if stats[2].select_one('.mod-t') else None,
                                'ct': stats[2].select_one('.mod-ct').get_text(strip=True) if stats[2].select_one('.mod-ct') else None
                            },
                            'd': {
                                'both': stats[3].select_one('.mod-both').get_text(strip=True) if stats[3].select_one('.mod-both') else None,
                                't': stats[3].select_one('.mod-t').get_text(strip=True) if stats[3].select_one('.mod-t') else None,
                                'ct': stats[3].select_one('.mod-ct').get_text(strip=True) if stats[3].select_one('.mod-ct') else None
                            },
                            'a': {
                                'both': stats[4].select_one('.mod-both').get_text(strip=True) if stats[4].select_one('.mod-both') else None,
                                't': stats[4].select_one('.mod-t').get_text(strip=True) if stats[4].select_one('.mod-t') else None,
                                'ct': stats[4].select_one('.mod-ct').get_text(strip=True) if stats[4].select_one('.mod-ct') else None
                            },
                            'kddiff': {
                                'both': stats[5].select_one('.mod-both').get_text(strip=True) if stats[5].select_one('.mod-both') else None,
                                't': stats[5].select_one('.mod-t').get_text(strip=True) if stats[5].select_one('.mod-t') else None,
                                'ct': stats[5].select_one('.mod-ct').get_text(strip=True) if stats[5].select_one('.mod-ct') else None
                            },
                            'kast': {
                                'both': stats[6].select_one('.mod-both').get_text(strip=True) if stats[6].select_one('.mod-both') else None,
                                't': stats[6].select_one('.mod-t').get_text(strip=True) if stats[6].select_one('.mod-t') else None,
                                'ct': stats[6].select_one('.mod-ct').get_text(strip=True) if stats[6].select_one('.mod-ct') else None
                            },
                            'adr': {
                                'both': stats[7].select_one('.mod-both').get_text(strip=True) if stats[7].select_one('.mod-both') else None,
                                't': stats[7].select_one('.mod-t').get_text(strip=True) if stats[7].select_one('.mod-t') else None,
                                'ct': stats[7].select_one('.mod-ct').get_text(strip=True) if stats[7].select_one('.mod-ct') else None
                            },
                            'hs': {
                                'both': stats[8].select_one('.mod-both').get_text(strip=True) if stats[8].select_one('.mod-both') else None,
                                't': stats[8].select_one('.mod-t').get_text(strip=True) if stats[8].select_one('.mod-t') else None,
                                'ct': stats[8].select_one('.mod-ct').get_text(strip=True) if stats[8].select_one('.mod-ct') else None
                            },
                            'fk': {
                                'both': stats[9].select_one('.mod-both').get_text(strip=True) if stats[9].select_one('.mod-both') else None,
                                't': stats[9].select_one('.mod-t').get_text(strip=True) if stats[9].select_one('.mod-t') else None,
                                'ct': stats[9].select_one('.mod-ct').get_text(strip=True) if stats[9].select_one('.mod-ct') else None
                            },
                            'fd': {
                                'both': stats[10].select_one('.mod-both').get_text(strip=True) if stats[10].select_one('.mod-both') else None,
                                't': stats[10].select_one('.mod-t').get_text(strip=True) if stats[10].select_one('.mod-t') else None,
                                'ct': stats[10].select_one('.mod-ct').get_text(strip=True) if stats[10].select_one('.mod-ct') else None
                            },
                            'fkddiff': {
                                'both': stats[11].select_one('.mod-both').get_text(strip=True) if stats[11].select_one('.mod-both') else None,
                                't': stats[11].select_one('.mod-t').get_text(strip=True) if stats[11].select_one('.mod-t') else None,
                                'ct': stats[11].select_one('.mod-ct').get_text(strip=True) if stats[11].select_one('.mod-ct') else None
                            }
                        }
                    }
                    players.append(player)

                # Group players by their team instead of assuming fixed positions
                team1_players = []
                team2_players = []
                
                for player in players:
                    if player['team'] == teams[0]['short_name']:
                        team1_players.append(player)
                    elif player['team'] == teams[1]['short_name']:
                        team2_players.append(player)
                
                game_data['scoreboard'] = {
                    teams[0]['short_name']: team1_players,
                    teams[1]['short_name']: team2_players
                }

                # Performance tab
                performance_url = f"{match['url']}?game={game_id}&tab=performance"
                performance_page_content = self.fetch_page(performance_url)
                performance_tab_soup = BeautifulSoup(performance_page_content, 'html.parser')

                # # write the performance page content to a file for debugging
                # with open(f"output/{match['match_id']}_performance_tab.html", "w", encoding="utf-8") as f:
                #     f.write(str(performance_tab_soup))

                performance_soup = performance_tab_soup.select_one('.vm-stats-game[data-game-id="' + game_id + '"]')

                # # write the performance page content to a file for debugging
                # with open(f"output/{match['match_id']}_performance.html", "w", encoding="utf-8") as f:
                #     f.write(str(performance_soup))

                stats_soup = performance_soup.select_one('.mod-adv-stats')

                # # write the stats page content to a file for debugging
                # with open(f"output/{match['match_id']}_stats.html", "w", encoding="utf-8") as f:
                #     f.write(str(stats_soup))
                    
                for player_elem in stats_soup.select('tr'):

                    player_name_elem = player_elem.select_one('.team > div')
                    if not player_name_elem:
                        continue

                    player_name = player_name_elem.contents[0].strip() if player_name_elem.contents else ''
                    player_team_short = player_name_elem.contents[1].get_text(strip=True) if len(player_name_elem.contents) > 1 else ''
                    # print(f"{player_team_short} {player_name}")

                    stats = player_elem.select('.stats-sq')

                    # skip the header row 
                    if not stats:
                        continue

                    multikills_stats = {
                        '2k': int(stats[1].contents[0].strip()) if stats[1].contents[0].strip() else 0,
                        '3k': int(stats[2].contents[0].strip()) if stats[2].contents[0].strip() else 0,
                        '4k': int(stats[3].contents[0].strip()) if stats[3].contents[0].strip() else 0,
                        '5k': int(stats[4].contents[0].strip()) if stats[4].contents[0].strip() else 0
                    }

                    clutches_stats = {
                        '1v1': int(stats[5].contents[0].strip()) if stats[5].contents[0].strip() else 0,
                        '1v2': int(stats[6].contents[0].strip()) if stats[6].contents[0].strip() else 0,
                        '1v3': int(stats[7].contents[0].strip()) if stats[7].contents[0].strip() else 0,
                        '1v4': int(stats[8].contents[0].strip()) if stats[8].contents[0].strip() else 0,
                        '1v5': int(stats[9].contents[0].strip()) if stats[9].contents[0].strip() else 0
                    }

                    eco = int(stats[10].contents[0].strip()) if stats[10].contents[0].strip() else 0
                    plant = int(stats[11].contents[0].strip()) if stats[11].contents[0].strip() else 0
                    defuse = int(stats[12].contents[0].strip()) if stats[12].contents[0].strip() else 0

                    # print(f"Multikills stats for {player_name}: {multikills_stats} Clutches stats: {clutches_stats} Eco: {eco} Plant: {plant} Defuse: {defuse}")

                    for player in game_data['scoreboard'][player_team_short]:
                        if player['name'] == player_name:
                            player['stats']['multikills'] = multikills_stats
                            player['stats']['clutches'] = clutches_stats
                            player['stats']['eco'] = eco
                            player['stats']['plant'] = plant
                            player['stats']['defuse'] = defuse
                            break


                # Economy tab
                economy_url = f"{match['url']}?game={game_id}&tab=economy"
                economy_page_content = self.fetch_page(economy_url)
                economy_tab_soup = BeautifulSoup(economy_page_content, 'html.parser')

                # # write the economy page content to a file for debugging
                # with open(f"output/{match['match_id']}_economy_tab.html", "w", encoding="utf-8") as f:
                #     f.write(str(economy_tab_soup))

                economy_soup = economy_tab_soup.select_one('.vm-stats-game[data-game-id="' + game_id + '"]')

                stats_soup = economy_soup.select_one('.mod-econ')

                # # write the economy stats page content to a file for debugging
                # with open(f"output/{match['match_id']}_economy_stats.html", "w", encoding="utf-8") as f:
                #     f.write(str(stats_soup))

                for team_elem in stats_soup.select('tr'):
                    team_name_elem = team_elem.select_one('.team')
                    if not team_name_elem:
                        continue
                    
                    team_short_name = team_name_elem.get_text(strip=True)
                    if team_short_name not in [teams[0]['short_name'], teams[1]['short_name']]:
                        continue

                    stats = team_elem.select('.stats-sq')
                    pistols_won = int(stats[0].contents[0].strip()) if stats[0].contents[0].strip() else 0
                    
                    economy_stats = {
                        'pistol': pistols_won,
                        'eco': {
                            # pistols do not count as eco rounds in VLR, so we subtract them from the played and won counts
                            'played': int(stats[1].contents[0].strip().replace('\t', '').partition('(')[0]) - 2 if stats[1].contents[0].strip() else 0,
                            'won': int(stats[1].contents[0].strip().replace('\t', '').partition('(')[2].replace(')', '')) - pistols_won if stats[1].contents[0].strip() else 0
                        },
                        'semi_eco': {
                            'played': int(stats[2].contents[0].strip().replace('\t', '').partition('(')[0]) if stats[2].contents[0].strip() else 0,
                            'won': int(stats[2].contents[0].strip().replace('\t', '').partition('(')[2].replace(')', '')) if stats[2].contents[0].strip() else 0
                        },
                        'semi_buy': {
                            'played': int(stats[3].contents[0].strip().replace('\t', '').partition('(')[0]) if stats[3].contents[0].strip() else 0,
                            'won': int(stats[3].contents[0].strip().replace('\t', '').partition('(')[2].replace(')', '')) if stats[3].contents[0].strip() else 0
                        },
                        'full_buy': {
                            'played': int(stats[4].contents[0].strip().replace('\t', '').partition('(')[0]) if stats[4].contents[0].strip() else 0,
                            'won': int(stats[4].contents[0].strip().replace('\t', '').partition('(')[2].replace(')', '')) if stats[4].contents[0].strip() else 0
                        }
                    }

                    # print(f"Economy stats for {team_short_name}: {economy_stats}")

                    game_data['economy'][team_short_name] = economy_stats

                games.append(game_data)

            match['games'] = games

            # break # Limit to one match for testing

        return matches

if __name__ == "__main__":

    t0 = time.time()
    scraper = VLRScraper()
    season = "vct-2023"
    try:
        events = scraper.collect_events(season)
        with open(f"output/{season}_events.json", "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        print(f"An error occurred: {e}")

    print(f"Collected {len(events)} events for season {season} in {time.time() - t0:.2f} seconds")

    # # Example of collecting matches for a specific event
    # event_id = "1494" # 1494 = Masters Tokyo, 1657 = Champions Los Angeles
    # try:
    #     matches = scraper.collect_matches(event_id)
    #     with open(f"output/event_{event_id}_matches.json", "w", encoding="utf-8") as f:
    #         json.dump(matches, f, indent=2)

    # except Exception as e:
    #     print(f"An error occurred: {e}")

    all_events_ids = [event['id'] for event in events]
    print(f"Found {len(all_events_ids)} events with IDs: {all_events_ids}")

    all_matches = []
    for event_id in all_events_ids:
        try:
            matches = scraper.collect_matches(event_id)
            all_matches.extend(matches)

            # save backup
            with open(f"backup/{season}_matches_{event_id}.json", "w", encoding="utf-8") as f:
                json.dump(matches, f, separators=(',', ': '))

        except Exception as e:
            print(f"An error occurred while collecting matches for event {event_id}: {e}")

    with open(f"output/{season}_matches.json", "w", encoding="utf-8") as f:
        json.dump(all_matches, f, indent=2)

    with open(f"output/{season}_matches_raw.json", "w", encoding="utf-8") as f:
        json.dump(all_matches, f, separators=(',', ': '))
    
    # # delete the backup files
    # backup_files = [f for f in os.listdir('backup') if f.startswith(f"{season}_matches_")]
    # for file in backup_files:
    #     os.remove(os.path.join('backup', file))

    print(f"Scraping completed in {time.time() - t0:.2f} seconds")