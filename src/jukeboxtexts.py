def init():
    # when the help, start command is given
    global help
    help = """
## FAQ
#### How do I couple the bot to my own Spotify Premium account?
- For now, you are sadly still required to use Telegram to connect the bot to your own Premium Spotify account. Please keep in mind, that if you later want to stream the audio to a Telegram group, you must be OWNER of that group! *(There is a difference between being owner and admin. Only owners can retrieve RTMP + streaming Key from a TG group)* If you are certain you don't want to stream the music into that TG group at a later date, you can just be admin. The bot will act within that group, only as a remote to your Spotify. 
1. Invite the [Jukebox Bot](https://t.me/Jukebox_Lightning_bot) to an existing or new Telegram Group
2. Make the bot admin
3. Send the bot a Private Message with this command: /couple
4. The bot will now give you a short list of what to do next
5. Locate the [link to your Spotify Developer account](https://developer.spotify.com/dashboard) and go there
6. In your [Spotify Developer account](https://developer.spotify.com/dashboard), click on the 'Create an app' button and give the bot a random name and description. Then click 'Create"
7. Click 'Edit Settings' and add EXACTLY this url https://jukebox.lighting/spotify under 'Redirect URIs'. Do not forget to click 'Add' and 'Save'
8. Copy the Client ID and give the bot this command in a Private Message and paste the client ID after it: /setclientid PasteClientID
9. Copy the Client Secret and give the bot this command in a Private Message and paste the secret after it: /setclientsecret PasteClientID
10. Now, make sure your spotify is playing music. *(We recommend setting a playlist to reteat continuously)*
11. Next, return to the group you made the bot admin of and type this command: /couple
12. The bot should give you a message with a button to click to finalize coupling your account. Click it!
13. The browser should open up, and you will see this message if all went well: *Authorisation Succesfull! You can close this window now.*
- To test if all works well (again, make sure spotify is playing music), try using some of the [commands you can use in Telegram](https://github.com/LightningJukeboxBot/LightningJukeboxBot/tree/main#tg-commands-for-the-bot)
*If you have trouble setting up, contact [@NoderunnersFM](https://t.me/noderunnersFM) or [@artdesigbysf](https://t.me/artdesigbysf) on Telegram*
- You can now plug in your pc/phone or whatever device is playing your spotify to a soundsystem and use the /web interface to /add music to the /queue!
Just give the /web command to print out QR codes with you unique web-interface link on it. 
- Additionally, you may set a /price. Standard is: /price 21 7 (Meaning 14 will go to your personal Jukeobox /stack and 7 will go to furhter development. You may choose to set /price to whatever you like. Examples: */price 0 0 (no amounts set, adding is free) /price 2100 210 (Price per track added is 2100 of which 210 go to bot dev fund and the rest to you)*
- More functionality is in the works!
    
#### How do I stream the music to some other location?
1. Make sure spotify is playing music
2. [Download and install OBS](https://obsproject.com/)
3. Make sure to mute your desktop audio, unless you want every sound your device makes to be streamed!
4. Make sure to set audio to 320KB for optimal quality
5. Set video bitrate to whatever works best for you
6. Add sources (select spotify exe), you may choose to add a microphone or imagery for your video feed
7. Important: set all audio outputs under 'Audio Mixer' to  -3 dB
8. If you are owner of a TG group, you can find the RTMP settings behind the symbol on the dopright (TG-desktop op ONLY!) that looks like a speech-balloon with three vertical lines in it.
9. Enter the RTMP werver of your TG group into OBS settings
10. Do the same for the key
11. Click, start streaming to begin streaming into TG
12. If you want to ouput to multiple locations, [use this plugin](https://obsproject.com/forum/resources/multiple-rtmp-outputs-plugin.964/)
13. Good luck and have fun!
"""           
    
    # when someone executes the balance command in a group
    global balance_in_group
    balance_in_group = "Like keeping your mnenomic seedphrase offline, it is better to query your balance in a private chat with me."

    # when someone executes the disconnect command in a private chat
    global disconnect_in_private_chat
    disconnect_in_private_chat = "Execute the /decouple command in a group where you want the player disconnected"

    # when someone tries to perform a command that requires admin permissions
    global you_are_not_admin
    you_are_not_admin = "You are not an admin in this chat."

    # when the spotify authorisation is removed
    global spotify_authorisation_removed
    spotify_authorisation_removed = "Removed player from group. To reconnect, an admin should perform the /couple command to authorize the bot."

    global spotify_authorisation_removed_error
    spotify_authorisation_removed_error = "Removed player from group failed. Sorry. retry or dm the captain."

    global no_client_id_set
    no_client_id_set = "No spotify ClientID set Use the /setclientid command to enter this id"

    global client_id_set
    client_id_set = "Spotify ClientID is set to {}"
    
    global no_client_secret_set
    no_client_secret_set = "No Spotify Client Secret set. Use the /setclientsecret command to enter this secret"        

    global client_secret_set
    client_secret_set = "Spotify Client Secret is set"

    global everything_set_now_do_connect
    everything_set_now_do_connect = "Both client_id and client_secret are set. Execute the /couple command in the group that you want to connect to the bot"

    global instructions_in_private_chat
    instructions_in_private_chat = "I'm sending instructions in the private chat."

    global button_to_private_chat
    button_to_private_chat = "Take me there"

    global click_the_button_to_authorize
    click_the_button_to_authorize = "Clicking on the button will take you to Spotify where you can grant the bot the authorisation to control the player."

    global add_command_help
    add_command_help = "Use the /add command to search for tracks and add them to the playlist. Enter the name of the artist and/or the song title after the /add command and select a track from the results. For example: \n/add rage against the machine killing in the name\n/add 7th element\n"
