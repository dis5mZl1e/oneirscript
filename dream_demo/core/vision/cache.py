"""视野集合缓存：``visible_cells()`` 的结果按「依赖签名」缓存复用。

为什么单独成模块：可见集合每帧（30fps 刷新）与每次鼠标悬停都会被请求，
逐格布雷森汉姆重算在大地图上是渲染热点的最大头；而它只依赖少数几个量——
客观时间、玩家位置、视距半径、照彻、植物布局（发光延长靠它）。把这些量
打包成一个签名，签名没变就直接复用上一次的结果。

缓存挂在 GameState 上（:data:`CACHE_ATTRIBUTE`），**不参与存档**：视野随时
可以重算，存它没有意义，反而会让旧存档把过期视野读回来。
"""

from __future__ import annotations

from typing import Any

# 缓存挂在 GameState 上的属性名（值为 ``(签名, 可见集合)``）。
CACHE_ATTRIBUTE = "_visible_cache"


def signature(state: Any) -> tuple:
    """可见集合的全部依赖，按值比较——任一变化都必须重算。

    - ``time``：照彻/锥光等按回合变化，异象位置也随回合变；
    - ``player.x / player.y``：视线起点；
    - ``effective_sight_radius()``：视距（含携带意象、征兆、构想、月下的修正）；
    - ``light_turns > 0``：灯塔「照彻」是全图可见的完全不同的分支；
    - ``plant_revision``：植物布局的变更计数（``GameState.set_plant`` 推进），
      决定发光能延长到哪些格——漏掉它就会出现「拔掉地衣后照亮区域还亮着」；
    - ``topology_revision``：墙体／门／推墙等遮挡关系变更计数（§10.5：同一世界时刻
      内改墙也必须重算）；
    - ``_sight_revision``：材料索引被生产侧置脏时推进（气体／烟雾／火／墙变化都会
      经 ``_material_index_ready = False`` 触发），§10.5 气体／烟雾半边据此失效。
    """
    return (
        state.time,
        state.player.x,
        state.player.y,
        state.effective_sight_radius(),
        state.light_turns > 0,
        state.plant_revision,
        state.topology_revision,
        int(getattr(state, "_sight_revision", 0)),
    )


def load(state: Any, key: tuple) -> set[tuple[int, int]] | None:
    """取缓存；签名不匹配（或从未算过）时返回 None。"""
    cached = getattr(state, CACHE_ATTRIBUTE, None)
    if cached is not None and cached[0] == key:
        return cached[1]
    return None


def store(state: Any, key: tuple, cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """写入缓存并原样返回可见集合，便于 ``return cache.store(...)``。"""
    setattr(state, CACHE_ATTRIBUTE, (key, cells))
    return cells


def invalidate(state: Any) -> None:
    """主动作废缓存（例如测试里手改地形后想立刻重算）。"""
    setattr(state, CACHE_ATTRIBUTE, None)
    # 机械光延长表（core/vision/glow.py）与可见集同生共死：显式作废时一起清，
    # 尽管它自己也按签名核对。
    state._glow_frame = None
