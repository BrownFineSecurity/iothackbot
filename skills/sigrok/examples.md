# Sigrok Capture Analysis Examples

## Example 1: Unknown Protocol Analysis

**Scenario**: You have a captured signal from an unknown IoT device and need to identify the protocol.

### Step 1: Check the file

```bash
python3 skills/sigrok/analyze_capture.py capture.sr --show
```

Output:
```
File: capture.sr
Channels: D0, D1, D2, D3
Sample rate: 24.0 MHz
Total samples: 2400000
Duration: 0.100s
```

### Step 2: Get an overview

```bash
python3 skills/sigrok/analyze_capture.py capture.sr
```

This shows basic timing statistics and automatic protocol guesses.

### Step 3: Look at timing distribution

```bash
python3 skills/sigrok/analyze_capture.py capture.sr --histogram --clusters
```

Look for distinct timing clusters — these help identify the protocol:
- **2-3 clusters** → likely UART or 1-Wire
- **Very regular clusters** → likely SPI or I2C (clock-based)
- **Wide spread** → likely analog or mixed protocol

### Step 4: Try the suggested decoder

```bash
# If UART was guessed at 115200 baud
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=115200
```

### Step 5: Export for further analysis

```bash
python3 skills/sigrok/analyze_capture.py capture.sr --export transitions.csv
```

---

## Example 2: UART Signal Decoding

**Scenario**: You captured UART communication from an IoT device's debug port.

### Identify UART characteristics

```bash
python3 skills/sigrok/analyze_capture.py uart_capture.sr --clusters
```

Look for:
- Signal idles HIGH
- Consistent bit period clusters
- Durations are multiples of the base bit period

### Decode at a specific baud rate

```bash
# Standard 115200 baud
python3 skills/sigrok/analyze_capture.py uart_capture.sr \
    --decode uart:baudrate=115200

# With channel mapping (TX on D0, RX on D1)
python3 skills/sigrok/analyze_capture.py uart_capture.sr \
    --decode uart:baudrate=115200:tx=D0:rx=D1
```

### Extract only the transmitted data

```bash
# Text annotations
python3 skills/sigrok/analyze_capture.py uart_capture.sr \
    --decode uart:baudrate=115200 \
    --annotations uart=tx-data

# Raw binary output
python3 skills/sigrok/analyze_capture.py uart_capture.sr \
    --decode uart:baudrate=115200 \
    --binary-decode uart=tx \
    --binary-out uart_tx.bin

# Inspect the binary
xxd uart_tx.bin | head -20
```

### Custom baud rate detection

If standard rates don't work, use timing analysis to find the baud rate:

```bash
python3 skills/sigrok/analyze_capture.py uart_capture.sr --clusters --raw -n 30
```

The smallest timing cluster represents the bit period. Calculate:
```
baud_rate = 1,000,000 / cluster_us
```

For example, if the smallest cluster is ~8.7us: `1000000 / 8.7 = 114943` → try 115200 baud.

---

## Example 3: SPI Analysis with Stacked Decoders

**Scenario**: Multi-channel SPI capture with clock and data lines.

### Identify SPI signals

First check which channels are present:
```bash
python3 skills/sigrok/analyze_capture.py spi_capture.sr --show
```

Analyze each channel to identify clock vs data:
```bash
# Check D0 (likely CLK - should be very regular)
python3 skills/sigrok/analyze_capture.py spi_capture.sr --channel D0 --clusters

# Check D1 (MOSI - data, less regular)
python3 skills/sigrok/analyze_capture.py spi_capture.sr --channel D1 --clusters
```

The channel with the most regular timing is the clock (SCLK).

### Decode SPI

```bash
# Basic SPI decode with channel mapping
python3 skills/sigrok/analyze_capture.py spi_capture.sr \
    --decode spi:clk=D0:mosi=D1:miso=D2:cs=D3

# With clock polarity/phase options
python3 skills/sigrok/analyze_capture.py spi_capture.sr \
    --decode spi:clk=D0:mosi=D1:miso=D2:cs=D3:cpol=0:cpha=0
```

### Stacked decoder: SPI Flash

```bash
# Decode SPI flash commands (read, write, erase)
python3 skills/sigrok/analyze_capture.py spi_capture.sr \
    --decode spi:clk=D0:mosi=D1:miso=D2:cs=D3,spiflash

# Show only flash data
python3 skills/sigrok/analyze_capture.py spi_capture.sr \
    --decode spi:clk=D0:mosi=D1:miso=D2:cs=D3,spiflash \
    --annotations spiflash
```

---

## Example 4: I2C Address Discovery

**Scenario**: Captured I2C communication and need to find device addresses.

### Decode I2C

```bash
# Basic I2C decode (SCL on D0, SDA on D1)
python3 skills/sigrok/analyze_capture.py i2c_capture.sr \
    --decode i2c:scl=D0:sda=D1
```

Output shows START, address, R/W, data bytes, ACK/NACK, STOP.

### Stacked decoder: EEPROM

```bash
# Decode I2C EEPROM read/write operations
python3 skills/sigrok/analyze_capture.py i2c_capture.sr \
    --decode i2c:scl=D0:sda=D1,eeprom24xx

# Show only EEPROM data
python3 skills/sigrok/analyze_capture.py i2c_capture.sr \
    --decode i2c:scl=D0:sda=D1,eeprom24xx \
    --annotations eeprom24xx
```

### Other I2C stacked decoders

```bash
# Temperature sensor (LM75)
--decode i2c:scl=D0:sda=D1,lm75

# Real-time clock (DS1307)
--decode i2c:scl=D0:sda=D1,ds1307

# Accelerometer (ADXL345)
--decode i2c:scl=D0:sda=D1,adxl345
```

---

## Example 5: CAN Bus Analysis

**Scenario**: Captured CAN bus traffic from a vehicle or industrial device.

### Decode CAN frames

```bash
# CAN at 500kbps
python3 skills/sigrok/analyze_capture.py can_capture.sr \
    --decode can:bitrate=500000

# CAN at 250kbps
python3 skills/sigrok/analyze_capture.py can_capture.sr \
    --decode can:bitrate=250000
```

### Timing analysis for bitrate detection

```bash
python3 skills/sigrok/analyze_capture.py can_capture.sr --clusters
```

The smallest cluster corresponds to the bit period:
- 2.0us → 500kbps
- 4.0us → 250kbps
- 8.0us → 125kbps
- 1.0us → 1Mbps

---

## Example 6: JTAG Tap Detection

**Scenario**: JTAG pins identified on a PCB, need to analyze the communication.

### Decode JTAG

```bash
# Basic JTAG decode
python3 skills/sigrok/analyze_capture.py jtag_capture.sr \
    --decode jtag:tck=D0:tms=D1:tdi=D2:tdo=D3

# STM32-specific JTAG
python3 skills/sigrok/analyze_capture.py jtag_capture.sr \
    --decode jtag:tck=D0:tms=D1:tdi=D2:tdo=D3,jtag_stm32
```

### SWD (Serial Wire Debug) — alternative to JTAG

```bash
# SWD decode (ARM Cortex-M)
python3 skills/sigrok/analyze_capture.py swd_capture.sr \
    --decode swd:swclk=D0:swdio=D1
```

---

## Example 7: Working with Different File Formats

### Sigrok session files (.sr)

Created by PulseView or sigrok-cli capture:
```bash
python3 skills/sigrok/analyze_capture.py capture.sr
python3 skills/sigrok/analyze_capture.py capture.sr --decode uart:baudrate=9600
```

### CSV files

Exported from logic analyzers or other tools:
```bash
# Sigrok-format CSV (Time [s],D0,D1,...)
python3 skills/sigrok/analyze_capture.py export.csv

# Analyze specific channel
python3 skills/sigrok/analyze_capture.py export.csv --channel D2
```

### VCD files (Value Change Dump)

Common output from simulators and some logic analyzers:
```bash
python3 skills/sigrok/analyze_capture.py waveform.vcd
python3 skills/sigrok/analyze_capture.py waveform.vcd --channel CLK
```

---

## Example 8: Combined Timing + Decoding Workflow

**Scenario**: Full analysis workflow from unknown capture to decoded data.

```bash
# Step 1: Overview
python3 skills/sigrok/analyze_capture.py mystery.sr --show

# Step 2: Timing analysis on each channel
python3 skills/sigrok/analyze_capture.py mystery.sr --channel D0 --clusters
python3 skills/sigrok/analyze_capture.py mystery.sr --channel D1 --clusters

# Step 3: Decode based on findings
python3 skills/sigrok/analyze_capture.py mystery.sr \
    --decode uart:baudrate=115200:tx=D0

# Step 4: Extract the data
python3 skills/sigrok/analyze_capture.py mystery.sr \
    --decode uart:baudrate=115200:tx=D0 \
    --binary-decode uart=tx \
    --binary-out decoded.bin

# Step 5: Analyze decoded data
xxd decoded.bin
strings decoded.bin
```

---

## Useful sigrok-cli Direct Commands

For advanced scenarios beyond the helper script:

```bash
# List all supported protocol decoders with details
sigrok-cli -L

# Show decoder options
sigrok-cli -P uart --show

# Decode with multiple independent decoder stacks
sigrok-cli -i capture.sr -P uart:tx=D0:baudrate=115200 -P spi:clk=D2:mosi=D3

# Export to different formats
sigrok-cli -i capture.sr -O csv > data.csv
sigrok-cli -i capture.sr -O vcd > data.vcd
sigrok-cli -i capture.sr -O bits > data.txt

# Continuous sampling to file
sigrok-cli -d fx2lafw --config samplerate=1m --samples 1m -o capture.sr
```
