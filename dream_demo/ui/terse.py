"""少字模式（terse mode）共享词表与文本压缩工具。

玩家设置 `terse_mode` 打开后，只压缩**右侧栏及其子菜单**：
- 有专属语义图标的字段直接用图标（stats / 噪音 / 混乱 / 导航）；
- 没有图标的标题、字段名用英文缩写；
- 可展开的注释默认收起。

左侧悬浮窗、全屏窗口（设置/图鉴/暂停/联想盘/格子详情等）**不经过**本模块。
这里只做纯文本与配色工具，不读 GameState，不拥有任何面板状态。
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping

from rich.text import Text

SETTING_KEY = "terse_mode"

# 心智 / 清醒四档（0 健康 → 3 紧急）。玩家指定：↑→↓X。
TIER_GLYPHS: tuple[str, str, str, str] = ("↑", "→", "↓", "X")

# 悬停地形四层，从下到上。玩家指定：⇓⇔⇗⇑。
LAYER_GLYPHS: tuple[str, str, str, str] = ("⇓", "⇔", "⇗", "⇑")
LAYER_LABELS: tuple[str, str, str, str] = ("地板", "表面", "高处", "空中")

# 没有专属图标时使用英文缩写的手工词表。键是代码里的中文原文（i18n 的键），
# 值是**显示用**的短缩写；宁可短到能排进窄栏，也不保留整段中文。
SHORT_LABELS: dict[str, str] = {
    # 位置 / 悬停读数
    "位置": "P", "当前": "C", "悬停": "H", "观察": "O", "地上": "G", "贴近": "N",
    "地板": "FLR", "表面": "SFC", "高处": "HI", "空中": "AIR",
    "硬": "H", "厚": "T", "完": "I",
    # 状态区
    "崩解度": "DIS", "回合数": "T", "回合": "T", "可下潜": "DIVE",
    "深层边界": "EDGE", "噪音": "NOISE", "混乱": "CHAOS", "混乱度": "CHAOS",
    # 右侧工作区 / 子页
    "行动": "ACT", "行囊": "PACK", "构筑": "BUILD", "自身": "SELF",
    "环境": "ENV", "日志": "LOG", "构想": "ABL", "发射": "FIRE",
    "篡改": "EDIT", "装备": "GEAR", "记忆": "MEM", "洞察": "INS",
    "征兆": "SIGN", "数值": "STAT", "详查": "FULL", "周围": "NEAR",
    "记录": "LOG", "任务": "TASK",
    # 通用字段
    "目标": "TGT", "作用区": "AOE", "作用环": "AOE", "中心": "C",
    "射程": "RNG", "范围": "AOE", "费用": "COST", "冷却": "CD",
    "强度": "PWR", "持续": "DUR", "基础值": "BASE", "来源": "SRC",
    "视野": "SIGHT", "探索进度": "EXP", "地图尺寸": "SIZE",
    "层名": "NAME", "层型": "FORM", "修饰符": "MOD", "当前层": "LAYER",
    "异象": "ANOM", "稳定意识": "CALM", "失控意识": "HOSTILE",
    "事件": "EVT", "掉落物": "DROP", "物品": "ITEM",
    # 环境页字段
    "墙体": "WALL", "液体": "LIQ", "气体": "GAS", "植物": "FLORA",
    "均值": "AVG", "总耐久": "DUR", "总液量": "VOL", "总气量": "GAS",
    "视觉遮蔽": "OCC", "听觉盲区": "DEAF", "环境风险": "RISK",
    "火焰": "FIRE", "可燃气": "F.GAS", "可燃液体": "F.LIQ",
    "接触效果": "TOUCH", "吸入效果": "INHALE",
    # 操作 / 物品菜单
    "使用": "USE", "投掷": "THROW", "放下": "DROP", "丢弃": "DROP",
    "卸下": "TAKE OFF", "携带": "CARRY", "分类": "TYPE",
    "搜索": "FIND", "筛选": "FILTER", "排序": "SORT", "详情": "MORE",
    "操作": "USE", "固定": "PIN", "返回": "BACK", "折叠": "FOLD",
    "清除": "CLR", "关闭": "CLOSE", "确认": "OK", "取消": "CANCEL",
    "基础耗时": "TIME", "有效耗时": "TIME", "基础创伤": "DMG",
    "事件记录": "LOG", "操作界面": "ACT", "同格内容": "CELL",
    "对象与任务": "OBJ", "另有": "MORE", "层": "F",
}

# 明确要求保留的文字型描述词（玩家原话：耐久等描述词保留）。
KEEP_WORDS: frozenset[str] = frozenset({"耐久", "总耐久", "厚度", "高度", "总液量",
                                            "总气量", "层数"})

# 冒号前的字段 / 标题用英文缩写。只匹配 1–10 个汉字（或 ·），不碰英文键名。
_FIELD_COLON_RE = re.compile(r"^(\s*)([\u4e00-\u9fff·]{1,10})[：:]")


def enabled(source) -> bool:
    """`source` 可以是 ConfigManager、Config 值字典，或带 `get` 的任意对象。"""
    if source is None:
        return False
    try:
        return bool(source.get(SETTING_KEY))
    except Exception:
        return False


def icon(key: str, fallback: str = "") -> str:
    """优先取语义图标（游戏启动器加载字体时），否则用两列文本回退。"""
    try:
        from ..data.semantic_icons import semantic_icon
        result = semantic_icon(key)
        if result:
            return result
    except Exception:
        pass
    return fallback


STAT_FALLBACKS: dict[str, str] = {
    "mind": "☻ ",
    "lucidity": "◉ ",
    "imagination": "✦ ",
    "noise": "♪ ",
    "chaos": "✳ ",
    "integrity": "▣ ",
    "collapse": "▨ ",
    "endurance": "◈ ",
}


def stat_glyph(kind: str, mode: str = "themed") -> str:
    """状态条标签：心智/清醒/想象/噪音/混乱等自己的符号。"""
    from ..symbols import symbol
    fallback = STAT_FALLBACKS.get(kind, "· ")
    if mode == "ascii":
        value = symbol("stat." + kind, mode)
        if value and value != "??":
            return value
        return fallback[:2]
    return icon("stat." + kind if kind != "noise" else "noise.pulse",
                fallback)


def tier_glyph(tier: int) -> str:
    return TIER_GLYPHS[max(0, min(len(TIER_GLYPHS) - 1, int(tier)))]


def layer_glyph(index: int) -> str:
    return LAYER_GLYPHS[max(0, min(len(LAYER_GLYPHS) - 1, int(index)))]


def _english(label: str) -> str:
    try:
        from ..i18n import LANGUAGE_PACKS
        text = LANGUAGE_PACKS.get("en", {}).get(label, "")
        return text if text and text != label else ""
    except Exception:
        return ""


def abbrev(label: str) -> str:
    """中文标签 → 短英文缩写；没有译文时原样返回（绝不吞掉信息）。"""
    label = str(label or "").strip()
    if not label or label in KEEP_WORDS:
        return label
    hand = SHORT_LABELS.get(label)
    if hand:
        return hand
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 /'-]*", label):
        explicit = globals().get('EN_PHRASES', {}).get(label)
        if explicit:
            return explicit
        words = re.findall(r"[A-Za-z0-9]+", label)
        if len(words) > 1:
            return ''.join(word[0] for word in words[:4]).upper()
        return label[:3].upper() if len(label) > 3 else label.upper()
    english = _english(label)
    if not english:
        return label
    explicit = globals().get('EN_PHRASES', {}).get(english)
    if explicit:
        return explicit
    words = re.findall(r"[A-Za-z0-9]+", english)
    if not words:
        return label
    if len(words) >= 2:
        return "".join(word[0] for word in words[:4]).upper()
    word = words[0]
    return word[:3].upper() if len(word) > 3 else word.upper()


def field_abbrev(label: str) -> str:
    """冒号前字段名的缩写；玩家指定保留的纯文字描述词除外。"""
    if label in KEEP_WORDS:
        return label
    return abbrev(label)


def _effective_style(text: Text, start: int, end: int) -> str:
    """Return the span style that covers [start,end); base style otherwise."""
    style = text.style
    for span in text.spans:
        if span.start <= start and end <= span.end:
            style = span.style
    return style if isinstance(style, str) else str(style or "")


def _segments(text: Text) -> Iterable[tuple[int, int, str]]:
    plain = text.plain
    length = len(plain)
    if not length:
        return
    boundaries = {0, length}
    for span in text.spans:
        boundaries.add(max(0, min(length, span.start)))
        boundaries.add(max(0, min(length, span.end)))
    points = sorted(boundaries)
    for start, end in zip(points, points[1:]):
        if start < end:
            yield start, end, _effective_style(text, start, end)


def replace_text(text: Text, replacements: Mapping[str, str]) -> Text:
    """按词表替换 Text 中的字符串，逐个 span 重建以保留颜色。"""
    plain = text.plain
    if not plain or not replacements:
        return text
    result = Text(style=text.style, no_wrap=text.no_wrap, justify=text.justify,
                  overflow=text.overflow, end=text.end)
    for start, end, style in _segments(text):
        segment = plain[start:end]
        for source in sorted(replacements, key=len, reverse=True):
            if source and source in segment:
                segment = segment.replace(source, replacements[source])
        if segment:
            result.append(segment, style=style)
    return result


def _runs(text: Text, start: int, end: int):
    """把 [start,end) 按 span 边界切成 (a,b,style) 片段。"""
    length = len(text.plain)
    start, end = max(0, start), min(length, end)
    if start >= end:
        return
    boundaries = {start, end}
    for span in text.spans:
        for point in (span.start, span.end):
            if start < point < end:
                boundaries.add(point)
    points = sorted(boundaries)
    for a, b in zip(points, points[1:]):
        yield a, b, _effective_style(text, a, b)


def _append_range(result: Text, text: Text, start: int, end: int) -> None:
    for a, b, style in _runs(text, start, end):
        result.append(text.plain[a:b], style=style)


def terse_fields(text: Text) -> Text:
    """把「字段：」的字段名换成英文缩写；行首标题也压成缩写。"""
    plain = text.plain
    if not plain:
        return text
    lines = plain.split("\n")
    targets: list[tuple[int, int, str] | None] = []
    changed = False
    for line in lines:
        match = _FIELD_COLON_RE.match(line)
        if match:
            indent, label = match.groups()
            short = field_abbrev(label)
            if short and short != label:
                targets.append((len(indent), len(label), short))
                changed = True
                continue
        targets.append(None)
    if not changed:
        return text
    result = Text(style=text.style, no_wrap=text.no_wrap, justify=text.justify,
                  overflow=text.overflow, end=text.end)
    offset = 0
    for index, (line, target) in enumerate(zip(lines, targets)):
        source_len = len(line)
        if target is not None:
            indent_len, label_len, short = target
            # 缩写沿用原字段第一个字/整段的样式（标签通常同色）。
            _append_range(result, text, offset, offset + indent_len)
            result.append(short, style=_effective_style(text, offset + indent_len,
                                                        offset + indent_len + label_len))
            _append_range(result, text, offset + indent_len + label_len, offset + source_len)
        else:
            _append_range(result, text, offset, offset + source_len)
        offset += source_len
        if index < len(lines) - 1:
            result.append("\n")
            offset += 1
    return result


def compress(text: Text, mode: str = "themed") -> Text:
    """通用右栏压缩：状态名→图标、字段名→英文缩写。"""
    mapping = {
        "心智": stat_glyph("mind", mode),
        "清醒度": stat_glyph("lucidity", mode),
        "想象力": stat_glyph("imagination", mode),
        "混乱度": stat_glyph("chaos", mode),
        "混乱": stat_glyph("chaos", mode),
        "噪音": stat_glyph("noise", mode),
        # 右栏标题：日志与构筑（world/equipment）整页不经过 compress，
        # 其余页面的标题按玩家规则压成英文缩写。
        "操作界面": "ACT",
        "事件记录": "LOG",
        "观测": "OBS",
        "环境概述": "ENV",
        "数值与来源": "STATS",
        # 视野外/知识权限读数（悬停 fog 分支）。
        "未探索": "?",
        "液态记忆": "≈ ",
        "弥散印象": "░ ",
        "始终可见": "VIS",
        "已发现地点": "SITE",
    }
    return terse_fields(replace_text(text, mapping))


def current_cell_entry() -> str:
    """悬停读数里的「当前格详情」点击入口（有语义图标就用自己的）。"""
    return icon("ui.details", "▸ ")

# ---------------------------------------------------------------------------
# 英文普通模式（少字模式关闭）的右栏压缩
# ---------------------------------------------------------------------------
# 英文界面右栏比中文宽得多，状态/悬停/环境/数值会被长单词挤到折行或截断。
# 这里只压**右侧栏**：左侧悬浮详情与全屏窗口（层详情、格子详情、设置、图鉴）
# 仍显示完整英文单词。
EN_PHRASES: dict[str, str] = {
    # 状态区
    "Shallow Dream": "SHAL DRM",
    "Recognizable Rooms": "RECO RMS",
    "Dissolution": "DIS",
    "Rounds": "R",
    "Noise": "NOI",
    "Chaos": "CHA",
    "Lucidity": "LUC",
    "Imagination": "IMA",
    "Healthy": "OK",
    "Impaired": "DMG",
    "Damaged": "DMG",
    "Danger": "DGR",
    "Critical": "CRIT",
    "Urgent": "URG",
    # 悬停地形
    "Floor": "FLR",
    "Surface": "SFC",
    "High": "HI",
    "Air": "AIR",
    "Position": "POS",
    "Current": "HERE",
    "Hover": "HOV",
    "Observe": "OBS",
    # 环境页
    "Anomalies": "ANOM",
    "Stable Consciousness": "CALM",
    "Survey": "SURV",
    "Wall": "WALL",
    "Liquid": "LIQ",
    "Gas": "GAS",
    "Plant": "FLORA",
    "Plants": "FLORA",
    "plants": "PLT",
    "Mean": "AVG",
    "Integrity": "INT",
    "Thickness": "THK",
    "Height": "HGT",
    "total durability": "DUR",
    "Durability": "DUR",
    "total volume": "VOL",
    "total gas": "GAS",
    "Sight blocked": "OCC",
    "obscuring gas/tall cover": "OBS GAS/COVER",
    "Hearing blind": "DEAF",
    "Sound blind spots": "DEAF",
    "Environmental risk": "RISK",
    "Environmental risks": "RISK",
    "risks": "RISK",
    "powered": "PWR",
    "Flammable gas": "FUEL GAS",
    "flammable gas": "FUEL GAS",
    "flammable liquid": "FUEL LIQ",
    "Combustible gas": "FUEL GAS",
    "Combustible liquid": "FUEL LIQ",
    "Contact effects": "TOUCH",
    "Inhalation effects": "INHALE",
    "Platform": "PLAT",
    "Contact effect": "TOUCH",
    "Inhalation effect": "INHALE",
    "Events": "EVT",
    "Drops": "DROP",
    "objects": "OBJ",
    "Objects": "OBJ",
    "Boundary": "BND",
    "Cotton": "COT",
    "Memory": "MEM",
    "Vessel": "VSL",
    "Diluted": "DIL",
    "weight": "WT",
    "Weight": "WT",
    "matching weakness": "weak match",
    "Unavailable": "N/A",
    "Inventory": "PACK",
    "Mind Inventory": "PACK",
    "Stats and sources": "STATS",
    "Stats and Sources": "STATS",
    "sources": "SRC",
    "Sources": "SRC",
    "Aggregate": "AGG",
    "aggregate": "AGG",
    "Compacted": "CMP",
    "compacted": "CMP",
    "Unstable": "UNST",
    "Reflective": "REFL",
    "Scalding": "SCLD",
    "Glowing": "GLOW",
    "Lichen": "LICH",
    "Thicket": "THKT",
    "Flammable": "FLAM",
    "No known objects in sight.": "NO OBJ IN SIGHT",
    "No known objects in sight": "NO OBJ IN SIGHT",
    "matching weakness": "weak match",
    "Matching weakness": "weak match",
    "matching weaknesses": "weak match",
    "turns/hit": "T/hit",
    "turns/tile": "T/TL",
    "turns": "T",
    "tiles": "TL",
    "tile": "TL",
    "points": "PTS",
    "point": "PT",
    "rounds": "R",
    "round": "R",
    "turns": "T",
    "turn": "T",
    # 数值页分类（正式词形在悬浮详情里给全）
    "Base melee trauma": "BMD",
    "Base melee time": "BMT",
    "Effective melee time": "EMT",
    "Base move time": "BMV",
    "Effective move time": "EMV",
    "Move delay penalty": "MDP",
    "Attack delay penalty": "ADP",
    "Action speed multiplier": "ASM",
    "Throw range": "TR",
    "Explosion bonus": "EB",
    "Fire spread": "FS",
    "Penetration bonus": "PB",
    "Solidity penalty": "SP",
    "Dissolution gain": "DG",
    "Loot luck": "LL",
    "Sight radius": "SR",
    "Identity environment weakness": "IEW",
    "Natural imagination regen": "NIR",
    "Imagination regen progress": "IRP",
    "Imagination cap": "IC",
    "Mind cap": "MC",
    "Lucidity cap": "LC",
    "One-shot buffer": "OSB",
    "Ability cost multiplier": "ACM",
    "Ability cooldown": "AC",
    "Consecutive tamper pressure": "CTP",
    "Final tamper chaos cost": "FTCC",
    "Immediate environment trauma": "IET",
    "Portent accumulation factor": "PAF",
    "New portent duration": "NPD",
}

# 这些词是键位/操作名，不缩写。
EN_KEEP = frozenset({
    "Alt", "Esc", "Enter", "Shift", "Ctrl", "Tab", "Home", "End", "PgUp",
    "PgDn", "WASD", "QoL", "ID", "HP", "UI", "OK",
})

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'/-]{2,}")


def _english_label_map() -> dict[str, str]:
    """整段英文数值项 → 缩写。

    只收**完整短语**（来自官方英译），不做逐词短词替换——「Close」「Off」
    这类短词会误伤物品名（例如 Coffee 里的 off），所以普通模式绝不做
    三字母以下的词表替换。
    """
    mapping: dict[str, str] = {}
    try:
        from ..i18n_stat_names_en import EN_STAT_NAMES
        for zh, english in EN_STAT_NAMES.items():
            if len(english) >= 6:
                mapping.setdefault(english, abbrev(zh))
    except Exception:
        pass
    return mapping


def _short_english_word(word: str) -> str:
    if word in EN_KEEP:
        return word
    if len(word) <= 5:
        return word
    # 保留全大写缩写/代号（环境页字段、图例）不动。
    if word.isupper():
        return word
    return word[:3].upper()


def _word_compact(text: Text) -> Text:
    result = Text(style=text.style, no_wrap=text.no_wrap, justify=text.justify,
                  overflow=text.overflow, end=text.end)
    for start, end, style in _segments(text):
        segment = text.plain[start:end]
        segment = _WORD_RE.sub(lambda m: _short_english_word(m.group(0)), segment)
        result.append(segment, style=style)
    return result


def compact_english_string(value: str) -> str:
    """英文右栏单行字符串压缩（用于换行前先缩词，避免先折行再缩写）。"""
    try:
        from ..i18n import get_language
        if get_language() != "en" or not value:
            return value
    except Exception:
        return value
    result = str(value)
    mapping = {**_english_label_map(), **EN_PHRASES}
    for source in sorted(mapping, key=len, reverse=True):
        if source and source in result:
            result = result.replace(source, mapping[source])
    return _WORD_RE.sub(lambda m: _short_english_word(m.group(0)), result)


def compact_english(text: Text, *, word_level: bool = True) -> Text:
    """英文右栏压缩：先替换整段字段/状态词，再按词缩短长单词。

    只在当前界面语言为 en 且少字模式关闭时由宿主调用；左侧悬浮窗和全屏
    窗口不经过这里，因此打开详情时仍是完整英文。
    """
    try:
        from ..i18n import get_language
        if get_language() != "en":
            return text
    except Exception:
        return text
    mapping = {**_english_label_map(), **EN_PHRASES}
    result = replace_text(text, mapping)
    return _word_compact(result) if word_level else result


def subpage_english_short(subpage_id: str) -> str:
    """英文普通模式的右栏小页签短名（详情界面仍显示完整词）。"""
    return {
        "全部": "ALL", "携带意象": "CARRY", "摄入物": "INGEST",
        "易逝物": "PERISH", "交互道具": "TOOL", "惯用物": "HABIT",
        "board": "GEAR", "memory": "MEM", "constructs": "CAST",
        "fire": "FIRE", "tamper": "EDIT",
    }.get(subpage_id, subpage_id)


def english_label(value: str) -> str:
    """英文普通模式的环境页标题短名；其它语言原样返回。"""
    try:
        from ..i18n import get_language
        if get_language() != "en":
            return value
    except Exception:
        return value
    return {
        "异象": "ANOM", "稳定意识": "CALM", "环境概述": "SURV",
        "视野": "SIGHT", "格": "T", "株": "PLANTS",
    }.get(value) or compact_english_string(value)


def route_symbol(route_key: str, mode: str = "themed") -> str:
    """右栏子页签符号；无专属图标时使用短 ASCII 代号。"""
    from ..symbols import symbol
    mapping = {
        "constructs": ("section.constructs", "✦ "),
        "fire": ("section.fire", "▲ "),
        "tamper": ("section.tamper", "✎ "),
        "equipment-board": ("section.board", "⚒ "),
        "equipment-memory": ("section.memory", "◈ "),
        "insights": ("section.insights", "◆ "),
        "portents": ("section.portents", "◇ "),
        "self-stats": ("section.stats", "∑ "),
        "self-audit": ("section.audit", "⊙ "),
        "nearby": ("section.nearby", "◎ "),
        "records": ("section.records", "☷ "),
        "quests": ("section.quests", "✓ "),
    }
    key, fallback = mapping.get(route_key, ("", "· "))
    if key:
        value = symbol(key, mode)
        if mode == "ascii" and len(value) > 2:
            value = value[:2]
        return value
    return fallback


def subpage_symbol(subpage_id: str, mode: str = "themed") -> str:
    """面板内部小页签（行囊分类 / 装备盘记忆 / 构想发射篡改）的符号。"""
    from ..symbols import symbol
    mapping = {
        "全部": ("subtab.all", "≣ "),
        "携带意象": ("subtab.carried", "♕ "),
        "摄入物": ("subtab.ingest", "♨ "),
        "易逝物": ("subtab.perishable", "◷ "),
        "交互道具": ("subtab.interactive", "◇ "),
        "惯用物": ("subtab.habit", "▣ "),
        "board": ("subtab.board", "▦ "),
        "memory": ("subtab.memory", "◈ "),
        "constructs": ("section.constructs", "✦ "),
        "fire": ("section.fire", "▲ "),
        "tamper": ("section.tamper", "✎ "),
    }
    key, fallback = mapping.get(subpage_id, ("", "· "))
    if key:
        value = symbol(key, mode)
        if mode == "ascii" and len(value) > 2:
            value = value[:2]
        return value
    return fallback


def tool_symbol(tool_key: str, mode: str = "themed") -> str:
    """右栏工具栏（搜/类/序/详情/操作/×/固定/返回/物品/折叠）符号。"""
    from ..symbols import symbol
    mapping = {
        "search": ("tool.search", "⌕ "),
        "filter": ("tool.filter", "▽ "),
        "sort": ("tool.sort", "↕ "),
        "expand": ("tool.expand", "＋ "),
        "menu": ("tool.menu", "☰ "),
        "clear": ("tool.clear", "× "),
        "pin": ("tool.pin", "⚲ "),
        "back": ("tool.back", "← "),
        "related": ("tool.related", "◇ "),
        "fold": ("tool.fold", "≣ "),
    }
    key, fallback = mapping.get(tool_key, ("", "· "))
    if key:
        value = symbol(key, mode)
        if mode == "ascii" and len(value) > 2:
            value = value[:2]
        return value
    return fallback


def material_glyph(kind: str, name: str, mode: str = "themed") -> str:
    """材料名 → 地图同款两列图标。

    `kind` ∈ wall/liquid/gas/plant/floor；找不到专属图标时退回该类的通用图标。
    """
    from ..materials import (FLOOR_DEFINITIONS, floor_def, gas_def, liquid_def,
                             plant_def_for, wall_def)
    from ..symbols import symbol
    try:
        if kind == "wall":
            return symbol(wall_def(name).symbol_key, mode)
        if kind == "liquid":
            return symbol("liquid.medium", mode)
        if kind == "gas":
            return symbol("gas.faint", mode)
        if kind == "plant":
            from ..materials.plants import PLANT_KINDS
            code = next((d.code for d in PLANT_KINDS if d.name == name), 0)
            return symbol(plant_def_for(code).key if code else "plant", mode)
        if kind == "floor":
            if name in FLOOR_DEFINITIONS:
                return symbol(floor_def(name).symbol_key, mode)
            return symbol("floor", mode)
    except Exception:
        pass
    fallback = {"wall": "solid", "liquid": "liquid.medium", "gas": "gas.faint",
                "plant": "plant", "floor": "floor"}.get(kind, "floor")
    return symbol(fallback, mode)
