"""Zero-time tutorial evidence and preparation owned by GameSession."""
from copy import deepcopy
from dataclasses import dataclass, fields
from typing import Literal

from .entities import ActionResult
from .command_context import capture_command_context, command_context_token, matches_command_context


@dataclass(frozen=True)
class TutorialObservation:
    home_mode: bool = False
    panel_mode: str = 'world'
    memory_page: bool = False
    controls_help_open: bool = False
    self_visible: bool = False
    self_expanded: bool = False
    self_category: str = ''
    self_sources: tuple = ()
    signal_detail_open: bool = False
    cell_detail_target: tuple | None = None
    anomaly_detail_target: bool = False
    item_menu_target: bool = False
    qol_searching: bool = False
    inventory_filter: str = '全部'
    inventory_sort: str = '原序'
    board_editor: bool = False
    aim_assist: tuple | None = None
    aim_free: tuple | None = None
    aiming: bool = False
    editor_open: bool = False
    editor_condition: bool = False
    editor_regions: bool = False
    editor_map: bool = False
    observe_mode: bool = False
    observe_cursor: tuple | None = None
    path: bool = False
    cursor_zone: str = 'map'
    layer: str | None = None
    throwing: bool = False
    session_token: int = 0
    action_seq: int = 0
    world_time: int = 0
    previous: tuple | None = None


TutorialVerb = Literal['facts', 'event', 'observe', 'frame', 'pump', 'prepare',
                        'skip', 'control', 'replay', 'cancel_aim', 'cancel_tamper']

# Evidence authored by UI flows, never an arbitrary attribute or callable.
_UI_FACTS = frozenset(('guide_hidden', 'guide_restored', 'exit_read', 'practice_log_seen',
    'aim_cancelled', 'throw_cancelled', 'path_cancelled', 'ability_cast',
    'tamper_cancelled', 'tamper_committed'))
_OPERATIONS = frozenset(('accept', 'deliver'))


def submit_tutorial(session, verb: TutorialVerb, *args, expected_context=None):
    state = session.state
    if not state.tutorial.get('active'):
        return ActionResult(False)
    context = capture_command_context(state) if expected_context is None else expected_context
    return session.apply('tutorial_view', state.layer_key(), context, verb, *args)


def new_tutorial_session(manager):
    """Build the disposable tutorial owner before publishing it to the UI."""
    from . import GameState
    from ..persistence import GameSession
    state = GameState.new(seed=20261023, tutorial=True)
    state.tutorial['coach_version'] = 1
    return GameSession(state, manager, persist_initial=False, persistence_enabled=False)


def initialize_intro_marker(state):
    """One-time bootstrap before the new session's initial save/publication."""
    state.tutorial['intro_shown'] = True


def _primitive(value):
    return (value is None or type(value) in (str, int, bool)
            or type(value) is tuple and all(_primitive(item) for item in value))


def _valid_observation(state, view):
    for field in fields(view):
        value = getattr(view, field.name)
        if not _primitive(value):
            return False
        if type(field.default) in (bool, str, int) and type(value) is not type(field.default):
            return False
    for name in ('cell_detail_target', 'observe_cursor', 'aim_assist', 'aim_free'):
        point = getattr(view, name)
        if point is not None:
            if type(point) is not tuple or len(point) != 2 or any(type(v) is not int for v in point):
                return False
            if name in ('cell_detail_target', 'observe_cursor') and not state.inside_board(*point):
                return False
    if view.layer is not None and type(view.layer) is not str:
        return False
    if not matches_command_context(state, (view.session_token, view.action_seq, view.world_time)):
        return False
    if view.previous is not None:
        previous = view.previous
        if (type(previous) is not tuple or len(previous) != 10
                or type(previous[0]) is not int or previous[0] != view.session_token
                or any(type(previous[index]) is not bool for index in (1, 2, 3, 5, 7, 8))
                or type(previous[4]) is not str
                or any(type(previous[index]) is not int for index in (6, 9))
                or not 0 <= previous[6] <= view.action_seq
                or not 0 <= previous[9] <= view.world_time):
            return False
    return type(view.self_sources) is tuple and all(
        type(row) is tuple and len(row) == 2
        and all(value is None or type(value) is str for value in row)
        for row in view.self_sources)


def apply_tutorial(session, expected_layer=None, expected_context=None, verb=None, *args):
    state = session.state
    if (type(expected_layer) is not str or expected_layer != state.layer_key()
            or not state.tutorial.get('active') or type(verb) is not str
            or not matches_command_context(state, expected_context)):
        return ActionResult(False)
    from . import origin_course as course
    from .tutorial import tutorial_pump, tutorial_skip_step
    from .tutorial_guidance import prepare_module, replay_state
    if verb in ('prepare', 'control', 'replay') and not course.is_course(state):
        return ActionResult(False)
    if (verb == 'prepare' and len(args) == 1 and type(args[0]) is str
            and state.tutorial.get('coach_prepared') == args[0]):
        return ActionResult(False)
    # Legacy fire practice can replenish charges without changing a checklist
    # field. Other preparation mutations always also update tutorial metadata.
    before = deepcopy(state.tutorial), deepcopy(state.tutorial_events), state.projectile_charges
    message = ''
    if verb == 'facts' and args and all(type(fact) is str and fact in _UI_FACTS for fact in args):
        course.note(state, *args)
    elif (verb in ('cancel_aim', 'cancel_tamper')
          and len(args) == (3 if verb == 'cancel_aim' else 2)
          and all(type(value) is int for value in args[:2])
          and (verb != 'cancel_aim' or type(args[2]) is bool)):
        if tuple(args[:2]) != (state.action_seq, state.time):
            return ActionResult(False)
        if verb == 'cancel_aim':
            course.note(state, 'aim_cancelled', *(['throw_cancelled'] if args[2] else []))
            course.pump(state)
        else:
            course.note(state, 'tamper_cancelled')
    elif verb == 'event' and args and all(_primitive(value) for value in args):
        event, *values = args
        if event == 'panel_opened' and len(values) == 1 and type(values[0]) is str:
            state.tutorial_events[event] = values[0]
        elif event in ('npc_talked', 'any_input') and not values:
            state.tutorial_events[event] = 1
        elif event in ('observe_cell', 'autowalk_arrived') and len(values) == 2 and all(type(v) is int for v in values):
            if state.inside_board(*values):
                state.tutorial_events[event] = tuple(values)
    elif verb in ('observe', 'frame') and len(args) == 1 and type(args[0]) is TutorialObservation:
        observation = args[0]
        if not _valid_observation(state, observation):
            return ActionResult(False)
        if course.is_course(state):
            course.observe_ui(state, observation)
        if verb == 'frame' and observation.observe_mode and observation.observe_cursor is not None:
            state.tutorial_events['observe_cell'] = observation.observe_cursor
        message = tutorial_pump(state) or ''
    elif verb == 'pump' and not args:
        message = tutorial_pump(state) or ''
    elif verb == 'prepare' and len(args) == 1 and type(args[0]) is str and args[0] in course.BY_ID:
        prepare_module(state, args[0])
    elif verb == 'skip' and not args:
        message = tutorial_skip_step(state)
    elif verb == 'control' and len(args) == 1 and type(args[0]) is str and args[0] in _OPERATIONS:
        message = course.control(state, args[0]).message
    elif verb == 'replay' and len(args) == 1 and type(args[0]) is str and args[0] in course.BY_ID:
        import time
        from .vision.knowledge import initialize_map_knowledge
        fresh = replay_state(state, args[0])
        # The previous UI wrapped replay_state in GameSession, sampling visible
        # terrain/hazards after lesson preparation and the approach teleport.
        initialize_map_knowledge(fresh)
        command_context_token(fresh)
        session.state = fresh
        session.persistence_enabled = False
        session.started = time.monotonic()
        session._last_saved_turn = session.state.time
        return ActionResult(True, data={'state_changed': True})
    changed = before != (state.tutorial, state.tutorial_events, state.projectile_charges)
    return ActionResult(changed, message, {'state_changed': changed})
