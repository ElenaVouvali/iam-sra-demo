"""Input bounds and errors shared by current interviews."""
from .settings import MAX_INPUT_BYTES

class AssessmentError(ValueError):
    def __init__(self, message, code="input"):
        super().__init__(message)
        self.code=code


def check_input(text):
    from .privacy import require_clean
    require_clean(text)
    if not text.strip() or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise AssessmentError(f"Enter 1–{MAX_INPUT_BYTES} UTF-8 bytes; input is never truncated.")
