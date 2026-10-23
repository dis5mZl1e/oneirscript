"""Pure music scene selection. Does not consume randomness or change game state."""
from dataclasses import dataclass

from .mapgen.layout import region_for_depth

ENDINGS = dict(A='ending_a_awake', B='ending_b_rewrite', C='ending_c_release',
               D='ending_d_cowrite', E='ending_e_sink', F='ending_f_dreamless')
REALMS = dict(door_corridor='realm_doors', toy_memories='realm_toys',
              ember_bridge='realm_ember', ebbing_hall='realm_tide',
              millennium_garden='realm_millennium', library_palace='realm_library',
              white_sanatorium='realm_hospital')
REGIONS = {'浅层梦境':'main_shallow', '幻觉空间':'main_middle', '无意识领域':'main_deep'}
FORMS = {'洞穴':'space', '长廊':'space', '回声大厅':'space', '迷宫':'repeat',
         '无限房间':'repeat', '破碎的房间':'fragments', '碎影平原':'fragments'}


@dataclass(frozen=True)
class MusicScene:
    track: str | None
    loops: int = -1
    fallback: str | None = None


def music_scene(state, *, home: bool) -> MusicScene:
    if home:
        return MusicScene('home_gate')
    if state.run_over:
        return MusicScene(ENDINGS.get(state.ending_id), loops=0)
    for enemy in state.enemies:
        if enemy.integrity <= 0 or enemy.relation != '失控意识' or enemy.alert_state != '追踪':
            continue
        visible = (state.is_visible(enemy.x, enemy.y) if hasattr(state, 'is_visible')
                   else (enemy.x, enemy.y) in getattr(state, 'visible', ()))
        if not visible:
            continue
        if enemy.catalog_id == 'anomaly.scribe':
            return MusicScene('scribe_battle')
        if enemy.catalog_id == 'library.core':
            return MusicScene('library_final')
        if enemy.catalog_id == 'hospital.core_sterile_grace':
            return MusicScene('hospital_final', fallback='obsession_battle')
        if enemy.catalog_id == 'anomaly.core_y2k_worm':
            return MusicScene('millennium_final')
        if enemy.anomaly_kind == '核心执念':
            return MusicScene('obsession_battle')
    if state.realm_id:
        if state.realm_id == 'white_sanatorium':
            return MusicScene('realm_hospital', fallback=REGIONS.get(region_for_depth(state.depth), 'main_deep'))
        return MusicScene(REALMS.get(state.realm_id, REGIONS.get(region_for_depth(state.depth), 'main_shallow')))
    if state.depth in (28,29,30):
        return MusicScene({28:'epilogue_28_recognize',29:'epilogue_29_accept',30:'epilogue_30_desk'}[state.depth],
                          fallback='deep_boundary')
    if state.depth <= 0 or state.tutorial.get('active'):
        return MusicScene('first_dream', fallback='main_shallow')
    base = REGIONS.get(region_for_depth(state.depth), 'main_shallow')
    family = FORMS.get(state.map_form)
    return MusicScene(f'{base}_{family}' if family else base, fallback=base)

