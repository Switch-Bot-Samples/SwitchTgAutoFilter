import logging
from struct import pack
import re, guessit
import base64
from aniparse import parse
from rapidfuzz import process, fuzz, utils
from swibots import Media as SwiMedia
from pymongo.errors import DuplicateKeyError
from aiohttp import ClientSession
from aiohttp_client_cache import CacheBackend, SQLiteBackend, CachedSession
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from config import (
    DATABASE_URI,
    DATABASE_NAME,
    COLLECTION_NAME,
    USE_DESCRIPTION_FILTER,
    TMDB_KEY,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)


async def make_request(url):
    async with CachedSession(cache=SQLiteBackend("urlcache")) as ses:
        async with ses.get(
            url,
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {TMDB_KEY}",
            },
        ) as res:
            return await res.json()


async def getMovie(mId, type="movie"):
    url = f"https://api.themoviedb.org/3/{type}/{mId}"
    return await make_request(url)


async def make_search(query, type="movie"):
    url = f"https://api.themoviedb.org/3/search/{type}?query={query.replace(' ', '+')}&include_adult=false&language=en-US&page=1"

    return await make_request(url)


@instance.register
class Media(Document):
    file_id = fields.IntField(attribute="_id")
    source_id = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.IntField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    thumbnail = fields.StrField(allow_none=True)
    description = fields.StrField(allow_none=True)
    file_url = fields.StrField(allow_none=True)
    imdb_id = fields.IntField(allow_none=True)
    movie_name = fields.StrField(allow_none=True)
    resolution = fields.StrField(allow_none=True)
    tv_show = fields.BooleanField(allow_none=True)
    episode_id = fields.IntField(allow_none=True)
    season_id = fields.IntField(allow_none=True)

    class Meta:
        indexes = ("$file_name",)
        collection_name = COLLECTION_NAME


async def save_file(media: SwiMedia):
    """Save file in database"""

    # TODO: Find better way to get same file_id for same media to avoid duplicates
    # file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    details = guessit.guessit(media.description)
    meName = details.get("title")
    if not meName:
        details = parse(media.description)
        meName = details.get("anime_title")
    print(meName)
    imdBid = None
    mname = None
    isTv = None
    poster = None
    #    print(details)
    if (media.description.endswith((".mkv", ".mp4", ".webm"))) and (name := meName):
        try:
            res = await make_search(name)
            selected, perc, index = process.extractOne(
                name,
                (
                    f"{r.get('title') or r.get('name')}"
                    for r in sorted(
                        res["results"],
                        key=lambda r: (
                            int(
                                r["release_date"].split("-")[0],
                            )
                            if r.get("release_date")
                            else -1
                        ),
                    )
                ),
                scorer=fuzz.token_sort_ratio,
            )
#            print(res["results"][index])
            if not res["results"] or perc < 80:
                res = await make_search(name, type="tv")
                selected, perc, index = process.extractOne(
                    name,
                    (
                        f"{r.get('title') or r.get('name')}"
                        for r in sorted(
                            res["results"],
                            key=lambda r: (
                                int(
                                    r["release_date"].split("-")[0],
                                )
                                if r.get("release_date")
                                else -1
                            ),
                            reverse=True,
                        )
                    ),
                    scorer=fuzz.token_sort_ratio,
                    processor=utils.default_process,
                )
                isTv = True
            if perc >= 80:
                syl = res["results"][index]
                imdBid = syl["id"]
                mname = syl.get("name") or syl.get("title") or syl.get("original_title")
                poster = "https://image.tmdb.org/t/p/w220_and_h330_face/" + syl.get(
                    "poster_path"
                )
        except Exception as er:
            print(er)
    try:
        file = Media(
            file_id=media.id,
            source_id=media.source_id,
            file_name=media.file_name,
            file_size=media.file_size,
            file_type=media.media_type,
            mime_type=media.mime_type,
            caption=media.caption,
            thumbnail=poster or media.thumbnail_url or poster,
            description=media.description,
            file_url=media.url,
            resolution=str(
                details.get("screen_size") or details.get("video_resolution", "")
            ),
            imdb_id=imdBid,
            movie_name=mname,
            tv_show="true" if isTv and imdBid else None,
            episode_id=details.get("episode_number") if isTv and imdBid else None,
            season_id=details.get("anime_season") if isTv and imdBid else None,
        )
    except ValidationError as e:
        logger.exception("Error occurred while saving file in database")
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )

            return False, 0
        else:
            logger.info(
                f'{getattr(media, "file_name", "NO_FILE")} is saved to database'
            )
            return True, 1


async def get_search_results(
    query, file_type=None, max_results=10, offset=0, filter=False
):
    """For given query return (results, next_offset)"""

    query = query.strip()
    # if filter:
    # better ?
    # query = query.replace(' ', r'(\s|\.|\+|\-|_)')
    # raw_pattern = r'(\s|_|\-|\.|\+)' + query + r'(\s|_|\-|\.|\+)'
    if not query:
        raw_pattern = "."
    elif " " not in query:
        raw_pattern = r"(\b|[\.\+\-_])" + query + r"(\b|[\.\+\-_])"
    else:
        raw_pattern = query.replace(" ", r".*[\s\.\+\-_]")

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []

    if USE_DESCRIPTION_FILTER:
        filter = {"$or": [{"description": regex}, {"caption": regex}]}
    else:
        filter = {"description": regex}

    if file_type:
        filter["file_type"] = file_type

    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results

    if next_offset > total_results:
        next_offset = ""

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort("$natural", -1)
    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)
    # Get list of files
    files = await cursor.to_list(length=max_results)

    return files, next_offset, total_results


async def get_file_details(query):
    filter = {"file_id": int(query)}
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
