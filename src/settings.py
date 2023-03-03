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
    global port
    
    # set the new environment and fall back to development
    env = None
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

    # webserver port
    port = 7000
    
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
        spotify_redirect_uri=f'{bot_url}/spotifycallback'
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
            os.environ['LNBITS_PROTOCOL'],
            os.environ['LNBITS_HOST'],
            os.environ['LNBITS_ADMINKEY'],
            os.environ['LNBITS_INVOICEKEY'],
            os.environ['LNBITS_USRKEY'])
        bot_url="https://bot.wholestack.nl/"
        spotify_redirect_uri='https://bot.wholestack.nl/spotifycallback' # this must literaly match the config in spotify
        bot_token=os.environ['BOT_TOKEN']
        qrcode_path = '/tmp'
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )



        return True
    else:
        print("unknown environment")
        quit()
        
