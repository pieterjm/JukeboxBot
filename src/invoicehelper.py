import redis
from redis import RedisError
import asyncio
from lnbits import LNbits
import settings
import json
import logging
import qrcode
import os
from time import time

class Invoice:
    def __init__(self, payment_hash, payment_request = None):
        self.payment_hash = payment_hash
        self.payment_request = payment_request
        self.rediskey = f"invoice:{self.payment_hash}"
        self.recipient = None
        self.user = None
        self.spotify_uri_list = None
        self.title = None
        self.chat_id = None
        self.message_id = None
    
    def toJson(self):
        userdata = {
            'payment_hash':self.payment_hash,
            'payment_request':self.payment_request,
            'recipient': {
                'userid': self.recipient.userid,
                'username': self.recipient.username
            },
            'user': {
                'id': self.user.userid,
                'username': self.user.username
            },
            'spotify_uri_list': self.spotify_uri_list,
            'title': self.invoice_title,
            'chat_id': self.chat_id,
            'message_id': self.message_id
    
        }
        return json.dumps(userdata)
        
    def loadJson(self, data):
        assert(data is not None)
        data = json.loads(data)
        assert(data is not None)
        assert(data['payment_hash'] == self.payment_hash)

        if self.payment_request is not None:
            assert(self.payment_request == data['payment_request'])
        else:
            self.payment_request = data['payment_request']

        udata = data['recipient']
        self.recipient = User(udata['userid'],udata['username'])
        udata = data['user']
        self.user = User(udata['userid'],udata['username'])
        
        self.spotify_uri_list = data['spotify_uri_list']
        self.invoice_title = data['title']
        self.chat_id = data['chat_id']
        self.message_id = data['message_id']

# Get/Create a QR code and store in filename
async def create_invoice(user, amount, memo):
    lnbits_invoice = await settings.lnbits.createInvoice(user.invoicekey,amount,memo)
    invoice = Invoice(lnbits_invoice['payment_hash'],lnbits_invoice['payment_request'])
    return invoice


async def pay_invoice(user, invoice):
    assert(invoice is not None)
    assert(user it not None)

    result = settings.lnbits.payInvoice(invoice.payment_request,user.adminkey)

    if result['result'] == True:
        return {
            'result': True,
            'detail': 'Payment success'
        }
    else:
        return {
            'result': False,
            'detail': 'Payment failed'
        }

async def save_invoice(invoice):
    settings.rds.set(invoice.rediskey,invoice.toJson())
            
async def delete_invoice(invoice):
    data = settings.rds.get(invoice.rediskey)
    if data is None:
        return True
    
    settings.rds.delete(invoice.rediskey)
    return True
    
async def invoice_paid(invoice):
    result = await settings.lnbits.checkInvoice(invoice.recipient.invoiceky,invoice.payment_hash)context.job.data['payment_hash'])
    if result == True:
        await delete_invoice(invoice)
        return True
    else:
        return False


async def get_invoice(payment_hash):
    """
    load invoice from redis
    """
    rediskey = f"invoice:{payment_hash}"
    data = settings.rds.get(rediskey)
    if data is None:
        return None

    data = json.loads(data)

    invoice = Invoice(data['payment_hash'],data['payment_request'])
    invoice.loadJson(data)
    
    return invoice

