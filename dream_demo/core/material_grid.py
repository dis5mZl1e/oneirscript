"""材料数组兼容视图：生产地图与 Cell 共享同一数值所有者。

phase_stock 仅镜像存量字典的存在标记；组成、数量及原地板仍读 Cell。
拒绝无法精确表示的数值，由调用方退回 Cell 路径，不截断游戏状态。
"""
from array import array
from enum import Enum

from ..materials.floors import floor_effect_for, FLOOR_DEFINITIONS, PLAIN_FLOOR
from ..materials.gases import GAS_DEFINITIONS
from ..materials.liquids import LIQUID_DEFINITIONS
from ..materials.walls import CONTAINER_KINDS
from .constants import GAS_MIN_FLOW, LIQ_MIN_FLOW, Material


class MaterialGrid:
    """行优先连续数组；一格数值存储 20 字节，名称表另计。"""

    CONTAINER = 1
    PRESERVES_GAS = 2
    FLOW_PASSABLE = 4
    GAS_FLOW_PASSABLE = 8
    # 仅表示本格候选资格；边界、封锁、延期预算仍由 pass 判断。
    LIQUID_SOURCE = 16
    GAS_SOURCE = 32
    BYTE_FIELDS = ('liquid', 'gas', 'flame', 'solid', 'height',
                   'plant', 'phase_stock', 'flags')
    SIGNED_FIELDS = ('elevation',)
    ID_FIELDS = ('liquid_id', 'gas_id', 'wall_id', 'floor_id', 'variant_id')

    def __init__(self, cells, width, height):
        if (type(width) is not int or type(height) is not int
                or width < 0 or height < 0
                or len(cells) != height or any(len(row) != width for row in cells)):
            raise ValueError('材料镜像尺寸与格子数组不一致')
        self.width, self.rows = width, height
        # 保存数组身份，deepcopy((state.cells, grid)) 时也保持共享关系。
        self._cells = cells
        self.names = ['']
        self._ids = {'': 0}
        size = width * height
        for field in self.BYTE_FIELDS:
            setattr(self, field, bytearray(size))
        for field in self.ID_FIELDS:
            setattr(self, field, array('H', [0]) * size)
        self.elevation = array('h', [0]) * size
        self.store = getattr(cells, 'store', None)
        if self.store is not None:
            for field in ('liquid', 'gas', 'flame', 'solid', 'height', 'plant', 'elevation'):
                setattr(self, field, self.store.columns[field])
        self._cursor = None

    @classmethod
    def from_cells(cls, cells, width, height):
        grid = cls(cells, width, height)
        for y, row in enumerate(cells):
            for x, cell in enumerate(row):
                grid.sync_cell(x, y, cell)
        if grid.store is not None:
            grid._cursor = grid.store.journal.cursor
        return grid

    def refresh_changes(self):
        """Update only derived columns touched since this view's private cursor.

        Consumers retain their own cursor; reading never drains another reader.
        A lagging cursor requests full recovery after bounded history expires.
        """
        if self.store is None:
            raise ValueError('incremental refresh requires an authoritative map')
        batch = self.store.journal.changes_since(self._cursor)
        positions = range(self.width * self.rows) if batch.reset else batch.positions
        for position in positions:
            y, x = divmod(position, self.width)
            self.sync_cell(x, y, self._cells[y][x])
        self._cursor = batch.cursor
        return batch

    def matches(self, cells, width, height):
        """仅校验地图身份和尺寸；单格修改由 sync_cell 同步。"""
        return cells is self._cells and width == self.width and height == self.rows

    def index(self, x, y):
        if (type(x) is not int or type(y) is not int
                or not 0 <= x < self.width or not 0 <= y < self.rows):
            raise IndexError((x, y))
        return y * self.width + x

    def intern(self, value):
        """空串固定为 0；未知内容同样保留，不依赖注册表完整性。"""
        if isinstance(value, Enum):
            value = value.value
        if not isinstance(value, str):
            raise ValueError('材料 ID 名称必须是字符串')
        found = self._ids.get(value)
        if found is not None:
            return found
        if len(self.names) >= 65536:
            raise ValueError('材料 ID 超出 uint16 容量')
        identifier = len(self.names)
        self.names.append(value)
        self._ids[value] = identifier
        return identifier

    def name(self, identifier):
        return self.names[identifier]

    @property
    def nbytes(self):
        """数组有效字节数，不含 Python 对象头及 intern 名称表。"""
        return (sum(len(getattr(self, field)) for field in self.BYTE_FIELDS)
                + sum(len(getattr(self, field)) * getattr(self, field).itemsize
                      for field in self.ID_FIELDS + self.SIGNED_FIELDS))

    def _sync_owned(self, position):
        from .material_numeric import try_sync_owned
        if try_sync_owned(self, position, globals()):
            return
        columns = self.store.columns
        # Nonrepresentable values retain their exact Cell fallback. Validate
        # before deriving any marker; never consume the placeholder array zero.
        for field in ('liquid', 'gas', 'flame', 'height', 'plant', 'elevation', 'solid'):
            if (field, position) in self.store.exceptions:
                raise ValueError(f'{field} cannot be represented by the compact material view')
        # Owned Cell reads bool columns through bool(value), including legacy
        # integer writes such as solid=2. Match that visible contract without
        # rewriting the authoritative raw value or creating an unjournaled edit.
        solid = bool(columns['solid'][position])
        phase = columns['phase_stock'][position]
        if not isinstance(phase, dict):
            raise ValueError('phase_stock must be a dictionary')
        liquid_kind, gas_kind = columns['liquid_kind'][position], columns['gas_kind'][position]
        wall_kind = columns['wall_kind'][position]
        floor, variant = columns['floor'][position], columns['aggregate_variant'][position]
        identifiers = [self.intern(value) for value in
                       (liquid_kind, gas_kind, wall_kind, floor, variant)]
        container = wall_kind in CONTAINER_KINDS
        passable = not solid or columns['height'][position] <= 1
        effect = FLOOR_DEFINITIONS.get(variant, PLAIN_FLOOR) if floor is Material.PLAIN_AGGREGATE else PLAIN_FLOOR
        flags = self.CONTAINER if container else 0
        if effect.preserves_gas:
            flags |= self.PRESERVES_GAS
        if passable:
            flags |= self.FLOW_PASSABLE
            if not container:
                flags |= self.GAS_FLOW_PASSABLE
                if columns['liquid'][position] >= LIQ_MIN_FLOW and liquid_kind in LIQUID_DEFINITIONS:
                    flags |= self.LIQUID_SOURCE
                if columns['gas'][position] >= GAS_MIN_FLOW and gas_kind in GAS_DEFINITIONS:
                    flags |= self.GAS_SOURCE
        # Numeric columns already alias the owner: only derived values change.
        self.phase_stock[position] = bool(phase)
        self.flags[position] = flags
        for field, identifier in zip(self.ID_FIELDS, identifiers):
            getattr(self, field)[position] = identifier

    def sync_cell(self, x, y, cell):
        position = self.index(x, y)
        if (self.store is not None
                and cell.__dict__.get('_material_binding') == (self.store, position)):
            self._sync_owned(position)
            return
        values = {}
        # 先完整校验再写数组，避免失败时留下半格新数据。
        for field in ('liquid', 'gas', 'flame', 'height', 'plant'):
            value = getattr(cell, field)
            if type(value) is not int or not 0 <= value <= 255:
                raise ValueError(f'{field} 无法精确表示为 uint8: {value!r}')
            values[field] = value
        if type(cell.elevation) is not int or not -32768 <= cell.elevation <= 32767:
            raise ValueError(f'elevation 无法精确表示为 int16: {cell.elevation!r}')
        values['elevation'] = cell.elevation
        if not isinstance(cell.solid, (bool, int)) or cell.solid not in (False, True):
            raise ValueError(f'solid 无法表示为布尔值: {cell.solid!r}')
        if not isinstance(cell.phase_stock, dict):
            raise ValueError('phase_stock 必须是存量字典')
        values['solid'] = int(cell.solid)
        values['phase_stock'] = int(bool(cell.phase_stock))
        identifiers = [self.intern(value) for value in
                       (cell.liquid_kind, cell.gas_kind, cell.wall_kind,
                        cell.floor, cell.aggregate_variant)]
        container = cell.wall_kind in CONTAINER_KINDS
        passable = not cell.solid or cell.height <= 1
        flags = self.CONTAINER if container else 0
        if floor_effect_for(cell).preserves_gas:
            flags |= self.PRESERVES_GAS
        if passable:
            flags |= self.FLOW_PASSABLE
            if not container:
                flags |= self.GAS_FLOW_PASSABLE
                if cell.liquid >= LIQ_MIN_FLOW and cell.liquid_kind in LIQUID_DEFINITIONS:
                    flags |= self.LIQUID_SOURCE
                if cell.gas >= GAS_MIN_FLOW and cell.gas_kind in GAS_DEFINITIONS:
                    flags |= self.GAS_SOURCE
        values['flags'] = flags
        for field, value in values.items():
            getattr(self, field)[position] = value
        for field, identifier in zip(self.ID_FIELDS, identifiers):
            getattr(self, field)[position] = identifier
