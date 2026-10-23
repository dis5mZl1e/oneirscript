"""Complete final-layer dialogue, exploration and ending translations."""
from .data.endings import EPILOGUE_ROOM_POOLS, EPILOGUE_ENDINGS

EN_EPILOGUE = {
    '辨认之馆的登记员：她说不清自己在这里多久了，也不打算说。': 'The gallery registrar cannot say how long she has been here, and does not intend to.',
    '「每个走进这里的人，都要去认领自己的记忆。认错了也没关系——」': '"Everyone entering must claim their memories. Getting one wrong is all right..."',
    '「馆里的规矩是：认错的人，比从不认的人，更接近清醒。」': '"Our rule is: those who make mistakes are closer to waking than those who never acknowledge anything."',
    '问清馆的规矩': 'Ask about the gallery rules',
    '替她整理一摞档案（上交 3 件消耗品）': 'Sort a stack of records (Give 3 consumables)',
    '听她讲一个借来的故事': 'Listen to a borrowed story',
    '问馆里丢了什么': 'Ask what the gallery has lost', '只是点头致意': 'Nod and leave',
    '站在承担之野入口的灰衣人：他举着一盏不照路、只照自己的灯。': 'A gray-clad guide stands at the entrance to the Field of Acceptance, holding a lamp that lights only himself.',
    '「前面三条路，走哪条都到碑前。区别只在——」': '"All three roads lead to the stele. The only difference is..."',
    '「你愿意在碑前承认什么。」': '"What you are willing to acknowledge before it."',
    '讨一口热水': 'Ask for warm water',
    '陪他站一段夜岗（上交 3 件消耗品）': 'Keep the night watch with him (Give 3 consumables)',
    '问灯照的是什么': 'Ask what the lamp illuminates',
    '问灯为什么照自己': 'Ask why the lamp lights himself', '沉默走过': 'Leave in silence',
    '展室中央悬着一段记忆。判断它从哪里来。': 'A memory hangs in the gallery. Decide where it came from.',
    '它属于——': 'It belongs to...',
    '我亲历过': 'I lived this myself', '我模仿来的': 'I borrowed this', '它根本不是我': 'This is not mine',
    '归档门': 'Archive Door',
    '三间展室的门在身后合拢。归档门上的铜锁等着一句话。': 'The three galleries close behind you. The archive lock awaits your answer.',
    '门后没有声音。它在等你说：我看完了。': 'Beyond the door is silence. It waits for you to say: I have seen it all.',
    '「我看完了。」（推门进入承担之野）': '"I have seen it all." (Enter the Field of Acceptance)',
    '「全部烧掉。」（抹去线索，强行进入）': '"Burn it all." (Erase your clues and enter)',
    '承担牵引碑': 'Guidance Stele', '接受牵引': 'Accept the guidance',
    '在三个承担点达成和解，且期间不解决任何异象。': 'Reconcile at the three burden sites without defeating any anomalies in between.',
    '依次回应三个承担点（每个都会提出一个小问题）。': 'Answer the three burden sites in order, facing each question.',
    '审判门': 'Judgment Door',
    '门楣上刻着：承担两分，方过此门。': 'The lintel reads: Accept two burdens to pass.',
    '审判门后是改写之台。门在等你承认够了再开。': 'The Rewriting Desk waits beyond. Accept enough burdens to open the door.',
    '推门（进入改写之台）': 'Open the door (Enter the Rewriting Desk)',
    '执笔者之桌': "The Scribe's Desk",
    '稿纸摊在桌上，末行空着。执笔者就在不远处写着你的人生。': 'The manuscript lies open with its final line blank. Nearby, the Scribe writes your life.',
    '重写结局（需要 4 条自我线索，且执笔者已沉默）': 'Rewrite (4 self clues; the Scribe must be defeated)',
    '让它写完（结局：放手）': 'Let the draft end (Letting Go)',
    '与它共写（需要 3 条自我线索与 40 点想象力）': 'Write together (3 self clues and 40 imagination)',
    '告辞。': 'Leave.',
    '倒扣的茶杯': 'Overturned Teacup',
    '茶杯扣在稿纸上，晕开的茶渍像一座岛。': 'The cup rests upside down on the manuscript. Its stain resembles an island.',
    '写着半句的便签': 'Half-Written Note',
    '便签上只有「我还记得」四个字，后面被咖啡洗掉了。': 'Only "I still remember" remains on the note. Coffee washed away the rest.',
    '丢失的笔帽': 'Lost Pen Cap', '笔帽找到了，笔却不在。它在等你。': 'The cap is here, but the pen is missing. It waits for you.',
    '停止的挂钟': 'Stopped Clock',
    '挂钟停在凌晨三点。你入梦前看过的最后一眼也是三点。': 'The clock stopped at three in the morning, the last time you saw before dreaming.',
    '拼错的模型说明书': 'Misprinted Model Instructions',
    '第 14 步和第 15 步印反了。你按着错误的顺序拼完了它。': 'Steps fourteen and fifteen were reversed. You assembled it in the wrong order.',
    '被退回的稿纸': 'Returned Manuscript', '纸页边缘卷了毛边——有人读过很多遍。': 'The edges are frayed. Someone has read these pages many times.',
    '旧票根': 'Old Ticket Stub', '票根上的日期是明天。': 'The date on the ticket is tomorrow.',
    '没有图的涂色本': 'Blank Coloring Book', '涂色本全是空白，但每一页都涂好了颜色。': 'The book has no pictures, but every page has been colored.',
    '耳机的另一只': 'The Other Earbud', '它与你在第 11 层丢的那只是一对。': 'It matches the earbud you lost on layer eleven.',
    '温热的台灯': 'Warm Desk Lamp', '台灯还热着。它等你回来之后又亮了一会儿。': 'The lamp is still warm. It waited for you and stayed lit a little longer.',
}

for index in range(3):
    EN_EPILOGUE[f'承担点·{index+1}'] = f'Burden Site {index+1}'
for profile, name in (('杀伐型', 'Warrior'), ('囤积型', 'Collector'), ('纵火型', 'Firestarter'), ('直面型', 'Witness')):
    EN_EPILOGUE[f'碑上刻着你的画像：{profile}。牵引已经写好。'] = f'The stele bears your portrait: {name}. Your guidance awaits.'
    EN_EPILOGUE[f'牵引画像：{profile}。'] = f'Your guiding portrait: {name}.'
    EN_EPILOGUE[f'承担（{profile}）'] = f'Accept ({name})'

_MEMORIES = {
    '亲历': (
        'A model-room lamp glows at midnight. The Gundam on the desk lacks an antenna. You remember breaking it yourself to test its battle-damaged paint.',
        'Before a deadline, the editor replied with one word: Rewrite. You deleted the chapter and typed it back, letter by letter.',
        'There was a second of silence before the electronic drop. You waited for it with closed eyes in the concert crowd, sweat dripping onto your ticket.',
        'As a child, you put a plaster on a model\'s broken finger. You believed it could hurt too.',
        'Your first rejected manuscript returned in a creased envelope. Later you learned that the postman had folded it, afraid it contained cash.',
        'At a rock show, sound made the floor tremble. Holding the railing, you thought: resonance is a physical phenomenon.',
    ),
    '模仿': (
        'Manga heroes clenched their fists among ruins. You did too, three minutes after pouring water into instant noodles.',
        'A writer must view the world coldly. You copied that interview line so often that even your voice became its voice.',
        'Mystery writers had quiet attics. You imagined your rented room as one until the landlord arrived to fix the heater.',
        'You wrote a chapter in a master\'s clipped style. Readers liked its flavor. You mistook that flavor for your own.',
        'An animation said: never abandon your dreams. You made it your signature during a difficult month, but only your signature.',
        'You shouted from a rooftop like a film character. A dog barked twice below. That reply was not in the script.',
    ),
    '外来': (
        'A childhood that was never yours: white bowls in another kitchen, another mother calling a name that is not your name.',
        'A funeral you never attended: white flowers, whispers, and a portrait that looks increasingly like you.',
        'An unfamiliar dialect repeats beside your ear. You cannot understand it, yet you know it calls you an impostor.',
        'A medical record that is not yours. The name was changed three times; the diagnosis describes your recent symptoms.',
        'An unsent message you never wrote lies in your drafts: Help me. Its timestamp is four this morning.',
        'A manuscript you never drew bears your pen name, in handwriting more practiced than your own.',
    ),
}
for origin, translations in _MEMORIES.items():
    for memory, translation in zip(EPILOGUE_ROOM_POOLS[origin], translations, strict=True):
        EN_EPILOGUE[memory['text']] = translation

_ENDING_LINES = {
    'A': ('Fragments of the core obsession still burn at your fingertips. Dawn enters the rift.',
          'You wake. Beside the pillow, your notebook lies open on the half-sentence you wrote before dreaming.',
          'You take up the pen. The dream has withdrawn to the back of the manuscript, for now.'),
    'B': ('You take the pen from the Scribe. It offers no resistance, as if waiting for an author brave enough to claim it.',
          '{clues} self clues form a sentence in your palm: This is my story, including every part I wrote badly.',
          'You rewrite the ending. When you wake, real birds sing outside, clumsy and out of tune, but belonging to this world.'),
    'C': ('You nod. The Scribe touches the keys and types the final full stop for you.',
          'The story is complete, like all your unfinished stories completed by someone else.',
          'You wake relieved, yet something is missing. You decide not to recall the name of that empty place.'),
    'D': ('You face the Scribe across the manuscript. It offers a pen; you keep your own. Both touch the page together.',
          'The ending moves between two hands, its neatness and your scrawl. Neither erases the other.',
          'You wake holding two pens. At least one rests in your own hand.'),
    'E': ('The deep boundary closes. Without pain, the dream ceases to need you.',
          '{fell_note}', 'Anyone waiting for you to wake receives only a name that will never wake again.'),
    'F': ('The dream closes around your shoulders. There is no waking, no continuation, only a thin silence.',
          'The long night gathers the memories you brought and puts them back in place.',
          'Those outside will only say: what a deep sleep.'),
}
for ending, translations in _ENDING_LINES.items():
    for line, translation in zip(EPILOGUE_ENDINGS[ending]['lines'], translations, strict=True):
        EN_EPILOGUE[line] = translation
