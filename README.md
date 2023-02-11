# JukeboxBot
A Bitcoin lightning enabled Jukebox for Telegram

![](assets/JukeboxBot.jpg)

## General info
 - The name of the bot is 'JukeboxBot'
 - The handle of the bot is "jukebox_fm_bot'

## Backlog
 - Upload code to github

 - Connect JukeboxBot to noderunnersfm
 - Integrate callback script and bot script into one script
 - Change polling function to callback from telegram
 - Create a welcome message for new users

## Ideas for new features
 - One-to-one communication: Allow users to have a private conversation with to bot. Search for tracks, manage their playlist, add to queue. This one is important to create as it enables to create other features as described below. 
 - Curated playlists: User can create a playlist and make that public to the bot. Other users can vote for the playlist by paying sats. When a threshold is reached, the playlist is submitted to the queue. A percentage of the amount payed for the playlist goes to the creator of the playlist. 
 - Create a playlist: User can create a playlist by direct communication to the the bot. Basically a version of the /add command, but without playing. Playlists managed by the bot. 
 - Custodial bot. When a user receives money from other users, the amount could be kept by the bot as a budget to request new songs. That means, when there is sufficient budget, the bot just displays a Pay xyz sats, only clickable for the user, which is then substracted from their budget
 - Personal budget for users. Users have personal budget where they can upload money to later spend on payments for songs -> faster payment flow
 - Create another instance of the bot so that it can be used on other groups. 
 
 ## Problems
  - When the player is not available, the bot keeps sending messages that the player is not available
  - When a track is selected, the payment message is a new message. This requires the user to scroll. Instead the track selection message should be replaced
  - When a payment is not made, the request should be removed after some time (half an hour or so)
  - Let updates of the price message stay, or add it to the current playing track message (including description of the most important commands)
 
 
## Done
 - Create a new bot with the name JukeboxBot
