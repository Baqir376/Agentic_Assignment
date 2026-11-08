"""
Agent 1a — Symbolic Rule Engine
First line of PII defense using hard-coded regex and dictionary lookups.
Guaranteed detection of structured PII (phones, CNICs, emails, etc.).
"""
import sys
import re
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import ONTOLOGY_DIR, PII_TYPES
from pipeline.state import PipelineState

# ── Regex patterns ────────────────────────────────────────────────────────────

PATTERNS = {
    "PHONE": [
        re.compile(r'\b(0[23][0-9]{9}|\+92[23][0-9]{9})\b'),           # Landlines
        re.compile(r'\b(03\d{2}[-\s]?\d{7}|\+923\d{2}[-\s]?\d{7})\b'),  # Mobile
    ],
    "CNIC": [
        re.compile(r'\b\d{5}-\d{7}-\d\b'),                             # XXXXX-XXXXXXX-X
        re.compile(r'\b\d{13}\b'),                                       # 13 digit block
    ],
    "EMAIL": [
        re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b'),
    ],
    "DATE": [
        re.compile(r'\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/]\d{4}\b'),
        re.compile(r'\b(January|February|March|April|May|June|July|August|September|'
                   r'October|November|December)\s+\d{1,2},?\s+\d{4}\b', re.IGNORECASE),
        re.compile(r'\b\d{4}[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b'),
    ],
    "MED_ID": [
        re.compile(r'\bMRN[-\s]?\d{4,8}\b', re.IGNORECASE),
        re.compile(r'\bMR[-\s]\d{4,8}\b', re.IGNORECASE),
        re.compile(r'\bEMP[-\s]?\d{4,6}\b', re.IGNORECASE),
        re.compile(r'\bCASE[-\s]?\d{3,6}/\d{4}\b', re.IGNORECASE),
        re.compile(r'\bREF[-\s]?\d{4,8}\b', re.IGNORECASE),
    ],
}

# ── Load ontology dictionaries ────────────────────────────────────────────────

def _load_ontology():
    names_path = ONTOLOGY_DIR / "names.json"
    locs_path  = ONTOLOGY_DIR / "locations.json"
    hosp_path  = ONTOLOGY_DIR / "hospitals.json"

    name_set  = set()
    loc_set   = set()
    hosp_set  = set()

    if names_path.exists():
        data = json.loads(names_path.read_text(encoding="utf-8"))
        for lst in data.values():
            name_set.update(lst)

    if locs_path.exists():
        data = json.loads(locs_path.read_text(encoding="utf-8"))
        for lst in data.values():
            if isinstance(lst, list):
                loc_set.update(lst)

    if hosp_path.exists():
        data = json.loads(hosp_path.read_text(encoding="utf-8"))
        hosp_set.update(data.get("hospitals", []))

    return name_set, loc_set, hosp_set


_NAME_SET, _LOC_SET, _HOSP_SET = _load_ontology()

_NAME_ALTS = '|'.join(sorted(_NAME_SET, key=len, reverse=True))
_HON_ALTS = (
    r'(?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Advocate|Justice|Hon\.|Honourable|Honorable|'
    r'Honorable\s+Justice|Honourable\s+Justice|Prof\.)\s+)'
)
_NAME_PATTERN = re.compile(rf'(?:{_HON_ALTS})?(?:{_NAME_ALTS})(?:\s+(?:{_NAME_ALTS})){{0,2}}\b')


# ── Core detection logic ──────────────────────────────────────────────────────

def _find_regex_matches(text: str) -> list[dict]:
    """Run all regex patterns and return list of match dicts."""
    matches = []
    for ptype, pattern_list in PATTERNS.items():
        for pat in pattern_list:
            for m in pat.finditer(text):
                matches.append({
                    "entity": m.group(),
                    "type": ptype,
                    "start": m.start(),
                    "end": m.end(),
                })
    return matches


def _find_dict_matches(text: str) -> list[dict]:
    """Word-boundary dictionary lookup for names, locations, hospitals."""
    matches = []

    # 1. Hospitals (check first — multi-word and specific)
    for hosp in sorted(_HOSP_SET, key=len, reverse=True):
        pattern = re.compile(r'\b' + re.escape(hosp) + r'\b', re.IGNORECASE)
        for m in pattern.finditer(text):
            matches.append({
                "entity": m.group(),
                "type": "HOSPITAL",
                "start": m.start(),
                "end": m.end(),
            })

    # 2. Locations
    for loc in sorted(_LOC_SET, key=len, reverse=True):
        pattern = re.compile(r'\b' + re.escape(loc) + r'\b', re.IGNORECASE)
        for m in pattern.finditer(text):
            matches.append({
                "entity": m.group(),
                "type": "LOCATION",
                "start": m.start(),
                "end": m.end(),
            })

    # 3. Names (Pakistani ontology full/single names with optional honorifics)
    for m in _NAME_PATTERN.finditer(text):
        matches.append({
            "entity": m.group(),
            "type": "PERSON",
            "start": m.start(),
            "end": m.end(),
        })

    return matches


def _resolve_overlaps(matches: list[dict]) -> list[dict]:
    """
    Remove overlapping matches, keeping the longest one (greedy longest).
    Returns list of matches sorted by start position.
    """
    if not matches:
        return []

    # Sort primarily by length descending, then start ascending
    by_len = sorted(matches, key=lambda m: (-(m["end"] - m["start"]), m["start"]))
    selected = []
    occupied: list[tuple[int, int]] = []

    for m in by_len:
        s, e = m["start"], m["end"]
        # Check if overlaps with any already selected interval
        if not any(not (e <= os or s >= oe) for os, oe in occupied):
            selected.append(m)
            occupied.append((s, e))

    return sorted(selected, key=lambda m: m["start"])


def _build_token_maps(text: str, matches: list[dict],
                      existing_map: dict, existing_reverse: dict
                      ) -> tuple[str, dict, dict, dict]:
    """
    Assign [TYPE_N] tokens to each match, replace in text, return updated maps.
    Works from end to start to preserve string offsets.
    """
    pii_token_map = dict(existing_map)
    reverse_map   = dict(existing_reverse)
    pii_counts: dict[str, int] = {}

    # Count existing tokens to continue numbering
    type_counters: dict[str, int] = {}
    for token in reverse_map:
        m = re.match(r'\[([A-Z_]+)_(\d+)\]', token)
        if m:
            ttype, num = m.group(1), int(m.group(2))
            type_counters[ttype] = max(type_counters.get(ttype, 0), num)

    # Sort matches end→start for safe in-place replacement
    ordered = sorted(matches, key=lambda x: x["start"], reverse=True)

    result = text
    for match in ordered:
        entity = match["entity"]
        ptype  = match["type"]

        if entity in pii_token_map:
            # Reuse existing token for repeated mentions
            token = pii_token_map[entity]
        else:
            # Assign new token
            type_key = ptype
            type_counters[type_key] = type_counters.get(type_key, 0) + 1
            token = f"[{type_key}_{type_counters[type_key]}]"

            pii_token_map[entity] = token
            reverse_map[token]    = entity
            pii_counts[ptype]     = pii_counts.get(ptype, 0) + 1

        # Replace in text at recorded position
        result = result[:match["start"]] + token + result[match["end"]:]

    return result, pii_token_map, reverse_map, pii_counts


# ── Public interface ──────────────────────────────────────────────────────────

def run(state: PipelineState) -> PipelineState:
    """Run the symbolic rule engine on state['raw_text']."""
    text = state["raw_text"]

    regex_matches = _find_regex_matches(text)
    dict_matches  = _find_dict_matches(text)
    all_matches   = _resolve_overlaps(regex_matches + dict_matches)

    sanitized, pii_map, rev_map, counts = _build_token_maps(
        text, all_matches,
        state.get("pii_token_map", {}),
        state.get("reverse_map", {}),
    )

    state["sanitized_text"] = sanitized
    state["pii_token_map"]  = pii_map
    state["reverse_map"]    = rev_map
    state["pii_counts"]     = counts
    return state


def symbolic_rule_engine_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {
        "pii_token_map":  updated["pii_token_map"],
        "reverse_map":    updated["reverse_map"],
        "sanitized_text": updated["sanitized_text"],
        "pii_counts":     updated["pii_counts"],
    }

