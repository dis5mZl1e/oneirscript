"""语句编译与能力注册（语法核心版 §5、§7.1）。

三种基础句式：持有句、行动句、反应句。效果权威是语句，不是「装上了」。
未完成或不合法的句子标为「未成句」：词块继续占地，但不获得旧装备效果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .board import EquipmentBoard, Placement
from .links import MAX_EQUIPMENT, MAX_NODES, ReactPath, compile_react_paths
from .senses import Sense, resolve
from .reading import scan, clauses
from .prose import complete_sentence, reaction_phrase, word_phrase
from .positional import compile_formation
from .roles import damage_norm, resolve_role
from ..i18n import tr

ACTIVE = "生效"
DORMANT = "备用"
PENDING = "待触发"
UNFORMED = "未成句"
SATISFIED = "条件未满足"


@dataclass(frozen=True)
class Ability:
    effect: str
    power: int
    power_secondary: int
    instance_id: str
    definition_id: str
    source: str  # hold | act
    sentence_id: str
    text: str
    profile: tuple[tuple[str, object], ...] = ()


@dataclass
class Sentence:
    sentence_id: str
    kind: str  # hold | act | react
    text: str
    status: str
    reason: str = ""
    instance_ids: tuple[str, ...] = ()
    abilities: tuple[Ability, ...] = ()
    cost: str = ""
    path: ReactPath | None = None
    # 中文句子生成器的着色片段 [(text, role)]；role ∈ sentence_prose.FRAGMENT_ROLES。
    fragments: tuple[tuple[str, str], ...] = ()
    # 与 fragments 按位对齐；记录片段来自装备实例或盘面功能词的位置。
    fragment_sources: tuple[tuple[str, ...], ...] = ()
    # 需要展开阅读的装备效果说明，不混入可复用的短句正文。
    details: tuple[str, ...] = ()
    # 这条显示句合并自哪些盘面行；行号保留为 0-based 编译坐标。
    source_rows: tuple[int, ...] = ()
    # §15 共用事实/输出契约；compare=False 让纯编译结果仍可跨语言比较。
    contract: Any = field(default=None, compare=False, repr=False)


@dataclass
class CompiledBoard:
    sentences: list[Sentence] = field(default_factory=list)
    abilities: list[Ability] = field(default_factory=list)
    react_paths: list[ReactPath] = field(default_factory=list)
    read_order: tuple[str, ...] = ()
    text: str = ''

    def contributions(self, effect: str) -> list[tuple[int, str]]:
        return [
            (ability.power, ability.instance_id)
            for ability in self.abilities
            if ability.effect == effect
        ]

    def secondaries(self, effect: str) -> list[tuple[int, str]]:
        return [
            (ability.power_secondary, ability.instance_id)
            for ability in self.abilities
            if ability.effect == effect
        ]

    def instances_with_effect(self, effect: str) -> set[str]:
        return {a.instance_id for a in self.abilities if a.effect == effect}

    def effect_ids(self) -> set[str]:
        return {a.effect for a in self.abilities if a.effect}


def _sense_of(placement: Placement) -> Sense:
    return resolve(placement.definition_id, placement.sense_id)


def semantics_of_placement(placement: Placement) -> frozenset:
    return _sense_of(placement).semantics if placement.sentence_written else frozenset()


def compile_board(board: EquipmentBoard, item_names: dict[str, str] | None = None) -> CompiledBoard:
    """把盘面编译成语句与已注册能力。纯函数：不触碰世界、RNG 或资源。"""
    if board.schema_version >= 3:
        from .projection import project
        from .syntax import column_roles
        return project(compile_formation(
            board, column_roles=column_roles(getattr(board, 'syntax', 'zh'))))
    item_names = item_names or {}
    compiled = CompiledBoard()
    focus = board.focus_instance_id
    ordered = [t.value for t in scan(board) if isinstance(t.value, Placement)]
    compiled.read_order = tuple(p.instance_id for p in ordered)

    for placement in ordered:
        current = _sense_of(placement)
        name = item_names.get(placement.instance_id, placement.definition_id)
        phrase = word_phrase(placement, current, focus, item_names)
        if not placement.sentence_written:
            compiled.sentences.append(Sentence(
                sentence_id=f"hold:{placement.instance_id}",
                kind="hold" if current.kind != "act" else "act",
                text=phrase,
                status=UNFORMED,
                reason=tr('这个念头还没有写下，暂不影响梦境。'),
                instance_ids=(placement.instance_id,),
            ))
            continue
        if current.kind == "node":
            compiled.sentences.append(Sentence(
                sentence_id=f"node:{placement.instance_id}",
                kind="hold",
                text=phrase,
                status=ACTIVE,
                reason=tr('借用它的含义来联想，原本的装备效果暂时放下。'),
                instance_ids=(placement.instance_id,),
            ))
            continue
        if current.kind == "act":
            if placement.instance_id != focus:
                compiled.sentences.append(Sentence(
                    sentence_id=f"act:{placement.instance_id}",
                    kind="act",
                    text=phrase,
                    status=DORMANT,
                    reason=tr('收着备用，切换握持后才用它攻击。'),
                    instance_ids=(placement.instance_id,),
                ))
                continue
            sentence = Sentence(
                sentence_id=f"act:{placement.instance_id}",
                kind="act",
                text=phrase,
                status=ACTIVE,
                instance_ids=(placement.instance_id,),
                cost=tr('攻击沿用这件武器的消耗'),
            )
            if current.effect:
                ability = Ability(
                    effect=current.effect, power=current.power,
                    power_secondary=current.power_secondary,
                    instance_id=placement.instance_id,
                    definition_id=placement.definition_id, source="act",
                    sentence_id=sentence.sentence_id, text=phrase,
                )
                sentence.abilities = (ability,)
                compiled.abilities.append(ability)
            compiled.sentences.append(sentence)
            continue
        sentence = Sentence(
            sentence_id=f"hold:{placement.instance_id}",
            kind="hold",
            text=phrase,
            status=ACTIVE,
            instance_ids=(placement.instance_id,),
            cost=tr('持续生效，不额外消耗想象力'),
        )
        if current.effect:
            ability = Ability(
                effect=current.effect, power=current.power,
                power_secondary=current.power_secondary,
                instance_id=placement.instance_id,
                definition_id=placement.definition_id, source="hold",
                sentence_id=sentence.sentence_id, text=phrase,
            )
            sentence.abilities = (ability,)
            compiled.abilities.append(ability)
        compiled.sentences.append(sentence)

    compiled.react_paths = compile_react_paths(board, semantics_of_placement)
    from .board import PIECE_SPECS

    for path in compiled.react_paths:
        spec = PIECE_SPECS[path.terminal_piece or ""]
        missing = spec.requires and spec.requires not in path.semantics
        missing_meaning = spec.requires if missing else None
        if path.deferred and not missing:
            outputs = [PIECE_SPECS[node[1]] for node in path.continuation]
            if not any(output_allowed(board, node, path.semantics) for node in path.continuation):
                missing = True
                missing_meaning = outputs[0].requires if outputs else spec.requires
        if not path.deferred and not output_allowed(board, ('piece', path.terminal_piece, *path.terminal), path.semantics):
            missing = True
            missing_meaning = spec.requires if spec.requires not in path.semantics else '照'
        compiled.sentences.append(Sentence(
            sentence_id=f"react:{path.endpoint}:{path.terminal}",
            kind="react",
            text=reaction_phrase(path, board),
            status=SATISFIED if missing else PENDING,
            reason=tr('这一分句缺少「{meaning}」的意象，联想还不能发生。', meaning=tr(missing_meaning)) if missing else "",
            instance_ids=tuple(n[1] for n in path.nodes if n[0] == "item"),
            cost=reaction_cost(path),
            path=path,
        ))
    parts = []
    for clause in clauses(board):
        ids = {t.node[1] for t in clause if t.node[0] == 'item'}
        nodes = {t.node for t in clause}
        parts.extend(s.text for s in compiled.sentences if s.kind != 'react'
                     and s.instance_ids[0] in ids)
        parts.extend(s.text for s in compiled.sentences if s.kind == 'react' and s.status == PENDING
                     and ('piece', s.path.terminal_piece, *s.path.terminal) in nodes)
    compiled.text = complete_sentence(parts)
    return compiled


COMPILE_LIMITS = {"max_nodes": MAX_NODES, "max_equipment": MAX_EQUIPMENT}


def output_allowed(board, node, semantics):
    from .board import PIECE_SPECS
    spec = PIECE_SPECS[node[1]]
    if spec.requires and spec.requires not in semantics:
        return False
    piece = next((p for p in board.pieces if (p.piece_id, p.x, p.y) == node[1:]), None)
    return not (piece and piece.destination_policy == 'visible_enemy'
                and piece.piece_id in ('spark', 'ember', 'voice') and '照' not in semantics)


def feedback_specs(path):
    from .board import PIECE_SPECS
    return [PIECE_SPECS[node[1]] for node in path.continuation] if path.deferred else [PIECE_SPECS[path.terminal_piece]]


def reaction_cost(path):
    from .board import PIECE_SPECS
    specs = feedback_specs(path)
    cost = max((spec.cost for spec in specs), default=0)
    cooldown = max((spec.cooldown for spec in specs), default=0)
    if path.deferred:
        return tr('等待 {delay} 回合；释放时想象力 {cost} · 共享冷却 {turns} 回合',
                  delay=PIECE_SPECS[path.terminal_piece].delay, cost=cost, turns=cooldown)
    return tr('想象力 {cost} · 共享冷却 {turns} 回合', cost=cost, turns=cooldown)


def board_signature(board: EquipmentBoard) -> Any:
    """布局指纹：用于缓存失效（预览不推进模拟，只重算派生图）。"""
    return repr(board.to_dict())
