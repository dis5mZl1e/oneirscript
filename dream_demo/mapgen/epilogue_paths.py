"""Connect story anchors with minimal carving, never cut the outer boundary."""
from collections import deque


def reachable(cells, start):
    width,height=len(cells[0]),len(cells)
    seen={start};queue=deque([start])
    while queue:
        x,y=queue.popleft()
        for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            a,b=p
            if 0<=a<width and 0<=b<height and p not in seen and not cells[b][a].solid:
                seen.add(p);queue.append(p)
    return seen


def connect_anchors(cells, info):
    from ..core.entities import Cell
    anchors=[info['spawn'],*info['events'].values(),*info.get('accept',()),
             *((x,y) for x,y,_ in info.get('enemies',())),*info.get('loot_spots',())]
    if info.get('npc'):anchors.append(info['npc'])
    anchors.extend((entry['x'],entry['y']) for entry in info.get('scene_events',()))
    anchors.extend(pos for pos,_ in info.get('structure_npcs',()))
    for x,y in anchors:
        if cells[y][x].wall_kind=='意识边界':
            raise ValueError('Story anchor crosses the outer boundary')
        cells[y][x]=Cell()
    connected=reachable(cells,info['spawn'])
    width,height=len(cells[0]),len(cells)
    for target in anchors:
        if target in connected:continue
        queue=deque([target]);cost={target:0};parents={target:None}
        join=None
        while queue:
            p=queue.popleft()
            if p in connected:join=p;break
            x,y=p
            for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                a,b=q
                if not (0<a<width-1 and 0<b<height-1) or cells[b][a].wall_kind=='意识边界':continue
                step=int(cells[b][a].solid);value=cost[p]+step
                if value>=cost.get(q,10**9):continue
                cost[q]=value;parents[q]=p
                (queue.append if step else queue.appendleft)(q)
        if join is None:raise ValueError('Unreachable epilogue anchor')
        while join is not None:
            x,y=join
            if cells[y][x].solid:cells[y][x]=Cell()
            join=parents[join]
        connected=reachable(cells,info['spawn'])
    return connected
