"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import __version__
from .analysis import TOLERANCE_PRESETS, AnalysisConfig, analyze_directory
from .models import REPORT_SCHEMA_VERSION
from .outputs import write_report

LOGGER = logging.getLogger("batch_symmetry_checker")
EXIT_SUCCESS = 0
EXIT_INCOMPLETE = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch symmetry analysis for periodic crystal structures."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} (schema {REPORT_SCHEMA_VERSION})",
    )
    parser.add_argument("--input", default=".", help="Input directory")
    parser.add_argument(
        "--output", default="symmetry_report.json", help="Output .json, .csv, or .xlsx path"
    )
    parser.add_argument(
        "--format",
        choices=("json", "csv", "xlsx"),
        help="Override format inferred from output suffix",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing report files")
    parser.add_argument("--preset", choices=tuple(TOLERANCE_PRESETS), default="wide")
    parser.add_argument(
        "--tolerances", nargs="+", type=float, help="Custom positive symprec values in angstrom"
    )
    parser.add_argument(
        "--angle-tolerance",
        "--angle_tolerance",
        type=float,
        default=5.0,
        help="spglib angle tolerance in degrees; -1 uses its internal default",
    )
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument(
        "--include-absolute-root",
        action="store_true",
        help="Include the resolved input directory in report metadata (off by default)",
    )
    parser.add_argument(
        "--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO"
    )
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.ERROR if args.quiet else getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )
    tolerances = tuple(args.tolerances) if args.tolerances else TOLERANCE_PRESETS[args.preset]
    config = AnalysisConfig(
        input_dir=Path(args.input),
        tolerances=tolerances,
        angle_tolerance=args.angle_tolerance,
        recursive=args.recursive,
    )
    try:
        report = analyze_directory(
            config,
            producer_version=__version__,
            report_input_root=(
                str(config.input_dir.resolve()) if args.include_absolute_root else "."
            ),
        )
        created = write_report(report, Path(args.output), args.format, overwrite=args.force)
    except (ValueError, RuntimeError, OSError) as exc:
        LOGGER.error("%s", exc)
        return EXIT_USAGE
    for error in report.errors:
        LOGGER.error("%s [%s]: %s", error.source_path, error.code, error.message)
    LOGGER.info(
        "status=%s records=%d errors=%d output=%s",
        report.status,
        len(report.records),
        len(report.errors),
        ", ".join(map(str, created)),
    )
    return EXIT_SUCCESS if report.status == "complete" else EXIT_INCOMPLETE


if __name__ == "__main__":
    raise SystemExit(main())
