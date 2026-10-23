"""A single controls reference; consume overlay mouse input before it reaches the map."""
from textual.containers import Vertical
from textual.widgets import Static
from rich.console import Group
from rich.table import Table
from rich.text import Text

from ..i18n import tr
from .ornament_frame import OrnamentBorderMixin


class ControlsReference:
    """Lay out key/meaning columns at the actual current console width."""

    def __init__(self, config):
        self.config = config

    def __rich_console__(self, console, options):
        from ..controls import PANEL_CONTROLS, PANEL_SHORTCUTS
        tamper = str(self.config.get('key_tamper')).upper()
        directions = '/'.join(str(self.config.get('key_' + axis)).upper()
                              for axis in ('up', 'down', 'left', 'right'))
        sections = (
            ('移动与地图', (
                ('↑↓←→ / 1–9', '地图移动；小键盘 5 等待可在设置中关闭'),
                (directions, '面板选择（←→/WASD 切本区分类，到端停留；五区用上方文字按钮，原业务快捷键保留）；方向主键可在设置中修改'),
                ('.', '等待'), ('N / B', '下潜 / 上浮'),
                ('Alt+↑ / Alt+↓', '地图缩放'), ('Alt+0 / Alt+9', '重置缩放 / 适合屏幕'))),
            ('战斗', (
                ('F', '瞄准；瞄准中再按打开来源表'), ('Q', '投掷；在面板中返回'), ('Enter', '行动或确认当前选择'),
                ('O', '瞄准时切换合法敌人'), ('Tab', '瞄准时进入自由落点'),
                ('↑↓←→ / 1–9', '自由落点模式：移动光标'), ('Esc', '取消瞄准'))),
            ('观察与目标', (
                ('X', '观察'), ('Enter', '观察时前往光标位置'), ('P', '观察时固定或取消固定当前格'),
                ('Alt+P', '观察时添加或移除快捷目标'), ('Alt+G', '直接进入地势观察；再次返回'),
                ('~ / `', '光标锁定'), ('/', '切换光标区域'),
                ('鼠标中键 / Alt+左键', '固定或快捷目标'))),
            ('行囊与装备', (
                ('G / U / E', '收纳 / 使用 / 回应'), ('Shift+D / Shift+W', '丢下首件 / 装备首件'),
                ('Alt+F', '行囊搜索'), ('Alt+L / Alt+R', '行囊筛选 / 排序'),
                ('Alt+E', '展开当前条目'), ('\\ / ]', '全部注释 / 单条注释点击'))),
            ('联想盘', (
                ('[', '打开联想盘'), ('↑↓←→ / WASD', '盘内选择或移动光标'),
                ('Enter', '确认当前盘内操作'), ('Esc / Q', '逐级返回；其余操作见盘内提示'))),
            ('界面与系统', tuple((c.key.upper(), c.label) for c in PANEL_CONTROLS) + (
                (tamper, '改写对话或眼前的文字'), ('Alt+H', '打开或关闭完整键位表'), ('F3 / Tab', '分层观察 / 观察中切层'),
                ('Alt+Z', '展开或收起底栏'), ('R', '为当前发射源换弹；有未完成换弹则继续；空匣/费用不足零消耗'),
                ('Esc', '返回或打开菜单'),
                ('F10 / Alt+Q', '保存退出'), ('鼠标左键 / 右键', '选择或行动 / 详情'),
                ('滚轮 / PgUp / PgDn', '滚动当前列表'))),
            ('面板快捷入口（保留原键）', tuple(
                (str(self.config.get(entry.setting) or entry.key).upper(),
                 tr(entry.label) + (tr('（主页）') if entry.action == 'history' else ''))
                for entry in PANEL_SHORTCUTS)),
        )
        width = options.max_width
        columns = 2 if width >= 104 else 1
        inner_width = (width - 4 * (columns - 1)) // columns
        groups = []
        for title, rows in sections:
            table = Table.grid(padding=(0, 1), expand=True)
            table.add_column(width=min(24, max(10, inner_width // 3)), style='#e6c46a', overflow='fold')
            table.add_column(ratio=1, overflow='fold', style='#ffffff')
            for key, description in rows:
                table.add_row(Text(tr(key)), Text(tr(description)))
            groups.append(Group(Text(tr(title), style='bold #9fdaca'), table, Text('')))
        if columns == 1:
            yield from groups
        else:
            grid = Table.grid(padding=(0, 2), expand=True)
            grid.add_column(ratio=1); grid.add_column(ratio=1)
            # Read down each column; the two halves contain three whole groups.
            grid.add_row(Group(*groups[:3]), Group(*groups[3:]))
            yield grid


class ControlsHelpLink(Static):
    def on_mouse_down(self, event):
        event.stop()
        if event.button == 1:
            # 这一行始终是「完整键位表」入口；分层观察用 F3，避免点击命中
            # 被左右分区改变（compact-controls 回归）。
            if self.app.layer_observation:
                self.app._exit_layer_observation()
            else:
                self.app.action_controls_help()


class ControlsHelpPanel(OrnamentBorderMixin, Vertical):
    def on_mouse_down(self, event):
        event.stop()

    def on_mouse_move(self, event):
        event.stop()

    def on_mouse_scroll_up(self, event):
        event.stop()

    def on_mouse_scroll_down(self, event):
        event.stop()
