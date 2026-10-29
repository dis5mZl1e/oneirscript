"""连续移动节拍（M1，2026-10-24）。

背景：旧实现每次「到点」都用 ``now`` 重新起算，30Hz 帧网格上 110ms 经常落到
第 4 个 tick（约 133ms）并持续漂移；另一个入口（按键重复事件）又可能直接走步，
造成同一步有两个来源。

本模块只做一件事：把「下一次允许行动的时刻」记成单调时钟上的**截止点**。

- ``begin(now)``：建立截止点 ``now + interval``（首次按键仍由调用方立即走一步）。
- ``take_due(now)``：到点才返回 True，并且**一次调用最多消费一个截止点**；
  正常偏差把截止点顺延一个周期（保持相位，不漂移）；落后达到一个完整周期
  则丢弃过期机会、从 ``now`` 重新起算，绝不循环补步。
- ``reset()``：清除截止点（转向、碰撞、浮层、换层、松键等）。

时间单位统一为秒，时钟由调用方传入（生产用 ``time.monotonic``，测试用假时钟）。
"""

from __future__ import annotations

_MIN_INTERVAL = 1e-6


class MoveCadence:
    """按固定周期发放移动许可的截止点调度器。"""

    def __init__(self, interval: float) -> None:
        self.interval = max(_MIN_INTERVAL, float(interval))
        self.deadline: float | None = None

    def begin(self, now: float) -> None:
        """从 ``now`` 起建立一个完整周期后的截止点。"""
        self.deadline = float(now) + self.interval

    def take_due(self, now: float) -> bool:
        """到点返回一次 True；同一时刻重复调用不会重复发放。"""
        if self.deadline is None:
            return False
        now = float(now)
        if now < self.deadline:
            return False
        lateness = now - self.deadline
        if lateness >= self.interval:
            # 主线程或终端阻塞超过一个周期：丢弃过期机会，从当前时间重新排期。
            self.deadline = now + self.interval
        else:
            # 正常迟到：顺延一个周期，保留原有相位，避免每次从 now 起算的漂移。
            self.deadline += self.interval
        return True

    def reset(self) -> None:
        self.deadline = None

    @property
    def active(self) -> bool:
        return self.deadline is not None
