from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pymatgen.core import Lattice, Structure

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_alias_is_exported_by_installed_package() -> None:
    import batch_symmetry_checker as package

    assert package.POINT_GROUP_HM_TO_SCHONFLIES is package.POINT_GROUP_HM_TO_SCHOENFLIES


def test_legacy_source_script_remains_executable() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "batch_symmetry_checker.py"), "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "0.2.0" in result.stdout
    assert "deprecated" in result.stderr


def test_legacy_source_script_preserves_xlsx_default(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    Structure(Lattice.cubic(4), ["Si"], [[0, 0, 0]]).to(
        filename=str(inputs / "POSCAR"), fmt="poscar"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "batch_symmetry_checker.py"),
            "--input",
            str(inputs),
            "--tolerances",
            "1e-3",
            "--quiet",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert (tmp_path / "symmetry_check_results.xlsx").is_file()


def test_legacy_source_script_matches_explicit_format_suffix(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    Structure(Lattice.cubic(4), ["Si"], [[0, 0, 0]]).to(
        filename=str(inputs / "POSCAR"), fmt="poscar"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "batch_symmetry_checker.py"),
            "--input",
            str(inputs),
            "--format",
            "json",
            "--tolerances",
            "1e-3",
            "--quiet",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert (tmp_path / "symmetry_check_results.json").is_file()
