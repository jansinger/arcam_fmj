"""Tests for the display module (human-friendly state output)."""

from unittest.mock import patch

from arcam.fmj import (
    AmxDuetResponse,
    CommandCodes,
    DolbyAudioMode,
    NetworkPlaybackStatus,
    NowPlayingEncoder,
    NowPlayingSampleRate,
)
from arcam.fmj.display import _fmt, print_state

# --- _fmt helper ---


def test_fmt_none():
    assert _fmt(None) == "\u2014"


def test_fmt_bool_true():
    assert _fmt(True) == "On"


def test_fmt_bool_false():
    assert _fmt(False) == "Off"


def test_fmt_enum():
    assert _fmt(DolbyAudioMode.MOVIE) == "Movie"


def test_fmt_enum_multi_word():
    assert _fmt(NetworkPlaybackStatus.STOPPED) == "Stopped"


def test_fmt_int():
    assert _fmt(42) == "42"


def test_fmt_string():
    assert _fmt("BBC Radio 1") == "BBC Radio 1"


# --- print_state with populated data ---


def _populate_state(state):
    """Set up a state with representative data for all sections."""
    state._amxduet = AmxDuetResponse(values={"Device-Model": "AVR30", "Device-Revision": "1.2"})
    state._state[CommandCodes.POWER] = bytes([0x01])
    state._state[CommandCodes.VOLUME] = bytes([42])
    state._state[CommandCodes.CURRENT_SOURCE] = bytes([0x08])  # NET
    state._state[CommandCodes.MUTE] = bytes([0x01])  # unmuted
    state._state[CommandCodes.MENU] = bytes([0x00])  # NONE
    state._state[CommandCodes.INCOMING_AUDIO_FORMAT] = bytes([0x01, 0x01])
    state._state[CommandCodes.INCOMING_AUDIO_SAMPLE_RATE] = bytes([0x02])  # 48kHz
    state._state[CommandCodes.DECODE_MODE_STATUS_2CH] = bytes([0x01])  # STEREO
    state._state[CommandCodes.DECODE_MODE_STATUS_MCH] = bytes([0x02])  # MULTI_CHANNEL
    state._state[CommandCodes.DOLBY_VOLUME] = bytes([0x01])  # MOVIE
    state._state[CommandCodes.COMPRESSION] = bytes([0x01])
    state._state[CommandCodes.BASS_EQUALIZATION] = bytes([0x05])
    state._state[CommandCodes.TREBLE_EQUALIZATION] = bytes([0x03])
    state._state[CommandCodes.BALANCE] = bytes([0x80])
    state._state[CommandCodes.SUBWOOFER_TRIM] = bytes([0x0A])
    state._state[CommandCodes.LIPSYNC_DELAY] = bytes([0x28])  # 40ms
    state._state[CommandCodes.INCOMING_VIDEO_PARAMETERS] = (
        b"\x07\x80\x04\x38\x3c\x00\x02\x00"  # 1920x1080@60Hz progressive 16:9 normal
    )
    state._state[CommandCodes.DAB_STATION] = b"BBC Radio 1"
    state._state[CommandCodes.TUNER_PRESET] = bytes([0x03])
    state._state[CommandCodes.NETWORK_PLAYBACK_STATUS] = bytes([0x02])  # PLAYING
    state._state[CommandCodes.DISPLAY_BRIGHTNESS] = bytes([0x02])
    state._state[CommandCodes.ROOM_EQUALIZATION] = bytes([0x01])
    state._state[CommandCodes.ROOM_EQ_NAMES] = (
        b"Living Room\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        + b"Bedroom\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        + b"\x00" * 20
    )
    state._state[CommandCodes.HDMI_SETTINGS] = bytes(
        [
            0x01,
            0x01,
            0x28,
            0x00,
            0x00,
            0x02,
            0x01,
            0x01,
            0x00,
            0x01,
        ]
    )
    state._state[CommandCodes.ZONE_SETTINGS] = bytes(
        [
            0x03,
            0x01,
            0x30,
            0x63,
            0x00,
            0x50,
        ]
    )
    state._state[CommandCodes.VIDEO_OUTPUT_FRAME_RATE] = (
        bytes([0x04]) + b"My Song"  # PLAYING_APTX + track
    )
    state._now_playing = {
        0xF0: "Bohemian Rhapsody",
        0xF1: "Queen",
        0xF2: "A Night at the Opera",
        0xF3: "Roon",
        0xF4: NowPlayingSampleRate.KHZ_44_1,
        0xF5: NowPlayingEncoder.FLAC,
    }


async def test_print_state_populated(make_state, capsys):
    """print_state runs without error on a fully populated state."""
    state = make_state()
    _populate_state(state)
    print_state(state)
    captured = capsys.readouterr()
    assert "AVR30" in captured.out
    assert "Zone 1" in captured.out
    assert "42" in captured.out
    assert "Bohemian Rhapsody" in captured.out
    assert "Queen" in captured.out
    assert "BBC Radio 1" in captured.out


async def test_print_state_empty(make_state, capsys):
    """print_state runs without error on an empty state (all None)."""
    state = make_state()
    print_state(state)
    captured = capsys.readouterr()
    assert "Zone 1" in captured.out


async def test_print_state_sections_skipped_when_all_none(make_state, capsys):
    """Sections with all None values are not displayed."""
    state = make_state()
    # Only set power, nothing else
    state._state[CommandCodes.POWER] = bytes([0x01])
    print_state(state)
    captured = capsys.readouterr()
    assert "General" in captured.out
    # Tuner section should be skipped (all None)
    assert "Tuner" not in captured.out
    # HDMI section should be skipped (None)
    assert "HDMI Settings" not in captured.out


async def test_print_state_fallback_without_rich(make_state, capsys):
    """Falls back to repr() when rich is not installed."""
    state = make_state()
    state._state[CommandCodes.POWER] = bytes([0x01])
    with patch.dict("sys.modules", {"rich": None, "rich.console": None, "rich.table": None}):
        # Re-import to pick up the mocked modules
        import importlib

        import arcam.fmj.display as display_mod

        importlib.reload(display_mod)
        display_mod.print_state(state)
        captured = capsys.readouterr()
        assert "State" in captured.out
        # Restore
        importlib.reload(display_mod)
