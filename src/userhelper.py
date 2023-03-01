import redis
import asyncio
from lnbits import LNbits
from user import User, SpotifySettings
import settings
import json


async def save_spotify_settings(sps):
    """
    Store spotify settings in Redis
    """
    settings.rds.hget(sps.userkey,"spotify",sps.toJson())
    

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
            return user
        except AssertionError:
            if userdata == b'null':
                settings.logging.warning(f"Null userdata for redis key '{user.rediskey}', resetting userdata")
                userdata = None
            else:
                settings.logging.error(f"Parse error while loading userdata from redis for key '{user.rediskey}'")
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
        
        
