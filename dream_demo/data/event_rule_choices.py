"""Finite rule edits with authored resource and progression tradeoffs."""
from .tamper_schema import TamperDefinition, TamperTransition, TamperVariant, TextFragment


RULES = (
    dict(name='tide_clock', index=0, word='again', fixed_dissolution=10,
         lead=('涨潮时，', 'At high tide, the clock will '),
         main=('钟会卷走五点想象，留下一枚燃烧瓶。', 'take five Imagination and leave a fire bottle.'),
         focus=('卷走三点心智，想象留在岸上；燃烧瓶仍会漂来。',
                'take three Mind, leaving Imagination ashore; the fire bottle will still arrive.'),
         extra=('等同一场潮回来，连同它带走的东西。',
                'bring the same tide, with the same loss and gift.'),
         patches=(dict(mind=0, imagination=-5, reward_count=1),
                  dict(mind=-3, imagination=0, reward_count=1),
                  dict(mind=0, imagination=-10, reward_count=2),
                  dict(mind=-6, imagination=0, reward_count=2))),
    dict(name='mirror_interview', index=1, word='also', fixed_dissolution=10,
         lead=('交白卷时，镜中人', 'For a blank answer, the reflection will '),
         main=('会替心智缝上三针，梦向下松动五分。', 'heal three Mind; the dream loosens by five.'),
         focus=('替清醒缝上六针，心智照原样；梦仍向下松动五分。',
                'heal six Lucidity, leaving Mind as it was; the dream still loosens by five.'),
         extra=('借走三点想象，另替心智缝上三针。',
                'borrow three Imagination to heal three more Mind.'),
         patches=(dict(mind=3, lucidity=0, imagination=0, dissolution=5),
                  dict(mind=0, lucidity=6, imagination=0, dissolution=5),
                  dict(mind=6, lucidity=0, imagination=-3, dissolution=5),
                  dict(mind=3, lucidity=6, imagination=-3, dissolution=5))),
    dict(name='last_train_window', index=1, word='also', fixed_dissolution=10,
         lead=('看着站台落后，车窗', 'As the platform falls behind, the window will '),
         main=('会抚平两点心智，梦向下松动五分。', 'heal two Mind; the dream loosens by five.'),
         focus=('抚平四点心智，不再多落下那五分的梦。', 'heal four Mind, without the extra five Dissolution.'),
         extra=('带走三点清醒，让六点想象从玻璃里回来。',
                'take three Lucidity and let six Imagination return through the glass.'),
         patches=(dict(mind=2, lucidity=0, imagination=0, dissolution=5),
                  dict(mind=4, lucidity=0, imagination=0, dissolution=0),
                  dict(mind=2, lucidity=-3, imagination=6, dissolution=5),
                  dict(mind=4, lucidity=-3, imagination=6, dissolution=0))),
    dict(name='silent_library', index=0, word='again', fixed_dissolution=8,
         lead=('每借一本书，借阅卡', 'For each borrowed book, the card will '),
         main=('会让梦再向下松动八分。', 'loosen the dream by eight more.'),
         focus=('剥下四点心智，不再让梦继续松动。',
                'take four Mind, without loosening the dream further.'),
         extra=('照同一条借阅约定，递来第二本书。',
                'lend a second book under the same terms.'),
         patches=(dict(mind=0, imagination=0, dissolution=8, reward_count=1),
                  dict(mind=-4, imagination=0, dissolution=0, reward_count=1),
                  dict(mind=0, imagination=0, dissolution=16, reward_count=2),
                  dict(mind=-8, imagination=0, dissolution=0, reward_count=2))),
    # ---- 2026-10-17 第四批：真实事件 option 与真实 reward／崩解口径 ----
    # 静电里的电台 options[1]（reward_id=single_earphone → old_keycap、崩解 4）。
    dict(name='static_choir', index=1, word='again', fixed_dissolution=10,
         lead=('录下这段调音时，', 'Recording the choir, the tape will '),
         main=('会留下一枚旧键帽，梦多松动四分。',
               'leave one old keycap, adding four Dissolution.'),
         focus=('留下那枚旧键帽，梦不再多松动那四分。',
                'leave that old keycap, without the extra four Dissolution.'),
         extra=('照同一盘带子再录一遍，键帽多一枚。',
                'record the same tape once more for a second keycap.'),
         patches=(dict(reward_count=1, dissolution=4),
                  dict(reward_count=1, dissolution=0),
                  dict(reward_count=2, dissolution=8),
                  dict(reward_count=2, dissolution=0))),
    # 拾荒者的提箱 options[0]（reward_id=glass_bottle、想象 −4；提箱有 2 次使用）。
    dict(name='scrapper_case', index=0, word='again', fixed_dissolution=10,
         lead=('打开提箱时，箱盖', 'When the case is opened, its lid will '),
         main=('会收下四点想象，递来一只玻璃瓶。',
               'take four Imagination and offer one glass bottle.'),
         focus=('收两点想象，仍递来一只玻璃瓶。',
                'take two Imagination and still offer one glass bottle.'),
         extra=('把箱底的备瓶一并算给你，想象多收四点。',
                'add the spare bottle from the bottom for four more Imagination.'),
         patches=(dict(imagination=-4, reward_count=1),
                  dict(imagination=-2, reward_count=1),
                  dict(imagination=-8, reward_count=2),
                  dict(imagination=-4, reward_count=2))),
)


def _definition(row):
    word = row['word']
    option = f"event.{row['name']}.option.{row['index']}"
    identities = {(False, False): 'base', (True, False): 'only',
                  (False, True): word, (True, True): 'only_' + word}
    variants, transitions = [], []
    for (only, extra), identity in identities.items():
        patch = row['patches'][int(only) + 2 * int(extra)]
        frames, notes = {}, {}
        for language, offset in (('zh', 0), ('en', 1)):
            fragments = [TextFragment('f_lead', row['lead'][offset])]
            if only:
                fragments.append(TextFragment('f_only', '只' if language == 'zh' else 'only '))
            fragments.append(TextFragment('f_main', row['focus' if only else 'main'][offset]))
            if extra:
                fragments.extend((TextFragment('f_join', ' '),
                                  TextFragment('f_' + word, ('再' if word == 'again' else '也')
                                               if language == 'zh' else ('Again, ' if word == 'again' else 'It will also ')),
                                  TextFragment('f_extra', row['extra'][offset])))
            frames[language] = tuple(fragments)
            labels = ('心智', '清醒度', '想象力', '崩解度') if language == 'zh' else (
                'Mind', 'Lucidity', 'Imagination', 'Dissolution')
            amounts = [patch.get(key, 0) for key in ('mind', 'lucidity', 'imagination', 'dissolution')]
            amounts[-1] += row['fixed_dissolution']
            # 先收集再拼接：只改崩解（其余为 0）的变体不会得到以「；」开头的残句。
            parts = [f'{label} {amount:+d}' for label, amount in zip(labels, amounts) if amount]
            if patch.get('reward_count'):
                parts.append(('领取份数 ' if language == 'zh' else 'reward quantity ')
                             + str(patch['reward_count']))
            note = ('，' if language == 'zh' else '; ').join(parts)
            if row['fixed_dissolution']:
                fixed = row['fixed_dissolution']
                note += (f'（含地点原有崩解 {fixed}）' if language == 'zh'
                         else f' (including the original site dissolution of {fixed})')
            notes[language] = note + ('。仍只消耗本次回应，原次数不增加；恢复受上限限制，损失最低降至零。'
                if language == 'zh' else '. Still one response; original uses do not increase. Recovery is capped; losses stop at zero.')
        variants.append(TamperVariant(identity, frames, {} if identity == 'base' else {option: dict(patch)}, notes))
        for token, active, destination in (
                ('only', only, identities[not only, extra]),
                (word, extra, identities[only, not extra])):
            cost, chaos = (3, 8) if token == 'only' else (5, 14) if token == 'again' else (4, 10)
            slot = ('slot_drop_' if active else 'slot_') + token
            transitions.append(TamperTransition(identity + ':' + slot, identity, destination,
                'delete' if active else 'insert', slot, None if active else token,
                2 if active else cost, 6 if active else chaos,
                rewrite=not active or token == 'only'))
    slots = {
        'slot_only': dict(kind='insert', anchor='f_main', insert_fragment='f_only', side='before'),
        'slot_' + word: dict(kind='insert', anchor='f_main', insert_fragment='f_' + word, side='after'),
        'slot_drop_only': dict(kind='delete', fragments=('f_only',)),
        'slot_drop_' + word: dict(kind='delete', fragments=('f_join', 'f_' + word, 'f_extra')),
    }
    return TamperDefinition(f"tamper.{row['name']}.rule_choices", 'event', 'event.' + row['name'],
        'rule', option, 'base', tuple(variants), tuple(transitions), {'zh': slots, 'en': slots})


def event_rule_definitions():
    return tuple(_definition(row) for row in RULES)
