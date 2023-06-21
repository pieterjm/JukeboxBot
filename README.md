# JukeboxBot
A Bitcoin lightning enabled Jukebox for Telegram

![](assets/20230307-Bot-logo-new.jpg)

## General info
 - The name of the bot is '@Jukebox_Lightning_bot'
 - The handle of the bot is "jukebox_fm_bot'
 - Jitsi link: https://meet.jit.si/NoderunnersFMRadioRocks24HoursADay

## Ideas for new features
 - Super admin stats: interface for dedicated superadmins that can see stuff like the groups that are using the bot, sats in the bot etc. 
 - Seperate queue: When folks type /queue, and the bot shows the queue, can we differentiate between what is added by plebs and what is the background playlist? Maybe by not showing the background playlist at all? We could create our own queue that is separate from the background playlist. If we manage our own queue we could also introduce features like upvoting items in the queue. 
- Song duration and time left displayed in TG somehow
- Stats: /stats command to see the top jukebox stats, most requested track, top 10 of users adding tracks to the queue. 
 - NOSTR connectivity: Chat embedded on the website (NOSTR maybe?) Endusers can toggle this on or of to be dislplayed in their own videofeed. Preferably should not requre a login but users should be able to set a username or use nostr or twitter login to chat. How would this look like when there are multiple instances of the JukeBox running? Would the admin of a group provide a NOSTR private key for the bot to use in this group?
 - Web API: the ability to use the bot through a Web API. How should this work for multiple groups? Provide an API endpoint in the Group Admin chat? This should preferably be a REST API (search, results, pay, queue, currentplaying). Actually the current playing track is a kind of (limited) REST API already.
 - Congestion control #1: limmeting folks to add more tracks if the queue gets to a certain size and they already added 2 tracks in a row. This is dependent on the seperate queue function.  
 - Congestion control #2: Increase cost per added track per track that is still waiting in the queue. This is dependent on the seperate queue. 
 - Connect the bot to NOSTR: Users can add a NOSTR private key to their private chat (which I wouldn't do). And then in a private chat with the bot enable/disable NOSTR through a command. The JukeboxBot uses that key to post a message when a track is played.  
 - Silent disco feature! 3-channels, crowd is the dj! 
 - Congestion control: For buys moments, a mode where only n of x requested tracks get added to the list (fair chance). This will probably increase the load even more. Just make more requests, best way is to increase the price. 
 - Audio players other than spotify
 - Improved faucet over LNtips with congestion control. 

 ## Backlog:
 - Test scripts for telegram itself
 - Conferences, Bitcoin Amsterdam/Miami etc. 
 - Curated playlists: User can create a playlist and make that public to the bot. Other users can vote for the playlist by paying sats. When a threshold is reached, the playlist is submitted to the queue. A percentage of the amount payed for the playlist goes to the creator of the playlist. 
 - Create a playlist: User can create a playlist by direct communication to the the bot. Basically a version of the /add command, but without playing. Playlists managed by the bot. 
 - Custodial bot. When a user receives money from other users, the amount could be kept by the bot as a budget to request new songs. That means, when there is sufficient budget, the bot just displays a Pay xyz sats, only clickable for the user, which is then substracted from their budget
 - rewards, gokken.
 - Liedjes faucet, ik gooi geld in de jukebox, maar jullie mogen de muziek uitzoeken. /faucet, when there is money left, /add payment comes from faucet 

## Problems
  - /fund limit is to low at 2100
  - /donate gives no feedback after setting /donate ammount
  - /stack command result looks like it is not updating when funds are added. However does update when funds are subtracted
  - /stats bot amount seems to only update in 21 increments, even though some groups have higher /donate ammount set. Example, B7 gropu has /price 2100 and /donate 400, however, after /add track, Tommy receives 2079 and the bot 21 sats
  - When the player is not available, the bot keeps sending messages that the player is not available, removed for now  
  - Let updates of the price message stay, or add it to the current playing track message (including description of the most important commands). Maybe the price command should be removed at all. Variable price appears as confusing
  
## Done
 - Donation per track
 - Create a new bot with the name JukeboxBot
 - Upload code to github 
 - When a track is selected, the payment message is a new message. This requires the user to scroll. Instead the track selection message should be replaced. Fixed.
 - Reversed history in message
 - Connect JukeboxBot to noderunnersfm
 - Integrate callback script and bot script into one script
 - Change polling function to callback from telegram
 - Create a welcome message for new users
 - One-to-one communication: Allow users to have a private conversation with to bot. Search for tracks, manage their playlist, add to queue. This one is important to create as it enables to create other features as described below. 
 - Curated playlists: User can create a playlist and make that public to the bot. Other users can vote for the playlist by paying sats. When a threshold is reached, the playlist is submitted to the queue. A percentage of the amount payed for the playlist goes to the creator of the playlist. 
 - Create a playlist: User can create a playlist by direct communication to the the bot. Basically a version of the /add command, but without playing. Playlists managed by the bot. 
 - Custodial bot. When a user receives money from other users, the amount could be kept by the bot as a budget to request new songs. That means, when there is sufficient budget, the bot just displays a Pay xyz sats, only clickable for the user, which is then substracted from their budget
 - Personal budget for users. Users have personal budget where they can upload money to later spend on payments for songs -> faster payment flow
 - Create another instance of the bot so that it can be used on other groups. 
 - When a payment is not made, the request should be removed after some time (half an hour or so). Appears not to be a mayor issue
 - Create new names and groups for Jukebox_lightning_test and Jukebox_lightning_development
 - Spotify gave a new error when connecting, test invalid ID's. Error appears to be resolved
 - Create nicely designed HTML pages for payment and Spotify connection.
 - Create another instance of the bot so that it can be used on other groups. 
 - One-to-one communication: Allow users to have a private conversation with to bot. Search for tracks, manage their playlist, add to queue. This one is important to create as it enables to create other features as described below. 
 - Personal budget for users. Users have personal budget where they can upload money to later spend on payments for songs -> faster payment flow
 - Faster payment feedback
 - Payment feedback in payment HTML page
 - Create nicely designed payment page for funding

## Test

Connect bot to test group
Disconnect from spotify
queue
history
add

