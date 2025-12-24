---
name: chipsec
description: Static analysis of UEFI/BIOS firmware dumps using Intel's chipsec framework. Decode firmware structure, detect known malware and rootkits (LoJax, ThinkPwn, HackingTeam, MosaicRegressor), generate EFI executable inventories with hashes, extract NVRAM variables, and parse SPI flash descriptors. Use when analyzing firmware .bin/.rom/.fd/.cap files offline without requiring hardware access.
---

# Chipsec - UEFI Firmware Static Analysis

You are helping the user perform static security analysis of UEFI/BIOS firmware dumps using Intel's chipsec framework. This skill focuses exclusively on offline analysis capabilities that do not require kernel driver access or root privileges.

## Tool Overview

Chipsec is Intel's Platform Security Assessment Framework. For static analysis of firmware dumps, it provides:

- EFI executable inventory generation with cryptographic hashes
- Detection of known UEFI malware and vulnerabilities
- Firmware structure decoding and extraction
- NVRAM/UEFI variable extraction
- SPI flash descriptor parsing
- Baseline comparison for change detection

## Prerequisites

### One-Time Setup (Fix Logging Permission)

Chipsec requires a writable logs directory. Run once:

```bash
sudo mkdir -p /usr/lib/python3.13/site-packages/logs
sudo chmod 777 /usr/lib/python3.13/site-packages/logs
```

### Verify Installation

```bash
chipsec_main --version
```

## Core Commands

All static analysis commands use these flags:
- `-i` : Ignore platform check (required for offline analysis)
- `-n` : No kernel driver (required for static analysis)

### 1. Malware and Vulnerability Scan (Primary Use)

Scan firmware for known threats including UEFI rootkits and SMM vulnerabilities:

```bash
chipsec_main -i -n -m tools.uefi.scan_blocked -a <firmware.bin>
```

**Detected Threats:**

| Threat | Description | Reference |
|--------|-------------|-----------|
| HT_UEFI_Rootkit | HackingTeam commercial UEFI rootkit | McAfee ATR |
| MR_UEFI_Rootkit | MosaicRegressor APT UEFI implant | Kaspersky |
| LoJax | First UEFI rootkit found in the wild (Sednit/APT28) | ESET |
| ThinkPwn | SystemSmmRuntimeRt SMM code execution vulnerability | cr4.sh |
| FirmwareBleed | SMM Return Stack Buffer stuffing vulnerability | Binarly |

**Example Output (Threat Found):**
```
[!] match 'ThinkPwn.SystemSmmRuntimeRt'
    GUID  : {7c79ac8c-5e6c-4e3d-ba6f-c260ee7c172e}
[!] found EFI binary matching 'ThinkPwn'
    MD5   : 59f5ba825911e7d0dffe06ee0d6d9828
    SHA256: 7f0e16f244151e7bfa170b7def014f6a225c5af626c223567f36a8b19f95e3ab

WARNING: Blocked EFI binary found in the UEFI firmware image
```

### 2. Generate EFI Executable Inventory

Create a JSON manifest of all EFI modules with cryptographic hashes:

```bash
chipsec_main -i -n -m tools.uefi.scan_image -a generate <output.json> <firmware.bin>
```

**Use Cases:**
- Create baseline for change detection
- Inventory all DXE drivers, PEI modules, applications
- Generate hashes for threat intelligence lookup

**Output Format (efilist.json):**
```json
{
  "sha256_hash": {
    "sha1": "...",
    "guid": "EFD652CC-0E99-40F0-96C0-E08C089070FC",
    "name": "S3Resume",
    "type": "S_PE32"
  }
}
```

### 3. Compare Against Baseline

Check firmware against a known-good inventory:

```bash
chipsec_main -i -n -m tools.uefi.scan_image -a check <baseline.json> <firmware.bin>
```

**Use Cases:**
- Detect unauthorized firmware modifications
- Verify firmware update integrity
- Incident response - compare compromised vs clean

### 4. Decode Firmware Structure

Extract and analyze firmware volumes, files, and sections:

```bash
chipsec_util -i -n uefi decode <firmware.bin>
```

**Creates output directory containing:**
```
firmware.bin.dir/
├── firmware_volumes/     # Extracted FV regions
├── efi_files/           # Individual EFI binaries
├── nvram/               # NVRAM variables (if found)
└── ...
```

### 5. Extract NVRAM Variables

NVRAM variables are extracted as part of the `uefi decode` command:

```bash
chipsec_util -i -n uefi decode <firmware.bin>
```

**NVRAM output location:**
```
firmware.bin.dir/
├── nvram_.nvram.lst          # List of NVRAM variables
├── nvram/                    # Extracted variable files (if present)
└── FV/                       # Firmware volumes
```

**View extracted variables:**
```bash
cat firmware.bin.dir/nvram_.nvram.lst
```

**Note:** The standalone `uefi nvram` command requires driver access and cannot be used for static analysis. Use `uefi decode` instead, which extracts NVRAM as part of the full firmware decode process.

### 6. Parse SPI Flash Descriptor

Analyze SPI flash regions (requires platform hint):

```bash
chipsec_util -p <PLATFORM> spidesc <firmware.bin>
```

**Common Platform Codes:**
| Code | Platform |
|------|----------|
| SNB | Sandy Bridge (2nd Gen Core) |
| IVB | Ivy Bridge (3rd Gen Core) |
| HSW | Haswell (4th Gen Core) |
| BDW | Broadwell (5th Gen Core) |
| SKL | Skylake (6th Gen Core) |
| KBL | Kaby Lake (7th Gen Core) |
| CFL | Coffee Lake (8th/9th Gen Core) |
| ICL | Ice Lake (10th Gen Core) |
| TGL | Tiger Lake (11th Gen Core) |
| ADL | Alder Lake (12th Gen Core) |
| RPL | Raptor Lake (13th Gen Core) |

**Shows:**
- Flash regions (Descriptor, BIOS, ME, GbE, PDR)
- Region base addresses and sizes
- Flash component information
- Master access permissions

## Supported Firmware Formats

| Extension | Description |
|-----------|-------------|
| `.bin` | Raw firmware/SPI flash dumps |
| `.rom` | SPI flash ROM dumps |
| `.fd` | UEFI Firmware Descriptor (OVMF, EDK2) |
| `.cap` | UEFI Capsule update files |
| `.scap` | Signed UEFI Capsule updates |
| `.fv` | UEFI Firmware Volume |
| `.flash` | Full flash dumps |

## Workflows

### Workflow 1: Standard Security Audit

Complete firmware security assessment:

```bash
TARGET="firmware.bin"
OUTPUT_DIR="./chipsec-analysis"
mkdir -p "$OUTPUT_DIR"

# Step 1: Scan for known threats (most important)
echo "[+] Scanning for known malware/vulnerabilities..."
chipsec_main -i -n -m tools.uefi.scan_blocked -a "$TARGET" 2>&1 | tee "$OUTPUT_DIR/threat_scan.txt"

# Step 2: Generate EFI inventory
echo "[+] Generating EFI executable inventory..."
chipsec_main -i -n -m tools.uefi.scan_image -a generate "$OUTPUT_DIR/efi_inventory.json" "$TARGET"

# Step 3: Decode firmware structure
echo "[+] Decoding firmware structure..."
chipsec_util -i -n uefi decode "$TARGET"

# Step 4: Check for NVRAM in decoded output
echo "[+] Checking for extracted NVRAM variables..."
cat "$TARGET.dir/nvram_.nvram.lst" 2>/dev/null || echo "No NVRAM variables extracted"

echo "[+] Analysis complete. Results in: $OUTPUT_DIR/"
echo "[+] Decoded firmware in: $TARGET.dir/"
```

### Workflow 2: Malware Detection Focus

Quick check for known threats:

```bash
# Run blocklist scan
chipsec_main -i -n -m tools.uefi.scan_blocked -a firmware.bin 2>&1 | tee scan_results.txt

# Check for any matches
echo "[+] Checking for threat matches..."
grep -E "match|found|WARNING" scan_results.txt

# If threats found, get details
grep -A10 "found EFI binary matching" scan_results.txt
```

### Workflow 3: Firmware Update Verification

Compare before/after firmware update:

```bash
# Before update - create baseline
chipsec_main -i -n -m tools.uefi.scan_image -a generate baseline_before.json firmware_original.bin

# After update - compare
chipsec_main -i -n -m tools.uefi.scan_image -a check baseline_before.json firmware_updated.bin

# Also generate new inventory for diff analysis
chipsec_main -i -n -m tools.uefi.scan_image -a generate baseline_after.json firmware_updated.bin

# Compare inventories
diff baseline_before.json baseline_after.json
```

### Workflow 4: Incident Response

Analyze potentially compromised firmware:

```bash
SUSPECT="compromised_dump.bin"
KNOWN_GOOD="golden_image.bin"
OUTPUT_DIR="./ir-analysis"
mkdir -p "$OUTPUT_DIR"

# 1. Immediate threat scan
echo "[!] Scanning for known implants..."
chipsec_main -i -n -m tools.uefi.scan_blocked -a "$SUSPECT" 2>&1 | tee "$OUTPUT_DIR/threat_scan.txt"

# 2. Generate inventory of suspect firmware
chipsec_main -i -n -m tools.uefi.scan_image -a generate "$OUTPUT_DIR/suspect_inventory.json" "$SUSPECT"

# 3. If golden image available, compare
if [ -f "$KNOWN_GOOD" ]; then
    chipsec_main -i -n -m tools.uefi.scan_image -a generate "$OUTPUT_DIR/golden_inventory.json" "$KNOWN_GOOD"
    echo "[+] Comparing against known-good baseline..."
    chipsec_main -i -n -m tools.uefi.scan_image -a check "$OUTPUT_DIR/golden_inventory.json" "$SUSPECT"
fi

# 4. Full decode for manual analysis
chipsec_util -i -n uefi decode "$SUSPECT"

echo "[+] IR analysis complete. Review: $OUTPUT_DIR/"
```

### Workflow 5: IoT Device Firmware Analysis

Analyze firmware extracted from IoT device:

```bash
# After extracting firmware with ffind or binwalk
IOT_FIRMWARE="extracted_firmware.bin"

# Quick threat check
chipsec_main -i -n -m tools.uefi.scan_blocked -a "$IOT_FIRMWARE"

# Generate inventory for documentation
chipsec_main -i -n -m tools.uefi.scan_image -a generate iot_efi_list.json "$IOT_FIRMWARE"

# Extract structure for deeper analysis
chipsec_util -i -n uefi decode "$IOT_FIRMWARE"

# NVRAM variables extracted as part of decode - check output
cat "$IOT_FIRMWARE.dir/nvram_.nvram.lst" 2>/dev/null
```

## Output Interpretation

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed, no issues found |
| 2 | Security issues detected (FAILED tests) |
| 16 | Module execution errors |
| 128 | Module not applicable |

### Result States

| State | Meaning | Action |
|-------|---------|--------|
| PASSED | No known threats detected | Document and proceed |
| WARNING | Potential issue found | Investigate further |
| FAILED | Security vulnerability confirmed | Remediate immediately |
| NOT APPLICABLE | Test couldn't run | Check firmware format |

### Interpreting Threat Matches

When `scan_blocked` finds a match:

```
[!] match 'ThinkPwn.SystemSmmRuntimeRt'
    GUID  : {7c79ac8c-5e6c-4e3d-ba6f-c260ee7c172e}
    regexp: bytes '...' at offset 1184h
[!] found EFI binary matching 'ThinkPwn'
    MD5   : 59f5ba825911e7d0dffe06ee0d6d9828
    SHA1  : 4979bc7660fcf3ab5562ef2e1c4c45097ecb615e
    SHA256: 7f0e16f244151e7bfa170b7def014f6a225c5af626c223567f36a8b19f95e3ab
```

**Key Information:**
- **Threat Name**: Which known threat was matched
- **GUID**: Unique identifier of the affected EFI module
- **Hashes**: For further threat intelligence lookup
- **Offset**: Location in binary where pattern matched

## Integration with IoTHackBot Tools

### With ffind (Firmware Extraction)

```bash
# Find firmware files in extracted filesystem
ffind /path/to/extracted -a

# Analyze found UEFI firmware
chipsec_main -i -n -m tools.uefi.scan_blocked -a found_firmware.bin
```

### With binwalk (Pre-processing)

```bash
# Extract firmware components first
binwalk -e firmware_package.bin

# Find and analyze UEFI images
find _firmware_package.bin.extracted -name "*.fd" -o -name "*.rom" | while read fw; do
    echo "[+] Analyzing: $fw"
    chipsec_main -i -n -m tools.uefi.scan_blocked -a "$fw"
done
```

## Troubleshooting

### Permission Denied on Logs

```
PermissionError: [Errno 13] Permission denied: '/usr/lib/python3.13/site-packages/logs/...'
```

**Solution:**
```bash
sudo mkdir -p /usr/lib/python3.13/site-packages/logs
sudo chmod 777 /usr/lib/python3.13/site-packages/logs
```

### Module Not Found

```
ERROR: No module named 'chipsec.modules.tools.uefi.scan_blocked'
```

**Solution:** Verify chipsec installation:
```bash
pip show chipsec
pip install --upgrade chipsec
```

### Invalid Firmware Format

```
[CHIPSEC] Found 0 EFI executables in UEFI firmware image
```

**Possible Causes:**
- File is not valid UEFI firmware
- File is encrypted or compressed
- File needs pre-processing (binwalk extraction)

**Diagnosis:**
```bash
file firmware.bin
binwalk firmware.bin
```

### Platform Required for spidesc

```
ERROR: This module requires a configuration to be loaded.
```

**Solution:** Specify platform with `-p`:
```bash
chipsec_util -p SKL spidesc firmware.bin
```

### NVRAM Not Extracted

If `nvram_.nvram.lst` is empty or shows an error after decode:

**Possible Causes:**
- Firmware doesn't contain standard NVRAM format
- NVRAM region is encrypted or compressed
- Non-standard vendor format

**Alternative Analysis:**
```bash
# Search for variable-like patterns in decoded output
grep -r "Setup\|Boot\|SecureBoot" firmware.bin.dir/

# Use binwalk to find NVRAM signatures
binwalk -R "\x06\x00\x00\x00" firmware.bin
```

## Best Practices

### 1. Always Run Threat Scan First

The blocklist scan is quick and catches known threats:
```bash
chipsec_main -i -n -m tools.uefi.scan_blocked -a firmware.bin
```

### 2. Generate Inventory for Every Firmware

Create baselines for future comparison:
```bash
chipsec_main -i -n -m tools.uefi.scan_image -a generate "$(basename firmware.bin .bin)_inventory.json" firmware.bin
```

### 3. Save All Output

Redirect output for documentation:
```bash
chipsec_main -i -n -m tools.uefi.scan_blocked -a firmware.bin 2>&1 | tee analysis_$(date +%Y%m%d).txt
```

### 4. Verify Firmware Format First

Before running chipsec:
```bash
file firmware.bin
binwalk firmware.bin | head -20
```

### 5. Use Organized Output Directories

```bash
mkdir -p analysis/{threats,inventories,decoded,nvram}
```

### 6. Cross-Reference with Other Tools

- **UEFITool**: Visual firmware structure analysis
- **binwalk**: Entropy analysis and extraction
- **strings**: Quick secrets/URL discovery

## Command Reference

### Quick Reference Table

| Task | Command |
|------|---------|
| Scan for malware | `chipsec_main -i -n -m tools.uefi.scan_blocked -a <fw>` |
| Generate inventory | `chipsec_main -i -n -m tools.uefi.scan_image -a generate <out.json> <fw>` |
| Compare baseline | `chipsec_main -i -n -m tools.uefi.scan_image -a check <base.json> <fw>` |
| Decode structure + NVRAM | `chipsec_util -i -n uefi decode <fw>` |
| Parse SPI descriptor | `chipsec_util -p <PLAT> spidesc <fw>` |

### Flag Reference

| Flag | Purpose |
|------|---------|
| `-i` | Ignore platform check (required for offline) |
| `-n` | No kernel driver (required for static analysis) |
| `-m` | Specify module to run |
| `-a` | Module arguments |
| `-p` | Specify platform (for spidesc) |
| `-j` | JSON output file |

## Security and Ethics

**IMPORTANT**: Only analyze firmware you own or have explicit authorization to analyze.

- Respect intellectual property and licensing
- Follow responsible disclosure for vulnerabilities found
- Document all analysis activities
- Be aware that some firmware may contain proprietary code
- Use findings for defensive security purposes only

## Success Criteria

A successful chipsec static analysis includes:

- Threat scan completed (PASSED or findings documented)
- EFI inventory JSON generated with module hashes
- Firmware structure decoded (if applicable)
- NVRAM variables extracted (if present)
- All findings documented with:
  - Threat name and severity
  - Affected module GUID and hashes
  - Recommendations for remediation
- Output files organized and saved for reporting
