"""异象战术角色（2026-10-22，A8「逐角色侧翼协作」的前置）。

## 为什么需要这个模块

方案 §5.1「协作意图可包括前排接近、后排射线、辅助救援、侧路接近；普通怪只做
少量规则，只有对应角色才会主动选侧翼／拦截」。要落地就得先回答「谁是哪个
角色」。本模块只做**可被 grep 与测试锁定**的推导，不做设计发明。

## 推导口径（以及被否掉的口径，都写在这里）

1. **辅助 `support`**：绑定技能里含支援三件之一
   （`edit_heal`／`wake_allies`／`echo_alert`）。这是硬事实，数据表可查。
   **优先级最高**：一个种类既帮人也远程时，它是辅助不是后排。
2. **后排 `back`**：**只认** `pathing.pursuit.RANGED_DISTANCE_BANDS` 里显式登记的
   种类。登记本身就是「这个种类以远程为角色」的人工声明；**不按射程自动推断后排。**
   登记的依据不是射程字段，是机制层面可实测的硬事实：把该种类放在空场里逐个
   调用它绑定的真实 caster，它在 d=1（贴脸）**一张牌都出不了**，要退到 3—6 格
   才有合法施法。贴上来只会普攻，等于把远程角色演成近战。
   当前登记 12 个种类，交集窗口 `(3, 6)`；推导与逐种类数据见
   `pathing/pursuit.py` 上方注释。守门测试 `tests/test_back_role_band_261022.py`
   会重跑这套实测，数据一变就红。
3. **前排 `front`**：有主动技能绑定，但既不是辅助、也没登记为后排。
4. **普通 `none`**：完全没有主动技能绑定（纸鱼、无面祭司这类）。这类只做
   最小区位规则，不参与协作站位。

**被否掉的口径**（三条都实测过，记录在此，避免以后又有人试一遍）：

- 「`max_range ≥ 3` 即后排」——73 个技能里 `max_range` **全部是 8**
  （含 `hospital.needle` 这种「射出至多五格」与 `fix` 类近身技），该字段对
  远程／近战没有任何区分力，按它推导会把所有有技能的异象都判成后排。
- 「绑定里远程形状过半」——`shape` 只有一个兜底值能表达「朝玩家方向的一片」，
  即 `锁定局部范围`（29/73），按它推导判出 **50 个候选**，等于没有角色。
- 「绑定里有射线／十字形状即后排」——`mirror_swap`／`space_fold` 这类位移技
  会让判据同时漏掉真正的后排、误收真正的近战。
- 唯一站得住的是**实测**：「在 d=1 没有任何一张合法的牌」。它直接量的是
  施法入口的返回结果，不依赖任何字段命名。
"""

from __future__ import annotations

from ..data.anomaly_skills import bindings_for

ROLE_NONE = "none"
ROLE_FRONT = "front"
ROLE_BACK = "back"
ROLE_SUPPORT = "support"

# 支援三件：与 `pathing.pursuit._SUPPORT_SKILL_IDS` 同一口径（那边用于走位，
# 这里用于角色判定）；两边都改时必须同步。
SUPPORT_SKILL_IDS = frozenset({"edit_heal", "wake_allies", "echo_alert"})


def role_for(catalog_id: str) -> str:
    """该种类的战术角色。未知种类／无技能种类返回 ``ROLE_NONE``。"""
    if not catalog_id:
        return ROLE_NONE
    bindings = bindings_for(catalog_id)
    if not bindings:
        return ROLE_NONE
    ids = {b.skill_id for b in bindings}
    if ids & SUPPORT_SKILL_IDS:
        return ROLE_SUPPORT
    from .pathing.pursuit import RANGED_DISTANCE_BANDS

    if catalog_id in RANGED_DISTANCE_BANDS:
        return ROLE_BACK
    return ROLE_FRONT


def side_of(target: tuple[int, int], cell: tuple[int, int]) -> int:
    """目标周围八格的「方位桶」：0=北 1=东 2=南 3=西。

    斜角按主轴归桶（|dx| > |dy| 归东西，否则归南北）。八格压在四个桶里，
    目的不是精确方位，而是「这一侧已经有人了吗」——同一侧站两只近战等于
    把包围变成了排队。
    """
    dx = int(cell[0]) - int(target[0])
    dy = int(cell[1]) - int(target[1])
    if abs(dx) > abs(dy):
        return 1 if dx > 0 else 3
    return 2 if dy > 0 else 0
