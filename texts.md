# Jukebox Lightning Bot texts

## commands for the /setcommands 

The following commands can be copy and pasted into the botfather to set the correct commands 

faq - View the bot FAQ
add - Add music to the queue
queue - View queue
history - View history
stack - View you balance
dj - Sent sats to another user
link - Connect via lndhub (BlueWallet, Zeus)
fund - Prefund your personal wallet
refund - Withdraw sats from your personal wallet

## User commands:
1.  /faq
    - View the bot FAQ that contains the commands and other tips & tricks to navigate the bot.
2.  /add (track info)
    - Add music to the queue.
3. /queue
    - View the queue.
4. /history
    - View the history.
5. /stack 
    - Replace /balance with /stack to prevent command collisions with other bots.
6. /fund 
    - Prefund ones personal jukebox stack, will open an LNRUL.
7. /refund (invoice)
    - Initiate a withdrawel from ones personal jukebox stack to an invoice.
8. /dj (amount)
    - Use this in a reply to send someone sats for their jukebox stack.
9.  /dj (@username) (amount)
    - Use this in a normal TG message to send sats to someones jukebox stack.
10. /dj (invoice)
    - Same as /refund (invoice), users can send sats from their stack to an invoice.
11. /link
    - View LNDHUB-QR code so users can link their jukebox stack LNBits wallet to their own lightning wallet.


## Admin commands:
1. /setclientid (player client id)
    - Sets the audioplayer client id. 
2. /setclientsecret (player client secret)
    - Sets the audioplayer client secret.
3. /couple 
    - Replace /connect with /couple to prevent command colissions with other bots. 
    - Admins use this command to couple their player to their Telegram group.
4. /decouple 
    - Replace /disconnect with /decouple to preveet command colissions with other bots. 
    - Admins use this command to decouple their player to their Telegram group.
5. /setdonate (on)
    - Donates 7 sats of the 21 to the botmainers at each jukebox /add 
6. /setdonate (off)
    - Disables the donation
    
## Jukeboxtexts.py edit suggestions

def init():
    # when the faq command is given
    global faq
    faq = """
Use these commands to control the Jukebox:

User commands:
/faq to show this cheatsheet.
/add (track info) to search for music. Replace (track info) with the artist and track title.
/queue to view the list of upcoming tracks. 
/history speaks for itself.
/fund to prefund your personal jukebox stack via a LNURL.
/refund (invoice) to initiate a withdrawel from your jukebox stack
/dj (amount) use this in a reply to send someone sats for their jukebox stack.
/dj (@username) (amount) use this in a normal message to send sats to someones jukebox stack.
/dj (invoice) does the same as /refund (invoice) and will send sats from your jukebox stack to an invoice.
    
The following will only show results in a private chat between you and the bot:
/stack to view the balance of your jukebox stack.
/link to view a LNDHUB-QR code which will link your personal jukebox LNbits wallet to a (mobile) lighting wallet that supports it (Blue/Zeus/etc.).

## Admin commands:
These will must be done in a private chat between you and the bot:
/setclientid /setclientid (Spotify client id) sets the spotify client id. 
/setclientsecret (Spotify client secret) sets the spotify client secret.

After you set the client id and secret, use the following in the group where you wish to enable the bot:
/couple to couple and enable the bot.
/decouple to decouple and disable the bot.

If you like this bot, send a donation to herovk@ln.tips and artdesignbysf@noderunners.org or simply /dj (amount) the bot. 

Alternatively each user can consider donating a set amount to the bot maintainers when they add music to the queue. Use the following command to make it so:
/donate (amount) (on) to specify the amount that will be added to the cost of adding a track to the que and which will be sent to the bot maintainers.
/donate (off) to disable donating at each track addition.           

    # when someone executes the stack command in a group
    global balance_in_group
    balance_in_group = "Don't reveal your stack! The bot had sent you a private message with the height of your jukebox stack."

    # when someone executes the decouple command in a private chat
    global disconnect_in_private_chat
    disconnect_in_private_chat = "Execute the /decouple command in a group where you want the player disconnected"

    # when someone tries to perform a command that requires admin permissions
    global you_are_not_admin
    you_are_not_admin = "You are not an admin in this chat."

    # when the spotify authorisation is removed
    global spotify_authorisation_removed
    spotify_authorisation_removed = "Removed audioplayer from group. To reconnect, an admin should perform the /couple command to authorize the bot."

    global spotify_authorisation_removed_error
    spotify_authorisation_removed_error = "Removed player from group failed. Sorry. Retry or dm the captain."

    global no_client_id_set
    no_client_id_set = "No spotify ClientID set Use the /setclientid command to enter this id."

    global client_id_set
    client_id_set = "Spotify ClientID is set to {}"
    
    global no_client_secret_set
    no_client_secret_set = "No Spotify Client Secret set. Use the /setclientsecret command to enter this secret"        

    global client_secret_set
    client_secret_set = "Spotify Client Secret is set"

    global everything_set_now_do_connect
    everything_set_now_do_connect = "Both client_id and client_secret are set. Execute the /couple command in the group that you want to connect to the bot"

    global instructions_in_private_chat
    instructions_in_private_chat = "I'm sending instructions in a private chat message."

    global button_to_private_chat
    button_to_private_chat = "Take me there"

    global click_the_button_to_authorize
    click_the_button_to_authorize = "Clicking this button will take you to Spotify where you must grant the bot the authorisation to control the player."

    global add_command_help
    add_command_help = "Type /faq for more info. Use the /add (track info) command to search for music and add them to the playlist. Replace (track info) with the name of the artist and the title of the music. Please beware, some music may not be listed. If at first you don't find what you are looking for, cancel and try again. Here is an example: /add Pink Floyd Money
