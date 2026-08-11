import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

EVENT_CHANNEL = "skyflip:events"


async def publish_event(redis: Redis | None, event_type: str, payload: dict[str, Any]) -> None:
    if redis is None:
        return
    event = {
        "type": event_type,
        "payload": payload,
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    try:
        await redis.publish(EVENT_CHANNEL, json.dumps(event, separators=(",", ":")))
    except Exception:
        # Event streaming is useful but must not make a successful market commit fail.
        return


async def redis_event_stream(redis: Redis) -> AsyncIterator[dict[str, Any] | None]:
    pubsub = redis.pubsub()
    await pubsub.subscribe(EVENT_CHANNEL)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if message is None:
                yield None
                continue
            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                yield json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
    finally:
        await pubsub.unsubscribe(EVENT_CHANNEL)
        await pubsub.close()
