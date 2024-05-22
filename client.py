from swibots import Client
import config

app = Client(config.BOT_TOKEN, plugins=dict(root="plugins"))

# communityId = app.run(app.get_community(username=f"tamil_links_official"))


async def hasJoined(user):
    return True
    try:
        data = await app.get_community_member(communityId.id, user)
        assert data != None
    except Exception:
        return False
    return True

