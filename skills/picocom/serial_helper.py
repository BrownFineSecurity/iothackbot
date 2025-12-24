#!/usr/bin/env python3
"""
Serial Helper for IoT Device UART Console Interaction
Provides clean command execution and output parsing for serial console devices.
"""

import serial
import time
import argparse
import sys
import re
import json
import subprocess
from typing import Optional, List, Tuple, Dict
from datetime import datetime


class SerialHelper:
    """
    Helper class for interacting with serial console devices.
    Handles connection, command execution, prompt detection, and output cleaning.
    """

    # Common prompt patterns for IoT devices
    DEFAULT_PROMPT_PATTERNS = [
        r'User@[^>]+>',           # User@/root>
        r'[#\$]\s*$',             # # or $
        r'root@[^#]+#',           # root@device#
        r'=>\s*$',                # U-Boot =>
        r'U-Boot>',               # U-Boot>
        r'>\s*$',                 # Generic >
        r'login:\s*$',            # Login prompt
        r'Password:\s*$',         # Password prompt
    ]

    def __init__(self, device: str, baud: int = 115200, timeout: float = 3.0,
                 prompt_pattern: Optional[str] = None, debug: bool = False,
                 logfile: Optional[str] = None):
        """
        Initialize serial helper.

        Args:
            device: Serial device path (e.g., /dev/ttyUSB0)
            baud: Baud rate (default: 115200)
            timeout: Read timeout in seconds (default: 3.0)
            prompt_pattern: Custom regex pattern for prompt detection
            debug: Enable debug output
            logfile: Optional file path to log all I/O
        """
        self.device = device
        self.baud = baud
        self.timeout = timeout
        self.debug = debug
        self.serial = None
        self.detected_prompt = None
        self.logfile = None

        # Setup prompt patterns
        if prompt_pattern:
            self.prompt_patterns = [re.compile(prompt_pattern)]
        else:
            self.prompt_patterns = [re.compile(p) for p in self.DEFAULT_PROMPT_PATTERNS]

        # Track command history
        self.command_history = []

        # Open logfile if specified
        if logfile:
            try:
                self.logfile = open(logfile, 'a', buffering=1)  # Line buffered
                self._log(f"\n{'='*60}\n")
                self._log(f"Session started: {datetime.now().isoformat()}\n")
                self._log(f"Device: {device} @ {baud} baud\n")
                self._log(f"{'='*60}\n")
            except IOError as e:
                print(f"Warning: Could not open logfile {logfile}: {e}", file=sys.stderr)
                self.logfile = None

    def _debug_print(self, msg: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def _log(self, data: str):
        """Write data to logfile if enabled."""
        if self.logfile:
            self.logfile.write(data)
            self.logfile.flush()

    def connect(self, skip_prompt_detection: bool = False) -> bool:
        """
        Establish serial connection.

        Args:
            skip_prompt_detection: Skip prompt detection for passive monitoring (default: False)

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._debug_print(f"Connecting to {self.device} at {self.baud} baud...")
            self.serial = serial.Serial(
                port=self.device,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )

            # Clear any existing data
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            if not skip_prompt_detection:
                # Send a newline to get initial prompt
                self._send_raw("\r\n")
                time.sleep(0.5)

                # Try to detect prompt
                initial_output = self._read_raw(timeout=1.0)
                self._detect_prompt(initial_output)

                self._debug_print(f"Connected successfully. Detected prompt: {self.detected_prompt}")
            else:
                self._debug_print(f"Connected successfully (passive monitoring mode)")

            return True

        except serial.SerialException as e:
            print(f"Error connecting to {self.device}: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return False

    def disconnect(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self._debug_print("Disconnecting...")
            self.serial.close()
            self.serial = None

        if self.logfile:
            self._log(f"\n{'='*60}\n")
            self._log(f"Session ended: {datetime.now().isoformat()}\n")
            self._log(f"{'='*60}\n\n")
            self.logfile.close()
            self.logfile = None

    def _send_raw(self, data: str):
        """Send raw data to serial port."""
        if self.serial and self.serial.is_open:
            self.serial.write(data.encode('utf-8'))
            self.serial.flush()
            self._log(data)  # Log sent data

    def _read_raw(self, timeout: Optional[float] = None) -> str:
        """
        Read raw data from serial port.

        Args:
            timeout: Optional custom timeout for this read

        Returns:
            Decoded string from serial port
        """
        if not self.serial or not self.serial.is_open:
            return ""

        original_timeout = self.serial.timeout
        if timeout is not None:
            self.serial.timeout = timeout

        try:
            output = b""
            start_time = time.time()
            while True:
                if self.serial.in_waiting:
                    chunk = self.serial.read(self.serial.in_waiting)
                    output += chunk
                    self._debug_print(f"Read {len(chunk)} bytes")
                else:
                    # Check if we've exceeded timeout
                    if time.time() - start_time > (timeout or self.timeout):
                        break
                    time.sleep(0.05)

            decoded = output.decode('utf-8', errors='replace')
            self._log(decoded)  # Log received data
            return decoded
        finally:
            self.serial.timeout = original_timeout

    def _detect_prompt(self, text: str):
        """
        Detect prompt pattern in text.

        Args:
            text: Text to search for prompt
        """
        lines = text.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line:
                for pattern in self.prompt_patterns:
                    if pattern.search(line):
                        self.detected_prompt = pattern.pattern
                        self._debug_print(f"Detected prompt pattern: {self.detected_prompt}")
                        return

    def _wait_for_prompt(self, timeout: Optional[float] = None) -> Tuple[str, bool]:
        """
        Read until prompt is detected or timeout occurs.

        Args:
            timeout: Optional custom timeout

        Returns:
            Tuple of (output, prompt_found)
        """
        output = ""
        start_time = time.time()
        timeout_val = timeout or self.timeout

        while True:
            chunk = self._read_raw(timeout=0.1)
            if chunk:
                output += chunk
                self._debug_print(f"Accumulated {len(output)} chars")

                # Check if prompt is in the output
                for pattern in self.prompt_patterns:
                    if pattern.search(output.split('\n')[-1]):
                        self._debug_print("Prompt detected")
                        return output, True

            # Check timeout
            if time.time() - start_time > timeout_val:
                self._debug_print("Timeout waiting for prompt")
                return output, False

            time.sleep(0.05)

    def _clean_output(self, raw_output: str, command: str) -> str:
        """
        Clean command output by removing echoes, prompts, and ANSI codes.

        Args:
            raw_output: Raw output from serial
            command: Command that was sent

        Returns:
            Cleaned output
        """
        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', raw_output)

        # Split into lines
        lines = cleaned.split('\n')

        # Remove empty lines and prompts
        result_lines = []
        for line in lines:
            line = line.strip('\r\n')

            # Skip empty lines
            if not line.strip():
                continue

            # Skip lines that are just the command echo
            if line.strip() == command.strip():
                continue

            # Skip lines that match prompt patterns
            is_prompt = False
            for pattern in self.prompt_patterns:
                if pattern.search(line):
                    is_prompt = True
                    break
            if is_prompt:
                continue

            result_lines.append(line)

        return '\n'.join(result_lines)

    def send_command(self, command: str, timeout: Optional[float] = None,
                    clean: bool = True) -> Tuple[str, bool]:
        """
        Send command and wait for output.

        Args:
            command: Command to send
            timeout: Optional custom timeout
            clean: Whether to clean the output (remove echoes, prompts)

        Returns:
            Tuple of (output, success)
        """
        if not self.serial or not self.serial.is_open:
            return "", False

        self._debug_print(f"Sending command: {command}")

        # Clear input buffer
        self.serial.reset_input_buffer()

        # Send command with carriage return
        self._send_raw(f"{command}\r\n")

        # Small delay to let command be processed
        time.sleep(0.1)

        # Wait for prompt
        raw_output, prompt_found = self._wait_for_prompt(timeout)

        # Track command
        self.command_history.append({
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'success': prompt_found,
            'raw_output': raw_output[:200] + '...' if len(raw_output) > 200 else raw_output
        })

        # Clean output if requested
        if clean:
            output = self._clean_output(raw_output, command)
        else:
            output = raw_output

        self._debug_print(f"Command completed. Success: {prompt_found}")
        return output, prompt_found

    def send_commands(self, commands: List[str], delay: float = 0.5) -> List[dict]:
        """
        Send multiple commands in sequence.

        Args:
            commands: List of commands to send
            delay: Delay between commands in seconds

        Returns:
            List of dictionaries with command results
        """
        results = []
        for command in commands:
            output, success = self.send_command(command)
            results.append({
                'command': command,
                'output': output,
                'success': success
            })
            if delay > 0:
                time.sleep(delay)
        return results

    def interactive_mode(self):
        """
        Enter interactive mode where user can type commands.
        Type 'exit' or Ctrl-C to quit.
        """
        print(f"Interactive mode - connected to {self.device}")
        print("Type 'exit' or press Ctrl-C to quit")
        print("-" * 50)

        try:
            while True:
                try:
                    command = input(">>> ")
                    if command.strip().lower() in ('exit', 'quit'):
                        break

                    if not command.strip():
                        continue

                    output, success = self.send_command(command)
                    print(output)

                    if not success:
                        print("[WARNING] Command may have timed out or failed", file=sys.stderr)

                except EOFError:
                    break

        except KeyboardInterrupt:
            print("\nExiting interactive mode...")

    def monitor_mode(self, duration: float = 30.0, trigger_script: Optional[str] = None,
                     trigger_delay: float = 5.0, baseline_duration: float = 0.0) -> Dict:
        """
        Passive monitoring mode - continuously read serial output.
        Optionally run an external trigger script and capture before/during/after output.

        Args:
            duration: Total monitoring duration in seconds (default: 30.0)
            trigger_script: Optional external script/command to run
            trigger_delay: Seconds to wait before running trigger (default: 5.0)
            baseline_duration: Seconds to capture baseline before trigger (if 0, trigger runs immediately)

        Returns:
            Dictionary with monitoring results including baseline, trigger, and post-trigger output
        """
        if not self.serial or not self.serial.is_open:
            return {'error': 'Serial connection not open'}

        print(f"Monitor mode - capturing for {duration} seconds")
        if trigger_script:
            print(f"Trigger script: {trigger_script}")
            print(f"Trigger will run after {trigger_delay} seconds")
        print("-" * 50)

        result = {
            'duration': duration,
            'trigger_script': trigger_script,
            'trigger_delay': trigger_delay,
            'baseline_duration': baseline_duration,
            'baseline_output': [],
            'trigger_output': [],
            'post_trigger_output': [],
            'trigger_executed': False,
            'trigger_exit_code': None,
            'trigger_timestamp': None,
            'timeline': []
        }

        start_time = time.time()
        trigger_time = start_time + trigger_delay
        baseline_end_time = start_time + baseline_duration if baseline_duration > 0 else start_time
        trigger_executed = False

        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time

                # Check if we've exceeded total duration
                if elapsed >= duration:
                    break

                # Read available data
                if self.serial.in_waiting:
                    chunk = self.serial.read(self.serial.in_waiting)
                    decoded = chunk.decode('utf-8', errors='replace')
                    timestamp = datetime.now().isoformat()

                    # Log to file if enabled
                    self._log(decoded)

                    # Categorize output based on timeline
                    timeline_entry = {
                        'timestamp': timestamp,
                        'elapsed': elapsed,
                        'data': decoded
                    }

                    if current_time < baseline_end_time:
                        # Baseline period
                        result['baseline_output'].append(decoded)
                        timeline_entry['phase'] = 'baseline'
                    elif trigger_executed:
                        # Post-trigger period
                        result['post_trigger_output'].append(decoded)
                        timeline_entry['phase'] = 'post_trigger'
                    else:
                        # Pre-trigger or during trigger
                        result['trigger_output'].append(decoded)
                        timeline_entry['phase'] = 'trigger'

                    result['timeline'].append(timeline_entry)

                    # Print to console with timestamp
                    print(f"[{elapsed:6.2f}s] {decoded}", end='', flush=True)

                # Execute trigger script if it's time
                if trigger_script and not trigger_executed and current_time >= trigger_time:
                    print(f"\n{'='*50}")
                    print(f"[TRIGGER] Executing: {trigger_script}")
                    print(f"{'='*50}")

                    result['trigger_timestamp'] = datetime.now().isoformat()

                    try:
                        # Execute the trigger script
                        proc = subprocess.run(
                            trigger_script,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=min(30, duration - elapsed - 1)  # Don't exceed remaining time
                        )
                        result['trigger_exit_code'] = proc.returncode
                        result['trigger_executed'] = True

                        print(f"[TRIGGER] Exit code: {proc.returncode}")
                        if proc.stdout:
                            print(f"[TRIGGER] stdout: {proc.stdout[:200]}")
                        if proc.stderr:
                            print(f"[TRIGGER] stderr: {proc.stderr[:200]}", file=sys.stderr)

                    except subprocess.TimeoutExpired:
                        print(f"[TRIGGER] WARNING: Script timed out", file=sys.stderr)
                        result['trigger_exit_code'] = -1
                        result['trigger_executed'] = True
                    except Exception as e:
                        print(f"[TRIGGER] ERROR: {e}", file=sys.stderr)
                        result['trigger_exit_code'] = -2
                        result['trigger_executed'] = True

                    trigger_executed = True
                    print(f"{'='*50}\n")

                # Small sleep to avoid busy-waiting
                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n\nMonitoring interrupted by user")
            result['interrupted'] = True

        # Calculate summary statistics
        total_baseline = ''.join(result['baseline_output'])
        total_trigger = ''.join(result['trigger_output'])
        total_post = ''.join(result['post_trigger_output'])

        result['summary'] = {
            'baseline_bytes': len(total_baseline),
            'trigger_bytes': len(total_trigger),
            'post_trigger_bytes': len(total_post),
            'total_bytes': len(total_baseline) + len(total_trigger) + len(total_post),
            'baseline_lines': len(total_baseline.split('\n')) if total_baseline else 0,
            'trigger_lines': len(total_trigger.split('\n')) if total_trigger else 0,
            'post_trigger_lines': len(total_post.split('\n')) if total_post else 0,
        }

        print(f"\n{'='*50}")
        print(f"Monitoring complete")
        print(f"Captured {result['summary']['total_bytes']} bytes total")
        if trigger_script:
            print(f"Baseline: {result['summary']['baseline_bytes']} bytes")
            print(f"During trigger: {result['summary']['trigger_bytes']} bytes")
            print(f"Post-trigger: {result['summary']['post_trigger_bytes']} bytes")
        print(f"{'='*50}")

        return result


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Serial Helper for IoT UART Console Interaction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single command
  %(prog)s --device /dev/ttyUSB0 --command "help"

  # Interactive mode
  %(prog)s --device /dev/ttyUSB0 --interactive

  # Batch commands from file
  %(prog)s --device /dev/ttyUSB0 --script commands.txt

  # Monitor mode - passive listening for 30 seconds
  %(prog)s --device /dev/ttyUSB0 --monitor --duration 30

  # Monitor with external trigger script
  %(prog)s --device /dev/ttyUSB0 --monitor --duration 60 \\
    --trigger-script "python3 /path/to/test_script.py" \\
    --trigger-delay 5

  # Monitor with baseline capture before trigger
  %(prog)s --device /dev/ttyUSB0 --monitor --duration 60 \\
    --trigger-script "./test.sh" \\
    --baseline-duration 10 \\
    --trigger-delay 15

  # Custom baud rate and timeout
  %(prog)s --device /dev/ttyUSB0 --baud 57600 --timeout 5 --command "ps"

  # Raw output (no cleaning)
  %(prog)s --device /dev/ttyUSB0 --command "help" --raw

  # JSON output for scripting
  %(prog)s --device /dev/ttyUSB0 --command "help" --json

  # Log all I/O to file (tail -f in another terminal to watch)
  %(prog)s --device /dev/ttyUSB0 --command "help" --logfile session.log
        """
    )

    # Connection arguments
    parser.add_argument('--device', '-d', default='/dev/ttyUSB0',
                       help='Serial device path (default: /dev/ttyUSB0)')
    parser.add_argument('--baud', '-b', type=int, default=115200,
                       help='Baud rate (default: 115200)')
    parser.add_argument('--timeout', '-t', type=float, default=3.0,
                       help='Read timeout in seconds (default: 3.0)')
    parser.add_argument('--prompt', '-p', type=str,
                       help='Custom prompt regex pattern')

    # Mode arguments (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--command', '-c', type=str,
                           help='Single command to execute')
    mode_group.add_argument('--interactive', '-i', action='store_true',
                           help='Enter interactive mode')
    mode_group.add_argument('--script', '-s', type=str,
                           help='File containing commands to execute (one per line)')
    mode_group.add_argument('--monitor', '-m', action='store_true',
                           help='Passive monitoring mode (just listen, no commands)')

    # Monitor mode specific arguments
    parser.add_argument('--duration', type=float, default=30.0,
                       help='Monitoring duration in seconds (default: 30.0)')
    parser.add_argument('--trigger-script', type=str,
                       help='External script/command to run during monitoring')
    parser.add_argument('--trigger-delay', type=float, default=5.0,
                       help='Seconds to wait before running trigger (default: 5.0)')
    parser.add_argument('--baseline-duration', type=float, default=0.0,
                       help='Seconds to capture baseline before trigger (default: 0.0)')

    # Output arguments
    parser.add_argument('--raw', '-r', action='store_true',
                       help='Output raw response (no cleaning)')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output in JSON format')
    parser.add_argument('--logfile', '-l', type=str,
                       help='Log all I/O to file (can tail -f in another terminal)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')

    args = parser.parse_args()

    # Create serial helper
    helper = SerialHelper(
        device=args.device,
        baud=args.baud,
        timeout=args.timeout,
        prompt_pattern=args.prompt,
        debug=args.debug,
        logfile=args.logfile
    )

    # Connect to device
    # Skip prompt detection in monitor mode (passive listening)
    skip_prompt = args.monitor if hasattr(args, 'monitor') else False
    if not helper.connect(skip_prompt_detection=skip_prompt):
        sys.exit(1)

    try:
        if args.monitor:
            # Monitor mode
            result = helper.monitor_mode(
                duration=args.duration,
                trigger_script=args.trigger_script,
                trigger_delay=args.trigger_delay,
                baseline_duration=args.baseline_duration
            )

            if args.json:
                # Convert output lists to single strings for JSON
                json_result = result.copy()
                json_result['baseline_output'] = ''.join(result['baseline_output'])
                json_result['trigger_output'] = ''.join(result['trigger_output'])
                json_result['post_trigger_output'] = ''.join(result['post_trigger_output'])
                # Remove timeline to reduce JSON size (can be very large)
                if 'timeline' in json_result and len(json_result['timeline']) > 100:
                    json_result['timeline_count'] = len(json_result['timeline'])
                    json_result['timeline'] = json_result['timeline'][:10] + ['... truncated ...'] + json_result['timeline'][-10:]
                print(json.dumps(json_result, indent=2))

            sys.exit(0 if not result.get('error') else 1)

        elif args.interactive:
            # Interactive mode
            helper.interactive_mode()

        elif args.command:
            # Single command mode
            output, success = helper.send_command(args.command, clean=not args.raw)

            if args.json:
                result = {
                    'command': args.command,
                    'output': output,
                    'success': success
                }
                print(json.dumps(result, indent=2))
            else:
                print(output)

            sys.exit(0 if success else 1)

        elif args.script:
            # Batch script mode
            try:
                with open(args.script, 'r') as f:
                    commands = [line.strip() for line in f if line.strip() and not line.startswith('#')]

                results = helper.send_commands(commands)

                if args.json:
                    print(json.dumps(results, indent=2))
                else:
                    for i, result in enumerate(results, 1):
                        print(f"\n{'='*50}")
                        print(f"Command {i}: {result['command']}")
                        print(f"{'='*50}")
                        print(result['output'])
                        if not result['success']:
                            print("[WARNING] Command may have failed", file=sys.stderr)

                # Exit with error if any command failed
                if not all(r['success'] for r in results):
                    sys.exit(1)

            except FileNotFoundError:
                print(f"Error: Script file '{args.script}' not found", file=sys.stderr)
                sys.exit(1)
            except IOError as e:
                print(f"Error reading script file: {e}", file=sys.stderr)
                sys.exit(1)

    finally:
        helper.disconnect()


if __name__ == '__main__':
    main()
