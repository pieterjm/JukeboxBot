# JukeboxBot
A Bitcoin lightning enabled Jukebox for Telegram

![](assets/20230307-Bot-logo-new.jpg)

## General info
 - The name of the bot is '@Jukebox_Lightning_bot'
 - The handle of the bot is "jukebox_fm_bot'
 - Jitsi link: https://meet.jit.si/NoderunnersFMRadioRocks24HoursADay

## Ideas for new features
Priority:
 - When folks type /queue, and the bot shows the queue, can we differentiate between what is added by plebs and what is the background playlist?
 - Chat embedded on the website (NOSTR maybe?) Endusers can toggle this on or of to be dislplayed in their own videofeed. Preferably should not requre a login but users should be able to set a username or use nostr or twitter login to chat. 
 - Connect the bot to NOSTR. How should that fundionaly work? 
 - Audio players other than spotify
 - Silent disco feature! 3-channels, crowd is the dj!
 - For buys moments, a mode where only n of x requested tracks get added to the list (fair chance)

 ## Backlog:
 - Test scripts for telegram itself
 - Conferences, Bitcoin Amsterdam/Miami etc. 
 - Curated playlists: User can create a playlist and make that public to the bot. Other users can vote for the playlist by paying sats. When a threshold is reached, the playlist is submitted to the queue. A percentage of the amount payed for the playlist goes to the creator of the playlist. 
 - Create a playlist: User can create a playlist by direct communication to the the bot. Basically a version of the /add command, but without playing. Playlists managed by the bot. 
 - Custodial bot. When a user receives money from other users, the amount could be kept by the bot as a budget to request new songs. That means, when there is sufficient budget, the bot just displays a Pay xyz sats, only clickable for the user, which is then substracted from their budget
 - rewards, gokken.
 - Liedjes faucet, ik gooi geld in de jukebox, maar jullie mogen de muziek uitzoeken. /faucet, when there is money left, /add payment comes from faucet 

## Problems
  - When the player is not available, the bot keeps sending messages that the player is not available, removed for now  
  - Let updates of the price message stay, or add it to the current playing track message (including description of the most important commands). Maybe the price command should be removed at all. Variable price appears as confusing
  
## Done
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

