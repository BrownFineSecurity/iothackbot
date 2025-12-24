---
name: iotnet
description: IoT network traffic analyzer for detecting IoT protocols and identifying security vulnerabilities in network communications. Use when you need to analyze network traffic, identify IoT protocols, or assess network security of IoT devices.
---

# IoTNet - IoT Network Traffic Analyzer

You are helping the user analyze network traffic to detect IoT protocols and identify security vulnerabilities using the iotnet tool.

## Tool Overview

IoTNet analyzes network packet captures (PCAPs) or performs live traffic capture to:
- Detect IoT-specific protocols (MQTT, CoAP, Zigbee, etc.)
- Identify security vulnerabilities in network traffic
- Analyze protocol distribution
- Find unencrypted communications
- Detect weak authentication mechanisms
- Identify insecure IoT device behaviors

## Instructions

When the user asks to analyze network traffic, capture IoT traffic, or assess network security:

1. **Determine input type**:
   - PCAP file analysis (offline)
   - Live network capture (requires interface)

2. **Gather requirements**:
   - For PCAP: Get file path(s)
   - For live capture: Get network interface name and duration
   - Ask about filtering needs (specific IPs, protocols)
   - Check if custom detection rules are needed

3. **Execute the analysis**:
   - Use the iotnet command from the iothackbot bin directory

## Usage Modes

### PCAP Analysis (Offline)
Analyze one or more existing packet capture files:
```bash
iotnet capture1.pcap capture2.pcap
```

### Live Capture
Capture and analyze traffic in real-time:
```bash
sudo iotnet -i eth0 -d 30
```

## Parameters

**Input Options:**
- `pcap_files`: One or more PCAP files to analyze
- `-i, --interface`: Network interface for live capture

**Filtering Options:**
- `--ip`: Filter traffic by IP address
- `-c, --capture-filter`: BPF syntax filter for live capture
- `--display-filter`: Wireshark display filter for PCAP analysis

**Live Capture Options:**
- `-d, --duration`: Capture duration in seconds (default: 30)

**Analysis Options:**
- `--config`: Custom IoT detection rules configuration file
  - Default: `config/iot/detection_rules.json` in the iothackbot directory

**Output Options:**
- `--format text|json|quiet`: Output format (default: text)
- `-v, --verbose`: Detailed output

## Examples

Analyze a packet capture file:
```bash
iotnet /path/to/capture.pcap
```

Live capture for 60 seconds on wifi interface:
```bash
sudo iotnet -i wlan0 -d 60
```

Analyze traffic for specific IP:
```bash
iotnet capture.pcap --ip 192.168.1.100
```

Live capture with BPF filter:
```bash
sudo iotnet -i eth0 -c "port 1883 or port 5683" -d 45
```

Multiple PCAPs with custom config:
```bash
iotnet file1.pcap file2.pcap --config custom-rules.json
```

Filter by display filter (Wireshark syntax):
```bash
iotnet capture.pcap --display-filter "mqtt or coap"
```

## Detected IoT Protocols

The tool can identify:
- **MQTT**: Message Queue Telemetry Transport
- **CoAP**: Constrained Application Protocol
- **Zigbee**: Low-power mesh networking
- **Z-Wave**: Home automation protocol
- **ONVIF**: IP camera protocol
- **UPnP/SSDP**: Universal Plug and Play
- **Modbus**: Industrial control protocol
- And many more (configurable)

## Security Checks

IoTNet identifies vulnerabilities such as:
- Unencrypted MQTT traffic
- Missing TLS/encryption
- Weak or no authentication
- Plaintext credentials
- Insecure protocol versions
- Known vulnerable implementations

## Output Information

Results include:
- **Total packets analyzed**
- **Protocol distribution** with percentages
- **IoT findings** with protocol details and packet info
- **Vulnerabilities** with severity levels (high/medium/low)
- **Recommendations** for remediation

## Important Notes

- Live capture requires root/sudo privileges
- Requires network access to specified interface
- PCAP analysis does not require elevated privileges
- Detection rules can be customized in config file
- Supports standard PCAP format from tcpdump, Wireshark, etc.
