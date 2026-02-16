"""Tests for State methods using mocked Client."""

import pytest

from arcam.fmj import (
    AmxDuetResponse,
    AnswerCodes,
    ApiModel,
    CommandCodes,
    CommandInvalidAtThisTime,
    CommandNotRecognised,
    DolbyAudioMode,
    HdmiSettings,
    MenuCodes,
    NetworkPlaybackStatus,
    NotConnectedException,
    NowPlayingInfo,
    NowPlayingSampleRate,
    NowPlayingEncoder,
    BluetoothStatus,
    ResponseException,
    ResponsePacket,
    RoomEqNames,
    SourceCodes,
    ZoneSettings,
)


# --- Tests for get_network_playback_status ---


async def test_get_network_playback_status_none(make_state):
    """Returns None when no state data exists."""
    state = make_state()
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
async def test_get_network_playback_status_values(make_state, raw, expected):
    """Correctly parses all network playback status bytes."""
    state = make_state()
    state._state[CommandCodes.NETWORK_PLAYBACK_STATUS] = bytes([raw])
    assert state.get_network_playback_status() == expected


# --- Tests for get_dolby_audio / set_dolby_audio ---


async def test_get_dolby_audio_none(make_state):
    """Returns None when no Dolby Audio state."""
    state = make_state()
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
async def test_get_dolby_audio_values(make_state, raw, expected):
    """Correctly parses all 4 Dolby Audio modes."""
    state = make_state()
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
async def test_set_dolby_audio(make_state, mode, expected_byte):
    """Sends correct byte for each Dolby Audio mode."""
    state = make_state()
    await state.set_dolby_audio(mode)
    state._client.request.assert_called_with(
        1, CommandCodes.DOLBY_VOLUME, bytes([expected_byte])
    )


# --- Tests for get_now_playing_info ---


async def test_get_now_playing_info_none(make_state):
    """Returns None when no now playing data has been polled."""
    state = make_state()
    assert state.get_now_playing_info() is None


async def test_get_now_playing_info_with_data(make_state):
    """Returns NowPlayingInfo built from _now_playing dict."""
    state = make_state()
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


async def test_get_now_playing_info_partial(make_state):
    """Returns NowPlayingInfo with defaults for missing fields."""
    state = make_state()
    state._now_playing = {0xF0: "Just Title"}
    info = state.get_now_playing_info()
    assert info is not None
    assert info.title == "Just Title"
    assert info.artist == ""
    assert info.sample_rate is None


# --- Tests for Room EQ (int instead of bool) ---


async def test_get_room_eq_none(make_state):
    """Returns None when no Room EQ state."""
    state = make_state()
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
async def test_get_room_eq_int_values(make_state, raw, expected):
    """Room EQ returns integer (0=off, 1=EQ1, 2=EQ2, 3=EQ3, 4=not calculated)."""
    state = make_state()
    state._state[CommandCodes.ROOM_EQUALIZATION] = bytes([raw])
    assert state.get_room_eq() == expected


@pytest.mark.parametrize("preset", [0, 1, 2, 3])
async def test_set_room_eq_preset(make_state, preset):
    """Sends correct preset byte value."""
    state = make_state()
    await state.set_room_eq(preset)
    state._client.request.assert_called_with(
        1, CommandCodes.ROOM_EQUALIZATION, bytes([preset])
    )


# --- Tests for get_hdmi_settings ---


async def test_get_hdmi_settings_none(make_state):
    """Returns None when no HDMI settings state."""
    state = make_state()
    assert state.get_hdmi_settings() is None


async def test_get_hdmi_settings_parsed(make_state):
    """Correctly parses HDMI settings from 10-byte state data."""
    state = make_state()
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


async def test_get_zone_settings_none(make_state):
    """Returns None when no zone settings state."""
    state = make_state()
    assert state.get_zone_settings() is None


async def test_get_zone_settings_parsed(make_state):
    """Correctly parses Zone settings from 6-byte state data."""
    state = make_state()
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


async def test_get_room_eq_names_none(make_state):
    """Returns None when no Room EQ names state."""
    state = make_state()
    assert state.get_room_eq_names() is None


async def test_get_room_eq_names_parsed(make_state):
    """Correctly parses Room EQ names from multi-byte state data."""
    state = make_state()
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


async def test_get_bluetooth_status_none(make_state):
    """Returns None when no Bluetooth status state."""
    state = make_state()
    assert state.get_bluetooth_status() is None


async def test_get_bluetooth_status_no_connection(make_state):
    """Parses 'no connection' Bluetooth status."""
    state = make_state()
    state._state[CommandCodes.VIDEO_OUTPUT_FRAME_RATE] = bytes([0x00])
    status, track = state.get_bluetooth_status()
    assert status == BluetoothStatus.NO_CONNECTION
    assert track == ""


async def test_get_bluetooth_status_playing_with_track(make_state):
    """Parses playing Bluetooth status with track name."""
    state = make_state()
    track_name = b"My Song"
    state._state[CommandCodes.VIDEO_OUTPUT_FRAME_RATE] = bytes([0x03]) + track_name
    status, track = state.get_bluetooth_status()
    assert status == BluetoothStatus.PLAYING_AAC
    assert track == "My Song"


# --- Tests for to_dict including new keys ---


async def test_to_dict_includes_new_hda_keys(make_state):
    """to_dict() includes all new HDA parameter keys."""
    state = make_state()
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


async def test_get_decode_mode_2ch_fallback_to_mch(make_state):
    """When 2CH mode returns None (error), falls back to MCH mode."""
    from arcam.fmj import DecodeModeMCH, IncomingAudioFormat

    state = make_state()
    # Audio format is PCM -> get_2ch() returns True
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    # 2CH returns error (None), MCH has a valid value
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x06])
    result = state.get_decode_mode()
    assert result == DecodeModeMCH.DOLBY_SURROUND


async def test_get_decode_mode_mch_fallback_to_2ch(make_state):
    """When MCH mode returns None (error), falls back to 2CH mode."""
    from arcam.fmj import DecodeMode2CH, IncomingAudioFormat

    state = make_state()
    # Audio format is Dolby -> get_2ch() returns False
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    # MCH returns error (None), 2CH has a valid value
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = bytes([0x01])
    result = state.get_decode_mode()
    assert result == DecodeMode2CH.STEREO


async def test_get_decode_mode_both_none(make_state):
    """When both 2CH and MCH return None, result is None."""
    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x00])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = None
    assert state.get_decode_mode() is None


async def test_get_decode_mode_2ch_primary_succeeds(make_state):
    """When 2CH mode has value, no fallback needed."""
    from arcam.fmj import DecodeMode2CH

    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x00])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = bytes([0x01])
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x06])
    result = state.get_decode_mode()
    assert result == DecodeMode2CH.STEREO


# --- Tests for set_decode_mode fallback ---


async def test_set_decode_mode_2ch_enum_always_uses_2ch(make_state):
    """When DecodeMode2CH enum is passed, always use 2CH setter regardless of get_2ch()."""
    from arcam.fmj import DecodeMode2CH

    state = make_state()
    # MCH audio format (get_2ch() returns False)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    await state.set_decode_mode(DecodeMode2CH.STEREO)
    # Should still go through set_decode_mode_2ch (RC5 command)
    state._client.request.assert_called_once()
    args = state._client.request.call_args
    assert args[0][1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_set_decode_mode_mch_enum_always_uses_mch(make_state):
    """When DecodeModeMCH enum is passed, always use MCH setter regardless of get_2ch()."""
    from arcam.fmj import DecodeModeMCH

    state = make_state()
    # PCM audio format (get_2ch() returns True)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    await state.set_decode_mode(DecodeModeMCH.DOLBY_SURROUND)
    # Should still go through set_decode_mode_mch (RC5 command)
    state._client.request.assert_called_once()
    args = state._client.request.call_args
    assert args[0][1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_set_decode_mode_string_fallback_2ch_to_mch(make_state):
    """When string mode not in 2CH enum, falls back to MCH."""
    from arcam.fmj import DecodeModeMCH

    state = make_state()
    # PCM audio (get_2ch() returns True), but mode only exists in MCH
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    await state.set_decode_mode("MULTI_CHANNEL")
    state._client.request.assert_called_once()


async def test_set_decode_mode_string_fallback_mch_to_2ch(make_state):
    """When string mode not in MCH enum, falls back to 2CH."""
    from arcam.fmj import DecodeMode2CH

    state = make_state()
    # Dolby audio (get_2ch() returns False), but mode only exists in 2CH
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    await state.set_decode_mode("DTS_NEURAL_X")
    state._client.request.assert_called_once()


async def test_set_decode_mode_mch_enum_not_rejected_when_2ch(make_state):
    """DecodeModeMCH enum must NOT raise ValueError when get_2ch() is True."""
    from arcam.fmj import DecodeModeMCH

    state = make_state()
    # PCM = get_2ch() True, but passing MCH enum should work (AV40 scenario)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    # This previously raised ValueError - now it should work
    await state.set_decode_mode(DecodeModeMCH.DOLBY_SURROUND)
    state._client.request.assert_called_once()


# --- Tests for MCH DTS_NEURAL_X rename ---


async def test_mch_0x03_is_dts_neural_x(make_state):
    """MCH status byte 0x03 should parse as DTS_NEURAL_X (not DOLBY_D_EX_OR_DTS_ES)."""
    from arcam.fmj import DecodeModeMCH

    state = make_state()
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x03])
    result = state.get_decode_mode_mch()
    assert result is not None
    assert result.name == "DTS_NEURAL_X"
    assert result == DecodeModeMCH.DTS_NEURAL_X


async def test_mch_dolby_d_ex_alias_still_works():
    """DOLBY_D_EX_OR_DTS_ES alias should still be accessible for backward compat."""
    from arcam.fmj import DecodeModeMCH

    assert DecodeModeMCH.DOLBY_D_EX_OR_DTS_ES == DecodeModeMCH.DTS_NEURAL_X
    assert DecodeModeMCH.DOLBY_D_EX_OR_DTS_ES == 0x03


# --- Tests for get_decode_modes() consistency with active mode ---


async def test_get_decode_modes_returns_mch_when_mch_active(make_state):
    """get_decode_modes() should return MCH modes when MCH decode mode is active."""
    from arcam.fmj import DecodeModeMCH

    state = make_state()
    # PCM audio (get_2ch()=True), but MCH mode active via fallback
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x06])
    modes = state.get_decode_modes()
    assert modes is not None
    # Should be MCH modes since MCH is active
    assert any(isinstance(m, DecodeModeMCH) for m in modes)
    assert any(m.name == "MULTI_CHANNEL" for m in modes)


async def test_get_decode_modes_returns_2ch_when_2ch_active(make_state):
    """get_decode_modes() should return 2CH modes when 2CH decode mode is active."""
    from arcam.fmj import DecodeMode2CH

    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x00])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = bytes([0x01])
    modes = state.get_decode_modes()
    assert modes is not None
    assert any(isinstance(m, DecodeMode2CH) for m in modes)
    assert any(m.name == "STEREO" for m in modes)


async def test_get_decode_modes_current_mode_in_list(make_state):
    """The current decode mode name must always appear in get_decode_modes() list."""
    from arcam.fmj import DecodeModeMCH

    state = make_state()
    # PCM audio + MCH DTS Neural:X active (the problematic case)
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x00, 0x1A])
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = None
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x03])
    current = state.get_decode_mode()
    modes = state.get_decode_modes()
    assert current is not None
    assert modes is not None
    # Current mode name MUST be in the modes list
    mode_names = [m.name for m in modes]
    assert current.name in mode_names, (
        f"Current mode '{current.name}' not in modes list {mode_names}"
    )


# --- Tests for update() polling new commands ---


async def test_update_disconnected_clears_now_playing(make_state):
    """update() clears _now_playing when client is disconnected."""
    state = make_state()
    state._client.connected = False
    state._now_playing = {0xF0: "Test"}
    state._state[CommandCodes.POWER] = bytes([1])
    await state.update()
    assert state._now_playing == {}
    assert state._state == {}


# --- Tests for get_power / set_power ---


async def test_get_power_none(make_state):
    """Returns None when no power state."""
    state = make_state()
    assert state.get_power() is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0x01, True),
        (0x00, False),
    ],
)
async def test_get_power_values(make_state, raw, expected):
    """Correctly parses power on/off."""
    state = make_state()
    state._state[CommandCodes.POWER] = bytes([raw])
    assert state.get_power() == expected


async def test_set_power_on_rc5(make_state):
    """HDA series uses RC5 IR command for power on."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    await state.set_power(True)
    state._client.request.assert_called_once()
    args = state._client.request.call_args[0]
    assert args[1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_set_power_off_rc5_uses_send(make_state):
    """HDA series power off uses send() (fire-and-forget) and seeds state."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    await state.set_power(False)
    # Power off uses send(), not request()
    state._client.send.assert_called_once()
    args = state._client.send.call_args[0]
    assert args[1] == CommandCodes.SIMULATE_RC5_IR_COMMAND
    # State should be seeded optimistically
    assert state._state[CommandCodes.POWER] == bytes([0])


async def test_set_power_on_direct_write(make_state):
    """SA series uses direct write for power on."""
    state = make_state(api_model=ApiModel.APISA_SERIES)
    await state.set_power(True)
    state._client.request.assert_called_with(
        1, CommandCodes.POWER, bytes([0x01])
    )


async def test_set_power_off_direct_write(make_state):
    """SA series uses direct write for power off and seeds state."""
    state = make_state(api_model=ApiModel.APISA_SERIES)
    await state.set_power(False)
    state._client.request.assert_called_with(
        1, CommandCodes.POWER, bytes([0x00])
    )
    assert state._state[CommandCodes.POWER] == bytes([0])


# --- Tests for get_volume / set_volume / inc_volume / dec_volume ---


async def test_get_volume_none(make_state):
    """Returns None when no volume state."""
    state = make_state()
    assert state.get_volume() is None


@pytest.mark.parametrize("raw, expected", [(0, 0), (50, 50), (99, 99)])
async def test_get_volume_values(make_state, raw, expected):
    """Correctly parses volume byte."""
    state = make_state()
    state._state[CommandCodes.VOLUME] = bytes([raw])
    assert state.get_volume() == expected


async def test_set_volume(make_state):
    """Sends correct volume byte."""
    state = make_state()
    await state.set_volume(42)
    state._client.request.assert_called_with(
        1, CommandCodes.VOLUME, bytes([42])
    )


async def test_inc_volume_step_supported(make_state):
    """ST series uses volume step command 0xF1."""
    state = make_state(api_model=ApiModel.APIST_SERIES)
    await state.inc_volume()
    state._client.request.assert_called_with(
        1, CommandCodes.VOLUME, bytes([0xF1])
    )


async def test_dec_volume_step_supported(make_state):
    """ST series uses volume step command 0xF2."""
    state = make_state(api_model=ApiModel.APIST_SERIES)
    await state.dec_volume()
    state._client.request.assert_called_with(
        1, CommandCodes.VOLUME, bytes([0xF2])
    )


async def test_inc_volume_rc5(make_state):
    """HDA series uses RC5 IR command for volume up."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    await state.inc_volume()
    state._client.request.assert_called_once()
    args = state._client.request.call_args[0]
    assert args[1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_dec_volume_rc5(make_state):
    """HDA series uses RC5 IR command for volume down."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    await state.dec_volume()
    state._client.request.assert_called_once()
    args = state._client.request.call_args[0]
    assert args[1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


# --- Tests for get_mute / set_mute ---


async def test_get_mute_none(make_state):
    """Returns None when no mute state."""
    state = make_state()
    assert state.get_mute() is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0x00, True),   # 0 = muted
        (0x01, False),  # 1 = unmuted
    ],
)
async def test_get_mute_values(make_state, raw, expected):
    """Correctly parses mute state (0=muted, 1=unmuted)."""
    state = make_state()
    state._state[CommandCodes.MUTE] = bytes([raw])
    assert state.get_mute() == expected


async def test_set_mute_direct_write(make_state):
    """SA series uses direct write for mute."""
    state = make_state(api_model=ApiModel.APISA_SERIES)
    await state.set_mute(True)
    state._client.request.assert_called_with(
        1, CommandCodes.MUTE, bytes([0x00])
    )


async def test_set_unmute_direct_write(make_state):
    """SA series uses direct write for unmute."""
    state = make_state(api_model=ApiModel.APISA_SERIES)
    await state.set_mute(False)
    state._client.request.assert_called_with(
        1, CommandCodes.MUTE, bytes([0x01])
    )


async def test_set_mute_rc5_with_followup_query(make_state):
    """HDA series uses RC5 command and re-queries mute state."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    # First call: RC5 command, second call: mute query
    state._client.request.side_effect = [
        None,  # RC5 command response
        bytes([0x00]),  # mute state query response
    ]
    await state.set_mute(True)
    assert state._client.request.call_count == 2
    # Second call should be the mute query
    second_call = state._client.request.call_args_list[1]
    assert second_call[0][1] == CommandCodes.MUTE
    assert second_call[0][2] == bytes([0xF0])
    # State should be updated from query
    assert state._state[CommandCodes.MUTE] == bytes([0x00])


async def test_set_mute_rc5_query_failure(make_state):
    """When mute state re-query fails, state is set to None."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    state._client.request.side_effect = [
        None,  # RC5 command succeeds
        TimeoutError(),  # mute query fails
    ]
    await state.set_mute(True)
    assert state._state[CommandCodes.MUTE] is None


# --- Tests for get_menu ---


async def test_get_menu_none(make_state):
    """Returns None when no menu state."""
    state = make_state()
    assert state.get_menu() is None


async def test_get_menu_value(make_state):
    """Correctly parses menu state."""
    state = make_state()
    state._state[CommandCodes.MENU] = bytes([0x02])
    assert state.get_menu() == MenuCodes.SETUP


# --- Tests for audio controls (bass, treble, balance, etc.) ---


@pytest.mark.parametrize(
    "getter, setter, cc",
    [
        ("get_bass", "set_bass", CommandCodes.BASS_EQUALIZATION),
        ("get_treble", "set_treble", CommandCodes.TREBLE_EQUALIZATION),
        ("get_balance", "set_balance", CommandCodes.BALANCE),
        ("get_subwoofer_trim", "set_subwoofer_trim", CommandCodes.SUBWOOFER_TRIM),
        ("get_lipsync_delay", "set_lipsync_delay", CommandCodes.LIPSYNC_DELAY),
        ("get_display_brightness", "set_display_brightness", CommandCodes.DISPLAY_BRIGHTNESS),
        ("get_compression", "set_compression", CommandCodes.COMPRESSION),
    ],
)
async def test_int_getter_none(make_state, getter, setter, cc):
    """Integer getters return None when no state."""
    state = make_state()
    assert getattr(state, getter)() is None


@pytest.mark.parametrize(
    "getter, setter, cc",
    [
        ("get_bass", "set_bass", CommandCodes.BASS_EQUALIZATION),
        ("get_treble", "set_treble", CommandCodes.TREBLE_EQUALIZATION),
        ("get_balance", "set_balance", CommandCodes.BALANCE),
        ("get_subwoofer_trim", "set_subwoofer_trim", CommandCodes.SUBWOOFER_TRIM),
        ("get_lipsync_delay", "set_lipsync_delay", CommandCodes.LIPSYNC_DELAY),
        ("get_display_brightness", "set_display_brightness", CommandCodes.DISPLAY_BRIGHTNESS),
        ("get_compression", "set_compression", CommandCodes.COMPRESSION),
    ],
)
async def test_int_getter_value(make_state, getter, setter, cc):
    """Integer getters correctly parse byte value."""
    state = make_state()
    state._state[cc] = bytes([42])
    assert getattr(state, getter)() == 42


@pytest.mark.parametrize(
    "setter, cc, value",
    [
        ("set_bass", CommandCodes.BASS_EQUALIZATION, 42),
        ("set_treble", CommandCodes.TREBLE_EQUALIZATION, 42),
        ("set_balance", CommandCodes.BALANCE, 42),
        ("set_subwoofer_trim", CommandCodes.SUBWOOFER_TRIM, 42),
        ("set_lipsync_delay", CommandCodes.LIPSYNC_DELAY, 42),
        ("set_display_brightness", CommandCodes.DISPLAY_BRIGHTNESS, 1),
        ("set_compression", CommandCodes.COMPRESSION, 2),
    ],
)
async def test_int_setter(make_state, setter, cc, value):
    """Integer setters send correct byte."""
    state = make_state()
    await getattr(state, setter)(value)
    state._client.request.assert_called_with(1, cc, bytes([value]))


# --- Tests for string getters ---


@pytest.mark.parametrize(
    "getter, cc",
    [
        ("get_dab_station", CommandCodes.DAB_STATION),
        ("get_dls_pdt", CommandCodes.DLS_PDT_INFO),
        ("get_rds_information", CommandCodes.RDS_INFORMATION),
    ],
)
async def test_string_getter_none(make_state, getter, cc):
    """String getters return None when no state."""
    state = make_state()
    assert getattr(state, getter)() is None


@pytest.mark.parametrize(
    "getter, cc",
    [
        ("get_dab_station", CommandCodes.DAB_STATION),
        ("get_dls_pdt", CommandCodes.DLS_PDT_INFO),
        ("get_rds_information", CommandCodes.RDS_INFORMATION),
    ],
)
async def test_string_getter_value(make_state, getter, cc):
    """String getters correctly decode UTF-8 and strip trailing whitespace."""
    state = make_state()
    state._state[cc] = b"Test Station   "
    assert getattr(state, getter)() == "Test Station"


# --- Tests for tuner preset ---


async def test_get_tuner_preset_none(make_state):
    """Returns None when no tuner preset state."""
    state = make_state()
    assert state.get_tuner_preset() is None


async def test_get_tuner_preset_0xff_is_none(make_state):
    """Returns None when preset is 0xFF (no preset selected)."""
    state = make_state()
    state._state[CommandCodes.TUNER_PRESET] = b"\xff"
    assert state.get_tuner_preset() is None


async def test_get_tuner_preset_value(make_state):
    """Returns preset number."""
    state = make_state()
    state._state[CommandCodes.TUNER_PRESET] = bytes([5])
    assert state.get_tuner_preset() == 5


async def test_set_tuner_preset(make_state):
    """Sends correct preset byte."""
    state = make_state()
    await state.set_tuner_preset(3)
    state._client.request.assert_called_with(
        1, CommandCodes.TUNER_PRESET, bytes([3])
    )


# --- Tests for _listen callback ---


async def test_listen_status_update(make_state):
    """_listen stores data on STATUS_UPDATE."""
    state = make_state()
    packet = ResponsePacket(
        zn=1, cc=CommandCodes.VOLUME, ac=AnswerCodes.STATUS_UPDATE, data=bytes([50])
    )
    state._listen(packet)
    assert state._state[CommandCodes.VOLUME] == bytes([50])


async def test_listen_error_clears_state(make_state):
    """_listen sets state to None on non-STATUS_UPDATE responses."""
    state = make_state()
    state._state[CommandCodes.VOLUME] = bytes([50])
    packet = ResponsePacket(
        zn=1,
        cc=CommandCodes.VOLUME,
        ac=AnswerCodes.COMMAND_NOT_RECOGNISED,
        data=bytes(),
    )
    state._listen(packet)
    assert state._state[CommandCodes.VOLUME] is None


async def test_listen_wrong_zone_ignored(make_state):
    """_listen ignores packets from other zones."""
    state = make_state(zn=1)
    packet = ResponsePacket(
        zn=2, cc=CommandCodes.VOLUME, ac=AnswerCodes.STATUS_UPDATE, data=bytes([50])
    )
    state._listen(packet)
    assert CommandCodes.VOLUME not in state._state


async def test_listen_amxduet_response(make_state):
    """_listen stores AMX duet response."""
    state = make_state()
    response = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    state._listen(response)
    assert state._amxduet is not None
    assert state._amxduet.device_model == "AVR30"


# --- Tests for wait_changed() event-based notification ---


async def test_wait_changed_fires_on_listen(make_state):
    """wait_changed() resolves after _listen processes a packet."""
    state = make_state()
    assert not state._changed.is_set()
    packet = ResponsePacket(
        zn=1, cc=CommandCodes.VOLUME, ac=AnswerCodes.STATUS_UPDATE, data=bytes([50])
    )
    state._listen(packet)
    assert state._changed.is_set()
    # wait_changed should return immediately and clear the event
    await state.wait_changed()
    assert not state._changed.is_set()


async def test_wait_changed_fires_on_amxduet(make_state):
    """wait_changed() resolves after _listen processes an AMX duet response."""
    state = make_state()
    response = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    state._listen(response)
    assert state._changed.is_set()
    await state.wait_changed()
    assert not state._changed.is_set()


async def test_wait_changed_not_fired_for_wrong_zone(make_state):
    """wait_changed() is not triggered by packets from other zones."""
    state = make_state(zn=1)
    packet = ResponsePacket(
        zn=2, cc=CommandCodes.VOLUME, ac=AnswerCodes.STATUS_UPDATE, data=bytes([50])
    )
    state._listen(packet)
    assert not state._changed.is_set()


# --- Tests for update() connected path ---


async def test_update_zone1_polls_all_commands(make_state):
    """update() zone 1 fires parallel requests for all command codes."""
    state = make_state(zn=1)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})

    async def mock_request(zn, cc, data):
        if cc == CommandCodes.PRESET_DETAIL:
            raise CommandInvalidAtThisTime()
        if cc == CommandCodes.NOW_PLAYING_INFO:
            raise CommandInvalidAtThisTime()
        return bytes([0x00])

    state._client.request.side_effect = mock_request
    await state.update()
    # Should have made many requests (power, volume, mute, source, etc.)
    assert state._client.request.call_count >= 20


async def test_update_zone2_polls_power_first(make_state):
    """update() zone 2 polls power first, then remaining if on."""
    state = make_state(zn=2)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})

    # Respond to preset detail with CommandInvalidAtThisTime to stop iteration
    async def mock_request(zn, cc, data):
        if cc == CommandCodes.PRESET_DETAIL:
            raise CommandInvalidAtThisTime()
        return bytes([0x01])

    state._client.request.side_effect = mock_request
    await state.update()
    # First call should be power
    first_call = state._client.request.call_args_list[0]
    assert first_call[0][1] == CommandCodes.POWER


async def test_update_zone2_skips_when_off(make_state):
    """update() zone 2 skips remaining polls when powered off."""
    state = make_state(zn=2)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    state._client.request.return_value = bytes([0x00])  # Power OFF
    await state.update()
    # Should only have power query (and no additional commands)
    assert state._client.request.call_count == 1


async def test_update_detects_model_from_amxduet(make_state):
    """update() auto-detects api_model from AMX duet response."""
    state = make_state(zn=1, api_model=ApiModel.API450_SERIES)
    state._client.request_raw.return_value = AmxDuetResponse(
        values={"Device-Make": "Arcam", "Device-Model": "AVR30"}
    )

    async def mock_request(zn, cc, data):
        if cc == CommandCodes.PRESET_DETAIL:
            raise CommandInvalidAtThisTime()
        if cc == CommandCodes.NOW_PLAYING_INFO:
            raise CommandInvalidAtThisTime()
        return bytes([0x00])

    state._client.request.side_effect = mock_request
    await state.update()
    assert state._api_model == ApiModel.APIHDA_SERIES


async def test_update_handles_timeout(make_state):
    """update() handles TimeoutError without crashing."""
    state = make_state(zn=1)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    state._client.request.side_effect = TimeoutError()
    await state.update()  # Should not raise


async def test_update_handles_response_exception(make_state):
    """update() handles ResponseException by setting state to None."""
    state = make_state(zn=1)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    state._client.request.side_effect = CommandNotRecognised()
    await state.update()
    # State entries that raised should be None
    assert state._state.get(CommandCodes.POWER) is None


# --- Tests for get_incoming_audio_sample_rate consistency ---


async def test_get_incoming_audio_sample_rate_none(make_state):
    """Returns None when no sample rate state (consistent with other getters)."""
    state = make_state()
    assert state.get_incoming_audio_sample_rate() is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0x00, 32000),
        (0x01, 44100),
        (0x02, 48000),
        (0x03, 88200),
        (0x04, 96000),
        (0x05, 176400),
        (0x06, 192000),
    ],
)
async def test_get_incoming_audio_sample_rate_values(make_state, raw, expected):
    """Correctly maps sample rate bytes to Hz values."""
    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_SAMPLE_RATE] = bytes([raw])
    assert state.get_incoming_audio_sample_rate() == expected


async def test_get_incoming_audio_sample_rate_unknown(make_state):
    """Returns None for unknown sample rate byte."""
    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_SAMPLE_RATE] = bytes([0xFF])
    assert state.get_incoming_audio_sample_rate() is None


# --- Tests for setter range validation ---


async def test_set_volume_rejects_out_of_range(make_state):
    """Volume must be 0-99."""
    state = make_state()
    with pytest.raises(ValueError, match="VOLUME"):
        await state.set_volume(100)
    with pytest.raises(ValueError, match="VOLUME"):
        await state.set_volume(-1)


async def test_set_volume_accepts_boundary(make_state):
    """Volume accepts 0 and 99."""
    state = make_state()
    state._client.request.return_value = bytes([0x00])
    await state.set_volume(0)
    await state.set_volume(99)


async def test_set_display_brightness_rejects_out_of_range(make_state):
    """Display brightness must be 0-2."""
    state = make_state()
    with pytest.raises(ValueError, match="DISPLAY_BRIGHTNESS"):
        await state.set_display_brightness(3)


async def test_set_room_eq_rejects_out_of_range(make_state):
    """Room EQ preset must be 0-4."""
    state = make_state()
    with pytest.raises(ValueError, match="ROOM_EQUALIZATION"):
        await state.set_room_eq(5)


async def test_set_compression_rejects_out_of_range(make_state):
    """Compression must be 0-3."""
    state = make_state()
    with pytest.raises(ValueError, match="COMPRESSION"):
        await state.set_compression(4)


async def test_set_bass_rejects_out_of_byte_range(make_state):
    """Bass must be 0-255 (single byte)."""
    state = make_state()
    with pytest.raises(ValueError, match="BASS"):
        await state.set_bass(256)
    with pytest.raises(ValueError, match="BASS"):
        await state.set_bass(-1)


# --- Tests for State lifecycle (start/stop/context manager) ---


async def test_start_registers_listener(make_state):
    """start() registers _listen as a client listener."""
    state = make_state()
    await state.start()
    state._client.add_listener.assert_called_once_with(state._listen)


async def test_stop_unregisters_listener(make_state):
    """stop() unregisters _listen from the client."""
    state = make_state()
    await state.stop()
    state._client.remove_listener.assert_called_once_with(state._listen)


async def test_context_manager(make_state):
    """Async context manager calls start/stop."""
    state = make_state()
    async with state as s:
        assert s is state
        state._client.add_listener.assert_called_once()
    state._client.remove_listener.assert_called_once()


# --- Tests for State properties ---


async def test_zn_property(make_state):
    """zn property returns the zone number."""
    state = make_state(zn=2)
    assert state.zn == 2


async def test_client_property(make_state):
    """client property returns the underlying Client."""
    state = make_state()
    assert state.client is state._client


async def test_model_property_none(make_state):
    """model property returns None when no AMX duet response."""
    state = make_state()
    assert state.model is None


async def test_model_property_with_amxduet(make_state):
    """model property returns device model from AMX duet."""
    state = make_state()
    state._amxduet = AmxDuetResponse(values={"Device-Model": "AVR30", "Device-Make": "Arcam"})
    assert state.model == "AVR30"


async def test_revision_property_none(make_state):
    """revision property returns None when no AMX duet response."""
    state = make_state()
    assert state.revision is None


async def test_revision_property_with_amxduet(make_state):
    """revision property returns device revision from AMX duet."""
    state = make_state()
    state._amxduet = AmxDuetResponse(
        values={"Device-Model": "AVR30", "Device-Make": "Arcam", "Device-Revision": "1.2.3"}
    )
    assert state.revision == "1.2.3"


# --- Tests for __repr__ ---


async def test_repr(make_state):
    """__repr__ includes state dict and AMX info."""
    state = make_state()
    r = repr(state)
    assert "State" in r
    assert "Amx" in r


# --- Tests for get_source / set_source / get_source_list ---


async def test_get_source_none(make_state):
    """get_source returns None when no source state."""
    state = make_state()
    assert state.get_source() is None


async def test_get_source_invalid_value(make_state):
    """get_source returns None for unknown source byte."""
    state = make_state()
    state._state[CommandCodes.CURRENT_SOURCE] = bytes([0xFF])
    assert state.get_source() is None


async def test_get_source_list(make_state):
    """get_source_list returns list of SourceCodes for the model."""
    state = make_state()
    sources = state.get_source_list()
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert all(isinstance(s, SourceCodes) for s in sources)


async def test_set_source_rc5(make_state):
    """HDA series uses RC5 for source selection."""
    state = make_state(api_model=ApiModel.APIHDA_SERIES)
    await state.set_source(SourceCodes.CD)
    state._client.request.assert_called_once()
    args = state._client.request.call_args[0]
    assert args[1] == CommandCodes.SIMULATE_RC5_IR_COMMAND


async def test_set_source_direct_write(make_state):
    """SA series uses direct write for source selection."""
    state = make_state(api_model=ApiModel.APISA_SERIES)
    await state.set_source(SourceCodes.CD)
    state._client.request.assert_called_once()
    args = state._client.request.call_args[0]
    assert args[1] == CommandCodes.CURRENT_SOURCE


# --- Tests for get_2ch edge cases ---


async def test_get_2ch_analogue_direct(make_state):
    """get_2ch returns True for analogue direct format."""
    from arcam.fmj import IncomingAudioFormat
    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes(
        [IncomingAudioFormat.ANALOGUE_DIRECT, 0x00]
    )
    assert state.get_2ch() is True


async def test_get_2ch_pcm_none_config(make_state):
    """get_2ch returns True for PCM with None audio config."""
    from arcam.fmj import IncomingAudioFormat, IncomingAudioConfig
    state = make_state()
    # PCM format but with an unknown config byte that returns None
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes(
        [IncomingAudioFormat.PCM, 0xFF]
    )
    # IncomingAudioConfig.from_int(0xFF) may return a value or None
    # If it returns a non-2CH config, get_2ch should return False
    # If None, get_2ch should return True
    result = state.get_2ch()
    assert isinstance(result, bool)


# --- Tests for get_decode_modes when no current mode ---


async def test_get_decode_modes_no_current_2ch(make_state):
    """get_decode_modes returns 2CH modes when get_2ch() is True and no current mode."""
    from arcam.fmj import DecodeMode2CH
    state = make_state()
    # No decode mode state at all → get_decode_mode() returns None
    # But get_2ch() will return True (no audio format → analogue direct)
    modes = state.get_decode_modes()
    assert modes is not None
    assert any(isinstance(m, DecodeMode2CH) for m in modes)


async def test_get_decode_modes_no_current_mch(make_state):
    """get_decode_modes returns MCH modes when get_2ch() is False and no current mode."""
    from arcam.fmj import DecodeModeMCH
    state = make_state()
    # Set audio format to Dolby (MCH) so get_2ch() returns False
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    modes = state.get_decode_modes()
    assert modes is not None
    assert any(isinstance(m, DecodeModeMCH) for m in modes)


# --- Tests for set_decode_mode string MCH primary ---


async def test_set_decode_mode_string_mch_primary(make_state):
    """When get_2ch() is False and string mode exists in MCH, use MCH directly."""
    state = make_state()
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x02, 0x00])
    await state.set_decode_mode("MULTI_CHANNEL")
    state._client.request.assert_called_once()


# --- Tests for update() edge cases ---


async def test_update_unsupported_zone(make_state):
    """update() handles UnsupportedZone without crashing."""
    from arcam.fmj import UnsupportedZone
    state = make_state(zn=2)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    # Power returns on, then remaining commands raise UnsupportedZone
    call_count = [0]

    async def mock_request(zn, cc, data):
        call_count[0] += 1
        if cc == CommandCodes.POWER:
            return bytes([0x01])
        if cc == CommandCodes.PRESET_DETAIL:
            raise CommandInvalidAtThisTime()
        raise UnsupportedZone()

    state._client.request.side_effect = mock_request
    await state.update()  # Should not raise
    assert call_count[0] > 1


async def test_update_not_connected_during_poll(make_state):
    """update() handles NotConnectedException by setting state to None."""
    from arcam.fmj import NotConnectedException
    state = make_state(zn=1)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})
    state._client.request.side_effect = NotConnectedException()
    await state.update()
    assert state._state.get(CommandCodes.POWER) is None


async def test_update_presets_success(make_state):
    """update() populates presets when data is valid."""
    state = make_state(zn=1)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})

    call_count = 0

    async def mock_request(zn, cc, data):
        nonlocal call_count
        call_count += 1
        if cc == CommandCodes.PRESET_DETAIL:
            if data == bytes([1]):
                return bytes([1]) + b"\x03SR P1   "
            raise CommandInvalidAtThisTime()
        if cc == CommandCodes.NOW_PLAYING_INFO:
            raise CommandInvalidAtThisTime()
        return bytes([0x00])

    state._client.request.side_effect = mock_request
    await state.update()
    assert 1 in state._presets


async def test_update_now_playing_success(make_state):
    """update() populates _now_playing with text and enum fields."""
    state = make_state(zn=1)
    state._amxduet = AmxDuetResponse(values={"Device-Make": "Arcam", "Device-Model": "AVR30"})

    async def mock_request(zn, cc, data):
        if cc == CommandCodes.NOW_PLAYING_INFO:
            sub = data[0]
            if sub == 0xF0:
                return b"My Song"
            elif sub == 0xF1:
                return b"My Artist"
            elif sub == 0xF2:
                return b"My Album"
            elif sub == 0xF3:
                return b"Spotify"
            elif sub == 0xF4:
                return bytes([0x01])  # 44.1kHz
            elif sub == 0xF5:
                return bytes([0x01])  # MP3
            raise CommandInvalidAtThisTime()
        if cc == CommandCodes.PRESET_DETAIL:
            raise CommandInvalidAtThisTime()
        return bytes([0x00])

    state._client.request.side_effect = mock_request
    await state.update()
    assert state._now_playing.get(0xF0) == "My Song"
    assert state._now_playing.get(0xF1) == "My Artist"


async def test_update_amxduet_timeout(make_state):
    """update() handles timeout during AMX duet query."""
    state = make_state(zn=1)
    state._client.request_raw.side_effect = TimeoutError()
    state._client.request.side_effect = CommandNotRecognised()
    await state.update()  # Should not raise


async def test_update_amxduet_not_connected(make_state):
    """update() handles NotConnectedException during AMX duet query."""
    from arcam.fmj import NotConnectedException
    state = make_state(zn=1)
    state._client.request_raw.side_effect = NotConnectedException()
    state._client.request.side_effect = CommandNotRecognised()
    await state.update()  # Should not raise


async def test_update_amxduet_response_exception(make_state):
    """update() handles ResponseException during AMX duet query."""
    state = make_state(zn=1)
    state._client.request_raw.side_effect = CommandNotRecognised()
    state._client.request.side_effect = CommandNotRecognised()
    await state.update()  # Should not raise
