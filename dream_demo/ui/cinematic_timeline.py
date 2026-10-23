"""分镜时间轴（2026-10-08）：用经过时间组织镜头与节奏。

职责（方案文档 §实现结构）：

- 按 ending_id 持有镜头序列（镜头内容在 asciimatics_bridge）；
- **固定步长与显示帧率分离**：high 档 20fps、low 档 10fps，总时长不变
  ——low 档只是减少显示帧（桥内部按帧序号取整，同一帧号返回缓存）；
- 跳过 / 暂停 / 重建尺寸 / 取消；经过时间以结算画面的 30fps 帧计数换算
  （``frame / 30``，与 GAME_FRAME_SECONDS 对齐）。

asciimatics 缺失或结局 ID 不支持时 ``has_shots``
为 False，消费方（settlement）自动回退纯文本旧行为——零回归。
"""

from __future__ import annotations

from .asciimatics_bridge import ASCIIMATICS_AVAILABLE, CinematicBridge
from .cinematic_frame import CinematicFrame

# 质量档 → 演出帧率（off 档不建时间轴，不进本模块）。
FPS_BY_QUALITY = {"high": 20, "low": 10}
# 时间轴的最小画布：更小的内容区直接放弃演出（优先正文，方案 §质量与验收）。
MIN_WIDTH = 12
MIN_HEIGHT = 6


class CinematicTimeline:
    """一场结局演出的时间轴。每局 feed 时新建，hide/cancel 时丢弃。"""

    def __init__(self, ending_id: str, width: int, height: int,
                 quality: str = "high") -> None:
        self.ending_id = ending_id
        self.quality = quality
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.elapsed = 0.0
        self._paused = False
        self._cancelled = False
        self._bridge: CinematicBridge | None = None
        if quality != 'off' and ASCIIMATICS_AVAILABLE and self.width >= MIN_WIDTH and self.height >= MIN_HEIGHT:
            self._bridge = CinematicBridge(ending_id, self.width, self.height, quality)
        self.duration = self._bridge.duration if self._bridge else 0.0

    # ---- 状态 ----

    @property
    def has_shots(self) -> bool:
        """该结局是否有可播分镜（桥可用且时长 > 0）。"""
        return self._bridge is not None and self.duration > 0.0

    @property
    def finished(self) -> bool:
        return self._cancelled or not self.has_shots or self.elapsed >= self.duration

    @property
    def paused(self) -> bool:
        return self._paused

    # ---- 推进 ----

    def advance(self, elapsed: float) -> CinematicFrame | None:
        """推进到 elapsed 秒并取当前帧；无分镜/已取消返回 None。"""
        if self._cancelled or self._bridge is None or not self.has_shots:
            return None
        if not self._paused:
            self.elapsed = max(self.elapsed, float(elapsed))
        # 越过终点后钳制（尾声阶段背景停在最后一帧，不再烧 CPU）。
        return self._bridge.advance(min(self.elapsed, self.duration))

    def skip(self) -> None:
        """快进：直接落在终帧。"""
        if self._bridge is None or self._cancelled:
            return
        self.elapsed = self.duration
        self._bridge.advance(self.duration)

    def pause(self) -> None:
        self._paused = True
        if self._bridge is not None:
            self._bridge.paused = True

    def resume(self) -> None:
        self._paused = False
        if self._bridge is not None:
            self._bridge.paused = False

    def resize(self, width: int, height: int) -> None:
        """内容区变化：桥重建重演（确定性），时长不变。"""
        width, height = max(1, int(width)), max(1, int(height))
        if (width, height) == (self.width, self.height) or self._cancelled:
            return
        self.width, self.height = width, height
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            if self._bridge is not None:
                self._bridge.cancel()
            self._bridge = None
            return
        if self._bridge is None:
            if self.quality != 'off' and ASCIIMATICS_AVAILABLE:
                self._bridge = CinematicBridge(
                    self.ending_id, width, height, self.quality)
                self.duration = self._bridge.duration
                if self.elapsed > 0:
                    self._bridge.advance(self.elapsed)
                self._bridge.paused = self._paused
            return
        self._bridge.resize(width, height)

    def cancel(self) -> None:
        """作废（换局/返回主页）：释放画布，之后 advance 返回 None。"""
        self._cancelled = True
        if self._bridge is not None:
            self._bridge.cancel()
            self._bridge = None
