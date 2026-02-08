"""Tests for arcam.fmj.__init__ module fixes."""

import pytest
from arcam.fmj import (
    APIVERSION_DAB_SERIES,
    APIVERSION_860_SERIES,
    APIVERSION_HDA_SERIES,
    SA_SOURCE_MAPPING,
    PresetDetail,
    PresetType,
    ResponsePacket,
    CommandPacket,
    AmxDuetResponse,
    AmxDuetRequest,
    CommandCodes,
    AnswerCodes,
    SourceCodes,
)


# --- Tests for APIVERSION_DAB_SERIES fix ---


def test_dab_series_contains_full_model_names():
    """Test that APIVERSION_DAB_SERIES contains full model name strings, not individual characters."""
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
        ), f"Duplicate byte value {byte_val!r} for {source} (already used by {[k for k, v in seen_values.items() if v == byte_val]})"
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
    name_bytes = "SR P1   ".encode("utf8")
    data = bytes([1, 0x02]) + name_bytes
    detail = PresetDetail.from_bytes(data)
    assert detail.name == "SR P1"


def test_preset_detail_dab_name():
    """Test DAB station name parsing."""
    name_bytes = "P3 Star ".encode("utf8")
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
