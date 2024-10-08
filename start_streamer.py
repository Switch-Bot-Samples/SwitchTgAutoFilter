#import uvloop
#uvloop.install()

from config import BIND_ADDRESS, STREAM_PORT
from aiohttp import web
import logging, pyrogram
from asyncio import get_event_loop
from utils import initialize_clients
from aiohttp.web import AppRunner,TCPSite
from streamer import web_server

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")])

pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999

async def start_web_server():
    server = AppRunner(web_server())

    await server.setup()
    await TCPSite(server, BIND_ADDRESS, STREAM_PORT).start()
    logging.info("Service Started")

loop = get_event_loop()
loop.run_until_complete(initialize_clients())
loop.run_until_complete(start_web_server())
loop.run_forever()