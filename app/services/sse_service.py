import asyncio
import json
import redis.asyncio as redis
from fastapi.responses import StreamingResponse
from app.core.config import settings

class RedisClient:
    def __init__(self, url):
        self.redis_url = url
        self.redis_pool = None

    async def connect(self):
        self.redis_pool = redis.ConnectionPool.from_url(self.redis_url, decode_responses=True)

    async def close(self):
        if self.redis_pool:
            await self.redis_pool.disconnect()

    async def publish(self, channel: str, message: dict):
        """
        Publishes a message to a Redis channel.
        """
        async with redis.Redis(connection_pool=self.redis_pool) as r:
            await r.publish(channel, json.dumps(message, ensure_ascii=False))

    async def listen(self, channel: str):
        """
        Listens to a Redis channel and yields messages.
        """
        async with redis.Redis(connection_pool=self.redis_pool) as r:
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
                if message:
                    yield message['data']
                await asyncio.sleep(0.01)

redis_client = RedisClient(settings.REDIS_URL)

async def sse_generator(game_id: int):
    """
    An async generator that yields SSE-formatted messages.
    """
    channel = f"game:{game_id}"
    async for message in redis_client.listen(channel):
        # SSE format: event: <event_name>\ndata: <json_string>\n\n
        yield f"event: new_scene\ndata: {message}\n\n"