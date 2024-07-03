from dotenv import load_dotenv
import asyncio
from client import app, hasJoined
from tgbot import bt
from tclient import tgclient
import os
from config import DISABLE_FORCE, START_SERVER, BIND_ADDRESS, STREAM_PORT
import swibots
from common import SW_COMMUNITY
from streamer import web_server
from aiohttp.web import TCPSite, AppRunner

from pyrogram import idle
from loader import load_modules

env_file = os.path.join(os.path.dirname(__file__), "..", ".env")  # noqa : E402
load_dotenv(env_file, override=True)

import logging.config  # noqa : E402
import logging  # noqa : E402
import swibots as s
from swibots import (
    BotContext,
    CommandEvent,
    CallbackQueryEvent,
    Message,
    filters,
    InlineKeyboardButton,
    InlineMarkup,
)
from swibots import BotCommand as RegisterCommand  # noqa : E402
from config import ADMINS

WS_URL = os.getenv("CHAT_SERVICE_WS_URL")
CONFIG_WS_URL = swibots.get_config()["CHAT_SERVICE"]["WS_URL"]

logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)

if not app._register_commands:
    app.set_bot_commands(
        [
            RegisterCommand("start", "Show help about commands", True),
            # help
            RegisterCommand("miniapp", "Open APP", True),
            RegisterCommand("verify", "Verify your telegram account", True),
            RegisterCommand("stream", "Stream movie from link", True),
            # imdb
            RegisterCommand("json", "Prints the message json", True),
            #       RegisterCommand("buttons", "Shows buttons", True),0
            # media
            RegisterCommand("search", "Search for indexed media", True),
            RegisterCommand("movie", "Search for a movie on IMDb", True),
            # filters
            RegisterCommand("addfilter", "Add a filter", True),
            RegisterCommand(
                "index", "Index current channel or group (OWNER ONLY)", True
            ),
            RegisterCommand("deleteall", "Delete all indexed (OWNER ONLY)", True),
            RegisterCommand("listfilters", "List all filters", True),
            RegisterCommand("deletefiles", "Delete files [OWNER]", True),
            RegisterCommand("delfilter", "Delete a filter", True),
            RegisterCommand("delallfilters", "Delete all filters", True),
            RegisterCommand("getfile", "Get file by id", True),
        ]
    )

print(app._register_commands)
load_modules("plugins")


@app.on_callback_query(filters.text("close_data"))
async def on_callback_query(ctx: BotContext[CallbackQueryEvent]):
    message: Message = ctx.event.message
    await message.delete()


@app.on_command("miniapp")
async def start(ctx: BotContext[CommandEvent]):
    mId = ctx.event.message
    if not DISABLE_FORCE and not await hasJoined(ctx.event.action_by_id):
        await ctx.event.message.send(
            f"🔮 *Please join below community in order to use this bot!*\n\nhttps://iswitch.click/{SW_COMMUNITY}"
        )
        return
    await mId.reply_text(
        "Click below button to open mini app.",
        inline_markup=InlineMarkup(
            [[InlineKeyboardButton("Open APP", callback_data="Home")]]
        ),
    )


@app.on_command("start")
async def start(ctx: BotContext[CommandEvent]):
    mId = ctx.event.params
    message: Message = ctx.event.message
    if mId and mId.isdigit():
        proc = await message.reply_text("Processing...")
        if not DISABLE_FORCE and not await hasJoined(ctx.event.action_by_id):
            await message.reply_text(
                f"🔮 *Please join below community in order to use this bot!*\n\nhttps://iswitch.click/{SW_COMMUNITY}"
            )
            await proc.delete()
            return
        try:
            media = await app.get_media(mId)
            media.id = 0
            await message.reply_text(
                f"Hey @{message.user.username}, here is your file!\n\n{media.description or media.file_name}",
                media_info=media,
                inline_markup=InlineMarkup(
                    [
                        [InlineKeyboardButton("Direct Download", url=media.url)],
                        [
                            InlineKeyboardButton(
                                "Stream file", callback_data=f"vfile|{mId}"
                            )
                        ],
                    ]
                ),
            )
        except Exception as er:
            print(er, mId)
            await message.reply_text(f"Media not found!")
        await proc.delete()
        return
    text = (
        "Hello! here is a list of commands you can use:\n"
        + "/help - Show this message\n"
        + "/json - Dump the message as json\n"
        + "/imdb <movie name> - Search for a movie on IMDb\n"
        + "/search Search for a file on my database\n"
    )

    if message.user_id in ADMINS:
        text += (
            "\nAdmin commands:\n"
            + "/index <group or channel> - Save media files from the channel or group\n"
            + "/addfilter <filter> - Add a filter\n"
            + "/delfilter <filter> - Delete a filter\n"
            + "/listfilters - List all filters\n"
            + "/delallfilters - Delete all filters\n"
        )

    await message.reply_text(
        text,
        #                             inline_markup=s.InlineMarkup([[
        #                               s.InlineKeyboardButton("Open APP",
        #                                                       callback_data="Home")
        #                         ]]
        # )
    )


loop = asyncio.get_event_loop()
loop.run_until_complete(app.start())

tgclient.start()
# loop.create_task(bt.start())


async def start_web_server():
    server = AppRunner(web_server())

    await server.setup()
    await TCPSite(server, BIND_ADDRESS, STREAM_PORT).start()
    logging.info("Service Started")


if START_SERVER:
    loop.run_until_complete(start_web_server())

loop.run_until_complete(bt.start())
idle()
# loop.run_forever()
# bt.run()
