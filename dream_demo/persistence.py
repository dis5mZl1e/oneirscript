from __future__ import annotations
from .materials import DOOR_KINDS

from dataclasses import asdict
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import shutil
import time
from typing import Any

from .core import ActionResult, Cell, Entity, GameState, ITEM_DEFINITIONS, Item, LayerSnapshot, Material, WorldEvent, WorldItem
from .core.constants import ELEV_STEP
from .core.vision.knowledge import (decode_hazard_memory, decode_terrain_memory,
                                    encode_terrain_memory)
from .core.save_kernel import (decode_cells as _kernel_decode_cells,
                               decode_compact_cell as _kernel_decode_compact_cell,
                               encode_cells as _kernel_encode_cells)
from .cy_kernels import enabled as _kernel_enabled
from .env_compat import flag as _env_flag
from .core.run_options import NEUTRAL_MODS as NEUTRAL_RUN_MODS
from .data.anomaly_skills import SKILL_DEFINITIONS
from .i18n import get_language, tr
from .equipment.root_facts import root_action
from .world.ledger import WorldLedger
from .map_generation import normalize_map_form
from .materials import DEFAULT_GAS, DEFAULT_LIQUID, DEFAULT_WALL, GAS_DEFINITIONS, LIQUID_DEFINITIONS, WALL_DEFINITIONS, wall_def


# ---------------------------------------------------------------------------
# 旧梦回忆：逐局历史条目（独立 history.json，跨存档槽汇总）
# ---------------------------------------------------------------------------

# 结局固定总结句（通关）；死亡句式按死因类型在 _death_cause 里组装。
HISTORY_ENDINGS: dict[str, dict[str, str]] = {
    "A": {"title": "初醒", "summary": "你选择了清晨，把梦留在稿纸背面。"},
    "B": {"title": "重写", "summary": "你夺回了笔，连同写坏的部分一起。"},
    "C": {"title": "放手", "summary": "故事由它收尾，你空着一块地方醒来。"},
    "D": {"title": "共写", "summary": "两支笔同时落下，谁也没盖过谁。"},
    # 27 层击破初啼之核后以 Enter 收局（未选醒来/深潜）。
    "core": {"title": "初啼之核", "summary": "啼哭止息，你在最深处找到了醒来的条件。"},
    "E": {"title": "沉没", "summary": ""},
    "F": {"title": "无梦", "summary": ""},
}
# 异象命中多少回合内致死，才把死因归到该异象（否则视为环境/耗尽）。
_HARM_RECENT_TURNS = 30


def _death_cause(state: GameState) -> tuple[str, str]:
    """死因归类：(kind, name)。kind ∈ epilogue / anomaly / env。

    - 深层边界（28-30）的死亡一律「沉没于深层边界」；
    - 死前 _HARM_RECENT_TURNS 回合内被异象真实命中 → 被该异象摧毁；
    - 其余按脚下现场推导（燃烧/气体/液体），都没有则「梦的重量」。
    """
    if state.depth >= 28:
        return "epilogue", "深层边界"
    if state.last_harm_source and state.time - state.last_harm_time <= _HARM_RECENT_TURNS:
        return "anomaly", state.last_harm_source
    cell = state.cell(state.player.x, state.player.y)
    if cell.flame > 0:
        return "env", "燃烧"
    if cell.gas > 0 and cell.gas_kind:
        return "env", cell.gas_kind
    if cell.liquid > 0 and cell.liquid_kind:
        return "env", cell.liquid_kind
    return "env", "梦的重量"


def _history_title_summary(state: GameState) -> tuple[str, str, bool]:
    """(结局名, 一句话, 是否通关)。"""
    ending_id = state.ending_id or ("core" if state.victory else "")
    definition = HISTORY_ENDINGS.get(ending_id)
    if definition is None:
        return tr("无梦"), tr("意识沉没于深层边界"), False
    if ending_id in ("E", "F"):
        kind, name = _death_cause(state)
        if kind == "epilogue":
            if state.run_stats.get("main_core_defeated"):
                return definition["title"], tr("已击破初啼之核；随后沉没于深层边界。"), False
            return definition["title"], tr("意识沉没于深层边界"), False
        if kind == "anomaly":
            return definition["title"], tr("意识被『{name}』摧毁了", name=name), False
        return definition["title"], tr("你因为『{name}』失去了意识", name=name), False
    return definition["title"], tr(definition["summary"]), True


def _build_history_entry(state: GameState, ts: float) -> dict[str, Any]:
    """从终局 state 装配一条游玩历史（含本局快照，供详细面板展示）。"""
    title, summary, victory = _history_title_summary(state)
    equipped_reverse = {instance_id: slot for slot, instance_id in (state.equipped or {}).items()}
    inventory = [
        {"id": item.definition_id, "slot": equipped_reverse.get(item.instance_id)}
        for item in state.inventory
    ]
    stats = state.run_stats or {}
    from .core.failure_review import build_review
    return {
        "ts": ts,
        "ending_id": state.ending_id or ("core" if state.victory else ""),
        "title": title,
        "summary": summary,
        "victory": victory,
        "main_core_defeated": bool(stats.get("main_core_defeated")),
        "difficulty_revision": int(state.difficulty_revision),
        "failure_review": build_review(state) if state.difficulty_revision >= 2 and not state.realm_id else {},
        "depth": int(state.depth),
        "stats": {
            "turns": int(state.time),
            "deepest": int(max(state.deepest_depth, state.depth) if state.depth > 0 else state.deepest_depth),
            "kills": int(stats.get("kills", 0)),
            "events": int(stats.get("events", 0)),
            "ignitions": int(stats.get("ignitions", 0)),
            "items_used": int(stats.get("items_used", 0)),
            "hits_taken": int(stats.get("hits_taken", 0)),
        },
        "inventory": inventory,
        "insights": list(state.insights),
        "abilities": list(state.abilities),
        "memories": list(state.memory_fragments),
    }


class OutdatedSaveError(RuntimeError):
    """梦痕格式过旧：**明确拒绝**载入并给出说明（重构方案 §12.2）。

    刻意不继承 ValueError/OSError/KeyError/TypeError——调用点惯用
    ``except (OSError, ValueError, KeyError, TypeError): continue`` 把坏档跳过，
    继承它们会让「拒绝旧档」被静默吞掉，退回「没有可恢复的梦痕」。
    """


#: 梦痕格式版本。2026-10-11 NPC／世界事件重构把它从 1 提到 2：一次性交易记账
#: 由「实例 id@坐标 → 选项显示下标」换成「actor_uid → option_id」，旧档里的账目
#: 既没有 uid 也没有 option_id，无法映射到新口径（方案 §15-P0「不要求读取旧存档」），
#: 所以拒绝载入，而不是用默认值把旧语义偷偷带进新系统。
SAVE_SCHEMA_VERSION = 2

#: 地势档位口径版本（§15.3）：旧实现把 ELEV_STEP 当一档，可能留下 ±25、±50…
#: 的档位。载入旧档时只做体检、原样保留并提示——正常位面地形、多次合法改造
#: 与旧版错值无法从数值可靠区分，不能按大小猜着除以 25 损坏整层地形。
TERRAIN_SCALE_VERSION = 1


def audit_legacy_elevations(state: GameState) -> dict[str, int]:
    """旧档地势体检：只统计，不改写。large＝绝对值达到一档换算值的格数。"""
    stats = {"cells": 0, "large": 0, "exact_steps": 0}
    grids = [state.cells]
    grids.extend(snapshot.cells for snapshot in state.layer_states.values()
                 if getattr(snapshot, "cells", None))
    for grid in grids:
        for row in grid:
            for cell in row:
                value = int(getattr(cell, "elevation", 0) or 0)
                stats["cells"] += 1
                if abs(value) >= ELEV_STEP:
                    stats["large"] += 1
                    if value % ELEV_STEP == 0:
                        stats["exact_steps"] += 1
    return stats


_JSON_KEY_TYPES = (str, int, float, bool, type(None))


def _sanitize_json_keys(value, path='state', found=None, depth=0):
    """把 JSON 不安全的字典键（典型是 (x, y) 元组）改成字符串键并记录路径。

    2026-10-27：原生会话里两次被 `json.dumps` 的
    "keys must be str, int, float, bool or None, not tuple" 打死——后台存档的
    编码异常会存进 `_async_error`，随后 `wait_for_pending_async_saves()` 抛
    OSError 直接终止 App。这里先保证「存档不因一个坏键就崩」，同时把坏键的
    路径记下来，便于定位真正的写入方。
    """
    if found is None:
        found = []
    if depth > 64:
        return value, found
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            safe_key = key if isinstance(key, _JSON_KEY_TYPES) else None
            if safe_key is None:
                safe_key = '|'.join(str(part) for part in key) if isinstance(key, tuple) else str(key)
                found.append(f"{path}.{safe_key}")
            out[safe_key] = _sanitize_json_keys(item, f"{path}.{safe_key}", found, depth + 1)[0]
        return out, found
    if isinstance(value, (list, tuple)):
        return [_sanitize_json_keys(item, f"{path}[{index}]", found, depth + 1)[0]
                for index, item in enumerate(value)], found
    return value, found


class SaveManager:
    SLOT_COUNT = 3

    def __init__(self, directory: str | Path, slot: int = 1):
        if not 1 <= slot <= self.SLOT_COUNT:
            raise ValueError("存档槽必须在 1 到 3 之间。")
        self.directory = Path(directory)
        self.slot = slot
        self.directory.mkdir(parents=True, exist_ok=True)
        suffix = "" if slot == 1 else f"-{slot}"
        self.primary = self.directory / f"run{suffix}.json"
        self.next_file = self.directory / f"run{suffix}.next.json"
        self.backup = self.directory / f"run{suffix}.backup.json"
        self.legacy = self.directory / "legacy.json"
        # 旧梦回忆：逐局游玩历史（跨存档槽汇总；详细列表最多保留 HISTORY_LIMIT 条，
        # 游玩/通关总计数独立累加、不受列表上限影响）。
        self.history = self.directory / "history.json"
        self.catalog_file = self.directory / "catalog.json"
        # 周期存档异步写盘（docs §11）：主线程只做 _encode（状态快照），
        # JSON 序列化/备份/重命名在单工作线程里完成。同步 save/load 会先等它。
        self._async_executor: ThreadPoolExecutor | None = None
        self._async_futures: list[Future] = []
        self._async_error: Exception | None = None
        # UI 契约：本次 load() 是否真的执行了旧档迁移。只有 True 时调用方才需要
        # 立刻把迁移结果落盘；普通新档为 False。读档失败路径也必须保证属性存在。
        self.load_migrated: bool = False
        # 图鉴读取缓存（纯进程内，不落盘、不改存档格式）：键是
        # (文件路径, st_mtime_ns, st_size)，值是已规范化的 entries。外部改写文件
        # 会改变 stat 键而失效；save_catalog 写盘后立即重建缓存。load_catalog
        # 永远返回副本，调用方改返回值不会污染缓存。
        self._catalog_cache_key: tuple[str, int, int] | None = None
        self._catalog_cache_entries: dict[str, dict[str, Any]] | None = None

    def save(self, state: GameState) -> None:
        try:
            self.wait_for_pending_async_saves()
        except Exception as error:
            # 上一次后台编码失败不该阻断这一次落盘：记下来，照常写新快照。
            self._record_save_diagnostic(error, ['pending-async'])
        payload = {"schema_version": SAVE_SCHEMA_VERSION, "state": self._encode_safe(state)}
        self.next_file.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if self.primary.exists():
            shutil.copyfile(self.primary, self.backup)
        self.next_file.replace(self.primary)
        self.save_catalog(state.catalog)

    def _encode_safe(self, state: GameState) -> dict[str, Any]:
        """编码后先自检一次 JSON 安全性；发现元组键就隔离并记诊断，绝不抛出。

        异常路径只影响这一次存档的形状（坏键变成字符串键），不影响游戏线程；
        诊断写 `save/_save_diagnostics.log`，下一次就能定位真正的写入方。
        """
        encoded = self._encode(state)
        try:
            json.dumps(encoded, ensure_ascii=False)
            return encoded
        except TypeError as error:
            fixed, paths = _sanitize_json_keys(encoded)
            try:
                json.dumps(fixed, ensure_ascii=False)
            except TypeError:
                paths = paths or ['state(未定位)']
            self._record_save_diagnostic(error, paths)
            return fixed

    def _record_save_diagnostic(self, error, paths) -> None:
        self.last_save_diagnostic = {'error': repr(error), 'paths': list(paths)}
        try:
            log = self.directory / '_save_diagnostics.log'
            stamp = time.strftime('%Y-%m-%d %H:%M:%S')
            with log.open('a', encoding='utf-8') as handle:
                handle.write(f"{stamp} {error!r} paths={list(paths)[:20]}\n")
        except Exception:
            pass

    def _write_encoded_async(self, encoded: dict[str, Any]) -> None:
        text = json.dumps({"schema_version": SAVE_SCHEMA_VERSION, "state": encoded},
                          ensure_ascii=False, separators=(",", ":"))
        self.next_file.write_text(text, encoding="utf-8")
        if self.primary.exists():
            shutil.copyfile(self.primary, self.backup)
        self.next_file.replace(self.primary)

    def _ensure_async_executor(self) -> ThreadPoolExecutor:
        if self._async_executor is None:
            self._async_executor = ThreadPoolExecutor(max_workers=1,
                                                      thread_name_prefix="dream-save")
        return self._async_executor

    def _track_async_future(self, future: Future) -> None:
        self._async_futures.append(future)

        def done(fut: Future) -> None:
            try:
                fut.result()
            except Exception as error:  # 磁盘错误不能影响游戏线程
                self._async_error = error
        future.add_done_callback(done)

    def _encode_and_write_with_lock(self, state: GameState, lock) -> None:
        """在动作锁内编码，随后在锁外写盘；主线程不再执行 _encode。"""
        with lock:
            encoded = self._encode_safe(state)
            self.save_catalog(state.catalog)
        self._write_encoded_async(encoded)

    def save_async(self, state: GameState, lock=None) -> Future:
        """Encode/write in one background worker; main thread returns immediately.

        lock 给真实游戏传 GameSession._action_lock：编码期间动作互斥，避免
        读到半更新状态。调用方若需要确定性（测试/退出），用
        wait_for_pending_async_saves()。目录/文件命名不变，失败记录在
        _async_error。
        """
        # 单工作线程保证 FIFO 写序；最多积压 4 个待写快照再阻塞，避免
        # 每次周期存档都为上一次写盘等待而失去异步收益。
        if len(self._async_futures) >= 4:
            self.wait_for_pending_async_saves()
        executor = self._ensure_async_executor()
        if lock is None:
            # 兼容旧调用/测试：编码在调用线程完成，保存调用时的确定性快照。
            encoded = self._encode_safe(state)
            future = executor.submit(self._write_encoded_async, encoded)
            self._track_async_future(future)
            self.save_catalog(state.catalog)
            return future
        future = executor.submit(self._encode_and_write_with_lock, state, lock)
        self._track_async_future(future)
        return future

    def wait_for_pending_async_saves(self) -> None:
        futures, self._async_futures = self._async_futures, []
        for future in futures:
            try:
                future.result()
            except Exception as error:
                self._async_error = error
        if self._async_error is not None:
            error, self._async_error = self._async_error, None
            raise OSError(f"后台存档失败：{error}")

    @staticmethod
    def _migrate_firing_sources(state: GameState) -> bool:
        """One-time inheritance for saves written before unified firing sources.

        Only a permanent license that was not board-derived becomes the independent
        inherited source; board-derived licenses are just real equipment now.
        """
        from .core.firing_sources import LEGACY_BASIC_ID, MAGAZINE_SPECS
        spec = MAGAZINE_SPECS[LEGACY_BASIC_ID]
        inherited = (bool(getattr(state, 'fire_unlocked', False))
                     and not bool(getattr(state, 'fire_from_board', False)))
        state.legacy_basic_magazine = spec.capacity if inherited else None
        state.legacy_basic_reload_steps = 0
        state.legacy_basic_reload_paid = False
        state.firing_sources_version = 1
        return inherited

    @staticmethod
    def _normalize_firing_sources(state: GameState) -> None:
        """Clamp damaged magazine data without ever refilling it.

        A corrupt step count loses its progress and, with it, the right to claim
        the first step was already paid; it must not become a free refill.
        """
        from .core.firing_sources import LEGACY_BASIC_ID, MAGAZINE_SPECS, magazine_spec
        legacy_spec = MAGAZINE_SPECS[LEGACY_BASIC_ID]
        if state.legacy_basic_magazine is not None:
            state.legacy_basic_magazine = max(
                0, min(legacy_spec.capacity, int(state.legacy_basic_magazine)))
            steps = int(state.legacy_basic_reload_steps or 0)
            if not 0 < steps < legacy_spec.reload_time:
                steps = 0
                state.legacy_basic_reload_paid = False
            state.legacy_basic_reload_steps = steps
            if not steps:
                state.legacy_basic_reload_paid = False
        for item in state.inventory:
            rule = magazine_spec(item.definition_id)
            if rule is None or getattr(item, 'magazine', None) is None:
                continue
            item.magazine = max(0, min(rule.capacity, int(item.magazine)))
            capacity = int(getattr(item, 'magazine_capacity', 0) or 0)
            if not 0 < capacity <= rule.capacity:
                item.magazine_capacity = rule.capacity
            steps = int(getattr(item, 'reload_steps', 0) or 0)
            if not 0 < steps < rule.reload_time:
                steps = 0
                item.reload_paid = False
            item.reload_steps = steps
            if not steps:
                item.reload_paid = False

    def load(self) -> GameState:
        # UI 契约：读档一开始就定义标记；失败路径（无档/旧档拒绝/坏档跳过）也保持
        # False，调用方用 getattr(manager, 'load_migrated', False) 读取。
        self.load_migrated = False
        self.wait_for_pending_async_saves()
        for path in (self.primary, self.backup):
            if not path.exists():
                continue
            # 每个候选文件独立判定：主档坏了落到备份重试时，不能沿用上一份的标记。
            self.load_migrated = False
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            try:
                version = int(payload.get("schema_version", 1)) if isinstance(payload, dict) else 0
            except (TypeError, ValueError):
                version = 0
            if version < SAVE_SCHEMA_VERSION:
                raise OutdatedSaveError(tr(
                    "这份梦痕是旧版存档（格式 v{old}，当前 v{new}）：NPC 与世界事件的记账口径已经换掉，"
                    "旧账目无法映射——请开一局新梦。",
                    old=version, new=SAVE_SCHEMA_VERSION))
            try:
                raw = payload['state']
                environment_upgrade = int(raw.get('environment_rework_version', 0) or 0) < 1
                if environment_upgrade:
                    migration_backup = path.with_name(path.stem + '.before-environment-rework-v1.json')
                    if not migration_backup.exists():
                        shutil.copyfile(path, migration_backup)
                drug_upgrade = (int(raw.get('drug_debt_version', 0) or 0) < 1
                                and int(raw.get('overclock_turns', 0) or 0) > 0)
                if drug_upgrade:
                    migration_backup = path.with_name(path.stem + '.before-drug-debts-v1.json')
                    if not migration_backup.exists():
                        shutil.copyfile(path, migration_backup)
                from .core.item_access import raw_legacy_awards
                limited_upgrade = 'item_grant_counts' not in raw and bool(raw_legacy_awards(raw))
                if limited_upgrade:
                    migration_backup = path.with_name(path.stem + '.before-limited-items-v1.json')
                    if not migration_backup.exists():
                        shutil.copyfile(path, migration_backup)
                state = self._decode(raw)
                if limited_upgrade:
                    self.load_migrated = True
                    state.messages.append(tr('限定显化物已补记本局发放记录：现有数量原样保留，丢弃或使用不会重置获取上限；载入前梦痕已备份。'))
                if drug_upgrade:
                    self.load_migrated = True
                    state.messages.append(tr('药物债务已改为逐份独立结算：只继承尚未支付的期数和原扣款时刻，不补收过去的账单；载入前梦痕已备份。'))
                if environment_upgrade:
                    self.load_migrated = True
                    state.environment_rework_version = 1
                    state.messages.append(tr('环境适配规则已更新：已有构想、洞察与记忆碎片采用新版范围、声音和条件效果；持有内容与槽位保留，旧构想残留按原剩余期限结束，载入前梦痕已备份。'))
                if int(raw.get('system_roles_version', 0)) < 1:
                    self.load_migrated = True
                    migration_backup = path.with_name(path.stem + '.before-system-roles-v1.json')
                    if not migration_backup.exists():
                        shutil.copyfile(path, migration_backup)
                    state.system_roles_version = 1
                    state.messages.append(tr('四系统规则已更新：记忆碎片改为耐受，洞察提供条件行动，构想与篡改采用新规则；原持有内容保留，迁移前梦痕已备份。'))
                    state.memory_effect_awards = list(dict.fromkeys([*state.memory_effect_awards, *state.memory_fragments]))
                if int(raw.get('firing_sources_version', 0) or 0) < 1:
                    self.load_migrated = True
                    migration_backup = path.with_name(path.stem + '.before-firing-sources-v1.json')
                    if not migration_backup.exists():
                        shutil.copyfile(path, migration_backup)
                    inherited = SaveManager._migrate_firing_sources(state)
                    if inherited:
                        state.messages.append(tr(
                            '发射来源已经统一：可用来源可以自由切换，无限来源改为逐武器弹匣并需要付费换弹，U 键不再解锁发射。'
                            '旧档的永久发射许可已继承为独立来源「基础发射（旧档继承）」：容量 3，换弹 2 行动／3 想象；'
                            '它不会让其他武器获得无限库存。聚合弹数量原样保留；迁移前梦痕已备份。'))
                    else:
                        state.messages.append(tr(
                            '发射来源已经统一：可用来源可以自由切换，无限来源改为逐武器弹匣并需要付费换弹，U 键不再解锁发射。'
                            '本次未发现可继承的永久发射许可（或旧许可只来自盘面装备），因此只按真实装备与聚合弹生成来源；'
                            '旧结构无法可靠区分历史付费与装备许可，未额外赠送能力。物品、联想盘与构想原样保留；迁移前梦痕已备份。'))
                SaveManager._normalize_firing_sources(state)
                if int(raw.get('terrain_scale_version', 0) or 0) < TERRAIN_SCALE_VERSION:
                    # 该分支一定会改写版本号（可能还追加提示），按「宁可多写一次盘」
                    # 口径置 True；不依赖 stats['large'] 是否真的提示。
                    self.load_migrated = True
                    stats = audit_legacy_elevations(state)
                    state.terrain_scale_version = TERRAIN_SCALE_VERSION
                    if stats['large']:
                        migration_backup = path.with_name(path.stem + '.before-terrain-scale-v1.json')
                        if not migration_backup.exists():
                            shutil.copyfile(path, migration_backup)
                        state.messages.append(tr(
                            '旧梦痕里有 {n} 格地势绝对值达到 {step} 档以上（其中 {exact} 格正好是 {step} 的整数倍）。'
                            '这既可能来自多次合法改造，也可能来自旧版把 {step} 当一档加减的错值；无法可靠区分，'
                            '因此全部原样保留，不按数值猜测改写，迁移前梦痕已备份。可在地势视图核对。',
                            n=stats['large'], exact=stats['exact_steps'], step=ELEV_STEP))
                if (state.depth == 0 and not state.realm_id
                        and state.map_form == '梦的起始' and state.tutorial.get('active')):
                    from .core.origin_course import COURSE_TEMPLATE_VERSION
                    course_version = int(state.tutorial.get('version', 0) or 0)
                    if course_version < COURSE_TEMPLATE_VERSION and not state.tutorial.get('legacy_course_notice'):
                        migration_backup = path.with_name(path.stem + '.before-origin-course-v2.json')
                        if not migration_backup.exists():
                            shutil.copyfile(path, migration_backup)
                        self.load_migrated = True
                        state.tutorial['legacy_course_notice'] = True
                        state.messages.append(tr(
                            '旧梦痕的 0 层仍是已退役的十二步教学图（教程 v{old}）：新版「梦的起始」课程不接管这一张图，旧步骤与进度不映射到新的子目标，也不按新地图伪造完成；本层地形、持有与掉落原样保留。要上新课程请开一局新梦，提示前的梦痕已备份。',
                            old=course_version or 1))
                return state
            except (OSError, ValueError, KeyError, TypeError):
                continue
        raise FileNotFoundError("没有可恢复的梦痕。")

    def inherited_memory(self) -> str | None:
        """⚠️ 已弃用（2026-10-09）：跨局记忆碎片继承删除，开局改为三选一。

        保留空实现是为了旧调用点不至于 AttributeError；新代码不得调用。
        """
        return None

    # 旧梦回忆详细列表上限；更早的条目被顶掉（总计数不受影响）。
    HISTORY_LIMIT = 100

    def record_finished_run(self, state: GameState) -> None:
        """终局落账：写一条游玩历史（旧梦回忆）+ 并入跨局记忆池。

        只在结局发生的那一刻调用一次（A-D/E/F/初啼之核胜利）；玩家中途删档、
        保存退出都不会写——没有结局的局不进统计。
        """
        import time as _time

        entry = _build_history_entry(state, _time.time())
        history = {"schema_version": 1, "total_runs": 0, "total_wins": 0, "runs": []}
        if self.history.exists():
            try:
                loaded = json.loads(self.history.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    history["total_runs"] = int(loaded.get("total_runs", 0) or 0)
                    history["total_wins"] = int(loaded.get("total_wins", 0) or 0)
                    runs = loaded.get("runs", [])
                    history["runs"] = runs if isinstance(runs, list) else []
            except (OSError, ValueError, TypeError):
                pass
        history["total_runs"] += 1
        if entry["victory"]:
            history["total_wins"] += 1
        history["runs"].append(entry)
        # 上限裁剪：只顶掉最早的详细记录，最早的先入列、也就先被挤出。
        del history["runs"][: max(0, len(history["runs"]) - self.HISTORY_LIMIT)]
        self.history.write_text(
            json.dumps(history, ensure_ascii=False), encoding="utf-8"
        )
        # 跨局记忆池已删除（2026-10-09 玩家定稿）：不再把碎片并给下一局。
        # legacy.json 若仍存在（旧版本写入）原样保留，不再读写。

    def load_history(self) -> dict[str, Any]:
        """读取旧梦回忆（无文件或损坏时回落空结构）。"""
        if self.history.exists():
            try:
                loaded = json.loads(self.history.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    return {
                        "total_runs": int(loaded.get("total_runs", 0) or 0),
                        "total_wins": int(loaded.get("total_wins", 0) or 0),
                        "runs": list(loaded.get("runs", []) or []),
                    }
            except (OSError, ValueError, TypeError):
                pass
        return {"total_runs": 0, "total_wins": 0, "runs": []}

    def clear_run(self) -> None:
        for path in (self.primary, self.next_file, self.backup):
            if path.exists():
                path.unlink()

    def for_slot(self, slot: int) -> "SaveManager":
        return SaveManager(self.directory, slot)

    def slot_exists(self, slot: int | None = None) -> bool:
        manager = self if slot is None else self.for_slot(slot)
        return manager.primary.exists() or manager.backup.exists()

    @staticmethod
    def _copy_catalog_entries(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """返回图鉴 entries 的副本：dict 与每条 entry 的 list 都复制。

        调用方（UI 面板、merge_catalogs 的输入）会改返回值；直接给出缓存对象
        会让下一次读档读到被改脏的图鉴。
        """
        return {
            key: {
                **value,
                "drops_seen": list(value.get("drops_seen") or []),
                "details": list(value.get("details") or []),
            }
            for key, value in entries.items()
        }

    def _catalog_stat_key(self, path: Path) -> tuple[str, int, int] | None:
        try:
            info = path.stat()
        except OSError:
            return None
        return (str(path), info.st_mtime_ns, info.st_size)

    def _remember_catalog_cache(self, entries: dict[str, dict[str, Any]]) -> None:
        """写盘后立刻用新内容重建缓存；stat 拿不到就失效（下次回源读取）。

        缓存内部存的是防御性副本，不保留调用方传入的 dict/list 引用。
        """
        stat_key = self._catalog_stat_key(self.catalog_file)
        if stat_key is None:
            self._catalog_cache_key = None
            self._catalog_cache_entries = None
            return
        self._catalog_cache_key = stat_key
        # 防御性副本：调用方常把刚传给 save_catalog 的同一个 dict 赋给
        # state.catalog 并继续原地修改（panels 的解锁全部图鉴路径）；直接存引用
        # 会让这些运行期改动被当成「磁盘上的内容」返回，直到 stat 变化。
        self._catalog_cache_entries = self._copy_catalog_entries(entries)

    def load_catalog(self) -> dict[str, Any]:
        path = self.catalog_file
        if not path.exists():
            self._catalog_cache_key = None
            self._catalog_cache_entries = None
            return {}
        stat_key = self._catalog_stat_key(path)
        if (stat_key is not None and stat_key == self._catalog_cache_key
                and self._catalog_cache_entries is not None):
            return self._copy_catalog_entries(self._catalog_cache_entries)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries = payload.get("entries", {})
            if not isinstance(entries, dict):
                return {}
            catalog = {
                key: self._normalize_catalog_entry(key, value)
                for key, value in entries.items()
                if isinstance(key, str) and isinstance(value, dict)
            }
        except (OSError, ValueError, TypeError):
            return {}
        if stat_key is not None:
            self._catalog_cache_key = stat_key
            self._catalog_cache_entries = catalog
        return self._copy_catalog_entries(catalog)

    def save_catalog(self, catalog: dict[str, Any]) -> None:
        merged = self.merge_catalogs(self.load_catalog(), catalog)
        self.catalog_file.write_text(json.dumps({"schema_version": 1, "entries": merged}, ensure_ascii=False, indent=2), encoding="utf-8")
        # 刚写出的内容就是 merged：直接建缓存，省掉紧接着读档/存档时的回源解析。
        # 外部改写由 stat 键失效兜底。
        self._remember_catalog_cache(merged)

    # 图鉴分类集合只依赖 CatalogCategory 枚举；按类缓存，避免每条 entry 都构造一次。
    _catalog_categories_cache: frozenset[str] | None = None

    @staticmethod
    def _catalog_category(key: str) -> str:
        if key.startswith("item."):
            # ⚠️ 只为「旧档里没有 category 字段」的条目兜底。
            # 能装进栏位的物品现在有自己的分类 carried_image，但旧档没这个信息，
            # 只能先落到 manifestation；重开一局重建图鉴时由 catalog_registry
            # 按 slot 重新判定（白名单见 _known_catalog_categories）。
            return "manifestation"
        if key.startswith("event."):
            return "site"
        return "consciousness"

    @staticmethod
    def _known_catalog_categories() -> frozenset[str]:
        """图鉴认可的分类 id 集合：从枚举推导，避免硬编码漏掉新增分类。

        ⚠️ 这里原来是字面量 ``{"consciousness", "manifestation", "site"}``：
        新增 carried_image 之后，存量条目每次读档都会因为「分类不认识」而被
        改回 manifestation——新分类在存档里永远留不住。改成枚举推导自动跟上。
        """
        cached = SaveManager._catalog_categories_cache
        if cached is None:
            from .catalog_registry import CatalogCategory

            cached = frozenset(member.value for member in CatalogCategory)
            SaveManager._catalog_categories_cache = cached
        return cached

    @classmethod
    def _normalize_catalog_entry(cls, key: str, value: dict[str, Any]) -> dict[str, Any]:
        def count(field: str) -> int:
            raw = value.get(field, 0)
            return max(0, raw) if isinstance(raw, int) and not isinstance(raw, bool) else 0

        def unique_strings(field: str) -> list[str]:
            result: list[str] = []
            raw = value.get(field, [])
            if not isinstance(raw, list):
                return result
            for item in raw:
                if isinstance(item, str) and item not in result:
                    result.append(item)
            return result

        name = value.get("name", key)
        category = value.get("category", cls._catalog_category(key))
        known = cls._known_catalog_categories()
        return {
            "name": name if isinstance(name, str) else key,
            "category": category if category in known else cls._catalog_category(key),
            "encounters": count("encounters"),
            "interactions": count("interactions"),
            "kills": count("kills"),
            "drops_seen": unique_strings("drops_seen"),
            "details": unique_strings("details"),
        }

    @classmethod
    def merge_catalogs(cls, *catalogs: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for catalog in catalogs:
            if not isinstance(catalog, dict):
                continue
            for key, raw in catalog.items():
                if not isinstance(key, str) or not isinstance(raw, dict):
                    continue
                value = cls._normalize_catalog_entry(key, raw)
                current = merged.setdefault(key, value)
                if current is value:
                    continue
                current["name"] = value["name"] or current["name"]
                current["category"] = value["category"]
                for field in ("encounters", "interactions", "kills"):
                    current[field] = max(current[field], value[field])
                for field in ("drops_seen", "details"):
                    for item in value[field]:
                        if item not in current[field]:
                            current[field].append(item)
        return merged

    # ---- 紧凑存档编码 -------------------------------------------------
    # 存档体随访问层数线性增长（每层一份完整地图快照）——dataclasses.asdict
    # 的递归深拷贝 + 带缩进 JSON 在 20 层后期一次存档接近 1 秒 / 14 MB，是
    # 「越往后越卡」的主因（每 10 回合自动存档一次即一次可见卡顿）。
    # 改为：格子编码为定长列表 + 字符串驻留表（种类字符串只存一次），
    # 层快照手工构建避免 asdict 递归整幅地图，JSON 使用紧凑分隔符。
    # 前六项是常见变体，序位历史上就固定了（存档按下标引用，不可重排）；
    # 稀有变体追加在尾部，老存档的下标不受影响（未登记的字符串本就会动态入表）。
    _AGGREGATE_VARIANTS = (
        "普通聚合物",
        "柔软聚合物",
        "粗糙聚合物",
        "反光聚合物",
        "吸声聚合物",
        "空白聚合物",
        "木质聚合物",
        "海绵聚合物",
        "金属聚合物",
        "灼热聚合物",
    )

    @staticmethod
    def _make_tables() -> dict[str, list[str]]:
        return {
            "floors": [material.value for material in Material],
            "variants": list(SaveManager._AGGREGATE_VARIANTS),
            "walls": list(WALL_DEFINITIONS),
            "liquids": list(LIQUID_DEFINITIONS),
            "gases": list(GAS_DEFINITIONS),
        }

    @staticmethod
    def _intern(tables: dict[str, list[str]], key: str, value: str,
                cache: dict[str, dict[str, int]] | None = None) -> int:
        """字符串 → 表内下标；未知字符串动态入表（前向兼容）。

        cache 是单次 _encode 内的 key→value→下标字典：同一张表内值很多时，
        比每格 list.index 线性扫描快；不改变表内容/顺序。
        """
        if cache is not None:
            index_map = cache.get(key)
            if index_map is None:
                index_map = cache[key] = {}
            found = index_map.get(value)
            if found is not None:
                return found
            index = len(tables[key])
            tables[key].append(value)
            index_map[value] = index
            return index
        table = tables[key]
        try:
            return table.index(value)
        except ValueError:
            table.append(value)
            return len(table) - 1

    @staticmethod
    def _lookup(tables: dict[str, list[str]], key: str, index: int, default: str = "") -> str:
        table = tables.get(key) or []
        return table[index] if 0 <= index < len(table) else default

    @staticmethod
    def _encode_cell(cell: Cell, tables: dict[str, list[str]],
                    cache: dict[str, dict[str, int]] | None = None) -> list:
        encoded = [
            SaveManager._intern(tables, "floors", cell.floor.value, cache),
            1 if cell.solid else 0,
            cell.liquid,
            cell.gas,
            cell.hardness,
            cell.thickness,
            cell.integrity,
            cell.cover,
            cell.flame,
            SaveManager._intern(tables, "variants", cell.aggregate_variant, cache),
            SaveManager._intern(tables, "walls", cell.wall_kind, cache),
            cell.height,
            cell.elevation,
            SaveManager._intern(tables, "liquids", cell.liquid_kind, cache),
            SaveManager._intern(tables, "gases", cell.gas_kind, cache),
            cell.plant,
            cell.wire,
        ]
        progress = [cell.plant_fuel, cell.floor_fuel, cell.item_burn_progress]
        while progress and progress[-1] == 0:
            progress.pop()
        encoded.extend(progress)
        if cell.creation:
            encoded.extend([0] * (20 - len(encoded)))
            encoded.append(dict(cell.creation))
        if cell.material_clocks:
            encoded.extend([0] * (21 - len(encoded)))
            encoded.append(dict(cell.material_clocks))
        if cell.light_radius or not cell.light_on:
            encoded.extend([0] * (22-len(encoded)))
            encoded.append(cell.light_radius)
            if not cell.light_on:
                encoded.append(False)
        if cell.doorway:
            encoded.extend([0] * (22-len(encoded)))
            if len(encoded) == 22:
                encoded.append(cell.light_radius)
            if len(encoded) == 23:
                encoded.append(cell.light_on)
            encoded.append(True)
        if cell.phase_stock:
            defaults = [cell.plant_fuel, cell.floor_fuel, cell.item_burn_progress,
                        dict(cell.creation), dict(cell.material_clocks),
                        cell.light_radius, cell.light_on, cell.doorway]
            while len(encoded) < 25:
                encoded.append(defaults[len(encoded)-17])
            encoded.append(dict(cell.phase_stock))
        if cell.plant_state:
            # 第 27 位（索引 26）：植物的一次性／有限状态。旧的尾部块按位置写，
            # 所以这里必须把 17–25 用真实值补齐——不能只补 0，否则 doorway
            # 会被写成 False、phase_stock 会被写成 0。
            defaults = [cell.plant_fuel, cell.floor_fuel, cell.item_burn_progress,
                        dict(cell.creation), dict(cell.material_clocks),
                        cell.light_radius, cell.light_on, cell.doorway,
                        dict(cell.phase_stock)]
            while len(encoded) < 26:
                encoded.append(defaults[len(encoded)-17])
            encoded.append(dict(cell.plant_state))
        return encoded

    @staticmethod
    def _encode_cells(rows: list, tables: dict[str, list[str]],
                      cache: dict[str, dict[str, int]] | None = None) -> list[list[list]]:
        """批量编码一层的紧凑格：CY-7 编译内核（默认关闭），否则用原实现。

        实测（2026-10-27，1.8MB / 10800 格）：编码内核把逐格编码从约
        12.9ms 降到 7.5ms（-5.3ms），但整条 save p50 只降约 5–6%，低于
        「save p50 降低 ≥10%」的保留线，因此**默认不走内核**；源码与复测
        开关 ``ONEIRSCRIPT_CY_KERNEL_SAVE_ENCODE=1`` 保留（仍受 save 总开关
        ``ONEIRSCRIPT_CY_KERNEL_SAVE`` 约束）。
        只有 _encode 会传入 cache；cache 为 None 时继续走逐格回退，保持
        ``_encode_cell(cache=None)`` 的 list.index 语义不变。
        """
        if (cache is not None and _kernel_enabled("save")
                and _env_flag("CY_KERNEL_SAVE_ENCODE", default=False)):
            return _kernel_encode_cells(rows, tables, cache)
        return [[SaveManager._encode_cell(cell, tables, cache) for cell in row]
                for row in rows]

    @staticmethod
    def _encode_layer(snapshot: LayerSnapshot, tables: dict[str, list[str]],
                     cache: dict[str, dict[str, int]] | None = None) -> dict[str, Any]:
        return {
            "depth": snapshot.depth,
            "seed": snapshot.seed,
            "cells": SaveManager._encode_cells(snapshot.cells, tables, cache),
            "enemies": [asdict(enemy) for enemy in snapshot.enemies],
            "world_items": [asdict(item) for item in snapshot.world_items],
            "events": [asdict(event) for event in snapshot.events],
            "player_x": snapshot.player_x,
            "player_y": snapshot.player_y,
            "dissolution": snapshot.dissolution,
            "theme": snapshot.theme,
            "map_form": snapshot.map_form,
            "width": snapshot.width,
            "height": snapshot.height,
            "logic_scenarios": {k: str(v) for k, v in snapshot.logic_scenarios.items()},
            "logic_valves": {k: list(v) for k, v in snapshot.logic_valves.items()},
            "logic_boards": snapshot.logic_boards,
            "logic_fences": snapshot.logic_fences,
            "enemy_skill_fields": snapshot.enemy_skill_fields,
            "realm_bg_zones": snapshot.realm_bg_zones,
            "material_time": snapshot.material_time,
            "realm_features": snapshot.realm_features,
        }

    @staticmethod
    @staticmethod
    def _decode_board(data: dict[str, Any], legacy_equipped: dict[str, str],
                      inventory: list) -> tuple[Any, str]:
        """读盘面；旧五栏存档走无损迁移（枚举旋转并回溯装箱，不贪心）。

        迁移失败时**不**静默卸下、丢弃或挤满行囊：返回空盘与一条可读说明，
        所有权仍在行囊里，玩家整理后重新上盘。
        """
        from .equipment.board import EquipmentBoard
        from .equipment.item_shapes import shape_for, is_material_source
        from .equipment.senses import default_sense, resolve
        from .i18n import tr

        if data.get("board"):
            try:
                board = EquipmentBoard.from_dict(data['board'])
                owned = {it.instance_id: it for it in inventory}
                problems = board.errors(allowed_instances=set(owned))
                for placement in board.placements:
                    item = owned.get(placement.instance_id)
                    if item is not None and (placement.definition_id != item.definition_id
                                             or (not item.slot and not is_material_source(item.definition_id))
                                             or item.slot == '记忆槽'):
                        problems.append('instance_mismatch')
                if not problems:
                    if int(data['board'].get('schema_version', 1)) < 3:
                        from .equipment.migration import assemble
                        migrated = assemble([(p.instance_id, p.definition_id) for p in board.placements],
                                            snapshot=board.legacy_snapshot)
                        if migrated is not None:
                            board = migrated
                        return board, tr('联想盘已迁移为位置语句；旧握持、词义与线路仅保存在迁移快照中，请检查当前句子。')
                    return board, ''
            except (ValueError, TypeError, KeyError, AttributeError):
                pass
            return EquipmentBoard(), tr('存档中的联想盘布局无效；意象仍在行囊中，请重新整理。')
        entries: list[tuple[str, str]] = []
        focus_id: str | None = None
        for slot, instance_id in (legacy_equipped or {}).items():
            item = next(
                (it for it in inventory if it.instance_id == instance_id), None
            )
            if item is None or not item.slot or item.slot == "记忆槽":
                continue
            entries.append((instance_id, item.definition_id))
            if slot == "手中意象":
                focus_id = instance_id
        if not entries:
            return EquipmentBoard(), ""
        from .equipment.migration import assemble
        board = assemble(entries, snapshot={"equipped": dict(legacy_equipped or {})})
        if board is None:
            return EquipmentBoard(), tr(
                "旧存档的五栏组合在 8×6 联想盘上放不下：装备仍留在行囊里，请重新整理上盘。"
            )
        return board, tr('联想盘已迁移为位置语句；旧握持、词义与线路仅保存在迁移快照中，请检查当前句子。')

    @staticmethod
    def _encode(state: GameState) -> dict[str, Any]:
        tables = SaveManager._make_tables()
        cache: dict[str, dict[str, int]] = {}
        # 顶层浅拷贝（asdict 会递归深拷贝全部层快照的整幅地图，是存档
        # 耗时的大头）；少量实体逐个 asdict，格子走紧凑编码。
        runtime_caches = ("_liquid_cells", "_gas_cells", "_periodic_liquid_cells", "_periodic_gas_cells", "_flame_cells", "_special_cells", "_ventilation_cells", "_exhaust_cells", "_phase_cells",
                          "_material_index_ready", "_material_index_ready_value",
                          "_sight_revision", "_visible_cache",
                          # 本帧机械光延长表（core/vision/glow.publish_frame）：键是格坐标，
                          # 进了 JSON 就是「keys must be ... not tuple」；视野随时可重算。
                          "_glow_frame",
                          # 光类装备（2026-10-25 批次二）的光照叠加表同样是运行期缓存：
                          # 内容全部由刻痕／上盘表现算，存进存档只会留下过期副本。
                          "_gear_light_overlay", "_gear_light_rev",
                          "last_sound_pulse", "_sound_pulse_seq",
                          "_region_proximity_turns",
                          "_kill_full_reward", "_superfluid_notified_depths", "_piezo_stacks",
                          "_recipe_notified_depths",
                          "explosion_cells", "explosion_age", "_last_full_scan_time",
                          "_mind_fences", "_rune_cooldowns", "_position_history", "explosion_blasts",
                          "gate_inputs", "_logic_energized", "_gate_evaluating",
                          "realm_gate_open", "realm_plate_order", "realm_plate_progress",
                          "_toy_switches", "_toy_plate_order", "_toy_plate_progress",
                          "_toy_lit", "_toy_npc_pos", "_natural_mechanism",
                          "_toy_targets", "_pending_circuit_board",
                          "_mind_drain_tick", "_lucid_drain_tick", "_cotton_tick",
                          "_natural_circuit_count",
                          "debug_full_vision", "debug_mind_invincible",
                          "debug_lucidity_invincible", "debug_imagination_infinite",
                          "_deferred_liquid_sources", "_deferred_gas_sources",
                          "enemy_bombs", "last_projectile", "projectile_seq",
                          # 异象意图切换提示是瞬时 UI 事实，不入档。
                          "anomaly_intents", "_anomaly_intent_before",
                          # §12 D 残余：激活短光队列是纯演出（<1s 就衰完），
                          # 与 last_sound_pulse 同口径——读档后不该被复活。
                          "light_flashes", "_light_flash_seq",
                          # 命中表现事件（2026-10-24 手感方案 §3.1）：读档/新局
                          # 不补播旧命中，队列与序号都必须留在运行期。
                          "presentation_hits", "hit_event_seq",
                          "_combat_fx_events", "_combat_fx_seq", "_cast_fx_capture",
                          # 构筑桥接组件的运行期瞬态（2026-10-08）：印记/每层一次
                          # 记账/冷却都是本层战斗内状态，跨档无意义（下潜即失效）。
                          "refract_marks", "bridge_once",
                          "wet_conduct_ready", "echo_armed_depth",
                          "blank_pass_depth", "blank_pass_pending",
                          # 携带意象联想盘（2026-10-09）：盘面走 data["board"]
                          # 的结构化编码；EquipmentView 是派生缓存，可重建。
                          "_equipment_view", "_legacy_slots",
                          "_equipment_claim_epoch", "_equipment_claimed_channels",
                          "_equipment_derived_depth", "_equipment_attacker", "_equipment_root_frame",
                          # 梦中梦支线·余烬廊桥与退潮厅（2026-10-08）：已关门位面集
                          # （set 不可 JSON，改写入 data["realm"]）、待并入的散落奖励。
                          "closed_realms", "_pending_realm_items",
          # 玩家地图知识（2026-10-18）：tuple 键 + 快照对象不能直接进 JSON，
          # 走 data["terrain_memory"] 的紧凑列表编码。
          "terrain_memory",
          # 资源结算事实/实际行动耗时（docs §10 第三批）：有界内存记录，
          # 不写存档；读档后重新开始记录。
                          "_recent_settlements", "_recent_action_times",
                          # §12 F：灯具坐标索引是运行期派生（按 cells 对象重建），
                          # 里面还带 id()，不入档。
                          "_light_fixture_index",
                          "pending_event_id", "pending_event_uid", "pending_npc_id")  # 运行期缓存/对话框瞬态不入档
        data = {
            key: value
            for key, value in state.__dict__.items()
            if key not in runtime_caches
            and key not in ("cells", "layer_states", "player", "enemies", "world_items",
                            "events", "inventory", "catalog", "developed_cells",
                            "slick_cells", "resolved_kinds", "hover_target", "board",
                            "world_ledger")
        }
        # 世界记录（§12.2）独立于层快照存：远层重建后仍要知道谁在这儿、
        # 设施还剩几次、哪几格被永久改过。
        data["world_ledger"] = state.world_ledger.to_dict()
        data["board"] = state.board.to_dict()
        data["player"] = asdict(state.player)
        data["enemies"] = [asdict(enemy) for enemy in state.enemies]
        data["world_items"] = [asdict(item) for item in state.world_items]
        data["events"] = [asdict(event) for event in state.events]
        data["inventory"] = [asdict(item) for item in state.inventory]
        data["catalog"] = state.catalog
        data["hover_target"] = list(state.hover_target) if state.hover_target else None
        data["layer_states"] = {
            key: SaveManager._encode_layer(snapshot, tables, cache)
            for key, snapshot in state.layer_states.items()
        }
        data["cells"] = SaveManager._encode_cells(state.cells, tables, cache)
        # set 无法直接进 JSON：按深度键的集合字段编码为有序列表。
        for key in ("developed_cells", "slick_cells"):
            data[key] = {
                depth: [list(position) for position in sorted(value)]
                for depth, value in (state.__dict__.get(key) or {}).items()
            }
        # 玩家地图知识（docs 第 1 节）：层键 -> 地形快照列表；旧档缺省即空记忆。
        data["terrain_memory"] = encode_terrain_memory(state)
        data["resolved_kinds"] = sorted(state.resolved_kinds)
        # 玩家点燃册（§4.4 归因）：层键 → 格坐标集；火熄灭在运行时除名，
        # 这里只做快照。旧档缺省空册。
        data["_ignition_owner"] = {
            key: [list(position) for position in sorted(value)]
            for key, value in (state.__dict__.get("_ignition_owner") or {}).items()
            if value
        }
        # 逻辑固体（内容扩展包 v1）：当前层的陷阱场景与阀储备。
        data["trap_scenarios"] = {k: str(v) for k, v in state.trap_scenarios.items()}
        data["logic_fences"] = {f"{x},{y}": life for (x,y), life in state._mind_fences.items()}
        # 梦中梦（2026-09-21）。
        data["realm"] = {
            "realm_id": state.realm_id, "realm_depth": state.realm_depth,
            "entry_depth": state.entry_depth, "entry_x": state.entry_x, "entry_y": state.entry_y,
            "strong_kills": state.strong_kills, "key_dropped": state.key_dropped,
            "realm_puzzle_solved": {k: True for k, v in state.realm_puzzle_solved.items() if v},
            # 梦中梦支线（2026-10-08）：本局已关闭、不再开启的位面（set → 有序列表）。
            "closed_realms": sorted(state.closed_realms),
        }
        data["valve_stored"] = {k: list(v) for k, v in state.valve_stored.items()}
        # 消息日志是**已格式化字符串**（docs §19 E）：它不随语言重译，因此记下
        # 写入时的语言，读档时才能诚实地说明「较早的记录保留当时语言」。
        data["message_language"] = get_language()
        data["tables"] = tables
        return data


    def _decode_cell(self, item: Any, tables: dict[str, list[str]] | None = None) -> Cell:
        """格子解码：紧凑列表（新存档）或字典（旧存档迁移）。"""
        if isinstance(item, dict):
            return SaveManager._decode_cell_legacy(item)
        tables = tables or SaveManager._make_tables()
        if _kernel_enabled("save"):
            return _kernel_decode_compact_cell(item, tables)
        return self._decode_compact_cell(item, tables)

    @staticmethod
    def _decode_compact_cell(item: list, tables: dict[str, list[str]]) -> Cell:
        """紧凑列表格（本版本写出的存档；第 16 位植物是后加字段，旧档缺省为 0）。

        ⚠️ 这是每份存档最大的一笔逐格成本（1.8MB 档约 10800 格）。为了不在热路径
        上反复做字符串表查询/方法分派，_lookup 的「越界取默认值」在这里内联成
        局部变量，Cell 也按 dataclass 字段顺序位置传参——**语义必须与
        scripts/probe_save_load_latency_261026.py 基线时的旧实现逐字节等价**：
        越界下标默认值、液/气种类合法性回退、dreamcrystal cover 存气体、
        solid+height>1 清空液气、未知墙体补定义表的硬度/高度/厚度/完整度全部保留。
        不要改成复用 Cell 实例：material_clocks/creation/phase_stock 会被原地修改。
        """
        length = len(item)
        (
            floor_idx, solid_int, liquid, gas, hardness, thickness,
            integrity, cover, flame, variant_idx, wall_idx, height,
            elevation, liquid_idx, gas_idx,
        ) = item[:15]
        plant = int(item[15]) if length > 15 else 0
        wire = int(item[16]) if length > 16 else 0
        solid = bool(solid_int)
        if solid and height > 1:
            liquid = 0
            gas = 0
        # ---- _lookup(tables, key, index[, default]) 的内联等价实现 ----
        liquids = tables.get("liquids") or ()
        raw_liquid_kind = liquids[liquid_idx] if 0 <= liquid_idx < len(liquids) else ""
        gas_table = tables.get("gases") or ()
        raw_gas_kind = gas_table[gas_idx] if 0 <= gas_idx < len(gas_table) else ""
        liquid_kind = (raw_liquid_kind if liquid and raw_liquid_kind in LIQUID_DEFINITIONS
                       else DEFAULT_LIQUID if liquid else "")
        gas_kind = (raw_gas_kind if gas and raw_gas_kind in GAS_DEFINITIONS
                    else DEFAULT_GAS if gas else "")
        walls = tables.get("walls") or ()
        raw_wall_kind = walls[wall_idx] if 0 <= wall_idx < len(walls) else ""
        known_wall = raw_wall_kind in WALL_DEFINITIONS
        wall_kind = raw_wall_kind if known_wall else DEFAULT_WALL if solid else ""
        if solid and cover > 0 and wall_def(wall_kind).break_effect == 'dreamcrystal':
            if raw_gas_kind in GAS_DEFINITIONS:
                gas_kind = raw_gas_kind  # cover stores gas; free gas may legitimately be zero.
        variants = tables.get("variants") or ()
        aggregate_variant = (variants[variant_idx] if 0 <= variant_idx < len(variants)
                             else "普通聚合物")
        # 位置传参＝Cell 的字段声明顺序（core/entities.py::Cell）：
        # wire, floor, solid, liquid, gas, hardness, thickness, integrity, cover,
        # flame, aggregate_variant, wall_kind, height, elevation, liquid_kind,
        # gas_kind, plant, plant_fuel, floor_fuel, item_burn_progress, creation,
        # material_clocks, light_radius, light_on, doorway, phase_stock。
        # 关键字传参在 10800 格上约多 7-8ms（每次 load 都付）。
        cell = Cell(
            max(0, wire),
            Material.SOLID_AGGREGATE if solid else Material.PLAIN_AGGREGATE,
            solid, liquid, gas, hardness, thickness, integrity, cover, flame,
            aggregate_variant, wall_kind, height, elevation, liquid_kind, gas_kind,
            max(0, plant) if not solid else 0,
            max(0, int(item[17])) if length > 17 else 0,
            max(0, int(item[18])) if length > 18 else 0,
            max(0, int(item[19])) if length > 19 else 0,
            dict(item[20]) if length > 20 and isinstance(item[20], dict) else {},
            dict(item[21]) if length > 21 and isinstance(item[21], dict) else {},
            max(0, int(item[22])) if length > 22 else 0,
            bool(item[23]) if length > 23 else True,
            bool(item[24]) if length > 24 else wall_kind in DOOR_KINDS,
            dict(item[25]) if length > 25 and isinstance(item[25], dict) else {},
            dict(item[26]) if length > 26 and isinstance(item[26], dict) else {},
        )
        if solid and not known_wall:
            definition = wall_def(wall_kind)
            cell.hardness = definition.hardness
            cell.height = definition.height
            cell.thickness = definition.thickness
            cell.integrity = definition.integrity
        return cell

    @staticmethod
    def _decode_cells(rows: list, tables: dict[str, list[str]]) -> list[list[Cell]]:
        """批量解码一层的格子：紧凑列表格直连快路径，旧字典格仍走迁移解码。"""
        legacy = SaveManager._decode_cell_legacy
        # CY-1：编译过的内核一次接管整层；未编译/关闭时用下方纯 Python 实现。
        if _kernel_enabled("save"):
            return _kernel_decode_cells(rows, tables, legacy)
        compact = SaveManager._decode_compact_cell
        return [
            [legacy(item) if isinstance(item, dict) else compact(item, tables)
             for item in row]
            for row in rows
        ]

    @staticmethod
    def _decode_cell_legacy(item: dict[str, Any]) -> Cell:
        solid = bool(item.get("solid", False))
        liquid = max(0, min(100, int(item.get("liquid", 0))))
        gas = max(0, min(100, int(item.get("gas", 0))))
        if solid and int(item.get("height", 0) or 0) > 1:
            # 中高墙不与液体/气体共存；低墙（高度 1）允许共存越过。
            liquid = 0
            gas = 0
        liquid_kind = item.get("liquid_kind", "")
        gas_kind = item.get("gas_kind", "")
        liquid_kind = liquid_kind if liquid and liquid_kind in LIQUID_DEFINITIONS else DEFAULT_LIQUID if liquid else ""
        gas_kind = gas_kind if gas and gas_kind in GAS_DEFINITIONS else DEFAULT_GAS if gas else ""
        raw_wall_kind = item.get("wall_kind", "")
        known_wall = raw_wall_kind in WALL_DEFINITIONS
        wall_kind = raw_wall_kind if known_wall else DEFAULT_WALL if solid else ""
        if solid and item.get('cover',0) > 0 and wall_def(wall_kind).break_effect == 'dreamcrystal':
            if item.get('gas_kind') in GAS_DEFINITIONS:
                gas_kind = item['gas_kind']
        cell = Cell(
            floor=Material.SOLID_AGGREGATE if solid else Material.PLAIN_AGGREGATE,
            solid=solid,
            liquid=liquid,
            gas=gas,
            hardness=item.get("hardness", 2),
            thickness=item.get("thickness", 1),
            integrity=item.get("integrity", 100),
            cover=item.get("cover", 0),
            flame=item.get("flame", 0),
            aggregate_variant=item.get("aggregate_variant", "普通聚合物"),
            wall_kind=wall_kind,
            height=item.get("height", 0),
            elevation=item.get("elevation", 0),
            liquid_kind=liquid_kind,
            gas_kind=gas_kind,
            plant=max(0, int(item.get("plant", 0))) if not solid else 0,
            wire=max(0, int(item.get("wire", 0))),
            plant_fuel=max(0, int(item.get("plant_fuel", 0))),
            floor_fuel=max(0, int(item.get("floor_fuel", 0))),
            item_burn_progress=max(0, int(item.get("item_burn_progress", 0))),
            creation=dict(item.get('creation') or {}),
            material_clocks=dict(item.get('material_clocks') or {}),
            light_radius=max(0, int(item.get('light_radius', 0))),
            doorway=bool(item.get('doorway', wall_kind in DOOR_KINDS)),
            light_on=bool(item.get('light_on', True)),
            phase_stock=dict(item.get('phase_stock') or {}),
            plant_state=dict(item.get('plant_state') or {}),
        )
        if solid and not known_wall:
            definition = wall_def(wall_kind)
            cell.hardness = definition.hardness
            cell.height = definition.height
            cell.thickness = definition.thickness
            cell.integrity = definition.integrity
        return cell

    @staticmethod
    def _decode_entity(payload: dict[str, Any]) -> Entity:
        data = dict(payload)
        data['biological_tags'] = tuple(data.get('biological_tags') or ())
        route = data.get("route") or []
        data["route"] = [tuple(cell) if isinstance(cell, (list, tuple)) else cell for cell in route]
        plan = data.get("path_plan") or []
        data["path_plan"] = [tuple(cell) if isinstance(cell, (list, tuple)) else cell for cell in plan]
        # §22 B：调查任务随档保存；旧档缺省为空。x/y 统一回整数，
        # 已尝试／不可达状态原样保留，读档不重抽线索。
        tasks = []
        for task in data.get("investigation_tasks") or ():
            if not isinstance(task, dict):
                continue
            try:
                task = dict(task)
                task["x"] = int(task.get("x", -1))
                task["y"] = int(task.get("y", -1))
                task["time"] = int(task.get("time", 0))
                task["expires"] = int(task.get("expires", 0))
            except (TypeError, ValueError):
                continue
            task["source"] = str(task.get("source", "hearing"))
            task["category"] = str(task.get("category", "generic"))
            task["tried"] = bool(task.get("tried", False))
            task["unreachable"] = bool(task.get("unreachable", False))
            tasks.append(task)
        data["investigation_tasks"] = tasks
        # 旧存档没有征兆「层」记账：缺省为空（有层数的征兆会回落到定义里的初值）。
        data["portent_stacks"] = {
            str(key): int(value) for key, value in (data.get("portent_stacks") or {}).items()
        }
        # 旧存档没有材料「附着」记账：缺省为空（附着层 2026-10-07 才引入）。
        data["portent_attach"] = {
            str(key): float(value) for key, value in (data.get("portent_attach") or {}).items()
        }
        # §17：单轮硬边界与结束后的隐藏保护；旧档缺省为空。
        data["portent_deadlines"] = {
            str(key): int(value) for key, value in (data.get("portent_deadlines") or {}).items()
        }
        data["portent_protection"] = {
            str(key): int(value) for key, value in (data.get("portent_protection") or {}).items()
        }
        # 异象主动技能（2026-10-08）：active_skill_state 缺省/类型恢复；
        # 旧 skill_clocks 的 s0/s1 下标按旧定义顺序尽量迁移为稳定技能 ID。
        raw_state = data.get("active_skill_state")
        skill_state: dict = dict(raw_state) if isinstance(raw_state, dict) else {}
        pending = skill_state.get("pending")
        if not isinstance(pending, dict) or not isinstance(pending.get("skill_id"), str):
            skill_state.pop("pending", None)
        data["active_skill_state"] = skill_state
        data["skill_clocks"], legacy_migrated = SaveManager._migrate_skill_clocks(
            data.get("skill_clocks") or {}, data.get("catalog_id", ""), skill_state,
        )
        if legacy_migrated:
            # 旧范围蓄力（aoe_charge 倒计时）在新机制里改走 pending：直接取消。
            data["aoe_charge"] = 0.0
        return Entity(**data)

    @staticmethod
    def _migrate_skill_clocks(clocks: dict, catalog_id: str, skill_state: dict) -> tuple[dict, bool]:
        """旧主动技能迁移：s0/s1 下标 → 稳定技能 ID；映射不清给全 CD 并取消旧蓄力。

        旧引擎把计时存在 ``skill_clocks["s{下标}"]``（按 anomalies.py 定义表
        "skills" 顺序）；新引擎用稳定技能 ID。读档时按下标顺序映射到数据层
        绑定的稳定 ID：s{i} → bindings[i]。映射不到的（下标越界/无绑定）不
        迁移；只要出现过 s* 键且该异象有主动绑定，就给全部绑定技能满 CD 并
        取消旧的范围蓄力（aoe_charge），避免旧蓄力在新机制里瞬爆。
        """
        migrated: dict[str, float] = {}
        legacy_keys = [key for key in clocks if isinstance(key, str) and key.startswith("s") and key[1:].isdigit()]
        stable = {
            key: float(value)
            for key, value in clocks.items()
            if isinstance(key, str) and key in SKILL_DEFINITIONS
        }
        migrated.update(stable)
        if not legacy_keys:
            return migrated, False
        from .data.anomaly_skills import SKILL_DEFINITIONS as _SKILLS, bindings_for

        bindings = bindings_for(catalog_id)
        mapped_all = True
        for key in sorted(legacy_keys, key=lambda k: int(k[1:])):
            index = int(key[1:])
            if index < len(bindings):
                skill_id = bindings[index].skill_id
                if skill_id not in migrated:
                    migrated[skill_id] = min(float(clocks[key]), float(_SKILLS[skill_id].cooldown_rounds))
            else:
                mapped_all = False
        if not mapped_all:
            # 映射不清（下标越界/无绑定）：全部绑定技能给满 CD，并取消旧蓄力状态。
            for binding in bindings:
                migrated[binding.skill_id] = max(
                    migrated.get(binding.skill_id, 0.0),
                    float(_SKILLS[binding.skill_id].cooldown_rounds),
                )
            skill_state.pop("recover_until", None)
        return migrated, bool(legacy_keys)

    def _decode(self, data: dict[str, Any]) -> GameState:
        tables = data.get("tables") or SaveManager._make_tables()
        cells = SaveManager._decode_cells(data["cells"], tables)
        player = self._decode_entity(data["player"])
        enemies = [self._decode_entity(enemy) for enemy in data.get("enemies", [])]
        def decode_item(item: dict[str, Any]) -> Item:
            # 名称以定义表为准：物品名从不在运行期被改写（始终由定义快照而来），
            # 因此读档时刷新可让老存档里带 emoji 尾缀、或措辞更新过的旧名字
            # 跟上当前定义，玩家不必为了一个名字开新档。图标同理走 Item.icon
            # 属性实时读取，不占存档字段。
            definition = ITEM_DEFINITIONS.get(str(item.get("definition_id", "")))
            decoded = Item(
                definition_id=item["definition_id"], instance_id=item["instance_id"],
                name=definition["name"] if definition else item["name"],
                category=item["category"], slot=item.get("slot"), description=item.get("description", ""),
                color=item.get("color", "bright_white"), quantity=item.get("quantity", 1),
                max_stack=item.get("max_stack", 1), effect=item.get("effect"), power=item.get("power", 0),
                power_secondary=item.get("power_secondary", 0),
                penetration=item.get("penetration", 0), push=item.get("push", 0),
                explosion_radius=item.get("explosion_radius", 0),
                projectile_template=item.get("projectile_template", "直线弹体"),
                rarity=item.get("rarity", ""),
                contents=dict(item.get("contents", {}) or {}),
                gas_decay_age={str(kind): max(0,int(age))
                               for kind,age in (item.get('gas_decay_age') or {}).items()
                               if kind in GAS_DEFINITIONS and kind in (item.get('contents') or {})},
                magazine=(None if item.get('magazine') is None
                          else max(0, int(item.get('magazine') or 0))),
                magazine_capacity=max(0, int(item.get('magazine_capacity') or 0)),
                reload_steps=max(0, int(item.get('reload_steps') or 0)),
                reload_paid=bool(item.get('reload_paid', False)),
                magazine_rule=max(0, int(item.get('magazine_rule') or 0)),
                # 分次部署余量；旧档没有这一项 → 0（照旧一次投完）。
                charges=max(0, int(item.get('charges') or 0)),
            )
            from .core.firing_sources import ensure_magazine
            ensure_magazine(decoded)
            return decoded

        def decode_world_item(entry: dict[str, Any]) -> WorldItem:
            return WorldItem(item=decode_item(entry["item"]), x=entry["x"], y=entry["y"],
                             surface=str(entry.get("surface", "") or ""))

        def decode_layer(entry: dict[str, Any]) -> LayerSnapshot:
            from .core.realm_surface import normalize_bg_zones
            layer_cells = SaveManager._decode_cells(entry["cells"], tables)
            layer_items = [decode_world_item(item) for item in entry.get("world_items", [])]
            for item in layer_items:
                cell = (layer_cells[item.y][item.x]
                        if layer_cells and 0 <= item.y < len(layer_cells)
                        and 0 <= item.x < len(layer_cells[0]) else None)
                item.sync_surface(cell)
            return LayerSnapshot(
                depth=entry["depth"], seed=entry["seed"], cells=layer_cells,
                enemies=[self._decode_entity(enemy) for enemy in entry.get("enemies", [])],
                world_items=layer_items,
                events=[WorldEvent(**event) for event in entry.get("events", [])],
                player_x=entry["player_x"], player_y=entry["player_y"],
                dissolution=entry.get("dissolution", 0), theme=entry.get("theme", ""),
                map_form=normalize_map_form(entry.get("map_form", "整齐的房间")),
                width=entry.get("width", 0), height=entry.get("height", 0),
                logic_scenarios={k: str(v) for k, v in entry.get("logic_scenarios", {}).items()},
                logic_valves={k: tuple(v) for k, v in entry.get("logic_valves", {}).items()},
                logic_boards=list(entry.get("logic_boards", [])),
                logic_fences=dict(entry.get("logic_fences", {})),
                enemy_skill_fields=list(entry.get("enemy_skill_fields", [])),
                material_time=int(entry.get("material_time", 0)),
                realm_features=dict(entry.get("realm_features", {}) or {}),
                realm_bg_zones=normalize_bg_zones(entry.get("realm_bg_zones", []),
                                                len(layer_cells[0]) if layer_cells else 0,
                                                len(layer_cells)),
            )

        equipped = dict(data.get("equipped", {}))
        if "依附物" in equipped:  # 旧存档单依附槽迁移到第一个标准槽
            equipped.setdefault("依附物·一", equipped.pop("依附物"))
        decoded_inventory = [decode_item(item) for item in data.get("inventory", [])]
        board, board_note = SaveManager._decode_board(data, equipped, decoded_inventory)
        loaded_messages = list(data.get("messages", []))
        if board_note:
            loaded_messages.append(board_note)
        # docs §19 E：旧记录只有已格式化字符串，允许保留原文，但必须说明兼容限制。
        # 只在两侧语言都已知且确实不同时追加一行，缺字段的旧档不猜。
        saved_language = str(data.get("message_language") or "")
        current_language = get_language()
        if (saved_language and current_language and saved_language != current_language
                and loaded_messages):
            loaded_messages.append(
                tr("较早的记录保留当时的语言，不随当前语言重译。"))
        merged_catalog = self.merge_catalogs(data.get("catalog", {}), self.load_catalog())
        state = GameState(
            width=data["width"], height=data["height"], seed=data["seed"], cells=cells, player=player,
            base_width=data.get("base_width", data["width"]), base_height=data.get("base_height", data["height"]),
            enemies=enemies, time=data["time"], depth=data["depth"], dissolution=data["dissolution"],
            mind=data["mind"], lucidity=data["lucidity"], imagination=data["imagination"],
            max_mind=data["max_mind"], max_lucidity=data["max_lucidity"], max_imagination=data["max_imagination"],
            messages=loaded_messages, next_enemy_id=data.get("next_enemy_id", len(enemies) + 1),
            fire_unlocked=data.get("fire_unlocked", False),
            fire_from_board=data.get("fire_from_board", False),
            projectile_charges=data.get("projectile_charges", 0),
            firing_sources_version=int(data.get("firing_sources_version", 0) or 0),
            legacy_basic_magazine=(None if data.get("legacy_basic_magazine") is None
                                   else max(0, int(data.get("legacy_basic_magazine") or 0))),
            legacy_basic_reload_steps=max(0, int(data.get("legacy_basic_reload_steps") or 0)),
            legacy_basic_reload_paid=bool(data.get("legacy_basic_reload_paid", False)),
            world_items=[decode_world_item(item) for item in data.get("world_items", [])],
            events=[WorldEvent(**event) for event in data.get("events", [])],
            inventory=decoded_inventory,
            board=board,
            memory_fragments=data.get("memory_fragments", []),
            insights=data.get("insights", []),
            pending_insight=data.get("pending_insight"),
            pending_memory=data.get("pending_memory"),
            catalog=merged_catalog,
            layer_states={key: decode_layer(value) for key, value in data.get("layer_states", {}).items()},
            next_item_id=data.get("next_item_id", 1),
            victory=data.get("victory", False),
            run_over=data.get("run_over", False),
            theme=data.get("theme", ""),
            map_form=normalize_map_form(data.get("map_form", "整齐的房间")),
            layer_modifier=str(data.get("layer_modifier", "") or ""),
            layer_drop_counts=data.get("layer_drop_counts", {}),
            overwrite_count=data.get("overwrite_count", 0),
            sight_radius=data.get("sight_radius", 8),
            developed_cells=self._decode_position_map(data.get("developed_cells")),
            # 玩家地图知识（2026-10-18 docs 第 1 节）：旧档缺字段 → 空记忆 +
            # 增强关闭 + 规则版本 0（该局按旧口径继续，直到新局才写 1）。
            terrain_memory=decode_terrain_memory(data.get("terrain_memory")),
            hazard_memory=decode_hazard_memory(data.get("hazard_memory")),
            terrain_known=bool(data.get("terrain_known", False)),
            map_knowledge_version=int(data.get("map_knowledge_version", 0) or 0),
            map_memory_enabled=bool(data.get("map_memory_enabled", False)),
            _ignition_owner={
                str(key): {(int(x), int(y)) for x, y in value}
                for key, value in (data.get("_ignition_owner") or {}).items()
            },
            trap_scenarios={k: str(v) for k, v in data.get("trap_scenarios", {}).items()},
            valve_stored={k: tuple(v) for k, v in data.get("valve_stored", {}).items()},
            realm_id=str(data.get("realm", {}).get("realm_id", "") or ""),
            realm_depth=int(data.get("realm", {}).get("realm_depth", 0) or 0),
            entry_depth=int(data.get("realm", {}).get("entry_depth", 1) or 1),
            entry_x=int(data.get("realm", {}).get("entry_x", 0) or 0),
            entry_y=int(data.get("realm", {}).get("entry_y", 0) or 0),
            strong_kills=int(data.get("realm", {}).get("strong_kills", 0) or 0),
            key_dropped=bool(data.get("realm", {}).get("key_dropped", False)),
            realm_puzzle_solved={int(k): True for k, v in data.get("realm", {}).get("realm_puzzle_solved", {}).items() if v},
            # 梦中梦支线（2026-10-08）：已关门位面 + 引火人/潮汐之门的确定性安放层号。
            closed_realms=set(data.get("realm", {}).get("closed_realms", ()) or ()),
            ember_npc_exists=bool(data.get("ember_npc_exists", False)),
            ember_npc_layer=int(data.get("ember_npc_layer", 0) or 0),
            realm_gate_layer=int(data.get("realm_gate_layer", 0) or 0),
            ebbing_contract_rounds=int(data.get("ebbing_contract_rounds", 0) or 0),
            ebbing_past_threshold=bool(data.get("ebbing_past_threshold", False)),
            ebbing_elapsed=int(data.get("ebbing_elapsed", 6 + int(data.get("ebbing_contract_rounds", 0)) * 6
                                        if data.get("ebbing_past_threshold") else 0)),
            ebbing_warning_ring=int(data.get("ebbing_warning_ring", -1)),
            realm_challenges=dict(data.get("realm_challenges", {})),
            slick_cells=self._decode_position_map(data.get("slick_cells")),
            tear_drinks={str(key): int(value) for key, value in (data.get("tear_drinks") or {}).items()},
            abilities=list(data.get("abilities", [])),
            ability_cooldowns={str(key): int(value) for key, value in (data.get("ability_cooldowns") or {}).items()},
            stasis_turns=max(0,int(data.get('stasis_turns',0) or 0)),
            vanish_turns=max(0,int(data.get('vanish_turns',0) or 0)),
            resonance_turns=max(0,int(data.get('resonance_turns',0) or 0)),
            library_bookmark=dict(data.get('library_bookmark') or {}),
            ability_turns={str(key): int(value) for key, value in (data.get("ability_turns") or {}).items()},
            resolved_kinds=set(data.get("resolved_kinds", [])),
            developed_total=int(data.get("developed_total", 0)),
            viscous_debt=float(data.get("viscous_debt", 0.0)),
            round_debt=float(data.get("round_debt", 0.0)),
            _action_count=int(data.get("_action_count", 0)),
            steal_cap=int(data.get("steal_cap", 0)),
            action_counts={str(key): int(value) for key, value in (data.get("action_counts") or {}).items()},
            free_liquid_moves=int(data.get("free_liquid_moves", 0)),
            free_actions=int(data.get("free_actions", 0)),
            # 底片的免费行动窗口；旧档没有 → 0（无窗口，行为同旧版）。
            free_action_until=int(data.get("free_action_until", 0) or 0),
            free_move_pending=int(data.get("free_move_pending", 0)),
            parry_charges=int(data.get("parry_charges", 0)),
            # 旧档没有这一项：0 = 不设期限，只按次数消耗（与旧版一致）。
            parry_until=int(data.get("parry_until", 0) or 0),
            overclock_turns=int(data.get("overclock_turns", 0)),
            # 延时声源（蜂鸣诱饵）的待响队列；旧档没有 → 空表（不再补响）。
            delayed_sounds=[dict(row) for row in (data.get("delayed_sounds") or [])],
            # 上一处实际诱引落点（扩展包「返场」）；旧档没有 → 空 dict（返场拒用）。
            last_lure=dict(data.get("last_lure") or {}),
            delayed_fuel=[dict(row) for row in (data.get("delayed_fuel") or [])],
            drug_debts=[dict(row) for row in data.get("drug_debts", [])],
            drug_debt_version=int(data.get("drug_debt_version", 0)),
            item_grant_counts={str(key): max(0, int(value))
                               for key, value in (data.get("item_grant_counts") or {}).items()},
            modem_boost_until=float(data.get("modem_boost_until", 0)),
            modem_recovery_until=float(data.get("modem_recovery_until", 0)),
            light_turns=int(data.get("light_turns", 0)),
            portent_ward_turns=int(data.get("portent_ward_turns", 0)),
            portent_ward_id=str(data.get("portent_ward_id", "") or ""),
            turns_since_descend=int(data.get("turns_since_descend", 0)),
            hang_item_id=data.get("hang_item_id"),
            # 联想盘反馈的玩家级状态：读档不清零（§7.3——冷却与缓冲跨存档保留）。
            board_cooldowns={str(key): int(value)
                             for key, value in (data.get("board_cooldowns") or {}).items()},
            equipment_damage_credit={
                "weapon_damage": max(0, min(999999, int(
                    (data.get("equipment_damage_credit") or {}).get("weapon_damage", 0))))
            } if data.get("equipment_damage_credit") else {},
            equipment_event_budget=dict(data.get("equipment_event_budget") or {}),
            equipment_marks={str(key): dict(value) for key, value in
                             (data.get("equipment_marks") or {}).items() if isinstance(value, dict)},
            board_buffer=dict(data.get("board_buffer") or {}),
            board_pending=[dict(entry) for entry in (data.get("board_pending") or [])
                           if int((data.get('board') or {}).get('schema_version', 1)) >= 2
                           and entry.get('continuation') and (entry.get('deferred') or [None, None, None])[-1] == 'read'],
            board_feedback_round=int(data.get("board_feedback_round", 0)),
            board_previous_cell=(tuple(data["board_previous_cell"])
                                 if data.get("board_previous_cell") else None),
            board_touch_cell=(tuple(data["board_touch_cell"])
                              if data.get("board_touch_cell") else None),
            board_touch_material=str(data.get("board_touch_material", "") or ""),
            # NPC 一次性交易记账：稳定 actor_uid → 已完成的稳定 option_id 列表。
            npc_traded_options={
                str(key): [str(value) for value in (entries or [])]
                for key, entries in (data.get("npc_traded_options") or {}).items()
            },
            npc_free_claims={str(key): list(dict.fromkeys(str(value) for value in entries))
                             for key, entries in (data.get('npc_free_claims') or {}).items()},
            hover_target=tuple(data["hover_target"]) if data.get("hover_target") else None,
            # 旧存档没有消散标记：从载入回合起算，避免一次性补扣数十点气量。
            gas_decay_mark=int(data.get("gas_decay_mark", data.get("time", 0))),
            # 液体挥发标记同理：旧存档从载入回合起算。
            liquid_decay_mark=int(data.get("liquid_decay_mark", data.get("time", 0))),
            # 地板吸水标记同上：旧存档从载入回合起算，避免载入瞬间被海绵吸掉一截。
            liquid_absorb_mark=int(
                data.get("liquid_absorb_mark", data.get("liquid_decay_mark", data.get("time", 0)))
            ),
            # 异象主动技能（2026-10-08）：动作序号与效果场随档恢复（旧档缺省）。
            action_seq=int(data.get("action_seq", 0)),
            enemy_skill_fields=list(data.get("enemy_skill_fields", [])),
            # 开局选项（2026-10-09）：旧档缺省 = 空选择 + 中性修正（行为不变）。
            run_options=dict(data.get("run_options", {}) or {}),
            run_mods=dict(data.get("run_mods", {}) or NEUTRAL_RUN_MODS),
            difficulty_revision=max(0, int(data.get("difficulty_revision", 0) or 0)),
            run_start_choices=dict(data.get("run_start_choices", {}) or {}),
            imagination_regen_credit=float(data.get('imagination_regen_credit', 0.0)),
            dream_type_choice=dict(data.get('dream_type_choice', {}) or {}),
            dream_type_mods=dict(data.get('dream_type_mods', {}) or {}),
            identity_state=dict(data.get('identity_state', {}) or {}),
            # 梦中梦·千禧园（2026-10-10）：底色带与拨号状态随档恢复（旧档缺省）。
            realm_bg_zones=list(data.get("realm_bg_zones", []) or []),
            realm_entry_state=dict(data.get("realm_entry_state", {}) or {}),
            realm_features=dict(data.get("realm_features", {}) or {}),
            dial_in=dict(data.get("dial_in", {}) or {}),
            # 篡改系统（规格 §6、§8.2）：混乱度、衰减余量、付费行动序号、改文序号
            # 与改文记录都随档恢复；旧档缺省 = 未改过文、混乱度 0。
            chaos=int(data.get("chaos", 0) or 0),
            chaos_decay_credit=float(data.get("chaos_decay_credit", 0.0) or 0.0),
            paid_action_seq=int(data.get("paid_action_seq", 0) or 0),
            tamper_sequence=max(int(data.get("tamper_sequence", 0) or 0),
                                int(data.get("world_tamper_sequence", 0) or 0)),
            system_roles_version=int(data.get('system_roles_version', 0) or 0),
            environment_rework_version=int(data.get('environment_rework_version', 0) or 0),
            terrain_scale_version=int(data.get('terrain_scale_version', 0) or 0),
            memory_effect_awards=list(data.get('memory_effect_awards', data.get('memory_fragments', [])) or []),
            memory_buffers={str(key): str(value)
                            for key, value in (data.get('memory_buffers') or {}).items()},
            quiet_step_ready=bool(data.get('quiet_step_ready', False)),
            quiet_step_charges=max(0, int(data.get('quiet_step_charges', 0) or 0)),
            quiet_step_until=int(data.get('quiet_step_until', 0) or 0),
            echo_ward_until=int(data.get('echo_ward_until', 0) or 0),
            masked_step_until=int(data.get('masked_step_until', 0) or 0),
            sound_bearing_until=int(data.get('sound_bearing_until', 0) or 0),
            listen_until=int(data.get('listen_until', 0) or 0),
            listen_realm_until=int(data.get('listen_realm_until', 0) or 0),
            precise_sound_markers=[
                dict(entry) for entry in (data.get('precise_sound_markers') or [])
                if isinstance(entry, dict)
            ][-12:],
            sound_sightings=[
                dict(entry) for entry in (data.get('sound_sightings') or [])
                if isinstance(entry, dict)
            ][-24:],
            confirmed_sound_sources=[
                dict(entry) for entry in (data.get('confirmed_sound_sources') or [])
                if isinstance(entry, dict)
            ][-12:],
            buzzing_echo_enabled=bool(data.get('buzzing_echo_enabled', True)),
            ash_memory_settled=[str(value) for value in
                                (data.get('ash_memory_settled') or [])][-64:],
            construct_environments=list(data.get('construct_environments', []) or []),
            book_offer_sequence=max(0, int(data.get('book_offer_sequence', 0) or 0)),
            tamper_pressure=max(0, min(3, int(data.get('tamper_pressure', 0) or 0))),
            tamper_pressure_gap=max(0, min(10, int(data.get('tamper_pressure_gap', 10)))),
            tamper_pressure_idle=max(0, int(data.get('tamper_pressure_idle', 0) or 0)) % 10,
            world_tamper_deletes={str(key): max(0, int(value))
                                  for key, value in (data.get("world_tamper_deletes") or {}).items()},
            tamper_records={
                str(key): dict(value)
                for key, value in (data.get("tamper_records") or {}).items()
                if isinstance(value, dict)
            },
        )
        # Ordinary gases now persist per-cell age. Legacy active cells can use
        # the old global mark; inactive legacy maps lack a per-map global mark,
        # so initialize once at their archived time. Existing clocks always win.
        for gas_cells, mark in [(state.cells, min(state.time,state.gas_decay_mark))] + [
            (snapshot.cells,snapshot.material_time) for snapshot in state.layer_states.values()
        ]:
            for row in gas_cells:
                for cell in row:
                    definition = GAS_DEFINITIONS.get(cell.gas_kind)
                    if cell.gas > 0 and definition and not definition.dissipation_period:
                        cell.material_clocks.setdefault('decay:' + cell.gas_kind, mark)
        # ---- 2026-09-19 修复：以下字段此前只编码、不恢复——存读一次即被
        # 静默清零（深层线索 epilogue_flags、NPC 任务 quests、本局统计
        # run_stats、最深层 deepest_depth、结局 id 等全部受影响）。逐一显式
        # 恢复；旧存档缺省回落到字段默认。----
        state.deepest_depth = int(data.get("deepest_depth", 1) or 1)
        state.ending_id = str(data.get("ending_id", "") or "")
        state.epilogue_profile = str(data.get("epilogue_profile", "") or "")
        state.epilogue_flags = dict(data.get("epilogue_flags", {}) or {})
        state.run_stats = {**{"kills": 0, "ignitions": 0, "events": 0, "items_used": 0, "hits_taken": 0},
                           **dict(data.get("run_stats", {}) or {})}
        state.quests = dict(data.get("quests", {}) or {})
        # 任务接取时刻的累计量快照（§16.1）：不随档恢复的话，读档后进度会
        # 重新变成「接活前的击杀也算」，同一份任务被折算两次。
        state.quest_baselines = {
            str(quest_id): {str(name): int(value) for name, value in (baseline or {}).items()}
            for quest_id, baseline in (data.get("quest_baselines") or {}).items()
        }
        # 本局身份与世界记录：稳定 UID 的前缀必须跨存档不变，否则读档一次
        # 就等于把所有 actor_uid／fact_uid 换成新号，一次性记账全部失效。
        state.run_uid = str(data.get("run_uid", "") or "")
        state.world_ledger = WorldLedger.from_dict(data.get("world_ledger") or {})
        # 任务协议迁移（2026-10-11）：旧「计数型」任务接实例模板后，接取时刻的
        # 计数进度无从折算——旧档里这些「进行中」的任务退回未接取；判据是
        # **有没有实例记录**（在 world_ledger 解码之后跑，migration.py 的清单
        # 只认真实存在过的旧计数任务，测试用的合成 id 不受影响）。
        from .data.migration import stale_quest_ids
        from .data.quests import QUEST_DEFINITIONS as _QUEST_DEFS

        _bound = {getattr(record, "definition_id", "")
                  for record in state.world_ledger.tasks.values()}
        for quest_id in stale_quest_ids(state.quests, _bound, _QUEST_DEFS):
            state.quests.pop(quest_id, None)
            state.quest_baselines.pop(quest_id, None)
        state.world_ledger.run_uid = state.run_uid
        state.gift_claims = dict(data.get("gift_claims", {}) or {})
        from .core.npc_offers import migrate_offer_limits
        migrate_offer_limits(state, legacy_free_claims='npc_free_claims' not in data)
        state.kills_by_kind = {str(k): int(v) for k, v in (data.get("kills_by_kind") or {}).items()}
        state.facing = tuple(data.get("facing", (1, 0)) or (1, 0))
        state.layers_since_rare = int(data.get("layers_since_rare", 0))
        state.layers_since_very_rare = int(data.get("layers_since_very_rare", 0))
        state.honey_drinks = {str(k): int(v) for k, v in (data.get("honey_drinks") or {}).items()}
        state.plant_revision = int(data.get("plant_revision", 0))
        # §10.5／§10.7（2026-10-22 收口）：可听拓扑版本与听觉线索随档恢复。
        # 旧档缺省为 0／空表；读档后不再把「存档基准 ≠ 当前版本」误当成拓扑已变。
        state.topology_revision = int(data.get("topology_revision", 0) or 0)
        state.heard_sound_clues = [
            {**dict(clue),
             **({"entry": tuple(clue["entry"])}
                if isinstance(clue.get("entry"), (list, tuple)) else {})}
            for clue in (data.get("heard_sound_clues") or [])
            if isinstance(clue, dict)
        ][-24:]

        # §10.7：旧档只有 last_seen_*，没有 last_seen_time。迁移成「带有限期限的
        # 历史调查点」：以读档时刻作为锚点，最多再保留 _visual_memory_turns 回合后
        # 过期。旧口径是哨兵 −1，期限比较被整个绕过（旧目击点永不过期）。
        def _migrate_visual_memory(entities) -> None:
            for entity in entities or ():
                if (getattr(entity, "last_seen_x", -1) >= 0
                        and int(getattr(entity, "last_seen_time", -1)) < 0):
                    entity.last_seen_time = int(state.time)

        _migrate_visual_memory(state.enemies)
        for snapshot in state.layer_states.values():
            _migrate_visual_memory(snapshot.enemies)
        # 新手引导（0 层）：步骤表/旗标/玩偶重生队列；旧档缺省 = 未激活。
        state.tutorial = dict(data.get("tutorial", {}) or {})
        state.tutorial_events = dict(data.get("tutorial_events", {}) or {})
        state.doll_respawns = [tuple(entry) for entry in (data.get("doll_respawns", []) or [])]
        # 深层边界残留守卫：已离开 0 层的档若 active 残留，读档即收束。
        state.history_recorded = bool(data.get("history_recorded", False))
        state.last_harm_source = str(data.get("last_harm_source", "") or "")
        state.last_harm_time = int(data.get("last_harm_time", -9999))
        # 层间守门（2026-10-14）：realm_gate_open 是运行期瞬态不入档；读档后按
        # 「本层是否已解谜」重算。玩具的回忆另有 acknowledged 恢复路径
        # （_resume_circuit_boards），两者口径一致（talk 后同真）；
        # 两谷（图书馆/医院）的集齐手续也写入 realm_puzzle_solved，同样可重算。
        state.realm_gate_open = bool(state.realm_puzzle_solved.get(state.realm_depth))
        state._sync_task_realm_gate()
        if state.depth >= 1 and state.tutorial.get("active"):
            state.tutorial["active"] = False
        if state.depth == 0 and not state.realm_id:
            from .core.origin_course import ensure_terrain_chart, note
            ensure_terrain_chart(state)
            note(state,'course_resumed')
        if "world_items" not in data:
            state._seed_layer_contents()
        # 旧存档里没有与生俱来的洞察（双读）：载入时补齐，且不报「获得」消息。
        state._ensure_innate_insights()
        state._sync_equipment_hooks()
        state.circuit_boards = list(data.get("circuit_boards", []))
        state._restore_logic_fences(data.get("logic_fences", {}))
        state._resume_circuit_boards()
        state._resume_epilogue()
        if state.realm_id == 'ember_bridge':
            from .core.realm_challenges import ensure_ember
            ensure_ember(state)
        elif state.realm_id == 'ebbing_hall':
            from .core.realm_challenges import ensure_tide_exit
            ensure_tide_exit(state)
        # 篡改系统（规格 §8.2、§9.3）：事件实例身份只补空值——当前层与每份历史
        # 层快照按各自的层键生成（位面层键形如 R{realm_id}:{depth}，不会与主梦
        # 深度混号）；改文记录随后对齐当前内容表。读档不重放已确定的风险、不重新
        # 召唤、不补扣费：存活的异象与效果场本来就从世界状态恢复。
        from .core.tamper_views import ensure_event_uids, migrate_tamper_records

        ensure_event_uids(state.events, run_uid=state.run_uid, layer_key=state.layer_key())
        for snapshot_key, snapshot in state.layer_states.items():
            ensure_event_uids(snapshot.events, run_uid=state.run_uid, layer_key=str(snapshot_key))
        for note in migrate_tamper_records(state):
            state.messages.append(note)
        # §14.6：旧档没有落点层级，按当前支撑物补一次（台面坐标＝台面物）。
        state.normalize_world_item_surfaces()
        from .core.drug_debts import migrate_legacy as migrate_drug_debts
        migrate_drug_debts(state)
        from .core.item_access import migrate_existing as migrate_item_grants
        migrate_item_grants(state, legacy='item_grant_counts' not in data)
        return state

    @staticmethod
    def _decode_position_map(raw: Any) -> dict[str, set]:
        """把 {depth: [[x, y], ...]} 形态的存档字段还原为 {depth: {(x, y), ...}}。"""
        result: dict[str, set] = {}
        if not isinstance(raw, dict):
            return result
        for depth_key, positions in raw.items():
            cells = set()
            for position in positions or []:
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    cells.add((int(position[0]), int(position[1])))
            result[str(depth_key)] = cells
        return result


class GameSession:
    # 全量存档序列化整个地图（数千格 + 实体 + 图鉴）耗时近百毫秒——
    # 每个动作都存档会拖垮移动节拍与渲染同步。改为：任何生效动作（含 move）
    # 只标记脏，由 flush_pending_save 按“距上次存档经过的回合数”节流落盘；
    # 退出时无条件全量保存。
    SAVE_TURN_INTERVAL = 10

    def __init__(self, state: GameState, manager: SaveManager, *, persist_initial: bool = True,
                 persistence_enabled: bool = True):
        self.state = state
        self.manager = manager
        self.persistence_enabled = persistence_enabled
        self.started = time.monotonic()  # 本局开始时刻，用于界面右上角的本局时长
        self._dirty = False
        self._last_saved_turn = state.time
        self._provisional = not persist_initial
        # 后台编码与动作互斥：apply/auto_pickup 持锁，存档线程在锁内读状态快照。
        self._action_lock = threading.RLock()
        # 状态初始化同样是一次知识采样（docs 第 1 节第一批）：开新局/读档后当前
        # 视野里的地形先入账，之后由每个生效动作继续补记。
        try:
            state.record_visible_terrain()
            # 初始化采样不要留下视野缓存：直接构造的测试/脚本常先改地形再
            # 渲染，缓存若保留旧视野会出现与动作结果不一致的假象。
            from .core.vision.cache import invalidate as _invalidate_visibility
            _invalidate_visibility(state)
        except Exception:  # pragma: no cover - 极端早期挂载中字段未就绪
            pass
        if persist_initial and self.persistence_enabled:
            self.manager.save(self.state)

    def start(self) -> None:
        """Commit an explicitly entered game, never a home-screen placeholder."""
        if self._provisional and self.persistence_enabled:
            self.manager.save(self.state)
            self._provisional = False

    def apply(self, command: str, *args: Any, choice: str | None = None) -> ActionResult:
        with self._action_lock:
            return self._apply_locked(command, *args, choice=choice)

    def _apply_locked(self, command: str, *args: Any, choice: str | None = None) -> ActionResult:
        # Finalize equipment's root frame before checking death and saving history.
        practice_before = {'abilities':len(self.state.abilities),
                           'position':(self.state.player.x,self.state.player.y),
                           'items_used':self.state.run_stats.get('items_used',0)}
        if command == 'choose_npc_option' and args and self.state.depth == 0:
            from .core.content import npc_effective_options
            npc=self.state.pending_npc()
            options=npc_effective_options(self.state,npc) if npc is not None else ()
            if 0<=args[0]<len(options): practice_before['option']=options[args[0]]
        mutation_before = (self.state.action_seq, self.state.time, self.state.mind,
                           self.state.lucidity, self.state.imagination, self.state.run_over)
        result = self._dispatch_apply(command, *args, choice=choice)
        if self.state.depth == 0:
            from .core.origin_course import action_result
            action_result(self.state,command,args,result,practice_before)
        self.state._check_run_over()
        mutated = mutation_before != (self.state.action_seq, self.state.time, self.state.mind,
                                      self.state.lucidity, self.state.imagination, self.state.run_over)
        # 确认「没有变化」的盘面是可见的成功操作（changed=True），但不写盘：
        # 它没有改变任何持久状态，不该把会话标脏或触发后续保存。
        noop_board = (command == 'commit_board' and result.changed
                      and 'equipment_sentence' not in (result.data or {}))
        # 玩家地图知识（docs 第 1 节第一批）：动作生效后记录正常视野内的地形变化；
        # 纯观察/缩放/打开面板不走这里，不会推进探索或伪造进度。
        if result.changed or mutated:
            try:
                self.state.record_visible_terrain()
            except Exception:  # pragma: no cover - 结算异常不污染动作结果
                pass
        if (result.changed and not noop_board) or mutated:
            if (
                self.state.run_over
                and self.persistence_enabled
                and not self.state.history_recorded
                and (self.state.ending_id or self.state.victory)
            ):
                # 终局落账（死亡 F/E、深层结局 A-D、初啼之核胜利收局）——
                # 2026-09-19 起深层结局也在此记录并清档（旧版只记死亡局，
                # 通关局会留在存档里变成「继续」一个已结束的梦）。
                self.manager.record_finished_run(self.state)
                self.state.history_recorded = True
                self._dirty = False
                self.manager.clear_run()
            else:
                self._dirty = True
        return result

    @root_action
    def _dispatch_apply(self, command: str, *args: Any, choice: str | None = None) -> ActionResult:
        # 视野半径缓存失效（2026-10-10 性能 P0）：apply 是所有玩家动作的唯一
        # 入口——动作可能改变征兆/洞察/记忆/装备（视距输入），在开头清掉
        # SightMixin.effective_sight_radius 的回合内缓存，结算期间与之后
        # 的渲染帧都会重算一次。纯位移（调试传送）靠键里的坐标自失效。
        self.state._sight_radius_cache = None
        if command == 'commit_board' and args and self.state.board.same_layout(args[0]):
            return self.state.commit_board(args[0])
        # 弹道动画「不跨回合」第二道保险（2026-09-23）：下一次已确认动作进入
        # 处理时立即清空上一发的回放缓存——极快手玩家也看不到残留轨迹。
        previous_projectile = self.state.last_projectile
        self.state.last_projectile = None
        if self.state.run_over and command != "finish_run":
            return ActionResult(False, tr("这次入梦已经结束，不能继续行动。"))
        if command == "abandon_task":
            from .world.tasks import abandon
            result = abandon(self.state, args[0])
        elif command == 'tutorial_control':
            from .core.origin_course import control
            result=control(self.state,*args)
        elif command in ('replace_pending_insight', 'replace_pending_memory',
                         'discard_pending_insight', 'discard_pending_memory'):
            kind = 'insight' if command.endswith('insight') else 'memory'
            pending = getattr(self.state, 'pending_' + kind)
            values = self.state.insights if kind == 'insight' else self.state.memory_fragments
            if not pending or (command.startswith('replace') and (not args or args[0] not in values)):
                result = ActionResult(False, tr('待替换对象已经改变。'))
            else:
                before = (pending, tuple(values))
                method = ('replace_' + kind) if command.startswith('replace') else ('discard_pending_' + kind)
                message = getattr(self.state, method)(*args)
                changed = before != (getattr(self.state, 'pending_' + kind), tuple(values))
                result = ActionResult(changed, message)
        elif command == "move":
            result = self.state.move_player(*args, choice=choice)
        elif command == "open":
            result = self.state.open_adjacent(*args)
        elif command == 'toggle_light':
            result = self.state.toggle_light(*args)
        elif command == 'operate_gate_control':
            from .core.tactical_layouts import operate_gate_control
            result=operate_gate_control(self.state,*args)
        elif command == "wait":
            result = self.state.wait()
        elif command == "reset_puzzle":
            result = self.state.reset_realm_puzzle()
        elif command == 'identity_ability':
            result = self.state.activate_identity_ability(*args)
        elif command == 'ability':
            # 主动构想。UI 历来直接调 state.activate_ability（战斗栏按键），
            # 命令层没有名字，于是无头/脚本玩家发不出构想。这里补一条等价
            # 路由：走同一个方法、同一套记账（视野地形、脏标记、终局检查），
            # 不改任何结算规则。
            result = self.state.activate_ability(*args)
        elif command == 'ability_targeted':
            # 浏览器选点和回放复用同一个 GameSession，确保存档与行动后处理一致。
            result = self.state.activate_ability(args[0], **args[1])
        elif command == "uproot_plant":
            result = self.state.uproot_plant()
        elif command == "fire":
            result = self.state.fire(*args, choice=choice)
        elif command == "container_fill":
            result = self.state.container_fill(args[0])
        elif command == "container_pour":
            result = self.state.container_pour(args[0])
        elif command == "fire_assisted":
            # 辅助瞄准发射：弹体沿直线飞向锁定目标。
            result = self.state.fire_assisted(args[0], args[1], choice=choice)
        elif command == 'use_equipment_sentence':
            result = self.state.use_equipment_sentence(*args, choice=choice)
        elif command == 'reload_weapon_step':
            result = self.state.reload_weapon_step(args[0])
        elif command == "unlock_fire":
            # 旧回放/旧脚本的正式命令：不得改世界，也不能被误映射成射击或换弹。
            result = ActionResult(False, tr(
                '「解锁发射」命令已随统一发射源移除，旧回放与旧脚本不能继续改变世界。'),
                {'rule_incompatible': True})
        elif command == "pickup":
            result = self.state.pickup()
        elif command == "take_from":
            result = self.state.take_from(*args)
        elif command == "put_on_table":
            result = self.state.put_on_table(*args)
        elif command == "collect_items":
            # 拾取面板的 Enter 结算：按 world_items 下标挑出要拿的显化物
            # （界面对话框传的是候选清单里的位置，这里换算成对象）。
            positions = list(args)
            entries = [
                entry for index, entry in enumerate(self.state.world_items)
                if index in positions
            ]
            result = self.state.collect_items(entries)
        elif command == "interact":
            result = self.state.interact()
        elif command == "choose_npc_option":
            # 稳定意识对话：结算选中的交易/选项。
            result = self.state.choose_npc_option(args[0])
        elif command == "choose_event_option":
            # 复合事件：结算事件面板底部选中的选项。
            result = self.state.choose_event_option(args[0])
        elif command == "commit_tamper":
            # 篡改提交（规格 §5）：参数是 TamperRequest，不是坐标整数。
            from .core.tampering import commit_tamper
            result = commit_tamper(self.state, args[0])
        elif command == "throw":
            result = self.state.throw_item(*args)
        elif command == "throw_target":
            # 瞄准投掷（使用燃烧瓶/雷管进入发射界面后点选落点）。
            result = self.state.throw_target(*args)
        elif command == "deploy_target":
            # 部署类物品的单点落点（2026-10-22 A2）：夜班灯／应急蜡封。
            result = self.state.deploy_item(*args)
        elif command == "deploy_pair":
            # 部署类物品的成对落点：折叠虹吸管（源／出口）、折好的逃生通道。
            result = self.state.deploy_item_pair(*args)
        elif command == "deploy_direction":
            # 部署类物品的方向落点：拆迁用的线轴。
            result = self.state.deploy_direction(*args)
        elif command == "ignite_here":
            # 镁光火柴的「原地点燃」副动作（§14.4.1），不经过投掷瞄准。
            result = self.state.ignite_item_here(*args)
        elif command == "spray_fire":
            result = self.state.spray_fire(*args, choice=choice)
        elif command == "spray_target":
            result = self.state.spray_target(*args, choice=choice)
        elif command == "fire_once":
            result = self.state.fire_once(*args)
        elif command == "fire_once_target":
            result = self.state.fire_once_target(*args)
        elif command == "choose_mirror_insight":
            # 洞察之镜三选一：选定洞察并消耗镜子。
            result = self.state.choose_mirror_insight(*args)
        elif command == "confirm_gate_offering":
            # §8 S23 青灯入口：面板选定三件祭品后结算，把门推进「开启」。
            result = self.state.confirm_gate_offering(args[0], args[1])
        elif command == "equip":
            result = self.state.equip_item(*args)
        elif command == 'commit_board':
            result = self.state.commit_board(*args)
        elif command == "unequip":
            result = self.state.unequip_item(*args)
        elif command == "toggle_equip":
            result = self.state.toggle_equip_item(*args)
        elif command in ('equip_memory', 'unequip_memory'):
            from .core import memory_management
            result = getattr(memory_management, command)(self.state, *args)
        elif command == "use":
            result = self.state.use_item(*args)
        elif command == "drop":
            result = self.state.drop_item(*args)
        elif command == "descend":
            result = self.state.descend()
        elif command == "backtrack":
            result = self.state.backtrack()
        elif command == "finish_run":
            result = self.state.finish_run()
        else:
            self.state.last_projectile = previous_projectile
            return ActionResult(False, tr("未知命令：{command}", command=command))
        if not result.changed or any(key in (result.data or {}) for key in ("throw_aim", "fire_once_aim")):
            self.state.last_projectile = previous_projectile
        return result

    def flush_pending_save(self) -> None:
        """节流落盘：脏状态距上次存档经过的回合数达到间隔时才写盘。"""
        if not self.persistence_enabled or not self._dirty:
            return
        if self.state.time - self._last_saved_turn >= self.SAVE_TURN_INTERVAL:
            try:
                self.manager.save(self.state)
            except Exception as error:
                # 存档失败不能打死游戏线程（2026-10-27：元组键导致 OSError 终止 App）。
                self.manager._record_save_diagnostic(error, ['flush'])
                self.last_save_error = repr(error)
                return
            self._dirty = False
            self._last_saved_turn = self.state.time

    def flush_pending_save_async(self) -> None:
        """同 flush_pending_save，但把 JSON/写盘交给后台线程（真实运行时用）。"""
        if not self.persistence_enabled or not self._dirty:
            return
        if self.state.time - self._last_saved_turn >= self.SAVE_TURN_INTERVAL:
            self.manager.save_async(self.state, self._action_lock)
            self._dirty = False
            self._last_saved_turn = self.state.time

    def auto_pickup(self) -> ActionResult:
        with self._action_lock:
            return self._auto_pickup_locked()

    def _auto_pickup_locked(self) -> ActionResult:
        if self.state.has_visible_hostile():
            return ActionResult(False, tr("视野内存在失控意识，自动收纳暂停。"))
        collected = []
        result = ActionResult(False)
        # Equipment remains on the ground, including when mixed with other
        # drops. Preserve the relative order of eligible automatic pickups.
        while (any(entry.item.category != "携带意象" for entry in self.state.pickup_candidates())
               and not self.state.pending_memory):
            result = self.state.collect_here(advance_time=False, include_equipment=False)
            if not result.changed:
                break
            self._dirty = True
            collected.append(result.data.get("item"))
        if collected:
            from .core.origin_course import note
            note(self.state,'picked_up')
            return ActionResult(True, self.state.messages[-1], {"items": collected})
        return result

    def save_and_exit(self) -> None:
        if not self.persistence_enabled:
            return
        if self._provisional and not self._dirty:
            return
        self.manager.save(self.state)
        self._provisional = False
        self._dirty = False
        self._last_saved_turn = self.state.time
