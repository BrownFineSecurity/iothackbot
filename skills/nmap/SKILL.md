---
name: nmap
description: Professional network reconnaissance and port scanning using nmap. Supports various scan types (quick, full, UDP, stealth), service detection, vulnerability scanning, and NSE scripts. Use when you need to enumerate network services, detect versions, or perform network reconnaissance.
---

# Nmap Scan - Professional Network Reconnaissance

You are helping the user perform professional network reconnaissance and port scanning using nmap. This skill provides guidance for various scan types, output formats, and result analysis.

## Output Directory

### Directory Structure
```bash
nmap-output/
├── nmap-portscan.nmap      # Initial fast port discovery
├── nmap-portscan.xml
├── nmap-portscan.gnmap
├── nmap-services.nmap      # Detailed service detection on open ports
├── nmap-services.xml
└── nmap-services.gnmap
```

**IMPORTANT**: Always save nmap output to an organized directory structure. By default, use `./nmap-output/` or specify a custom directory.

## Default Scanning Strategy

**IMPORTANT**: Unless the user explicitly requests a different scan type, ALWAYS use this two-phase approach:

### Phase 1: Fast Port Discovery (Root SYN Scan)
```bash
sudo nmap -p- <target> -oA <output-dir>/nmap-portscan
```
- **Why sudo**: Running as root enables fast SYN scan (-sS is implicit)
- **Why -p-**: Scans all 65535 ports quickly
- **Duration**: Typically 1-3 minutes for SYN scan
- **Output**: List of all open ports

**Host Down Detection**:
If the scan output contains "Note: Host seems down", automatically retry with:
```bash
sudo nmap -p- -Pn <target> -oA <output-dir>/nmap-portscan
```
- `-Pn`: Skip host discovery, treat host as online
- Use this when firewalls block ping probes

### Phase 2: Targeted Service Detection
After Phase 1 completes, parse the open ports and run:
```bash
nmap -p <OPEN_PORT_LIST> -sV -sC <target> -oA <output-dir>/nmap-services
```
- `-p <OPEN_PORT_LIST>`: Only scan the ports found to be open (e.g., `-p 23,80,443,554,8000`)
- `-sV`: Service version detection
- `-sC`: Run default NSE scripts for additional enumeration
- **Duration**: Usually 1-3 minutes since only scanning known open ports

### Why This Strategy?

1. **Speed**: Fast SYN scan finds all open ports in 1-3 minutes
2. **Thoroughness**: Covers all 65535 ports, not just top 1000
3. **Efficiency**: Service detection only runs on confirmed open ports
4. **Accuracy**: Two-phase approach reduces false negatives

### Parsing Open Ports

After Phase 1, extract open ports using:
```bash
# Extract open ports from .gnmap file
grep "Ports:" <output-dir>/nmap-portscan.gnmap | sed 's/.*Ports: //g' | sed 's|/|\n|g' | grep "open" | cut -d'/' -f1 | tr '\n' ',' | sed 's/,$//'
```

Or parse from .nmap file:
```bash
grep "^[0-9]" <output-dir>/nmap-portscan.nmap | grep "open" | cut -d'/' -f1 | tr '\n' ',' | sed 's/,$//'
```

## Implementation Workflow

When the nmap-scan skill is invoked:

1. **Create output directory**
   ```bash
   OUTPUT_DIR="./nmap-output"
   mkdir -p "$OUTPUT_DIR"
   ```

2. **Run Phase 1: Fast port discovery**
   ```bash
   sudo nmap -p- <target> -oA "$OUTPUT_DIR/nmap-portscan"
   ```

3. **Check for "Host seems down" error**
   ```bash
   if grep -q "Host seems down" "$OUTPUT_DIR/nmap-portscan.nmap"; then
       echo "Host appears down, retrying with -Pn flag..."
       sudo nmap -p- -Pn <target> -oA "$OUTPUT_DIR/nmap-portscan"
   fi
   ```

4. **Parse open ports from results**
   ```bash
   OPEN_PORTS=$(grep "^[0-9]" "$OUTPUT_DIR/nmap-portscan.nmap" | grep "open" | cut -d'/' -f1 | tr '\n' ',' | sed 's/,$//')
   ```

5. **Run Phase 2: Service detection on open ports**
   ```bash
   if [ -n "$OPEN_PORTS" ]; then
       nmap -p "$OPEN_PORTS" -sV -sC <target> -oA "$OUTPUT_DIR/nmap-services"
   else
       echo "No open ports found, skipping service detection."
   fi
   ```

6. **Report results location**
   ```bash
   echo "Scan complete. Results saved to: $OUTPUT_DIR"
   ```

## Scan Types

### Quick Scan (Top 1000 Ports)
Use for initial reconnaissance or when time is limited:
```bash
nmap -sV -sC <target> -oA <output-prefix>
```
- `-sV`: Service version detection
- `-sC`: Run default NSE scripts
- `-oA`: Output in all formats (normal, XML, grepable)
- Scans top 1000 most common ports
- Typical duration: 1-3 minutes

### Comprehensive Scan (All Ports)
Use for thorough assessment when all ports must be checked:
```bash
nmap -sV -sC -p- <target> -oA <output-prefix>
```
- `-p-`: Scan all 65535 ports
- Significantly longer duration (5-30+ minutes depending on target)
- Use only when comprehensive coverage is required

### Stealth SYN Scan
Use when trying to avoid detection (requires root/sudo):
```bash
sudo nmap -sS -sV -sC <target> -oA <output-prefix>
```
- `-sS`: SYN stealth scan (doesn't complete TCP handshake)
- Less likely to be logged by target
- Requires root privileges

### UDP Scan
Use when UDP services need to be enumerated:
```bash
sudo nmap -sU --top-ports 100 <target> -oA <output-prefix>
```
- `-sU`: UDP scan
- `--top-ports 100`: Scan top 100 UDP ports (UDP scanning is slow)
- Common UDP services: DNS (53), SNMP (161), DHCP (67/68)
- Very slow - use top-ports to limit scope

### Aggressive Scan
Use for maximum information gathering (noisy):
```bash
nmap -A -T4 <target> -oA <output-prefix>
```
- `-A`: Enable OS detection, version detection, script scanning, traceroute
- `-T4`: Aggressive timing template (faster but more detectable)
- Very noisy - will be detected by IDS/IPS
- Use only with authorization

### Vulnerability Scan
Use to check for known vulnerabilities:
```bash
nmap -sV --script vuln <target> -oA <output-prefix>
```
- `--script vuln`: Run NSE vulnerability detection scripts
- Checks for common CVEs and misconfigurations
- Can be noisy and trigger alerts

### OS Detection
Use to identify operating system:
```bash
sudo nmap -O <target> -oA <output-prefix>
```
- `-O`: Enable OS detection
- Requires root privileges
- Uses TCP/IP stack fingerprinting

## Alternative Scan Types

The following scan types are available if the user explicitly requests them instead of the default two-phase strategy:

### Quick Scan (Top 1000 Ports Only)
Use ONLY if user explicitly requests a quick/fast scan:
```bash
nmap -sV -sC <target> -oA <output-dir>/nmap-quick
```
- `-sV`: Service version detection
- `-sC`: Run default NSE scripts
- `-oA`: Output in all formats (normal, XML, grepable)
- Scans top 1000 most common ports ONLY
- Typical duration: 1-3 minutes
- **Limitation**: May miss services on non-standard ports

## Scan Workflow

### Default Workflow (Two-Phase Strategy)

**Phase 1: Port Discovery**
1. Run fast SYN scan: `sudo nmap -p- <target> -oA <output-dir>/nmap-portscan`
2. Check for "Host seems down" and retry with `-Pn` if needed
3. Wait for scan to complete (typically 1-3 minutes)

**Phase 2: Service Detection**
4. Parse open ports from Phase 1 results
5. Run targeted service detection: `nmap -p <OPEN_PORTS> -sV -sC <target> -oA <output-dir>/nmap-services`
6. Wait for scan to complete (typically 1-3 minutes)

**Phase 3: Analysis**
7. Review the service detection results to determine:
   - What services are running?
   - What versions are detected?
   - Are there any interesting services (web, SSH, database, IoT protocols)?
   - Do NSE scripts reveal any issues?

### Additional Targeted Scans (Optional)
Based on service detection results, run specialized scans:

**If web services found (80, 443, 8080, etc.)**:
```bash
nmap -p 80,443,8080,8443 --script http-* <target> -oA <output-dir>/nmap-web
```

**If SSH found**:
```bash
nmap -p 22 --script ssh-* <target> -oA <output-dir>/nmap-ssh
```

**If RTSP found (554)**:
```bash
nmap -p 554 --script rtsp-* <target> -oA <output-dir>/nmap-rtsp
```

**If ONVIF/camera suspected**:
```bash
nmap -p 80,554,8000,8080 --script http-methods,http-headers <target> -oA <output-dir>/nmap-onvif
```


## Output Management

### Output Formats
Always use `-oA <prefix>` to generate all three formats:
- `.nmap` - Normal human-readable format
- `.xml` - XML format for parsing/importing into tools
- `.gnmap` - Grepable format for command-line processing


## Timing and Performance

### Timing Templates
Use `-T<0-5>` to control scan speed:
- `-T0` (Paranoid): Extremely slow, for IDS evasion
- `-T1` (Sneaky): Very slow, for IDS evasion
- `-T2` (Polite): Slow, less bandwidth intensive
- `-T3` (Normal): Default, balanced speed
- `-T4` (Aggressive): Fast, recommended for modern networks
- `-T5` (Insane): Very fast, may miss results

**Default**: Use `-T3` or omit (default is T3)
**Fast scans**: Use `-T4` when speed is important and network can handle it
**Stealth**: Use `-T1` or `-T2` for evasion

### Timeout Considerations
- Phase 1 Port Discovery (sudo nmap -p-): 180-300 seconds timeout (3-5 minutes)
- Phase 2 Service Detection (nmap -p <ports> -sV -sC): 120-180 seconds timeout (2-3 minutes)
- UDP scan: 600+ seconds timeout (very slow)

## Network Ranges

### Single Host
```bash
nmap <ip-address>
```

### CIDR Notation
```bash
nmap 192.168.1.0/24
```

### IP Range
```bash
nmap 192.168.1.1-254
```

### Multiple Hosts
```bash
nmap 192.168.1.1 192.168.1.10 192.168.1.100
```

### Exclude Hosts
```bash
nmap 192.168.1.0/24 --exclude 192.168.1.1,192.168.1.254
```

## NSE Scripts

### Common Script Categories
```bash
# Authentication scripts
nmap --script auth <target>

# Brute force scripts
nmap --script brute <target>

# Default safe scripts
nmap -sC <target>  # equivalent to --script default

# Discovery scripts
nmap --script discovery <target>

# Vulnerability scripts
nmap --script vuln <target>

# All HTTP scripts
nmap --script "http-*" <target>
```

### IoT-Specific Scripts
```bash
# RTSP enumeration
nmap -p 554 --script rtsp-methods,rtsp-url-brute <target>

# UPnP discovery
nmap -p 1900 --script upnp-info <target>

# MQTT discovery
nmap -p 1883,8883 --script mqtt-subscribe <target>

# Modbus enumeration
nmap -p 502 --script modbus-discover <target>
```

## Result Analysis

### Key Information to Extract

1. **Open Ports and Services**
   - What ports are open?
   - What services are running?
   - What versions are detected?

2. **Service Fingerprints**
   - Does version detection reveal outdated software?
   - Are there known vulnerabilities for detected versions?

3. **NSE Script Results**
   - Authentication issues?
   - Information disclosure?
   - Misconfigurations?

4. **Operating System**
   - What OS is running?
   - What OS version?

### Parsing Nmap Output

**Extract open ports**:
```bash
grep "^[0-9]" nmap-output.nmap | grep "open"
```

**Extract service versions**:
```bash
grep -E "^[0-9]+/tcp.*open" nmap-output.nmap
```

**Check for vulnerabilities in NSE output**:
```bash
grep -i "vuln\|cve\|exploit" nmap-output.nmap
```

## Common IoT Service Ports

When scanning IoT devices, pay special attention to:

| Port | Service | Description |
|------|---------|-------------|
| 21 | FTP | File transfer (often misconfigured) |
| 22 | SSH | Remote administration |
| 23 | Telnet | Insecure remote access |
| 80 | HTTP | Web interface |
| 443 | HTTPS | Secure web interface |
| 554 | RTSP | Video streaming |
| 1883 | MQTT | IoT messaging protocol |
| 3702 | WS-Discovery | ONVIF device discovery |
| 5000 | UPnP | Universal Plug and Play |
| 8000 | HTTP Alt | Alternative HTTP port |
| 8080 | HTTP Proxy | Alternative HTTP port |
| 8883 | MQTT/TLS | Secure MQTT |

## Best Practices

### 1. Always Save Output
Never run nmap without saving output:
```bash
# GOOD
nmap -p <ports> -sV -sC <target> -oA output/nmap-services

# BAD
nmap -sV -sC <target>
```

### 2. Always Use Two-Phase Strategy
Always use the default two-phase strategy unless explicitly told otherwise:
```bash
# Phase 1: Fast port discovery
sudo nmap -p- <target> -oA nmap-portscan

# Phase 2: Service detection on open ports
nmap -p <OPEN_PORTS> -sV -sC <target> -oA nmap-services
```

### 3. Use Appropriate Timing
Match timing to your needs:
```bash
# Pentest with authorization: Fast
nmap -sV -sC -T4 <target>

# Red team/stealth: Slow
nmap -sV -sC -T2 <target>
```

### 4. Document Scan Parameters
Always document:
- What scan type was used?
- What date/time was scan performed?
- What were the scan results?
- Any anomalies or errors?

### 5. Respect Authorization
- Only scan systems you have permission to scan
- Respect scope limitations
- Be aware of scan impact on production systems
- Use appropriate timing to avoid DoS

## Integration with IoT Testing Workflow

### For IoT Pentests
1. Run default two-phase scan (port discovery + service detection)
2. Run wsdiscovery if ONVIF suspected based on open ports
3. Run onvifscan if port 80/554 open on camera
4. Run targeted HTTP scripts if web interface found

### Output Directory Usage
Always save to an organized output directory:
```bash
OUTPUT_DIR="./nmap-output"
mkdir -p "$OUTPUT_DIR"

# Phase 1: Port discovery
sudo nmap -p- <target> -oA "$OUTPUT_DIR/nmap-portscan"

# Phase 2: Service detection
nmap -p <OPEN_PORTS> -sV -sC <target> -oA "$OUTPUT_DIR/nmap-services"
```

## Troubleshooting

### Scan Taking Too Long
- Use `-T4` for faster scanning
- Limit port range: `-p 1-1000` instead of `-p-`
- Use `--top-ports 100` instead of all ports

### No Results / Firewalled
- Try different scan types: `-sS`, `-sT`, `-sA`
- Use `-Pn` to skip host discovery
- Try `-f` for fragmented packets
- Consider using `--source-port 53` or other trusted ports

### Requires Root/Sudo
These scan types require root:
- `-sS` (SYN scan)
- `-sU` (UDP scan)
- `-O` (OS detection)
- Raw packet features

### Permission Denied Errors
If you see "Permission denied" or "Operation not permitted":
```bash
# Run with sudo
sudo nmap <options> <target>
```

## Example Workflows

### Workflow 1: Standard Single Target Scan (Default)
```bash
TARGET="192.168.1.100"
OUTPUT_DIR="./nmap-output"
mkdir -p "$OUTPUT_DIR"

# Phase 1: Fast port discovery
sudo nmap -p- $TARGET -oA "$OUTPUT_DIR/nmap-portscan"

# Check for "Host seems down"
if grep -q "Host seems down" "$OUTPUT_DIR/nmap-portscan.nmap"; then
    sudo nmap -p- -Pn $TARGET -oA "$OUTPUT_DIR/nmap-portscan"
fi

# Parse open ports
OPEN_PORTS=$(grep "^[0-9]" "$OUTPUT_DIR/nmap-portscan.nmap" | grep "open" | cut -d'/' -f1 | tr '\n' ',' | sed 's/,$//')

# Phase 2: Service detection
if [ -n "$OPEN_PORTS" ]; then
    nmap -p "$OPEN_PORTS" -sV -sC $TARGET -oA "$OUTPUT_DIR/nmap-services"
fi
```

### Workflow 2: IoT Camera Testing
```bash
OUTPUT_DIR="./nmap-output"
mkdir -p "$OUTPUT_DIR"

# 1. Run default two-phase scan
sudo nmap -p- 192.168.1.100 -oA "$OUTPUT_DIR/nmap-portscan"
OPEN_PORTS=$(grep "^[0-9]" "$OUTPUT_DIR/nmap-portscan.nmap" | grep "open" | cut -d'/' -f1 | tr '\n' ',' | sed 's/,$//')
nmap -p "$OPEN_PORTS" -sV -sC 192.168.1.100 -oA "$OUTPUT_DIR/nmap-services"

# 2. If ONVIF camera detected, check HTTP methods
nmap -p 80 --script http-methods 192.168.1.100 -oA "$OUTPUT_DIR/nmap-http"

# 3. Check RTSP service
nmap -p 554 --script rtsp-methods 192.168.1.100 -oA "$OUTPUT_DIR/nmap-rtsp"
```

### Workflow 3: Additional UDP/OS Detection
```bash
OUTPUT_DIR="./nmap-output"

# After completing default two-phase scan, optionally add:

# UDP scan (top ports)
sudo nmap -sU --top-ports 100 <target> -oA "$OUTPUT_DIR/nmap-udp"

# OS detection
sudo nmap -O <target> -oA "$OUTPUT_DIR/nmap-os"

# Vulnerability scan
nmap -sV --script vuln <target> -oA "$OUTPUT_DIR/nmap-vuln"
```

## Questions to Ask User

Before starting scans, clarify:

1. **Target**: What is the IP address or network range?
2. **Scope**: Single host or network range?
3. **Scan Type**: Use default two-phase strategy or user has specific requirements?
4. **Authorization**: Do you have permission to scan this target?
5. **Special interests**: Any specific services or ports to focus on after initial scan?

Note: Output is saved to `./nmap-output/` by default.

## Success Criteria

A successful nmap scan includes:

- Phase 1 port discovery completed without errors
- Phase 2 service detection completed on all open ports
- Results saved in all formats (-oA) in output directory
- Open ports identified with service versions
- NSE scripts executed successfully
- Results documented and ready for analysis
- Clear summary provided showing:
  - Number of open ports found
  - Key services detected
  - Location of output files
