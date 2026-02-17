"""Test with a fake server"""

import asyncio
import logging
import unittest
from unittest.mock import ANY

import pytest

from arcam.fmj import (
    CommandCodes,
    CommandNotRecognised,
    ConnectionFailed,
    UnsupportedZone,
)
from arcam.fmj.client import Client, ClientContext
from arcam.fmj.server import Server, ServerContext
from arcam.fmj.state import State

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
async def server():
    s = Server("localhost", 0, "AVR450")
    async with ServerContext(s):
        s.register_handler(0x01, CommandCodes.POWER, bytes([0xF0]), lambda **kwargs: bytes([0x00]))
        s.register_handler(0x01, CommandCodes.VOLUME, bytes([0xF0]), lambda **kwargs: bytes([0x01]))
        yield s


@pytest.fixture
async def silent_server():
    s = Server("localhost", 0, "AVR450")

    async def process(reader, writer):
        while True:
            if await reader.read(1) == bytes([]):
                break

    s.process_runner = process
    async with ServerContext(s):
        yield s


def _server_port(server: Server) -> int:
    """Get the actual port assigned by the OS."""
    return server._server.sockets[0].getsockname()[1]


@pytest.fixture
async def client(server):
    c = Client("localhost", _server_port(server))
    async with ClientContext(c):
        yield c


@pytest.fixture
async def speedy_client(mocker):
    mocker.patch("arcam.fmj.client._HEARTBEAT_INTERVAL", new=1.0)
    mocker.patch("arcam.fmj.client._HEARTBEAT_TIMEOUT", new=2.0)
    mocker.patch("arcam.fmj.client._REQUEST_TIMEOUT", new=0.5)


async def test_power(server, client):
    data = await client.request(0x01, CommandCodes.POWER, bytes([0xF0]))
    assert data == bytes([0x00])


async def test_multiple(server, client):
    data = await asyncio.gather(
        client.request(0x01, CommandCodes.POWER, bytes([0xF0])),
        client.request(0x01, CommandCodes.VOLUME, bytes([0xF0])),
    )
    assert data[0] == bytes([0x00])
    assert data[1] == bytes([0x01])


async def test_invalid_command(server, client):
    with pytest.raises(CommandNotRecognised):
        await client.request(0x01, CommandCodes.from_int(0xFF), bytes([0xF0]))


async def test_state(server, client):
    state = State(client, 0x01)
    await state.update()
    # Server returns power=OFF (standby), so only power is queried
    assert state.get(CommandCodes.POWER) == bytes([0x00])


async def test_silent_server_request(speedy_client, silent_server):
    c = Client("localhost", _server_port(silent_server))
    async with ClientContext(c):
        with pytest.raises(asyncio.TimeoutError):
            await c.request(0x01, CommandCodes.POWER, bytes([0xF0]))


async def test_unsupported_zone(speedy_client, silent_server):
    c = Client("localhost", _server_port(silent_server))
    async with ClientContext(c):
        with pytest.raises(UnsupportedZone):
            await c.request(0x02, CommandCodes.DECODE_MODE_STATUS_2CH, bytes([0xF0]))


async def test_silent_server_disconnect(speedy_client, silent_server):
    from arcam.fmj.client import _HEARTBEAT_TIMEOUT

    c = Client("localhost", _server_port(silent_server))
    connected = True
    with pytest.raises(ConnectionFailed):
        async with ClientContext(c):
            await asyncio.sleep(_HEARTBEAT_TIMEOUT + 0.5)
            connected = c.connected
    assert not connected


async def test_heartbeat(speedy_client, server, client):
    from arcam.fmj.client import _HEARTBEAT_INTERVAL

    with unittest.mock.patch.object(server, "process_request", wraps=server.process_request) as req:
        await asyncio.sleep(_HEARTBEAT_INTERVAL + 0.5)
        req.assert_called_once_with(ANY)


async def test_cancellation(silent_server):
    e = asyncio.Event()
    c = Client("localhost", _server_port(silent_server))

    async def runner():
        await c.start()
        try:
            e.set()
            await c.process()
        finally:
            await c.stop()

    task = asyncio.create_task(runner())
    async with asyncio.timeout(5):
        await e.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
