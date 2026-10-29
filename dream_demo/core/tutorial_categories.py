"""Tutorial browsing categories, independent of the practice map's zones."""

CATEGORIES = (
    ('basic', '基础操作', 'Basics'),
    ('information', '界面与信息', 'Interface'),
    ('board', '联想盘', 'Board'),
    ('tamper', '篡改', 'Tampering'),
    ('environment', '环境交互', 'Environment'),
    ('combat', '战斗与射击', 'Combat'),
)

_GROUPS = {
    'basic': ('A1', 'A4', 'D1', 'D2', 'D3', 'J5', 'I4', 'I3'),
    'information': ('A2', 'A3', 'B1', 'B2', 'B3', 'J6', 'E4'),
    'board': ('E1', 'E2', 'E3', 'E5', 'E6'),
    'tamper': ('F2', 'F3', 'F4'),
    'environment': ('B4', 'G1', 'G2', 'G3', 'D4', 'J2', 'J3', 'H1', 'H2', 'H3',
                    'J1', 'I1', 'I2', 'F1', 'J8', 'J9', 'J10'),
    'combat': ('C1', 'C2', 'C3', 'J4', 'J7'),
}


def category_for(module_id):
    return next(key for key, ids in _GROUPS.items() if module_id in ids)


def lessons(category):
    from .origin_course import BY_ID
    return tuple(BY_ID[key] for key in _GROUPS[category] if key in BY_ID)
