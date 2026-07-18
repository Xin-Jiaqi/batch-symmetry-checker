# Batch Symmetry Checker

Batch Symmetry Checker creates versioned, machine-readable symmetry reports for periodic crystal structures. It reads CIF, POSCAR, CONTCAR, and `.vasp` files with pymatgen, evaluates each structure over one or more spglib tolerances, and records space group, point group, crystal system, lattice metric, source hash, and structured failures.

The project is an **alpha research tool**. It supports reproducible screening and quality control; it does not replace crystallographic validation for publication. In particular, a three-dimensional space-group result for a slab with vacuum must be interpreted in its physical context.

## Why this release matters

- Every source structure is parsed exactly once, regardless of tolerance count.
- JSON is the default output; CSV and Excel are also supported.
- Report schema `1.0.0` separates successful records from file- and tolerance-level errors.
- Source SHA-256, dependency versions, units, and run configuration are recorded.
- The Python API accepts loader and point-group resolver adapters without depending on unfinished sibling repositories.
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

No open-source license has yet been granted. See `LICENSE_STATUS.md` before reuse or redistribution.

## Command line

```bash
batch-symmetry-checker --input ./structures --recursive
```

This writes `symmetry_report.json`. A custom tolerance scan and output can be selected explicitly:

```bash
batch-symmetry-checker \
  --input ./structures \
  --output results.csv \
  --tolerances 1e-4 1e-3 1e-2 5e-2
```

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
from batch_symmetry_checker import AnalysisConfig, analyze_directory

report = analyze_directory(
    AnalysisConfig(
        input_dir=Path("structures"),
        tolerances=(1e-3, 1e-2),
        recursive=True,
    ),
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

CI runs the tests on Python 3.10 and 3.12, exercises the CLI, builds wheel and source distributions, and validates their metadata.

## Scope and roadmap

Implemented: deterministic file discovery, one-time parsing, multi-tolerance symmetry analysis, 32 crystallographic point-group labels, structured JSON/CSV/Excel reports, source hashing, typed API, tests, packaging, and CI.

Not implemented: magnetic symmetry, layer-group classification, automatic structural repair, canonical structure identity, or direct `materials-structure-core`/`group-theory-operations-toolkit` imports. Those integrations remain gated on stable contracts in the sibling projects. See [ROADMAP.md](ROADMAP.md).

## Author and use status

Jiaqi Xin (辛嘉琪), Beijing Jiaotong University. Contact: jiaqixin2@bjtu.edu.cn.

Copyright is retained by the author. Public visibility does not grant permission to copy, modify, redistribute, or use the code commercially; see [LICENSE_STATUS.md](LICENSE_STATUS.md).
