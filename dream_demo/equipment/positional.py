"""Pure row compiler for fixed 8×6 position grammar.

The output describes possibilities, never current world eligibility. Runtime
must filter rows by the actual action/event before aggregating their sources.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from ..data.items import ITEM_DEFINITIONS
from .board import EquipmentBoard, piece_cells
from .function_words import FUNCTION_WORDS
from .relations import (SyntaxRelation, _manner_matches, compile_relational_row,
                        enforce_restriction_scope)
from .roles import (ACTION_MODIFIER_EFFECTS, BASIC_WORDS, COLUMN_ROLES,
                    DamageSource, FEEDBACK_FROM_MODIFIER, RoleResponse,
                    WARD_EFFECTS, is_weapon, melee_increment, resolve_role)


@dataclass(frozen=True)
class Voice:
    x: int
    y: int
    instance_id: str
    definition_id: str
    response: RoleResponse


@dataclass(frozen=True)
class Predicate:
    kind: str
    event: str = ""
    threshold: int = 0
    source_id: str = ""
    negated: bool = False
    children: tuple[Predicate, ...] = ()


@dataclass(frozen=True)
class Contract:
    instance_id: str
    definition_id: str
    effect: str
    power: int
    secondary: int = 0
    condition: Predicate | None = None
    row: int = 0
    profile: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True)
class RowSentence:
    row: int
    status: str = "dormant"
    reason: str = "缺少行为"
    kind: str = ""
    opcode: str = ""
    event: str = ""
    instance_ids: tuple[str, ...] = ()
    source_id: str = ""
    operand_type: str = ""
    condition: Predicate | None = None
    action_profile: tuple[tuple[str, object], ...] = ()
    action_modes: tuple[str, ...] = ()
    consumes_source: bool = False
    damage_sources: tuple[DamageSource, ...] = ()
    feedback_opcodes: tuple[str, ...] = ()
    contracts: tuple[Contract, ...] = ()
    voices: tuple[Voice, ...] = ()
    relations: tuple[SyntaxRelation, ...] = ()
    action_modifiers: tuple[tuple[str, str, int], ...] = ()
    alternatives: tuple[RowSentence, ...] = ()
    branch_group: str = ''
    branch_key: str = ''
    guard_members: tuple[str, ...] = ()
    target_kind: str = ''
    # 「被」的被动响应：只在该类型创伤实际落账时触发（hurt 事件过滤）。
    hurt_kind: str = ''


@dataclass(frozen=True)
class FormationResult:
    valid: bool
    rows: tuple[RowSentence, ...]
    voices: tuple[Voice, ...]
    diagnostics: tuple[str, ...] = ()
    semantic_signature: tuple = ()

    @property
    def nodes(self) -> tuple[RowSentence, ...]:
        def walk(row):
            yield row
            for child in row.alternatives:
                yield from walk(child)
        return tuple(node for row in self.rows for node in walk(row))

    @property
    def clauses(self) -> tuple[RowSentence, ...]:
        return tuple(row for row in self.nodes if not row.alternatives)

    @property
    def actions(self) -> tuple[RowSentence, ...]:
        return tuple(row for row in self.clauses if row.status == 'ready' and row.kind == 'action')

    @property
    def alternative_members(self) -> frozenset[str]:
        return frozenset(iid for row in self.nodes
                         if any(relation.operator == 'alternative' for relation in row.relations)
                         for iid in row.instance_ids)

    @property
    def reactions(self) -> tuple[RowSentence, ...]:
        members = self.alternative_members
        return tuple(r for r in self.clauses if r.status == "ready" and r.kind == "reaction"
                     and not members.intersection(r.instance_ids))

    @property
    def contracts(self) -> tuple[Contract, ...]:
        # Conditions remain part of the identity: runtime must check them.
        unique = {}
        members = self.alternative_members
        for row in self.clauses:
            for contract in row.contracts:
                if contract.instance_id in members:
                    continue
                key = (contract.instance_id, contract.effect, contract.condition)
                unique.setdefault(key, contract)
        return tuple(unique.values())


def _compile_row(index: int, voices: tuple[Voice, ...]) -> RowSentence:
    by_column = {v.x: v for v in voices}
    verb = by_column.get(4)
    source = by_column.get(1)
    operand = by_column.get(5)
    condition_voice = by_column.get(0)
    predicate = None
    if condition_voice:
        response = condition_voice.response
        predicate = Predicate(response.condition_kind, response.event,
                              response.secondary, condition_voice.instance_id)
    row = RowSentence(index, condition=predicate, voices=voices)
    if not verb:
        return row
    vr = verb.response
    payload = operand.response.payload_type if operand else ""
    carrier = source or operand
    if vr.kind == "generic":
        if carrier is None:
            return replace(row, reason="缺少真实载体或效果载荷")
        definition = ITEM_DEFINITIONS.get(carrier.definition_id, {})
        if vr.opcode in ("cover", "maintain"):
            runtime_contract_gear = bool(
                definition.get("runtime_primary_effect")
                or definition.get("runtime_feedback_effect"))
            if ((is_weapon(definition) and not runtime_contract_gear)
                    or carrier.response.consumes_source):
                return replace(row, reason="这个载体不能形成持续契约")
            natural = resolve_role(carrier.definition_id, "verb")
            if natural is None or natural.kind != "contract":
                return replace(row, reason="这个行为不能改成持续契约")
            if vr.opcode == "cover" and definition.get("effect") not in WARD_EFFECTS:
                return replace(row, reason="披覆需要护持载荷")
            vr = replace(carrier.response, role="verb", kind="contract", opcode=vr.opcode)
            verb = replace(carrier, x=4, response=vr)
        else:
            resolved = resolve_role(carrier.definition_id, "verb", payload or None)
            if resolved is None:
                return replace(row, reason="载体没有可用行为")
            vr = resolved
            verb = replace(carrier, x=4, response=vr)
    else:
        resolved = resolve_role(verb.definition_id, "verb", payload or None)
        if resolved:
            vr = resolved
    if vr.kind == "reaction" and vr.opcode == "ignite" and payload not in ("", "heat"):
        return replace(row, reason="点燃不接受这种载荷")
    if vr.kind == "contract" and operand and payload not in (
        "", "buff", vr.payload_type, "ward" if vr.effect in WARD_EFFECTS else vr.payload_type,
    ):
        return replace(row, reason="持续行为与对象类型不相容")

    ids = tuple(dict.fromkeys(v.instance_id for v in voices
                             if v.definition_id in ITEM_DEFINITIONS))
    contracts: dict[tuple[str, str], Contract] = {}
    damage: dict[str, DamageSource] = {}
    feedback = []
    # 2026-10-14 修饰位差异化：行为行直接收集同行 2/3 列的裸修饰（旧版只有
    # 「的/地」功能词能挂 action_modifiers，裸摆放的修饰列零消费）。相容
    # 家族与「地」共用 _manner_matches，两种摆法语义一致；同一实体不重复
    # 计入（与「同一实体不能通过自身孔洞建立修饰关系」同口径）。
    bare_modifiers: dict[tuple[str, str], tuple[str, str, int, str]] = {}
    for voice in voices:
        if voice.response.role == "condition":
            continue
        definition = ITEM_DEFINITIONS.get(voice.definition_id, {})
        if is_weapon(definition) and voice.response.payload_type in ("", "carrier", "cut"):
            value = melee_increment(definition)
            if value:
                damage[voice.instance_id] = DamageSource(
                    voice.instance_id, voice.definition_id, value)
        if vr.kind == "contract":
            effect = voice.response.effect
            runtime_contract_gear = bool(
                definition.get("runtime_primary_effect")
                or definition.get("runtime_feedback_effect"))
            if effect and (not is_weapon(definition) or runtime_contract_gear) and (
                voice.instance_id == verb.instance_id
                or voice.response.kind in ("carrier", "payload", "modifier", "supplement")
            ):
                contracts[(voice.instance_id, effect)] = Contract(
                    voice.instance_id, voice.definition_id, effect,
                    voice.response.power, voice.response.secondary, predicate, index,
                    voice.response.profile)
        elif (vr.kind == "action" and voice.x in (2, 3)
              and voice.instance_id != verb.instance_id
              and voice.response.kind == "modifier"
              and voice.response.opcode in ACTION_MODIFIER_EFFECTS
              and _manner_matches(voice.response.opcode, vr.opcode)):
            bare_modifiers[(voice.instance_id, voice.response.opcode)] = (
                voice.instance_id, voice.response.opcode,
                voice.response.power, voice.definition_id)
    action_modifiers = tuple((iid, effect, power)
                             for iid, effect, power, _d in bare_modifiers.values())
    for iid, effect, power, definition_id in bare_modifiers.values():
        opcode = FEEDBACK_FROM_MODIFIER.get(effect)
        if power > 0:
            if opcode:
                feedback.append(opcode)
            if effect == "throw_master":
                damage[iid] = DamageSource(iid, definition_id, power)
    if vr.kind == "contract" and vr.effect:
        contracts[(verb.instance_id, vr.effect)] = Contract(
            verb.instance_id, verb.definition_id, vr.effect,
            vr.power, vr.secondary, predicate, index, vr.profile)
    if vr.kind == "action" and vr.opcode in ("strike", "fire") and payload == "heat":
        feedback.append("ignite")
    elif vr.kind == "action" and vr.opcode in ("strike", "fire") and payload == "electric":
        feedback.append("shock")
    kind = vr.kind
    event = vr.event
    if predicate and predicate.kind == "event":
        if kind == "action":
            kind = "reaction"
        event = predicate.event
    return replace(
        row, status="ready", reason="", kind=kind, opcode=vr.opcode, event=event,
        instance_ids=ids, source_id=verb.instance_id, operand_type=payload,
        action_profile=vr.profile, action_modes=vr.action_modes,
        consumes_source=vr.consumes_source, damage_sources=tuple(damage.values()),
        feedback_opcodes=tuple(dict.fromkeys(feedback)),
        action_modifiers=action_modifiers,
        contracts=tuple(contracts.values()),
    )


def compile_formation(board: EquipmentBoard,
                      item_names: dict[str, str] | None = None,
                      column_roles=None) -> FormationResult:
    """Compile roles, rows and contracts without changing the board or world.

    Legacy focus/sense/enable flags are intentionally not read. Display names
    are accepted for API symmetry; localization is a separate rendering step.
    """
    roles = tuple(column_roles or COLUMN_ROLES)
    if len(roles) != len(COLUMN_ROLES) or 'verb' not in roles:
        raise ValueError('column_roles must be the eight reviewed equipment columns')
    verb_column = roles.index('verb')
    object_column = roles.index('object') if 'object' in roles else 5
    physical = board.clone()
    physical.focus_instance_id = None
    try:
        problems = physical.errors()
    except (KeyError, ValueError):
        problems = ["未知或损坏的形状"]
    signature = (
        (board.width, board.height), tuple(roles),
        tuple(sorted((p.instance_id, p.definition_id, p.shape_id,
                      p.x, p.y, p.rotation, p.shape_version) for p in board.placements)),
        tuple(sorted((p.piece_id, p.x, p.y, p.rotation) for p in board.pieces)),
        tuple(sorted((t.connector, t.x, t.y, t.rotation) for t in board.traces)),
    )
    if problems:
        return FormationResult(False, tuple(RowSentence(y, reason="盘面物理无效")
                                            for y in range(6)), (),
                               tuple(problems), signature)
    voices = []
    diagnostics = []
    for placement in board.placements:
        for x, y in sorted(placement.cells(), key=lambda point: (point[1], point[0])):
            response = resolve_role(placement.definition_id, roles[x])
            if response:
                voices.append(Voice(x, y, placement.instance_id,
                                    placement.definition_id, response))
            else:
                diagnostics.append(f"{placement.instance_id}@{x},{y}:此位置沉默")
    for piece in board.pieces:
        if piece.piece_id in FUNCTION_WORDS:
            continue  # Relation words bind constituents, never occupy a verb slot.
        if piece.piece_id not in BASIC_WORDS:
            diagnostics.append(f"{piece.piece_id}@{piece.x},{piece.y}:旧标点不参与位置语义")
            continue
        for x, y in piece_cells(piece):
            if roles[x] != "verb":
                diagnostics.append(f"{piece.piece_id}@{x},{y}:基础写法需要行为位")
                continue
            opcode = BASIC_WORDS[piece.piece_id]
            voices.append(Voice(x, y, f"word:{piece.piece_id}:{x}:{y}", "",
                                RoleResponse("verb", opcode, "generic", opcode=opcode)))
    # Resolve the declared operand branch before exposing either cell meanings
    # or sentences, so the editor and executor cannot disagree about the verb.
    operands = {v.y: v.response.payload_type for v in voices if v.x == object_column}
    resolved_voices = []
    for voice in voices:
        if voice.x == verb_column and voice.definition_id:
            response = resolve_role(voice.definition_id, "verb", operands.get(voice.y))
            if response:
                voice = replace(voice, response=response)
        resolved_voices.append(voice)
    ordered = tuple(sorted(resolved_voices, key=lambda v: (v.y, v.x, v.instance_id)))
    rows = []
    for y in range(6):
        row = _compile_row(y, tuple(v for v in ordered if v.y == y))
        words = [piece for piece in board.pieces if piece.y == y and piece.piece_id in FUNCTION_WORDS]
        if words:
            row = compile_relational_row(y, board, row, words)
        rows.append(row)
    from .conditions import compile_conditions
    rows = compile_conditions(board, tuple(rows), column_roles=roles)
    from .targets import compile_targets
    rows = compile_targets(board, rows)
    rows = enforce_restriction_scope(rows, board)
    # Expose the same relation-selected reading in the inspector and sentence.
    # Bindings, rather than the word's physical column, determine the scope.
    def annotate(row):
        modes = {}
        for relation in row.relations:
            for iid, role in relation.role_bindings:
                modes[(iid, role)] = relation.operator
        return replace(row, voices=tuple(replace(v, response=replace(
            v.response, reading=modes.get((v.instance_id, v.response.role), "default")))
            for v in row.voices), alternatives=tuple(annotate(child) for child in row.alternatives))
    rows = tuple(annotate(row) for row in rows)
    ordered = tuple(sorted((voice for row in rows for voice in row.voices),
                           key=lambda v: (v.y, v.x, v.instance_id)))
    for row in rows:
        if row.voices and row.status != "ready":
            diagnostics.append(f"第{row.row + 1}行:{row.reason}")
    return FormationResult(True, rows, ordered, tuple(diagnostics), signature)
