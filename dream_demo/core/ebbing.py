"""退潮厅（梦中梦·高密度手关）的潮汐收缩结算（2026-10-08）。

单层位面「退潮厅」（``realm_id == "ebbing_hall"``）：外环散落留白线件、
中心岛是出口。玩家一旦离开出生门槛平台，边界的「意识边界」就按客观回合
一圈圈向内吞没；没在预算内走到中心岛出口，就会被退潮卷走。

设计口径：
- **按客观回合结算**：独立累计 elapsed，先缓冲 6，再每 6 回合吞一圈；
  与「减速行动多结算」一致，不按行动次数或主梦回合相位。
- **失败不结束游戏**：唯一的全局失败仍是 ``mind <= 0 and lucidity <= 0``
  （见 tempo.py 的 ``_check_run_over``）。退潮失败只走 ``_exit_realm("fail")``：
  最多扣 5 心智 + 本局关门，罚款不导致双归零。
- **跨门立即封路**：免费移动也记录门槛；计时与预警随档保存，
  出口是普通 ``WorldEvent`` 地点（相邻 + Enter）。
"""

from __future__ import annotations

from ..i18n import tr

# 每 6 个客观回合吞掉一圈边界。
EBBING_CONTRACT_INTERVAL = 6
EBBING_GRACE = 6
# 未逃出的代价：最多扣 5 心智；清醒归零时不因罚款形成双归零。
EBBING_FAIL_MIND_COST = 5
# 收缩上限：到第 10 环即整场沉没；中心出口最晚在此之前退出。
EBBING_MAX_RINGS = 10
# 出生门槛平台中心（3×3 = 该坐标 ±1）；离开即触发退潮。
EBBING_PLATFORM = (20, 18)
# 边界墙种（复用既有「意识边界」，零新增符号）。
EBBING_WALL_KIND = "意识边界"


class EbbingMixin:
    """挂在 GameState 上：退潮厅的逐回合收缩。"""

    def _ebbing_ring(self, x: int, y: int) -> int:
        """坐标到最近边界的环序号（0 = 最外圈）。"""
        return min(x, y, self.width - 1 - x, self.height - 1 - y)

    def _tick_ebbing(self, previous: int, amount: int) -> None:
        """纯结算体：只在退潮厅内推进收缩与失败判定。"""
        if self.realm_id != "ebbing_hall":
            return
        self._note_ebbing_departure()
        if not self.ebbing_past_threshold:
            return
        # Entry phase is independent of the main dream's round number. Slow and
        # multi-round actions pay their actual elapsed rounds, including crossing.
        self.ebbing_elapsed += amount
        target = min(EBBING_MAX_RINGS, max(0, (self.ebbing_elapsed-EBBING_GRACE) // EBBING_CONTRACT_INTERVAL))
        while self.ebbing_contract_rounds < target:
            if self.realm_id != "ebbing_hall":
                return  # 已在上一环的失败判定中退出
            self.ebbing_contract_rounds += 1
            self._ebbing_consume_ring(self.ebbing_contract_rounds)
        # ---- 失败：玩家被吞，或已到收缩上限 ----
        if (self._ebbing_ring(self.player.x, self.player.y) < self.ebbing_contract_rounds
                or self.ebbing_contract_rounds >= EBBING_MAX_RINGS):
            self._exit_realm("fail")
            return
        remaining = EBBING_GRACE + EBBING_MAX_RINGS * EBBING_CONTRACT_INTERVAL - self.ebbing_elapsed
        next_rounds = EBBING_GRACE + (self.ebbing_contract_rounds+1) * EBBING_CONTRACT_INTERVAL - self.ebbing_elapsed
        if 0 < next_rounds <= 2 and self.ebbing_warning_ring != self.ebbing_contract_rounds+1:
            from .realm_challenges import say
            self.ebbing_warning_ring = self.ebbing_contract_rounds+1
            self.messages.append(say('tide_warn', ring=self.ebbing_warning_ring,
                                     rounds=next_rounds, remaining=remaining))

    def _note_ebbing_departure(self) -> None:
        """Seal retreat on any crossing, even movement that costs no round."""
        if self.realm_id != 'ebbing_hall' or self.ebbing_past_threshold:
            return
        if max(abs(self.player.x-EBBING_PLATFORM[0]), abs(self.player.y-EBBING_PLATFORM[1])) > 1:
            self.ebbing_past_threshold = True
            from .realm_challenges import say
            self.messages.append(say('tide_start'))

    def _ebbing_consume_ring(self, rounds: int) -> None:
        """把 dist < rounds 的开放格转化为「意识边界」，并清掉其上的内容。"""
        rimmed: set[tuple[int, int]] = set()
        for y in range(self.height):
            for x in range(self.width):
                if self._ebbing_ring(x, y) < rounds:
                    rimmed.add((x, y))
        for (x, y) in rimmed:
            cell = self.cell(x, y)
            if not cell.solid:
                self.configure_wall(cell, EBBING_WALL_KIND)
        if rimmed:
            self.world_items = [it for it in self.world_items if (it.x, it.y) not in rimmed]
            self.events = [e for e in self.events if (e.x, e.y) not in rimmed]
            self.enemies = [e for e in self.enemies if (e.x, e.y) not in rimmed]
            self._reset_material_index()
        self.messages.append(
            tr("潮水又漫过一圈——外环沉入意识边界。（第 {n} 环）", n=rounds)
        )
