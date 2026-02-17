"""UPnP/SSDP device discovery helpers.

Requires the optional ``discovery`` dependency group:
``pip install arcam-fmj[discovery]``
"""

import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _log_exception(msg: str, *args: object) -> None:
    """Log an error and turn on traceback if debug is on."""
    _LOGGER.error(msg, *args, exc_info=_LOGGER.getEffectiveLevel() == logging.DEBUG)


def get_uniqueid_from_udn(data: str | None) -> str | None:
    """Extract a unique id from udn."""
    if data is None:
        return None
    try:
        return data[5:].split("-")[4]
    except IndexError:
        _log_exception("Unable to get unique id from %s", data)
        return None


def get_possibly_invalid_xml(data: str) -> Any:
    from defusedxml import ElementTree

    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError:
        _LOGGER.info("Device provided corrupt xml, trying with ampersand replacement")
        data = re.sub(r"&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)", r"&amp;", data)
        return ElementTree.fromstring(data)


def get_udn_from_xml(xml: Any) -> str | None:
    result: str | None = xml.findtext(
        "d:device/d:UDN", None, {"d": "urn:schemas-upnp-org:device-1-0"}
    )
    return result


async def get_uniqueid_from_device_description(session: Any, url: str) -> str | None:
    """Retrieve and extract unique id from url."""
    import aiohttp
    from defusedxml import ElementTree

    try:
        async with session.get(url) as req:
            req.raise_for_status()
            data = await req.text()
            xml = get_possibly_invalid_xml(data)
            udn = get_udn_from_xml(xml)
            return get_uniqueid_from_udn(udn)
    except (aiohttp.ClientError, TimeoutError, ElementTree.ParseError):
        _log_exception("Unable to get device description from %s", url)
        return None


async def get_uniqueid_from_host(session: Any, host: str) -> str | None:
    """Try to deduce a unique id from a host based on ssdp/upnp."""
    return await get_uniqueid_from_device_description(session, f"http://{host}:8080/dd.xml")
