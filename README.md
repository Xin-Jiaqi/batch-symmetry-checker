# Batch Symmetry Checker

[![tests](https://github.com/Xin-Jiaqi/batch-symmetry-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/Xin-Jiaqi/batch-symmetry-checker/actions/workflows/tests.yml)

Batch Symmetry Checker creates versioned, machine-readable symmetry reports for periodic crystal structures. It reads CIF, POSCAR, CONTCAR, and `.vasp` files through pymatgen or the validated `materials-structure-core` input contract, evaluates each structure over one or more spglib tolerances, and records space group, point group, crystal system, lattice metric, source hash, and structured failures.

The project is an **alpha research tool**. It supports reproducible screening and quality control; it does not replace crystallographic validation for publication. In particular, a three-dimensional space-group result for a slab with vacuum must be interpreted in its physical context.

## Why this release matters

- Every source structure is parsed exactly once, regardless of tolerance count.
- JSON is the default output; CSV and Excel are also supported.
- Report schema `1.0.0` separates successful records from file- and tolerance-level errors.
- Source SHA-256, dependency versions, units, and run configuration are recorded.
- Reports use relative source paths and a logical input root by default, avoiding accidental disclosure of local usernames and project directories.
- The Python API and CLI can use the released `materials-structure-core` 0.0.2 contract while retaining the original pymatgen loader for compatibility.
- Partial batches keep valid results and return a nonzero exit status.

## Installation

Python 3.10 or newer is required.

```bash
python -m pip install -e .
```

Excel output is optional:

```bash
python -m pip install -e '.[excel]'
```

The project is available under the [BSD 3-Clause License](LICENSE).

The optional core loader currently uses the tagged GitHub release because the
core package is not yet distributed through PyPI:

```bash
python -m pip install \
  'materials-structure-core[io] @ git+https://github.com/Xin-Jiaqi/materials-structure-core.git@v0.0.2'
```

## Command line

```bash
batch-symmetry-checker --input ./structures --recursive
```

To make the shared structure contract the explicit parsing boundary:

```bash
batch-symmetry-checker \
  --input ./structures \
  --structure-loader core
```

`pymatgen` remains the default loader in release 0.2. Selecting `core` requires
`materials-structure-core>=0.0.2`; it validates the input through its
`StructureRecord` contract before conversion to pymatgen for symmetry analysis.
The conversion preserves lattice, species, site order, and fractional
coordinates. A record with a non-periodic axis is rejected rather than silently
promoted to a three-dimensionally periodic structure. Selective-dynamics flags
are validated by the core reader but do not affect symmetry classification.

This writes `symmetry_report.json`. A custom tolerance scan and output can be selected explicitly:

```bash
batch-symmetry-checker \
  --input ./structures \
  --output results.csv \
  --tolerances 1e-4 1e-3 1e-2 5e-2
```

The report records `configuration.input_root` as `"."` by default. Use `--include-absolute-root` only for a controlled internal report that needs the resolved local directory.

Excel remains available for interactive inspection:

```bash
batch-symmetry-checker --input ./structures --output results.xlsx
```

Exit codes are stable:

| Code | Meaning |
|---:|---|
| `0` | every requested analysis succeeded |
| `1` | a partial or failed scientific batch; valid records are retained |
| `2` | invalid configuration, missing input, or output failure |

Use `--help` for all options. `--angle-tolerance -1` delegates the angle choice to spglib; otherwise the value is in degrees. `symprec` is reported in ångström.

Existing output files are never replaced implicitly. Pass `--force` to overwrite a report; for CSV, the same check is applied to the `.errors.csv` sidecar before either file is written.

The former `python batch_symmetry_checker.py ...` source-checkout launcher remains in release 0.2 and preserves its historical XLSX default. It emits a warning and will be removed no earlier than release 1.0. This is a launcher migration aid, **not** full library-API compatibility: undocumented helper functions from the old single-file module were removed. The old misspelled point-group constant is retained as an alias; downstream Python callers should migrate to the documented API below.

## Python API

```python
from pathlib import Path
from batch_symmetry_checker import (
    AnalysisConfig,
    MaterialsStructureCoreLoader,
    analyze_directory,
)

report = analyze_directory(
    AnalysisConfig(
        input_dir=Path("structures"),
        tolerances=(1e-3, 1e-2),
        recursive=True,
    ),
    loader=MaterialsStructureCoreLoader(),
    producer_version="my-workflow",
)

for record in report.records:
    print(record.source_path, record.space_group_symbol, record.point_group_hm)

for error in report.errors:
    print(error.source_path, error.code, error.message)
```

The API returns immutable dataclasses. JSON-safe field definitions and format behavior are documented in the [report contract](https://github.com/Xin-Jiaqi/batch-symmetry-checker/blob/main/docs/REPORT_SCHEMA.md); architecture and extension boundaries are documented in the [technical design](https://github.com/Xin-Jiaqi/batch-symmetry-checker/blob/main/docs/TECHNICAL_DESIGN.md).

The roles of spglib, pymatgen, ASE, and atomate2, along with supported application scenarios, are summarized in the [upstream landscape](https://github.com/Xin-Jiaqi/batch-symmetry-checker/blob/main/docs/UPSTREAM_LANDSCAPE.md).

## Scientific interpretation

Changing `symprec` can change the detected space group. A high-symmetry assignment that appears only at a loose tolerance is evidence of tolerance sensitivity, not proof that the idealized structure is physically realized. The `metric_crystal_system` field is independently inferred from lattice lengths and angles and is therefore a diagnostic, not a replacement for the full atomic symmetry result.

The implementation uses pymatgen's `SpacegroupAnalyzer`, which is an interface to spglib. The backend returns standardized crystallographic symbols and settings; this repository does not invent a separate space-group convention.

## Development

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m build
python -m twine check dist/*
```

CI runs the tests on Python 3.10 and the latest stable Python 3.14, exercises the CLI, builds wheel and source distributions, and validates their metadata.

CI also consumes the versioned `batch-smoke-v1` split from
[`materials-structure-benchmark`](https://github.com/Xin-Jiaqi/materials-structure-benchmark).
It verifies 12 pinned, redistributable structures (six CC BY 4.0 monolayers and
six CC0 bulks) at four tolerances, producing 48 deterministic records whose source
hashes are bound to the benchmark manifest. This is a parsing, provenance, and
reporting contract; it does not establish stability, synthesizability,
ferroelectricity, layer-group ground truth, or any other material property.

For research use, cite the exact version using [`CITATION.cff`](CITATION.cff). A DOI or preferred paper citation will be added only when a corresponding release or publication exists.

## Scope and roadmap

Implemented: deterministic file discovery, one-time parsing, multi-tolerance symmetry analysis, 32 crystallographic point-group labels, structured JSON/CSV/Excel reports, source hashing, typed API, tests, packaging, and CI.

Not implemented: magnetic symmetry, layer-group classification, automatic structural repair, canonical structure identity, or a direct `group-theory-operations-toolkit` registry import. See [ROADMAP.md](ROADMAP.md).

## Author and license

Jiaqi Xin (辛嘉琪), Beijing Jiaotong University. Contact: jiaqixin2@bjtu.edu.cn.

Copyright is retained by the author; reuse and redistribution are permitted under the [BSD 3-Clause License](LICENSE).
