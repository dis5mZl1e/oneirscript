"""Avoid relayout when a caller submits unchanged static text."""
from rich.text import Text


def update_static_if_changed(widget, content) -> bool:
    """Update text, retaining formatting, mutations, and external writes."""
    if type(content) is Text:
        key = (Text, content.plain, tuple(content.spans), content.style,
               content.justify, content.overflow, content.no_wrap,
               content.end, content.tab_size)
    elif type(content) is str:
        key = (str, content)
    else:
        widget.update(content)
        widget._unchanged_text_snapshot = None
        return True
    previous = getattr(widget, "_unchanged_text_snapshot", None)
    if (previous is not None and previous[0] is widget._content
            and previous[1] == key):
        return False
    widget.update(content)
    widget._unchanged_text_snapshot = (widget._content, key)
    return True
