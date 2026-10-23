"""NPC 任务定义与结构-NPC 绑定。"""

from __future__ import annotations

from typing import Any

#: 目标模板（重构方案 §7.1 首版六类）。任务定义里的 ``template`` 只能是其中之一；
#: 具体哪几条已经有解法器由 :mod:`dream_demo.world.tasks` 自己声明。
TARGET_TEMPLATES = frozenset({
    "threat",             # 指定威胁：击败／驱离／封堵一个实际存在的目标
    "guard_place",        # 护守地点：保持设施可用并顶住一段短时威胁
    "recover_deliver",    # 回收／递送：选取真实物品或具名记录完成交付
    "fix_environment",    # 环境修复：指定区域达到可观察状态
    "investigate",        # 调查／辨认：发现具名线索后再做一次区分行动
    "negotiate",          # 交涉／关系：让两个明确的角色或岗位达成条件
})

QUEST_DEFINITIONS: dict[str, dict[str, Any]] = {
    "quest.press_ink": {
        "name": "头版的油墨", "giver": "npc.press_boy",
        # §7.2「头版显影」（来源改造：旧「头版的油墨」计数协议）：交付点就是
        # 报童本人（delivery: giver）。显影液是**液体**不是物品（旧定义曾把它
        # 写成 item id，任务永远无法达成）——交付＝把液体倒在委托人站的托盘格
        # 上，兑现时从同一格扣除，同一个事务。§7.2 的另一条解法（带回可显影
        # 现场记录）等 S12 画廊显影族落地再接；液体托盘这条先入实例协议。
        "template": "recover_deliver",
        "delivery": "giver",
        "requirement": {"type": "liquid", "liquid": "显影液", "count": 3},
        "requirement_text": "把 3 单位显影液倒进报童的印版托盘（他站着的那格）",
        "rewards": {
            "supply": {"label": "一张头版＋一份补给", "gain": {"item": "espresso_shot", "insight": "疾行拾荒"}},
            "service": {"label": "一次排版帮工", "gain": {"stat": ["max_imagination", 2]}},
        },
        "hint": "报童要印一份「醒着的报纸」：把 3 单位显影液倒进他站的托盘格，他要拿去调油墨。",
    },
    # 旧「拾荒的账目」（kill_any ×4）已按 §7.2 由「泵房的狩猎登记」接替：
    # 「先屠图再回登记员面前一口气补领」正是 §7.3 要堵的口径，定义随之删除。
    "quest.pump_hunt": {
        "name": "泵房的狩猎登记", "giver": "npc.scrap_registrar",
        # 目标实例任务（§7.1 模板 1「指定威胁」）：绑的是泵房里那一位的 actor_uid，
        # 不是本局击杀计数。两条解法都落在真实地图上，缺一都不结。
        "template": "threat",
        "site": "scene.pump_house",
        "zone": "yard",
        "requirement": {"type": "target_resolve", "count": 1},
        "target_text": "解决泵房里那一位：当场击败，或引出院子、放下侧门挡板，"
                       "让保护区连着 3 个世界回合没有失控意识踩进去",
        "rewards": {
            "supply": {"label": "泵房使用权＋一份物资", "gain": {"item": "mint_lozenge"}},
            "service": {"label": "一次协会回收服务", "gain": {"stat": ["max_mind", 2]}},
        },
        # 报酬里带地图效果的那一档：回到那一层的泵房，把玩家自己放下的挡板抬起来。
        "site_effects": {"supply": "side_door"},
        # 接活之前那位就没了（或干脆是异象互杀）：只认一次确认现场，给小额收益。
        "confirm_gain": {"item": "folded_projectile"},
        "hint": "泵房里窝了一位。要么当场解决它，要么让泵机空转一声把它引出院子、在门柱手柄边"
                "放下侧门挡板，连着三个世界回合别让失控意识踩进保护区——回来销账时说要哪一档报酬。",
    },
    "quest.lamp_refuge": {
        "name": "留灯的巡房", "giver": "npc.scrap_registrar",
        # 环境修复（§7.1 模板 4）：目标区域达到可观察状态——点亮留灯后，
        # 环线连着 3 个世界回合没有火、没有失控意识踩进去（复用 hold: 事实）。
        "template": "fix_environment",
        "site": "scene.lamp_refuge",
        "zone": "ring",
        "requirement": {"type": "target_resolve", "count": 1},
        "target_text": "把留灯的避难圈点起来，让环内连着 3 个世界回合没有火、没有失控意识踩进去",
        "rewards": {
            "supply": {"label": "一份补给＋避难圈使用权", "gain": {"item": "mint_lozenge"}},
            "service": {"label": "一次夜诊护理", "gain": {"stat": ["max_mind", 2]}},
        },
        "confirm_gain": {"item": "folded_projectile"},
        "hint": "第 2 层往下有一处留灯的避难圈。点亮灯台，把环内清干净（关掉火源、放气，"
                "或放下侧门挡板把东西挡在外头），连着三个世界回合别让失控意识踩进环里，回来销账。",
    },
    "quest.watcher_pages": {
        "name": "监视者的页码", "giver": "npc.scrap_registrar",
        # §7.2「监视者的三页」：具名散页有实际去向——3–17 层的档案馆编目台每台
        # 能拆出一页（scene.archive_desk 的 extract_leaf），纸页犬身上也带着一页
        # （掉落改为留言板签名页）。两条来路不强迫任何一条刷满（§7.2「其余页
        # 不强迫刷同种敌人」）。
        "template": "recover_deliver",
        "delivery": "giver",
        "requirement": {"type": "item", "item": "guestbook_page", "count": 3},
        "requirement_text": "找回 3 页协会账页（档案馆编目台拆页，或从纸页犬身上取回）",
        "rewards": {
            "supply": {"label": "一份线轴补给", "gain": {"item": "loose_thread"}},
            "service": {"label": "一次协会护理", "gain": {"stat": ["max_mind", 3]}},
        },
        "hint": "纸页犬咬走了协会的账本页。散页有实际去向：3–17 层的档案馆编目台能拆出一页，"
                "纸页犬身上也带着一页——凑够 3 页回来销账。",
    },
    "quest.lf_marathon": {
        "name": "遗失物有名字", "giver": "npc.lost_found",
        # §7.2「遗失物有名字」（来源改造：旧「失物招领的马拉松」累计回应 5 处）：
        # 调查模板（§7.1 模板 5）——候车厅的两处证据（失物登记册＋行李签）确定
        # 一件具名失物的物主；怎么处置由交付时的报酬选择决定（§7.2「偷拿的关系
        # 后果预览」直接写进选项标签，不当隐藏惩罚）。
        "template": "investigate",
        "site": "scene.waiting_hall",
        "clues": ("manifest", "tag"),
        "requirement": {"type": "target_resolve", "count": 1},
        "requirement_text": "在候车厅查两处证据（失物登记册＋行李签），确定那只玻璃瓶的物主",
        "rewards": {
            "return": {"label": "交还失主，换一次招领服务", "gain": {"stat": ["max_lucidity", 2]}},
            "keep": {"label": "代为保管，换一条旁路情报", "gain": {"item": "mirror_shard"}},
            "claim": {"label": "声明占有（招领处会记住这瓶归了你）", "gain": {"item": "glass_bottle"}},
        },
        "hint": "候车厅里压着一件没人认领的失物。查失物登记册、再对窗边杂物上的行李签，"
                "两处证据对上就定了物主——归还、代管还是声明占有，销账时说清楚。",
    },
    "quest.bar_wake": {
        "name": "一杯给醒着的人", "giver": "npc.dream_bartender",
        # §7.2「一杯给醒着的人」（来源改造：旧「到达第 11 层」绝对深度目标）：
        # 环境修复模板——把候车厅的铺位铺出来、让大厅连着 3 个世界回合安全，
        # 避难点才算恢复（§7.2「不要求护送到另一大区」；护送旅人一支等行程链）。
        "template": "fix_environment",
        "site": "scene.waiting_hall",
        "zone": "hall",
        "requirement": {"type": "target_resolve", "count": 1},
        "target_text": "把候车厅的长椅铺成旅人的铺位，让大厅连着 3 个世界回合没有火、"
                       "没有失控意识踩进去",
        "rewards": {
            "supply": {"label": "避难点开放＋一份温饮", "gain": {"item": "deep_thought_tea"}},
            "service": {"label": "一次夜班照料", "gain": {"stat": ["max_mind", 3]}},
        },
        "hint": "候车厅是旅人歇脚的地方，只是还没人收拾：把长椅铺成铺位，守着大厅连着三个"
                "世界回合别让失控意识踩进去——回来换一杯给醒着的人的茶。",
    },
    "quest.poet_line": {
        "name": "诗的下半句", "giver": "npc.nameless_poet",
        # §7.2「诗的下半句」：调查模板——两处有不同意义的回声＝对折渡口的两张
        # 折页（纸页本身就是诗页）：内外两端各自折稳，各漏出半句回声；两处都要
        # 在接取之后立住（facts.report）。§7.2 的「选择解释并完成对应行动」
        # 等回声族场景再分岔，先认「两处都听到」这一段。
        "template": "investigate",
        "site": "scene.fold_ferry",
        "clues": ("echo_inner", "echo_outer"),
        "requirement": {"type": "target_resolve", "count": 1},
        "requirement_text": "在对折的渡口把内外两张折页都折稳，听全两处回声",
        "rewards": {
            "supply": {"label": "一份晨露＋他替你记下的一句", "gain": {"item": "morning_dew", "insight": "留白"}},
            "service": {"label": "一次润笔", "gain": {"stat": ["max_imagination", 2]}},
        },
        "hint": "诗人丢了下半句诗。对折的渡口那两张空白折页本身就是诗页：把内外两端都折稳，"
                "回声会漏出他要的词——回来念给他听。",
    },
}
STRUCTURE_NPC_BINDING: dict[str, str] = {
    "grand_shrine": "npc.mind_observer",
    "reading_hall": "npc.hypnotist",
}
