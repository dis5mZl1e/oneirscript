"""The map display setting, also usable after a live output failure."""
from rich.text import Text
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Static
from ..i18n import tr
from .ornament_frame import OrnamentBorderMixin


class MapModeOption(Static):
    def __init__(self, value, label, **kwargs):
        super().__init__(label, **kwargs)
        self.value = value

    def on_mouse_down(self, event):
        event.stop()
        if event.button == 1:
            self.screen.dismiss(self.value)


class MapModePane(OrnamentBorderMixin,Vertical):
    pass


class MapDisplayScreen(ModalScreen):
    DEFAULT_CSS = '''
    MapDisplayScreen { align: center middle; background: #07070bcc; }
    #map-mode-options { width: 54; height: auto; max-height: 90%;
        border: solid #778ca5; background: #151927; padding: 1 2; overflow-y: auto; }
    MapModeOption { height: auto; min-height: 2; color: #bac7da; }
    MapModeOption.selected { color: #e4c689; text-style: bold underline; }
    #map-mode-title { height: auto; color: #c7a5e9; margin-bottom: 1; }
    #map-mode-status { height: auto; color: #91bfb9; margin-top: 1; }
    '''
    def __init__(self, selected, reason):
        super().__init__()
        self.selection = ('auto','image','character').index(selected if selected in ('auto','image','character') else 'auto')
        self.reason = reason

    def compose(self):
        with MapModePane(id='map-mode-options'):
            yield Static(tr('地图显示'), id='map-mode-title')
            for index,(value,label) in enumerate((('auto','自动（推荐）'),('image','图像'),('character','字符'))):
                yield MapModeOption(value, f'{index+1}  '+tr(label),
                                    classes='selected' if index == self.selection else '')
            yield Static(Text(self.reason+'\n'+tr('↑↓ 选择 · Enter 确认 · Esc 返回')), id='map-mode-status')

    def on_key(self, event):
        event.stop()
        event.prevent_default()
        if event.key in ('escape','q'):
            self.dismiss(None)
        elif event.key in ('1','2','3'):
            self.dismiss(('auto','image','character')[int(event.key)-1])
        elif event.key in ('enter','space'):
            self.dismiss(('auto','image','character')[self.selection])
        elif event.key in ('up','down'):
            self.selection = (self.selection+(-1 if event.key == 'up' else 1)) % 3
            for index,option in enumerate(self.query(MapModeOption)):
                option.set_class(index == self.selection,'selected')
