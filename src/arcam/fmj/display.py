"""Human-friendly state display using rich tables.

Requires the optional ``cli`` dependency group: ``pip install arcam-fmj[cli]``
Falls back to ``repr()`` if rich is not installed.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import State

NONE = "\u2014"  # em-dash for missing values


def _fmt(value: object) -> str:
    """Format a single value for display."""
    if value is None:
        return NONE
    if isinstance(value, bool):
        return "On" if value else "Off"
    if isinstance(value, IntEnum):
        return value.name.replace("_", " ").title()
    return str(value)


def _section(
    table,
    title: str,
    rows: list[tuple[str, object]],
) -> None:
    """Add a titled section to *table*, skipping it if all values are None."""
    if all(v is None for _, v in rows):
        return
    table.add_row(f"[bold cyan]{title}[/bold cyan]", "", end_section=True)
    for label, value in rows:
        table.add_row(f"  {label}", _fmt(value))


def print_state(state: State) -> None:
    """Print *state* as a grouped rich table.

    Falls back to ``print(repr(state))`` when rich is not installed.
    """
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print(repr(state))
        return

    console = Console()
    model = state.model or "Unknown"
    revision = state.revision or ""
    header = f"{model} {revision}".strip()

    table = Table(
        title=f"[bold]{header}[/bold]  \u2014  Zone {state.zn}",
        show_header=False,
        padding=(0, 2),
        expand=False,
    )
    table.add_column("Property", style="white", min_width=24)
    table.add_column("Value", style="bright_white")

    # --- General -----------------------------------------------------------
    _section(table, "General", [
        ("Power", state.get_power()),
        ("Source", state.get_source()),
        ("Volume", state.get_volume()),
        ("Mute", state.get_mute()),
        ("Menu", state.get_menu()),
    ])

    # --- Audio Input -------------------------------------------------------
    audio_fmt, audio_cfg = state.get_incoming_audio_format()
    _section(table, "Audio Input", [
        ("Format", audio_fmt),
        ("Channel Config", audio_cfg),
        ("Sample Rate", (
            f"{state.get_incoming_audio_sample_rate() / 1000:.1f} kHz"
            if state.get_incoming_audio_sample_rate() is not None
            else None
        )),
    ])

    # --- Audio Processing --------------------------------------------------
    _section(table, "Audio Processing", [
        ("Decode Mode 2CH", state.get_decode_mode_2ch()),
        ("Decode Mode MCH", state.get_decode_mode_mch()),
        ("Dolby Audio", state.get_dolby_audio()),
        ("Compression", state.get_compression()),
    ])

    # --- Audio Controls ----------------------------------------------------
    _section(table, "Audio Controls", [
        ("Bass", state.get_bass()),
        ("Treble", state.get_treble()),
        ("Balance", state.get_balance()),
        ("Subwoofer Trim", state.get_subwoofer_trim()),
        ("Lip-Sync Delay", (
            f"{state.get_lipsync_delay()} ms"
            if state.get_lipsync_delay() is not None
            else None
        )),
    ])

    # --- Video Input -------------------------------------------------------
    vp = state.get_incoming_video_parameters()
    if vp is not None:
        scan = "i" if vp.interlaced else "p"
        _section(table, "Video Input", [
            ("Resolution", f"{vp.horizontal_resolution}x{vp.vertical_resolution}{scan}"),
            ("Refresh Rate", f"{vp.refresh_rate} Hz"),
            ("Aspect Ratio", vp.aspect_ratio),
            ("Colorspace", vp.colorspace),
        ])

    # --- Tuner -------------------------------------------------------------
    _section(table, "Tuner", [
        ("DAB Station", state.get_dab_station()),
        ("DLS / PDT", state.get_dls_pdt()),
        ("RDS", state.get_rds_information()),
        ("Preset", state.get_tuner_preset()),
    ])

    # --- Now Playing -------------------------------------------------------
    np = state.get_now_playing_info()
    if np is not None:
        _section(table, "Now Playing", [
            ("Title", np.title or None),
            ("Artist", np.artist or None),
            ("Album", np.album or None),
            ("Application", np.application or None),
            ("Sample Rate", np.sample_rate),
            ("Encoder", np.encoder),
        ])

    # --- Network / Bluetooth -----------------------------------------------
    bt = state.get_bluetooth_status()
    bt_status = bt[0] if bt else None
    bt_track = bt[1] if bt and bt[1] else None
    _section(table, "Network / Bluetooth", [
        ("Playback Status", state.get_network_playback_status()),
        ("Bluetooth", bt_status),
        ("Bluetooth Track", bt_track),
    ])

    # --- Display & Room EQ -------------------------------------------------
    eq_names = state.get_room_eq_names()
    room_eq_rows: list[tuple[str, object]] = [
        ("Display Brightness", state.get_display_brightness()),
        ("Room EQ", state.get_room_eq()),
    ]
    if eq_names is not None:
        if eq_names.eq1:
            room_eq_rows.append(("  EQ1 Name", eq_names.eq1))
        if eq_names.eq2:
            room_eq_rows.append(("  EQ2 Name", eq_names.eq2))
        if eq_names.eq3:
            room_eq_rows.append(("  EQ3 Name", eq_names.eq3))
    _section(table, "Display & Room EQ", room_eq_rows)

    # --- HDMI Settings -----------------------------------------------------
    hdmi = state.get_hdmi_settings()
    if hdmi is not None:
        _section(table, "HDMI Settings", [
            ("Zone 1 OSD", hdmi.zone1_osd),
            ("Zone 1 Output", hdmi.zone1_output),
            ("Zone 1 Lip-Sync", f"{hdmi.zone1_lipsync} ms"),
            ("Audio to TV", hdmi.hdmi_audio_to_tv),
            ("Bypass IP", hdmi.hdmi_bypass_ip),
            ("Bypass Source", hdmi.hdmi_bypass_source),
            ("CEC Control", hdmi.cec_control),
            ("ARC Control", hdmi.arc_control),
            ("TV Audio", hdmi.tv_audio),
            ("Power-Off Control", hdmi.power_off_control),
        ])

    # --- Zone Settings -----------------------------------------------------
    zs = state.get_zone_settings()
    if zs is not None:
        _section(table, "Zone Settings", [
            ("Zone 2 Input", zs.zone2_input),
            ("Zone 2 Status", zs.zone2_status),
            ("Zone 2 Volume", zs.zone2_volume),
            ("Zone 2 Max Volume", zs.zone2_max_volume),
            ("Zone 2 Fixed Volume", zs.zone2_fixed_volume),
            ("Zone 2 Max-On Volume", zs.zone2_max_on_volume),
        ])

    # --- Presets -----------------------------------------------------------
    presets = state.get_preset_details()
    if presets:
        table.add_row(
            f"[bold cyan]Presets[/bold cyan]",
            f"({len(presets)} stored)",
            end_section=True,
        )
        for idx in sorted(presets):
            p = presets[idx]
            table.add_row(f"  #{idx:2d}  {_fmt(p.type)}", p.name)

    console.print()
    console.print(table)
    console.print()
