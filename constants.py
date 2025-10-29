BASE_API = 'https://www.boardgamegeek.com/xmlapi2'

USER_DATA = 'USERS'
GEEKBUDDIES_DATA = 'GEEKBUDDIES'
GAME_DATA = 'BGG_GAMES'
EXTRA_DATA = 'EXTRA_DATA'

SLEEP_DELAY = 12 

with open('TOKENS/bgg-token.txt', 'r') as f:
    AUTHORIZATION_TOKEN = f.readline().strip()

AUTHORIZATION_DICT = {'Authorization:' :f'Bearer {AUTHORIZATION_TOKEN}'}

