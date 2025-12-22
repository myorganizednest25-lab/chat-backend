from __future__ import annotations

from typing import Iterable, Optional, Tuple

from rapidfuzz import fuzz, process


def best_fuzzy_match(
    query: str, choices: Iterable[str], score_cutoff: int = 70
) -> Optional[Tuple[str, float]]:
    if not query or not choices:
        return None
    match = process.extractOne(
        query,
        choices,
        scorer=fuzz.QRatio,
        score_cutoff=score_cutoff,
    )
    if not match:
        return None
    choice, score, _ = match
    return choice, float(score)
