"""Reviewed three-word edit graphs; repetition affects the main clause only."""
from itertools import product

from .tamper_schema import TamperDefinition, TamperTransition, TamperVariant, TextFragment


WORDS = ('only', 'also', 'again')
FOCUSED_LABELS = {
    'wet_letterbox': ('收下信里的想象，把线头留下', 'Leave the thread and accept the letter\'s imagination'),
    'static_radio': ('听电流带回清醒，把耳机留下', 'Leave the earphone and regain lucidity from the static'),
    'night_ward_round': ('让铃声扶回清醒，把药留下', 'Leave the medicine and regain lucidity from the bell'),
    'sunken_bell': ('听钟声送回想象，把凝固剂留下', 'Leave the coagulant and regain imagination from the bell'),
    'missing_screw': ('记住模型里的想象，把螺丝留下', 'Leave the screw and remember the model\'s imagination'),
    'vault_seed_ledger': ('收下账簿里的清醒，把弹页留下', 'Leave the folded projectile and accept the ledger\'s lucidity'),
    'dream_post_office': ('签收邮包里的清醒，把卷尺留下', 'Leave the tape measure and accept the parcel\'s lucidity'),
    'polaroid_wall': ('看清照片，把键帽留下', 'Leave the keycap and see the photo clearly'),
    'blank_gallery': ('收下灯里的清醒，把灯笼留下', 'Leave the lantern and accept its lucidity'),
    # 2026-10-17 第四批：真实事件 option.0 与真实 reward。
    'rusty_faucet': ('收下想象，把玻璃瓶留下', 'Leave the glass bottle and accept the imagination'),
    'star_clearance': ('买下想象，把玻璃样品留下', 'Leave the sample and accept the imagination'),
}
ROWS = (
    dict(name='wet_letterbox', reward='loose_thread', fixed=10,
         lead=('拆信时，信封', 'When opened, the envelope will '),
         main=('留下一根线头和三点想象，梦多松动五分。',
               'leave a loose thread and three Imagination, adding five Dissolution.'),
         focus=('留下六点想象，不交出线头；梦仍多松动五分。',
                'leave six Imagination and no thread, still adding five Dissolution.'),
         extra=('带走三点清醒，替心智缝上三针。',
                'take three Lucidity to restore three Mind.'),
         base=dict(imagination=3, dissolution=5),
         focused=dict(imagination=6, dissolution=5), extra_values=dict(mind=3, lucidity=-3)),
    dict(name='static_radio', reward='single_earphone', fixed=10,
         lead=('报上名字，电台', 'Upon hearing your name, the radio will '),
         main=('递来一只耳机，梦多松动五分。',
               'give one earphone, adding five Dissolution.'),
         focus=('让六点清醒穿过电流，不留下耳机；梦仍多松动五分。',
                'restore six Lucidity and leave no earphone, still adding five Dissolution.'),
         extra=('借走三点心智，送回四点想象。',
                'take three Mind to restore four Imagination.'),
         base=dict(dissolution=5), focused=dict(lucidity=6, dissolution=5),
         extra_values=dict(imagination=4, mind=-3)),
    dict(name='night_ward_round', reward='unlabeled_sedative', fixed=10,
         lead=('按下铃，值夜人', 'When the bell rings, the night attendant will '),
         main=('留下一份镇静药，梦多松动四分。',
               'leave one sedative, adding four Dissolution.'),
         focus=('扶回五点清醒，不留下药；梦仍多松动四分。',
                'restore five Lucidity and leave no medicine, still adding four Dissolution.'),
         extra=('借走三点想象，替心智缝上三针。',
                'take three Imagination to restore three Mind.'),
         base=dict(dissolution=4), focused=dict(lucidity=5, dissolution=4),
         extra_values=dict(mind=3, imagination=-3)),
    dict(name='sunken_bell', reward='void_coagulant', fixed=10,
         lead=('撞响沉钟，钟声', 'When struck, the sunken bell will '),
         main=('带走两点心智，留下一份凝固剂；梦多松动十分。',
               'take two Mind and leave one coagulant, adding ten Dissolution.'),
         focus=('留下六点想象，不交出凝固剂；仍带走两点心智，梦多松动十分。',
                'restore six Imagination and leave no coagulant, still taking two Mind and adding ten Dissolution.'),
         extra=('借走三点想象，扶回五点清醒。',
                'take three Imagination to restore five Lucidity.'),
         base=dict(mind=-2, dissolution=10),
         focused=dict(mind=-2, imagination=6, dissolution=10),
         extra_values=dict(lucidity=5, imagination=-3)),
    dict(name='missing_screw', reward='model_screw', fixed=10,
         lead=('拧下螺丝，模型', 'When the screw is loosened, the model will '),
         main=('留下一颗备用螺丝。', 'leave one spare screw.'),
         focus=('把四点想象送回手心，不留下螺丝。',
                'restore four Imagination and leave no screw.'),
         extra=('借走三点清醒，让心智恢复四点。',
                'take three Lucidity to restore four Mind.'),
         base={}, focused=dict(imagination=4), extra_values=dict(mind=4, lucidity=-3)),
    dict(name='vault_seed_ledger', reward='folded_projectile', fixed=0,
         lead=('接过书页，账簿', 'When a page is accepted, the ledger will '),
         main=('递来一张折好的弹页。', 'give one folded projectile.'),
         focus=('让清醒恢复四点，不交出弹页。',
                'restore four Lucidity and leave no folded projectile.'),
         extra=('借走三点心智，送回四点想象。',
                'take three Mind to restore four Imagination.'),
         base={}, focused=dict(lucidity=4), extra_values=dict(imagination=4, mind=-3)),
    dict(name='dream_post_office', reward='tape_measure', fixed=10,
         lead=('签下名字，包裹', 'When signed for, the parcel will '),
         main=('留下一把卷尺，梦多松动五分。', 'leave a tape measure, adding five Dissolution.'),
         focus=('送回六点清醒，不留下卷尺；梦仍多松动五分。',
                'restore six Lucidity and leave no tape measure, still adding five Dissolution.'),
         extra=('借走三点心智，把四点想象寄回来。',
                'take three Mind to send back four Imagination.'),
         base=dict(dissolution=5), focused=dict(lucidity=6, dissolution=5),
         extra_values=dict(imagination=4, mind=-3)),
    dict(name='polaroid_wall', reward='old_keycap', fixed=10,
         lead=('揭下一张照片，墙', 'When a photo is peeled off, the wall will '),
         main=('留下一枚键帽，梦多松动四分。', 'leave a keycap, adding four Dissolution.'),
         focus=('让五点清醒从照片里回来，不留下键帽；梦仍多松动四分。',
                'restore five Lucidity from the photo and leave no keycap, still adding four Dissolution.'),
         extra=('借走三点想象，抚平三点心智。', 'take three Imagination to restore three Mind.'),
         base=dict(dissolution=4), focused=dict(lucidity=5, dissolution=4),
         extra_values=dict(mind=3, imagination=-3)),
    dict(name='blank_gallery', reward='night_lantern', fixed=10,
         lead=('站在空白画前，画框', 'Before the blank canvas, the frame will '),
         main=('递来一盏无光灯笼。', 'give one unlit lantern.'),
         focus=('照亮四点清醒，不留下灯笼。', 'restore four Lucidity and leave no lantern.'),
         extra=('借走三点心智，让四点想象填进空白。',
                'take three Mind to fill the blank with four Imagination.'),
         base={}, focused=dict(lucidity=4), extra_values=dict(imagination=4, mind=-3)),
    # ---- 2026-10-17 第四批：真实事件 option.0 与真实 reward ----
    # 生锈的水龙头：玻璃瓶、清醒 −1（无选项崩解；地点基值默认 10）。
    dict(name='rusty_faucet', reward='glass_bottle', fixed=10,
         lead=('拧开龙头，水管', 'When the tap is opened, the pipe will '),
         main=('灌来一只玻璃瓶，磨去一点清醒。',
               'fill a glass bottle and erode one Lucidity.'),
         focus=('让六点想象回到手心，把玻璃瓶留下。',
                'restore six Imagination and leave the glass bottle.'),
         extra=('借走三点心智，送回四点清醒。',
                'take three Mind to restore four Lucidity.'),
         base=dict(lucidity=-1), focused=dict(imagination=6),
         extra_values=dict(mind=-3, lucidity=4)),
    # 星星大甩卖：清醒玻璃、心智 −2（无选项崩解；地点基值默认 10）。
    dict(name='star_clearance', reward='clear_glass', fixed=10,
         lead=('买下那颗样品，摊主', 'Buying the last sample, the seller will '),
         main=('收下两点心智，递来一小片清醒玻璃。',
               'take two Mind and hand over a shard of clear glass.'),
         focus=('让两点想象回到手边，把玻璃样品留下。',
                'restore two Imagination and leave the glass sample.'),
         extra=('借走三点清醒，替心智补回三点。',
                'take three Lucidity to restore three Mind.'),
         base=dict(mind=-2), focused=dict(imagination=2),
         extra_values=dict(lucidity=-3, mind=3)),
)


def _identity(flags):
    return '_'.join(word for word, active in zip(WORDS, flags) if active) or 'base'


def _definition(row):
    option_id = 'event.' + row['name'] + '.option.0'
    variants, transitions = [], []
    labels = {'zh': ('心智', '清醒度', '想象力', '崩解度'),
              'en': ('Mind', 'Lucidity', 'Imagination', 'Dissolution')}
    for flags in product((False, True), repeat=3):
        only, also, again = flags
        identity = _identity(flags)
        main = row['focused'] if only else row['base']
        values = {key: main.get(key, 0) * (2 if again else 1)
                  + (row['extra_values'].get(key, 0) if also else 0)
                  for key in ('mind', 'lucidity', 'imagination', 'dissolution')}
        values['reward_count'] = 0 if only else 2 if again else 1
        frames, notes = {}, {}
        for language, offset in (('zh', 0), ('en', 1)):
            fragments = [TextFragment('f_lead', row['lead'][offset])]
            if only:
                fragments.append(TextFragment('f_only', '只' if language == 'zh' else 'only '))
            fragments.append(TextFragment('f_main', row['focus' if only else 'main'][offset]))
            if again:
                fragments.extend((TextFragment('f_again', '再' if language == 'zh' else ' Again, it will '),
                                  TextFragment('f_extra_again', '照前一句的约定，添一份所得，也添一份代价。'
                                               if language == 'zh' else 'repeat the main clause, with the same gain and loss.')))
            if also:
                fragments.extend((TextFragment('f_also', '也' if language == 'zh' else ' It will also '),
                                  TextFragment('f_extra_also', row['extra'][offset])))
            frames[language] = tuple(fragments)
            amounts = [values[key] for key in ('mind', 'lucidity', 'imagination', 'dissolution')]
            amounts[-1] += row['fixed']
            note = ('，' if language == 'zh' else ', ').join(
                f'{label} {amount:+d}' for label, amount in zip(labels[language], amounts) if amount)
            note += (('；不领取实物' if only else f'；领取 {values["reward_count"]} 份实物')
                     if language == 'zh' else ('; no item reward' if only else f'; {values["reward_count"]} item reward(s)'))
            if row['fixed']:
                note += (f'（含地点原有崩解 {row["fixed"]}）' if language == 'zh'
                         else f' (including {row["fixed"]} original site Dissolution)')
            note += ('。“再”只重复前一句的所得与代价，“也”的交换只做一次；地点次数不增加。恢复受上限限制，损失最低降至零。'
                     if language == 'zh' else '. Again repeats only the main gain and loss; the Also exchange happens once. Original uses do not increase. Recovery is capped; losses stop at zero.')
            notes[language] = note
        option_labels = ({language: FOCUSED_LABELS[row['name']][offset]
                          for language, offset in (('zh', 0), ('en', 1))} if only else {})
        variants.append(TamperVariant(identity, frames, {} if identity == 'base' else {option_id: values},
                                      notes, option_label_by_language=option_labels))
        for index, word in enumerate(WORDS):
            destination = list(flags)
            destination[index] = not flags[index]
            deleting = flags[index]
            slot = ('slot_drop_' if deleting else 'slot_') + word
            cost, chaos = {'only': (3, 8), 'also': (4, 10), 'again': (5, 14)}[word]
            transitions.append(TamperTransition(identity + ':' + slot, identity, _identity(destination),
                'delete' if deleting else 'insert', slot, None if deleting else word,
                2 if deleting else cost, 6 if deleting else chaos, rewrite=not deleting or word == 'only'))
    slots = {
        'slot_only': dict(kind='insert', anchor='f_main', insert_fragment='f_only', side='before'),
        'slot_also': dict(kind='insert', anchor='f_main', insert_fragment='f_also', side='after'),
        'slot_again': dict(kind='insert', anchor='f_main', insert_fragment='f_again', side='after'),
        'slot_drop_only': dict(kind='delete', fragments=('f_only',)),
        'slot_drop_also': dict(kind='delete', fragments=('f_also', 'f_extra_also')),
        'slot_drop_again': dict(kind='delete', fragments=('f_again', 'f_extra_again')),
    }
    return TamperDefinition('tamper.' + row['name'] + '.three_choices', 'event', 'event.' + row['name'],
                            'rule', option_id, 'base', tuple(variants), tuple(transitions),
                            {'zh': slots, 'en': slots})


def three_choice_definitions():
    return tuple(_definition(row) for row in ROWS)
