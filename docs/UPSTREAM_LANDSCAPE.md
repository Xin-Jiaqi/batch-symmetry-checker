# Upstream landscape and application boundary

This repository is an orchestration and reporting layer. It does not compete with or reimplement the crystallographic engines below.

## Upstream tools

### spglib

spglib is the numerical symmetry backend. Its dataset defines international and Hall symbols, rotations/translations, Wyckoff positions, equivalent atoms, standardized cells, and the crystallographic point group. Batch Symmetry Checker currently exposes the group identifiers needed for screening but deliberately does not claim Wyckoff, standardization, or repair features that are not yet implemented.

Primary source: [spglib dataset documentation](https://spglib.readthedocs.io/en/stable/dataset.html).

### pymatgen

pymatgen supplies crystal file parsing and `SpacegroupAnalyzer`, which is explicitly documented as an interface to spglib for pymatgen `Structure` objects. Its CLI can inspect structure symmetry, while this project adds deterministic directory discovery, multi-tolerance scanning, source hashing, versioned batch reports, and partial-failure semantics.

Primary sources: [pymatgen symmetry API](https://pymatgen.org/pymatgen.symmetry.html) and [pymatgen CLI examples](https://pymatgen.org/).

### ASE

ASE offers `read`, `iread`, and `write` over a broad format registry. Adding ASE as a second parser today would increase ambiguity about frame selection and format-specific behavior. It is therefore an evaluated future adapter, not a current dependency. A future adapter must state the selected frame and prove equivalence on shared CIF/POSCAR fixtures.

Primary source: [ASE file I/O documentation](https://wiki.fysik.dtu.dk/ase/ase/io/io.html).

### atomate2 and emmet

atomate2 demonstrates the ecosystem-level pattern this project should interoperate with rather than replace: workflows scale from one material to large collections, and structured Task Documents make outputs queryable and transferable. Batch Symmetry Checker's JSON schema is intentionally small and local; a future atomate2 job should wrap the public API and translate the report into an appropriate document model instead of coupling to internal modules.

Primary sources: [atomate2 introduction](https://materialsproject.github.io/atomate2/user/index.html) and [schema/document model guide](https://materialsproject.github.io/atomate2/user/docs_schemas_emmet.html).

## Validated application scenarios

- Gate a directory of relaxed structures before expensive electronic, phonon, or stacking calculations.
- Detect tolerance-sensitive symmetry assignments without discarding the raw result at each tolerance.
- Audit polar or non-centrosymmetric candidates by a downstream rule operating on point/space-group fields.
- Compare nominally equivalent structures from different simulation stages using source hashes and explicit backend versions.
- Produce JSON artifacts for CI, HPC, or database ingestion and Excel only for human inspection.

These are screening and audit scenarios. The tool does not establish ferroelectricity, physical stability, magnetic order, a layer group, or a publishable structural refinement.

## Highest-impact follow-ons

1. Curate redistribution-safe golden structures across all seven crystal systems and representative slab cells.
2. Add a derived tolerance-stability summary while preserving every raw record.
3. Wrap the API as an atomate2/jobflow job only after schema review.
4. Add the shared structure and point-group adapters after sibling contracts reach their stated release gates.
