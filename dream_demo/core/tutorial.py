"""新手引导任务系统（0 层「梦的起始」专用）。

表驱动步骤链：每一步等待「对应键位输入 + 目标实际完成」才进入下一步。
完成判定走**事件旗标**（action 成功路径埋点写入 ``state.tutorial_events``）
与几何谓词（玩家/光标坐标），不轮询全量状态；旗标在步骤推进或跳过时清空，
提前完成的后续目标可以借「连跳」一次认可（如一发射击同时完成攻击与发射步）。

本模块是纯逻辑：UI 侧每帧调用 :func:`tutorial_pump`（推进）、
:tfunc:`tutorial_card_text`（教程卡文案）与 :func:`tutorial_target_cells`
（地图高亮），Esc 跳步走 :func:`tutorial_skip_step`。n 键下潜由
``GameState.descend`` 直接收束引导，不经这里。
"""

from __future__ import annotations

from typing import Any

from ..i18n import tr
from .origin_course import COURSE_TEMPLATE_VERSION

# 步骤表：id / 标题 / 正文 / 键位徽章 / 目标短句 / 关联站点（None = 无位置目标）。
# 顺序即教学动线；最后一只玩偶步之后必然是发射步（共用两只玩偶，死一只
# 8 回合后原地重生，任何顺序都做得出「撞一下」和「打一发」）。
TUTORIAL_STEPS: tuple[dict[str, Any], ...] = (
    {
        "id": "welcome",
        "title": "梦的起始",
        "body": (
            "这里是所有梦开始的地方。\n"
            "左侧是梦境本身；右侧是意识面板——心智、清醒度与想象力，"
            "事件记录与七个页签都在那边。"
        ),
        "key": "任意键",
        "goal": "随便按一个键",
        "station": None,
    },
    {
        "id": "move",
        "title": "迈出第一步",
        "body": (
            "用方向键或小键盘移动。WASD 被派给了面板选位，不负责走路。\n"
            "走到亮起的 ◇ 上。每走一步，世界便流过一回合。"
        ),
        "key": "方向键 / 小键盘",
        "goal": "走到 ◇",
        "station": "move_target",
    },
    {
        "id": "observe",
        "title": "观察",
        "body": (
            "按 X 进入观察模式，时间会为你停住。\n"
            "用方向键把 ? 移到亮起的 ◎ 上，读一读那株草——按 ' 可以展开它的详情。"
        ),
        "key": "X",
        "goal": "用 ? 对准 ◎",
        "station": "observe_target",
    },
    {
        "id": "panel",
        "title": "意识面板",
        "body": (
            "按 Tab 打开行囊。行囊、携带意象（T）、征兆（V）、洞察（I）、"
            "观测（K）、操作（?）都列在右侧。\n"
            "面板下方那行小字，是随时可查的键位备忘。"
        ),
        "key": "Tab",
        "goal": "打开行囊",
        "station": None,
    },
    {
        "id": "talk",
        "title": "打招呼",
        "body": (
            "梦里不止你和异象。走到迎面的纸偶身边，按 E（或左键点它）开口——"
            "有的意识愿意交谈，有的只顾着追你。\n"
            "它只陪聊天，不做买卖；聊完按 Esc 收起对话。"
        ),
        "key": "E / 左键",
        "goal": "与纸偶说上一次话",
        "station": "chat_npc",
    },
    {
        "id": "strike",
        "title": "触碰即交锋",
        "body": (
            "梦里的异象需要被解决。朝旁边发亮的玩偶意识体走过去——"
            "撞上它就是一次攻击。\n"
            "它不设防，也不记仇；散开之后，过一会儿会自己重新叠好。"
        ),
        "key": "方向键（撞向目标）",
        "goal": "命中一次玩偶意识体",
        "station": "doll_melee",
    },
    {
        "id": "fire",
        "title": "发射",
        "body": (
            "你带着 3 枚聚合弹。按 F 举起投射物，再按一个方向键把它射出去。\n"
            "站到亮起的 ◆ 处，把远处那只玩偶打下来；瞄准时按 O 可以自动锁定最近的目标。"
        ),
        "key": "F → 方向键",
        "goal": "发射并命中",
        "station": "fire_from",
    },
    {
        "id": "autowalk",
        "title": "让梦带你走",
        "body": (
            "按 X 观察、再按 O 开启辅助：一条淡黄的路径会铺到 ◎ 与你之间，"
            "按 Enter 沿它走过去。\n"
            "直接用鼠标点远处同样可以——抵达 ◈ 时若踩着东西，顺手就会捡起。"
        ),
        "key": "X → O → Enter",
        "goal": "自动走到 ◈",
        "station": "autowalk_target",
    },
    {
        "id": "board_place",
        "title": "联想盘：先放一件",
        "body": (
            "教学行囊备有补丁睡衣和盐渍线圈。按 T 打开携带意象，选中一件按 Enter 拿进手里。\n"
            "方向键移动，a 放到盘上，再按 Enter 确认整理；确认后才生效。盘面逐行读词，不需要接线。"
        ),
        "key": "T → Enter 拿起 → a → Enter",
        "goal": "让盘上多留下一件装备",
        "station": None,
    },
    {
        "id": "board_rotate",
        "title": "转一转，腾出空间",
        "body": (
            "盘面只有 8×6 格，放不下时先别丢。\n"
            "在编辑器拿起一件按 R 旋转，用方向键挪位、a 放下，再放第二件并按 Enter 确认整理。旋转只改变形状。"
        ),
        "key": "拿起 → R → a → Enter",
        "goal": "旋转之后盘上至少有两件",
        "station": None,
    },
    {
        "id": "board_gate",
        "title": "给句子加条件",
        "body": (
            "把盐渍线圈摆到盘面第 1 列（条件位），水枪摆到同一行的第 5 列（行为位），按 Enter 确认整理。\n"
            "条件只约束同一行：线圈给出「事件格导电才放行」，行为命中湿润位置时才出手。按 V 读整句。"
        ),
        "key": "选装备 → Enter 拿起 → a 放下 → Enter 确认整理",
        "goal": "摆出条件位与行为位同行的成句盘面",
        "station": None,
    },
    {
        "id": "dive",
        "title": "下潜",
        "body": (
            "在更深的梦层，崩解度满 100 才允许下潜；这里不需要。\n"
            "亮起的 ▼ 只是提醒：随时按 N，离开梦的起始。下潜之后，这里不再为你重开。"
        ),
        "key": "N",
        "goal": "按 N 下潜",
        "station": "dive_mark",
    },
)


def tutorial_active(state) -> bool:
    """引导是否仍在进行。"""
    return bool(state.tutorial.get("active"))


def tutorial_step(state) -> dict[str, Any] | None:
    """当前步骤定义；引导未激活时返回 None。"""
    if state.tutorial.get('version') == COURSE_TEMPLATE_VERSION:
        from .origin_course import current
        return current(state)
    if not tutorial_active(state):
        return None
    index = int(state.tutorial.get("step", 0))
    if 0 <= index < len(TUTORIAL_STEPS):
        return TUTORIAL_STEPS[index]
    return None


def tutorial_stations(state) -> dict[str, tuple[int, int]]:
    """本层站点表（生成时写入 state.tutorial["stations"]；统一转 tuple 便于比较）。"""
    return {name: tuple(pos) for name, pos in (state.tutorial.get("stations", {}) or {}).items()}


def _wet_gate_on_live_path(state) -> bool:
    """条件是否真的挂进了同一行的句子。

    旧「湿润门串在活线上」的位置语义对应物：盐渍线圈占条件位、同一行还有
    行为位，编译出 ready 的「导电才放行」句子，玩家才算真的把它用起来。
    """
    for row in state.equipment.formation().rows:
        if (row.status == "ready" and row.condition is not None
                and row.condition.kind == "conductive"):
            return True
    return False


def _check(state, step: dict[str, Any], events: dict) -> bool:
    """单步完成判定：几何谓词 + 事件旗标。"""
    step_id = step["id"]
    if step_id == "welcome":
        return "any_input" in events
    if step_id == "move":
        return (state.player.x, state.player.y) == tutorial_stations(state).get("move_target")
    if step_id == "observe":
        return events.get("observe_cell") == tutorial_stations(state).get("observe_target")
    if step_id == "panel":
        return events.get("panel_opened") == "inventory"
    if step_id == "talk":
        return "npc_talked" in events
    if step_id == "strike":
        # 谓词只认「命中了玩偶」这个结果，不区分手段——射击命中同样认可，
        # 由 pump 的事件保留机制自然完成攻击步+发射步的连跳。
        return "struck_doll" in events or "fired_hit" in events
    if step_id == "fire":
        return "fired_hit" in events
    if step_id == "autowalk":
        return events.get("autowalk_arrived") == tutorial_stations(state).get("autowalk_target")
    if step_id == "board_place":
        return "board_committed" in events
    if step_id == "board_rotate":
        return "board_rotated" in events and len(state.board.placements) >= 2
    if step_id == "board_gate":
        return _wet_gate_on_live_path(state)
    if step_id == "dive":
        # 下潜由 GameState.descend 直接收束（本步不存在「按下但失败」的分支）。
        return False
    return False


def tutorial_pump(state) -> str | None:
    """评估当前步骤并在达标时推进（UI 每帧调用）。

    允许连跳：一次评估里逐步检查后续步骤，上一批事件旗标在推进途中保留，
    因此「一发射击同时完成攻击步与发射步」会被一次认可。返回给 UI 的提示
    文本仅在引导彻底结束时非空——步骤切换本身靠教程卡与高亮的变化呈现。
    """
    if state.tutorial.get('version') == COURSE_TEMPLATE_VERSION:
        from .origin_course import pump, is_course
        if is_course(state): pump(state)
        return None
    if not tutorial_active(state):
        state.tutorial_events.clear()
        return None
    state._ensure_tutorial_supplies()
    current_step = tutorial_step(state)
    if current_step and current_step['id'] == 'fire' and state.projectile_charges <= 0:
        state.projectile_charges = 3  # 教学发射耗尽后仍可完成，不在正式层补充。
    events = state.tutorial_events
    index = int(state.tutorial.get("step", 0))
    progressed = False
    while index < len(TUTORIAL_STEPS) and _check(state, TUTORIAL_STEPS[index], events):
        index += 1
        progressed = True
        if index >= len(TUTORIAL_STEPS):
            break
    if not progressed:
        return None
    state.tutorial["step"] = index
    events.clear()
    if index >= len(TUTORIAL_STEPS):
        state.tutorial["active"] = False
        return tr("引导完成——梦层在等你按 N 下潜。")
    return None


def tutorial_skip_step(state) -> str:
    """Esc：跳过当前步骤进入下一步（已确认的交互口径）。

    最后一步也被跳过时直接结束引导（等价于「n 键随时离开」之外的出口）。
    """
    if state.tutorial.get('version') == COURSE_TEMPLATE_VERSION:
        from .origin_course import skip
        return skip(state)
    if not tutorial_active(state):
        return ""
    step = tutorial_step(state)
    state.tutorial["skipped"] = list(state.tutorial.get("skipped", [])) + ([step["id"]] if step else [])
    state.tutorial_events.clear()
    index = int(state.tutorial.get("step", 0)) + 1
    state.tutorial["step"] = index
    if index >= len(TUTORIAL_STEPS):
        state.tutorial["active"] = False
        return tr("引导结束。梦层在等你按 N 下潜。")
    return tr("已跳过：{title}。", title=tr(step["title"] if step else ""))


def tutorial_end(state, message: str | None = None) -> str:
    """收束引导（下潜离开 / 外部强制）。返回给事件记录的收束文本。"""
    if not state.tutorial.get("active"):
        return message or ""
    state.tutorial["active"] = False
    state.tutorial_events.clear()
    return message or tr("梦的起始在你身后合拢。")


def tutorial_target_cells(state) -> dict[tuple[int, int], str]:
    """当前步骤的地图高亮：{格子: 叠加字形}。引导未激活返回空表。

    玩偶步的目标跟随实体实时位置（玩偶会踱步）；其余步骤用固定站点。
    """
    if state.tutorial.get('version') == COURSE_TEMPLATE_VERSION:
        from .origin_course import current
        step=current(state)
        if step is None: return {}
        target=state.tutorial.get('zones',{}).get(step['zone'])
        if step['id']=='A1': target=state.tutorial['stations']['move_target']
        # Fixed station markers only: never track an unseen moving opponent.
        return {tuple(target):'◇'} if target else {}
    if not tutorial_active(state):
        return {}
    step = tutorial_step(state)
    if step is None:
        return {}
    stations = tutorial_stations(state)
    step_id = step["id"]
    if step_id == "move":
        target = stations.get("move_target")
        return {target: "◇"} if target else {}
    if step_id == "observe":
        target = stations.get("observe_target")
        return {target: "◎"} if target else {}
    if step_id == "talk":
        npc = next(
            (enemy for enemy in state.enemies
             if enemy.integrity > 0 and getattr(enemy, "npc_kind", "") == "npc.origin_greeter"),
            None,
        )
        if npc is not None:
            return {(npc.x, npc.y): "☃"}
        target = stations.get("chat_npc")
        return {target: "☃"} if target else {}
    if step_id in ("strike", "fire"):
        cells: dict[tuple[int, int], str] = {}
        dolls = [
            (enemy.x, enemy.y)
            for enemy in state.enemies
            if enemy.integrity > 0 and enemy.relation == "玩偶意识体"
        ]
        for position in dolls:
            cells[position] = "◍"
        if step_id == "fire":
            origin = stations.get("fire_from")
            if origin:
                cells[origin] = "◆"
        elif not cells:
            # 玩偶恰好都在重生倒计时里：回落到出生站点提示位置。
            fallback = stations.get("doll_melee")
            if fallback:
                cells[fallback] = "◍"
        return cells
    if step_id == "autowalk":
        target = stations.get("autowalk_target")
        return {target: "◈"} if target else {}
    if step_id == "dive":
        target = stations.get("dive_mark")
        return {target: "▼"} if target else {}
    return {}


def tutorial_card_text(state, width: int = 34):
    """教程卡内容（rich Text）。引导未激活返回空 Text（卡片隐藏）。"""
    from rich.text import Text

    if state.tutorial.get('version') == COURSE_TEMPLATE_VERSION:
        from .origin_course import current, localized
        step=current(state)
        if step is None: return Text()
        text=Text(localized(step,'title'),style='bold #9fdaca')
        text.append('\n'+tr('目标与操作见任务日志；Esc 跳过，N 随时离开。'),style='#e6c46a')
        return text

    if not tutorial_active(state):
        return Text()
    step = tutorial_step(state)
    if step is None:
        return Text()
    index = int(state.tutorial.get("step", 0))
    text = Text()
    text.append(
        tr("✦ {current}/{total} · {title}", current=index + 1, total=len(TUTORIAL_STEPS), title=tr(step["title"]))
        + "\n",
        style="bold bright_cyan",
    )
    for line in step["body"].split("\n"):
        text.append(tr(line) + "\n", style="bright_white")
    text.append(
        tr("▸ {key} — {goal}", key=tr(step["key"]), goal=tr(step["goal"])) + "\n",
        style="yellow",
    )
    text.append(
        tr("Esc 跳过此步 · n 随时下潜离开"),
        style="grey58",
    )
    return text
