---
name: logicmso
description: Analyze digital and analog captures from Saleae Logic MSO devices. Decode protocols like UART, SPI, I2C from exported binary files. Use when analyzing logic analyzer captures for CTF challenges, hardware reverse engineering, or protocol decoding.
---

# Saleae Logic MSO Analysis

This skill enables analysis of captured signals from Saleae Logic MSO devices using the `saleae-mso-api` Python library. It supports loading binary exports, analyzing signal transitions, and decoding common protocols.

## Prerequisites

- `saleae-mso-api` Python package — **Do NOT blindly pip install.** First check if it's already installed:
  ```bash
  python3 -c "from saleae.mso_api.binary_files import read_file; print('saleae-mso-api is available')"
  ```
  Only if that fails, install it: `pip install saleae-mso-api`
- Binary export files from Saleae Logic software (`.bin` format)

## Quick Reference

### Loading Binary Files

```python
from saleae.mso_api.binary_files import read_file
from pathlib import Path

file_path = Path("capture.bin")
saleae_file = read_file(file_path)

# Access metadata
print(f"Version: {saleae_file.version}")
print(f"Type: {saleae_file.type}")

# Access data
contents = saleae_file.contents
```

### Digital Capture Structure

Digital exports contain `DigitalExport_V1` with chunks:

```python
chunk = saleae_file.contents.chunks[0]

# Key attributes:
chunk.initial_state      # Starting logic level (0 or 1)
chunk.transition_times   # numpy array of transition timestamps (seconds)
chunk.sample_rate        # Capture rate in Hz
chunk.begin_time         # Capture start time
chunk.end_time           # Capture end time
```

### Calculating Pulse Durations

```python
import numpy as np

times = np.array(chunk.transition_times)
durations_ms = np.diff(times) * 1000  # Convert to milliseconds

# If initial_state is 0 (LOW):
#   - Even indices (0, 2, 4...) = HIGH pulse durations
#   - Odd indices (1, 3, 5...) = LOW gap durations
# If initial_state is 1 (HIGH):
#   - Even indices = LOW gap durations
#   - Odd indices = HIGH pulse durations
```

## Helper Scripts

This skill includes helper scripts for common analysis tasks:

### Protocol Analyzer

```bash
# Analyze signal characteristics
python3 skills/logicmso/analyze_protocol.py capture.bin

# Show detailed timing histogram
python3 skills/logicmso/analyze_protocol.py capture.bin --histogram

# Show detected timing clusters
python3 skills/logicmso/analyze_protocol.py capture.bin --clusters

# Export transitions to CSV
python3 skills/logicmso/analyze_protocol.py capture.bin --export transitions.csv

# Show raw transition values
python3 skills/logicmso/analyze_protocol.py capture.bin --raw -n 50
```

## Common Protocol Patterns

### UART (Asynchronous Serial)
- **Idle state**: HIGH
- **Start bit**: LOW (1 bit period)
- **Data bits**: 8 bits, LSB first
- **Stop bit**: HIGH (1-2 bit periods)
- **Common baud rates**: 9600, 19200, 38400, 57600, 115200
- **Bit period calculation**: `1/baud_rate` seconds
- **Identifying features**: Consistent bit periods, durations are multiples of base period

### SPI (Serial Peripheral Interface)
- **4 signals**: SCLK (clock), MOSI (master out), MISO (master in), CS (chip select)
- **Clock polarity (CPOL)**: Idle clock state (0=LOW, 1=HIGH)
- **Clock phase (CPHA)**: Sample edge (0=leading, 1=trailing)
- **Data**: Sampled on clock edges, typically 8 bits per transaction
- **Identifying features**: Regular clock signal, CS goes LOW during transaction

### I2C (Inter-Integrated Circuit)
- **2 signals**: SDA (data), SCL (clock)
- **Idle state**: Both HIGH (pulled up)
- **Start condition**: SDA falls while SCL is HIGH
- **Stop condition**: SDA rises while SCL is HIGH
- **Data**: 8 bits + ACK/NACK, MSB first
- **Address**: 7-bit (first byte after START)
- **Identifying features**: START/STOP conditions, 9 clock pulses per byte (8 data + ACK)

### 1-Wire
- **Single signal**: DQ (data/power)
- **Idle state**: HIGH (pulled up)
- **Reset pulse**: Master pulls LOW for 480us minimum
- **Presence pulse**: Slave responds LOW for 60-240us
- **Write 0**: LOW for 60-120us
- **Write 1**: LOW for 1-15us, then release
- **Read**: Master samples 15us after pulling LOW

## Analysis Workflow

### Step 1: Initial Exploration
```python
from saleae.mso_api.binary_files import read_file
import numpy as np

f = read_file("capture.bin")
chunk = f.contents.chunks[0]

print(f"Sample rate: {chunk.sample_rate/1e6:.1f} MHz")
print(f"Duration: {chunk.end_time - chunk.begin_time:.3f}s")
print(f"Initial state: {'HIGH' if chunk.initial_state else 'LOW'}")
print(f"Transitions: {len(chunk.transition_times)}")
```

### Step 2: Analyze Timing Patterns
```python
times = np.array(chunk.transition_times)
durations_us = np.diff(times) * 1e6  # microseconds

# Separate HIGH and LOW durations
high_idx = 0 if chunk.initial_state == 0 else 1
high_durations = durations_us[high_idx::2]
low_durations = durations_us[(1-high_idx)::2]

print(f"HIGH pulses: min={min(high_durations):.1f}us, max={max(high_durations):.1f}us")
print(f"LOW gaps: min={min(low_durations):.1f}us, max={max(low_durations):.1f}us")

# Find unique timing values (cluster detection)
unique_high = sorted(set(round(d, -1) for d in high_durations))  # Round to 10us
unique_low = sorted(set(round(d, -1) for d in low_durations))
print(f"HIGH clusters: {unique_high}")
print(f"LOW clusters: {unique_low}")
```

### Step 3: Identify Protocol
Based on timing patterns:
- **UART**: Consistent bit periods, durations are multiples of base period, idles HIGH
- **SPI/I2C**: us-scale timing, needs clock signal analysis, look for regular patterns
- **1-Wire**: Reset pulses ~480us, data pulses 1-120us

### Step 4: Decode
Once protocol is identified, decode based on protocol rules. For unknown/custom protocols, analyze the timing clusters and bit patterns to determine encoding scheme.

## UART Decoding Example

```python
from saleae.mso_api.binary_files import read_file
import numpy as np

f = read_file("uart_capture.bin")
chunk = f.contents.chunks[0]
times = np.array(chunk.transition_times)

BAUD = 115200
BIT_PERIOD = 1 / BAUD

def decode_uart_byte(start_time, times, bit_period):
    """Decode a single UART byte starting at start_time."""
    byte_val = 0
    for bit_num in range(8):
        # Sample at center of each bit (1.5, 2.5, 3.5... bit periods from start)
        sample_time = start_time + (1.5 + bit_num) * bit_period
        # Find state at sample_time
        idx = np.searchsorted(times, sample_time)
        state = (chunk.initial_state + idx) % 2
        if state:
            byte_val |= (1 << bit_num)  # LSB first
    return byte_val

# Find start bits (falling edges when idle HIGH)
decoded_bytes = []
i = 0
while i < len(times) - 1:
    # Look for falling edge (start bit)
    if chunk.initial_state == 1 or i > 0:
        byte_val = decode_uart_byte(times[i], times, BIT_PERIOD)
        decoded_bytes.append(byte_val)
        # Skip to next potential start bit (after stop bit)
        i += 1
        while i < len(times) and times[i] < times[i-1] + 10 * BIT_PERIOD:
            i += 1
    else:
        i += 1

print("Decoded:", bytes(decoded_bytes))
```

## CTF Tips

1. **Unknown protocol**: Start with `analyze_protocol.py --clusters` to see timing distribution
2. **Multiple channels**: Export each channel separately, identify clock vs data lines
3. **Inverted signals**: Some captures have inverted logic levels
4. **Timing variations**: Real hardware has jitter, use threshold-based detection
5. **Partial captures**: Check if capture starts mid-transmission
6. **Custom protocols**: Look for repeating patterns, identify sync/framing bytes

## Troubleshooting

### "No module named 'saleae.mso_api'"
First verify it's truly missing:
```bash
python3 -c "from saleae.mso_api.binary_files import read_file"
```
Only if the import fails, install it:
```bash
pip install saleae-mso-api
```

### Empty or corrupt file
Check file size and try re-exporting from Saleae Logic software.

### No transitions detected
- Signal may be constant (stuck high/low)
- Check if correct channel was exported
- Verify trigger settings in original capture

### Timing seems wrong
- Check sample rate matches original capture settings
- Verify time units (seconds vs milliseconds vs microseconds)
