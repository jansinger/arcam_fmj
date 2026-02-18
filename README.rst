********************************
Arcam IP Control
********************************
This module supports controlling an Arcam FMJ receiver (as well as JBL and AudioControl processors) over the network.
It's built mainly for use with the Home Assistant project, but should work for other projects as well.

Status
______
.. image:: https://github.com/elupus/arcam_fmj/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/elupus/arcam_fmj/actions

Supported Devices
=================

.. list-table::
   :header-rows: 1
   :widths: 20 40 20

   * - Series
     - Models
     - Zone 2
   * - 450 Series
     - AVR380, AVR450, AVR750
     - Yes
   * - 860 Series
     - AV860, AVR850, AVR550, AVR390, SR250, RV-6, RV-9, MC-10
     - Yes
   * - HDA Series
     - AVR5, AVR10, AVR20, AVR30, AV40, AVR11, AVR21, AVR31, AV41, SDP-55, SDP-58
     - AVR20/30/AV40, AVR21/31/AV41, SDP-55/58
   * - SA Series
     - SA10, SA20, SA30, SA750
     - No
   * - PA Series
     - PA720, PA240, PA410
     - No
   * - ST Series
     - ST60
     - No

Protocol Overview
=================

Communication is over TCP on port **50000**. All packets use a binary format:

**Command packet** (host → device)::

    [0x21] [Zone] [CC] [DL] [Data...] [0x0D]

**Response packet** (device → host)::

    [0x21] [Zone] [CC] [AC] [DL] [Data...] [0x0D]

Where:

- ``0x21`` = Start byte (``!``)
- ``Zone`` = Zone number (1 or 2)
- ``CC`` = Command Code
- ``AC`` = Answer Code (0x00 = Status Update)
- ``DL`` = Data Length
- ``0x0D`` = End byte (``\r``)

To **query** the current value of a command, send ``data = [0xF0]``.

Module
======

Basic Usage
-----------

.. code-block:: python

    import asyncio
    from arcam.fmj import SourceCodes
    from arcam.fmj.client import Client, ClientContext
    from arcam.fmj.state import State

    async def run():
        host = '192.168.0.2'
        port = 50000
        zone = 1

        client = Client(host, port)
        async with ClientContext(client):
            state = State(client, zone)
            await state.start()

            await state.set_power(True)
            await state.update()

            print(f"Power: {state.get_power()}")
            print(f"Volume: {state.get_volume()}")
            print(f"Source: {state.get_source()}")
            print(f"Mute: {state.get_mute()}")

            await state.set_volume(50)
            await state.set_source(SourceCodes.PVR)

            await state.stop()

    asyncio.run(run())

Audio Controls
--------------

.. code-block:: python

    # Bass/Treble: 0x00 (0dB) to 0x0C (+12dB), 0x81 (-1dB) to 0x8C (-12dB)
    await state.set_bass(0x00)        # flat (0dB)
    await state.set_treble(0x02)      # +2dB

    # Balance: 0x00 (full left) to 0x0C (full right), center = 0x06
    await state.set_balance(0x06)     # center

    # Subwoofer Trim: 0x00 (-12dB) to 0x0C (+0dB)
    await state.set_subwoofer_trim(0x06)

    # Lipsync Delay: 0x00-0xFA (0-250ms in 1ms steps)
    await state.set_lipsync_delay(50)

    # Display Brightness: 0x00 (off) to 0x02 (full)
    await state.set_display_brightness(0x01)

    # Room EQ: 0=off, 1=EQ1, 2=EQ2, 3=EQ3, 4=not calculated
    await state.set_room_eq(1)

    # Compression: 0x00 (off), 0x01 (medium), 0x02 (high)
    await state.set_compression(0x01)

Dolby Audio (HDA Series)
------------------------

.. code-block:: python

    from arcam.fmj import DolbyAudioMode

    mode = state.get_dolby_audio()  # DolbyAudioMode | None
    await state.set_dolby_audio(DolbyAudioMode.MOVIE)

    # Available modes:
    # DolbyAudioMode.OFF   = 0x00
    # DolbyAudioMode.MOVIE = 0x01
    # DolbyAudioMode.MUSIC = 0x02
    # DolbyAudioMode.NIGHT = 0x03

Network Playback (HDA Series)
------------------------------

.. code-block:: python

    from arcam.fmj import NetworkPlaybackStatus

    status = state.get_network_playback_status()
    # NetworkPlaybackStatus.STOPPED        = 0x00
    # NetworkPlaybackStatus.TRANSITIONING  = 0x01
    # NetworkPlaybackStatus.PLAYING        = 0x02
    # NetworkPlaybackStatus.PAUSED         = 0x03

Now Playing Info (HDA Series)
------------------------------

.. code-block:: python

    info = state.get_now_playing_info()
    if info:
        print(f"Title: {info.title}")
        print(f"Artist: {info.artist}")
        print(f"Album: {info.album}")
        print(f"Application: {info.application}")
        print(f"Sample Rate: {info.sample_rate}")
        print(f"Encoder: {info.encoder}")

    # Sample rates: KHZ_32, KHZ_44_1, KHZ_48, KHZ_88_2, KHZ_96,
    #               KHZ_176_4, KHZ_192, UNKNOWN, UNDETECTED
    # Encoders: MP3, WAV, WMA, FLAC, ALAC, MQA, UNKNOWN

HDMI Settings (HDA Series)
----------------------------

.. code-block:: python

    settings = state.get_hdmi_settings()
    if settings:
        print(f"Zone1 OSD: {settings.zone1_osd}")
        print(f"Zone1 Output: {settings.zone1_output}")
        print(f"Zone1 Lipsync: {settings.zone1_lipsync}ms")
        print(f"Audio to TV: {settings.hdmi_audio_to_tv}")
        print(f"Bypass IP: {settings.hdmi_bypass_ip}")
        print(f"CEC Control: {settings.cec_control}")
        print(f"ARC Control: {settings.arc_control}")

Zone Settings (HDA Multi-Zone)
-------------------------------

.. code-block:: python

    zone_settings = state.get_zone_settings()
    if zone_settings:
        print(f"Zone2 Input: {zone_settings.zone2_input}")
        print(f"Zone2 Status: {zone_settings.zone2_status}")
        print(f"Zone2 Volume: {zone_settings.zone2_volume}")
        print(f"Zone2 Fixed Volume: {zone_settings.zone2_fixed_volume}")

Room EQ Names (HDA Series)
----------------------------

.. code-block:: python

    names = state.get_room_eq_names()
    if names:
        print(f"EQ1: {names.eq1}")
        print(f"EQ2: {names.eq2}")
        print(f"EQ3: {names.eq3}")

Bluetooth Status (HDA Series)
-------------------------------

.. code-block:: python

    from arcam.fmj import BluetoothStatus

    result = state.get_bluetooth_status()
    if result:
        status, track_name = result
        print(f"Status: {status}")
        print(f"Track: {track_name}")

    # BluetoothStatus.NO_CONNECTION     = 0x00
    # BluetoothStatus.CONNECTED_PAUSED  = 0x01
    # BluetoothStatus.PLAYING_SBC       = 0x02
    # BluetoothStatus.PLAYING_AAC       = 0x03
    # BluetoothStatus.PLAYING_APTX      = 0x04
    # BluetoothStatus.PLAYING_APTX_HD   = 0x05

Safety Limits (SA30/SA750)
---------------------------

.. code-block:: python

    # These are read-only via State, configurable via direct client.request()
    # MAXIMUM_TURN_ON_VOLUME (0x65)
    # MAXIMUM_VOLUME (0x66)
    # MAXIMUM_STREAMING_VOLUME (0x67)

Implemented Commands Reference
===============================

.. list-table::
   :header-rows: 1
   :widths: 8 28 8 20 18 18

   * - Code
     - Name
     - Zone
     - Series
     - State Getter
     - State Setter
   * - 0x00
     - POWER
     - 1,2
     - All
     - ``get_power()``
     - ``set_power()``
   * - 0x01
     - DISPLAY_BRIGHTNESS
     - 1
     - All
     - ``get_display_brightness()``
     - ``set_display_brightness()``
   * - 0x08
     - SIMULATE_RC5_IR_COMMAND
     - 1,2
     - All
     - \-
     - (internal)
   * - 0x0D
     - VOLUME
     - 1,2
     - All
     - ``get_volume()``
     - ``set_volume()``
   * - 0x0E
     - MUTE
     - 1,2
     - All
     - ``get_mute()``
     - ``set_mute()``
   * - 0x0F
     - DIRECT_MODE_STATUS
     - 1
     - All
     - \-
     - \-
   * - 0x10
     - DECODE_MODE_STATUS_2CH
     - 1
     - All
     - ``get_decode_mode_2ch()``
     - ``set_decode_mode_2ch()``
   * - 0x11
     - DECODE_MODE_STATUS_MCH
     - 1
     - All
     - ``get_decode_mode_mch()``
     - ``set_decode_mode_mch()``
   * - 0x12
     - RDS_INFORMATION
     - 1,2
     - All
     - ``get_rds_information()``
     - \-
   * - 0x14
     - MENU
     - 1
     - All
     - ``get_menu()``
     - \-
   * - 0x15
     - TUNER_PRESET
     - 1,2
     - All
     - ``get_tuner_preset()``
     - ``set_tuner_preset()``
   * - 0x18
     - DAB_STATION
     - 1,2
     - DAB
     - ``get_dab_station()``
     - \-
   * - 0x1A
     - DLS_PDT_INFO
     - 1,2
     - All
     - ``get_dls_pdt()``
     - \-
   * - 0x1B
     - PRESET_DETAIL
     - 1,2
     - All
     - ``get_preset_details()``
     - \-
   * - 0x1C
     - NETWORK_PLAYBACK_STATUS
     - 1
     - HDA
     - ``get_network_playback_status()``
     - \-
   * - 0x1D
     - CURRENT_SOURCE
     - 1,2
     - All
     - ``get_source()``
     - ``set_source()``
   * - 0x34
     - ROOM_EQ_NAMES
     - 1
     - HDA
     - ``get_room_eq_names()``
     - \-
   * - 0x35
     - TREBLE_EQUALIZATION
     - 1,2
     - All
     - ``get_treble()``
     - ``set_treble()``
   * - 0x36
     - BASS_EQUALIZATION
     - 1,2
     - All
     - ``get_bass()``
     - ``set_bass()``
   * - 0x37
     - ROOM_EQUALIZATION
     - 1,2
     - All
     - ``get_room_eq()``
     - ``set_room_eq()``
   * - 0x38
     - DOLBY_VOLUME / DOLBY_AUDIO
     - 1,2
     - All / HDA
     - ``get_dolby_audio()``
     - ``set_dolby_audio()``
   * - 0x3B
     - BALANCE
     - 1,2
     - All
     - ``get_balance()``
     - ``set_balance()``
   * - 0x3F
     - SUBWOOFER_TRIM
     - 1,2
     - All
     - ``get_subwoofer_trim()``
     - ``set_subwoofer_trim()``
   * - 0x40
     - LIPSYNC_DELAY
     - 1,2
     - All
     - ``get_lipsync_delay()``
     - ``set_lipsync_delay()``
   * - 0x41
     - COMPRESSION
     - 1,2
     - All
     - ``get_compression()``
     - ``set_compression()``
   * - 0x42
     - INCOMING_VIDEO_PARAMETERS
     - 1
     - All
     - ``get_incoming_video_parameters()``
     - \-
   * - 0x43
     - INCOMING_AUDIO_FORMAT
     - 1
     - All
     - ``get_incoming_audio_format()``
     - \-
   * - 0x44
     - INCOMING_AUDIO_SAMPLE_RATE
     - 1
     - All
     - ``get_incoming_audio_sample_rate()``
     - \-
   * - 0x50
     - BLUETOOTH_STATUS
     - 1
     - HDA
     - ``get_bluetooth_status()``
     - \-
   * - 0x2E
     - HDMI_SETTINGS
     - 1
     - HDA
     - ``get_hdmi_settings()``
     - \-
   * - 0x2F
     - ZONE_SETTINGS
     - 1
     - HDA Multi-Zone
     - ``get_zone_settings()``
     - \-
   * - 0x64
     - NOW_PLAYING_INFO
     - 1,2
     - HDA
     - ``get_now_playing_info()``
     - \-

Unimplemented Commands Reference
==================================

The following commands are defined in the protocol specification (SH289E Rev F)
but do not have dedicated State getter/setter methods. They can be accessed
directly via ``client.request(zone, CommandCodes.XXX, data)``.

.. list-table::
   :header-rows: 1
   :widths: 8 30 62

   * - Code
     - Name
     - Description
   * - 0x02
     - HEADPHONES
     - Headphone connection status (0x00=off, 0x01=on)
   * - 0x03
     - FMGENRE
     - FM genre/PTY code
   * - 0x04
     - SOFTWARE_VERSION
     - Firmware version string
   * - 0x05
     - RESTORE_FACTORY_DEFAULT
     - Restore factory defaults
   * - 0x06
     - SAVE_RESTORE_COPY_OF_SETTINGS
     - Save/restore settings to flash
   * - 0x09
     - DISPLAY_INFORMATION_TYPE
     - Display info type shown on front panel
   * - 0x0A
     - VIDEO_SELECTION
     - Video source selection
   * - 0x0B
     - SELECT_ANALOG_DIGITAL
     - Select analog/digital input mode
   * - 0x0C
     - VIDEO_INPUT_TYPE
     - Video input type / IMAX Enhanced (860/HDA)
   * - 0x13
     - VIDEO_OUTPUT_RESOLUTION
     - Video output resolution setting
   * - 0x16
     - TUNE
     - Tune to specific frequency
   * - 0x19
     - DAB_PROGRAM_TYPE_CATEGORY
     - DAB program type/category filter
   * - 0x1F
     - HEADPHONES_OVERRIDE
     - Headphones output override
   * - 0x20
     - INPUT_NAME
     - Custom input name (up to 8 chars)
   * - 0x23
     - FM_SCAN
     - Scan FM band
   * - 0x24
     - DAB_SCAN
     - Scan DAB band
   * - 0x25
     - HEARTBEAT
     - Connection keepalive
   * - 0x26
     - REBOOT
     - Reboot the device
   * - 0x27
     - SETUP
     - Setup menu structure (HDA). Multi-page response with setup tree data.
   * - 0x28
     - INPUT_CONFIG
     - Input configuration (HDA). Per-input settings: name, default source,
       skip, max volume.
   * - 0x29
     - GENERAL_SETUP
     - General setup (HDA). System-wide settings: auto-standby timeout,
       power on volume, network standby.
   * - 0x2A
     - SPEAKER_TYPES
     - Speaker type configuration (HDA). Per-speaker: size (Large/Small/Off),
       crossover frequency.
   * - 0x2B
     - SPEAKER_DISTANCES
     - Speaker distance configuration (HDA). Per-speaker distance in cm/ft
       for time alignment.
   * - 0x2C
     - SPEAKER_LEVELS
     - Speaker level trim (HDA). Per-speaker level adjustment in 0.5dB steps.
   * - 0x2D
     - VIDEO_INPUTS
     - Video input configuration (HDA). Per-input video source assignment.
   * - 0x30
     - NETWORK_MENU_INFO
     - Network menu browsing (HDA). Multi-level menu for UPnP/DLNA,
       internet radio, streaming services.
   * - 0x32
     - BLUETOOTH_MENU_INFO
     - Bluetooth menu info (HDA). Pairing, device list, connection management.
   * - 0x33
     - ENGINEERING_MENU_INFO
     - Engineering/diagnostic menu (HDA). Internal diagnostics, firmware info.
   * - 0x39
     - DOLBY_LEVELER
     - **Removed** in protocol Rev C.0 (no longer used)
   * - 0x3A
     - DOLBY_VOLUME_CALIBRATION_OFFSET
     - **Removed** in protocol Rev C.0 (no longer used)
   * - 0x3C
     - DOLBY_PLII_X_MUSIC_DIMENSION
     - Dolby PLII/X Music dimension setting
   * - 0x3D
     - DOLBY_PLII_X_MUSIC_CENTRE_WIDTH
     - Dolby PLII/X Music centre width setting
   * - 0x3E
     - DOLBY_PLII_X_MUSIC_PANORAMA
     - Dolby PLII/X Music panorama setting
   * - 0x45
     - SUB_STEREO_TRIM
     - Sub/stereo trim level
   * - 0x46
     - VIDEO_BRIGHTNESS
     - Video output brightness
   * - 0x47
     - VIDEO_CONTRAST
     - Video output contrast
   * - 0x48
     - VIDEO_COLOUR
     - Video output colour/saturation
   * - 0x49
     - VIDEO_FILM_MODE
     - Video film mode (cadence detection)
   * - 0x4A
     - VIDEO_EDGE_ENHANCEMENT
     - Video edge enhancement level
   * - 0x4C
     - VIDEO_NOISE_REDUCTION
     - Video noise reduction level
   * - 0x4D
     - VIDEO_MPEG_NOISE_REDUCTION
     - Video MPEG artifact noise reduction
   * - 0x4E
     - ZONE_1_OSD_ON_OFF
     - Zone 1 OSD on/off
   * - 0x4F
     - VIDEO_OUTPUT_SWITCHING
     - Video output switching mode

Amp Diagnostics Commands (SA/PA Series)
----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 8 30 62

   * - Code
     - Name
     - Description
   * - 0x51
     - DC_OFFSET
     - DC offset measurement per channel
   * - 0x52
     - SHORT_CIRCUIT_STATUS
     - Short circuit detection status (Class G only)
   * - 0x53
     - FRIENDLY_NAME
     - Device friendly name for network discovery
   * - 0x54
     - IP_ADDRESS
     - Device IP address
   * - 0x55
     - TIMEOUT_COUNTER
     - Protection timeout counter
   * - 0x56
     - LIFTER_TEMPERATURE
     - Lifter/heatsink temperature (Class G only)
   * - 0x57
     - OUTPUT_TEMPERATURE
     - Output stage temperature
   * - 0x58
     - AUTO_SHUTDOWN_CONTROL
     - Auto shutdown timer control
   * - 0x59
     - PHONO_INPUT_TYPE
     - Phono input type: MM or MC (SA30/SA750)
   * - 0x5A
     - INPUT_DETECT
     - Input signal detection status
   * - 0x5B
     - PROCESSOR_MODE_INPUT
     - Processor mode input (SA Series)
   * - 0x5C
     - PROCESSOR_MODE_VOLUME
     - Processor mode volume (SA Series)
   * - 0x5D
     - SYSTEM_STATUS
     - System health/status
   * - 0x5E
     - SYSTEM_MODEL
     - System model identification
   * - 0x61
     - DAC_FILTER
     - DAC filter selection (SA Series)
   * - 0x65
     - MAXIMUM_TURN_ON_VOLUME
     - Maximum turn-on volume (SA30/SA750)
   * - 0x66
     - MAXIMUM_VOLUME
     - Maximum volume limit (SA30/SA750)
   * - 0x67
     - MAXIMUM_STREAMING_VOLUME
     - Maximum streaming volume limit (SA30/SA750)

Console
=======

The module contains a commandline utility to test and request data from
called ``arcam-fmj``.

Code to set volume and source using console.

.. code-block:: bash

    arcam-fmj state --host 192.168.0.2 --port 50000 --source PVR --volume 50

Changelog
=========

2.4.0
-----
- Priority queue for command polling (power/source first, info commands last)
- Request deduplication to avoid redundant queries
- Polling optimization: skip commands when device is in standby

2.3.0
-----
- **Architecture:** Split ``__init__.py`` into submodules (``enums.py``, ``packets.py``,
  ``dataclasses.py``, ``exceptions.py``, ``discovery.py``); backwards-compatible re-exports
- **New state commands:** ``get_imax_enhanced()``/``set_imax_enhanced()``,
  ``get_sub_stereo_trim()``/``set_sub_stereo_trim()``, ``get_headphones()``,
  ``get_software_version()``, ``get_incoming_audio_sample_rate()``,
  ``get_incoming_audio_format()``, ``get_incoming_video_parameters()``,
  ``get_input_name()``, ``get_dab_station()``, ``get_dls_pdt()``,
  ``get_preset_details()``, ``get_menu()``
- **Protocol reference:** Added ``docs/protocol-reference.md`` (SH289E Rev F)
- **Display:** Rich-powered live state display (``arcam-fmj state`` with ``rich``)
- Sequential state polling with standby awareness
- Fixed compression range validation (0–2, not 0–3)
- Fixed multichannel PCM detection in ``get_2ch()``
- Renamed MCH 0x03 to ``DTS_NEURAL_X``
- Decode mode get/set fallback on query error
- Test coverage improved from 82% to 93%

2.2.0
-----
- **New HDA State methods:** ``get_network_playback_status()``, ``get_dolby_audio()``/``set_dolby_audio()``,
  ``get_now_playing_info()``, ``get_hdmi_settings()``, ``get_zone_settings()``,
  ``get_room_eq_names()``, ``get_bluetooth_status()``
- **New enums:** ``NetworkPlaybackStatus``, ``DolbyAudioMode``, ``NowPlayingSampleRate``,
  ``NowPlayingEncoder``, ``BluetoothStatus``
- **New data classes:** ``NowPlayingInfo``, ``HdmiSettings``, ``ZoneSettings``, ``RoomEqNames``
- **Breaking change:** ``get_room_eq()`` now returns ``int`` (0=off, 1-3=EQ preset, 4=not calculated) instead of ``bool``.
  ``set_room_eq()`` now takes ``int`` instead of ``bool``.
- ``update()`` now polls HDA-specific commands (network playback, Dolby audio, HDMI settings,
  zone settings, room EQ names, Bluetooth status, now playing info)

2.1.0
-----
- Fixed ``APIVERSION_DAB_SERIES`` string iteration bug
- Fixed ``SA_SOURCE_MAPPING`` duplicate byte value for NET/USB
- Fixed ``PresetDetail`` zero-padding for frequency formatting
- Renamed ``respons_to`` → ``responds_to`` (typo fix, backwards compatible)
- Upgraded ``pytest-asyncio`` to 1.3.0
- Added get/set methods for bass, treble, balance, sub trim, lipsync,
  display brightness, room EQ, compression
