# Observing Serial Console Sessions

This guide explains how to monitor and observe what's happening on the serial console in real-time while the helper script or skill is interacting with the device.

## Method 1: Built-in Logging (Easiest - RECOMMENDED)

The `serial_helper.py` script now includes built-in session logging that captures all I/O in real-time.

### Usage

**Terminal 1 - Run the helper script with logging:**
```bash
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --prompt "User@[^>]+>" \
  --logfile /tmp/serial_session.log \
  --interactive
```

**Terminal 2 - Watch the log in real-time:**
```bash
tail -f /tmp/serial_session.log
```

### What Gets Logged

The logfile captures:
- Session start/end timestamps
- All data sent to the device (commands)
- All data received from the device (responses, prompts, echoes)
- Raw I/O exactly as it appears on the wire

### Example Log Output

```
============================================================
Session started: 2025-10-19T23:20:27.384436
Device: /dev/ttyUSB0 @ 115200 baud
============================================================


User@/root>
User@/root>date
date
Thu Dec  1 00:10:11 GMT+5 2011

User@/root>
User@/root>ifconfig
ifconfig
eth0      Link encap:Ethernet  HWaddr E4:F1:4C:77:66:08
          inet addr:192.168.1.27  Bcast:192.168.1.255  Mask:255.255.255.0
[...]

============================================================
Session ended: 2025-10-19T23:20:29.130706
============================================================
```

### Advantages

✅ No additional setup required
✅ Works with all modes (single command, interactive, batch)
✅ Doesn't interfere with the serial connection
✅ Can be tailed from another terminal
✅ Captures exact I/O timing
✅ Persistent record for later analysis

### Limitations

❌ Not truly real-time (buffered, but line-buffered so minimal delay)
❌ Requires specifying logfile when starting

## Method 2: Using socat for Port Mirroring (Advanced)

For true real-time observation or when you need multiple simultaneous connections, use `socat` to create a virtual serial port that mirrors the real one.

### Setup

**Terminal 1 - Create virtual port with socat:**
```bash
sudo socat -d -d \
  PTY,raw,echo=0,link=/tmp/vserial0 \
  PTY,raw,echo=0,link=/tmp/vserial1
```

This creates two linked virtual serial ports that mirror each other.

**Terminal 2 - Bridge real device to one virtual port:**
```bash
sudo socat /dev/ttyUSB0,raw,echo=0,b115200 /tmp/vserial0
```

**Terminal 3 - Use helper script on the bridge:**
```bash
python3 .claude/skills/picocom/serial_helper.py \
  --device /tmp/vserial1 \
  --prompt "User@[^>]+>" \
  --interactive
```

**Terminal 4 - Observe on picocom:**
```bash
picocom -b 115200 --nolock --echo --omap crlf /tmp/vserial0
```

### Advantages

✅ True real-time observation
✅ Multiple processes can "spy" on the connection
✅ Can use picocom with full interactive features
✅ Most flexible approach

### Limitations

❌ Complex setup with multiple terminals
❌ Requires socat installed
❌ Requires root/sudo for some operations
❌ More potential for errors

## Method 3: Using screen with Logging

If you prefer `screen` over `picocom`, you can use its built-in logging feature.

### Usage

**Start screen with logging:**
```bash
screen -L -Logfile /tmp/serial_screen.log /dev/ttyUSB0 115200
```

Then in another terminal:
```bash
tail -f /tmp/serial_screen.log
```

### Advantages

✅ Built into screen
✅ Simple to use
✅ Good for manual interaction

### Limitations

❌ Not suitable for automated scripting
❌ Less control over output format
❌ Requires screen (not picocom)

## Method 4: Direct Device File Monitoring (Read-Only Spy)

For read-only observation without interfering with the helper script:

**Terminal 1 - Run helper script normally:**
```bash
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --interactive
```

**Terminal 2 - Spy on the device (read-only):**
```bash
# This reads without opening the port exclusively
cat /dev/ttyUSB0 | tee /tmp/spy.log
```

### Warnings

⚠️ This method is unreliable:
- May miss data that was read by the helper script
- Can cause timing issues
- Not recommended for production use
- **Only use for debugging if other methods don't work**

## Comparison Matrix

| Method | Real-time | Easy Setup | Multi-Observer | Reliable | Recommended |
|--------|-----------|------------|----------------|----------|-------------|
| Built-in Logging | Near | ✅ Yes | Limited | ✅ Yes | ⭐ **Best** |
| socat Mirror | ✅ Yes | ❌ Complex | ✅ Yes | ✅ Yes | Advanced |
| screen -L | Near | ✅ Yes | Limited | ✅ Yes | Manual use |
| cat spy | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ⚠️ Last resort |

## Recommended Workflow

### For Claude Code Skill Usage

When Claude is using the skill to interact with your device:

1. **Before starting**, set up a log watcher:
   ```bash
   # Terminal 1
   touch /tmp/device_session.log
   tail -f /tmp/device_session.log
   ```

2. **Tell Claude to use logging**:
   ```
   Please enumerate the device and log the session to /tmp/device_session.log
   ```

3. **Watch Terminal 1** to see real-time I/O

### For Manual Debugging

1. Use the interactive mode with logging:
   ```bash
   python3 .claude/skills/picocom/serial_helper.py \
     --device /dev/ttyUSB0 \
     --prompt "User@[^>]+>" \
     --logfile /tmp/debug.log \
     --debug \
     --interactive
   ```

2. In another terminal, watch the log:
   ```bash
   tail -f /tmp/debug.log
   ```

3. Debug output goes to stderr, log goes to the file

### For Multiple Simultaneous Connections

If you need both automated scripting AND manual interaction:

1. Set up socat bridge (see Method 2)
2. Run helper script on one virtual port
3. Use picocom on the other virtual port
4. Both can interact simultaneously

## Example: Watching Claude Enumerate a Device

**Terminal 1 - Start log watcher:**
```bash
tail -f /tmp/device_enum.log
```

**Terminal 2 - Run Claude Code and tell it:**
```
Please enumerate the Uniview camera using the serial helper with
--logfile /tmp/device_enum.log so I can watch what's happening
```

**Terminal 1 Output (real-time):**
```
============================================================
Session started: 2025-10-19T23:30:15.123456
Device: /dev/ttyUSB0 @ 115200 baud
============================================================


User@/root>
User@/root>help
help
    logout
    exit
    update
[... you see everything as it happens ...]
```

## Troubleshooting

### Log file not updating

**Problem:** `tail -f` shows nothing

**Solutions:**
```bash
# Make sure the file exists first
touch /tmp/serial_session.log
tail -f /tmp/serial_session.log

# Check if the helper script is actually writing
ls -lh /tmp/serial_session.log

# Try unbuffered tail
tail -f -n +1 /tmp/serial_session.log
```

### Permission denied on /dev/ttyUSB0

**Problem:** Multiple processes trying to access device

**Solutions:**
```bash
# Check what's using it
fuser /dev/ttyUSB0

# Add your user to dialout group
sudo usermod -a -G dialout $USER

# Use --nolock option if needed (already default in helper)
```

### socat "device busy" error

**Problem:** Device already opened

**Solutions:**
```bash
# Kill all processes using the device
sudo fuser -k /dev/ttyUSB0

# Wait a moment
sleep 1

# Try socat again
```

## Best Practices

1. **Always use logging** for important sessions - you can analyze them later
2. **Use descriptive log filenames** with timestamps:
   ```bash
   --logfile "/tmp/device_$(date +%Y%m%d_%H%M%S).log"
   ```

3. **Keep logs for documentation** - they're valuable for reports and analysis

4. **Use --debug with --logfile** to get both debug info and I/O logs:
   ```bash
   python3 .claude/skills/picocom/serial_helper.py \
     --device /dev/ttyUSB0 \
     --command "help" \
     --logfile session.log \
     --debug 2>&1 | tee debug.txt
   ```

5. **Compress old logs** to save space:
   ```bash
   gzip /tmp/old_session.log
   ```

## Security Considerations

⚠️ **Log files may contain sensitive information:**
- Passwords entered during sessions
- Cryptographic keys or tokens
- Network configurations
- Device identifiers

**Recommendations:**
- Store logs in secure locations (not /tmp for sensitive data)
- Use proper file permissions:
  ```bash
  chmod 600 /tmp/sensitive_session.log
  ```
- Shred logs after analysis:
  ```bash
  shred -u /tmp/sensitive_session.log
  ```
- Never commit logs to public repositories

## Summary

**For most use cases:** Use the built-in `--logfile` option and `tail -f` in another terminal. It's simple, reliable, and works well.

**For advanced needs:** Use socat to create a virtual serial port mirror for true real-time observation and multi-process access.

**Key Command:**
```bash
# Start with logging
python3 .claude/skills/picocom/serial_helper.py \
  --device /dev/ttyUSB0 \
  --prompt "User@[^>]+>" \
  --logfile /tmp/session.log \
  --interactive

# Watch in another terminal
tail -f /tmp/session.log
```
