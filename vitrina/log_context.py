import contextvars
import logging

# Request-scoped fields rendered into log lines, with the value used when a
# field is unavailable (no request, anonymous user, background task, ...).
# Add a key here, populate it from middleware/call sites, and reference it in
# the LOGGING formatter to surface a new detail.
LOG_CONTEXT_DEFAULTS = {
    "user_id": "anonymous",
}

_log_context: contextvars.ContextVar[dict] = contextvars.ContextVar("vitrina_log_context")


def set_log_context(**fields):
    current = dict(get_log_context())
    current.update(fields)
    return _log_context.set(current)


def get_log_context() -> dict:
    try:
        return _log_context.get()
    except LookupError:
        return {}


def reset_log_context(token) -> None:
    _log_context.reset(token)


class LogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = get_log_context()
        for field, default in LOG_CONTEXT_DEFAULTS.items():
            setattr(record, field, context.get(field, default))
        return True
