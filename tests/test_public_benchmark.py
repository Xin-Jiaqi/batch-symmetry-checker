from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest

from batch_symmetry_checker import AnalysisConfig, analyze_directory

BENCHMARK_CASES = {
    "bulk.vasp": {
        "relative_path": "structures/bulk/cod/9008574.vasp",
        "sha256": "779e40f436a0f05cf6d2aed15d6c2665a97d635e4d1b3562dc4648ccf6ffae7c",
        "space_group": "R-3m",
        "point_group": "-3m",
    },
    "monolayer.vasp": {
        "relative_path": (
            "structures/monolayer/mc2d/00/"
            "002e6827-db47-4e77-9e91-25db60799475.vasp"
        ),
        "sha256": "270ddc035eb7c5abfda61a5f9616d7a71be45e4d3234010a7bd09a540004d8c2",
        "space_group": "Cmme",
        "point_group": "mmm",
    },
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_pinned_public_benchmark_contract(tmp_path: Path) -> None:
    configured_root = os.environ.get("MATERIALS_STRUCTURE_BENCHMARK_ROOT")
    if not configured_root:
        pytest.skip("set MATERIALS_STRUCTURE_BENCHMARK_ROOT for cross-repository validation")

    benchmark_root = Path(configured_root)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for output_name, case in BENCHMARK_CASES.items():
        source = benchmark_root / str(case["relative_path"])
        assert source.is_file(), f"missing pinned benchmark structure: {source}"
        assert _sha256_file(source) == case["sha256"]
        shutil.copyfile(source, inputs / output_name)

    report = analyze_directory(
        AnalysisConfig(input_dir=inputs, tolerances=(1e-3, 1e-2)),
        producer_version="public-benchmark-integration",
    )

    assert report.status == "complete"
    assert not report.errors
    assert len(report.records) == 4
    for record in report.records:
        case = BENCHMARK_CASES[record.source_path]
        assert record.source_sha256 == case["sha256"]
        assert record.space_group_symbol == case["space_group"]
        assert record.point_group_hm == case["point_group"]
        assert record.symprec_angstrom in {1e-3, 1e-2}
