"""读档预取：打开存档页时后台把可安全读取的存档解码好，点「继续」直接复用。

为什么只在这里做：玩家从主页进存档页 → 看清三行槽位 → 再按 Enter，通常有
数百毫秒；把这期间的 CPU 用于 JSON 解析与状态解码，点击瞬间就只剩换会话和
首帧。预取在**后台线程**完成，不写玩家存档、不改任何文件；结果按
「文件 stat 键」校验，文件变了就作废，回落到正常读档。

为什么不直接调 SaveManager.load() 就完事：load() 遇到旧档会写迁移备份、追加
迁移提示，这些是玩家真正读档时才该发生的副作用。因此预取前先用
payload_needs_migration() 做一次保守检查：只要有任何版本化迁移迹象就不预取，
把这次读档完整留给点击时的正常路径。检查漏判的最坏结果也只是「打开存档页时
提前生成了迁移备份」，不会损坏存档；测试与文档都按这个边界写。

不预取的情况（一律走原路径）：主档不存在（只剩 backup）、JSON 损坏、格式过旧、
需要迁移、读档抛错。玩家直接按 1/2/3 再 Enter 的路径同样先开存档页并预取。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from ...persistence import SAVE_SCHEMA_VERSION, TERRAIN_SCALE_VERSION, SaveManager


def _slot_primary_key(manager: SaveManager) -> tuple[int, int] | None:
    """预取缓存键：只用主档的 (mtime_ns, size)。没有主档就不预取。

    主档损坏、靠 backup 恢复属于少数路径，交给点击时的正常 load()，避免缓存
    与「primary→backup 回退」的择档逻辑各算一套。
    """
    try:
        info = manager.primary.stat()
    except OSError:
        return None
    return (info.st_mtime_ns, info.st_size)


def payload_needs_migration(payload: Any, raw: Any) -> bool:
    """保守判断：这份存档读档时是否会触发 load() 里的迁移副作用。

    True / 判断不了 → 不预取。条件与 persistence.SaveManager.load() 的版本化
    迁移分支一一对应；将来新增迁移时必须同步这里，否则最坏结果是打开存档页时
    提前生成一次迁移备份（不损坏存档）。
    """
    try:
        if not isinstance(payload, dict) or not isinstance(raw, dict):
            return True
        if int(payload.get("schema_version", 1)) < SAVE_SCHEMA_VERSION:
            return True
        if int(raw.get("environment_rework_version", 0) or 0) < 1:
            return True
        if (int(raw.get("drug_debt_version", 0) or 0) < 1
                and int(raw.get("overclock_turns", 0) or 0) > 0):
            return True
        if "item_grant_counts" not in raw:
            from ...core.item_access import raw_legacy_awards
            if raw_legacy_awards(raw):
                return True
        if int(raw.get("system_roles_version", 0) or 0) < 1:
            return True
        if int(raw.get("firing_sources_version", 0) or 0) < 1:
            return True
        if int(raw.get("terrain_scale_version", 0) or 0) < TERRAIN_SCALE_VERSION:
            return True
        tutorial = raw.get("tutorial") or {}
        realm = raw.get("realm") or {}
        if (int(raw.get("depth", 0) or 0) == 0 and not realm.get("realm_id")
                and str(raw.get("map_form", "")) == "梦的起始"
                and isinstance(tutorial, dict) and tutorial.get("active")):
            from ...core.origin_course import COURSE_TEMPLATE_VERSION
            if (int(tutorial.get("version", 0) or 0) < COURSE_TEMPLATE_VERSION
                    and not tutorial.get("legacy_course_notice")):
                return True
        return False
    except Exception:
        return True


class SavePrefetcher:
    """单线程、按令牌作废的存档预取器（每个 App 一个实例）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: object | None = None
        self._results: dict[int, tuple[tuple[int, int], Any]] = {}
        self._thread: threading.Thread | None = None

    # ---- 生命周期 ----
    def start(self, root: Path, slots: list[int]) -> None:
        if not slots:
            return
        token = object()
        with self._lock:
            self._token = token
            self._results = {}
        thread = threading.Thread(
            target=self._work, args=(Path(root), tuple(slots), token),
            name="dream-save-prefetch", daemon=True)
        self._thread = thread
        thread.start()

    def wait(self, timeout: float | None = None) -> bool:
        """测试/探针用：等当前预取线程结束（不改变结果）。"""
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def take(self, root: Path, slot: int) -> Any | None:
        """取出并移除预取状态；文件自预取后变过则作废（返回 None）。"""
        manager = SaveManager(root).for_slot(slot)
        key = _slot_primary_key(manager)
        if key is None:
            return None
        with self._lock:
            entry = self._results.pop(slot, None)
        if entry is None:
            return None
        cached_key, state = entry
        return state if cached_key == key else None

    # ---- 线程体 ----
    def _work(self, root: Path, slots: tuple[int, ...], token: object) -> None:
        results: dict[int, tuple[tuple[int, int], Any]] = {}
        for slot in slots:
            manager = SaveManager(root).for_slot(slot)
            key = _slot_primary_key(manager)
            if key is None:
                continue
            try:
                payload = json.loads(manager.primary.read_text(encoding="utf-8"))
                raw = payload.get("state") if isinstance(payload, dict) else None
                if payload_needs_migration(payload, raw):
                    continue
                state = manager.load()
                # 万一预检查漏判（load 仍执行了迁移）：丢弃缓存，让点击时走正常
                # 读档；迁移备份最多已提前生成一次，不影响存档内容。
                if getattr(manager, "load_migrated", False):
                    continue
            except Exception:
                continue
            results[slot] = (key, state)
        with self._lock:
            if self._token is token:
                self._results = results
