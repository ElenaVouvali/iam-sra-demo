"""Input bounds and errors shared by current interviews."""
from .settings import MAX_INPUT_BYTES

class AssessmentError(ValueError):
    def __init__(self, message, code="input", field=None):
        super().__init__(message)
        self.code=code
        # Safe structural path only; never attach rejected values here.
        self.field=field


def check_input(text):
    from .privacy import require_clean
    require_clean(text)
    if not text.strip() or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise AssessmentError(f"Enter 1–{MAX_INPUT_BYTES} UTF-8 bytes; input is never truncated.")
