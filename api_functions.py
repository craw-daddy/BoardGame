#  Functionality to interact with BGG's XML_API2.
#  For more information see: https://boardgamegeek.com/wiki/page/BGG_XML_API2#

import pandas as pd
import numpy as np
import requests
import re
import time
import dill

from bs4 import BeautifulSoup

from constants import BASE_API, EXTRA_DATA

#  Filter out some annoying warnings from the latest version of BeautifulSoup
import warnings
from bs4.builder import XMLParsedAsHTMLWarning
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)


def get_thing(id, **args):
    '''A "thing" is BGG's designation for a physical item, 
       such as a board game, expansion, board game accessory, 
       etc.  The "id" supplied can have several numbers 
       separated by commas to retrieve more than one item 
       at a time.

       For more information see: https://boardgamegeek.com/wiki/page/BGG_XML_API2#
       
       **args can supply an arbitrary collection of options 
       (in the form of paramaters like key=value) that will 
       be appended into the query string, where these pairs 
       will be turned into strings like "key=value" and added 
       to the query string (preceded, of course, by an ampersand 
       to make it a separate element of the URL query string).  
       
       Returns:  A string for the "thing".  The only processing 
       done is to remove the newline and tab characters from 
       the string.  
    '''
    
    url = f'{BASE_API}/thing?id=' + str(id).strip()
    for (k,v) in args.items():   #  Add the arbitrary (key,value) 
                                 #  pairs passed to the query string.
        url += '&' + str(k) + '=' + str(v)
        
    r = requests.get(url)
    if r.status_code == 404:
        return None
    while r.status_code == 202:
        time.sleep(5)
        r = requests.get(url)
    return re.sub('[\n\t]', '', r.text)


def getBGGCategories(save=False):
    '''Retrieve all of the boardgame categories used by BGG for classification.'''
    
    page = requests.get('https://boardgamegeek.com/browse/boardgamecategory')
    soup = BeautifulSoup(page.text, 'lxml')
    result = []
    for item in soup.findAll('td'):
        anchor = item.find('a')
        if anchor is not None:
            value = anchor.attrs['href'].split('/')[2]
            category = anchor.text
            result.append([value, category])
    result = pd.DataFrame(result, columns=['id','category']).set_index('id')
    
    if save:
        with open(f'{EXTRA_DATA}/boardGameCategories.dill', 'wb') as f:
            dill.dump(result, f)
            
    return result


def getBGGMechanisms(save=False):
    '''Retrieve all of the boardgame mechanisms used by BGG for classification.'''
    
    mechs = []
    page = requests.get('https://boardgamegeek.com/browse/boardgamemechanic')
    soup = BeautifulSoup(re.sub('[\t\n]', '', page.text), 'lxml')
    for item in soup.findAll('td'):
        anchor = item.find('a')
        if anchor:
            c = anchor.attrs['href'].split('/')[2]
            m = anchor.text
            mechs.append((c,m))
    result = pd.DataFrame(mechs, columns=['id', 'mechanism']).set_index('id')
    
    if save:
        with open(f'{EXTRA_DATA}/boardGameMechanisms.dill', 'wb') as f:
            dill.dump(result, f)
            
    return result


def _cleanGameItem(response):
    '''A utility method to take an XML <item> from a BGG response and
       parse to a DataFrame with information about the game.
    '''
    results = dict()
    results['id'] = int(response.attrs['id'])
    try:
        results['name'] = response.find('name').attrs['value']
    except AttributeError:
        results['name'] = np.nan
    results['subtype'] = response.attrs['type']
    #  Clean the description up a little bit here
    try:
        results['description'] = response.find('description').text
        results['description'] = re.sub(r'&#10;|&mdash;|&ndash;', ' ', results['description'])
        results['description'] = re.sub(r'\s+', ' ', results['description'])
        results['description'] = re.sub(r'&quot;', '"', results['description'])
    except AttributeError:
        results['description'] = np.nan
        
    try:
        results['yearpublished'] = int(response.find('yearpublished').attrs['value'])
    except AttributeError:
        results['yearpublished'] = np.nan
    try:
        results['minplayers'] = int(response.find('minplayers').attrs['value'])
    except AttributeError:
        results['minplayers'] = np.nan
    try:
        results['maxplayers'] = int(response.find('maxplayers').attrs['value'])
    except AttributeError:
        results['maxplayers'] = np.nan
    try:
        results['playingtime'] = int(response.find('playingtime').attrs['value'])
    except AttributeError:
        results['playingtime'] = np.nan
    try:
        results['minplaytime'] = int(response.find('minplaytime').attrs['value'])
    except AttributeError:
        results['minplaytime'] = np.nan
    try:
        results['maxplaytime'] = int(response.find('maxplaytime').attrs['value'])
    except AttributeError:
        results['maxplaytime'] = np.nan
    try:
        results['averating'] = float(response.find('average').attrs['value'])
    except AttributeError:
        results['averating'] = np.nan
    try:
        results['bayesaverage'] = float(response.find('bayesaverage').attrs['value'])
    except AttributeError:
        results['bayesaverage'] = np.nan
    try:
        results['bggrank'] = int([r['value'] for r in response.find_all('rank') 
                                  if r.attrs['name'] == 'boardgame'][0])
    except (AttributeError, IndexError, ValueError):
        results['bggrank'] = np.nan
    try:
        results['averageweight'] = float(response.find('averageweight').attrs['value'])
    except AttributeError:
        results['averageweight'] = np.nan
    results['categories'] = [c['value'] for c in response.find_all('link') 
                             if c['type'] == 'boardgamecategory']
    results['mechanics'] = [c['value'] for c in response.find_all('link') 
                            if c['type'] == 'boardgamemechanic']
    results['family'] = [c['value'] for c in response.find_all('link') 
                         if c['type'] == 'boardgamefamily']
    results['designer'] = [c['value'] for c in response.find_all('link') 
                           if c['type'] == 'boardgamedesigner']
    results['artist'] = [c['value'] for c in response.find_all('link') 
                         if c['type'] == 'boardgameartist']
    results['publisher'] = [c['value'] for c in response.find_all('link') 
                            if c['type'] == 'boardgamepublisher']
    results['expansions'] = [int(c['id']) for c in response.find_all('link')
                             if c['type'] == 'boardgameexpansion']
    results['numratings'] = int(response.find('usersrated').attrs['value'])

    return pd.DataFrame([results]).set_index('id')  


def getGame(bggGameId):
    '''A method to get information about one or more games from BGG and
       return that information in the form of a DataFrame.

       Jan 18, 2024  Apparent BUG in BGG API.  Submitting a string with several
       comma-separated values for games seems to result in the description
       of game beyond the first to (not necessarily) be included in the output.
       Hence the more complicated approach to handling more than one game
       in the request below (as well as allowing for int, str, list, range inputs).  
    '''
    if isinstance(bggGameId, int):
        response = BeautifulSoup(get_thing(bggGameId, stats=1), 'lxml')
        if response.find('item'):
            result = [_cleanGameItem(response.find('item'))]
        else:
            return None
    elif isinstance(bggGameId, (str, list, range)):  #  Assumes a comma-separated string
        if isinstance(bggGameId, str):
            games = [int(x) for x in bggGameId.split(',')]
        elif isinstance(bggGameId, range):
            games = list(bggGameId)
        else:
            games = bggGameId

        item_numbers = [int(item.attrs['id']) for item in BeautifulSoup(get_thing(games), 'lxml').find_all('item')]
        time.sleep(1)
        result = []
        for g in item_numbers:
            response = BeautifulSoup(get_thing(g, stats=1), 'lxml')
            if response.find('item'):
                result.append(_cleanGameItem(response.find('item')))
            time.sleep(1)
            
    if result:
        return pd.concat(result)
    else:
        return None





