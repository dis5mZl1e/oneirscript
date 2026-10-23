"""Portable grammar images; generated only within the palace."""
_ROWS=(
 ('bookmark','门前书签','门槛','跨过门后，下一次攻击多一分力；六次行动内有效。'),
 ('index','失时索引','记起','再遇见它时，记下它此刻的方位与完整度；六次行动内离开视野也不更新，不揭示全图。'),
 ('fold','隐城折页','边界','走完一步，折出已探索区域通向未知的最近两处边界；只说边界，不记那边有什么。'),
 ('paperweight','留白纸镇','独处','四周没人时，下一次自然恢复多回来一点；总上限不变。'),
 ('lens','阿莱夫透镜','汇聚','命中后，把目标周围一格的导电与火源连接定住三回合；伤害不复制。'),
 ('quill','拒誊羽笔','拒绝','拒绝一次弱控制；十次行动一回，直接创伤不挡。'),
 ('card','蝶梦借阅证','变化后','环境状态与上次记录不同时，视野增加2格，持续4回合；每6次行动至多记一次。'),
 ('testimony','罗生门残页','存疑','命中后记下这个目标：下次打它时，先报出它被推开几格、撞在哪里。'),
)
ITEMS={ 'library.'+key:dict(name=name,category='携带意象',slot='携带意象',rarity='稀有',color='#b08b45',
    description=desc, effect='library_'+key,power=1,loot=False,spawn_realms=('library_palace',),
    grammar_word=word) for key,name,word,desc in _ROWS}

for _key,_icon in zip(ITEMS, ('▯','▥','◩','▰','◉','✒','▱','◪')):
    ITEMS[_key]['icon'] = _icon

ITEMS['library.unbound_page'] = dict(
    name='未装订的书页',category='易逝物',rarity='少见',icon='▱',color='#c5b086',
    description='这一页还没归进任何书里。折痕深处，藏着另一种读法。',
    effect_description='习得一个尚未学会的图书馆专属构想；全部学会后恢复10点想象力。',
    effect='learn_ability',ability_pool='library',max_stack=3,flammable=True,
    loot=False,spawn_realms=('library_palace',))
