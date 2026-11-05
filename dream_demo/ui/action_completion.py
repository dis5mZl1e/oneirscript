"""Run serial feedback immediately or after an owner publication on the UI loop."""
from concurrent.futures import Future


def after_action(app, result, continuation):
    if isinstance(result, Future):
        return app.session.then(result, continuation)
    return continuation(result)
