"""材料数据类：墙体 / 液体 / 气体 / 征兆的定义骨架。

每个材料类别一个定义 dataclass，目录表与生成参数放在各自的模块里
（walls.py / liquids.py / gases.py / portents.py），这里只放类型本身。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WallDef:
    name: str
    symbol_key: str
    color: str
    hardness: int
    height: int
    thickness: int
    integrity: int
    proximity_effect: str = ""
    break_effect: str = "none"
    hand_breakable: bool = False
    # 透明墙体：仍然坚实（阻挡移动），但不阻断视线——隔墙可以看见对面的地形与异象。
    transparent: bool = False
    # 「点击可寻路」（隐藏属性，游戏内文本不显示）：这类固体虽然不可通行，
    # 但左键点它时不会当场放弃寻路——改为寻路到它旁边、被它挡住，然后回应
    # 台面上的异常地点或取走台面上的显化物（见 ui/input.py 的 _left_click）。
    # 台子（木桌子/石台）第一个使用它；以后其他「值得走过去点一下」的固体也挂这个旗标。
    path_clickable: bool = False
    # 可推墙（推箱子式）：向它移动会把它推到下一格（只能推不能拉），
    # 下一格被墙/生物/边界挡住时推不动。
    pushable: bool = False
    # 免疫弹体：子弹/远程攻击对它完全不造成损伤（如玉米淀粉墙吞掉所有弹体）。
    projectile_immune: bool = False
    flammable: bool = False
    spawn_realms: tuple[str, ...] = ()
    gas_dissipation_multiplier: int = 1
    gas_push_direction: tuple[int, int] = ()
    gas_push_range: int = 6
    light_radius: int = 0


@dataclass(frozen=True)
class LiquidDef:
    name: str
    color: str
    max_flow: int
    viscosity: int
    # Base evaporation amount; ordinary legacy liquids retain zero.
    evaporation: int = 0
    evaporation_gas: str = ""
    contact_effect: str = ""
    flammable: bool = False
    # 扩散无视地势：不看地势高低，向所有开放邻格均匀流动（如液氦超流体）。
    ignores_terrain: bool = False
    # 流到的格子上的火焰被当场扑灭（不产生灼热蒸汽之类的次生反应）。
    extinguishes_fire: bool = False
    # Slow liquids receive one source budget per world-time period, shared by
    # all simulation passes. One retains the existing fast-liquid behaviour.
    flow_period: int = 1
    # Zero retains the legacy global evaporation clock. Authored liquids have
    # independent cell clocks and may use a conservative 1:1 gas conversion.
    evaporation_period: int = 0
    evaporation_ratio: int = 2
    spawn_realms: tuple[str, ...] = ()  # Empty means unrestricted generation.
    gas_flow_divisor: int = 1
    gas_flow_threshold: int = 8
    light_radius: int = 0
    light_threshold: int = 6
    # 踩入液面时的接触声径（docs 261022 §6.2）：负值按黏度推导，
    # 稀液 2／黏稠 1；特殊液体（回声、金属、超流体等）显式登记。
    contact_noise: int = -1


@dataclass(frozen=True)
class GasDef:
    name: str
    symbol_key: str
    color: str
    max_diffusion: int
    dissipation: int
    opacity: int
    inhalation_effect: str = ""
    flammable: bool = False
    # 类墙体效果（不是征兆）：黑烟完全阻断视线；灰尘云把「透过后」的剩余视野按倍率衰减。
    blocks_sight: bool = False
    sight_attenuation: float = 1.0
    dissipation_period: int = 0  # Zero keeps the legacy global decay interval.
    spawn_realms: tuple[str, ...] = ()
    # 浓度达到 light_threshold 时形成机械照明，照亮半径 light_radius（0 = 不发光）。
    # 与液体共用同一组字段名，供 glow.source_radius 统一判定（docs 261022 §13.3）。
    light_radius: int = 0
    light_threshold: int = 6


@dataclass(frozen=True)
class PortentDef:
    """征兆：附着在意识上的持续状态。

    材料来源的征兆由 `material` 字段绑定到液体/气体名——踩进该材料的格子时
    按 `duration` 赋予若干回合，站在其中不叠加也不递减，离开后才逐回合衰减
    到消失。非材料来源的征兆（道具、异象）由 core 的状态谓词驱动。
    """

    name: str
    kind: str  # 正面 / 负面 / 中性
    effect: str  # 界面上的灰色注释与 Excel 的具体效果
    source: str  # 获取方式
    duration: int = 0  # 接触赋予的回合数（0 = 非接触来源）
    material: str = ""  # 触发材料名（液体或气体）
    affects_creatures: bool = True  # 是否同样赋予其他生物
    # 每 period 回合结算一次的资源变化（正为恢复），period 为 0 表示不随时间滴血。
    # 计时一律走「回合」（客观时间，见 core 顶部的时间轴术语）。
    period: int = 0
    mind: float = 0
    lucidity: float = 0
    imagination: float = 0
    # 镇静：持续期内拦截「环境来源」的心智减少（毒气/腐蚀/下潜反噬等；
    # 2026-10-07 起异象造成的战斗创伤不再被拦截——见 core._lose_mind 的 combat 口径）。
    blocks_mind_loss: bool = False
    # 心智流失倍率（1.0 = 不减）：<1 的征兆（忘忧 0.5）对**一切**心智来源生效，
    # 包括异象战斗创伤。与 blocks_mind_loss 叠乘。
    mind_loss_factor: float = 1.0
    # 连续型修正。
    move_time: float = 0.0
    attack_time: float = 0.0
    vision: int = 0
    # ---- 视觉通道分类（docs 261022 §14.1）----
    # 一条效果只允许登记「平减 `vision`」或「比例 `vision_ratio`」之一，不能同一次
    # 效果既减 n 又乘倍率。同族（`vision_family`）平减取最大，不同族可共同作用；
    # 比例缩视跨族取最小倍率（不相乘至近零）。`blinds` 在最后覆盖，普通视觉归零。
    vision_ratio: float = 1.0
    vision_family: str = ""
    blinds: bool = False
    # 本项平减最多把结果压到的下限（docs §14.1 的「失焦只对本项托底 3」）：
    # 0 = 不托底。托底只约束这一项自己，不会解除别的致盲／限视。
    vision_floor: int = 0
    # 单轮硬期限（回合）：0 = 沿用 `duration`×层＋附着推导出的预算。
    round_max: int = 0
    sound_multiplier: int = 1
    extra_turn: int = 0
    # 行动速度倍率（>1 = 更快）：2.0 表示「加速 2 倍」，该生物的行动耗时减半
    # ——1 回合登记为 0.5 回合，零头由 core 的 round_debt 记账，两次行动才
    # 凑满 1 回合结算一次。与 move_time / attack_time 的区别：那两个是
    # 「额外追加的时间」，本字段是「整体倍率」。
    speed_multiplier: float = 1.0
    min_amount: int = 5  # 生效最少材料量（默认沿用全局接触下限）
    # 洞见所有意象：视野外的失控意识也以轮廓显形（诅咒灵视）。
    reveal_anomalies: bool = False
    # ---- 界面计数口径：层 vs 回合（2026-09-16）----
    # 「层」= 可叠加的份数/使用次数（不会自然消失的那一类，如镜面架势的
    # 反弹次数）；「回合」= 持续时间（`duration`，会随时间衰减）。
    # 两者独立计数，同时存在时**界面先写层、后写回合**，各自归零互不影响；
    # 默认时长归零只降 1 层（`duration_drop`，0 表示不降层），层数归零才消失。
    # `stacks` 留 0 = 这个征兆不谈层数（界面上不显示「层」）。
    stacks: int = 0
    # 默认时长（duration）耗尽时降低的层数：默认 1（玩家口径），特殊规定可改。
    duration_drop: int = 1
    washable: bool = False  # Only finite, explicitly registered durations may be shortened.
