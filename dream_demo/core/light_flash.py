"""§12 D 残余：激活类环境的一次短光（2026-10-20）。

方案原文（`docs/261018方案合集.md` §4.3 末行）：

    已激活显影方尖、感应符文 | 已有环境／激活文本 |
    使用既有激活动作的一次短光或明确持续态微光 |
    不把「永久显影」误当永久强灯；没有可持久化激活状态的条目不先假定常亮。

两个来源都**没有**「亮着」的可持久化状态：

* 显影方尖点亮是**一次性**动作（`logic._resolve_receiver`），
  「永久显影」写进地图知识（`developed_cells`），不是照明；
* 感应符文墙的感知有 5 回合冷却（`logic.RUNE_SENSOR_COOLDOWN`），
  感知到才发信号，没感知时它和普通墙一样黑。

所以这里按原文取「一次短光」这一支：真实激活动作发生时压一条带寿命的
演出记录，UI 按 ``seq`` 差分拾取、按 ``life`` 秒衰完。**不登记成常驻光源**
（`data/light_sources.light_spec_for_cell` 里不含这两条墙）。

纯演出字段，不入存档（`persistence.SaveManager._encode` 的 runtime_caches
里排除了 ``light_flashes`` / ``_light_flash_seq``，与 ``last_sound_pulse``
同口径——读档后短光自然消失，不需要也不应该被复活）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.light_sources import LightFlashSpec, flash_spec

# 同时存在的短光上限：一次信号可能连锁点亮多格，超出就丢最旧的。
# 短光寿命 <1s，正常情况下队列里只有一两条。
FLASH_MAX = 8


@dataclass(frozen=True)
class LightFlash:
    """一条待播的短光（世界坐标）。"""

    seq: int
    kind: str
    x: int
    y: int
    color: str
    radius: float
    brightness: float
    life: float
    world_time: int = 0
    source_id: str = ""      # 稳定身份（= data.light_sources.FLASHES 的 flash_id）

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "color": self.color,
            "radius": self.radius,
            "brightness": self.brightness,
            "life": self.life,
            "world_time": self.world_time,
            "source_id": self.source_id,
        }


def note_light_flash(state, kind: str, x: int, y: int) -> LightFlash | None:
    """登记一次激活短光；未登记的 ``kind`` 直接忽略（不猜光色）。

    返回刚压入的那条，方便调用方/测试断言；**不改任何世界状态**——它不是
    伤害入口、不是探查入口，也不消耗随机流。
    """
    spec: LightFlashSpec | None = flash_spec(kind)
    if spec is None:
        return None
    seq = int(getattr(state, "_light_flash_seq", 0) or 0) + 1
    state._light_flash_seq = seq
    flash = LightFlash(
        seq=seq, kind=spec.kind, x=int(x), y=int(y), color=spec.color,
        radius=float(spec.radius), brightness=float(spec.brightness),
        life=float(spec.life), world_time=int(getattr(state, "time", 0) or 0),
        source_id=spec.flash_id,
    )
    queue = list(getattr(state, "light_flashes", ()) or ())
    queue.append(flash.to_dict())
    state.light_flashes = queue[-FLASH_MAX:]
    return flash
