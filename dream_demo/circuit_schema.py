"""Pure validation and coordinate transforms for named circuit boards."""
from copy import deepcopy

INPUTS = {"toggle", "pulse", "step", "plate", "cube", "timer", "sensor"}
OPERATORS = INPUTS | {"and", "or", "not", "sequence", "output"}


def validate_board(board: dict, width: int, height: int) -> list[str]:
    nodes = board["nodes"]
    occupied = set()
    for key, node in nodes.items():
        pos = tuple(node["pos"])
        if len(pos) != 2 or not (0 <= pos[0] < width and 0 <= pos[1] < height):
            raise ValueError(f"Circuit {key}: position outside board")
        if pos in occupied or node["op"] not in OPERATORS:
            raise ValueError(f"Circuit {key}: duplicate position or unknown operator")
        occupied.add(pos)
        refs = node.get("inputs", [])
        if any(ref not in nodes for ref in refs) or len(refs) != len(set(refs)):
            raise ValueError(f"Circuit {key}: invalid input ports")
        if node["op"] in {"not", "output"} and len(refs) != 1:
            raise ValueError(f"Circuit {key}: requires one input")
        if node["op"] in {"and", "or", "sequence"} and not refs:
            raise ValueError(f"Circuit {key}: missing inputs")
        if node["op"] == "timer" and not (0 < node.get("window", 1) <= node.get("period", 8)):
            raise ValueError(f"Circuit {key}: invalid clock")
        if node.get("phase_input") and node["phase_input"] not in refs:
            raise ValueError(f"Circuit {key}: phase control must be an input")
        if node["op"] == "sequence" and any(ref not in refs for ref in node["order"]):
            raise ValueError(f"Circuit {key}: invalid sequence")
    pending, order = set(nodes), []
    while pending:
        ready = sorted(key for key in pending if all(ref in order for ref in nodes[key].get("inputs", [])))
        if not ready:
            raise ValueError("Circuit contains a combinational cycle")
        order.extend(ready)
        pending.difference_update(ready)
    edges = set()
    for net in board["nets"]:
        a, b = net["from"], net["to"]
        path = [tuple(p) for p in net["path"]]
        if a not in nodes or b not in nodes or (a, b) in edges:
            raise ValueError("Circuit has invalid or duplicate net")
        if not path or path[0] != tuple(nodes[a]["pos"]) or path[-1] != tuple(nodes[b]["pos"]):
            raise ValueError("Circuit trace does not reach its ports")
        for x, y in path:
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError("Circuit trace outside board")
        if any(abs(a[0]-b[0]) + abs(a[1]-b[1]) != 1 for a, b in zip(path, path[1:])):
            raise ValueError("Circuit trace is not continuous")
        # A trace may cross another trace, but must not pass through another component.
        if any(p in occupied for p in path[1:-1]):
            raise ValueError("Circuit trace passes through an unrelated component")
        edges.add((a, b))
    expected = {(ref, key) for key, node in nodes.items() for ref in node.get("inputs", [])}
    if edges != expected:
        raise ValueError("Circuit wiring does not match named input ports")
    return order


def transform_board(board: dict, transform) -> dict:
    board = deepcopy(board)
    for node in board["nodes"].values():
        node["pos"] = list(transform(*node["pos"]))
    for net in board["nets"]:
        net["path"] = [list(transform(*p)) for p in net["path"]]
    return board

