import redis
from redis import RedisError
import asyncio
import settings
import json
import logging
from spotipy import CacheHandler
import spotipy
from spotipy.oauth2 import SpotifyOAuth

class SpotifySettings:
    def __init__(self, tguserid):
        self.userid = tguserid
        self.chatid = None
        self.userkey = f"user:{self.userid}"        
        self.client_secret = None
        self.client_id = None
        self.token = None

    def toJson(self):
        data = {
            'telegram_userid': self.userid,
            'client_secret': self.client_secret,
            'client_id': self.client_id,
            'token': self.token,
            'chatid': self.chatid
        }
        return json.dumps(data)

    def loadJson(self, data):
        assert(data is not None)
        obj = json.loads(data)
        assert(obj is not None)
        assert(obj['telegram_userid'] == self.userid)

        if 'client_secret' in obj:
            self.client_secret = obj['client_secret']

        if 'client_id' in obj:
            self.client_id = obj['client_id']

        if 'token' in obj:
            self.token = obj['token']
    
        if 'chatid' in obj:
            self.chatid = obj['token']
            
class CacheJukeboxHandler(CacheHandler):
    """
    This cache handler keeps track of spotify auth data and is stored in the redis database per group so that multiple authorisations can be active at the same time
    """    
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.key = f"spotify_token:{self.chat_id}"

    def get_cached_token(self):
        logging.info("Obtain cached token")
        token_info = None
    
        try:
            token_info = settings.rds.get(self.key)
            if token_info:
                return json.loads(token_info)
        except RedisError as e:
            logging.warning('Error getting token from cache: ' + str(e))       

        return token_info


    def save_token_to_cache(self, token_info):
        logging.info("saving token to cache")
        try:
            settings.rds.set(self.key, json.dumps(token_info))
        except RedisError as e:
            logging.warning('Error saving token to cache: ' + str(e))



def add_to_queue(sp, spotify_uri_list):
    for uri in spotify_uri_list:
        sp.add_to_queue(uri)            


# construct the track title from a Spotify track item
def get_track_title(item):
    return "{artist} - {track}".format(artist=item['artists'][0]['name'],track=item['name'])
            
async def create_auth_manager(chat_id, client_id, client_secret):
    return SpotifyOAuth(
        scope='user-read-currently-playing,user-modify-playback-state,user-read-playback-state',
        client_secret=client_secret,
        client_id=client_id,
        redirect_uri=settings.spotify_redirect_uri,
        show_dialog=False,
        open_browser=False,        
        cache_handler=CacheJukeboxHandler(chat_id))
            
async def init_auth_manager(chat_id, client_id, client_secret):
    """
    Initialize a spotify auth manager for a specific group
    """
    data = {
        'chat_id': chat_id,
        'client_id': client_id,
        'client_secret': client_secret
    }
    settings.rds.set(f"authmanager:{chat_id}", json.dumps(data))

    return await create_auth_manager(chat_id, client_id, client_secret)
        
        
async def get_auth_manager(chat_id):
    """
    Create a spotify auth manager for a specific group
    """
    data = settings.rds.get(f"authmanager:{chat_id}")
    if data is None:
        return None

    data = json.loads(data)
    return await create_auth_manager(data['chat_id'], data['client_id'], data['client_secret'])

            
async def save_spotify_settings(sps):
    """
    Store spotify settings in Redis
    """
    settings.rds.hset(sps.userkey,"spotify",sps.toJson())
    

async def get_spotify_settings(userid):
    """
    Get the spotify settings for this user
    """
    sps = SpotifySettings(userid)    
    data = settings.rds.hget(sps.userkey,"spotify")
    if data is not None:
        sps.loadJson(data)
    return sps
