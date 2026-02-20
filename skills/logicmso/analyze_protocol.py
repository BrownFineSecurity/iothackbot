#!/usr/bin/env python3
"""
Protocol Analyzer for Saleae Logic MSO captures.

Analyzes digital signal captures to identify timing patterns and help
determine the protocol being used.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    from saleae.mso_api.binary_files import read_file
except ImportError:
    print("Error: saleae-mso-api not installed. Run: pip install saleae-mso-api")
    sys.exit(1)

# Add parent directory to path for shared module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.signal_analysis import (
    analyze_timing as _analyze_timing,
    detect_clusters,
    export_transitions_csv,
    format_duration,
    guess_protocol,
    print_histogram,
)


def load_capture(file_path: Path) -> dict:
    """Load a Saleae binary capture file and return transition data."""
    saleae_file = read_file(file_path)

    if not hasattr(saleae_file.contents, 'chunks') or len(saleae_file.contents.chunks) == 0:
        raise ValueError("No digital data chunks found in file")

    chunk = saleae_file.contents.chunks[0]
    times = np.array(chunk.transition_times)

    return {
        'times': times,
        'initial_state': chunk.initial_state,
        'sample_rate': chunk.sample_rate,
        'begin_time': chunk.begin_time,
        'end_time': chunk.end_time,
    }


def analyze_timing(data: dict) -> dict:
    """Analyze timing characteristics of the signal."""
    duration = data['end_time'] - data['begin_time']
    return _analyze_timing(data['times'], data['initial_state'], duration)


def export_csv(data: dict, output_path: Path):
    """Export transitions to CSV file."""
    export_transitions_csv(data['times'], data['initial_state'], output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze digital signal captures from Saleae Logic MSO"
    )
    parser.add_argument("file", type=Path, help="Binary capture file (.bin)")
    parser.add_argument("--histogram", action="store_true",
                        help="Show timing histogram")
    parser.add_argument("--bins", type=int, default=20,
                        help="Number of histogram bins (default: 20)")
    parser.add_argument("--export", type=Path, metavar="CSV",
                        help="Export transitions to CSV file")
    parser.add_argument("--clusters", action="store_true",
                        help="Show detected timing clusters")
    parser.add_argument("--raw", action="store_true",
                        help="Show raw duration values")
    parser.add_argument("-n", type=int, default=20,
                        help="Number of raw values to show (default: 20)")

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    try:
        data = load_capture(args.file)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    analysis = analyze_timing(data)

    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        sys.exit(1)

    # Print basic info
    print(f"File: {args.file}")
    print(f"Sample rate: {data['sample_rate']/1e6:.1f} MHz")
    print(f"Capture duration: {analysis['capture_duration_s']:.3f}s")
    print(f"Signal duration: {analysis['signal_duration_s']:.3f}s")
    print(f"Initial state: {analysis['initial_state']}")
    print(f"Total transitions: {analysis['total_transitions']}")
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
        print_histogram(analysis['durations_us'], bins=args.bins, title="All Durations")
        print_histogram(analysis['high_durations_us'], bins=args.bins, title="HIGH Pulse Durations")
        print_histogram(analysis['low_durations_us'], bins=args.bins, title="LOW Gap Durations")

    # Export
    if args.export:
        export_csv(data, args.export)


if __name__ == "__main__":
    main()
