import redis
from redis import RedisError
import asyncio
from lnbits import LNbits
import settings
import json
import logging
import qrcode
import os

class User:
    def __init__(self, tguserid, tgusername):
        self.userid = tguserid
        self.username = tgusername
        self.rediskey = f"user:{self.userid}"
        self.invoicekey = None
        self.adminkey = None 
        self.lnbitsuserid = None
        self.walletid = None
        self.lnurlp = None
        self.lndhub = None

    def toJson(self):
        userdata = {
            'telegram_userid':self.userid,
            'lnbits_userid':self.lnbitsuserid,
            'telegram_username':self.username,
            'invoicekey':self.invoicekey,
            'adminkey':self.adminkey,
            'walletid':self.walletid,
            'lnurlp':self.lnurlp,
            'lndhub':self.lndhub
        }
        return json.dumps(userdata)
        
    def loadJson(self, data):
        assert(data is not None)
        userdata = json.loads(data)
        assert(userdata is not None)
        assert(userdata['telegram_userid'] == self.userid)
        
        self.invoicekey = userdata['invoicekey']
        self.adminkey = userdata['adminkey']
        self.walletid = userdata['walletid']
        self.lnurlp = userdata['lnurlp']
        self.lndhub = userdata['lndhub']
        self.lnbitsuserid = userdata['lnbits_userid']


# Get/Create a QR code and store in filename
def get_qrcode_filename(data):
    filename = os.path.join(settings.qrcode_path,"{}.png".format(hash(data)))
    if not os.path.isfile(filename):
        img = qrcode.make(data)
        file = open(filename,'wb')
        if file:
            img.save(file)
            file.close()
    return filename
        
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
        
        
