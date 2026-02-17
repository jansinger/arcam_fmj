"""Unit tests for server.py: Server, ServerContext."""

import asyncio

import pytest

from arcam.fmj import (
    AmxDuetRequest,
    AnswerCodes,
    CommandCodes,
    CommandNotRecognised,
    CommandPacket,
    ResponsePacket,
)
from arcam.fmj.server import Server, ServerContext


@pytest.fixture
def server():
    """Create a Server instance for testing."""
    return Server("localhost", 0, "AVR450")


# --- process_request tests ---


async def test_process_request_amx_duet(server):
    """process_request returns AmxDuetResponse for AmxDuetRequest."""
    request = AmxDuetRequest()
    responses = await server.process_request(request)
    assert len(responses) == 1
    assert responses[0].device_model == "AVR450"


async def test_process_request_handler_returns_bytes(server):
    """process_request wraps bytes handler result in ResponsePacket."""
    server.register_handler(1, CommandCodes.POWER, bytes([0xF0]), lambda **kwargs: bytes([0x01]))
    request = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    responses = await server.process_request(request)
    assert len(responses) == 1
    assert isinstance(responses[0], ResponsePacket)
    assert responses[0].ac == AnswerCodes.STATUS_UPDATE
    assert responses[0].data == bytes([0x01])


async def test_process_request_handler_returns_list(server):
    """process_request passes through list handler result directly."""
    response_list = [
        ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([0x01])),
        ResponsePacket(1, CommandCodes.CURRENT_SOURCE, AnswerCodes.STATUS_UPDATE, bytes([0x02])),
    ]
    server.register_handler(1, CommandCodes.POWER, None, lambda **kwargs: response_list)
    request = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    responses = await server.process_request(request)
    assert len(responses) == 2
    assert responses is response_list


async def test_process_request_no_handler(server):
    """process_request returns COMMAND_NOT_RECOGNISED when no handler found."""
    request = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    responses = await server.process_request(request)
    assert len(responses) == 1
    assert responses[0].ac == AnswerCodes.COMMAND_NOT_RECOGNISED


async def test_process_request_wildcard_handler(server):
    """Wildcard handler (data=None) matches any data for that (zn, cc)."""
    server.register_handler(1, CommandCodes.VOLUME, None, lambda data, **kwargs: data)
    request = CommandPacket(1, CommandCodes.VOLUME, bytes([0x20]))
    responses = await server.process_request(request)
    assert len(responses) == 1
    assert responses[0].data == bytes([0x20])


async def test_process_request_exact_match_over_wildcard(server):
    """Exact (zn, cc, data) match takes precedence over wildcard."""
    server.register_handler(1, CommandCodes.VOLUME, None, lambda data, **kwargs: bytes([0xFF]))
    server.register_handler(1, CommandCodes.VOLUME, bytes([0xF0]), lambda **kwargs: bytes([0x42]))
    request = CommandPacket(1, CommandCodes.VOLUME, bytes([0xF0]))
    responses = await server.process_request(request)
    assert responses[0].data == bytes([0x42])


async def test_process_request_handler_raises_response_exception(server):
    """Handler raising ResponseException produces error ResponsePacket."""

    def failing_handler(**kwargs):
        raise CommandNotRecognised()

    server.register_handler(1, CommandCodes.POWER, bytes([0xF0]), failing_handler)
    request = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    responses = await server.process_request(request)
    assert len(responses) == 1
    assert responses[0].ac == AnswerCodes.COMMAND_NOT_RECOGNISED


# --- register_handler tests ---


def test_register_handler_with_data(server):
    """register_handler with data creates (zn, cc, data) key."""

    def handler(**kwargs):
        return bytes([0x01])

    server.register_handler(1, CommandCodes.POWER, bytes([0xF0]), handler)
    assert (1, CommandCodes.POWER, bytes([0xF0])) in server._handlers


def test_register_handler_without_data(server):
    """register_handler with data=None creates (zn, cc) key."""

    def handler(**kwargs):
        return bytes([0x01])

    server.register_handler(1, CommandCodes.POWER, None, handler)
    assert (1, CommandCodes.POWER) in server._handlers


# --- Server start/stop lifecycle ---


async def test_server_start_stop():
    """Server.start() and stop() manage the server lifecycle."""
    s = Server("localhost", 0, "AVR450")
    await s.start()
    assert s._server is not None
    await s.stop()
    assert s._server is None


async def test_server_stop_cancels_client_tasks():
    """Server.stop() cancels active client tasks before closing."""
    s = Server("localhost", 0, "AVR450")
    await s.start()
    port = s._server.sockets[0].getsockname()[1]

    # Connect a client (keeps connection open so task stays alive)
    reader, writer = await asyncio.open_connection("localhost", port)
    await asyncio.sleep(0.1)

    assert len(s._tasks) == 1
    await s.stop()
    assert len(s._tasks) == 0

    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass


async def test_process_runner_client_disconnect():
    """process_runner handles client disconnect gracefully."""
    s = Server("localhost", 0, "AVR450")
    await s.start()
    port = s._server.sockets[0].getsockname()[1]

    # Connect and immediately disconnect
    reader, writer = await asyncio.open_connection("localhost", port)
    writer.close()
    await writer.wait_closed()

    # Give server time to handle disconnect
    await asyncio.sleep(0.2)
    assert len(s._tasks) == 0
    await s.stop()


async def test_server_stop_noop_when_not_started():
    """Server.stop() is a no-op when not started."""
    s = Server("localhost", 0, "AVR450")
    await s.stop()  # Should not raise


# --- ServerContext tests ---


async def test_server_context():
    """ServerContext manages start/stop lifecycle."""
    s = Server("localhost", 0, "AVR450")
    async with ServerContext(s):
        assert s._server is not None
    assert s._server is None
