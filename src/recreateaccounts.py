import userhelper
import settings
import json
import redis
import asyncio
from userhelper import User

settings.init()


for userkey in settings.rds.scan_iter("user:*"):
    userdata = settings.rds.hget(userkey,"userdata")

    if userdata is not None:
        userdata = json.loads(userdata)

        tgusername = userdata['telegram_username']
        tguserid = userdata['telegram_userid']

        if userdata['lnurlp'] is None:
            print(tgusername,tguserid)
            print(userdata['lnurlp'])

            settings.rds.hdel(userkey,"userdata")

            user = asyncio.run(userhelper.get_or_create_user(tguserid, tgusername))

            print(user.lnurlp)
