# SPDX-License-Identifier: PROPRIETARY
"""Data quality validation framework - Great Expectations-style checkpoints."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

logger = structlog.get_logger("data_quality")


class ValidationResult:
    """Result of a single validation check."""

    def __init__(
        self,
        check_name: str,
        status: str,  # "PASS", "WARN", "FAIL"
        message: str,
        evidence: Optional[Dict[str, Any]] = None,
    ):
        self.check_name = check_name
        self.status = status
        self.message = message
        self.evidence = evidence or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status": self.status,
            "message": self.message,
            "evidence": self.evidence,
        }


class DataQualityCheckpoint:
    """
    Checkpoint pattern for data quality validation.

    Runs validations, produces a report, and can take actions (e.g., alert, block).
    Inspired by Great Expectations Checkpoint concept.
    """

    def __init__(self, artifact_dir: Optional[Path] = None):
        self.artifact_dir = artifact_dir or Path("/tmp/hbc_data_snapshots")
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ValidationResult] = []

    def validate_schema(
        self, df: pd.DataFrame, required_columns: List[str], source_name: str
    ) -> ValidationResult:
        """Validate that DataFrame has required columns."""
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            return ValidationResult(
                check_name=f"{source_name}_schema",
                status="FAIL",
                message=f"Missing required columns: {missing}",
                evidence={
                    "missing_columns": missing,
                    "present_columns": list(df.columns),
                },
            )
        return ValidationResult(
            check_name=f"{source_name}_schema",
            status="PASS",
            message=f"All required columns present: {required_columns}",
        )

    def validate_types(
        self, df: pd.DataFrame, column_types: Dict[str, type], source_name: str
    ) -> ValidationResult:
        """Validate column types."""
        issues = []
        for col, expected_type in column_types.items():
            if col not in df.columns:
                continue
            if expected_type is float:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    issues.append(f"{col} should be numeric, got {df[col].dtype}")
            elif expected_type is str:
                if not pd.api.types.is_string_dtype(df[col]):
                    issues.append(f"{col} should be string, got {df[col].dtype}")

        if issues:
            return ValidationResult(
                check_name=f"{source_name}_types",
                status="FAIL",
                message=f"Type mismatches: {issues}",
                evidence={"issues": issues},
            )
        return ValidationResult(
            check_name=f"{source_name}_types",
            status="PASS",
            message="All column types correct",
        )

    def validate_freshness(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        max_age_hours: int,
        source_name: str,
    ) -> ValidationResult:
        """Validate that data is fresh (within max_age_hours)."""
        if timestamp_col not in df.columns:
            return ValidationResult(
                check_name=f"{source_name}_freshness",
                status="WARN",
                message=f"Timestamp column '{timestamp_col}' not found",
            )

        if df.empty:
            return ValidationResult(
                check_name=f"{source_name}_freshness",
                status="WARN",
                message="DataFrame is empty, cannot check freshness",
            )

        # Get most recent timestamp
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        latest = df[timestamp_col].max()

        age_hours = (datetime.now() - latest).total_seconds() / 3600

        if age_hours > max_age_hours:
            return ValidationResult(
                check_name=f"{source_name}_freshness",
                status="WARN",
                message=f"Data is {age_hours:.1f} hours old (max: {max_age_hours})",
                evidence={"age_hours": age_hours, "latest_timestamp": str(latest)},
            )

        return ValidationResult(
            check_name=f"{source_name}_freshness",
            status="PASS",
            message=f"Data is fresh ({age_hours:.1f} hours old)",
            evidence={"age_hours": age_hours},
        )

    def validate_cardinality(
        self, df: pd.DataFrame, min_rows: int, source_name: str
    ) -> ValidationResult:
        """Validate minimum row count."""
        if len(df) < min_rows:
            return ValidationResult(
                check_name=f"{source_name}_cardinality",
                status="WARN",
                message=f"Only {len(df)} rows (expected at least {min_rows})",
                evidence={"row_count": len(df), "min_expected": min_rows},
            )
        return ValidationResult(
            check_name=f"{source_name}_cardinality",
            status="PASS",
            message=f"Sufficient rows: {len(df)}",
            evidence={"row_count": len(df)},
        )

    def validate_range(
        self,
        df: pd.DataFrame,
        column: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        source_name: str = "",
    ) -> ValidationResult:
        """Validate numeric column is within expected range."""
        if column not in df.columns:
            return ValidationResult(
                check_name=f"{source_name}_range_{column}",
                status="WARN",
                message=f"Column '{column}' not found",
            )

        if df.empty:
            return ValidationResult(
                check_name=f"{source_name}_range_{column}",
                status="WARN",
                message="DataFrame is empty",
            )

        values = df[column].dropna()
        if len(values) == 0:
            return ValidationResult(
                check_name=f"{source_name}_range_{column}",
                status="WARN",
                message=f"Column '{column}' has no non-null values",
            )

        issues = []
        if min_val is not None and values.min() < min_val:
            issues.append(f"Min value {values.min()} < {min_val}")
        if max_val is not None and values.max() > max_val:
            issues.append(f"Max value {values.max()} > {max_val}")

        if issues:
            return ValidationResult(
                check_name=f"{source_name}_range_{column}",
                status="WARN",
                message=f"Range violations: {issues}",
                evidence={
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "expected_range": [min_val, max_val],
                },
            )

        return ValidationResult(
            check_name=f"{source_name}_range_{column}",
            status="PASS",
            message=f"Values in range [{min_val}, {max_val}]",
            evidence={"min": float(values.min()), "max": float(values.max())},
        )

    def save_snapshot(
        self, df: pd.DataFrame, source_name: str, region_id: Optional[str] = None
    ) -> Path:
        """Save a snapshot of the data for evidence/audit."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        region_part = f"_{region_id}" if region_id else ""
        snapshot_dir = self.artifact_dir / source_name
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = snapshot_dir / f"{source_name}{region_part}_{timestamp}.json"
        # Convert DataFrame to JSON-serializable format
        df_dict = df.to_dict(orient="records")
        with open(snapshot_path, "w") as f:
            json.dump(
                {
                    "source": source_name,
                    "region": region_id,
                    "timestamp": timestamp,
                    "row_count": len(df),
                    "columns": list(df.columns),
                    "data": df_dict[:100],  # Sample first 100 rows
                },
                f,
                indent=2,
                default=str,
            )

        return snapshot_path

    def run_checkpoint(
        self,
        source_name: str,
        df: pd.DataFrame,
        region_id: Optional[str] = None,
        required_columns: Optional[List[str]] = None,
        column_types: Optional[Dict[str, type]] = None,
        timestamp_col: Optional[str] = None,
        max_age_hours: int = 48,
        min_rows: int = 1,
        range_checks: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[ValidationResult]:
        """
        Run a full checkpoint for a data source.

        Args:
            source_name: Name of the data source
            df: DataFrame to validate
            region_id: Optional region identifier
            required_columns: Required column names
            column_types: Expected column types
            timestamp_col: Column name for timestamp (for freshness check)
            max_age_hours: Maximum age for freshness check
            min_rows: Minimum row count
            range_checks: Dict of {column: {min: val, max: val}} for range validation
        """
        results = []

        # Save snapshot for evidence
        if not df.empty:
            snapshot_path = self.save_snapshot(df, source_name, region_id)
            logger.info("Saved data snapshot", path=str(snapshot_path))

        # Schema check
        if required_columns:
            results.append(self.validate_schema(df, required_columns, source_name))

        # Type check
        if column_types:
            results.append(self.validate_types(df, column_types, source_name))

        # Cardinality check
        results.append(self.validate_cardinality(df, min_rows, source_name))

        # Freshness check
        if timestamp_col:
            results.append(
                self.validate_freshness(df, timestamp_col, max_age_hours, source_name)
            )

        # Range checks
        if range_checks:
            for col, bounds in range_checks.items():
                results.append(
                    self.validate_range(
                        df,
                        col,
                        min_val=bounds.get("min"),
                        max_val=bounds.get("max"),
                        source_name=source_name,
                    )
                )

        self.results.extend(results)
        return results

    def generate_report(self) -> str:
        """Generate a human-readable data quality report."""
        report_lines = [
            "# HBC Data Quality Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
        ]

        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        warned = sum(1 for r in self.results if r.status == "WARN")
        failed = sum(1 for r in self.results if r.status == "FAIL")

        report_lines.append(f"- Total checks: {total}")
        report_lines.append(f"- PASS: {passed}")
        report_lines.append(f"- WARN: {warned}")
        report_lines.append(f"- FAIL: {failed}")
        report_lines.append("")

        # Group by source
        by_source: Dict[str, List[ValidationResult]] = {}
        for result in self.results:
            source = result.check_name.split("_")[0]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(result)

        report_lines.append("## Per-Source Results")
        for source, results in sorted(by_source.items()):
            report_lines.append(f"\n### {source}")
            for result in results:
                status_emoji = {"PASS": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}.get(
                    result.status, ""
                )
                report_lines.append(
                    f"{status_emoji} {result.check_name}: {result.message}"
                )
                if result.evidence:
                    report_lines.append(
                        f"   Evidence: {json.dumps(result.evidence, indent=2)}"
                    )

        return "\n".join(report_lines)

    def save_report(self, path: Optional[Path] = None) -> Path:
        """Save the data quality report to a file."""
        if path is None:
            path = Path("/tmp/HBC_DATA_QUALITY_REPORT.md")

        report = self.generate_report()
        path.write_text(report)
        logger.info("Saved data quality report", path=str(path))
        return path
