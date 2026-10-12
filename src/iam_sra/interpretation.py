"""Immutable citizen passages and stable assessment fingerprints."""
import hashlib
import json
from pydantic import BaseModel, ConfigDict

class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    id: str
    text: str
    context: str
    source: str  # citizen_original, citizen_correction, citizen_choice, question
    question_id: str | None = None


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
