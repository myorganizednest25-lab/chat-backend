from __future__ import annotations

from typing import Iterable, Optional, Tuple

from rapidfuzz import fuzz, process


def _normalize(value: str) -> str:
    return value.lower().strip() if value else ""


def best_fuzzy_match(
    query: str, choices: Iterable[str], score_cutoff: int = 70
) -> Optional[Tuple[str, float]]:
    if not query or not choices:
        return None
    original_choices = list(choices)
    if not original_choices:
        return None

    normalized_choices = [_normalize(c) for c in original_choices]
    normalized_query = _normalize(query)

    match = process.extractOne(
        normalized_query,
        normalized_choices,
        scorer=fuzz.partial_ratio,
        score_cutoff=score_cutoff,
    )
    if not match:
        return None
    _, score, index = match
    original_choice = original_choices[index]
    return original_choice, float(score)
