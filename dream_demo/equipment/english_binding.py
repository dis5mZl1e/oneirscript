"""§15 第二批：英文功能词的结合方向（前附／后附／词形／从句）。

中文功能词（和／或者／如果／否则／把／被／向／从／的／地／只／再）在英文里
并不是一一对应的"词"，而是**结合方向**不同的成分：有的前附在动词前（Only、
When hurt by），有的后附成介词短语（with／from／at），有的改变主语或宾语位置
（WITH 把……交给行为、ON 把左侧设备变成受击响应），有的整句另起（IF／ELSE／OR）。

这个模块只描述**语序与附着方向**，不新增任何机制。机制仍然由
``equipment.relations`` 与 ``equipment.grammar`` 决定；这里只决定同一批事实
在英文里以什么顺序、用什么功能词连起来。中文语序的措辞由
``sentence_prose`` 的中文分支负责，两者共享 ``core.sentence_contract`` 的事实。

三条不变量（改这块之前先看）：

1. 一个功能词只能有一个槽位与一个方向，重复登记即报错——否则同一份事实在
   不同句子里会被拼成两种语序，审校无从下手。
2. 槽位顺序是**英文语序**，不是中文语序：中文可以"以轻快节拍地攻击"，英文
   必须"Strike … swiftly"。所以槽位表不随 ``board.syntax`` 变化——句法只改
   盘面列角色（谁占哪一列），不改目标语言的语序。
3. 组合只做排序与拼接，不读取数值、不重新抽取物品、不消耗随机序列。
"""
from __future__ import annotations

from dataclasses import dataclass

# 英文语序的槽位，从句子最前到最末。restriction 与 clause 在动词之前，
# repetition 落在句末；instrument/manner/origin/coordinate 依次后附。
SLOTS = (
    "clause",        # IF / ELSE / OR：整句另起的分句
    "restriction",   # ONLY：动词之前的限定
    "predicate",     # 动词 + 宾语 + 目标
    "instrument",    # OF：with …
    "manner",        # BY：swiftly / with a sharp edge
    "origin",        # FROM：from …
    "direction",     # TO：at …
    "coordinate",    # AND：together with …
    "repetition",    # AGAIN：again
)
_SLOT_INDEX = {slot: index for index, slot in enumerate(SLOTS)}

DIRECTIONS = ("before", "after", "form", "clause")


@dataclass(frozen=True)
class EnglishBinding:
    """一个功能词在英文句里的落点。``template`` 用 ``{x}`` 占位。"""

    word_id: str
    operator: str
    slot: str
    direction: str
    template: str

    def __post_init__(self) -> None:
        if self.slot not in _SLOT_INDEX:
            raise ValueError(f"{self.word_id}: unknown English slot {self.slot}")
        if self.direction not in DIRECTIONS:
            raise ValueError(f"{self.word_id}: unknown attachment {self.direction}")
        if self.direction == "form" and "{x}" not in self.template:
            raise ValueError(f"{self.word_id}: a word-form binding needs a placeholder")

    def render(self, value: str = "") -> str:
        text = self.template.replace("{x}", str(value or "").strip())
        return " ".join(text.split())


_BINDINGS = (
    # 并列：两侧共同构成一次行动 → 后附并列短语。
    EnglishBinding("word_and", "coordinate", "coordinate", "after", "together with {x}"),
    # 候选：一句里只说"二者之一"，不并列执行。
    EnglishBinding("word_or", "alternative", "clause", "clause",
                   "Otherwise, you may choose {x}"),
    EnglishBinding("word_if", "conditional", "clause", "clause", "If {x}"),
    EnglishBinding("word_else", "alternative_condition", "clause", "clause", "Otherwise"),
    # 把：载荷成为动词的宾语（"Imprint a mark on the target"），所以是前附。
    EnglishBinding("word_ba", "disposal", "predicate", "before", "{x}"),
    # 被：左侧设备成为受击响应的主语，右侧决定触发类型 → 前附原因状语。
    EnglishBinding("word_bei", "passive", "clause", "before", "When hurt by {x}"),
    EnglishBinding("word_toward", "direction", "direction", "after", "at {x}"),
    EnglishBinding("word_from", "origin", "origin", "after", "from {x}"),
    # 的：属性来源，英文固定为 with 引导的工具短语。
    EnglishBinding("word_de", "attribution", "instrument", "after", "with {x}"),
    # 地：行为方式，英文走副词或方式短语，位置在工具短语之后。
    EnglishBinding("word_de_manner", "manner", "manner", "after", "{x}"),
    EnglishBinding("word_only", "restriction", "restriction", "before", "Only"),
    EnglishBinding("word_again", "repetition", "repetition", "after", "again"),
)

ENGLISH_BINDINGS = {binding.word_id: binding for binding in _BINDINGS}
if len(ENGLISH_BINDINGS) != len(_BINDINGS):
    raise ValueError("duplicate English binding: one function word owns one slot")

# operator → 绑定。多个功能词共用同一 operator 时取第一个（当前没有重复）。
_BY_OPERATOR: dict[str, EnglishBinding] = {}
for _binding in _BINDINGS:
    _BY_OPERATOR.setdefault(_binding.operator, _binding)


def binding_for(word_id: str = "", operator: str = "") -> EnglishBinding | None:
    """按功能词 id 或关系算子取绑定；都没有时返回 ``None``（保持原文直陈）。"""
    if word_id and word_id in ENGLISH_BINDINGS:
        return ENGLISH_BINDINGS[word_id]
    return _BY_OPERATOR.get(str(operator or ""))


def slot_index(slot: str) -> int:
    try:
        return _SLOT_INDEX[slot]
    except KeyError:
        raise ValueError(f"unknown English slot: {slot}") from None


def order_phrases(entries) -> list:
    """把 ``(slot, text)`` 按英文槽位排序；同槽位保持登记顺序（稳定排序）。"""
    return [text for _, text in sorted(entries, key=lambda entry: slot_index(entry[0]))]


def compose(predicate: str = "", phrases=(), clauses=()) -> str:
    """按英文语序拼一整句。

    ``clauses`` 是整句另起的分句（IF／ELSE／When hurt by …），``phrases`` 是
    ``(slot, text)`` 对。``restriction`` 落在动词之前，``repetition`` 落在句末，
    其余按 ``SLOTS`` 顺序后附——排序只依赖绑定表，不依赖中文语序。
    """
    ordered = sorted(phrases, key=lambda entry: slot_index(entry[0]))
    prefix = [text for text in clauses if text]
    rest = [text for slot, text in ordered if slot == "restriction" and text]
    if rest and predicate:
        # 「只」是动词之前的限定词，谓语首字母必须落下。
        predicate = predicate[:1].lower() + predicate[1:]
    prefix += rest
    body = [predicate] if predicate else []
    body += [text for slot, text in ordered
             if slot not in ("restriction", "repetition") and text]
    body += [text for slot, text in ordered if slot == "repetition" and text]
    text = " ".join(part for part in prefix + body if part).strip()
    return " ".join(text.split())
