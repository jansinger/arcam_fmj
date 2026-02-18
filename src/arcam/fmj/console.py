import argparse
import asyncio
import logging
import sys

from . import CommandCodes, SourceCodes
from .client import Client, ClientContext
from .display import build_table, print_state
from .dummy import DummyServer
from .server import ServerContext
from .state import State

_LOGGER = logging.getLogger(__name__)


def auto_int(x: str) -> int:
    return int(x, 0)


def auto_source(x: str) -> SourceCodes:
    return SourceCodes[x]


parser = argparse.ArgumentParser(description="Communicate with arcam receivers.")
parser.add_argument("--verbose", action="store_true")

subparsers = parser.add_subparsers(dest="subcommand")

parser_state = subparsers.add_parser("state")
parser_state.add_argument("--host", required=True)
parser_state.add_argument("--port", default=50000, type=int)
parser_state.add_argument("--zone", default=1, type=int)
parser_state.add_argument("--volume", type=int)
parser_state.add_argument("--source", type=auto_source)
parser_state.add_argument("--monitor", action="store_true")
parser_state.add_argument("--power-on", action=argparse.BooleanOptionalAction)
parser_state.add_argument("--power-off", action=argparse.BooleanOptionalAction)

parser_client = subparsers.add_parser("client")
parser_client.add_argument("--host", required=True)
parser_client.add_argument("--port", default=50000, type=int)
parser_client.add_argument("--zone", default=1, type=int)
parser_client.add_argument("--command", type=auto_int, required=True)
parser_client.add_argument("--data", nargs="+", default=[0xF0], type=auto_int)

parser_server = subparsers.add_parser("server")
parser_server.add_argument("--host", default="localhost")
parser_server.add_argument("--port", default=50000, type=int)
parser_server.add_argument("--model", default="AVR450")


async def run_client(args: argparse.Namespace) -> None:
    client = Client(args.host, args.port)
    async with ClientContext(client):
        result = await client.request(args.zone, CommandCodes(args.command), bytes(args.data))
        print(result)


def _live_progress(live):
    """Return a progress callback that updates a Rich Live display."""

    def _update(state):
        table = build_table(state)
        if table is not None:
            live.update(table)

    return _update


async def run_state(args: argparse.Namespace) -> None:
    client = Client(args.host, args.port)
    async with ClientContext(client):
        state = State(client, args.zone)

        try:
            from rich.live import Live

            with Live(refresh_per_second=8) as live:
                await state.update(progress=_live_progress(live))
        except ImportError:
            await state.update()

        if args.volume is not None:
            await state.set_volume(args.volume)

        if args.source is not None:
            await state.set_source(args.source)

        if args.power_on:
            await state.set_power(True)

        if args.power_off:
            await state.set_power(False)

        if args.monitor:
            async with state:
                print_state(state)
                while client.connected:
                    await state.wait_changed()
                    print_state(state)
        else:
            print_state(state)


async def run_server(args: argparse.Namespace) -> None:
    server = DummyServer(args.host, args.port, args.model)
    async with ServerContext(server):
        while True:
            await asyncio.sleep(delay=1)


def main() -> None:
    args = parser.parse_args()

    if args.verbose:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        channel = logging.StreamHandler(sys.stdout)
        channel.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        channel.setFormatter(formatter)
        root.addHandler(channel)

    if args.subcommand == "client":
        asyncio.run(run_client(args))
    elif args.subcommand == "state":
        asyncio.run(run_state(args))
    elif args.subcommand == "server":
        asyncio.run(run_server(args))


if __name__ == "__main__":
    main()
