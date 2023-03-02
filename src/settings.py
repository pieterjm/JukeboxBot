import redis
import logging
from lnbits import LNbits
import os
import random
import string

def init():
    global environment
    global rds
    global lnbits
    global price
    global fund_max
    global fund_min
    global lnbits_public_host
    global spotify_redirect_uri
    global bot_url
    global bot_token
    global delete_message_timeout_short
    global delete_message_timeout_medium
    global delete_message_timeout_long
    global secret_token
    global qrcode_path
    
    # set the new environment and fall back to development
    env = 'development'
    if 'JUKEBOX_ENV' in os.environ:
        env = os.environ['JUKEBOX_ENV']
        
    # already initialised for this environment
    try:
        if environment == env:
            return True
    except NameError:
        pass

    # short time for deleting messages in seconds
    delete_message_timeout_short = 10
    delete_message_timeout_medium = 60
    delete_message_timeout_long = 300

    # set secret token for telegram
    secret_token = "".join(random.sample(string.ascii_letters,12))

    environment = env
    if env == 'production':
        rds = redis.Redis(db=0)
        price = os.environ['REQUEST_PRICE']
        fund_max = 100 * price
        fund_min = price
        lnbits = LNbits(
            os.environ['LNBITS_PROTOCOL'],
            os.environ['LNBITS_HOST'],
            os.environ['LNBITS_ADMINKEY'],
            os.environ['LNBITS_INVOICEKEY'],
            os.environ['LNBITS_USRKEY'])
        bot_url="https://bot.wholestack.nl/"
        lnbits_public_host='lnbits.wholestack.nl'
        spotify_redirect_uri=os.environ['MY_SPOTIPY_REDIRECT_URI']
        bot_token = os.environ['BOT_TOKEN']
        qrcode_path= '/tmp'

        logging.basicConfig(
            filename="logfile_{time}.dat".format(time=time()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
            )



        return True
    elif env == 'development':
        price = 21
        fund_max = 100 * price
        fund_min = price
        rds = redis.Redis(db=2)
        lnbits_public_host='lnbits.wholestack.nl'
        lnbits = LNbits(
            'https',
            lnbits_public_host,
            'f6f99487036447618a0de0e2fcc1720a',
            'a46583204eda467fb4a52c5b8e9e8b59',            
            '47ddeb21c32a46ac82c7eacb482020cb')
        spotify_redirect_uri='http://localhost:8080/'
        bot_url="https://bot.wholestack.nl/"
        bot_token="6163071450:AAGRq9Jo9eAgYo6EepzsT0SmWSA3snVR9ns"
        qrcode_path = '/tmp'
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )




        return True
    else:
        print("unknown environment")
        quit()
        
