"""Unit tests for client.py: ClientBase, Client, ClientContext."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from arcam.fmj import (
    ArcamException,
    CommandCodes,
    CommandNotRecognised,
    ConnectionFailed,
    EnumFlags,
    NotConnectedException,
    ResponsePacket,
    AnswerCodes,
    UnsupportedZone,
)
from arcam.fmj.client import Client, ClientBase, ClientContext


# --- ClientBase unit tests ---


def test_add_remove_listener():
    """add_listener/remove_listener manage the listener set."""
    base = ClientBase()
    listener = lambda pkt: None
    base.add_listener(listener)
    assert listener in base._listen
    base.remove_listener(listener)
    assert listener not in base._listen


def test_listen_context_manager():
    """listen() context manager adds/removes listener."""
    base = ClientBase()
    listener = lambda pkt: None
    with base.listen(listener):
        assert listener in base._listen
    assert listener not in base._listen


def test_connected_false_when_no_reader():
    """connected is False when no reader."""
    base = ClientBase()
    assert base.connected is False


async def test_connected_false_when_reader_at_eof():
    """connected is False when reader is at EOF."""
    base = ClientBase()
    reader = asyncio.StreamReader()
    reader.feed_eof()
    base._reader = reader
    assert base.connected is False


async def test_connected_true_when_reader_active():
    """connected is True when reader is active."""
    base = ClientBase()
    reader = asyncio.StreamReader()
    reader.feed_data(b"\x00")
    base._reader = reader
    assert base.connected is True


def test_started_false_when_no_writer():
    """started is False when no writer."""
    base = ClientBase()
    assert base.started is False


def test_started_true_when_writer_exists():
    """started is True when writer set."""
    base = ClientBase()
    base._writer = MagicMock()
    assert base.started is True


async def test_request_raw_not_connected():
    """request_raw raises NotConnectedException when not connected."""
    base = ClientBase()
    from arcam.fmj import CommandPacket

    with pytest.raises(NotConnectedException):
        await base.request_raw(CommandPacket(1, CommandCodes.POWER, bytes([0xF0])))


async def test_send_not_connected():
    """send() raises NotConnectedException when not connected."""
    base = ClientBase()
    with pytest.raises(NotConnectedException):
        await base.send(1, CommandCodes.POWER, bytes([0xF0]))


async def test_send_unsupported_zone():
    """send() raises UnsupportedZone for zone-unsupported commands."""
    base = ClientBase()
    base._writer = MagicMock()
    # DECODE_MODE_STATUS_2CH doesn't have ZONE_SUPPORT flag
    with pytest.raises(UnsupportedZone):
        await base.send(2, CommandCodes.DECODE_MODE_STATUS_2CH, bytes([0xF0]))


async def test_send_success():
    """send() writes packet when connected and zone supported."""
    base = ClientBase()
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    base._writer = writer

    await base.send(1, CommandCodes.POWER, bytes([0xF0]))
    writer.write.assert_called_once()


async def test_request_not_connected():
    """request() raises NotConnectedException when not connected."""
    base = ClientBase()
    with pytest.raises(NotConnectedException):
        await base.request(1, CommandCodes.POWER, bytes([0xF0]))


async def test_request_unsupported_zone():
    """request() raises UnsupportedZone for zone-unsupported commands."""
    base = ClientBase()
    base._writer = MagicMock()
    with pytest.raises(UnsupportedZone):
        await base.request(2, CommandCodes.DECODE_MODE_STATUS_2CH, bytes([0xF0]))


async def test_request_send_only():
    """request() delegates to send() for SEND_ONLY commands and returns None."""
    base = ClientBase()
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    base._writer = writer

    # SIMULATE_RC5_IR_COMMAND has SEND_ONLY flag
    result = await base.request(1, CommandCodes.SIMULATE_RC5_IR_COMMAND, bytes([0x10, 0x01]))
    assert result is None


async def test_request_raises_response_exception():
    """request() raises ResponseException for non-STATUS_UPDATE answers."""
    base = ClientBase()
    base._writer = MagicMock()

    response = ResponsePacket(
        1, CommandCodes.POWER, AnswerCodes.COMMAND_NOT_RECOGNISED, b""
    )
    base.request_raw = AsyncMock(return_value=response)

    with pytest.raises(CommandNotRecognised):
        await base.request(1, CommandCodes.POWER, bytes([0xF0]))


async def test_process_data_server_disconnect():
    """_process_data sets _reader to None when packet is None (server disconnect)."""
    base = ClientBase()
    reader = asyncio.StreamReader()
    base._reader = reader
    # Feed a valid response that the reader will parse, but we'll mock read_response
    # to return None (server disconnect)
    with patch("arcam.fmj.client.read_response", new_callable=AsyncMock, return_value=None):
        await base._process_data(reader)
    assert base._reader is None


# --- Client unit tests ---


def test_client_host_port():
    """Client exposes host and port properties."""
    c = Client("192.168.1.10", 50000)
    assert c.host == "192.168.1.10"
    assert c.port == 50000


async def test_client_start_already_started():
    """Client.start() raises ArcamException if already started."""
    c = Client("localhost", 50000)
    c._writer = MagicMock()
    with pytest.raises(ArcamException, match="Already started"):
        await c.start()


async def test_client_start_connection_error():
    """Client.start() raises ConnectionFailed on ConnectionError."""
    c = Client("localhost", 59999)
    with patch("arcam.fmj.client.asyncio.open_connection", side_effect=ConnectionRefusedError()):
        with pytest.raises(ConnectionFailed):
            await c.start()


async def test_client_start_os_error():
    """Client.start() raises ConnectionFailed on OSError."""
    c = Client("localhost", 59999)
    with patch("arcam.fmj.client.asyncio.open_connection", side_effect=OSError("network unreachable")):
        with pytest.raises(ConnectionFailed):
            await c.start()


async def test_client_stop_connection_error():
    """Client.stop() swallows ConnectionError during close."""
    c = Client("localhost", 50000)
    writer = MagicMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock(side_effect=ConnectionResetError())
    c._writer = writer
    c._reader = MagicMock()

    await c.stop()
    assert c._writer is None
    assert c._reader is None


async def test_client_stop_os_error():
    """Client.stop() swallows OSError during close."""
    c = Client("localhost", 50000)
    writer = MagicMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock(side_effect=OSError("broken pipe"))
    c._writer = writer
    c._reader = MagicMock()

    await c.stop()
    assert c._writer is None
    assert c._reader is None


async def test_client_stop_noop_when_not_connected():
    """Client.stop() is a no-op when not connected."""
    c = Client("localhost", 50000)
    await c.stop()  # Should not raise


# --- ClientContext tests ---


async def test_client_context():
    """ClientContext starts, processes, and stops the client."""
    c = Client("localhost", 50000)
    c.start = AsyncMock()
    c.process = AsyncMock()
    c.stop = AsyncMock()

    async with ClientContext(c) as client:
        assert client is c
        c.start.assert_called_once()

    c.stop.assert_called_once()
