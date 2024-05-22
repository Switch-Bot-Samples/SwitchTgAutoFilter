import logging
from swibots import (
    InlineKeyboardButton,
    InlineMarkup,
    InlineQueryResultDocument,
    InlineQuery,
    BotApp,
    BotContext,
    InlineQueryEvent,
    InlineQueryAnswer,
)
from swdatabase.ia_filterdb import get_search_results
from swutils import get_size, file_int_from_name, file_str_from_int
from config import CUSTOM_FILE_CAPTION
from client import app

logger = logging.getLogger(__name__)


@app.on_inline_query()
async def answer(ctx: BotContext[InlineQueryEvent]):
    """Show search results for given inline query"""
    query: InlineQuery = ctx.event.query

    results = []
    if "|" in query.query:
        string, file_type = query.query.split("|", maxsplit=1)
        file_type = file_int_from_name(file_type.lower().strip())
        string = string.strip()
    else:
        string = query.query.strip()
        file_type = None

    offset = int(query.offset or 0)
    reply_markup = get_reply_markup(query=string)
    files, next_offset, total = await get_search_results(
        string, file_type=file_type, max_results=10, offset=offset
    )

    for file in files:
        title = file.file_name
        size = get_size(file.file_size)
        f_caption = file.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name="" if title is None else title,
                    file_size="" if size is None else size,
                    file_caption="" if f_caption is None else f_caption,
                )
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{file.file_name}"
        results.append(
            InlineQueryResultDocument(
                id=file.file_id,
                title=f_caption,
                document_url=file.file_url,
                mime_type=file.mime_type,
                description=f"Size: {get_size(file.file_size)}\nType: {file_str_from_int(file.file_type)}",
                reply_markup=reply_markup,
            )
        )

    if results:
        pm_text = f"📁 Results - {total}"
        if string:
            pm_text += f" for {string}"
        try:
            await query.answer(
                InlineQueryAnswer(
                    results=results,
                    is_personal=True,
                    pm_text=pm_text,
                    pm_parameter="start",
                    next_offset=str(next_offset),
                )
            )
        except Exception as e:
            logging.exception(str(e))
    else:
        pm_text = f"❌ No results"
        if string:
            pm_text += f' for "{string}"'

        await query.answer(
            InlineQueryAnswer(
                title=pm_text,
                results=[],
                is_personal=True,
                pm_text=pm_text,
                pm_parameter="okay",
            )
        )


def get_reply_markup(query):
    buttons = [[InlineKeyboardButton("Search again")]]
    return InlineMarkup(buttons)
