"""Scientific analysis API built on pymatgen's spglib interface."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from .adapters import PymatgenStructureLoader, StructureLoader
from .models import AnalysisError, SymmetryRecord, SymmetryReport

DEFAULT_TOLERANCES = (1e-4, 1e-3, 1e-2, 5e-2, 1e-1)
TOLERANCE_PRESETS: dict[str, tuple[float, ...]] = {
    "fine": (1e-5, 1e-4, 1e-3),
    "normal": (1e-3, 1e-2, 5e-2),
    "rough": (1e-2, 5e-2, 1e-1),
    "wide": DEFAULT_TOLERANCES,
}

POINT_GROUP_HM_TO_SCHOENFLIES = {
    "1": "C1",
    "-1": "Ci",
    "2": "C2",
    "m": "Cs",
    "2/m": "C2h",
    "222": "D2",
    "mm2": "C2v",
    "mmm": "D2h",
    "4": "C4",
    "-4": "S4",
    "4/m": "C4h",
    "422": "D4",
    "4mm": "C4v",
    "-42m": "D2d",
    "4/mmm": "D4h",
    "3": "C3",
    "-3": "C3i",
    "32": "D3",
    "3m": "C3v",
    "-3m": "D3d",
    "6": "C6",
    "-6": "C3h",
    "6/m": "C6h",
    "622": "D6",
    "6mm": "C6v",
    "-6m2": "D3h",
    "6/mmm": "D6h",
    "23": "T",
    "m-3": "Th",
    "432": "O",
    "-43m": "Td",
    "m-3m": "Oh",
}


PointGroupResolver = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    input_dir: Path
    tolerances: tuple[float, ...] = DEFAULT_TOLERANCES
    angle_tolerance: float = 5.0
    recursive: bool = False
    lattice_length_rel_tol: float = 1e-3
    lattice_angle_abs_tol: float = 0.5

    def validate(self) -> None:
        validate_symprec_list(self.tolerances)
        if not math.isfinite(self.angle_tolerance) or (
            self.angle_tolerance < 0 and self.angle_tolerance != -1
        ):
            raise ValueError("angle_tolerance must be -1 or a finite non-negative number")
        if not math.isfinite(self.lattice_length_rel_tol) or self.lattice_length_rel_tol <= 0:
            raise ValueError("lattice_length_rel_tol must be finite and greater than zero")
        if not math.isfinite(self.lattice_angle_abs_tol) or self.lattice_angle_abs_tol <= 0:
            raise ValueError("lattice_angle_abs_tol must be finite and greater than zero")


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_symprec_list(values: Sequence[float]) -> None:
    if not values:
        raise ValueError("at least one symprec tolerance is required")
    invalid = [value for value in values if not math.isfinite(value) or value <= 0]
    if invalid:
        raise ValueError(f"symprec values must be finite and greater than zero: {invalid}")
    if len(set(values)) != len(values):
        raise ValueError("symprec values must be unique")


def find_structure_files(input_dir: Path, recursive: bool = False) -> list[Path]:
    iterator = input_dir.rglob("*") if recursive else input_dir.iterdir()
    files = []
    for path in iterator:
        if not path.is_file():
            continue
        upper = path.name.upper()
        if path.suffix.lower() in {".cif", ".vasp"} or upper in {"POSCAR", "CONTCAR"}:
            files.append(path)
        elif upper.startswith(("POSCAR_", "CONTCAR_")):
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(input_dir).as_posix())


def _equal_length(x: float, y: float, tolerance: float) -> bool:
    return abs(x - y) / max(abs(x), abs(y), 1e-12) <= tolerance


def _equal_angle(x: float, y: float, tolerance: float) -> bool:
    return abs(x - y) <= tolerance


def _length_relation(ab: bool, bc: bool, ac: bool) -> str:
    if ab and bc and ac:
        return "a=b=c"
    if ab and not bc and not ac:
        return "a=b≠c"
    if ac and not ab and not bc:
        return "a=c≠b"
    if bc and not ab and not ac:
        return "b=c≠a"
    if not ab and not bc and not ac:
        return "a≠b, b≠c, a≠c"
    return f"a{'=' if ab else '≠'}b, b{'=' if bc else '≠'}c, a{'=' if ac else '≠'}c"


def get_lattice_metric_info(
    structure: Structure,
    length_rel_tol: float = 1e-3,
    angle_abs_tol: float = 0.5,
) -> tuple[str, str, str]:
    """Return legacy formatted parameters, relation, and metric crystal system."""

    lattice = structure.lattice
    a, b, c = map(float, (lattice.a, lattice.b, lattice.c))
    alpha, beta, gamma = map(float, (lattice.alpha, lattice.beta, lattice.gamma))
    ab = _equal_length(a, b, length_rel_tol)
    bc = _equal_length(b, c, length_rel_tol)
    ac = _equal_length(a, c, length_rel_tol)
    a90, b90, g90 = (_equal_angle(v, 90.0, angle_abs_tol) for v in (alpha, beta, gamma))
    all_90 = a90 and b90 and g90
    all_equal = ab and bc and ac
    lengths = _length_relation(ab, bc, ac)
    parameters = (
        f"a={a:.6f} Å, b={b:.6f} Å, c={c:.6f} Å; α={alpha:.4f}°, β={beta:.4f}°, γ={gamma:.4f}°"
    )
    if all_equal and all_90:
        return parameters, "a=b=c, α=β=γ=90°", "cubic"

    # A conventional hexagonal cell may be presented with any of the three
    # axes as the unique axis.  The angle opposite the equal-length pair is
    # 60/120 degrees and the other two angles are right angles.
    hexagonal_arrangements = (
        (ab, a90 and b90, gamma, "γ"),
        (ac, a90 and g90, beta, "β"),
        (bc, b90 and g90, alpha, "α"),
    )
    for equal_pair, other_angles_right, included_angle, angle_name in hexagonal_arrangements:
        at_60 = _equal_angle(included_angle, 60.0, angle_abs_tol)
        at_120 = _equal_angle(included_angle, 120.0, angle_abs_tol)
        if equal_pair and other_angles_right and (at_60 or at_120):
            target = 60 if at_60 else 120
            return parameters, f"{lengths}, two right angles, {angle_name}={target}°", "hexagonal"

    equal_pair_count = sum((ab, bc, ac))
    if all_90 and equal_pair_count == 1:
        return parameters, f"{lengths}, α=β=γ=90°", "tetragonal"
    if all_90 and equal_pair_count == 0:
        return parameters, f"{lengths}, α=β=γ=90°", "orthorhombic"

    equal_angles = (
        _equal_angle(alpha, beta, angle_abs_tol)
        and _equal_angle(beta, gamma, angle_abs_tol)
        and _equal_angle(alpha, gamma, angle_abs_tol)
    )
    if all_equal and equal_angles and not all_90:
        return parameters, f"a=b=c, α≈β≈γ; α={alpha:.4f}°", "rhombohedral"
    right_count = sum((a90, b90, g90))
    if right_count == 2:
        return parameters, f"{lengths}; α={alpha:.4f}°, β={beta:.4f}°, γ={gamma:.4f}°", "monoclinic"
    if right_count or ab or bc or ac:
        return (
            parameters,
            f"partial relation: {lengths}; α={alpha:.4f}°, β={beta:.4f}°, γ={gamma:.4f}°",
            "ambiguous",
        )
    return parameters, f"{lengths}; α={alpha:.4f}°, β={beta:.4f}°, γ={gamma:.4f}°", "triclinic"


def compare_metric_and_symmetry_crystal_system(
    metric_crystal_system: str, symmetry_crystal_system: str
) -> str:
    metric = metric_crystal_system.lower().strip()
    symmetry = symmetry_crystal_system.lower().strip()
    if metric == "ambiguous":
        return "ambiguous metric"
    if metric == symmetry:
        return "consistent"
    if symmetry == "trigonal" and metric in {"hexagonal", "rhombohedral"}:
        return "compatible: trigonal symmetry with hexagonal/rhombohedral metric"
    return "inconsistent"


def resolve_schoenflies(point_group_hm: str, resolver: PointGroupResolver | None = None) -> str:
    """Resolve a point group, allowing a future shared registry to be injected."""

    if resolver is not None:
        resolved = resolver(point_group_hm)
        if resolved:
            return resolved
    try:
        return POINT_GROUP_HM_TO_SCHOENFLIES[point_group_hm]
    except KeyError as exc:
        raise ValueError(f"unsupported crystallographic point group: {point_group_hm!r}") from exc


def analyze_structure(
    structure: Structure,
    *,
    source_path: str,
    source_sha256: str,
    symprec: float,
    angle_tolerance: float,
    lattice_length_rel_tol: float = 1e-3,
    lattice_angle_abs_tol: float = 0.5,
    point_group_resolver: PointGroupResolver | None = None,
) -> SymmetryRecord:
    _, relation, metric_system = get_lattice_metric_info(
        structure, lattice_length_rel_tol, lattice_angle_abs_tol
    )
    analyzer = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tolerance)
    point_group = analyzer.get_point_group_symbol()
    lattice = structure.lattice
    return SymmetryRecord(
        source_path=source_path,
        source_sha256=source_sha256,
        formula=structure.composition.reduced_formula,
        num_sites=len(structure),
        symprec_angstrom=float(symprec),
        angle_tolerance_degree=float(angle_tolerance),
        space_group_symbol=analyzer.get_space_group_symbol(),
        space_group_number=int(analyzer.get_space_group_number()),
        hall_symbol=analyzer.get_hall(),
        point_group_hm=point_group,
        point_group_schoenflies=resolve_schoenflies(point_group, point_group_resolver),
        crystal_system=analyzer.get_crystal_system(),
        lattice_a_angstrom=float(lattice.a),
        lattice_b_angstrom=float(lattice.b),
        lattice_c_angstrom=float(lattice.c),
        lattice_alpha_degree=float(lattice.alpha),
        lattice_beta_degree=float(lattice.beta),
        lattice_gamma_degree=float(lattice.gamma),
        lattice_relation=relation,
        metric_crystal_system=metric_system,
        metric_vs_symmetry_check=compare_metric_and_symmetry_crystal_system(
            metric_system, analyzer.get_crystal_system()
        ),
    )


def analyze_one_structure(
    file_path: Path,
    symprec: float,
    angle_tolerance: float,
    display_path: str | None = None,
) -> dict[str, object]:
    """Compatibility wrapper for the original single-tolerance API."""

    structure = PymatgenStructureLoader().load(file_path)
    record = analyze_structure(
        structure,
        source_path=display_path or file_path.name,
        source_sha256=sha256_file(file_path),
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    )
    data = record.to_dict()
    return {
        "file_name": data["source_path"],
        "formula": data["formula"],
        "num_sites": data["num_sites"],
        "symprec": data["symprec_angstrom"],
        "space_group_symbol": data["space_group_symbol"],
        "space_group_number": data["space_group_number"],
        "point_group_HM": data["point_group_hm"],
        "point_group_Schoenflies": data["point_group_schoenflies"],
        "crystal_system": data["crystal_system"],
        "lattice_parameters": get_lattice_metric_info(structure)[0],
        "lattice_relation": data["lattice_relation"],
        "metric_crystal_system": data["metric_crystal_system"],
        "metric_vs_symmetry_check": data["metric_vs_symmetry_check"],
    }


def analyze_directory(
    config: AnalysisConfig,
    *,
    loader: StructureLoader | None = None,
    point_group_resolver: PointGroupResolver | None = None,
    producer_version: str = "unknown",
    report_input_root: str = ".",
) -> SymmetryReport:
    """Analyze a directory deterministically, parsing each source exactly once."""

    config.validate()
    root = config.input_dir.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("input directory does not exist or is not a directory")
    files = find_structure_files(root, config.recursive)
    if not files:
        raise ValueError("no supported structure files found in input directory")
    loader = loader or PymatgenStructureLoader()
    records: list[SymmetryRecord] = []
    errors: list[AnalysisError] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        try:
            source_bytes = path.read_bytes()
            source_hash = hashlib.sha256(source_bytes).hexdigest()
            byte_loader = getattr(loader, "load_bytes", None)
            if callable(byte_loader):
                structure = byte_loader(source_bytes, path)
            else:
                structure = loader.load(path)
                if sha256_file(path) != source_hash:
                    raise RuntimeError("source changed while it was being parsed")
        except Exception as exc:
            message = str(exc).replace(str(root), "<input_root>")
            errors.append(AnalysisError(relative, "structure_parse_error", message))
            continue
        for tolerance in config.tolerances:
            try:
                records.append(
                    analyze_structure(
                        structure,
                        source_path=relative,
                        source_sha256=source_hash,
                        symprec=tolerance,
                        angle_tolerance=config.angle_tolerance,
                        lattice_length_rel_tol=config.lattice_length_rel_tol,
                        lattice_angle_abs_tol=config.lattice_angle_abs_tol,
                        point_group_resolver=point_group_resolver,
                    )
                )
            except Exception as exc:
                message = str(exc).replace(str(root), "<input_root>")
                errors.append(
                    AnalysisError(relative, "symmetry_analysis_error", message, tolerance)
                )
    return SymmetryReport.from_parts(
        records,
        errors,
        input_root=report_input_root,
        recursive=config.recursive,
        tolerances_angstrom=config.tolerances,
        angle_tolerance_degree=config.angle_tolerance,
        producer_version=producer_version,
        pymatgen_version=package_version("pymatgen"),
        spglib_version=package_version("spglib"),
    )
