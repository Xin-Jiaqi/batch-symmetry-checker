#!/usr/bin/env python3
"""Deprecated source-checkout entry point.

Prefer the installed ``batch-symmetry-checker`` command. This wrapper remains
for users who previously ran ``python batch_symmetry_checker.py`` directly.
"""

import sys
from pathlib import Path

# When imported from a source checkout, make this module package-like so legacy
# ``import batch_symmetry_checker`` users see the same API as an installed wheel.
__path__ = [str(Path(__file__).resolve().parent / "src" / "batch_symmetry_checker")]
__package__ = __name__
if __spec__ is not None:
    __spec__.submodule_search_locations = __path__
from .adapters import (  # noqa: E402,F401
    MaterialsStructureCoreLoader,
    MaterialsStructureCoreUnavailableError,
    PymatgenStructureLoader,
    StructureLoader,
    structure_record_to_pymatgen,
)
from .analysis import (  # noqa: E402,F401
    POINT_GROUP_HM_TO_SCHOENFLIES,
    AnalysisConfig,
    analyze_directory,
    analyze_one_structure,
    analyze_structure,
    compare_metric_and_symmetry_crystal_system,
    find_structure_files,
    get_lattice_metric_info,
    resolve_schoenflies,
    validate_symprec_list,
)
from .models import (  # noqa: E402,F401
    REPORT_SCHEMA_VERSION,
    AnalysisError,
    SymmetryRecord,
    SymmetryReport,
)

__version__ = "0.2.0"

# Preserve the historical misspelling used by the original single-file API.
POINT_GROUP_HM_TO_SCHONFLIES = POINT_GROUP_HM_TO_SCHOENFLIES


def main(argv: list[str] | None = None) -> int:
    """Launch the modern CLI while preserving the old script's XLSX default."""

    from .cli import main as package_main

    arguments = list(sys.argv[1:] if argv is None else argv)
    has_output = any(item == "--output" or item.startswith("--output=") for item in arguments)
    if not has_output:
        selected_format = "xlsx"
        for position, item in enumerate(arguments):
            if item.startswith("--format="):
                selected_format = item.split("=", 1)[1]
            elif item == "--format" and position + 1 < len(arguments):
                selected_format = arguments[position + 1]
        arguments.extend(("--output", f"symmetry_check_results.{selected_format}"))
    return package_main(arguments)


if __name__ == "__main__":
    print(
        "WARNING: direct script execution is deprecated; install the project "
        "and use 'batch-symmetry-checker'.",
        file=sys.stderr,
    )
    raise SystemExit(main())
