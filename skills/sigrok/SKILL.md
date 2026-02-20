---
name: sigrok
description: Analyze logic analyzer captures (.sr, CSV, VCD) using sigrok-cli and 131+ protocol decoders. Decode UART, SPI, I2C, CAN, JTAG, USB, 1-Wire, and many more protocols from any sigrok-compatible hardware. Use for CTF challenges, hardware reverse engineering, and protocol decoding.
---

# Sigrok Capture Analysis

This skill enables analysis of captured digital signals from any sigrok-compatible logic analyzer. It wraps `sigrok-cli` for protocol decoding (131+ decoders) and provides custom timing analysis, cluster detection, and protocol identification.

Sigrok supports 258+ devices from 58 vendors, including Saleae Logic clones, DSLogic, Kingst LA series, fx2lafw-based analyzers, and many more.

## Prerequisites

- `sigrok-cli` installed — **Do NOT blindly install.** First check if it's available:
  ```bash
  sigrok-cli --version
  ```
  Only if that fails, install it:
  - Arch Linux: `sudo pacman -S sigrok-cli`
  - Ubuntu/Debian: `sudo apt install sigrok-cli`
  - Fedora: `sudo dnf install sigrok-cli`
  - macOS: `brew install sigrok-cli`
  - Windows: Download from https://sigrok.org/wiki/Downloads
    - If you get a missing DLL error: `winget install --id=Microsoft.VCRedist.2010.x64`

- `numpy` Python package (for timing analysis):
  ```bash
  python3 -c "import numpy; print('numpy available')"
  ```
  Only if that fails: `pip install numpy`

## Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Sigrok session | `.sr` | Native PulseView/sigrok session files |
| CSV | `.csv` | Comma-separated values (sigrok or generic) |
| VCD | `.vcd` | Value Change Dump (standard digital waveform format) |

All formats are auto-detected by file extension.

## Quick Reference

### File Information

```bash
# Show capture metadata (channels, sample rate, duration)
python3 skills/sigrok/analyze_capture.py capture.sr --show
```

### Timing Analysis

```bash
# Basic timing analysis with protocol guessing
python3 skills/sigrok/analyze_capture.py capture.sr

# Show detailed timing histogram
python3 skills/sigrok/analyze_capture.py capture.sr --histogram

# Show detected timing clusters
python3 skills/sigrok/analyze_capture.py capture.sr --clusters

# Analyze a specific channel
python3 skills/sigrok/analyze_capture.py capture.sr --channel D2

# Show raw transition values
python3 skills/sigrok/analyze_capture.py capture.sr --raw -n 50

# Export transitions to CSV
python3 skills/sigrok/analyze_capture.py capture.sr --export transitions.csv
```

### Protocol Decoding

```bash
# Decode UART at 115200 baud
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200

# Decode with annotation filtering (show only TX data)
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200 --annotations uart=tx-data

# Decode SPI
python3 skills/sigrok/analyze_capture.py capture.sr --decode spi:cpol=0:cpha=0

# Stacked decoders (I2C + EEPROM)
python3 skills/sigrok/analyze_capture.py capture.sr --decode i2c,eeprom24xx

# CAN bus decoding
python3 skills/sigrok/analyze_capture.py capture.sr --decode can:bitrate=500000

# Extract binary data from decoder
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200 --binary-decode uart=tx --binary-out data.bin

# List all available decoders
python3 skills/sigrok/analyze_capture.py --list-decoders

# Include sample numbers in output
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200 --samplenum
```

### Direct sigrok-cli Usage

For advanced use cases, invoke sigrok-cli directly:

```bash
# Export .sr to CSV
sigrok-cli -i capture.sr -O csv > capture.csv

# Decode with full output
sigrok-cli -i capture.sr -P uart:baudrate=115200

# Stacked decoders with annotation filter
sigrok-cli -i capture.sr -P i2c,eeprom24xx -A eeprom24xx

# Binary output (raw decoded bytes)
sigrok-cli -i capture.sr -P uart:baudrate=115200 -B uart=tx > uart_data.bin

# Show file details
sigrok-cli -i capture.sr --show

# List all decoders with details
sigrok-cli -L
```

## Common Protocol Patterns

### UART (Asynchronous Serial)
- **Idle state**: HIGH
- **Start bit**: LOW (1 bit period)
- **Data bits**: 8 bits, LSB first
- **Stop bit**: HIGH (1-2 bit periods)
- **Common baud rates**: 9600, 19200, 38400, 57600, 115200
- **Bit period calculation**: `1/baud_rate` seconds
- **Decoder**: `uart:baudrate=115200` (adjust baud rate)
- **Channel mapping**: `uart:baudrate=115200:tx=D0:rx=D1`

### SPI (Serial Peripheral Interface)
- **4 signals**: SCLK (clock), MOSI (master out), MISO (master in), CS (chip select)
- **Clock polarity (CPOL)**: Idle clock state (0=LOW, 1=HIGH)
- **Clock phase (CPHA)**: Sample edge (0=leading, 1=trailing)
- **Data**: Sampled on clock edges, typically 8 bits per transaction
- **Decoder**: `spi:cpol=0:cpha=0:clk=D0:mosi=D1:miso=D2:cs=D3`

### I2C (Inter-Integrated Circuit)
- **2 signals**: SDA (data), SCL (clock)
- **Idle state**: Both HIGH (pulled up)
- **Start condition**: SDA falls while SCL is HIGH
- **Stop condition**: SDA rises while SCL is HIGH
- **Data**: 8 bits + ACK/NACK, MSB first
- **Address**: 7-bit (first byte after START)
- **Decoder**: `i2c:scl=D0:sda=D1`
- **Stacked**: `i2c,eeprom24xx` to decode EEPROM commands

### CAN (Controller Area Network)
- **Single differential bus**: CANH/CANL (or single-ended capture)
- **Common bitrates**: 125kbps, 250kbps, 500kbps, 1Mbps
- **Frame**: SOF, arbitration ID, control, data, CRC, ACK, EOF
- **Decoder**: `can:bitrate=500000`

### 1-Wire
- **Single signal**: DQ (data/power)
- **Idle state**: HIGH (pulled up)
- **Reset pulse**: Master pulls LOW for 480us minimum
- **Presence pulse**: Slave responds LOW for 60-240us
- **Write 0**: LOW for 60-120us
- **Write 1**: LOW for 1-15us, then release
- **Decoder**: `onewire_link` (link layer), `onewire_network` (network layer)

### JTAG
- **4-5 signals**: TCK, TMS, TDI, TDO, (TRST)
- **Decoder**: `jtag:tck=D0:tms=D1:tdi=D2:tdo=D3`
- **Stacked**: `jtag,jtag_stm32` for STM32-specific decoding

### USB
- **2 signals**: D+, D-
- **Decoder**: `usb_signalling:dp=D0:dm=D1`
- **Stacked**: `usb_signalling,usb_packet,usb_request` for full USB decode

## Analysis Workflow

### Step 1: Get File Overview
```bash
python3 skills/sigrok/analyze_capture.py capture.sr --show
```
Check channels, sample rate, and duration.

### Step 2: Run Timing Analysis
```bash
python3 skills/sigrok/analyze_capture.py capture.sr --clusters --histogram
```
Look at timing distributions to identify the protocol.

### Step 3: Try Protocol Decoders
Based on timing analysis, try appropriate decoders:
```bash
# If UART is guessed
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200

# If SPI-like timing
python3 skills/sigrok/analyze_capture.py capture.sr --decode spi:cpol=0:cpha=0

# If I2C-like timing
python3 skills/sigrok/analyze_capture.py capture.sr --decode i2c
```

### Step 4: Extract Data
```bash
# Get decoded text
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200 --annotations uart=tx-data

# Extract raw bytes
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200 --binary-decode uart=tx --binary-out decoded.bin

# Export timing data for external tools
python3 skills/sigrok/analyze_capture.py capture.sr --export timing.csv
```

## CTF Tips

1. **Unknown protocol**: Start with `--clusters --histogram` to see timing distribution
2. **Try the helper script first**: `python3 skills/sigrok/analyze_capture.py capture.sr` gives automatic protocol guesses
3. **Multiple channels**: Use `--show` to see available channels, then `--channel D2` to analyze each
4. **Stacked decoders**: Use `i2c,eeprom24xx` or `spi,spiflash` to decode higher-level protocols
5. **Inverted signals**: Some captures have inverted logic — check initial state
6. **Binary extraction**: Use `--binary-decode` to get raw bytes for further analysis with `xxd` or `binwalk`
7. **Custom baud rate**: If standard rates don't match, calculate from timing clusters: `baud = 1e6 / cluster_us`
8. **List decoders**: Run `--list-decoders` to see all 131+ available decoders

## Troubleshooting

### "sigrok-cli not found"
Verify installation:
```bash
sigrok-cli --version
```
Install if missing (see Prerequisites section above).

### Missing DLL error on Windows
sigrok-cli depends on the Visual C++ 2010 Redistributable. Install it with:
```bash
winget install --id=Microsoft.VCRedist.2010.x64
```

### "No transitions detected"
- Signal may be constant (stuck high/low)
- Check if the correct channel is selected with `--channel`
- Use `--show` to verify file has data

### Decoder produces no output
- Check channel mapping: `uart:baudrate=115200:tx=D0`
- Verify baud rate/bitrate matches the signal
- Try without annotation filter first
- Use `--samplenum` to verify decoder is processing samples

### Wrong timing values
- Check if file uses correct timescale (especially VCD files)
- Verify sample rate shown by `--show`
- For CSV files, ensure the time column is in seconds

### "Unsupported format"
- Supported: `.sr`, `.csv`, `.vcd`
- For Saleae `.bin` files, use the `logicmso` skill instead
- Convert other formats to CSV or VCD first
