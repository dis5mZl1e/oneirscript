"""篡改系统的冻结数据模型（规格 §3、§10；实施计划「共享接口约定」）。

只依赖标准库：不导入 GameState、内容表或界面模块，界面与核心共用这里的身份。

身份规则（规格 §3.1、§4.5）：位置用片段 ID 表达，不保存屏幕行列，也不保存
汉字下标；各语言可以有不同的片段顺序与插入点，但同一个 slot_id 在所有语言里
指向同一处合法变化。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional

#: 玩家可见档位（规格 §7.1）；概率只进开发配置与调试信息。
#: 2026-10-22 平衡修复：风险几乎不构成约束（五档期望损失 0.08–2.11 价值点，
#: 对照单次篡改 5–21 点），概率整体上调为 0.12／0.22／0.36／0.55／0.75。
RISK_TIERS: tuple[tuple[int, int, str, float], ...] = (
    (0, 19, "微弱", 0.12),
    (20, 39, "不稳", 0.22),
    (40, 59, "扭曲", 0.36),
    (60, 79, "错乱", 0.55),
    (80, 100, "失序", 0.75),
)

CHAOS_MIN = 0
CHAOS_MAX = 100
#: 每累计这么多「已支付的有效行动耗时」降低 1 点混乱度（规格 §6.2）。
CHAOS_DECAY_INTERVAL = 5.0

Operation = Literal["insert", "delete", "replace"]
Region = Literal["dialogue", "rule", "option"]


@dataclass(frozen=True)
class TextFragment:
    """一段固定正文。`fragment_id` 跨渲染、翻译与显示顺序保持稳定。"""

    fragment_id: str
    text: str


@dataclass(frozen=True)
class TamperVariant:
    """一个审核过的完整变体：各语言片段 + 对既有交互结果的功能补丁。"""

    variant_id: str
    fragments_by_language: Mapping[str, tuple[TextFragment, ...]]
    option_patches: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    #: 确认前必须读到的实际效果说明（规格 §8.4）。
    effect_note_by_language: Mapping[str, str] = field(default_factory=dict)
    #: 可选的简短选项名称：对白改换所得时同步显示，不参与功能补丁或库存身份。
    option_label_by_language: Mapping[str, str] = field(default_factory=dict)

    def fragments(self, language: str) -> tuple[TextFragment, ...]:
        return self.fragments_by_language.get(language) or self.fragments_by_language["zh"]

    def effect_note(self, language: str) -> str:
        return self.effect_note_by_language.get(language) or self.effect_note_by_language.get("zh", "")


@dataclass(frozen=True)
class TamperTransition:
    """一次可以提交的合法变化（规格 §3.3：每次只提交一处）。"""

    transition_id: str
    from_variant: str
    to_variant: str
    operation: Operation
    slot_id: str
    word_id: Optional[str]
    imagination_cost: int
    chaos_delta: int
    #: 整句润顺（2026-10-12 玩家反馈）：改写不局限于机械拼插的词，可以按原意
    #: 调整整句使语气通顺。置真时校验器不再逐字比对片段，只要求变体正文仍
    #: 保留插入词本身（删除类改写要求删词后的意思确实消失）。
    rewrite: bool = False


@dataclass(frozen=True)
class TamperDefinition:
    """一处可篡改文本：所属对象、入口区域、变体图与位置定义。"""

    text_id: str
    target_kind: Literal["npc", "event"]
    definition_id: str
    region: Region
    option_id: str
    initial_variant: str
    variants: tuple[TamperVariant, ...]
    transitions: tuple[TamperTransition, ...]
    slots_by_language: Mapping[str, Mapping[str, Mapping[str, Any]]]
    content_version: int = 1

    def variant(self, variant_id: str) -> TamperVariant | None:
        for entry in self.variants:
            if entry.variant_id == variant_id:
                return entry
        return None

    def transition(self, transition_id: str) -> TamperTransition | None:
        for entry in self.transitions:
            if entry.transition_id == transition_id:
                return entry
        return None

    def slots(self, language: str) -> Mapping[str, Mapping[str, Any]]:
        return self.slots_by_language.get(language) or self.slots_by_language["zh"]


@dataclass(frozen=True)
class TamperWord:
    """首批固定词汇（规格 §3.2）。篡改词表与装备词表各自独立注册。"""

    word_id: str
    label_by_language: Mapping[str, str]
    insert_by_language: Mapping[str, str]
    imagination_cost: int
    chaos_delta: int

    def label(self, language: str) -> str:
        return self.label_by_language.get(language) or self.label_by_language["zh"]

    def insert_text(self, language: str) -> str:
        return self.insert_by_language.get(language, "")


@dataclass(frozen=True)
class TamperTarget:
    """改文归属的实例身份（规格 §8.1、§8.2）。"""

    kind: Literal["npc", "event"]
    definition_id: str
    instance_uid: str

    def record_key(self, text_id: str) -> str:
        return encode_record_key(self.instance_uid, text_id)


@dataclass(frozen=True)
class TamperRequest:
    """一次提交请求；`expected_version` 用来拒绝过期预览。"""

    target: TamperTarget
    text_id: str
    transition_id: str
    expected_version: int
    request_id: str


@dataclass(frozen=True)
class TamperPreview:
    """确认前的可见信息：代价、混乱度与档位（不揭示具体负面事件）。"""

    request: TamperRequest
    before_text: str
    after_text: str
    imagination_cost: int
    chaos_delta: int
    chaos_after: int
    risk_tier: str
    available: bool
    reason: str
    effect_note: str = ""
    risk_note: str = ""
    # §15：确认前预览的共用事实/输出契约；不参与相等比较，不写存档。
    contract: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class RiskOutcome:
    """已确定的风险结果；可序列化，不持有实体引用。"""

    event_id: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class HitSpan:
    """屏幕上的一段命中范围；列范围左闭右开（规格 §4.5）。"""

    text_id: str
    slot_id: str
    row: int
    start_col: int
    end_col: int


def encode_record_key(instance_uid: str, text_id: str) -> str:
    """`tamper_records` 的键：JSON 二元数组的紧凑编码，避免手拼分隔符碰撞。"""
    import json

    return json.dumps([instance_uid, text_id], ensure_ascii=False, separators=(",", ":"))


def decode_record_key(key: str) -> tuple[str, str]:
    import json

    pair = json.loads(key)
    return str(pair[0]), str(pair[1])
