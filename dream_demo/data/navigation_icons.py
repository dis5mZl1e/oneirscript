"""Navigation identities shared by the terminal and browser presentations."""
NAVIGATION_SYMBOLS = {'actions': '✔', 'inventory': '▣', 'equipment': '▼',
                      'portents': '◈', 'environment': '⌖', 'tasks': '☷', 'catalog': '◉'}
NAVIGATION_ASCII = {'actions': '>', 'inventory': '#', 'equipment': '^',
                    'portents': '@', 'environment': '+', 'tasks': '=', 'catalog': '?'}


def navigation_icon_key(key):
    return 'nav.catalog' if key == 'environment' else 'nav.' + key
