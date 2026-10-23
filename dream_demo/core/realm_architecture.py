"""Small architectural variations applied before furniture and authored content."""
from collections import deque
import random


def vary_room(rect, rng, width, height, margin):
    x0,y0,x1,y1 = rect
    dx,dy = rng.randint(-2,2),rng.randint(-2,2)
    return (max(margin,x0+dx),max(margin,y0+dy),
            min(width-margin-1,x1+dx+rng.randint(-1,1)),
            min(height-margin-1,y1+dy+rng.randint(-1,1)))


def add_side_rooms(builder, realm, seed, depth):
    """Branch from existing passages; never dig after material placement."""
    rng = random.Random(seed ^ 0x524F4F4D ^ depth*3571)
    margin = 3 if realm == 'library_palace' else 2
    wanted = rng.randint(2,4)
    planned_tanks={(x,y) for cy in (11,24,37) for y in range(cy-3,cy+4) for x in range(8,15)} if realm=='white_sanatorium' and depth==3 else set()
    for index in range(wanted):
        existing = [(x,y) for y in range(margin+1,builder.height-margin-1)
                    for x in range(margin+1,builder.width-margin-1)
                    if not builder.cells[y][x].solid and (x,y) not in planned_tanks]
        anchors={p:p for p in existing};queue=deque(existing)
        while queue:
            x,y=queue.popleft()
            for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if margin<=p[0]<builder.width-margin and margin<=p[1]<builder.height-margin and p not in anchors:
                    anchors[p]=anchors[(x,y)];queue.append(p)
        candidates = []
        for half,threshold in ((2,18),(1,4)):
            for y in range(margin+half+1,builder.height-margin-half-1,2):
                for x in range(margin+half+1,builder.width-margin-half-1,2):
                    rect = (x-half,y-half,x+half,y+half)
                    if any((xx,yy) in planned_tanks for yy in range(y-half,y+half+1) for xx in range(x-half,x+half+1)):continue
                    if sum(builder.cells[yy][xx].solid for yy in range(y-half,y+half+1)
                           for xx in range(x-half,x+half+1)) < threshold:continue
                    nearest=anchors[(x,y)]
                    ax,ay=nearest
                    passage={(xx,yy) for xx in range(min(x,ax)-1,max(x,ax)+2) for yy in range(y-1,y+2)}
                    passage|={(xx,yy) for xx in range(ax-1,ax+2) for yy in range(min(y,ay)-1,max(y,ay)+2)}
                    if passage & planned_tanks:continue
                    if abs(x-nearest[0])+abs(y-nearest[1])<=12:candidates.append((rect,nearest))
            if candidates:break
        if not candidates:
            raise ValueError(f'{realm}: no site for side room {index+1}/{wanted}')
        rect,anchor = rng.choice(candidates)
        if realm == 'library_palace':
            builder.room('side_reading',rect,'desks',vary=False)
        else:
            builder.room('side_clinic',rect,True,vary=False)
        center = ((rect[0]+rect[2])//2,(rect[1]+rect[3])//2)
        builder.corridor(center,anchor)
    builder.side_room_count = wanted


def reachable(cells, start):
    seen, queue = {start},deque([start])
    w,h = len(cells[0]),len(cells)
    while queue:
        x,y = queue.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            p = x+dx,y+dy
            if (0 <= p[0] < w and 0 <= p[1] < h and p not in seen
                    and (not cells[p[1]][p[0]].solid or cells[p[1]][p[0]].doorway)):
                seen.add(p);queue.append(p)
    return seen


def validate_structure(builder, spawn, exit_pos):
    seen = reachable(builder.cells,spawn)
    if exit_pos not in seen:
        raise ValueError('realm architecture disconnected its exit')
    for room in builder.rooms:
        x0,y0,x1,y1 = room['rect']
        if ((x0+x1)//2,(y0+y1)//2) not in seen:
            raise ValueError('realm architecture disconnected a room')


def ventilation_clearance(cells, reach=3):
    """Open cells that must stay free of walls in front of installed exhaust fans."""
    directions={'北':(0,-1),'东':(1,0),'南':(0,1),'西':(-1,0)}
    reserved=set()
    for y,row in enumerate(cells):
        for x,cell in enumerate(row):
            if not cell.wall_kind.startswith('换气扇·'):
                continue
            direction=cell.wall_kind.rsplit('·',1)[-1]
            dx,dy=directions[direction]
            reserved.update((x+dx*i,y+dy*i) for i in range(1,reach+1))
    return reserved
