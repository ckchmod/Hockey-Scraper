"""
This module contains functions to scrape the Json Play by Play for any given game
"""

import pandas as pd
import json
import time
import hockey_scraper.shared as shared


def get_pbp(game_id):
    """
    Given a game_id it returns the raw json
    Ex: http://statsapi.web.nhl.com/api/v1/game/2016020475/feed/live
    
    :param game_id: the game
    
    :return: raw json of game or None if couldn't get game
    """
    url = 'http://statsapi.web.nhl.com/api/v1/game/{}/feed/live'.format(game_id)

    response = shared.get_url(url)
    time.sleep(1)

    # Return None if can't get page
    if not response:
        print("Json pbp for game {} is either not there or can't be obtained".format(game_id))
        return None

    return json.loads(response.text)


def change_event_name(event):
    """
    Change event names from json style to html
    ex: BLOCKED_SHOT to BLOCK
    
    :param event: event type
    
    :return: fixed event type
    """
    event_types ={
        'PERIOD_START': 'PSTR',
        'FACEOFF': 'FAC',
        'BLOCKED_SHOT': 'BLOCK',
        'GAME_END': 'GEND',
        'GIVEAWAY': 'GIVE',
        'GOAL': 'GOAL',
        'HIT': 'HIT',
        'MISSED_SHOT': 'MISS',
        'PERIOD_END': 'PEND',
        'SHOT': 'SHOT',
        'STOP': 'STOP',
        'TAKEAWAY': 'TAKE',
        'PENALTY': 'PENL',
        'Early Intermission Start': 'EISTR',
        'Early Intermission End': 'EIEND',
        'Shootout Completed': 'SOC',
    }

    try:
        return event_types[event]
    except KeyError:
        return event


def get_teams(pbp_json):
    """
    Get teams 
    
    :param json: pbp json
    
    :return: dict with home and away
    """
    return {'Home': shared.TEAMS[pbp_json['gameData']['teams']['home']['name'].upper()],
            'Away': shared.TEAMS[pbp_json['gameData']['teams']['away']['name'].upper()]}


def parse_event(event):
    """
    Parses a single event when the info is in a json format
    
    :param event: json of event 
    
    :return: dictionary with the info
    """
    play = dict()

    play['period'] = event['about']['period']
    play['event'] = str(change_event_name(event['result']['eventTypeId']))
    play['seconds_elapsed'] = shared.convert_to_seconds(event['about']['periodTime'])

    # If there's a players key that means an event occurred on the play.
    if 'players' in event.keys():
        play['p1_name'] = shared.fix_name(event['players'][0]['player']['fullName'])
        play['p1_ID'] = event['players'][0]['player']['id']

        for i in range(len(event['players'])):
            if event['players'][i]['playerType'] != 'Goalie':
                play['p{}_name'.format(i + 1)] = shared.fix_name(event['players'][i]['player']['fullName'].upper())
                play['p{}_ID'.format(i + 1)] = event['players'][i]['player']['id']

        # Coordinates aren't always there
        try:
            play['xC'] = event['coordinates']['x']
            play['yC'] = event['coordinates']['y']
        except KeyError:
            play['xC'] = ''
            play['yC'] = ''

    return play


def parse_json(game_json, game_id):
    """
    Scrape the json for a game
    
    :param game_json: raw json
    :param game_id: game id for game
    
    :return: Either a DataFrame with info for the game 
    """
    columns = ['period', 'event', 'seconds_elapsed', 'p1_name', 'p1_ID', 'p2_name', 'p2_ID', 'p3_name', 'p3_ID', 'xC', 'yC']

    # 'PERIOD READY' & 'PERIOD OFFICIAL'..etc aren't found in html...so get rid of them
    events_to_ignore = ['PERIOD_READY', 'PERIOD_OFFICIAL', 'GAME_READY', 'GAME_OFFICIAL']

    try:
        plays = game_json['liveData']['plays']['allPlays'][2:]  # All the plays/events in a game
        events = [parse_event(play) for play in plays if play['result']['eventTypeId'] not in events_to_ignore]
    except Exception as e:
        print('Error parsing Json pbp for game {}'.format(game_id), e)
        return None

    return pd.DataFrame(events, columns=columns)


def scrape_game(game_id):
    """
    Used for debugging. HTML depends on json so can't follow this structure
    
    :param game_id: game to scrape
    
    :return: DataFrame of game info
    """
    game_json = get_pbp(game_id)

    if not game_json:
        print("Json pbp for game {} is not either not there or can't be obtained".format(game_id))
        return None

    try:
        game_df = parse_json(game_json, game_id)
    except Exception as e:
        print('Error parsing Json pbp for game {}'.format(game_id), e)
        return None

    return game_df

