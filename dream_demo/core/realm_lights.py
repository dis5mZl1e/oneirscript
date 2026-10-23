"""Shared temporary light ownership, stored with the active realm snapshot."""


def light_key(pos):
    return f'{pos[0]},{pos[1]}'


def borrow_light(state,pos,owner,radius):
    cell=state.cell(*pos)
    leases=state.realm_features.setdefault('temporary_lights',{})
    record=leases.setdefault(light_key(pos),dict(radius=cell.light_radius,enabled=cell.light_on,source=cell.wall_kind,owners={}))
    record['owners'][owner]=radius
    cell.light_radius=max(record['radius'],*record['owners'].values())
    cell.light_on=True
    state._visible_cache=None


def release_light(state,pos,owner):
    leases=state.realm_features.get('temporary_lights',{})
    record=leases.get(light_key(pos))
    if record is None:return
    record['owners'].pop(owner,None)
    cell=state.cell(*pos)
    if cell.light_radius<=0 or cell.wall_kind!=record.get('source',cell.wall_kind):
        leases.pop(light_key(pos),None)
        state._visible_cache=None
        return
    if record['owners']:
        cell.light_radius=max(record['radius'],*record['owners'].values())
    else:
        # A destroyed source must never be recreated by a delayed expiry.
        if cell.light_radius>0:
            cell.light_radius=record['radius'];cell.light_on=record['enabled']
        leases.pop(light_key(pos),None)
    state._visible_cache=None


def cancel_borrowed_light(state,pos):
    record=state.realm_features.get('temporary_lights',{}).pop(light_key(pos),None)
    if record is None:return False
    state.cell(*pos).light_radius=record['radius']
    return True
