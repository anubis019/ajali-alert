"""
Matches free text (an incident description, or a follow-up question typed
by the citizen) against the local first-aid knowledge base.

Deliberately simple keyword-overlap scoring rather than an embedding model
or an LLM call: it's fast, has zero external dependencies, behaves the same
offline as online, and every match it can produce traces back to a specific
vetted KB entry - there's no risk of it inventing a step under pressure.

If you later want an LLM in the loop, the natural seam is `rephrase_hook`
below: point it at a completion call that takes the *already-matched* KB
steps and rephrases/expands them for tone, without ever asking the model to
originate medical steps itself.
"""
import re
from typing import List, Optional

from first_aid_kb import all_topics

_WORD_RE = re.compile(r"[a-z']+")


def _tokenize(text: str) -> set:
    return set(_WORD_RE.findall(text.lower()))


def match_topics(query: str, type_code: Optional[str] = None, limit: int = 3) -> List[dict]:
    """Return up to `limit` KB topics ranked by keyword overlap with `query`.

    If nothing scores above zero, falls back to the topics tagged for the
    given incident type (so there's always *something* useful to show),
    or an empty list if there's no type either.
    """
    tokens = _tokenize(query or "")
    scored = []
    for topic in all_topics():
        score = 0
        for kw in topic["keywords"]:
            kw_tokens = _tokenize(kw)
            if not kw_tokens:
                continue
            if kw_tokens.issubset(tokens):
                score += 2 * len(kw_tokens)  # longer phrase match = more specific = weighted higher
            elif kw_tokens & tokens:
                score += 1
        if type_code and type_code in topic["types"]:
            score += 0.5  # small nudge for type relevance, doesn't dominate keyword hits
        if score > 0:
            scored.append((score, topic))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [t for _, t in scored[:limit]]

    if not results and type_code:
        results = [t for t in all_topics() if type_code in t["types"]][:limit]

    return results


def rephrase_hook(topics: List[dict], original_query: str) -> List[dict]:
    """No-op by default. Swap this out to post-process matched topics through
    an LLM for phrasing/expansion - keep it constrained to rewording the
    `steps`/`warnings` already present, never adding new medical content."""
    return topics
