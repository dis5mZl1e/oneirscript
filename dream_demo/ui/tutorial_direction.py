"""Numbered, click-through bearings to tutorial targets outside the view."""
from __future__ import annotations

from math import atan2, pi

from rich.text import Text
from textual.geometry import Region

from .floating_toast import FloatingToast, MapHintText


def direction_arrow(player, target):
    """Choose the nearest of eight directions in world coordinates."""
    dx, dy = target[0] - player[0], target[1] - player[1]
    if not dx and not dy:
        return ''
    index = round(atan2(dy, dx) / (pi / 4)) % 8
    return ('→', '↘', '↓', '↙', '←', '↖', '↑', '↗')[index]


def offscreen_directions(player, targets, viewport, visible):
    """Include fog-hidden or camera-clipped targets, in marker-number order."""
    left, top, width, height = viewport
    return tuple((number, direction_arrow(player, point))
                 for number, point in sorted(targets.items())
                 if point != player and (point not in visible or not (
                     left <= point[0] < left+width and top <= point[1] < top+height)))


class TutorialDirectionOverlay(MapHintText):
    """A small text overlay; mouse events are forwarded to the map underneath."""
    DEFAULT_CSS = """
    TutorialDirectionOverlay {
        layer: tutorial; position: absolute; display: none;
        width: auto; height: 1; padding: 0;
        background: #173642; color: #ffe09a; text-style: bold;
    }
    """

    def on_mouse_down(self, event):
        FloatingToast._forward_mouse(self, event, 'down')

    def on_mouse_move(self, event):
        FloatingToast._forward_mouse(self, event, 'move')

    def on_mouse_scroll_up(self, event):
        FloatingToast._forward_mouse(self, event, 'scroll_up')

    def on_mouse_scroll_down(self, event):
        FloatingToast._forward_mouse(self, event, 'scroll_down')


def place_near_player(app, view, overlay, player, width):
    """Find a free one-line rectangle close to the player, never on the player."""
    area = view.content_region.intersection(Region(0, 0, app.size.width, max(0, app.size.height-1)))
    if width > area.width or not player or not area.contains_region(player):
        return None
    center = player.x + player.width // 2
    left = max(area.x, min(area.right-width, center-width//2))
    anchor = getattr(app, '_coach_anchor_rect', None)
    cue_area = anchor.grow((1, 3, 1, 3)) if anchor else None
    ys = sorted(range(area.y, area.bottom), key=lambda y: (abs(y-player.y), y <= player.y))
    xs = sorted(range(area.x, area.right-width+1), key=lambda x: abs(x-left))
    for y in ys:
        for x in xs:
            candidate = Region(x, y, width, 1)
            if candidate.overlaps(player) or (cue_area and candidate.overlaps(cue_area)):
                continue
            try:
                if all((widget is view or widget is overlay or widget.id == 'map-hints')
                       for widget, _ in (app.screen._compositor.get_widget_at(col, y)
                                         for col in range(x, x+width))):
                    return candidate
            except Exception:
                continue
    return None


def update_overlay(app):
    """Recompute only when target visibility, camera, player or UI geometry changes."""
    from rich.cells import cell_len
    overlay = getattr(app, '_tutorial_direction_widget', None)
    if overlay is None or not overlay.is_mounted:
        try:
            overlay = app.query_one('#tutorial-direction', TutorialDirectionOverlay)
        except Exception:  # Screen is still mounting or has already been torn down.
            return
        app._tutorial_direction_widget = overlay
    enabled = (app._coach_enabled() and not getattr(app, '_coach_hidden', False)
               and not getattr(app, '_coach_directory', False)
               and app.board_editor is None
               and app.qol_confirmation is None and app.settings_page.capture_target is None
               and app._active_left_overlay() is None and app._active_tamper_editor() is None
               and app.layer_observation is None and not app._inspection_active())
    if not enabled:
        overlay.display = False
        overlay._direction_key = None
        return
    try:
        view = app.query_one('#map')
    except Exception:
        overlay.display = False
        overlay._direction_key = None
        return
    if not view.is_on_screen or not view.display:
        overlay.display = False
        overlay._direction_key = None
        return
    state = app.session.state
    player_pos = (state.player.x, state.player.y)
    targets = app._coach_map_targets()
    visible = {point for point in targets.values() if state.is_visible(*point)}
    directions = offscreen_directions(player_pos, targets, view.viewport, visible)
    if not directions:
        overlay.display = False
        overlay._direction_key = None
        return
    label = ' '.join(f'{number}{arrow}' for number, arrow in directions)
    player = app._coach_map_region(player_pos)
    coach = getattr(app, '_coach_frame_widget', None)
    hints = app.query_one('#map-hints')
    key = (player_pos, view.viewport, view.content_region, player, directions,
           coach.region if coach and coach.display else None,
           getattr(app, '_coach_anchor_rect', None),
           hints.region if hints.display else None,
           app.panel_mode, bool(app.aiming), bool(app.layer_observation))
    if key == getattr(overlay, '_direction_key', None):
        return
    region = place_near_player(app, view, overlay, player, cell_len(label))
    if region is None:
        overlay.display = False
        overlay._direction_key = key
        return
    overlay._direction_key = key
    overlay.update(Text(label, style='bold #ffe09a', no_wrap=True))
    overlay.styles.width = region.width
    overlay.styles.offset = (region.x, region.y)
    overlay.display = True
