"""植物在界面上必须提前说清的几件事（docs 2026-10-26 §3.4.4、§10.1）。

公开性要求：**名称、格内描述、格子详情的「踩踏／拔除」两行、拔除确认句**，
四处都要在触发前读到同样的规则。这里只生成文本，不改任何结算；
格子详情与篡改预览共用同一份，避免「面板说一套、实际做一套」。
"""

from __future__ import annotations

from ..i18n import get_language, tr
from ..materials.plants import PlantDef, plant_def_for


def _amount_text(channel: str, release) -> str:
    if channel == "liquid" and release.liquid:
        return tr("{name} {n} 单位", name=tr(release.liquid), n=release.amount)
    if channel == "gas" and release.gas:
        return tr("{name} {n} 单位", name=tr(release.gas), n=release.amount)
    if channel == "ignite" and release.ignite:
        return tr("点燃最多 {n} 格", n=release.ignite)
    if channel == "electric" and release.electric:
        return tr("放出 ≤{n} 格、1 回合的静电场", n=release.electric)
    if channel == "sound" and release.sound:
        return tr("{n} 格的响声", n=release.sound)
    if channel == "integrity" and release.integrity:
        return tr("刮掉最多 3 格地形各 {n} 点耐久", n=release.integrity)
    if channel == "push_gas" and release.push_gas:
        return tr("把本格 {n} 单位气体推向朝向邻格", n=release.push_gas)
    if channel == "portent" and release.portent:
        return tr("把触发者缠住 1 回合")
    return ""


def release_summary(definition: PlantDef) -> str:
    """一句「会被放出什么」（没有释出配方时返回空串）。"""
    release = definition.release
    if release is None:
        return ""
    parts = [
        _amount_text(channel, release)
        for channel in ("liquid", "gas", "push_gas", "ignite", "electric", "sound",
                        "integrity", "portent")
    ]
    parts = [part for part in parts if part]
    # 分隔符随语言走：英文面板里不能残留中文顿号（i18n 覆盖率会查）。
    return ("，" if get_language() == "zh" else ", ").join(parts)


def plant_lines(definition: PlantDef, *, depleted: bool = False) -> list[str]:
    """格子详情里的常驻／触发说明（每项一行，全部是公开信息）。"""
    lines: list[str] = []
    if definition.move_penalty:
        if definition.move_penalty_radius >= 1:
            lines.append(tr("进入：本格与相邻一圈 +{v} 世界回合", v=_fmt(definition.move_penalty)))
        else:
            lines.append(tr("进入：本格 +{v} 世界回合", v=_fmt(definition.move_penalty)))
    if definition.step_quiet:
        scope = tr("相邻一圈") if definition.step_quiet_radius >= 1 else tr("本格")
        suffix = tr("（本格有光时失效）") if definition.step_quiet_dark else ""
        lines.append(tr("脚步：{scope}内声径 −{n}{suffix}", scope=scope,
                        n=definition.step_quiet, suffix=suffix))
    if definition.conductive:
        lines.append(tr("常驻：本格是可导电介质（自己不发电）"))
    if definition.absorb_gas:
        lines.append(tr("常驻：每回合吸 1 单位{names}，共 {n}",
                        names="／".join(tr(name) for name in definition.absorb_gas),
                        n=definition.absorb_gas_budget))
    if definition.absorb_liquid:
        lines.append(tr("常驻：每回合吸 1 单位{names}，共 {n}",
                        names="／".join(tr(name) for name in definition.absorb_liquid),
                        n=definition.absorb_liquid_budget))
    if definition.push_gas_budget:
        lines.append(tr("常驻：每回合把本格 1 单位气体按朝向推走，共 {n}",
                        n=definition.push_gas_budget))
    if definition.purify_budget:
        lines.append(tr("常驻：每回合把附近一项可洗征兆缩短 1 回合，共 {n}",
                        n=definition.purify_budget))
    if definition.sight_bonus_delta:
        lines.append(tr("常驻：本格与相邻一圈的照明视距加值 {v}",
                        v=_fmt_signed(definition.sight_bonus_delta)))
    if definition.gas_flow_divisor > 1:
        lines.append(tr("常驻：本格向外扩散的气体预算 ÷{n}", n=definition.gas_flow_divisor))
    release = definition.release
    if release is not None:
        summary = release_summary(definition)
        if release.allows("trample"):
            lines.append(tr("踩踏：踩碎会释出 {detail}", detail=summary))
        if release.allows("uproot"):
            lines.append(tr("拔除：拔起会释出 {detail}", detail=summary))
        if release.allows("both"):
            lines.append(tr("一次用尽：踩与拔共用同一次释出"))
    if depleted:
        lines.append(tr("状态：已经用尽（空壳）"))
    return lines


def uproot_warning(definition: PlantDef) -> str:
    """拔除确认句里的那半句（没有释出配方时为空串）。"""
    release = definition.release
    if release is None or not release.allows("uproot"):
        return ""
    return tr("，拔起会释出 {detail}（落点在这株脚下，不是你的脚下）",
              detail=release_summary(definition))


def plant_lines_for_code(code: int, *, depleted: bool = False) -> list[str]:
    if not code:
        return []
    return plant_lines(plant_def_for(code), depleted=depleted)


def _fmt(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text


def _fmt_signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)
