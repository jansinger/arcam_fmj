"""Tests for State methods using mocked Client."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from arcam.fmj import (
    ApiModel,
    CommandCodes,
    CommandInvalidAtThisTime,
    DolbyAudioMode,
    HdmiSettings,
    NetworkPlaybackStatus,
    NowPlayingInfo,
    NowPlayingSampleRate,
    NowPlayingEncoder,
    BluetoothStatus,
    RoomEqNames,
    ZoneSettings,
)
from arcam.fmj.client import Client
from arcam.fmj.state import State


def _make_state(zn=1, api_model=ApiModel.APIHDA_SERIES):
    """Helper to create a State with a mocked Client."""
    client = MagicMock(spec=Client)
    client.request = AsyncMock()
    client.request_raw = AsyncMock()
    client.connected = True
    return State(client, zn, api_model)


# --- Tests for get_network_playback_status ---


async def test_get_network_playback_status_none():
    """Returns None when no state data exists."""
    state = _make_state()
    assert state.get_network_playback_status() is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0x00, NetworkPlaybackStatus.STOPPED),
        (0x01, NetworkPlaybackStatus.TRANSITIONING),
        (0x02, NetworkPlaybackStatus.PLAYING),
        (0x03, NetworkPlaybackStatus.PAUSED),
    ],
)
async def test_get_network_playback_status_values(raw, expected):
    """Correctly parses all network playback status bytes."""
    state = _make_state()
    state._state[CommandCodes.NETWORK_PLAYBACK_STATUS] = bytes([raw])
    assert state.get_network_playback_status() == expected


# --- Tests for get_dolby_audio / set_dolby_audio ---


async def test_get_dolby_audio_none():
    """Returns None when no Dolby Audio state."""
    state = _make_state()
    assert state.get_dolby_audio() is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0x00, DolbyAudioMode.OFF),
        (0x01, DolbyAudioMode.MOVIE),
        (0x02, DolbyAudioMode.MUSIC),
        (0x03, DolbyAudioMode.NIGHT),
    ],
)
async def test_get_dolby_audio_values(raw, expected):
    """Correctly parses all 4 Dolby Audio modes."""
    state = _make_state()
    state._state[CommandCodes.DOLBY_VOLUME] = bytes([raw])
    assert state.get_dolby_audio() == expected


@pytest.mark.parametrize(
    "mode, expected_byte",
    [
        (DolbyAudioMode.OFF, 0x00),
        (DolbyAudioMode.MOVIE, 0x01),
        (DolbyAudioMode.MUSIC, 0x02),
        (DolbyAudioMode.NIGHT, 0x03),
    ],
)
async def test_set_dolby_audio(mode, expected_byte):
    """Sends correct byte for each Dolby Audio mode."""
    state = _make_state()
    await state.set_dolby_audio(mode)
    state._client.request.assert_called_with(
        1, CommandCodes.DOLBY_VOLUME, bytes([expected_byte])
    )


# --- Tests for get_now_playing_info ---


async def test_get_now_playing_info_none():
    """Returns None when no now playing data has been polled."""
    state = _make_state()
    assert state.get_now_playing_info() is None


async def test_get_now_playing_info_with_data():
    """Returns NowPlayingInfo built from _now_playing dict."""
    state = _make_state()
    state._now_playing = {
        0xF0: "My Song",
        0xF1: "My Artist",
        0xF2: "My Album",
        0xF3: "Spotify",
        0xF4: NowPlayingSampleRate.KHZ_44_1,
        0xF5: NowPlayingEncoder.FLAC,
    }
    info = state.get_now_playing_info()
    assert info is not None
    assert info.title == "My Song"
    assert info.artist == "My Artist"
    assert info.album == "My Album"
    assert info.application == "Spotify"
    assert info.sample_rate == NowPlayingSampleRate.KHZ_44_1
    assert info.encoder == NowPlayingEncoder.FLAC


async def test_get_now_playing_info_partial():
    """Returns NowPlayingInfo with defaults for missing fields."""
    state = _make_state()
    state._now_playing = {0xF0: "Just Title"}
    info = state.get_now_playing_info()
    assert info is not None
    assert info.title == "Just Title"
    assert info.artist == ""
    assert info.sample_rate is None


# --- Tests for Room EQ (int instead of bool) ---


async def test_get_room_eq_none():
    """Returns None when no Room EQ state."""
    state = _make_state()
    assert state.get_room_eq() is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0x00, 0),  # off
        (0x01, 1),  # EQ1
        (0x02, 2),  # EQ2
        (0x03, 3),  # EQ3
        (0x04, 4),  # not calculated
    ],
)
async def test_get_room_eq_int_values(raw, expected):
    """Room EQ returns integer (0=off, 1=EQ1, 2=EQ2, 3=EQ3, 4=not calculated)."""
    state = _make_state()
    state._state[CommandCodes.ROOM_EQUALIZATION] = bytes([raw])
    assert state.get_room_eq() == expected


@pytest.mark.parametrize("preset", [0, 1, 2, 3])
async def test_set_room_eq_preset(preset):
    """Sends correct preset byte value."""
    state = _make_state()
    await state.set_room_eq(preset)
    state._client.request.assert_called_with(
        1, CommandCodes.ROOM_EQUALIZATION, bytes([preset])
    )


# --- Tests for get_hdmi_settings ---


async def test_get_hdmi_settings_none():
    """Returns None when no HDMI settings state."""
    state = _make_state()
    assert state.get_hdmi_settings() is None


async def test_get_hdmi_settings_parsed():
    """Correctly parses HDMI settings from 10-byte state data."""
    state = _make_state()
    state._state[CommandCodes.HDMI_SETTINGS] = bytes(
        [0x01, 0x02, 0x32, 0x01, 0x00, 0x03, 0x01, 0x01, 0x01, 0x01]
    )
    settings = state.get_hdmi_settings()
    assert settings is not None
    assert settings.zone1_osd is True
    assert settings.zone1_output == 2
    assert settings.zone1_lipsync == 0x32
    assert settings.hdmi_audio_to_tv is True
    assert settings.hdmi_bypass_ip is False
    assert settings.hdmi_bypass_source == 3
    assert settings.cec_control == 1
    assert settings.arc_control == 1


# --- Tests for get_zone_settings ---


async def test_get_zone_settings_none():
    """Returns None when no zone settings state."""
    state = _make_state()
    assert state.get_zone_settings() is None


async def test_get_zone_settings_parsed():
    """Correctly parses Zone settings from 6-byte state data."""
    state = _make_state()
    state._state[CommandCodes.ZONE_SETTINGS] = bytes(
        [0x01, 0x01, 0x32, 0x53, 0x00, 0x32]
    )
    settings = state.get_zone_settings()
    assert settings is not None
    assert settings.zone2_input == 1
    assert settings.zone2_status == 1
    assert settings.zone2_volume == 0x32
    assert settings.zone2_max_volume == 0x53
    assert settings.zone2_fixed_volume is False


# --- Tests for get_room_eq_names ---


async def test_get_room_eq_names_none():
    """Returns None when no Room EQ names state."""
    state = _make_state()
    assert state.get_room_eq_names() is None


async def test_get_room_eq_names_parsed():
    """Correctly parses Room EQ names from multi-byte state data."""
    state = _make_state()
    eq1 = b"Living Room\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    eq2 = b"Cinema\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    eq3 = b"Music\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    state._state[CommandCodes.ROOM_EQ_NAMES] = eq1 + eq2 + eq3
    names = state.get_room_eq_names()
    assert names is not None
    assert names.eq1 == "Living Room"
    assert names.eq2 == "Cinema"
    assert names.eq3 == "Music"


# --- Tests for get_bluetooth_status ---


async def test_get_bluetooth_status_none():
    """Returns None when no Bluetooth status state."""
    state = _make_state()
    assert state.get_bluetooth_status() is None


async def test_get_bluetooth_status_no_connection():
    """Parses 'no connection' Bluetooth status."""
    state = _make_state()
    state._state[CommandCodes.VIDEO_OUTPUT_FRAME_RATE] = bytes([0x00])
    status, track = state.get_bluetooth_status()
    assert status == BluetoothStatus.NO_CONNECTION
    assert track == ""


async def test_get_bluetooth_status_playing_with_track():
    """Parses playing Bluetooth status with track name."""
    state = _make_state()
    track_name = b"My Song"
    state._state[CommandCodes.VIDEO_OUTPUT_FRAME_RATE] = bytes([0x03]) + track_name
    status, track = state.get_bluetooth_status()
    assert status == BluetoothStatus.PLAYING_AAC
    assert track == "My Song"


# --- Tests for to_dict including new keys ---


async def test_to_dict_includes_new_hda_keys():
    """to_dict() includes all new HDA parameter keys."""
    state = _make_state()
    result = state.to_dict()
    expected_keys = [
        "NETWORK_PLAYBACK_STATUS",
        "DOLBY_AUDIO",
        "NOW_PLAYING_INFO",
        "HDMI_SETTINGS",
        "ZONE_SETTINGS",
        "ROOM_EQ_NAMES",
        "BLUETOOTH_STATUS",
    ]
    for key in expected_keys:
        assert key in result, f"to_dict() should include key '{key}'"


# --- Tests for get_decode_mode fallback ---


async def test_get_decode_mode_2ch_fallback_to_mch():
    """When 2CH mode returns None (error), falls back to MCH mode."""
    from arcam.fmj import DecodeModeMCH, IncomingAudioFormat

    state = _make_state()
    # Audio format is PCM -> get_2ch() returns True
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    # 2CH returns error (None), MCH has a valid value
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x06])
    result = state.get_decode_mode()
    assert result == DecodeModeMCH.DOLBY_SURROUND


async def test_get_decode_mode_mch_fallback_to_2ch():
    """When MCH mode returns None (error), falls back to 2CH mode."""
    from arcam.fmj import DecodeMode2CH, IncomingAudioFormat

    state = _make_state()
    # Audio format is Dolby -> get_2ch() returns False
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    # MCH returns error (None), 2CH has a valid value
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = bytes([0x01])
    result = state.get_decode_mode()
    assert result == DecodeMode2CH.STEREO


async def test_get_decode_mode_both_none():
    """When both 2CH and MCH return None, result is None."""
    state = _make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x00])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = None
    assert state.get_decode_mode() is None


async def test_get_decode_mode_2ch_primary_succeeds():
    """When 2CH mode has value, no fallback needed."""
    from arcam.fmj import DecodeMode2CH

    state = _make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x00])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = bytes([0x01])
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x06])
    result = state.get_decode_mode()
    assert result == DecodeMode2CH.STEREO


# --- Tests for set_decode_mode fallback ---


async def test_set_decode_mode_2ch_enum_always_uses_2ch():
    """When DecodeMode2CH enum is passed, always use 2CH setter regardless of get_2ch()."""
    from arcam.fmj import DecodeMode2CH

    state = _make_state()
    # MCH audio format (get_2ch() returns False)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    await state.set_decode_mode(DecodeMode2CH.STEREO)
    # Should still go through set_decode_mode_2ch (RC5 command)
    state._client.request.assert_called_once()
    args = state._client.request.call_args
    assert args[0][1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_set_decode_mode_mch_enum_always_uses_mch():
    """When DecodeModeMCH enum is passed, always use MCH setter regardless of get_2ch()."""
    from arcam.fmj import DecodeModeMCH

    state = _make_state()
    # PCM audio format (get_2ch() returns True)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    await state.set_decode_mode(DecodeModeMCH.DOLBY_SURROUND)
    # Should still go through set_decode_mode_mch (RC5 command)
    state._client.request.assert_called_once()
    args = state._client.request.call_args
    assert args[0][1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_set_decode_mode_string_fallback_2ch_to_mch():
    """When string mode not in 2CH enum, falls back to MCH."""
    from arcam.fmj import DecodeModeMCH

    state = _make_state()
    # PCM audio (get_2ch() returns True), but mode only exists in MCH
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    await state.set_decode_mode("MULTI_CHANNEL")
    state._client.request.assert_called_once()


async def test_set_decode_mode_string_fallback_mch_to_2ch():
    """When string mode not in MCH enum, falls back to 2CH."""
    from arcam.fmj import DecodeMode2CH

    state = _make_state()
    # Dolby audio (get_2ch() returns False), but mode only exists in 2CH
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    await state.set_decode_mode("DTS_NEURAL_X")
    state._client.request.assert_called_once()


async def test_set_decode_mode_mch_enum_not_rejected_when_2ch():
    """DecodeModeMCH enum must NOT raise ValueError when get_2ch() is True."""
    from arcam.fmj import DecodeModeMCH

    state = _make_state()
    # PCM = get_2ch() True, but passing MCH enum should work (AV40 scenario)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    # This previously raised ValueError - now it should work
    await state.set_decode_mode(DecodeModeMCH.DOLBY_SURROUND)
    state._client.request.assert_called_once()


# --- Tests for update() polling new commands ---


async def test_update_disconnected_clears_now_playing():
    """update() clears _now_playing when client is disconnected."""
    state = _make_state()
    state._client.connected = False
    state._now_playing = {0xF0: "Test"}
    state._state[CommandCodes.POWER] = bytes([1])
    await state.update()
    assert state._now_playing == {}
    assert state._state == {}
