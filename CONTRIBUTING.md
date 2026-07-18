# Contributing

The repository is in an alpha validation stage and is not currently accepting unsolicited feature contributions. Reproducible bug reports and scientific validation cases are welcome through GitHub Issues.

A useful report includes the package version, Python version, pymatgen and spglib versions, the exact command, expected and observed crystallographic result, and a minimal structure file that you have permission to share.

Changes must preserve the report schema contract, add tests for scientific invariants and failure semantics, and pass `python -m pytest`, `python -m build`, and `python -m twine check dist/*`. Do not add third-party structure fixtures without a recorded source and redistribution permission.
