#!/usr/bin/env python3
"""
Capture Analyzer for sigrok-compatible logic analyzer files.

Analyzes digital signal captures (.sr, .csv, .vcd) to identify timing
patterns, decode protocols using sigrok-cli's 131+ decoders, and help
with hardware reverse engineering and CTF challenges.
"""

import argparse
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Add parent directory to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.signal_analysis import (
    analyze_timing as _analyze_timing,
    detect_clusters,
    export_transitions_csv,
    format_duration,
    guess_protocol,
    parse_sample_rate,
    print_histogram,
)


# ============================================================================
# CONSTANTS
# ============================================================================

SUPPORTED_EXTENSIONS = {'.sr', '.csv', '.vcd'}

VCD_TIMESCALE_UNITS = {
    's': 1.0,
    'ms': 1e-3,
    'us': 1e-6,
    'ns': 1e-9,
    'ps': 1e-12,
    'fs': 1e-15,
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CaptureData:
    """Normalized capture data from any supported format."""
    times: np.ndarray           # Transition timestamps in seconds
    initial_state: int          # Starting logic level (0 or 1)
    sample_rate: float          # Hz (estimated if not available)
    channel_name: str           # Name of the analyzed channel
    file_format: str            # 'sr', 'csv', or 'vcd'
    duration: float = 0.0       # Total capture duration in seconds
    total_samples: int = 0      # Total sample count (if known)
    available_channels: List[str] = field(default_factory=list)


# ============================================================================
# SIGROK-CLI INTERACTION
# ============================================================================

def check_sigrok_cli() -> Tuple[bool, str]:
    """Check if sigrok-cli is installed and return version info."""
    try:
        result = subprocess.run(
            ['sigrok-cli', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            return True, version
        return False, "sigrok-cli returned non-zero exit code"
    except FileNotFoundError:
        return False, "sigrok-cli not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "sigrok-cli timed out"
    except Exception as e:
        return False, str(e)


def run_sigrok_cli(args: List[str], timeout: int = 60,
                   binary: bool = False) -> Tuple[int, str, str]:
    """
    Run sigrok-cli with the given arguments.

    Returns (returncode, stdout, stderr).
    """
    cmd = ['sigrok-cli'] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=not binary,
            timeout=timeout
        )
        stdout = result.stdout if not binary else result.stdout.decode('latin-1')
        stderr = result.stderr if not binary else result.stderr.decode('latin-1')
        return result.returncode, stdout, stderr
    except FileNotFoundError:
        return 1, '', 'sigrok-cli not found'
    except subprocess.TimeoutExpired:
        return 1, '', 'sigrok-cli timed out'


def show_file_info(file_path: Path) -> Optional[dict]:
    """
    Show capture file metadata using sigrok-cli --show.

    Returns dict with channels, sample_rate, duration, etc.
    """
    rc, stdout, stderr = run_sigrok_cli(['-i', str(file_path), '--show'])
    if rc != 0:
        return None

    info = {
        'channels': [],
        'sample_rate': 0.0,
        'total_samples': 0,
        'duration': 0.0,
        'raw': stdout,
    }

    for line in stdout.split('\n'):
        line = line.strip()
        if 'samplerate' in line.lower():
            info['sample_rate'] = parse_sample_rate(line)
        elif 'total samples' in line.lower():
            match = re.search(r'(\d+)', line)
            if match:
                info['total_samples'] = int(match.group(1))
        elif line.startswith('D') or line.startswith('CH'):
            info['channels'].append(line.split(':')[0].strip())

    if info['sample_rate'] > 0 and info['total_samples'] > 0:
        info['duration'] = info['total_samples'] / info['sample_rate']

    return info


def list_decoders() -> List[Tuple[str, str]]:
    """
    List available protocol decoders.

    Returns list of (name, description) tuples.
    """
    rc, stdout, stderr = run_sigrok_cli(['-L'])
    if rc != 0:
        return []

    decoders = []
    in_decoders = False

    for line in stdout.split('\n'):
        if 'protocol decoder' in line.lower() or 'Supported protocol decoders' in line:
            in_decoders = True
            continue
        if in_decoders:
            if line.strip() == '' or line.startswith('Supported '):
                if decoders:
                    break
                continue
            match = re.match(r'\s+(\S+)\s*-\s*(.*)', line)
            if match:
                decoders.append((match.group(1).strip(), match.group(2).strip()))

    return decoders


def decode_protocol(file_path: Path, decoder_spec: str,
                    annotations: str = None,
                    sample_numbers: bool = False) -> dict:
    """
    Run sigrok-cli protocol decoder on a capture file.

    Args:
        file_path: Path to .sr, .csv, or .vcd file
        decoder_spec: Decoder specification, e.g. "uart:baudrate=115200"
                      or "i2c,eeprom24xx" for stacked decoders
        annotations: Annotation filter, e.g. "uart=tx-data"
        sample_numbers: Include sample numbers in output

    Returns dict with 'success', 'output', and 'error' keys.
    """
    args = ['-i', str(file_path), '-P', decoder_spec]

    if annotations:
        args.extend(['-A', annotations])
    if sample_numbers:
        args.append('--protocol-decoder-samplenum')

    rc, stdout, stderr = run_sigrok_cli(args)

    return {
        'success': rc == 0,
        'output': stdout,
        'error': stderr if rc != 0 else None,
        'decoder': decoder_spec,
    }


def extract_binary(file_path: Path, decoder_spec: str,
                   binary_spec: str, output_path: Path) -> dict:
    """
    Extract binary data from protocol decoder to a file.

    Args:
        file_path: Input capture file
        decoder_spec: e.g. "uart:baudrate=115200"
        binary_spec: e.g. "uart=tx"
        output_path: Where to write binary output

    Returns dict with 'success' and 'error' keys.
    """
    cmd = [
        'sigrok-cli', '-i', str(file_path),
        '-P', decoder_spec,
        '-B', binary_spec,
    ]
    try:
        with open(output_path, 'wb') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=False,
                timeout=60
            )
        if result.returncode == 0:
            size = output_path.stat().st_size
            return {'success': True, 'size': size, 'error': None}
        else:
            return {
                'success': False,
                'size': 0,
                'error': result.stderr.decode('utf-8', errors='replace'),
            }
    except Exception as e:
        return {'success': False, 'size': 0, 'error': str(e)}


# ============================================================================
# FILE LOADING
# ============================================================================

def load_capture(file_path: Path, channel: str = None) -> CaptureData:
    """
    Load a capture file and return normalized transition data.

    Supports .sr (native parsing, with sigrok-cli fallback), .csv, and .vcd.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format: {suffix} "
            f"(supported: {', '.join(SUPPORTED_EXTENSIONS)})"
        )

    if suffix == '.sr':
        return _load_sr(file_path, channel)
    elif suffix == '.csv':
        return _load_csv(file_path, channel)
    elif suffix == '.vcd':
        return _load_vcd(file_path, channel)


def _load_sr(file_path: Path, channel: str = None) -> CaptureData:
    """Load .sr file, trying native parsing first, falling back to sigrok-cli."""
    # Try native parsing first (no sigrok-cli dependency)
    try:
        return _load_sr_native(file_path, channel)
    except Exception as native_err:
        pass

    # Fall back to sigrok-cli CSV export
    available, _ = check_sigrok_cli()
    if not available:
        raise RuntimeError(
            f"Native .sr parsing failed ({native_err}), "
            f"and sigrok-cli is not installed. "
            f"Install sigrok-cli or check the .sr file."
        )

    info = show_file_info(file_path)
    args = ['-i', str(file_path), '-O', 'csv']
    if channel:
        args.extend(['-C', channel])

    rc, stdout, stderr = run_sigrok_cli(args, timeout=120)
    if rc != 0:
        raise RuntimeError(f"sigrok-cli export failed: {stderr}")

    return _parse_sigrok_csv(
        stdout,
        channel=channel,
        file_format='sr',
        sample_rate=info['sample_rate'] if info else 0.0,
        available_channels=info['channels'] if info else [],
    )


def _load_sr_native(file_path: Path, channel: str = None) -> CaptureData:
    """Parse .sr file natively without sigrok-cli."""
    with zipfile.ZipFile(file_path, 'r') as zf:
        meta = _parse_sr_metadata(zf)

        sample_rate = meta['samplerate']
        if sample_rate <= 0:
            raise ValueError("No sample rate found in .sr metadata")

        unitsize = meta['unitsize']
        total_probes = meta['total_probes']
        capturefile = meta['capturefile']
        probe_names = meta['probes']

        available_channels = [
            probe_names.get(i, f"D{i}") for i in range(total_probes)
        ]

        # Determine which channel to extract
        channel_idx, channel_name = _resolve_sr_channel(
            channel, probe_names, total_probes
        )

        # Read logic data chunks
        packed_data = _read_sr_logic_data(zf, capturefile)

    if len(packed_data) == 0:
        raise ValueError("No logic data found in .sr file")

    # Extract transitions for the selected channel
    times, initial_state = _extract_channel_transitions(
        packed_data, channel_idx, unitsize, sample_rate
    )

    total_samples = len(packed_data) // unitsize
    duration = total_samples / sample_rate

    return CaptureData(
        times=times,
        initial_state=initial_state,
        sample_rate=sample_rate,
        channel_name=channel_name,
        file_format='sr',
        duration=duration,
        total_samples=total_samples,
        available_channels=available_channels,
    )


def _parse_sr_metadata(zf: zipfile.ZipFile) -> Dict:
    """Parse the metadata file from a sigrok .sr ZIP archive."""
    try:
        raw = zf.read('metadata').decode('utf-8')
    except KeyError:
        raise ValueError("No 'metadata' file found in .sr archive")

    meta = {
        'samplerate': 0.0,
        'total_probes': 0,
        'unitsize': 1,
        'capturefile': 'logic-1',
        'probes': {},  # index -> name
    }

    for line in raw.split('\n'):
        line = line.strip()
        if not line or line.startswith('[') or line.startswith(';'):
            continue

        if '=' not in line:
            continue

        key, _, value = line.partition('=')
        key = key.strip().lower()
        value = value.strip()

        if key == 'samplerate':
            # Can be "24000000" or "24 MHz"
            rate = parse_sample_rate(value)
            if rate > 0:
                meta['samplerate'] = rate
            else:
                try:
                    meta['samplerate'] = float(value)
                except ValueError:
                    pass
        elif key == 'total probes':
            try:
                meta['total_probes'] = int(value)
            except ValueError:
                pass
        elif key == 'unitsize':
            try:
                meta['unitsize'] = int(value)
            except ValueError:
                pass
        elif key == 'capturefile':
            meta['capturefile'] = value
        elif re.match(r'^probe(\d+)$', key):
            idx = int(re.match(r'^probe(\d+)$', key).group(1)) - 1  # 0-based
            meta['probes'][idx] = value

    if meta['total_probes'] == 0 and meta['probes']:
        meta['total_probes'] = max(meta['probes'].keys()) + 1

    return meta


def _read_sr_logic_data(zf: zipfile.ZipFile, capturefile: str) -> bytes:
    """Read and concatenate logic data chunks from .sr archive."""
    names = sorted(zf.namelist())
    chunks = []

    # Look for chunked files: logic-1-1, logic-1-2, ... or just logic-1
    pattern = re.compile(re.escape(capturefile) + r'(-\d+)?$')
    data_files = sorted(
        [n for n in names if pattern.match(n)],
        key=lambda n: (
            int(re.search(r'-(\d+)$', n).group(1))
            if re.search(r'-(\d+)$', n) and n != capturefile
            else 0
        ),
    )

    if not data_files:
        raise ValueError(
            f"No logic data files matching '{capturefile}' in .sr archive"
        )

    for name in data_files:
        chunks.append(zf.read(name))

    return b''.join(chunks)


def _resolve_sr_channel(
    channel: Optional[str],
    probe_names: Dict[int, str],
    total_probes: int,
) -> Tuple[int, str]:
    """Resolve a channel specifier to (index, name)."""
    if channel is None:
        idx = 0
        return idx, probe_names.get(idx, 'D0')

    # Try exact match on probe names
    for i, name in probe_names.items():
        if name == channel:
            return i, name

    # Try D0, D1, ... format
    match = re.match(r'^D(\d+)$', channel, re.IGNORECASE)
    if match:
        idx = int(match.group(1))
        if idx < total_probes:
            return idx, probe_names.get(idx, f'D{idx}')

    # Try numeric index
    try:
        idx = int(channel)
        if 0 <= idx < total_probes:
            return idx, probe_names.get(idx, f'D{idx}')
    except ValueError:
        pass

    available = [probe_names.get(i, f'D{i}') for i in range(total_probes)]
    raise ValueError(
        f"Channel '{channel}' not found. Available: {available}"
    )


def _extract_channel_transitions(
    packed_data: bytes,
    channel_idx: int,
    unitsize: int,
    sample_rate: float,
) -> Tuple[np.ndarray, int]:
    """
    Extract transition timestamps for a single channel from packed binary data.

    Each sample is `unitsize` bytes. Channel N = bit N (LSB-first within bytes).
    Returns (transition_times_array, initial_state).
    """
    # Determine which byte and bit within that byte
    byte_offset = channel_idx // 8
    bit_mask = 1 << (channel_idx % 8)

    if byte_offset >= unitsize:
        raise ValueError(
            f"Channel index {channel_idx} exceeds unitsize {unitsize} "
            f"({unitsize * 8} bits available)"
        )

    total_samples = len(packed_data) // unitsize

    # Convert to numpy array for efficient processing
    raw = np.frombuffer(packed_data, dtype=np.uint8)

    # Extract the relevant byte for each sample (stride = unitsize)
    channel_bytes = raw[byte_offset::unitsize][:total_samples]

    # Extract the single bit
    channel_bits = (channel_bytes & bit_mask).astype(bool).astype(np.uint8)

    initial_state = int(channel_bits[0])

    # Find transitions (where consecutive samples differ)
    transitions = np.where(np.diff(channel_bits) != 0)[0] + 1

    if len(transitions) == 0:
        raise ValueError(
            f"No transitions detected (signal constant at {initial_state})"
        )

    # Convert sample indices to timestamps
    transition_times = transitions.astype(np.float64) / sample_rate

    return transition_times, initial_state


def _load_csv(file_path: Path, channel: str = None) -> CaptureData:
    """Load a CSV file with time and signal columns."""
    with open(file_path, 'r') as f:
        content = f.read()
    return _parse_sigrok_csv(content, channel=channel, file_format='csv')


def _parse_sigrok_csv(content: str, channel: str = None,
                      file_format: str = 'csv',
                      sample_rate: float = 0.0,
                      available_channels: List[str] = None) -> CaptureData:
    """
    Parse sigrok-style CSV content into CaptureData.

    Sigrok CSV format has a header comment section followed by:
    Time [s],D0,D1,...,Dn
    0.000000000,0,1,...,0
    """
    if available_channels is None:
        available_channels = []

    lines = content.strip().split('\n')

    # Skip comment lines (sigrok CSV starts with ;)
    data_lines = []
    header = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(';'):
            # Extract sample rate from comments if present
            if 'samplerate' in line.lower():
                rate = parse_sample_rate(line)
                if rate > 0:
                    sample_rate = rate
            continue
        if header is None:
            header = line
            continue
        data_lines.append(line)

    if header is None or not data_lines:
        raise ValueError("CSV file is empty or has no data rows")

    # Parse header to find columns
    columns = [c.strip() for c in header.split(',')]

    # Find the time column
    time_col = None
    for i, col in enumerate(columns):
        if 'time' in col.lower():
            time_col = i
            break
    if time_col is None:
        time_col = 0  # Assume first column is time

    # Find the channel column
    signal_cols = [i for i in range(len(columns)) if i != time_col]
    if not signal_cols:
        raise ValueError("No signal columns found in CSV")

    # Determine which channel to use
    channel_col = None
    channel_name = None

    if channel:
        # User specified a channel name or index
        for i, col in enumerate(columns):
            if col.strip() == channel or col.strip() == f'D{channel}':
                channel_col = i
                channel_name = col.strip()
                break
        if channel_col is None:
            try:
                idx = int(channel)
                if idx < len(signal_cols):
                    channel_col = signal_cols[idx]
                    channel_name = columns[channel_col].strip()
            except ValueError:
                pass
        if channel_col is None:
            raise ValueError(
                f"Channel '{channel}' not found. "
                f"Available: {[columns[i].strip() for i in signal_cols]}"
            )
    else:
        # Default to first signal channel
        channel_col = signal_cols[0]
        channel_name = columns[channel_col].strip()

    if not available_channels:
        available_channels = [columns[i].strip() for i in signal_cols]

    # Parse data rows and extract transitions
    times = []
    states = []

    for line in data_lines:
        parts = line.split(',')
        if len(parts) <= max(time_col, channel_col):
            continue
        try:
            t = float(parts[time_col].strip())
            s = int(parts[channel_col].strip())
            times.append(t)
            states.append(s)
        except (ValueError, IndexError):
            continue

    if not times:
        raise ValueError("No valid data rows found in CSV")

    # Extract only transition points (where signal changes)
    initial_state = states[0]
    transition_times = []

    for i in range(1, len(times)):
        if states[i] != states[i - 1]:
            transition_times.append(times[i])

    if not transition_times:
        raise ValueError(
            "No transitions detected on channel "
            f"'{channel_name}' (signal constant at {initial_state})"
        )

    # Estimate sample rate from data if not known (use median for robustness)
    if sample_rate == 0.0 and len(times) > 2:
        intervals = np.diff(times[:min(1000, len(times))])
        dt = float(np.median(intervals))
        if dt > 0:
            sample_rate = 1.0 / dt
    elif sample_rate == 0.0 and len(times) > 1:
        dt = times[1] - times[0]
        if dt > 0:
            sample_rate = 1.0 / dt

    duration = times[-1] - times[0] if len(times) > 1 else 0.0

    return CaptureData(
        times=np.array(transition_times),
        initial_state=initial_state,
        sample_rate=sample_rate,
        channel_name=channel_name,
        file_format=file_format,
        duration=duration,
        total_samples=len(times),
        available_channels=available_channels,
    )


def _load_vcd(file_path: Path, channel: str = None) -> CaptureData:
    """Parse a VCD (Value Change Dump) file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Parse header
    timescale = 1e-9  # Default: 1ns
    variables = {}  # var_id -> name

    lines = content.split('\n')
    data_start = 0

    for i, line in enumerate(lines):
        line = line.strip()

        if '$timescale' in line:
            # Support both integer and float values (e.g. 1ns, 100ps, 1.0ns)
            match = re.search(r'(\d+(?:\.\d+)?)\s*(s|ms|us|ns|ps|fs)', line)
            if match:
                val = float(match.group(1))
                unit = match.group(2)
                timescale = val * VCD_TIMESCALE_UNITS.get(unit, 1e-9)

        elif '$var' in line:
            # Format: $var wire 1 ! D0 $end
            match = re.match(
                r'\$var\s+\w+\s+\d+\s+(\S+)\s+(\S+)', line
            )
            if match:
                var_id = match.group(1)
                var_name = match.group(2)
                variables[var_id] = var_name

        elif '$enddefinitions' in line:
            data_start = i + 1
            break

    if not variables:
        raise ValueError("No variables found in VCD file")

    available_channels = list(variables.values())

    # Determine target variable
    target_id = None
    target_name = None

    if channel:
        # Find by name or ID
        for vid, vname in variables.items():
            if vname == channel or vid == channel:
                target_id = vid
                target_name = vname
                break
        if target_id is None:
            raise ValueError(
                f"Channel '{channel}' not found. "
                f"Available: {available_channels}"
            )
    else:
        # Default to first variable
        target_id = list(variables.keys())[0]
        target_name = variables[target_id]

    # Parse data section
    current_time = 0.0
    transitions = []  # (time_seconds, state)

    for line in lines[data_start:]:
        line = line.strip()
        if not line:
            continue

        if line.startswith('#'):
            try:
                current_time = int(line[1:]) * timescale
            except ValueError:
                continue

        elif line.startswith('0') or line.startswith('1'):
            # Single-bit value change: 0! or 1!
            state = int(line[0])
            var_id = line[1:]
            if var_id == target_id:
                transitions.append((current_time, state))

        elif line.startswith('b'):
            # Multi-bit value: bXXXX var_id
            parts = line.split()
            if len(parts) == 2 and parts[1] == target_id:
                try:
                    state = int(parts[0][1:], 2) & 1  # Take LSB
                    transitions.append((current_time, state))
                except ValueError:
                    continue

    if not transitions:
        raise ValueError(
            f"No transitions found for channel '{target_name}'"
        )

    initial_state = transitions[0][1]

    # Filter to only actual transitions (state changes)
    transition_times = []
    prev_state = initial_state
    for t, s in transitions[1:]:
        if s != prev_state:
            transition_times.append(t)
            prev_state = s

    if not transition_times:
        raise ValueError(
            f"No state changes on channel '{target_name}' "
            f"(constant at {initial_state})"
        )

    duration = transitions[-1][0] - transitions[0][0]

    return CaptureData(
        times=np.array(transition_times),
        initial_state=initial_state,
        sample_rate=1.0 / timescale,
        channel_name=target_name,
        file_format='vcd',
        duration=duration,
        total_samples=len(transitions),
        available_channels=available_channels,
    )


# ============================================================================
# ANALYSIS WRAPPERS
# ============================================================================

def analyze_timing(data: CaptureData) -> dict:
    """Analyze timing characteristics of the signal."""
    return _analyze_timing(data.times, data.initial_state, data.duration)


def export_csv(data: CaptureData, output_path: Path):
    """Export transitions to CSV file."""
    export_transitions_csv(data.times, data.initial_state, output_path)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze logic analyzer captures using sigrok",
        epilog=(
            "Examples:\n"
            "  %(prog)s capture.sr\n"
            "  %(prog)s capture.sr --histogram --clusters\n"
            "  %(prog)s capture.sr --decode uart:baudrate=115200\n"
            "  %(prog)s capture.sr --decode i2c,eeprom24xx\n"
            "  %(prog)s capture.sr --export transitions.csv\n"
            "  %(prog)s --list-decoders\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", type=Path, nargs='?',
                        help="Capture file (.sr, .csv, .vcd)")

    # Timing analysis options
    timing = parser.add_argument_group('timing analysis')
    timing.add_argument("--histogram", action="store_true",
                        help="Show timing histogram")
    timing.add_argument("--bins", type=int, default=20,
                        help="Number of histogram bins (default: 20)")
    timing.add_argument("--clusters", action="store_true",
                        help="Show detected timing clusters")
    timing.add_argument("--raw", action="store_true",
                        help="Show raw transition durations")
    timing.add_argument("-n", type=int, default=20,
                        help="Number of raw values to show (default: 20)")

    # Channel selection
    parser.add_argument("--channel", "-C", type=str, default=None,
                        help="Channel to analyze (name or index, default: first)")

    # Export options
    export = parser.add_argument_group('export')
    export.add_argument("--export", type=Path, metavar="CSV",
                        help="Export transitions to CSV file")
    export.add_argument("--binary-out", type=Path, metavar="FILE",
                        help="Extract binary data to file (use with --decode)")

    # Protocol decoding
    decoding = parser.add_argument_group('protocol decoding')
    decoding.add_argument("--decode", "-P", type=str, metavar="DECODER",
                          help="Protocol decoder spec (e.g., uart:baudrate=115200)")
    decoding.add_argument("--annotations", "-A", type=str, metavar="FILTER",
                          help="Filter decoder annotations (e.g., uart=tx-data)")
    decoding.add_argument("--binary-decode", "-B", type=str, metavar="SPEC",
                          help="Binary output spec (e.g., uart=tx)")
    decoding.add_argument("--samplenum", action="store_true",
                          help="Include sample numbers in decoder output")

    # Info commands
    info = parser.add_argument_group('information')
    info.add_argument("--list-decoders", action="store_true",
                      help="List available protocol decoders")
    info.add_argument("--show", action="store_true",
                      help="Show capture file metadata")

    args = parser.parse_args()

    # Handle --list-decoders (no file required)
    if args.list_decoders:
        available, version = check_sigrok_cli()
        if not available:
            print(f"Error: {version}")
            _print_install_help()
            sys.exit(1)

        decoders = list_decoders()
        if decoders:
            print(f"Available Protocol Decoders ({len(decoders)}):")
            print("-" * 60)
            for name, desc in decoders:
                print(f"  {name:25s} {desc}")
        else:
            print("No decoders found (check sigrok-cli installation)")
        sys.exit(0)

    # All other commands require a file
    if args.file is None:
        parser.error("the following arguments are required: file")

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    # Commands that require sigrok-cli: --show, --decode
    needs_sigrok = args.show or args.decode

    if needs_sigrok:
        available, version = check_sigrok_cli()
        if not available:
            print(f"Error: {version}")
            _print_install_help()
            sys.exit(1)

    # Handle --show
    if args.show:
        info = show_file_info(args.file)
        if info:
            print(f"File: {args.file}")
            print(info['raw'])
        else:
            print(f"Error: Could not read file info for {args.file}")
            sys.exit(1)
        sys.exit(0)

    # Handle protocol decoding
    if args.decode:
        # Binary extraction
        if args.binary_out and args.binary_decode:
            result = extract_binary(
                args.file, args.decode, args.binary_decode, args.binary_out
            )
            if result['success']:
                print(f"Extracted {result['size']} bytes to {args.binary_out}")
            else:
                print(f"Error: {result['error']}")
                sys.exit(1)
            sys.exit(0)

        # Annotation decoding
        result = decode_protocol(
            args.file, args.decode,
            annotations=args.annotations,
            sample_numbers=args.samplenum,
        )
        if result['success']:
            if result['output']:
                print(result['output'], end='')
            else:
                print("No decoder output (check decoder spec and channel mapping)")
        else:
            print(f"Error decoding: {result['error']}")
            sys.exit(1)

        # If no timing analysis flags, stop here
        if not (args.histogram or args.clusters or args.raw or args.export):
            sys.exit(0)

    # Load capture for timing analysis
    try:
        data = load_capture(args.file, channel=args.channel)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    analysis = analyze_timing(data)

    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        sys.exit(1)

    # Print basic info
    print(f"File: {args.file}")
    print(f"Format: {data.file_format}")
    print(f"Channel: {data.channel_name}")
    if data.sample_rate > 0:
        if data.sample_rate >= 1e6:
            print(f"Sample rate: {data.sample_rate/1e6:.1f} MHz")
        elif data.sample_rate >= 1e3:
            print(f"Sample rate: {data.sample_rate/1e3:.1f} kHz")
        else:
            print(f"Sample rate: {data.sample_rate:.1f} Hz")
    print(f"Capture duration: {analysis['capture_duration_s']:.3f}s")
    print(f"Signal duration: {analysis['signal_duration_s']:.3f}s")
    print(f"Initial state: {analysis['initial_state']}")
    print(f"Total transitions: {analysis['total_transitions']}")
    if data.available_channels:
        print(f"Available channels: {', '.join(data.available_channels)}")
    print()

    # Timing summary
    print("Timing Summary")
    print("-" * 40)
    a = analysis['all']
    print(f"All durations:  min={format_duration(a['min_us'])}  "
          f"max={format_duration(a['max_us'])}  "
          f"mean={format_duration(a['mean_us'])}")

    h = analysis['high']
    print(f"HIGH pulses ({h['count']}): min={format_duration(h['min_us'])}  "
          f"max={format_duration(h['max_us'])}  "
          f"mean={format_duration(h['mean_us'])}")

    lo = analysis['low']
    print(f"LOW gaps ({lo['count']}):   min={format_duration(lo['min_us'])}  "
          f"max={format_duration(lo['max_us'])}  "
          f"mean={format_duration(lo['mean_us'])}")
    print()

    # Protocol guesses
    guesses = guess_protocol(analysis)
    if guesses:
        print("Protocol Guesses")
        print("-" * 40)
        for name, confidence, details in guesses:
            print(f"  {name} ({confidence*100:.0f}% confidence)")
            print(f"    {details}")
        print()

    # Clusters
    if args.clusters:
        print("Detected Timing Clusters")
        print("-" * 40)

        high_clusters = detect_clusters(analysis['high_durations_us'])
        print("HIGH pulse clusters:")
        for center, count in high_clusters[:5]:
            print(f"  ~{format_duration(center)} ({count} occurrences)")

        low_clusters = detect_clusters(analysis['low_durations_us'])
        print("LOW gap clusters:")
        for center, count in low_clusters[:5]:
            print(f"  ~{format_duration(center)} ({count} occurrences)")
        print()

    # Raw values
    if args.raw:
        print(f"First {args.n} Transitions")
        print("-" * 40)
        durations = analysis['durations_us']
        initial = 0 if analysis['initial_state'] == 'LOW' else 1
        for i in range(min(args.n, len(durations))):
            state = "HIGH" if (i + initial) % 2 == 0 else "LOW"
            dur = durations[i]
            print(f"  [{i:3d}] {state}: {format_duration(dur)}")
        print()

    # Histogram
    if args.histogram:
        print_histogram(analysis['durations_us'], bins=args.bins,
                        title="All Durations")
        print_histogram(analysis['high_durations_us'], bins=args.bins,
                        title="HIGH Pulse Durations")
        print_histogram(analysis['low_durations_us'], bins=args.bins,
                        title="LOW Gap Durations")

    # Export
    if args.export:
        export_csv(data, args.export)


def _print_install_help():
    """Print installation instructions for sigrok-cli."""
    print("\nInstall sigrok-cli:")
    print("  Arch Linux:  sudo pacman -S sigrok-cli")
    print("  Ubuntu:      sudo apt install sigrok-cli")
    print("  Fedora:      sudo dnf install sigrok-cli")
    print("  macOS:       brew install sigrok-cli")
    print("  Windows:     Download from https://sigrok.org/wiki/Downloads")
    print("               If you get a missing DLL error, install the VC++ 2010 runtime:")
    print("               winget install --id=Microsoft.VCRedist.2010.x64")


if __name__ == "__main__":
    main()
