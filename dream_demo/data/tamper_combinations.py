"""Authored finite edit graphs: independent words can coexist and be removed separately.

The graphs are built once at import time. No runtime text parsing, arbitrary
insertion or multiplier accumulation is allowed.
"""
from .tamper_schema import TamperDefinition, TamperTransition, TamperVariant, TextFragment


def _fragments(zh, en):
    return {language: tuple(TextFragment(key, text) for key, text in rows)
            for language, rows in (('zh', zh), ('en', en))}


def _insert(anchor, fragment, side='before'):
    return dict(kind='insert', anchor=anchor, insert_fragment=fragment, side=side)


def _delete(*fragments):
    return dict(kind='delete', fragments=fragments)


def _edge(source, target, word, slot, *, deleting=False, rewrite=False, identity=None):
    return TamperTransition(identity or f'{source}:{slot}', source, target,
                            'delete' if deleting else 'insert', slot,
                            None if deleting else word,
                            2 if deleting or word=='negate' else 4 if word=='also' else 5,
                            6 if deleting or word=='negate' else 10 if word=='also' else 14,
                            rewrite=rewrite)


def _pill_box():
    option='event.pill_box.option.1'
    ids={(0,False):'base',(1,False):'again',(2,False):'shake',
         (0,True):'calm',(1,True):'again_calm',(2,True):'shake_calm'}
    variants=[]; transitions=[]
    for (gain,calm), identity in ids.items():
        zh=[]; en=[('f_label','Pocket the whole box')]
        if gain==1: zh.append(('f_again','再'))
        zh.append(('f_label','把整盒收进口袋'))
        if gain==1: en.append(('f_again',' again'))
        if gain==2:
            zh.append(('f_shake','，再抖出两份'))
            en.append(('f_shake',', then shake it again for two more doses'))
        zh.append(('f_tail','，药味')); en.append(('f_tail','; its stale scent will '))
        if calm:
            zh.append(('f_negate','不')); en.append(('f_negate','not '))
        zh.append(('f_cost','伤心智。')); en.append(('f_cost','hurt your mind.'))
        patch={} if identity=='base' else {option: {'reward_count':2+gain,'mind':0 if calm else -2}}
        note={'zh':f'过期药 {2+gain} 份；'+('药味不再伤心智。' if calm else '心智损失 2 点。')+'药盒仍只领一次。',
              'en':f'{2+gain} expired doses; '+('no Mind loss. ' if calm else 'lose 2 Mind. ')+'The box is still claimed once.'}
        variants.append(TamperVariant(identity,_fragments(zh,en),patch,note))
        if gain==0:
            for to_gain,slot in ((1,'slot_again'),(2,'slot_shake')):
                name=('t_again' if to_gain==1 else 't_shake') if not calm else None
                transitions.append(_edge(identity,ids[to_gain,calm],'again',slot,rewrite=to_gain==2,identity=name))
        else:
            transitions.append(_edge(identity,ids[0,calm],None,'slot_drop_again' if gain==1 else 'slot_drop_shake',deleting=True))
        transitions.append(_edge(identity,ids[gain,not calm],None if calm else 'negate',
                                 'slot_drop_negate' if calm else 'slot_negate',deleting=calm,
                                 identity='t_negate' if identity=='base' else None))
    common={'slot_negate':_insert('f_cost','f_negate'), 'slot_drop_negate':_delete('f_negate'),
            'slot_shake':_insert('f_label','f_shake','after'), 'slot_drop_shake':_delete('f_shake'),
            'slot_drop_again':_delete('f_again')}
    return TamperDefinition('tamper.pill_box.more_pills','event','event.pill_box','option',option,'base',
                            tuple(variants),tuple(transitions),
                            {'zh':{**common,'slot_again':_insert('f_label','f_again')},
                             'en':{**common,'slot_again':_insert('f_label','f_again','after')}},content_version=2)


def _rain():
    option='event.rain_upside_down.option.0'
    ids={(False,False):'base',(True,False):'again',
         (False,True):'also_thunder',(True,True):'again_also_thunder'}
    variants=[]; transitions=[]
    for (again,also),identity in ids.items():
        zh=[];en=[('f_label','Catch a drop')]
        if again:zh.append(('f_again','再'))
        zh.append(('f_label','接一滴'))
        if again:en.append(('f_again',' again'))
        if also:
            zh.extend((('f_join','，'),('f_also','也'),('f_tail','接住一声闷雷')))
            en.extend((('f_join',', and '),('f_also','also '),('f_tail','catch a muffled rumble')))
        patch={} if identity=='base' else {option:{'reward_count':2 if again else 1,'mind':2 if also else 0}}
        note={'zh':f'水珠 {2 if again else 1} 份，清醒度恢复 2 点；'+('雷声让心智恢复 2 点。' if also else '心智不变。')+'仍只接取一次。',
              'en':f'{2 if again else 1} drops, restore 2 Lucidity; '+('restore 2 Mind from the thunder. ' if also else 'Mind is unchanged. ')+'One event use is spent.'}
        variants.append(TamperVariant(identity,_fragments(zh,en),patch,note))
        transitions.append(_edge(identity,ids[not again,also],None if again else 'again',
                                 'slot_drop_again' if again else 'slot_again',deleting=again,
                                 identity='t_again' if identity=='base' else None))
        transitions.append(_edge(identity,ids[again,not also],None if also else 'also',
                                 'slot_drop_also' if also else 'slot_also',deleting=also,rewrite=not also,
                                 identity='t_also' if identity=='base' else None))
    common={'slot_also':_insert('f_label','f_also','after'),
            'slot_drop_also':_delete('f_join','f_also','f_tail'), 'slot_drop_again':_delete('f_again')}
    return TamperDefinition('tamper.rain_upside_down.also_thunder','event','event.rain_upside_down','option',option,'base',
                            tuple(variants),tuple(transitions),
                            {'zh':{**common,'slot_again':_insert('f_label','f_again')},
                             'en':{**common,'slot_again':_insert('f_label','f_again','after')}},content_version=2)


# Each row records an actual old choice, two editable clauses and their fixed
# results. Negative costs and repeated gains stay independent in the graph.
_PAIRED_ROWS=(
    ('broken_meter',1,('等电表停下，余电','补回想象','，跳字','磨去清醒。'),
     ('Wait for the meter to stop. Its last spark ','restores imagination','; the dial will ','erode lucidity.'),
     {'imagination':6,'lucidity':-3},{'imagination':12},{'lucidity':0},''),
    ('paper_moon',0,('','戳破纸月亮','，折痕','割伤心智。'),
     ('','Prick the paper moon','; its crease will ','cut your mind.'),
     {'reward_count':1,'mind':-1},{'reward_count':2},{'mind':0},'残页'),
    ('bath_tide',0,('','接回漩涡里的温水','，漩涡','磨去清醒。'),
     ('','Draw warm water from the whirlpool','; the whirlpool will ','erode lucidity.'),
     {'reward_count':2,'lucidity':-2},{'reward_count':4},{'lucidity':0},'温水'),
    ('fog_organ',1,('琴声','补回想象','，余音','耗去清醒。'),
     ('The song ','restores imagination','; its echo will ','dim lucidity.'),
     {'imagination':5,'lucidity':-2},{'imagination':10},{'lucidity':0},''),
    ('wet_score',1,('休止符','补回清醒','，梦层','随之松动。'),
     ('The rest ','restores lucidity','; the layer will ','loosen around you.'),
     {'lucidity':4,'dissolution':3},{'lucidity':8},{'dissolution':0},''),
    ('model_lamp',1,('灯光','补回想象','，梦层','随之松动。'),
     ('The light ','restores imagination','; the layer will ','loosen around you.'),
     {'imagination':3,'dissolution':4},{'imagination':6},{'dissolution':0},''),
)


def _paired(row):
    name,index,zh_parts,en_parts,base,repeated,negated,reward=row
    option=f'event.{name}.option.{index}'
    ids={(False,False):'base',(True,False):'again',(False,True):'negated',(True,True):'again_negated'}
    variants=[];transitions=[]
    labels={'mind':'心智','lucidity':'清醒度','imagination':'想象力','dissolution':'崩解度'}
    for (again,negate),identity in ids.items():
        frames={}
        for language,parts in (('zh',zh_parts),('en',en_parts)):
            lead,gain,between,cost=parts
            fragments=[('f_lead',lead)]
            if again and language=='zh':fragments.append(('f_again','再'))
            fragments.append(('f_gain',gain))
            if again and language=='en':fragments.append(('f_again',' again'))
            fragments.append(('f_between',between))
            if negate:fragments.append(('f_negate','不' if language=='zh' else 'not '))
            fragments.append(('f_cost',cost))
            frames[language]=tuple(TextFragment(fid,text) for fid,text in fragments)
        values={**base,**(repeated if again else {}),**(negated if negate else {})}
        zh_note='；'.join(f'{reward} {value} 份' if field=='reward_count' else f'{labels[field]} {value:+d}'
                         for field,value in values.items())+'。该处使用次数照常。'
        en_reward={'残页':'torn pages','温水':'warm water'}.get(reward,'reward')
        en_note='; '.join(f'{en_reward} x{value}' if field=='reward_count' else f'{field.title()} {value:+d}'
                         for field,value in values.items())+'. The event use limit is unchanged.'
        variants.append(TamperVariant(identity,frames,{} if identity=='base' else {option:values},
                                      {'zh':zh_note,'en':en_note}))
        for word,active,destination,slot in (
                ('again',again,ids[not again,negate],'again'),
                ('negate',negate,ids[again,not negate],'negate')):
            transitions.append(_edge(identity,destination,None if active else word,
                                     'slot_drop_'+slot if active else 'slot_'+slot,deleting=active,
                                     identity='t_'+word if identity=='base' else None))
    common={'slot_negate':_insert('f_cost','f_negate'),'slot_drop_negate':_delete('f_negate'),
            'slot_drop_again':_delete('f_again')}
    return TamperDefinition(f'tamper.{name}.paired','event',f'event.{name}','option',option,'base',
                            tuple(variants),tuple(transitions),
                            {'zh':{**common,'slot_again':_insert('f_gain','f_again')},
                             'en':{**common,'slot_again':_insert('f_gain','f_again','after')}})


def extend_tamper_content(definitions):
    from .npc_tamper_choices import npc_choice_definitions
    from .event_rule_choices import event_rule_definitions
    from .tamper_three_choices import three_choice_definitions
    replacements={d.text_id:d for d in (_pill_box(),_rain())}
    return (tuple(replacements.get(d.text_id,d) for d in definitions)
            + tuple(_paired(row) for row in _PAIRED_ROWS) + npc_choice_definitions()
            + event_rule_definitions() + three_choice_definitions())
