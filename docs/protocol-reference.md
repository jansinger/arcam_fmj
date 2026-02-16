# Arcam RS232/NET Protocol Reference (SH289E Rev F)

Serial programming interface and IR remote commands for Arcam AVR5/AVR10/AVR20/AVR30/AV40/AVR11/AVR21/ARV31/AVR41.

Document: RS232_5_10_20_30_40_11_21_31_41__SH289E_F_07Oct21.pdf

## Applicability

**Models:** AVR5, AVR10, AVR20, AVR30, AV40, AVR11, AVR21, ARV31, AVR41

### Changelog

| Issue | Changes |
|-------|---------|
| A.0 | First draft |
| B.0 | Added C4 & DANTE to engineering menu control & correct 0x13 |
| C.0 | Removed commands 0x39/0x3A as no longer used. Auro commands 0x10, 0x11 & 0x28 updated. Dolby Centre spread removed from 0x29. Leveller & Calibration Offset removed from 0x28. Added Auro Native & Auro 2D IR commands. |
| D.0 | Added Auro channel responses to 0x43 / 0x29. Correct Bass -1 IR command. |
| E.0 | Added AVR5 |
| F.0 | Added AVR11, AVR21, ARV31, AV41 |

---

## Introduction

This document describes the remote control protocol for controlling via the RS232/NET interface. The AV implements virtual IR commands in order to simplify the protocol. Any operation that can be invoked using the IR remote control can be achieved over a control link using the Simulate RC5 IR command (0x08). See page 7 for details. The RC5 IR code set is listed from page 39.

## Set-up

The AV must be correctly configured for Control; by default, Control is disabled for minimum standby power consumption. RS232 control can be enabled using the front panel: press and hold the front panel **DIRECT** button for 4 seconds until "RS232 CONTROL ON" is displayed on the VFD. Alternatively, Control for RS232 or IP can be enabled using the OSD menu. IP control is via port 50000 of the IP address of the unit (in the Network Settings menu).

## Conventions

- All hexadecimal numbers begin 0x.
- Any character in single quotes gives the ASCII equivalent of a hex value.
- `<n>` represents an unknown or variable number.

---

## Serial Cable Specification

The cable is wired as a null modem:

| Connector 1 pin | Connector 2 pin | Function |
|------------------|------------------|----------|
| 2 | 3 | Rx <- Tx |
| 3 | 2 | Tx -> Rx |
| 5 | 5 | RS232 Ground |

### Data Transfer Format

- Transfer rate: 38,400bps
- 1 start bit, 8 data bits, 1 stop bit, no parity, no flow control

---

## Command and Response Formats

Communication between the remote controller (RC) and the AV takes the form of sequences of bytes, with all commands and responses having the same basic format. The AV shall always respond to a received command, but may also send messages at other times.

### Command Format (RC to AV)

`<St> <Zn> <Cc> <Dl> <Data> <Et>`

| Field | Description |
|-------|-------------|
| St | Start transmission: 0x21 `'!'` |
| Zn | Zone number (see below) |
| Cc | Command code |
| Dl | Data length: number of data bytes following, excluding Et |
| Data | Parameters for the command |
| Et | End transmission: 0x0D |

### Response Format (AV to RC)

`<St> <Zn> <Cc> <Ac> <Dl> <Data> <Et>`

| Field | Description |
|-------|-------------|
| St | Start transmission: 0x21 `'!'` |
| Zn | Zone number |
| Cc | Command code |
| Ac | Answer code (see below) |
| Dl | Data length: number of data bytes following, excluding Et. Max 255. |
| Data | Parameters for the response |
| Et | End transmission: 0x0D |

The AV responds to each command from the RC within three seconds. The RC may send further commands before a previous command response has been received.

### Zone Numbers

| Value | Zone |
|-------|------|
| 0x01 | Zone 1 (master zone). Commands that appear zone-less refer to the master zone. |
| 0x02 | Zone 2 |

### Answer Codes

| Code | Meaning |
|------|---------|
| 0x00 | Status update |
| 0x82 | Zone invalid |
| 0x83 | Command not recognised |
| 0x84 | Parameter not recognised |
| 0x85 | Command invalid at this time (e.g. setup menu displayed, tuner not selected) |
| 0x86 | Invalid data length |

### State Changes as a Result of Other Inputs

It is possible that the state of the AV may be changed as a result of user input via the front panel buttons or via the IR remote control. Any change resulting from these inputs is relayed to the RC using the appropriate message type.

### Reserved Commands

Commands 0xF0 to 0xFF (inclusive) are reserved for test functions and should never be used.

---

## Example Command and Response Sequence

Simulate the RC5 command "16-16" (volume up):

**Command:**

| STR | ZONE | CC | DL | Data 1 | Data 2 | ETR |
|-----|------|----|----|--------|--------|-----|
| 0x21 | 0x01 | 0x08 | 0x02 | 0x10 | 0x10 | 0x0D |

**Response:**

| STR | ZONE | CC | AC | DL | Data 1 | Data 2 | ETR |
|-----|------|----|----|-----|--------|--------|-----|
| 0x21 | 0x01 | 0x08 | 0x00 | 0x02 | 0x10 | 0x10 | 0x0D |

---

## Discovery Protocols

### AMX Duet Support

The AV is fully compatible with AMX Duet Dynamic Device Discovery Protocol (DDDP).

Data is specified in ASCII format. `"\r"` is a carriage return (0x0D).

**Command:** `AMX\r`

**Response:** `AMXB<Device-SDKClass=Receiver><Device-Make=ARCAM><Device-Model=modelname><Device-Revision=x.y.z>\r`

Where x.y.z = RS232 protocol version number.

### Control 4 SDDP Support

The AV is fully compatible with the Control 4 SDDP discovery protocol.

### Crestron Connected Support

The AV is fully compatible with the Crestron Connected discovery protocol.

---

## System Command Specifications

### Power (0x00)

Request the stand-by state of a zone.

**Command:** Cc=0x00, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request power state |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Zone is in stand-by |
| 0x01 | Zone is powered on |

**Example:** Query zone 1 power (on) -> `21 01 00 01 F0 0D` -> `21 01 00 00 01 01 0D`

---

### Display Brightness (0x01)

Request the brightness of the front panel display.

**Command:** Cc=0x01, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request brightness |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Front panel is off |
| 0x01 | Front panel L1 |
| 0x02 | Front panel L2 |

**Example:** Query brightness (off) -> `21 01 01 01 F0 0D` -> `21 01 01 00 01 00 0D`

---

### Headphones (0x02)

Determine whether headphones are connected.

**Command:** Cc=0x02, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request current headphone connection status |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Headphones are not connected |
| 0x01 | Headphones are connected |

**Example:** Query headphones (not connected) -> `21 01 02 01 F0 0D` -> `21 01 02 00 01 00 0D`

---

### FM Genre (0x03)

Request information on the current station programme type from FM source in a given zone. If FM is not selected on the given zone an error 0x85 is returned.

**Command:** Cc=0x03, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | FM program type |

**Response:** Dl=`<n>`

| Data | Description |
|------|-------------|
| Data1..Data`<n>` | The radio programme type in ASCII characters |

**Example:** Query zone 1 FM genre ("POP MUSIC") -> `21 01 03 01 F0 0D` -> `21 01 03 00 09 50 4F 50 20 4D 55 53 49 43 0D`

---

### Software Version (0x04)

Request the version number of the various pieces of software on the AVR.

**Command:** Cc=0x04, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request RS232 version |
| 0xF1 | Request Host version |
| 0xF2 | Request OSD version |
| 0xF3 | Request DSP version |
| 0xF4 | Request NET version |
| 0xF5 | Request IAP version |

**Response:** Dl=0x03

| Data | Description |
|------|-------------|
| Data1 | Echo data from command |
| Data2 | Major version number |
| Data3 | Minor version number |

**Example:** Query RS232 version (1.4) -> `21 01 04 01 F0 0D` -> `21 01 04 00 03 F0 01 04 0D`

---

### Restore Factory Default Settings (0x05)

Force a restore of the factory default settings.

**Command:** Cc=0x05, Dl=0x02

| Data | Description |
|------|-------------|
| Data1 | 0xAA (confirmation pattern to avoid accidental restore) |
| Data2 | 0xAA (confirmation pattern to avoid accidental restore) |

**Response:** Dl=0x00

**Example:** Restore factory defaults -> `21 01 05 02 AA AA 0D` -> `21 01 05 00 00 0D`

---

### Save/Restore Secure Copy of Settings (0x06)

Force a save/restore of the secure copy of the settings. If no secure copy has been made, returns answer code 0x85. If the system is currently doing a save and another save is requested, the second save will fail silently. If a 0x1E command is being processed, returns answer code 0x85.

**Command:** Cc=0x06, Dl=0x07

| Data | Description |
|------|-------------|
| Data1 | 0x00 = Save secure backup, 0x01 = Restore secure backup |
| Data2 | 0x55 (confirmation pattern) |
| Data3 | 0x55 (confirmation pattern) |
| Data4 | Pin digit 1 |
| Data5 | Pin digit 2 |
| Data6 | Pin digit 3 |
| Data7 | Pin digit 4 |

**Response:** Dl=0x00

**Example:** Restore secure backup -> `21 01 06 07 01 55 55 01 02 03 04 0D` -> `21 01 06 00 00 0D`

---

### Simulate RC5 IR Command (0x08)

Simulate an RC5 command via the RS232 port. An additional status message will be sent in most cases as a result of the IR command.

**Command:** Cc=0x08, Dl=0x02

| Data | Description |
|------|-------------|
| Data1 | RC5 System code |
| Data2 | RC5 Command code |

**Response:** Dl=0x02

| Data | Description |
|------|-------------|
| Data1 | RC5 System code |
| Data2 | RC5 Command code |

**Example:** RC5 16-17 (volume down) in zone 1 -> `21 01 08 02 10 11 0D` -> `21 01 08 00 02 10 11 0D`

---

### Display Information Type (0x09)

Set the VFD display information type (where applicable). The return data echoes the data sent.

**Command:** Cc=0x09, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Set the display to Processing mode |
| 0xE0 | Cycle through all displayable information |
| 0xF0 | Request the current display type |

**If the current source is FM:**

| Data | Description |
|------|-------------|
| 0x01 | Set the display to Radio text |
| 0x02 | Set the display to Programme type |
| 0x03 | Set the display to Signal strength |

**If the current source is DAB:**

| Data | Description |
|------|-------------|
| 0x01 | Set the display to Radio text |
| 0x02 | Set the display to Genre |
| 0x03 | Set the display to Signal quality |
| 0x04 | Set the display to Bit rate |

**If the current source is NET:**

| Data | Description |
|------|-------------|
| 0x01 | Set the display to Track |
| 0x02 | Set the display to Artist |
| 0x03 | Set the display to Album |
| 0x04 | Set the display to audio type |
| 0x05 | Set the display to rate |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| Data1 | The current display is returned, as for the command |

**Example:** Set display to FM radio text in zone 2 -> `21 02 09 01 01 0D` -> `21 02 09 00 01 01 0D`

---

### Request Current Source (0x1D)

Request the source currently selected for a given zone.

**Command:** Cc=0x1D, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request current source |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Follow Zone 1 |
| 0x01 | CD |
| 0x02 | BD |
| 0x03 | AV |
| 0x04 | SAT |
| 0x05 | PVR |
| 0x06 | UHD |
| 0x08 | AUX |
| 0x09 | DISPLAY |
| 0x0B | TUNER (FM) |
| 0x0C | TUNER (DAB) |
| 0x0E | NET |
| 0x10 | STB |
| 0x11 | GAME |
| 0x12 | BT |

**Example:** Query zone 1 source (SAT) -> `21 01 1D 01 F0 0D` -> `21 01 1D 00 01 04 0D`

---

### Headphone Over-ride (0x1F)

Activate/deactivate the mute relays (does not zero the volume).

**Command:** Cc=0x1F, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Headphone/Over-ride Clear (speakers muted if headphones present) |
| 0x01 | Headphone/Over-ride Set (speakers unmuted if headphones present) |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| Data1 | Relay state |

**Example:** Activate mute relays -> `21 01 1F 01 01 0D` -> `21 01 1F 00 01 01 0D`

---

## Input Command Specifications

### Select Analogue/Digital (0x0B)

Select an analogue/digital audio input for the current source. Returns invalid (0x85) if OSD is showing setup screen.

**Command:** Cc=0x0B, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Use the analogue audio for the current source |
| 0x01 | Use the digital audio for the current source (if available) |
| 0x02 | Use HDMI for the current source (if available) |
| 0xF0 | Request the audio type in use for the current source |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Analogue audio is in use for the current source |
| 0x01 | Digital audio is in use for the current source |
| 0x02 | HDMI audio is in use for the current source |

**Example:** Set to digital in zone 1 -> `21 01 0B 01 01 0D` -> `21 01 0B 00 01 01 0D`

---

## Output Command Specifications

### Set/Request Volume (0x0D)

Set or request the volume of a zone. This command returns the volume even if the zone is muted. The "Request Mute status" command can be used to discover if the zone is muted.

Response data format: e.g. for volume 42dB: Data1=0x2A (42)

**Command:** Cc=0x0D, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x63 | Set the volume (0-99) |
| 0xF0 | Request the current volume |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| Data1 | Zone volume, integer value: 0x00 (0) - 0x63 (99) |

**Example:** Set zone 1 volume to 45dB -> `21 01 0D 01 2D 0D` -> `21 01 0D 00 01 2D 0D`

---

### Request Mute Status (0x0E)

Request the mute status of the audio in a zone.

**Command:** Cc=0x0E, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request mute status |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Zone is muted |
| 0x01 | Zone is not muted |

**Example:** Query mute status zone 1 (muted) -> `21 01 0E 01 F0 0D` -> `21 01 0E 00 01 00 0D`

---

### Request Direct Mode Status (0x0F)

Request the direct mode status on Zone 1.

**Command:** Cc=0x0F, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request mode setting |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | 'Direct mode' is off |
| 0x01 | 'Direct mode' is on |

**Example:** Query direct mode (on) -> `21 01 0F 01 F0 0D` -> `21 01 0F 00 01 01 0D`

---

### Request Decode Mode Status - 2ch (0x10)

Request the decode mode for two-channel material in zone 1.

**Command:** Cc=0x10, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request decode mode |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x01 | Stereo |
| 0x04 | Dolby Surround |
| 0x07 | Neo:6 Cinema |
| 0x08 | Neo:6 Music |
| 0x09 | 5/7 Ch Stereo |
| 0x0A | DTS Neural:X |
| 0x0B | Reserved |
| 0x0C | DTS Virtual:X |
| 0x0D | Dolby Virtual Height |
| 0x0E | Auro Native (not AVR5) |
| 0x0F | Auro-Matic 3D (not AVR5) |
| 0x10 | Auro-2D (not AVR5) |

**Example:** Query 2ch decode mode (Dolby Surround) -> `21 01 10 01 F0 0D` -> `21 01 10 00 01 04 0D`

---

### Request Decode Mode Status - MCH (0x11)

Request the decode mode for multi-channel material in zone 1.

**Command:** Cc=0x11, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request decode mode |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x01 | Stereo down-mix |
| 0x02 | Multi channel |
| 0x03 | DTS Neural:X |
| 0x06 | Dolby Surround |
| 0x0B | Reserved |
| 0x0C | DTS Virtual:X |
| 0x0D | Dolby Virtual Height |
| 0x0E | Auro Native (not AVR5) |
| 0x0F | Auro-Matic 3D (not AVR5) |
| 0x10 | Auro-2D (not AVR5) |

**Example:** Query MCH decode mode (Dolby Surround) -> `21 01 11 01 F0 0D` -> `21 01 11 00 01 06 0D`

---

### Request RDS Information (0x12)

Request RDS information from the current radio station in a given zone. If FM is not selected on the given zone an error 0x85 is returned.

**Command:** Cc=0x12, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | FM |

**Response:** Dl=`<n>`

| Data | Description |
|------|-------------|
| Data1..Data`<n>` | The radio programme type in ASCII characters |

**Example:** Query RDS info ("Playing your favourite music") -> `21 01 12 01 F0 0D` -> `21 01 12 00 1C 00 50 6C 61 79 ...0D`

---

### Request Video Output Resolution (0x13)

Request the Video Output Resolution of zone 1. Will always be bypass (command for legacy control support).

**Command:** Cc=0x13, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request the video output |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x07 | bypass |

**Example:** Query video output (bypass) -> `21 01 13 01 F0 0D` -> `21 01 13 00 01 07 0D`

---

## Menu Command Specifications

### Request Menu Status (0x14)

Request which (if any) menu is open in the unit.

**Command:** Cc=0x14, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request the open menu state |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | No menu is open |
| 0x02 | Set-up Menu Open |
| 0x03 | Trim Menu Open |
| 0x04 | Bass Menu Open |
| 0x05 | Treble Menu Open |
| 0x06 | Sync Menu Open |
| 0x07 | Sub Menu Open |
| 0x08 | Tuner Menu Open |
| 0x09 | Network menu Open |
| 0x0A | USB Menu Open |

**Example:** Query menu (Trim menu) -> `21 01 14 01 F0 0D` -> `21 01 14 00 01 03 0D`

---

### Request Tuner Preset (0x15)

Request the current tuner preset number. If the tuner is not selected on the given zone an error 0x85 is returned.

**Command:** Cc=0x15, Dl=0x01

| Data | Description |
|------|-------------|
| 0x01 - 0x32 | (1-50) Number of required preset |
| 0xF0 | Request current preset number |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0xFF | Currently no preset selected |
| 0x01 - 0x32 | (1-50) The current preset number |

**Example:** Query preset (10) -> `21 01 15 01 F0 0D` -> `21 01 15 00 01 0A 0D`

---

### Tune (0x16)

Increment/Decrement the tuner frequency in 0.05MHz steps (FM). If the tuner is not selected on the given zone an error 0x85 is returned.

The returned frequency is calculated as follows:
- FM freq. (MHz) = reported freq. (MHz)
- FM freq. (kHz) = reported freq. (kHz)

For these reasons, this command may return values that cannot be translated into ASCII characters.

**Command:** Cc=0x16, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Decrement tuner frequency by 1 step |
| 0x01 | Increment tuner frequency by 1 step |
| 0xF0 | Request the current tuner frequency |

**Response:** Dl=0x02

| Data | Description |
|------|-------------|
| Data1 | FM: New frequency (MHz) |
| Data2 | FM: New frequency (10's kHz) |

**Example:** Increment FM from 85.0MHz to 85.05MHz -> `21 01 16 01 01 0D` -> `21 01 16 00 02 55 05 0D`

---

### Request DAB Station (0x18)

Request the current DAB station selected. If DAB is not selected on the given zone, an error 0x85 is returned.

**Command:** Cc=0x18, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request the current DAB station |

**Response:** Dl = Data length, fixed to 16 bytes (ASCII characters)

| Data | Description |
|------|-------------|
| Data1-Data128 | The service label of the DAB station in ASCII characters. Padded to 16 bytes with space character (0x20). |

**Example:** Query DAB station ("DAB STATION 2") -> `21 01 18 01 F0 0D` -> `21 01 18 00 10 44 41 42 20 53 54 41 54 49 4F 4E 20 32 20 20 20 0D`

---

### Prog. Type/Category (0x19)

Request information on the current station programme type from DAB source in a given zone. If DAB is not selected on the given zone an error 0x85 is returned.

**Command:** Cc=0x19, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | DAB program type |

**Response:** Dl = Data length, fixed to 16 bytes (ASCII characters)

| Data | Description |
|------|-------------|
| Data1-Data128 | The radio programme type in ASCII characters. Padded to 16 bytes with space character (0x20). |

**Example:** Query DAB programme type ("POP MUSIC") -> `21 01 19 01 F0 0D` -> `21 01 19 00 10 50 4F 50 20 4D 55 53 49 43 20 20 20 20 20 20 20 0D`

---

### DLS/PDT Info (0x1A)

Request DLS/PDT information (digital radio text) from the current radio station in a given zone. If DAB is not selected on the given zone an error 0x85 is returned.

**Command:** Cc=0x1A, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | DAB |

**Response:** Dl = Data length, fixed to 128 bytes (ASCII characters)

| Data | Description |
|------|-------------|
| Data1-Data`<n>` | The radio programme type in ASCII characters. Padded to 128 bytes with space character (0x20). |

**Example:** Query DLS info ("Playing your favourite music") -> `21 01 1A 01 F0 0D` -> `21 01 1A 00 80 00 50 6C 61 79 ...0D`

---

### Request Preset Details (0x1B)

Request details of tuner presets.

**Command:** Cc=0x1B, Dl=0x01

| Data | Description |
|------|-------------|
| 0x01 - 0x32 | (1-50) The number of the required preset |

**Response:** Dl=`<n>`

| Data | Description |
|------|-------------|
| Data1 | 0x01-0x32: (1-50) The number of the requested preset |
| Data2 | 0x01: FM frequency, 0x02: FM RDS name, 0x03: DAB (AVR450/750 only) |
| Data3 | FM: New frequency (MHz) |
| Data4 | FM: New frequency (10's kHz) |
| Data`<n>` | The name (DAB, FM if RDS) in ASCII characters |

**Example:** Request preset 1 (DAB "DAB STATION 2") -> `21 01 1B 01 01 0D` -> `21 01 1B 00 0F 01 02 44 41 42 20 53 54 41 54 49 4F 4E 20 32 0D`

---

### Network Playback Status (0x1C)

Network message format. If the network is not selected on the given zone an error 0x85 is returned.

**Command:** Cc=0x1C, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request Network playback status |

**Response:** Dl=`<n>`

| Data | Description |
|------|-------------|
| 0x00 | Stopped |
| 0x01 | Transitioning |
| 0x02 | Playing |
| 0x03 | Paused |

**Example:** Query network playback (playing) -> `21 01 1C 01 F0 0D` -> `21 01 1C 00 01 01 0D`

---

### IMAX Enhanced (0x0C) (not AVR5)

Controls IMAX Enhanced.

**Command:** Cc=0x0C, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request current IMAX Enhanced state |
| 0xF1 | IMAX Enhanced Auto |
| 0xF2 | IMAX Enhanced On |
| 0xF3 | IMAX Enhanced Off |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | IMAX Enhanced Off |
| 0x01 | IMAX Enhanced On |
| 0x02 | IMAX Enhanced Auto |

**Example:** Set IMAX Enhanced to Auto -> `21 01 0C 01 F1 0D` -> `21 01 0C 00 01 02 0D`

---

## Setup Adjustment Command Specifications

### Treble Equalisation (0x35)

Adjust the amount of treble equalisation.

**Command:** Cc=0x35, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x0C | Set treble to 0dB - +12dB |
| 0x81 - 0x8C | Set treble to -1dB - -12dB |
| 0xF0 | Request current treble value |
| 0xF1 | Increment treble by 1dB |
| 0xF2 | Decrement treble by 1dB |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x0C | Treble is 0dB - +12dB |
| 0x81 - 0x8C | Treble is -1dB - -12dB |

**Example:** Set treble to -2dB -> `21 01 35 01 82 0D` -> `21 01 35 00 01 82 0D`

---

### Bass Equalisation (0x36)

Adjust the amount of bass equalisation.

**Command:** Cc=0x36, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x0C | Set bass to 0dB - +12dB |
| 0x81 - 0x8C | Set bass to -1dB - -12dB |
| 0xF0 | Request current bass value |
| 0xF1 | Increment bass by 1dB |
| 0xF2 | Decrement bass by 1dB |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x0C | Bass is 0dB - +12dB |
| 0x81 - 0x8C | Bass is -1dB - -12dB |

**Example:** Increase bass by 1dB (was 0dB) -> `21 01 36 01 F1 0D` -> `21 01 36 00 01 01 0D`

---

### Room Equalisation (0x37)

Turn the room equalisation system on/off.

**Command:** Cc=0x37, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request current Room EQ state |
| 0x00 | Room EQ off |
| 0x01 | Room EQ 1 on |
| 0x02 | Room EQ 2 on |
| 0x03 | Room EQ 3 on |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Room EQ is off |
| 0x01 | Room EQ 1 is on |
| 0x02 | Room EQ 2 is on |
| 0x03 | Room EQ 3 is on |
| 0x04 | Room EQ has not been calculated and is therefore off |

**Example:** Set Room EQ to EQ1 -> `21 01 37 01 01 0D` -> `21 01 37 00 01 01 0D`

---

### Dolby Audio (0x38)

Control the status of the Dolby Audio system.

**Command:** Cc=0x38, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Dolby Audio off |
| 0x01 | Dolby Audio movie mode |
| 0x02 | Dolby Audio music mode |
| 0x03 | Dolby Audio night mode |
| 0xF0 | Request current Dolby Audio mode |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Dolby Audio is off |
| 0x01 | Dolby Audio movie mode |
| 0x02 | Dolby Audio Music mode |
| 0x03 | Dolby Audio night mode |

**Example:** Set Dolby Audio to movie mode -> `21 01 38 01 01 0D` -> `21 01 38 00 01 02 0D`

---

### Balance (0x3B)

Adjust the balance control.

**Command:** Cc=0x3B, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x06 | Set the balance to 0 - 6 |
| 0x81 - 0x86 | Set the balance to -1 - -6 |
| 0xF0 | Request current balance |
| 0xF1 | Increment the balance by 1dB |
| 0xF2 | Decrement the balance by 1dB |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x06 | Balance is 0 - 6 |
| 0x81 - 0x86 | Balance is -1 - -6 |

**Example:** Set balance to -3 -> `21 01 3B 01 83 0D` -> `21 01 3B 00 01 83 0D`

---

### Subwoofer Trim (0x3F)

Adjust the value of subwoofer trim.

**Command:** Cc=0x3F, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x14 | Set positive subwoofer trim in 0.5dB steps (e.g. 0x02 = +1.0dB) |
| 0x81 - 0x94 | Set negative sub. trim in 0.5dB steps (e.g. 0x82 = -1.0dB) |
| 0xF0 | Request current subwoofer trim value |
| 0xF1 | Increment the subwoofer trim by 0.5dB |
| 0xF2 | Decrement the subwoofer trim by 0.5dB |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x14 | Positive subwoofer trim in 0.5dB steps (e.g. 0x02 = +1.0dB) |
| 0x81 - 0x94 | Negative subwoofer trim in 0.5dB steps (e.g. 0x82 = -1.0dB) |

**Example:** Set sub trim to -1.5dB -> `21 01 3F 01 85 0D` -> `21 01 3F 00 01 85 0D`

---

### Lipsync Delay (0x40)

Adjust the lipsync delay value.

**Command:** Cc=0x40, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x32 | Set the lipsync delay in 5ms steps (e.g. 0x08 = 40ms) |
| 0xF0 | Request current lipsync delay value |
| 0xF1 | Increment the lipsync delay by 5ms |
| 0xF2 | Decrement the lipsync delay by 5ms |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 - 0x32 | The lipsync delay in 5ms steps (e.g. 0x10 = 80ms) |

**Example:** Set lipsync delay to 50ms -> `21 01 40 01 0A 0D` -> `21 01 40 00 01 0A 0D`

---

### Compression (0x41)

Adjust the dynamic range compression setting.

**Command:** Cc=0x41, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Compression off |
| 0x01 | Set compression to medium |
| 0x02 | Set compression to high |
| 0xF0 | Request current compression setting |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Compression off |
| 0x01 | medium |
| 0x02 | high |

**Example:** Set compression to medium -> `21 01 41 01 01 0D` -> `21 01 41 00 01 01 0D`

---

## Audio/Video Info Commands

### Request Incoming Video Parameters (0x42)

Request the incoming video resolution, refresh rate and aspect ratio.

**Command:** Cc=0x42, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request incoming video parameters |

**Response:** Dl=0x08

| Data | Description |
|------|-------------|
| Data1 | Horizontal resolution MSB (e.g. for 720p: 0x05 since 1280 = 0x0500) |
| Data2 | Horizontal resolution LSB (e.g. for 720p: 0x00 since 1280 = 0x0500) |
| Data3 | Vertical resolution MSB (e.g. for 720p: 0x02 since 720 = 0x02D0) |
| Data4 | Vertical resolution LSB (e.g. for 720p: 0xD0 since 720 = 0x02D0) |
| Data5 | Refresh rate for full image update (half the field rate for interlaced signals) (e.g. for 50Hz progressive: 0x32) |
| Data6 | Interlaced flag: 0x00 = Progressive, 0x01 = Interlaced |
| Data7 | Aspect ratio: 0x00 = Undefined, 0x01 = 4:3, 0x02 = 16:9 |
| Data8 | Colour space: 0x00 = normal, 0x01 = HDR10, 0x02 = Dolby Vision, 0x03 = HLG, 0x04 = HDR10+ (not HDMI2.0) |

**Example:** Query video params (1280x720 50Hz 16:9 normal) -> `21 01 42 01 F0 0D` -> `21 01 42 00 08 05 00 02 D0 32 00 02 00 0D`

---

### Request Incoming Audio Format (0x43)

Request the incoming audio format.

**Command:** Cc=0x43, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request incoming audio format |

**Response:** Dl=0x02

| Data | Description |
|------|-------------|
| **Data1** | **Audio stream format** |
| 0x00 | PCM |
| 0x01 | Analogue Direct |
| 0x02 | Dolby Digital |
| 0x03 | Dolby Digital EX |
| 0x04 | Dolby Digital Surround |
| 0x05 | Dolby Digital Plus |
| 0x06 | Dolby Digital True HD |
| 0x07 | DTS |
| 0x08 | DTS 96/24 |
| 0x09 | DTS ES Matrix |
| 0x0A | DTS ES Discrete |
| 0x0B | DTS ES Matrix 96/24 |
| 0x0C | DTS ES Discrete 96/24 |
| 0x0D | DTS HD Master Audio |
| 0x0E | DTS HD High Res Audio |
| 0x0F | DTS Low Bit Rate |
| 0x10 | DTS Core |
| 0x13 | PCM Zero |
| 0x14 | Unsupported |
| 0x15 | Undetected |
| 0x16 | Dolby Atmos |
| 0x17 | DTS:X |
| 0x18 | IMAX ENHANCED (not AVR5) |
| 0x19 | Auro 3D (not AVR5) |
| **Data2** | **Audio channel configuration** |
| 0x00 | Dual Mono |
| 0x01 | Centre only |
| 0x02 | Stereo only |
| 0x03 | Stereo + mono surround |
| 0x04 | Stereo + Surround L & R |
| 0x05 | Stereo + Surround L & R + mono Surround Back |
| 0x06 | Stereo + Surround L & R + Surround Back L & R |
| 0x07 | Stereo + Surround L & R containing matrix info for surr. back L&R |
| 0x08 | Stereo + Centre |
| 0x09 | Stereo + Centre + mono surround |
| 0x0A | Stereo + Centre + Surround L & R |
| 0x0B | Stereo + Centre + Surround L & R + mono Surround Back |
| 0x0C | Stereo + Centre + Surround L & R + Surround Back L & R |
| 0x0D | Stereo + Centre + Surr. L&R plus matrix info for surr. back L&R |
| 0x0E | Stereo Downmix Lt Rt |
| 0x0F | Stereo Only (Lo Ro) |
| 0x10 | Dual Mono + LFE |
| 0x11 | Centre + LFE |
| 0x12 | Stereo + LFE |
| 0x13 | Stereo + single surround + LFE |
| 0x14 | Stereo + Surround L & R + LFE |
| 0x15 | Stereo + Surround L & R + mono Surround Back + LFE |
| 0x16 | Stereo + Surround L & R + Surround Back L & R + LFE |
| 0x17 | Stereo + Surround L & R + LFE |
| 0x18 | Stereo + Centre + LFE plus matrix information for surr. back L&R |
| 0x19 | Stereo + Centre + single surround + LFE |
| 0x1A | Stereo + Centre + Surround L & R + LFE (Standard 5.1) |
| 0x1B | Stereo + Centre + Surr. L & R + mono Surr. Back + LFE (6.1, e.g. DTS ES Discrete) |
| 0x1C | Stereo + Centre + Surround L & R + Surround Back L & R + LFE (7.1) |
| 0x1D | Stereo + Centre + Surround L & R + LFE, plus matrix for surr. back L&R (6.1, e.g. Dolby Digital EX) |
| 0x1E | Stereo Downmix (Lt Rt) + LFE |
| 0x1F | Stereo Only (Lo Ro) + LFE |
| 0x20 | Unknown |
| 0x21 | Undetected |
| 0x30 | Auro Quad (not AVR5) |
| 0x31 | Auro 5.0 (not AVR5) |
| 0x32 | Auro 5.1 (not AVR5) |
| 0x33 | Auro 2.2.2 (not AVR5) |
| 0x34 | Auro 8.0 (not AVR5) |
| 0x35 | Auro 9.1 (not AVR5) |
| 0x36 | Auro 10.1 (not AVR5) |
| 0x37 | Auro 11.1 (not AVR5) |
| 0x38 | Auro 13.1 (not AVR5) |

**Example:** Query audio format (Dolby Digital 5.1) -> `21 01 43 01 F0 0D` -> `21 01 43 00 02 02 1A 0D`

---

### Request Incoming Audio Sample Rate (0x44)

Request the incoming audio sample rate.

**Command:** Cc=0x44, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request incoming audio sample rate |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | 32 KHz |
| 0x01 | 44.1 KHz |
| 0x02 | 48 KHz |
| 0x03 | 88.2 KHz |
| 0x04 | 96 KHz |
| 0x05 | 176.4 KHz |
| 0x06 | 192 KHz |
| 0x07 | Unknown |
| 0x08 | Undetected |

**Example:** Query sample rate (48kHz) -> `21 01 44 01 F0 0D` -> `21 01 44 00 01 02 0D`

---

### Set/Request Sub Stereo Trim (0x45)

Set/Request the subwoofer trim value for stereo mode.

**Command:** Cc=0x45, Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Set the Sub Stereo Trim value to 0dB |
| 0x81 - 0x94 | Set the Sub Stereo Trim value to -0.5dB - -10.00dB |
| 0xF0 | Request Sub Stereo Trim value |
| 0xF1 | Increment Sub Stereo Trim value by 0.5dB |
| 0xF2 | Decrement Sub Stereo Trim value by 0.5dB |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00, 0x81 - 0x94 | Sub Stereo Trim value in -0.5dB steps |

**Example:** Set sub stereo trim to -1.5dB -> `21 01 45 01 83 0D` -> `21 01 45 00 01 83 0D`

---

## Control Commands

### Set/Request Zone 1 OSD on/off (0x4E)

Set/Request whether the Zone 1 OSD is shown.

**Command:** Cc=0x4E, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request current Zone 1 OSD on/off state |
| 0xF1 | Set Zone 1 OSD to On |
| 0xF2 | Set Zone 1 OSD to Off |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | Zone 1 OSD is On |
| 0x01 | Zone 1 OSD is Off |

**Example:** Set Zone 1 OSD to Off -> `21 01 4E 01 F2 0D` -> `21 01 4E 00 01 01 0D`

---

### Set/Request Video Output Switching (0x4F)

Set/Request the HDMI video output selection.

**Command:** Cc=0x4F, Dl=0x01

| Data | Description |
|------|-------------|
| 0x02 | Set HDMI Output 1 |
| 0x03 | Set HDMI Output 2 |
| 0x04 | Set HDMI Output 1 & 2 |
| 0xF0 | Request current video output switching setting |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x02 | HDMI Output 1 |
| 0x03 | HDMI Output 2 |
| 0x04 | HDMI Output 1 & 2 |

**Example:** Set video output to HDMI output 1 -> `21 01 4F 01 02 0D` -> `21 01 4F 00 01 02 0D`

---

### Set/Request Input Name (0x20)

This command returns the name of an input if renamed by the user. It can also be used to set the input name.

**Command:** Cc=0x20, Dl=0x01 (query) or `<n>` (limited to 10 characters) for setting name

| Data | Description |
|------|-------------|
| 0xF0 | Query |
| 1-`<n>` | ASCII characters for setting name |

**Response:** Dl=`<n>` if setting, 0x0A if requesting the name

| Data | Description |
|------|-------------|
| Data1-Data`<n>` | Input name in ASCII characters |

**Example:** Set input name to "BDP300" -> `21 01 20 06 42 44 50 33 30 30 0D` -> `21 20 01 20 00 06 42 44 50 33 30 30 0D`

---

### FM Scan Up/Down (0x23)

Initiates a FM scan up or down. Only valid if on FM input.

**Command:** Cc=0x23, Dl=0x01

| Data | Description |
|------|-------------|
| 0x01 | Scan up |
| 0x02 | Scan down |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0xFF | scanning |

---

### DAB Scan (0x24)

Initiates a DAB scan. Only valid if on DAB input.

**Command:** Cc=0x24, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Start DAB scan |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0xFF | scanning |
| 0x00 | Scan finished |

**Example:** Start DAB scan -> `21 01 24 01 F0 0D` -> `21 01 24 00 01 FF 0D`

---

### Heartbeat (0x25)

Heartbeat command to check unit is still connected and communication - also resets the EuP standby timer.

**Command:** Cc=0x25, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Heartbeat |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | response |

**Example:** Send heartbeat -> `21 01 25 01 F0 0D` -> `21 01 25 00 01 00 0D`

---

### Reboot (0x26)

Forces a reboot of the unit.

**Command:** Cc=0x26, Dl=0x06

| Data | Description |
|------|-------------|
| Data1 | 0x52 |
| Data2 | 0x45 |
| Data3 | 0x42 |
| Data4 | 0x4F |
| Data5 | 0x4F |
| Data6 | 0x54 |

(Data1-6 = ASCII "REBOOT" as confirmation pattern)

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | response |

**Example:** Send reboot -> `21 01 26 06 52 45 42 4F 4F 54 0D` -> `21 01 26 01 00 0D`

---

## Now Playing & Bluetooth

### Bluetooth Status (0x50)

Bluetooth status. Only valid if on BT input.

**Command:** Cc=0x50, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | BT status request |

**Response:** Dl=`<n>`

| Data | Description |
|------|-------------|
| **Data1** | **Connection status** |
| 0x00 | No connection |
| 0x01 | Connected, audio paused |
| 0x02 | Connected, audio playing SBC |
| 0x03 | Connected, audio playing AAC |
| 0x04 | Connected, audio playing aptX |
| 0x05 | Connected, audio playing aptX-HD |
| **Data2-Data`<n>`** | Name of track in ASCII if playing or paused |

**Example:** Query BT status (paired, paused) -> `21 01 50 01 F0 0D` -> `21 01 50 00 01 01 0D`

---

### Now Playing Information (0x64)

Request the various now playing track details. Response length is limited to 100 characters.

**Command:** Cc=0x64, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request the currently playing track title |
| 0xF1 | Request the currently playing artist |
| 0xF2 | Request the currently playing album |
| 0xF3 | Request the currently playing application (GoogleCast only) |
| 0xF4 | Request the currently playing sample rate |
| 0xF5 | Request the currently playing track encoder |

**Response for 0xF0 (Track):** Dl=`<n>`
Track title in ASCII characters.

**Response for 0xF1 (Artist):** Dl=`<n>`
Artist name in ASCII characters.

**Response for 0xF2 (Album):** Dl=`<n>`
Album name in ASCII characters.

**Response for 0xF3 (Application):** Dl=`<n>`
GoogleCast source application in ASCII characters.

**Response for 0xF4 (Sample rate):** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | 32 kHz |
| 0x01 | 44.1 kHz |
| 0x02 | 48 kHz |
| 0x03 | 88.2 kHz |
| 0x04 | 96 kHz |
| 0x05 | 176.4 kHz |
| 0x06 | 192 kHz |
| 0x07 | Unknown |
| 0x08 | Undetected |

**Response for 0xF5 (Audio encoder):** Dl=0x01

| Data | Description |
|------|-------------|
| 0x00 | MP3 |
| 0x01 | WAV |
| 0x02 | WMA |
| 0x03 | FLAC |
| 0x04 | ALAC |
| 0x05 | MQA |
| 0x0A | Unknown |

**Example:** Query artist ("A") -> `21 01 64 01 F1 0D` -> `21 01 64 00 02 41 0D`

---

## Configuration Commands

### Input Config (0x28)

Sends input config menu info.

**Command:** Cc=0x28, Dl=0x01 (query) / 0x19 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Input config |
| Data1-25 | Set input config as below |

**Response:** Dl=0x19

| Data | Description |
|------|-------------|
| **Data1-10** | Input name in ASCII characters (0xnn) |
| **Data11** | **Lip Sync** |
| | 0x00 - 0x32: Lip sync in 5mS steps |
| **Data12** | **Mode** |
| 0x00 | Last mode |
| 0x01 | Stereo |
| 0x02 | Stereo Direct |
| 0x03 | Dolby Surround |
| 0x04 | DTS Neural:X |
| 0x05 | Virtual Height |
| 0x06 | 16 Ch Stereo Mode |
| 0x07 | Auro 2D Surround (not AVR5) |
| 0x08 | Reserved |
| 0x09 | Auro 3D (not AVR5) |
| 0x0A | Auro Native (not AVR5) |
| **Data13** | **MCH mode** |
| 0x00 | Last mode |
| 0x01 | Native |
| 0x02 | Stereo Downmix |
| 0x03 | Virtual Height |
| 0x04 | Native Upmixer (Dolby Surround, DTS Virtual:X) |
| 0x05 | Reserved |
| 0x06 | Auro 2D Surround (not AVR5) |
| 0x07 | Auro 3D (not AVR5) |
| 0x08 | Auro Native (not AVR5) |
| **Data14** | **Bass** |
| | 0x00 - 0x0C: Bass is 0dB - +12dB |
| | 0x81 - 0x8C: Bass is -1dB - -12dB |
| **Data15** | **Treble** |
| | 0x00 - 0x0C: Treble is 0dB - +12dB |
| | 0x81 - 0x8C: Treble is -1dB - -12dB |
| **Data16** | **Room EQ** |
| 0x00 | Room EQ off |
| 0x01 | Room EQ1 |
| 0x02 | Room EQ2 |
| 0x03 | Room EQ3 |
| 0x04 | Not calculated |
| **Data17** | **Input Trim** |
| 0x00 | 1V |
| 0x01 | 2V |
| 0x02 | 4V |
| **Data18** | **Dolby Audio** |
| 0x00 | Dolby Audio off |
| 0x01 | Dolby Audio movie |
| 0x02 | music |
| 0x03 | night |
| **Data19** | **Stereo mode** |
| 0x00 | Left/Right |
| 0x01 | Left/Right+Sub |
| 0x02 | Sub+Sat |
| 0x03 | As speaker types |
| **Data20** | **Sub Stereo** |
| 0x00 | 0dB |
| 0x81 - 0x94 | Sub Stereo is -0.5 - -10dB |
| **Data21** | **IMAX Enhanced mode (not AVR5)** |
| 0x00 | Auto |
| 0x01 | On |
| 0x02 | Off |
| **Data22** | **Auro-Matic 3D (not AVR5)** |
| 0x00 | Small |
| 0x01 | Medium |
| 0x02 | Large |
| 0x03 | Movie |
| 0x04 | Speech |
| **Data23** | **Auro-Matic Strength (not AVR5)** |
| | 0x00 - 0x10: 0-16 |
| **Data24** | **Audio Source** |
| 0x00 | Analogue audio is in use for the current source |
| 0x01 | Digital audio is in use for the current source |
| 0x02 | HDMI audio is in use for the current source |
| **Data25** | **CD Direct** |
| 0x00 | CD Direct off |
| 0x01 | CD Direct on |

---

### General Setup (0x29)

Sends general setup menu info.

**Command:** Cc=0x29, Dl=0x01 (query) / 0x20 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Input config |
| Data1-32 | Set input config as below |

**Response:** Dl=0x20

| Data | Description |
|------|-------------|
| **Data1-10** | Input name in ASCII characters (0xnn) |
| **Data11** | **Audio stream format** (same values as 0x43 Data1) |
| 0x00 | PCM |
| 0x01 | Analogue Direct |
| 0x02 | Dolby Digital |
| 0x03 | Dolby Digital EX |
| 0x04 | Dolby Digital Surround |
| 0x05 | Dolby Digital Plus |
| 0x06 | Dolby Digital True HD |
| 0x07 | DTS |
| 0x08 | DTS 96/24 |
| 0x09 | DTS ES Matrix |
| 0x0A | DTS ES Discrete |
| 0x0B | DTS ES Matrix 96/24 |
| 0x0C | DTS ES Discrete 96/24 |
| 0x0D | DTS HD Master Audio |
| 0x0E | DTS HD High Res Audio |
| 0x0F | DTS Low Bit Rate |
| 0x10 | DTS Core |
| 0x13 | PCM Zero |
| 0x14 | Unsupported |
| 0x15 | Undetected |
| 0x16 | Dolby Atmos |
| 0x17 | DTS:X |
| 0x18 | IMAX ENHANCED (not AVR5) |
| 0x19 | Auro 3D (not AVR5) |
| **Data12** | **Audio channel configuration** (same values as 0x43 Data2, including Auro values 0x30-0x38) |
| **Data13** | **Incoming audio sample rate** |
| 0x00 | 32 KHz |
| 0x01 | 44.1 KHz |
| 0x02 | 48 KHz |
| 0x03 | 88.2 KHz |
| 0x04 | 96 KHz |
| 0x05 | 176.4 KHz |
| 0x06 | 192 KHz |
| 0x07 | Unknown |
| 0x08 | Undetected |
| **Data14** | **Incoming bitrate** |
| 0x00 | 32kbps |
| 0x01 | 56kbps |
| 0x02 | 64kbps |
| 0x03 | 96kbps |
| 0x04 | 112kbps |
| 0x05 | 128kbps |
| 0x06 | 192kbps |
| 0x07 | 224kbps |
| 0x08 | 256kbps |
| 0x09 | 320kbps |
| 0x0A | 384kbps |
| 0x0B | 448kbps |
| 0x0C | 512kbps |
| 0x0D | 576kbps |
| 0x0E | 640kbps |
| 0x0F | 768kbps |
| 0x10 | 960kbps |
| 0x11 | 1024kbps |
| 0x12 | 1152kbps |
| 0x13 | 1280kbps |
| 0x14 | 1344kbps |
| 0x15 | 1408kbps |
| 0x16 | 1411.2kbps |
| 0x17 | 1472kbps |
| 0x18 | 1536kbps |
| 0x19 | 1920kbps |
| 0x1A | 2048kbps |
| 0x1B | 3072kbps |
| 0x1C | 3840kbps |
| 0x1D | Open |
| 0x1E | Variable |
| 0x1F | Lossless |
| **Data15** | **Dialnorm** |
| | 0x00 (0dB) - 0x1F (31dB) |
| **Data16-20** | **Incoming video resolution** (returns 0x00 x 5 if no input) |
| | Horizontal resolution MSB |
| | Horizontal resolution LSB |
| | Vertical resolution MSB |
| | Vertical resolution LSB |
| | Refresh rate for full image update |
| **Data21** | **Interlaced flag** |
| 0x00 | Progressive |
| 0x01 | Interlaced |
| **Data22** | **Aspect ratio** |
| 0x00 | Undefined |
| 0x01 | 4:3 |
| 0x02 | 16:9 |
| **Data23** | **Colour space** |
| 0x00 | normal |
| 0x01 | HDR10 |
| 0x02 | Dolby Vision |
| 0x03 | HLG |
| 0x04 | HDR10+ |
| **Data24** | **Audio compression** |
| 0x00 | Off |
| 0x01 | Medium |
| 0x02 | High |
| **Data25** | **Balance** |
| | 0x00 - 0x06: Balance is 0 - 6 |
| | 0x81 - 0x86: Balance is -1 - -6 |
| **Data26** | **DTS Dialogue Control** |
| | 0x00 - 0x06: DTS Dialog Control is 0 - 6 |
| **Data27** | **Maximum volume** |
| | 0x00 (0) - 0x63 (99) |
| **Data28** | **Maximum on volume** |
| | 0x00 (0) - 0x63 (99): Set the volume |
| **Data29** | **Display on time** |
| 0x00 | 5 seconds |
| 0x01 | 10 seconds |
| 0x02 | 30 seconds |
| 0x03 | 1 minute |
| 0x04 | Always on |
| **Data30** | **Control option** |
| 0x00 | Off |
| 0x01 | RS232 |
| 0x02 | IP |
| **Data31** | **Power on option** |
| 0x00 | Last state |
| 0x01 | Standby |
| 0x02 | On |
| **Data32** | **Language** |
| 0x00 | English |
| 0x01 | Francais |
| 0x02 | Deutsch |
| 0x03 | Espanol |
| 0x04 | Nederlands |
| 0x05 | Pyccknn (Russian) |
| 0x06 | Chinese |

---

### Speaker Types (0x2A)

Set / request speaker type menu info.

**Command:** Cc=0x2A, Dl=0x01 (query) / 0x0D (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Speaker Types |
| Data1-10 | Set Speaker Types as below |

**Response:** Dl=0x0D

| Data | Description |
|------|-------------|
| **Data1-6** | **Speaker type (1=L/R, 2=Centre, 3=Surr, 4=Back, 5=Height1, 6=Height2)** |
| 0x00 | Large |
| 0x01 | Small, 40Hz |
| 0x02 | Small, 50Hz |
| 0x03 | Small, 60Hz |
| 0x04 | Small, 70Hz |
| 0x05 | Small, 80Hz |
| 0x06 | Small, 90Hz |
| 0x07 | Small, 100Hz |
| 0x08 | Small, 110Hz |
| 0x09 | Small, 120Hz |
| 0x0A | Small, 150Hz |
| 0x0B | Small, 160Hz |
| 0x0C | Small, 170Hz |
| 0x0D | Small, 180Hz |
| 0x0E | Small, 180Hz |
| 0x0F | Small, 200Hz |
| 0x10 | None |
| **Data7** | **Subwoofer** |
| 0x00 | Subwoofer |
| 0x01 | None |
| **Data8** | **Channel 13 & 14 (not AVR5, AVR10 - report 0x11)** |
| 0x00 | Front wide, large |
| 0x01 | Front wide, small, 40Hz |
| 0x02 | Front wide, small, 50Hz |
| 0x03 | Front wide, small, 60Hz |
| 0x04 | Front wide, small, 70Hz |
| 0x05 | Front wide, small, 80Hz |
| 0x06 | Front wide, small, 90Hz |
| 0x07 | Front wide, small, 100Hz |
| 0x08 | Front wide, small, 110Hz |
| 0x09 | Front wide, small, 120Hz |
| 0x0A | Front wide, small, 150Hz |
| 0x0B | Front wide, small, 160Hz |
| 0x0C | Front wide, small, 170Hz |
| 0x0D | Front wide, small, 180Hz |
| 0x0E | Front wide, small, 190Hz |
| 0x0F | Front wide, small, 200Hz |
| 0x10 | Front subs |
| 0x11 | None |
| **Data9** | **Channel 15 & 16 (not AVR5, AVR10, report 0x21)** |
| 0x00 | Middle heights, large, 0x10 = CH & TS large |
| 0x01 | Middle heights, small, 40Hz, 0x10 = CH & TS, small, 40Hz |
| 0x02 | Middle heights, small, 50Hz, 0x12 = CH & TS, small, 50Hz |
| 0x03 | Middle heights, small, 60Hz, 0x13 = CH & TS, small, 60Hz |
| 0x04 | Middle heights, small, 70Hz, 0x14 = CH & TS, small, 70Hz |
| 0x05 | Middle heights, small, 80Hz, 0x15 = CH & TS, small, 80Hz |
| 0x06 | Middle heights, small, 90Hz, 0x16 = CH & TS, small, 90Hz |
| 0x07 | Middle heights, small, 100Hz, 0x17 = CH & TS, small, 100Hz |
| 0x08 | Middle heights, small, 110Hz, 0x18 = CH & TS, small, 110Hz |
| 0x09 | Middle heights, small, 120Hz, 0x19 = CH & TS, small, 120Hz |
| 0x0A | Middle heights, small, 150Hz, 0x1A = CH & TS, small, 150Hz |
| 0x0B | Middle heights, small, 160Hz, 0x1B = CH & TS, small, 160Hz |
| 0x0C | Middle heights, small, 170Hz, 0x1C = CH & TS, small, 170Hz |
| 0x0D | Middle heights, small, 180Hz, 0x1D = CH & TS, small, 180Hz |
| 0x0E | Middle heights, small, 190Hz, 0x1E = CH & TS, small, 190Hz |
| 0x0F | Middle heights, small, 200Hz, 0x1F = CH & TS, small, 200Hz |
| 0x20 | Rear subs |
| 0x21 | None |
| **Data10** | **Height type** |
| 0x00 | Top |
| 0x01 | Dolby Enabled |
| **Data11** | **Use channel 6&7** |
| 0x00 | Surround back |
| 0x01 | Bi-Amp L+R |
| 0x02 | Zone2 (not AVR5, AVR10) |
| 0x03 | Height1 |
| **Data12** | **Filter slope** |
| 0x00 | 12dB |
| 0x01 | 24dB |
| 0x02 | 36dB |
| 0x03 | 48dB |
| **Data13** | **Sub gain** |
| 0x00 | 0dB |
| 0x01 | -6dB |
| 0x02 | -12dB |
| 0x03 | -18dB |
| 0x04 | -24dB |
| 0x05 | -30dB |

---

### Speaker Distances (0x2B)

Set / request speaker distance menu info.

**Command:** Cc=0x2B, Dl=0x01 (query) / 0x21 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Speaker Distance |
| Data1-33 | Set Speaker Distance as below |

**Response:** Dl=0x21

| Data | Description |
|------|-------------|
| **Data1** | **Units** |
| 0x00 | metres |
| 0x01 | feet |
| 0x02 | mS |
| **Data2-33** | **Distance in 2 bytes per speaker (m:cm / ft:in)** |
| | Front Left |
| | Centre |
| | Front Right |
| | Surr. Right |
| | Surr. Back Right |
| | Surr. Back Left |
| | Surr. Left |
| | Left Top Front |
| | Right Top Front |
| | Left Top Back |
| | Right Top Back |
| | Subwoofer |
| | Channel13 (not AVR5, AVR10, reports 0x00, 0x00) |
| | Channel14 (not AVR5, AVR10, reports 0x00, 0x00) |
| | Channel15 (not AVR5, AVR10, reports 0x00, 0x00) |
| | Channel 16 (not AVR5, AVR10, reports 0x00, 0x00) |

---

### Speaker Levels (0x2C)

Set / request speaker level menu info.

**Command:** Cc=0x2C, Dl=0x01 (query) / 0x12 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Speaker Levels |
| Data1-16 | Set Speaker Levels as below |

**Response:** Dl=0x12

| Data | Description |
|------|-------------|
| **Data1** | **Test tone** |
| 0x00 | Internal |
| 0x01 | External |
| **Data2-17** | **Speaker level** |
| | 0x00 - 0x14: 0dB - +10dB |
| | 0x81 - 0x94: -0.5dB - -10dB |
| | Speaker order: Front Left, Centre, Front Right, Surr. Right, Surr. Back Right, Surr. Back Left, Surr. Left, Left Top Front, Right Top Front, Left Top Back, Right Top Back, Subwoofer, Channel13 (not AVR5, AVR10, reports 0x14), Channel14 (not AVR5, AVR10, reports 0x14), Channel15 (not AVR5, AVR10, reports 0x14), Channel 16 (not AVR5, AVR10, reports 0x14) |
| **Data18** | **Noise output** |
| 0x00 | None (switch off audio noise output) |
| 0x01 | Front Left |
| 0x02 | Centre |
| 0x03 | Front Right |
| 0x04 | Surr. Right |
| 0x05 | Surr. Back Right |
| 0x06 | Surr. Back Left |
| 0x07 | Surr. Left |
| 0x08 | Left Top Front |
| 0x09 | Right Top Front |
| 0x0A | Left Top Back |
| 0x0B | Right Top Back |
| 0x0C | Subwoofer |
| 0x0D | Channel 13 (not AVR5, AVR10) |
| 0x0E | Channel 14 (not AVR5, AVR10) |
| 0x0F | Channel 15 (not AVR5, AVR10) |
| 0x10 | Channel 16 (not AVR5, AVR10) |

---

### Video Inputs (0x2D)

Set / request video inputs config.

**Command:** Cc=0x2D, Dl=0x01 (query) / 0x06 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Video Inputs config |
| Data1-16 | Set Video Inputs config as below |

**Response:** Dl=0x06

Video input in order for: Data1=CD, Data2=Aux, Data3=FM, Data4=DAB, Data5=NET, Data6=BT

| Data | Description |
|------|-------------|
| 0x00 | STB |
| 0x01 | GAME |
| 0x02 | AV |
| 0x03 | SAT |
| 0x04 | BD |
| 0x05 | VCR |
| 0x06 | PVR |
| 0x07 | None |

---

### HDMI Settings (0x2E)

Set / request HDMI settings menu info.

**Command:** Cc=0x2E, Dl=0x01 (query) / 0x0A (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request HDMI config |
| Data1-09 | Set HDMI config as below |

**Response:** Dl=0x0A

| Data | Description |
|------|-------------|
| **Data1** | **Zone 1 OSD** |
| 0x00 | Off |
| 0x01 | On |
| **Data2** | **Zone 1 Out** |
| 0x00 | Out 1 & 2 |
| 0x01 | Out 1 |
| 0x02 | Out 2 |
| **Data3** | **Zone 1 lip sync (information only)** |
| | 0x00 - 0xFA: lipsync in 1mS steps |
| **Data4** | **HDMI Audio to TV** |
| 0x00 | Off |
| 0x01 | On |
| **Data5** | **HDMI Bypass & IP** |
| 0x00 | Off |
| 0x01 | HDMI & IP On |
| **Data6** | **HDMI Bypass source** |
| 0x00 | Last |
| 0x01 | STB |
| 0x02 | Game |
| 0x03 | AV |
| 0x04 | SAT |
| 0x05 | BD |
| 0x06 | VCR |
| 0x07 | PVR |
| **Data7** | **CEC Control** |
| 0x00 | Off |
| 0x01 | Output1 |
| **Data8** | **ARC Control** |
| 0x00 | Off |
| 0x01 | Auto |
| **Data9** | **TV Audio** |
| 0x00 | Off |
| 0x01 | Auto |
| **Data10** | **Power Off Control** |
| 0x00 | Off |
| 0x01 | Auto |

---

### Zone Settings (0x2F) (not AVR5, AVR10)

Set / request Zone settings menu info.

**Command:** Cc=0x2F, Dl=0x01 (query) / 0x06 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Zone settings |
| Data1-10 | Set Zone settings as below |

**Response:** Dl=0x06

| Data | Description |
|------|-------------|
| **Data1** | **Zone 2 Input (not AVR5, AVR10)** |
| 0x00 | Follow Zone1 |
| 0x01 | CD |
| 0x02 | BD |
| 0x03 | AV |
| 0x04 | SAT |
| 0x05 | PVR |
| 0x06 | VCR |
| 0x07 | STB |
| 0x08 | Game |
| 0x09 | FM |
| 0x0A | DAB |
| 0x0B | NET |
| 0x0C | BT |
| 0x0D | Aux |
| 0x0E | Display |
| **Data2** | **Zone 2 Status** |
| 0x00 | Standby |
| 0x01 | On |
| **Data3** | **Zone 2 Volume** |
| | 0x14 (20) - 0x53 (83) |
| **Data4** | **Zone 2 Max. Volume** |
| | 0x14 (20) - 0x53 (83) |
| **Data5** | **Zone 2 fixed volume** |
| 0x00 | No |
| 0x01 | Yes |
| **Data6** | **Zone 2 Maximum On Volume** |
| | 0x14 (20) - 0x53 (83) |

---

### Network (0x30)

Set / request Network menu info.

**Command:** Cc=0x30, Dl=0x01 (query) / 0x45 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Network settings |
| Data1-69 | Set Network settings as below |

**Response:** Dl=0x45

| Data | Description |
|------|-------------|
| **Data1** | **Net source** |
| 0x00 | Follow Zone1 |
| 0x01 | Follow Zone2 |
| **Data2-21** | SSID name (20 character limit) |
| **Data22-41** | Network key (20 character limit - set only) |
| **Data42-45** | IP address (0x00-0xFF per byte) |
| **Data46-49** | MAC address (0x00-0xFF per byte) |
| **Data50-69** | Friendly name (20 characters, ASCII) |

---

### Bluetooth (0x32)

Set / request Bluetooth menu info.

**Command:** Cc=0x32, Dl=0x01 (query) / 0x02 (set) / 0xnn

| Data | Description |
|------|-------------|
| 0xF0 | Request Bluetooth settings |
| Data1-2 | Set Bluetooth settings as below (only pair & clear can be set) |

**Response:** Dl=0xn (dependent on number of paired devices)

| Data | Description |
|------|-------------|
| **Data1** | **Pair Device (set only)** |
| 0x00 | no effect |
| 0x01 | Start Pair Device |
| **Data2** | **Clear Paired Devices (set only)** |
| 0x00 | no effect |
| 0x01 | Clear Paired Devices |
| **Data3-22** | Paired device1 name (read only / 20 characters, ASCII) |
| **Data23-42** | Paired device2 name (read only / 20 characters, ASCII) |
| **Data43-`<n>`** | Paired device3-8 name (read only / 20 characters, ASCII) |

---

### Setup (0x27)

Starts remote setup of the unit.

**Command:** Cc=0x27, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request setup |

**Response:** Dl=0x01

| Data | Description |
|------|-------------|
| 0xnn | setup mode active, nn = version of menu |
| 0xFF | setup mode from front panel, remote setup not possible |

---

### Room EQ Name(s) (0x34)

Request Room EQ name(s).

**Command:** Cc=0x34, Dl=0x01

| Data | Description |
|------|-------------|
| 0xF0 | Request EQ names |

**Response:** Dl=0xn (dependent on number of EQ slots filled: 20, 40, or 60)

| Data | Description |
|------|-------------|
| Data1-20 | EQ1 name (read only / 20 characters, ASCII) |
| Data21-40 | EQ2 name (read only / 20 characters, ASCII) |
| Data41-60 | EQ3 name (read only / 20 characters, ASCII) |

---

### Engineering Menu (0x33)

Set / request Engineering menu info.

**Command:** Cc=0x33, Dl=0x01 (query) / 0x33 (set)

| Data | Description |
|------|-------------|
| 0xF0 | Request Engineering menu settings |
| Data1- | Set Engineering menu settings as below |

**Response:** Dl=0x2B

| Data | Description |
|------|-------------|
| **Data1** | **Reset Factory Defaults (set only)** |
| 0x00 | no effect |
| 0x01 | Reset factory defaults |
| **Data2** | **Check for update (set only)** |
| 0x00 | no effect |
| 0x01 | Check for Update |
| **Data3** | **Restore Secure backup** |
| 0x00 | no effect |
| 0x01 | Restore secure backup |
| **Data4** | **Store Secure Backup** |
| 0x00 | no effect |
| 0x01 | Store secure backup |
| **Data5** | **Restore USB backup** |
| 0x00 | no effect |
| 0x01 | Restore USB backup |
| **Data6** | **Store USB Backup** |
| 0x00 | no effect |
| 0x01 | Store USB |
| **Data7-10** | Pin in hex 1-4 |
| **Data11** | **Region** |
| 0x00 | Europe |
| 0x01 | US |
| 0x02 | Canada |
| 0x03 | Australia |
| 0x04 | China |
| **Data12** | **Remote Code** |
| 0x00 | 16 |
| 0x01 | 19 |
| **Data13** | **Standby Mode** |
| 0x00 | Auto |
| 0x01 | Manual |
| **Data14** | **Protection sensitivity** |
| 0x00 | High (default) |
| 0x01 | Medium |
| 0x02 | Low |
| **Data15** | **Use Display HDMI** |
| 0x00 | Yes |
| 0x01 | No |
| **Data16** | **Display type** |
| 0x00 | 16:9 |
| 0x01 | 21:9 |
| **Data17** | **DANTE enable** |
| 0x00 | Off |
| 0x01 | On |
| **Data18** | **C4 SDDP** |
| 0x00 | Off |
| 0x01 | On |
| **Data19** | **Send C4 Identify** |
| 0x00 | No effect |
| 0x01 | Send C4 Identify |
| **Data20** | **Shut down code (info only)** |
| 0x00 | 00 (normal) |
| 0x01 | 01 (amp DC offset) |
| 0x02 | 02 (amp overtemp) |
| 0x03 | 03 (amp overcurrent) |
| **Data21-29** | Host/IAP version (info only), Version in ASCII e.g. "2.01/0.03" |
| **Data30-33** | DSP version (info only), Version in ASCII e.g. "1.03" |
| **Data34-37** | OSD version (info only), Version in ASCII e.g. "0.11" |
| **Data38-51** | NET version (info only), Version in ASCII e.g. "2.5.13.50017-6" |

---

## AV RC5 Command Codes

These codes are recognised as infra-red signals received by the front panel, RC5 electrical signals received by the remote in jacks and as control data using the 'Simulate RC5 IR Command' (0x08).

### Basic Functions

These RC5 codes are present on the supplied IR remote control and provide control over basic amplifier and video processing functions.

| Function | RC5 Code [system-command] | RC5 Code (Data1-Data2) |
|----------|---------------------------|------------------------|
| Standby | 16-12 | 0x10 - 0x0C |
| Eject (Speaker trim) | 16-45 | 0x10 - 0x2D |
| 1 | 16-1 | 0x10 - 0x01 |
| 2 | 16-2 | 0x10 - 0x02 |
| 3 | 16-3 | 0x10 - 0x03 |
| 4 | 16-4 | 0x10 - 0x04 |
| 5 | 16-5 | 0x10 - 0x05 |
| 6 | 16-6 | 0x10 - 0x06 |
| 7 | 16-7 | 0x10 - 0x07 |
| 8 | 16-8 | 0x10 - 0x08 |
| 9 | 16-9 | 0x10 - 0x09 |
| SYNC - Access Lipsync Delay control | 16-50 | 0x10 - 0x32 |
| 0 | 16-0 | 0x10 - 0x00 |
| INFO - Cycle between VFD information panels | 16-55 | 0x10 - 0x37 |
| Rewind | 16-121 | 0x10 - 0x79 |
| Fast Forward | 16-52 | 0x10 - 0x34 |
| Skip Back | 16-33 | 0x10 - 0x21 |
| Skip Forward | 16-11 | 0x10 - 0x0B |
| Stop | 16-54 | 0x10 - 0x36 |
| Play | 16-53 | 0x10 - 0x35 |
| Pause | 16-48 | 0x10 - 0x30 |
| Disc (Record) (DTS dialogue control) | 16-90 | 0x10 - 0x5A |
| MENU (Enter system menu) | 16-82 | 0x10 - 0x52 |
| Navigate Up | 16-86 | 0x10 - 0x56 |
| Pop Up (Dolby Volume on/off) | 16-70 | 0x10 - 0x46 |
| Navigate Left | 16-81 | 0x10 - 0x51 |
| OK | 16-87 | 0x10 - 0x57 |
| Navigate Right | 16-80 | 0x10 - 0x50 |
| Audio (Room EQ on/off) | 16-30 | 0x10 - 0x1E |
| Navigate Down | 16-85 | 0x10 - 0x55 |
| RTN (Access Subwoofer Trim control) | 16-51 | 0x10 - 0x33 |
| HOME | 16-43 | 0x10 - 0x2B |
| Mute | 16-13 | 0x10 - 0x0D |
| Increase volume (+) | 16-16 | 0x10 - 0x10 |
| MODE (Cycle between decoding modes) | 16-32 | 0x10 - 0x20 |
| DISP (Change VFD brightness) | 16-59 | 0x10 - 0x3B |
| Activate DIRECT mode | 16-10 | 0x10 - 0x0A |
| Decrease volume (-) | 16-17 | 0x10 - 0x11 |
| Red | 16-41 | 0x10 - 0x29 |
| Green | 16-42 | 0x10 - 0x2A |
| Yellow | 16-43 | 0x10 - 0x2B |
| Blue | 16-55 | 0x10 - 0x37 |
| Radio | 16-91 | 0x10 - 0x5B |
| Aux | 16-99 | 0x10 - 0x63 |
| Net | 16-92 | 0x10 - 0x5C |
| AV | 16-94 | 0x10 - 0x5E |
| Sat | 16-27 | 0x10 - 0x1B |
| PVR | 16-96 | 0x10 - 0x60 |
| Game | 16-97 | 0x10 - 0x61 |
| BD | 16-98 | 0x10 - 0x62 |
| CD | 16-118 | 0x10 - 0x76 |
| STB | 16-100 | 0x10 - 0x64 |
| UHD | 16-125 | 0x10 - 0x7D |
| BT | 16-122 | 0x10 - 0x7A |
| Display | 16-58 | 0x10 - 0x3A |
| Power On | 16-123 | 0x10 - 0x7B |
| Power Off | 16-124 | 0x10 - 0x7C |

### Advanced Functions

These RC5 codes are not present on the supplied remote control but have been created for custom install use. In order for the AVR to respond to these codes they must be transmitted from a programmable IR remote control or over the control link using the 'Simulate RC5 IR Command' (0x08).

| Function | RC5 Code [system-command] | RC5 Code (Data1-Data2) |
|----------|---------------------------|------------------------|
| Change control to next zone | 16-95 | 0x10 - 0x5F |
| Access Bass control | 16-39 | 0x10 - 0x27 |
| Access Speaker Trim controls | 16-37 | 0x10 - 0x25 |
| Access Treble control | 16-14 | 0x10 - 0x0E |
| Random | 16-76 | 0x10 - 0x4C |
| Repeat | 16-49 | 0x10 - 0x31 |
| Direct mode On | 16-78 | 0x10 - 0x4E |
| Direct mode Off | 16-79 | 0x10 - 0x4F |
| Multi Channel | 16-106 | 0x10 - 0x6A |
| Stereo | 16-107 | 0x10 - 0x6B |
| Dolby Surround | 16-110 | 0x10 - 0x6E |
| DTS Neo:6 Cinema | 16-111 | 0x10 - 0x6F |
| DTS Neo:6 Music | 16-112 | 0x10 - 0x70 |
| DTS Neural:X | 16-113 | 0x10 - 0x71 |
| Reserved | 16-114 | 0x10 - 0x72 |
| Virtual Height | 16-115 | 0x10 - 0x73 |
| 5/7 Ch Stereo | 16-69 | 0x10 - 0x45 |
| Dolby D EX | 16-23 | 0x10 - 0x17 |
| Auro Matic-3D | 16-71 | 0x10 - 0x47 |
| Auro Native | 16-103 | 0x10 - 0x67 |
| Auro 2D | 16-104 | 0x10 - 0x68 |
| Mute On | 16-26 | 0x10 - 0x1A |
| Mute Off | 16-120 | 0x10 - 0x78 |
| FM | 16-28 | 0x10 - 0x1C |
| DAB | 16-72 | 0x10 - 0x48 |
| Lip Sync +5ms | 16-15 | 0x10 - 0x0F |
| Lip sync -5ms | 16-101 | 0x10 - 0x65 |
| Sub trim +0.5dB | 16-105 | 0x10 - 0x69 |
| Sub trim -0.5dB | 16-108 | 0x10 - 0x6C |
| Display Off | 16-31 | 0x10 - 0x1F |
| Display L1 | 16-34 | 0x10 - 0x22 |
| Display L2 | 16-35 | 0x10 - 0x23 |
| Balance left | 16-38 | 0x10 - 0x26 |
| Balance right | 16-40 | 0x10 - 0x28 |
| Bass +1 | 16-44 | 0x10 - 0x2C |
| Bass -1 | 16-56 | 0x10 - 0x38 |
| Treble +1 | 16-46 | 0x10 - 0x2E |
| Treble -1 | 16-102 | 0x10 - 0x66 |
| Set Zone 2 to Follow Zone 1 | 16-20 | 0x10 - 0x14 |
| Zone 2 Power On (not AVR5, AVR10) | 23-123 | 0x17 - 0x7B |
| Zone 2 Power Off (not AVR5, AVR10) | 23-124 | 0x17 - 0x7C |
| Zone 2 Vol+ (not AVR5, AVR10) | 23-1 | 0x17 - 0x01 |
| Zone 2 Vol- (not AVR5, AVR10) | 23-2 | 0x17 - 0x02 |
| Zone 2 Mute (not AVR5, AVR10) | 23-3 | 0x17 - 0x03 |
| Zone 2 Mute On (not AVR5, AVR10) | 23-4 | 0x17 - 0x04 |
| Zone 2 Mute Off (not AVR5, AVR10) | 23-5 | 0x17 - 0x05 |
| Zone 2 CD (not AVR5, AVR10) | 23-6 | 0x17 - 0x06 |
| Zone 2 BD (not AVR5, AVR10) | 23-7 | 0x17 - 0x07 |
| Zone 2 STB (not AVR5, AVR10) | 23-8 | 0x17 - 0x08 |
| Zone 2 AV (not AVR5, AVR10) | 23-9 | 0x17 - 0x09 |
| Zone 2 Game (not AVR5, AVR10) | 23-11 | 0x17 - 0x0B |
| Zone 2 Aux (not AVR5, AVR10) | 23-13 | 0x17 - 0x0D |
| Zone 2 PVR (not AVR5, AVR10) | 23-15 | 0x17 - 0x0F |
| Zone 2 FM (not AVR5, AVR10) | 23-14 | 0x17 - 0x0E |
| Zone 2 DAB (not AVR5, AVR10) | 23-16 | 0x17 - 0x10 |
| Zone 2 USB (not AVR5, AVR10) | 23-18 | 0x17 - 0x12 |
| Zone 2 NET (not AVR5, AVR10) | 23-19 | 0x17 - 0x13 |
| Zone 2 SAT (not AVR5, AVR10) | 23-20 | 0x17 - 0x14 |
| Zone 2 UHD (not AVR5, AVR10) | 23-23 | 0x17 - 0x17 |
| Zone 2 BT (not AVR5, AVR10) | 23-22 | 0x17 - 0x16 |
| Select HDMI Out 1 | 16-73 | 0x10 - 0x49 |
| Select HDMI Out 2 | 16-74 | 0x10 - 0x4A |
| Select HDMI Out 1 & 2 | 16-75 | 0x10 - 0x4B |
