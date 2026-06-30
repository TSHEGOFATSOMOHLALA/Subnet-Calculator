"""Command-line interface for subnetcalc."""

from __future__ import annotations

import argparse
import json
import sys

from . import core


def _print_info(info: core.SubnetInfo, as_json: bool) -> None:
    if as_json:
        print(json.dumps(info.as_dict(), indent=2))
        return

    rows = [
        ("CIDR", info.cidr),
        ("Network address", info.network_address),
        ("Broadcast address", info.broadcast_address or "n/a"),
        ("Netmask", info.netmask),
        ("Wildcard mask", info.wildcard_mask),
        ("First usable host", info.first_usable or "n/a"),
        ("Last usable host", info.last_usable or "n/a"),
        ("Total addresses", str(info.total_addresses)),
        ("Usable hosts", str(info.usable_hosts)),
        ("Private", str(info.is_private)),
        ("IP version", str(info.version)),
    ]
    width = max(len(label) for label, _ in rows)
    for label, val in rows:
        print(f"{label:<{width}} : {val}")


def cmd_info(args: argparse.Namespace) -> None:
    info = core.get_subnet_info(args.network)
    _print_info(info, args.json)


def cmd_split(args: argparse.Namespace) -> None:
    subnets = core.split_into_subnets(args.network, args.new_prefix)
    if args.json:
        print(json.dumps([s.as_dict() for s in subnets], indent=2))
        return
    print(f"{len(subnets)} subnet(s):\n")
    for s in subnets:
        print(f"  {s.cidr:<20} hosts: {s.first_usable or '-'} - {s.last_usable or '-'} "
              f"({s.usable_hosts} usable)")


def cmd_vlsm(args: argparse.Namespace) -> None:
    requirements = [int(h) for h in args.hosts.split(",")]
    allocations = core.vlsm_allocate(args.network, requirements)
    if args.json:
        print(json.dumps(allocations, indent=2))
        return
    print(f"VLSM allocation for {args.network}:\n")
    for alloc in allocations:
        print(
            f"  need {alloc['requested_hosts']:>5} hosts -> {alloc['cidr']:<20} "
            f"({alloc['usable_hosts']} usable, range {alloc['first_usable']} - {alloc['last_usable']})"
        )


def cmd_supernet(args: argparse.Namespace) -> None:
    result = core.supernet(args.networks)
    if args.json:
        print(json.dumps({"supernet": result}, indent=2))
    else:
        print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subnetcalc", description="A subnet calculator and IP toolkit."
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Show details about a network, e.g. 192.168.1.0/24")
    p_info.add_argument("network")
    p_info.set_defaults(func=cmd_info)

    p_split = sub.add_parser("split", help="Split a network into equal subnets")
    p_split.add_argument("network")
    p_split.add_argument("new_prefix", type=int, help="New prefix length, e.g. 26")
    p_split.set_defaults(func=cmd_split)

    p_vlsm = sub.add_parser("vlsm", help="Allocate subnets sized to host requirements")
    p_vlsm.add_argument("network")
    p_vlsm.add_argument("hosts", help="Comma-separated host counts, e.g. 50,20,10,2")
    p_vlsm.set_defaults(func=cmd_vlsm)

    p_super = sub.add_parser("supernet", help="Find the smallest supernet containing given networks")
    p_super.add_argument("networks", nargs="+")
    p_super.set_defaults(func=cmd_supernet)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
