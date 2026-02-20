#!/usr/bin/env python3
"""
RF Signal Analyzer for URH (Universal Radio Hacker) compatible captures.

Analyzes IQ signal files (.complex, .complex16s, .complex16u, .wav) to
identify modulation type, demodulate OOK/FSK signals, and decode protocols
using urh_cli. For CTF RF challenges and IoT device reverse engineering.
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

# Add parent directory to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.signal_analysis import (
    detect_clusters,
    export_transitions_csv,
    format_duration,
    guess_protocol,
    parse_sample_rate,
    print_histogram,
)
from common.signal_analysis import analyze_timing as _analyze_timing


# ============================================================================
# CONSTANTS
# ============================================================================

SUPPORTED_EXTENSIONS = {'.complex', '.cfile', '.complex16s', '.complex16u', '.wav'}

# URH filename convention: signal_<samplerate>_<centerfreq>.complex
# e.g. signal_2000000_433920000.complex or capture_2M_433.92M.complex
_RATE_PATTERN = r'(\d+(?:\.\d+)?)\s*([kMG]?)(?:_|\b)'


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SignalData:
    """Normalized IQ signal data from any supported format."""
    samples: np.ndarray        # Complex float64 samples
    sample_rate: float         # Samples per second (Hz)
    center_freq: float         # Center frequency in Hz (0 if unknown)
    file_format: str           # 'complex', 'complex16s', 'complex16u', or 'wav'
    duration: float            # Total duration in seconds
    n_samples: int             # Total sample count
    available_channels: List[str] = field(default_factory=list)


# ============================================================================
# URH-CLI INTERACTION
# ============================================================================

def check_urh_cli() -> Tuple[bool, str]:
    """Check if urh_cli is installed and return version info."""
    for cmd in [['urh_cli', '--version'], ['python3', '-m', 'urh.cli.urh_cli', '--version']]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = (result.stdout or result.stderr).strip().split('\n')[0]
                return True, version
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return False, "urh_cli timed out"
        except Exception as e:
            return False, str(e)
    return False, "urh_cli not found in PATH"


def run_urh_cli(args: List[str], timeout: int = 60) -> Tuple[int, str, str]:
    """
    Run urh_cli with the given arguments.

    Returns (returncode, stdout, stderr).
    """
    # Try direct command first, fall back to module invocation
    for cmd_prefix in [['urh_cli'], ['python3', '-m', 'urh.cli.urh_cli']]:
        cmd = cmd_prefix + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return 1, '', 'urh_cli timed out'
    return 1, '', 'urh_cli not found'


def _print_install_help():
    print("Install URH with: pip install urh")
    print("Or run via module: python3 -m urh.cli.urh_cli")


# ============================================================================
# FILENAME PARSING
# ============================================================================

def _parse_rate_from_name(name: str) -> float:
    """
    Try to extract sample rate from a filename.

    URH convention: signal_<samplerate>_<centerfreq>.complex
    Examples: capture_2000000_433920000.complex, sig_2M_433.92M.complex
    """
    import re
    # Look for standalone numbers that could be a sample rate (common: 1M, 2M, 8M)
    # Pattern: digits followed by optional k/M/G multiplier
    matches = re.findall(r'(\d+(?:\.\d+)?)([kKmMgG]?)', name)
    for val_str, unit in matches:
        val = float(val_str)
        multiplier = {'k': 1e3, 'K': 1e3, 'm': 1e6, 'M': 1e6, 'g': 1e9, 'G': 1e9}.get(unit, 1)
        rate = val * multiplier
        # Plausible sample rates: 8kHz – 56MHz
        if 8e3 <= rate <= 56e6:
            return rate
    return 0.0


def _parse_freq_from_name(name: str) -> float:
    """
    Try to extract center frequency from a filename.

    Looks for frequency hints like 433, 433.92, 433920000.
    Skips the first plausible sample-rate value to avoid returning
    the sample rate as the center frequency on URH-convention filenames
    like capture_2000000_433920000.complex.
    """
    import re
    matches = re.findall(r'(\d+(?:\.\d+)?)([kKmMgG]?)', name)
    skipped_one = False
    for val_str, unit in matches:
        val = float(val_str)
        multiplier = {'k': 1e3, 'K': 1e3, 'm': 1e6, 'M': 1e6, 'g': 1e9, 'G': 1e9}.get(unit, 1)
        candidate = val * multiplier
        # Skip the first value that falls in the sample-rate range (8 kHz – 56 MHz)
        # so that we return the second numeric token (the center frequency)
        if not skipped_one and 8e3 <= candidate <= 56e6:
            skipped_one = True
            continue
        # Plausible RF center frequencies: 100 kHz – 6 GHz
        if 1e5 <= candidate <= 6e9:
            return candidate
    return 0.0


# ============================================================================
# FILE LOADING
# ============================================================================

def load_signal(file_path: Path, sample_rate: float = 0.0,
                center_freq: float = 0.0) -> SignalData:
    """
    Load an IQ signal file and return normalized SignalData.

    Auto-detects format from file extension.
    """
    ext = file_path.suffix.lower()
    if ext in ('.complex', '.cfile'):
        return _load_complex32(file_path, sample_rate, center_freq)
    elif ext == '.complex16s':
        return _load_complex16(file_path, sample_rate, center_freq, signed=True)
    elif ext == '.complex16u':
        return _load_complex16(file_path, sample_rate, center_freq, signed=False)
    elif ext == '.wav':
        return _load_wav(file_path, sample_rate, center_freq)
    else:
        raise ValueError(
            f"Unsupported format '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


def _load_complex32(file_path: Path, sample_rate: float,
                    center_freq: float) -> SignalData:
    """Load float32 interleaved IQ file (.complex, .cfile)."""
    raw = np.fromfile(str(file_path), dtype=np.float32)
    if len(raw) % 2 != 0:
        raw = raw[:-1]
    samples = raw[0::2].astype(np.float64) + 1j * raw[1::2].astype(np.float64)

    if sample_rate == 0.0:
        sample_rate = _parse_rate_from_name(file_path.name)
    if center_freq == 0.0:
        center_freq = _parse_freq_from_name(file_path.name)

    n = len(samples)
    duration = n / sample_rate if sample_rate > 0 else 0.0
    return SignalData(
        samples=samples,
        sample_rate=sample_rate,
        center_freq=center_freq,
        file_format='complex',
        duration=duration,
        n_samples=n,
    )


def _load_complex16(file_path: Path, sample_rate: float,
                    center_freq: float, signed: bool) -> SignalData:
    """Load int16 interleaved IQ file (.complex16s or .complex16u)."""
    dtype = np.int16 if signed else np.uint16
    raw = np.fromfile(str(file_path), dtype=dtype)
    if len(raw) % 2 != 0:
        raw = raw[:-1]

    i_vals = raw[0::2].astype(np.float64)
    q_vals = raw[1::2].astype(np.float64)

    # Normalize to [-1, 1]
    scale = 32768.0 if signed else 32768.0
    if not signed:
        i_vals -= 32768.0
        q_vals -= 32768.0
    samples = (i_vals / scale) + 1j * (q_vals / scale)

    if sample_rate == 0.0:
        sample_rate = _parse_rate_from_name(file_path.name)
    if center_freq == 0.0:
        center_freq = _parse_freq_from_name(file_path.name)

    fmt = 'complex16s' if signed else 'complex16u'
    n = len(samples)
    duration = n / sample_rate if sample_rate > 0 else 0.0
    return SignalData(
        samples=samples,
        sample_rate=sample_rate,
        center_freq=center_freq,
        file_format=fmt,
        duration=duration,
        n_samples=n,
    )


def _load_wav(file_path: Path, sample_rate: float,
              center_freq: float) -> SignalData:
    """
    Load a WAV file as IQ signal.

    Stereo WAV: left channel = I, right channel = Q.
    Mono WAV: treated as real-valued (Q = 0).
    """
    try:
        import wave
        import struct
        with wave.open(str(file_path), 'rb') as wf:
            n_channels = wf.getnchannels()
            samp_width = wf.getsampwidth()
            wav_rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

        if sample_rate == 0.0:
            sample_rate = float(wav_rate)

        # Decode samples
        fmt_map = {1: np.int8, 2: np.int16, 4: np.int32}
        if samp_width not in fmt_map:
            raise ValueError(f"Unsupported WAV sample width: {samp_width} bytes")
        dtype = fmt_map[samp_width]
        max_val = float(2 ** (8 * samp_width - 1))

        all_samples = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float64) / max_val

        if n_channels == 2:
            i_vals = all_samples[0::2]
            q_vals = all_samples[1::2]
            samples = i_vals + 1j * q_vals
        else:
            samples = all_samples + 0j

    except ImportError:
        raise ImportError("Could not import 'wave' module (standard library)")

    if center_freq == 0.0:
        center_freq = _parse_freq_from_name(file_path.name)

    n = len(samples)
    duration = n / sample_rate if sample_rate > 0 else 0.0
    return SignalData(
        samples=samples,
        sample_rate=sample_rate,
        center_freq=center_freq,
        file_format='wav',
        duration=duration,
        n_samples=n,
    )


# ============================================================================
# SIGNAL ANALYSIS
# ============================================================================

def compute_amplitude_envelope(samples: np.ndarray) -> np.ndarray:
    """Compute the amplitude (magnitude) envelope of the IQ signal."""
    return np.abs(samples)


def compute_spectrum(samples: np.ndarray, sample_rate: float,
                     n_bins: int = 512) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute a power spectrum (FFT) of the IQ signal.

    Returns (freqs_hz, power_db) arrays, both of length n_bins.
    Frequencies are centered on 0 Hz (baseband).
    """
    # Downsample to n_bins samples, apply window, then FFT
    if len(samples) >= n_bins:
        # Decimate: average groups of samples down to n_bins points
        step = len(samples) // n_bins
        decimated = samples[:step * n_bins].reshape(n_bins, step).mean(axis=1)
    else:
        # Zero-pad to n_bins
        decimated = np.zeros(n_bins, dtype=complex)
        decimated[:len(samples)] = samples

    window = np.hanning(n_bins)
    fft_out = np.fft.fftshift(np.fft.fft(decimated * window))
    power = 20 * np.log10(np.abs(fft_out) + 1e-10)
    freqs = np.fft.fftshift(np.fft.fftfreq(n_bins, d=1.0 / sample_rate))
    return freqs, power


def compute_energy_profile(samples: np.ndarray, block_size: int = 512) -> np.ndarray:
    """
    Compute the signal energy in consecutive blocks.

    Returns an array of RMS energy values, one per block.
    """
    n_blocks = len(samples) // block_size
    if n_blocks == 0:
        return np.array([float(np.mean(np.abs(samples)))])
    trimmed = samples[:n_blocks * block_size].reshape(n_blocks, block_size)
    return np.mean(np.abs(trimmed), axis=1)


def demodulate_ook(samples: np.ndarray, threshold: Optional[float] = None
                   ) -> Tuple[np.ndarray, float]:
    """
    Demodulate OOK signal to a binary sequence via amplitude thresholding.

    Returns (binary_signal, threshold_used) where binary_signal is a 0/1 array.
    """
    envelope = compute_amplitude_envelope(samples)
    env_min = float(envelope.min())
    env_max = float(envelope.max())

    if threshold is None:
        # Otsu-like: midpoint between noise floor and peak
        threshold = env_min + (env_max - env_min) * 0.5

    binary = (envelope >= threshold).astype(np.uint8)
    return binary, threshold


def demodulate_fsk(samples: np.ndarray) -> np.ndarray:
    """
    Demodulate FSK signal via instantaneous frequency.

    Returns a float array of instantaneous frequency deviations (Hz not scaled).
    Positive values correspond to one symbol, negative to the other.
    """
    # Instantaneous frequency from phase derivative
    phase = np.angle(samples)
    inst_freq = np.diff(np.unwrap(phase))
    return inst_freq


def extract_ook_transitions(binary_signal: np.ndarray,
                             sample_rate: float) -> Tuple[np.ndarray, int]:
    """
    Extract transition timestamps (in seconds) from a binary OOK signal.

    Returns (times, initial_state) compatible with common/signal_analysis.py.
    """
    if len(binary_signal) == 0:
        return np.array([]), 0

    initial_state = int(binary_signal[0])

    # Find indices where the signal changes value
    diffs = np.diff(binary_signal.astype(np.int8))
    transition_indices = np.where(diffs != 0)[0] + 1  # +1: index after transition

    # Convert indices to timestamps
    times = transition_indices.astype(np.float64) / sample_rate
    return times, initial_state


def detect_modulation_hint(signal: SignalData) -> str:
    """
    Provide a coarse modulation hint based on spectrum and amplitude characteristics.

    Returns a string: 'OOK/ASK', 'FSK', 'PSK', or 'UNKNOWN'.
    """
    env = compute_amplitude_envelope(signal.samples)
    env_max = float(env.max())
    if env_max == 0:
        return 'UNKNOWN'

    env_norm = env / env_max

    # OOK/ASK: amplitude varies significantly (ratio of std to mean is high)
    env_std = float(env_norm.std())
    env_mean = float(env_norm.mean())
    amp_variation = env_std / (env_mean + 1e-9)

    # FSK: look for two lobes in the spectrum
    if signal.sample_rate > 0:
        _, power = compute_spectrum(signal.samples, signal.sample_rate)
        half = len(power) // 2
        left_power = float(np.max(power[:half]))
        right_power = float(np.max(power[half:]))
        # Two roughly equal lobes on both sides: FSK
        if abs(left_power - right_power) < 6 and left_power > -60:
            return 'FSK'

    if amp_variation > 0.3:
        return 'OOK/ASK'

    return 'PSK'


# ============================================================================
# OUTPUT DISPLAY
# ============================================================================

def print_spectrum(freqs: np.ndarray, power: np.ndarray,
                   width: int = 60, title: str = "Power Spectrum"):
    """Print an ASCII representation of the power spectrum."""
    p_min = float(power.min())
    p_max = float(power.max())
    p_range = p_max - p_min if p_max > p_min else 1.0

    # Downsample to display width
    n_bins = len(power)
    step = max(1, n_bins // width)
    display_power = []
    display_freqs = []
    for i in range(0, n_bins, step):
        end = min(i + step, n_bins)
        display_power.append(float(np.max(power[i:end])))
        display_freqs.append(float(np.mean(freqs[i:end])))

    print(f"\n{title}")
    print("=" * 60)
    print(f"{'Freq (kHz)':>12}  Spectrum")
    print("-" * 60)

    for freq_hz, p in zip(display_freqs, display_power):
        bar_len = int(40 * (p - p_min) / p_range)
        bar = "#" * bar_len
        freq_khz = freq_hz / 1e3
        print(f"{freq_khz:>12.1f}  |{bar}")

    print(f"\n  Peak power:  {p_max:.1f} dB")
    print(f"  Noise floor: {p_min:.1f} dB")


def print_energy_profile(energy: np.ndarray, sample_rate: float,
                         block_size: int = 512, title: str = "Signal Energy"):
    """Print an ASCII energy-over-time plot."""
    e_max = float(energy.max())
    if e_max == 0:
        print(f"{title}: No signal energy detected")
        return

    energy_norm = energy / e_max
    block_duration_ms = block_size / sample_rate * 1000.0

    print(f"\n{title} (block size: {block_duration_ms:.2f}ms)")
    print("=" * 60)

    width = 40
    for i, e in enumerate(energy_norm):
        bar_len = int(width * e)
        bar = "#" * bar_len
        t_ms = i * block_duration_ms
        print(f"{t_ms:8.1f}ms  |{bar}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze RF IQ signal captures for URH-compatible files"
    )
    parser.add_argument("file", type=Path, help="IQ signal file (.complex, .cfile, .complex16s, .complex16u, .wav)")
    parser.add_argument("-s", "--sample-rate", type=float, default=0.0, metavar="HZ",
                        help="Sample rate in Hz (e.g. 2000000 for 2 MSPS). "
                             "Parsed from filename if not specified.")
    parser.add_argument("-c", "--center-freq", type=float, default=0.0, metavar="HZ",
                        help="Center frequency in Hz (for display only).")

    # Display options
    parser.add_argument("--spectrum", action="store_true",
                        help="Show ASCII power spectrum")
    parser.add_argument("--energy", action="store_true",
                        help="Show signal energy over time (packet boundary detection)")
    parser.add_argument("--raw", action="store_true",
                        help="Show raw IQ samples (basic stats) or raw pulse transitions "
                             "(after demodulation)")
    parser.add_argument("-n", type=int, default=20,
                        help="Number of raw values to show (default: 20)")

    # Demodulation
    parser.add_argument("--demodulate", choices=['ook', 'fsk', 'ask'], metavar="MODE",
                        help="Demodulate the signal (ook, fsk, ask). "
                             "After OOK demodulation, enables --clusters, --histogram, --raw for pulse analysis.")
    parser.add_argument("--threshold", type=float, default=None,
                        help="OOK amplitude threshold 0.0–1.0 (default: auto midpoint)")

    # Pulse analysis (after OOK/ASK demodulation)
    parser.add_argument("--clusters", action="store_true",
                        help="Show detected pulse duration clusters (after OOK demodulation)")
    parser.add_argument("--histogram", action="store_true",
                        help="Show pulse duration histogram (after OOK demodulation)")
    parser.add_argument("--bins", type=int, default=20,
                        help="Number of histogram bins (default: 20)")

    # Protocol decoding via urh_cli
    parser.add_argument("--decode", action="store_true",
                        help="Run urh_cli auto-analysis for protocol decoding")
    parser.add_argument("--modulation", choices=['OOK', 'ASK', 'FSK', 'PSK'],
                        help="Modulation hint for urh_cli --decode (OOK, ASK, FSK, PSK)")

    # Export
    parser.add_argument("--export", type=Path, metavar="CSV",
                        help="Export to CSV. Without --demodulate: exports IQ samples. "
                             "With --demodulate ook: exports pulse transitions.")

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    ext = args.file.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported file extension '{ext}'")
        print(f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    # --- Load signal ---
    try:
        signal = load_signal(args.file, sample_rate=args.sample_rate,
                             center_freq=args.center_freq)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    if signal.sample_rate == 0.0:
        print("Warning: Sample rate unknown. Use -s to specify it.")
        print("  Example: -s 2000000 for 2 MSPS")
        print()

    # --- Basic info ---
    print(f"File:         {args.file}")
    print(f"Format:       {signal.file_format}")
    print(f"Samples:      {signal.n_samples:,}")
    if signal.sample_rate > 0:
        rate_str = f"{signal.sample_rate/1e6:.3f} MSPS" if signal.sample_rate >= 1e6 else f"{signal.sample_rate/1e3:.1f} kSPS"
        print(f"Sample rate:  {rate_str}")
        print(f"Duration:     {signal.duration*1000:.2f} ms  ({signal.duration:.4f} s)")
    if signal.center_freq > 0:
        freq_str = f"{signal.center_freq/1e6:.3f} MHz" if signal.center_freq >= 1e6 else f"{signal.center_freq/1e3:.1f} kHz"
        print(f"Center freq:  {freq_str}")

    env = compute_amplitude_envelope(signal.samples)
    env_max = float(env.max())
    env_mean = float(env.mean())
    print()
    print("Amplitude")
    print("-" * 40)
    print(f"  Peak:   {env_max:.4f}")
    print(f"  Mean:   {env_mean:.4f}")
    print(f"  Std:    {float(env.std()):.4f}")

    # Modulation hint
    hint = detect_modulation_hint(signal)
    print()
    print(f"Modulation hint: {hint}")
    print()

    # --- Spectrum ---
    if args.spectrum:
        if signal.sample_rate == 0.0:
            print("Warning: Sample rate unknown — spectrum frequencies will be incorrect.")
            sample_rate_for_fft = 1.0
        else:
            sample_rate_for_fft = signal.sample_rate
        freqs, power = compute_spectrum(signal.samples, sample_rate_for_fft)
        print_spectrum(freqs, power)
        print()

    # --- Energy profile ---
    if args.energy:
        block_size = max(64, signal.n_samples // 200)
        energy = compute_energy_profile(signal.samples, block_size=block_size)
        if signal.sample_rate > 0:
            print_energy_profile(energy, signal.sample_rate, block_size=block_size)
        else:
            print_energy_profile(energy, 1.0, block_size=block_size)
        print()

    # --- Raw IQ samples (no demodulation) ---
    if args.raw and not args.demodulate:
        print(f"First {args.n} IQ Samples")
        print("-" * 40)
        for i in range(min(args.n, signal.n_samples)):
            s = signal.samples[i]
            amp = abs(s)
            print(f"  [{i:4d}]  I={s.real:+.4f}  Q={s.imag:+.4f}  |{amp:.4f}|")
        print()

    # --- Demodulation ---
    if args.demodulate:
        mode = args.demodulate.lower()

        if mode in ('ook', 'ask'):
            binary, thresh_used = demodulate_ook(signal.samples, threshold=args.threshold)
            print(f"OOK Demodulation (threshold: {thresh_used:.4f})")
            print("-" * 40)

            if signal.sample_rate > 0:
                times, initial_state = extract_ook_transitions(binary, signal.sample_rate)
                print(f"Transitions detected: {len(times)}")
                if len(times) < 2:
                    print("Warning: Very few transitions detected.")
                    print("  Try adjusting --threshold or check that the signal contains pulses.")
                    print()
                else:
                    analysis = _analyze_timing(times, initial_state, signal.duration)
                    if 'error' in analysis:
                        print(f"Timing analysis error: {analysis['error']}")
                    else:
                        from common.signal_analysis import format_duration
                        print(f"Initial state:        {'HIGH' if initial_state else 'LOW'}")
                        a = analysis['all']
                        print(f"All pulses:  min={format_duration(a['min_us'])}  "
                              f"max={format_duration(a['max_us'])}  "
                              f"mean={format_duration(a['mean_us'])}")
                        h = analysis['high']
                        print(f"HIGH pulses ({h['count']}): min={format_duration(h['min_us'])}  "
                              f"max={format_duration(h['max_us'])}")
                        lo = analysis['low']
                        print(f"LOW gaps   ({lo['count']}): min={format_duration(lo['min_us'])}  "
                              f"max={format_duration(lo['max_us'])}")
                        print()

                        guesses = guess_protocol(analysis)
                        if guesses:
                            print("Protocol Guesses (from pulse timing)")
                            print("-" * 40)
                            for name, confidence, details in guesses:
                                print(f"  {name} ({confidence*100:.0f}% confidence)")
                                print(f"    {details}")
                            print()

                        if args.clusters:
                            print("Detected Pulse Duration Clusters")
                            print("-" * 40)
                            high_clusters = detect_clusters(analysis['high_durations_us'])
                            print("HIGH pulse clusters:")
                            for center, count in high_clusters[:6]:
                                print(f"  ~{format_duration(center)} ({count} occurrences)")
                            low_clusters = detect_clusters(analysis['low_durations_us'])
                            print("LOW gap clusters:")
                            for center, count in low_clusters[:6]:
                                print(f"  ~{format_duration(center)} ({count} occurrences)")
                            print()

                        if args.histogram:
                            print_histogram(analysis['durations_us'], bins=args.bins,
                                            title="All Pulse Durations")
                            print_histogram(analysis['high_durations_us'], bins=args.bins,
                                            title="HIGH Pulse Durations")
                            print_histogram(analysis['low_durations_us'], bins=args.bins,
                                            title="LOW Gap Durations")

                        if args.raw:
                            print(f"First {args.n} Pulse Transitions")
                            print("-" * 40)
                            durations = analysis['durations_us']
                            for i in range(min(args.n, len(durations))):
                                state = "HIGH" if (i + initial_state) % 2 == 0 else "LOW"
                                print(f"  [{i:3d}] {state}: {format_duration(durations[i])}")
                            print()

                        if args.export:
                            export_transitions_csv(times, initial_state, args.export)
                            # (print message inside export_transitions_csv)
            else:
                # No sample rate: show raw binary sequence only
                print(f"Binary (first {args.n*8} bits): ", end='')
                print(''.join(map(str, binary[:args.n * 8])))
                print()

        elif mode == 'fsk':
            inst_freq = demodulate_fsk(signal.samples)
            threshold = float(np.median(inst_freq))
            binary_fsk = (inst_freq > threshold).astype(np.uint8)
            print(f"FSK Demodulation (frequency threshold: {threshold:.4f})")
            print("-" * 40)
            print(f"Instantaneous freq: min={float(inst_freq.min()):.4f}  "
                  f"max={float(inst_freq.max()):.4f}  "
                  f"mean={float(inst_freq.mean()):.4f}")
            print()
            if args.raw:
                print(f"First {args.n} demodulated FSK values (normalized freq)")
                print("-" * 40)
                for i in range(min(args.n, len(inst_freq))):
                    sym = "HI" if binary_fsk[i] else "LO"
                    print(f"  [{i:4d}]  freq={inst_freq[i]:+.4f}  -> {sym}")
                print()

            if args.export:
                with open(args.export, 'w') as f:
                    f.write("index,inst_freq,symbol\n")
                    for i, (fr, sym) in enumerate(zip(inst_freq, binary_fsk)):
                        f.write(f"{i},{fr:.6f},{sym}\n")
                print(f"Exported {len(inst_freq)} FSK samples to {args.export}")

    # --- Protocol decoding via urh_cli ---
    if args.decode:
        ok, version = check_urh_cli()
        if not ok:
            print(f"Error: urh_cli not available ({version})")
            _print_install_help()
            sys.exit(1)

        print(f"urh_cli Protocol Decoding  [{version}]")
        print("-" * 40)

        urh_args = ['analyze', '-f', str(args.file)]
        if signal.sample_rate > 0:
            urh_args += ['-s', str(int(signal.sample_rate))]
        if args.modulation:
            urh_args += ['--modulation', args.modulation]

        rc, stdout, stderr = run_urh_cli(urh_args)
        if stdout:
            print(stdout)
        if stderr and rc != 0:
            print(f"urh_cli error: {stderr.strip()}")
        if rc != 0:
            print("urh_cli returned non-zero exit code. Check the error message above.")
        print()

    # --- Export IQ (without demodulation) ---
    if args.export and not args.demodulate:
        n_export = min(signal.n_samples, 100000)
        with open(args.export, 'w') as f:
            f.write("index,i,q,amplitude\n")
            for i in range(n_export):
                s = signal.samples[i]
                f.write(f"{i},{s.real:.6f},{s.imag:.6f},{abs(s):.6f}\n")
        print(f"Exported {n_export} IQ samples to {args.export}")


if __name__ == "__main__":
    main()
