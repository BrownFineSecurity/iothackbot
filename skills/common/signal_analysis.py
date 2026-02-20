#!/usr/bin/env python3
"""
Shared signal analysis utilities for logic analyzer skills.

Provides timing analysis, cluster detection, protocol guessing,
histogram generation, and duration formatting used by both the
logicmso and sigrok skills.
"""

import re
from typing import List, Tuple

import numpy as np


# Common baud rates and their bit periods in microseconds
COMMON_BAUD_RATES = {
    300: 3333.33,
    1200: 833.33,
    2400: 416.67,
    4800: 208.33,
    9600: 104.17,
    19200: 52.08,
    38400: 26.04,
    57600: 17.36,
    115200: 8.68,
    230400: 4.34,
    460800: 2.17,
    921600: 1.09,
}


def analyze_timing(times: np.ndarray, initial_state: int,
                   duration: float) -> dict:
    """
    Analyze timing characteristics of a digital signal.

    Args:
        times: Array of transition timestamps in seconds.
        initial_state: Starting logic level (0 or 1).
        duration: Total capture duration in seconds.

    Returns:
        Dict with timing statistics, or {'error': msg} on failure.
    """
    if len(times) < 2:
        return {'error': 'Not enough transitions'}

    durations_s = np.diff(times)
    durations_us = durations_s * 1e6

    # Separate HIGH and LOW durations
    high_idx = 0 if initial_state == 0 else 1
    low_idx = 1 - high_idx

    high_durations_us = durations_us[high_idx::2]
    low_durations_us = durations_us[low_idx::2]

    return {
        'total_transitions': len(times),
        'capture_duration_s': duration,
        'signal_duration_s': times[-1] - times[0] if len(times) > 0 else 0,
        'initial_state': 'HIGH' if initial_state else 'LOW',
        'all': {
            'min_us': float(durations_us.min()),
            'max_us': float(durations_us.max()),
            'mean_us': float(durations_us.mean()),
            'std_us': float(durations_us.std()),
        },
        'high': {
            'count': len(high_durations_us),
            'min_us': float(high_durations_us.min()) if len(high_durations_us) > 0 else 0,
            'max_us': float(high_durations_us.max()) if len(high_durations_us) > 0 else 0,
            'mean_us': float(high_durations_us.mean()) if len(high_durations_us) > 0 else 0,
        },
        'low': {
            'count': len(low_durations_us),
            'min_us': float(low_durations_us.min()) if len(low_durations_us) > 0 else 0,
            'max_us': float(low_durations_us.max()) if len(low_durations_us) > 0 else 0,
            'mean_us': float(low_durations_us.mean()) if len(low_durations_us) > 0 else 0,
        },
        'durations_us': durations_us,
        'high_durations_us': high_durations_us,
        'low_durations_us': low_durations_us,
    }


def detect_clusters(durations_us: np.ndarray,
                    tolerance: float = 0.15) -> List[Tuple[float, int]]:
    """
    Detect clusters of similar durations.

    Returns list of (center_value, count) tuples sorted by count (most
    common first).
    """
    if len(durations_us) == 0:
        return []

    sorted_durations = np.sort(durations_us)
    clusters = []
    current_cluster = [sorted_durations[0]]

    for dur in sorted_durations[1:]:
        cluster_mean = np.mean(current_cluster)
        if cluster_mean > 0 and abs(dur - cluster_mean) / cluster_mean <= tolerance:
            current_cluster.append(dur)
        elif cluster_mean == 0 and dur == 0:
            current_cluster.append(dur)
        else:
            clusters.append((float(np.mean(current_cluster)), len(current_cluster)))
            current_cluster = [dur]

    if current_cluster:
        clusters.append((float(np.mean(current_cluster)), len(current_cluster)))

    clusters.sort(key=lambda x: -x[1])
    return clusters


def guess_protocol(analysis: dict) -> List[Tuple[str, float, str]]:
    """
    Attempt to guess the protocol based on timing characteristics.

    Returns list of (protocol_name, confidence, details) tuples sorted
    by confidence (highest first).
    """
    guesses = []

    all_min = analysis['all']['min_us']
    all_max = analysis['all']['max_us']

    # Check for UART (look for consistent bit period)
    for baud, period_us in COMMON_BAUD_RATES.items():
        if 0.7 < all_min / period_us < 1.3:
            multiples = analysis['durations_us'] / period_us
            rounded = np.round(multiples)
            error = np.abs(multiples - rounded).mean()
            if error < 0.15:
                guesses.append((
                    f'UART ({baud} baud)',
                    max(0.3, 0.9 - error * 3),
                    f'Bit period ~{period_us:.1f}us'
                ))

    # Check for 1-Wire (reset pulse ~480us, data pulses 1-120us)
    if all_min < 20 and all_max > 400:
        has_reset = any(400 < d < 600 for d in analysis['low_durations_us'])
        has_short = any(d < 20 for d in analysis['durations_us'])
        if has_reset and has_short:
            guesses.append((
                '1-Wire',
                0.6,
                'Detected reset pulses and short data pulses'
            ))

    # Check for CAN bus
    can_bitrates = {125000: 8.0, 250000: 4.0, 500000: 2.0, 1000000: 1.0}
    for bitrate, period_us in can_bitrates.items():
        if 0.7 < all_min / period_us < 1.3:
            multiples = analysis['durations_us'] / period_us
            rounded = np.round(multiples)
            error = np.abs(multiples - rounded).mean()
            if error < 0.15:
                guesses.append((
                    f'CAN ({bitrate // 1000}kbps)',
                    max(0.3, 0.85 - error * 3),
                    f'Bit period ~{period_us:.1f}us'
                ))

    guesses.sort(key=lambda x: -x[1])
    return guesses


def format_duration(us: float) -> str:
    """Format a duration in microseconds with appropriate units."""
    if us < 1000:
        return f"{us:.1f}us"
    elif us < 1000000:
        return f"{us/1000:.2f}ms"
    else:
        return f"{us/1e6:.3f}s"


def print_histogram(durations_us: np.ndarray, bins: int = 20,
                    title: str = "Duration Histogram"):
    """Print a simple ASCII histogram of timing durations."""
    if len(durations_us) == 0:
        print(f"{title}: No data")
        return

    hist, edges = np.histogram(durations_us, bins=bins)
    max_count = max(hist)

    print(f"\n{title}")
    print("=" * 60)

    for i, count in enumerate(hist):
        left = edges[i]
        right = edges[i + 1]
        bar_len = int(40 * count / max_count) if max_count > 0 else 0
        bar = "#" * bar_len
        label = f"{format_duration(left):>10s}-{format_duration(right):>10s}"
        print(f"{label} |{bar} ({count})")


def export_transitions_csv(times: np.ndarray, initial_state: int,
                           output_path, label: str = ""):
    """Export transitions to CSV file."""
    from pathlib import Path
    output_path = Path(output_path)

    with open(output_path, 'w') as f:
        f.write("index,time_s,state,duration_us\n")

        for i, t in enumerate(times):
            state = (initial_state + i) % 2
            if i < len(times) - 1:
                dur = (times[i + 1] - t) * 1e6
            else:
                dur = 0
            f.write(f"{i},{t:.9f},{state},{dur:.3f}\n")

    print(f"Exported {len(times)} transitions to {output_path}")


def parse_sample_rate(text: str) -> float:
    """
    Extract sample rate from a string like '24 MHz' or '1 kHz'.

    Returns sample rate in Hz, or 0.0 if not found.
    """
    match = re.search(r'(\d+(?:\.\d+)?)\s*(Hz|kHz|MHz|GHz)', text)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        multiplier = {'Hz': 1, 'kHz': 1e3, 'MHz': 1e6, 'GHz': 1e9}
        return val * multiplier.get(unit, 1)
    return 0.0
