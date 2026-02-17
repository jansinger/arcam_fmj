"""Tests for protocol I/O: read_response, read_command, _read_delimited, write_packet."""

import asyncio

import pytest

from arcam.fmj import (
    AmxDuetRequest,
    AmxDuetResponse,
    AnswerCodes,
    CommandCodes,
    CommandPacket,
    ConnectionFailed,
    ResponsePacket,
    read_command,
    read_response,
    write_packet,
)

# --- read_response tests ---


async def test_read_response_valid_packet(make_reader):
    """Test read_response parses a valid ResponsePacket."""
    # Zone 1, POWER command, STATUS_UPDATE, data=0x01
    packet = ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([0x01]))
    reader = make_reader(packet.to_bytes())
    result = await read_response(reader)
    assert isinstance(result, ResponsePacket)
    assert result.zn == 1
    assert result.cc == CommandCodes.POWER
    assert result.ac == AnswerCodes.STATUS_UPDATE
    assert result.data == bytes([0x01])


async def test_read_response_amx_duet(make_reader):
    """Test read_response parses an AMX Duet response."""
    amx = AmxDuetResponse({"Device-Model": "AVR30", "Device-Make": "ARCAM"})
    reader = make_reader(amx.to_bytes())
    result = await read_response(reader)
    assert isinstance(result, AmxDuetResponse)
    assert result.device_model == "AVR30"


async def test_read_response_eof(make_reader):
    """Test read_response raises ConnectionFailed on EOF (IncompleteReadError)."""
    reader = make_reader(b"")
    with pytest.raises(ConnectionFailed):
        await read_response(reader)


async def test_read_response_skips_invalid_packet(make_reader):
    """Test read_response skips InvalidPacket and reads next valid packet."""
    # First: invalid start byte (0x99), then a valid response packet
    valid_packet = ResponsePacket(1, CommandCodes.VOLUME, AnswerCodes.STATUS_UPDATE, bytes([0x32]))
    data = b"\x99" + valid_packet.to_bytes()
    reader = make_reader(data)
    result = await read_response(reader)
    assert isinstance(result, ResponsePacket)
    assert result.cc == CommandCodes.VOLUME
    assert result.data == bytes([0x32])


async def test_read_response_skips_null_packet(make_reader):
    """Test read_response skips NullPacket (0x00 byte) and reads next valid packet."""
    valid_packet = ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([0x01]))
    data = b"\x00" + valid_packet.to_bytes()
    reader = make_reader(data)
    result = await read_response(reader)
    assert isinstance(result, ResponsePacket)
    assert result.cc == CommandCodes.POWER


async def test_read_response_connection_failed_on_incomplete(make_reader):
    """Test read_response raises ConnectionFailed on incomplete data."""
    # Start byte present but not enough data to complete the packet
    reader = make_reader(b"\x21\x01")
    with pytest.raises(ConnectionFailed):
        await read_response(reader)


# --- read_command tests ---


async def test_read_command_valid_packet(make_reader):
    """Test read_command parses a valid CommandPacket."""
    packet = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    reader = make_reader(packet.to_bytes())
    result = await read_command(reader)
    assert isinstance(result, CommandPacket)
    assert result.zn == 1
    assert result.cc == CommandCodes.POWER
    assert result.data == bytes([0xF0])


async def test_read_command_amx_duet(make_reader):
    """Test read_command parses an AMX Duet request."""
    reader = make_reader(b"AMX\r")
    result = await read_command(reader)
    assert isinstance(result, AmxDuetRequest)


async def test_read_command_eof(make_reader):
    """Test read_command raises ConnectionFailed on EOF."""
    reader = make_reader(b"")
    with pytest.raises(ConnectionFailed):
        await read_command(reader)


async def test_read_command_skips_invalid_packet(make_reader):
    """Test read_command skips InvalidPacket and reads next valid packet."""
    valid_packet = CommandPacket(1, CommandCodes.VOLUME, bytes([0xF0]))
    data = b"\x99" + valid_packet.to_bytes()
    reader = make_reader(data)
    result = await read_command(reader)
    assert isinstance(result, CommandPacket)
    assert result.cc == CommandCodes.VOLUME


# --- _read_delimited AMX header variant tests ---


async def test_read_response_amx_with_caret_header(make_reader):
    r"""Test _read_delimited handles \x01^AMX header variant."""
    # _read_delimited reads \x01, then ^AMX (4 bytes), then readuntil(\r).
    # It builds packet as b"AMX" + data (where data includes \r).
    # For AmxDuetResponse.from_bytes, packet must start with "AMXB".
    # So the stream after ^AMX must start with B: \x01^AMXB<tags>\r
    amx_data = b"\x01^AMXB<Device-Model=AVR30><Device-Make=ARCAM>\r"
    reader = make_reader(amx_data)
    result = await read_response(reader)
    assert isinstance(result, AmxDuetResponse)
    assert result.device_model == "AVR30"


async def test_read_response_amx_with_plain_header(make_reader):
    """Test _read_delimited handles plain AMX header (A + MX)."""
    # _read_delimited reads A, then MX (2 bytes), then readuntil(\r).
    # Packet = A + MX + data. For AmxDuetResponse: must be AMXB<tags>.
    # So stream: AMXB<tags>\r
    amx_data = b"AMXB<Device-Model=AVR850><Device-Make=ARCAM>\r"
    reader = make_reader(amx_data)
    result = await read_response(reader)
    assert isinstance(result, AmxDuetResponse)
    assert result.device_model == "AVR850"


async def test_read_response_amx_caret_invalid_header(make_reader):
    r"""Test _read_delimited raises InvalidPacket on \x01 + non-AMX header."""
    data = b"\x01XXXX"
    reader = make_reader(data)
    # read_response should skip the invalid packet, then hit EOF → ConnectionFailed
    with pytest.raises(ConnectionFailed):
        await read_response(reader)


async def test_read_response_amx_plain_a_invalid_header(make_reader):
    """Test _read_delimited raises InvalidPacket on A + non-MX header."""
    data = b"AXX"
    reader = make_reader(data)
    with pytest.raises(ConnectionFailed):
        await read_response(reader)


async def test_read_command_amx_with_caret_header(make_reader):
    r"""Test read_command handles \x01^AMX header variant."""
    amx_data = b"\x01^AMX\r"
    reader = make_reader(amx_data)
    result = await read_command(reader)
    assert isinstance(result, AmxDuetRequest)


# --- write_packet tests ---


async def test_write_packet_command():
    """Test write_packet writes CommandPacket bytes to writer."""
    # just verify the bytes written
    written = bytearray()

    class FakeWriter:
        def write(self, data):
            written.extend(data)

        async def drain(self):
            pass

        def close(self):
            pass

    packet = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    await write_packet(FakeWriter(), packet)
    assert bytes(written) == packet.to_bytes()


async def test_write_packet_response():
    """Test write_packet writes ResponsePacket bytes to writer."""
    written = bytearray()

    class FakeWriter:
        def write(self, data):
            written.extend(data)

        async def drain(self):
            pass

    packet = ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([0x01]))
    await write_packet(FakeWriter(), packet)
    assert bytes(written) == packet.to_bytes()


async def test_write_packet_timeout_raises_connection_failed():
    """write_packet raises ConnectionFailed on timeout."""

    class SlowWriter:
        def write(self, data):
            pass

        async def drain(self):
            raise TimeoutError()

    packet = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    with pytest.raises(ConnectionFailed):
        await write_packet(SlowWriter(), packet)


async def test_write_packet_connection_error_raises_connection_failed():
    """write_packet raises ConnectionFailed on ConnectionError."""

    class BrokenWriter:
        def write(self, data):
            pass

        async def drain(self):
            raise ConnectionResetError()

    packet = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    with pytest.raises(ConnectionFailed):
        await write_packet(BrokenWriter(), packet)


async def test_write_packet_os_error_raises_connection_failed():
    """write_packet raises ConnectionFailed on OSError."""

    class ErrorWriter:
        def write(self, data):
            pass

        async def drain(self):
            raise OSError("broken pipe")

    packet = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    with pytest.raises(ConnectionFailed):
        await write_packet(ErrorWriter(), packet)


# --- _read_delimited connection error tests ---


async def test_read_response_connection_error():
    """_read_delimited raises ConnectionFailed on ConnectionError."""
    reader = asyncio.StreamReader()
    reader.set_exception(ConnectionResetError())
    with pytest.raises(ConnectionFailed):
        await read_response(reader)


async def test_read_response_os_error():
    """_read_delimited raises ConnectionFailed on OSError."""
    reader = asyncio.StreamReader()
    reader.set_exception(OSError("network down"))
    with pytest.raises(ConnectionFailed):
        await read_response(reader)


async def test_read_command_connection_error():
    """_read_command raises ConnectionFailed on ConnectionError."""
    reader = asyncio.StreamReader()
    reader.set_exception(ConnectionResetError())
    with pytest.raises(ConnectionFailed):
        await read_command(reader)
