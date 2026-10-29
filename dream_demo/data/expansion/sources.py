"""One random authorization and six event families, shared by all five kinds."""
from .catalog import by_category

EVENT_FAMILIES = {
    'sound': ('event.first_echo', 'event.sunken_bell', 'event.static_radio',
              'event.wet_score', 'event.radio_rain', 'event.midnight_broadcast'),
    'light': ('event.photo_booth', 'event.blank_gallery', 'event.polaroid_wall',
              'event.stargazer_desk', 'event.mirror_interview'),
    'terrain': ('event.tide_of_names', 'event.bath_tide', 'event.rusty_faucet',
                'event.tide_clock'),
    'projectile': ('event.lost_luggage', 'event.scrapper_case',
                   'event.toolbox_grave', 'event.last_train_window'),
    'circuit': ('event.broken_meter', 'event.clock_repairs',
                'event.static_radio', 'event.toolbox_grave'),
    'realm': ('event.silent_library', 'event.night_ward_round',
              'event.dream_post_office', 'event.post_to_waking'),
}

# 「出院与归档」（2026-10-25）：``depth >= 28`` 起由尾声层整层接管，
# ``event_candidates`` 不再投放普通异常地点，``LAYER_EVENT_IDS`` 最深也只到 27，
# 所以「最低28」的条目只能在这一层交付。
#
# 归档门**刻意不登记进** ``EVENT_FAMILIES``：线索菜单一旦认领事件就会把它
# ``resolved``，而「我看完了」是通往 29 层的唯一出口——玩家会被卡死在 28 层。
# 因此这里只给一条**授权**（谁的条目可以从这个门交付），发放仍走归档门上
# 显式列出的选项与 ``item_access.refusal`` 同一道闸。
DEEP_BRANCH_THEMES = {'epilogue.gate28': 'realm'}


def deep_branch_themes(event_id):
    base = str(event_id).removeprefix('event:').split('@', 1)[0]
    theme = DEEP_BRANCH_THEMES.get(base)
    return (theme,) if theme else ()


def event_themes(event_id):
    base = str(event_id).removeprefix('event:').split('@', 1)[0]
    return tuple(theme for theme, ids in EVENT_FAMILIES.items() if base in ids)


def source_allowed(entry, source):
    if entry.get('integration_status') != 'runtime':
        return False
    if entry.get('source_permission') == 'D':
        return (source == entry['source_id']
                or (str(source).startswith('event:')
                    and (entry['theme'] in event_themes(source)
                         or entry['theme'] in deep_branch_themes(source))))
    # Existing floor/table producers share the random pool. NPC shelves,
    # event random-options and rarity guarantees cannot duplicate this route.
    return source in {'expansion.random', 'floor_scatter', 'vault'}


def growth_token_rows():
    """Exact-ID manifestations carry an insight or conception through a slot.

    These are representations of the existing catalog entries, not extra IDs.
    Targeted events grant growth directly; a random floor slot uses this finite
    representation so it never awards invisible growth on map generation.
    """
    result = {}
    for category in ('insight', 'ability'):
        for entry in by_category(category):
            if entry.get('integration_status') != 'runtime':
                continue
            result[entry['id']] = {
                'name': entry['name_zh'], 'category': '交互道具',
                'description': entry['description_zh'],
                'color': entry['icon_color'], 'rarity': entry.get('rarity_zh') or '稀有',
                'max_stack': 1, 'effect': 'expansion_growth',
                'loot': entry['source_permission'] == 'G',
                'min_depth': entry['min_depth'],
                'run_limit': entry['tuning_proposal']['max_acquisitions_per_run'],
                'grant_source': (entry['source_id'] if entry['source_permission'] == 'D' else None),
                'expansion_catalog_id': entry['id'], 'integration_status': 'runtime',
            }
    return result
