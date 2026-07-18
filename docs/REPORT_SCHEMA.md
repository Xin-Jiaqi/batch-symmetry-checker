# Symmetry report contract

Schema version: `1.0.0`.

JSON is the canonical serialization. The top-level object contains `schema_version`, producer and backend versions, UTC generation time, status, run configuration, summary counts, successful `records`, and structured `errors`.

## Record fields

Each record represents one source structure at one `symprec`. Field names include units where ambiguity matters.

| Field | Type | Meaning |
|---|---|---|
| `source_path` | string | POSIX path relative to the selected input root |
| `source_sha256` | string | SHA-256 of the exact input bytes |
| `formula` | string | pymatgen reduced formula |
| `num_sites` | integer | sites explicitly present in the parsed structure |
| `symprec_angstrom` | number | spglib position tolerance in Å |
| `angle_tolerance_degree` | number | spglib angle tolerance in degrees; `-1` delegates to spglib |
| `space_group_symbol` | string | short international Hermann–Mauguin symbol |
| `space_group_number` | integer | International Tables number, 1–230 |
| `hall_symbol` | string | Hall symbol returned by the backend |
| `point_group_hm` | string | crystallographic point-group Hermann–Mauguin symbol |
| `point_group_schoenflies` | string | mapped Schönflies label for one of the 32 crystallographic point groups |
| `crystal_system` | string | full symmetry classification from pymatgen/spglib |
| `lattice_*` | number | input-cell lengths in Å and angles in degrees |
| `lattice_relation` | string | human-readable metric summary |
| `metric_crystal_system` | string | independent metric-only diagnostic |
| `metric_vs_symmetry_check` | string | `consistent`, `inconsistent`, a trigonal compatibility note, or `ambiguous metric` |

No field is intentionally blank in a successful record. Every tolerance row is independently readable.

## Errors

Errors are data, not console tracebacks:

- `structure_parse_error` is emitted once per unreadable source, because parsing occurs before the tolerance loop.
- `symmetry_analysis_error` is emitted for one source/tolerance combination.

The message is intended for diagnosis but is not a stable identifier. Consumers must branch on `code`.

## CSV and Excel projections

CSV writes successful records to the requested path and always creates `<stem>.errors.csv` with a fixed schema, even when there are no errors. The main CSV is published last and acts as the pair's commit marker. A handled publication failure rolls the sidecar back; a reader must not consume a changed sidecar until the corresponding main CSV is visible. CSV does not carry the full run metadata, so JSON should be archived for provenance-sensitive workflows.

Excel writes `symmetry_records`, `errors`, and `metadata` sheets. It is an optional presentation format, not the canonical data contract.

## Compatibility policy

Within schema major version 1, existing fields retain their type and meaning. New optional fields may be added in a minor schema version. Removing or redefining fields requires schema 2.0.0. Package and schema versions are independent.
