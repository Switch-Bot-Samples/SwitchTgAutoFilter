# Taken from megadlbot_oss <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/webserver/routes.py>
# Thanks to Eyaadh <https://github.com/eyaadh>

import pyrogram
import re
import time, asyncio, json
import math
from asyncio import Queue
import logging
from random import choice
from streamer import utils
from pyrogram import raw
from os import getenv
import mimetypes
from aiohttp.web import Request
from typing import Union
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from base64 import b16decode
from streamer.exceptions import *
from streamer.utils.constants import work_loads, multi_clients
from database.ia_filterdb import get_file_details, decode_file_ref

from pyrogram.file_id import FileId

logger = logging.getLogger("routes")
StartTime = time.time()

routes = web.RouteTableDef()


@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": utils.get_readable_time(time.time() - StartTime),
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
        }
    )


@routes.get(r"/stream", allow_head=True)
async def stream_handler(request: web.Request):
    return await __stream_handler(request)


@routes.get(r"/thumb", allow_head=True)
async def stream_handler(request: web.Request):
    return await __stream_handler(request, True)


async def __stream_handler(request: web.Request, thumb=False):
    try:
        channel, messageId = None, None
        file_id = request.query.get("fileId")

        hash = request.query.get("hash")
        if hash:
            channel, message = b16decode(hash.encode()).decode().split(":")
            try:
                channel = int(channel)
            except Exception:
                pass
            messageId = int(message)
        #            print(channel, message)
        elif not file_id:
            channel = request.query.get("channel")
            try:
                channel = int(channel)
            except Exception as er:
                pass
            messageId = int(request.query.get("messageId"))
        return await media_streamer(request, channel, messageId, thumb, file_id)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:

        logger.critical(str(e), exc_info=True)
        raise web.HTTPInternalServerError(text=str(e))


class_cache = {}
fileHolder = {}
from itertools import cycle
'''

async def yield_complete_part(part_count, channel_id, message_id, offset, chunk_size, threads: int = 5):
    tasks = []
    current_part = 1
    clients = cycle(multi_clients.values())  # Assuming multi_clients is a predefined dictionary

    while current_part <= part_count:
        client = next(clients)
        task = asyncio.create_task(
            yield_files(client, channel_id, message_id, current_part, offset, chunk_size)
        )
        tasks.append((current_part, task))
        offset += chunk_size

        if len(tasks) >= threads:
            for part, task in sorted(tasks, key=lambda x: x[0]):
                await asyncio.wait([task], return_when=asyncio.ALL_COMPLETED)
                yield task.result()[1]
                tasks.remove((part, task))
                break

        current_part += 1

    # Handle any remaining tasks
    for part, task in sorted(tasks, key=lambda x: x[0]):
        await asyncio.wait([task], return_when=asyncio.ALL_COMPLETED)
        yield task.result()[1]

async def yield_files(client, channel_id, message_id, current_part, offset, chunk_size):
    if client in class_cache:
        streamer = class_cache[client]
    else:
        streamer = utils.ByteStreamer(client)
        class_cache[client] = streamer

    file_id = await streamer.generate_file_properties(channel_id, message_id, thumb=False)
    media_session = await streamer.generate_media_session(client, file_id)
    location = await streamer.get_location(file_id)

    r = await media_session.invoke(
        raw.functions.upload.GetFile(
            location=location, offset=offset, limit=chunk_size
        ),
    )
    
    if isinstance(r, raw.types.upload.File):
        chunk = r.bytes
        return (current_part, chunk)

'''
async def yield_complete_part(part_count, channel_id, message_id, offset, chunk_size, threads: int = 5):
    tasks = []
    current_part = 1
    clients = cycle(multi_clients.values())

    while current_part <= part_count:
        tasks.append(
            (current_part, asyncio.create_task(yield_files(next(clients), channel_id, message_id, current_part, offset, chunk_size)
        )))
        offset += chunk_size

        if len(tasks) == threads:
            for task in sorted(tasks, key=lambda x: x[0]):
                while not task[1].done():
                    await asyncio.sleep(0)
                current_part += 1
#                if current_part <= part_count:
#                    tasks.append(
 #               (current_part, asyncio.create_task(yield_files(next(clients), channel_id, message_id, current_part, offset, chunk_size)
  #          )))
                yield task[1].result()[1]
                tasks.remove(task)
                break
        else:

           current_part += 1
        """
            resp = await asyncio.gather(*tasks)
            for part, chunk in resp:
                yield chunk
            tasks.clear()
        """
#        current_part += 1
        
    if tasks:
        for task in sorted(tasks, key=lambda x: x[0]):
            while not task[1].done():
                await asyncio.sleep(0)
            yield task[1].result()[1]


async def yield_files(client, channel_id, message_id, current_part, offset, chunk_size):
        if client in class_cache:
            streamer = class_cache[client]
        else:
            streamer = utils.ByteStreamer(client)
            class_cache[client] = streamer

        file_id = await streamer.generate_file_properties(channel_id, message_id, thumb=False)
        media_session = await streamer.generate_media_session(client, file_id)
        location = await streamer.get_location(file_id)

        r = await media_session.invoke(
                        raw.functions.upload.GetFile(
                            location=location, offset=offset, limit=chunk_size
                        ),
            )
        if isinstance(r, raw.types.upload.File):
            chunk = r.bytes
            return (current_part, chunk)     


async def media_streamer(
    request: web.Request,
    channel: Union[str, int],
    message_id: int,
    thumb: bool = False,
    file_id: str = None,
):
    from tclient import tgclient as bot

    range_header = request.headers.get("Range", 0)

    if not class_cache.get(0):
        class_cache[0] = utils.ByteStreamer(bot)

    index = min(work_loads, key=work_loads.get)
#    print(work_loads, multi_clients)
    faster_client = multi_clients[index]

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logger.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logger.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = utils.ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect

    logger.debug("before calling get_file_properties")
 #   faster_client: Telegram
  #  res = faster_client.call_method("getMessageLinkInfo", {"url": f"https://t.me/{channel}/{message_id}"})
   # res.wait()
#    print(res.update, res.error_info)
#    file_id = res.update["message"]["content"]['video']['video']['id']
#    print(fileId)
 #   return web.json_response(res.update)
  #  exit()

    file_id = await tg_connect.get_file_properties(channel, message_id, thumb)
    logger.debug("after calling get_file_properties")

    file_size = file_id.file_size
#     file_size = res.update["message"]["content"]['video']['video']['size']

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 256
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)


    """body = tg_connect.yield_file(
        file_id,
        channel,
        message_id,
        index,
        offset,
        first_part_cut,
        last_part_cut,
        part_count,
        chunk_size,
    )"""
    body = yield_complete_part(part_count, channel, message_id, offset, chunk_size)
#    mime_type = res.update["message"]["content"]['video']['mime_type']
    mime_type = file_id.mime_type
    file_name = utils.get_name(file_id)
 #   file_name = res.update["message"]["content"]['video']['file_name']

    print(file_name, mime_type, file_id)
    disposition = "attachment"

    if not mime_type:
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    if "video/" in mime_type or "audio/" in mime_type or "/html" in mime_type:
        disposition = "inline"
    
    print(range_header, from_bytes, until_bytes, file_size, req_length)

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": str(mime_type),
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )


APP_AUTH_TOKEN = getenv("APP_AUTH_TOKEN", "")


def notVerified(request: Request):
    headers = request.headers
    if APP_AUTH_TOKEN and headers.get("Authorization") != APP_AUTH_TOKEN:
        return web.json_response({"ok": False, "message": "UNAUTHORIZED"})
    return


@routes.get("/messageInfo")
async def getMessage(request: Request):
    if notVerified(request):
        return

    clients = multi_clients
    bot = choice(list(clients.values()))

    channel = request.query.get("channel")
    try:
        msgId = int(request.query.get("messageId"))
    except Exception:
        return web.json_response({"ok": False, "message": "INVALID_RESPONSE"})
    try:
        channel = int(channel)
    except Exception:
        pass
    message = await bot.get_messages(chat_id=channel, message_ids=msgId)
    return web.json_response(json.loads(str(message)))
