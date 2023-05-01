# TwitchBot

## Installing Prerequisites

`pip install -r requirements.txt`

## Setup

> **Note**
> Todo: explain .env file setup and how to get bot and stream codes

### Twitch Bot Application Setup

> **Note**
> Todo: note application url as https://localhost

---
### Chat IRC

To generate the code used to login to twitch chat IRC use the url below and insert your applications client id in the relevant place

https://id.twitch.tv/oauth2/authorize?response_type=token&redirect_uri=https://localhost&scope=chat:read chat:edit&client_id=[CLIENT_ID]

After authorizing the application it will redirect to a bad page but the code will be in the address bar.

Copy the code and place it in the .env file for the BOT_IRC_AUTH_TOKEN

---

### BOT_CODE/STREAM_CODE

https://id.twitch.tv/oauth2/authorize?response_type=code&redirect_uri=https://localhost&scope=channel:moderate+channel:read:redemptions+channel:read:subscriptions+moderator:manage:banned_users+moderator:read:followers+channel:moderate+bits:read&client_id=[CLIENT_ID]

get code from result url and place into .env BOT_CODE/STREAM_CODE
when logged in as bot account place code into BOT_CODE
when logged in as stream account place code into STREAM_CODE

Example .env file


```ini
STREAM_USER=coolguy

BOT_USERNAME=CoolBot
BOT_USER=coolbot
BOT_IRC_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BOT_CODE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
STREAM_CODE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

IRC_HOST=wss://irc-ws.chat.twitch.tv:443

DB=data.db
```

## Running

`python TwitchBot`