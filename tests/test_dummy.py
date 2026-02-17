"""Unit tests for dummy.py: DummyServer handlers."""

import pytest

from arcam.fmj import (
    RC5CODE_DECODE_MODE_2CH,
    RC5CODE_DECODE_MODE_MCH,
    RC5CODE_SOURCE,
    ApiModel,
    CommandCodes,
    CommandInvalidAtThisTime,
    CommandNotRecognised,
    ResponsePacket,
)
from arcam.fmj.dummy import DummyServer


@pytest.fixture
def dummy():
    """Create a DummyServer for testing (no TCP, just handler logic)."""
    return DummyServer("localhost", 0, "AVR450")


@pytest.fixture
def dummy_hda():
    """Create a DummyServer with HDA model."""
    return DummyServer("localhost", 0, "AVR30")


# --- Constructor ---


def test_dummy_unknown_model():
    """DummyServer raises ValueError for unknown model."""
    with pytest.raises(ValueError, match="Unexpected model"):
        DummyServer("localhost", 0, "UNKNOWN_MODEL_XYZ")


def test_dummy_avr450_api_version(dummy):
    """DummyServer detects correct API version for AVR450."""
    assert dummy._api_version == ApiModel.API450_SERIES


def test_dummy_avr30_api_version(dummy_hda):
    """DummyServer detects correct API version for AVR30."""
    assert dummy_hda._api_version == ApiModel.APIHDA_SERIES


# --- Power handler ---


def test_get_power(dummy):
    """get_power returns power on."""
    assert dummy.get_power() == bytes([1])


# --- Volume handlers ---


def test_get_volume(dummy):
    """get_volume returns initial volume."""
    assert dummy.get_volume() == bytes([10])


def test_set_volume(dummy):
    """set_volume updates and returns new volume."""
    result = dummy.set_volume(data=bytes([42]))
    assert result == bytes([42])
    assert dummy.get_volume() == bytes([42])


# --- Source handlers ---


def test_get_source(dummy):
    """get_source returns initial source."""
    assert isinstance(dummy.get_source(), bytes)


def test_set_source(dummy):
    """set_source updates and returns new source."""
    result = dummy.set_source(data=bytes([0x05]))
    assert result == bytes([0x05])
    assert dummy.get_source() == bytes([0x05])


# --- IR command handler ---


def test_ir_command_source_change(dummy):
    """ir_command with source RC5 code changes source and returns two packets."""
    rc5_key = (dummy._api_version, 1)
    # Get the first source RC5 code
    first_source_code = next(iter(RC5CODE_SOURCE[rc5_key]))
    rc5_data = RC5CODE_SOURCE[rc5_key][first_source_code]

    result = dummy.ir_command(data=rc5_data)
    assert len(result) == 2
    assert isinstance(result[0], ResponsePacket)
    assert result[0].cc == CommandCodes.SIMULATE_RC5_IR_COMMAND
    assert result[1].cc == CommandCodes.CURRENT_SOURCE


def test_ir_command_decode_mode_2ch(dummy):
    """ir_command with 2CH decode mode RC5 code changes decode mode."""
    rc5_key = (dummy._api_version, 1)
    first_mode = next(iter(RC5CODE_DECODE_MODE_2CH[rc5_key]))
    rc5_data = RC5CODE_DECODE_MODE_2CH[rc5_key][first_mode]

    result = dummy.ir_command(data=rc5_data)
    assert len(result) == 2
    assert result[1].cc == CommandCodes.DECODE_MODE_STATUS_2CH


def test_ir_command_decode_mode_mch(dummy):
    """ir_command with MCH-only RC5 code changes MCH decode mode."""
    rc5_key = (dummy._api_version, 1)
    # Find an MCH RC5 code that doesn't overlap with 2CH codes
    mch_codes = RC5CODE_DECODE_MODE_MCH[rc5_key]
    two_ch_values = set(RC5CODE_DECODE_MODE_2CH[rc5_key].values())
    for _mode, rc5_data in mch_codes.items():
        if rc5_data not in two_ch_values:
            break
    else:
        pytest.skip("No unique MCH RC5 code for this model")

    result = dummy.ir_command(data=rc5_data)
    assert len(result) == 2
    assert result[1].cc == CommandCodes.DECODE_MODE_STATUS_MCH


def test_ir_command_unknown_code(dummy):
    """ir_command raises CommandNotRecognised for unknown RC5 code."""
    with pytest.raises(CommandNotRecognised):
        dummy.ir_command(data=bytes([0xFF, 0xFF]))


# --- Decode mode getters ---


def test_get_decode_mode_2ch(dummy):
    """get_decode_mode_2ch returns current 2CH decode mode."""
    result = dummy.get_decode_mode_2ch()
    assert isinstance(result, bytes)
    assert len(result) == 1


def test_get_decode_mode_mch(dummy):
    """get_decode_mode_mch returns current MCH decode mode."""
    result = dummy.get_decode_mode_mch()
    assert isinstance(result, bytes)
    assert len(result) == 1


# --- Audio/Video parameter getters ---


def test_get_incoming_video_parameters(dummy):
    """get_incoming_video_parameters returns raw bytes."""
    result = dummy.get_incoming_video_parameters()
    assert isinstance(result, bytes)
    assert len(result) == 8


def test_get_incoming_audio_format(dummy):
    """get_incoming_audio_format returns 2-byte audio format."""
    result = dummy.get_incoming_audio_format()
    assert isinstance(result, bytes)
    assert len(result) == 2


def test_get_incoming_audio_sample_rate(dummy):
    """get_incoming_audio_sample_rate returns sample rate as raw bytes."""
    assert dummy.get_incoming_audio_sample_rate() == bytes([0x02])


# --- Tuner preset handlers ---


def test_get_tuner_preset(dummy):
    """get_tuner_preset returns initial preset (0xFF = none)."""
    assert dummy.get_tuner_preset() == b"\xff"


def test_set_tuner_preset(dummy):
    """set_tuner_preset updates and returns new preset."""
    result = dummy.set_tuner_preset(data=bytes([0x03]))
    assert result == bytes([0x03])
    assert dummy.get_tuner_preset() == bytes([0x03])


# --- Preset detail handler ---


def test_get_preset_detail_known(dummy):
    """get_preset_detail returns preset data for known preset."""
    result = dummy.get_preset_detail(data=b"\x01")
    assert result == b"\x01\x03SR P1   "


def test_get_preset_detail_unknown(dummy):
    """get_preset_detail raises CommandInvalidAtThisTime for unknown preset."""
    with pytest.raises(CommandInvalidAtThisTime):
        dummy.get_preset_detail(data=b"\x50")
