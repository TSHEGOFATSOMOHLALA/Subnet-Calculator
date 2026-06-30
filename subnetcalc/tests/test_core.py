import pytest

from subnetcalc import core


def test_get_subnet_info_basic():
    info = core.get_subnet_info("192.168.1.0/24")
    assert info.network_address == "192.168.1.0"
    assert info.broadcast_address == "192.168.1.255"
    assert info.netmask == "255.255.255.0"
    assert info.first_usable == "192.168.1.1"
    assert info.last_usable == "192.168.1.254"
    assert info.usable_hosts == 254
    assert info.total_addresses == 256
    assert info.is_private is True
    assert info.version == 4


def test_get_subnet_info_host_bits_set():
    # strict=False should tolerate host bits being set
    info = core.get_subnet_info("192.168.1.130/24")
    assert info.network_address == "192.168.1.0"


def test_get_subnet_info_slash_32():
    info = core.get_subnet_info("10.0.0.1/32")
    assert info.total_addresses == 1
    assert info.usable_hosts == 1
    assert info.broadcast_address is None


def test_split_into_subnets():
    subnets = core.split_into_subnets("192.168.0.0/24", 26)
    assert len(subnets) == 4
    assert subnets[0].cidr == "192.168.0.0/26"
    assert subnets[1].cidr == "192.168.0.64/26"
    assert subnets[2].cidr == "192.168.0.128/26"
    assert subnets[3].cidr == "192.168.0.192/26"
    for s in subnets:
        assert s.usable_hosts == 62


def test_split_into_subnets_invalid_prefix():
    with pytest.raises(ValueError):
        core.split_into_subnets("192.168.0.0/24", 22)


@pytest.mark.parametrize(
    "num_hosts,expected_prefix",
    [
        (1, 30),
        (2, 30),
        (5, 29),
        (14, 28),
        (50, 26),
        (254, 24),
        (255, 23),
    ],
)
def test_smallest_prefix_for_hosts(num_hosts, expected_prefix):
    assert core.smallest_prefix_for_hosts(num_hosts) == expected_prefix


def test_smallest_prefix_for_hosts_invalid():
    with pytest.raises(ValueError):
        core.smallest_prefix_for_hosts(0)


def test_vlsm_allocate_fits_and_preserves_order():
    allocations = core.vlsm_allocate("192.168.1.0/24", [50, 20, 10, 2])
    assert len(allocations) == 4
    assert allocations[0]["requested_hosts"] == 50
    assert allocations[1]["requested_hosts"] == 20
    assert allocations[2]["requested_hosts"] == 10
    assert allocations[3]["requested_hosts"] == 2

    for alloc in allocations:
        assert alloc["usable_hosts"] >= alloc["requested_hosts"]

    # No overlapping subnets
    networks = [core.parse_network(a["cidr"]) for a in allocations]
    for i, n1 in enumerate(networks):
        for j, n2 in enumerate(networks):
            if i != j:
                assert not n1.overlaps(n2)


def test_vlsm_allocate_too_small_raises():
    with pytest.raises(ValueError):
        core.vlsm_allocate("192.168.1.0/29", [50, 20])


def test_supernet_collapses_adjacent():
    result = core.supernet(["192.168.0.0/25", "192.168.0.128/25"])
    assert result == "192.168.0.0/24"


def test_supernet_single_network():
    result = core.supernet(["10.0.0.0/24"])
    assert result == "10.0.0.0/24"


def test_supernet_mixed_versions_raises():
    with pytest.raises(ValueError):
        core.supernet(["10.0.0.0/24", "2001:db8::/32"])


def test_ipv6_basic():
    info = core.get_subnet_info("2001:db8::/64")
    assert info.version == 6
    assert info.network_address == "2001:db8::"
