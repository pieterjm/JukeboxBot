#!/usr/bin/env python
import os
import base64
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import re
import httpx
import random
import string
import shutil
from time import time


BOT_TEXT_QUERY_CANCELED="Search canceled"
BOT_TEXT_QUERY="Choose from the following"
BOT_TEXT_SPOTIFY_UNAVAILABLE="Control unavailabel at the moment"


telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']
telegram_token = os.environ['TELEGRAM_TOKEN']
status_json = os.environ['STATUS_JSON']
lnbits_host=os.environ['LNBITS_HOST']
lnbits_api_key=os.environ['LNBITS_API_KEY']
lnbits_callback_url = os.environ['LNBITS_CALLBACK_URL']

price = int(os.environ['REQUEST_PRICE'])
LIST_OF_ADMINS = json.loads(os.environ['LIST_OF_ADMINS'])
lnbits_lnurlp_path = os.environ['LNBITS_LNURLP_PATH']
open_orders_path = os.environ['OPEN_ORDERS_PATH']
paid_orders_path = os.environ['PAID_ORDERS_PATH']
done_orders_path = os.environ['DONE_ORDERS_PATH']

spotify_allowed = True
telegram_now_id = 0 #os.environ['TELEGRAM_NOW_PLAYING_ID']


# initializie spotipy
scope = 'user-read-currently-playing,user-modify-playback-state,user-read-playback-state'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
track_history = []


# Enable logging
logging.basicConfig(
#    filename="logfile_{time}.dat".format(time=time()),
    filename="logfile.dat",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# start command handler, returns help information
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """You can use one of the following commands:

 /add to search for tracks. Searches can be refined using statements such as 'artist:'.
 /queue to view the list of upcoming tracks. 
 /history view the list of tracks that were played recently
"""           
    message = await context.bot.send_message(chat_id=update.message.chat_id,text=text)
    context.job_queue.run_once(delete_message, 30, data={'message':message})
    await update.message.delete()

# construct the track title from a Spotify track item
def getTrackTitle(item):
    return "{artist} - {track}".format(artist=item['artists'][0]['name'],track=item['name'])

# get or set the price
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global price
    text = "Track history:\n"
    
    
    for i in range(min(20,len(track_history)) - 1,-1,-1):
        item = track_history[i]
        text += " {title}\n".format(title=item)            

    message = await context.bot.send_message(chat_id=update.message.chat_id,text=text)    
    context.job_queue.run_once(delete_message, 20, data={'message':message})
    await update.message.delete()

# get or set the price
async def play_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global price
    chat_id = update.message.chat_id
    if str(chat_id) != str(telegram_chat_id):
        logging.info(chat_id)
        return


    if update.message.text == '/price':
        message = await context.bot.send_message(chat_id=chat_id,text="Current track request price is {price} sats".format(price=price))
        context.job_queue.run_once(delete_message, 20, data={'message':message})        
        await update.message.delete()
    else:        
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            await update.message.delete()
            return
        
        newprice = update.message.text.split(' ',1)
        if len(newprice) > 1:
            newprice = newprice[1]
            if newprice.isdigit():
                newprice = int(newprice)
            else:
                await update.message.delete()    
                message = await context.bot.send_message(chat_id=chat_id,text="Use /price <sats>. Price is either 0 or 10 or more sats.")        
                context.job_queue.run_once(delete_message, 5, data={'message':message})
                return
            
            if newprice >= 10 or newprice == 0:
                price = newprice
                await update.message.delete()                                         
                message = await context.bot.send_message(chat_id=chat_id,text="Updating price to {price} sats".format(price=price))

                await message.delete()
                message = await context.bot.send_message(chat_id=chat_id,text="Current track request price is {price} sats".format(price=price))
                context.job_queue.run_once(delete_message, 20, data={'message':message})        
            else:
                await update.message.delete()    
                message = await context.bot.send_message(text="Use /price <sats>. Price is either 0 or 10 or more sats.")        
                context.job_queue.run_once(delete_message, 5, data={'message':message})
       


# disable spotify 
async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    if str(chat_id) != str(telegram_chat_id):
        return
    
    user_id = update.effective_user.id
    if user_id in LIST_OF_ADMINS:
        spotify_allowed = False
        message = await context.bot.send_message(chat_id=telegram_chat_id,text="Music control disabled")
        context.job_queue.run_once(delete_message, 20, data={'message':message})

    # delete the original message
    await update.message.delete()

# enable spotify 
async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    if str(chat_id) != str(telegram_chat_id):
        return

    user_id = update.effective_user.id
    if user_id in LIST_OF_ADMINS:
        spotify_allowed = True
        message = await context.bot.send_message(chat_id=telegram_chat_id,text="Music control enabled")
        context.job_queue.run_once(delete_message, 20, data={'message':message})

    await update.message.delete()
    
# cancel unused search dialogs
async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    try:
        #message = await context.job.data['message'].edit_reply_markup(reply_markup=None)
        #if ( message.text == BOT_TEXT_QUERY ):
        #await context.job.data['message'].de;leedit_text('Auto closed') #BOT_TEXT_QUERY_CANCELED)
        if 'message' in context.job.data:
            await context.job.data['message'].delete()
        if 'messages' in context.job.data:
            for i in range(len(context.job.data['messages'])):
                await context.job.data['messages'][i].delete()
    finally:
        return

    
# search command handler
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # return if not in the correct chat
    chat_id = update.message.chat_id

    # return ifspotify is not allowed
    if spotify_allowed == False:
        return

    searchstr = update.message.text.split(' ',1)
    if len(searchstr) > 1:
        searchstr = searchstr[1]
    else:
        message = await context.bot.send_message(chat_id=update.message.chat_id,text="Use the /add command to search for tracks and add them to the playlist. Enter the name of the artist and/or the song title after the /add command and select a track from the results. For example: \n/add rage against the machine killing in the name\n/add 7th element\n")
        context.job_queue.run_once(delete_message, 30, data={'message':message})
        await update.message.delete()
        return

    # search for tracks
    result = sp.search(searchstr)
    
    # create a list of max five buttons, each with a unique song title
    if len(result['tracks']['items']) > 0:
        tracktitles  = {}
        button_list = []
        for item in result['tracks']['items']:            
            title = getTrackTitle(item)
            if title not in tracktitles:
                tracktitles[title] = 1
                button_list.append([InlineKeyboardButton(title, callback_data = "{id}:{uri}".format(id=update.effective_user.id,uri=item['uri']))])

                # max five suggestions
                if len(tracktitles) == 5:
                    break

        # Add a cancel button to the list
        button_list.append([InlineKeyboardButton('Cancel', callback_data = "{id}:CANCEL".format(id=update.effective_user.id))])

        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Results for '{query}'".format(query=searchstr),
            reply_markup=InlineKeyboardMarkup(button_list))

        # start a job to kill the search window after 30 seconds if not used
        context.job_queue.run_once(delete_message, 30, data={'message':message})
    else:
        message = await context.bot.send_message(chat_id=update.message.chat_id,text="No results for '{query}'".format(query=searchstr))
        context.job_queue.run_once(delete_message, 10, data={'message':message})

        
    # delete the original message
    await update.message.delete()


# display the play queue
async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # return ifspotify is not allowed
    if spotify_allowed == False:
        return

    # get the current track
    track = sp.current_user_playing_track()
    title = "Nothing is playing at the moment"    
    if track:                    
        title = "🎵 {title} 🎵".format(title=getTrackTitle(track['item']))
    
    # query the queue 
    result = sp.queue()
    
    text = ""
    for i in range(min(10,len(result['queue']))):
        item = result['queue'][i]       
        text += " {count}. {title}\n".format(count=(i+1),title=getTrackTitle(item))

    if len(text) == 0:
        text = title + "\nNo items in queue."
    else:
        text = title + "\nUpcoming tracks:\n" + text
            
    await update.message.delete()
    message = await context.bot.send_message(chat_id=update.message.chat_id,text=text)    
    context.job_queue.run_once(delete_message, 15, data={'message':message})

# create a payment link
async def lnbits_create_lnurlp(orderid,title,price):
    global lnbits_callback_url, lnbits_host, lnbits_api_key
    # create lightning invoice and display the QR code
    payment_data = {
        "description": title,
        "amount": price,
        "max": price,
        "min": price,
        "comment_chars": 0,
        "webhook_url": "{url}?orderid={orderid}".format(url=lnbits_callback_url,orderid=orderid)
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://{host}/lnurlp/api/v1/links".format(host=lnbits_host),
            json=payment_data,
            headers={'X-Api-Key':lnbits_api_key})
        result = response.json()
        #print(result)
        return result['id']

    raise Exception("Did not get id from lnbits")

        
        
# This function displays the current track being played
# the current track is updated in the same telegram message
# if no message is configured, a new message is created, which is then updated
# this callback reschedules itself to update the current playing track
async def callback_spotify(context: ContextTypes.DEFAULT_TYPE):
    global telegram_chat_id, telegram_now_id, track_history
    next_check = 60
    
    try:
        track = sp.current_user_playing_track()
        brinkietitle = "Nothing is playing at the moment"
            
        if track:
            title = getTrackTitle(track['item'])
            if title not in track_history:
                track_history.append(title)
            while len(track_history) > 20:
                track_history.pop(0)
                
            brinkietitle = "🎵 {title} 🎵".format(title=title)

            # update status to file
            file = open(status_json,'w')
            if file:
                status = {
                    'artist': track['item']['artists'][0]['name'],
                    'track': track['item']['name'],
                    'title': title
                }
                file.write(json.dumps(status))
                file.close()
                
            # make an educated guess when to check again
            next_check  = ( track['item']['duration_ms'] - track['progress_ms'] ) / 1000
            if next_check > 60:
                next_check = 60
            if next_check < 10:
                next_check = 10


        # send or update the current track message
        if telegram_now_id != 0:
            try:
                await context.bot.editMessageText(brinkietitle,chat_id=telegram_chat_id,message_id=telegram_now_id)
            except:
                pass
        else:
            try: 
                message = await context.bot.send_message(text=title,chat_id=telegram_chat_id)
                telegram_now_id = message.id
                await context.bot.pin_chat_message(chat_id=telegram_chat_id, message_id=telegram_now_id)
                 
                logging.info("Created new messsage with id: {}".format(telegram_now_id))
            except:
                pass
            
                    
    finally:
        context.job_queue.run_once(callback_spotify, next_check)

#callback for button presses
async def callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global price, paymentlinks, telegram_chat_id
    if spotify_allowed == False:
        await query.edit_message_text(text=BOT_TEXT_QUERY_SPOTIFY_UNAVAILABLE)
        return

    query = update.callback_query
    userid, qdata = query.data.split(':',1)        
    
    # only the user that requested the track can select a track
    if str(userid) != str(update.effective_user.id):
        logging.info("Avoiding real click")
        return

    # CallbackQueries need to be answered, even if no notification to the user is needed    
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery    
    await query.answer()
        
    if qdata == 'CANCEL':
        message = await query.edit_message_text(text=BOT_TEXT_QUERY_CANCELED)
        context.job_queue.run_once(delete_message, 5, data={'message':message})    
    else:
        
        
        order = {
            'spotify_uri': qdata,
            'title': getTrackTitle(sp.track(qdata)),
            'userid': update.effective_user.id,
            'price': price,
            'username': update.effective_user.username,
            'chat_id': update.effective_chat.id,
            'messageid': query.message.id
        }
        
        if price == 0:
            try:
                sp.add_to_queue(order['spotify_uri'])
                
                await context.bot.send_message(chat_id=telegram_chat_id,text="@{username} added '{title}' to the queue".format(**order))
                if update.effective_chat.id != telegram_chat_id:
                    await context.bot.send_message(chat_id=update.effective_chat.id,text="Added '{title}' to the queue".format(**order))
                
            except spotipy.exceptions.SpotifyException:
                await context.bot.send_message(chat_id=telegram_chat_id,text="Could not add '{title}' to the queue. Player unavailable.".format(**order))
                if update.effective_chat.id != telegram_chat_id:
                    await context.bot.send_message(chat_id=update.effective_chat.id,text="Could not add '{title}' to the queue. Player unavailable.".format(**order))
                
            finally:
                await query.delete_message()
                return


        orderid = ''.join(random.choice(string.ascii_letters) for i in range(8))
        order['id'] = orderid
        
        lnbits_id = await lnbits_create_lnurlp(order['id'],order['title'],order['price'])
        order['lnbits_id'] = lnbits_id
        order['paylink'] = "https://{host}{path}{id}".format(id=order['lnbits_id'],host=lnbits_host,path=lnbits_lnurlp_path)        

        
        await query.edit_message_text("@{username} add '{title}'?".format(**order))
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Pay {price} sats".format(**order),url=order['paylink'])
            ]
        ]))
        with open(os.path.join(open_orders_path,"{id}.json".format(**order)), 'w') as outfile:
            json.dump(order, outfile)
        
        
        #await query.delete_message()


# do the actual payment processing
async def process_payment(context: ContextTypes.DEFAULT_TYPE,filename: str):
    global done_orders_path
    
    with open(filename) as file:
        order = json.load(file)
        
        try:
            sp.add_to_queue(order['spotify_uri'])
        
            try:
                shutil.move(filename,done_orders_path)
            except shutil.Error:
                os.unlink(fname)
                pass
                    
            try:
                await context.bot.delete_message(order['chat_id'],order['messageid'])
            except:
                pass
            await context.bot.send_message(chat_id=telegram_chat_id,text="@{username} added '{title}' to the queue".format(**order))
            if str(telegram_chat_id) != str(order['chat_id']):
                await context.bot.send_message(chat_id=order['chat_id'],text="Added '{title}' to the queue".format(**order))
                        
            async with httpx.AsyncClient() as client:
                await client.delete(
                    "https://{host}/lnurlp/api/v1/links/{payid}".format(host=lnbits_host,payid=order['lnbits_id']),
                    headers={'X-Api-Key':lnbits_api_key})
            
        except spotipy.exceptions.SpotifyException:
            logging.info("Player is not available")
            await context.bot.send_message(
                chat_id=order['chat_id'],
                text="Could not add '{title}' to the queue. Player unavailable.".format(**order))                    


# callback that checks when a payment is made
async def callback_payments(context: ContextTypes.DEFAULT_TYPE):
    global telegram_chat_id
    
    files = os.listdir(paid_orders_path)
    for filename in files:
        fname = os.path.join(paid_orders_path, filename)
        if os.path.isfile(fname):
            logging.info("New payment {}".format(filename))
            await process_payment(context,fname)


# callback that checks when a payment is made
async def callback_stuckpayments(context: ContextTypes.DEFAULT_TYPE):
    global lnbits_host, lnbits_api_key
    
    # return if no open orders
    files = os.listdir(open_orders_path)
    if len(files) == 0:
        return
    
    # make HTTP call to lnbits to check payment status
    lnbits_ids = []
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://{host}/api/v1/payments".format(host=lnbits_host),
            headers={'X-Api-Key':lnbits_api_key})
        result = response.json()
        for item in result:
            if item['pending'] == True:
                continue
            
            if 'extra' not in item:
                continue
            
            if 'tag' not in item['extra']:
                continue
            
            if item['extra']['tag'] != 'lnurlp':
                continue
                    
            lnbits_ids.append(item['extra']['link'])

    for filename in files:
        fname = os.path.join(open_orders_path, filename)
        if os.path.isfile(fname):
            logging.info("New payment {}".format(filename))
            
            with open(fname) as file:
                order = json.load(file)
                if order['lnbits_id'] in lnbits_ids:
                    shutil.move(fname,paid_orders_path)

                    


                
if __name__ == "__main__":
    
    """Run bot."""
    #config = uvicorn.Config("main:app", port=6000, log_level="info")
    #server = uvicorn.Server(config)
    
    application = Application.builder().token(telegram_token).build()    
    # Create the Application and pass it your bot's token.
    

    # on different commands - answer in Telegram

    # add spotify to the job queue

    
    # Run the bot until the user presses Ctrl-C
    
    application.add_handler(CommandHandler(["start", "help","info","correcthorsebatterystaple"], start))
    application.add_handler(CommandHandler(['add','play','adr','ade','adf','adc','adx','ads','ads'], play))
    application.add_handler(CommandHandler('queue', queue))
    application.add_handler(CommandHandler('price', play_price))
    application.add_handler(CommandHandler('enable', enable))
    application.add_handler(CommandHandler('disable', disable))
    application.add_handler(CommandHandler('history', history))

    application.add_handler(CallbackQueryHandler(callback_button))
    application.job_queue.run_once(callback_spotify, 1)
    application.job_queue.run_repeating(callback_payments, 5)
    application.job_queue.run_repeating(callback_stuckpayments, 30)


    application.run_polling()


