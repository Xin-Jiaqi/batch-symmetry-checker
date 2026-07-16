import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd
from pymatgen.core import Lattice, Structure

import batch_symmetry_checker as checker


def structure_with_lattice(lattice: Lattice) -> Structure:
    return Structure(lattice, ["H"], [[0, 0, 0]])


class BatchSymmetryCheckerRegressionTests(unittest.TestCase):
    def test_hexagonal_metric_accepts_60_and_120_degree_bases(self) -> None:
        for gamma in (60.0, 120.0):
            with self.subTest(gamma=gamma):
                structure = structure_with_lattice(
                    Lattice.from_parameters(4.0, 4.0, 7.0, 90.0, 90.0, gamma)
                )

                _, relation, metric = checker.get_lattice_metric_info(structure)

                self.assertEqual(metric, "hexagonal")
                self.assertIn(f"γ={int(gamma)}°", relation)
                self.assertTrue(relation.startswith("a=b≠c"))

    def test_monoclinic_relation_does_not_invent_length_inequality(self) -> None:
        structure = structure_with_lattice(
            Lattice.from_parameters(4.0, 4.0, 7.0, 90.0, 100.0, 90.0)
        )

        _, relation, metric = checker.get_lattice_metric_info(structure)

        self.assertEqual(metric, "monoclinic")
        self.assertTrue(relation.startswith("a=b≠c"))
        self.assertNotIn("a≠b≠c", relation)

    def test_each_tolerance_row_is_complete_and_uses_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "structures"
            nested_dir = input_dir / "sample"
            nested_dir.mkdir(parents=True)
            structure = Structure(
                Lattice.cubic(4.0),
                ["Si", "Si"],
                [[0, 0, 0], [0.501, 0.5, 0.5]],
            )
            structure.to(filename=str(nested_dir / "POSCAR"), fmt="poscar")
            output_path = root / "results.xlsx"

            exit_code = checker.main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_path),
                    "--recursive",
                    "--tolerances",
                    "1e-4",
                    "1e-2",
                ]
            )

            self.assertEqual(exit_code, 0)
            results = pd.read_excel(output_path, keep_default_na=False)
            self.assertEqual(len(results), 2)
            self.assertEqual(set(results["file_name"]), {"sample/POSCAR"})
            for column in (
                "formula",
                "num_sites",
                "crystal_system",
                "lattice_parameters",
                "lattice_relation",
                "metric_crystal_system",
                "metric_vs_symmetry_check",
            ):
                self.assertTrue(all(str(value).strip() for value in results[column]))

    def test_invalid_tolerance_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertNotEqual(
                checker.main(["--input", temp_dir, "--tolerances", "0"]),
                0,
            )
            self.assertNotEqual(
                checker.main(["--input", temp_dir, "--tolerances", "nan"]),
                0,
            )

    def test_nonfinite_angle_tolerance_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertNotEqual(
                checker.main(
                    ["--input", temp_dir, "--angle_tolerance", "nan"]
                ),
                0,
            )

    def test_no_input_files_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertNotEqual(checker.main(["--input", temp_dir]), 0)

    def test_all_failed_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "structures"
            input_dir.mkdir()
            (input_dir / "POSCAR").write_text(
                "not a valid structure\n",
                encoding="utf-8",
            )
            output_path = root / "results.xlsx"

            exit_code = checker.main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_path),
                    "--tolerances",
                    "1e-3",
                ]
            )

            self.assertNotEqual(exit_code, 0)
            self.assertFalse(output_path.exists())

    def test_partial_failure_keeps_valid_rows_and_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "structures"
            input_dir.mkdir()
            valid_path = input_dir / "POSCAR_valid"
            Structure(
                Lattice.cubic(4.0),
                ["Si", "Si"],
                [[0, 0, 0], [0.5, 0.5, 0.5]],
            ).to(filename=str(valid_path), fmt="poscar")
            (input_dir / "POSCAR_broken").write_text(
                "not a valid structure\n",
                encoding="utf-8",
            )
            output_path = root / "results.xlsx"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = checker.main(
                    [
                        "--input",
                        str(input_dir),
                        "--output",
                        str(output_path),
                        "--tolerances",
                        "1e-3",
                    ]
                )

            self.assertNotEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            results = pd.read_excel(output_path, keep_default_na=False)
            self.assertEqual(len(results), 1)
            self.assertEqual(results.loc[0, "file_name"], "POSCAR_valid")
            combined_log = stdout.getvalue() + stderr.getvalue()
            self.assertIn("POSCAR_broken", combined_log)
            self.assertIn("FAILED", combined_log)


if __name__ == "__main__":
    unittest.main()
