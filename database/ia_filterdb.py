import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from rapidfuzz.process import extract
from rapidfuzz.fuzz import token_set_ratio, partial_token_sort_ratio, token_ratio
from config import SEARCH_SWITCH_FILES
# extract()

from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from swdatabase.ia_filterdb import Media as SMedia

from tgconfig import FILE_DB_URL, FILE_DB_NAME, COLLECTION_NAME, MAX_RIST_BTNS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = AsyncIOMotorClient(FILE_DB_URL)
db = client[FILE_DB_NAME]
instance = Instance.from_db(db)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute="_id")
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    file_reference = fields.StrField(allow_none=True)
    unique_id = fields.StrField(allow_none=True)
    chat_id = fields.StrField(allow_none=True)
    message_id = fields.StrField(allow_none=True)

    class Meta:
        collection_name = COLLECTION_NAME


async def save_file(media, chat_id, message_id):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        print(chat_id, message_id)
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            chat_id=str(chat_id),
            message_id=str(message_id),
        )
    except ValidationError:
        logger.exception("Error Occurred While Saving File In Database")
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            logger.warning(
                str(getattr(media, "file_name", "NO FILE NAME"))
                + " is already saved in database"
            )
            return False, 0
        else:
            logger.info(
                str(getattr(media, "file_name", "NO FILE NAME"))
                + " is saved in database"
            )
            return True, 1


def splitList(lis, ind=10):
    newL = []
    while lis:
        newL.append(lis[:ind])
        lis = lis[ind:]
    return newL


async def get_search_results(
    query, file_type=None, max_results=(MAX_RIST_BTNS), offset=0, **kwargs
):
    query = query.strip()
    if not query:
        raw_pattern = "."
    elif " " not in query:
        raw_pattern = r"(\b|[\.\+\-_])" + query + r"(\b|[\.\+\-_])"
    else:
        raw_pattern = query.replace(" ", r".*[\s\.\+\-_]")
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], "", 0

    filter = {"file_name": regex}
    if file_type:
        filter["file_type"] = file_type
    
    if SEARCH_SWITCH_FILES:
        #    total_results = await Media.count_documents(filter)
        sfilter = {"$or": [{"description": regex}, {"caption": regex}]}
        cs = SMedia.find(sfilter)
        cs.sort("$natural", -1)
        files = await cs.to_list(length=250)
    else:
        files = []

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort("$natural", -1)
    # Slice files according to offset and max results
    cursor.limit(250)
    files.extend(await cursor.to_list(length=250))

    if kwargs.get("yfilter"):
        topRes = extract(
            query.lower(),
            [getattr(f, "description", f.file_name).lower() for f in files],
            scorer=token_ratio,
            limit=250,
        )
        results = [files[y[-1]] for y in topRes]
    else:
        results = files

    t_results = len(results)

    spl = splitList(results, max_results)

    if offset + 1 < len(spl):
        noffset = offset + 1
    elif t_results < max_results:
        noffset = ""
    else:
        noffset = 0

    try:
        res = spl[offset]
    except:
        res = []
    if not noffset and not res and query.count(" ") > 1:
        return await get_search_results(
            query.rsplit(" ", 1)[0], file_type, max_results, offset, **kwargs
        )

    return res, noffset, t_results

    trs = await SMedia.count_documents(sfilter)
    print("from switch", trs)
    total_results += trs

    next_offset = offset + max_results
    if next_offset > total_results:
        next_offset = ""
    prev = offset * max_results
    files = []
    if trs > prev:
        cs = SMedia.find(sfilter)
        cs.sort("$natural", -1)

        cs.skip(offset).limit(max_results)
        files = await cs.to_list(length=max_results)
    #        print(files)

    if offset or (len(files) < max_results):
        noffset = int(((offset * max_results) + len(files)) % max_results)
        #        print(noffset)
        cursor = Media.find(filter)
        # Sort by recent
        cursor.sort("$natural", -1)
        # Slice files according to offset and max results
        offset = offset - 1 if len(files) == max_results else offset
        cursor.skip(offset).limit(max_results)
        # Get list of files
        files.extend(await cursor.to_list(length=max_results))

    return files, next_offset, total_results


async def get_file_details(query):
    filter = {"file_id": query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def decode_file_ref(file_ref: str) -> bytes:
    return base64.urlsafe_b64decode((file_ref + "=").encode())


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash,
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref


"""
import asyncio
async def main():
    res = await get_search_results("star")
    #print(res)

#loop = asyncio.get_event_loop()

#loop.run_until_complete(main())
#exit()
# """
