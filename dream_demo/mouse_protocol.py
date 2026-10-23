"""鼠标输入协议（平台中立）：Windows 原生层与 POSIX 适配层共用的同一套语义。

游戏逻辑（ui/input.py 的取物/瞄准/寻路/滚轮缩放等）只消费这里定义的事件
协议，绝不感知平台：

- 事件类型：``MouseDown / MouseUp / MouseMove / MouseScrollUp / MouseScrollDown``
- 按键编号（``button``）：**1=左键、2=中键、3=右键**（Win32 层语义，游戏键位
  即按此写成：左键行动、右键交互列表、中键固定目标）；
- ``ctrl / shift / meta(alt)`` 修饰位、``x/y``（相对坐标）与 ``screen_x/screen_y``
  （绝对坐标）随事件携带；
- 滚轮事件的 ``button`` 恒为 0（Windows 层如此，POSIX 层保持一致）。

两端差异只允许存在于各自的驱动/适配层内，且必须经过
``normalize_to_game_semantics`` 出口对齐后才能进入 ``process_message``。
"""

from __future__ import annotations

from textual import events

# 游戏键位编号（Win32 层语义；XTerm 解析器 `(buttons+1)&3` 产出即此语义）。
BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT = 1, 2, 3

# 两个驱动层各自的产出约定（供审计，不参与运行时）：
#   windows_mouse.native_mouse_events → BUTTONS 掩码映射，恒 1 基；
#   textual XTermParser（POSIX 路径）→ `(buttons+1)&3`，恒 1 基。
# 因此接缝是**恒等校验**：任何非游戏语义的编号都在这里被拦下并归一，
# 未来若接入新的原始驱动（例如直接喂 0 基 SGR 的第三方层），改这里即可。

_PRESS_TYPES = (events.MouseDown, events.MouseUp)


def normalize_to_game_semantics(event: events.MouseEvent) -> events.MouseEvent:
    """把鼠标事件对齐到游戏键位语义；已合规的事件**原样返回**（零拷贝）。

    合规 = 按下/释放事件 button ∈ {1,2,3}；移动事件 button ∈ {0,1,2,3}
    （0 = 无键拖动）；滚轮事件 button 恒 0（与 Windows 层一致）。
    """
    if isinstance(event, _PRESS_TYPES) and event.button not in (BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT):
        # 防御：非 1 基按下编号（0 基 SGR 残留）映射为游戏语义。
        remap = {0: BUTTON_LEFT, 1: BUTTON_MIDDLE, 2: BUTTON_RIGHT}
        target = remap.get(event.button)
        if target is not None:
            return type(event)(
                event.widget,
                event.x,
                event.y,
                event.delta_x,
                event.delta_y,
                target,
                event.shift,
                event.meta,
                event.ctrl,
                screen_x=event.screen_x,
                screen_y=event.screen_y,
                style=event.style,
            )
    return event
