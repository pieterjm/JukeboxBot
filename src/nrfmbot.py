!/usr/bin/env python
import os
import base64
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, MessageEntity, ChatMember
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, CallbackContext, MessageHandler, filters
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import re
import httpx
import random
import string
import shutil
import redis
from lnbits import LNbits
from time import time
import qrcode

rds = redis.Redis()

BOT_TEXT_QUERY_CANCELED="Search canceled"
BOT_TEXT_QUERY="Choose from the following"
BOT_TEXT_SPOTIFY_UNAVAILABLE="Control unavailabel at the moment"


telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']
telegram_token = os.environ['TELEGRAM_TOKEN']
status_json = os.environ['STATUS_JSON']
lnbits_host=os.environ['LNBITS_HOST']
lnbits_public_host=os.environ['LNBITS_PUBLIC_HOST']
lnbits_protocol=os.environ['LNBITS_PROTOCOL']
lnbits_api_key=os.environ['LNBITS_API_KEY']
lnbits_admin_id=os.environ['LNBITS_ADMIN_ID']
lnbits_invoice_key=os.environ['LNBITS_INVOICE_KEY']
lnbits_callback_url = os.environ['LNBITS_CALLBACK_URL']
qrcode_path = os.environ['QRCODE_PATH']


tip = 7
price = int(os.environ['REQUEST_PRICE'])
LIST_OF_ADMINS = json.loads(os.environ['LIST_OF_ADMINS'])
lnbits_lnurlp_path = os.environ['LNBITS_LNURLP_PATH']
open_orders_path = os.environ['OPEN_ORDERS_PATH']
paid_orders_path = os.environ['PAID_ORDERS_PATH']
done_orders_path = os.environ['DONE_ORDERS_PATH']
expired_orders_path = os.environ['EXPIRED_ORDERS_PATH']


spotify_allowed = True
telegram_now_id = 0 #os.environ['TELEGRAM_NOW_PLAYING_ID']

lnbits = LNbits(lnbits_protocol,lnbits_host)

# initializie spotipy
scope = 'user-read-currently-playing,user-modify-playback-state,user-read-playback-state' # playlist-modify-private'

am = SpotifyOAuth(
    scope=scope,
    client_secret=os.environ['MY_SPOTIPY_CLIENT_SECRET'],
    client_id=os.environ['MY_SPOTIPY_CLIENT_ID'],
    redirect_uri=os.environ['MY_SPOTIPY_REDIRECT_URI'],
    show_dialog=False,
    open_browser=False
)

#print(am.get_authorize_url())
#quit()

sp = spotipy.Spotify(auth_manager=am)

# Enable logging
logging.basicConfig(
#    filename="logfile_{time}.dat".format(time=time()),
    filename="logfile.dat",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Create a QR code and store in filename
def get_qrcode_image_filename(data):
    filename = os.path.join(qrcode_path,"{}.png".format(hash(data)))
    if not os.path.isfile(filename):
        img = qrcode.make(data)
        file = open(filename,'wb')
        if file:
            img.save(file)
            file.close()

    return filename
    
# pay and invoice
async def pay_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = re.search("/pay_invoice\s+(lnbc[a-z0-9]+)\s*$",update.message.text)
    if result is None:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Unknown lightning invoice format. Should start with 'lnbc'.")
        return
        
    
    payment_request = result.groups()[0]
    
    payment_result = await lnbits.payinvoice(payment_request, await get_user_adminkey(update.effective_user.id))
    if payment_result['result'] == True:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Payment succes.")
    else:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            parse_mode='HTML',
            text="Payment failed. <pre>{detail}</pre>".format(detail=payment_result['detail']))
        
    
    

# Connect spotify player
async def connect_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(update.message.chat.type)
    if update.message.chat.type == "private":
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Send this command in the group where you want to connect the bot")
        return

    admin = False
    for member in await context.bot.get_chat_administrators(update.message.chat.id):
        if member.user.id == update.effective_user.id and member.status in ['administrator','creator']:
            admin = True
            
    if admin == False:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="You are not an admin in this chat.")
        return

    bot_me = await context.bot.get_me()
    message = await context.bot.send_message(
        chat_id=update.message.chat_id,
        text="I'm sending instructions in the private chat.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
        ]))


    message = await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Clicking on the button below will take you to Spotify where you can grant the bot the authorisation to control the player.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Authorize player",url=am.get_authorize_url())]
        ]))

    
    
    
# get current balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    if str(update.message.chat_id) == str(telegram_chat_id):
        bot_me = await context.bot.get_me()
        print(f"https://t.me/{bot_me.username}")
    
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Like keeping your mnenomic seedphrase offline, it is better to query your balance in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

        context.job_queue.run_once(delete_message, 60, data={'message':message})
        # direct the user to their private chat
        return

    balance = await lnbits.getbalance(await get_user_invoicekey(update.effective_user.id))
    
    message = await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=f"Your balance is {balance} sats.")

    await update.message.delete()


# get lndhub link
async def link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    if str(update.message.chat_id) == str(telegram_chat_id):
        bot_me = await context.bot.get_me()
        print(f"https://t.me/{bot_me.username}")
    
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Like keeping your mnenomic seedphrase offline, it is better to request your lndhub link in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

        context.job_queue.run_once(delete_message, 60, data={'message':message})
        # direct the user to their private chat
        return

    lndhublink = await get_user_lndhub(update.effective_user.id)
    filename = get_qrcode_image_filename(lndhublink)
    with open(filename,'rb') as file:
        message = await context.bot.send_photo(
            update.message.chat_id,
            file,
            caption=f"Scan this QR code with an lndhub compatible wallet like BlueWallet or Zeus. Your lndhub link is:\n<pre>{lndhublink}</pre>",
            parse_mode='HTML')

    await update.message.delete()    

# give sats to user
async def deejay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.delete()

    
# start command handler, returns help information
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """You can use one of the following commands:

 /info /help /startare all result in this output
 /add to search for tracks. Searches can be refined using statements such as 'artist:'.
 /queue to view the list of upcoming tracks. 
 /history view the list of tracks that were played recently
 /dj <amount> to share some of your sats balance with another user. Use this command in a reply to them.

You can also chat in private with me to do stuff like viewing your balance.

 /balance shows your balance.
 /fund can be used to add sats to your balance. While you can pay for each track, you can also add some sats in advance.
 /link provides an lndhub URL so that you can connect BlueWallet or Zeus to your wallet in the bot. That also makes it possible to withdraw/add funds.

The NOSTR pubkey of NoderunnersFM is: npub1ua6fxn9ktc4jncanf79jzvklgjftcdrt5etverwzzg0lgpmg3hsq2gh6v6
"""           
    message = await context.bot.send_message(chat_id=update.message.chat_id,text=text)
    context.job_queue.run_once(delete_message, 60, data={'message':message})
    await update.message.delete()

# construct the track title from a Spotify track item
def getTrackTitle(item):
    return "{artist} - {track}".format(artist=item['artists'][0]['name'],track=item['name'])

# get or set the price
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global price
    text = "Track history:\n"

    historykey = f"history:{telegram_chat_id}"
    for i in range(0, min(20,rds.llen(historykey))):
        title = rds.lindex(historykey, i).decode('utf-8')
        text += f"{title}\n"            

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
        userid = update.effective_user.id
        if userid not in LIST_OF_ADMINS:
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
    
    userid = update.effective_user.id
    if userid in LIST_OF_ADMINS:
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

    userid = update.effective_user.id
    if userid in LIST_OF_ADMINS:
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

    # check if the search string is a spotify URL
    match = re.search('https://open.spotify.com/playlist/([A-Za-z0-9]+).*$',searchstr)
    if (match):
        playlistid = match.groups()[0]
        result = sp.playlist(playlistid,fields=['name'])
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"@{update.effective_user.username} wants you to play tracks from the '{result['name']}' playlist.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"Pay {price} sats for a random track", callback_data = f"0:PLAYRANDOM:{playlistid}:1"),
            ]]))

        
#        message = await context.bot.send_message(
#            chat_id=update.message.chat_id,
#            text=f"How many random tracks of the '{result['name']}' playlist do you want to add?",
#            reply_markup=InlineKeyboardMarkup([[
#                InlineKeyboardButton("1", callback_data = f"{update.effective_user.id}:PLAYRANDOM:{playlistid}:1"),
#                InlineKeyboardButton("2", callback_data = f"{update.effective_user.id}:PLAYRANDOM:{playlistid}:2"),
#                InlineKeyboardButton("3", callback_data = f"{update.effective_user.id}:PLAYRANDOM:{playlistid}:3"),
#                InlineKeyboardButton("4", callback_data = f"{update.effective_user.id}:PLAYRANDOM:{playlistid}:4"),
#                InlineKeyboardButton("5", callback_data = f"{update.effective_user.id}:PLAYRANDOM:{playlistid}:6")
#            ]]))
        
        # start a job to kill the message  after 30 seconds if not used
        context.job_queue.run_once(delete_message, 180, data={'message':message})
    
        # delete the original message
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

            historykey = f"history:{telegram_chat_id}"
            rds_title = rds.lindex(historykey,0)
            if rds_title is None:
                rds.lpush(historykey,title)
            else:
                rds_title = rds_title.decode('utf-8')
                if rds_title != title:
                    rds.lpush(historykey,title)
                    
                if rds.llen(historykey) > 100:
                    rds.rpop(historykey)


            rds.hset(f"lastplayed:{telegram_chat_id}",title,int(time()))
            
                    
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
            if next_check > 90:
                next_check = 90
            if next_check < 5:
                next_check = 5


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
async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lnurlp = await get_user_lnurlp(update.effective_user.id,update.effective_user.username)
    
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Click on the button to fund the wallet of @{update.effective_user.username}. Anyone can spend!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Fund sats",url=user_lnurlp)]
            ]))
    context.job_queue.run_once(delete_message, 60, data={'message':message})        
    
    await update.message.delete()

# add track(s) to the play queue
# verify that the track has not been played before in the last hour(s) or so
async def add_to_queue(context: ContextTypes.DEFAULT_TYPE, spotify_uri_list, username, chat_id):
    text = ""
    if len(spotify_uri_list) == 1:
        text=f"@{username} added '{getTrackTitle(sp.track(spotify_uri_list[0]))}' to the queue"
    else:
        text = f"@{username} added to the queue:\n"
        for item in spotify_uri_list:
            text += f" {getTrackTitle(sp.track(item))}\n"
            sp.add_to_queue(item)            

    # send a message
    await context.bot.send_message(chat_id=chat_id,text=text)

    # add to playlist
    # this does not yet work, 
    # sp.playlist_add_items('30LZGM5LM95Wv3qggybvQF', spotify_uri_list)
    

    

async def callback_check_invoice(context: ContextTypes.DEFAULT_TYPE):
    paid = False
    
    # check if the invoice has been paid
    if paid == False and await lnbits.check_invoice(context.job.data['invoicekey'],context.job.data['payment_hash']) == True:        
        paid = True


    if paid == False:
        payment_result = await lnbits.payinvoice(context.job.data['payment_request'],context.job.data['adminkey'])
        if payment_result['result'] == True:
            paid = True

    if paid == True:
        await add_to_queue(context,context.job.data['spotify_uri_list'],context.job.data['username'],context.job.data['chat_id'])
        await context.bot.delete_message(context.job.data['chat_id'],context.job.data['message_id'])
        return

    
    
    if context.job.data['timeout'] <= 0:
        await context.bot.delete_message(context.job.data['chat_id'],context.job.data['message_id'])
        return
    else:
        # reschedule job
        context.job.data['timeout'] -= 5
        title = context.job.data['title']
        

        balance = await lnbits.getbalance(await get_user_invoicekey(context.job.data['userid']))
        amount = context.job.data['amount_to_pay'] - balance
        
        # update message with updated amount
        try:
            await context.bot.edit_message_text(
                text=f"@{context.job.data['username']} add '{title}' to the play queue?\n\nYou have to fund your balance with at least <b>{amount}</b> sats to add '{title}' to the queue.\n\nSats paid in excess will not be lost and are added to your balance to pay for additional tracks.",
                chat_id=context.job.data['chat_id'],
                message_id=context.job.data['message_id'],
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"Open payment link",url=context.job.data['lnurlp']),
                    InlineKeyboardButton('Cancel', callback_data = "{id}:CANCEL".format(id=context.job.data['userid']))
                ]]))
        except:
            pass
            
        
        context.job_queue.run_once(callback_check_invoice, 5, data=context.job.data)

    
#callback for button presses
async def callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if spotify_allowed == False:
        await query.edit_message_text(text=BOT_TEXT_QUERY_SPOTIFY_UNAVAILABLE)
        return

    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed    
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery    
    await query.answer()
    

    spotify_uri_list = []
    
    userid, qdata = query.data.split(':',1)        
    
    # only the user that requested the track can select a track   
    if int(userid) != 0 and str(userid) != str(update.effective_user.id):
        logging.info("Avoiding real click")
        return

    if qdata == 'CANCEL':
        message = await query.edit_message_text(text=BOT_TEXT_QUERY_CANCELED)
        context.job_queue.run_once(delete_message, 5, data={'message':message})
        return
    elif qdata.startswith("PLAYRANDOM"):
        (command, playlistid, amount) = qdata.split(':')
    
        result = sp.playlist_items(playlistid,offset=0,limit=1)
        llen = result['total'] 
        
        amount = int(amount)
        if result['total'] < amount:
            amount = result['total']

        # get a random item from the list
        # if item not already in playlist
        # if item not in recent lastplayed
        # how to prevent a short list
        # llen = length of the list
        # if item in recent last played llen - 1
        # if item added to playlist llen - 1
        # if llen == 0, no more items to get
        # what is no items could be added at all
        idxs = random.sample(range(0,result['total']),amount)
        for idx in idxs:
            result = sp.playlist_items(playlistid,offset=idx,limit=1)
            for item in result['items']:
                spotify_uri_list.append(item['track']['uri'])            
    else:
        # add a single track to the list
        # TODO validate the input
        spotify_uri_list = [qdata]
        await query.delete_message()

    payment_required = True
    amount_to_pay = int(price * len(spotify_uri_list))
    
    if amount_to_pay == 0:
        payment_required = False

    # if no payment required
    if payment_required == False:
        await add_to_queue(context,spotify_uri_list,update.effective_user.username,telegram_chat_id)
        await query.delete_message()
        return


        
    # create a title for the order
    title = getTrackTitle(sp.track(spotify_uri_list[0]))
    if len(spotify_uri_list) > 1:
        title = "random tracks from a playlist"

    # create an invoice
    invoice = await lnbits.createinvoice(lnbits_invoice_key,amount_to_pay,title)
    
    # get the user wallet
    user_adminkey = await get_user_adminkey(update.effective_user.id)
    
    # pay the invoice
    payment_result = await lnbits.payinvoice(invoice['payment_request'],user_adminkey)
    if payment_result['result'] == True:
        await add_to_queue(context,spotify_uri_list,update.effective_user.username,update.effective_chat.id)
        return

    # get payment link for the user
    user_lnurlp = await get_user_lnurlp(update.effective_user.id,update.effective_user.username)

    # get balance for user
    balance = await lnbits.getbalance(await get_user_invoicekey(update.effective_user.id))
        
    # we failed paying the invoice, popup the lnurlp
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"@{update.effective_user.username} add '{title}' to the play queue?\n\nYou have to fund your balance with at least <b>{amount_to_pay - balance}</b> sats to add '{title}' to the queue.\n\nSats paid in excess will not be lost and are added to your balance to pay for additional tracks.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Open payment link",url=user_lnurlp),
            InlineKeyboardButton('Cancel', callback_data = "{id}:CANCEL".format(id=update.effective_user.id))
        ]]))
    

    # create a job to check the invoice
    context.job_queue.run_once(callback_check_invoice, 5, data={
        'payment_request':invoice['payment_request'],
        'payment_hash': invoice['payment_hash'],
        'invoicekey': lnbits_invoice_key,
        'adminkey':user_adminkey,
        'spotify_uri_list':spotify_uri_list,
        'message_id':message.id,
        'amount_to_pay': amount_to_pay,
        'title': title,
        'chat_id':update.effective_chat.id,
        'username':update.effective_user.username,
        'userid':update.effective_user.id,
        'timeout': 180,
        'lnurlp':user_lnurlp
        })
        
                           
if __name__ == "__main__":
    
    """Run bot."""
    application = Application.builder().token(telegram_token).build()    
    # Create the Application and pass it your bot's token.
    

    # on different commands - answer in Telegram

    # add spotify to the job queue

    
    # Run the bot until the user presses Ctrl-C
    
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler(['add'], play))
    application.add_handler(CommandHandler('queue', queue))
    application.add_handler(CommandHandler('price', play_price))
    application.add_handler(CommandHandler('enable', enable))
    application.add_handler(CommandHandler('disable', disable))
    application.add_handler(CommandHandler('history', history))
    application.add_handler(CommandHandler('dj', deejay))
    application.add_handler(CommandHandler('fund',fund))
    application.add_handler(CommandHandler('link',link))
    application.add_handler(CommandHandler('balance', balance))
    application.add_handler(CommandHandler('connect_player', connect_player))
    application.add_handler(CommandHandler('pay_invoice', pay_invoice))
    #application.add_handler(MessageHandler(~ filters.Chat(int(telegram_chat_id)),callback_message))

    application.add_handler(CallbackQueryHandler(callback_button))
    application.job_queue.run_once(callback_spotify, 1)
    #application.job_queue.run_repeating(callback_payments, 5)
    #application.job_queue.run_repeating(callback_stuckpayments, 30)


    application.run_polling()


