# Jukebox Lightning Bot texts

USER COMMANDS:
1.  /faq
    - view the help/info file that contains the commands and other tips/tricks to navigate the bot.|
2.  /add [track info] 
    - add music to the queue.
3. /queue
    - view the queue.
4. /history
    - view the history.
5. /stack 
    - replace /balance with /stack to prevent command collisions with other bots.
/fund 
    # command to prefund ones personal jukebox stack, will open an LNRUL.
/refund [invoice] 
    # to initiate a withdrawel from ones personal jukebox stack to an invoice.
/dj [amount]
    # Use this in a reply to send someone sats for their jukebox stack.
/dj [@username] [amount] 
    # Use this in a normal TG message to send sats to someones jukebox stack.
/dj [invoice]
    # Same as /refund [invoice], users can send sats from their stack to an invoice.
/link
    # view LNDHUB-QR code so users can link their jukebox stack LNBits wallet to their own lightning wallet.

ADMIN COMMANDS:
/setclientid
    # sets the spotify client id. 
/setclientsecret
    # sets the client secret.
/couple 
    # replace /connect with /coule to preveent command colissions with other bots. 
    # Admins use this command to couple their spotify to their Telegram group.
/decouple 
    # replace /disconnect with /decouple to preveent command colissions with other bots. 
    #Admins use this command to decouple their spotify player to their Telegram group.
