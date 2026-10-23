"""门的开合：有生物/物品踩上即开、离开即关；门的恒阻视线由 SightMixin 处理。"""

from __future__ import annotations

from ..i18n import tr
from ..materials import DOOR_KINDS, wall_def
from .constants import Material
from .entities import Cell



class DoorMixin:
    @staticmethod
    def _open_door(cell: Cell) -> None:
        """把门打到「开」：变为可通行（相当于空气），但保留 ``wall_kind="门"``
        以便识别与恒阻视线（见 ``_sight_reaches``）。"""
        cell.solid = False
        cell.floor = Material.PLAIN_AGGREGATE
        cell.height = 0
        cell.hardness = 0
        cell.thickness = 0
        cell.integrity = 0
        cell.liquid = 0
        cell.liquid_kind = ""
        cell.gas = 0
        cell.gas_kind = ""
        cell.flame = 0

    def _close_door(self, cell: Cell) -> None:
        """把门打到「关」：恢复为高墙实体（相当于墙，阻挡移动与液体/气体）。"""
        definition = wall_def(cell.wall_kind or "门")
        cell.solid = True
        cell.floor = Material.SOLID_AGGREGATE
        cell.height = definition.height
        cell.hardness = definition.hardness
        cell.thickness = definition.thickness
        cell.integrity = definition.integrity
        cell.liquid = 0
        cell.liquid_kind = ""
        cell.gas = 0
        cell.gas_kind = ""

    def _update_doors(self) -> None:
        """按占位刷新所有门的开/合：门上有任意生物或物品即开（可穿过气体液体），
        否则关（相当于墙）。门恒阻视线由 ``_sight_reaches`` 单独处理，这里只管通行与流体。
        """
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                if cell.wall_kind not in DOOR_KINDS:
                    continue
                occupied = (
                    (self.player.x == x and self.player.y == y)
                    or any(
                        enemy.integrity > 0 and enemy.x == x and enemy.y == y
                        for enemy in self.enemies
                    )
                    or any(item.x == x and item.y == y for item in self.world_items)
                )
                if occupied:
                    if cell.solid:
                        self._open_door(cell)
                        self.topology_revision += 1
                        # docs 261022 §16.6：门状态确实改变才发 R=2 机械声。
                        self._sound_pulse(x, y, 2, category="mechanical",
                                          source=tr("门"), announce=False)
                elif not cell.solid:
                    self._close_door(cell)
                    self.topology_revision += 1
                    self._sound_pulse(x, y, 2, category="mechanical",
                                      source=tr("门"), announce=False)

