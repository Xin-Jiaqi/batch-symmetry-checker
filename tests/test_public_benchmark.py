from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path

import pytest

from batch_symmetry_checker import (
    REPORT_SCHEMA_VERSION,
    AnalysisConfig,
    __version__,
    analyze_directory,
)

TOLERANCES = (1e-4, 1e-3, 1e-2, 5e-2)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_payload(report: object) -> dict[str, object]:
    payload = report.to_dict()  # type: ignore[attr-defined]
    payload.pop("generated_at")
    return payload


def test_pinned_public_benchmark_contract(tmp_path: Path) -> None:
    configured_root = os.environ.get("MATERIALS_STRUCTURE_BENCHMARK_ROOT")
    if not configured_root:
        pytest.skip("set MATERIALS_STRUCTURE_BENCHMARK_ROOT for cross-repository validation")

    benchmark_root = Path(configured_root)
    split = json.loads(
        (benchmark_root / "splits/batch-smoke-v1.json").read_text(encoding="utf-8")
    )
    assert split["schema_version"] == 1
    assert split["id"] == "batch-smoke-v1"
    assert len(split["records"]) == 12
    assert Counter(entry["structure_type"] for entry in split["records"]) == {
        "monolayer": 6,
        "bulk": 6,
    }

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    expected_hashes: dict[str, str] = {}
    for entry in split["records"]:
        source = benchmark_root / entry["path"]
        output_name = f"{entry['id']}.vasp"
        assert source.is_file(), f"missing pinned benchmark structure: {source}"
        assert _sha256_file(source) == entry["sha256"]
        assert entry["license"] in {"CC-BY-4.0", "CC0-1.0"}
        shutil.copyfile(source, inputs / output_name)
        expected_hashes[output_name] = entry["sha256"]

    config = AnalysisConfig(input_dir=inputs, tolerances=TOLERANCES)
    first = analyze_directory(config, producer_version=__version__)
    second = analyze_directory(config, producer_version=__version__)

    assert first.status == "complete"
    assert first.schema_version == REPORT_SCHEMA_VERSION
    assert first.producer_version == __version__
    assert first.input_root == "."
    assert not first.errors
    assert len(first.records) == 48
    assert _stable_payload(first) == _stable_payload(second)

    combinations = Counter(
        (record.source_path, record.symprec_angstrom) for record in first.records
    )
    assert set(combinations.values()) == {1}
    assert set(combinations) == {
        (source_path, tolerance)
        for source_path in expected_hashes
        for tolerance in TOLERANCES
    }
    for record in first.records:
        assert record.source_sha256 == expected_hashes[record.source_path]
        assert 1 <= record.space_group_number <= 230
        assert record.space_group_symbol
        assert record.hall_symbol
        assert record.point_group_hm
        assert record.point_group_schoenflies
        assert record.crystal_system
        assert not Path(record.source_path).is_absolute()
