"""InputMixin 包（自 ui/input.py 拆分，纯搬家见 docs/megafile-refactor-plan.md）。"""

from ..aiming import AimingMixin
from .context_actions import ACTION_SOUNDS, ATTACK_CONFIRMATION_SECONDS, ContextActionsMixin
from .key_routing import KeyRoutingMixin
from .mouse_routing import MouseRoutingMixin


class InputMixin(KeyRoutingMixin, MouseRoutingMixin, ContextActionsMixin, AimingMixin):
    """键位/鼠标输入混合层：组合三个子 mixin，对外接口与拆分前一致。"""


__all__ = ["InputMixin", "KeyRoutingMixin", "MouseRoutingMixin", "ContextActionsMixin",
           "ATTACK_CONFIRMATION_SECONDS", "ACTION_SOUNDS"]
