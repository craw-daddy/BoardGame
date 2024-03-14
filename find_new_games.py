'''Designed to search for new games that aren't already in the database, update
the file that contains all games, and update the "guard" value that is used
to search in the future.  Will also copy the new "all games" file to the 
BACKUP directory, and delete all files in the BGG_GAMES directory except for
the latest file.  
'''
import dill
import glob
import re
import time
import shutil
import os

import pandas as pd

from datetime import datetime

from constants import GAME_DATA
from api_functions import getGame

if __name__ == '__main__':
    game_file = sorted(glob.glob(f'{GAME_DATA}/all-to-*.dill'), key=lambda x: int(re.search(r'[\d]+',x).group(0)))[-1]

    with open(game_file, 'rb') as f:
        all_games = dill.load(f)

    with open('find_new_games_guard.txt', 'r') as f:
        limit = int(f.readline())

    rest = pd.Index(range(1, limit)).difference(all_games.index).tolist()
    step_size = 100
    new_found = []
    start = datetime.now()
    print('----------------------')
    print(f'Start time: {start}')

    for index in range(0, len(rest) + 1, step_size):
        games = getGame(rest[index:index+step_size])
        if games is not None:
            new_found.append(games)
        time.sleep(4)

    end = datetime.now()
    print(f'End time: {end}')

    if new_found:
        new_found = pd.concat(new_found)
        print(f'Found {len(new_found)} games in {end - start}')

        new_all = pd.concat([all_games, new_found]).sort_index()
        new_max = new_all.index.max()

        with open(f'{GAME_DATA}/all-to-{new_max}.dill', 'wb') as f:
            dill.dump(new_all, f)
        with open('find_new_games_guard.txt', 'w') as f:
            f.write(str(new_max + 10000))

        all_files = sorted(glob.glob(f'{GAME_DATA}/all-to-*.dill'), key=lambda x: int(re.search(r'[\d]+',x).group(0)))
        shutil.copy(all_files[-1], f'{GAME_DATA}/BACKUPS/')
        for g in all_files[:-1]:
            os.remove(g)
    else:
        print('Found no new games.')
