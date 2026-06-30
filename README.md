# Subnet Calculator

[![CI](https://github.com/TSHEGOFATSOMOHLALA/Subnet-Calculator/actions/workflows/ci.yml/badge.svg)](https://github.com/TSHEGOFATSOMOHLALA/Subnet-Calculator/actions/workflows/ci.yml)

**[Live demo →](https://TSHEGOFATSOMOHLALA.github.io/Subnet-Calculator/)**

A command-line subnet calculator and IP toolkit for IPv4/IPv6, built on Python's
standard `ipaddress` module — no third-party dependencies. Also ships as an
interactive browser demo, no install required.



## Features

- **info** — network/broadcast address, usable host range, netmask, wildcard mask
- **split** — divide a network into equal-sized subnets at a target prefix
- **vlsm** — Variable Length Subnet Masking: allocate right-sized subnets from a list of host requirements
- **supernet** — find the smallest CIDR block containing a set of networks
- IPv4 and IPv6 support (CLI/library — the browser demo currently covers IPv4)
- JSON output for scripting (`--json`)

## Install

```bash
git clone https://github.com/TSHEGOFATSOMOHLALA/Subnet-Calculator.git
cd Subnet-Calculator
pip install -e .
```

## Usage

```bash
# Basic network info
subnetcalc info 192.168.1.0/24

# Split a /24 into four /26 subnets
subnetcalc split 192.168.0.0/24 26

# VLSM: carve a /24 into subnets fitting these host counts
subnetcalc vlsm 192.168.1.0/24 50,20,10,2

# Find the smallest supernet containing two networks
subnetcalc supernet 192.168.0.0/25 192.168.0.128/25

# JSON output, for piping into other tools
subnetcalc --json info 10.0.0.0/8
```

### As a library

```python
from subnetcalc import get_subnet_info, vlsm_allocate

info = get_subnet_info("192.168.1.0/24")
print(info.first_usable, info.last_usable, info.usable_hosts)

allocations = vlsm_allocate("192.168.1.0/24", [50, 20, 10, 2])
```

## Development

```bash
pip install -e .[dev]
pytest -v
```

## License

MIT
