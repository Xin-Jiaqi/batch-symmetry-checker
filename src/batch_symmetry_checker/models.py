"""Versioned, JSON-safe report models."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

REPORT_SCHEMA_VERSION = "1.0.0"


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp with second precision."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True, slots=True)
class SymmetryRecord:
    """One successful structure/tolerance analysis result."""

    source_path: str
    source_sha256: str
    formula: str
    num_sites: int
    symprec_angstrom: float
    angle_tolerance_degree: float
    space_group_symbol: str
    space_group_number: int
    hall_symbol: str
    point_group_hm: str
    point_group_schoenflies: str
    crystal_system: str
    lattice_a_angstrom: float
    lattice_b_angstrom: float
    lattice_c_angstrom: float
    lattice_alpha_degree: float
    lattice_beta_degree: float
    lattice_gamma_degree: float
    lattice_relation: str
    metric_crystal_system: str
    metric_vs_symmetry_check: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping with stable field names."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class AnalysisError:
    """A machine-readable failure without an unstable traceback payload."""

    source_path: str
    code: str
    message: str
    symprec_angstrom: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SymmetryReport:
    """A complete batch run, including successful records and failures."""

    records: tuple[SymmetryRecord, ...] = field(default_factory=tuple)
    errors: tuple[AnalysisError, ...] = field(default_factory=tuple)
    input_root: str = ""
    recursive: bool = False
    tolerances_angstrom: tuple[float, ...] = field(default_factory=tuple)
    angle_tolerance_degree: float = 5.0
    generated_at: str = field(default_factory=utc_now_iso)
    producer: str = "batch-symmetry-checker"
    producer_version: str = "unknown"
    pymatgen_version: str = "unknown"
    spglib_version: str = "unknown"
    schema_version: str = REPORT_SCHEMA_VERSION

    @property
    def status(self) -> str:
        if self.records and not self.errors:
            return "complete"
        if self.records:
            return "partial"
        return "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "producer": {
                "name": self.producer,
                "version": self.producer_version,
                "pymatgen_version": self.pymatgen_version,
                "spglib_version": self.spglib_version,
            },
            "generated_at": self.generated_at,
            "status": self.status,
            "configuration": {
                "input_root": self.input_root,
                "recursive": self.recursive,
                "tolerances_angstrom": list(self.tolerances_angstrom),
                "angle_tolerance_degree": self.angle_tolerance_degree,
            },
            "summary": {
                "record_count": len(self.records),
                "error_count": len(self.errors),
                "source_count": len(
                    {record.source_path for record in self.records}
                    | {error.source_path for error in self.errors}
                ),
            },
            "records": [record.to_dict() for record in self.records],
            "errors": [error.to_dict() for error in self.errors],
        }

    @classmethod
    def from_parts(
        cls,
        records: Iterable[SymmetryRecord],
        errors: Iterable[AnalysisError],
        **metadata: Any,
    ) -> SymmetryReport:
        return cls(records=tuple(records), errors=tuple(errors), **metadata)
