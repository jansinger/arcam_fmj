"""Tests for arcam.fmj.__init__ module fixes."""

import pytest

from arcam.fmj import (
    APIVERSION_DAB_SERIES,
    APIVERSION_HDA_SERIES,
    DEVICE_PROFILES,
    SA_SOURCE_MAPPING,
    AmxDuetRequest,
    AmxDuetResponse,
    AnswerCodes,
    ApiModel,
    CommandCodes,
    CommandInvalidAtThisTime,
    CommandNotRecognised,
    CommandPacket,
    HdmiSettings,
    InvalidDataLength,
    InvalidPacket,
    InvalidZoneException,
    ParameterNotRecognised,
    PresetDetail,
    ResponseException,
    ResponsePacket,
    SourceCodes,
    VideoParameters,
    ZoneSettings,
    detect_api_model,
)

# --- Tests for APIVERSION_DAB_SERIES fix ---


def test_dab_series_contains_full_model_names():
    """APIVERSION_DAB_SERIES contains full model name strings, not individual characters."""
    expected_models = {"AV860", "AVR850", "AVR550", "AVR390", "RV-6", "RV-9", "MC-10"}
    for model in expected_models:
        assert model in APIVERSION_DAB_SERIES, f"{model} should be in APIVERSION_DAB_SERIES"


def test_dab_series_no_single_characters():
    """Test that APIVERSION_DAB_SERIES doesn't contain single characters from the bug."""
    # If the bug existed, individual characters like 'A', 'V', '8' would be in the set
    for char in ["A", "V", "8", "6", "0"]:
        # These single chars should NOT be in the set (unless they happen to be valid model names)
        if len(char) == 1:
            assert char not in APIVERSION_DAB_SERIES, (
                f"Single character '{char}' should not be in APIVERSION_DAB_SERIES"
            )


def test_dab_series_includes_hda_models():
    """Test that APIVERSION_DAB_SERIES includes all HDA series models."""
    for model in APIVERSION_HDA_SERIES:
        assert model in APIVERSION_DAB_SERIES, (
            f"HDA model {model} should be in APIVERSION_DAB_SERIES"
        )


def test_dab_series_includes_base_models():
    """Test that APIVERSION_DAB_SERIES includes original base models."""
    assert "AVR450" in APIVERSION_DAB_SERIES
    assert "AVR750" in APIVERSION_DAB_SERIES


# --- Tests for SA_SOURCE_MAPPING no duplicates ---


def test_sa_source_mapping_no_duplicate_bytes():
    """Test that SA_SOURCE_MAPPING has no duplicate byte values."""
    seen_values = {}
    for source, byte_val in SA_SOURCE_MAPPING.items():
        assert byte_val not in seen_values.values() or all(
            k == source for k, v in seen_values.items() if v == byte_val
        ), (
            f"Duplicate byte value {byte_val!r} for {source} "
            f"(already used by {[k for k, v in seen_values.items() if v == byte_val]})"
        )
        seen_values[source] = byte_val


def test_sa_source_mapping_net_usb_different():
    """Test that NET and USB have different byte mappings in SA_SOURCE_MAPPING."""
    assert SA_SOURCE_MAPPING[SourceCodes.NET] != SA_SOURCE_MAPPING[SourceCodes.USB]


# --- Tests for PresetDetail frequency formatting ---


def test_preset_detail_fm_frequency_zero_padded():
    """Test that FM frequency formatting uses zero-padded seconds."""
    # data[0]=preset index, data[1]=type (0x01=FM), data[2]=major, data[3]=minor
    data = bytes([1, 0x01, 98, 5])
    detail = PresetDetail.from_bytes(data)
    assert detail.name == "98.05 MHz"


def test_preset_detail_am_frequency_zero_padded():
    """Test that AM frequency formatting uses zero-padded value."""
    data = bytes([1, 0x00, 5, 3])
    detail = PresetDetail.from_bytes(data)
    assert detail.name == "503 kHz"


def test_preset_detail_fm_rds_name():
    """Test FM RDS name parsing."""
    name_bytes = b"SR P1   "
    data = bytes([1, 0x02]) + name_bytes
    detail = PresetDetail.from_bytes(data)
    assert detail.name == "SR P1"


def test_preset_detail_dab_name():
    """Test DAB station name parsing."""
    name_bytes = b"P3 Star "
    data = bytes([1, 0x03]) + name_bytes
    detail = PresetDetail.from_bytes(data)
    assert detail.name == "P3 Star"


# --- Tests for responds_to rename ---


def test_response_packet_responds_to():
    """Test that ResponsePacket.responds_to works (renamed from respons_to)."""
    response = ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([1]))
    command = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    assert response.responds_to(command) is True


def test_response_packet_responds_to_different_command():
    """Test that responds_to returns False for different commands."""
    response = ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([1]))
    command = CommandPacket(1, CommandCodes.VOLUME, bytes([0xF0]))
    assert response.responds_to(command) is False


def test_response_packet_responds_to_amx_request():
    """Test that ResponsePacket.responds_to returns False for AmxDuetRequest."""
    response = ResponsePacket(1, CommandCodes.POWER, AnswerCodes.STATUS_UPDATE, bytes([1]))
    request = AmxDuetRequest()
    assert response.responds_to(request) is False


def test_amx_duet_response_responds_to():
    """Test that AmxDuetResponse.responds_to works (renamed from respons_to)."""
    amx_response = AmxDuetResponse({"Device-Model": "AVR450"})
    amx_request = AmxDuetRequest()
    assert amx_response.responds_to(amx_request) is True


def test_amx_duet_response_responds_to_command_packet():
    """Test that AmxDuetResponse.responds_to returns False for CommandPacket."""
    amx_response = AmxDuetResponse({"Device-Model": "AVR450"})
    command = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    assert amx_response.responds_to(command) is False


# --- Tests for NetworkPlaybackStatus enum ---


def test_network_playback_status_values():
    """Test that NetworkPlaybackStatus enum has correct values per SH289E spec."""
    from arcam.fmj import NetworkPlaybackStatus

    assert NetworkPlaybackStatus.STOPPED == 0x00
    assert NetworkPlaybackStatus.TRANSITIONING == 0x01
    assert NetworkPlaybackStatus.PLAYING == 0x02
    assert NetworkPlaybackStatus.PAUSED == 0x03


def test_network_playback_status_from_bytes():
    """Test NetworkPlaybackStatus parsing from bytes."""
    from arcam.fmj import NetworkPlaybackStatus

    assert NetworkPlaybackStatus.from_bytes(bytes([0x00])) == NetworkPlaybackStatus.STOPPED
    assert NetworkPlaybackStatus.from_bytes(bytes([0x02])) == NetworkPlaybackStatus.PLAYING
    assert NetworkPlaybackStatus.from_bytes(bytes([0x03])) == NetworkPlaybackStatus.PAUSED


# --- Tests for DolbyAudioMode enum ---


def test_dolby_audio_mode_values():
    """Test that DolbyAudioMode has 4 modes per SH289E spec (not boolean)."""
    from arcam.fmj import DolbyAudioMode

    assert DolbyAudioMode.OFF == 0x00
    assert DolbyAudioMode.MOVIE == 0x01
    assert DolbyAudioMode.MUSIC == 0x02
    assert DolbyAudioMode.NIGHT == 0x03


def test_dolby_audio_mode_from_bytes():
    """Test DolbyAudioMode parsing from bytes."""
    from arcam.fmj import DolbyAudioMode

    assert DolbyAudioMode.from_bytes(bytes([0x00])) == DolbyAudioMode.OFF
    assert DolbyAudioMode.from_bytes(bytes([0x01])) == DolbyAudioMode.MOVIE
    assert DolbyAudioMode.from_bytes(bytes([0x03])) == DolbyAudioMode.NIGHT


# --- Tests for NowPlayingSampleRate enum ---


def test_now_playing_sample_rate_values():
    """Test NowPlayingSampleRate enum values per SH289E spec."""
    from arcam.fmj import NowPlayingSampleRate

    assert NowPlayingSampleRate.KHZ_32 == 0x00
    assert NowPlayingSampleRate.KHZ_44_1 == 0x01
    assert NowPlayingSampleRate.KHZ_48 == 0x02
    assert NowPlayingSampleRate.KHZ_88_2 == 0x03
    assert NowPlayingSampleRate.KHZ_96 == 0x04
    assert NowPlayingSampleRate.KHZ_176_4 == 0x05
    assert NowPlayingSampleRate.KHZ_192 == 0x06
    assert NowPlayingSampleRate.UNKNOWN == 0x07
    assert NowPlayingSampleRate.UNDETECTED == 0x08


# --- Tests for NowPlayingEncoder enum ---


def test_now_playing_encoder_values():
    """Test NowPlayingEncoder enum values per SH289E spec."""
    from arcam.fmj import NowPlayingEncoder

    assert NowPlayingEncoder.MP3 == 0x00
    assert NowPlayingEncoder.WAV == 0x01
    assert NowPlayingEncoder.WMA == 0x02
    assert NowPlayingEncoder.FLAC == 0x03
    assert NowPlayingEncoder.ALAC == 0x04
    assert NowPlayingEncoder.MQA == 0x05
    assert NowPlayingEncoder.UNKNOWN == 0x0A


# --- Tests for BluetoothStatus enum ---


def test_bluetooth_status_values():
    """Test BluetoothStatus enum values per SH289E spec."""
    from arcam.fmj import BluetoothStatus

    assert BluetoothStatus.NO_CONNECTION == 0x00
    assert BluetoothStatus.CONNECTED_PAUSED == 0x01
    assert BluetoothStatus.PLAYING_SBC == 0x02
    assert BluetoothStatus.PLAYING_AAC == 0x03
    assert BluetoothStatus.PLAYING_APTX == 0x04
    assert BluetoothStatus.PLAYING_APTX_HD == 0x05


# --- Tests for NowPlayingInfo data class ---


def test_now_playing_info_from_dict_full():
    """Test NowPlayingInfo.from_dict with all fields populated."""
    from arcam.fmj import NowPlayingEncoder, NowPlayingInfo, NowPlayingSampleRate

    data = {
        0xF0: "Test Song",
        0xF1: "Test Artist",
        0xF2: "Test Album",
        0xF3: "Spotify",
        0xF4: NowPlayingSampleRate.KHZ_44_1,
        0xF5: NowPlayingEncoder.FLAC,
    }
    info = NowPlayingInfo.from_dict(data)
    assert info.title == "Test Song"
    assert info.artist == "Test Artist"
    assert info.album == "Test Album"
    assert info.application == "Spotify"
    assert info.sample_rate == NowPlayingSampleRate.KHZ_44_1
    assert info.encoder == NowPlayingEncoder.FLAC


def test_now_playing_info_from_dict_partial():
    """Test NowPlayingInfo.from_dict with only title, defaults empty."""
    from arcam.fmj import NowPlayingInfo

    data = {0xF0: "Only Title"}
    info = NowPlayingInfo.from_dict(data)
    assert info.title == "Only Title"
    assert info.artist == ""
    assert info.album == ""
    assert info.application == ""
    assert info.sample_rate is None
    assert info.encoder is None


def test_now_playing_info_from_dict_empty():
    """Test NowPlayingInfo.from_dict with empty dict."""
    from arcam.fmj import NowPlayingInfo

    info = NowPlayingInfo.from_dict({})
    assert info.title == ""
    assert info.artist == ""


def test_now_playing_info_to_dict():
    """Test NowPlayingInfo.to_dict round-trip."""
    from arcam.fmj import NowPlayingEncoder, NowPlayingInfo, NowPlayingSampleRate

    info = NowPlayingInfo(
        title="Song",
        artist="Artist",
        album="Album",
        application="App",
        sample_rate=NowPlayingSampleRate.KHZ_48,
        encoder=(
            NowPlayingEncoder.AAC if hasattr(NowPlayingEncoder, "AAC") else NowPlayingEncoder.MP3
        ),
    )
    d = info.to_dict()
    assert d["title"] == "Song"
    assert d["artist"] == "Artist"
    assert d["album"] == "Album"
    assert len(d) == 6


# --- Tests for HdmiSettings data class ---


def test_hdmi_settings_from_bytes():
    """Test HdmiSettings.from_bytes parsing 10-byte response."""
    from arcam.fmj import HdmiSettings

    # Zone1 OSD=On, Out=Out1, Lipsync=50ms, AudioToTV=On,
    # Bypass=Off, Source=STB, CEC=Output1, ARC=Auto, TV Audio=Auto, PowerOff=Auto
    data = bytes([0x01, 0x01, 0x32, 0x01, 0x00, 0x01, 0x01, 0x01, 0x01, 0x01])
    settings = HdmiSettings.from_bytes(data)
    assert settings.zone1_osd is True
    assert settings.zone1_output == 1
    assert settings.zone1_lipsync == 0x32
    assert settings.hdmi_audio_to_tv is True
    assert settings.hdmi_bypass_ip is False
    assert settings.hdmi_bypass_source == 1
    assert settings.cec_control == 1
    assert settings.arc_control == 1
    assert settings.tv_audio == 1
    assert settings.power_off_control == 1


def test_hdmi_settings_from_bytes_all_off():
    """Test HdmiSettings.from_bytes with all features off."""
    from arcam.fmj import HdmiSettings

    data = bytes([0x00] * 10)
    settings = HdmiSettings.from_bytes(data)
    assert settings.zone1_osd is False
    assert settings.zone1_output == 0
    assert settings.hdmi_audio_to_tv is False
    assert settings.hdmi_bypass_ip is False
    assert settings.cec_control == 0
    assert settings.arc_control == 0


# --- Tests for ZoneSettings data class ---


def test_zone_settings_from_bytes():
    """Test ZoneSettings.from_bytes parsing 6-byte response."""
    from arcam.fmj import ZoneSettings

    # Input=CD, Status=On, Volume=50, MaxVol=83, Fixed=No, MaxOnVol=50
    data = bytes([0x01, 0x01, 0x32, 0x53, 0x00, 0x32])
    settings = ZoneSettings.from_bytes(data)
    assert settings.zone2_input == 1
    assert settings.zone2_status == 1
    assert settings.zone2_volume == 0x32
    assert settings.zone2_max_volume == 0x53
    assert settings.zone2_fixed_volume is False
    assert settings.zone2_max_on_volume == 0x32


def test_zone_settings_fixed_volume():
    """Test ZoneSettings with fixed volume enabled."""
    from arcam.fmj import ZoneSettings

    data = bytes([0x00, 0x01, 0x32, 0x53, 0x01, 0x32])
    settings = ZoneSettings.from_bytes(data)
    assert settings.zone2_fixed_volume is True


# --- Tests for RoomEqNames data class ---


def test_room_eq_names_from_bytes_full():
    """Test RoomEqNames.from_bytes with all 3 names (60 bytes)."""
    from arcam.fmj import RoomEqNames

    eq1 = b"Living Room\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    eq2 = b"Cinema Mode\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    eq3 = b"Music Room\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    data = eq1 + eq2 + eq3
    names = RoomEqNames.from_bytes(data)
    assert names.eq1 == "Living Room"
    assert names.eq2 == "Cinema Mode"
    assert names.eq3 == "Music Room"


def test_room_eq_names_from_bytes_partial():
    """Test RoomEqNames.from_bytes with only 1 EQ (20 bytes)."""
    from arcam.fmj import RoomEqNames

    eq1 = b"My EQ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    names = RoomEqNames.from_bytes(eq1)
    assert names.eq1 == "My EQ"
    assert names.eq2 == ""
    assert names.eq3 == ""


# --- Tests for from_bytes boundary checks ---


def test_preset_detail_from_bytes_too_short():
    """Test PresetDetail.from_bytes raises InvalidPacket on short data."""
    with pytest.raises(InvalidPacket):
        PresetDetail.from_bytes(b"\x00")


def test_preset_detail_from_bytes_empty():
    """Test PresetDetail.from_bytes raises InvalidPacket on empty data."""
    with pytest.raises(InvalidPacket):
        PresetDetail.from_bytes(b"")


def test_video_parameters_from_bytes_too_short():
    """Test VideoParameters.from_bytes raises InvalidPacket on short data."""
    with pytest.raises(InvalidPacket):
        VideoParameters.from_bytes(b"\x00" * 7)


def test_video_parameters_from_bytes_empty():
    """Test VideoParameters.from_bytes raises InvalidPacket on empty data."""
    with pytest.raises(InvalidPacket):
        VideoParameters.from_bytes(b"")


def test_hdmi_settings_from_bytes_too_short():
    """Test HdmiSettings.from_bytes raises InvalidPacket on short data."""
    with pytest.raises(InvalidPacket):
        HdmiSettings.from_bytes(b"\x00" * 9)


def test_hdmi_settings_from_bytes_empty():
    """Test HdmiSettings.from_bytes raises InvalidPacket on empty data."""
    with pytest.raises(InvalidPacket):
        HdmiSettings.from_bytes(b"")


def test_zone_settings_from_bytes_too_short():
    """Test ZoneSettings.from_bytes raises InvalidPacket on short data."""
    with pytest.raises(InvalidPacket):
        ZoneSettings.from_bytes(b"\x00" * 5)


def test_zone_settings_from_bytes_empty():
    """Test ZoneSettings.from_bytes raises InvalidPacket on empty data."""
    with pytest.raises(InvalidPacket):
        ZoneSettings.from_bytes(b"")


# --- Tests for VideoParameters happy-path ---


def test_video_parameters_from_bytes_happy_path():
    """Test VideoParameters.from_bytes with valid 8-byte data."""
    # 1920x1080, 60Hz, interlaced, 16:9, HDR10
    data = bytes([0x07, 0x80, 0x04, 0x38, 0x3C, 0x01, 0x02, 0x01])
    params = VideoParameters.from_bytes(data)
    assert params.horizontal_resolution == 1920
    assert params.vertical_resolution == 1080
    assert params.refresh_rate == 60
    assert params.interlaced is True
    assert params.aspect_ratio == 0x02  # ASPECT_16_9
    assert params.colorspace == 0x01  # HDR10


def test_video_parameters_from_bytes_progressive():
    """Test VideoParameters.from_bytes with progressive scan."""
    data = bytes([0x0F, 0x00, 0x08, 0x70, 0x3C, 0x00, 0x02, 0x00])
    params = VideoParameters.from_bytes(data)
    assert params.horizontal_resolution == 3840
    assert params.vertical_resolution == 2160
    assert params.refresh_rate == 60
    assert params.interlaced is False


def test_video_parameters_to_dict():
    """Test VideoParameters.to_dict returns all fields."""
    data = bytes([0x07, 0x80, 0x04, 0x38, 0x3C, 0x00, 0x02, 0x01])
    params = VideoParameters.from_bytes(data)
    d = params.to_dict()
    assert d["horizontal_resolution"] == 1920
    assert d["vertical_resolution"] == 1080
    assert d["refresh_rate"] == 60
    assert d["interlaced"] is False
    assert len(d) == 6


# --- Tests for CommandPacket round-trip ---


def test_command_packet_round_trip():
    """Test CommandPacket serialize → deserialize → verify equality."""
    original = CommandPacket(1, CommandCodes.POWER, bytes([0xF0]))
    serialized = original.to_bytes()
    restored = CommandPacket.from_bytes(serialized)
    assert restored.zn == original.zn
    assert restored.cc == original.cc
    assert restored.data == original.data


def test_command_packet_round_trip_with_data():
    """Test CommandPacket round-trip with multi-byte data."""
    original = CommandPacket(2, CommandCodes.VOLUME, bytes([0x32]))
    serialized = original.to_bytes()
    restored = CommandPacket.from_bytes(serialized)
    assert restored.zn == 2
    assert restored.cc == CommandCodes.VOLUME
    assert restored.data == bytes([0x32])


def test_command_packet_round_trip_empty_data():
    """Test CommandPacket round-trip with empty data."""
    original = CommandPacket(1, CommandCodes.SOFTWARE_VERSION, b"")
    serialized = original.to_bytes()
    restored = CommandPacket.from_bytes(serialized)
    assert restored.zn == 1
    assert restored.data == b""


# --- Tests for DeviceProfile and detect_api_model ---


@pytest.mark.parametrize(
    "model, expected",
    [
        ("AVR30", ApiModel.APIHDA_SERIES),
        ("AVR450", ApiModel.API450_SERIES),
        ("AV860", ApiModel.API860_SERIES),
        ("SA20", ApiModel.APISA_SERIES),
        ("PA720", ApiModel.APIPA_SERIES),
        ("ST60", ApiModel.APIST_SERIES),
    ],
)
def test_detect_api_model_known(model, expected):
    """detect_api_model returns correct ApiModel for known devices."""
    assert detect_api_model(model) == expected


def test_detect_api_model_unknown():
    """detect_api_model returns None for unknown model names."""
    assert detect_api_model("UNKNOWN_MODEL") is None


def test_device_profiles_cover_all_api_models():
    """Every ApiModel enum value has a corresponding DeviceProfile."""
    for model in ApiModel:
        assert model in DEVICE_PROFILES, f"Missing profile for {model}"


def test_device_profiles_feature_flags_consistent():
    """Feature flags in profiles match the legacy *_SUPPORTED sets."""
    from arcam.fmj import (
        MUTE_WRITE_SUPPORTED,
        POWER_WRITE_SUPPORTED,
        SOURCE_WRITE_SUPPORTED,
        VOLUME_STEP_SUPPORTED,
    )

    for api_model, profile in DEVICE_PROFILES.items():
        assert profile.power_writable == (api_model in POWER_WRITE_SUPPORTED), (
            f"{api_model}: power_writable mismatch"
        )
        assert profile.mute_writable == (api_model in MUTE_WRITE_SUPPORTED), (
            f"{api_model}: mute_writable mismatch"
        )
        assert profile.source_writable == (api_model in SOURCE_WRITE_SUPPORTED), (
            f"{api_model}: source_writable mismatch"
        )
        assert profile.volume_steppable == (api_model in VOLUME_STEP_SUPPORTED), (
            f"{api_model}: volume_steppable mismatch"
        )


# --- Tests for ResponseException.from_response() factory ---


@pytest.mark.parametrize(
    "ac, expected_type",
    [
        (AnswerCodes.ZONE_INVALID, InvalidZoneException),
        (AnswerCodes.COMMAND_NOT_RECOGNISED, CommandNotRecognised),
        (AnswerCodes.PARAMETER_NOT_RECOGNISED, ParameterNotRecognised),
        (AnswerCodes.COMMAND_INVALID_AT_THIS_TIME, CommandInvalidAtThisTime),
        (AnswerCodes.INVALID_DATA_LENGTH, InvalidDataLength),
    ],
)
def test_response_exception_from_response(ac, expected_type):
    """from_response returns correct exception subclass for each answer code."""
    response = ResponsePacket(zn=1, cc=CommandCodes.POWER, ac=ac, data=b"")
    exc = ResponseException.from_response(response)
    assert isinstance(exc, expected_type)


def test_response_exception_from_response_unknown_ac():
    """from_response returns base ResponseException for unknown answer codes."""
    # Use a raw int value that maps to an unusual AnswerCode
    response = ResponsePacket(zn=1, cc=CommandCodes.POWER, ac=AnswerCodes.STATUS_UPDATE, data=b"")
    exc = ResponseException.from_response(response)
    assert type(exc) is ResponseException


# --- Tests for SourceCodes.from_bytes / to_bytes error paths ---


def test_source_codes_from_bytes_unknown_value():
    """SourceCodes.from_bytes raises ValueError for unknown byte value."""
    with pytest.raises(ValueError, match="Unknown source code"):
        SourceCodes.from_bytes(bytes([0xFE]), ApiModel.APIHDA_SERIES, 1)


def test_source_codes_to_bytes_unknown_model():
    """SourceCodes.to_bytes raises ValueError for unknown model/zone."""
    with pytest.raises(ValueError, match="Unknown source map"):
        SourceCodes.CD.to_bytes(ApiModel.APIPA_SERIES, 99)


def test_source_codes_from_bytes_unknown_model():
    """SourceCodes.from_bytes raises ValueError for unknown model/zone."""
    with pytest.raises(ValueError, match="Unknown source map"):
        SourceCodes.from_bytes(bytes([0x01]), ApiModel.APIPA_SERIES, 99)


def test_source_codes_to_bytes_unknown_source():
    """SourceCodes.to_bytes raises ValueError for source not in model's mapping."""
    # PHONO is not in HDA source mapping
    with pytest.raises(ValueError, match="Unknown byte code"):
        SourceCodes.PHONO.to_bytes(ApiModel.APIHDA_SERIES, 1)


# --- Tests for PresetDetail.from_bytes unknown type ---


def test_preset_detail_from_bytes_unknown_type():
    """PresetDetail.from_bytes handles unknown preset type with str(data) fallback."""
    # Preset type byte 0xFF is unknown
    data = bytes([0x01, 0xFF, 0x41, 0x42])
    detail = PresetDetail.from_bytes(data)
    assert detail.index == 1
    assert isinstance(detail.name, str)


# --- Tests for ResponsePacket.from_bytes validation ---


def test_response_packet_from_bytes_too_short():
    """ResponsePacket.from_bytes raises InvalidPacket for short data."""
    with pytest.raises(InvalidPacket, match="too short"):
        ResponsePacket.from_bytes(b"\x21\x01\x00")


def test_response_packet_from_bytes_invalid_length():
    """ResponsePacket.from_bytes raises InvalidPacket for length mismatch."""
    # Header says 5 bytes of data but only 1 present
    with pytest.raises(InvalidPacket, match="Invalid length"):
        ResponsePacket.from_bytes(b"\x21\x01\x00\x00\x05\x01\x0d")


# --- Tests for CommandPacket.from_bytes validation ---


def test_command_packet_from_bytes_too_short():
    """CommandPacket.from_bytes raises InvalidPacket for short data."""
    with pytest.raises(InvalidPacket, match="too short"):
        CommandPacket.from_bytes(b"\x21\x01")


def test_command_packet_from_bytes_invalid_length():
    """CommandPacket.from_bytes raises InvalidPacket for length mismatch."""
    with pytest.raises(InvalidPacket, match="Invalid length"):
        CommandPacket.from_bytes(b"\x21\x01\x00\x05\x01\x0d")


# --- Tests for AmxDuetRequest.from_bytes ---


def test_amx_duet_request_from_bytes_valid():
    """AmxDuetRequest.from_bytes parses valid AMX request."""
    req = AmxDuetRequest.from_bytes(b"AMX\r")
    assert isinstance(req, AmxDuetRequest)


def test_amx_duet_request_from_bytes_invalid():
    """AmxDuetRequest.from_bytes raises InvalidPacket for non-AMX data."""
    with pytest.raises(InvalidPacket, match="not a amx"):
        AmxDuetRequest.from_bytes(b"NOTAMX")


# --- Tests for IntOrTypeEnum ---


def test_intenum_from_int_basic():
    """IntOrTypeEnum.from_int returns correct member for known values."""
    from arcam.fmj import IntOrTypeEnum

    class TestEnum(IntOrTypeEnum):
        TEST = 55
        TEST_VERSION = 23, {1}

    res = TestEnum.from_int(55)
    assert res.name == "TEST"
    assert res.value == 55
    assert res.version is None

    res = TestEnum.from_int(23)
    assert res.name == "TEST_VERSION"
    assert res.value == 23
    assert res.version == {1}


def test_intenum_from_int_auto_creates_unknown():
    """IntOrTypeEnum.from_int auto-creates CODE_N for unknown values."""
    from arcam.fmj import IntOrTypeEnum

    class TestEnum(IntOrTypeEnum):
        TEST = 55

    res = TestEnum.from_int(1)
    assert res.name == "CODE_1"
    assert res.value == 1
    assert res.version is None


# --- Tests for AmxDuetResponse round-trip ---


def test_amx_duet_response_round_trip():
    """AmxDuetResponse.from_bytes → to_bytes round-trip preserves data."""
    src = (
        b"AMXB<Device-SDKClass=Receiver><Device-Make=ARCAM>"
        b"<Device-Model=AV860><Device-Revision=x.y.z>\r"
    )
    res = AmxDuetResponse.from_bytes(src)
    assert res.device_class == "Receiver"
    assert res.device_make == "ARCAM"
    assert res.device_model == "AV860"
    assert res.device_revision == "x.y.z"
    assert res.to_bytes() == src
