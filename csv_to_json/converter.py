"""
Main CSV to JSON converter.

Orchestrates the complete conversion pipeline:
1. Detect encoding and delimiter
2. Parse CSV
3. Normalize fields
4. Validate records
5. Output JSON + error report
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, List, Any

from csv_to_json.encoding import decode_file
from csv_to_json.delimiter import parse_csv_with_delimiter, detect_delimiter
from csv_to_json.normalizers import normalize_field
from csv_to_json.validators import validate_record
from csv_to_json.schemas import REQUIRED_FIELDS, FIELD_VALIDATORS


class CsvToJsonConverter:
    """Converts CSV incident files to JSON format for the dashboard."""

    def __init__(self):
        """Initialize converter."""
        self.valid_records = []
        self.errors = []
        self.stats = {
            "total_records": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0.0
        }

    def convert_file(
        self,
        input_path: str,
        output_path: str = None,
        error_report_path: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Convert CSV file to JSON format.

        Args:
            input_path: Path to input CSV file
            output_path: Path for output JSON file
            error_report_path: Path for error report JSON file

        Returns:
            Tuple of (success: bool, report: dict with stats and errors)
        """
        input_file = Path(input_path)

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Read file bytes
        with open(input_file, 'rb') as f:
            file_bytes = f.read()

        # Decode with encoding detection
        file_text, detected_encoding = self._decode_file(file_bytes)

        # Parse CSV
        records = self._parse_csv(file_text)
        self.stats["total_records"] = len(records)

        # Process each record
        for row_num, record in enumerate(records, start=2):  # Start at 2 (after header)
            success, errors = self._process_record(record, row_num)

            if success:
                self.stats["successful"] += 1
                self.valid_records.append(record)
            else:
                self.stats["failed"] += len(errors)
                for error in errors:
                    self.errors.append({
                        "row": row_num,
                        "fields": {error["field"]: {
                            "original": error["original"],
                            "error": error["error"]
                        }}
                    })

        # Calculate success rate
        if self.stats["total_records"] > 0:
            self.stats["success_rate"] = (
                self.stats["successful"] / self.stats["total_records"] * 100
            )

        # Write output files if paths provided
        if output_path:
            self._write_json_output(output_path)

        if error_report_path:
            self._write_error_report(error_report_path)

        return self.stats["failed"] == 0, {
            "stats": self.stats,
            "errors": self.errors,
            "encoding_detected": detected_encoding
        }

    def _decode_file(self, file_bytes: bytes) -> Tuple[str, str]:
        """Decode file with encoding detection."""
        return decode_file(file_bytes)

    def _parse_csv(self, file_text: str) -> List[Dict[str, str]]:
        """Parse CSV with delimiter detection."""
        return parse_csv_with_delimiter(file_text)

    def _process_record(self, record: Dict[str, str], row_number: int) -> Tuple[bool, List[Dict]]:
        """
        Process a single record: normalize and validate.

        Returns:
            Tuple of (is_valid, errors)
        """
        # Normalize all fields
        normalized_record = {}
        for field_name, value in record.items():
            normalized_record[field_name] = normalize_field(field_name, value)

        # Validate normalized record
        is_valid, errors = validate_record(normalized_record, row_number)

        if is_valid:
            # Update original record with normalized values
            for field_name, value in normalized_record.items():
                record[field_name] = value

        return is_valid, errors

    def _calculate_massive_kpis(self, incidents: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Calculate KPIs for Massive Incidents data.
        Uses same logic as Massive Incidents Dashboard.

        Returns:
            Dictionary with KPI values (total, pending, trends)
        """
        if not incidents:
            return {
                "total": 0,
                "pending": 0,
                "trend_7d": None,
                "trend_15d": None,
                "trend_30d": None
            }

        from datetime import timedelta

        # Total incidents
        total = len(incidents)

        # Pending incidents (NOT closed/resolved/cancelled)
        pending = sum(
            1 for i in incidents
            if (i.get('Estatus', '').lower() not in ['cerrado', 'resuelto', 'cancelado'])
        )

        # Parse date helper
        def parse_date(date_str: str) -> datetime:
            """Parse date in format 'dd/mm/yyyy HH:mm a/p'"""
            try:
                date_part = date_str.split()[0]  # Get "dd/mm/yyyy"
                day, month, year = date_part.split('/')
                return datetime(int(year), int(month), int(day))
            except:
                return None

        # Count pending at different dates (like Dashboard does)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        def count_pending_at_date(target_date: datetime) -> int:
            """Count incidents that were open on target_date"""
            count = 0
            for incident in incidents:
                entry_str = incident.get('Fecha de envío', '')
                if not entry_str:
                    continue

                entry_date = parse_date(entry_str)
                if not entry_date or entry_date > target_date:
                    continue

                status = incident.get('Estatus', '').lower()

                # If closed, check resolution date
                if status in ['cerrado', 'resuelto', 'cancelado']:
                    resolve_str = incident.get('Fecha de última resolución', '')
                    if resolve_str:
                        resolve_date = parse_date(resolve_str)
                        if resolve_date and resolve_date > target_date:
                            count += 1
                else:
                    # Not closed = was open
                    count += 1

            return count

        # Calculate trends
        pending_7d_ago = count_pending_at_date(today - timedelta(days=7))
        pending_15d_ago = count_pending_at_date(today - timedelta(days=15))
        pending_30d_ago = count_pending_at_date(today - timedelta(days=30))

        def calc_trend(count_at_date: int, current: int) -> float:
            """Calculate percentage change"""
            if count_at_date == 0:
                return 0.0 if current == 0 else 100.0
            return ((current - count_at_date) / count_at_date) * 100

        trend_7d = calc_trend(pending_7d_ago, pending)
        trend_15d = calc_trend(pending_15d_ago, pending)
        trend_30d = calc_trend(pending_30d_ago, pending)

        return {
            "total": total,
            "pending": pending,
            "trend_7d": round(trend_7d, 1),
            "trend_15d": round(trend_15d, 1),
            "trend_30d": round(trend_30d, 1)
        }

    def _write_json_output(self, output_path: str) -> None:
        """Write valid records to JSON file with metadata."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine type based on filename
        # Files with "-massive" suffix are Massive Incidents
        # Files with "-postmortem" suffix are Postmortem data
        filename = output_file.stem  # Get filename without extension
        data_type = "massive" if "-massive" in filename else "unknown"

        # Calculate KPIs for massive incidents
        kpis = None
        if data_type == "massive":
            kpis = self._calculate_massive_kpis(self.valid_records)

        # Create output structure with metadata
        metadata = {
            "type": data_type,
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "record_count": len(self.valid_records)
        }

        # Add KPIs to metadata if calculated
        if kpis:
            metadata["kpis"] = kpis

        output_data = {
            "_metadata": metadata,
            "data": self.valid_records
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    def _write_error_report(self, error_report_path: str) -> None:
        """Write error report to JSON file."""
        report_file = Path(error_report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "summary": self.stats,
            "errors": self.errors
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        return self.stats

    def get_errors(self) -> List[Dict]:
        """Get list of validation errors."""
        return self.errors
