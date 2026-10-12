"""Retrieve original citizen wording without rewriting it."""
import re
from .assessment import check_input

def passages(text):
    check_input(text)
    # Formatting inside a passage is retained. This is segmentation, not normalization.
    chunks=[part.strip() for part in re.split(r'(?<=[.!?])\s+|\n\s*\n',text) if part.strip()]
    return {f"p{i:03d}":part for i,part in enumerate(chunks,1)}


def original_quote(text,quotation):
    """Match whitespace-only formatting differences and return untouched source text.

    PDF line wrapping may be rendered as spaces by the model. Words, spelling,
    case, punctuation and passage boundaries must still match the citizen.
    """
    if not isinstance(quotation,str) or not quotation.strip():return None
    if quotation in text:return quotation
    pattern=r'\s+'.join(re.escape(word) for word in quotation.split())
    match=re.search(pattern,text)
    return match.group(0) if match else None
