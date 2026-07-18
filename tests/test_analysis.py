from __future__ import annotations

from pathlib import Path

import pytest
from pymatgen.core import Lattice, Structure

from batch_symmetry_checker import (
    POINT_GROUP_HM_TO_SCHOENFLIES,
    AnalysisConfig,
    analyze_directory,
    analyze_structure,
    get_lattice_metric_info,
    validate_symprec_list,
)


def one_atom(lattice: Lattice) -> Structure:
    return Structure(lattice, ["Si"], [[0, 0, 0]])


def write_poscar(path: Path, structure: Structure | None = None) -> None:
    (structure or one_atom(Lattice.cubic(4.0))).to(filename=str(path), fmt="poscar")


class CountingLoader:
    def __init__(self) -> None:
        self.calls = 0

    def load(self, path: Path) -> Structure:
        self.calls += 1
        return Structure.from_file(path)


class MutatingLoader:
    def load(self, path: Path) -> Structure:
        structure = Structure.from_file(path)
        path.write_text("changed during parse\n", encoding="utf-8")
        return structure


@pytest.mark.parametrize("gamma", [60.0, 120.0])
def test_hexagonal_metric_accepts_conventional_basis_choices(gamma: float) -> None:
    structure = one_atom(Lattice.from_parameters(4, 4, 7, 90, 90, gamma))
    _, relation, metric = get_lattice_metric_info(structure)
    assert metric == "hexagonal"
    assert f"γ={int(gamma)}°" in relation


def test_hexagonal_metric_does_not_depend_on_accidental_c_length() -> None:
    structure = one_atom(Lattice.from_parameters(4, 4, 4, 90, 90, 120))
    _, relation, metric = get_lattice_metric_info(structure)
    assert metric == "hexagonal"
    assert relation.startswith("a=b=c")


@pytest.mark.parametrize(
    ("parameters", "angle_name"),
    [
        ((4, 7, 4, 90, 120, 90), "β"),
        ((7, 4, 4, 120, 90, 90), "α"),
    ],
)
def test_hexagonal_metric_is_invariant_to_unique_axis_choice(
    parameters: tuple[float, ...], angle_name: str
) -> None:
    structure = one_atom(Lattice.from_parameters(*parameters))
    _, relation, metric = get_lattice_metric_info(structure)
    assert metric == "hexagonal"
    assert f"{angle_name}=120°" in relation


@pytest.mark.parametrize("lengths", [(4, 7, 4), (7, 4, 4)])
def test_tetragonal_metric_is_invariant_to_unique_axis_choice(
    lengths: tuple[float, float, float]
) -> None:
    structure = one_atom(Lattice.from_parameters(*lengths, 90, 90, 90))
    assert get_lattice_metric_info(structure)[2] == "tetragonal"


def test_rhombohedral_metric_requires_all_angle_pairs_within_tolerance() -> None:
    structure = one_atom(Lattice.from_parameters(4, 4, 4, 60.0, 60.4, 60.8))
    assert get_lattice_metric_info(structure, angle_abs_tol=0.5)[2] != "rhombohedral"


def test_monoclinic_relation_does_not_invent_length_inequality() -> None:
    structure = one_atom(Lattice.from_parameters(4, 4, 7, 90, 100, 90))
    _, relation, metric = get_lattice_metric_info(structure)
    assert metric == "monoclinic"
    assert relation.startswith("a=b≠c")


def test_ideal_cubic_scientific_invariants() -> None:
    record = analyze_structure(
        one_atom(Lattice.cubic(4.0)),
        source_path="POSCAR",
        source_sha256="0" * 64,
        symprec=1e-5,
        angle_tolerance=5.0,
    )
    assert record.space_group_symbol == "Pm-3m"
    assert record.space_group_number == 221
    assert record.point_group_hm == "m-3m"
    assert record.point_group_schoenflies == "Oh"
    assert record.crystal_system == record.metric_crystal_system == "cubic"
    assert record.metric_vs_symmetry_check == "consistent"


def test_registry_contains_exactly_32_crystallographic_point_groups() -> None:
    assert len(POINT_GROUP_HM_TO_SCHOENFLIES) == 32
    assert len(set(POINT_GROUP_HM_TO_SCHOENFLIES.values())) == 32


def test_directory_parses_each_structure_once_for_many_tolerances(tmp_path: Path) -> None:
    write_poscar(tmp_path / "POSCAR")
    loader = CountingLoader()
    report = analyze_directory(
        AnalysisConfig(tmp_path, tolerances=(1e-4, 1e-3, 1e-2)),
        loader=loader,
        producer_version="test",
    )
    assert loader.calls == 1
    assert len(report.records) == 3
    assert report.status == "complete"
    assert len({record.source_sha256 for record in report.records}) == 1


def test_parse_failure_is_one_file_level_error_not_one_per_tolerance(tmp_path: Path) -> None:
    (tmp_path / "POSCAR_broken").write_text("broken\n", encoding="utf-8")
    report = analyze_directory(
        AnalysisConfig(tmp_path, tolerances=(1e-4, 1e-3, 1e-2)), producer_version="test"
    )
    assert not report.records
    assert len(report.errors) == 1
    assert report.errors[0].code == "structure_parse_error"
    assert report.errors[0].symprec_angstrom is None


def test_custom_loader_source_change_is_rejected_as_a_provenance_failure(tmp_path: Path) -> None:
    write_poscar(tmp_path / "POSCAR")
    report = analyze_directory(
        AnalysisConfig(tmp_path, tolerances=(1e-3,)),
        loader=MutatingLoader(),
        producer_version="test",
    )
    assert not report.records
    assert len(report.errors) == 1
    assert "source changed" in report.errors[0].message


def test_recursive_paths_and_order_are_deterministic(tmp_path: Path) -> None:
    (tmp_path / "z").mkdir()
    (tmp_path / "a").mkdir()
    write_poscar(tmp_path / "z" / "POSCAR")
    write_poscar(tmp_path / "a" / "POSCAR")
    report = analyze_directory(
        AnalysisConfig(tmp_path, tolerances=(1e-3,), recursive=True), producer_version="test"
    )
    assert [record.source_path for record in report.records] == ["a/POSCAR", "z/POSCAR"]


@pytest.mark.parametrize("values", [(), (0.0,), (float("nan"),), (1e-3, 1e-3)])
def test_invalid_symprec_lists_are_rejected(values: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        validate_symprec_list(values)


def test_angle_tolerance_only_accepts_spglib_sentinel_or_non_negative(tmp_path: Path) -> None:
    AnalysisConfig(tmp_path, angle_tolerance=-1).validate()
    AnalysisConfig(tmp_path, angle_tolerance=0).validate()
    with pytest.raises(ValueError):
        AnalysisConfig(tmp_path, angle_tolerance=-0.5).validate()
