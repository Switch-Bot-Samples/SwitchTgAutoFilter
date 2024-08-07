from pyrogram import Client
from tgconfig import BOT_TOKEN, API_ID, API_HASH, USE_TG_CLIENT
from streamer.utils.constants import multi_clients, work_loads
from os import environ, path, mkdir
from sys import argv

import asyncio, logging

logger = logging.getLogger("clients")

tgclient = Client(
    "bot2" if argv[-1] == "start_streamer.py" else "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

SLEEP_THRESHOLD = 360
USE_SESSION_FILE = True
sessions_dir = "sessions"

if not path.exists(sessions_dir):
    mkdir(sessions_dir)

if USE_TG_CLIENT:
    multi_clients[0] = tgclient


async def initialize_clients():
    all_tokens = dict(
        (c + 1, t)
        for c, (_, t) in enumerate(
            filter(lambda n: n[0].startswith("MULTI_TOKEN"), sorted(environ.items()))
        )
    )
    if not all_tokens:
        logger.info("No additional clients found, using default client")
        return

    async def start_client(client_id, token):
        try:
            logger.info(f"Starting - Client {client_id}")
            if client_id == len(all_tokens):
                await asyncio.sleep(2)
                print("This will take some time, please wait...")
            
            client = await Client(
                name=str(client_id),
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=token,
                sleep_threshold=SLEEP_THRESHOLD,
                workdir=sessions_dir if USE_SESSION_FILE else Client.PARENT_DIR,
                no_updates=True,
                in_memory=not USE_SESSION_FILE,
                workers=32,
                max_concurrent_transmissions=80
            ).start()
            """
            client = Telegram(
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=token,
                database_encryption_key=str(client_id),
                use_message_database=False,
                
            )
            client.login()"""

            work_loads[client_id] = 0
            return client_id, client
        except Exception:
            logger.error(f"Failed starting Client - {client_id} Error:", exc_info=True)

    print(all_tokens)
    clients = await asyncio.gather(
        *[start_client(i, token) for i, token in all_tokens.items()]
    )

    print(multi_clients)
    multi_clients.update(dict(clients))
    if len(multi_clients) != 1:
        MULTI_CLIENT = True
        logger.info("Multi-client mode enabled")
    else:
        logger.info("No additional clients were initialized, using default client")
