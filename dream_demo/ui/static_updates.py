"""Avoid relayout when a caller submits unchanged static text."""
from rich.text import Text


def _text_key(content):
    return (Text, content.plain, tuple(content.spans), content.style,
            content.justify, content.overflow, content.no_wrap,
            content.end, content.tab_size)


def update_static_if_changed(widget, content) -> bool:
    """Update text, retaining formatting, mutations, and external writes."""
    if type(content) is Text:
        key = _text_key(content)
    elif type(content) is str:
        key = (str, content)
    else:
        widget.update(content)
        widget._unchanged_text_snapshot = None
        return True
    previous = getattr(widget, "_unchanged_text_snapshot", None)
    if (previous is not None and previous[0] is widget._content
            and previous[1] == key):
        # A retained model may have repaired an externally mutated published
        # Text. Its healthy signature still matches the old snapshot, but the
        # actual widget must be repaired too. The shared-object path already
        # validated current content when constructing key above.
        current = widget._content
        if content is current or type(current) is str:
            return False
        if type(current) is Text and _text_key(current) == key:
            return False
    widget.update(content)
    widget._unchanged_text_snapshot = (widget._content, key)
    return True
