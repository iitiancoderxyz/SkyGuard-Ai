"""
In-process EventBus for pushing events to SSE subscribers.
Bounded queues per subscriber; never blocks the processing engine.
"""
import asyncio
from typing import Set, Dict, Any
from app.core.logging import logger


class EventBus:
    def __init__(self, max_queue_size: int = 100):
        self._subscribers: Set[asyncio.Queue] = set()
        self._max_queue_size = max_queue_size

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.discard(q)

    def publish(self, event: Dict[str, Any]):
        for q in list(self._subscribers):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(event)
            except Exception as e:
                logger.warning(f"Failed to push to subscriber: {e}")


bus = EventBus()
