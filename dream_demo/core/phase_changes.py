"""Finite, capacity-checked phase changes using only registered materials.

The clock is world time, not the number of instability simulation passes.
Frozen volume is material, not a repeatable reward attached to an ice glyph.
"""
from math import ceil

from ..materials.reactions import OTHER_REACTIONS
from ..materials.plants import plant_survives_liquid
from ..materials.walls import WALL_DEFINITIONS
from .constants import Material
from .tamper_protection import construction_reason, liquid_reason, terrain_reason

RATE = 8
COLD = frozenset(('液氮', '液氦'))
VAPOR = {'水': '水蒸气', '红酒': '酒精蒸气', '燃油': '可燃气体'}
CONDENSATE = {'水蒸气': '水', '酒精蒸气': '红酒'}
WAX = {'蜡化记忆墙': 30, '烛泪柱': 20}
FREEZES = tuple(r for r in OTHER_REACTIONS if r.mechanism in ('freeze_floor', 'freeze_wall'))
# 按反应物液体种类预筛配方：普通液体不进入冻结循环（docs §11 P0）。
FREEZE_BY_LIQUID: dict[str, tuple] = {}
for _recipe in FREEZES:
    FREEZE_BY_LIQUID.setdefault(_recipe.reactant_a, ())
    FREEZE_BY_LIQUID[_recipe.reactant_a] += (_recipe,)
CLOCK = 'phase:at'


def locked(state, cell):
    return cell.material_clocks.get(CLOCK) == state.time


def _near(state, x, y, include_self=True):
    points = ((x, y), (x+1, y), (x-1, y), (x, y+1), (x, y-1))
    return [p for p in points[int(not include_self):] if state.inside_board(*p)]


def _mark(state, cell):
    cell.material_clocks[CLOCK] = state.time


def hot(state, x, y):
    cell = state.cell(x, y)
    if cell.aggregate_variant == '灼热聚合物':
        return True
    return any((other.flame > 0 or other.gas_kind == '灼热蒸汽' and other.gas > 0
                or other.liquid_kind == '熔念金属' and other.liquid > 0)
               for other in (state.cell(*p) for p in _near(state, x, y)))


def _deposit_plan(state, x, y, kind, amount, attribute):
    """Reserve compatible capacity before touching any source material."""
    plan = []
    for point in _near(state, x, y):
        cell = state.cell(*point)
        if cell.solid or (point != (x, y) and locked(state, cell)):
            continue
        current = int(getattr(cell, attribute))
        current_kind = getattr(cell, attribute + '_kind')
        if current and current_kind != kind:
            continue
        take = min(amount, max(0, 100-current))
        if take:
            plan.append((point, take)); amount -= take
        if not amount:
            break
    return plan


def _deposit(state, plan, kind, attribute):
    # Plans only include empty or compatible slots: no mixing, cap truncation or
    # source re-indexing can consume material behind the reservation's back.
    for (x, y), amount in plan:
        cell = state.cell(x, y)
        setattr(cell, attribute, getattr(cell, attribute) + amount)
        setattr(cell, attribute + '_kind', kind)
        if attribute == 'liquid' and cell.plant and not plant_survives_liquid(cell.plant):
            state.set_plant_at(cell, 0)
        _mark(state, cell)
        state._sync_material_position(x, y)


def _cold_source(state, x, y, required_kind=None):
    for point in _near(state, x, y):
        cell = state.cell(*point)
        if (cell.liquid > 0 and cell.liquid_kind in COLD
                and (required_kind is None or cell.liquid_kind == required_kind)
                and not locked(state, cell)
                and not liquid_reason(cell.liquid_kind)):
            # The exhausted cold liquid has an existing, inert vapor product.
            plan = _deposit_plan(state, *point, '晨霜清气', 1, 'gas')
            if sum(q for _, q in plan) == 1:
                return point, cell, plan
    return None


def _consume_cold(state, source):
    point, cell, plan = source
    cell.liquid -= 1
    if not cell.liquid:
        cell.liquid_kind = ''
    _mark(state, cell)
    _deposit(state, plan, '晨霜清气', 'gas')
    state._sync_material_position(*point)


def freeze_recipe(state, x, y, recipe, is_hot=None):
    cell = state.cell(x, y)
    if (cell.solid or cell.plant or cell.liquid <= 0
            or cell.liquid_kind != recipe.reactant_a or locked(state, cell)
            or liquid_reason(cell.liquid_kind)
            or (hot(state, x, y) if is_hot is None else is_hot)):
        return False
    if recipe.mechanism == 'freeze_wall' and (construction_reason(state, x, y) or cell.gas):
        return False
    source = _cold_source(state, x, y, recipe.reactant_b)
    if source is None:
        return False
    stock = dict(cell.phase_stock)
    if stock and (stock.get('form') != 'ice' or stock.get('kind') != cell.liquid_kind):
        return False
    total = int(stock.get('amount', 0)) + cell.liquid
    if total > 100:
        return False
    original = stock.get('base_floor', cell.aggregate_variant)
    kind = cell.liquid_kind
    if recipe.mechanism == 'freeze_wall':
        state.configure_wall(cell, recipe.product)
        stock = dict(form='wall', kind=kind, amount=total, initial_amount=total,
                     initial_integrity=cell.integrity, wall=recipe.product, base_floor=original)
    else:
        cell.liquid = 0; cell.liquid_kind = ''
        cell.floor = Material.PLAIN_AGGREGATE
        cell.aggregate_variant = recipe.product
        stock = dict(form='ice', kind=kind, amount=total, base_floor=original)
    cell.phase_stock = stock
    _mark(state, cell)
    _consume_cold(state, source)
    state._sync_material_position(x, y)
    return True


def melt_ice(state, x, y, *, force=False):
    cell = state.cell(x, y)
    if (cell.solid or cell.aggregate_variant != '冰面' or locked(state, cell)
            or not (force or hot(state, x, y))):
        return False
    stock = dict(cell.phase_stock or dict(form='ice', kind='水', amount=8,
                                        base_floor='普通聚合物'))
    if stock.get('form') != 'ice' or liquid_reason(stock.get('kind', '')):
        return False
    amount = max(0, min(100, int(stock.get('amount', 0))))
    plan = _deposit_plan(state, x, y, stock['kind'], min(RATE, amount), 'liquid')
    taken = sum(q for _, q in plan)
    if not taken:
        return False
    stock['amount'] = amount-taken
    cell.phase_stock = stock if stock['amount'] else {}
    if not stock['amount']:
        cell.aggregate_variant = stock.get('base_floor', '普通聚合物')
    _mark(state, cell)
    _deposit(state, plan, stock['kind'], 'liquid')
    state._sync_material_position(x, y)
    return True


def _melt_wall(state, x, y, *, force=False):
    cell = state.cell(x, y)
    if (not cell.solid or cell.wall_kind not in WAX or locked(state, cell)
            or not (force or hot(state, x, y)) or terrain_reason(state, x, y)):
        return False
    definition = WALL_DEFINITIONS[cell.wall_kind]
    stock = dict(cell.phase_stock)
    if not stock:
        amount = max(1, WAX[cell.wall_kind]*cell.integrity//definition.integrity)
        stock = dict(form='wall', kind='熔融蜡烛', amount=amount,
                     initial_amount=amount, initial_integrity=cell.integrity,
                     wall=cell.wall_kind, base_floor=cell.aggregate_variant)
    if stock.get('form') != 'wall' or stock.get('kind') != '熔融蜡烛':
        return False
    amount = min(int(stock['amount']), ceil(int(stock['initial_amount'])*cell.integrity /
                                          max(1, int(stock['initial_integrity']))))
    plan = _deposit_plan(state, x, y, '熔融蜡烛', min(RATE, amount), 'liquid')
    taken = sum(q for _, q in plan)
    if not taken:
        return False
    stock['amount'] = amount-taken
    if not stock['amount']:
        if not state.destroy_wall(x, y, 'phase_melt'):
            return False
        cell.aggregate_variant = stock.get('base_floor', '普通聚合物')
        cell.phase_stock = {}
    else:
        cell.phase_stock = stock
        cell.integrity = max(1, ceil(int(stock['initial_integrity'])*stock['amount'] /
                                    max(1, int(stock['initial_amount']))))
    _mark(state, cell)
    _deposit(state, plan, '熔融蜡烛', 'liquid')
    state._sync_material_position(x, y)
    return True


def melt_wall(state, x, y, *, force=False):
    """公开入口：蜡墙回蜡。

    ``force=True`` 时无视热量，按存量逐步化回熔蜡——应急蜡封到期时用这条
    通道；受热提前融化仍走 ``tick`` 里的热路径（``force=False``）。
    """
    return _melt_wall(state, x, y, force=force)


def tick(state):
    state._ensure_material_index()
    # 相变存量/蜡墙由材料索引维护；不再每拍全图补扫（docs §11 P0）。
    candidates = set(state._liquid_cells) | set(state._gas_cells)
    candidates |= set(getattr(state, '_phase_cells', ()))
    for x, y in sorted(candidates):
        cell = state.cell(x, y)
        if locked(state, cell):
            continue
        if cell.solid:
            if cell.wall_kind in WAX:
                _melt_wall(state, x, y)
            continue
        if (cell.phase_stock or cell.aggregate_variant == '冰面') and melt_ice(state, x, y):
            continue
        liquid_kind = str(cell.liquid_kind or '')
        gas_kind = str(cell.gas_kind or '')
        liquid = int(cell.liquid)
        gas = int(cell.gas)
        vapor = liquid > 0 and liquid_kind in VAPOR
        condensate = gas > 0 and gas_kind in CONDENSATE
        recipes = FREEZE_BY_LIQUID.get(liquid_kind) if liquid > 0 else ()
        if not (vapor or condensate or recipes or cell.phase_stock):
            continue
        is_hot = hot(state, x, y) if (vapor or condensate or recipes) else False
        if vapor and is_hot and not liquid_reason(liquid_kind):
            product = VAPOR[liquid_kind]
            plan = _deposit_plan(state, x, y, product, min(RATE, liquid), 'gas')
            taken = sum(q for _, q in plan)
            if taken:
                cell.liquid -= taken
                if not cell.liquid: cell.liquid_kind = ''
                _mark(state, cell); _deposit(state, plan, product, 'gas')
                state._sync_material_position(x, y)
            continue
        if is_hot is False and condensate:
            source = _cold_source(state, x, y)
            product = CONDENSATE[gas_kind]
            plan = _deposit_plan(state, x, y, product, min(RATE, gas), 'liquid')
            taken = sum(q for _, q in plan)
            if source is not None and taken:
                # The target plan must not consume capacity reserved for the
                # cold byproduct; those are separate material slots.
                cell.gas -= taken
                if not cell.gas: cell.gas_kind = ''
                _mark(state, cell); _deposit(state, plan, product, 'liquid')
                _consume_cold(state, source); state._sync_material_position(x, y)
                continue
        if is_hot is False and recipes:
            for recipe in recipes:
                if freeze_recipe(state, x, y, recipe, is_hot=False):
                    break
