import json
import logging
from typing import Tuple
from swibots import (
    BotApp,
    BotContext,
    MessageEvent,
    Message,
    filters,
    RestClient,
    RestResponse,
    JSONDict,
    NetworkError,
    filters,
    CallbackQueryEvent,
    CommandEvent,
    BotCommand as RegisterCommand,
)

from config import ADMINS

log = logging.getLogger(__name__)

restclient = RestClient()


def parse_response(response: Tuple[int, bytes]) -> RestResponse[JSONDict]:
    decoded_s = response[1].decode("utf-8", "replace")
    try:
        jsonObject = json.loads(decoded_s)
    except ValueError as exc:
        jsonObject = decoded_s

    response = RestResponse(jsonObject, response[0], {})
    if response.is_error:
        raise NetworkError(response.error_message)
    return response
