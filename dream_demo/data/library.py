"""Literary identities and authored second-region encounter values."""
_ROWS = (
 ('reader','未借出的读者','Q',9,4,('question',)),
 ('threshold','门前迟疑者','カ',10,4,('threshold',)),
 ('page','倒写的页码','Ж',10,4,('ink',)),
 ('narrator','擦去的旁白','ぬ',11,4,('omit',)),
 ('index','迟到的索引','문',11,4,('return',)),
 ('lamp','借光的校对者','灯',10,4,('lamp',)),
 ('foldwalker','折页行者','ろ',11,4,('foldstep',)),
 ('binder','散页装订者','책',12,4,('bind',)),
 ('scribe','无人称抄写员','藏',18,5,('stroke','revision')),
 ('witness','多版本见证','꿈',18,5,('echo',)),
 ('refuser','拒绝誊清者','א',19,5,('blank',)),
 ('core','未尽目录','未',80,5,('index_line','echo','delete','last_page')),
)
LIBRARY_ANOMALIES = {}
LIBRARY_BINDINGS = {}
LIBRARY_DESCRIPTIONS = {
 'reader': '它捧着一本谁都没借过的书，目光越过书页追着你看。',
 'threshold': '它在一道看不见的门槛前来回踱步，等谁先迈过去。',
 'page': '一页页码印反了，墨从字的背面渗出来。',
 'narrator': '它讲到一半就停笔，剩下的话被擦得只剩一道白痕。',
 'index': '索引慢了半拍，才翻到你所在的那一页。',
 'lamp': '它提着一盏借来的灯；光走到哪儿，哪儿就欠它一回。',
 'foldwalker': '它走过的地方，书页似的地面留下一道折痕。',
 'binder': '它抱着一摞永远装订不完的散页，走到哪儿收到哪儿。',
 'scribe': '它抄写一切，唯独不抄自己；笔下只落下划线和校订的记号。',
 'witness': '同一件事，它能誊出好几个互相出入的版本。',
 'refuser': '它递来的稿纸上全是空白——它拒绝誊清任何一个字。',
 'core': '一部永远差最后一页的目录。它的条目都空着，等你被写进去。',
}
for i, (key,name,glyph,hp,power,skills) in enumerate(_ROWS):
    aid = 'library.'+key
    tier = 2 if i == 11 else 1 if i >= 8 else 0
    LIBRARY_ANOMALIES[aid] = dict(name=name,description=LIBRARY_DESCRIPTIONS[key],
        glyph=glyph,anomaly_kind=('普通异象','强烈异象','核心执念')[tier],integrity=hp,power=power,
        trauma_type='心智创伤',move_time=1.2,attack_time=1.3,vision=6 if tier<2 else 8,
        communicates=False,drop_id=None,dissolution_reward=(8,12,16)[tier],layers=(16,22),pool=False,
        spawn_realms=('library_palace',),color=f"#{int(('214f42','722f40','705522')[tier],16)+i+1:06x}",
        final_realm_stats=True,phase_thresholds=(.55,) if tier==2 else (),skill='、'.join({'question':'短距追问','threshold':'阈限','ink':'错页','omit':'省略','return':'回目','lamp':'引灯','foldstep':'折步','bind':'收页','stroke':'划线','revision':'校订','echo':'异文誊影','blank':'留白','index_line':'归目','delete':'删改','last_page':'最后一页'}[key] for key in skills))
    LIBRARY_BINDINGS[aid] = tuple('library.'+s for s in skills)
# key, name, tier, cd, W, range, cell cap, damage, duration
LIBRARY_SKILLS = (
 ('question','短距追问',0,5,1,4,4,5,0),('threshold','阈限',0,7,1,2,1,0,2),
 ('ink','错页',0,6,1,4,1,0,3),('omit','省略',0,8,1,4,1,0,0),
 ('return','回目',0,7,1,3,2,0,0),('lamp','引灯',0,8,1,4,1,0,2),
 ('foldstep','折步',0,7,1,4,1,0,0),('bind','收页',0,9,1,2,2,0,2),
 ('stroke','划线',1,7,1,6,6,6,0),('revision','校订',1,10,1,4,1,0,2),
 ('echo','异文誊影',1,10,1,5,2,0,8),('blank','留白',1,9,1,2,2,0,2),
 ('index_line','归目',2,5,1,7,7,7,2),('delete','删改',2,7,1,6,2,0,3),
 ('last_page','最后一页',2,9,2,7,7,7,0),
)
LIBRARY_FLOOR_NAMES=('借阅之门','失时长廊','不可见庭院','众声抄写宫','最后一册')
LIBRARY_HINTS=(
 '书架能挡住视线，推书车挪动之后，遮挡也跟着变；中间那条通道始终敞着。',
 '页码可以重排。湿墨只泼在侧路上；横着走的索引廊遇不上长线。',
 '同一座庭院开着一排不同的窗口。灯光对两边都亮；干燥回廊不沾水，也不导电。',
 '隔间把每个声音分开存放。纸堆有限，书车可以来回推；校勘纯属自愿。',
 '目录已经为别的名字写好了注脚，只剩你那一栏空着。三份记录随时可读；按下确认，战斗才开始。',
)

LIBRARY_FLOOR_POOLS = (tuple(LIBRARY_ANOMALIES)[:8],)*4
LIBRARY_STRONG_IDS = tuple(LIBRARY_ANOMALIES)[8:11]
