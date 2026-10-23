"""Game-process Alt/Meta decoding; keeps Textual's streaming VT parser intact."""
from enum import Enum
from functools import lru_cache
from string import ascii_letters, digits


@lru_cache(maxsize=1)
def install_alt_sequences():
    # Textual's parser already handles split reads, timeout, CSI, SS3 and paste.
    # Supply its missing Alt letter/number entries instead of splitting batches
    # ourselves. Uppercase O is an SS3 prefix and must not be claimed here.
    from textual._ansi_sequences import ANSI_SEQUENCES_KEYS
    characters = ascii_letters.replace('O', '') + digits
    keys = Enum('GameAltKey', {f'KEY_{ord(c)}': 'alt+'+c.lower() for c in characters})
    for char in characters:
        ANSI_SEQUENCES_KEYS['\x1b'+char] = (keys[f'KEY_{ord(char)}'],)
