"""Grammatical tokens, deliberately independent of legacy feedback pieces.

The registry defines binding requirements, not world effects. Execution must
use the typed relations and budgets of the participating real equipment.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionWord:
    word_id: str
    label: str
    category: str
    operator: str
    binding: str
    detail: str
    english_label: str = ""
    english_token: str = ""
    english_detail: str = ""

    @property
    def cells(self) -> tuple[tuple[int, int], ...]:
        return tuple((x, 0) for x in range(len(self.label)))

    def label_for(self, language: str) -> str:
        return self.english_label if language == "en" and self.english_label else self.label

    def detail_for(self, language: str) -> str:
        return self.english_detail if language == "en" and self.english_detail else self.detail


_WORDS = (
    FunctionWord("word_and", "和", "conjunction", "coordinate", "compatible_pair",
                 "让左右两侧共同构成一次行动；同一次行动不会重复计算消耗。",
                 "AND", "&", "Both sides form one action; that action does not pay twice."),
    FunctionWord("word_or", "或者", "conjunction", "alternative", "candidate_pair",
                 "每次只能选择一侧的行为；两侧不会同时生效。",
                 "OR", "OR", "Choose one side each time; both sides never take effect together."),
    FunctionWord("word_if", "如果", "conjunction", "conditional", "predicate_clause",
                 "满足关联装备提供的条件时，才执行后面的行为；“如果”本身不提供条件。",
                 "IF", "IF", "Run the action only when the linked equipment's condition holds; IF itself supplies no condition."),
    FunctionWord("word_else", "否则", "conjunction", "alternative_condition", "conditional_clause",
                 "对应的“如果”条件不满足时才执行这里的行为；行动资源不足不会转入“否则”分支。",
                 "ELSE", "ELSE", "Run this branch only when the matching IF condition is false; insufficient resources do not fall through."),
    FunctionWord("word_ba", "把", "preposition", "disposal", "patient_action",
                 "把后面的内容交给行为作用，例如把刀痕印在目标上，或把瓶中材料喷向目标。",
                 "WITH", "WI", "Hand the payload to the action, such as imprinting a mark or spraying material from a bottle."),
    FunctionWord("word_bei", "被", "preposition", "passive", "patient_agent",
                 "左侧装备改为受击响应，右侧装备决定响应哪类创伤；相应创伤实际结算后才会触发。",
                 "ON", "ON", "Turn the left equipment into a hit response; the right side selects the damage kind that triggers it."),
    FunctionWord("word_toward", "向", "preposition", "direction", "action_target",
                 "指定行动瞄准的目标；原有射程和视线限制仍然有效。",
                 "TO", "TO", "Set the action's target; existing range and line-of-sight limits still apply."),
    FunctionWord("word_from", "从", "preposition", "origin", "material_action",
                 "从后面的容器取用已有液体或气体，再交给对应装备喷射；容器为空时不会凭空产生材料。",
                 "FROM", "FR", "Draw existing liquid or gas from the container for the linked action; empty containers create nothing."),
    FunctionWord("word_de", "的", "particle", "attribution", "property_head",
                 "把前面装备切换为属性来源，修饰后面的行为：刀锋增加锋利，余温或静电附加命中反馈，节拍让本次行为更快；属性来源不会额外执行自身行为。",
                 "OF", "OF", "Treat the left equipment as a property source for the action; it does not perform a second action."),
    FunctionWord("word_de_manner", "地", "particle", "manner", "manner_action",
                 "把前面装备切换为行为方式，例如用饰品的轻快节拍缩短后续攻击耗时；方式只修饰关联行为，不支持的组合无法成句。",
                 "BY", "BY", "Turn the left equipment into a manner for the action; unsupported combinations cannot form a sentence."),
    FunctionWord("word_only", "只", "adverb", "restriction", "selected_action",
                 "只让选定的那件事发生；同句里用于修饰或附加效果的其他词义这一回都不参与。",
                 "ONLY", "OL", "Only the selected action happens; other modifiers or feedback in the row do not participate this time."),
    FunctionWord("word_again", "再", "adverb", "repetition", "completed_action",
                 "前一次确实造成创伤后，才会追加一次；追加前会重新检查资源，两次共用本次行动的消耗和创伤额度。",
                 "AGAIN", "AG", "Append one more attempt only after the first actually dealt damage; resources are rechecked and both share the budget."),
)

FUNCTION_WORDS = {word.word_id: word for word in _WORDS}
