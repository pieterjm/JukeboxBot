#!/usr/bin/env python
import asyncio
import re
import os
import base64
import json
from time import time
import html
import logging
from dataclasses import dataclass
from http import HTTPStatus
import redis

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

import spotipy
from spotipy.oauth2 import SpotifyOAuth


from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ExtBot,
    TypeHandler,
)

# import all local stuff
from lnbits import LNbits
import userhelper
from userhelper import User
import spotifyhelper
from spotifyhelper import SpotifySettings, CacheJukeboxHandler
import settings


settings.init()

@dataclass
class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""
    user_id: int
    payload: str

class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `WebhookUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)

# delete telegram messages
# This function is used in callbacks to enable the deletion of messages from users or the bot itself after some time
async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'message' in context.job.data:
            await context.job.data['message'].delete()
        if 'messages' in context.job.data:
            for i in range(len(context.job.data['messages'])):
                await context.job.data['messages'][i].delete()
    finally:
        return

    
# start command handler, returns help information
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """You can use one of the following commands:

 /start and /help both result in this output
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
    # send the message
    message = await context.bot.send_message(chat_id=update.message.chat_id,text=text)

    # only create a callback to delete the message when not in a private chat
    if update.message.chat.type != "private":
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})

    # delete the command from the user
    await update.message.delete()    


# get the current balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # do not show balance in other than private chats
    if update.message.chat.type != "private":
        bot_me = await context.bot.get_me()
        print(f"https://t.me/{bot_me.username}")
        
        # direct the user to their private chat
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Like keeping your mnenomic seedphrase offline, it is better to query your balance in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})
        return

    # we're in a private chat now
    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)
            
    # get the balance from LNbits
    balance = await settings.lnbits.getBalance(user.invoicekey)

    # create a message with the balance
    message = await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=f"Your balance is {balance} sats.")

    # delete the command from the user
    await update.message.delete()

# Connect a spotify player to the bot, the connect command
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # get spotify settings for the user
    sps = await spotifyhelper.get_spotify_settings(update.effective_user.id)    
    
    # this command has to be execute from within a group
    if update.message.chat.type == "private":
        # check that client_id is not None
        if sps.client_id is None:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"No spotify ClientID set Use the /setclientid command to enter this id")        
        else:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"ClientID is set to {sps.client_id}")
            
        # check that client secret is not None
        if sps.client_secret is None:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"No Spotify Client Secret set. Use the /setclientsecret command to enter this secret")        
        else:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Client secret is set.")

        # hint the user for the connect command
        if sps.client_id is not None and sps.client_secret is not None:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Both client_id and client_secret are set. Execute the /connect command in the group that you want to connect to the bot")

        return

    # the user should be admin in the group
    admin = False
    for member in await context.bot.get_chat_administrators(update.message.chat.id):
        if member.user.id == update.effective_user.id and member.status in ['administrator','creator']:
            admin = True            
    if admin == False:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="You are not an admin in this chat.")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})
        return

    # send message in group to go to private chat
    bot_me = await context.bot.get_me()

    # if both variables are not none, ask the user to authorize
    if sps.client_id is not None and sps.client_secret is not None:

        auth_manager = await spotifyhelper.init_auth_manager(update.message.chat_id,sps.client_id,sps.client_secret)

        # send instructions in the group
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="I'm sending instructions in the private chat.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})

        state = base64.b64encode(f"{update.message.chat_id}:{update.effective_user.id}".encode('ascii')).decode('ascii')
        
        # send a message to the private chat of the bot
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Clicking on the button below will take you to Spotify where you can grant the bot the authorisation to control the player.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Authorize player",url=auth_manager.get_authorize_url(state=state))]
            ]))
    else:
        # send a message that configuration is required
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Additional configuration is required, execute this command in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

            
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})

# display the play queue
async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type == "private":
        return
    
    # get an auth managher, if no auth manager is available, dump a message
    await spotifyhelper.get_auth_manager(update.message.chat_id)
    if auth_manager is None:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            parse_mode='HTML',
            text="Bot not connected to player. The admin should perform the /connect command to authorize the bot.")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})        
        return

    # create spotify instance
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
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
    context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})

        
# connect a spotify player to the bot, the setclient secret and set client id commands
async def spotify_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type != "private":
        bot_me = await context.bot.get_me()
        print(f"https://t.me/{bot_me.username}")
        
        # direct the user to their private chat
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Like keeping your mnenomic seedphrase offline, it is better to perform these actions in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})
        return
    
    # get spotify settings for the user
    sps = await spotifyhelper.get_spotify_settings(update.effective_user.id)

    result = re.search("/(setclientid|setclientsecret)\s+([a-z0-9]+)\s*$",update.message.text)
    if result is None:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Incorrect usage. ")
        return

    # after validation
    command = result.groups()[0]
    value = result.groups()[1]

    bSave = False
    if command == 'setclientid':
        sps.client_id = value
        bSave = True
        
    if command == 'setclientsecret':
        sps.client_secret = value
        bSave = True
        
    if bSave == True:
        await spotifyhelper.save_spotify_settings(sps)
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Settings updated. Type /connect for current settings and instructions.")


# fund the wallet of the user
async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Click on the button to fund the wallet of @{user.username}.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Fund sats",url=user.lnurlp)]
            ]))
    
    context.job_queue.run_once(delete_message, settings.delete_message_timeout_long, data={'message':message})

    # delete the original message
    await update.message.delete()

# view the history of recently played tracks
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type == "private":
        return
    
    # get an auth managher, if no auth manager is available, dump a message
    await spotifyhelper.get_auth_manager(update.message.chat_id)
    if auth_manager is None:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            parse_mode='HTML',
            text="Bot not connected to player. The admin should perform the /connect command to authorize the bot.")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})        
        return

    # create spotify instance
    sp = spotipy.Spotify(auth_manager=auth_manager)
        
    text = "Track history:\n"
    historykey = f"history:{telegram_chat_id}"
    for i in range(0, min(20,rds.llen(historykey))):
        title = rds.lindex(historykey, i).decode('utf-8')
        text += f"{title}\n"            

    message = await context.bot.send_message(chat_id=update.message.chat_id,text=text)    
    context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})
    await update.message.delete()

    
    
# get lndhub link for user
async def link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # create a message tyo do this in a private chat
    if update.message.chat.type != "private":
        bot_me = await context.bot.get_me()
        print(f"https://t.me/{bot_me.username}")
    
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Like keeping your mnenomic seedphrase offline, it is better to request your lndhub link in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})
        return

    # we're in a private chat now
    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)

    # create QR code for the link    
    filename = userhelper.get_qrcode_filename(lndhublink)
    with open(filename,'rb') as file:
        message = await context.bot.send_photo(
            update.message.chat_id,
            file,
            caption=f"Scan this QR code with an lndhub compatible wallet like BlueWallet or Zeus. Your lndhub link is:\n<pre>{user.lndhublink}</pre>",
            parse_mode='HTML')

    # delete the original command
    await update.message.delete()    

# pay a lightning invoice
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = re.search("/pay\s+(lnbc[a-z0-9]+)\s*$",update.message.text)
    if result is None:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Unknown lightning invoice format. Should start with 'lnbc'.")
        return

    # get the patment request from the regular expression
    payment_request = result.groups()[0]

    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)
    
    # pay the invoice
    payment_result = await settings.lnbits.payInvoice(payment_request,user.adminkey)
    if payment_result['result'] == True:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Payment succes.")
    else:
        # TODO, filter on the result detail. It may contain sensitive information
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            parse_mode='HTML',
            text="Payment failed.")

# search for a track
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function searches for tracks in spotify and createas a list of tracks to play
    If a playlist URL is provided, that playlist is used
    This function only works in a group chat
    """
    if update.message.chat.type == "private":
        return
    
    # get an auth managher, if no auth manager is available, dump a message
    auth_manager = await spotifyhelper.get_auth_manager(update.message.chat_id)
    if auth_manager is None:
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            parse_mode='HTML',
            text="Bot not connected to player. The admin should perform the /connect command to authorize the bot.")
        return

    # create spotify instance
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    # validate the search string
    searchstr = update.message.text.split(' ',1)
    if len(searchstr) > 1:
        searchstr = searchstr[1]
    else:
        message = await context.bot.send_message(chat_id=update.message.chat_id,text="Use the /add command to search for tracks and add them to the playlist. Enter the name of the artist and/or the song title after the /add command and select a track from the results. For example: \n/add rage against the machine killing in the name\n/add 7th element\n")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})
        await update.message.delete()
        return

    # check if the search string is a spotify URL
    match = re.search('https://open.spotify.com/playlist/([A-Za-z0-9]+).*$',searchstr)
    if (match):
        playlistid = match.groups()[0]
        result = sp.playlist(playlistid,fields=['name'])
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"@{update.effective_user.username} suggests to play tracks from the '{result['name']}' playlist.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"Pay {price} sats for a random track", callback_data = f"0:PLAYRANDOM:{playlistid}"),
            ]]))

        # start a job to kill the message  after 30 seconds if not used
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_long, data={'message':message})
    
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
                button_list.append([InlineKeyboardButton(title, callback_data = f"{update.effective_user.id}:{item['uri']}")])
                
                # max five suggestions
                if len(tracktitles) == 5:
                    break

        # Add a cancel button to the list
        button_list.append([InlineKeyboardButton('Cancel', callback_data = f"{update.effective_user.id}:CANCEL")])

        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Results for '{searchstr}'",
            reply_markup=InlineKeyboardMarkup(button_list))

        # start a job to kill the search window after 30 seconds if not used
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})
    else:
        message = await context.bot.send_message(chat_id=update.message.chat_id,text=f"No results for '{searchstr}'")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})

        
    # delete the original message
    await update.message.delete()

# send sats from user to user
async def zap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send sats from one user to another
    """
    # verify that this is not a private chat
    # verify that the message is a reply
    if update.message.reply_to_message is None or update.message.chat.type != "private":
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"The /zap of /dj command only works in a group chat as a reply to another user. If no amount is specified, the price for a track, {settings.price} is sent.")
        await update.message.delete()
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})        
        return

    # parse the amount to be paid
    amount = setings.price
    result = re.search("/[a-z]+(\s+([0-9]+))?\s*$",update.message.text)
    if result is not None:
        amount = result.groups()[1]
        if amount is None:
            amount = 21
        else:
            amount = int(amount)
            
    # get the user that is sending the sats and check his balance
    sender = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)
    balance = await settings.lnbits.getBalance(user.invoicekey)

    if balance < amount:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Insufficient balance, /fund your balance first to /zap or /dj another user.")
        await update.message.delete()
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})        
    
    # get the receiving user and create an invoice
    recipient = await userhelper.get_or_create_user(update.message.reply_to_message.from_user.id,update.message.reply_to_message.from_user.username)
    invoice = await settings.lnbits.createInvoice(recipient.invoicekey,amount,f"Zap from @{sender.username}")

    # pay the invoice
    result = await settings.lnbits.payInvoice(invoice["payment_request"],sender.adminkey)
    if result['result'] == True:
        # send message in the group chat
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"@{sender.username} zapped {amount} sats to @{recipient.username}.")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_medium, data={'message':message})        

        # send a message in the private chat
        message = await context.bot.send_message(
            chat_id=recipient.userid,
            text=f"Got zapped {amount} sats by @{recipient.username}.")
        
        # delete the message
        await update.message.delete()
    else:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Zap failed. Sorry.")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})        

        # delete the message
        await update.message.delete()


# periodic check for a paid invoice            
async def callback_check_invoice(context: ContextTypes.DEFAULT_TYPE):
    
    # check if the invoice has been paid
    if await settings.lnbits.checkInvoice(settings.lnbits._admin_invoicekey,context.job.data['payment_hash']) == true:
        auth_manager = await spotify_helper.get_auth_manager(context.job.data['chat_id'])
        if auth_manager is None:
            logging.error("No auth manager after succesfull payment")
            return

        # add to the queue and inform others
        sp = spotipy.Spotify(auth_manager=auth_manager)
        for uri in spotify_uri_list:
            sp.add_to_queue(item)            
        await context.bot.send_message(
            chat_id=context.job.data['chat_id'],
            parse_mode='HTML',
            text=f"@{context.job.data['username']} added {context.job.data['invoice_title']} to the queue.")
        await context.bot.send_message(
            chat_id=context.job.data['user_id'],
            parse_mode='HTML',
            text=f"You paid {context.job.data['amount_to_pay']} sats for {context.job.data['invoice_title']}.")

        # delete the payment request message
        await context.bot.delete_message(context.job.data['chat_id'],context.job.data['message_id'])
        return

    # not yet paid, reschedule job or forget about it after some time
    if context.job.data['timeout'] <= 0:
        await context.bot.delete_message(context.job.data['chat_id'],context.job.data['message_id'])
    else:
        interval = 5
        context.job.data['timeout'] -= interval            
        context.job_queue.run_once(callback_check_invoice, interval, data=context.job.data)
    
            
#callback for button presses
async def callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This functions handles all button presses that are fed back into the application
    """
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed    
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery    
    await query.answer()
    
    # parse the callback data.
    # TODO: Should convert this into an access reference map pattern
    userid, command = query.data.split(':',1)        

    # only the user that requested the track can select a track
    # or when the userid is explicitly set to 0
    if int(userid) != 0 and str(userid) != str(update.effective_user.id):
        logging.debug("Avoiding real click")
        return
    
    # process the various commands
    # cancel command
    if command == 'CANCEL':
        """
        Cancel just deletes the message
        """
        await query.delete_message()
        return

    # the commands from here on modify a list of tracks to be queue
    # and we have to check hat we have spotify available
    # get an auth managher, if no auth manager is available, dump a message
    await spotifyhelper.get_auth_manager(update.effective_chat.id)
    if auth_manager is None:
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            parse_mode='HTML',
            text="Bot not connected to player. The admin should perform the /connect command to authorize the bot.")
        context.job_queue.run_once(delete_message, settings.delete_message_timeout_short, data={'message':message})        
        return

    # create spotify instance
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # TODO: verify that player is available, otherwise it has no use to queue a track
                      
    # Play a random track from a playlist
    spotify_uri_list = []            
    if command.startswith("PLAYRANDOM"):
        (command, playlistid) = command.split(':')    
        result = sp.playlist_items(playlistid,offset=0,limit=1)
        idxs = random.sample(range(0,result['total']),1)
        for idx in idxs:    
            result = sp.playlist_items(playlistid,offset=idx,limit=1)
            for item in result['items']:
                spotify_uri_list.append(item['track']['uri'])            
    else:
        # add a single track to the list
        spotify_uri_list = [command]
        await query.delete_message()

    # validate payment conditions
    payment_required = True
    amount_to_pay = int(price * len(spotify_uri_list))    
    if amount_to_pay == 0:
        payment_required = False
            
    # if no payment required, add the tracks to the queue one by one
    if payment_required == False:
        for uri in spotify_uri_list:
            sp.add_to_queue(item)            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                parse_mode='HTML',
                text=f"@{update.effective_user.username} added '{spotifyhelper.get_track_title(sp.track(item))}' to the queue.")
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                parse_mode='HTML',
                text=f"You added '{spotifyhelper.get_track_title(sp.track(item))}' to the queue.")
                
    # create an invoice title
    invoice_title = f"'{spotify_uri_list[0]}'"
    for i in range(1,len(spotify_uri_list)):
        title += f",'{spotify_uri_list[i]}'"

    # create the invoice 
    invoice = await settings.lnbits.createInvoice(settings.lnbits._admin_invoicekey,amount_to_pay,invoice_title)

    # get the user wallet and try to pay the invoice
    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)

    # pay the invoice
    result = await settings.lnbits.payInvoice(invoice['payment_request'],user.adminkey)

    # if payment success
    if payment_result['result'] == True:
        for uri in spotify_uri_list:
            sp.add_to_queue(item)            
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            parse_mode='HTML',
            text=f"@{update.effective_user.username} added {invoicetitle} to the queue.")
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            parse_mode='HTML',
            text=f"You paid {amount_to_pay} sats for {invoice_title}.")
        return
            
    # if payment fails, either fund the wallet or pay the invoice            
    # get balance for user
    balance = await settings.lnbits.getBalance(user.invoicekey)
        
    # we failed paying the invoice, popup the lnurlp
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"@{update.effective_user.username} add '{invoice_title}' to the queue?\n\nThen pay the invoice sats.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Pay {amount_to_pay} sats",url=f"https://bot.wholestack.nl/redirect?url=lightning:{invoice['payment_request']}"),
            InlineKeyboardButton('Cancel', callback_data = "{id}:CANCEL".format(id=update.effective_user.id))
        ]]))
    

    # create a job to check the invoice
    context.job_queue.run_once(callback_check_invoice, 5, data={
        'payment_hash': invoice['payment_hash'],
        'user_id':update.effective_user.id,
        'username': update.effective_user.username,
        'invoice_title': invoice_title,
        'spotify_uri_list': spotify_uri_list,
        'message_id': message.id,
        'chat_id': chat.id,
        'timeout': 180        
        })

async def webhook_update(update: WebhookUpdate, context: CustomContext) -> None:
    """Callback that handles the custom updates."""
    chat_member = await context.bot.get_chat_member(chat_id=update.user_id, user_id=update.user_id)
    payloads = context.user_data.setdefault("payloads", [])
    payloads.append(update.payload)
    combined_payloads = "</code>\n• <code>".join(payloads)
    text = (
        f"The user {chat_member.user.mention_html()} has sent a new payload. "
        f"So far they have sent the following payloads: \n\n• <code>{combined_payloads}</code>"
    )
    await context.bot.send_message(
        chat_id=context.bot_data["admin_chat_id"], text=text, parse_mode=ParseMode.HTML
    )

                  
async def main() -> None:
    """Set up the application and a custom webserver."""
    url = "https://bot.wholestack.nl"
    admin_chat_id = 6249016860
    port = 7000

    context_types = ContextTypes(context=CustomContext)
    # Here we set updater to None because we want our custom webhook server to handle the updates
    # and hence we don't need an Updater instance
    application = (
        Application.builder().token(settings.bot_token).updater(None).context_types(context_types).build()
    )
    # save the values in `bot_data` such that we may easily access them in the callbacks
    application.bot_data["url"] = settings.bot_url

    # register handlers
    application.add_handler(CommandHandler('add', search))  # search for a track
    application.add_handler(CommandHandler('balance', balance)) # view wallet balance
    application.add_handler(CommandHandler('connect', connect)) # connect to spotify account
    application.add_handler(CommandHandler('fund',fund)) # add funds to wallet
    application.add_handler(CommandHandler('history', history)) # view history of tracks
    application.add_handler(CommandHandler('link',link)) # view LNDHUB QR 
    application.add_handler(CommandHandler('pay', pay)) # pay a lightning invoice
    application.add_handler(CommandHandler('queue', queue)) # view the queue
    application.add_handler(CommandHandler("setclientsecret",spotify_settings)) # set the secret for a spotify app
    application.add_handler(CommandHandler("setclientid",spotify_settings))  # set the clientid or a spotify app
    application.add_handler(CommandHandler(["start","help"],start))  # help message
    application.add_handler(CommandHandler(['dj','zap'], zap))  # pay another user
#    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))

    # Pass webhook settings to telegram
    await application.bot.set_webhook(url=f"{url}/telegram")

    # Set up webserver
    async def telegram(request: Request) -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await application.update_queue.put(
            Update.de_json(data=await request.json(), bot=application.bot)
        )
        return Response()


    async def spotify_callback(request: Request) -> PlainTextResponse:
        """ 
        This function handles the callback from spotify when authorizing request to an account
        
        A typical request will like like the following
     
        GET /spotifycallback?code=AQB5sDUcKql9oULl10ftgo9Lhmyzr3lpMRQl7i65drdM4WGaWvfx9ANBcUXVg-yR1FAqS2_yINbf6ej41lNr9ghmBGik0Bjwcgf90yxYLgk_H5c_ZcV2AKz9-eiqsnjZxqVoJyWqc5LnRHn0aEGG8YwBsk5ZHKIQh82uHikDZyAxKSCdLGCIaPbQtNUR0ej8WZH1y_gg_YOJa5aoC-f4ODJYOrokOTolxnlEy3zaJvddOgCF_GC8Fd9upxmovV5JR8LfACvrurjGYW7MaGeDKWMCb29GNXtg3lovTh2rwzE HTTP/1.0
        """

        code = request.query_params["code"]
        if not re.search("^[A-Za-z0-9\-\_]+$",code):
            return Response()

        state = request.query_params["state"]
        if not re.search("^[0-9\-]+$",state):
            return Response()

        try:
            state = base64.b64decode(state.encode('ascii')).decode('ascii')        
            [chatid, userid] = state.split(':')
            chatid = int(chatid)
            userid = int(userid)
        except:
            logging.error("Failure during query parameter parsing")
            return Response()

        
        try:
            auth_manager = await spotifyhelper.get_auth_manager(chatid)
            if auth_manager is not None:
                await application.bot.send_message(
                    chat_id=userid,
                    text=f"Spotify connected to the chat.")
        except:
            logging.error("Failure during auth_manager instantiation")
            return Response()

        return Response("Authorisation succesfull. You can close this window now")
    
            
    async def lnbits_lnurlp_callback(request: Request) -> PlainTextResponse:
        """
        Callback from LNbits when a wallet is funded. Send a message to the telegram user

        The callback is a POST request with a userid parameter in the URL
        
        The body content should be similar to the following

        {"payment_hash": "6d0734e641013e56767c6d8e4c0d02e6db0ddfdaa35cc370320e0cafb66565e7", "payment_request": "lnbc210n1p3l7k46pp5d5rnfejpqyl9vanudk8ycrgzumdsmh765dwvxupjpcx2ldn9vhnshp58aq3spsfd2263qpprxz7pqvhqm03mf2np6n9j8v0fpu7zqma94dqcqzpgxqzjcsp52d0hk2pzn75ugwzxev8tnf8xype05eaeadpmmv6rg72zchm649xs9qyyssqptzl7wwwkkjmaggr4s0m6gghmtla0uv38036m9py535ezng3pmxne69tw5p99f4e2vv4kqpwyx2kle6yn2xw4qes5268j97d3ycn97gp954uw3", "amount": 21000, "comment": null, "lnurlp": "2bP7Xn", "body": ""}'
        
        """
        tguserid = request.query_params['userid']
        if re.search("^[0-9]+$",tguserid):            
            obj = json.loads(await request.body())
            amount = int(obj['amount'] / 1000)            
            await application.bot.send_message(
                chat_id=int(tguserid),
                text=f"Received {amount} sats.Type /balance to view your balance.")
        return Response()
            
    starlette_app = Starlette(
        routes=[
            Route("/telegram", telegram, methods=["POST"]),
            Route("/lnbitscallback", lnbits_lnurlp_callback, methods=["POST"]),
            Route("/spotifycallback", spotify_callback, methods=["GET"])
        ]
    )
    
    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            port=port,
            use_colors=False,
            host="127.0.0.1",
        )
    )

    # Run application and webserver together
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
