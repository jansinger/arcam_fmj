"""Exception classes for the Arcam protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .enums import AnswerCodes

if TYPE_CHECKING:
    from .enums import CommandCodes
    from .packets import ResponsePacket


class ArcamException(Exception):
    pass


class ConnectionFailed(ArcamException):
    pass


class NotConnectedException(ArcamException):
    pass


class UnsupportedZone(ArcamException):
    pass


class ResponseException(ArcamException):
    def __init__(
        self,
        ac: AnswerCodes | None = None,
        zn: int | None = None,
        cc: CommandCodes | None = None,
        data: bytes | None = None,
    ):
        self.ac = ac
        self.zn = zn
        self.cc = cc
        self.data = data
        super().__init__(f"'ac':{ac}, 'zn':{zn}, 'cc':{cc}, 'data':{data}")

    @staticmethod
    def from_response(response: ResponsePacket):
        kwargs = {"zn": response.zn, "cc": response.cc, "data": response.data}
        if response.ac == AnswerCodes.ZONE_INVALID:
            return InvalidZoneException(**kwargs)
        elif response.ac == AnswerCodes.COMMAND_NOT_RECOGNISED:
            return CommandNotRecognised(**kwargs)
        elif response.ac == AnswerCodes.PARAMETER_NOT_RECOGNISED:
            return ParameterNotRecognised(**kwargs)
        elif response.ac == AnswerCodes.COMMAND_INVALID_AT_THIS_TIME:
            return CommandInvalidAtThisTime(**kwargs)
        elif response.ac == AnswerCodes.INVALID_DATA_LENGTH:
            return InvalidDataLength(**kwargs)
        else:
            return ResponseException(ac=response.ac, **kwargs)


class InvalidZoneException(ResponseException):
    def __init__(
        self,
        zn: int | None = None,
        cc: CommandCodes | None = None,
        data: bytes | None = None,
    ):
        super().__init__(ac=AnswerCodes.ZONE_INVALID, zn=zn, cc=cc, data=data)


class CommandNotRecognised(ResponseException):
    def __init__(
        self,
        zn: int | None = None,
        cc: CommandCodes | None = None,
        data: bytes | None = None,
    ):
        super().__init__(ac=AnswerCodes.COMMAND_NOT_RECOGNISED, zn=zn, cc=cc, data=data)


class ParameterNotRecognised(ResponseException):
    def __init__(
        self,
        zn: int | None = None,
        cc: CommandCodes | None = None,
        data: bytes | None = None,
    ):
        super().__init__(ac=AnswerCodes.PARAMETER_NOT_RECOGNISED, zn=zn, cc=cc, data=data)


class CommandInvalidAtThisTime(ResponseException):
    def __init__(
        self,
        zn: int | None = None,
        cc: CommandCodes | None = None,
        data: bytes | None = None,
    ):
        super().__init__(ac=AnswerCodes.COMMAND_INVALID_AT_THIS_TIME, zn=zn, cc=cc, data=data)


class InvalidDataLength(ResponseException):
    def __init__(
        self,
        zn: int | None = None,
        cc: CommandCodes | None = None,
        data: bytes | None = None,
    ):
        super().__init__(ac=AnswerCodes.INVALID_DATA_LENGTH, zn=zn, cc=cc, data=data)


class InvalidPacket(ArcamException):
    pass


class NullPacket(ArcamException):
    pass
