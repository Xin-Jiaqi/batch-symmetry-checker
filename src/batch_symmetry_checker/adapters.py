"""Structure input adapters shared by the public API and CLI."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal, Protocol

from pymatgen.core import Structure


class StructureLoader(Protocol):
    """Load a supported structure into pymatgen's analysis representation."""

    def load(self, path: Path) -> Structure: ...


class PymatgenStructureLoader:
    """Read CIF, POSCAR, CONTCAR, and ``.vasp`` files with pymatgen."""

    def load(self, path: Path) -> Structure:
        return Structure.from_file(str(path))

    def load_bytes(self, payload: bytes, path: Path) -> Structure:
        """Parse the same immutable byte snapshot used for provenance."""

        format_name: Literal["cif", "poscar"] = (
            "cif" if path.suffix.lower() == ".cif" else "poscar"
        )
        return Structure.from_str(payload.decode("utf-8"), fmt=format_name)


class MaterialsStructureCoreUnavailableError(RuntimeError):
    """Raised when the optional core input adapter cannot be constructed."""


def structure_record_to_pymatgen(record: Any) -> Structure:
    """Convert a ``materials-structure-core`` record without changing its cell.

    Symmetry analysis is three-dimensionally periodic, so records with a
    non-periodic axis are rejected instead of silently changing their PBC
    contract. Selective-dynamics flags do not alter crystallographic symmetry
    and therefore remain input metadata rather than pymatgen site properties.
    """

    if not all(record.pbc):
        raise ValueError(
            "batch symmetry analysis requires pbc=(True, True, True); "
            "a non-periodic StructureRecord cannot be converted implicitly"
        )
    return Structure(
        lattice=record.lattice_array(),
        species=list(record.species),
        coords=record.fractional_array(),
        coords_are_cartesian=False,
        to_unit_cell=False,
        validate_proximity=False,
    )


class MaterialsStructureCoreLoader:
    """Read structures through the stable ``materials-structure-core`` contract.

    The dependency is imported only when this adapter is selected, so the base
    pymatgen input path remains available to existing users.
    """

    def __init__(self) -> None:
        try:
            from materials_structure_core import __version__ as core_version
            from materials_structure_core import read_structure
        except ImportError as exc:
            raise MaterialsStructureCoreUnavailableError(
                "the 'core' structure loader requires materials-structure-core "
                "0.0.2 or newer with its I/O dependencies"
            ) from exc
        try:
            version_parts = tuple(int(part) for part in core_version.split(".")[:3])
        except (AttributeError, ValueError) as exc:
            raise MaterialsStructureCoreUnavailableError(
                "materials-structure-core has an unreadable version; 0.0.2 or newer is required"
            ) from exc
        if version_parts < (0, 0, 2):
            raise MaterialsStructureCoreUnavailableError(
                "the 'core' structure loader requires materials-structure-core 0.0.2 or newer"
            )
        self._read_structure: Callable[..., Any] = read_structure

    @staticmethod
    def _format(path: Path) -> str:
        return "cif" if path.suffix.lower() == ".cif" else "vasp"

    def load(self, path: Path) -> Structure:
        result = self._read_structure(path, format=self._format(path))
        return structure_record_to_pymatgen(result.structure)

    def load_bytes(self, payload: bytes, path: Path) -> Structure:
        """Parse an immutable source snapshot through the core file contract."""

        suffix = ".cif" if self._format(path) == "cif" else ".vasp"
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(prefix="bsc-core-", suffix=suffix, delete=False) as handle:
                handle.write(payload)
                temporary = Path(handle.name)
            result = self._read_structure(temporary, format=self._format(path))
            expected_hash = hashlib.sha256(payload).hexdigest()
            if result.source_sha256 != expected_hash:
                raise RuntimeError("materials-structure-core returned a mismatched source hash")
            return structure_record_to_pymatgen(result.structure)
        except Exception as exc:
            if temporary is None:
                raise
            message = str(exc).replace(str(temporary), str(path))
            # Parser exceptions do not share a common constructor contract
            # (for example, UnicodeDecodeError requires five arguments).  A
            # stable wrapper preserves the useful, redacted message without
            # risking a second exception while handling the first one.
            raise RuntimeError(message) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
