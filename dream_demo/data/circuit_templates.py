"""PCB-style puzzle boards: named ports, continuous traces and explicit crossings."""
from collections import deque


def component(x, y, op, label, wall="", inputs=(), **extra):
    return {"pos": [x, y], "op": op, "label": label, "wall": wall,
            "inputs": list(inputs), **extra}


def connect_board(board, width, height):
    """Route each net around other components; intersections are insulated nets."""
    nodes = board["nodes"]
    occupied = {tuple(n["pos"]) for n in nodes.values()}
    nets = []
    for target, node in nodes.items():
        for source in node.get("inputs", []):
            start, end = tuple(nodes[source]["pos"]), tuple(node["pos"])
            parents = {start: None}
            queue = deque([start])
            while queue and end not in parents:
                x, y = queue.popleft()
                for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                    p = (x+dx, y+dy)
                    if not (1 <= p[0] < width-1 and 1 <= p[1] < height-1):
                        continue
                    if p in parents or (p in occupied and p != end):
                        continue
                    parents[p] = (x, y)
                    queue.append(p)
            if end not in parents:
                raise ValueError("Unable to route circuit net")
            path, p = [], end
            while p is not None:
                path.append(list(p))
                p = parents[p]
            nets.append({"from": source, "to": target, "path": path[::-1]})
    board["nets"] = nets
    return board


def toy_board(depth):
    width, height = 27, 17
    if depth == 1:
        nodes = {
            "a": component(4, 3, "toggle", "左灯开关", "机关石台"),
            "b": component(4, 7, "toggle", "中灯开关", "机关石台"),
            "c": component(4, 11, "toggle", "右灯开关", "机关石台"),
            "ab": component(10, 5, "and", "双灯合辙", "合辙枢", ("a", "b")),
            "nc": component(10, 11, "not", "熄灯接线", "接线枢", ("c",)),
            "ready": component(16, 7, "and", "校验合辙", "合辙枢", ("ab", "nc")),
            "door": component(21, 7, "output", "记忆之门", "机关门", ("ready",), latch=True),
        }
    elif depth == 2:
        nodes = {
            "phase": component(4, 11, "toggle", "调相开关", "机关石台"),
            "clock_a": component(6, 3, "timer", "左摆轮", "定时摆轮", period=8, window=2),
            "clock_b": component(14, 3, "timer", "右摆轮", "定时摆轮", ("phase",), period=8, window=2, phase=4, phase_input="phase", on_phase=0),
            "plate": component(10, 11, "plate", "同步压板"),
            "ready": component(16, 7, "and", "同步合辙", "合辙枢", ("clock_a", "clock_b", "plate")),
            "door": component(21, 7, "output", "记忆之门", "机关门", ("ready",), latch=True),
        }
    else:
        nodes = {
            "a": component(4, 3, "step", "低音压板"),
            "b": component(4, 8, "step", "中音压板"),
            "c": component(4, 13, "step", "高音压板"),
            "arm": component(10, 3, "toggle", "上弦开关", "机关石台"),
            "seq": component(12, 9, "sequence", "音序接线", "接线枢", ("a", "b", "c"), order=["a", "c", "b", "c"]),
            "ready": component(17, 7, "and", "音序合辙", "合辙枢", ("arm", "seq")),
            "door": component(21, 7, "output", "记忆之门", "机关门", ("ready",), latch=True),
        }
    board = connect_board({"id": f"toy_{depth}", "nodes": nodes, "completion": "door"}, width, height)
    # The gate is the only passage into the right compartment; the keeper can
    # be approached on the input side for clues before solving the puzzle.
    pattern = [["#" if x in (0, width-1) or y in (0, height-1) or x == 21 else "."
                for x in range(width)] for y in range(height)]
    return ["".join(row) for row in pattern], board, (2, 14), (13, 14)


def vault_board(kind):
    from .advanced_circuit_vaults import KINDS, advanced_board
    if kind in KINDS:
        return advanced_board(kind)
    if kind not in {"dual", "relay", "timer", "selector", "sensor", "trap", "compound"}:
        raise ValueError(f"Unknown circuit template: {kind}")
    width, height = 15, 11
    n = {
        "a": component(3, 3, "toggle", "主控开关", "机关石台"),
        "b": component(3, 7, "plate", "辅助压板"),
        "gate": component(7, 5, "and", "双源合辙", "合辙枢", ("a", "b")),
        "door": component(11, 5, "output", "通路门", "机关门", ("gate",), latch=True),
    }
    if kind == "relay":
        n["gate"] = component(7, 5, "or", "双路分流", "分流枢", ("a", "b"))
    elif kind == "timer":
        n["b"] = component(3, 7, "timer", "定时摆轮", "定时摆轮", period=8, window=2)
    elif kind == "selector":
        n["b"] = component(7, 8, "not", "反相接线", "接线枢", ("a",))
        n["gate"] = component(7, 3, "or", "分路接线", "分流枢", ("a",))
        n["door"].update(inputs=["gate"], latch=False)
        n["valve"] = component(11, 8, "output", "备用灌注阀", "灌注阀", ("b",))
    elif kind == "sensor":
        n["a"] = component(3, 3, "sensor", "感应符文墙", "感应符文墙")
        n["b"] = component(3, 7, "toggle", "警报使能", "机关石台", initial=True)
        n["door"] = component(11, 5, "output", "共鸣报警器", "共鸣报警器", ("gate",))
    elif kind == "trap":
        n["a"] = component(3, 3, "plate", "陷阱压板")
        n["b"] = component(3, 7, "toggle", "陷阱使能", "机关石台", initial=True)
        n["door"] = component(11, 5, "output", "陷阱石台", "陷阱石台", ("gate",))
    elif kind == "compound":
        n["c"] = component(3, 9, "toggle", "旁路开关", "机关石台")
        n["merge"] = component(9, 8, "or", "旁路分流", "分流枢", ("c", "gate"))
        n["door"]["inputs"] = ["merge"]
    board = connect_board({"id": kind, "nodes": n}, width, height)
    rows = [["#" if x in (0, width-1) or y in (0, height-1) else "." for x in range(width)] for y in range(height)]
    # One controlled passage into a reward compartment; the outer dream remains escapable.
    if kind not in {"sensor", "trap"}:
        for y in range(1, height-1):
            rows[y][11] = "#"
    from ..mapgen.vaults.base import VAULT_CHAR_KINDS_INVERTED
    for node in n.values():
        x, y = node["pos"]
        rows[y][x] = VAULT_CHAR_KINDS_INVERTED[node["wall"]] if node["wall"] else "p"
    rows[height-1][2] = "@"
    rows[3][13] = "S"
    return ["".join(row) for row in rows], board
