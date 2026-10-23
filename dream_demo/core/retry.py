"""以原开局选择创建全新一局，绝不复制本局成长或已消耗资源。"""
from __future__ import annotations
from copy import deepcopy


def retry_state(previous, *, seed, tutorial=False):
    from . import GameState
    choices = previous.run_start_choices
    if not previous.run_over or not choices:
        raise ValueError("No completed run with recorded starting choices")
    return GameState.new(seed=seed, tutorial=tutorial,
                         width=int(choices.get("width", 60)),
                         height=int(choices.get("height", 60)),
                         run_options=deepcopy(choices.get("run_options", {})),
                         dream_type=deepcopy(choices.get("dream_type")),
                         starting_memory=choices.get("starting_memory"))
