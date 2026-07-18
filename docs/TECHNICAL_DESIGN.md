# Technical design

## Processing boundary

The batch engine has four stages:

1. Discover supported files in deterministic relative-path order.
2. Snapshot each source once; hash and parse that same byte sequence with the default loader.
3. Run pymatgen `SpacegroupAnalyzer` for each requested tolerance on the in-memory structure.
4. Serialize immutable report records and structured errors.

This separation eliminates repeated parsing and makes incomplete batches observable in automated workflows.

## Scientific backend

`SpacegroupAnalyzer` is pymatgen's interface to spglib. The analysis preserves the original input cell when reporting lattice metrics. It does not standardize, refine, or repair coordinates. Hall symbols are included so settings are not represented only by a potentially ambiguous short international symbol.

The metric-only classifier checks lengths and angles independently. Trigonal symmetry with a hexagonal or rhombohedral metric is treated as compatible. Other disagreements remain visible rather than being silently reconciled.

## Extension boundaries

`StructureLoader` is a protocol whose `load(Path)` method returns a pymatgen `Structure`. The default implementation calls `Structure.from_file`. A future `materials-structure-core` adapter can implement this protocol after that project has stable POSCAR/CIF conversion and provenance contracts. The core package is deliberately not imported today.

The point-group resolver is an injected callable from Hermann–Mauguin to Schönflies notation. The bundled 32-group map is the default. A future `group-theory-operations-toolkit` registry can be injected after its point-group schema is stable; this package does not guess that unpublished interface.

## Error and exit semantics

Library methods return a `SymmetryReport` and reserve exceptions for invalid configuration or an unusable input root. File-level and tolerance-level scientific failures are stored in `report.errors`.

The CLI exits `0` for a complete batch, `1` for a partial/failed scientific batch, and `2` for configuration, input, or output errors. This prevents a high-throughput pipeline from treating partial results as complete while preserving valid rows for inspection.

Output paths are protected against accidental replacement. The CLI requires `--force` before replacing any report; a CSV report and its fixed-schema error sidecar are checked together before writing begins. Single-file formats use an atomic same-directory replacement. CSV prepares both files, publishes the sidecar first and the main CSV last as a commit marker; handled replacement failures restore the old sidecar.

## Security and reproducibility

Inputs are read as crystal structure data through pymatgen. The project does not execute input content. Reports include the exact source-byte SHA-256 and backend versions. The hash is a provenance reference, not a canonical structure identity: whitespace changes alter it, while physically equivalent structures may have different hashes.

## Upstream references

- [pymatgen symmetry API](https://pymatgen.org/pymatgen.symmetry.html)
- [spglib dataset and conventions](https://spglib.readthedocs.io/en/stable/dataset.html)
- [ASE file I/O](https://wiki.fysik.dtu.dk/ase/ase/io/io.html), evaluated as a possible future alternative loader rather than added as a dependency
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
