"""直接写入资源的登记表（2026-10-18 docs/261018方案合集.md 第 10 节第三、五批）。

第三批迁移核心环境/剧情损耗与恢复/上限变化；第五批把战斗、道具、社交、异象
技能、篡改报价、构想与装备事件里剩余的直接写入全部迁到 core/settlement.py。
现在登记表应为空：任何文件出现新的 self.<resource> / state.<resource> 直接赋值
都会让审计测试失败，必须走 settlement 接口。
"""
from __future__ import annotations

RESOURCE_WRITE_BACKLOG: dict[str, dict[str, object]] = {}

# 已完成迁移的文件：不得再出现 self.<resource> / state.<resource> 直接赋值。
MIGRATED_FILES = (
    "dream_demo/core/state.py",
    "dream_demo/core/materials_sim.py",
    "dream_demo/core/portents.py",
    "dream_demo/core/run_options.py",
    "dream_demo/core/hospital_effects.py",
    "dream_demo/core/hospital_scenes.py",
    "dream_demo/core/dreams.py",
    "dream_demo/core/logic.py",
    "dream_demo/core/generation.py",
    "dream_demo/core/library_content.py",
    "dream_demo/core/tamper_pipeline.py",
    "dream_demo/core/tamper_risks.py",
    "dream_demo/core/weapons.py",
    "dream_demo/core/actions/combat.py",
    "dream_demo/core/actions/items.py",
    "dream_demo/core/actions/social.py",
    "dream_demo/core/enemies.py",
    "dream_demo/core/enemy_skills.py",
    "dream_demo/core/identity_traits.py",
    "dream_demo/equipment/events.py",
    "dream_demo/equipment/positional_events.py",
)
