# Chipsec Static Analysis Skill - Implementation Plan

**Status: IMPLEMENTED**

## Overview

This plan outlines the implementation of a Claude Code skill for UEFI firmware static analysis using chipsec. The skill focuses exclusively on **offline static analysis** capabilities - analyzing firmware dump files without requiring kernel driver access or root privileges.

**Skill Name:** `chipsec` (changed from `chipsec-uefi` for simplicity)

## Scope

### In Scope (Static Analysis Only)
- Firmware image decoding and structure analysis
- EFI executable inventory and hash generation
- Malware/rootkit detection (blocklist scanning)
- NVRAM/UEFI variable extraction from dumps
- Baseline generation and comparison
- Known vulnerability pattern matching (ThinkPwn, LoJax, etc.)

### Out of Scope (Live System Analysis - Requires Separate Skill)
- SPI flash dumping from live systems
- BIOS write protection checks
- SMM security testing
- Secure Boot live verification
- Intel Boot Guard checks
- Any module requiring kernel driver

## Skill Structure

```
.claude/skills/chipsec/
├── SKILL.md                    # Main skill file with instructions
├── WORKFLOWS.md                # Common analysis workflows
└── BLOCKLIST_REFERENCE.md      # Known threats reference (optional)
```

## SKILL.md Design

### Frontmatter
```yaml
---
name: chipsec-uefi
description: Static analysis of UEFI firmware dumps using chipsec. Decode firmware structure, detect known malware/rootkits (LoJax, ThinkPwn, HackingTeam), extract EFI executable inventories, and analyze NVRAM variables. Use when analyzing firmware .bin/.rom/.fd files offline.
---
```

### Key Sections

#### 1. Tool Overview
- What chipsec is (Intel's Platform Security Assessment Framework)
- Focus on offline/static capabilities
- Prerequisites (chipsec installed, logs directory writable)

#### 2. Prerequisites Check
```bash
# One-time fix for chipsec logging issue
sudo mkdir -p /usr/lib/python3.13/site-packages/logs
sudo chmod 777 /usr/lib/python3.13/site-packages/logs
```

#### 3. Core Commands

**A. Generate EFI Executable Inventory**
```bash
chipsec_main -i -n -m tools.uefi.scan_image -a generate <output.json> <firmware.bin>
```
- Creates JSON manifest of all EFI modules with SHA256 hashes
- Use for baseline/change detection

**B. Malware/Vulnerability Scan**
```bash
chipsec_main -i -n -m tools.uefi.scan_blocked -a <firmware.bin>
```
- Checks against known threats:
  - HackingTeam UEFI Rootkit
  - MosaicRegressor UEFI Rootkit
  - LoJax (first wild UEFI rootkit)
  - ThinkPwn SMM vulnerability
  - FirmwareBleed SMM vulnerability

**C. Firmware Structure Decoding**
```bash
chipsec_util -i -n uefi decode <firmware.bin>
```
- Extracts firmware volumes, files, sections
- Creates output directory with components

**D. NVRAM Variable Extraction**
```bash
chipsec_util -i -n uefi nvram vss <firmware.bin>
chipsec_util -i -n uefi nvram nvar <firmware.bin>
```
- Extracts stored UEFI variables
- VSS format (common) and NVAR format (AMI BIOS)

**E. Baseline Comparison**
```bash
chipsec_main -i -n -m tools.uefi.scan_image -a check <baseline.json> <firmware.bin>
```
- Compare firmware against known-good baseline
- Detect unauthorized modifications

#### 4. Command Flags Reference
| Flag | Purpose |
|------|---------|
| `-i` | Ignore platform check (required for offline analysis) |
| `-n` | No kernel driver (required for static analysis) |
| `-m` | Specify module to run |
| `-a` | Module arguments |

#### 5. Output Interpretation

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 2 | Security issues found |
| 16 | Module errors |
| 128 | Module not applicable |

**Result States:**
- PASSED: No issues detected
- WARNING: Potential issue found (e.g., blocked binary detected)
- FAILED: Security vulnerability confirmed

#### 6. Workflows

**Workflow 1: Standard Firmware Audit**
```bash
# 1. Generate inventory
chipsec_main -i -n -m tools.uefi.scan_image -a generate inventory.json firmware.bin

# 2. Scan for known threats
chipsec_main -i -n -m tools.uefi.scan_blocked -a firmware.bin

# 3. Decode structure for manual inspection
chipsec_util -i -n uefi decode firmware.bin
```

**Workflow 2: Malware Detection Focus**
```bash
# Run blocklist scan and capture details
chipsec_main -i -n -m tools.uefi.scan_blocked -a firmware.bin 2>&1 | tee scan_results.txt

# Check for matches
grep -A5 "match\|found" scan_results.txt
```

**Workflow 3: Baseline Comparison (Update Verification)**
```bash
# Before update - generate baseline
chipsec_main -i -n -m tools.uefi.scan_image -a generate baseline.json firmware_original.bin

# After update - compare
chipsec_main -i -n -m tools.uefi.scan_image -a check baseline.json firmware_updated.bin
```

**Workflow 4: NVRAM Analysis**
```bash
# Try VSS format first (most common)
chipsec_util -i -n uefi nvram vss firmware.bin

# If that fails, try NVAR (AMI)
chipsec_util -i -n uefi nvram nvar firmware.bin
```

#### 7. Known Threats Database

Document the threats detected by scan_blocked:

| Threat ID | Name | Description | Reference |
|-----------|------|-------------|-----------|
| HT_UEFI_Rootkit | HackingTeam | Commercial spyware UEFI rootkit | McAfee ATR |
| MR_UEFI_Rootkit | MosaicRegressor | APT UEFI implant | Kaspersky |
| ThinkPwn | SystemSmmRuntimeRt | SMM code execution vuln | cr4.sh |
| LoJax | LoJax | First wild UEFI rootkit (Sednit/APT28) | ESET |
| FirmwareBleed | RSB Stuffing | SMM return stack buffer issue | Binarly |

#### 8. Supported Firmware Formats

- `.bin` - Raw firmware dumps
- `.rom` - SPI flash dumps
- `.fd` - UEFI Firmware Descriptors (OVMF, EDK2)
- `.cap` - UEFI Capsule updates
- `.scap` - Signed capsule updates

#### 9. Integration with IoTHackBot

**With ffind:**
```bash
# Find firmware files
ffind /path/to/extracted -a

# Analyze found firmware
chipsec_main -i -n -m tools.uefi.scan_blocked -a firmware.bin
```

**With nmap (post-exploitation):**
- After dumping firmware from compromised IoT device
- Analyze for implants or backdoors

#### 10. Troubleshooting

**Permission Denied on Logs**
```bash
sudo mkdir -p /usr/lib/python3.13/site-packages/logs
sudo chmod 777 /usr/lib/python3.13/site-packages/logs
```

**Module Not Found**
- Verify chipsec installation: `pip show chipsec`
- Check Python version compatibility

**Decode Produces No Output**
- File may not be valid UEFI firmware
- Try `file firmware.bin` and `binwalk firmware.bin` first

#### 11. Best Practices

1. **Always generate inventory first** - Creates baseline for future comparison
2. **Run blocklist scan on all firmware** - Quick check for known threats
3. **Save all output** - Use output redirection for documentation
4. **Verify firmware format** - Use `file` and `binwalk` before chipsec
5. **Cross-reference findings** - Use UEFITool for visual confirmation

#### 12. Example Analysis Session

```bash
TARGET="Dell-A02.rom"
OUTPUT_DIR="./chipsec-analysis"
mkdir -p "$OUTPUT_DIR"

echo "[+] Generating EFI inventory..."
chipsec_main -i -n -m tools.uefi.scan_image \
  -a generate "$OUTPUT_DIR/efi_inventory.json" "$TARGET"

echo "[+] Scanning for known threats..."
chipsec_main -i -n -m tools.uefi.scan_blocked \
  -a "$TARGET" 2>&1 | tee "$OUTPUT_DIR/threat_scan.txt"

echo "[+] Decoding firmware structure..."
chipsec_util -i -n uefi decode "$TARGET"

echo "[+] Extracting NVRAM..."
chipsec_util -i -n uefi nvram vss "$TARGET" > "$OUTPUT_DIR/nvram.txt" 2>&1

echo "[+] Analysis complete. Results in: $OUTPUT_DIR/"
```

#### 13. Success Criteria

A successful chipsec static analysis includes:

- EFI inventory JSON generated with module hashes
- Blocklist scan completed (PASSED or WARNING with details)
- Firmware structure decoded and extractable
- NVRAM variables extracted (if present)
- Any security findings documented with:
  - Threat name and description
  - Affected module GUID
  - SHA256 hash of affected binary
  - Reference URL for remediation

## Implementation Steps

1. **Create skill directory**: `.claude/skills/chipsec/`

2. **Write SKILL.md**: Following the structure above with:
   - YAML frontmatter (name, description)
   - Tool overview
   - Prerequisites
   - Command reference with examples
   - Workflows for common tasks
   - Troubleshooting section
   - Integration notes

3. **Optional: Create WORKFLOWS.md**: Extended workflow documentation
   - Detailed step-by-step for complex analyses
   - Multi-firmware comparison workflows
   - Incident response procedures

4. **Test the skill**:
   - Run against sample firmware (Dell-A02.rom, OVMF, etc.)
   - Verify all commands work with `-i -n` flags
   - Test troubleshooting steps

5. **Update README.md**: Add chipsec to the tools list in iothackbot README

## Design Decisions

### Why Static Analysis Only?

1. **Safety**: Live system analysis requires kernel drivers and root access
2. **Portability**: Static analysis works on any firmware dump
3. **Scope Clarity**: Separate concerns - live analysis deserves its own skill
4. **IoT Focus**: Firmware dumps from IoT devices are the common use case

### Why These Specific Modules?

| Module | Rationale |
|--------|-----------|
| tools.uefi.scan_image | Core inventory/baseline functionality |
| tools.uefi.scan_blocked | Known threat detection - high value |
| uefi decode | Structure analysis essential for manual review |
| uefi nvram | Variable extraction useful for config analysis |

### Excluded Modules (Require Live System)

- common.bios_wp (BIOS write protection)
- common.spi_lock (SPI flash lock)
- common.smm (SMM memory protection)
- common.secureboot.* (Secure Boot checks)
- tools.uefi.reputation (requires VirusTotal API)
- tools.uefi.s3script_modify (requires live S3 access)

## Estimated Complexity

- **SKILL.md**: ~400-500 lines (similar to nmap-scan skill)
- **Development Time**: 2-3 hours
- **Testing Time**: 1 hour with sample firmware

## Dependencies

- chipsec >= 1.13.x
- Python 3.x
- Write access to chipsec logs directory (one-time fix)

## Future Enhancements

1. **Custom blocklist support**: Allow user-defined threat signatures
2. **Report generation**: Structured JSON/HTML reports
3. **Diff tool integration**: Visual comparison of firmware versions
4. **UEFITool integration**: Cross-reference with GUI tool findings
