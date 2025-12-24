---
name: wsdiscovery
description: WS-Discovery protocol scanner for discovering and enumerating ONVIF cameras and IoT devices on the network. Use when you need to discover ONVIF devices, cameras, or WS-Discovery enabled equipment on a network.
---

# Wsdiscovery - WS-Discovery Protocol Scanner

You are helping the user discover and enumerate devices using the WS-Discovery protocol (commonly used by ONVIF cameras and IoT devices) using the wsdiscovery tool.

## Tool Overview

Wsdiscovery implements the WS-Discovery protocol to discover network devices that support this standard. It's particularly useful for finding ONVIF cameras, network video recorders (NVRs), and other IoT devices that advertise themselves via WS-Discovery.

## Instructions

When the user asks to discover ONVIF devices, find network cameras, or scan for WS-Discovery devices:

1. **Understand the target**:
   - Ask for the target hostname or IP address
   - Determine if they want verbose output (full XML responses)
   - Decide on output format

2. **Execute the scan**:
   - Use the wsdiscovery command from the iothackbot bin directory
   - Basic usage: `wsdiscovery <hostname_or_ip>`
   - For verbose output: `wsdiscovery <hostname_or_ip> -v`
   - For JSON output: `wsdiscovery <hostname_or_ip> --format json`

3. **Output formats**:
   - `--format text` (default): Human-readable colored output with device details
   - `--format json`: Machine-readable JSON
   - `--format quiet`: Minimal output

## What It Discovers

The tool extracts and displays:
- IP addresses and ports
- Endpoint references (device UUIDs)
- Device types
- Manufacturer information
- Device names and models
- Hardware versions
- Serial numbers
- Firmware versions
- Location information
- Service endpoints (XAddrs) - URLs for device management
- Metadata versions

## Examples

Discover devices on a specific host:
```bash
wsdiscovery 192.168.1.100
```

Discover with full XML responses:
```bash
wsdiscovery 192.168.1.100 -v
```

Output device information as JSON:
```bash
wsdiscovery 192.168.1.100 --format json
```

Scan network broadcast address to find all devices:
```bash
wsdiscovery 239.255.255.250
```

## Important Notes

- WS-Discovery uses multicast/broadcast discovery
- Devices must support the WS-Discovery protocol to be found
- Common with ONVIF cameras, printers, and network media devices
- Service endpoints (XAddrs) can be used with onvifscan for further testing
- The tool parses ONVIF-specific scope information when available
