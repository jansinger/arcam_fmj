"""Zone state management for Arcam receivers.

Provides the State class which maintains a cached view of a receiver zone's
current settings and exposes getter/setter methods for all controllable
parameters. State is updated via polling (update()) and real-time listener
callbacks from the Client.
"""

import asyncio
import logging
from typing import Any, TypeVar

from . import (
    AmxDuetRequest,
    AmxDuetResponse,
    AnswerCodes,
    ApiModel,
    BluetoothStatus,
    CommandCodes,
    CommandInvalidAtThisTime,
    CommandNotRecognised,
    DecodeMode2CH,
    DecodeModeMCH,
    DolbyAudioMode,
    HdmiSettings,
    IncomingAudioConfig,
    IncomingAudioFormat,
    MenuCodes,
    NetworkPlaybackStatus,
    NotConnectedException,
    NowPlayingEncoder,
    NowPlayingInfo,
    NowPlayingSampleRate,
    PresetDetail,
    RoomEqNames,
    VideoParameters,
    ResponseException,
    ResponsePacket,
    SourceCodes,
    ZoneSettings,
    POWER_WRITE_SUPPORTED,
    MUTE_WRITE_SUPPORTED,
    SOURCE_WRITE_SUPPORTED,
    VOLUME_STEP_SUPPORTED,
    RC5CODE_SOURCE,
    RC5CODE_POWER,
    RC5CODE_MUTE,
    RC5CODE_VOLUME,
    RC5CODE_DECODE_MODE_2CH,
    RC5CODE_DECODE_MODE_MCH,
    UnsupportedZone,
    detect_api_model,
)
from .client import Client

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")


class State:
    """Cached state for a single receiver zone.

    Maintains an in-memory cache of raw protocol responses keyed by
    CommandCodes. Getter methods parse the raw bytes into typed values.
    Setter methods send commands to the receiver via the Client.

    Use as an async context manager to automatically register/unregister
    the real-time listener::

        async with State(client, zn=1) as state:
            await state.update()
            print(state.get_volume())

    Args:
        client: Connected Client instance for sending/receiving commands.
        zn: Zone number (1 for main zone, 2+ for additional zones).
        api_model: API version for the receiver model. Auto-detected
            during update() if AMX Duet response is available.
    """

    _state: dict[CommandCodes, bytes | None]
    _presets: dict[int, PresetDetail]

    def __init__(
        self, client: Client, zn: int, api_model: ApiModel = ApiModel.API450_SERIES
    ) -> None:
        self._zn = zn
        self._client = client
        self._state = dict()
        self._presets = dict()
        self._now_playing: dict[int, Any] = dict()
        self._amxduet: AmxDuetResponse | None = None
        self._api_model = api_model
        self._changed: asyncio.Event = asyncio.Event()

    async def start(self) -> None:
        """Register the real-time listener for state updates."""
        self._client.add_listener(self._listen)

    async def stop(self) -> None:
        """Unregister the real-time listener."""
        self._client.remove_listener(self._listen)

    async def __aenter__(self) -> "State":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def wait_changed(self) -> None:
        """Wait until the state changes due to a received packet.

        Blocks until ``_listen`` processes a packet, then clears the event
        so the next call will block again. Useful for event-driven monitoring
        instead of polling with ``repr()`` comparisons.
        """
        await self._changed.wait()
        self._changed.clear()

    def to_dict(self) -> dict[str, Any]:
        """Return all state values as a dictionary."""
        return {
            "POWER": self.get_power(),
            "VOLUME": self.get_volume(),
            "SOURCE": self.get_source(),
            "MUTE": self.get_mute(),
            "MENU": self.get_menu(),
            "INCOMING_VIDEO_PARAMETERS": self.get_incoming_video_parameters(),
            "INCOMING_AUDIO_FORMAT": self.get_incoming_audio_format(),
            "INCOMING_AUDIO_SAMPLE_RATE": self.get_incoming_audio_sample_rate(),
            "DECODE_MODE_2CH": self.get_decode_mode_2ch(),
            "DECODE_MODE_MCH": self.get_decode_mode_mch(),
            "DAB_STATION": self.get_dab_station(),
            "DLS_PDT": self.get_dls_pdt(),
            "RDS_INFORMATION": self.get_rds_information(),
            "TUNER_PRESET": self.get_tuner_preset(),
            "PRESET_DETAIL": self.get_preset_details(),
            "BASS": self.get_bass(),
            "TREBLE": self.get_treble(),
            "BALANCE": self.get_balance(),
            "SUBWOOFER_TRIM": self.get_subwoofer_trim(),
            "LIPSYNC_DELAY": self.get_lipsync_delay(),
            "DISPLAY_BRIGHTNESS": self.get_display_brightness(),
            "ROOM_EQUALIZATION": self.get_room_eq(),
            "COMPRESSION": self.get_compression(),
            "NETWORK_PLAYBACK_STATUS": self.get_network_playback_status(),
            "DOLBY_AUDIO": self.get_dolby_audio(),
            "NOW_PLAYING_INFO": (
                self.get_now_playing_info().to_dict()
                if self.get_now_playing_info() is not None
                else None
            ),
            "HDMI_SETTINGS": self.get_hdmi_settings(),
            "ZONE_SETTINGS": self.get_zone_settings(),
            "ROOM_EQ_NAMES": self.get_room_eq_names(),
            "BLUETOOTH_STATUS": self.get_bluetooth_status(),
        }

    def __repr__(self) -> str:
        return "State ({}) Amx ({})".format(
            self.to_dict(), self._amxduet.values if self._amxduet else {}
        )

    def _listen(self, packet: ResponsePacket | AmxDuetResponse) -> None:
        if isinstance(packet, AmxDuetResponse):
            self._amxduet = packet
            self._changed.set()
            return

        if packet.zn != self._zn:
            return

        if packet.ac == AnswerCodes.STATUS_UPDATE:
            self._state[packet.cc] = packet.data
        else:
            self._state[packet.cc] = None
        self._changed.set()

    @property
    def zn(self) -> int:
        return self._zn

    @property
    def client(self) -> Client:
        return self._client

    @property
    def model(self) -> str | None:
        if self._amxduet:
            return self._amxduet.device_model
        return None

    @property
    def revision(self) -> str | None:
        if self._amxduet:
            return self._amxduet.device_revision
        return None

    def get_rc5code(
        self, table: dict[tuple[ApiModel, int], dict[_T, bytes]], value: _T
    ) -> bytes:
        """Look up the RC5 IR command bytes for a given value and model/zone."""
        lookup = table.get((self._api_model, self._zn))
        if not lookup:
            raise ValueError(
                "Unknown mapping for model {} and zone {}".format(
                    self._api_model, self._zn
                )
            )

        command = lookup.get(value)
        if not command:
            raise ValueError(
                "Unknown command for model {} and zone {} and value {}".format(
                    self._api_model, self._zn, value
                )
            )
        return command

    def get(self, cc):
        return self._state[cc]

    def _get_int(self, cc: CommandCodes) -> int | None:
        value = self._state.get(cc)
        if value is None:
            return None
        return int.from_bytes(value, "big")

    async def _set_int(
        self, cc: CommandCodes, value: int, min_val: int = 0, max_val: int = 255
    ) -> None:
        if not min_val <= value <= max_val:
            raise ValueError(
                f"{cc.name} value {value} out of range [{min_val}, {max_val}]"
            )
        await self._client.request(self._zn, cc, bytes([value]))

    def get_incoming_video_parameters(self) -> VideoParameters | None:
        value = self._state.get(CommandCodes.INCOMING_VIDEO_PARAMETERS)
        if value is None:
            return None
        return VideoParameters.from_bytes(value)

    def get_incoming_audio_format(
        self,
    ) -> tuple[IncomingAudioFormat, IncomingAudioConfig] | tuple[None, None]:
        value = self._state.get(CommandCodes.INCOMING_AUDIO_FORMAT)
        if value is None:
            return None, None
        return (
            IncomingAudioFormat.from_int(value[0]),
            IncomingAudioConfig.from_int(value[1]),
        )

    def get_incoming_audio_sample_rate(self) -> int | None:
        value = self._state.get(CommandCodes.INCOMING_AUDIO_SAMPLE_RATE)
        if value is None:
            return None
        sample_rate_mapping = {
            0x00: 32000,
            0x01: 44100,
            0x02: 48000,
            0x03: 88200,
            0x04: 96000,
            0x05: 176400,
            0x06: 192000,
        }
        return sample_rate_mapping.get(value[0])

    def get_decode_mode_2ch(self) -> DecodeMode2CH | None:
        value = self._state.get(CommandCodes.DECODE_MODE_STATUS_2CH)
        if value is None:
            return None
        return DecodeMode2CH.from_bytes(value)

    async def set_decode_mode_2ch(self, mode: DecodeMode2CH) -> None:
        command = self.get_rc5code(RC5CODE_DECODE_MODE_2CH, mode)
        await self._client.request(
            self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
        )

    def get_decode_mode_mch(self) -> DecodeModeMCH | None:
        value = self._state.get(CommandCodes.DECODE_MODE_STATUS_MCH)
        if value is None:
            return None
        return DecodeModeMCH.from_bytes(value)

    async def set_decode_mode_mch(self, mode: DecodeModeMCH) -> None:
        command = self.get_rc5code(RC5CODE_DECODE_MODE_MCH, mode)
        await self._client.request(
            self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
        )

    _2CH_CONFIGS = frozenset({
        IncomingAudioConfig.DUAL_MONO,
        IncomingAudioConfig.MONO,
        IncomingAudioConfig.STEREO_ONLY,
        IncomingAudioConfig.STEREO_ONLY_LO_RO,
        IncomingAudioConfig.DUAL_MONO_LFE,
        IncomingAudioConfig.MONO_LFE,
        IncomingAudioConfig.STEREO_LFE,
        IncomingAudioConfig.STEREO_ONLY_LO_RO_LFE,
    })

    def get_2ch(self) -> bool:
        """Return if source is 2 channel or not."""
        audio_format, audio_config = self.get_incoming_audio_format()
        if audio_format in (
            IncomingAudioFormat.ANALOGUE_DIRECT,
            IncomingAudioFormat.UNDETECTED,
            None,
        ):
            return True
        if audio_format == IncomingAudioFormat.PCM:
            # PCM can be multichannel (e.g. 3/2.1) — check channel config
            if audio_config is None:
                return True
            return audio_config in self._2CH_CONFIGS
        return False

    def get_decode_mode(self) -> DecodeModeMCH | DecodeMode2CH | None:
        if self.get_2ch():
            result = self.get_decode_mode_2ch()
            if result is None:
                result = self.get_decode_mode_mch()
            return result
        else:
            result = self.get_decode_mode_mch()
            if result is None:
                result = self.get_decode_mode_2ch()
            return result

    def get_decode_modes(
        self,
    ) -> list[DecodeModeMCH] | list[DecodeMode2CH] | None:
        current = self.get_decode_mode()
        if isinstance(current, DecodeModeMCH):
            modes = RC5CODE_DECODE_MODE_MCH.get((self._api_model, self._zn))
            return list(modes) if modes else None
        elif isinstance(current, DecodeMode2CH):
            modes = RC5CODE_DECODE_MODE_2CH.get((self._api_model, self._zn))
            return list(modes) if modes else None
        if self.get_2ch():
            modes = RC5CODE_DECODE_MODE_2CH.get((self._api_model, self._zn))
            if not modes:
                modes = RC5CODE_DECODE_MODE_MCH.get((self._api_model, self._zn))
            return list(modes) if modes else None
        else:
            modes = RC5CODE_DECODE_MODE_MCH.get((self._api_model, self._zn))
            if not modes:
                modes = RC5CODE_DECODE_MODE_2CH.get((self._api_model, self._zn))
            return list(modes) if modes else None

    async def set_decode_mode(self, mode: str | DecodeModeMCH | DecodeMode2CH) -> None:
        if isinstance(mode, DecodeMode2CH):
            await self.set_decode_mode_2ch(mode)
        elif isinstance(mode, DecodeModeMCH):
            await self.set_decode_mode_mch(mode)
        elif self.get_2ch():
            try:
                await self.set_decode_mode_2ch(DecodeMode2CH[mode])
            except KeyError:
                await self.set_decode_mode_mch(DecodeModeMCH[mode])
        else:
            try:
                await self.set_decode_mode_mch(DecodeModeMCH[mode])
            except KeyError:
                await self.set_decode_mode_2ch(DecodeMode2CH[mode])

    def get_power(self) -> bool | None:
        """Return power state (True=on, False=off, None=unknown)."""
        value = self._state.get(CommandCodes.POWER)
        if value is None:
            return None
        return int.from_bytes(value, "big") == 0x01

    async def set_power(self, power: bool) -> None:
        """Turn zone on or off. Uses direct write or RC5 depending on model."""
        if self._api_model in POWER_WRITE_SUPPORTED:
            bool_to_hex = 0x01 if power else 0x00
            if not power:
                self._state[CommandCodes.POWER] = bytes([0])
            await self._client.request(
                self._zn, CommandCodes.POWER, bytes([bool_to_hex])
            )
        else:
            command = self.get_rc5code(RC5CODE_POWER, power)
            if power:
                await self._client.request(
                    self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
                )
            else:
                # seed with a response, since device might not
                # respond in timely fashion, so let's just
                # assume we succeded until response come
                # back.
                self._state[CommandCodes.POWER] = bytes([0])
                await self._client.send(
                    self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
                )

    def get_menu(self) -> MenuCodes | None:
        value = self._state.get(CommandCodes.MENU)
        if value is None:
            return None
        return MenuCodes.from_bytes(value)

    def get_mute(self) -> bool | None:
        """Return mute state (True=muted, False=unmuted, None=unknown)."""
        value = self._state.get(CommandCodes.MUTE)
        if value is None:
            return None
        return int.from_bytes(value, "big") == 0

    async def set_mute(self, mute: bool) -> None:
        """Set mute state. Uses direct write or RC5+re-query depending on model."""
        if self._api_model in MUTE_WRITE_SUPPORTED:
            bool_to_hex = 0x00 if mute else 0x01
            await self._client.request(
                self._zn, CommandCodes.MUTE, bytes([bool_to_hex])
            )
        else:
            command = self.get_rc5code(RC5CODE_MUTE, mute)
            await self._client.request(
                self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
            )
            # Query mute state after RC5 command to update _state[MUTE]
            # RC5 commands don't update the MUTE state directly, only SIMULATE_RC5_IR_COMMAND
            try:
                data = await self._client.request(
                    self._zn, CommandCodes.MUTE, bytes([0xF0])
                )
                self._state[CommandCodes.MUTE] = data
            except (
                ResponseException,
                NotConnectedException,
                UnsupportedZone,
                TimeoutError,
            ) as exc:
                self._state[CommandCodes.MUTE] = None
                _LOGGER.debug(
                    "Mute state query failed after RC5 command for zone %s: %s",
                    self._zn,
                    exc,
                )

    def get_source(self) -> SourceCodes | None:
        """Return the current input source, or None if unknown."""
        value = self._state.get(CommandCodes.CURRENT_SOURCE)
        if value is None:
            return None
        try:
            return SourceCodes.from_bytes(value, self._api_model, self._zn)
        except ValueError:
            return None

    def get_source_list(self) -> list[SourceCodes]:
        """Return the list of available sources for this model and zone."""
        return list(RC5CODE_SOURCE[(self._api_model, self._zn)].keys())

    async def set_source(self, src: SourceCodes) -> None:
        """Switch to the given input source."""
        if self._api_model in SOURCE_WRITE_SUPPORTED:
            value = src.to_bytes(self._api_model, self._zn)
            await self._client.request(self._zn, CommandCodes.CURRENT_SOURCE, value)
        else:
            command = self.get_rc5code(RC5CODE_SOURCE, src)
            await self._client.request(
                self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
            )

    def get_volume(self) -> int | None:
        """Return the current volume level (0-99), or None if unknown."""
        return self._get_int(CommandCodes.VOLUME)

    async def set_volume(self, volume: int) -> None:
        """Set volume level. Raises ValueError if not in range 0-99."""
        await self._set_int(CommandCodes.VOLUME, volume, 0, 99)

    async def inc_volume(self) -> None:
        """Increment volume by one step."""
        if self._api_model in VOLUME_STEP_SUPPORTED:
            await self._client.request(self._zn, CommandCodes.VOLUME, bytes([0xF1]))
        else:
            command = self.get_rc5code(RC5CODE_VOLUME, True)
            await self._client.request(
                self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
            )

    async def dec_volume(self) -> None:
        """Decrement volume by one step."""
        if self._api_model in VOLUME_STEP_SUPPORTED:
            await self._client.request(self._zn, CommandCodes.VOLUME, bytes([0xF2]))
        else:
            command = self.get_rc5code(RC5CODE_VOLUME, False)
            await self._client.request(
                self._zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, command
            )

    def get_bass(self) -> int | None:
        """Return bass EQ level (0-255), or None if unknown."""
        return self._get_int(CommandCodes.BASS_EQUALIZATION)

    async def set_bass(self, bass: int) -> None:
        """Set bass EQ level (0-255)."""
        await self._set_int(CommandCodes.BASS_EQUALIZATION, bass)

    def get_treble(self) -> int | None:
        """Return treble EQ level (0-255), or None if unknown."""
        return self._get_int(CommandCodes.TREBLE_EQUALIZATION)

    async def set_treble(self, treble: int) -> None:
        """Set treble EQ level (0-255)."""
        await self._set_int(CommandCodes.TREBLE_EQUALIZATION, treble)

    def get_balance(self) -> int | None:
        """Return balance level (0-255), or None if unknown."""
        return self._get_int(CommandCodes.BALANCE)

    async def set_balance(self, balance: int) -> None:
        """Set balance level (0-255)."""
        await self._set_int(CommandCodes.BALANCE, balance)

    def get_subwoofer_trim(self) -> int | None:
        """Return subwoofer trim level (0-255), or None if unknown."""
        return self._get_int(CommandCodes.SUBWOOFER_TRIM)

    async def set_subwoofer_trim(self, trim: int) -> None:
        """Set subwoofer trim level (0-255)."""
        await self._set_int(CommandCodes.SUBWOOFER_TRIM, trim)

    def get_lipsync_delay(self) -> int | None:
        """Return lip-sync delay in ms (0-255), or None if unknown."""
        return self._get_int(CommandCodes.LIPSYNC_DELAY)

    async def set_lipsync_delay(self, delay: int) -> None:
        """Set lip-sync delay in ms (0-255)."""
        await self._set_int(CommandCodes.LIPSYNC_DELAY, delay)

    def get_display_brightness(self) -> int | None:
        """Return display brightness (0=off, 1=dim, 2=bright), or None."""
        return self._get_int(CommandCodes.DISPLAY_BRIGHTNESS)

    async def set_display_brightness(self, brightness: int) -> None:
        """Set display brightness (0=off, 1=dim, 2=bright)."""
        await self._set_int(CommandCodes.DISPLAY_BRIGHTNESS, brightness, 0, 2)

    def get_room_eq(self) -> int | None:
        """Return Room EQ preset (0=off, 1-3=EQ1-3, 4=not calculated), or None."""
        return self._get_int(CommandCodes.ROOM_EQUALIZATION)

    async def set_room_eq(self, preset: int) -> None:
        """Set Room EQ preset (0=off, 1-3=EQ1-3, 4=not calculated)."""
        await self._set_int(CommandCodes.ROOM_EQUALIZATION, preset, 0, 4)

    def get_compression(self) -> int | None:
        """Return dynamic range compression mode (0-3), or None."""
        return self._get_int(CommandCodes.COMPRESSION)

    async def set_compression(self, compression: int) -> None:
        """Set dynamic range compression mode (0-3)."""
        await self._set_int(CommandCodes.COMPRESSION, compression, 0, 3)

    def get_network_playback_status(self) -> NetworkPlaybackStatus | None:
        """Return network playback status (stopped/playing/paused), or None."""
        value = self._state.get(CommandCodes.NETWORK_PLAYBACK_STATUS)
        if value is None:
            return None
        return NetworkPlaybackStatus.from_bytes(value)

    def get_dolby_audio(self) -> DolbyAudioMode | None:
        """Return Dolby Audio mode (off/movie/music/night), or None."""
        value = self._state.get(CommandCodes.DOLBY_VOLUME)
        if value is None:
            return None
        return DolbyAudioMode.from_bytes(value)

    async def set_dolby_audio(self, mode: DolbyAudioMode) -> None:
        """Set Dolby Audio mode."""
        await self._client.request(
            self._zn, CommandCodes.DOLBY_VOLUME, bytes([mode])
        )

    def get_now_playing_info(self) -> NowPlayingInfo | None:
        """Return now-playing info (title, artist, album, etc.), or None."""
        if not self._now_playing:
            return None
        return NowPlayingInfo.from_dict(self._now_playing)

    def get_hdmi_settings(self) -> HdmiSettings | None:
        """Return HDMI settings (OSD, output, lipsync, CEC, ARC), or None."""
        value = self._state.get(CommandCodes.HDMI_SETTINGS)
        if value is None:
            return None
        return HdmiSettings.from_bytes(value)

    def get_zone_settings(self) -> ZoneSettings | None:
        """Return Zone 2 settings (input, volume, max volume), or None."""
        value = self._state.get(CommandCodes.ZONE_SETTINGS)
        if value is None:
            return None
        return ZoneSettings.from_bytes(value)

    def get_room_eq_names(self) -> RoomEqNames | None:
        """Return custom Room EQ preset names (EQ1-3), or None."""
        value = self._state.get(CommandCodes.ROOM_EQ_NAMES)
        if value is None:
            return None
        return RoomEqNames.from_bytes(value)

    def get_bluetooth_status(self) -> tuple[BluetoothStatus, str] | None:
        """Return Bluetooth status and current track name, or None."""
        value = self._state.get(CommandCodes.VIDEO_OUTPUT_FRAME_RATE)
        if value is None:
            return None
        status = BluetoothStatus.from_bytes(value[:1])
        track = value[1:].decode("utf8").rstrip() if len(value) > 1 else ""
        return status, track

    def get_dab_station(self) -> str | None:
        """Return current DAB station name, or None."""
        value = self._state.get(CommandCodes.DAB_STATION)
        if value is None:
            return None
        return value.decode("utf8").rstrip()

    def get_dls_pdt(self) -> str | None:
        """Return DAB Dynamic Label Segment / Programme Data Text, or None."""
        value = self._state.get(CommandCodes.DLS_PDT_INFO)
        if value is None:
            return None
        return value.decode("utf8").rstrip()

    def get_rds_information(self) -> str | None:
        """Return FM RDS text, or None."""
        value = self._state.get(CommandCodes.RDS_INFORMATION)
        if value is None:
            return None
        return value.decode("utf8").rstrip()

    async def set_tuner_preset(self, preset: int) -> None:
        """Select a tuner preset by index."""
        await self._client.request(self._zn, CommandCodes.TUNER_PRESET, bytes([preset]))

    def get_tuner_preset(self) -> int | None:
        """Return current tuner preset index, or None if no preset active."""
        value = self._state.get(CommandCodes.TUNER_PRESET)
        if value is None or value == b"\xff":
            return None
        return int.from_bytes(value, "big")

    def get_preset_details(self) -> dict[int, PresetDetail]:
        """Return all known tuner presets as {index: PresetDetail}."""
        return self._presets

    async def update(self) -> None:
        """Poll the receiver for current state of all commands.

        For zone 1, queries all commands in parallel. For zone 2+, queries
        power first and only polls remaining commands if the zone is on.
        Clears state if the client is disconnected.
        """
        async def _update(cc: CommandCodes):
            try:
                data = await self._client.request(self._zn, cc, bytes([0xF0]))
                self._state[cc] = data
            except UnsupportedZone:
                _LOGGER.debug("Unsupported zone %s for %s", self._zn, cc)
            except ResponseException as e:
                _LOGGER.debug("Response error skipping %s - %s", cc, e.ac)
                self._state[cc] = None
            except NotConnectedException as e:
                _LOGGER.debug("Not connected skipping %s", cc)
                self._state[cc] = None
            except TimeoutError:
                _LOGGER.error("Timeout requesting %s", cc)

        async def _update_presets() -> None:
            presets = {}
            for preset in range(1, 51):
                try:
                    data = await self._client.request(
                        self._zn, CommandCodes.PRESET_DETAIL, bytes([preset])
                    )
                    if data != b"\x00":
                        presets[preset] = PresetDetail.from_bytes(data)
                except CommandInvalidAtThisTime:
                    break
                except CommandNotRecognised:
                    _LOGGER.debug("Presets not supported skipping %s", preset)
                    break
                except NotConnectedException as e:
                    _LOGGER.debug("Not connected skipping preset %s", preset)
                    return
                except TimeoutError:
                    _LOGGER.error("Timeout requesting preset %s", preset)
                    return
            self._presets = presets

        async def _update_now_playing() -> None:
            now_playing: dict[int, Any] = {}
            for sub_query in (0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5):
                try:
                    data = await self._client.request(
                        self._zn, CommandCodes.NOW_PLAYING_INFO, bytes([sub_query])
                    )
                    if sub_query in (0xF4, 0xF5):
                        # Sample rate and encoder are byte enums
                        if sub_query == 0xF4:
                            now_playing[sub_query] = NowPlayingSampleRate.from_bytes(data)
                        else:
                            now_playing[sub_query] = NowPlayingEncoder.from_bytes(data)
                    else:
                        # Text fields (title, artist, album, application)
                        now_playing[sub_query] = data.decode("utf8").rstrip()
                except CommandInvalidAtThisTime:
                    break
                except ResponseException as e:
                    _LOGGER.debug("Response error skipping now_playing 0x%02X - %s", sub_query, e.ac)
                except NotConnectedException:
                    _LOGGER.debug("Not connected skipping now_playing")
                    return
                except TimeoutError:
                    _LOGGER.error("Timeout requesting now_playing 0x%02X", sub_query)
                    return
            self._now_playing = now_playing

        async def _update_amxduet() -> None:
            try:
                data = await self._client.request_raw(AmxDuetRequest())
                self._amxduet = data

                detected = detect_api_model(data.device_model)
                if detected is not None:
                    self._api_model = detected

            except ResponseException as e:
                _LOGGER.debug("Response error skipping %s", e.ac)
            except NotConnectedException as e:
                _LOGGER.debug("Not connected skipping amx")
            except TimeoutError:
                _LOGGER.error("Timeout requesting amx")

        if self._client.connected:
            if self._amxduet is None:
                await _update_amxduet()

            if self._zn == 1:
                # Zone 1: poll all commands in parallel
                updates = [
                    _update(CommandCodes.POWER),
                    _update(CommandCodes.VOLUME),
                    _update(CommandCodes.MUTE),
                    _update(CommandCodes.CURRENT_SOURCE),
                    _update(CommandCodes.MENU),
                    _update(CommandCodes.DECODE_MODE_STATUS_2CH),
                    _update(CommandCodes.DECODE_MODE_STATUS_MCH),
                    _update(CommandCodes.INCOMING_VIDEO_PARAMETERS),
                    _update(CommandCodes.INCOMING_AUDIO_FORMAT),
                    _update(CommandCodes.INCOMING_AUDIO_SAMPLE_RATE),
                    _update(CommandCodes.DAB_STATION),
                    _update(CommandCodes.DLS_PDT_INFO),
                    _update(CommandCodes.RDS_INFORMATION),
                    _update(CommandCodes.TUNER_PRESET),
                    _update_presets(),
                    _update(CommandCodes.BASS_EQUALIZATION),
                    _update(CommandCodes.TREBLE_EQUALIZATION),
                    _update(CommandCodes.BALANCE),
                    _update(CommandCodes.SUBWOOFER_TRIM),
                    _update(CommandCodes.LIPSYNC_DELAY),
                    _update(CommandCodes.DISPLAY_BRIGHTNESS),
                    _update(CommandCodes.ROOM_EQUALIZATION),
                    _update(CommandCodes.COMPRESSION),
                    _update(CommandCodes.NETWORK_PLAYBACK_STATUS),
                    _update(CommandCodes.DOLBY_VOLUME),
                    _update(CommandCodes.HDMI_SETTINGS),
                    _update(CommandCodes.ZONE_SETTINGS),
                    _update(CommandCodes.ROOM_EQ_NAMES),
                    _update(CommandCodes.VIDEO_OUTPUT_FRAME_RATE),
                    _update_now_playing(),
                ]
                await asyncio.gather(*updates)
            else:
                # Zone 2+: poll power first, then only poll remaining
                # commands if the zone is actually powered on. This avoids
                # timeouts and retries for commands sent to inactive zones.
                await _update(CommandCodes.POWER)

                if self.get_power() is True:
                    updates = [
                        _update(CommandCodes.VOLUME),
                        _update(CommandCodes.MUTE),
                        _update(CommandCodes.CURRENT_SOURCE),
                        _update(CommandCodes.DAB_STATION),
                        _update(CommandCodes.DLS_PDT_INFO),
                        _update(CommandCodes.RDS_INFORMATION),
                        _update(CommandCodes.TUNER_PRESET),
                        _update_presets(),
                    ]
                    await asyncio.gather(*updates)
        else:
            if self._state:
                self._state = dict()
            if self._now_playing:
                self._now_playing = dict()
