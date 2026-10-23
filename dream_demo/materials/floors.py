"""聚合地面变体（地板）的机制定义。

``Cell.aggregate_variant`` 原本只决定颜色与悬停显示（见 ui/render.py 的
AGGREGATE_STYLES）。这里给它实装轻量效果与环境交互：
每种地板一个 :class:`FloorDef`，各效果只调环境通道的一点点边角。

设计约束（2026-09-17 玩家要求，**2026-10-07 D1 放宽**，**2026-10-15 混乱化改造回归**）：
- 地板依旧**绝不造成直接伤害、绝不改变通行性**——地板永远可以放心走；
- 2026-10-07 曾允许 ±1 量级的创伤读数（灼热聚合物 ``scald_lucidity``），
  2026-10-15 混乱化改造把地板**拉回零创伤**：灼热聚合物改走纯环境通道
  （挥发 +4 / 气体消散 +2），``scald_lucidity`` 字段保留但已无地板使用；
- 2026-10-15 起环境交互数值全面上调（挥发/吸水/流动/视野/声响/吸气/增益），
  让「能与环境互动、能改造环境的地板」真正参与场面改造，不再是边角点缀；
- 优先走已有的环境通道（液体挥发/流动、气体消散、视野、声响、踩踏、植物生成）；
- 液体的两条损耗通道**节奏不同**：挥发沿用 ``LIQUID_DECAY_INTERVAL``（20 回合），
  吸水另走 ``LIQUID_ABSORB_INTERVAL``（2 回合）——吸水要的是「一点点渗下去」，
  用挥发的大周期会显得突兀。

只有 ``floor is Material.PLAIN_AGGREGATE`` 的格子才吃这些效果——液态记忆、
弥散印象等其它地面类型即便残留着变体名也不生效（见 :func:`floor_effect_for`）。

各变体的实际效果（``FLOOR_DEFINITIONS``）：

==================  ==========================================================
普通聚合物          基准面：无任何特殊效果（对照用）
柔软聚合物          软垫护住植物：踩过不会把高丛踩折（protects_plants）
粗糙聚合物          磨砂颗粒拖慢液体：流动预算 ÷3，扩散变慢但不堵死（flow_divisor）
反光聚合物          映出光线：站在上面视距 +2（sight_bonus）
吸声聚合物          吞掉回响：站在上面声响半径 −4（sound_reduction）
空白聚合物          梦还没画完：植物无法在其上生长（bare）
木质聚合物          吸湿易干：每挥发区间多蒸掉 3 点液体（evaporation_bonus）
海绵聚合物          多孔吸水：每 2 回合渗掉 2 点液体，不产气（liquid_absorb）
金属聚合物          光滑冷硬：液体流动预算 ×5，流得更畅（flow_bonus）
灼热聚合物          余温：每挥发区间多蒸掉 4 点液体，气体消散 +2（两头都慢不下来）
==================  ==========================================================

数值标定：挥发按 ``LIQUID_DECAY_INTERVAL``（20 回合）结算，吸水按
``LIQUID_ABSORB_INTERVAL``（2 回合）结算——两者刻意用不同节奏，因为挥发是
「隔一阵蒸发一截」，而吸水要的是「一点点渗下去」：

- 海绵 2 点/2 回合 ≈ 1 点/回合：一小滩 20 点的液体约 20 回合渗干，满池
  100 点约 100 回合。**每 2 回合才扣 2 点**，玩家看到的是一条平滑的下降曲线，
  而不是每隔 20 回合突然少一截。
- 粗糙的 ``flow_divisor=3`` 只是把流动预算除以 3（下限 1）：水本来的
  ``max_flow`` 是 24，粗糙面上是 8，扩散明显变慢，但**永远不会变成 0**
  ——磨砂地面拖住液体，不是把液体封在原地。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import Material


@dataclass(frozen=True)
class FloorDef:
    variant: str
    # 每个吸收区间（LIQUID_ABSORB_INTERVAL = 2 回合）被地面吸走的液量；不生成气体。
    # 按短周期反复结算，数值取 1～2——「一点点渗下去」而不是「隔一阵少一截」。
    liquid_absorb: int = 0
    # 每挥发区间额外挥发掉的液量；走液体自己的挥发通道（有 evaporation_gas 才产气）。
    evaporation_bonus: int = 0
    # 液体流动预算加成：budget = max_flow * (1 + flow_bonus)。
    flow_bonus: int = 0
    # 液体流动预算折减：budget //= flow_divisor（下限 1，只让扩散变慢、不会变成 0）。
    flow_divisor: int = 1
    # 每消散区间（GAS_DECAY_INTERVAL 回合）额外消散的气量。
    gas_dissipation_bonus: int = 0
    # 站在本格上时的视距加成。
    sight_bonus: int = 0
    # 站在本格上时声响半径的减免（至少留 1）。
    sound_reduction: int = 0
    # 踩踏不折植物（软垫护住）。
    protects_plants: bool = False
    # 植物无法在本格生长。
    bare: bool = False
    # 地图符号键（symbols.SYMBOLS）：缺省用通用 "floor"（"· "），与旧变体一致。
    symbol_key: str = "floor"
    # 冰面：沿移动方向一次性滑到头（撞到墙/固体/离开冰面为止），仍只花 1 回合。
    slide: bool = False
    # 可燃地板：被火焰点燃后烧毁，回落为指定变体（如书页地 → 普通聚合物）。
    burns_to: str = ""
    # 位面专属登记：非空时只有这些位面（realm_id）的生成器允许铺设本变体，
    # 主梦与其它位面的随机地板池一律排除（与 WallDef/LiquidDef/GasDef 同口径）。
    spawn_realms: tuple[str, ...] = ()
    # 每 2 回合从本格气体中吸收的气量（月壤）。
    gas_absorb: int = 0
    # 保气地板跳过自然消散与地板吸附；扩散、反应、燃烧及抽取仍正常转移数量。
    preserves_gas: bool = False
    # 棋盘格：黑白两色按回合奇偶交替显示。
    checkerboard: bool = False
    # 棋盘格：上方生物每回合以此概率获得一个随机常见增益征兆。
    buff_chance: float = 0.0
    # 绝热层：火焰无法蔓延进本格（本格永不烧起来）。
    fireproof: bool = False
    # 压电地板：站上每回合 +1 层蓄电，离开每回合 −1；攒满 ``piezo_threshold``
    # 层清零并放电（2026-10-15 混乱化改造：放电只打击异象，玩家零创伤）。
    piezo: bool = False
    piezo_threshold: int = 4
    # 空鼓地板：踩踏发出空洞声响引怪（值为声响半径）。
    hollow_noise: int = 0
    # 真实落脚声径（docs 261022 §6.2）：0 = 安静落脚面，1 = 普通硬地轻响，
    # 2 = 接缝／金属／木质，4 = 空鼓的显著闷响。与液体接触声取较大值。
    footstep: int = 1
    # 【2026-10-15 退役】灼热地板的战斗读数字段（2026-10-07 D1 放宽引入）：
    # 混乱化改造后地板回归零创伤，当前没有任何地板使用本字段；代码保留
    # 兼容旧存档与外部登记（materials_sim 的结算路径读到此字段才会生效）。
    scald_lucidity: int = 0
    # 传送带（扩展包 v1）：方向 (dx,dy)；站上不动被推行一格/回合，
    # 顺行移动耗时减半（两次免一步）、逆行翻倍。不可燃、无需动力。
    conveyor: tuple = ()


PLAIN_FLOOR = FloorDef("普通聚合物")

FLOOR_DEFINITIONS: dict[str, FloorDef] = {
    "普通聚合物": PLAIN_FLOOR,
    "密封板": FloorDef("密封板", preserves_gas=True, bare=True, footstep=2,
                       spawn_realms=("white_sanatorium",)),
    "洁白釉板": FloorDef("洁白釉板", bare=True, footstep=2,
                         spawn_realms=("white_sanatorium",)),
    "柔软聚合物": FloorDef("柔软聚合物", protects_plants=True, footstep=0),
    "粗糙聚合物": FloorDef("粗糙聚合物", flow_divisor=3, footstep=2),
    "反光聚合物": FloorDef("反光聚合物", sight_bonus=2),
    "吸声聚合物": FloorDef("吸声聚合物", sound_reduction=4, footstep=0),
    "空白聚合物": FloorDef("空白聚合物", bare=True),
    "木质聚合物": FloorDef("木质聚合物", evaporation_bonus=3, footstep=2),
    "海绵聚合物": FloorDef("海绵聚合物", liquid_absorb=2, footstep=0),
    "金属聚合物": FloorDef("金属聚合物", flow_bonus=4, footstep=2),
    "灼热聚合物": FloorDef("灼热聚合物", evaporation_bonus=4, gas_dissipation_bonus=2),
    # ---- 2026-09-18 Excel 新一批（专属符号 ⨀⊙●○ 等，与其他地形区分）----
    # 梦境绒毯：完全消音（声响半径压到最小 1），不可燃（火焰蔓延绕开）。
    "梦境绒毯": FloorDef("梦境绒毯", sound_reduction=9, footstep=0,
                       symbol_key="floor.carpet", fireproof=True),
    # 冰面：沿移动方向滑到头，只花 1 回合。
    "冰面": FloorDef("冰面", symbol_key="floor.ice", slide=True),
    # 星图地：嵌着星图微微发光——站上面视距 +3。
    "星图地": FloorDef("星图地", symbol_key="floor.star", sight_bonus=3),
    # 书页地：纸页铺地，可燃；烧完变回普通聚合物。
    "书页地": FloorDef("书页地", symbol_key="floor.page", burns_to="普通聚合物"),
    # 月壤：孔隙吸气——每 2 回合从本格吸掉 2 点气体。
    "月壤": FloorDef("月壤", symbol_key="floor.moon", gas_absorb=2, footstep=0),
    # 棋盘格地板：黑白按回合交替；上方生物每回合 25% 获得一个常见增益征兆。
    "棋盘格地板": FloorDef("棋盘格地板", symbol_key="floor.checker", checkerboard=True, buff_chance=0.25),
    # 绝热层：火焰无法在上面蔓延。
    "绝热层": FloorDef("绝热层", symbol_key="floor.insulation", fireproof=True),
    # 压电地板：蓄电征兆堆叠（站 +1/回合、离开 −1/回合），满 3 层放电；
    # 2026-10-15 起放电只打击失控意识，玩家不再吃清醒创伤。
    "压电地板": FloorDef("压电地板", symbol_key="floor.piezo", piezo=True, piezo_threshold=3),
    # ---- 内容扩展包 v1（2026-09-20）----
    # 空鼓地板：踩踏发出空洞闷响（2026-10-22 起并入统一足音，R=4）——压力地板
    # 的「哑弹」变体，与压力地板外观相似，让玩家无法确定脚下地板是否连着机关。
    "空鼓地板": FloorDef("空鼓地板", symbol_key="floor.hollow", hollow_noise=4, footstep=4),
    # 压力地板：逻辑固体·触发源的地板形态（踏上/离开各发一次信号，强度 2）——
    # 信号管线在逻辑固体批次接线；本批先落地板变体与符号。
    "压力地板": FloorDef("压力地板", symbol_key="floor.pressure"),
    # ---- 传送带（扩展包 v1）：四向、不可燃、无需动力 ----
    "传送带·北": FloorDef("传送带·北", symbol_key="floor.belt.n", fireproof=True, conveyor=(0, -1)),
    "传送带·东": FloorDef("传送带·东", symbol_key="floor.belt.e", fireproof=True, conveyor=(1, 0)),
    "传送带·南": FloorDef("传送带·南", symbol_key="floor.belt.s", fireproof=True, conveyor=(0, 1)),
    "传送带·西": FloorDef("传送带·西", symbol_key="floor.belt.w", fireproof=True, conveyor=(-1, 0)),
}


def floor_def(variant: str) -> FloorDef:
    """变体名 → 定义；未登记的变体一律按「普通聚合物」（无效果）处理。"""
    return FLOOR_DEFINITIONS.get(variant, PLAIN_FLOOR)


def floor_fireproof(cell) -> bool:
    """该格的变体是否防火（不受 cell.floor 材质门控——植物格是 SOLID 地面，
    floor_effect_for 会回落成普通聚合物，防火语义就丢了）。"""
    return FLOOR_DEFINITIONS.get(cell.aggregate_variant, PLAIN_FLOOR).fireproof


def floor_effect_for(cell) -> FloorDef:
    """格子的地板效果。

    只有 ``floor is Material.PLAIN_AGGREGATE`` 的格子才生效：液态记忆、
    弥散印象等其它地面类型即便残留着聚合变体名，也不该带着变体效果。
    """
    if cell.floor is not Material.PLAIN_AGGREGATE:
        return PLAIN_FLOOR
    return FLOOR_DEFINITIONS.get(cell.aggregate_variant, PLAIN_FLOOR)
LIBRARY_FLOORS={
    '干纸堆':FloorDef('干纸堆',burns_to='普通聚合物',spawn_realms=('library_palace',)),
    '防火石面':FloorDef('防火石面',fireproof=True,spawn_realms=('library_palace',)),
}
FLOOR_DEFINITIONS.update(LIBRARY_FLOORS)
