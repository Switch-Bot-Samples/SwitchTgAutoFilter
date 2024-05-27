import asyncio
import logging
import aiohttp
from os import getenv

logger = logging.getLogger("keep_alive")


async def ping_server():
    sleep_time = getenv("PING_INTERVAL", 80)
    logger.info("Started with {}s interval between pings".format(sleep_time))
    while True:
        await asyncio.sleep(sleep_time)
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(getenv("URL", "")) as resp:
                    logger.info("Pinged server with response: {}".format(resp.status))
        except TimeoutError:
            logger.warning("Couldn't connect to the site URL..")
        except Exception:
            logger.error("Unexpected error: ", exc_info=True)
