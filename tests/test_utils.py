"""Tests for utils."""

import asyncio
import time

import pytest
from aiohttp import web

from arcam.fmj.utils import Throttle, async_retry, get_uniqueid_from_device_description

MOCK_UNIQUE_ID = "0011044feeef"
MOCK_UDN = f"uuid:aa331113-fa23-3333-2222-{MOCK_UNIQUE_ID}"
MOCK_SERIAL_NO = "01a0132032f01103100400010010ff00"


def _get_dd(unique_id, serial_no, udn):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:pnpx="http://schemas.microsoft.com/windows/pnpx/2005/11" xmlns:microsoft="urn:schemas-microsoft-com:WMPNSS-1-0" xmlns:df="http://schemas.microsoft.com/windows/2008/09/devicefoundation">
   <specVersion>
      <major>1</major>
      <minor>0</minor>
   </specVersion>
   <device>
      <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>


      <friendlyName>Arcam media client {unique_id}</friendlyName>
      <manufacturer>ARCAM</manufacturer>
      <manufacturerURL>http://www.arcam.co.uk</manufacturerURL>
      <modelDescription>ir-ser-FS2026-0500-0001_V2.5.14.36554-15</modelDescription>
      <modelName> </modelName>
      <modelNumber>AVR450, AVR750</modelNumber>
      <modelURL>http://www.arcamradio.co.uk</modelURL>
      <serialNumber>{serial_no}</serialNumber>
      <UDN>{udn}</UDN>
      <iconList>
         <icon>
            <mimetype>image/png</mimetype>
            <width>48</width>
            <height>48</height>
            <depth>32</depth>
            <url>/icon.png</url>
         </icon>
         <icon>
            <mimetype>image/jpeg</mimetype>
            <width>48</width>
            <height>48</height>
            <depth>32</depth>
            <url>/icon.jpg</url>
         </icon>
         <icon>
            <mimetype>image/png</mimetype>
            <width>120</width>
            <height>120</height>
            <depth>32</depth>
            <url>/icon2.png</url>
         </icon>
         <icon>
            <mimetype>image/jpeg</mimetype>
            <width>120</width>
            <height>120</height>
            <depth>32</depth>
            <url>/icon2.jpg</url>
         </icon>
      </iconList>
  <serviceList><service><serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType><serviceId>urn:upnp-org:serviceId:AVTransport</serviceId><SCPDURL>AVTransport/scpd.xml</SCPDURL><controlURL>AVTransport/control</controlURL><eventSubURL>AVTransport/event</eventSubURL></service><service><serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType><serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId><SCPDURL>ConnectionManager/scpd.xml</SCPDURL><controlURL>ConnectionManager/control</controlURL><eventSubURL>ConnectionManager/event</eventSubURL></service><service><serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType><serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId><SCPDURL>RenderingControl/scpd.xml</SCPDURL><controlURL>RenderingControl/control</controlURL><eventSubURL>RenderingControl/event</eventSubURL></service></serviceList><dlna:X_DLNADOC xmlns:dlna="urn:schemas-dlna-org:device-1-0">DMR-1.50</dlna:X_DLNADOC>
<pnpx:X_hardwareId>VEN_2A2D&amp;DEV_0001&amp;SUBSYS_0001&amp;REV_01 VEN_0033&amp;DEV_0006&amp;REV_01</pnpx:X_hardwareId>
<pnpx:X_compatibleId>MS_DigitalMediaDeviceClass_DMR_V001</pnpx:X_compatibleId>
<pnpx:X_deviceCategory>MediaDevices</pnpx:X_deviceCategory>
<df:X_deviceCategory>Multimedia.DMR</df:X_deviceCategory>
<microsoft:magicPacketWakeSupported>0</microsoft:magicPacketWakeSupported>
<microsoft:magicPacketSendSupported>1</microsoft:magicPacketSendSupported></device></root>
"""


async def test_throttle_no_delay_on_first_call():
    """Test that Throttle.get() returns immediately on first call."""
    throttle = Throttle(0.1)
    start = time.monotonic()
    await throttle.get()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


async def test_throttle_delays_subsequent_calls():
    """Test that Throttle.get() delays second call by configured delay."""
    throttle = Throttle(0.1)
    await throttle.get()
    start = time.monotonic()
    await throttle.get()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05  # Should be ~0.1s, allow some tolerance


async def test_throttle_no_delay_after_waiting():
    """Test that Throttle.get() doesn't delay if enough time has passed."""
    throttle = Throttle(0.05)
    await throttle.get()
    import asyncio

    await asyncio.sleep(0.1)
    start = time.monotonic()
    await throttle.get()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


async def test_retry_fails():
    calls = 0

    @async_retry(2, Exception)
    async def tester():
        nonlocal calls
        calls += 1
        raise Exception()

    with pytest.raises(Exception):  # noqa: B017
        await tester()

    assert calls == 2


async def test_retry_succeeds():
    calls = 0

    @async_retry(2, Exception)
    async def tester():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise Exception()
        return True

    assert await tester()


async def test_retry_unexpected():
    calls = 0

    @async_retry(2, TimeoutError)
    async def tester():
        nonlocal calls
        calls += 1
        raise ValueError()

    with pytest.raises(ValueError):
        await tester()
    assert calls == 1


async def test_throttle_priority_ordering():
    """Test that higher priority (lower number) requests are dispatched first."""
    throttle = Throttle(0.01)
    order = []

    async def acquire(priority, label):
        await throttle.get(priority=priority)
        order.append(label)

    # First request starts immediately
    await throttle.get()

    # Queue three requests with different priorities while throttle is busy
    tasks = [
        asyncio.create_task(acquire(2, "poll")),
        asyncio.create_task(acquire(0, "user")),
        asyncio.create_task(acquire(1, "normal")),
    ]
    # Let them all register in the queue
    await asyncio.sleep(0)
    await asyncio.gather(*tasks)

    assert order == ["user", "normal", "poll"]


async def test_throttle_dedup_cancels_previous():
    """Test that dedup_key cancels a previous queued entry with same key."""
    throttle = Throttle(0.01)

    # First call to occupy the throttle
    await throttle.get()

    # Queue two requests with the same dedup_key
    key = (1, "VOLUME")
    task1 = asyncio.create_task(throttle.get(priority=0, dedup_key=key))
    await asyncio.sleep(0)
    task2 = asyncio.create_task(throttle.get(priority=0, dedup_key=key))
    await asyncio.sleep(0)

    # task1 should be cancelled, task2 should complete
    with pytest.raises(asyncio.CancelledError):
        await task1

    await task2  # Should complete without error


async def test_throttle_dedup_different_keys_both_run():
    """Test that different dedup_keys do not cancel each other."""
    throttle = Throttle(0.01)
    completed = []

    await throttle.get()

    async def acquire(key, label):
        await throttle.get(priority=0, dedup_key=key)
        completed.append(label)

    tasks = [
        asyncio.create_task(acquire((1, "VOLUME"), "vol")),
        asyncio.create_task(acquire((1, "MUTE"), "mute")),
    ]
    await asyncio.gather(*tasks)
    assert set(completed) == {"vol", "mute"}


async def test_throttle_backwards_compatible():
    """Test that get() with no arguments still works (backwards compat)."""
    throttle = Throttle(0.01)
    # Should work without priority or dedup_key
    await throttle.get()
    await throttle.get()


async def test_get_uniqueid_from_device_description(aiohttp_client):
    response_text = ""

    async def device_description(request):
        return web.Response(text=response_text)

    app = web.Application()
    app.router.add_get("/dd.xml", device_description)
    client = await aiohttp_client(app)

    response_text = "non xml"
    assert await get_uniqueid_from_device_description(client, "/dd.xml") is None

    response_text = _get_dd(MOCK_UNIQUE_ID, MOCK_SERIAL_NO, "malformed udn")
    assert await get_uniqueid_from_device_description(client, "/dd.xml") is None

    response_text = _get_dd(MOCK_UNIQUE_ID, MOCK_SERIAL_NO, MOCK_UDN)
    assert await get_uniqueid_from_device_description(client, "/dd.xml") == MOCK_UNIQUE_ID
