import asyncio
import functools
import heapq
import logging
import time

_LOGGER = logging.getLogger(__name__)


def async_retry(attempts=2, allowed_exceptions=()):
    def decorator(f):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            attempt = attempts
            while True:
                attempt -= 1

                try:
                    return await f(*args, **kwargs)
                except allowed_exceptions:
                    if attempt == 0:
                        raise
                    _LOGGER.debug("Retrying: %s %s", f, args)

        return wrapper

    return decorator


class Throttle:
    """Serializes command execution with minimum spacing, priority ordering,
    and optional deduplication.

    Lower *priority* values are dispatched first.  When *dedup_key* is
    provided and another entry with the same key is already queued, the
    older entry is cancelled (its ``await`` raises `CancelledError`).
    """

    def __init__(self, delay: float) -> None:
        self._timestamp = time.monotonic()
        self._delay = delay
        self._queue: list[tuple[int, int, asyncio.Future]] = []
        self._dedup: dict[tuple, asyncio.Future] = {}
        self._counter = 0
        self._lock = asyncio.Lock()

    async def get(
        self, priority: int = 1, dedup_key: tuple | None = None
    ) -> None:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()

        if dedup_key is not None:
            old = self._dedup.pop(dedup_key, None)
            if old is not None and not old.done():
                old.cancel()
            self._dedup[dedup_key] = future

        heapq.heappush(self._queue, (priority, self._counter, future))
        self._counter += 1

        if not self._lock.locked():
            asyncio.ensure_future(self._dispatch())

        await future

    async def _dispatch(self) -> None:
        async with self._lock:
            while self._queue:
                _, _, future = heapq.heappop(self._queue)
                if future.done():
                    continue

                now = time.monotonic()
                delay = self._timestamp - now
                if delay > 0:
                    await asyncio.sleep(delay)
                self._timestamp = time.monotonic() + self._delay

                if future.cancelled():
                    continue

                # Clean up dedup entry if this future owns it
                for key, f in list(self._dedup.items()):
                    if f is future:
                        del self._dedup[key]
                        break

                future.set_result(None)


# Re-exports for backwards compatibility
from .discovery import (  # noqa: E402, F401
    get_possibly_invalid_xml,
    get_udn_from_xml,
    get_uniqueid_from_device_description,
    get_uniqueid_from_host,
    get_uniqueid_from_udn,
)
