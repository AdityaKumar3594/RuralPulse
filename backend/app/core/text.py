"""Text helpers shared by retrieval and ranking, so both tokenize identically."""

import unicodedata

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "for",
        "and",
        "or",
        "of",
        "in",
        "on",
        "to",
        "me",
        "my",
        "i",
        "we",
        "you",
        "how",
        "can",
        "what",
        "is",
        "are",
        "do",
        "does",
        "want",
        "like",
        "with",
    ]
)
MAX_TOKENS = 8


def tokenize(query: str | None) -> list[str]:
    """Words only (letters, combining marks, digits), lower-cased. Safe to embed in a tsquery."""
    tokens: list[str] = []
    for raw in (query or "").split():
        word = "".join(ch for ch in raw if unicodedata.category(ch)[0] in "LMN").casefold()
        if word:
            tokens.append(word)
    meaningful = [t for t in tokens if t not in STOPWORDS] or tokens
    return list(dict.fromkeys(meaningful))[:MAX_TOKENS]
