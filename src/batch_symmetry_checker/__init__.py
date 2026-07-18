"""Reliable batch symmetry reports for periodic crystal structures."""

from .analysis import (
    POINT_GROUP_HM_TO_SCHOENFLIES,
    AnalysisConfig,
    PymatgenStructureLoader,
    analyze_directory,
    analyze_one_structure,
    analyze_structure,
    compare_metric_and_symmetry_crystal_system,
    find_structure_files,
    get_lattice_metric_info,
    resolve_schoenflies,
    validate_symprec_list,
)
from .models import (
    REPORT_SCHEMA_VERSION,
    AnalysisError,
    SymmetryRecord,
    SymmetryReport,
)

__version__ = "0.2.0"
POINT_GROUP_HM_TO_SCHONFLIES = POINT_GROUP_HM_TO_SCHOENFLIES

__all__ = [
    "AnalysisConfig",
    "AnalysisError",
    "POINT_GROUP_HM_TO_SCHOENFLIES",
    "POINT_GROUP_HM_TO_SCHONFLIES",
    "PymatgenStructureLoader",
    "REPORT_SCHEMA_VERSION",
    "SymmetryRecord",
    "SymmetryReport",
    "analyze_directory",
    "analyze_one_structure",
    "analyze_structure",
    "compare_metric_and_symmetry_crystal_system",
    "find_structure_files",
    "get_lattice_metric_info",
    "resolve_schoenflies",
    "validate_symprec_list",
]
