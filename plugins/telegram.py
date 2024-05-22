from client import app
from swibots import BotContext, CommandEvent
from secrets import token_hex
from base64 import urlsafe_b64decode
import logging
from tclient import tgclient
from common import waitingHashes, approvedUsers, pHash
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup
from tgconfig import LOG_CHANNEL


@app.on_command("verify")
async def verifyHandler(ctx: BotContext[CommandEvent]):
    m = ctx.event.message
    param = ctx.event.params
    user = m.user
    logging.info(ctx)
    if not param:
        await m.reply_text("Please provide verification code to verify yourself!")
        return
    if not param.endswith("="):
        param += "=="
    if param in waitingHashes:
        await m.reply_text("Provided verification code has already been used!")
        return
    decode = urlsafe_b64decode(param.encode()).decode()
    if "|" not in decode:
        await m.reply_text("Invalid verification code!")
        return
    spliit = decode.split("|")
    fileId = spliit[0]
    time = float(spliit[-1])
    diff = (datetime.now() - datetime.fromtimestamp(time)).total_seconds() / 3600
    if diff > 12:
        await m.reply_text("Verification code expired!")
        return
    userId = int(spliit[1])
#    print(fileId)
    approvedUsers[userId] = time
    await m.reply_text("Verified successfully!")

    from database.ia_filterdb import get_file_details
    from utils import get_size
    
    files = await get_file_details(fileId)
    print(files)
    file = files[0]
    title = file.file_name
    try:
        await tgclient.send_message(
            LOG_CHANNEL, f"**UserID:** {userId} got verified!\n\n**Switch:**  `@{user.username}`\n\n**File:** `{title}`\n#Verified",
        )
    except Exception as er:
        print(er)
    size = get_size(file.file_size)
    f_caption = f"[{size}] {title}"
    await tgclient.send_cached_media(
        chat_id=userId,
        file_id=fileId,
        caption=f_caption
    )
    await m.send("Your file has been sent on telegram!")
    if pHash.get(userId):
        await tgclient.delete_messages(
            chat_id=userId,
            message_ids=pHash[userId],
        )
