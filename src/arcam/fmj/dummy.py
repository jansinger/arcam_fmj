"""Dummy server for development and testing.

Provides a simulated Arcam receiver that responds to protocol commands
with configurable state. Useful for integration testing and development
without physical hardware.
"""

from . import (
    ApiModel,
    CommandCodes,
    CommandInvalidAtThisTime,
    CommandNotRecognised,
    SourceCodes,
    IncomingVideoAspectRatio,
    IncomingVideoColorspace,
    IncomingAudioFormat,
    IncomingAudioConfig,
    VideoParameters,
    ResponsePacket,
    AnswerCodes,
    RC5CODE_SOURCE,
    RC5CODE_DECODE_MODE_2CH,
    RC5CODE_DECODE_MODE_MCH,
    detect_api_model,
)
from .server import Server


class DummyServer(Server):
    """Simulated Arcam receiver for testing and development.

    Implements common command handlers (power, volume, source, decode modes,
    video/audio parameters, tuner presets) with in-memory state. Responds
    to both direct commands and RC5 IR simulation.

    Args:
        host: Bind address for the TCP server.
        port: Port number (default 50000).
        model: Device model name (e.g. 'AVR450', 'AVR850', 'AVR30').
            Must be in one of the known API version series.

    Raises:
        ValueError: If the model is not in any known series.
    """

    def __init__(self, host: str, port: int, model: str) -> None:
        super().__init__(host, port, model)

        detected = detect_api_model(model)
        if detected is None:
            raise ValueError(f"Unexpected model: {model}")
        self._api_version = detected

        rc5_key = (self._api_version, 1)

        self._volume = bytes([10])
        self._source = SourceCodes.PVR.to_bytes(self._api_version, 1)
        self._video_parameters = VideoParameters(
            horizontal_resolution=1920,
            vertical_resolution=1080,
            refresh_rate=60,
            interlaced=False,
            aspect_ratio=IncomingVideoAspectRatio.ASPECT_16_9,
            colorspace=IncomingVideoColorspace.NORMAL,
        )
        self._audio_format = bytes(
            [IncomingAudioFormat.PCM, IncomingAudioConfig.STEREO_ONLY]
        )
        self._audio_sample_rate = 48000
        self._decode_mode_2ch = bytes(
            [next(iter(RC5CODE_DECODE_MODE_2CH[rc5_key]))]
        )
        self._decode_mode_mch = bytes(
            [next(iter(RC5CODE_DECODE_MODE_MCH[rc5_key]))]
        )
        self._tuner_preset = b"\xff"
        self._presets: dict[bytes, bytes] = {
            b"\x01": b"\x03SR P1   ",
            b"\x02": b"\x03SR Klass",
            b"\x03": b"\x03P3 Star ",
            b"\x04": b"\x02SR P4   ",
            b"\x05": b"\x02SR P4   ",
            b"\x06": b"\x01jP",
        }

        def invert_rc5(data):
            return {value: key for key, value in data[rc5_key].items()}

        self._source_rc5 = invert_rc5(RC5CODE_SOURCE)
        self._decode_mode_2ch_rc5 = invert_rc5(RC5CODE_DECODE_MODE_2CH)
        self._decode_mode_mch_rc5 = invert_rc5(RC5CODE_DECODE_MODE_MCH)

        self.register_handler(
            0x01, CommandCodes.POWER, bytes([0xF0]), self.get_power
        )
        self.register_handler(
            0x01, CommandCodes.VOLUME, bytes([0xF0]), self.get_volume
        )
        self.register_handler(0x01, CommandCodes.VOLUME, None, self.set_volume)
        self.register_handler(
            0x01, CommandCodes.CURRENT_SOURCE, bytes([0xF0]), self.get_source
        )
        self.register_handler(
            0x01,
            CommandCodes.INCOMING_VIDEO_PARAMETERS,
            bytes([0xF0]),
            self.get_incoming_video_parameters,
        )
        self.register_handler(
            0x01,
            CommandCodes.INCOMING_AUDIO_FORMAT,
            bytes([0xF0]),
            self.get_incoming_audio_format,
        )
        self.register_handler(
            0x01,
            CommandCodes.INCOMING_AUDIO_SAMPLE_RATE,
            bytes([0xF0]),
            self.get_incoming_audio_sample_rate,
        )
        self.register_handler(
            0x01,
            CommandCodes.DECODE_MODE_STATUS_2CH,
            bytes([0xF0]),
            self.get_decode_mode_2ch,
        )
        self.register_handler(
            0x01,
            CommandCodes.DECODE_MODE_STATUS_MCH,
            bytes([0xF0]),
            self.get_decode_mode_mch,
        )
        self.register_handler(
            0x01, CommandCodes.SIMULATE_RC5_IR_COMMAND, None, self.ir_command
        )
        self.register_handler(
            0x01, CommandCodes.PRESET_DETAIL, None, self.get_preset_detail
        )
        self.register_handler(
            0x01, CommandCodes.TUNER_PRESET, bytes([0xF0]), self.get_tuner_preset
        )
        self.register_handler(
            0x01, CommandCodes.TUNER_PRESET, None, self.set_tuner_preset
        )

    def get_power(self, **kwargs):
        return bytes([1])

    def set_volume(self, data, **kwargs):
        self._volume = data
        return self._volume

    def get_volume(self, **kwargs):
        return self._volume

    def get_source(self, **kwargs):
        return self._source

    def set_source(self, data, **kwargs):
        self._source = data
        return self._source

    def ir_command(self, data, **kwargs):
        source = self._source_rc5.get(data)
        if source:
            source_bytes = source.to_bytes(self._api_version, 1)
            self.set_source(source_bytes)
            return [
                ResponsePacket(
                    zn=0x01,
                    cc=CommandCodes.SIMULATE_RC5_IR_COMMAND,
                    ac=AnswerCodes.STATUS_UPDATE,
                    data=data,
                ),
                ResponsePacket(
                    zn=0x01,
                    cc=CommandCodes.CURRENT_SOURCE,
                    ac=AnswerCodes.STATUS_UPDATE,
                    data=source_bytes,
                ),
            ]
        decode_mode_2ch = self._decode_mode_2ch_rc5.get(data)
        if decode_mode_2ch:
            self._decode_mode_2ch = bytes([decode_mode_2ch])
            return [
                ResponsePacket(
                    zn=0x01,
                    cc=CommandCodes.SIMULATE_RC5_IR_COMMAND,
                    ac=AnswerCodes.STATUS_UPDATE,
                    data=data,
                ),
                ResponsePacket(
                    zn=0x01,
                    cc=CommandCodes.DECODE_MODE_STATUS_2CH,
                    ac=AnswerCodes.STATUS_UPDATE,
                    data=self._decode_mode_2ch,
                ),
            ]

        decode_mode_mch = self._decode_mode_mch_rc5.get(data)
        if decode_mode_mch:
            self._decode_mode_mch = bytes([decode_mode_mch])
            return [
                ResponsePacket(
                    zn=0x01,
                    cc=CommandCodes.SIMULATE_RC5_IR_COMMAND,
                    ac=AnswerCodes.STATUS_UPDATE,
                    data=data,
                ),
                ResponsePacket(
                    zn=0x01,
                    cc=CommandCodes.DECODE_MODE_STATUS_MCH,
                    ac=AnswerCodes.STATUS_UPDATE,
                    data=self._decode_mode_mch,
                ),
            ]

        raise CommandNotRecognised()

    def get_decode_mode_2ch(self, **kwargs):
        return self._decode_mode_2ch

    def get_decode_mode_mch(self, **kwargs):
        return self._decode_mode_mch

    def get_incoming_video_parameters(self, **kwargs):
        return self._video_parameters

    def get_incoming_audio_format(self, **kwargs):
        return self._audio_format

    def get_incoming_audio_sample_rate(self, **kwargs):
        return self._audio_sample_rate

    def get_tuner_preset(self, **kwargs):
        return self._tuner_preset

    def set_tuner_preset(self, data, **kwargs):
        self._tuner_preset = data
        return self._tuner_preset

    def get_preset_detail(self, data, **kwargs):
        preset = self._presets.get(data)
        if preset:
            return data + preset
        else:
            raise CommandInvalidAtThisTime()
