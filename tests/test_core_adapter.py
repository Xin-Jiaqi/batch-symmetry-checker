from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from materials_structure_core import StructureRecord
from pymatgen.core import Lattice, Structure

from batch_symmetry_checker import (
    AnalysisConfig,
    MaterialsStructureCoreLoader,
    PymatgenStructureLoader,
    analyze_directory,
    structure_record_to_pymatgen,
)
from batch_symmetry_checker.cli import EXIT_SUCCESS, main


def write_poscar(path: Path) -> None:
    Structure(
        Lattice.from_parameters(3.1, 3.1, 12.0, 90, 90, 120),
        ["B", "N"],
        [[0, 0, 0.5], [1 / 3, 2 / 3, 0.5]],
    ).to(filename=str(path), fmt="poscar")


def test_structure_record_conversion_preserves_analysis_coordinates() -> None:
    record = StructureRecord.from_fractional(
        lattice=[[3.0, 0.0, 0.0], [0.2, 3.2, 0.0], [0.1, 0.3, 9.0]],
        species=["B", "N"],
        fractional_coordinates=[[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]],
        selective_dynamics=[[True, False, True], [True, True, True]],
    )
    converted = structure_record_to_pymatgen(record)
    assert [str(specie) for specie in converted.species] == list(record.species)
    np.testing.assert_allclose(converted.lattice.matrix, record.lattice_array())
    np.testing.assert_allclose(converted.frac_coords, record.fractional_array())


def test_nonperiodic_record_is_not_silently_promoted_to_3d_periodic() -> None:
    record = StructureRecord.from_fractional(
        lattice=np.eye(3),
        species=["H"],
        fractional_coordinates=[[0, 0, 0]],
        pbc=[True, True, False],
    )
    with pytest.raises(ValueError, match="requires pbc"):
        structure_record_to_pymatgen(record)


def test_core_and_pymatgen_loaders_produce_equivalent_symmetry_records(tmp_path: Path) -> None:
    write_poscar(tmp_path / "POSCAR")
    config = AnalysisConfig(tmp_path, tolerances=(1e-4, 1e-3))
    direct = analyze_directory(config, loader=PymatgenStructureLoader(), producer_version="test")
    core = analyze_directory(config, loader=MaterialsStructureCoreLoader(), producer_version="test")
    assert core.status == direct.status == "complete"
    assert [record.to_dict() for record in core.records] == [
        record.to_dict() for record in direct.records
    ]


def test_core_loader_keeps_strict_core_parse_failures_and_redacts_temporary_path(
    tmp_path: Path,
) -> None:
    (tmp_path / "POSCAR_bad").write_text(
        "velocity fixture\n1\n1 0 0\n0 1 0\n0 0 1\nH\n1\n"
        "Direct\n0 0 0\nCartesian\n0.01 0.02 0.03\n",
        encoding="utf-8",
    )
    report = analyze_directory(
        AnalysisConfig(tmp_path, tolerances=(1e-3,)),
        loader=MaterialsStructureCoreLoader(),
        producer_version="test",
    )
    assert report.status == "failed"
    assert len(report.errors) == 1
    assert report.errors[0].code == "structure_parse_error"
    assert "bsc-core-" not in report.errors[0].message
    assert str(tmp_path) not in report.errors[0].message


def test_core_loader_wraps_exceptions_with_nonstandard_constructors(tmp_path: Path) -> None:
    loader = MaterialsStructureCoreLoader()

    def fail_decode(*args: object, **kwargs: object) -> object:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid fixture")

    loader._read_structure = fail_decode
    with pytest.raises(RuntimeError, match="codec can't decode byte"):
        loader.load_bytes(b"\xff", tmp_path / "POSCAR")


def test_cli_can_select_core_input_contract(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    write_poscar(inputs / "POSCAR")
    output = tmp_path / "report.json"
    assert (
        main(
            [
                "--input",
                str(inputs),
                "--output",
                str(output),
                "--tolerances",
                "1e-3",
                "--structure-loader",
                "core",
                "--quiet",
            ]
        )
        == EXIT_SUCCESS
    )
    assert output.is_file()
