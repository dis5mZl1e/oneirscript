"""英文语言包 · 内容部分（原 i18n_content_en.py，按域拆分）。

对外仍导出原有 15 个符号——``dream_demo/i18n.py`` 的既有 import
（EN_CONTENT / EN_UNCONSCIOUS / … / JOURNAL_EN）零改动。
"""

from __future__ import annotations

from .content_tutorial import (  # noqa: F401
    EN_CONTENT,
)

from .content_realms import (  # noqa: F401
    EN_UNCONSCIOUS,
)

from .content_events import (  # noqa: F401
    EN_EVENTS_SEP18,
    EN_ITEMS_PACK_V1,
    EN_EVENTS_DIALOGUE_LABELS,
    EN_PORTENT_REBALANCE_LABELS,
    EN_BUILD_BRIDGE,
)

from .content_materials import (  # noqa: F401
    EN_MATERIALS_PACK_V1,
    EN_MATERIALS_SEP18,
)

from .content_extra import (  # noqa: F401
    EXTENSION_V2_EN,
    EXTENSION_V2_MESSAGES_EN,
    CATALOG_NPC_EN,
    FACTIONS_EN,
    TRAVEL_EN,
    JOURNAL_EN,
)
