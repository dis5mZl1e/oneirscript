"""Playable vertical slice for Oneirscript."""

from .core import GameState
from .core.content import ensure_content_validated
from .persistence import GameSession

# 内容表加载即校验（NPC／事件重构方案 §2.1）：坏定义在导入期就炸，不进游戏也不进总表。
ensure_content_validated()

__all__ = ["GameState", "GameSession"]
