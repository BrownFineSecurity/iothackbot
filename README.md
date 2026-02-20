# IoTHackBot

Open-source IoT security testing toolkit with integrated Claude Code skills for automated vulnerability discovery.

## Overview

IoTHackBot is a collection of specialized tools and Claude Code skills designed for security testing of IoT devices, IP cameras, and embedded systems. It provides both command-line tools and AI-assisted workflows for comprehensive IoT security assessments.

## Tools Included

### Network Discovery & Reconnaissance

- **wsdiscovery** - WS-Discovery protocol scanner for discovering ONVIF cameras and IoT devices
- **iotnet** - IoT network traffic analyzer for detecting protocols and vulnerabilities
- **netflows** - Network flow extractor with DNS hostname resolution from pcap files
- **nmap** (skill) - Professional network reconnaissance with two-phase scanning strategy

### Device-Specific Testing

- **onvifscan** - ONVIF device security scanner
  - Authentication bypass testing
  - Credential brute-forcing

### Firmware & File Analysis

- **chipsec** (skill) - UEFI/BIOS firmware static analysis
  - Detect known rootkits (LoJax, ThinkPwn, HackingTeam)
  - Generate EFI executable inventories with hashes
  - Decode firmware structure and extract NVRAM

- **ffind** - Advanced file finder with type detection and filesystem extraction
  - Identifies artifact file types
  - Extracts ext2/3/4 and F2FS filesystems
  - Designed for firmware analysis

### Android Analysis

- **apktool** (skill) - APK unpacking and resource extraction
  - Decode AndroidManifest.xml
  - Extract resources, layouts, strings
  - Disassemble to smali code

- **jadx** (skill) - APK decompilation
  - Convert DEX to readable Java source
  - Search for hardcoded credentials
  - Analyze app logic

### Hardware & Console Access

- **picocom** (skill) - IoT UART console interaction for hardware testing
  - Bootloader manipulation
  - Shell enumeration
  - Firmware extraction
  - Includes Python helper script for automated interaction

- **telnetshell** (skill) - IoT telnet shell interaction
  - Unauthenticated shell testing
  - Device enumeration
  - BusyBox command handling
  - Includes Python helper script and pre-built enumeration scripts

### Logic Analyzer & Signal Analysis

- **sigrok** (skill) - Analyze logic analyzer captures using sigrok-cli and 131+ protocol decoders
  - Native .sr file parsing (no sigrok-cli needed for timing analysis)
  - Supports .sr, .csv, and .vcd formats
  - Decode UART, SPI, I2C, CAN, JTAG, USB, 1-Wire, and many more
  - Timing analysis with histograms, cluster detection, and protocol guessing
  - Binary data extraction from decoded protocols

- **logicmso** (skill) - Analyze captures from Saleae Logic MSO devices
  - Decode protocols (UART, SPI, I2C) from exported binary files
  - Digital and analog capture analysis
  - Hardware reverse engineering and CTF challenges

- **urh** (skill) - RF signal analysis and protocol decoding using Universal Radio Hacker
  - Supports OOK, ASK, FSK, and PSK modulations
  - Loads .complex/.cfile (float32), .complex16s, .complex16u, and .wav IQ formats
  - Native IQ loading with numpy — spectrum, energy, and OOK demodulation without URH installed
  - Protocol decoding via urh_cli with automatic modulation detection
  - Covers 433MHz/315MHz remotes, Z-Wave, Zigbee, and arbitrary RF protocols
  - Recording via URH GUI with any compatible SDR (RTL-SDR, HackRF, USRP, etc.)

## Installation

### Prerequisites

```bash
# Python dependencies
pip install colorama pyserial pexpect requests

# System dependencies (Arch Linux)
sudo pacman -S nmap e2fsprogs f2fs-tools python python-pip inetutils

# For other distributions, install equivalent packages
```

### Setup

1. Clone the repository:
```bash
git clone https://github.com/BrownFineSecurity/iothackbot.git
cd iothackbot
```

2. Add the bin directory to your PATH:
```bash
export PATH="$PATH:$(pwd)/bin"
```

3. For permanent setup, add to your shell configuration:
```bash
echo 'export PATH="$PATH:/path/to/iothackbot/bin"' >> ~/.bashrc
```

## Usage

### Quick Start Examples

#### Discover ONVIF Devices
```bash
wsdiscovery 192.168.1.0/24
```

#### Test ONVIF Device Security
```bash
onvifscan auth http://192.168.1.100
onvifscan brute http://192.168.1.100
```

#### Analyze Network Traffic
```bash
# Analyze PCAP file for IoT protocols
iotnet capture.pcap

# Live capture
sudo iotnet -i eth0 -d 60
```

#### Extract Network Flows
```bash
# Extract flows from device with DNS resolution
netflows capture.pcap --source-ip 192.168.1.100

# Get just hostname:port list
netflows capture.pcap -s 192.168.1.100 --format quiet
```

#### Analyze Logic Analyzer Captures
```bash
# Timing analysis of a sigrok capture (no sigrok-cli needed)
python3 skills/sigrok/analyze_capture.py capture.sr --histogram --clusters

# Decode UART protocol (requires sigrok-cli)
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200

# Analyze a specific channel
python3 skills/sigrok/analyze_capture.py capture.sr --channel D2 --raw
```

#### Analyze RF Signals
```bash
# Signal overview and modulation hint
python3 skills/urh/analyze_signal.py signal.complex -s 2000000

# Inspect power spectrum
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --spectrum

# Demodulate OOK and show pulse timing clusters (e.g. 433MHz remote)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --clusters

# Full protocol decoding via urh_cli
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --decode --modulation OOK
```

#### Analyze Firmware
```bash
# Identify file types
ffind firmware.bin

# Extract filesystems (requires sudo)
sudo ffind firmware.bin -e
```

### Claude Code Plugin

IoTHackBot is available as a Claude Code plugin, providing AI-assisted security testing with specialized skills.

#### Available Skills

| Skill | Description |
|-------|-------------|
| **chipsec** | UEFI/BIOS firmware static analysis - malware detection, EFI inventory |
| **apktool** | Android APK unpacking and resource extraction |
| **jadx** | Android APK decompilation to Java source |
| **ffind** | Firmware file analysis with filesystem extraction |
| **iotnet** | IoT network traffic analysis |
| **netflows** | Network flow extraction with DNS hostname resolution |
| **nmap** | Professional network reconnaissance |
| **onvifscan** | ONVIF device security testing |
| **logicmso** | Saleae Logic MSO capture analysis and protocol decoding |
| **picocom** | UART console interaction |
| **sigrok** | Logic analyzer capture analysis with 131+ protocol decoders |
| **urh** | RF signal analysis — OOK/FSK/ASK/PSK demodulation and protocol decoding |
| **telnetshell** | Telnet shell enumeration |
| **wsdiscovery** | WS-Discovery device discovery |

#### Plugin Installation

**Option 1: Use directly during development**

```bash
claude --plugin-dir /path/to/iothackbot
```

**Option 2: Install as local marketplace (persistent)**

Add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "iothackbot-local": {
      "source": {
        "source": "directory",
        "path": "/path/to/iothackbot"
      }
    }
  },
  "enabledPlugins": {
    "iothackbot": true
  }
}
```

Then restart Claude Code for the settings to take effect.

**Option 3: Project-specific setup**

For use within a specific project, the skills are also available via the `.claude/skills/` symlink for backwards compatibility.

## Tool Architecture

All tools follow a consistent design pattern:

- **CLI Layer** (`tools/iothackbot/*.py`) - Command-line interface with argparse
- **Core Layer** (`tools/iothackbot/core/*_core.py`) - Core functionality implementing ToolInterface
- **Binary** (`bin/*`) - Executable wrapper scripts

This separation enables:
- Easy automation and chaining
- Consistent output formats (text, JSON, quiet)
- Standardized error handling
- Tool composition and pipelines

## Configuration

### IoT Detection Rules
`config/iot/detection_rules.json` - Custom IoT protocol detection rules for iotnet

### Wordlists
- `wordlists/onvif-usernames.txt` - Default usernames for ONVIF devices
- `wordlists/onvif-passwords.txt` - Default passwords for ONVIF devices

## Development

### Adding New Tools

See `TOOL_DEVELOPMENT_GUIDE.md` for detailed information on:
- Project structure standards
- Development patterns
- Output formatting guidelines
- Testing and integration

### Key Interfaces

- **ToolInterface** - Base interface for all tools
- **ToolConfig** - Standardized configuration object
- **ToolResult** - Standardized result object with success, data, errors, and metadata

## Output Formats

All tools support multiple output formats:

```bash
# Human-readable text with colors (default)
onvifscan auth 192.168.1.100

# Machine-readable JSON
onvifscan auth 192.168.1.100 --format json

# Minimal output
onvifscan auth 192.168.1.100 --format quiet
```

## Security & Ethics

**IMPORTANT**: These tools are designed for authorized security testing only.

- Only test devices you own or have explicit permission to test
- Respect scope limitations and rules of engagement
- Be aware of the impact on production systems
- Use appropriate timing to avoid denial of service
- Document all testing activities
- Follow responsible disclosure practices

## Contributing

Contributions are welcome! Please ensure:

- New tools follow the architecture patterns in `TOOL_DEVELOPMENT_GUIDE.md`
- All tools support text, JSON, and quiet output formats
- Code includes proper error handling
- Documentation is clear and comprehensive

## License

MIT License - See LICENSE file for details

## Disclaimer

This toolkit is provided for educational and authorized security testing purposes only. Users are responsible for ensuring they have proper authorization before testing any systems. The authors are not responsible for misuse or damage caused by this toolkit.
