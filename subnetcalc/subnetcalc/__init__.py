from .core import (
    SubnetInfo,
    get_subnet_info,
    smallest_prefix_for_hosts,
    split_into_subnets,
    supernet,
    vlsm_allocate,
)

__all__ = [
    "SubnetInfo",
    "get_subnet_info",
    "smallest_prefix_for_hosts",
    "split_into_subnets",
    "supernet",
    "vlsm_allocate",
]

__version__ = "0.1.0"
