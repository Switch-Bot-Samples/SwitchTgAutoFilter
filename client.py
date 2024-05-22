from swibots import Client
import config
from common import SW_COMMUNITY
app = Client(config.BOT_TOKEN, plugins=dict(root="plugins"))


async def hasJoined(user):
    communityId = await app.get_community(username=SW_COMMUNITY)
    try:
        data = await app.get_community_member(communityId.id, user)
        assert data != None
    except Exception:
        return False
    return True

