"""Shared test fixtures."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from arcam.fmj import ApiModel
from arcam.fmj.client import Client
from arcam.fmj.state import State


@pytest.fixture
def make_state():
    """Factory fixture to create a State with a mocked Client."""

    def _make_state(zn=1, api_model=ApiModel.APIHDA_SERIES):
        client = MagicMock(spec=Client)
        client.request = AsyncMock()
        client.request_raw = AsyncMock()
        client.send = AsyncMock()
        client.connected = True
        return State(client, zn, api_model)

    return _make_state


@pytest.fixture
def make_reader():
    """Factory fixture to create a StreamReader fed with bytes."""

    def _make_reader(data: bytes) -> asyncio.StreamReader:
        reader = asyncio.StreamReader()
        reader.feed_data(data)
        reader.feed_eof()
        return reader

    return _make_reader
