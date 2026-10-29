# -*- coding: utf-8 -*-
"""右栏标题行的锁定图标（2026-10-27 玩家需求）。

玩家要求：右侧面板六个页签正上方的第一行标题（#status 第 1 行，层信息行）
的最右空白处放一个可点击的锁图标——默认是关闭的锁，点一下变成打开的锁；
它实时锁定「当前所在的右侧框界面」（panel_mode + 子页自标签 + 详情引用），
行动/瞄准/对话等自动换页不能把它变回默认页。

锁定语义完全复用 ~ 键的 panel_locked：本模块只负责画图标和给出点击列区，
真正的开关仍是 app.toggle_cursor_lock()（快照恢复见 sidebar_workspaces）。

锁使用随包的单色轮廓字形。保留原码位的两列宽，不附加会让部分终端
改按单列排版的 VS15，保证标题末尾的显示位置和点击区域一致。

字形由随包 DreamStrataLockOutline.ttf 提供（wezterm_setup 注册
assume_emoji_presentation = true，优先于系统彩色 emoji），所以裸码位
\U0001F512 / \U0001F513 就是最终口径，不要加 VS15。

本模块不依赖 Textual/DreamApp，纯 rich Text 操作，便于单测：
stamp_title_lock 把标题行截到 width-2 列、补空格，再把锁字形贴到最右
2 列，返回点击命中的列区 (width-2, width)。
"""
from __future__ import annotations

from rich.cells import cell_len
from rich.text import Text

# 未锁定：关闭的锁（点击 = 锁定当前右栏子界面）。
UNLOCKED_GLYPH = "\U0001F512"
# 已锁定：打开的锁（点击 = 解除锁定）。
LOCKED_GLYPH = "\U0001F513"

# 两种状态用不同的暖色：未锁定的暖灰低调，锁定的暖黄醒目；
# 两者对纸感封面底 ZONE_COVER #3a3120 的对比度都 >= 6.8（见验收测试）。
UNLOCKED_STYLE = "#c7bda4"
LOCKED_STYLE = "#ffd166"

# 至少 6 列才放得下「标题若干列 + 2 列锁」；更窄时不画图标（返回 None）。
MIN_TITLE_LOCK_WIDTH = 6


def lock_glyph(locked: bool) -> str:
    """返回当前锁定状态对应的锁字形（cell_len == 2）。"""
    return LOCKED_GLYPH if locked else UNLOCKED_GLYPH


def lock_style(locked: bool) -> str:
    """返回锁字形样式：锁定暖黄、未锁定暖灰（都在纸感底色上够亮）。"""
    return LOCKED_STYLE if locked else UNLOCKED_STYLE


def stamp_title_lock(line: Text, *, locked: bool, width: int) -> tuple[int, int] | None:
    """把锁图标贴到标题行最右 2 列，返回点击命中的列区。

    - line 原地修改：先 truncate(width-2, overflow='ellipsis')，
      再补空格到 width-2 列，最后追加锁字形（样式见 lock_style）。
    - width 是这一行可用的终端列数；返回 (width-2, width)。
    - width < MIN_TITLE_LOCK_WIDTH 时不改行、不加图标，返回 None。

    调用方（_refresh_world_view）每次刷新都重新调用：宽度和 panel_locked
    都会变，命中列区不能缓存。
    """
    if width < MIN_TITLE_LOCK_WIDTH:
        return None
    glyph = lock_glyph(locked)
    glyph_width = cell_len(glyph)
    if glyph_width <= 0 or width <= glyph_width:
        return None
    start = width - glyph_width
    # 标题太长：截到锁左边并在末尾用省略号（第 1 行的左侧仍是层详情入口）。
    line.truncate(start, overflow="ellipsis")
    # 标题偏短：用空格补到锁的起点，保证锁始终贴最右 2 列。
    padding = start - cell_len(line.plain)
    if padding > 0:
        line.append(" " * padding)
    line.append(glyph, style=lock_style(locked))
    return (start, width)
