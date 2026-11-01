"""A single controls reference; consume overlay mouse input before it reaches the map."""
from textual.containers import Vertical
from textual.widgets import Static
from rich.console import Group
from rich.table import Table
from rich.text import Text

from ..i18n import tr
from .ornament_frame import OrnamentBorderMixin


def key_table_sections(config):
    """Every documented (key, meaning) row, grouped by section title.

    Both the rendered reference and the coverage tests read this table, so a
    binding routed in code but absent here fails the gate.
    """
    from ..controls import PANEL_CONTROLS, PANEL_SHORTCUTS
    tamper = str(config.get('key_tamper')).upper()
    return (
            ('移动与地图', (
                ('↑↓←→ / 1–9', '移动角色（始终，与区域无关）；小键盘 5 等待可在设置中关闭'),
                ('W A S D', '恒控右栏：W/S 选择 · A/D 切页；左浮层开着时按 / 把 WASD 交给浮层'),
                ('- / =', '上一个 / 下一个子标签；选中右侧行囊时切换格子 / 竖排'),
                ('/', '切换 WASD 的区域：地图 / 右栏都控右栏，左浮层开着可切给浮层（永不控地图）'),
                ('.', '等待'), ('N / B', '下潜 / 上浮'),
                ('( / )', '地图缩放（Alt+↑/↓ 仍可用）'), ('Alt+0 / Alt+9', '重置缩放 / 适合屏幕'))),
            ('战斗', (
                ('F', '瞄准；瞄准中再按打开来源表'), ('Q', '投掷；在面板中返回'), ('Enter', '行动或确认当前选择'),
                ('O', '瞄准时切换合法敌人'), ('Tab', '瞄准时进入自由落点'), (', / <', '瞄准中切换发射来源'),
                ('↑↓←→ / 1–9', '自由落点模式：移动光标'), ('Esc', '取消瞄准'))),
            ('观察与目标', (
                ('X', '观察'), ('Enter', '观察时前往光标位置'), ('P', '观察时固定或取消固定当前格'),
                ('Alt+P', '观察时添加或移除快捷目标'), ('Alt+G', '直接进入地势观察；再次返回'),
                ('~ / `', '光标锁定'), ('/', '切换光标区域'),
                ('鼠标中键 / Alt+左键', '固定或快捷目标'))),
            ('行囊与装备', (
                ('G / U / E', '收纳 / 使用 / 回应'), ('Shift+D / Shift+W', '丢下首件 / 装备首件'),
                ('↑↓ / W S', '行囊网格按整行（5 格）移动；到最上排再按 ↑ 把焦点交给「格子 / 竖排」控件'),
                ('Enter / - / =', '焦点在「格子 / 竖排」控件时切换排布；行囊内任意时刻按 - / = 也直接切换'),
                ('Alt+F', '当前行囊／构想搜索'), ('Alt+L / Alt+R', '行囊筛选／排序；征兆页 Alt+L 分类'),
                ('Alt+I', '当前物品比较、来源详情或任务物品'), ('Alt+W', '固定构想；总览中展开或折叠'),
                ('Alt+E', '展开当前条目'), ('\\ / ]', '全部注释 / 单条注释点击'),
                ("'", "行囊／装备页打开左侧物品菜单；图鉴页打开条目详情；观察中打开光标格详情"))),
            ('联想盘', (
                ('[ / M', '打开联想盘'),
                ('↑↓←→ / 小键盘 2·4·6·8', '盘内移动光标；编辑器里 WASD 不当方向键（a 是拿放）'),
                (', / . 或 PgUp / PgDn', '在右侧「行囊中的携带意象」列表里换项'),
                ('空格', '拿起或放下列表里选中的这一件'),
                ('a / A', '在当前格拿放 · 自动安置选中的这一件'),
                ('R / X', '旋转手中的装备 / 拆除当前格的装备'),
                ('Z / P', '循环功能词 / 切换放置策略'),
                ('V', '切换视图（不离开编辑器）'),
                ('Enter', '确认当前盘内操作'), ('Esc / Q', '逐级返回；其余操作见盘内提示'))),
            ('篡改面板（编辑器内）', (
                ('↑↓ / W S', '选字词；焦点在条件区时选条件'),
                ('←→ / A D', '换目标槽'),
                ('Tab / Shift+Tab', '字词焦点 ↔ 条件焦点'),
                ('空格', '勾选或取消当前条件'),
                ('[ ] 或 , .', '换条件组合'),
                ('- / =', '换程度（通常 / 轻轻 / 用力）'),
                ('R', '切换范围（这一处 / 全视野）'),
                ('\\', '展开或收起效果详情'),
                ('V', '查看地图上的落点'),
                ('PgUp / PgDn', '翻字词列表（整五行）'),
                ('Enter', '进确认 / 执行'),
                ('Esc / Q', '逐级退出：确认 → 字词 → 右栏 → 取消'))),
            ('主页与存档', (
                ('1 / 2 / 3', '直选存档槽；主菜单上按数字直达该槽'),
                ('↑↓ / 小键盘 2·8 / ←→ / 小键盘 4·6', '在存档槽与图鉴 / 设置 / 退出之间移动光标'),
                ('K', '从主页打开完整图鉴'),
                ('S / ,', '从主页打开设置'),
                ('D', '删除光标所在的存档槽（两段确认）'),
                ('Enter', '激活光标项：载入 / 新建存档、进图鉴、设置或退出'))),
            ('界面与系统', tuple((c.key.upper(), c.label) for c in PANEL_CONTROLS) + (
                ('Tab / Shift+Tab', '循环行动、行囊、构筑、自身、环境、日志；设置中换页'), (tamper, '改写对话或眼前的文字'), ('Alt+H', '打开或关闭完整键位表'), ('F3 / Tab', '分层观察 / 观察中切层'),
                ('Alt+Z', '展开或收起底栏'), ('R', '为当前发射源换弹；有未完成换弹则继续；空匣/费用不足零消耗'),
                ('F2', '打开地图显示页：当前渲染方式与不可用原因'),
                ('Y / N', '洞察替换的二次确认：确定放弃 / 先不换（Enter 同 Y，Q/Esc 回列表）'),
                ('Esc', '返回或打开菜单'),
                ('F10 / Alt+Q', '保存退出'), ('鼠标左键 / 右键', '选择或行动 / 详情'),
                ('滚轮 / PgUp / PgDn', '滚动当前列表'))),
            ('面板快捷入口（保留原键）', tuple(
                (str(config.get(entry.setting) or entry.key).upper(),
                 tr(entry.label) + (tr('（主页）') if entry.action == 'history' else ''))
                for entry in PANEL_SHORTCUTS)),
    )


class ControlsReference:
    """Lay out key/meaning columns at the actual current console width."""

    def __init__(self, config):
        self.config = config

    def __rich_console__(self, console, options):
        sections = key_table_sections(self.config)
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
            # Read down each column; the left half carries the odd group when the
            # section count is odd.
            mid = (len(groups) + 1) // 2
            grid.add_row(Group(*groups[:mid]), Group(*groups[mid:]))
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
