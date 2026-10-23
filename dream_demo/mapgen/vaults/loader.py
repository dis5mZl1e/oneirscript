"""vault 模板的 JSON 读取与校验。

四个数据文件按两条分类轴的组合分文件：

============  ================  ================
              **固定** fixed    **不定** variable
**前置** pre   ``pre_fixed.json``   ``pre_variable.json``
**后置** post  ``post_fixed.json``  ``post_variable.json``
============  ================  ================

每个文件是一个对象：``{"phase": ..., "material": ..., "vaults": [ ... ]}``。
**每条模板自己也带 phase 与 material**（「任何 vault 都有这两种属性」），
读取时会校验它和所在文件一致——手改 JSON 时把模板挪错文件、或只改了一半，
启动即报错，而不是悄悄按文件推断。

单条模板的字段（除 id/name/pattern/phase/material 外都可省略）：

``min_open`` / ``min_solid``
    后置模板的地形门槛（0.0 = 不校验；两条都设时要求同时满足）。
``base_kind``
    整栋 ``#`` 统一墙种；**仅固定模板可用**（不定模板的材料来自常见池）。
``liquid``
    ``~`` 液体位灌入的液态记忆；**仅固定模板可用**（不定模板从常见池抽）。
``loot``
    中央格是石台、盛放稀有物品（见 VaultPlacement.loot_cell）。
``decor``
    附加属性：进房间装饰池（只在房间类层型从房间矩形内部盖章）。
``forms``
    附加属性：层型专属池（只在列出的层型出现；空 = 公用池）。
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import (
    ALL_PATTERN_CHARS,
    FIXED,
    LIQUID_CHAR,
    MATERIAL_MODES,
    PHASES,
    POST,
    PRE,
    RARITIES,
    VARIABLE,
    VAULT_CHAR_KINDS,
    Vault,
)

DATA_DIR = Path(__file__).resolve().parent

# (phase, material) → 数据文件名。四个组合对应四个文件。
DATASET_FILES: dict[tuple[str, str], str] = {
    (PRE, FIXED): "pre_fixed.json",
    (PRE, VARIABLE): "pre_variable.json",
    (POST, FIXED): "post_fixed.json",
    (POST, VARIABLE): "post_variable.json",
}

_REQUIRED_FIELDS = ("id", "name", "phase", "material", "pattern")


class VaultDataError(ValueError):
    """模板数据不合法（文件缺失、字段越界、分类归属对不上……）。"""


def _load_file(path: Path, phase: str, material: str) -> list[Vault]:
    if not path.exists():
        raise VaultDataError(f"缺少 vault 数据文件：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VaultDataError(f"{path.name} 不是合法 JSON：{error}") from error
    if not isinstance(payload, dict):
        raise VaultDataError(f"{path.name} 顶层应是对象（含 phase/material/vaults）")
    declared = (payload.get("phase"), payload.get("material"))
    if declared != (phase, material):
        raise VaultDataError(
            f"{path.name} 的分组声明是 {declared}，应为 {(phase, material)}"
        )
    entries = payload.get("vaults")
    if not isinstance(entries, list):
        raise VaultDataError(f"{path.name} 的 vaults 应是数组")
    return [_build_vault(entry, phase, material, path.name) for entry in entries]


def _build_vault(entry: object, phase: str, material: str, filename: str) -> Vault:
    if not isinstance(entry, dict):
        raise VaultDataError(f"{filename}：模板条目应是对象，收到 {type(entry).__name__}")
    missing = [field for field in _REQUIRED_FIELDS if field not in entry]
    if missing:
        raise VaultDataError(f"{filename}：模板缺少字段 {missing}")
    vid = str(entry["id"])
    where = f"{filename}:{vid}"
    if entry["phase"] != phase or entry["material"] != material:
        raise VaultDataError(
            f"{where} 自带分类 {(entry['phase'], entry['material'])} "
            f"与所在文件 {(phase, material)} 不一致"
        )
    pattern = [str(row) for row in entry["pattern"]]
    circuit = None
    if entry.get("circuit_template"):
        from ...data.circuit_templates import vault_board
        from ...circuit_schema import validate_board
        expected_pattern, circuit = vault_board(str(entry["circuit_template"]))
        if pattern != expected_pattern:
            raise VaultDataError(f"{where}: pattern differs from circuit port layout")
        validate_board(circuit, len(pattern[0]), len(pattern))
    if not pattern:
        raise VaultDataError(f"{where} 的 pattern 为空")
    widths = {len(row) for row in pattern}
    if len(widths) != 1:
        raise VaultDataError(f"{where} 的 pattern 各行宽度不一致：{sorted(widths)}")
    unknown = set("".join(pattern)) - ALL_PATTERN_CHARS
    if unknown:
        raise VaultDataError(
            f"{where} 含未知图案字符 {sorted(unknown)}；"
            f"可用字符：{sorted(ALL_PATTERN_CHARS)}"
        )
    base_kind = str(entry.get("base_kind", "") or "")
    liquid = str(entry.get("liquid", "") or "")
    if material == VARIABLE:
        # 不定模板的材料一律来自常见池；写死材料请改用固定模板，或直接在图案里
        # 用写死字符（S/T/G/A/C/F）。
        if base_kind:
            raise VaultDataError(f"{where} 是不定模板，不能写 base_kind（材料须从常见池抽）")
        if liquid:
            raise VaultDataError(f"{where} 是不定模板，不能写 liquid（液体须从常见池抽）")
    else:
        if base_kind and base_kind not in VAULT_CHAR_KINDS.values():
            raise VaultDataError(f"{where} 的 base_kind「{base_kind}」不是已知墙种")
        if liquid and LIQUID_CHAR not in "".join(pattern):
            raise VaultDataError(f"{where} 写了 liquid 却没有液体位（{LIQUID_CHAR}）")
    if liquid and base_kind == liquid:
        raise VaultDataError(f"{where} 的墙种与液体同名（{liquid}）")
    rarity = str(entry.get("rarity", "常见"))
    if rarity not in RARITIES:
        raise VaultDataError(f"{where} 的稀有度「{rarity}」不在 {list(RARITIES)} 之内")
    decor = bool(entry.get("decor", False))
    forms = tuple(str(form) for form in entry.get("forms", ()) or ())
    if phase == PRE and (decor or forms):
        raise VaultDataError(f"{where} 是前置模板，decor/forms 只对后置模板有意义")
    min_open = float(entry.get("min_open", 0.0) or 0.0)
    min_solid = float(entry.get("min_solid", 0.0) or 0.0)
    loot_anchor = entry.get("loot_anchor")
    if loot_anchor:
        if (not isinstance(loot_anchor, list) or len(loot_anchor) != 2
                or not all(isinstance(v, int) for v in loot_anchor)
                or not (0 <= loot_anchor[0] < len(pattern) and 0 <= loot_anchor[1] < len(pattern[0]))
                or pattern[loot_anchor[0]][loot_anchor[1]] != "S"):
            raise VaultDataError(f"{where}: loot anchor must point to a stone platform")
    for label, value in (("min_open", min_open), ("min_solid", min_solid)):
        if not 0.0 <= value <= 1.0:
            raise VaultDataError(f"{where} 的 {label}={value} 越界（应在 0~1）")
    depths = entry.get("allowed_depths", [])
    realms = entry.get("allowed_realms", {})
    if (not isinstance(depths, list) or any(type(d) is not int or not 1 <= d <= 30 for d in depths)
            or len(set(depths)) != len(depths) or not isinstance(realms, dict)
            or any(not isinstance(ds, list) or not ds or any(type(d) is not int or d < 1 for d in ds)
                   for ds in realms.values())):
        raise VaultDataError(f"{where}: invalid layer scope")
    from ...materials.logic import TEMPLATE_ONLY_CIRCUIT_WALLS
    scoped_chars = {ch for ch, kind in VAULT_CHAR_KINDS.items() if kind in TEMPLATE_ONLY_CIRCUIT_WALLS} | {"w", "p"}
    if (set("".join(pattern)) & scoped_chars or base_kind in TEMPLATE_ONLY_CIRCUIT_WALLS) and not (depths or realms or entry.get("exclusive_layer")):
        raise VaultDataError(f"{where}: circuit infrastructure requires explicit layer scope")
    anchors = {}
    for field in ("event_anchor", "npc_anchor"):
        value = entry.get(field)
        if value is not None:
            if (not isinstance(value, list) or len(value) != 2 or any(type(v) is not int for v in value)
                    or not (0 <= value[0] < len(pattern) and 0 <= value[1] < len(pattern[0]))
                    or (field == "npc_anchor" and pattern[value[0]][value[1]] not in ".@")
                    or (field == "event_anchor" and pattern[value[0]][value[1]] not in ".@S")):
                raise VaultDataError(f"{where}: invalid {field}")
            anchors[field] = tuple(value)
    if entry.get("npc_id"):
        from ...data.npcs import NPC_DEFINITIONS
        if entry["npc_id"] not in NPC_DEFINITIONS or "npc_anchor" not in anchors:
            raise VaultDataError(f"{where}: NPC requires a known ID and open anchor")
    return Vault(
        vid,
        str(entry["name"]),
        phase,
        pattern,
        material=material,
        min_open=min_open,
        min_solid=min_solid,
        base_kind=base_kind,
        liquid=liquid,
        loot=bool(entry.get("loot", False)),
        decor=decor,
        forms=forms,
        rarity=rarity,
        event=str(entry.get("event", "")),
        trap_pool=tuple(str(name) for name in entry.get("trap_pool", ())),
        exclusive_layer=int(entry.get("exclusive_layer", 0) or 0),
        valve_material=str(entry.get("valve_material", "") or ""),
        circuit=circuit,
        loot_anchor=tuple(entry["loot_anchor"]) if entry.get("loot_anchor") else None,
        allowed_depths=tuple(depths),
        allowed_realms={k: tuple(v) for k,v in realms.items()},
        event_anchor=anchors.get("event_anchor"),
        npc_id=str(entry.get("npc_id", "")),
        npc_anchor=anchors.get("npc_anchor"),
    )


def load_vaults() -> dict[str, Vault]:
    """读取四个数据文件，按文件顺序返回 ``{vid: Vault}``。"""
    vaults: dict[str, Vault] = {}
    for (phase, material), filename in DATASET_FILES.items():
        for vault in _load_file(DATA_DIR / filename, phase, material):
            if vault.vid in vaults:
                raise VaultDataError(f"模板 id 重复：{vault.vid}")
            vaults[vault.vid] = vault
    return vaults


_ALL = load_vaults()

# ---- 由 JSON 推导的池子（生成器只认这些名字，规则与数据分离）----
ALL_VAULTS: tuple[Vault, ...] = tuple(_ALL.values())

FIXED_VAULTS: tuple[Vault, ...] = tuple(v for v in ALL_VAULTS if v.material == FIXED)
VARIABLE_VAULTS: tuple[Vault, ...] = tuple(v for v in ALL_VAULTS if v.material == VARIABLE)

#: 前置：所有 phase=pre 的模板（层型掩码生成后立即盖章）。
PRE_VAULTS: tuple[Vault, ...] = tuple(v for v in ALL_VAULTS if v.phase == PRE)
#: 后置公用池：phase=post、且不挂 decor/forms 修饰的那些。
# 专属层 vault（exclusive_layer）不进随机池：只在对应层保底盖章。
EXCLUSIVE_VAULTS: tuple[Vault, ...] = tuple(
    v for v in ALL_VAULTS if v.phase == POST and v.exclusive_layer
)
POST_VAULTS: tuple[Vault, ...] = tuple(
    v for v in ALL_VAULTS
    if v.phase == POST and not v.decor and not v.forms and not v.exclusive_layer
)
#: 房间装饰池：附加属性 decor。
ROOM_DECOR_VAULTS: tuple[Vault, ...] = tuple(v for v in ALL_VAULTS if v.decor)
#: 层型专属池：附加属性 forms。
FORM_VAULT_POOLS: dict[str, tuple[Vault, ...]] = {}
for _vault in ALL_VAULTS:
    for _form in _vault.forms:
        FORM_VAULT_POOLS.setdefault(_form, ())
        FORM_VAULT_POOLS[_form] += (_vault,)

#: 大型前置模板：单纯按尺寸分组（生成器与测试的便利视图，不是独立属性）。
LARGE_PRE_VAULTS: tuple[Vault, ...] = tuple(
    v for v in PRE_VAULTS if v.width >= 10 and v.height >= 10
)

#: 四种组合的视图：(phase, material) → 模板元组。
VAULTS_BY_COMBINATION: dict[tuple[str, str], tuple[Vault, ...]] = {
    (phase, material): tuple(
        v for v in ALL_VAULTS if v.phase == phase and v.material == material
    )
    for phase in PHASES
    for material in MATERIAL_MODES
}

__all__ = [
    "DATA_DIR",
    "DATASET_FILES",
    "VaultDataError",
    "load_vaults",
    "ALL_VAULTS",
    "FIXED_VAULTS",
    "VARIABLE_VAULTS",
    "PRE_VAULTS",
    "POST_VAULTS",
    "ROOM_DECOR_VAULTS",
    "FORM_VAULT_POOLS",
    "LARGE_PRE_VAULTS",
    "VAULTS_BY_COMBINATION",
]
