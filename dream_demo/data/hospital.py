"""Exclusive clinical encounters and their final third-region tuning.

These authored values are not main-dream depth bases. Shared difficulty modifiers
still apply once, but neither subfloor HP scaling nor regional skill scaling does.
"""

_ROWS = (
    ('membrane', '膜泡球', '⊙', 8, 5, '心智创伤', 1.2, 'pathogen', ()),
    ('capsid', '衣壳针', '↟', 9, 6, '清醒创伤', 1.3, 'pathogen', ('needle',)),
    ('sporebud', '孢芽团', '♧', 9, 4, '心智创伤', 1.4, 'pathogen', ('spore_dust',)),
    ('filament', '菌丝束', '⋈', 11, 6, '心智创伤', 1.3, 'pathogen', ('filament',)),
    ('syringe', '游走注射器', '⇅', 11, 7, '清醒创伤', 1.2, 'device', ('syringe_dash',)),
    ('forceps', '缝合钳', '⋔', 13, 8, '心智创伤', 1.3, 'device', ('forceps_pull',)),
    ('listener', '悬浮听诊盘', 'θ', 9, 4, '清醒创伤', 1.5, 'device', ('listen',)),
    ('dripstand', '自行输液架', '⊤', 14, 6, '心智创伤', 1.4, 'device', ('drip',)),
    ('spore_crown', '孢子冠', '✺', 18, 8, '心智创伤', 1.4, 'pathogen', ('spore_dust', 'membrane_guard')),
    ('blade_disc', '刀片转盘', '✣', 22, 9, '清醒创伤', 1.3, 'device', ('blade_arc',)),
    ('scan_halo', '过曝扫描环', '⌾', 19, 7, '清醒创伤', 1.4, 'device', ('scan_line',)),
    ('core_sterile_grace', '无菌的恩典', '⊚', 64, 7, '清醒创伤', 1.3, 'device', ('white_cut', 'ring_wash', 'core_infusion', 'reopen')),
)

HOSPITAL_ANOMALIES = {}
HOSPITAL_BINDINGS = {}
for index, (key, name, glyph, hp, power, channel, attack, bio, skills) in enumerate(_ROWS):
    aid = 'hospital.'+key
    tier = 2 if index == 11 else 1 if index >= 8 else 0
    HOSPITAL_ANOMALIES[aid] = {
        'name': name, 'description': f'至白疗所中的{name}，由{("病原体" if bio == "pathogen" else "医疗器械")}意象凝聚。',
        'glyph': glyph, 'anomaly_kind': ('普通异象', '强烈异象', '核心执念')[tier],
        'integrity': hp, 'power': power, 'trauma_type': channel,
        'move_time': 1.3 if tier == 2 else 1.2, 'attack_time': attack,
        'vision': 8 if tier == 2 else 6, 'communicates': False,
        'drop_id': None, 'dissolution_reward': (8,12,16)[tier], 'layers': (21, 26),
        'pool': False, 'spawn_realms': ('white_sanatorium',), 'biological_tags': (bio,),
        'color': f"#{int('52768c' if bio == 'device' else '748f67',16)+index+1:06x}",
        'skill': '、'.join(skills), 'final_realm_stats': True,
        'phase_thresholds': (.7, .35) if tier == 2 else (),
        'trait': 'hospital_retreat' if key == 'membrane' else '',
    }
    HOSPITAL_BINDINGS[aid] = tuple('hospital.'+s for s in skills)

# key, title, tier, CD, windup, range, cells, damage, channel, recovery, FX
HOSPITAL_SKILLS = (
    ('needle', '衣壳针线', 0, 7, 1, 5, 5, 6, '清醒', 1, 'needle'),
    ('spore_dust', '有限产尘', 0, 9, 1, 4, 4, 0, '无', 1, 'field'),
    ('filament', '菌丝迟线', 0, 8, 1, 4, 2, 0, '无', 1, 'needle'),
    ('syringe_dash', '注射推进', 0, 8, 1, 4, 3, 7, '清醒', 1, 'needle'),
    ('forceps_pull', '缝合牵引', 0, 8, 1, 3, 3, 0, '无', 1, 'needle'),
    ('listen', '听诊广播', 0, 9, 1, 6, 1, 0, '无', 1, 'field'),
    ('drip', '脑脊滴注', 0, 9, 1, 4, 3, 0, '无', 1, 'field'),
    ('membrane_guard', '短时菌膜', 1, 10, 1, 3, 1, 0, '无', 1, 'field'),
    ('blade_arc', '刀片弧扫', 1, 8, 1, 3, 3, 10, '清醒', 1, 'needle'),
    ('scan_line', '局部过曝扫描', 1, 9, 1, 6, 6, 9, '清醒', 1, 'needle'),
    ('white_cut', '白昼切线', 2, 7, 1, 7, 7, 9, '清醒', 1, 'needle'),
    ('ring_wash', '净相环洗', 2, 9, 2, 3, 8, 5, '心智', 1, 'field'),
    ('core_infusion', '回流配液', 2, 10, 1, 4, 3, 0, '无', 1, 'field'),
    ('reopen', '重开耗材', 2, 12, 2, 5, 1, 0, '无', 1, 'field'),
)

HOSPITAL_SKILL_EFFECTS = {
    'needle': '射出至多五格的针线，命中一次清醒创伤6；实体墙会截断针线。',
    'spore_dust': '抖出胞尘：孢芽团每次4单位、分至多两格，孢子冠每次6单位、分至多四格；一场至多抖出12单位。',
    'filament': '在目标附近布下至多两格菌丝迟线；踩中的目标拖上两回合迟拍。',
    'syringe_dash': '沿直线推进至多两格，撞上实体便停；警示线上的目标吃一次清醒创伤7。',
    'forceps_pull': '预告之后，把仍留在短线上的目标拖近一格；拖不进墙，也不挤进已有人的格子。',
    'listen': '把它最后一次看清的位置广播给同伴；广播之后不再更新。',
    'drip': '往至多三格滴下共2单位脑脊液；一场至多滴6单位。',
    'membrane_guard': '给自己裹上三回合菌膜；替它挡下一次命中的1点创伤。菌膜可以洗掉。',
    'blade_arc': '沿目标附近三格扫出一道弧，命中一次清醒创伤10；扫完至少停一回合。',
    'scan_line': '射出至多六格扫描线，命中清醒创伤9；它自己周围半径2被照亮，三回合后恢复。',
    'white_cut': '锁定至多七格细线，落线时命中一次清醒创伤9。',
    'ring_wash': '预告两回合后，在周围八格扬起一圈稀疏水环；敌我的一项可洗征兆被缩短3，并受心智创伤5。',
    'core_infusion': '往首次确定的至多三个槽格注液，每次6单位、总量12；流出的脑脊液对敌我都有帮助。',
    'reopen': '第二阶段起，预告两回合后召出一只膜泡球（完整度6、清醒创伤3）；至多两次，同时至多一只，膜泡没有溶解奖励。',
}

_DESCRIPTIONS = {
    'membrane': '薄膜裹着一滴安静的液体，边缘却一直颤动。它碰到你便缩回一格。',
    'capsid': '透明衣壳像细小针尖排列。它射出针线前，地板会先留下一道提示。',
    'sporebud': '一簇洁白孢芽，像没有开封的培养样本。',
    'filament': '菌丝束沿地板接缝舒展，像误写在白瓷上的缝线。',
    'syringe': '细长器械自行滑行，针尖总比身体先转向。',
    'forceps': '一对没有手握住的钳口，在空中轻轻开合。',
    'listener': '金属听诊盘浮在一条看不见的软管末端。',
    'dripstand': '银架推着最后几滴浅蓝配液，滴管里的液面已经很低。',
    'spore_crown': '培养皿般的圆冠悬在病原体上方，边缘垂着灰白的絮。',
    'blade_disc': '三枚刀片在洁净圆盘上轮换着反光。',
    'scan_halo': '一圈过亮的扫描镜缓慢旋转，白光扫过之处连影子都藏不住。',
    'core_sterile_grace': '银白环状灭菌设备包着透明核心。它相信清除所有变化就能永远安全。',
}
_SKILL_NAMES = {row[0]: row[1] for row in HOSPITAL_SKILLS}
for _aid, _definition in HOSPITAL_ANOMALIES.items():
    _definition['description'] = _DESCRIPTIONS[_aid.split('.', 1)[1]]
    _definition['skill'] = '；'.join(_SKILL_NAMES[sid.split('.', 1)[1]]+'｜'+HOSPITAL_SKILL_EFFECTS[sid.split('.', 1)[1]]
                                    for sid in HOSPITAL_BINDINGS[_aid])

HOSPITAL_FLOOR_POOLS = (
    ('hospital.membrane', 'hospital.capsid', 'hospital.sporebud'),
    ('hospital.membrane', 'hospital.capsid', 'hospital.filament', 'hospital.syringe', 'hospital.listener'),
    ('hospital.sporebud', 'hospital.filament', 'hospital.syringe', 'hospital.listener', 'hospital.dripstand'),
    ('hospital.membrane', 'hospital.forceps', 'hospital.listener', 'hospital.dripstand'),
)
HOSPITAL_STRONG_IDS = ('hospital.spore_crown', 'hospital.blade_disc', 'hospital.scan_halo')
HOSPITAL_FLOOR_NAMES = ('接引的白厅', '配液工坊', '气相静室', '白昼病房', '无垢圣所')

# 层间下潜守门提示（2026-10-14，#83/#85）：d1-d4 守门人兼任问询处。
# 第 5 层（滴瓶看守）是最深处、没有下潜，不挂这句。
HOSPITAL_GATE_HINT = ('要往更深处去，得先办齐这层的手续：读一遍散落的病历夹，'
                      '看一眼停摆的叫号屏，再完成任意一处设施的操作。')

HOSPITAL_NPCS = {
    'hospital.triage_bell': {
        'name':'分诊铃','glyph':'♧','integrity':20,'relation':'稳定意识','vault_only':True,
        'spawn_realms':('white_sanatorium',),
        'dialogue':['「分诊吗？」铃舌晃了一下，没有等到回音。「这里没人挂号。要容器的话，自己拿一只。」',
                    HOSPITAL_GATE_HINT],
        'options':({'label':'领取一次基础液/气容器','hospital_scene':{'operation':'borrow','rewards':('hospital.sealed_ampoule','hospital.clean_air_bottle')},'always':True},
                   {'label':'离开','leave':True,'always':True})},
    'hospital.dispenser': {
        'name':'无手药柜','glyph':'▣','integrity':20,'relation':'稳定意识','vault_only':True,
        'spawn_realms':('white_sanatorium',),'dialogue':['「只剩最后一份药材。」抽屉自己开出一条缝。「处方带来了吗？」',
                    HOSPITAL_GATE_HINT],
        'options':({'label':'配制洗忆泡腾片（洗兆液2，心智1/清醒1/想象2）','hospital_scene':{'operation':'service','reward':'hospital.memory_fizz','material':'洗兆液'},'always':True},
                   {'label':'配制淋巴胶囊（淋巴液2，心智1/清醒1/想象2）','hospital_scene':{'operation':'service','reward':'hospital.lymph_capsule','material':'淋巴液'},'always':True},
                   {'label':'离开','leave':True,'always':True})},
    'hospital.linen_cart': {
        'name':'净衣护理车','glyph':'♧','integrity':20,'relation':'稳定意识','vault_only':True,
        'spawn_realms':('white_sanatorium',),'dialogue':['「先帮我把回风口清干净。」它停稳了，白布抖平一角。「之后我替你守一会儿这儿。」',
                    HOSPITAL_GATE_HINT],
        'options':({'label':'恢复附近已关闭的灯段（耗材一次）','hospital_scene':{'operation':'restore_light'},'always':True},
                   {'label':'使用一次守护服务（安全时心智+4）','hospital_scene':{'operation':'guard'},'always':True},
                   {'label':'离开','leave':True,'always':True})},
    'hospital.infusion_keeper': {
        'name':'滴瓶看守','glyph':'♜','integrity':20,'relation':'稳定意识','vault_only':True,
        'spawn_realms':('white_sanatorium',),'dialogue':['「阀门别乱拧，供液就那么些。」它举了举手里空了一半的滴瓶。「灯的开关归你管。我不在了，记录还在。」'],
        'options':({'label':'阅读材料效果记录','hospital_scene':{'operation':'record'},'always':True},
                   {'label':'一次准备：缓释凝片','hospital_scene':{'operation':'prepare','reward':'hospital.slow_gel'},'always':True},
                   {'label':'一次准备：载氧棉糖','hospital_scene':{'operation':'prepare','reward':'hospital.oxygen_sugar'},'always':True},
                   {'label':'离开','leave':True,'always':True})},
}

for _key, _glyph in zip(HOSPITAL_NPCS, ("🔔", "💊", "🧺", "💉")):
    HOSPITAL_NPCS[_key]["glyph"] = _glyph
    HOSPITAL_NPCS[_key]["color"] = "#365d72"
