"""Shared, context-aware player controls; configuration and help use this table."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    key: str
    label: str
    panel: str = ''
    aliases: tuple[str, ...] = ()


PANEL_CONTROLS = (
    Control('tab', '意识行囊', 'inventory'), Control('t', '携带意象', 'equipment'),
    Control('v', '征兆', 'portents'), Control('i', '现实洞察', 'insights'),
    Control('k', '观测', 'catalog'), Control('j', '任务日志', 'tasks'),
    Control('h', '操作与帮助', 'actions', ('?', '？', 'question', 'question_mark')),
)
WORLD_CONTROLS = (
    Control('f', '瞄准'), Control('o', '辅助瞄准'), Control('x', '观察'),
    Control('g', '收纳'), Control('e', '回应'), Control('q', '返回或投掷'),
    Control('u', '使用'), Control('n', '下潜'), Control('b', '上浮'),
    Control('.', '等待', aliases=('。',)), Control('/', '光标区域', aliases=('slash',)),
    Control('~', '光标锁定', aliases=('`',)), Control('\\', '全部注释'),
    Control('[', '联想盘'), Control(']', '单条注释点击'),
    Control('r', '换弹'),
)


@dataclass(frozen=True)
class PanelShortcut:
    action: str
    key: str
    label: str

    @property
    def setting(self):
        return 'key_panel_' + self.action


PANEL_SHORTCUTS = (
    PanelShortcut('self', 'alt+s', '自我察觉'),
    PanelShortcut('signals', 'alt+n', '噪音与混乱度'),
    PanelShortcut('detail', 'alt+d', '当前对象详情'),
    PanelShortcut('context', 'alt+c', '当前目标操作'),
    PanelShortcut('board', 'alt+b', '联想盘'),
    PanelShortcut('tamper', 'alt+t', '篡改'),
    PanelShortcut('codex', 'alt+k', '完整图鉴'),
    PanelShortcut('settings', 'alt+o', '设置'),
    PanelShortcut('display', 'alt+m', '地图显示'),
    PanelShortcut('layers', 'alt+v', '分层观察'),
    PanelShortcut('elevation', 'alt+g', '地势观察'),
    PanelShortcut('inventory', 'alt+1', '意识行囊'),
    PanelShortcut('portents', 'alt+2', '征兆'),
    PanelShortcut('equipment', 'alt+3', '携带意象'),
    PanelShortcut('insights', 'alt+4', '现实洞察'),
    PanelShortcut('catalog', 'alt+5', '观测'),
    PanelShortcut('actions', 'alt+6', '操作与帮助'),
    PanelShortcut('tasks', 'alt+7', '任务日志'),
    PanelShortcut('history', 'alt+8', '梦境历史'),
    PanelShortcut('item_detail', 'alt+i', '右栏详情与比较'),
    PanelShortcut('workspace_prev', 'alt+left', '上一个右栏分区'),
    PanelShortcut('workspace_next', 'alt+right', '下一个右栏分区'),
)
RESERVED_ALT_KEYS = {
    'alt+h': '完整键位表', 'alt+e': '展开当前条目', 'alt+f': '行囊搜索',
    'alt+l': '行囊筛选', 'alt+r': '行囊排序', 'alt+p': '快捷目标',
    'alt+q': '保存退出', 'alt+z': '展开底栏', 'alt+0': '重置缩放', 'alt+9': '适合屏幕',
    'alt+up': '地图缩放', 'alt+down': '地图缩放',
}


def panel_for_key(key, character=None, aliases=()):
    if '+' in str(key):
        return None
    names = {key, character, *aliases}
    return next((c.panel for c in PANEL_CONTROLS if names.intersection((c.key, *c.aliases))), None)


def reserved_keys():
    entries = {str(n): '固定方向或等待键' for n in range(1, 10)}
    for control in (*PANEL_CONTROLS, *WORLD_CONTROLS):
        for key in (control.key, *control.aliases):
            if len(key) == 1:
                entries[key] = control.label
    return entries


def help_lines():
    from .i18n import tr
    return [f'{c.key.upper() if len(c.key) == 1 else c.key} · {tr(c.label)}'
            for c in (*PANEL_CONTROLS, *WORLD_CONTROLS)] + [
        f'{c.key.upper()} · {tr(c.label)}' for c in PANEL_SHORTCUTS
    ] + [
        'Enter：行动/激活当前选择；Esc：返回/菜单；F10 / Alt+Q：保存退出',
        '方向键/小键盘：地图移动；WASD：面板选择；/ 切换焦点区域',
        '鼠标左键：选择/行动；右键：详情；中键/Alt+左键：固定/快捷目标',
        'Alt+E：展开当前条目；Alt+F：行囊搜索；Alt+L：行囊筛选；Alt+R：行囊排序',
        'Alt+0：重置地图缩放；Alt+9：适合屏幕；F10：保存退出',
        'Alt+↑/↓：地图缩放；Shift+D：丢下首件物品；Shift+W：装备首件物品',
        '瞄准时 O：切换合法敌人；Tab：自由落点；Enter：确认；Esc：取消',
        '自由落点：方向键/小键盘移动光标；Enter：确认落点',
        '观察时 P：固定/取消固定当前格；Alt+P：添加/移除快捷目标',
        '噪音面板（Alt+N）内 L：凝听一回合；1–9：选择听觉线索并高亮地图',
        'F3 / Alt+V：分层观察；Alt+G：地势；观察内 Tab / [ ] 切层，\\ 图例，Esc 返回',
        '完整包已附 WezTerm 与字体；通过默认启动入口使用，兼容终端也可进入',
    ]
