# Arcam FMJ – Project Instructions for Claude

## Project Overview

Python library for controlling Arcam AV receivers via RS232/TCP (port 50000). Binary protocol with 0x21 start byte, 0x0D end byte. Query current value by sending `data=[0xF0]`.

## Code Review

Follow the rules in `docs/code-review-guidelines.md` for all code reviews, refactorings, and new code. This document defines the project's standards for architecture, code style, type hints, testing, dependencies, and security.

## Project Structure

```
src/arcam/fmj/
  __init__.py   # Protocol definitions: enums, data classes, exceptions, I/O, DeviceProfile
  state.py      # Zone state management (getters/setters, update(), wait_changed())
  client.py     # Async TCP client with heartbeat/listener
  console.py    # CLI entry point (arcam-fmj command)
  display.py    # Rich-powered state display
  dummy.py      # DummyServer for testing
  server.py     # Server-side protocol support
  utils.py      # Throttle, async_retry
tests/
  conftest.py   # Shared fixtures: make_state, make_reader
  test_*.py     # One test file per module
docs/
  protocol-reference.md  # Complete protocol spec (SH289E Rev F) – use this for all protocol lookups
```

- `src/` layout with `arcam` as namespace package (no `__init__.py` in `src/arcam/`).
- `py.typed` marker present (PEP 561).

## Key Conventions

### Enums & Data Classes
- Enums extend `IntOrTypeEnum` (custom IntEnum with version/flags metadata).
- Data classes use `attr.s` decorator with PEP 526 annotation style.
- `__all__` is explicitly defined in `__init__.py`.

### State Management
- `State` stores raw bytes in `_state[CommandCodes]`, parsed via getter methods.
- `_get_int(cc)` / `_set_int(cc, value, min_val, max_val)` helpers for integer controls.
- `_now_playing` and `_presets` use dict pattern for multi-sub-query commands.
- `wait_changed()` for event-based monitoring.

### Device Families
- `DeviceProfile` dataclass + `detect_api_model()` for device family lookup.
- API version sets: `APIVERSION_450_SERIES`, `APIVERSION_HDA_SERIES`, etc.
- AMX Duet keys: `Device-Model`, `Device-Make`, `Device-Revision` (NOT `Model`/`Make`).

## Protocol Reference

Always use `docs/protocol-reference.md` for protocol lookups – not the PDF. Key facts:
- Dolby Audio (0x38) = 4-mode enum (OFF/MOVIE/MUSIC/NIGHT), NOT boolean.
- NOW_PLAYING_INFO (0x64) uses 6 sub-queries (0xF0–0xF5).
- Bluetooth Status shares CommandCode 0x50 with VIDEO_OUTPUT_FRAME_RATE.
- Room EQ (0x37): 0=off, 1=EQ1, 2=EQ2, 3=EQ3, 4=not calculated.

## Development Workflow

### Running Tests
```bash
.venv/bin/pytest tests/ -v          # Full suite (~257 tests)
.venv/bin/pytest tests/ --cov       # With coverage
```

### Test Patterns
- pytest with `asyncio_mode = "auto"` – no `@pytest.mark.asyncio` needed.
- Use `make_state` factory fixture from `conftest.py` for State tests.
- Use `make_reader` factory fixture for protocol I/O tests.
- Mock pattern: `MagicMock(spec=Client)` with `AsyncMock()` for async methods.
- TDD approach: write tests first, then implement.

### Adding New Commands
1. Look up the command in `docs/protocol-reference.md`.
2. Add `CommandCodes` enum entry with correct version flags in `__init__.py`.
3. Add getter/setter methods to `State` in `state.py`.
4. Write tests in `test_state.py` using `make_state` fixture.
5. Follow existing patterns (`_get_int`/`_set_int` for integers, `_now_playing` dict for sub-queries).

## Dependencies

- Runtime: `attrs>=22.1` (only required dependency).
- Optional `[discovery]`: `aiohttp>=3.8`, `defusedxml>=0.7.1`.
- Optional `[cli]`: `rich>=13.0`.
- Requires Python >= 3.11.

## Style Notes

- Short variable names (`cc`, `zn`, `e`, `s`) are acceptable in domain context.
- Module-level `_LOGGER = logging.getLogger(__name__)` in every module.
- Prefer minimal changes – don't refactor surrounding code unless asked.
- Don't add docstrings, comments, or type annotations to unchanged code.
