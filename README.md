# batch_symmetry_checker
A lightweight Python script for batch symmetry analysis of crystal structure files using `pymatgen` and `spglib`.

# Batch Symmetry Checker

A lightweight Python script for batch symmetry analysis of crystal structure files using `pymatgen` and `spglib`.

作者：辛嘉琪  
Email: jiaqixin2@bjtu.edu.cn  

仅作学习交流，有任何问题欢迎联系我，请勿用于商业用途。  
转给他人时请保留作者信息，并告知所属机构以便统计。

## 功能简介

本脚本用于批量读取晶体结构文件，并自动判断其空间群、点群、晶系以及晶格参数关系。适合用于材料高通量筛选中的初步对称性检查。

支持的输入文件包括：

- `.cif`
- `.vasp`
- `POSCAR`
- `CONTCAR`
- `POSCAR_xxx`
- `CONTCAR_xxx`

脚本会对每个结构文件扫描多个 `symprec` tolerance，并将结果输出为 Excel 表格。

## 安装依赖

推荐使用 `conda` 安装：

    conda install -c conda-forge pymatgen spglib pandas openpyxl

也可以使用 `pip` 安装：

    pip install pymatgen spglib pandas openpyxl

## 使用方法

将脚本 `batch_symmetry_check.py` 放在结构文件所在文件夹中，然后直接运行：

    python batch_symmetry_check.py

默认情况下，脚本会读取当前文件夹中的 `.cif`、`.vasp`、`POSCAR`、`CONTCAR` 文件，并输出：

    symmetry_check_results.xlsx

也可以手动指定输入文件夹：

    python batch_symmetry_check.py --input "./structures"

也可以自定义 tolerance：

    python batch_symmetry_check.py --tolerances 1e-4 1e-3 1e-2 5e-2 1e-1

递归搜索子文件夹：

    python batch_symmetry_check.py --recursive

## Excel 中包含以下列

| 列名 | 含义 |
|---|---|
| `file_name` | 输入结构文件名，例如 `POSCAR`、`CONTCAR`、`xxx.vasp`、`xxx.cif` |
| `formula` | 从结构文件读取并约分后的化学式，例如 `SnP2S6`、`MoS2`、`BiTeI` |
| `num_sites` | 输入结构中的原子 site 数，也就是结构文件中显式写出的原子位点数量 |
| `symprec` | spglib / pymatgen 做空间群识别时使用的原子位置容差，单位通常可按 Å 理解 |
| `space_group_symbol` | 当前 `symprec` 下识别得到的空间群 Hermann-Mauguin 符号，例如 `P3m1`、`P-3m1`、`C2/m` |
| `space_group_number` | 当前 `symprec` 下识别得到的国际空间群编号，例如 `156`、`164`、`12` |
| `point_group_HM` | 当前 `symprec` 下识别得到的点群 Hermann-Mauguin 符号，例如 `3m`、`-3m`、`mm2` |
| `point_group_Schoenflies` | 当前 `symprec` 下识别得到的点群 Schönflies 符号，例如 `C3v`、`D3d`、`C2v` |
| `crystal_system` | 由空间群识别结果得到的晶系，即 pymatgen / spglib 基于完整空间群判断得到的结果 |
| `lattice_parameters` | 从输入结构文件直接读取的晶格参数数值，包括 `a, b, c, α, β, γ` |
| `lattice_relation` | 根据输入结构的晶格参数直接判断出的 `a, b, c, α, β, γ` 关系，例如 `a=b≠c, α=β=90°, γ=120°` |
| `metric_crystal_system` | 仅根据晶格常数和角度关系判断得到的晶系，不使用原子坐标对称性 |
| `metric_vs_symmetry_check` | 比较 `crystal_system` 和 `metric_crystal_system` 是否一致或兼容 |

对于每个结构文件，脚本会输出多行，对应不同的 `symprec`。其中结构固定信息只在该体系第一行填写，后续 tolerance 行留空；随 tolerance 变化的空间群、点群信息每一行都会填写。

## Tolerance 说明

脚本默认使用：

    TOLERANCE_MODE = "wide"

对应：

    [1e-4, 1e-3, 1e-2, 5e-2, 1e-1]

一般经验如下：

| symprec | 说明 |
|---|---|
| `1e-4 ~ 1e-3` | 较严格，适合理想结构或高精度结构 |
| `1e-2` | 常用，适合多数 DFT relaxed 结构 |
| `5e-2` | 较宽松，可识别轻微畸变后的近似对称性 |
| `1e-1` | 很宽松，适合粗略判断近似高对称性，但需谨慎使用 |

如果一个结构只有在很大的 `symprec` 下才出现高对称性，通常说明该结构只是近似高对称，需要进一步人工检查。

## 点群符号

脚本同时输出两种点群记号：

- Hermann-Mauguin 符号，例如 `3m`
- Schönflies 符号，例如 `C3v`

脚本内部包含 32 个晶体学点群的 Hermann-Mauguin 到 Schönflies 映射表。

例如：

| Hermann-Mauguin | Schönflies |
|---|---|
| `1` | `C1` |
| `-1` | `Ci` |
| `m` | `Cs` |
| `2` | `C2` |
| `mm2` | `C2v` |
| `3m` | `C3v` |
| `4mm` | `C4v` |
| `6mm` | `C6v` |
| `-43m` | `Td` |
| `m-3m` | `Oh` |

## 晶格参数关系检查

除了 pymatgen / spglib 给出的 `crystal_system`，脚本还会直接从输入结构的晶格参数中判断晶格度量关系，例如：

    a=b≠c, α=β=90°, γ=120°

并给出仅由晶格参数判断的：

    metric_crystal_system

这样可以将空间群识别得到的晶系和晶格常数直接判断得到的晶系进行并行比较。

例如：

- `crystal_system = hexagonal`
- `metric_crystal_system = hexagonal`
- `metric_vs_symmetry_check = consistent`

对于三方结构，需要注意其可能使用 hexagonal setting 或 rhombohedral setting。因此脚本会将部分情况标记为兼容，而不是简单判断为错误：

    compatible: trigonal symmetry with hexagonal/rhombohedral metric

## 用户自定义参数

脚本开头有用户自定义区，常用参数如下：

    INPUT_FOLDER = "./"
    OUTPUT_EXCEL_NAME = "symmetry_check_results.xlsx"
    RECURSIVE_SEARCH = False
    TOLERANCE_MODE = "wide"
    CUSTOM_SYMPREC_LIST = [1e-4, 1e-3, 1e-2, 5e-2, 1e-1]
    ANGLE_TOLERANCE = 5.0
    LATTICE_LENGTH_REL_TOL = 1e-3
    LATTICE_ANGLE_ABS_TOL = 0.5

其中：

| 参数 | 含义 |
|---|---|
| `INPUT_FOLDER` | 输入结构文件所在文件夹，默认 `./` |
| `OUTPUT_EXCEL_NAME` | 输出 Excel 文件名 |
| `RECURSIVE_SEARCH` | 是否递归搜索子文件夹 |
| `TOLERANCE_MODE` | tolerance 预设模式 |
| `CUSTOM_SYMPREC_LIST` | 自定义 `symprec` 列表 |
| `ANGLE_TOLERANCE` | 空间群识别时使用的角度 tolerance，单位为 degree |
| `LATTICE_LENGTH_REL_TOL` | 判断 `a=b`、`b=c`、`a=c` 时使用的相对容差 |
| `LATTICE_ANGLE_ABS_TOL` | 判断角度是否等于 90° 或 120° 时使用的绝对容差，单位为 degree |

## Tolerance 模式

脚本提供以下预设模式：

    TOLERANCE_PRESETS = {
        "fine": [1e-5, 1e-4, 1e-3],
        "normal": [1e-3, 1e-2, 5e-2],
        "rough": [1e-2, 5e-2, 1e-1],
        "wide": [1e-4, 1e-3, 1e-2, 5e-2, 1e-1],
        "custom": CUSTOM_SYMPREC_LIST,
    }

推荐高通量初筛时使用：

    TOLERANCE_MODE = "wide"

如果只想检查比较严格的对称性，可以使用：

    TOLERANCE_MODE = "fine"

如果只关心常规 DFT relaxed 结构，可以使用：

    TOLERANCE_MODE = "normal"

## 注意事项

1. 本脚本适合用于批量初筛，不建议完全替代人工判断。
2. 对于轻微畸变结构，不同 `symprec` 下空间群和点群可能不同。
3. 对于二维材料、层状材料、真空层较大的结构，三维空间群判断结果需要结合物理背景理解。
4. CIF、POSCAR、vasp 文件中的结构是否标准化，会影响输出结果。
5. `metric_crystal_system` 只由晶格参数关系判断，不考虑原子坐标对称性，因此它和 `crystal_system` 不一定完全一致。
6. 若需要严格发表级别的空间群确认，建议结合 Materials Studio、VESTA、Bilbao Crystallographic Server 等工具进一步验证。

## 适用场景

本脚本适合用于：

- 批量检查 CIF / POSCAR / `.vasp` 文件的空间群和点群
- 高通量筛选 non-centrosymmetric / polar 材料前的初步对称性判断
- 比较不同 tolerance 下结构对称性是否稳定
- 检查 DFT relaxed 结构是否偏离理想高对称结构
- 快速替代 Materials Studio 中逐个手动 `Find Symmetry` 的流程

## License

For academic and educational use only.

Please keep the author information when redistributing this script.
