"""音频门面：pygame.mixer 懒初始化 + 全降级保护。

设计要点（2026-09-17 评估结论的实现）：
- pygame 只在本模块内按需局部导入，首次真正播放时才加载（省 100-300ms 启动）；
- ``mixer.init()`` 失败（RDP 无声卡、音频设备被禁用、pygame 未安装）→
  永久降级为静音标志，绝不抛异常拖垮游戏；
- 短音效走 ``mixer.Sound``（整段解码进内存、play 非阻塞），长音乐走
  ``mixer.music``（磁盘流式、支持无限循环与淡入淡出），两者不可混用；
- 线程纪律：只在 asyncio 主循环线程（UI handler）调用——native 输入线程的
  事件已经由 run_coroutine_threadsafe 路由到主循环，天然单线程，无需加锁；
- 资源基名不带扩展名：优先 ``.ogg``（正式资源），回退 ``.wav``（占位
  资源），以后替换成正式音频不用改代码；
- 打包态路径：onefile 下资源经 ``--add-data`` 解压到 ``sys._MEIPASS``，
  开发态回退仓库 ``assets/`` 目录。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

# 语义事件 → 资源基名（assets/sfx/<name>.ogg 或 .wav）。
# 未列出的动作不发声；列出的资源缺失时仅跳过该事件，不影响其他音效/音乐。
#
# [SFX挂点] 第一批已接入 2026-09-19（30 个事件，素材全部在 assets/sfx/）。
# 完整挂点清单与触发条件见仓库根目录《音效挂点索引.md》；接入新事件时
# 在此登记键名并放置同名资源文件。
SOUND_MAP = {
    # ---- 动作命令（ui/input.py ACTION_SOUNDS 驱动）----
    "step": "step",            # 移动成功（普通地面）
    "step_water": "step_water",  # 踩进液体移动
    "step_plant": "step_plant",  # 踩着植物移动
    "step_ice": "step_ice",      # 冰面（滑行地板）移动
    "throw": "throw",          # 投掷
    "fire": "fire",            # 开火（有弹/已解锁）
    "fire_empty": "fire_empty",  # 空放（未解锁且无聚合弹，只有扣扳机干响）
    "hit": "hit",              # 打中目标（射击/近战撞击）
    "pickup": "pickup",        # 收纳/拾取（含台面取物、NPC 交易成交）
    "unlock": "unlock",        # 解锁（纵火解锁等）
    "descend": "descend",      # 下潜换层
    "backtrack": "backtrack",  # 层间返回（上浮）
    "finish": "finish",        # 本局结束（通关）
    "open": "open",            # 开门/推墙
    "uproot": "uproot",        # 拔植物
    "equip": "equip",          # 穿上/脱下携带意象
    "use_potion": "use_potion",  # 使用易逝物（消耗品）
    # ---- core 被动事件（_apply 状态 diff 驱动）----
    "wound_light": "wound_light",  # 玩家心智受创（轻，1–7 点）
    "wound_heavy": "wound_heavy",  # 玩家心智受创（重，≥8 点）
    "parry": "parry",              # （素材就绪，暂无触发点——见索引 B4）
    "enemy_die": "enemy_die",      # 异象崩解死亡（_apply 敌数 diff 触发）
    "insight": "insight",          # 获得洞察
    "memory": "memory",            # 获得记忆碎片
    "defeat": "defeat",            # 意识沉没（行动中败局，非 finish_run）
    # ---- 互动 / UI ----
    "npc": "npc",              # NPC 对话唤起
    "interact": "interact",    # 事件对话唤起/对话选项确认
    "event_done": "event_done",  # 事件完成（resolved：交付/次数耗尽/剧情房间）
    "construct": "construct",  # 使用主动构想
    "ui_click": "ui_click",    # 界面点击（切页/开菜单/调设置）
    "ui_error": "ui_error",    # 界面错误提示（删除存档待确认警告）
}


def _asset_path(*parts: str) -> Path | None:
    """解析资源路径：打包态优先 sys._MEIPASS，开发态回退仓库 assets/。"""
    bases = []
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        bases.append(Path(bundle))
    bases.append(Path(__file__).resolve().parent.parent / "assets")
    for base in bases:
        candidate = base.joinpath(*parts)
        if candidate.is_file():
            return candidate
    return None


class AudioBus:
    """音效与音乐的统一门面；所有方法永不抛异常（音频失败只降级不崩溃）。

    ``backend`` 是测试注入点：鸭子类型提供 pygame.mixer 的同名接口
    （pre_init / init / set_num_channels / Sound / music），None 表示
    使用真 pygame（懒导入）。
    """

    def __init__(self, backend: Any = None) -> None:
        self._backend = backend
        self._mixer: Any = None
        self._ready = False
        self._disabled = False
        self._sounds: dict[str, Any] = {}
        self._sfx_volume = 1.0
        self._music_volume = 1.0
        self._music_current: tuple | None = None
        self._music_pending: tuple | None = None
        self._music_transition: tuple[float, float, float] | None = None
        self._music_gain = 1.0
        self.diagnostics: dict[str, str] = {}

    # ---- 初始化 -------------------------------------------------------

    def _load(self) -> bool:
        """首次调用时初始化混音器并预载音效；失败则永久静音（不再重试）。"""
        if self._ready or self._disabled:
            return self._ready
        try:
            if self._backend is not None:
                mixer = self._backend
            else:
                # pygame 2.x 导入时会向 stdout 打印 "Hello from the pygame
                # community" 横幅——游戏运行中任何 stdout 写入都会破坏 TUI
                # 画面，必须在导入前压掉（setdefault：尊重用户显式设置）。
                os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
                from pygame import mixer  # 懒导入：缺库/无声卡都不拖垮游戏
            mixer.pre_init(44100, -16, 2, 512)
            mixer.init()
            mixer.set_num_channels(16)
        except Exception as error:
            self._disabled = True
            self.diagnostics['device'] = str(error)
            return False
        self._mixer = mixer
        self._ready = True
        for event, basename in SOUND_MAP.items():
            for extension in ('ogg', 'wav'):
                path = _asset_path('sfx', f'{basename}.{extension}')
                if path is None:
                    continue
                try:
                    self._sounds[event] = mixer.Sound(str(path))
                    break
                except Exception as error:
                    self.diagnostics[f'sfx:{event}:{extension}'] = str(error)
        return True

    # ---- 音效（短，内存预载） ------------------------------------------

    def play(self, event: str, volume: float | None = None) -> None:
        """播放一个语义音效；资源缺失或混音器不可用时静默跳过。"""
        sound = self._sounds.get(event) if self._load() else None
        if sound is None:
            return
        try:
            sound.set_volume(self._clamp(self._sfx_volume if volume is None else volume))
            sound.play()
        except Exception:
            pass  # 播放失败不影响游戏

    # ---- 音乐（长，磁盘流式） -----------------------------------------

    def play_music(self, basename: str, fade_ms: int = 1500, volume: float | None = None,
                   *, loops: int = -1) -> bool:
        if not self._load():
            return False
        for extension in ('ogg', 'wav'):
            path = _asset_path('music', f'{basename}.{extension}')
            if path is None:
                continue
            try:
                self._mixer.music.load(str(path))
                self._music_gain = 1.0
                self._mixer.music.set_volume(self._clamp(self._music_volume if volume is None else volume))
                self._mixer.music.play(loops=loops, fade_ms=max(0, int(fade_ms)))
                self._music_current = (basename, loops, None)
                return True
            except Exception as error:
                self.diagnostics[f'music:{basename}:{extension}'] = str(error)
        return False

    def request_music(self, basename: str | None, *, loops: int = -1, context=None,
                      fade_ms: int = 500, now: float | None = None) -> bool:
        """Latest request wins. tick() drives a fade without mixer.fadeout blocking."""
        wanted = (basename, loops, context) if basename else None
        if self._music_transition is not None and wanted == self._music_pending:
            return True
        if wanted == self._music_current:
            if self._music_transition is not None:
                self._music_transition = None
                self._music_pending = None
                self._music_gain = 1.0
                self.set_volume(music=self._music_volume)
            return True
        if basename and not (_asset_path('music', f'{basename}.ogg') or _asset_path('music', f'{basename}.wav')):
            self.diagnostics[f'music:{basename}'] = 'missing asset'
            return False
        now = time.monotonic() if now is None else now
        if self._music_current is None or fade_ms <= 0:
            self._music_transition = None
            self._music_pending = None
            if wanted is None:
                self._stop_music_now()
                return True
            ok = self.play_music(basename, fade_ms=fade_ms, loops=loops)
            if ok:
                self._music_current = wanted
            return ok
        self._music_pending = wanted
        self._music_transition = (now, fade_ms/1000, self._music_gain)
        return True

    def tick(self, now: float | None = None) -> None:
        if self._music_transition is None or not self._ready:
            return
        now = time.monotonic() if now is None else now
        start, duration, initial = self._music_transition
        progress = min(1., max(0., (now-start)/max(duration,.001)))
        self._music_gain = initial*(1-progress)
        try:
            self._mixer.music.set_volume(self._music_volume*self._music_gain)
        except Exception:
            pass
        if progress >= 1:
            wanted = self._music_pending
            self._music_transition = None
            self._music_pending = None
            self._stop_music_now()
            if wanted and self.play_music(wanted[0], loops=wanted[1], fade_ms=400):
                self._music_current = wanted

    def _stop_music_now(self) -> None:
        if self._ready:
            try:
                self._mixer.music.stop()
            except Exception:
                pass
        self._music_current = None
        self._music_gain = 1.0

    def stop_music(self, fade_ms: int = 800) -> None:
        self.request_music(None, fade_ms=fade_ms)

    # ---- 音量 / 生命周期 -------------------------------------------------

    def set_volume(self, sfx: float | None = None, music: float | None = None) -> None:
        """调整两类音量（0.0-1.0）；音效音量即时作用于后续播放。"""
        if sfx is not None:
            self._sfx_volume = self._clamp(sfx)
        if music is not None:
            self._music_volume = self._clamp(music)
            if self._ready:
                try:
                    self._mixer.music.set_volume(self._music_volume*self._music_gain)
                except Exception:
                    pass

    def shutdown(self) -> None:
        """停掉音乐并释放音频设备（on_unmount 时调用）。"""
        if not self._ready:
            return
        try:
            self._mixer.music.stop()
            self._mixer.quit()
        except Exception:
            pass
        self._ready = False
        self._sounds = {}
        self._music_current = None
        self._music_pending = None
        self._music_transition = None

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


# 模块级单例：UI 层统一从这里调用。
sfx = AudioBus()
