"""Finite NPC choices: narrow a bargain or add a paid service, with both clauses independent."""
from .tamper_schema import TamperDefinition, TamperTransition, TamperVariant, TextFragment


# Text tuples are (payment clause, gain clause). Only changes the named clause;
# Also appends one complete service clause. All outcomes are authored, not parsed.
CHOICES = (
    dict(npc='hypnotist', index=1, key='half_waking', anchor='f_cost',
         base_zh=('借十二点心智，', '替你撑开清醒的边沿。'),
         only_zh=('借六点心智，', '替你撑开一半的清醒边沿。'),
         extra_zh='替你合上心智的伤口，另收十二点想象。',
         base_en=('Lend me twelve Mind; ', 'I will widen the edge of your lucidity.'),
         only_en=('lend me six Mind; ', 'I will widen that edge half as much.'),
         extra_en='heal your mind completely, for twelve more Imagination.',
         cost={'mind': 12}, gain={'stat': ['max_lucidity', 6]},
         only_cost={'mind': 6}, only_gain={'stat': ['max_lucidity', 3]},
         extra_cost={'imagination': 12}, extra_gain={'restore': 'mind'},
         base_note=('心智付 12，清醒上限提高 6。', 'Pay 12 Mind; gain 6 maximum Lucidity.'),
         only_note=('心智付 6，清醒上限只提高 3。', 'Pay 6 Mind; gain only 3 maximum Lucidity.'),
         extra_note=('另付想象力 12，心智恢复至上限。', 'Pay 12 more Imagination; restore Mind to its maximum.')),
    dict(npc='scrapper', index=1, key='named_payment', anchor='f_cost',
         base_zh=('药片、响罐凑四件，', '换我这枚雷管。'),
         only_zh=('收一只烟雾罐，', '雷管就归你。'),
         extra_zh='把灰烬里的记忆给你，另收八点心智。',
         base_en=('Bring four doses or disposable devices; ', 'the detonator is yours.'),
         only_en=('bring one smoke canister; ', 'the detonator is yours.'),
         extra_en='give you Ash Memory, for eight more Mind.',
         cost={'consumables': 4}, gain={'item': 'detonator_capsule'},
         only_cost={'items': ['smoke_canister', 1]}, only_gain={'item': 'detonator_capsule'},
         extra_cost={'mind': 8}, extra_gain={'insight': '灰烬记忆'},
         base_note=('交四件摄入物或易逝物，换雷管胶囊。', 'Trade four ingestibles or ephemerals for a detonator capsule.'),
         only_note=('指定交一只烟雾罐，换雷管胶囊；其他物品不抵账。', 'Trade one named smoke canister for a detonator capsule; other items cannot pay.'),
         extra_note=('另付心智 8，学会灰烬记忆；已经学会则不再多得一份。', 'Pay 8 more Mind to learn Ash Memory; an already known insight is not granted twice.')),
    # 夜药剂师：想象 6 → 浓缩咖啡锭（options[1]）。
    # 2026-10-22（E5后续 P3）：代价从「清醒 10」改为「想象 6」——不再收取该
    # 药品要恢复的同一种资源（清醒度），随 npcs.py 的报价一起改。
    dict(npc='night_pharmacist', index=1, key='coffee_choice', anchor='f_cost',
         base_zh=('六点想象，', '换我这一锭浓咖啡。'),
         only_zh=('三点想象，', '换我这半罐温咖啡。'),
         extra_zh='替你合上心智的伤口，另收十二点清醒。',
         base_en=('Six Imagination; ', 'take this espresso tablet.'),
         only_en=('pay three Imagination; ', 'take this half-can of warm coffee instead.'),
         extra_en='heal your mind completely, for twelve more Lucidity.',
         cost={'imagination': 6}, gain={'item': 'espresso_tablet'},
         only_cost={'imagination': 3}, only_gain={'item': 'warm_coffee'},
         extra_cost={'lucidity': 12}, extra_gain={'restore': 'mind'},
         base_note=('想象力付 6，得浓缩咖啡锭；服用时恢复清醒度。', 'Pay 6 Imagination for an espresso tablet, which restores Lucidity when used.'),
         only_note=('想象力付 3，改得半罐温咖啡；服用时恢复想象力。', 'Pay 3 Imagination for warm coffee instead, which restores Imagination when used.'),
         extra_note=('另付清醒度 12，心智恢复至上限。', 'Pay 12 more Lucidity; restore Mind to its maximum.')),
    dict(npc='little_devil', index=2, key='known_thought', anchor='f_gain',
         base_zh=('十二点心智，', '买一个还没见过的念头。'),
         only_zh=('十二点心智，', '买辨认残影的念头。'),
         extra_zh='填满你的想象，另收六点心智。',
         base_en=('Twelve Mind; ', 'buy a thought you have never had.'),
         only_en=('Twelve Mind; ', 'buy the thought that recognizes afterimages.'),
         extra_en='fill your imagination, for six more Mind.',
         cost={'mind': 12}, gain={'random_insight': True},
         only_cost={'mind': 12}, only_gain={'insight': '残影直觉'},
         extra_cost={'mind': 6}, extra_gain={'restore': 'imagination'},
         base_note=('心智付 12，随机学会一个未学洞察。', 'Pay 12 Mind for a random unknown insight.'),
         only_note=('心智付 12，改学残影直觉；已经学会则不再多得一份。', 'Pay 12 Mind for Afterimage Intuition instead; it cannot be learned twice.'),
         extra_note=('另付心智 6，想象力恢复至上限。', 'Pay 6 more Mind; restore Imagination to its maximum.')),
    # ---- 2026-10-17 第四批：真实货架上的既有交易，逐条核对 npcs.py 的
    # option 下标与 cost/gain 字段。每行只改一处真实货架条目，不新开货币。
    # 注意挑选**尚未被既有篡改定义占用**的 option：同一 option 挂两条定义会
    # 让两条补丁互相覆盖（既有 mind_cost 已占 mind_observer trade.3、
    # hypnotist trade.0、scrapper trade.0）。----
    # 催眠师：心智 16 → 洞察「延迟抵达」（options[3]）。
    dict(npc='hypnotist', index=3, key='delayed_insight', anchor='f_cost',
         base_zh=('十六点心智，', '买一份「延迟抵达」的洞察。'),
         only_zh=('十二点心智，', '同一份「延迟抵达」照给。'),
         extra_zh='替你补满心智，另收八点清醒。',
         base_en=('Sixteen Mind; ', 'I will sell you the insight "Delayed Arrival."'),
         only_en=('twelve Mind; ', 'the same "Delayed Arrival" is yours.'),
         extra_en='refill your mind, for eight more Lucidity.',
         cost={'mind': 16}, gain={'insight': '延迟抵达'},
         only_cost={'mind': 12}, only_gain={'insight': '延迟抵达'},
         extra_cost={'lucidity': 8}, extra_gain={'restore': 'mind'},
         base_note=('心智付 16，得洞察「延迟抵达」。',
                    'Pay 16 Mind for the insight "Delayed Arrival".'),
         only_note=('心智付 12，同一洞察照给。', 'Pay 12 Mind for the same insight.'),
         extra_note=('另付清醒度 8，心智恢复至上限。',
                     'Pay 8 more Lucidity; restore Mind to its maximum.')),
    # 夜药剂师：心智 6 → 梦境电解水（options[2]）。
    # 2026-10-22（E5后续 P3）：代价从「想象 10」改为「心智 6」——不再收取该
    # 药品要恢复的同一种资源（想象／清醒）。
    dict(npc='night_pharmacist', index=2, key='electrolyte', anchor='f_cost',
         base_zh=('六点心智，', '换一瓶梦境电解水。'),
         only_zh=('三点心智，', '电解水照给。'),
         extra_zh='告诉你这瓶水兑了什么，另收六点清醒。',
         base_en=('Six Mind; ', 'take one dream electrolyte water.'),
         only_en=('three Mind; ', 'the electrolyte water is still yours.'),
         extra_en='tell you what is dissolved in it, for six more Lucidity.',
         cost={'mind': 6}, gain={'item': 'dream_electrolytes'},
         only_cost={'mind': 3}, only_gain={'item': 'dream_electrolytes'},
         extra_cost={'lucidity': 6}, extra_gain={'insight': '液态亲和'},
         base_note=('心智付 6，得梦境电解水。',
                    'Pay 6 Mind for dream electrolyte water.'),
         only_note=('心智付 3，电解水照给。',
                    'Pay 3 Mind for the same water.'),
         extra_note=('另付清醒度 6，学会「液态亲和」；已经学会则不再多得一份。',
                     'Pay 6 more Lucidity to learn "Liquid Affinity"; it cannot be learned twice.')),
    # 拾荒者：消耗品 2 → 蜂鸣诱饵（options[2]）。
    dict(npc='scrapper', index=2, key='buzz_lure', anchor='f_cost',
         base_zh=('两件药片、响罐或烟雾，', '换一只蜂鸣诱饵。'),
         only_zh=('一件消耗品，', '蜂鸣诱饵照给。'),
         extra_zh='顺着响罐的嗡声替你定神，另收六点心智。',
         base_en=('Two doses, noise cans or smoke; ', 'the buzz lure is yours.'),
         only_en=('one consumable; ', 'the buzz lure is yours.'),
         extra_en='steady you with the hum of the can, for six more Mind.',
         cost={'consumables': 2}, gain={'item': 'buzz_lure'},
         only_cost={'consumables': 1}, only_gain={'item': 'buzz_lure'},
         extra_cost={'mind': 6}, extra_gain={'restore': 'lucidity'},
         base_note=('交两件摄入物或易逝物，换蜂鸣诱饵。',
                    'Trade two ingests or ephemerals for a buzz lure.'),
         only_note=('交一件消耗品，蜂鸣诱饵照给。',
                    'Trade one consumable for the same buzz lure.'),
         extra_note=('另付心智 6，清醒度恢复至上限。',
                     'Pay 6 more Mind; restore Lucidity to its maximum.')),
    # 小魔鬼：清醒 12 → 晨露药剂（options[5]）。
    dict(npc='little_devil', index=5, key='morning_dew', anchor='f_cost',
         base_zh=('十二点清醒，', '换一瓶晨露药剂。'),
         only_zh=('八点清醒，', '晨露药剂照给。'),
         extra_zh='替你把清醒补满，另收六点心智。',
         base_en=('Twelve Lucidity; ', 'take a bottle of morning dew.'),
         only_en=('eight Lucidity; ', 'the morning dew is still yours.'),
         extra_en='refill your lucidity, for six more Mind.',
         cost={'lucidity': 12}, gain={'item': 'morning_dew'},
         only_cost={'lucidity': 8}, only_gain={'item': 'morning_dew'},
         extra_cost={'mind': 6}, extra_gain={'restore': 'lucidity'},
         base_note=('清醒度付 12，得晨露药剂。', 'Pay 12 Lucidity for a bottle of morning dew.'),
         only_note=('清醒度付 8，晨露药剂照给。', 'Pay 8 Lucidity for the same bottle.'),
         extra_note=('另付心智 6，清醒度恢复至上限。',
                     'Pay 6 more Mind; restore Lucidity to its maximum.')),
    # 拾荒的委托人：清醒 10 → 多出来的螺丝（options[1]）。
    dict(npc='scavenger', index=1, key='model_screw', anchor='f_cost',
         base_zh=('十点清醒，', '换一颗多出来的螺丝。'),
         only_zh=('七点清醒，', '那颗螺丝照给。'),
         extra_zh='告诉你拾荒的疾行诀窍，另收六点心智。',
         base_en=('Ten Lucidity; ', 'one spare screw is yours.'),
         only_en=('seven Lucidity; ', 'the same screw is yours.'),
         extra_en="teach you the scrapper's quick-step, for six more Mind.",
         cost={'lucidity': 10}, gain={'item': 'model_screw'},
         only_cost={'lucidity': 7}, only_gain={'item': 'model_screw'},
         extra_cost={'mind': 6}, extra_gain={'insight': '疾行拾荒'},
         base_note=('清醒度付 10，得一颗多出来的螺丝。',
                    'Pay 10 Lucidity for a spare screw.'),
         only_note=('清醒度付 7，那颗螺丝照给。', 'Pay 7 Lucidity for the same screw.'),
         extra_note=('另付心智 6，学会「疾行拾荒」；已经学会则不再多得一份。',
                     'Pay 6 more Mind to learn "Scavenger\'s Sprint"; it cannot be learned twice.')),
    # 织梦酒保：清醒 12 → 洞察「和声耐受」（options[3]）。
    dict(npc='dream_bartender', index=3, key='harmony_insight', anchor='f_cost',
         base_zh=('十二点清醒，', '换一页旧稿上的「和声耐受」。'),
         only_zh=('九点清醒，', '同一页旧稿照给。'),
         extra_zh='替你补满清醒，另收六点心智。',
         base_en=('Twelve Lucidity; ', 'buy the "Harmonic Tolerance" insight from an old draft.'),
         only_en=('nine Lucidity; ', 'the same page is yours.'),
         extra_en='refill your lucidity, for six more Mind.',
         cost={'lucidity': 12}, gain={'insight': '和声耐受'},
         only_cost={'lucidity': 9}, only_gain={'insight': '和声耐受'},
         extra_cost={'mind': 6}, extra_gain={'restore': 'lucidity'},
         base_note=('清醒度付 12，得洞察「和声耐受」。',
                    'Pay 12 Lucidity for the insight "Harmonic Tolerance".'),
         only_note=('清醒度付 9，同一洞察照给。', 'Pay 9 Lucidity for the same insight.'),
         extra_note=('另付心智 6，清醒度恢复至上限。',
                     'Pay 6 more Mind; restore Lucidity to its maximum.')),
    # 催眠师：清醒 16 → 灯塔透镜（options[4]）。
    dict(npc='hypnotist', index=4, key='lighthouse_lens', anchor='f_cost',
         base_zh=('十六点清醒，', '换一枚灯塔透镜。'),
         only_zh=('十二点清醒，', '透镜照给。'),
         extra_zh='替你补满清醒，另收六点心智。',
         base_en=('Sixteen Lucidity; ', 'take one lighthouse lens.'),
         only_en=('twelve Lucidity; ', 'the same lens is yours.'),
         extra_en='refill your lucidity, for six more Mind.',
         cost={'lucidity': 16}, gain={'item': 'lighthouse_lens'},
         only_cost={'lucidity': 12}, only_gain={'item': 'lighthouse_lens'},
         extra_cost={'mind': 6}, extra_gain={'restore': 'lucidity'},
         base_note=('清醒度付 16，得灯塔透镜。',
                    'Pay 16 Lucidity for a lighthouse lens.'),
         only_note=('清醒度付 12，透镜照给。', 'Pay 12 Lucidity for the same lens.'),
         extra_note=('另付心智 6，清醒度恢复至上限。',
                     'Pay 6 more Mind; restore Lucidity to its maximum.')),
    # 拾荒者：消耗品 2 → 烟雾罐（options[3]）。
    dict(npc='scrapper', index=3, key='smoke_canister', anchor='f_cost',
         base_zh=('两件药片、响罐或烟雾，', '换一只烟雾罐。'),
         only_zh=('一件消耗品，', '烟雾罐照给。'),
         extra_zh='替你压稳呼吸，另收六点心智。',
         base_en=('Two doses, noise cans or smoke; ', 'the smoke canister is yours.'),
         only_en=('one consumable; ', 'the smoke canister is yours.'),
         extra_en='steady your breath, for six more Mind.',
         cost={'consumables': 2}, gain={'item': 'smoke_canister'},
         only_cost={'consumables': 1}, only_gain={'item': 'smoke_canister'},
         extra_cost={'mind': 6}, extra_gain={'restore': 'lucidity'},
         base_note=('交两件摄入物或易逝物，换烟雾罐。',
                    'Trade two ingests or ephemerals for a smoke canister.'),
         only_note=('交一件消耗品，烟雾罐照给。',
                    'Trade one consumable for the same smoke canister.'),
         extra_note=('另付心智 6，清醒度恢复至上限。',
                     'Pay 6 more Mind; restore Lucidity to its maximum.')),
)

_LABELS = {
    'hypnotist': (('换清醒的边沿', 'Widen the edge of lucidity'),
                 ('换半份清醒的边沿', 'Widen the edge half as much'),
                 ('请她疗合心智', 'ask her to heal your mind')),
    'scrapper': (('拿四件药片或响罐换雷管胶囊', 'Trade four doses or devices for a detonator'),
                ('拿烟雾罐换雷管胶囊', 'Trade a smoke canister for a detonator'),
                ('带走灰烬记忆', 'take Ash Memory too')),
    'night_pharmacist': (('换浓缩咖啡锭', 'Buy an espresso tablet'),
                        ('换半罐温咖啡', 'Buy warm coffee instead'),
                        ('请她疗合心智', 'ask her to heal your mind')),
    'little_devil': (('买一个未见的念头', 'Buy an unknown thought'),
                    ('买残影直觉', 'Buy Afterimage Intuition'),
                    ('填满想象', 'fill your imagination')),
}


_LABELS_BY_ROW = {
    # 2026-10-17 第四批：每个新增候选单独命名，避免同一位 NPC 的多笔交易
    # 共用一组笼统标签（否则改一条会显示成另一条的效果）。
    ('hypnotist', 'delayed_insight'): (
        ('买延迟抵达的洞察', 'Buy the Delayed Arrival insight'),
        ('只收十二点心智换洞察', 'Twelve Mind for the insight'),
        ('补满心智', 'refill your mind')),
    ('night_pharmacist', 'electrolyte'): (
        ('换梦境电解水', 'Buy dream electrolyte water'),
        ('只收三点心智换水', 'Three Mind for the water'),
        ('加学液态亲和', 'learn Liquid Affinity too')),
    ('scrapper', 'buzz_lure'): (
        ('拿两件消耗品换蜂鸣诱饵', 'Two consumables for the buzz lure'),
        ('拿一件消耗品换蜂鸣诱饵', 'One consumable for the buzz lure'),
        ('定神补满清醒', 'steady you and refill lucidity')),
    ('little_devil', 'morning_dew'): (
        ('换晨露药剂', 'Buy a bottle of morning dew'),
        ('只收八点清醒换药剂', 'Eight Lucidity for the dew'),
        ('补满清醒', 'refill your lucidity')),
    ('scavenger', 'model_screw'): (
        ('换多出来的螺丝', 'Buy the spare screw'),
        ('只收七点清醒换螺丝', 'Seven Lucidity for the screw'),
        ('加学疾行拾荒', 'learn Scavenger\'s Sprint too')),
    ('dream_bartender', 'harmony_insight'): (
        ('买和声耐受的旧稿', 'Buy the Harmonic Tolerance draft'),
        ('只收九点清醒换旧稿', 'Nine Lucidity for the draft'),
        ('补满清醒', 'refill your lucidity')),
    # 2026-10-17 第五批：再补两笔真实货架交易（未与既有定义占用冲突）。
    ('hypnotist', 'lighthouse_lens'): (
        ('清醒换灯塔透镜', 'Trade lucidity for a lighthouse lens'),
        ('只收十二点清醒换透镜', 'Twelve Lucidity for the lens'),
        ('补满清醒', 'refill your lucidity')),
    ('scrapper', 'smoke_canister'): (
        ('拿两件消耗品换烟雾罐', 'Two consumables for the smoke canister'),
        ('拿一件消耗品换烟雾罐', 'One consumable for the smoke canister'),
        ('压稳呼吸', 'steady your breath')),
}


def _definition(row):
    option = f"npc.{row['npc']}.trade.{row['index']}"
    ids = {(False, False): 'base', (True, False): 'only',
           (False, True): 'also', (True, True): 'only_also'}
    variants, transitions = [], []
    # 2026-10-20 §15 第四批：「只」插在整句开头时英文必须大写。词的插入文本
    # 仍是 'only '（句中插入到处在用），只有落在句首这一种位置换首字母——
    # 中文没有大小写，两种语言的插入位置因此保持一致。
    only_at_head = row['anchor'] == 'f_cost'
    for (only, also), identity in ids.items():
        frames, notes = {}, {}
        for language, note_index in (('zh', 0), ('en', 1)):
            cost_text, gain_text = row[('only_' if only else 'base_') + language]
            if language == 'zh':
                # 中文句读之间不留空格（旧版把 ' ' 也拼进来，读出「。 也」）。
                only_token, also_token, joiner = '只', '也', ''
                tail_note = '每人仍只交易一次。'
            else:
                only_token = 'Only ' if only_at_head else 'only '
                also_token, joiner = 'I will also ', ' '
                tail_note = ' Still one trade per instance.'
            fragments = []
            for fragment_id, text in (('f_cost', cost_text), ('f_gain', gain_text)):
                if only and fragment_id == row['anchor']:
                    fragments.append(TextFragment('f_only', only_token))
                fragments.append(TextFragment(fragment_id, text))
            if also:
                fragments.extend((TextFragment('f_join', joiner),
                                  TextFragment('f_also', also_token),
                                  TextFragment('f_extra', row['extra_' + language])))
            frames[language] = tuple(fragments)
            notes[language] = row['only_note' if only else 'base_note'][note_index]
            if also:
                notes[language] += joiner + row['extra_note'][note_index]
            notes[language] += tail_note
        cost = dict(row['only_cost' if only else 'cost'])
        gain = dict(row['only_gain' if only else 'gain'])
        if also:
            for field, amount in row['extra_cost'].items():
                cost[field] = cost.get(field, 0) + amount
            gain.update(row['extra_gain'])
        patch = {} if identity == 'base' else {option: {'cost': cost, 'gain': gain}}
        labels = {}
        if identity != 'base':
            wording = (_LABELS_BY_ROW.get((row['npc'], row['key']))
                       or _LABELS[row['npc']])
            for language, note_index in (('zh', 0), ('en', 1)):
                labels[language] = wording[1 if only else 0][note_index]
                if also:
                    labels[language] += ('，' if language == 'zh' else '; ') + wording[2][note_index]
        variants.append(TamperVariant(identity, frames, patch, notes, labels))
        for word, active, destination in (('only', only, ids[not only, also]),
                                          ('also', also, ids[only, not also])):
            slot = ('slot_drop_' if active else 'slot_') + word
            transitions.append(TamperTransition(f'{identity}:{slot}', identity, destination,
                'delete' if active else 'insert', slot, None if active else word,
                2 if active else 3 if word == 'only' else 4,
                6 if active else 8 if word == 'only' else 10, rewrite=not active or word == 'only'))
    slots = {
        'slot_only': dict(kind='insert', anchor=row['anchor'], insert_fragment='f_only', side='before'),
        'slot_also': dict(kind='insert', anchor='f_gain', insert_fragment='f_also', side='after'),
        'slot_drop_only': dict(kind='delete', fragments=('f_only',)),
        'slot_drop_also': dict(kind='delete', fragments=('f_join', 'f_also', 'f_extra')),
    }
    return TamperDefinition(f"tamper.{row['npc']}.{row['key']}", 'npc', f"npc.{row['npc']}",
        'dialogue', option, 'base', tuple(variants), tuple(transitions), {'zh': slots, 'en': slots})


def npc_choice_definitions():
    return tuple(_definition(row) for row in CHOICES)
