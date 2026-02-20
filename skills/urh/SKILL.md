---
name: urh
description: Analyze and decode RF signals using Universal Radio Hacker (URH). Supports OOK, ASK, FSK, PSK modulations and common IoT RF protocols including 433MHz/315MHz remotes, Zigbee, Z-Wave, and more. Use for CTF RF challenges and IoT device RF analysis.
---

# Universal Radio Hacker (URH) RF Signal Analysis

This skill enables analysis and decoding of RF signal captures using Universal Radio Hacker (URH). It wraps `urh_cli` for command-line protocol analysis and provides a helper script for spectrum inspection, demodulation, and OOK/FSK signal decoding. URH supports OOK, ASK, FSK, and PSK modulations, making it the primary tool for reverse engineering 433MHz/315MHz remotes, Zigbee, Z-Wave, and arbitrary RF protocols in both CTF and IoT security contexts.

## Prerequisites

- `urh` Python package — **Do NOT blindly pip install.** First check if it's already installed:
  ```bash
  python3 -c "import urh; print('urh available')"
  ```
  Only if that fails, install it. URH requires Cython to build its C extensions, so install that first:
  ```bash
  pip install cython
  pip install urh
  ```

- **Windows standalone installer**: URH may also be installed as a standalone app at
  `C:\Program Files\Universal Radio Hacker\urh_cli.exe`.
  **Important limitation**: The standalone installer's `urh_cli.exe` only supports live SDR
  capture (`-rx`/`-tx`). It **cannot** analyze saved `.complex`/`.complex16s` files offline.
  For offline file analysis use either:
  - The URH GUI (`urh.exe`) — open the project file or drag-and-drop signal files
  - The pip-installed `urh` Python package with `analyze_signal.py` (this skill's helper)

- Verify CLI tool is accessible:
  ```bash
  urh_cli --version
  ```
  If `urh_cli` is not found but `urh` imports correctly, run it as a module:
  ```bash
  python3 -m urh.cli.urh_cli --version
  ```

- `numpy` Python package (for the helper script):
  ```bash
  python3 -c "import numpy; print('numpy available')"
  ```
  Only if that fails: `pip install numpy`

- **For recording with an SDR**: A compatible SDR device and its driver must be installed
  (e.g., RTL-SDR via `rtl-sdr`, HackRF via `hackrf`). URH detects these automatically at runtime.

## Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Complex float32 | `.complex`, `.cfile` | GNU Radio / URH native IQ, 32-bit float pairs |
| Complex int16 (signed) | `.complex16s` | 16-bit signed integer IQ pairs (e.g., HackRF) |
| Complex int16 (unsigned) | `.complex16u` | 16-bit unsigned integer IQ pairs (e.g., RTL-SDR raw) |
| WAV | `.wav` | Audio WAV — stereo channel as IQ (L=I, R=Q) |

All formats are auto-detected by file extension.

## Quick Reference

### Signal Inspection

```bash
# Show signal metadata and statistics (sample count, duration, amplitude stats)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000

# Show power spectrum (ASCII FFT) to identify modulation type
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --spectrum

# Show signal energy over time to identify packet boundaries
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --energy

# Show first N raw IQ samples
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --raw -n 20
```

### Demodulation and Pulse Analysis

```bash
# Demodulate as OOK (most common for 433MHz remotes)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook

# Demodulate as FSK (common for IoT sensors, Z-Wave)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate fsk

# OOK with custom amplitude threshold (0.0–1.0, default: auto)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --threshold 0.3

# Show timing clusters after OOK demodulation (pulse-width analysis)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --clusters

# Show pulse duration histogram after OOK demodulation
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --histogram

# Show raw demodulated pulse transitions (-n limits count)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --raw -n 50
```

### Protocol Decoding (urh_cli)

```bash
# Auto-analyze with urh_cli (detects modulation automatically)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --decode

# Specify modulation for urh_cli decoding
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --decode --modulation OOK
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --decode --modulation FSK
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --decode --modulation ASK
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --decode --modulation PSK
```

### Export

```bash
# Export IQ samples to CSV
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --export iq.csv

# Export OOK pulse transitions to CSV (like sigrok's --export)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --export pulses.csv
```

### Direct urh_cli Usage

```bash
# Auto-detect modulation and print decoded bits
urh_cli analyze -f signal.complex -s 2000000

# Specify modulation explicitly
urh_cli analyze -f signal.complex -s 2000000 --modulation OOK

# Analyze a WAV file
urh_cli analyze -f capture.wav -s 44100 --modulation OOK

# Launch the full URH graphical interface (for recording, visual inspection, protocol editor)
urh
```

## Recording RF Signals

URH recording is done through the **GUI** — launch it with:

```bash
urh
```

In the GUI:

1. Go to **File > Record Signal**
2. Select your SDR device (RTL-SDR, HackRF, USRP, LimeSDR, PlutoSDR, etc.)
3. Set the center frequency (e.g., 433.92 MHz for common remotes, 868 MHz for Z-Wave EU)
4. Set the sample rate (minimum 2× the signal bandwidth; 2 MSPS is a safe default for narrow-band IoT)
5. Set the gain (start around 20–30 dB for RTL-SDR)
6. Press **Record** and trigger the device under test
7. Save as `.complex` (URH native format) for subsequent analysis

### Recommended SDR Settings by Protocol

| Protocol | Frequency | Sample Rate | Notes |
|----------|-----------|-------------|-------|
| 433MHz remotes | 433.92 MHz | 2 MSPS | OOK, very common |
| 315MHz remotes | 315 MHz | 2 MSPS | OOK, North America |
| Z-Wave EU | 868.42 MHz | 2 MSPS | FSK, 9.6/40/100 kbps |
| Z-Wave US | 908.42 MHz | 2 MSPS | FSK |
| Zigbee | 2.405–2.480 GHz | 4+ MSPS | O-QPSK, needs HackRF/USRP |

## Common RF Protocol Patterns

### OOK (On-Off Keying)

The most common modulation for 433MHz and 315MHz consumer RF remotes.

- **Principle**: Carrier ON = 1-bit, carrier OFF = 0-bit (or vice versa)
- **Identifying features**: Signal amplitude alternates between high and near-zero; clear ON/OFF envelope
- **Typical bit rates**: 1 kbps – 10 kbps
- **Common encodings**: NRZ (direct), pulse-width (short/long pulse = 0/1), Manchester
- **Preamble**: Alternating 1/0 for AGC settling
- **Payload**: Typically 24–32 bits (device address + command)
- **Decoder**: `--demodulate ook` or `--modulation OOK`

```bash
python3 skills/urh/analyze_signal.py remote.complex -s 2000000 --demodulate ook --clusters
urh_cli analyze -f remote.complex -s 2000000 --modulation OOK
```

### ASK (Amplitude Shift Keying)

Generalization of OOK where the amplitude shifts between two non-zero levels.

- **Principle**: Two amplitude levels encode 0 and 1 (unlike OOK, carrier is always present)
- **Identifying features**: Amplitude varies but signal is never fully off
- **Common in**: RFID (125 kHz), some proprietary protocols
- **Decoder**: `--modulation ASK`

### FSK (Frequency Shift Keying)

Common for IoT sensors, Z-Wave, and many 433MHz/868MHz devices.

- **Principle**: Two frequencies encode 0 and 1 (e.g., center ± deviation)
- **Identifying features**: Constant-amplitude signal that shifts frequency; visible as two lobes in the spectrum
- **Typical deviation**: 25 kHz – 100 kHz for narrowband IoT
- **Decoder**: `--demodulate fsk` or `--modulation FSK`

```bash
python3 skills/urh/analyze_signal.py sensor.complex -s 2000000 --demodulate fsk
urh_cli analyze -f zwave.complex -s 2000000 --modulation FSK
```

### PSK (Phase Shift Keying)

Used in protocols requiring higher data rates or better noise immunity.

- **Principle**: Phase of the carrier encodes bits (BPSK: 2 phases, QPSK: 4 phases)
- **Identifying features**: Constant amplitude and frequency; phase reversals visible in I/Q constellation
- **Common in**: Zigbee (O-QPSK at 2.4 GHz), RFID
- **Decoder**: `--modulation PSK`

### Common IoT Protocols

#### 433MHz / 315MHz Remotes (OOK, Pulse-Width or Manchester)

- **Modulation**: OOK
- **Bit encoding**: Pulse-width (short ≈ 300–500 µs = 0, long ≈ 900–1500 µs = 1) or Manchester
- **Frame**: 24–48 bits, repeated 3–10 times with guard gap
- **Attack**: Replay — record and retransmit the exact bit sequence

#### Z-Wave (868 MHz EU / 908 MHz US)

- **Modulation**: 2-FSK
- **Data rates**: 9.6 kbps (legacy), 40 kbps, 100 kbps (Z-Wave+)
- **Frame**: Preamble (0x55 bytes), SOF (0xF0), length, payload, checksum
- **Analysis**: Capture at 2 MSPS, demodulate FSK, look for 0x55 preamble

#### Zigbee (2.4 GHz, O-QPSK)

- **Modulation**: O-QPSK (requires HackRF or USRP — RTL-SDR cannot tune to 2.4 GHz)
- **Data rate**: 250 kbps
- **Note**: Full decoding requires Wireshark with the IEEE 802.15.4 dissector

## Analysis Workflow

### Step 1: Get Signal Overview

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000
```

Check sample count, duration, and amplitude statistics. Confirm the file loaded correctly.

### Step 2: Inspect the Spectrum

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --spectrum
```

- **Single lobe at center (0 Hz)**: likely OOK or ASK (baseband amplitude modulation)
- **Two symmetrical lobes offset from 0 Hz**: FSK (the offset is the frequency deviation)
- **Flat/spread spectrum**: PSK or higher-order modulation

### Step 3: Check Signal Energy Over Time

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --energy
```

Identify packet boundaries — bursts of high energy separated by silence. Count the number of frames.

### Step 4: Demodulate

```bash
# OOK (most common for narrowband IoT / remotes)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --clusters

# FSK (if spectrum shows two lobes)
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate fsk
```

### Step 5: Decode with urh_cli

```bash
urh_cli analyze -f signal.complex -s 2000000 --modulation OOK
```

### Step 6: Export and Analyze Bits

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --export pulses.csv

# Convert bit string to hex
python3 -c "bits='01001000...'; print(hex(int(bits, 2)))"
```

## CTF Tips

1. **OOK is overwhelmingly common in CTF RF challenges**: If the frequency is 315/433 MHz and the signal has clear bursting, try OOK first.
2. **Start with `--spectrum`**: The spectrum shape is the fastest way to identify OOK vs FSK.
3. **Repeated frames**: Most RF remotes transmit the same frame 3–10 times. Use `--energy` to count packets.
4. **Pulse-width decoding**: If NRZ gives garbage, check `--clusters` — two timing clusters indicate pulse-width encoding (short=0, long=1 or vice versa).
5. **Preamble identification**: A long run of alternating bits at the start is sync/preamble — skip it, focus on what follows.
6. **Manchester encoding**: If the payload looks like `10101010...` throughout, you are seeing un-decoded Manchester. Every `10` → `1`, every `01` → `0`.
7. **URH GUI for difficult signals**: When CLI output is ambiguous, `urh` opens the graphical editor where you can visually set thresholds and zoom into individual bits.
8. **Sample rate must be exact**: If `-s` does not match the actual capture rate, bit timing will be wrong and decoding will fail. Check SDR software logs for the exact rate.
9. **Flag in the bits**: After decoding, convert the bit string to ASCII — CTF flags often appear directly in RF payloads as plaintext strings.
10. **Fixed vs rolling codes**: Simple 433MHz remotes use fixed codes (same bits every press) — safe to replay. Modern systems use rolling codes — replay will not work.

## Troubleshooting

### "urh_cli not found"

Verify the package is installed:
```bash
python3 -c "import urh; print('urh available')"
```

If the import works but `urh_cli` is not on PATH:
```bash
python3 -m urh.cli.urh_cli analyze -f signal.complex -s 2000000
```

### "No module named 'urh'"

Install the package. URH requires Cython to build its C extensions — install it first:
```bash
pip install cython
pip install urh
```

### "You need Cython to build URH's extensions!"

Cython is a build-time dependency for URH. Install it before installing URH:
```bash
pip install cython
pip install urh
```

### Decoded bits look like noise / all zeros / all ones

- **Wrong sample rate**: The `-s` value must exactly match the rate used during capture.
- **Wrong modulation**: Try a different modulation type.
- **Inverted signal**: Try `--demodulate ook --threshold 0.7` or manually invert bits:
  ```bash
  python3 -c "bits=open('bits.txt').read().strip(); print(''.join('1' if b=='0' else '0' for b in bits))"
  ```

### "No transitions detected" after OOK demodulation

- Signal may be too weak or clipped. Check amplitude statistics with the basic run.
- Try a lower threshold: `--threshold 0.1`
- Use `--energy` to verify packets are actually present in the signal.

### URH GUI fails to launch (Qt errors on Linux)

```bash
# With X11 forwarding:
ssh -X user@host urh

# Check Qt installation:
python3 -c "from PyQt5.QtWidgets import QApplication; print('Qt OK')"
```

### "Unsupported format"

- GNU Radio `.cfile` → rename to `.complex`
- Raw RTL-SDR uint8 I/Q → this format is not supported; convert to `.complex16u` or float32 first
- If unsure about format, try `.complex` and check if the spectrum looks reasonable
