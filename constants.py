BASE_API = 'https://boardgamegeek.com/xmlapi2'

USER_DATA = 'USERS'
GEEKBUDDIES_DATA = 'GEEKBUDDIES'
GAME_DATA = 'BGG_GAMES'
EXTRA_DATA = 'EXTRA_DATA'

SLEEP_DELAY = 12 

#  Set up the "Authorization dictionary" in order to pass credentials
#  into BGG, as required.  
#  See https://boardgamegeek.com/wiki/page/XML_API_Terms_of_Use#
#  Import this dictionary as needed, in order to pass the authorization token
#  in using the "requests" package.  
with open('TOKENS/bgg-token.txt', 'r') as f:
    AUTHORIZATION_TOKEN = f.readline().strip()

AUTHORIZATION_DICT = {'Authorization' :f'Bearer {AUTHORIZATION_TOKEN}'}

