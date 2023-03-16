import redis
from redis import RedisError
import asyncio
from lnbits import LNbits
import settings
import json
import logging
import qrcode
import os
import re
from time import time

class User:
    def __init__(self, tguserid: int, tgusername:str = None) -> None:
        self.userid = int(tguserid)
        self.username = tgusername
        self.rediskey = f"user:{self.userid}"
        self.invoicekey = None
        self.adminkey = None 
        self.lnbitsuserid = None
        self.walletid = None
        self.lnurlp = None
        self.lndhub = None

    def toJson(self) -> str:
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
        
    def loadJson(self, data: str) -> None:
        assert(data is not None)
        userdata = json.loads(data)
        assert(userdata is not None)
        if (int(userdata['telegram_userid']) != self.userid):
            logging.error(userdata['telegram_userid'])
            logging.error(self.userid)
            return
        
        if self.username is None:
            self.username = userdata['telegram_username']
        self.invoicekey = userdata['invoicekey']
        self.adminkey = userdata['adminkey']
        self.walletid = userdata['walletid']
        self.lnurlp = userdata['lnurlp']
        self.lndhub = userdata['lndhub']
        for legacy in ['bot.wholestack.nl']:
            if self.lnurlp is not None:
                self.lnurlp = self.lnurlp.replace(legacy,settings.domain)
            if self.lndhub is not None:
                self.lndhub = self.lndhub.replace(legacy,settings.domain)

        self.lnbitsuserid = userdata['lnbits_userid']

# Get/Create a QR code and store in filename
def get_qrcode_filename(data: str) -> str:
    filename = os.path.join(settings.qrcode_path,"{}.png".format(hash(data)))
    if not os.path.isfile(filename):
        img = qrcode.make(data)
        file = open(filename,'wb')
        if file:
            img.save(file)
            file.close()
    return filename


async def get_group_owner(chat_id: int) -> User:
    data = settings.rds.hget(f"group:{chat_id}","owner")
    assert(data is not None)
    
    userid = data.decode('utf-8')

    return await get_or_create_user(userid)    

  
async def delete_group_owner(chat_id: int) -> None:
    data = settings.rds.hdel(f"group:{chat_id}","owner")

async def get_balance(user:User) -> int:
    return await settings.lnbits.getBalance(user.invoicekey)


async def set_group_owner(chat_id: int, userid: int) -> None:
    data = settings.rds.hget(f"group:{chat_id}","owner")
    if data is not None:
        rds_userid = data.decode('utf-8')
        assert(userid == rds_userid)
    data = settings.rds.hset(f"group:{chat_id}","owner",userid)

async def get_funding_lnurl(user: User) -> str:
    """
    Return the funding LNURL
    """
    result = re.search(".*\/([A-Za-z0-9]+)",user.lnurlp)
    if result:
        payid = result.groups()[0]
        details = settings.lnbits.getLnurlp(f"https://{settings.domain}/",user.invoicekey,payid)
        return details['lnurl']
    else:
        return None

async def get_or_create_user(userid: int,username: str = None) -> User:
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
        user.lndhub = f"lndhub://admin:{user.adminkey}@https://{settings.domain}/lndhub/ext/"

        # create lnurlp link
        lnurlpid = await settings.lnbits.createLnurlp(user.adminkey,{
            "description": f"Fund the wallet of @{user.username}",
            "amount": settings.price,
            "max": settings.fund_max,
            "min": settings.fund_min,
            "comment_chars": 0,
            "webhook_url": f"https://{settings.domain}/jukebox/lnbitscallback?userid={user.userid}"
        })
        user.lnurlp = f"https://{settings.domain}/lnurlp/link/{lnurlpid}"    

        # save parameters
        settings.rds.hset(user.rediskey,"userdata",user.toJson())
        
        return user
        
        
