from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .i18n import tr


class SettingType(str, Enum):
    BOOL = "bool"
    ENUM = "enum"
    INT = "int"
    KEY_BIND = "key_bind"
    # 动作型设置项：没有可调整的值，Enter/点击触发一次操作（如删除历史统计）。
    ACTION = "action"


@dataclass(frozen=True)
class SettingDef:
    key: str
    label: str
    setting_type: SettingType
    default: bool | int | str
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    step: int = 1
    description: str = ""
    formatter: Callable[[bool | int | str], str] | None = None


def _format_symbol_mode(value: bool | int | str) -> str:
    return "主题符号" if value == "themed" else "ASCII"


def _format_fx_quality(value: bool | int | str) -> str:
    return {"off": "关闭", "low": "流畅", "high": "完整"}.get(str(value), str(value))


def _format_map_display(value: bool | int | str) -> str:
    return {"auto": "自动（推荐）", "image": "图像", "character": "字符"}.get(
        str(value), str(value))


def _format_map_observe(value: bool | int | str) -> str:
    return tr({"composite": "综合", "floor": "地板", "low": "低层", "middle": "中层",
               "high": "高层", "terrain": "地形", "liquid": "液体", "gas": "气体",
               "elevation": "地势", "sound": "声音线索"}.get(str(value), str(value)))


def _format_equipment_syntax(value: bool | int | str) -> str:
    return {"zh": tr("中文语序"), "en": tr("英文语序")}.get(str(value), str(value))


def _format_language(value: bool | int | str) -> str:
    from .i18n import LANGUAGE_LABELS

    return LANGUAGE_LABELS.get(str(value), str(value))


SETTING_REGISTRY: tuple[SettingDef, ...] = (
    SettingDef(
        "symbol_mode",
        "表征模式",
        SettingType.ENUM,
        "themed",
        choices=("themed", "ascii"),
        description="切换主题符号与固定双列 ASCII 符号。",
        formatter=_format_symbol_mode,
    ),
    SettingDef(
        "auto_pickup",
        "自动收纳",
        SettingType.BOOL,
        False,
        description="安全时进入显化物所在格后自动收纳。",
    ),
    SettingDef(
        "show_details",
        "默认展开注释",
        SettingType.BOOL,
        True,
        description="控制行囊、观测录和操作页的灰色说明。",
    ),
    SettingDef("key_up", "向上主键", SettingType.KEY_BIND, "w"),
    SettingDef("key_down", "向下主键", SettingType.KEY_BIND, "s"),
    SettingDef("key_left", "向左主键", SettingType.KEY_BIND, "a"),
    SettingDef("key_right", "向右主键", SettingType.KEY_BIND, "d"),
    SettingDef(
        "numpad5_wait",
        "小键盘5等待",
        SettingType.BOOL,
        True,
        description="开启后按小键盘 5 原地等待一回合；关闭则 5 无效，避免误触。",
    ),
    SettingDef(
        "language",
        "语言",
        SettingType.ENUM,
        "zh",
        choices=("zh", "en"),
        description="切换界面与内容的显示语言。",
        formatter=_format_language,
    ),
    # 危险动作：追加在注册表末尾（既有设置项的下标保持不变，测试依赖行号）。
    # 值列不落盘，删除走 SettingsPageState.delete_callback（见 ui/app.py）。
    # 动作项：追加在注册表末尾（既有设置项的下标保持不变，测试依赖行号）。
    # 值列不落盘，动作走 SettingsPageState 的回调（见 ui/app.py）。
    SettingDef(
        "unlock_catalog",
        "一键解锁全部图鉴",
        SettingType.ACTION,
        "",
        description="把图鉴中所有条目标记为已解锁，便于查阅资料。",
    ),
    SettingDef(
        "delete_history",
        "删除历史统计",
        SettingType.ACTION,
        "",
        description="清除图鉴里的遭遇/解决/交互等历史记录，不可恢复。",
    ),
    # 音频设置：追加在注册表末尾（既有设置项的下标保持不变，测试依赖行号）。
    SettingDef(
        "sfx_enabled",
        "音效",
        SettingType.BOOL,
        True,
        description="移动、投掷、下潜等动作音效。",
    ),
    SettingDef(
        "sfx_volume",
        "音效音量",
        SettingType.INT,
        7,
        minimum=0,
        maximum=10,
        description="0 静音，10 最响。",
    ),
    SettingDef(
        "music_volume",
        "音乐音量",
        SettingType.INT,
        6,
        minimum=0,
        maximum=10,
        description="背景音乐音量；0 为静音，不影响音效。",
    ),
    # 画面特效：追加在注册表末尾（既有设置项的下标保持不变，测试依赖行号）。
    SettingDef(
        "fx_scanlines",
        "扫描线效果",
        SettingType.BOOL,
        True,
        description="低清醒度时的隔行扫描线（CRT 暗线）。可独立于画面特效开关。",
    ),
    SettingDef(
        "fx_quality",
        "画面特效",
        SettingType.ENUM,
        "high",
        choices=("off", "low", "high"),
        description="地图动态光影：关闭 / 流畅（10 帧） / 完整（呼吸光环·暗角·涟漪）。",
        formatter=_format_fx_quality,
    ),
    SettingDef(
        "floor_transition",
        "上下层切换动画",
        SettingType.BOOL,
        True,
        description="下潜/上浮时旧层崩解、新层在角色周围生成；关闭则直接切换。",
    ),
    SettingDef(
        "fx_light_walls",
        "光照覆盖墙体",
        SettingType.BOOL,
        True,
        description="动态光照作用于地板、墙体与一切格子；关闭则只照亮可通行的格。",
    ),
    SettingDef("skip_tutorial", "新存档跳过教程", SettingType.BOOL, False,
               description="开启后新建存档直接进入第一层；不改变已有存档的教程状态。"),
    SettingDef("music_enabled", "音乐", SettingType.BOOL, True,
               description="播放主页、区域、梦中梦与结局音乐；与音效开关独立。"),
    # 篡改键：地图与事件/NPC 对话共享入口，不进 RESERVED_KEY_BINDINGS
    # ——「c」本来没人占用，而把它登记进去会让这一项拒绝自己的默认值。
    SettingDef("key_tamper", "篡改键", SettingType.KEY_BIND, "c",
               description="对话与地图中打开篡改面板的按键。"),
    # 地图显示模式（docs §13.2）：WezTerm 主图像，其他终端兼容字符。
    SettingDef(
        "map_display",
        "地图显示",
        SettingType.ENUM,
        "auto",
        choices=("auto", "image", "character"),
        description="自动优先图像（适配终端时），否则字符；图像初始化失败会回退字符并给出原因。",
        formatter=_format_map_display,
    ),
    SettingDef(
        "map_observe",
        "默认观察层",
        SettingType.ENUM,
        "composite",
        choices=("composite", "floor", "low", "middle", "high", "liquid", "gas", "elevation", "terrain", "sound"),
        description="F3 进入分层观察；观察层切换只在本次界面生效，不覆盖本机地图显示偏好。",
        formatter=_format_map_observe,
    ),
    # 装备盘语序（docs §14.13 第 5 项）：只决定**新盘面**用哪套列角色，
    # 已有盘面各自带 syntax（随存档往返），切换语序不会重解已摆好的构筑。
    SettingDef(
        "equipment_syntax",
        "装备句法",
        SettingType.ENUM,
        "zh",
        choices=("zh", "en"),
        description="中文语序＝修饰在前、行为在四列；英文语序把行为前移到三列，"
                    "宾语在后。只影响新盘面与词牌标签，不改变任何效果、费用或冷却。",
        formatter=_format_equipment_syntax,
    ),
    # 异象切换提示（docs/261021异象意图与行动切换提示设计.md §6.1/§12）：
    # 只关角标、字形强调与内缘亮起；技能危险区域与观察文字照常显示。
    SettingDef(
        "intent_hints",
        "异象切换提示",
        SettingType.BOOL,
        True,
        description="异象开始怀疑、调查、逃离、蓄力、被打断或进入恢复时，"
                    "在该格短暂亮起小角标；追踪状态不再显示最高频的「!」。"
                    "关闭不影响技能危险区域与观察文字。",
    ),
    # 2026-10-22 玩家要求：整格大意图高亮（角色地图前景强调）默认关闭；
    # 小角标默认开启，但追踪（chase）的「!」不渲染。
    SettingDef(
        "intent_large_marks",
        "异象整格意图高亮",
        SettingType.BOOL,
        False,
        description="开启后异象切换意图时，在角色地图给异象所在整格字形叠前景高亮；"
                    "默认关闭，避免大标记周期性重绘影响连续移动。右上角小角标不受影响。",
    ),
)


from .controls import PANEL_SHORTCUTS, RESERVED_ALT_KEYS
SETTING_REGISTRY += tuple(
    SettingDef(entry.setting, entry.label, SettingType.KEY_BIND, entry.key,
               description='面板唤起键；只打开界面，不执行其中操作。')
    for entry in PANEL_SHORTCUTS
)


# 外部配置文件（game_config.ini）里「只在游戏内没有设置记录时生效」的键。
# 语言是这一类：初次开启按配置文件走，玩家在游戏内选过语言后永远按那次选择走
# （override_saved_settings 也压不过它，见 user_config.py 的优先级说明）。
RECORD_WINS_KEYS: frozenset[str] = frozenset({"language"})


RESERVED_KEY_BINDINGS: dict[str, str] = {
    **{key: "固定方向或等待键" for key in "123456789"},
    ".": "等待动作",
    "。": "等待动作",
    "f": "瞄准动作",
    "g": "收纳动作",
    "e": "回应动作",
    "q": "返回或投掷动作",
    "u": "使用动作",
    "n": "层间移动",
    "b": "层间返回",
    "i": "现实洞察界面",
    "k": "观测录界面",
    "?": "操作界面",
    "？": "操作界面",
    "/": "光标区域切换",
    "h": "操作界面",
    "\\": "注释展开收起",
}
from .controls import reserved_keys
RESERVED_KEY_BINDINGS.update(reserved_keys())


@dataclass
class GameConfig:
    values: dict[str, bool | int | str]

    def get(self, key: str) -> bool | int | str:
        return self.values[key]


@dataclass(frozen=True)
class SettingChange:
    changed: bool
    message: str
    persisted: bool = True


class ConfigManager:
    def __init__(
        self,
        path: str | Path,
        registry: Iterable[SettingDef] = SETTING_REGISTRY,
        file_defaults: Mapping[str, Any] | None = None,
        file_overrides_saved: bool = False,
    ) -> None:
        """``file_defaults`` 是外部配置文件（game_config.ini）的取值：

        优先级 内置默认 < file_defaults < 游戏内设置记录（玩家亲手改过的键）。
        ``file_overrides_saved=True`` 时 file_defaults 反过来压过游戏内记录，
        但 RECORD_WINS_KEYS（语言）永远尊重玩家在游戏内的选择。
        """
        self.path = Path(path)
        self.registry = tuple(registry)
        self.definitions = {definition.key: definition for definition in self.registry}
        self.file_defaults: dict[str, Any] = {
            key: value for key, value in (file_defaults or {}).items() if key in self.definitions
        }
        self.file_overrides_saved = bool(file_overrides_saved)
        self.migration_messages: list[str] = []
        self._keybind_resets: dict[str, str] = {}
        # 玩家在游戏内**亲手改过**的键（"有没有设置记录"的判据）。
        self.touched: set[str] = set()
        self.config = GameConfig({definition.key: definition.default for definition in self.registry})
        self._apply_file_defaults()
        self._load()
        if self.file_overrides_saved:
            self._apply_file_defaults()
        # File defaults are subject to the same reserved-key rules as saved keys.
        self._load_keybinds({}, [d for d in self.registry if d.setting_type is SettingType.KEY_BIND])
        if self._keybind_resets:
            for key in self._keybind_resets:
                self.touched.add(key)
            persisted, message = self._persist()
            for key, old in self._keybind_resets.items():
                label = tr(self.definitions[key].label)
                self.migration_messages.append(
                    f'{label}：{old} → {self.values[key]}。' + tr('旧按键与现有操作冲突，已恢复可用键位。') + message
                )

    @property
    def values(self) -> dict[str, bool | int | str]:
        return self.config.values

    def get(self, key: str) -> bool | int | str:
        return self.config.get(key)

    @staticmethod
    def _normalize(definition: SettingDef, value: Any) -> bool | int | str:
        if definition.setting_type is SettingType.BOOL:
            return value if type(value) is bool else definition.default
        if definition.setting_type is SettingType.ENUM:
            return value if isinstance(value, str) and value in definition.choices else definition.default
        if definition.setting_type is SettingType.INT:
            if type(value) is not int:
                return definition.default
            if definition.minimum is not None:
                value = max(definition.minimum, value)
            if definition.maximum is not None:
                value = min(definition.maximum, value)
            return value
        if definition.setting_type is SettingType.KEY_BIND:
            return value.lower() if isinstance(value, str) and value.strip() else definition.default
        if definition.setting_type is SettingType.ACTION:
            return definition.default
        return definition.default

    def has_record(self, key: str) -> bool:
        """这项设置有没有「玩家在游戏内改过」的记录。"""
        return key in self.touched

    def _apply_file_defaults(self) -> None:
        """套用外部配置文件的取值（无条件覆盖当前值，RECORD_WINS_KEYS 除外）。

        __init__ 里在 _load() 前后各调一次：后一次是 file_overrides_saved
        的「配置文件压过游戏内记录」通道。
        """
        for key, value in self.file_defaults.items():
            definition = self.definitions.get(key)
            if definition is None:
                continue
            if key in RECORD_WINS_KEYS and self.has_record(key):
                continue  # 语言：玩家在游戏内选过就永远听玩家的
            self.values[key] = self._normalize(definition, value)

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            user_values = payload.get("values", {}) if isinstance(payload, dict) else {}
            if not isinstance(user_values, dict):
                return
        except (OSError, ValueError, TypeError):
            return
        raw_touched = payload.get("touched") if isinstance(payload, dict) else None
        # 旧档（schema 1）压根没有 touched 字段：无法区分"改过/没改过"。
        legacy = "touched" not in payload or not isinstance(raw_touched, list)
        if legacy:
            # 旧档（schema 1）没记 touched：用「与内置默认不同」推断玩家改过；
            # 等于默认的项一律视作没改过，好让外部配置文件能接管它们。
            applied = {
                key: value
                for key, value in user_values.items()
                if key in self.definitions
                and self._normalize(self.definitions[key], value) != self.definitions[key].default
            }
        else:
            self.touched = {key for key in raw_touched if isinstance(key, str) and key in self.definitions}
            # 新档：只认玩家亲手改过的键，其余交给内置默认/外部配置文件。
            applied = {key: value for key, value in user_values.items() if key in self.touched}
        keybinds: list[SettingDef] = []
        for key, definition in self.definitions.items():
            if definition.setting_type is SettingType.KEY_BIND:
                keybinds.append(definition)
            elif key in applied:
                self.values[key] = self._normalize(definition, applied[key])
        self._load_keybinds(applied, keybinds)
        if legacy:
            self.touched = {
                key
                for key, definition in self.definitions.items()
                if key in applied and self.values[key] != definition.default
            }

    def _load_keybinds(self, user_values: dict[str, Any], definitions: list[SettingDef]) -> None:
        options: list[tuple[tuple[str, int], ...]] = []
        requested: dict[str, str] = {}
        for definition in definitions:
            # 没改过的按键回落到**当前值**（可能是外部配置文件的取值），
            # 而不是内置默认——否则配置文件改的键位会被旧档默认值顶掉。
            fallback = self.values.get(definition.key, definition.default)
            normalized = str(self._normalize(definition, user_values.get(definition.key, fallback)))
            requested[definition.key] = normalized
            if (self._keybind_format_issue(normalized) is not None
                    or definition.key.startswith('key_panel_') and not normalized.startswith('alt+')):
                normalized = str(definition.default)
            preferred = 1 if definition.key in user_values else 0
            choices = [(normalized, preferred)]
            if normalized != definition.default:
                choices.append((str(definition.default), 0))
            options.append(tuple(choices))

        best_values: tuple[str, ...] | None = None
        best_rank: tuple[int, tuple[int, ...]] | None = None
        possible = tuple(max(priority for _, priority in choices) for choices in options)
        maximum_rank = (sum(possible), possible)
        for combination in product(*options):
            values = tuple(value for value, _preferred in combination)
            if len(set(values)) != len(values):
                continue
            preferences = tuple(preferred for _value, preferred in combination)
            rank = (sum(preferences), preferences)
            if best_rank is None or rank > best_rank:
                best_values = values
                best_rank = rank
                if best_rank == maximum_rank:
                    break
        if best_values is not None:
            for definition, value in zip(definitions, best_values):
                self.values[definition.key] = value
                if requested[definition.key] != value:
                    self._keybind_resets.setdefault(definition.key, requested[definition.key])

    @staticmethod
    def _keybind_format_issue(candidate: str) -> str | None:
        alt = candidate.startswith('alt+') and len(candidate) == 5 and candidate[-1].isascii() and candidate[-1].isalnum()
        if (len(candidate) != 1 or not candidate.isprintable()) and not alt:
            return tr('按键须为单个可打印字符或 Alt+字母／数字。')
        if candidate in RESERVED_ALT_KEYS:
            return tr('该按键由{action}保留。', action=tr(RESERVED_ALT_KEYS[candidate]))
        reserved_for = RESERVED_KEY_BINDINGS.get(candidate)
        if reserved_for is not None:
            return tr("该按键由{action}保留。", action=tr(reserved_for))
        return None

    def _keybind_issue(self, key: str, candidate: str) -> str | None:
        if key.startswith('key_panel_') and not candidate.startswith('alt+'):
            return tr('面板唤起键必须使用 Alt+字母／数字。')
        format_issue = self._keybind_format_issue(candidate)
        if format_issue is not None:
            return format_issue
        for other in self.registry:
            if (
                other.key != key
                and other.setting_type is SettingType.KEY_BIND
                and self.values[other.key] == candidate
            ):
                return tr("按键已用于{label}。", label=tr(other.label))
        return None

    def _persist(self) -> tuple[bool, str]:
        next_path = self.path.with_suffix(self.path.suffix + ".next")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            next_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "values": self.values,
                        # 玩家亲手改过的键：外部配置文件只补没改过的项（语言等
                        # RECORD_WINS_KEYS 则永远以这里为准）。
                        "touched": sorted(self.touched),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            next_path.replace(self.path)
            return True, tr("设置已保存。")
        except OSError:
            try:
                if next_path.is_file():
                    next_path.unlink()
            except OSError:
                pass
            return False, tr("设置仅本次会话生效；配置文件暂时无法写入。")

    def set_value(self, key: str, value: bool | int | str) -> SettingChange:
        definition = self.definitions.get(key)
        if definition is None:
            return SettingChange(False, tr("未知设置项。"))
        normalized = self._normalize(definition, value)
        if normalized != value:
            return SettingChange(False, tr("设置值无效。"))
        if self.values[key] == normalized:
            return SettingChange(False, tr("设置没有变化。"))
        self.values[key] = normalized
        self.touched.add(key)
        persisted, message = self._persist()
        return SettingChange(True, message, persisted)

    def adjust(self, key: str, delta: int) -> SettingChange:
        definition = self.definitions.get(key)
        if definition is None:
            return SettingChange(False, tr("未知设置项。"))
        current = self.values[key]
        if definition.setting_type is SettingType.BOOL:
            return self.set_value(key, not bool(current))
        if definition.setting_type is SettingType.ENUM:
            choices = definition.choices
            index = choices.index(str(current))
            return self.set_value(key, choices[(index + delta) % len(choices)])
        if definition.setting_type is SettingType.INT:
            target = int(current) + delta * definition.step
            if definition.minimum is not None:
                target = max(definition.minimum, target)
            if definition.maximum is not None:
                target = min(definition.maximum, target)
            return self.set_value(key, target)
        if definition.setting_type is SettingType.ACTION:
            return SettingChange(False, tr("此项需要按 Enter 确认。"))
        return SettingChange(False, tr("该设置需要捕获一个按键。"))

    def capture_key(self, key: str, candidate: str) -> SettingChange:
        definition = self.definitions.get(key)
        if definition is None or definition.setting_type is not SettingType.KEY_BIND:
            return SettingChange(False, tr("该设置不是按键绑定。"))
        candidate = candidate.lower().strip()
        if not candidate:
            return SettingChange(False, tr("不能绑定空按键。"))
        issue = self._keybind_issue(key, candidate)
        if issue is not None:
            return SettingChange(False, issue)
        return self.set_value(key, candidate)


def format_setting_value(definition: SettingDef, value: bool | int | str) -> str:
    if definition.formatter is not None:
        return definition.formatter(value)
    if definition.setting_type is SettingType.BOOL:
        return tr("开启") if value else tr("关闭")
    return str(value)
