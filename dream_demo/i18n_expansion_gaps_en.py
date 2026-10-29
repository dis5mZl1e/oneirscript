"""扩展包装备的运行期反馈与奖励选项英文（2026-10-25）。

六主题（声源/光场/地势/弹体/电路/realm）装备的实现 2026-10-25 成批落地，
``_apply`` 回给玩家的成品句直接走 ``tr(字面量)``（AST 覆盖测试看得见），
但英文包没跟上：``test_i18n_coverage`` 的 72 条模板与 8 条事件选项标签因此
一直红着。

用词对齐 ``data/expansion/catalog.py`` 的 ``name_en``（脚步机＝Borrowed
Footsteps、空椅＝Empty Seat in the Back Row…），句子按「第二人称、给动作
结果」的口吻写，与既有装备反馈一致。
"""

EN_EXPANSION_GAPS = {
    # ---- 装备与联想盘的通用拒绝句 ----
    "装备须先上盘。": "The gear must be placed on the association board first.",
    "{item}现在没有可以直接做的动作。": "{item} has no direct action right now.",
    "{item}不接受单点。": "{item} doesn't take a single point.",
    "{item}不接受成对落点。": "{item} doesn't take paired points.",
    "{item}不接受方向。": "{item} doesn't take a direction.",
    "{item}要先装到联想盘上才能这样用。":
        "{item} has to be on the association board before it can be used that way.",
    "你的另一只手还举着{busy}——先放下它。":
        "Your other hand is still holding {busy} — put it down first.",
    "选择投掷落点，取消不消耗。": "Choose where to throw; cancelling costs nothing.",
    "选择已知目标，取消不消耗。": "Choose a known target; cancelling costs nothing.",
    "这份物品已经不在行囊中。": "That item is no longer in your pack.",
    "换弹尚未完成，当前不能移位。": "The reload isn't finished; you can't step away yet.",
    # ---- 装订钳 / 止退片 / 工作服（realm、terrain 批的封衣口径）----
    "装订钳还固定着同类残留，暂时不能另铺。":
        "The binding pliers still pin the same kind of residue; you can't lay another yet.",
    "止退片挡住这次推动后碎裂了。": "The paper backstop took the push, then shattered.",
    "工作服的外层还封着——先解开再喷射。":
        "The suit's outer layer is still sealed — unseal it before spraying.",
    "工作服的外层还封着——先解开再盛装。":
        "The suit's outer layer is still sealed — unseal it before filling.",
    "你把工作服的外层封死了——{n} 回合内不会沾上新的液体，但也盛不了东西。":
        "You seal the suit's outer layer — no new liquid sticks for {n} rounds, "
        "but you can't fill anything either.",
    # ---- 光场：台灯／手电／遮片／披布／灯罩／把手 ----
    "你把台灯转了个方向——正面亮了一格，背后仍旧照不到。":
        "You turn the desk lamp — one cell brighter in front, still dark behind.",
    "长窄束：前面看得更远，两侧照旧。":
        "Long narrow beam: farther ahead; the sides are unchanged.",
    "短宽束：四周各多一格，但前面不再多照。":
        "Short wide beam: one extra cell on every side, no extra reach ahead.",
    "你把手电关上了。": "You switch the flashlight off.",
    "手电的电量已经见底了——切哪一档都不亮。":
        "The flashlight is out of charge — neither mode lights up.",
    "手电闪了两下就灭了——电量用完了。":
        "The flashlight flickers twice and dies — the charge is spent.",
    "你举起焦黑的遮片挡住正面的光：那边你看不见，那边也看不清你。它不会自己放下，也不腾手做别的工具动作。":
        "You raise the soot shield against the light ahead: you can't see that side, and it "
        "can't see you either. It won't come down by itself, and it keeps a hand from other "
        "tool actions.",
    "你放下遮片——正面的视线回来了。": "You lower the shield — sight ahead returns.",
    "你把黑披布架了起来——那一侧的视线也被它一起挡住了。":
        "You set the black drape up — sight on that side is blocked along with it.",
    "你一动，黑披布就滑下来了一角——那面遮光面倒了。":
        "As you move, a corner of the black drape slips — that shaded side falls.",
    "你把灯罩装了回去——光又收拢成一圈。":
        "You fit the lampshade back on — the light gathers into a ring again.",
    "你把灯罩卸了下来——那盏灯散得更开，也多照出一圈。":
        "You take the lampshade off — the lamp spreads wider and lights one extra ring.",
    "斜口把一部分光引成了一条短线——原来那一圈随之小了一圈。":
        "The angled mouth draws part of the light into a short line — the original ring "
        "shrinks by one.",
    "灯罩没法隔空够到——先站到那盏灯的旁边。":
        "You can't reach the lampshade from here — stand next to that lamp first.",
    "那格没有亮着的灯可以拆罩子。": "There's no lit lamp there to take a shade from.",
    "被引光的那格得是一盏亮着的灯。": "The cell you draw light to has to be a lit lamp.",
    "朝着灯自己是引不出方向来的——在另一头点一下。":
        "You can't draw light toward the lamp itself — click from the other end.",
    "灯前头没有可以引过去的直线。":
        "There's no straight line in front of the lamp to draw the light along.",
    "那盏灯已经引着一条光了——等它回满再引。":
        "That lamp is already drawing a beam — wait for it to refill.",
    "那格没有可以转的固定灯。": "There's no fixed lamp there to turn.",
    "你还没确认过那盏灯——把手先转不动它。":
        "You haven't confirmed that lamp yet — the handle won't turn it.",
    "光被墙截住了——隔墙转不动灯。":
        "The wall blocks the light — you can't turn a lamp through it.",
    "灯架的电源接在电路上，把手转不动它。":
        "That lamp rig is wired to a circuit; the handle can't turn it.",
    "把手一转，远处那盏灯亮了。": "A turn of the handle, and the distant lamp lights up.",
    "把手一转，远处那盏灯灭了。": "A turn of the handle, and the distant lamp goes dark.",
    # ---- 声源：鞋垫／铃轴／漏斗／软帘／传声筒／脚步机／空椅 ----
    "鞋垫在脚下碎开——本层还剩 {n} 片。":
        "The insole crumbles underfoot — {n} left on this floor.",
    "这一层的鞋垫已经全踩碎了。": "Every insole on this floor has already been crushed.",
    "木底鞋的槽里积了一点液面——这一下没沾上。":
        "Liquid pools in the groove of the wooden clogs — this step stays clean.",
    "铃轴贴着墙根滚了出去，一路都带着响。":
        "The bell spool rolls away along the base of the wall, ringing the whole way.",
    "铃轴在墙根停住了，滚不动也响不动。":
        "The bell spool stops against the wall, unable to roll or ring.",
    "没有方向，铃轴滚不出去。": "Without a direction, the bell spool can't roll.",
    "铃轴推不出去——那边是墙。": "The bell spool can't go that way — wall.",
    "漏斗扣上了——下一次诱引会朝那个方向收窄。":
        "The funnel is clipped on — your next lure will narrow toward that direction.",
    "软帘挂起来了——穿过这两格的声音会哑一分，你自己的也一样。":
        "The sound-damping curtain goes up — sound crossing these two cells is muffled a "
        "notch, your own included.",
    "软帘只能挂在相邻的两格之间。":
        "The sound-damping curtain only hangs between two adjacent cells.",
    "软帘松脱，落了下来。": "The sound-damping curtain comes loose and falls.",
    "两只传声筒接好了——声音会从另一头出来，一点也不会更响。":
        "Both speaking tubes are connected — the sound comes out the far end, no louder.",
    "传声筒的两头松开了。": "Both ends of the speaking tubes come apart.",
    "脚步机在落点放下了——它会把刚才那几步重新走一遍。":
        "Borrowed Footsteps is set down at the target — it will replay those last steps.",
    "脚步机还没记下足够的步子——先走两步再来。":
        "Borrowed Footsteps hasn't recorded enough steps — walk a little first.",
    "脚步机走完了最后一步，停在原地。":
        "Borrowed Footsteps takes its last step and stops.",
    "脚步机的发条走完了。": "Borrowed Footsteps winds down.",
    "脚步机复放的脚步": "Replayed footsteps",
    "空椅面向走廊放着——它先替你安静两回合。":
        "The empty seat faces the corridor — it keeps quiet for you for two rounds.",
    "空椅把那一声原样放了出来。": "The empty seat plays that sound back exactly.",
    "空椅一直没等到声音，被人搬回墙角了。":
        "The empty seat waited for a sound that never came; it has been carried back to "
        "the corner.",
    "最后那排空椅把这一声吞了下去。":
        "The last row of empty seats swallows the sound.",
    "铃在没有铃舌的情况下响了一声——那声音替你喊了出来。":
        "The clapperless bell rings once — the sound shouts in your place.",
    # ---- 洞察：蒸气的出口（expansion_insights 的运行期播报）----
    "蒸气的出口：本回合 {n} 格新起了气——{cells}，自 ({sx}, {sy}) 推进。":
        "Vapour outlet: {n} new gas cells this round — {cells}, spreading from ({sx}, {sy}).",
    "蒸气的出口：另有 {n} 格新推进的落点一并记下。":
        "Vapour outlet: {n} further cells reached by the spread are recorded as well.",
    "蒸气的出口：本回合 {n} 格起了气，可上一回合没看见挨着它的气——{cells}；不猜来向。":
        "Vapour outlet: {n} cells produced gas this round, but no gas beside them was seen "
        "last round — {cells}; the direction of origin is not guessed.",
    "蒸气的出口：本回合 {n} 格的气退了——{cells}。":
        "Vapour outlet: gas receded from {n} cells this round — {cells}.",
    # ---- 事件奖励选项（六主题事件各自的「拿走那件东西」）----
    "从回声里拎出那台脚步机": "Pull Borrowed Footsteps out of the echo",
    "从空画框后抽出乐池的指挥棒": "Draw the Pit Conductor's Baton from behind the empty frame",
    "从退潮处捡起那件沉箱工作服": "Pick up the Caisson Work Suit where the tide went out",
    "扯下画框上蒙着的那块黑披布": "Tear the Photographer's Black Drape off the frame",
    "扶起画框下那盏不肯熄灭的灯芯架":
        "Stand up the Lampwick Stand That Won't Go Out beneath the frame",
    "拆下错接在一起的两只传声筒": "Take down the Miswired Speaking Tubes",
    "捡起回声里那把聚光把手": "Pick the Lost Spotlight Handle out of the echo",
    "搬走最后一排那张空椅": "Carry off the Empty Seat in the Back Row",
}
