import pandas as pd
import numpy as np
import re
import time
import requests
import dill
import glob
import os

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from constants import BASE_API, USER_DATA, GEEKBUDDIES_DATA

with open('TOKENS/bgg-token.txt', 'r') as f:
    AUTHORIZATION_TOKEN = f.readline().strip()

AUTHORIZATION_DICT = { 'Authorization:' : f'{Bearer {AUTHORIZATION_TOKEN}}'}

#  Filter out some annoying warnings from the latest version of BeautifulSoup
import warnings
from bs4.builder import XMLParsedAsHTMLWarning
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)


def get_collection(bggUserName, cutoff=timedelta(days=7)):
    '''For more information see:  https://boardgamegeek.com/wiki/page/BGG_XML_API2

       Get the board games, and then get the board game 
       expansions.  This is a quirk of the BGG xmlapi2 interface, 
       in that it will incorrectly return the expansions as 
       subtype="boardgame", so we make two calls to get the 
       boardgames, and then the expansions separately.
       
       Returns:  A pandas DataFrame with the designated boardgames 
       in the user's collection, with columns containing 
       information about the games such as the user rating, 
       number of plays, etc.  
       
       Note:  In an effort to reduce traffic, we will check
       if we have previously retrieved the collections within
       the previous week.  If so, we just load and
       return that information, otherwise we will download the
       collection.  
    '''
    bggUserName = bggUserName.strip()
    
    #  Check:  Do we have a previous version of this
    #  collection that was retrieved in the last 7 days (by default)? 
    #  If so, we use that.  Otherwise we get the collection
    #  information from BGG.
    files_to_check = glob.glob(f'{USER_DATA}/{bggUserName}-*.*')
    if files_to_check and (cutoff is not None):
        name = files_to_check[0]
        file_time_stamp = datetime(int(name[-18:-14]), int(name[-14:-12]), 
                            int(name[-12:-10]), int(name[-9:-7]), 
                            int(name[-7:-5]))
        now = datetime.now()
        if (now - file_time_stamp) <= cutoff:
            with open(name, 'rb') as f:
                glist = dill.load(f)
                return glist
    
    result = []
    for game_type in ['excludesubtype=boardgameexpansion', 
                      'subtype=boardgameexpansion']:
        url = f'{BASE_API}/collection?username={bggUserName.strip()}&{game_type}&stats=1'

        r = requests.get(url, headers=AUTHORIZATION_DICT)
        if r.status_code == 404:
            return 'Page not found'
        else:
            while r.status_code == 202:   ##  BGG says that it usually 
                            ## queues requests for a collection, so we 
                            ## must check for a 202 code, and sleep 
                            ## and try again if necessary.  
                time.sleep(12)
                r = requests.get(url, headers=AUTHORIZATION_DICT)
            initial_res = re.sub('[\n\t]', '', r.text)
            #  Check if there was an error from BGG, such as 
            #  an invalid username.  Return the error message if found.  
            error = BeautifulSoup(initial_res, 'lxml').find('error')
            if error:
                return error.text
            result.extend(list(BeautifulSoup(initial_res, 'lxml').find_all('item')))
    
    ##  Handle a special case where someone has not logged their collection, in
    ##  order to avoid certain errors.  
    if len(result) == 0:
        with open(f'{USER_DATA}/______no_collection.dill', 'rb') as f:
            glist = dill.load(f)
        
        now = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
        with open(f'{USER_DATA}/{bggUserName}-{now}.dill', 'wb') as f:
            dill.dump(glist, f)
        
        return glist
        
    glist = []
    for item in result:
        d = dict()
        d['id'] = int(item.attrs['objectid'])
        d['name'] = item.find('name').text
        d['subtype'] = item.attrs['subtype']
        if item.find('yearpublished'):
            d['yearpublished'] = int(item.find('yearpublished').text)

        d.update(item.find("status").attrs)
        d['numplays'] = int(item.find('numplays').text)
        d['lastmodified'] = pd.to_datetime(d['lastmodified'])
        if item.find('rating'):
            d['rating'] = item.find('rating').attrs['value']
            if d['rating'] == 'N/A':
                d['rating'] = np.nan
            else:
                d['rating'] = float(d['rating'])
        else:
            d['rating'] = np.nan
        if item.find('wishlistpriority'):
            d['wishlistpriority'] = item.find('wishlistpriority').text
        else:
            d['wishlistpriority'] = np.nan
        if item.find('comment'):
            d['comment'] = item.find('comment').text
        else:
            d['comment'] = np.nan
        d['username'] = bggUserName
        glist.append(d)
    
    glist = pd.DataFrame(glist).set_index('id').sort_values('name')
    glist = glist[['name', 'subtype', 'yearpublished', 'own', 'prevowned', 'fortrade',
       'want', 'wanttoplay', 'wanttobuy', 'wishlist', 'preordered',
       'lastmodified', 'rating', 'numplays', 'wishlistpriority',
       'comment', 'username']]
    
    for column in ['yearpublished', 'own', 'prevowned', 
                   'fortrade', 'want', 'wanttoplay', 
                   'wanttobuy', 'wishlist', 'preordered', 
                   'numplays', 'wishlistpriority']:
        glist[column] = glist[column].fillna(-1).astype(np.int32)
    
    #  Let's save the collection once we have it 
    #  First remove any previous versions for this user
    files_to_delete = glob.glob(f'{USER_DATA}/{bggUserName}-*.dill')
    for f in files_to_delete:
        os.remove(f)
        
    now = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
    with open(f'{USER_DATA}/{bggUserName}-{now}.dill', 'wb') as f:
        dill.dump(glist, f)
        
    return glist


class User():
    '''A class to denote a BGG user, i.e. identified by their 
       BGG username and a method to gather their collection 
       (assuming it's been put onto BGG.  

       Includes a method to get the list of Geekbuddies of 
       a user, and various other methods to filter the collection.
    '''
    def __init__(self, bggUserName, cutoff=timedelta(days=7)):
        self.bggUserName = bggUserName.strip()
        #  Gather the collection of a user
        self.collection = get_collection(self.bggUserName, cutoff)
        if isinstance(self.collection, str):
            raise ValueError(f'{self.collection}')
            
    def __repr__(self):
        return f'BGG User: {self.bggUserName}'
    
    def refresh_collection(self):
        #  Force an immediate "refresh" of the collection information of a user
        self.collection = get_collection(self.bggUserName, cutoff=timedelta(seconds=0))

    def filter(self, subtype=None,
               own=None, prevowned=None, 
               fortrade=None, 
               want=None, wanttoplay=None, wanttobuy=None, wishlist=None, 
               preordered=None, 
               has_rating=None, has_comment=None,
               wishlistpriority=None, 
               yearpublished=None, published_before=None, published_after=None,
               min_numplays=0, max_numplays=None):
        '''A method to filter the collection based on various 
           criteria and return a new DataFrame with the filtered 
           games.  This does not modify the underlying "collection" 
           information of a user. 
        '''
        result = self.collection.copy()
        
        if isinstance(subtype, str) and subtype in ['boardgame', 'boardgameexpansion']:
            result = result[result['subtype'] == subtype].copy()
            
        for option, flag in [('own', own),
                             ('prevowned', prevowned), 
                             ('fortrade', fortrade), 
                             ('want', want), 
                             ('wanttoplay', wanttoplay),
                             ('wanttobuy', wanttobuy), 
                             ('wishlist', wishlist), 
                             ('preordered', preordered)]:
            if isinstance(flag, (int, bool)):
                result = result[result[option] == int(flag)].copy()
        
        for option, flag in [('rating', has_rating),
                             ('comment', has_comment)]:
            if isinstance(flag, (int, bool)):
                if flag:
                    result = result[~result[option].isna()].copy()
                else:
                    result = result[result[option].isna()].copy()

        if isinstance(wishlistpriority, int):
            result = result[result['wishlistpriority'] == wishlistpriority].copy()

        if isinstance(yearpublished, int):
            result = result[result['yearpublished'] == yearpublished].copy()
        if isinstance(published_before, int):
            result = result[result['yearpublished'] < published_before].copy()
        if isinstance(published_after, int):
            result = result[result['yearpublished'] > published_after] .copy()       

        if isinstance(min_numplays, (int, float)):
            result = result[result['numplays'] >= min_numplays].copy()
        if isinstance(max_numplays, (int, float)):
            result = result[result['numplays'] <= max_numplays].copy()
            
        return result.copy()
    
    def own(self):
        return self.filter(own=True)
    
    def prevowned(self):
        return self.filter(prevowned=True)
    
    def fortrade(self):
        return self.filter(fortrade=True)
    
    def want(self):
        return self.filter(want=True)
    
    def wanttoplay(self):
        return self.filter(wanttoplay=True)
    
    def wanttobuy(self):
        return self.filter(wanttobuy=True)
    
    def wishlist(self):
        return self.filter(wishlist=True)
    
    def preordered(self):
        return self.filter(preordered=True)

    def has_rating(self):
        return self.filter(has_rating=True)
    
    def has_comment(self):
        return self.filter(has_comment=True)
    
    def base(self):
        return self.filter(subtype='boardgame')
    
    def expansion(self):
        return self.filter(subtype='boardgameexpansion')
    
    def geekbuddies(self, cutoff=timedelta(days=7)):
        '''Get the list of Geekbuddies of a user.  This 
           assumes that the user has at most 1000 Geekbuddies 
           (which is the current maximum number returned 
           from the API call, without additional pagination, 
           which I am not doing here).
        '''

        #  Check to see if this has been retrieved recently, and, if so,
        #  just load and return that data.  
        files_to_check = glob.glob(f'{GEEKBUDDIES_DATA}/{self.bggUserName}-*.*')
        if files_to_check and (cutoff is not None):
            name = files_to_check[0]
            file_time_stamp = datetime(int(name[-18:-14]), int(name[-14:-12]), 
                                int(name[-12:-10]), int(name[-9:-7]), 
                                int(name[-7:-5]))
            now = datetime.now()
            if (now - file_time_stamp) <= cutoff:
                with open(name, 'rb') as f:
                    buddies = dill.load(f)
                return buddies

        #  Otherwise, make the call to retrieve and store this information.
        url = f'{BASE_API}/users?name={self.bggUserName}&buddies=1'
        result = requests.get(url, headers=AUTHORIZATION_DICT)
        error = BeautifulSoup(result.text, 'lxml').find('error')
        if error:
            return f'{error.text}'
        
        buddies = [(item.get('name'), item.get('id')) for item in BeautifulSoup(result.text, features='lxml').find_all('buddy')]

        #  Let's save the list of geekbuddies once we have it 
        #  First remove any previous versions for this user
        files_to_delete = glob.glob(f'{GEEKBUDDIES_DATA}/{self.bggUserName}-*.dill')
        for f in files_to_delete:
            os.remove(f)
        
        now = datetime.strftime(datetime.now(), '%Y%m%d-%H%M')
        with open(f'{GEEKBUDDIES_DATA}/{self.bggUserName}-{now}.dill', 'wb') as f:
            dill.dump(buddies, f)
            
        return buddies

