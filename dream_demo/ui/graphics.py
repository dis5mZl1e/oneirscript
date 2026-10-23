"""兼容终端提示与保存后重启的底层支持；设置页不再提供下载入口。"""

from __future__ import annotations

import sys
from pathlib import Path

from ..i18n import tr
from ..wezterm_setup import child_command, launch


class GraphicsMixin:
    def _graphics_startup_notice(self) -> None:
        if not getattr(self,'terminal_compatibility_notice',False):
            return
        message=tr('当前使用兼容终端，游戏可正常进入；字体、emoji 或地图对齐可能有差异。完整包已附 WezTerm，重新使用默认启动入口即可，无需另行下载。')
        self.settings_page.feedback=message
        self.notify(message,title=tr('终端兼容提示'),severity='warning',timeout=10)

    def _graphics_base_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            if '--game-directory' in sys.argv:
                index=sys.argv.index('--game-directory')
                if index+1<len(sys.argv):
                    return Path(sys.argv[index+1]).resolve()
            return Path(sys.executable).parent
        return Path(__file__).resolve().parents[2]

    def _graphics_restart(self, executable: Path | None) -> None:
        if not self.home_mode and not self.session.state.run_over and not getattr(self,'save_disabled',False):
            try:
                self.session.save_and_exit()
            except OSError as error:
                self.show_toast(tr('保存失败，未重启：{reason}',reason=str(error)),4)
                return
        try:
            launched = launch(self._graphics_base_dir(), child_command())
        except (OSError,ValueError) as error:
            self.show_toast(tr('终端配置失败：{reason}',reason=str(error)),4)
            return
        if launched is None:
            self.show_toast(tr("WezTerm 启动失败：{path}", path=str(executable or "?")), 4)
            return
        self.exit()
