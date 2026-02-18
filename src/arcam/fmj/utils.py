import asyncio
import functools
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
    def __init__(self, delay: float) -> None:
        self._timestamp = time.monotonic()
        self._lock = asyncio.Lock()
        self._delay = delay

    async def get(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self._timestamp - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._timestamp = time.monotonic() + self._delay


# Re-exports for backwards compatibility
from .discovery import (  # noqa: E402, F401
    get_possibly_invalid_xml,
    get_udn_from_xml,
    get_uniqueid_from_device_description,
    get_uniqueid_from_host,
    get_uniqueid_from_udn,
)
