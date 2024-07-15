'''A script to update the existing game information.  Takes a block of indices
and attempts to scrape the game information from BGG.  Then combines this
new information with other info for games that haven't been updated, and
writes out the data to the same dill file.
'''
import time
import dill
import glob
import re

import pandas as pd
import numpy as np 

from datetime import datetime

from constants import GAME_DATA
from api_functions import getGame

WINDOW = 10000
STEP_SIZE = 100

if __name__ == '__main__':
    game_file = sorted(glob.glob(f'{GAME_DATA}/all-to-*.dill'), key=lambda x: int(re.search(r'[\d]+',x).group(0)))[-1]

    with open(game_file, 'rb') as f:
        all_games = dill.load(f)
    
    with open('update_existing_games_start.txt', 'r') as f:
        first = int(f.readline())
    
    to_update = all_games.index[first:first+WINDOW].tolist()
    
    result = []
    start_time = datetime.now()
    print('---------------------------')
    print(f'Start time: {start_time}')
    print(f'{len(all_games)} games in the starting collection.')
    
    for index in range(0, len(to_update), STEP_SIZE):
        games = getGame(to_update[index:index+STEP_SIZE])
        if games is not None:
            result.append(games)
        time.sleep(4)
    
    end_time = datetime.now()
    print(f'End time: {end_time}')
    
    #  Note that we may not quite capture all the data for game indices that were in the original 
    #  all_games DataFrame, hence this is why we are taking the difference between the 
    #  set of indices in the "result" and the portion of "all_games" that we are trying to update.  
    #  We don't want to lose those games for which we might not have gotten a valid result in 
    #  the update portion of this script.  
    if result:
        result = pd.concat(result)
        print(f'Updated {len(result)} games in {end_time - start_time}.')
        new = pd.concat([all_games.loc[list(set(to_update).difference(result.index))], 
                         all_games.iloc[:first], all_games.iloc[first+WINDOW:], 
                         result]).sort_index()
    
        print(f'{len(new)} games in the updated collection.')
        with open(game_file, 'wb') as f:
            dill.dump(new, f)
        
        first += WINDOW
        if first > len(new):
            first = 0
        with open('update_existing_games_start.txt', 'w') as f:
            f.write(str(first))
