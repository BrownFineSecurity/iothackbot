# IoTHackBot

Open-source IoT security testing toolkit with integrated Claude Code skills for automated vulnerability discovery.

## Overview

IoTHackBot is a collection of specialized tools and Claude Code skills designed for security testing of IoT devices, IP cameras, and embedded systems. It provides both command-line tools and AI-assisted workflows for comprehensive IoT security assessments.

## Tools Included

### Network Discovery & Reconnaissance

- **wsdiscovery** - WS-Discovery protocol scanner for discovering ONVIF cameras and IoT devices
- **iotnet** - IoT network traffic analyzer for detecting protocols and vulnerabilities
- **nmap-scan** (skill) - Professional network reconnaissance with two-phase scanning strategy

### Device-Specific Testing

- **onvifscan** - ONVIF device security scanner
  - Authentication bypass testing
  - Credential brute-forcing

### Firmware & File Analysis

- **ffind** - Advanced file finder with type detection and filesystem extraction
  - Identifies artifact file types
  - Extracts ext2/3/4 and F2FS filesystems
  - Designed for firmware analysis

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

## Installation

### Prerequisites

#### Python Dependencies

**Option 1: Using uv (recommended)**
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies in a virtual environment
uv sync
```

**Option 2: Using pip**
```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install colorama pyserial pexpect requests
```

#### System Dependencies

**Arch Linux:**
```bash
sudo pacman -S nmap e2fsprogs f2fs-tools python inetutils
```

**Ubuntu/Debian:**
```bash
sudo apt install nmap e2fsprogs f2fs-tools python3 inetutils-telnet
```

**macOS:**
```bash
brew install nmap e2fsprogs f2fs-tools
```

### Setup

1. Clone the repository:
```bash
git clone https://github.com/BrownFineSecurity/iothackbot.git
cd iothackbot
```

2. Install Python dependencies (see above)

3. **Using uv (recommended)**: The tools are automatically available via entry points after `uv sync`:
```bash
# Tools are available via uv run
uv run wsdiscovery 192.168.1.0/24
uv run ffind firmware.bin
uv run onvifscan auth http://192.168.1.100
uv run iotnet capture.pcap

# Or activate the venv to use them directly
source .venv/bin/activate
wsdiscovery 192.168.1.0/24
ffind firmware.bin
```

4. **Using bin/ directory**: Alternatively, add the bin directory to your PATH:
```bash
export PATH="$PATH:$(pwd)/bin"
```

For permanent setup, add to your shell configuration:
```bash
echo 'export PATH="$PATH:/path/to/iothackbot/bin"' >> ~/.bashrc
```

## Usage

**Note:** All examples below assume you've either:
- Activated the uv virtual environment (`source .venv/bin/activate`), OR
- Are using `uv run` prefix (e.g., `uv run wsdiscovery 192.168.1.0/24`), OR
- Added `bin/` to your PATH

### Quick Start Examples

#### Discover ONVIF Devices
```bash
wsdiscovery 192.168.1.0/24
# Or: uv run wsdiscovery 192.168.1.0/24
```

#### Test ONVIF Device Security
```bash
onvifscan auth http://192.168.1.100
onvifscan brute http://192.168.1.100
```

#### Analyze Network Traffic
```bash
# Analyze PCAP file
iotnet capture.pcap

# Live capture
sudo iotnet -i eth0 -d 60
```

#### Analyze Firmware
```bash
# Identify file types
ffind firmware.bin

# Extract filesystems (requires sudo)
sudo ffind firmware.bin -e
```

### Claude Code Skills

IoTHackBot includes specialized skills for Claude Code that provide guided, interactive security testing:

- **ffind** - Firmware file analysis with extraction
- **iotnet** - Network traffic analysis
- **nmap-scan** - Professional network reconnaissance
- **onvifscan** - ONVIF device security testing
- **picocom** - UART console interaction
- **telnetshell** - Telnet shell enumeration
- **wsdiscovery** - WS-Discovery device discovery

To use these skills with Claude Code, they are automatically available in the `.claude/skills/` directory.

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
