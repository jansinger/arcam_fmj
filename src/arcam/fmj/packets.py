"""Packet classes and protocol I/O for the Arcam protocol."""

import asyncio
import logging
import re
from asyncio.exceptions import IncompleteReadError

import attr

from .enums import AnswerCodes, CommandCodes
from .exceptions import ConnectionFailed, InvalidPacket, NullPacket

PROTOCOL_STR = b"\x21"
PROTOCOL_ETR = b"\x0d"
PROTOCOL_EOF = b""

_LOGGER = logging.getLogger(__name__)
_WRITE_TIMEOUT = 3
_READ_TIMEOUT = 3


@attr.s
class ResponsePacket:
    """Represent a response from device."""

    zn: int = attr.ib()
    cc: CommandCodes = attr.ib()
    ac: AnswerCodes = attr.ib()
    data: bytes = attr.ib()

    def responds_to(self, request: "AmxDuetRequest | CommandPacket"):
        if not isinstance(request, CommandPacket):
            return False
        return self.zn == request.zn and self.cc == request.cc

    @staticmethod
    def from_bytes(data: bytes) -> "ResponsePacket":
        if len(data) < 6:
            raise InvalidPacket(f"Packet too short {data!r}")

        if data[4] != len(data) - 6:
            raise InvalidPacket(f"Invalid length in data {data!r}")

        return ResponsePacket(
            data[1],
            CommandCodes.from_int(data[2]),
            AnswerCodes.from_int(data[3]),
            data[5 : 5 + data[4]],
        )

    def to_bytes(self):
        return bytes(
            [
                *PROTOCOL_STR,
                self.zn,
                self.cc,
                self.ac,
                len(self.data),
                *self.data,
                *PROTOCOL_ETR,
            ]
        )


@attr.s
class CommandPacket:
    """Represent a command sent to device."""

    zn: int = attr.ib()
    cc: CommandCodes = attr.ib()
    data: bytes = attr.ib()

    def to_bytes(self):
        return bytes([*PROTOCOL_STR, self.zn, self.cc, len(self.data), *self.data, *PROTOCOL_ETR])

    @staticmethod
    def from_bytes(data: bytes) -> "CommandPacket":
        if len(data) < 5:
            raise InvalidPacket(f"Packet too short {data!r}")

        if data[3] != len(data) - 5:
            raise InvalidPacket(f"Invalid length in data {data!r}")

        return CommandPacket(data[1], CommandCodes.from_int(data[2]), data[4 : 4 + data[3]])


@attr.s
class AmxDuetRequest:
    @staticmethod
    def from_bytes(data: bytes) -> "AmxDuetRequest":
        if not data == b"AMX\r":
            raise InvalidPacket(f"Packet is not a amx request {data!r}")
        return AmxDuetRequest()

    def to_bytes(self):
        return b"AMX\r"


@attr.s
class AmxDuetResponse:
    values: dict[str, str] = attr.ib()

    @property
    def device_class(self) -> str | None:
        return self.values.get("Device-SDKClass")

    @property
    def device_make(self) -> str | None:
        return self.values.get("Device-Make")

    @property
    def device_model(self) -> str | None:
        return self.values.get("Device-Model")

    @property
    def device_revision(self) -> str | None:
        return self.values.get("Device-Revision")

    def responds_to(self, packet: AmxDuetRequest | CommandPacket):
        return isinstance(packet, AmxDuetRequest)

    @staticmethod
    def from_bytes(data: bytes) -> "AmxDuetResponse":
        if not data.startswith(b"AMXB"):
            raise InvalidPacket(f"Packet is not a amx response {data!r}")

        tags = re.findall(r"<(.+?)=(.+?)>", data[4:].decode("ASCII"))
        return AmxDuetResponse(dict(tags))

    def to_bytes(self):
        res = "AMXB" + "".join([f"<{key}={value}>" for key, value in self.values.items()]) + "\r"
        return res.encode("ASCII")


# --- Protocol I/O functions ---


async def _read_delimited(reader: asyncio.StreamReader, header_len) -> bytes | None:
    try:
        start = await reader.readexactly(1)
        if start == PROTOCOL_EOF:
            _LOGGER.debug("eof")
            return None

        if start == PROTOCOL_STR:
            header = await reader.readexactly(header_len - 1)
            data_len = await reader.readexactly(1)
            data = await reader.readexactly(int.from_bytes(data_len, "big"))
            etr = await reader.readexactly(1)

            if etr != PROTOCOL_ETR:
                raise InvalidPacket(f"unexpected etr byte {etr!r}")

            packet = bytes([*start, *header, *data_len, *data, *etr])
        elif start == b"\x01":
            # Sometimes the AMX header is sent as \x01^AMX
            header = await reader.readexactly(4)
            if header != b"^AMX":
                raise InvalidPacket(f"Unexpected AMX header: {header!r}")

            data = await reader.readuntil(PROTOCOL_ETR)
            packet = bytes([*b"AMX", *data])
        elif start == b"A":
            header = await reader.readexactly(2)
            if header != b"MX":
                raise InvalidPacket("Unexpected AMX header")

            data = await reader.readuntil(PROTOCOL_ETR)
            packet = bytes([*start, *header, *data])
        elif start == b"\x00":
            raise NullPacket()
        else:
            raise InvalidPacket(f"unexpected str byte {start!r}")

        return packet

    except TimeoutError as exception:
        raise ConnectionFailed() from exception
    except ConnectionError as exception:
        raise ConnectionFailed() from exception
    except OSError as exception:
        raise ConnectionFailed() from exception
    except IncompleteReadError as exception:
        raise ConnectionFailed() from exception


async def _read_response(
    reader: asyncio.StreamReader,
) -> ResponsePacket | AmxDuetResponse | None:
    data = await _read_delimited(reader, 4)
    if not data:
        return None

    if data.startswith(b"AMX"):
        return AmxDuetResponse.from_bytes(data)
    else:
        return ResponsePacket.from_bytes(data)


async def read_response(
    reader: asyncio.StreamReader,
) -> ResponsePacket | AmxDuetResponse | None:
    while True:
        try:
            data = await _read_response(reader)
        except InvalidPacket as e:
            _LOGGER.warning(str(e))
            continue
        except NullPacket:
            _LOGGER.debug("Ignoring 0x00 start byte sent from some devices")
            continue
        return data


async def _read_command(
    reader: asyncio.StreamReader,
) -> CommandPacket | AmxDuetRequest | None:
    data = await _read_delimited(reader, 3)
    if not data:
        return None
    if data.startswith(b"AMX"):
        return AmxDuetRequest.from_bytes(data)
    else:
        return CommandPacket.from_bytes(data)


async def read_command(
    reader: asyncio.StreamReader,
) -> CommandPacket | AmxDuetRequest | None:
    while True:
        try:
            data = await _read_command(reader)
        except InvalidPacket as e:
            _LOGGER.warning(str(e))
            continue
        return data


async def write_packet(
    writer: asyncio.StreamWriter,
    packet: CommandPacket | ResponsePacket | AmxDuetRequest | AmxDuetResponse,
) -> None:
    try:
        data = packet.to_bytes()
        writer.write(data)
        async with asyncio.timeout(_WRITE_TIMEOUT):
            await writer.drain()
    except TimeoutError as exception:
        raise ConnectionFailed() from exception
    except ConnectionError as exception:
        raise ConnectionFailed() from exception
    except OSError as exception:
        raise ConnectionFailed() from exception
