from __future__ import annotations

from typing import Dict, List, Tuple


def build_citation_map(documents: List[dict]) -> Tuple[Dict[str, dict], List[str]]:
    keys: Dict[str, dict] = {}
    ordered_keys: List[str] = []
    for idx, doc in enumerate(documents, start=1):
        key = f"doc{idx}"
        keys[key] = doc
        ordered_keys.append(key)
    return keys, ordered_keys


def format_citations(citation_keys: List[str], citation_map: Dict[str, dict]) -> List[dict]:
    results = []
    for key in citation_keys:
        doc = citation_map.get(key)
        if not doc:
            continue
        results.append(
            {
                "key": key,
                "title": doc.get("title"),
                "source_url": doc.get("source_url"),
            }
        )
    return results
