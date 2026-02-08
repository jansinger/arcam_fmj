import pytest
from unittest.mock import AsyncMock, MagicMock, call
from arcam.fmj.client import Client
from arcam.fmj.state import State
from arcam.fmj import (
    AnswerCodes,
    ApiModel,
    CommandCodes,
    CommandInvalidAtThisTime,
    ResponsePacket,
    ResponseException,
    POWER_WRITE_SUPPORTED,
    MUTE_WRITE_SUPPORTED,
    VOLUME_STEP_SUPPORTED,
    RC5CODE_MUTE,
    RC5CODE_VOLUME,
)

TEST_PARAMS = [
    (1, ApiModel.API450_SERIES),
    (1, ApiModel.API860_SERIES),
    (1, ApiModel.APIHDA_SERIES),
    (1, ApiModel.APISA_SERIES),
    (1, ApiModel.APIPA_SERIES),
    (1, ApiModel.APIST_SERIES),
    (2, ApiModel.API450_SERIES),
    (2, ApiModel.API860_SERIES),
    (2, ApiModel.APIHDA_SERIES),
    (2, ApiModel.APISA_SERIES),
    (2, ApiModel.APIPA_SERIES),
]

# zn, api_model, power
PARAMS_TO_RC5COMMAND = {
    (1, ApiModel.API450_SERIES, True): bytes([16, 123]),
    (1, ApiModel.API450_SERIES, False): bytes([16, 124]),
    (1, ApiModel.API860_SERIES, True): bytes([16, 123]),
    (1, ApiModel.API860_SERIES, False): bytes([16, 124]),
    (1, ApiModel.APIHDA_SERIES, True): bytes([16, 123]),
    (1, ApiModel.APIHDA_SERIES, False): bytes([16, 124]),
    (1, ApiModel.APISA_SERIES, True): bytes([16, 123]),
    (1, ApiModel.APISA_SERIES, False): bytes([16, 124]),
    (2, ApiModel.API450_SERIES, True): bytes([23, 123]),
    (2, ApiModel.API450_SERIES, False): bytes([23, 124]),
    (2, ApiModel.API860_SERIES, True): bytes([23, 123]),
    (2, ApiModel.API860_SERIES, False): bytes([23, 124]),
    (2, ApiModel.APIHDA_SERIES, True): bytes([23, 123]),
    (2, ApiModel.APIHDA_SERIES, False): bytes([23, 124]),
    (2, ApiModel.APISA_SERIES, True): bytes([16, 123]),
    (2, ApiModel.APISA_SERIES, False): bytes([16, 124]),
}


@pytest.mark.parametrize("zn, api_model", TEST_PARAMS)
async def test_power_on(zn, api_model):
    client = MagicMock(spec=Client)
    state = State(client, zn, api_model)
    response = ResponsePacket(
        zn,
        CommandCodes.SIMULATE_RC5_IR_COMMAND,
        AnswerCodes.STATUS_UPDATE,
        bytes([0x01]),
    )
    client.request.return_value = response
    await state.set_power(True)
    if api_model in POWER_WRITE_SUPPORTED:
        client.request.assert_called_with(zn, CommandCodes.POWER, bytes([0x01]))
    else:
        # zn, api_model, power
        code = PARAMS_TO_RC5COMMAND[zn, api_model, True]
        client.request.assert_called_with(
            zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, code
        )


@pytest.mark.parametrize("zn, api_model", TEST_PARAMS)
async def test_power_off(zn, api_model):
    client = MagicMock(spec=Client)
    state = State(client, zn, api_model)

    assert state.get_power() is None
    await state.set_power(False)
    if api_model in POWER_WRITE_SUPPORTED:
        client.request.assert_called_with(zn, CommandCodes.POWER, bytes([0x00]))
    else:
        # zn, api_model, power
        code = PARAMS_TO_RC5COMMAND[zn, api_model, False]
        client.send.assert_called_with(zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, code)
    assert state.get_power() is False


# --- Tests for new get/set methods (bass, treble, balance, etc.) ---


INT_PARAMETER_TESTS = [
    ("bass", CommandCodes.BASS_EQUALIZATION),
    ("treble", CommandCodes.TREBLE_EQUALIZATION),
    ("balance", CommandCodes.BALANCE),
    ("subwoofer_trim", CommandCodes.SUBWOOFER_TRIM),
    ("lipsync_delay", CommandCodes.LIPSYNC_DELAY),
    ("display_brightness", CommandCodes.DISPLAY_BRIGHTNESS),
    ("compression", CommandCodes.COMPRESSION),
]


@pytest.mark.parametrize("param_name, command_code", INT_PARAMETER_TESTS)
async def test_get_int_param_none(param_name, command_code):
    """Test that get methods return None when no state is set."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    getter = getattr(state, f"get_{param_name}")
    assert getter() is None


@pytest.mark.parametrize("param_name, command_code", INT_PARAMETER_TESTS)
@pytest.mark.parametrize("value", [0, 5, 127, 255])
async def test_get_int_param_value(param_name, command_code, value):
    """Test that get methods correctly decode state bytes."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[command_code] = bytes([value])
    getter = getattr(state, f"get_{param_name}")
    assert getter() == value


@pytest.mark.parametrize("param_name, command_code", INT_PARAMETER_TESTS)
@pytest.mark.parametrize("value", [0, 50, 255])
async def test_set_int_param(param_name, command_code, value):
    """Test that set methods send correct command to client."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    setter = getattr(state, f"set_{param_name}")
    await setter(value)
    client.request.assert_called_with(1, command_code, bytes([value]))


@pytest.mark.parametrize("zn", [1, 2])
@pytest.mark.parametrize("param_name, command_code", INT_PARAMETER_TESTS)
async def test_set_int_param_zones(zn, param_name, command_code):
    """Test that set methods use correct zone."""
    client = MagicMock(spec=Client)
    state = State(client, zn, ApiModel.API450_SERIES)
    setter = getattr(state, f"set_{param_name}")
    await setter(42)
    client.request.assert_called_with(zn, command_code, bytes([42]))


# --- Tests for room_eq (boolean parameter) ---


async def test_get_room_eq_none():
    """Test that get_room_eq returns None when no state is set."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    assert state.get_room_eq() is None


@pytest.mark.parametrize("raw, expected", [
    (0x00, False),
    (0x01, True),
    (0x02, True),
])
async def test_get_room_eq_value(raw, expected):
    """Test that get_room_eq correctly interprets state as boolean."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[CommandCodes.ROOM_EQUALIZATION] = bytes([raw])
    assert state.get_room_eq() == expected


@pytest.mark.parametrize("enabled, expected_byte", [
    (True, 0x01),
    (False, 0x00),
])
async def test_set_room_eq(enabled, expected_byte):
    """Test that set_room_eq sends correct boolean encoding."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    await state.set_room_eq(enabled)
    client.request.assert_called_with(
        1, CommandCodes.ROOM_EQUALIZATION, bytes([expected_byte])
    )


# --- Tests for to_dict including new parameters ---


async def test_to_dict_includes_new_params():
    """Test that to_dict includes all new parameter keys."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    result = state.to_dict()
    for key in [
        "BASS", "TREBLE", "BALANCE", "SUBWOOFER_TRIM",
        "LIPSYNC_DELAY", "DISPLAY_BRIGHTNESS", "ROOM_EQUALIZATION",
        "COMPRESSION",
    ]:
        assert key in result


async def test_to_dict_with_values():
    """Test that to_dict returns correct values for new parameters."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[CommandCodes.BASS_EQUALIZATION] = bytes([10])
    state._state[CommandCodes.TREBLE_EQUALIZATION] = bytes([20])
    state._state[CommandCodes.BALANCE] = bytes([30])
    state._state[CommandCodes.SUBWOOFER_TRIM] = bytes([40])
    state._state[CommandCodes.LIPSYNC_DELAY] = bytes([50])
    state._state[CommandCodes.DISPLAY_BRIGHTNESS] = bytes([2])
    state._state[CommandCodes.ROOM_EQUALIZATION] = bytes([1])
    state._state[CommandCodes.COMPRESSION] = bytes([3])

    result = state.to_dict()
    assert result["BASS"] == 10
    assert result["TREBLE"] == 20
    assert result["BALANCE"] == 30
    assert result["SUBWOOFER_TRIM"] == 40
    assert result["LIPSYNC_DELAY"] == 50
    assert result["DISPLAY_BRIGHTNESS"] == 2
    assert result["ROOM_EQUALIZATION"] is True
    assert result["COMPRESSION"] == 3


# --- Tests for mute state query fix on AV receivers ---

# Models that use RC5 for mute (NOT in MUTE_WRITE_SUPPORTED)
RC5_MUTE_PARAMS = [
    (1, ApiModel.API450_SERIES),
    (1, ApiModel.API860_SERIES),
    (1, ApiModel.APIHDA_SERIES),
    (2, ApiModel.API450_SERIES),
    (2, ApiModel.API860_SERIES),
    (2, ApiModel.APIHDA_SERIES),
]

# Models that use direct mute write
DIRECT_MUTE_PARAMS = [
    (1, ApiModel.APISA_SERIES),
    (1, ApiModel.APIPA_SERIES),
    (1, ApiModel.APIST_SERIES),
]


@pytest.mark.parametrize("zn, api_model", RC5_MUTE_PARAMS)
async def test_set_mute_rc5_queries_mute_state(zn, api_model):
    """Test that set_mute queries mute state after RC5 command on AV receivers."""
    client = MagicMock(spec=Client)
    # Return mute state bytes on second call (the query)
    client.request = AsyncMock(side_effect=[
        bytes([0x00]),  # RC5 command response
        bytes([0x00]),  # Mute query response
    ])
    state = State(client, zn, api_model)
    await state.set_mute(True)

    rc5_code = RC5CODE_MUTE[(api_model, zn)][True]
    assert client.request.call_count == 2
    client.request.assert_any_call(
        zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, rc5_code
    )
    client.request.assert_any_call(
        zn, CommandCodes.MUTE, bytes([0xF0])
    )


@pytest.mark.parametrize("zn, api_model", RC5_MUTE_PARAMS)
async def test_set_mute_rc5_updates_state(zn, api_model):
    """Test that mute state is updated after RC5 mute query succeeds."""
    client = MagicMock(spec=Client)
    mute_data = bytes([0x00])  # muted
    client.request = AsyncMock(side_effect=[
        bytes([0x00]),  # RC5 command response
        mute_data,      # Mute query response
    ])
    state = State(client, zn, api_model)
    await state.set_mute(True)

    assert state._state[CommandCodes.MUTE] == mute_data


@pytest.mark.parametrize("zn, api_model", RC5_MUTE_PARAMS)
async def test_set_mute_rc5_query_failure_no_crash(zn, api_model):
    """Test that set_mute doesn't crash when mute query fails after RC5 command."""
    client = MagicMock(spec=Client)
    client.request = AsyncMock(side_effect=[
        bytes([0x00]),      # RC5 command response
        TimeoutError(),     # Mute query fails
    ])
    state = State(client, zn, api_model)
    # Should not raise
    await state.set_mute(True)
    # Mute state should be set to None (unknown) consistent with update() pattern
    assert state._state[CommandCodes.MUTE] is None
    assert state.get_mute() is None


@pytest.mark.parametrize("zn, api_model", RC5_MUTE_PARAMS)
async def test_set_mute_rc5_query_response_exception(zn, api_model):
    """Test that ResponseException on mute query sets state to None."""
    client = MagicMock(spec=Client)
    client.request = AsyncMock(side_effect=[
        bytes([0x00]),
        ResponseException(AnswerCodes.COMMAND_NOT_RECOGNISED),
    ])
    state = State(client, zn, api_model)
    await state.set_mute(True)
    assert state._state[CommandCodes.MUTE] is None


@pytest.mark.parametrize("zn, api_model", DIRECT_MUTE_PARAMS)
async def test_set_mute_direct_write(zn, api_model):
    """Test that direct-write models send MUTE command directly without follow-up query."""
    client = MagicMock(spec=Client)
    state = State(client, zn, api_model)
    await state.set_mute(True)
    client.request.assert_called_once_with(zn, CommandCodes.MUTE, bytes([0x00]))


@pytest.mark.parametrize("zn, api_model", DIRECT_MUTE_PARAMS)
async def test_set_unmute_direct_write(zn, api_model):
    """Test that direct-write models send correct unmute command."""
    client = MagicMock(spec=Client)
    state = State(client, zn, api_model)
    await state.set_mute(False)
    client.request.assert_called_once_with(zn, CommandCodes.MUTE, bytes([0x01]))


# --- Test get_mute ---


async def test_get_mute_none():
    """Test that get_mute returns None when no state is set."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    assert state.get_mute() is None


@pytest.mark.parametrize("raw, expected", [
    (0x00, True),   # 0x00 means muted
    (0x01, False),  # 0x01 means not muted
])
async def test_get_mute_value(raw, expected):
    """Test that get_mute correctly interprets state bytes."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[CommandCodes.MUTE] = bytes([raw])
    assert state.get_mute() == expected


# --- Test state listener updates ---


async def test_listen_updates_state():
    """Test that _listen callback correctly updates state from status update packets."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    packet = ResponsePacket(
        1, CommandCodes.BASS_EQUALIZATION, AnswerCodes.STATUS_UPDATE, bytes([15])
    )
    state._listen(packet)
    assert state.get_bass() == 15


async def test_listen_ignores_other_zone():
    """Test that _listen ignores packets from other zones."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    packet = ResponsePacket(
        2, CommandCodes.BASS_EQUALIZATION, AnswerCodes.STATUS_UPDATE, bytes([15])
    )
    state._listen(packet)
    assert state.get_bass() is None


async def test_listen_clears_state_on_error():
    """Test that _listen sets state to None for non-status-update packets."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[CommandCodes.TREBLE_EQUALIZATION] = bytes([10])
    packet = ResponsePacket(
        1, CommandCodes.TREBLE_EQUALIZATION, AnswerCodes.COMMAND_NOT_RECOGNISED, bytes([])
    )
    state._listen(packet)
    assert state.get_treble() is None


# --- Tests for volume get/set/inc/dec ---


async def test_get_volume_none():
    """Test that get_volume returns None when no state is set."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    assert state.get_volume() is None


@pytest.mark.parametrize("value", [0, 50, 99])
async def test_get_volume_value(value):
    """Test that get_volume correctly decodes state bytes."""
    client = MagicMock(spec=Client)
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[CommandCodes.VOLUME] = bytes([value])
    assert state.get_volume() == value


@pytest.mark.parametrize("zn", [1, 2])
async def test_set_volume(zn):
    """Test that set_volume sends correct command."""
    client = MagicMock(spec=Client)
    state = State(client, zn, ApiModel.API450_SERIES)
    await state.set_volume(42)
    client.request.assert_called_with(zn, CommandCodes.VOLUME, bytes([42]))


@pytest.mark.parametrize("api_model", [ApiModel.APIST_SERIES])
async def test_inc_volume_step_supported(api_model):
    """Test that inc_volume uses VOLUME 0xF1 for step-supported models."""
    client = MagicMock(spec=Client)
    state = State(client, 1, api_model)
    await state.inc_volume()
    client.request.assert_called_with(1, CommandCodes.VOLUME, bytes([0xF1]))


@pytest.mark.parametrize("api_model", [ApiModel.APIST_SERIES])
async def test_dec_volume_step_supported(api_model):
    """Test that dec_volume uses VOLUME 0xF2 for step-supported models."""
    client = MagicMock(spec=Client)
    state = State(client, 1, api_model)
    await state.dec_volume()
    client.request.assert_called_with(1, CommandCodes.VOLUME, bytes([0xF2]))


@pytest.mark.parametrize("zn, api_model", [
    (1, ApiModel.API450_SERIES),
    (1, ApiModel.API860_SERIES),
    (1, ApiModel.APIHDA_SERIES),
    (2, ApiModel.API450_SERIES),
])
async def test_inc_volume_rc5(zn, api_model):
    """Test that inc_volume uses RC5 for non-step-supported models."""
    client = MagicMock(spec=Client)
    state = State(client, zn, api_model)
    await state.inc_volume()
    rc5_code = RC5CODE_VOLUME[(api_model, zn)][True]
    client.request.assert_called_with(
        zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, rc5_code
    )


@pytest.mark.parametrize("zn, api_model", [
    (1, ApiModel.API450_SERIES),
    (1, ApiModel.API860_SERIES),
    (1, ApiModel.APIHDA_SERIES),
    (2, ApiModel.API450_SERIES),
])
async def test_dec_volume_rc5(zn, api_model):
    """Test that dec_volume uses RC5 for non-step-supported models."""
    client = MagicMock(spec=Client)
    state = State(client, zn, api_model)
    await state.dec_volume()
    rc5_code = RC5CODE_VOLUME[(api_model, zn)][False]
    client.request.assert_called_with(
        zn, CommandCodes.SIMULATE_RC5_IR_COMMAND, rc5_code
    )


# --- Tests for update() ---

AUDIO_CONTROL_CODES = {
    CommandCodes.BASS_EQUALIZATION,
    CommandCodes.TREBLE_EQUALIZATION,
    CommandCodes.BALANCE,
    CommandCodes.SUBWOOFER_TRIM,
    CommandCodes.LIPSYNC_DELAY,
    CommandCodes.DISPLAY_BRIGHTNESS,
    CommandCodes.ROOM_EQUALIZATION,
    CommandCodes.COMPRESSION,
}

BASE_UPDATE_CODES = {
    CommandCodes.POWER,
    CommandCodes.VOLUME,
    CommandCodes.MUTE,
    CommandCodes.CURRENT_SOURCE,
    CommandCodes.MENU,
    CommandCodes.DECODE_MODE_STATUS_2CH,
    CommandCodes.DECODE_MODE_STATUS_MCH,
    CommandCodes.INCOMING_VIDEO_PARAMETERS,
    CommandCodes.INCOMING_AUDIO_FORMAT,
    CommandCodes.INCOMING_AUDIO_SAMPLE_RATE,
    CommandCodes.DAB_STATION,
    CommandCodes.DLS_PDT_INFO,
    CommandCodes.RDS_INFORMATION,
    CommandCodes.TUNER_PRESET,
}

# Zone 2+ only polls zone-supported commands (no MENU, DECODE_MODE, VIDEO/AUDIO info)
ZONE2_UPDATE_CODES = {
    CommandCodes.VOLUME,
    CommandCodes.MUTE,
    CommandCodes.CURRENT_SOURCE,
    CommandCodes.DAB_STATION,
    CommandCodes.DLS_PDT_INFO,
    CommandCodes.RDS_INFORMATION,
    CommandCodes.TUNER_PRESET,
}


async def test_update_zone1_polls_audio_controls():
    """Test that update() on Zone 1 polls audio control commands."""
    client = MagicMock(spec=Client)
    client.connected = True
    client.request = AsyncMock(side_effect=CommandInvalidAtThisTime)
    client.request_raw = AsyncMock(side_effect=TimeoutError)
    state = State(client, 1, ApiModel.API450_SERIES)

    await state.update()

    polled_codes = {
        args[0][1]
        for args in client.request.call_args_list
        if len(args[0]) >= 2
    }
    for cc in AUDIO_CONTROL_CODES:
        assert cc in polled_codes, f"{cc} should be polled on Zone 1"


async def test_update_zone2_skips_audio_controls():
    """Test that update() on Zone 2 does NOT poll audio control commands even when powered on."""
    client = MagicMock(spec=Client)
    client.connected = True

    # POWER returns "on" (0x01), other commands raise CommandInvalidAtThisTime
    async def mock_request(zn, cc, data):
        if cc == CommandCodes.POWER:
            return bytes([0x01])
        raise CommandInvalidAtThisTime()

    client.request = AsyncMock(side_effect=mock_request)
    client.request_raw = AsyncMock(side_effect=TimeoutError)
    state = State(client, 2, ApiModel.API450_SERIES)

    await state.update()

    polled_codes = {
        args[0][1]
        for args in client.request.call_args_list
        if len(args[0]) >= 2
    }
    for cc in AUDIO_CONTROL_CODES:
        assert cc not in polled_codes, f"{cc} should NOT be polled on Zone 2"


async def test_update_zone2_powered_on_polls_zone_commands():
    """Test that update() on Zone 2 polls zone commands when powered on."""
    client = MagicMock(spec=Client)
    client.connected = True

    # POWER returns "on" (0x01), other commands raise CommandInvalidAtThisTime
    async def mock_request(zn, cc, data):
        if cc == CommandCodes.POWER:
            return bytes([0x01])
        raise CommandInvalidAtThisTime()

    client.request = AsyncMock(side_effect=mock_request)
    client.request_raw = AsyncMock(side_effect=TimeoutError)
    state = State(client, 2, ApiModel.API450_SERIES)

    await state.update()

    polled_codes = {
        args[0][1]
        for args in client.request.call_args_list
        if len(args[0]) >= 2
    }
    # POWER should always be polled
    assert CommandCodes.POWER in polled_codes
    # When powered on, zone-supported commands should be polled
    for cc in ZONE2_UPDATE_CODES:
        assert cc in polled_codes, f"{cc} should be polled on Zone 2 when powered on"


async def test_update_zone2_powered_off_only_polls_power():
    """Test that update() on Zone 2 only polls POWER when zone is off."""
    client = MagicMock(spec=Client)
    client.connected = True

    # POWER returns "off" (0x00)
    async def mock_request(zn, cc, data):
        if cc == CommandCodes.POWER:
            return bytes([0x00])
        raise CommandInvalidAtThisTime()

    client.request = AsyncMock(side_effect=mock_request)
    client.request_raw = AsyncMock(side_effect=TimeoutError)
    state = State(client, 2, ApiModel.API450_SERIES)

    await state.update()

    polled_codes = {
        args[0][1]
        for args in client.request.call_args_list
        if len(args[0]) >= 2
    }
    # Only POWER should be polled when zone is off
    assert polled_codes == {CommandCodes.POWER}


async def test_update_disconnected_clears_state():
    """Test that update() clears state when client is disconnected."""
    client = MagicMock(spec=Client)
    client.connected = False
    state = State(client, 1, ApiModel.API450_SERIES)
    state._state[CommandCodes.POWER] = bytes([1])
    state._state[CommandCodes.VOLUME] = bytes([50])
    state._state[CommandCodes.BASS_EQUALIZATION] = bytes([10])

    await state.update()

    assert state._state == {}


async def test_update_disconnected_empty_state_no_reset():
    """Test that update() doesn't create new dict when state is already empty."""
    client = MagicMock(spec=Client)
    client.connected = False
    state = State(client, 1, ApiModel.API450_SERIES)
    original_state = state._state

    await state.update()

    assert state._state is original_state
