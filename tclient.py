from pyrogram import Client
from tgconfig import BOT_TOKEN, API_ID, API_HASH


tgclient = Client("bot",
                  api_id=API_ID,
                  api_hash=API_HASH,
                  bot_token=BOT_TOKEN,
                  no_updates=True)