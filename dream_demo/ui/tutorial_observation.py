"""Capture interface evidence as immutable primitives, never pass an app to core."""
from ..core.tutorial_control import TutorialObservation, submit_tutorial
from ..core.command_context import command_context_token


def capture_tutorial_ui(app):
    state = app.session.state
    editor = getattr(app, 'world_tamper_editor', None)
    layer = getattr(app, 'layer_observation', None)
    token = command_context_token(state)
    current = (token, bool(getattr(app, 'aiming', False)),
               bool(getattr(app, 'path', ())), editor is not None,
               getattr(app, 'cursor_zone', 'map'), layer is not None,
               state.action_seq, bool(editor and editor.map_preview),
               getattr(app, 'throw_item_index', None) is not None, state.time)
    previous = getattr(app, '_course_ui_previous', None)
    if previous and previous[0] != token:
        previous = None
    visible = bool(getattr(app, '_self_audit_visible', lambda: False)())
    sources = getattr(app, '_sa_last_sections', {}).get('sources', ()) if visible else ()
    observation = TutorialObservation(
        home_mode=bool(getattr(app, 'home_mode', False)),
        panel_mode=getattr(app, 'panel_mode', 'world'),
        memory_page=getattr(app, '_panel_subpage_id', lambda: '')() == 'memory',
        controls_help_open=bool(getattr(app, 'controls_help_open', False)),
        self_visible=visible, self_expanded=bool(getattr(app, '_sa_expanded', False)),
        self_category=getattr(app, '_sa_category', ''),
        self_sources=tuple((row.get('source_kind'), row.get('source_id')) for row in sources),
        signal_detail_open=bool(getattr(app, 'signal_detail_open', False)),
        cell_detail_target=getattr(app, 'cell_detail_target', None),
        anomaly_detail_target=getattr(app, 'anomaly_detail_target', None) is not None,
        item_menu_target=getattr(app, 'item_menu_target', None) is not None,
        qol_searching=bool(getattr(app, 'qol_searching', False)),
        inventory_filter=getattr(app, 'inventory_filter', '全部'),
        inventory_sort=getattr(app, 'inventory_sort', '原序'),
        board_editor=getattr(app, 'board_editor', None) is not None,
        aim_assist=getattr(app, '_aim_assist_pos', None),
        aim_free=getattr(app, '_aim_free_cursor', None), aiming=current[1],
        editor_open=current[3],
        editor_condition=bool(editor and (editor.focus == 'condition' or editor.condition_ids)),
        editor_regions=bool(editor and editor.slot.region_members),
        editor_map=current[7], observe_mode=bool(getattr(app, 'observe_mode', False)),
        observe_cursor=getattr(app, 'observe_cursor', None), path=current[2],
        cursor_zone=current[4], layer=layer.layer if layer is not None else None,
        throwing=current[8], session_token=current[0], action_seq=current[6],
        world_time=current[9], previous=previous)
    app._course_ui_previous = current
    return observation


def observe_tutorial_ui(app, *, frame=False):
    if not app.session.state.tutorial.get('active'):
        return None
    return submit_tutorial(app.session, 'frame' if frame else 'observe', capture_tutorial_ui(app))
