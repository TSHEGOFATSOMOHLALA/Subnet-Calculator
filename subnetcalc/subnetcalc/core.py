"""Core IPv4/IPv6 subnet calculation logic built on the stdlib ipaddress module."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Union

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@dataclass
class SubnetInfo:
    """Summary of a network's key properties."""

    cidr: str
    network_address: str
    broadcast_address: str | None
    netmask: str
    wildcard_mask: str
    first_usable: str | None
    last_usable: str | None
    total_addresses: int
    usable_hosts: int
    is_private: bool
    version: int

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def parse_network(value: str, strict: bool = False) -> IPNetwork:
    """Parse a string like '192.168.1.0/24' or '10.0.0.5/8' into an IPNetwork.

    strict=False allows host bits to be set (e.g. 192.168.1.5/24), matching
    common real-world input.
    """
    return ipaddress.ip_network(value, strict=strict)


def get_subnet_info(value: str) -> SubnetInfo:
    """Return a full breakdown of a network address."""
    net = parse_network(value)
    ip_cls = ipaddress.IPv4Address if net.version == 4 else ipaddress.IPv6Address

    if net.version == 4 and net.num_addresses >= 2:
        broadcast = str(net.broadcast_address)
    else:
        broadcast = None

    # Compute usable range arithmetically instead of materializing every host
    # in the network (a /64 IPv6 network has 2**64 addresses).
    network_int = int(net.network_address)
    if net.num_addresses == 1:
        first_usable = last_usable = str(net.network_address)
        usable_hosts = 1
    elif net.version == 4:
        if net.num_addresses == 2:
            # /31: both addresses are usable (RFC 3021), no network/broadcast.
            first_usable = str(ip_cls(network_int))
            last_usable = str(ip_cls(network_int + 1))
            usable_hosts = 2
        else:
            first_usable = str(ip_cls(network_int + 1))
            last_usable = str(net.broadcast_address - 1)
            usable_hosts = net.num_addresses - 2
    else:
        first_usable = str(ip_cls(network_int))
        last_usable = str(net[-1])
        usable_hosts = net.num_addresses

    return SubnetInfo(
        cidr=str(net),
        network_address=str(net.network_address),
        broadcast_address=broadcast,
        netmask=str(net.netmask),
        wildcard_mask=str(net.hostmask),
        first_usable=first_usable,
        last_usable=last_usable,
        total_addresses=net.num_addresses,
        usable_hosts=usable_hosts,
        is_private=net.is_private,
        version=net.version,
    )


def split_into_subnets(value: str, new_prefix: int) -> list[SubnetInfo]:
    """Split a network into equal-sized subnets at the given new prefix length."""
    net = parse_network(value)
    if new_prefix < net.prefixlen:
        raise ValueError(
            f"new_prefix /{new_prefix} must be >= base prefix /{net.prefixlen}"
        )
    subnets = net.subnets(new_prefix=new_prefix)
    return [get_subnet_info(str(s)) for s in subnets]


def smallest_prefix_for_hosts(num_hosts: int, version: int = 4) -> int:
    """Return the smallest prefix length (largest subnet) that fits num_hosts usable hosts."""
    if num_hosts < 1:
        raise ValueError("num_hosts must be >= 1")

    max_bits = 32 if version == 4 else 128
    reserved = 2 if version == 4 else 0  # network + broadcast reserved for IPv4
    # Smallest meaningful subnet for IPv4 is /30 (2 usable hosts); IPv6 has no
    # network/broadcast reservation so it can start from a single address.
    start_bits = 2 if version == 4 else 0

    for host_bits in range(start_bits, max_bits + 1):
        capacity = 2**host_bits
        usable = capacity - reserved
        if usable >= num_hosts:
            return max_bits - host_bits
    raise ValueError("Requested host count exceeds address space")


def vlsm_allocate(base_network: str, host_requirements: list[int]) -> list[dict]:
    """Variable Length Subnet Masking: carve a base network into subnets sized
    to fit each entry in host_requirements (largest first), preserving the
    caller's original ordering in the output.

    Raises ValueError if the base network is too small to fit all requirements.
    """
    net = parse_network(base_network)
    version = net.version

    # Sort by host count descending, but remember original positions.
    indexed = sorted(
        enumerate(host_requirements), key=lambda pair: pair[1], reverse=True
    )

    allocations: list[dict | None] = [None] * len(host_requirements)
    cursor = net.network_address
    broadcast_limit = int(net.broadcast_address)

    for original_index, num_hosts in indexed:
        prefix = smallest_prefix_for_hosts(num_hosts, version=version)
        size = 2 ** ((32 if version == 4 else 128) - prefix)

        start = int(cursor)
        # Align start to a boundary for this subnet size.
        if start % size != 0:
            start = (start // size + 1) * size

        end = start + size - 1
        if end > broadcast_limit:
            raise ValueError(
                f"Base network {base_network} is too small to fit all requested subnets"
            )

        subnet = ipaddress.ip_network((start, prefix), strict=False) if False else None
        ip_cls = ipaddress.IPv4Address if version == 4 else ipaddress.IPv6Address
        subnet_str = f"{ip_cls(start)}/{prefix}"
        info = get_subnet_info(subnet_str)
        allocations[original_index] = {
            "requested_hosts": num_hosts,
            **info.as_dict(),
        }
        cursor = ip_cls(end + 1)

    return allocations  # type: ignore[return-value]


def supernet(networks: list[str]) -> str:
    """Find the smallest supernet (CIDR block) that contains all given networks."""
    nets = [parse_network(n) for n in networks]
    if len({n.version for n in nets}) > 1:
        raise ValueError("Cannot supernet a mix of IPv4 and IPv6 networks")

    collapsed = list(ipaddress.collapse_addresses(nets))
    if len(collapsed) == 1:
        return str(collapsed[0])

    # Not contiguous/aligned enough to collapse to one block; widen until it fits.
    version = nets[0].version
    max_bits = 32 if version == 4 else 128
    low = min(int(n.network_address) for n in nets)
    high = max(int(n.broadcast_address) if version == 4 else int(n[-1]) for n in nets)

    for prefix in range(max_bits, -1, -1):
        size = 2 ** (max_bits - prefix)
        candidate_start = (low // size) * size
        if candidate_start <= low and candidate_start + size - 1 >= high:
            ip_cls = ipaddress.IPv4Address if version == 4 else ipaddress.IPv6Address
            return str(ipaddress.ip_network((candidate_start, prefix)))
    raise ValueError("Could not compute supernet")
