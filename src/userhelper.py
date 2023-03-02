import redis
from redis import RedisError
import asyncio
from lnbits import LNbits
from user import User, SpotifySettings
import settings
import json
import logging
from spotipy import CacheHandler
import spotipy
from spotipy.oauth2 import SpotifyOAuth

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
        
async def get_or_create_user(userid,username):
    """
    Get or create a user in redis and lnbits and return the user object
    """    
    user = User(userid,username)
        
    userdata = settings.rds.hget(user.rediskey,"userdata")

    if userdata is not None:
        try:
            user.loadJson(userdata)
            logging.info("Got the fast path for retrieving the user")
            return user
        except AssertionError:
            if userdata == b'null':
                logging.warning(f"Null userdata for redis key '{user.rediskey}', resetting userdata")
                userdata = None
            else:
                logging.error(f"Parse error while loading userdata from redis for key '{user.rediskey}'")
                raise
    
    # no entry in redis, get user and wallet from lnbits 
    if userdata is None:
        # maybe it is an existing user
        lnusers = await settings.lnbits.getUsers()
        for lnuser in lnusers:
            if lnuser['name'] == user.rediskey:
                user.lnbitsuserid = lnuser['id']
                break

        # create if not existing
        if user.lnbitsuserid is None:
            user.lnbitsuserid = await settings.lnbits.createUser(user.rediskey)

        # get or create wallet if not existing
        wallet = await settings.lnbits.getWallet(user.lnbitsuserid)
        if wallet is None:
            wallet = await settings.lnbits.createWallet(user.lnbitsuserid,user.rediskey)

        # copy parameters
        user.invoicekey = wallet['inkey']
        user.adminkey = wallet['adminkey']
        user.walletid = wallet['id']

        # enable extensions for user
        await settings.lnbits.enableExtension("lnurlp",user.lnbitsuserid)
        await settings.lnbits.enableExtension("lndhub",user.lnbitsuserid)
    
        # create lndhub link
        user.lndhub = f"lndhub://admin:{user.adminkey}@https://lnbits.wholestack.nl/lndhub/ext/"

        # create lnurlp link
        lnurlpid = await settings.lnbits.createLnurlp(user.adminkey,{
            "description": f"Fund the wallet of @{user.username}",
            "amount": settings.price,
            "max": settings.fund_max,
            "min": settings.fund_min,
            "comment_chars": 0,
            "webhook_url": f"https://bot.wholestack.nl/lnbitscallback?userid={user.userid}"
        })
        user.lnurlp = f"https://lnbits.wholestack.nl/lnurlp/link/{lnurlpid}"

    

        # save parameters
        settings.rds.hset(user.rediskey,"userdata",user.toJson())
        
        return user
        
        
