"""Stable-schema report writers with atomic single-file publication."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from dataclasses import fields
from pathlib import Path

from .models import AnalysisError, SymmetryRecord, SymmetryReport

OUTPUT_FORMATS = {"json", "csv", "xlsx"}
RECORD_FIELDS = [field.name for field in fields(SymmetryRecord)]
ERROR_FIELDS = [field.name for field in fields(AnalysisError)]


def infer_format(path: Path, explicit: str | None = None) -> str:
    if explicit:
        output_format = explicit.lower()
    else:
        output_format = path.suffix.lower().lstrip(".")
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"output format must be one of {sorted(OUTPUT_FORMATS)}")
    return output_format


def _write_csv_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _temporary_sibling(path: Path) -> Path:
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    return Path(name)


def _replace_temporary(temporary: Path, destination: Path) -> None:
    temporary.replace(destination)


def write_report(
    report: SymmetryReport,
    path: Path,
    output_format: str | None = None,
    *,
    overwrite: bool = False,
) -> tuple[Path, ...]:
    """Write a report and return every created path."""

    path = path.resolve()
    selected = infer_format(path, output_format)
    prospective_paths = [path]
    if selected == "csv":
        prospective_paths.append(path.with_name(f"{path.stem}.errors.csv"))
    existing = [candidate for candidate in prospective_paths if candidate.exists()]
    if existing and not overwrite:
        rendered = ", ".join(str(candidate) for candidate in existing)
        raise ValueError(f"refusing to overwrite existing output: {rendered}; use --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    if selected == "json":
        temporary = _temporary_sibling(path)
        try:
            temporary.write_text(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            _replace_temporary(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return (path,)
    record_rows = [record.to_dict() for record in report.records]
    error_rows = [error.to_dict() for error in report.errors]
    if selected == "csv":
        error_path = prospective_paths[1]
        record_temporary = _temporary_sibling(path)
        error_temporary = _temporary_sibling(error_path)
        error_backup: Path | None = None
        try:
            _write_csv_rows(record_temporary, record_rows, RECORD_FIELDS)
            _write_csv_rows(error_temporary, error_rows, ERROR_FIELDS)
            # The main report is the commit marker: update the sidecar first
            # and publish the main file only after both complete successfully.
            if error_path.exists():
                error_backup = _temporary_sibling(error_path)
                error_backup.unlink()
                error_path.replace(error_backup)
            try:
                _replace_temporary(error_temporary, error_path)
                _replace_temporary(record_temporary, path)
            except Exception:
                if error_backup is not None and error_backup.exists():
                    error_backup.replace(error_path)
                else:
                    error_path.unlink(missing_ok=True)
                raise
        finally:
            record_temporary.unlink(missing_ok=True)
            error_temporary.unlink(missing_ok=True)
            if error_backup is not None:
                error_backup.unlink(missing_ok=True)
        return (path, error_path)
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "Excel output requires: pip install 'batch-symmetry-checker[excel]'"
        ) from exc
    temporary = _temporary_sibling(path)
    try:
        with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
            pd.DataFrame(record_rows, columns=RECORD_FIELDS).to_excel(
                writer, index=False, sheet_name="symmetry_records"
            )
            pd.DataFrame(error_rows, columns=ERROR_FIELDS).to_excel(
                writer, index=False, sheet_name="errors"
            )
            metadata = report.to_dict()
            metadata.pop("records")
            metadata.pop("errors")
            pd.DataFrame(
                [{"report_metadata_json": json.dumps(metadata, ensure_ascii=False)}]
            ).to_excel(writer, index=False, sheet_name="metadata")
            for worksheet in writer.sheets.values():
                worksheet.freeze_panes = "A2"
        _replace_temporary(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return (path,)
