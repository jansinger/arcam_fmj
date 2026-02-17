"""Tests for console.py: argument parsing, helpers, and CLI dispatch."""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arcam.fmj import SourceCodes
from arcam.fmj.console import auto_int, auto_source, main, parser

# --- Helper functions ---


def test_auto_int_decimal():
    assert auto_int("42") == 42


def test_auto_int_hex():
    assert auto_int("0x2A") == 42


def test_auto_int_octal():
    assert auto_int("0o52") == 42


def test_auto_source_valid():
    assert auto_source("CD") == SourceCodes.CD


def test_auto_source_invalid():
    with pytest.raises(KeyError):
        auto_source("NONEXISTENT")


# --- Argument parsing ---


def test_parse_state_minimal():
    args = parser.parse_args(["state", "--host", "192.168.1.1"])
    assert args.subcommand == "state"
    assert args.host == "192.168.1.1"
    assert args.port == 50000
    assert args.zone == 1
    assert args.volume is None
    assert args.source is None
    assert args.monitor is False
    assert args.power_on is None
    assert args.power_off is None


def test_parse_state_full():
    args = parser.parse_args(
        [
            "state",
            "--host",
            "10.0.0.1",
            "--port",
            "12345",
            "--zone",
            "2",
            "--volume",
            "50",
            "--source",
            "CD",
            "--monitor",
            "--power-on",
        ]
    )
    assert args.port == 12345
    assert args.zone == 2
    assert args.volume == 50
    assert args.source == SourceCodes.CD
    assert args.monitor is True
    assert args.power_on is True


def test_parse_state_no_power_on():
    """--no-power-on sets power_on to False (not None)."""
    args = parser.parse_args(["state", "--host", "h", "--no-power-on"])
    assert args.power_on is False


def test_parse_client_minimal():
    args = parser.parse_args(["client", "--host", "h", "--command", "0x01"])
    assert args.subcommand == "client"
    assert args.command == 1
    assert args.data == [0xF0]


def test_parse_client_with_data():
    args = parser.parse_args(["client", "--host", "h", "--command", "1", "--data", "0x01", "0x02"])
    assert args.data == [1, 2]


def test_parse_server_defaults():
    args = parser.parse_args(["server"])
    assert args.subcommand == "server"
    assert args.host == "localhost"
    assert args.port == 50000
    assert args.model == "AVR450"


# --- main() dispatch ---


@patch("arcam.fmj.console.asyncio.run")
def test_main_dispatches_client(mock_run):
    with patch.object(
        parser, "parse_args", return_value=argparse.Namespace(subcommand="client", verbose=False)
    ):
        main()
    mock_run.assert_called_once()


@patch("arcam.fmj.console.asyncio.run")
def test_main_dispatches_state(mock_run):
    with patch.object(
        parser, "parse_args", return_value=argparse.Namespace(subcommand="state", verbose=False)
    ):
        main()
    mock_run.assert_called_once()


@patch("arcam.fmj.console.asyncio.run")
def test_main_dispatches_server(mock_run):
    with patch.object(
        parser, "parse_args", return_value=argparse.Namespace(subcommand="server", verbose=False)
    ):
        main()
    mock_run.assert_called_once()


@patch("arcam.fmj.console.asyncio.run")
def test_main_verbose_sets_logging(mock_run):
    with patch.object(
        parser, "parse_args", return_value=argparse.Namespace(subcommand="client", verbose=True)
    ):
        main()


def test_main_no_subcommand():
    """No subcommand → no asyncio.run called."""
    with (
        patch("arcam.fmj.console.asyncio.run") as mock_run,
        patch.object(
            parser,
            "parse_args",
            return_value=argparse.Namespace(subcommand=None, verbose=False),
        ),
    ):
        main()
    mock_run.assert_not_called()


# --- run_state ---


async def test_run_state_basic():
    """run_state() calls update() and print_state()."""
    args = argparse.Namespace(
        host="h",
        port=50000,
        zone=1,
        volume=None,
        source=None,
        power_on=None,
        power_off=None,
        monitor=False,
    )
    mock_client = MagicMock()
    mock_state = MagicMock()
    mock_state.update = AsyncMock()
    mock_state.set_volume = AsyncMock()
    mock_state.set_source = AsyncMock()
    mock_state.set_power = AsyncMock()

    with (
        patch("arcam.fmj.console.Client", return_value=mock_client),
        patch("arcam.fmj.console.ClientContext") as mock_ctx,
        patch("arcam.fmj.console.State", return_value=mock_state),
        patch("arcam.fmj.console.print_state") as mock_print,
    ):
        mock_ctx.return_value.__aenter__ = AsyncMock()
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from arcam.fmj.console import run_state

        await run_state(args)

    mock_state.update.assert_awaited_once()
    mock_print.assert_called_once_with(mock_state)
    mock_state.set_volume.assert_not_awaited()
    mock_state.set_source.assert_not_awaited()
    mock_state.set_power.assert_not_awaited()


async def test_run_state_with_volume_and_source():
    """run_state() applies volume and source when set."""
    args = argparse.Namespace(
        host="h",
        port=50000,
        zone=1,
        volume=42,
        source=SourceCodes.CD,
        power_on=None,
        power_off=None,
        monitor=False,
    )
    mock_client = MagicMock()
    mock_state = MagicMock()
    mock_state.update = AsyncMock()
    mock_state.set_volume = AsyncMock()
    mock_state.set_source = AsyncMock()
    mock_state.set_power = AsyncMock()

    with (
        patch("arcam.fmj.console.Client", return_value=mock_client),
        patch("arcam.fmj.console.ClientContext") as mock_ctx,
        patch("arcam.fmj.console.State", return_value=mock_state),
        patch("arcam.fmj.console.print_state"),
    ):
        mock_ctx.return_value.__aenter__ = AsyncMock()
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from arcam.fmj.console import run_state

        await run_state(args)

    mock_state.set_volume.assert_awaited_once_with(42)
    mock_state.set_source.assert_awaited_once_with(SourceCodes.CD)


async def test_run_state_power_on():
    """run_state() calls set_power(True) when power_on is True."""
    args = argparse.Namespace(
        host="h",
        port=50000,
        zone=1,
        volume=None,
        source=None,
        power_on=True,
        power_off=None,
        monitor=False,
    )
    mock_client = MagicMock()
    mock_state = MagicMock()
    mock_state.update = AsyncMock()
    mock_state.set_volume = AsyncMock()
    mock_state.set_source = AsyncMock()
    mock_state.set_power = AsyncMock()

    with (
        patch("arcam.fmj.console.Client", return_value=mock_client),
        patch("arcam.fmj.console.ClientContext") as mock_ctx,
        patch("arcam.fmj.console.State", return_value=mock_state),
        patch("arcam.fmj.console.print_state"),
    ):
        mock_ctx.return_value.__aenter__ = AsyncMock()
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from arcam.fmj.console import run_state

        await run_state(args)

    mock_state.set_power.assert_awaited_once_with(True)


async def test_run_state_no_power_on_flag():
    """run_state() does NOT call set_power when --no-power-on (power_on=False)."""
    args = argparse.Namespace(
        host="h",
        port=50000,
        zone=1,
        volume=None,
        source=None,
        power_on=False,
        power_off=None,
        monitor=False,
    )
    mock_client = MagicMock()
    mock_state = MagicMock()
    mock_state.update = AsyncMock()
    mock_state.set_volume = AsyncMock()
    mock_state.set_source = AsyncMock()
    mock_state.set_power = AsyncMock()

    with (
        patch("arcam.fmj.console.Client", return_value=mock_client),
        patch("arcam.fmj.console.ClientContext") as mock_ctx,
        patch("arcam.fmj.console.State", return_value=mock_state),
        patch("arcam.fmj.console.print_state"),
    ):
        mock_ctx.return_value.__aenter__ = AsyncMock()
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        from arcam.fmj.console import run_state

        await run_state(args)

    mock_state.set_power.assert_not_awaited()
