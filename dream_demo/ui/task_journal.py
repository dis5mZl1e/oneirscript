"""任务日志面板（§14）：接下的委托在哪、缺什么、找谁交付。

数据口径：

* 只列世界记录里的任务实例（§7.1 新模板）——旧累计计数任务不进这面墙，
  它们的进度还在对话页显示，两套口径不混排；
* 「已满足项」直接用 :func:`world.tasks.status_text` 的现成一句话：面板与
  交付拒绝共用同一份状态来源，不允许文案说一套、逻辑做一套（§10.1）；
* 交付点 = 委托人所在层。跨层交付（具名代收点／派系服务台）还没落地，
  委托人不在本层时明说「回去找 TA」，不许含糊（§6.3「离开当前层前，
  任务面板说明是否可跨层交付」——现在的答案就是「不可，得回去」）。

排版输出（``journal_lines``）与右侧面板的「首行偏移 + 视窗切片」渲染约定
对齐：返回完整行列表、每行对应的条目序号（本面板只读，全部 -1）与标题行，
滚动切片由 ``panels._scrolled_panel_text`` 统一处理。模块对世界层延迟导入，
自身只依赖已入库的 i18n 与 rich。
"""
from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.text import Text

from ..i18n import tr
from .panel_fields import FIELD_COLORS as FC, field_text

_WRAP_CONSOLE = Console(legacy_windows=False)
_HEADER_STYLE = 'bold ' + FC['grammar']
_MUTED = FC['muted']
_OK = FC['effect']
_ACTIVE = "bold white"


def _layer_text(layer_key: str) -> str:
    """层键 → 可读层名：主梦是「第 N 层」，其余（梦中梦/异常键）原样。"""
    if layer_key.isdigit():
        return tr("第 {n} 层", n=int(layer_key))
    return layer_key


def journal_tasks(state: Any) -> list[dict[str, Any]]:
    """进行中的任务实例 → 展示字段（每单一条 dict，顺序按实例 UID）。"""
    from ..data.npcs import NPC_DEFINITIONS
    from ..data.quests import QUEST_DEFINITIONS
    from ..world import tasks as world_tasks

    ledger = state.world_ledger
    here = state.layer_key()
    entries: list[dict[str, Any]] = []
    for record in sorted(ledger.tasks.values(), key=lambda r: r.task_uid):
        if record.status not in ("进行中", "待交付"):
            continue  # 已结算的单从日志里消失：墙是「还欠什么」，不是账本。
        quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
        giver = ledger.actor(record.giver_uid)
        giver_kind = giver.npc_kind if giver is not None else str(quest.get("giver", ""))
        giver_definition = NPC_DEFINITIONS.get(giver_kind) or {}
        giver_name = tr(giver_definition.get("name", giver_kind))
        giver_layer = giver.layer_key if giver is not None else record.layer_key
        resolution = world_tasks.resolution(state, record)
        closed = any(giver_layer.startswith(f"R{realm}:")
                     for realm in getattr(state, "closed_realms", ()))
        if giver is None or not giver.alive or closed:
            reason = "档案缺失" if giver is None else ("已经离世" if not giver.alive else "所在位面已关闭")
            deliver = tr("交付人失联：{reason}；可放弃委托恢复名额。", reason=tr(reason))
        elif giver_layer == here:
            deliver = (tr("委托人就在本层——随时可交付。") if resolution
                       else tr("委托人在本层。"))
        else:
            deliver = tr("委托人在{place}——回去找 TA 才能交付。",
                         place=_layer_text(giver_layer))
        rewards = "／".join(
            tr(option.get("label", ""))
            for option in (quest.get("rewards") or {}).values()
            if option.get("label")
        )
        entries.append({
            "task_uid": record.task_uid,
            "abandonable": True,
            "name": tr(quest.get("name", record.definition_id)),
            "status": record.status,
            "resolved": bool(resolution),
            "status_line": world_tasks.status_text(state, record),
            "target_text": tr(quest.get("target_text", "")),
            "place": _layer_text(record.layer_key),
            "giver": giver_name,
            "deliver": deliver,
            "rewards": rewards,
        })
    return entries


def journal_lines(state: Any, *, width: int, actionable: bool = False,
                  selection: int | None = None) -> tuple[list[Text], list[int], Text]:
    """面板排版：返回（完整行列表, 每行条目序号, 标题行）。

    默认保留只读行映射；actionable=True 时，放弃行映射到 journal_actions 的 UID。
    selection 使用同一条目序号，显式标出键盘当前选中的放弃操作。
    UI 必须先确认，再通过 session 执行，排版本身不修改世界。
    """
    entries = journal_tasks(state)
    header = Text.assemble(
        (tr("任务日志"), _HEADER_STYLE),
        (f"  {len(entries)}", "white"),
    )
    lines: list[Text] = []
    row_indices: list[int] = []

    def add(line: Text, row_index: int = -1) -> None:
        for wrapped in line.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
            lines.append(wrapped)
            row_indices.append(row_index)

    from ..core.origin_course import is_course
    if not entries and not is_course(state):
        add(Text(tr("没有接下的委托。"), style=_MUTED))
        add(Text(tr("委托从对话里接——能给活的梦中人会把选项摆在明面上。"), style=_MUTED))
    for entry_index, entry in enumerate(entries):
        mark = "✓" if entry["resolved"] else "▶"
        add(Text.assemble((mark + ' ', _OK if entry['resolved'] else FC['position']),
            (entry['name'], FC['heading']), ('（'+entry['status']+'）',
                _OK if entry['resolved'] else FC['area'])))
        if entry["target_text"]:
            add(Text("    " + entry["target_text"], style=_MUTED))
        add(Text('    ') + field_text('地点', entry['place'], field='position', separator='：')
            + Text('　') + field_text('委托人', entry['giver'], field='identity', separator='：'))
        add(Text("    " + entry["deliver"], style=_OK if entry["resolved"] else _MUTED))
        add(Text("    " + entry["status_line"], style=_MUTED))
        if entry["rewards"]:
            add(Text('    ') + field_text('报酬', entry['rewards'], field='effect', separator='：'))
        selected = actionable and selection == entry_index
        add(Text(("  > " if selected else "    ")
                 + tr("放弃委托（不领取报酬，恢复名额）"),
                 style=('bold underline ' if selected else '') + FC['danger']),
            entry_index if actionable else -1)
        add(Text(""))
    checklist = realm_checklist(state)
    if checklist:
        add(Text(tr("位面下潜手续（不可放弃）"), style=_HEADER_STYLE))
        for check in checklist:
            add(Text(("✓ " if check["done"] else "□ ") + check["label"], style=FC['effect' if check['done'] else 'windup']))
    from ..core.origin_course import entries as course_entries, localized
    modules=course_entries(state)
    if modules:
        offset=len(entries)
        add(Text(tr('教学：梦的起始（不占委托名额）'),style=_HEADER_STYLE))
        add(Text(tr('新增教材与练习成长仅本层有效；N 可随时离开。'),style=_MUTED))
        statuses={'done':'已实践','pending':'待机制接入','skipped':'已跳过','todo':'待实践'}
        for index,module in enumerate(modules):
            selected=actionable and selection==offset+index
            title=('▸ ' if selected else '  ')+module['id']+' '+localized(module,'title')+' · '+tr(statuses[module['status']])
            add(Text(title,style=('bold underline ' if selected else '')+FC['effect' if module['status']=='done' else 'heading']),
                offset+index if actionable else -1)
            if selected:
                add(Text('    '+localized(module,'body'),style=FC['text']))
                if module['pending']: add(Text('    '+tr(module['pending']),style=FC['danger']))
                else: add(Text(tr('    Enter／点击选择此目标，不重置完成记录。'),style=_MUTED),offset+index)
        quest=state.tutorial.get('practice_quest')
        if quest=='active':
            uid=state.tutorial.get('practice_item_uid')
            have=any(i.instance_id==uid for i in state.inventory)
            add(Text(tr('练习委托：{status}；在物品区取练习玻璃杯，交给出口纸偶。',
                        status=tr('待交付' if have else '缺少练习玻璃杯')),style=FC['condition']))
        for key,label in course_controls(state):
            index=offset+len(modules)
            offset+=1
            add(Text(('▸ ' if actionable and selection==index else '  ')+tr(label),style=FC['grammar']),
                index if actionable else -1)
    return lines, row_indices, header


def journal_actions(state: Any) -> list[str]:
    """Action index -> stable commission UID; rebuild alongside journal_lines."""
    from ..core.origin_course import entries
    return ([entry["task_uid"] for entry in journal_tasks(state)]
            + ['course:select:'+m['id'] for m in entries(state)]
            + ['course:'+key for key,_ in course_controls(state)])


def course_controls(state):
    from ..core.origin_course import is_course
    if not is_course(state): return []
    controls=[('pause','展开／收起教学提示'),('reset','归还遗失教材／恢复练习资源'),
              ('noise','开始／重置声音练习（G 区）'),('environment','开始／重置环境练习（H 区）'),
              ('hearing','开始／重置听闻练习（G 区）'),
              ('tamper_samples','准备篡改液体样本（F 区）'),('passives','借用记忆与洞察教材（本层有效）')]
    if state.tutorial.get('practice_quest')=='active': controls.append(('abandon','放弃练习委托（可重接）'))
    return controls


def realm_checklist(state: Any) -> list[dict[str, Any]]:
    """Read current floor gate bookkeeping without initializing or mutating it."""
    realm = getattr(state, "realm_id", "")
    features = getattr(state, "realm_features", {})
    names = {"card": "借书卡", "margin": "批注", "optional": "目录机关",
             "chart": "病历夹", "queue": "叫号屏", "scene": "一处设施"}
    key = {"library_palace": "library_gate", "white_sanatorium": "hospital_gate"}.get(realm)
    if key:
        gate = features.get(key) or {}
        required = gate.get("required", ("card", "margin", "optional") if key == "library_gate"
                            else ("chart", "queue", "scene"))
        return [{"label": tr(names.get(item, item)), "done": item in gate.get("done", ()),
                 "abandonable": False} for item in required]
    if realm == "toy_memories":
        return [{"label": tr("完成本层解谜，并与守门人交谈"),
                 "done": bool(getattr(state, "realm_gate_open", False)), "abandonable": False}]
    return []
