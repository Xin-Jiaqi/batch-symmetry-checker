# Roadmap

## Release 0.2 alpha — implemented in this branch

- Parse each source once and scan many tolerances in memory.
- Publish a typed Python API and stable CLI exit semantics.
- Add versioned JSON, CSV/error-sidecar, and Excel reports.
- Record source hashes, units, Hall symbols, and backend versions.
- Add scientific invariants, failure-path tests, packaging, and pinned CI actions.

## Release 0.3 candidate

- Add golden CIF/POSCAR fixtures whose redistribution rights are documented.
- Validate output equivalence across supported pymatgen/spglib version windows.
- Add a tolerance-stability summary derived from, but separate from, raw records.
- Add performance fixtures for thousands of small structures.
- [x] Publish repository-authored code and documentation under BSD-3-Clause.

## Release 1.0 gate

- Stable schema and deprecation policy demonstrated over at least one minor release.
- Independent crystallographic validation on representative 3D materials.
- Documented limitations and fixtures for slab/vacuum structures.
- Reproducible wheel installation and clean-environment examples.
- Security, documentation, and scientific review complete.

## Gated ecosystem integrations

- `materials-structure-core`: wait for its stable I/O and provenance release, then implement a loader adapter and equivalence tests.
- `group-theory-operations-toolkit`: wait for its 32-point-group registry contract, then replace the bundled label map through the existing resolver boundary.
- Application-layer stacking tools: consume JSON reports only after the schema is accepted; do not couple to internal modules.

Magnetic symmetry, layer groups, automatic repair, and patent-oriented workflows are outside this repository's current claims.
