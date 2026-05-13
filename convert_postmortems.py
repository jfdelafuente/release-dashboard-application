#!/usr/bin/env python3
"""
Postmortem CSV to JSON Converter CLI.

Converts postmortem CSV files to JSON format compatible with Postmortem Dashboard.

Features:
- Auto-detects CSV encoding and delimiter
- Normalizes field names and data types
- Calculates KPIs and includes in metadata
- Outputs with -postmortem suffix for Dashboard Hub auto-discovery
- Generates detailed error reports for invalid records
- Supports batch processing of multiple files

Usage:
    Single file:
        python convert_postmortems.py data/input/postmortem.csv

    With explicit output:
        python convert_postmortems.py data/input/postmortem.csv -o data/output/custom-output.json

    Batch mode (process all CSVs in directory):
        python convert_postmortems.py data/input/ -b

    With error report:
        python convert_postmortems.py data/input/postmortem.csv -e data/errors/report.json
"""

import argparse
import sys
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter


def get_output_path(input_path: Path, output_dir: Path = None) -> Path:
    """
    Generate output path with -postmortem suffix.

    Args:
        input_path: Input CSV file path
        output_dir: Output directory (defaults to data/output/)

    Returns:
        Output JSON file path with -postmortem suffix
    """
    if output_dir is None:
        output_dir = Path("data") / "output"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract base name without extension
    base_name = input_path.stem

    # Add -postmortem suffix
    output_filename = f"{base_name}-postmortem.json"
    return output_dir / output_filename


def get_error_report_path(output_path: Path, error_dir: Path = None) -> Path:
    """
    Generate error report path based on output filename.

    Args:
        output_path: Output JSON file path
        error_dir: Error directory (defaults to data/errors/)

    Returns:
        Error report JSON file path
    """
    if error_dir is None:
        error_dir = Path("data") / "errors"

    error_dir.mkdir(parents=True, exist_ok=True)

    # Use same base name as output with _errors suffix
    error_filename = f"{output_path.stem}_errors.json"
    return error_dir / error_filename


def convert_single_file(input_path: Path, output_path: Path = None, error_path: Path = None) -> bool:
    """
    Convert a single postmortem CSV to JSON.

    Args:
        input_path: Path to input CSV file
        output_path: Path for output JSON (auto-generated if not specified)
        error_path: Path for error report (auto-generated if not specified)

    Returns:
        True if conversion successful (no invalid records), False otherwise
    """
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return False

    # Generate output path if not specified
    if output_path is None:
        output_path = get_output_path(input_path)

    # Generate error path if not specified
    if error_path is None:
        error_path = get_error_report_path(output_path)

    print(f"\nConverting: {input_path}")
    print(f"  Output:   {output_path}")
    print(f"  Errors:   {error_path}")

    converter = PostmortemConverter()
    success, report = converter.convert_file(
        str(input_path),
        str(output_path),
        str(error_path)
    )

    # Report results
    stats = report['stats']
    print(f"  Result:   {stats['successful']}/{stats['total_records']} records converted")
    print(f"  Success:  {stats['success_rate']:.1f}%")
    print(f"  Encoding: {report['encoding_detected']}")

    if not success:
        print(f"  WARNING: {stats['failed']} records failed validation")
        print(f"  ERROR:   {error_path}")

    return success


def convert_batch(input_dir: Path, output_dir: Path = None, error_dir: Path = None) -> tuple:
    """
    Convert all CSV files in a directory.

    Args:
        input_dir: Directory containing CSV files
        output_dir: Output directory for JSON files
        error_dir: Error directory for error reports

    Returns:
        Tuple of (total_files, successful_conversions)
    """
    if not input_dir.is_dir():
        print(f"ERROR: Input directory not found: {input_dir}")
        return 0, 0

    csv_files = list(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"WARNING: No CSV files found in {input_dir}")
        return 0, 0

    print(f"\nBatch converting {len(csv_files)} CSV files from {input_dir}")

    successful = 0
    for csv_file in csv_files:
        output_path = get_output_path(csv_file, output_dir)
        error_path = get_error_report_path(output_path, error_dir)

        if convert_single_file(csv_file, output_path, error_path):
            successful += 1

    print(f"\n{successful}/{len(csv_files)} files converted successfully")
    return len(csv_files), successful


def main():
    """Parse arguments and execute conversion."""
    parser = argparse.ArgumentParser(
        description="Convert postmortem CSV files to JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file (output to data/output/ with -postmortem suffix)
  python convert_postmortems.py data/input/postmortem.csv

  # Batch mode (convert all CSVs in directory)
  python convert_postmortems.py data/input/ -b

  # Custom output location
  python convert_postmortems.py data/input/postmortem.csv -o custom_output.json

  # With error report location
  python convert_postmortems.py data/input/postmortem.csv -e custom_errors.json

  # Batch with custom directories
  python convert_postmortems.py data/input/ -b -o data/output/ -e data/errors/
        """
    )

    parser.add_argument(
        "input",
        help="Input CSV file or directory (for batch mode)"
    )
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="Batch mode: process all CSV files in input directory"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: data/output/<filename>-postmortem.json)"
    )
    parser.add_argument(
        "-e", "--errors",
        help="Error report path (default: data/errors/<filename>_errors.json)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    error_path = Path(args.errors) if args.errors else None

    try:
        if args.batch:
            total, successful = convert_batch(input_path, output_path, error_path)
            sys.exit(0 if successful == total else 1)
        else:
            success = convert_single_file(input_path, output_path, error_path)
            sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
