import redis
import logging
from lnbits import LNbits
import os

def init(env):
    global environment
    global rds
    global lnbits
    global price
    global fund_max
    global fund_min
    global lnbits_public_host
    global spotify_redirect_uri
    
    # already initialised for this environment
    try:
        if environment == env:
            return True
    except NameError:
        pass

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
        lnbits_public_host='lnbits.wholestack.nl'
        spotify_redirect_uri=os.environ['MY_SPOTIPY_REDIRECT_URI']
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
        spotify_redirect_uri=os.environ['MY_SPOTIPY_REDIRECT_URI']

        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
            )




        return True
    else:
        print("unknown environment")
        quit()
        
