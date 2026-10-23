"""Exclusive sources, portable effects; no ordinary loot or reward pool."""


MEDICINE_PROSE = {
    '甘眠露': '一小瓶淡金色的露，摇过以后，液面仍很平静。闻起来像晒过的枕头。',
    '载氧棉糖': '蓬松的白糖团，拆开包装就缓缓鼓起，像还在呼吸。',
    '梦敏颗粒': '细粒在舌尖化开，几个忘掉的颜色先后浮上来。',
    '淋巴素软胶囊': '半透明的胶囊里悬着一滴浅绿液体，始终没有碰到内壁。',
    '免疫球蛋白锭': '药锭表面布满细小圆纹，握在手里，比体温凉一点。',
    '洗忆泡腾片': '白片一碰水就响起细碎的气泡声，水面映出的旧影跟着散开。',
    '无菌咀嚼片': '硬片咬开时几乎没有味道，齿间只留下干净的粉末。',
    '脑脊滴': '细长滴管里装着清亮的液体，每一滴都悬得很久才落下。',
    '缓释凝片': '柔软的凝片贴着纸包，揭下来时，还拉着一根透明的细丝。',
    '停痛糖衣': '糖衣甜得很淡。含化以后，脑海里那阵刺痛远了一点。',
    '生理盐片': '边缘微微结晶的白片，咸味像眼泪，包装却没有水迹。',
    '骨髓糖': '糖心泛着温润的浅黄，咬开时有一点松软的阻力。',
    '口服的清晨': '小瓶里亮着晨光。拧开盖子，冷露的气味先飘出来。',
    '白瓷维生素': '白片圆得像瓷器上落下的一枚小扣，表面没有刻字。',
    '晨醒含片': '薄片带着清凉的香气，压在舌下，仿佛有人拉开了窗帘。',
    '退烧的雪': '纸包里有一撮细雪，捏在指间不化，贴近额头却很凉。',
}


def medicine(name, description, effect, *, power=0, secondary=0, stack=2):
    return dict(name=name, description=MEDICINE_PROSE[name],
                effect_description=description, category='摄入物',
                rarity='少见', color='#d7f5ef', effect=effect, power=power,
                power_secondary=secondary, max_stack=stack, loot=False,
                spawn_realms=('white_sanatorium',))


ITEMS = {
    'hospital.gentle_sleep': medicine('甘眠露',
        '没有可见敌对目标且不在危险格时恢复心智10、想象6；条件不满足不消耗。', 'hospital_safe_sleep'),
    'hospital.oxygen_sugar': medicine('载氧棉糖',
        '4回合内不追加胞尘族伤害；不抵挡其他毒气、火焰或敌人创伤。', 'hospital_oxygen'),
    'hospital.dream_sensitive': medicine('梦敏颗粒',
        '6回合内，恢复一项意识指标时，若另一项仍未满，额外恢复那一项至多3点；额外补充不会再次触发此效果。', 'hospital_sensitive'),
    'hospital.lymph_capsule': medicine('淋巴素软胶囊',
        '6回合内下一次直接命中病原体附加2点完整度创伤；非病原体不消耗。', 'hospital_lymph_hit'),
    'hospital.immunoglobulin': medicine('免疫球蛋白锭',
        '6回合内下一项新负面征兆初始持续减2，至少1回合；不减免后续续效。', 'hospital_immune_once'),
    'hospital.memory_fizz': medicine('洗忆泡腾片',
        '选择一项可洗征兆削短4回合，先处理附着。取消不消耗。', 'hospital_wash_choice'),
    'hospital.sterile_chew': medicine('无菌咀嚼片',
        '选择一项正面可洗征兆削短3回合，恢复清醒4。不足3回合不能转化。', 'hospital_positive_choice'),
    'hospital.cerebral_drops': medicine('脑脊滴',
        '自然想象恢复×1.25，持续6回合；与脑脊液取最大，不加速技能。', 'hospital_fluent'),
    'hospital.slow_gel': medicine('缓释凝片',
        '6回合内抵扣下一次实际创伤1点，使用间隔8回合。', 'hospital_gel_buffer'),
    'hospital.pain_sugar': medicine('停痛糖衣',
        '6回合内抵扣首次心智创伤2点，不减免清醒创伤。', 'hospital_pain_buffer'),
    'hospital.saline': medicine('生理盐片', '恢复心智8、清醒6，按当前缺口结算。',
                               'hospital_saline', power=8, secondary=6, stack=3),
    'hospital.marrow_sugar': medicine('骨髓糖', '恢复心智14，不增加上限。',
                                     'restore_mind', power=14),
    'hospital.oral_morning': medicine('口服的清晨', '恢复清醒14，不增加上限。',
                                     'restore_lucidity', power=14),
    'hospital.porcelain_vitamin': medicine('白瓷维生素', '恢复想象12，不增加上限。',
                                          'restore_imagination', power=12, stack=3),
    'hospital.morning_lozenge': medicine('晨醒含片',
        '削短一项沉眠族征兆4回合，先处理附着；无目标不消耗。', 'hospital_wake'),
    'hospital.fever_snow': medicine('退烧的雪',
        '削短一项热或燃烧征兆4回合；不熄灭地图火焰，无目标不消耗。', 'hospital_fever'),
}
