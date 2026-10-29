"""Actionable microsteps and fresh, isolated replay for the origin course."""
from dataclasses import dataclass
from functools import lru_cache

from .origin_course import BY_ID, MODULES, control, localized, select


@dataclass(frozen=True)
class Instruction:
    fact: str
    anchor: str
    zh: str
    en: str


# Each row follows the module's real evidence order. Anchors reference actual
# widgets or fixed practice cells, never the position of an unseen creature.
_ROWS = {
 'E5': 'board:relation^打开联想盘：将点火手套放在第1列、美工刀放在同行第5列。按 Z 切到「的」工具，在同行第4列按 a 放下，读取整句后 Enter 确认；余温作为属性附加点燃，不会额外行动。^Open the board. Put the warm gloves in column 1 and the boxcutter in column 5 of the same row. Press Z to select OF, move to column 4 and press a. Read the sentence, then Enter to commit. The gloves supply ignition feedback rather than another action.',
 'E6': 'board:relation^打开联想盘：将迅念指环放在第1列、美工刀放同行第5列。按 Z 循环到「地」工具，在同行第4列按 a 放下，读取攻击耗时后 Enter 确认；只有关联行为加速，其他行不共享。^Open the board. Put the swift ring in column 1 and the boxcutter in column 5 of the same row. Cycle Z to BY, move to column 4 and press a. Read the attack timing, then Enter to commit. Only this linked action becomes faster; other rows do not share its manner.',
 'A1': 'map:move_target^用方向键或小键盘走到地图①标记。移动会推进时间。^Use arrows or numpad to walk to marker 1.|widget:#status^按 . 等待一次，观察右侧回合数增加。^Press . to wait once and watch the round counter.|map:move_target^继续走到①所在的格子，站上去才算完成。^Stand on the exact tile marked 1.',
 'A2': 'widget:#panel-tabs^按 Tab 切换右侧大菜单；Shift+Tab 反向切换。^Tab changes the right workspace, Shift+Tab goes back.|widget:#panel-tabs^按 / 切换地图与面板焦点，再按一次比较高亮边框。^Press / to switch map and panel focus and compare the borders.',
 'A3': 'widget:#nav-portents^按 Alt+S 打开自我察觉，或点击「自身」再选「详查」。^Open Self / Full, or press Alt+S.|widget:#self-audit-body^在自我察觉中点击一个属性，展开基础值与来源。^Expand one attribute in the self inspection.|widget:#signal-status^点击右侧噪音/混乱读数，打开来源详情。^Click the noise/chaos readout to inspect its sources.|widget:#panel-help^先进入右侧「行动」界面，在右栏底部点击「完整键位表」，或按 Alt+H。读完 Esc 返回。^Open Act in the right sidebar, then Controls at its bottom (or Alt+H). Esc returns.|widget:#settings-categories^按 Esc 打开暂停菜单，选择设置；读完后返回。^Open Settings from the pause menu, then return.',
 'A4': 'map:move_target^按 X 进入观察，用方向键移动 ? 辅助选中区；Enter 前往该可达位置，X/Q/Esc 只退出观察。^Press X and move the observation cursor with arrows. Enter walks there; X/Q/Esc exit observation.|map:autowalk_target^在②可达空地左键寻路，或 X 观察选中②后 Enter；等角色走到终点。^Click reachable marker 2, or select it in observation and press Enter. Wait for arrival.|map:autowalk_target^再次点击较远空地，或 X 观察选点后 Enter 开始寻路；行走途中按任意键取消，这次按键只刹停、不执行其他动作。^Click a distant clear tile, or use X then Enter to start walking. Press any key while walking to cancel; that key only stops movement.',
 'B1': 'map:35,5^按 X，把观察光标移到①隔墙后的侧室，读已知地形。^Observe the charted side room behind the wall at 1.|map:34,8^从墙南侧开口绕进去，走到②侧室，比较真正看到的内容。^Use the southern opening and enter the side room to see its contents.',
 'B2': 'map:12,18^到①水边教材格，右键打开格子详情，逐项读生物、物品、材料和地板。^Open cell details at the water-side teaching tile and read its layers.',
 'B3': 'widget:#map^按 F3 打开分层观察，地图顶部会出现观察层。^Press F3 to open layer observation.|widget:#layer-strip^按 Tab 切到低层，读取低层内容。^Use Tab to inspect the low layer.|widget:#layer-strip^再按 Tab 切到中层。^Use Tab to inspect the middle layer.|widget:#layer-strip^再按 Tab 切到高层。^Use Tab to inspect the high layer.|widget:#layer-strip^按 Alt+G 查看地势，比较高度数字。^Press Alt+G to inspect elevation.|widget:#map^在分层观察中按 Enter，打开本格详情。^Press Enter in layer observation to inspect the cell.|widget:#map^Esc 逐层返回，退出分层观察并回到原地图。^Use Esc to close details and leave layer observation.',
 'B4': 'map:28,4^先走到①灯旁一格内，点击本框「光源操作」，再在右侧「行动」的目标操作中点击「熄灭光源/点亮光源」，观察亮度变化。^Stand within one tile of lamp 1. Click Light controls in this guide, then Turn light off/on in the Act sidebar target actions.',
 'C1': 'map:doll_melee^走到①练习玩偶旁，朝它移动；若出现攻击确认，按 Y 或 Enter 确认命中。稳定向导不是靶子。^Approach doll 1 and move into it. If asked to confirm attacking a neutral target, press Y or Enter.|map:doll_melee^右键玩偶所在格，再打开生物详情，读完整度和状态。^Inspect the struck doll and read integrity and status.',
 'C2': 'widget:#map^按 F 瞄准，再按 Esc 取消一次；取消不会扣弹。^Press F then Esc to cancel aiming once.|widget:#map^再次 F 瞄准，按 O 辅助选择练习靶。^Aim again and press O to assist targeting.|map:doll_ranged^瞄准时按 Tab 进入自由落点，移动光标到①练习靶。^Use Tab for free aiming and point at practice target 1.|map:doll_ranged^确认弹道畅通后 Enter 或左键射击，实际命中①。^Fire with Enter or click and actually hit target 1.',
 'C3': 'map:47,7^F 瞄准①障碍后的靶，观察弹道被墙挡住；先不要射击。^Aim across obstacle 1 and inspect the blocked path without firing.|map:doll_ranged^取消瞄准，绕到②畅通靶道，再瞄准并实际命中远靶。^Move to the clear lane, aim and hit the distant target.',
 'D1': 'map:10,18^走到①教材上，按 G 收纳；教材已为本节备好。^Walk to teaching item 1 and press G.|widget:#nav-inventory^打开行囊，选择物品并打开其操作/详情。^Open Pack and inspect the teaching item.',
 'D2': 'widget:#nav-inventory^打开行囊，选一份可用教材，点击或 Enter 使用，观察效果与余量。^Use one available teaching item from Pack and compare its effect and quantity.',
 'D3': 'map:12,18^从行囊选择普通教材，按 Q 投掷到①近处玩偶格，观察无伤害物不会砸伤它。^Throw a plain teaching item at the nearby practice doll.|map:16,18^再选择诱饵，Q 投掷到②远处空地，观察其真实功能。^Throw a lure at the distant clear tile 2.|map:12,18^近投落点与角色不超过 2 格。选择普通教材，再完成一次近投。^Complete a throw landing within 2 tiles.|map:16,18^远投落点与角色至少相隔 3 格。选择诱饵，再完成一次远投。^Complete a throw landing at least 3 tiles away.|widget:#map^再进入一次投掷瞄准，Esc 取消，确认物品仍在行囊。^Enter throwing aim once more and cancel with Esc.',
 'D4': 'map:12,19^玻璃瓶已借出，①处另有备用瓶。走到②水格，在行囊使用玻璃瓶并选择盛装。^A bottle is supplied; marker 1 has a spare. Stand on water tile 2, use the bottle in Pack and choose Fill.|map:12,19^仍在水边，使用装水瓶并选择倒出，观察实际存量。^Use the filled bottle and choose Pour.|map:8,16^走到③石台旁，在物品菜单按 P，或点「放到台面」。^Stand beside platform 3 and use P in the item menu to put an item on it.|map:8,16^留在台面旁，按 Enter 行动，取回台面上的教材。^Press Enter beside the platform to retrieve the teaching item.',
 'E1': 'board:grid^打开「构筑→装备」，进入联想盘；用 a 拿起教材、移到空格再 a 放下，Enter 确认整理。^Open Build / Gear, use a to pick and place a piece, then Enter to commit.|board:grid^再次打开联想盘，a 拿起一件意象，按 R 旋转，a 放下后 Enter 确认。^Pick up an image on the board, rotate with R, place with a and commit.',
 'E2': 'board:holding^进入联想盘，把补丁睡衣放在第 3 列形成持有句，Enter 确认。^Place patched pyjamas in column 3 and commit the holding sentence.|widget:#board-editor-sentence^打开联想盘，读下方预览中的整句和实际效果。^Read the full sentence and effects in the board preview.|widget:#self-audit-body^退出编辑，进入「自身→详查」，在顶部切到「来源」，阅读装备提供的条目。^Leave the editor, open Self / Full, select Sources at the top and read the equipment contribution.',
 'E3': 'board:conductive^在联想盘同一行放置：第 1 列浸盐的线圈，第 5 列喷水枪，再确认成句。^Place the salt-soaked coil in column 1 and the water gun in column 5 on the same row, then commit.|map:12,19^退出编辑，先走到 (11,19)。按 F 瞄准、Tab 切自由落点，分别把落点移到①金属导电教材格与旁边普通干地，比较条件放行与不放行，无需射击。^Leave the editor and walk to (11,19). Press F, then Tab for free aiming. Compare conductive metal tile 1 with nearby dry ground; do not fire.',
 'E4': 'widget:#nav-portents^本节已借出被动教材；若出现替换框，先完成选择。^Passive teaching materials are supplied, finish any replacement choice first.|widget:#section-equipment-memory^打开「构筑→记忆」，阅读借用记忆的来源。^Open Build / Memory and read the borrowed memory.|widget:#section-insights^打开「构筑→洞察」，展开蜂鸣回响/听声辨向的规则。^Open Build / Insights and inspect the borrowed rules.|map:16,18^从行囊把诱饵投到①空地，等待真实回响，验证被动效果。^Throw a lure to clear tile 1 and wait for its actual echo.',
 'F1': 'widget:#nav-inventory^在行囊使用借用书卷，完成学习或替换选择。^Use the borrowed book in Pack and finish its learning choice.|widget:#section-constructs^先到②(45,16)，向右走一格，面朝右侧①(47,16)练习空地；打开「行动→构想」点击已学构想施放。若进入选点，选择①确认。主通道不能造墙。^Walk to 2 (45,16), then one tile right to face clear practice tile 1 (47,16). Open Act / Cast and activate the learned ability; if targeting opens, confirm tile 1. Main routes cannot be walled.',
 'F2': 'tamper:source^靠近①样本，按 C 打开篡改，读原句，再 Esc 取消一次。^Approach sample 1, press C to read its original sentence, then cancel with Esc.|tamper:degree^再次按 C，点击程度位置，选择一个可支付的程度并读取报价。^Reopen tampering and choose an affordable degree while reading the quote.|tamper:condition^点击条件位置，查看可选条件与代价，不要跳过原句。^Inspect the condition choices and their cost.|tamper:submit^确认对象、程度、条件与费用，点击提交或按界面确认键，完成一次真实修改。^Verify the target, degree, condition and price, then commit a real edit.',
 'F3': 'widget:#section-constructs^先在「行动→构想」成功施放一次可用构想。^Successfully cast one available ability from Act / Cast.|tamper:submit^再对①样本提交一次可支付的篡改。^Commit one affordable edit to sample 1.|widget:#signal-status^点击噪音/混乱读数，展开混乱和连续篡改压力的实际来源。^Inspect noise/chaos details after the edit and read pressure sources.',
 'F4': 'tamper:source^靠近①②两份液体样本，按 C，点击来源并比较可选的具体区域。^Approach samples 1 and 2, open tampering and inspect source regions.|tamper:preview^在篡改中按 V 查看地图，再按 V 返回编辑，核对草稿保留。^Press V for the map preview, then V to return with the draft intact.',
 'G1': 'map:9,30^走过①安静路线，观察右侧噪音条：安静地面移动后周围噪音较低；点开详情可看下一拍预计声径。^Walk the quiet route 1 and watch the ambient noise bar stay low; open details to read the next-step noise preview.|map:9,28^再走过②空鼓路线，比较移动后噪音条升高的幅度。^Walk the hollow-floor route 2 and compare how much the ambient noise bar rises.|widget:#signal-status^点击噪音读数，展开周围噪音与本次预计声径的来源与修正。^Open noise details for ambient noise, the next-step preview and their modifiers.',
 'G2': 'map:9,29^声音练习已准备好：把诱饵投向①，再等待练习对手调查声源。^Throw a lure to marker 1 and wait for the practice opponent to investigate.|map:7,30^沿②掩体路线绕开，停止继续制造声音，等对手解除追踪。^Go around cover via route 2, stay quiet and wait for pursuit to end.',
 'G3': 'map:15,31^走到①隔墙北面，按 . 等待真实钟声；不要先绕到声源旁。^Wait at marker 1 north of the wall for the real bell.|widget:#signal-status^点击噪音详情，读取隔墙钟声的方向线索。^Read the heard direction clue in noise details.|map:15,33^从墙侧开口绕到②声源，让它真正进入视野。^Use the wall opening and actually see sound source 2.',
 'H1': 'map:29,28^走入①环境样本，获得一个真实征兆。^Enter environmental sample 1 and acquire a real status.|widget:#section-portents^打开「自身→征兆」，展开当前征兆说明。^Open Self / Signs and read the current status.|map:27,28^离开来源到②安全空地，按 . 等待征兆自然结束。^Leave the source for safe tile 2 and wait for the status to expire.',
 'H2': 'map:34,29^①隔离池已有水、水蒸气和灼热池底；站在②玻璃池外安全通道按 . 等待一回合，池底热源会触发真实相变，不必隔墙投掷。^Pool 1 already contains water, steam and a heated floor. Wait one round outside the glass for a real phase change; no throw through the wall is needed.|map:34,29^观察①并打开格子详情，读新材料和剩余量。^Inspect pool 1 and read its new material and remaining quantity.',
 'H3': 'map:31,28^先站到②安全观察格，向①玻璃池外的高丛投出燃烧瓶，触发真实点燃；不要隔着玻璃投向池内。^Stand at safe marker 2 and throw the fire bottle at tall grass 1 outside the glass pool. Do not throw through the glass.|map:31,26^留在②安全格，右键①燃烧格读火焰和材料变化，不要走进落点。^Stay at safe marker 2 and right-click burning tile 1 to read fire and materials.',
 'I1': 'map:chat_npc^走到①出口纸偶旁，打开对话并聊天一次。^Approach exit guide 1 and chat.|map:chat_npc^在对话里读清费用，完成一次付费交换。^Read the price and complete one paid exchange.|map:chat_npc^再选择限领赠品；领完后仍可继续聊天。^Choose the limited gift from the guide.',
 'I2': 'widget:#coach-extra^点击本提示框的「接取练习」，领取取回玻璃瓶的委托。^Click Accept practice in this guide to take the retrieval exercise.|widget:#coach-body^委托要求：取回①物品区的练习玻璃瓶，带回②纸偶旁交付。点击「我已读懂」继续，也可打开日志核对。^Retrieve the practice bottle at 1 and deliver it beside guide 2. Click Understood to continue, or check the Log.|map:14,18^去①取回练习玻璃瓶，再回②纸偶旁，点击本框「交付练习」。^Retrieve the practice bottle at 1, return beside guide 2 and click Deliver practice.',
 'I3': 'widget:#coach-extra^读完后点击本框「我已读懂」完成本项。教程中随时按 N 或点「退出练习」可返回正常存档页；不会生成正式存档。^Click Understood in this guide to complete this lesson. N or Exit practice returns to normal save slots without saving this practice.',
 'I4': 'widget:#coach-hide^点击「收起提示」，确认小悬浮入口仍可见。教程不保存，正式存档不受影响。^Hide the guide and keep its small floating reopen control.|widget:#coach-show^点击小悬浮入口重新打开提示，继续当前练习。^Reopen the floating guide and continue the current exercise.',
 'J1': 'map:14,3^事件已备好：到①异常地点旁按 Enter，打开回应选项。^Approach event 1 and press Enter to read its choices.|widget:#map-overlay^读完选项的代价与所得，再选择一次；离开也是合法决定。^Read the cost and reward, then choose an option or leave.',
 'J2': 'map:32,13^走过①高丛，观察它被踩成低草。^Walk through tall plants 1 and observe them become low grass.|map:36,14^站到②稀有植株上，按 Enter 拔起，再读所得材料或征兆。^Stand on rare plant 2, press Enter to uproot it and read the result.',
 'J3': 'map:30,20^玻璃瓶已借出：在①水源盛水，再走到②湿墨池使用瓶子倒出，观察新液体。^Fill the supplied bottle at water source 1, pour into wet ink pool 2 and inspect the reaction.',
 'J4': 'board:grid^钉枪已借出：放进联想盘源位确认成句，再 F 射击一次，读取弹匣减少。^Commit the supplied nail gun on the board and fire once to reduce its magazine.|widget:#section-fire^射击到空匣，按 R 换弹，读换弹步数、余量及想象力费用。^Empty the magazine and press R to reload, reading its steps, supply and cost.',
 'J5': 'widget:#nav-inventory^在行囊使用借出的浓缩咖啡因，查看清醒度债务账单。^Use the supplied espresso shot and inspect its lucidity debt.|widget:#status^按 . 等待两回合，观察债务实际分期扣除。^Wait two rounds and observe the actual debt payments.',
 'J6': 'map:33,21^异象已准备：在①打开生物详情，读分级、完整度、关系和技能。^Open creature details for anomaly 1 and read grade, integrity, relation and skills.',
 'J7': 'map:33,21^击破①练习异象，确认它实际消失并记入击杀。^Defeat practice anomaly 1 and verify the actual kill.|map:33,21^走到①原位置按 G 拾取固定掉落，再读击杀记录与崩解度。^Collect its fixed drop with G and read kill/dissolution results.',
 'J8': 'widget:#section-constructs^火花已借出：先面朝相邻空地，或将鼠标停在可见空地，再在「行动→构想」点击火花或选中后 Enter，立即施放；不会再弹出选点确认。^Spark is supplied. Face adjacent clear ground or hover over visible clear ground, then click Spark in Act / Cast or select it and press Enter. It casts immediately without another targeting confirmation.|widget:#map^先观察构造出的场，再按 . 等待两回合，直到它落地并消失。^Observe the constructed field, then wait two rounds for it to settle and end.',
 'J9': 'map:34,15^机关已备好：到①机关石台旁取走练习物，观察电线把信号送到②显影方尖。^Retrieve the item from mechanism platform 1 and observe the signal reach reveal obelisk 2.',
 'J10': 'map:30,16^到①外观相同的陷阱石台旁取走练习物，读取这次真实触发结果。^Retrieve the item from trap platform 1 and read what actually triggers.',
}


@lru_cache(maxsize=None)
def instructions(module_id):
    parts = [row.split('^') for row in _ROWS[module_id].split('|')]
    facts = BY_ID[module_id]['requires']
    if len(parts) != len(facts):
        raise ValueError(f'Guidance/evidence mismatch: {module_id}')
    return tuple(Instruction(fact, *part) for fact, part in zip(facts, parts))


def next_instruction(state):
    from .origin_course import current
    module = current(state)
    if module is None:
        return None, 0, 0
    rows = instructions(module['id'])
    facts = set(state.tutorial.get('facts', ()))
    for index, row in enumerate(rows):
        if row.fact not in facts:
            return row, index + 1, len(rows)
    return rows[-1], len(rows), len(rows)


def map_targets(state, module_id):
    explicit = {
        'F1': ('47,16', '45,16'),
        'H2': ('34,29', '31,29'),
        'D4': ('10,18', '12,19', '8,16'), 'I2': ('14,18', 'chat_npc'),
        'F2': ('46,18', '54,18'), 'F3': ('46,18',), 'F4': ('46,18', '54,18'),
        'J3': ('30,20', '34,20'), 'J9': ('34,15', '37,15'),
    }
    names = explicit.get(module_id)
    if names is None:
        names = tuple(dict.fromkeys(row.anchor[4:] for row in instructions(module_id)
                                    if row.anchor.startswith('map:')))
    result = {}
    for number, name in enumerate(names, 1):
        point = state.tutorial.get('stations', {}).get(name)
        if point is None:
            point = tuple(map(int, name.split(',')))
        result[number] = tuple(point)
    return result


_PREPARE = {'E4': ('passives',), 'F3': ('spark', 'tamper_samples'),
            'F2': ('tamper_samples',), 'F4': ('tamper_samples',),
            'G2': ('noise',), 'G3': ('hearing',), 'H1': ('environment',),
            'H2': ('environment',), 'H3': ('environment',), 'J1': ('event',),
            'J2': ('plants',), 'J3': ('reaction',), 'J4': ('magazine',),
            'J5': ('drug',), 'J6': ('anomaly',), 'J7': ('anomaly',),
            'J8': ('spark',), 'J9': ('circuit',), 'J10': ('trap',)}


def prepare_module(state, module_id):
    """Prepare real practice tools without supplying completion evidence."""
    if state.tutorial.get('coach_prepared') == module_id:
        return
    state.tutorial['coach_prepared'] = module_id
    for operation in _PREPARE.get(module_id, ()):
        control(state, operation)
    if module_id in ('D4', 'J3') and not any(i.definition_id == 'glass_bottle' for i in state.inventory):
        from .origin_course import _add_loan_item
        _add_loan_item(state, 'glass_bottle')
    if module_id == 'E3':
        # A finite puddle can flow away while editing the board. A real metal
        # teaching tile keeps the conductive comparison repeatable without
        # changing water simulation or inventing a successful condition.
        state.cell(12, 19).aggregate_variant = '金属聚合物'
    if module_id == 'H3':
        # The sealed phase-change pool blocks throws. Fire practice gets its
        # own finite, reachable target outside the glass, away from the stand.
        state.set_plant(31, 28, 2)
    if module_id.startswith('E') or module_id == 'J4':
        from .origin_course import _add_loan_item
        for item_id in ('pen_sharp', 'patched_pajamas', 'salt_soaked_coil', 'water_gun'):
            from .content import ITEM_DEFINITIONS
            if item_id in ITEM_DEFINITIONS and not any(i.definition_id == item_id for i in state.inventory):
                _add_loan_item(state, item_id)
    if module_id in ('E5', 'E6'):
        from .origin_course import _add_loan_item
        from ..equipment.board import EquipmentBoard
        # Both are freely accessible exercises; start with an empty draft space.
        state.board = EquipmentBoard(syntax=state.board.syntax)
        state.equipment.invalidate()
        for item_id in ('rusty_boxcutter', 'ignite_gloves' if module_id == 'E5' else 'swift_thought_ring'):
            if not any(i.definition_id == item_id for i in state.inventory):
                _add_loan_item(state, item_id)
    if module_id in ('F1', 'F3'):
        # A real existing cast is available even when this chapter is opened first.
        if module_id == 'F3':
            control(state, 'spark')


def replay_state(previous, module_id):
    if module_id not in BY_ID:
        raise ValueError(module_id)
    from . import GameState
    state = GameState.new(seed=20261023, tutorial=True)
    done = set(previous.tutorial.get('completed', ())) | set(previous.tutorial.get('reviewed', ()))
    state.tutorial['completed'] = sorted(done - {module_id})
    state.tutorial['reviewed'] = sorted(done)
    state.tutorial['coach_version'] = 1
    select(state, module_id)
    prepare_module(state, module_id)
    # Start at the chapter's safe approach rather than demand a cross-map walk.
    from ..mapgen.origin import ZONE_CENTRES
    zone = BY_ID[module_id]['zone'] if not module_id.startswith('J') else {'J1': 'A', 'J5': 'D', 'J8': 'F'}.get(module_id, 'E')
    cx, cy = ZONE_CENTRES[zone]
    candidates = sorted(((x, y) for y in range(max(1, cy-3), min(state.height-1, cy+4))
                         for x in range(max(1, cx-3), min(state.width-1, cx+4))),
                        key=lambda p: abs(p[0]-cx) + abs(p[1]-cy))
    for pos in candidates:
        cell = state.cell(*pos)
        if not cell.solid and not cell.flame and not cell.liquid and state.entity_at(*pos) is None:
            state.player.x, state.player.y = pos
            break
    return state
