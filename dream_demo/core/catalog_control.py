"""Catalog settings executed by the session owner, using its save manager."""
from .entities import ActionResult
from ..catalog_registry import CatalogCategory, build_catalog_definitions
from ..i18n import tr


def apply_catalog_control(session, operation=None, *extra):
    if extra or type(operation) is not str or operation not in ('clear', 'unlock'):
        return ActionResult(False)
    if not session.persistence_enabled:
        return ActionResult(False, tr('教程中不修改正式记录。'))
    manager, state = session.manager, session.state
    if operation == 'clear':
        changed = bool(state.catalog)
        state.catalog = {}
        try:
            if manager.catalog_file.exists():
                manager.catalog_file.unlink()
        except OSError:
            pass
        for slot in range(1, manager.SLOT_COUNT + 1):
            slot_manager = manager.for_slot(slot)
            if not (slot_manager.primary.exists() or slot_manager.backup.exists()):
                continue
            try:
                slot_state = slot_manager.load()
                slot_state.catalog = {}
                slot_manager.save(slot_state)
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return ActionResult(True, tr('历史统计已删除。'), {'state_changed': changed})
    merged = manager.merge_catalogs(state.catalog, manager.load_catalog())
    unlocked = 0
    for definition in build_catalog_definitions().values():
        entry = merged.setdefault(definition.catalog_id, {
            'name': definition.name, 'category': definition.category.value,
            'encounters': 0, 'interactions': 0, 'kills': 0,
            'drops_seen': [], 'details': []})
        counter = ('encounters' if definition.category is CatalogCategory.CONSCIOUSNESS
                   else 'interactions')
        if int(entry.get(counter, 0)) == 0:
            entry[counter] = 1
            unlocked += 1
    changed = merged != state.catalog
    manager.save_catalog(merged)
    state.catalog = merged
    return ActionResult(True, tr('图鉴已全部解锁（新标记 {n} 条）。').format(n=unlocked),
                        {'state_changed': changed})
