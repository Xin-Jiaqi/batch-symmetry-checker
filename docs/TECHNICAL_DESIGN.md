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

`StructureLoader` is a protocol whose `load(Path)` method returns a pymatgen `Structure`. The default implementation calls `Structure.from_file` and preserves release-0.2 behavior.

`MaterialsStructureCoreLoader` is the maintained optional adapter for `materials-structure-core>=0.0.2`. The batch engine snapshots each source once; the adapter sends those exact bytes through the core POSCAR/CIF reader, verifies the returned source hash, then converts the validated `StructureRecord` to an unchanged pymatgen lattice/species/fractional-coordinate representation for `SpacegroupAnalyzer`. Temporary parser paths are removed from public errors and deleted after every load.

The conversion refuses a `StructureRecord` with a non-periodic axis because pymatgen `Structure` and the present spglib workflow are three-dimensionally periodic. Selective-dynamics flags are intentionally not copied to pymatgen site properties: the core reader has already validated them, and allowed ionic motion is not an input to crystallographic symmetry classification. The adapter is imported lazily, so users who keep the default pymatgen boundary do not acquire ASE or core-package dependencies.

The point-group resolver is an injected callable from Hermann–Mauguin to Schönflies notation. The bundled 32-group map is the default. A future `group-theory-operations-toolkit` registry can be injected after its point-group schema is stable; this package does not guess that unpublished interface.

## Error and exit semantics

Library methods return a `SymmetryReport` and reserve exceptions for invalid configuration or an unusable input root. File-level and tolerance-level scientific failures are stored in `report.errors`.

The CLI exits `0` for a complete batch, `1` for a partial/failed scientific batch, and `2` for configuration, input, or output errors. This prevents a high-throughput pipeline from treating partial results as complete while preserving valid rows for inspection.

Output paths are protected against accidental replacement. The CLI requires `--force` before replacing any report; a CSV report and its fixed-schema error sidecar are checked together before writing begins. Single-file formats use an atomic same-directory replacement. CSV prepares both files, publishes the sidecar first and the main CSV last as a commit marker; handled replacement failures restore the old sidecar.

## Security and reproducibility

Inputs are read as crystal structure data through the selected loader. The project does not execute input content. Reports include the exact source-byte SHA-256 and symmetry-backend versions. The hash is a provenance reference, not a canonical structure identity: whitespace changes alter it, while physically equivalent structures may have different hashes. When the optional core input boundary is used, workflows should also pin the core release as shown in the installation instructions; input-loader identity is selected by the invocation and is not yet a report-schema field.

## Upstream references

- [pymatgen symmetry API](https://pymatgen.org/pymatgen.symmetry.html)
- [spglib dataset and conventions](https://spglib.readthedocs.io/en/stable/dataset.html)
- [ASE file I/O](https://wiki.fysik.dtu.dk/ase/ase/io/io.html), evaluated as a possible future alternative loader rather than added as a dependency
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
