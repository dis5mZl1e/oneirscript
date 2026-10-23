"""vault 世界生成模板包：数据（JSON）+ 基础设施（盖章/放置）。

模块划分：
- ``base``   —— Vault 数据类、图案字符表、盖章与放置尝试（含房间内盖章）
- ``loader`` —— 四个 JSON 数据文件的读取与校验，并推导出各投放池
- ``*.json`` —— 模板数据本体，按「前置/后置 × 固定/不定」四种组合分文件

每个模板都同时具备两条分类轴（``phase`` 前置/后置、``material`` 固定/不定），
各自二选一、无第三项；池子（公用后置 / 房间装饰 / 层型专属 / 大型前置）由
附加属性与尺寸推导，不再散落在各模块里。想改地图模板，改 JSON 即可。
"""

from .base import (
    ALL_PATTERN_CHARS,
    BLANK_CHAR,
    CONNECT_CHAR,
    COMMON_SOLID_CHAR,
    FIXED,
    LIQUID_CHAR,
    MATERIAL_MODES,
    OPEN_CHAR,
    PHASES,
    POST,
    PRE,
    RARITIES,
    RARITY_WEIGHTS,
    SOLID_CHAR,
    VARIABLE,
    VAULT_CHAR_KINDS,
    Vault,
    VaultPlacement,
    pick_by_rarity,
    regions_overlap,
    rotate_vault,
    stamp_vault,
    stamp_vault_in_room,
    stamp_vault_near_open,
    try_stamp_vault,
)
from .loader import (
    ALL_VAULTS,
    DATA_DIR,
    DATASET_FILES,
    FIXED_VAULTS,
    FORM_VAULT_POOLS,
    LARGE_PRE_VAULTS,
    POST_VAULTS,
    EXCLUSIVE_VAULTS,
    PRE_VAULTS,
    ROOM_DECOR_VAULTS,
    VARIABLE_VAULTS,
    VAULTS_BY_COMBINATION,
    VaultDataError,
    load_vaults,
)

__all__ = [
    "ALL_PATTERN_CHARS",
    "BLANK_CHAR",
    "COMMON_SOLID_CHAR",
    "CONNECT_CHAR",
    "FIXED",
    "LIQUID_CHAR",
    "MATERIAL_MODES",
    "OPEN_CHAR",
    "PHASES",
    "POST",
    "PRE",
    "RARITIES",
    "RARITY_WEIGHTS",
    "SOLID_CHAR",
    "VARIABLE",
    "VAULT_CHAR_KINDS",
    "Vault",
    "VaultPlacement",
    "pick_by_rarity",
    "regions_overlap",
    "rotate_vault",
    "stamp_vault",
    "stamp_vault_in_room",
    "stamp_vault_near_open",
    "try_stamp_vault",
    "ALL_VAULTS",
    "DATA_DIR",
    "DATASET_FILES",
    "FIXED_VAULTS",
    "FORM_VAULT_POOLS",
    "LARGE_PRE_VAULTS",
    "POST_VAULTS",
    "EXCLUSIVE_VAULTS",
    "PRE_VAULTS",
    "ROOM_DECOR_VAULTS",
    "VARIABLE_VAULTS",
    "VAULTS_BY_COMBINATION",
    "VaultDataError",
    "load_vaults",
]
