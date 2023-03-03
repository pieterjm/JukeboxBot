import json
import httpx

class LNbits:
    def __init__(self, protocol, host, admin_adminkey, admin_invoicekey, admin_usrkey):
        self.protocol = protocol
        self.host = host
        self._admin_adminkey = admin_adminkey
        self._admin_invoicekey = admin_invoicekey
        self._admin_usrkey = admin_usrkey

    # get balance
    async def getBalance(self, invoicekey):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.protocol}://{self.host}/api/v1/wallet",
                headers = {"X-Api-Key": invoicekey})
            result = json.loads(response.text)
            return int(result['balance']/1000)
    
    # pay an invoice
    async def payInvoice(self, invoice, adminkey):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.protocol}://{self.host}/api/v1/payments",
                json = {"out": True, "internal": True, "bolt11": invoice },
                headers = {"X-Api-Key": adminkey})
            result = json.loads(response.text)
            if "payment_hash" in result:
                result['result'] = True
            else:
                result['result'] = False
            return result
        
    # creat an lnbits invoice
    async def createInvoice(self, invoicekey, amount, memo):    
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.protocol}://{self.host}/api/v1/payments",
                headers={'X-Api-Key':invoicekey},
                json={
                    "out": False,
                    "amount": amount,
                    "memo": memo,
                    "internal": True
                })        
            return json.loads(response.text)

    # create a user and initial wallet
    async def createUser(self, name):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.protocol}://{self.host}/usermanager/api/v1/users",
                headers={'X-Api-Key':self._admin_invoicekey},
                json={
                    "admin_id": self._admin_usrkey,
                    "wallet_name": name,
                    "user_name": name                    
                })
        user = json.loads(response.text)
        return user['id']

    # delete user and their wallets
    async def deleteUser(self, lnbitsuserid):
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.protocol}://{self.host}/usermanager/api/v1/users/{lnbitsuserid}",
                headers={'X-Api-Key':self._admin_adminkey})
                         
    # create a wallet for a user
    async def createWallet(self, lnbitsuserid, name):
        print("We should not come in the function createWallet")
        return None
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.protocol}://{self.host}/usermanager/api/v1/wallets",
                headers={'X-Api-Key':self._admin_invoicekey},
                json={
                    "user_id": lnbitsuserid,
                    "wallet_name": name,
                    "admin_id": self._admin_usrkey
                })
        wallet = json.loads(response.text)
        return wallet

    # enable extension
    async def enableExtension(self, name, lnbitsuserid):
        # enable extension for user wallet
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.protocol}://{self.host}/usermanager/api/v1/extensions?extension={name}&userid={lnbitsuserid}&active=true",
                headers={'X-Api-Key': self._admin_invoicekey})
            if response.status_code == 200:
                return True
            else:
                return False
        
    # creates LNURLP link
    async def createLnurlp(self, adminkey, json):
        # create lnurlp link
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.protocol}://{self.host}/lnurlp/api/v1/links",
                json=json,
                headers={'X-Api-Key':adminkey})
            result = response.json()
            return result['id']

    # check wether an invoice has been paid. Returns True if paid. Otherwise False
    async def checkInvoice(self,invoicekey,payment_hash):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.protocol}://{self.host}/api/v1/payments/{payment_hash}",
                headers = {"X-Api-Key": invoicekey})
            
            jsobj = json.loads(response.text)
            if jsobj['paid'] == True:
                return True
        return False


    # get all wallets in lnbits
    async def getWallets(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.protocol}://{self.host}/usermanager/api/v1/wallets",
                headers = {"X-Api-Key": self._admin_adminkey})
            return json.loads(response.text)

    # get all wallets in lnbits
    async def getUsers(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.protocol}://{self.host}/usermanager/api/v1/users",
                headers = {"X-Api-Key": self._admin_adminkey})
            return json.loads(response.text)

    # return the wallet for a specific user
    async def getWallet(self, lnbitsuserid):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.protocol}://{self.host}/usermanager/api/v1/wallets/{lnbitsuserid}",
                headers = {"X-Api-Key": self._admin_adminkey})
            result = json.loads(response.text)
            if len(result) > 0:
                return result[0]

        return None
        

