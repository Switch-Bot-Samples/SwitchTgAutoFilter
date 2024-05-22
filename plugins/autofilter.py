import logging
import re
from swibots import (
    BotApp,
    BotContext,
    CommandEvent,
    InlineKeyboardButton,
    InlineMarkup,
    Message,
    filters,
    CallbackQueryEvent,
    MessageEvent,
    Media,
)
from config import ADMINS, CHATS, COMMUNITIES, INDEX_COMMUNITY_ID, INDEX_CHANNEL_ID
from swutils import parser, split_quotes, get_channel_or_group
from swdatabase.ia_filterdb import save_file
from client import app
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from swdatabase.filters_mdb import (
    add_filter,
    get_filters,
    delete_filter,
    count_filters,
    del_all,
    find_filter,
)

logger = logging.getLogger(__name__)


@app.on_command("addfilter")
async def add_autofilter_filter(ctx: BotContext[CommandEvent]):
    message = ctx.event.message
    #    print(message)
    if ADMINS is None or message.user_id not in ADMINS:
        await message.reply_text("You are not allowed to use this command!")
        return

    channel_or_group, is_group = await get_channel_or_group(message, app)
    if not channel_or_group:
        return

    args = ctx.event.message.message.split(None, 1)
    if len(args) < 2:
        await message.reply_text("Command Incomplete :(")
        return

    extracted = split_quotes(args[1])
    text = extracted[0].lower()

    if not message.replied_to and len(extracted) < 2:
        await message.reply_text("Add some content to save your filter!")
        return

    if (len(extracted) >= 2) and not message.replied_to:
        reply_text, btn, alert = parser(extracted[1], text, app)
        fileid = None
        if not reply_text:
            await message.reply_text(
                "You cannot have buttons alone, give some text to go with it!"
            )
            return
    elif message.replied_to and message.replied_to.inline_markup:
        try:
            rm = message.replied_to.inline_markup
            btn = rm.inline_keyboard
            if message.replied_to.media_id:
                fileid = message.replied_to.media_id
                reply_text = message.replied_to.media_info.caption
            else:
                reply_text = message.replied_to.message
                fileid = None
            alert = None
        except:
            reply_text = ""
            btn = "[]"
            fileid = None
            alert = None
    elif message.replied_to and message.replied_to.media_id:
        try:
            fileid = message.replied_to.media_id
            reply_text, btn, alert = parser(message.replied_to.message, text, app)
        except:
            reply_text = ""
            btn = "[]"
            alert = None
    elif message.replied_to and message.replied_to.message:
        try:
            fileid = None
            reply_text, btn, alert = parser(message.replied_to.message, text, app)
        except:
            reply_text = ""
            btn = "[]"
            alert = None
    else:
        return

    await add_filter(channel_or_group.id, text, reply_text, btn, fileid, alert)

    await message.reply_text(
        f"Filter for  `{text}`  added in  **{channel_or_group.name}**"
    )


@app.on_command("listfilters")
async def autofilter_filters(ctx: BotContext[CommandEvent]):
    message = ctx.event.message
    if ADMINS is None or message.user_id not in ADMINS:
        await message.reply_text("You are not allowed to use this command!")
        return
    channel_or_group, is_group = await get_channel_or_group(message, app)
    if not channel_or_group:
        return

    texts = await get_filters(channel_or_group.id)
    count = await count_filters(channel_or_group.id)
    title = channel_or_group.name
    if count:
        filterlist = f"Total number of filters in **{title}** : {count}\n\n"

        for text in texts:
            keywords = " ×  `{}`\n".format(text)

            filterlist += keywords

    else:
        filterlist = f"There are no active filters in **{title}**"

    await message.reply_text(
        filterlist,
    )


@app.on_command("delfilter")
async def autofilter_delfilter(ctx: BotContext[CommandEvent]):
    message = ctx.event.message
    if ADMINS is None or message.user_id not in ADMINS:
        await message.reply_text("You are not allowed to use this command!")
        return
    channel_or_group, is_group = await get_channel_or_group(message, app)
    if not channel_or_group:
        return await message.reply_text("Use this is community")
    try:
        cmd, text = message.message.split(" ", 1)
    except:
        await message.reply_text(
            "<i>Mention the filtername which you wanna delete!</i>\n\n"
            "<code>/delfilter filtername</code>\n\n"
            "Use /listfilters to view all available filters",
        )
        return

    query = text.lower()

    await delete_filter(message, query, channel_or_group.id)


@app.on_command("delallfilters")
async def autofilter_delallfilters(ctx: BotContext[CommandEvent]):
    message = ctx.event.message
    if ADMINS is None or message.user_id not in ADMINS:
        await message.reply_text("You are not allowed to use this command!")
        return
    channel_or_group, is_group = await get_channel_or_group(message, app)
    if not channel_or_group:
        return

    await message.reply_text(
        f"This will delete all filters from '{channel_or_group.name}'.\nDo you want to continue??",
        inline_markup=InlineMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Yes", callback_data="delallfiltersconfirm"
                    )
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="close_data")],
            ]
        ),
    )


@app.on_callback_query(filters.regexp(r"^delallfiltersconfirm"))
async def delete_all_index_confirm(ctx: BotContext[CallbackQueryEvent]):
    message = ctx.event.message
    channel_or_group, is_group = await get_channel_or_group(message, app)
    if not channel_or_group:
        return
    await del_all(message, channel_or_group.id, channel_or_group.name)


@app.on_message()
async def autofilter_filter(ctx: BotContext[MessageEvent]):
    message = ctx.event.message

    #    print(message)
    if message.receiver_id:
        return
    #   is_group = bool(message.group_id)
    # print(message)
    #    channel_or_group, is_group = await get_channel_or_group(message, app)
    #    print(channel_or_group)
    #  if not channel_or_group:
    #     return
    group_id = message.channel_id or message.group_id
    if not (message.media_info):
        return
    print(message.community_id, COMMUNITIES)
    if group_id in CHATS or message.community_id in COMMUNITIES:
        await save_file(message.media_info)
        return
    name = message.message
    reply_id = message.replied_to_id if message.replied_to_id > 0 else message.id
    keywords = await get_filters(group_id)
#    print(keywords)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        print(pattern, name)
        if re.search(pattern, name, flags=re.IGNORECASE):
            text, btn, alert, fileid = await find_filter(group_id, keyword)

            if text:
                text = text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await message.reply_text(
                                text.format(
                                    first=message.user.name,
                                    username=(
                                        None
                                        if not message.user.username
                                        else "@" + message.user.username
                                    ),
                                    id=message.user.id,
                                    query=name,
                                ),
                            )
                        else:
                            button = eval(btn)
                            await message.reply_text(
                                text.format(
                                    first=message.user.name,
                                    username=(
                                        None
                                        if not message.user.username
                                        else "@" + message.user.username
                                    ),
                                    id=message.user.id,
                                    query=name,
                                ),
                                inline_markup=InlineMarkup(button),
                            )
                    elif btn == "[]":
                        await message.reply_text(
                            "",
                            cached_media=Media(
                                fileid,
                                caption=text.format(
                                    first=message.user.name,
                                    username=(
                                        None
                                        if not message.user.username
                                        else "@" + message.user.username
                                    ),
                                    id=message.user.id,
                                    query=name,
                                )
                                or "",
                            ),
                        )
                    else:
                        button = eval(btn)
                        await message.reply_text(
                            "",
                            cached_media=Media(
                                fileid,
                                caption=text.format(
                                    first=message.user.name,
                                    username=(
                                        None
                                        if not message.user.username
                                        else "@" + message.user.username
                                    ),
                                    id=message.user.id,
                                    query=name,
                                )
                                or "",
                            ),
                            inline_markup=InlineMarkup(button),
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False


lastIndex = None


async def addFetchJob():
    global lastIndex
    messages = await app.get_channel_chat_history(
        INDEX_COMMUNITY_ID, INDEX_CHANNEL_ID, page_limit=50
    )
    for message in messages.messages:
        if lastIndex and message.id < lastIndex:
            break
        if message.media_info:
            try:
                await save_file(message.media_info)
            except Exception as er:
                logger.exception(er)
    if messages.messages:
        lastIndex = messages.messages[0].id


if INDEX_COMMUNITY_ID and INDEX_CHANNEL_ID:
    sched = AsyncIOScheduler()
    sched.add_job(addFetchJob, "interval", minutes=3)
    sched.start()