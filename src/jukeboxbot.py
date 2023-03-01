#!/usr/bin/env python
import asyncio
import os
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
from user import User, SpotifySettings
import userhelper
import settings

settings.init('development')


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
        context.job_queue.run_once(delete_message, 60, data={'message':message})

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

        context.job_queue.run_once(delete_message, 60, data={'message':message})
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
    sps = userhelper.get_spotify_settings(update.effective_user.id)    
    
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
        if sps.clientid is not None and sps.clientsecret is not None:
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
        context.job_queue.run_once(delete_message, 30, data={'message':message})
        return

    # send message in group to go to private chat
    bot_me = await context.bot.get_me()

    # if both variables are not none, ask the user to authorize
    if sps.clientid is not None and sps.clientsecret is not None:
        spotifyauth = SpotifyOAuth(
            scope='user-read-currently-playing,user-modify-playback-state,user-read-playback-state',
            client_secret=sps.client_secret,            
            client_id=sps.client_id,
            redirect_uri=settings.spotify_redirect_uri,
            show_dialog=False,
            open_browser=False
        )

        # send instruscuitn in the group
        message = await context.bot.send_message(
        chat_id=update.message.chat_id,
        text="I'm sending instructions in the private chat.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
        ]))
        context.job_queue.run_once(delete_message, 60, data={'message':message})
        
        # send a message to the private chat of the bot
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Clicking on the button below will take you to Spotify where you can grant the bot the authorisation to control the player.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Authorize player",url=spotifyauth.get_authorize_url())]
            ]))
    else:
        # send a message that configuration is required
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Additional configuration is required, execute this command in a private chat with me.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Take me there",url=f"https://t.me/{bot_me.username}")]
            ]))

            
        context.job_queue.run_once(delete_message, 30, data={'message':message})
        
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

        context.job_queue.run_once(delete_message, 30, data={'message':message})
        return
    
    # get spotify settings for the user
    sps = userhelper.get_spotify_settings(update.effective_user.id)

    result = re.search("/(setclientid|setclientsecret)\s+([a-z0-9]+)\s*$",update.message.text)
    if result is None:
        message = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Incorrect usage. ")
                       
    command = result.groups()[0]
    value = result.groups()[1]

    bSave = False
    if command == 'setclientid':
        sps.client_id = value
        bSave = True
        
    if command == 'setclientsecret':
        sps.client_secret = valuee
        bSave = True
        
    if bSave == True:
        userhelper.save_spotify_settings(sps)
    

# fund the wallet of the user
async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Click on the button to fund the wallet of @{user.username}. Anyone can spend!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Fund sats",url=user.lnurlp)]
            ]))
    context.job_queue.run_once(delete_message, 300, data={'message':message})

    # delete the original message
    await update.message.delete()
    

# Get/Create a QR code and store in filename
def get_qrcode_image_filename(data):
    filename = os.path.join(qrcode_path,"{}.png".format(hash(data)))
    if not os.path.isfile(filename):
        img = qrcode.make(data)
        file = open(filename,'wb')
        if file:
            img.save(file)
            file.close()
    return filename

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

        context.job_queue.run_once(delete_message, 60, data={'message':message})
        return

    # we're in a private chat now
    user = await userhelper.get_or_create_user(update.effective_user.id,update.effective_user.username)

    # create QR code for the link    
    filename = get_qrcode_image_filename(lndhublink)
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
        Application.builder().token("6249016860:AAEBWywfONRT_GsTNt5l1ZfCcBuwk48hins").updater(None).context_types(context_types).build()
    )
    # save the values in `bot_data` such that we may easily access them in the callbacks
    application.bot_data["url"] = url
    application.bot_data["admin_chat_id"] = admin_chat_id

    # register handlers
    #application.add_handler(CommandHandler('add', add))
    application.add_handler(CommandHandler('balance', balance))
    application.add_handler(CommandHandler('connect', connect)) # in both private and public chats
    application.add_handler(CommandHandler('fund',fund))
    #application.add_handler(CommandHandler('history', history))
    application.add_handler(CommandHandler('link',link))
    application.add_handler(CommandHandler('pay', pay)) # only in private chat
    #application.add_handler(CommandHandler('price', play_price))
    #application.add_handler(CommandHandler('queue', queue))
    application.add_handler(CommandHandler("setclientsecret",spotify_settings))    # TODO only in private chat
    application.add_handler(CommandHandler("setclientid",spotify_settings))  # TODO only in private chat
    application.add_handler(CommandHandler(["start","help"],start))    
    #application.add_handler(CommandHandler(['dj','zap'], zap))            
    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))

    # Pass webhook settings to telegram
    await application.bot.set_webhook(url=f"{url}/telegram")

    # Set up webserver
    async def telegram(request: Request) -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await application.update_queue.put(
            Update.de_json(data=await request.json(), bot=application.bot)
        )
        return Response()

    async def lnbits_lnurlp_callback(request: Request) -> PlainTextResponse:
        """
        Callback from LNbits when a wallet is funded
        """
        tguserid = request.query_params['userid']
        if re.search("^[0-9]+$",userid):            
            await application.bot.send_message(
                chat_id=int(tguserid),
                text=f"Received a funding payment.")
            print(await request.body())
        
    
    async def custom_updates(request: Request) -> PlainTextResponse:
        """
        Handle incoming webhook updates by also putting them into the `update_queue` if
        the required parameters were passed correctly.
        """
        try:
            user_id = int(request.query_params["user_id"])
            payload = request.query_params["payload"]
        except KeyError:
            return PlainTextResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content="Please pass both `user_id` and `payload` as query parameters.",
            )
        except ValueError:
            return PlainTextResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content="The `user_id` must be a string!",
            )

        await application.update_queue.put(WebhookUpdate(user_id=user_id, payload=payload))
        return PlainTextResponse("Thank you for the submission! It's being forwarded.")

    async def health(_: Request) -> PlainTextResponse:
        """For the health endpoint, reply with a simple plain text message."""
        return PlainTextResponse(content="The bot is still running fine :)")

    starlette_app = Starlette(
        routes=[
            Route("/telegram", telegram, methods=["POST"]),
            Route("/healthcheck", health, methods=["GET"]),
            Route("/submitpayload", custom_updates, methods=["POST", "GET"]),
            Route("/lnbitscallback", lnbits_lnurlp_callback, methods=["POST"])
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
