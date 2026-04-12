from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator


class EventBus:
    def __init__(self) -> None:
        self._listeners: set[asyncio.Queue[str]] = set()

    async def publish(self, event_type: str, payload: dict) -> None:
        message = f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"
        dead: list[asyncio.Queue[str]] = []
        for queue in self._listeners:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self._listeners.discard(queue)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._listeners.add(queue)
        try:
            yield ": connected\n\n"
            while True:
                message = await queue.get()
                yield message
        finally:
            self._listeners.discard(queue)


event_bus = EventBus()
