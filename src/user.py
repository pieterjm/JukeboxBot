import json

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

                                
class SpotifySettings:
    def __init__(self, tguserid):
        self.userid = tguserid
        self.userkey = f"user:{self.userid}"        
        self.client_secret = None
        self.client_id = None

    def toJson(self):
        data = {
            'telegram_userid': self.userid,
            'client_secret': self.client_secret,
            'client_id': self.client_id
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
    
