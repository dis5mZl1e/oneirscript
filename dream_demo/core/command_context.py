"""Runtime world identity and action context for owner command boundaries.

The token is generated once for a world, survives faithful deepcopy/pickle,
and is deliberately excluded from persistent saves. A new/replayed world gets
its own token; layer names and process-local object addresses cannot identify it.
"""
from uuid import uuid4


def command_context_token(state) -> int:
    token = getattr(state, '_command_context_token', None)
    if type(token) is not int or token <= 0:
        token = uuid4().int
        state._command_context_token = token
    return token


def capture_command_context(state) -> tuple[int, int, int]:
    return command_context_token(state), state.action_seq, state.time


def matches_command_context(state, expected) -> bool:
    return (type(expected) is tuple and len(expected) == 3
            and all(type(value) is int for value in expected)
            and expected[0] > 0
            and expected == capture_command_context(state))
