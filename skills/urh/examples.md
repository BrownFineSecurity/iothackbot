# URH RF Signal Analysis Examples

## Example 1: Unknown RF Signal — Full Analysis Pipeline

**Scenario**: You have a captured RF signal from an unknown IoT device and need to identify the protocol.

### Step 1: Get an overview

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000
```

Output:
```
File:         signal.complex
Format:       complex
Samples:      200,000
Sample rate:  2.000 MSPS
Duration:     100.00 ms  (0.1000 s)

Amplitude
----------------------------------------
  Peak:   0.8432
  Mean:   0.1234
  Std:    0.2156

Modulation hint: OOK/ASK
```

### Step 2: Inspect the spectrum

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --spectrum
```

A single lobe centered at 0 Hz confirms this is OOK/ASK (baseband amplitude modulation).

### Step 3: Check for packet boundaries

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --energy
```

Look for bursts of high energy separated by silence. This shows how many frames are in the capture.

### Step 4: Demodulate and analyze timing

```bash
python3 skills/urh/analyze_signal.py signal.complex -s 2000000 --demodulate ook --clusters
```

Output:
```
OOK Demodulation (threshold: 0.4216)
----------------------------------------
Transitions detected: 156
Initial state:        LOW
All pulses:  min=300.0us  max=1200.0us  mean=600.0us
HIGH pulses (78): min=300.0us  max=900.0us
LOW gaps   (78): min=300.0us  max=1200.0us

Detected Pulse Duration Clusters
----------------------------------------
HIGH pulse clusters:
  ~300.0us (52 occurrences)
  ~900.0us (26 occurrences)
LOW gap clusters:
  ~300.0us (48 occurrences)
  ~1200.0us (8 occurrences)
```

Two pulse duration clusters (300µs and 900µs, ratio 1:3) → pulse-width encoding.

### Step 5: Decode with urh_cli

```bash
urh_cli analyze -f signal.complex -s 2000000 --modulation OOK
```

---

## Example 2: 433MHz Remote Control

**Scenario**: Captured a 433.92 MHz garage door remote with 2 MSPS sample rate.

### Identify the protocol

```bash
python3 skills/urh/analyze_signal.py remote_433.complex -s 2000000 --demodulate ook --clusters --histogram
```

Typical output for a fixed-code 433MHz remote:
- 2–3 HIGH pulse clusters (preamble + short bit + long bit)
- Guard gap cluster much longer than data bits
- Repeated 3–5 times

### Decode to bits

```bash
urh_cli analyze -f remote_433.complex -s 2000000 --modulation OOK
```

### Export pulses for manual analysis

```bash
python3 skills/urh/analyze_signal.py remote_433.complex -s 2000000 --demodulate ook --export pulses.csv
```

### Convert decoded bits to hex

```bash
python3 -c "bits='010100110101...'; print(hex(int(bits, 2)))"
```

---

## Example 3: FSK Sensor Signal

**Scenario**: Captured a 433MHz temperature/humidity sensor that uses FSK.

### Identify FSK via spectrum

```bash
python3 skills/urh/analyze_signal.py sensor.complex -s 2000000 --spectrum
```

Two symmetrical lobes offset from 0 Hz → FSK confirmed.

### Demodulate FSK

```bash
python3 skills/urh/analyze_signal.py sensor.complex -s 2000000 --demodulate fsk
```

### Decode with urh_cli

```bash
urh_cli analyze -f sensor.complex -s 2000000 --modulation FSK
```

---

## Example 4: CTF RF Challenge

**Scenario**: CTF provides `capture.cfile` (GNU Radio format). The flag is encoded in the transmission.

### Step 1: Rename and check (GNU Radio .cfile is float32 IQ)

```bash
# .cfile is the same as .complex, both are float32 IQ
python3 skills/urh/analyze_signal.py capture.cfile -s 2000000
```

If sample rate is unknown, try common values: 1000000, 2000000, 8000000.

### Step 2: Try OOK (most common in CTF)

```bash
python3 skills/urh/analyze_signal.py capture.cfile -s 2000000 --demodulate ook --clusters
```

### Step 3: Decode bits

```bash
urh_cli analyze -f capture.cfile -s 2000000 --modulation OOK
```

### Step 4: Look for the flag

```bash
# Convert bit string to ASCII
python3 -c "
bits = '0100011001001100010000010100011101111011...'
n = len(bits) - (len(bits) % 8)
chars = [chr(int(bits[i:i+8], 2)) for i in range(0, n, 8)]
print(''.join(chars))
"
```

### Step 5: Try Manchester decoding if bits look like alternating pairs

```bash
python3 -c "
bits = '1001100110...'  # raw demodulated bits
# Manchester: 10 -> 1, 01 -> 0
decoded = []
for i in range(0, len(bits) - 1, 2):
    pair = bits[i:i+2]
    if pair == '10': decoded.append('1')
    elif pair == '01': decoded.append('0')
print(''.join(decoded))
"
```

---

## Example 5: Multiple File Formats

### GNU Radio .cfile (float32 IQ)

```bash
python3 skills/urh/analyze_signal.py capture.cfile -s 2000000 --demodulate ook
```

### HackRF .complex16s (int16 signed IQ)

```bash
python3 skills/urh/analyze_signal.py hackrf_capture.complex16s -s 8000000 --spectrum
```

### RTL-SDR raw (int16 unsigned IQ)

```bash
python3 skills/urh/analyze_signal.py rtlsdr_capture.complex16u -s 2048000 --demodulate ook --clusters
```

### WAV file (stereo IQ — left=I, right=Q)

```bash
python3 skills/urh/analyze_signal.py iq_capture.wav --spectrum
# (sample rate read automatically from WAV header)
```

---

## Useful Direct urh_cli Commands

```bash
# Full auto-analysis (URH detects modulation)
urh_cli analyze -f signal.complex -s 2000000

# Specify modulation type
urh_cli analyze -f signal.complex -s 2000000 --modulation OOK
urh_cli analyze -f signal.complex -s 2000000 --modulation FSK
urh_cli analyze -f signal.complex -s 2000000 --modulation ASK
urh_cli analyze -f signal.complex -s 2000000 --modulation PSK

# If urh_cli is not on PATH:
python3 -m urh.cli.urh_cli analyze -f signal.complex -s 2000000

# Launch GUI for interactive analysis and recording
urh
```
