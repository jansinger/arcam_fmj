"""Data classes for the Arcam protocol."""

from typing import Any

import attr

from .enums import (
    APIVERSION_450_SERIES,
    APIVERSION_860_SERIES,
    APIVERSION_HDA_SERIES,
    APIVERSION_PA_SERIES,
    APIVERSION_SA_SERIES,
    APIVERSION_ST_SERIES,
    ApiModel,
    IncomingVideoAspectRatio,
    IncomingVideoColorspace,
    NowPlayingEncoder,
    NowPlayingSampleRate,
    PresetType,
)
from .exceptions import InvalidPacket


@attr.s(slots=True, frozen=True)
class DeviceProfile:
    """Capabilities and metadata for a device model family.

    Consolidates per-series feature flags and model names into a single
    data structure. Use ``detect_api_model()`` to look up the profile
    for a given model name.
    """

    api_model: ApiModel = attr.ib()
    models: frozenset[str] = attr.ib()
    power_writable: bool = attr.ib(default=False)
    mute_writable: bool = attr.ib(default=False)
    source_writable: bool = attr.ib(default=False)
    volume_steppable: bool = attr.ib(default=False)


DEVICE_PROFILES: dict[ApiModel, DeviceProfile] = {
    ApiModel.API450_SERIES: DeviceProfile(
        api_model=ApiModel.API450_SERIES,
        models=frozenset(APIVERSION_450_SERIES),
    ),
    ApiModel.API860_SERIES: DeviceProfile(
        api_model=ApiModel.API860_SERIES,
        models=frozenset(APIVERSION_860_SERIES),
    ),
    ApiModel.APISA_SERIES: DeviceProfile(
        api_model=ApiModel.APISA_SERIES,
        models=frozenset(APIVERSION_SA_SERIES),
        power_writable=True,
        mute_writable=True,
        source_writable=True,
    ),
    ApiModel.APIHDA_SERIES: DeviceProfile(
        api_model=ApiModel.APIHDA_SERIES,
        models=frozenset(APIVERSION_HDA_SERIES),
    ),
    ApiModel.APIPA_SERIES: DeviceProfile(
        api_model=ApiModel.APIPA_SERIES,
        models=frozenset(APIVERSION_PA_SERIES),
        power_writable=True,
        mute_writable=True,
    ),
    ApiModel.APIST_SERIES: DeviceProfile(
        api_model=ApiModel.APIST_SERIES,
        models=frozenset(APIVERSION_ST_SERIES),
        power_writable=True,
        mute_writable=True,
        volume_steppable=True,
    ),
}


def detect_api_model(model_name: str) -> ApiModel | None:
    """Detect the API model family from a device model name.

    Args:
        model_name: Device model string (e.g. 'AVR30', 'SA20').

    Returns:
        The matching ApiModel, or None if the model is unknown.
    """
    for profile in DEVICE_PROFILES.values():
        if model_name in profile.models:
            return profile.api_model
    return None


@attr.s
class PresetDetail:
    index: int = attr.ib()
    type: PresetType | int = attr.ib()
    name: str = attr.ib()

    @staticmethod
    def from_bytes(data: bytes) -> "PresetDetail":
        if len(data) < 2:
            raise InvalidPacket(f"PresetDetail data too short: {len(data)} bytes")
        preset_type = PresetType.from_int(data[1])
        if preset_type == PresetType.FM_RDS_NAME or preset_type == PresetType.DAB:
            name = data[2:].decode("utf8").rstrip()
        elif preset_type == PresetType.FM_FREQUENCY:
            name = f"{data[2]}.{data[3]:02} MHz"
        elif preset_type == PresetType.AM_FREQUENCY:
            name = f"{data[2]}{data[3]:02} kHz"
        else:
            name = str(data[2:])
        return PresetDetail(data[0], preset_type, name)


@attr.s
class VideoParameters:
    horizontal_resolution: int = attr.ib()
    vertical_resolution: int = attr.ib()
    refresh_rate: int = attr.ib()
    interlaced: bool = attr.ib()
    aspect_ratio: IncomingVideoAspectRatio = attr.ib()
    colorspace: IncomingVideoColorspace = attr.ib()

    @staticmethod
    def from_bytes(data: bytes) -> "VideoParameters":
        if len(data) < 8:
            raise InvalidPacket(f"VideoParameters data too short: {len(data)} bytes")
        return VideoParameters(
            horizontal_resolution=int.from_bytes(data[0:2], "big"),
            vertical_resolution=int.from_bytes(data[2:4], "big"),
            refresh_rate=data[4],
            interlaced=(data[5] == 0x01),
            aspect_ratio=IncomingVideoAspectRatio.from_int(data[6]),
            colorspace=IncomingVideoColorspace.from_int(data[7]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizontal_resolution": self.horizontal_resolution,
            "vertical_resolution": self.vertical_resolution,
            "refresh_rate": self.refresh_rate,
            "interlaced": self.interlaced,
            "aspect_ratio": self.aspect_ratio,
            "colorspace": self.colorspace,
        }


@attr.s
class NowPlayingInfo:
    """Now playing information from HDA series receivers (command 0x64)."""

    title: str = attr.ib(default="")
    artist: str = attr.ib(default="")
    album: str = attr.ib(default="")
    application: str = attr.ib(default="")
    sample_rate: NowPlayingSampleRate | None = attr.ib(default=None)
    encoder: NowPlayingEncoder | None = attr.ib(default=None)

    @staticmethod
    def from_dict(data: dict) -> "NowPlayingInfo":
        return NowPlayingInfo(
            title=data.get(0xF0, ""),
            artist=data.get(0xF1, ""),
            album=data.get(0xF2, ""),
            application=data.get(0xF3, ""),
            sample_rate=data.get(0xF4),
            encoder=data.get(0xF5),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "application": self.application,
            "sample_rate": self.sample_rate,
            "encoder": self.encoder,
        }


@attr.s
class HdmiSettings:
    """HDMI settings (HDA series, command 0x2E). 10-byte response."""

    zone1_osd: bool = attr.ib()
    zone1_output: int = attr.ib()
    zone1_lipsync: int = attr.ib()
    hdmi_audio_to_tv: bool = attr.ib()
    hdmi_bypass_ip: bool = attr.ib()
    hdmi_bypass_source: int = attr.ib()
    cec_control: int = attr.ib()
    arc_control: int = attr.ib()
    tv_audio: int = attr.ib()
    power_off_control: int = attr.ib()

    @staticmethod
    def from_bytes(data: bytes) -> "HdmiSettings":
        if len(data) < 10:
            raise InvalidPacket(f"HdmiSettings data too short: {len(data)} bytes")
        return HdmiSettings(
            zone1_osd=data[0] != 0,
            zone1_output=data[1],
            zone1_lipsync=data[2],
            hdmi_audio_to_tv=data[3] != 0,
            hdmi_bypass_ip=data[4] != 0,
            hdmi_bypass_source=data[5],
            cec_control=data[6],
            arc_control=data[7],
            tv_audio=data[8],
            power_off_control=data[9],
        )


@attr.s
class ZoneSettings:
    """Zone settings (HDA multi-zone series, command 0x2F). 6-byte response."""

    zone2_input: int = attr.ib()
    zone2_status: int = attr.ib()
    zone2_volume: int = attr.ib()
    zone2_max_volume: int = attr.ib()
    zone2_fixed_volume: bool = attr.ib()
    zone2_max_on_volume: int = attr.ib()

    @staticmethod
    def from_bytes(data: bytes) -> "ZoneSettings":
        if len(data) < 6:
            raise InvalidPacket(f"ZoneSettings data too short: {len(data)} bytes")
        return ZoneSettings(
            zone2_input=data[0],
            zone2_status=data[1],
            zone2_volume=data[2],
            zone2_max_volume=data[3],
            zone2_fixed_volume=data[4] != 0,
            zone2_max_on_volume=data[5],
        )


@attr.s
class RoomEqNames:
    """Room EQ preset names (HDA series, command 0x34). Up to 60-byte response."""

    eq1: str = attr.ib(default="")
    eq2: str = attr.ib(default="")
    eq3: str = attr.ib(default="")

    @staticmethod
    def from_bytes(data: bytes) -> "RoomEqNames":
        n = len(data)
        eq1 = data[0:20].decode("ascii").rstrip("\x00").rstrip() if n >= 20 else ""
        eq2 = data[20:40].decode("ascii").rstrip("\x00").rstrip() if n >= 40 else ""
        eq3 = data[40:60].decode("ascii").rstrip("\x00").rstrip() if n >= 60 else ""
        return RoomEqNames(eq1=eq1, eq2=eq2, eq3=eq3)
