"""深层边界（28-30）剧情表：三展室记忆池 / 微事件 / 结局 / 承担牵引规则。"""

from __future__ import annotations

from typing import Any

EPILOGUE_ROOM_POOLS: dict[str, list[dict]] = {
    "亲历": [
        {"text": "一间模型屋的灯在半夜亮着：桌上的高达缺了一支天线，你记得是你自己掰断的——为了测试它的「战损涂装」。", "truth": "亲历"},
        {"text": "某个截稿前的凌晨，编辑的回复只有两个字「重写」。你盯着屏幕，把整章删了，又一个字一个字敲了回来。", "truth": "亲历"},
        {"text": "耳机里那段电音的 drop 前有一秒静默——你在livehouse人群里闭眼等过那一秒，汗从下颌滴在票根上。", "truth": "亲历"},
        {"text": "小时候你把创可贴贴在模型的手指上，因为它的手指断了，而你觉得它也会疼。", "truth": "亲历"},
        {"text": "你交出去的第一篇稿子被退回时信封上有一道折痕。你后来才明白，折痕是邮差怕里面是钱。", "truth": "亲历"},
        {"text": "摇滚现场的音浪让地板发麻，你扶着护栏想：原来「共鸣」是个物理现象。", "truth": "亲历"},
    ],
    "模仿": [
        {"text": "少年漫画里主角总在废墟里握紧拳头。你也握紧过——但那是在方便面泡开的第三分钟。", "truth": "模仿"},
        {"text": "「作家应该冷眼看世界。」这句话你从某本访谈里抄来，抄了太多次，连语气都换了它的。", "truth": "模仿"},
        {"text": "悬疑小说里的作家都有一间安静的阁楼。你也想要一间，于是把出租屋想象成阁楼，直到房东来修热水器。", "truth": "模仿"},
        {"text": "你模仿过某位大师的短句风格写了一整章。读者说「这段有味道」——你把「它」的味道当成了你的。", "truth": "模仿"},
        {"text": "动画里的台词说「只要不放弃梦想」。你在崩溃的那个月把这句话设成了签名，但只是设成了签名。", "truth": "模仿"},
        {"text": "你学着电影里的角色在天台上大喊。喊完之后楼下的狗叫了两声——那不是剧本写的反应。", "truth": "模仿"},
    ],
    "外来": [
        {"text": "一段不属于自己的童年：别家厨房的白瓷碗，别家的母亲在喊一个不是你的名字吃饭。", "truth": "外来"},
        {"text": "一场你没去过的葬礼：白花、低语、和一张越看越像你自己的遗像。", "truth": "外来"},
        {"text": "一句你没听过的方言在耳边循环。你听不懂，但你知道它在骂「冒牌货」。", "truth": "外来"},
        {"text": "一份不属于你的病历：姓名栏被涂改过三次，诊断栏写着你最近才有的症状。", "truth": "外来"},
        {"text": "一条你没发过的消息出现在你手机的草稿箱：「救救我」。发送时间是今天凌晨四点。", "truth": "外来"},
        {"text": "一张你从没画过的手稿，签着你的笔名，笔迹比你的更熟练。", "truth": "外来"},
    ],
}
EPILOGUE_MICRO_EVENTS: tuple[dict, ...] = (
    {"event_id": "epilogue.micro1", "name": "倒扣的茶杯", "description": "茶杯扣在稿纸上，晕开的茶渍像一座岛。", "reward_id": "warm_coffee", "catalog_id": "epilogue.micro1"},
    {"event_id": "epilogue.micro2", "name": "写着半句的便签", "description": "便签上只有「我还记得」四个字，后面被咖啡洗掉了。", "reward_id": "mint_lozenge", "catalog_id": "epilogue.micro2"},
    {"event_id": "epilogue.micro3", "name": "丢失的笔帽", "description": "笔帽找到了，笔却不在。它在等你。", "reward_id": "pen_sharp", "catalog_id": "epilogue.micro3"},
    {"event_id": "epilogue.micro4", "name": "停止的挂钟", "description": "挂钟停在凌晨三点。你入梦前看过的最后一眼也是三点。", "reward_id": "cold_tea", "catalog_id": "epilogue.micro4"},
    {"event_id": "epilogue.micro5", "name": "拼错的模型说明书", "description": "第 14 步和第 15 步印反了。你按着错误的顺序拼完了它。", "reward_id": "model_screw", "catalog_id": "epilogue.micro5"},
    {"event_id": "epilogue.micro6", "name": "被退回的稿纸", "description": "纸页边缘卷了毛边——有人读过很多遍。", "reward_id": "loose_thread", "catalog_id": "epilogue.micro6"},
    {"event_id": "epilogue.micro7", "name": "旧票根", "description": "票根上的日期是明天。", "reward_id": "quiet_ticket", "catalog_id": "epilogue.micro7"},
    {"event_id": "epilogue.micro8", "name": "没有图的涂色本", "description": "涂色本全是空白，但每一页都涂好了颜色。", "reward_id": "clear_glass", "catalog_id": "epilogue.micro8"},
    {"event_id": "epilogue.micro9", "name": "耳机的另一只", "description": "它与你在第 11 层丢的那只是一对。", "reward_id": "single_earphone", "catalog_id": "epilogue.micro9"},
    {"event_id": "epilogue.micro10", "name": "温热的台灯", "description": "台灯还热着。它等你回来之后又亮了一会儿。", "reward_id": "warm_water", "catalog_id": "epilogue.micro10"},
)
EPILOGUE_ENDINGS: dict[str, dict] = {
    "A": {
        "title": "初醒",
        "subtitle": "裂隙尽头是清晨",
        "lines": [
            "核心执念的碎片还在指尖发烫。裂隙里透进来的不是光——是清晨。",
            "你醒了。枕边的笔记本摊在最后一页，上面是你入梦前写下的半句话。",
            "你拿起了笔。梦没有结束，它只是暂时退到了稿纸背面。",
        ],
    },
    "B": {
        "title": "重写",
        "subtitle": "这是我的故事，包括写坏的部分",
        "lines": [
            "你把笔从执笔者手里抽了出来。它没有抵抗——仿佛它一直在等一个敢这么做的作者。",
            "{clues} 条自我线索在你掌心拼成一句话：「这是我的故事，包括所有写坏的部分。」",
            "你重新写下了结局。醒来的时候，窗外有真实的鸟叫——笨拙、走音，但属于这个世界。",
        ],
    },
    "C": {
        "title": "放手",
        "subtitle": "故事由它收尾，你如释重负",
        "lines": [
            "你点了点头。执笔者的手指落在键盘上，替你敲完最后一个句号。",
            "故事很完整。完整得像所有你没写完的故事被人代笔后的样子。",
            "你醒来时觉得轻松，又觉得哪里空了一块。那块地方的名字，你决定不再去想。",
        ],
    },
    "D": {
        "title": "共写",
        "subtitle": "两支笔同时落下",
        "lines": [
            "你和执笔者隔着稿纸对坐。它递来笔，你留下了自己的那支——两支笔同时落下。",
            "结局在两行笔迹之间来回：它的工整，你的潦草，谁也没盖过谁。",
            "你醒来时手里攥着两支笔。至少其中一支，握在你自己手里。",
        ],
    },
    "E": {
        "title": "沉没",
        "subtitle": "梦不再需要你",
        "lines": [
            "深层边界合拢了。没有痛苦——只是从某一拍开始，梦不再需要你。",
            "{fell_note}",
            "如果还有人在等这局梦醒——他们等到的，只是一个不再醒来的名字。",
        ],
    },
    # F「无梦」：意识与清醒一同耗尽（深层边界之外的死亡）。
    "F": {
        "title": "无梦",
        "subtitle": "意识与清醒一同耗尽",
        "lines": [
            "梦在你双肩上合拢。没有醒，也没有继续——只是薄薄的一层安静。",
            "长夜收下了你带来的所有记忆，把它们叠好，放回原处。",
            "门外的人只会说：这一觉睡得真沉。",
        ],
    },
}
EPILOGUE_PROFILE_RULES: tuple[dict, ...] = (
    {"profile": "杀伐型", "when": ("kills", ">=", 40), "label": "无血的和解", "hint": "在三个承担点达成和解，且期间不解决任何异象。"},
    {"profile": "囤积型", "when": ("bag", ">=", 10), "label": "松手", "hint": "在三个承担点各舍弃 1 件未装备的携带意象。"},
    {"profile": "纵火型", "when": ("ignitions", ">=", 60), "label": "冷灰", "hint": "在承担点附近五格内没有火焰时回应三个承担点。"},
    {"profile": "直面型", "when": (), "label": "直面", "hint": "依次回应三个承担点（每个都会提出一个小问题）。"},
)
