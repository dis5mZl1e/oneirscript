"""Finite runtime contracts; catalog remains the authority for prose and access."""
from .catalog import by_category

FORMS = {
    'sound': ('point','self','point','point','point','point'),
    'light': ('point','point','self','point','direction','point'),
    'terrain': ('point','direction','point','point','point','point'),
    'projectile': ('self','point','self','direction','direction','self'),
    'circuit': ('pair','self','point','point','point','point'),
    'realm': ('self','point','self','self','self','pair'),
}

def consumable_item_rows():
    return {e['id']: {'effect':'expansion_consumable', 'power':1,
                     'consumable_uses':1, 'max_stack':1,
                     'consumable_use':{'form':FORMS[e['theme']][int(e['id'][-2:])-1],
                                       'range':6, 'kind':'any'}}
            for e in by_category('consumable')}
