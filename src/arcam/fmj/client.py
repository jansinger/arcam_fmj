"""Async TCP client for Arcam receiver protocol.

Provides ClientBase (protocol logic, heartbeat, request/response matching)
and Client (TCP connection management). Use ClientContext as an async
context manager to handle the full connection lifecycle.
"""

import asyncio
import contextlib
import logging
import time
from asyncio.streams import StreamReader, StreamWriter
from collections.abc import Callable
from contextlib import contextmanager
from typing import overload

from . import (
    AmxDuetRequest,
    AmxDuetResponse,
    AnswerCodes,
    ArcamException,
    CommandCodes,
    CommandPacket,
    ConnectionFailed,
    EnumFlags,
    NotConnectedException,
    ResponseException,
    ResponsePacket,
    UnsupportedZone,
    read_response,
    write_packet,
)
from .utils import Throttle, async_retry

_LOGGER = logging.getLogger(__name__)
_REQUEST_TIMEOUT = 3.0
_REQUEST_THROTTLE = 0.2

_HEARTBEAT_INTERVAL = 5.0
_HEARTBEAT_TIMEOUT = _HEARTBEAT_INTERVAL + _HEARTBEAT_INTERVAL


class ClientBase:
    """Base protocol handler with heartbeat, listeners, and request/response matching.

    Handles the binary protocol framing, sends periodic heartbeat pings,
    dispatches incoming packets to registered listeners, and provides
    request/response correlation with timeout and retry.
    """

    def __init__(self) -> None:
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None
        self._task = None
        self._listen: set[Callable] = set()
        self._throttle = Throttle(_REQUEST_THROTTLE)
        self._timestamp = time.monotonic()

    def add_listener(self, listener: Callable) -> None:
        self._listen.add(listener)

    def remove_listener(self, listener: Callable) -> None:
        self._listen.remove(listener)

    @contextmanager
    def listen(self, listener: Callable):
        self.add_listener(listener)
        yield self
        self.remove_listener(listener)

    async def _process_heartbeat(self, writer: StreamWriter):
        while True:
            delay = self._timestamp + _HEARTBEAT_INTERVAL - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                _LOGGER.debug("Sending ping")
                await write_packet(writer, CommandPacket(1, CommandCodes.POWER, bytes([0xF0])))
                self._timestamp = time.monotonic()

    async def _process_data(self, reader: StreamReader):
        try:
            while True:
                try:
                    async with asyncio.timeout(_HEARTBEAT_TIMEOUT):
                        packet = await read_response(reader)
                except TimeoutError as exception:
                    _LOGGER.debug("Missed all pings")
                    raise ConnectionFailed() from exception

                if packet is None:
                    _LOGGER.info("Server disconnected")
                    return

                _LOGGER.debug("Packet received: %s", packet)
                for listener in self._listen:
                    listener(packet)
        finally:
            self._reader = None

    async def process(self) -> None:
        if not self._writer:
            raise NotConnectedException("Writer missing")
        if not self._reader:
            raise NotConnectedException("Reader missing")

        _process_heartbeat = asyncio.create_task(self._process_heartbeat(self._writer))
        try:
            await self._process_data(self._reader)
        finally:
            _process_heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _process_heartbeat
            self._writer.close()
            await self._writer.wait_closed()

    @property
    def connected(self) -> bool:
        return self._reader is not None and not self._reader.at_eof()

    @property
    def started(self) -> bool:
        return self._writer is not None

    @overload
    async def request_raw(
        self, request: CommandPacket, *, timeout: float | None = None
    ) -> ResponsePacket: ...

    @overload
    async def request_raw(
        self, request: AmxDuetRequest, *, timeout: float | None = None
    ) -> AmxDuetResponse: ...

    @async_retry(2, asyncio.TimeoutError)
    async def request_raw(
        self,
        request: CommandPacket | AmxDuetRequest,
        *,
        timeout: float | None = None,
    ) -> ResponsePacket | AmxDuetResponse:
        if not self._writer:
            raise NotConnectedException()
        writer = self._writer  # keep copy around if stopped by another task
        future: asyncio.Future[ResponsePacket | AmxDuetResponse] = asyncio.Future()

        def listen(response: ResponsePacket | AmxDuetResponse):
            if response.responds_to(request) and not (future.cancelled() or future.done()):
                future.set_result(response)

        await self._throttle.get()

        async with asyncio.timeout(timeout or _REQUEST_TIMEOUT):
            _LOGGER.debug("Requesting %s", request)
            with self.listen(listen):
                await write_packet(writer, request)
                self._timestamp = time.monotonic()
                return await future

    async def send(self, zn: int, cc: CommandCodes, data: bytes) -> None:
        """Send a command without waiting for a response (fire-and-forget)."""
        if not self._writer:
            raise NotConnectedException()

        if not (cc.flags & EnumFlags.ZONE_SUPPORT) and zn != 1:
            raise UnsupportedZone()

        writer = self._writer
        request = CommandPacket(zn, cc, data)
        await self._throttle.get()
        await write_packet(writer, request)

    async def request(
        self, zn: int, cc: CommandCodes, data: bytes, *, timeout: float | None = None
    ):
        """Send a command and return the response data bytes.

        Raises ResponseException subclasses for non-STATUS_UPDATE answers.
        """
        if not self._writer:
            raise NotConnectedException()

        if not (cc.flags & EnumFlags.ZONE_SUPPORT) and zn != 1:
            raise UnsupportedZone()

        if cc.flags & EnumFlags.SEND_ONLY:
            await self.send(zn, cc, data)
            return

        response = await self.request_raw(CommandPacket(zn, cc, data), timeout=timeout)

        if response.ac == AnswerCodes.STATUS_UPDATE:
            return response.data

        raise ResponseException.from_response(response)


class Client(ClientBase):
    """TCP client for connecting to an Arcam receiver.

    Args:
        host: Hostname or IP address of the receiver.
        port: TCP port (default 50000).
    """

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    async def start(self) -> None:
        """Open TCP connection to the receiver."""
        if self._writer:
            raise ArcamException("Already started")

        _LOGGER.debug("Connecting to %s:%d", self._host, self._port)
        try:
            self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        except ConnectionError as exception:
            raise ConnectionFailed() from exception
        except OSError as exception:
            raise ConnectionFailed() from exception
        _LOGGER.info("Connected to %s:%d", self._host, self._port)

    async def stop(self) -> None:
        """Close TCP connection to the receiver."""
        if self._writer:
            try:
                _LOGGER.info("Disconnecting from %s:%d", self._host, self._port)
                self._writer.close()
                await self._writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            finally:
                self._writer = None
                self._reader = None


class ClientContext:
    """Async context manager that starts, processes, and stops a Client.

    Usage::

        async with ClientContext(client) as c:
            result = await c.request(1, CommandCodes.POWER, bytes([0xF0]))
    """

    def __init__(self, client: Client):
        self._client = client
        self._task: asyncio.Task | None = None

    async def __aenter__(self) -> Client:
        await self._client.start()
        self._task = asyncio.create_task(self._client.process())
        return self._client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self._client.stop()
