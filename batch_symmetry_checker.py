#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
作者：辛嘉琪
jiaqixin2@bjtu.edu.cn
仅作学习交流，有任何问题欢迎联系我，请勿用于商业用途。
转给他人时请保留此注释，并告知所属机构以便统计。

批量判定 CIF / POSCAR / CONTCAR / .vasp 的空间群、点群、晶系，并检查晶格参数关系

默认行为：
1. 输入文件夹 = ./
2. 读取其中所有 .cif / .vasp / POSCAR / CONTCAR 文件
3. 对每个结构扫描多个 symprec tolerance
4. 输出 Excel 到当前文件夹

依赖：
pymatgen spglib pandas openpyxl

============================================================
Excel 输出列说明
============================================================

file_name:
    输入结构文件名，例如 POSCAR、CONTCAR、xxx.vasp、xxx.cif。

formula:
    从结构文件读取并约分后的化学式，例如 SnP2S6、MoS2、BiTeI。

num_sites:
    输入结构中的原子 site 数，也就是结构文件中显式写出的原子位点数量。

symprec:
    spglib / pymatgen 做空间群识别时使用的原子位置容差。
    单位通常可按 Å 理解。
    不同 symprec 下，空间群和点群可能发生变化。

space_group_symbol:
    当前 symprec 下识别得到的空间群 Hermann-Mauguin 符号，例如 P3m1、P-3m1、C2/m。

space_group_number:
    当前 symprec 下识别得到的国际空间群编号，例如 156、164、12。

point_group_HM:
    当前 symprec 下识别得到的点群 Hermann-Mauguin 符号，例如 3m、-3m、mm2。

point_group_Schoenflies:
    当前 symprec 下识别得到的点群 Schönflies 符号，例如 C3v、D3d、C2v。

crystal_system:
    由空间群识别结果得到的晶系。
    这是 pymatgen / spglib 基于完整空间群判断得到的结果，
    例如 triclinic、monoclinic、orthorhombic、tetragonal、trigonal、hexagonal、cubic。

lattice_parameters:
    从输入结构文件直接读取的晶格参数数值，包括 a, b, c 和 α, β, γ。
    例如 a=3.800000 Å, b=3.800000 Å, c=6.200000 Å; α=90.0000°, β=90.0000°, γ=120.0000°。

lattice_relation:
    根据输入结构的晶格参数直接判断出的 a, b, c 和 α, β, γ 的关系。
    例如 a=b≠c, α=β=90°, γ=120°。

metric_crystal_system:
    仅根据晶格常数和角度关系判断得到的晶系。
    它不使用原子坐标对称性，只检查晶胞度量关系。
    例如 hexagonal、tetragonal、orthorhombic、rhombohedral、monoclinic、triclinic、ambiguous。

metric_vs_symmetry_check:
    比较 crystal_system 和 metric_crystal_system 是否一致或兼容。
    例如 consistent、inconsistent、ambiguous metric、
    compatible: trigonal symmetry with hexagonal/rhombohedral metric。

注意：
    对每个结构文件，会输出 n 行，对应 n 个 symprec。
    其中 file_name、formula、num_sites、crystal_system、lattice_parameters、
    lattice_relation、metric_crystal_system、metric_vs_symmetry_check
    这些结构固定信息只在该体系第一行填写。
    后续 n-1 行留空。
    symprec、space_group_symbol、space_group_number、point_group_HM、
    point_group_Schoenflies 会在每一行填写，因为它们可能随 tolerance 变化。
"""


from pathlib import Path
import argparse
import traceback

import pandas as pd
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


# ============================================================
# 用户自定义区
# ============================================================

# 输入 POSCAR / CIF / .vasp 所在文件夹
# 默认 "./" 表示当前运行该 python 脚本时所在的文件夹
INPUT_FOLDER = "./"

# 输出 Excel 文件名
OUTPUT_EXCEL_NAME = "symmetry_check_results.xlsx"

# 是否递归搜索子文件夹
# False：只读取 INPUT_FOLDER 当前文件夹
# True ：读取 INPUT_FOLDER 及其所有子文件夹
RECURSIVE_SEARCH = False

# tolerance 模式
#
# 可选：
# "fine"   : 精细判定，适合理想结构或高精度结构
# "normal" : 常规判定，适合大多数 DFT relaxed 结构，推荐默认使用
# "rough"  : 粗略判定，允许较大结构畸变
# "wide"   : 宽范围扫描，用于判断对称性是否对 tolerance 敏感
# "custom" : 使用下面的 CUSTOM_SYMPREC_LIST
#
TOLERANCE_MODE = "wide"

# 自定义 symprec 列表
# 仅当 TOLERANCE_MODE = "custom" 时生效
#
# symprec 可以粗略理解为原子位置匹配容差，单位通常按 Å 理解。
#
# 一般经验：
# 1e-4 ~ 1e-3：非常严格，适合理想结构
# 1e-2       ：常用，适合多数 DFT 弛豫后的结构
# 5e-2       ：较宽松，可识别轻微畸变后的近似对称性
# 1e-1       ：很宽松，适合粗略判断近似高对称性，但要谨慎使用
#
CUSTOM_SYMPREC_LIST = [
    1e-4,
    1e-3,
    1e-2,
    5e-2,
    1e-1,
]

# 角度 tolerance，单位为 degree
# 一般保持 5.0 即可。
# 高通量筛选时通常主要扫描 symprec，不需要把 angle_tolerance 也作为输出列。
ANGLE_TOLERANCE = 5.0

# ============================================================
# 晶格参数关系判断用 tolerance
# ============================================================

# 判断 a=b、b=c、a=c 时使用的相对容差
# 例如 1e-3 表示 0.1% 以内认为相等
LATTICE_LENGTH_REL_TOL = 1e-3

# 判断角度是否等于 90° 或 120° 时使用的绝对容差，单位 degree
# 如果结构是 DFT relaxed 后的轻微畸变结构，可以改成 0.5 或 1.0
LATTICE_ANGLE_ABS_TOL = 0.5


# ============================================================
# 预设 tolerance 梯度
# ============================================================

TOLERANCE_PRESETS = {
    "fine": [
        1e-5,
        1e-4,
        1e-3,
    ],

    "normal": [
        1e-3,
        1e-2,
        5e-2,
    ],

    "rough": [
        1e-2,
        5e-2,
        1e-1,
    ],

    "wide": [
        1e-4,
        1e-3,
        1e-2,
        5e-2,
        1e-1,
    ],

    "custom": CUSTOM_SYMPREC_LIST,
}


# ============================================================
# 32 crystallographic point groups:
# Hermann-Mauguin -> Schönflies
# ============================================================

POINT_GROUP_HM_TO_SCHONFLIES = {
    # Triclinic
    "1": "C1",
    "-1": "Ci",

    # Monoclinic
    "2": "C2",
    "m": "Cs",
    "2/m": "C2h",

    # Orthorhombic
    "222": "D2",
    "mm2": "C2v",
    "mmm": "D2h",

    # Tetragonal
    "4": "C4",
    "-4": "S4",
    "4/m": "C4h",
    "422": "D4",
    "4mm": "C4v",
    "-42m": "D2d",
    "4/mmm": "D4h",

    # Trigonal
    "3": "C3",
    "-3": "C3i",
    "32": "D3",
    "3m": "C3v",
    "-3m": "D3d",

    # Hexagonal
    "6": "C6",
    "-6": "C3h",
    "6/m": "C6h",
    "622": "D6",
    "6mm": "C6v",
    "-6m2": "D3h",
    "6/mmm": "D6h",

    # Cubic
    "23": "T",
    "m-3": "Th",
    "432": "O",
    "-43m": "Td",
    "m-3m": "Oh",
}


def get_symprec_list():
    """
    根据 TOLERANCE_MODE 返回 symprec 列表。
    """

    mode = TOLERANCE_MODE.lower().strip()

    if mode not in TOLERANCE_PRESETS:
        raise ValueError(
            f"Unknown TOLERANCE_MODE = {TOLERANCE_MODE}. "
            f"Allowed values: {list(TOLERANCE_PRESETS.keys())}"
        )

    return TOLERANCE_PRESETS[mode]


def find_structure_files(input_dir: Path, recursive: bool = False):
    """
    搜索输入文件夹中的 CIF / POSCAR / CONTCAR / .vasp 文件。
    """

    files = []

    if recursive:
        iterator = input_dir.rglob("*")
    else:
        iterator = input_dir.iterdir()

    for p in iterator:
        if not p.is_file():
            continue

        name_upper = p.name.upper()
        suffix_lower = p.suffix.lower()

        if suffix_lower == ".cif":
            files.append(p)
        elif suffix_lower == ".vasp":
            files.append(p)
        elif name_upper == "POSCAR":
            files.append(p)
        elif name_upper == "CONTCAR":
            files.append(p)
        elif name_upper.startswith("POSCAR_"):
            files.append(p)
        elif name_upper.startswith("CONTCAR_"):
            files.append(p)

    return sorted(files, key=lambda x: str(x))


def get_formula_from_structure(structure: Structure):
    """
    从结构中读取化学式。

    输出形式尽量接近常用化学式，例如：
    SnP2S6
    MoS2
    BiTeI
    """

    return structure.composition.reduced_formula


def nearly_equal_length(x, y, rel_tol=LATTICE_LENGTH_REL_TOL):
    """
    判断两个晶格长度是否近似相等。
    """

    scale = max(abs(x), abs(y), 1e-12)
    return abs(x - y) / scale <= rel_tol


def nearly_equal_angle(x, target, abs_tol=LATTICE_ANGLE_ABS_TOL):
    """
    判断角度是否接近目标角度。
    """

    return abs(x - target) <= abs_tol


def get_lattice_metric_info(structure: Structure):
    """
    直接从输入结构的晶格参数判断 a,b,c,α,β,γ 的关系。

    返回：
    1. lattice_parameters:
       带数值的晶格参数

    2. lattice_relation:
       例如：
       a=b≠c, α=β=90°, γ=120°

    3. metric_crystal_system:
       仅根据晶格参数判断出的晶系：
       cubic / tetragonal / orthorhombic / hexagonal /
       rhombohedral / monoclinic / triclinic / ambiguous
    """

    lattice = structure.lattice

    a = float(lattice.a)
    b = float(lattice.b)
    c = float(lattice.c)

    alpha = float(lattice.alpha)
    beta = float(lattice.beta)
    gamma = float(lattice.gamma)

    ab = nearly_equal_length(a, b)
    bc = nearly_equal_length(b, c)
    ac = nearly_equal_length(a, c)

    alpha_90 = nearly_equal_angle(alpha, 90.0)
    beta_90 = nearly_equal_angle(beta, 90.0)
    gamma_90 = nearly_equal_angle(gamma, 90.0)

    alpha_120 = nearly_equal_angle(alpha, 120.0)
    beta_120 = nearly_equal_angle(beta, 120.0)
    gamma_120 = nearly_equal_angle(gamma, 120.0)

    all_90 = alpha_90 and beta_90 and gamma_90
    all_lengths_equal = ab and bc and ac

    lattice_parameters = (
        f"a={a:.6f} Å, b={b:.6f} Å, c={c:.6f} Å; "
        f"α={alpha:.4f}°, β={beta:.4f}°, γ={gamma:.4f}°"
    )

    # cubic
    if all_lengths_equal and all_90:
        metric_crystal_system = "cubic"
        lattice_relation = "a=b=c, α=β=γ=90°"

    # tetragonal
    elif ab and (not ac) and (not bc) and all_90:
        metric_crystal_system = "tetragonal"
        lattice_relation = "a=b≠c, α=β=γ=90°"

    # orthorhombic
    elif (not ab) and (not bc) and (not ac) and all_90:
        metric_crystal_system = "orthorhombic"
        lattice_relation = "a≠b≠c, α=β=γ=90°"

    # hexagonal setting
    elif ab and (not ac) and (not bc) and alpha_90 and beta_90 and gamma_120:
        metric_crystal_system = "hexagonal"
        lattice_relation = "a=b≠c, α=β=90°, γ=120°"

    # rhombohedral metric
    elif all_lengths_equal and nearly_equal_angle(alpha, beta) and nearly_equal_angle(beta, gamma) and (not all_90):
        metric_crystal_system = "rhombohedral"
        lattice_relation = "a=b=c, α=β=γ≠90°"

    # monoclinic standard setting, usually unique axis b
    elif alpha_90 and gamma_90 and (not beta_90):
        metric_crystal_system = "monoclinic"
        lattice_relation = "a≠b≠c, α=γ=90°, β≠90°"

    # monoclinic non-standard settings
    elif beta_90 and gamma_90 and (not alpha_90):
        metric_crystal_system = "monoclinic"
        lattice_relation = "a≠b≠c, β=γ=90°, α≠90°"

    elif alpha_90 and beta_90 and (not gamma_90):
        metric_crystal_system = "monoclinic"
        lattice_relation = "a≠b≠c, α=β=90°, γ≠90°"

    # 如果长度关系或角度关系存在部分匹配，但不符合标准晶系，标记为 ambiguous
    elif ab or bc or ac or alpha_90 or beta_90 or gamma_90 or alpha_120 or beta_120 or gamma_120:
        metric_crystal_system = "ambiguous"
        lattice_relation = (
            f"partial relation: "
            f"a{'=' if ab else '≠'}b, "
            f"b{'=' if bc else '≠'}c, "
            f"a{'=' if ac else '≠'}c; "
            f"α={alpha:.4f}°, β={beta:.4f}°, γ={gamma:.4f}°"
        )

    # triclinic general case
    else:
        metric_crystal_system = "triclinic"
        lattice_relation = "a≠b≠c, α≠β≠γ, none of α,β,γ constrained to 90° or 120°"

    return lattice_parameters, lattice_relation, metric_crystal_system


def compare_metric_and_symmetry_crystal_system(metric_crystal_system: str, symmetry_crystal_system: str):
    """
    比较仅由晶格参数判断的 metric_crystal_system
    和 spglib/pymatgen 由空间群判断出的 crystal_system 是否一致。

    注意：
    trigonal 结构可能使用 rhombohedral metric，也可能使用 hexagonal axes。
    因此这里对 trigonal 做宽容匹配。
    """

    metric = str(metric_crystal_system).lower().strip()
    symmetry = str(symmetry_crystal_system).lower().strip()

    if metric == "ambiguous":
        return "ambiguous metric"

    if metric == symmetry:
        return "consistent"

    # trigonal 的晶胞表示可能是 hexagonal setting 或 rhombohedral setting
    if symmetry == "trigonal" and metric in ["hexagonal", "rhombohedral"]:
        return "compatible: trigonal symmetry with hexagonal/rhombohedral metric"

    return "inconsistent"


def analyze_one_structure(file_path: Path, symprec: float, angle_tolerance: float):
    """
    对单个结构、单个 symprec 做对称性分析。
    """

    structure = Structure.from_file(str(file_path))

    formula = get_formula_from_structure(structure)

    lattice_parameters, lattice_relation, metric_crystal_system = get_lattice_metric_info(
        structure
    )

    sga = SpacegroupAnalyzer(
        structure,
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    )

    space_group_symbol = sga.get_space_group_symbol()
    space_group_number = sga.get_space_group_number()
    point_group_hm = sga.get_point_group_symbol()
    crystal_system = sga.get_crystal_system()

    point_group_schoenflies = POINT_GROUP_HM_TO_SCHONFLIES.get(
        point_group_hm,
        "Unknown"
    )

    metric_vs_symmetry_check = compare_metric_and_symmetry_crystal_system(
        metric_crystal_system=metric_crystal_system,
        symmetry_crystal_system=crystal_system,
    )

    return {
        "file_name": file_path.name,
        "formula": formula,
        "num_sites": len(structure),

        "symprec": symprec,

        "space_group_symbol": space_group_symbol,
        "space_group_number": space_group_number,

        "point_group_HM": point_group_hm,
        "point_group_Schoenflies": point_group_schoenflies,

        "crystal_system": crystal_system,
        "lattice_parameters": lattice_parameters,
        "lattice_relation": lattice_relation,
        "metric_crystal_system": metric_crystal_system,
        "metric_vs_symmetry_check": metric_vs_symmetry_check,
    }


def blank_repeated_static_fields(rows_for_one_file):
    """
    对同一个结构文件的多行结果进行处理。

    保留第一行的结构固定信息。
    后续 tolerance 行中，将这些固定信息置空。

    这样 Excel 中每个体系的 n 行更清晰：
    第一行写材料信息和晶格关系，
    后续行只写不同 tolerance 下可能变化的空间群/点群。
    """

    if len(rows_for_one_file) <= 1:
        return rows_for_one_file

    static_columns = [
        "file_name",
        "formula",
        "num_sites",
        "crystal_system",
        "lattice_parameters",
        "lattice_relation",
        "metric_crystal_system",
        "metric_vs_symmetry_check",
    ]

    processed_rows = []

    for i, row in enumerate(rows_for_one_file):
        row_copy = dict(row)

        if i > 0:
            for col in static_columns:
                row_copy[col] = ""

        processed_rows.append(row_copy)

    return processed_rows


def main():
    parser = argparse.ArgumentParser(
        description="Batch symmetry check for CIF/POSCAR/CONTCAR/.vasp using pymatgen + spglib."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=INPUT_FOLDER,
        help="Input folder. Default is defined by INPUT_FOLDER in the script.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=OUTPUT_EXCEL_NAME,
        help="Output Excel file path or name. Default is defined by OUTPUT_EXCEL_NAME in the script.",
    )

    parser.add_argument(
        "--tolerances",
        type=float,
        nargs="+",
        default=None,
        help="Override symprec tolerance list, e.g. --tolerances 1e-4 1e-3 1e-2 5e-2 1e-1",
    )

    parser.add_argument(
        "--angle_tolerance",
        type=float,
        default=ANGLE_TOLERANCE,
        help="Angle tolerance in degrees. Default is defined by ANGLE_TOLERANCE in the script.",
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search subfolders.",
    )

    args = parser.parse_args()

    input_dir = Path(args.input).resolve()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path = output_path.resolve()

    if args.tolerances is not None:
        symprec_list = args.tolerances
        tolerance_mode_used = "command-line custom"
    else:
        symprec_list = get_symprec_list()
        tolerance_mode_used = TOLERANCE_MODE

    angle_tolerance = args.angle_tolerance
    recursive_search = RECURSIVE_SEARCH or args.recursive

    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_dir}")

    structure_files = find_structure_files(
        input_dir=input_dir,
        recursive=recursive_search,
    )

    if len(structure_files) == 0:
        print(f"No CIF/POSCAR/CONTCAR/.vasp files found in: {input_dir}")
        return

    print("=" * 80)
    print("Batch symmetry check")
    print("=" * 80)
    print(f"Input folder      : {input_dir}")
    print(f"Output Excel      : {output_path}")
    print(f"Recursive search  : {recursive_search}")
    print(f"Number of files   : {len(structure_files)}")
    print(f"Tolerance mode    : {tolerance_mode_used}")
    print(f"symprec list      : {symprec_list}")
    print(f"angle_tolerance   : {angle_tolerance}")
    print(f"Length rel tol    : {LATTICE_LENGTH_REL_TOL}")
    print(f"Angle abs tol     : {LATTICE_ANGLE_ABS_TOL} degree")
    print("=" * 80)

    rows = []
    failed_files = []

    for file_path in structure_files:
        print(f"\nProcessing: {file_path.name}")

        rows_for_one_file = []

        for symprec in symprec_list:
            try:
                row = analyze_one_structure(
                    file_path=file_path,
                    symprec=symprec,
                    angle_tolerance=angle_tolerance,
                )

                print(
                    f"  symprec={symprec:<8g} "
                    f"formula={row['formula']:<12} "
                    f"SG={row['space_group_symbol']:<12} "
                    f"No.={row['space_group_number']:<4} "
                    f"PG={row['point_group_HM']:<8} "
                    f"{row['point_group_Schoenflies']:<6} "
                    f"crystal={row['crystal_system']:<12} "
                    f"metric={row['metric_crystal_system']:<12} "
                    f"{row['metric_vs_symmetry_check']}"
                )

                rows_for_one_file.append(row)

            except Exception as e:
                failed_files.append((file_path.name, symprec, str(e)))
                print(f"  symprec={symprec:<8g} FAILED: {e}")
                traceback.print_exc()

        rows.extend(blank_repeated_static_fields(rows_for_one_file))

    if len(rows) == 0:
        print("\nNo valid symmetry results were obtained.")
        return

    df = pd.DataFrame(rows)

    column_order = [
        "file_name",
        "formula",
        "num_sites",

        "symprec",

        "space_group_symbol",
        "space_group_number",

        "point_group_HM",
        "point_group_Schoenflies",

        "crystal_system",
        "lattice_parameters",
        "lattice_relation",
        "metric_crystal_system",
        "metric_vs_symmetry_check",
    ]

    df = df[column_order]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="symmetry_results")

        worksheet = writer.sheets["symmetry_results"]

        for col_idx, column_name in enumerate(df.columns, start=1):
            max_len = max(
                [len(str(column_name))]
                + [len(str(x)) for x in df[column_name].head(200)]
            )
            adjusted_width = min(max_len + 2, 100)
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=col_idx).column_letter
            ].width = adjusted_width

        worksheet.freeze_panes = "A2"

    print("\n" + "=" * 80)
    print("Done.")
    print(f"Saved to: {output_path}")

    if failed_files:
        print("\nSome files failed and were not written to Excel:")
        for fname, symprec, errmsg in failed_files:
            print(f"  {fname}, symprec={symprec}: {errmsg}")

    print("=" * 80)


if __name__ == "__main__":
    main()