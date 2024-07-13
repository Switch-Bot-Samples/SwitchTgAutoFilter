from config import BIND_ADDRESS, STREAM_PORT
from aiohttp import web
import logging
from asyncio import get_event_loop
from tclient import initialize_clients, tgclient
from aiohttp.web import AppRunner,TCPSite
from streamer import web_server

async def start_web_server():
    server = AppRunner(web_server())

    await server.setup()
    await TCPSite(server, BIND_ADDRESS, STREAM_PORT).start()
    logging.info("Service Started")

tgclient.start()

loop = get_event_loop()
loop.run_until_complete(initialize_clients())
loop.run_until_complete(start_web_server())
loop.run_forever()