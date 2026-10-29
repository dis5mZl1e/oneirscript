"""Whole dream identities and the independent, shared aptitude price table."""

DREAM_BUDGET = 12
REFUND_LIMIT = 3
TIER_PRICES = (-2, -1, 0, 2, 5)
APTITUDES = ('mind', 'lucidity', 'imagination', 'melee', 'shooting',
             'throwing', 'conceive', 'materials')
APTITUDE_NAMES = dict(zip(APTITUDES, ('心智', '清醒', '想象', '近战', '射击',
                                    '投掷', '构想', '材料操作')))
IDENTITIES = {
    'ordinary': {'name': '常梦者', 'cost': 0, 'trait': 'ordinary'},
    'paper': {'name': '纸身旅人', 'cost': 3, 'trait': 'late_steps'},
    'rain': {'name': '雨里住客', 'cost': 4, 'trait': 'water_trace'},
    'ember': {'name': '余烬抄写者', 'cost': 6, 'trait': 'borrowed_fire'},
    'porcelain': {'name': '瓷壳修补匠', 'cost': 4, 'trait': 'circuit_echo'},
    'mirror': {'name': '镜中替身', 'cost': 8, 'trait': 'borrowed_strike'},
    'fog': {'name': '雾中旁观者', 'cost': 5, 'trait': 'borrow_fog'},
    'writer': {'name': '未署名的执笔者', 'cost': 7, 'trait': 'retract'},
}

IDENTITY_RULE_DESCRIPTIONS = {
    'ordinary': '和大多数梦一样开始。均衡探索与自由构筑；没有额外的护持、弱点，也没有专属的本事。',
    'paper': '你是由纸叠成的。失去追踪视线的移动留下半径 3 的旧位置声源，冷却 14；毒性附着缩短 20%，火焰创伤 +15%。你惯于绕着墙角走。',
    'rain': '你习惯住在雨里。从液体走到干地时，一项同源负面附着减少 1，冷却 10；负面液体附着缩短 20%，电创伤 +15%。积水对你不是障碍。',
    'ember': '你用没烧完的火写字。亲手点燃未燃燃料后，3 回合内一次火焰直接创伤减 2，冷却 12；免疫燃烧征兆，电创伤 +15%。你总给自己留一条退路。',
    'porcelain': '你的外壳是瓷的。亲手首次激活接收器恢复想象 2，每层最多两次、间隔 12；腐蚀附着缩短 20%，异象直接清醒创伤 +10%。你认得每一处机关的接缝。',
    'mirror': '你从镜面那一侧来。记录实际直接受创最多 2，4 回合内下次普通近战追加等量创伤，记录冷却 12；负面视线附着缩短 20%，电创伤 +10%。你擅长把挨过的打还回去。',
    'fog': '你站在雾的边缘。借雾：脚下黑烟 36，想象成本 5、冷却 14；免疫中毒征兆，异象直接心智创伤 +10%。退进雾里是你最熟的路。',
    'writer': '你的签名位置还空着。退稿：撤去相邻的本人构想墙，成本 4、冷却 14，每层首次恢复想象 2；火焰创伤 +10%。你习惯亲手改动地形。',
}

from .identity_prose import IDENTITY_PROSE
IDENTITY_DESCRIPTIONS = {
    key: prose[0] + '\n' + IDENTITY_RULE_DESCRIPTIONS[key].split('。', 1)[1]
    for key, prose in IDENTITY_PROSE.items()
}
