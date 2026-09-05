import re

_YEARS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", re.IGNORECASE)

_EDUCATION_PATTERNS = [
    ("doctorate", re.compile(r"\bph\.?d\.?\b|\bdoctorate\b", re.IGNORECASE)),
    ("master", re.compile(r"\bm\.?s\.?\b|\bmaster'?s?\b|\bmba\b", re.IGNORECASE)),
    ("bachelor", re.compile(r"\bb\.?s\.?\b|\bb\.?a\.?\b|\bbachelor'?s?\b", re.IGNORECASE)),
    ("associate", re.compile(r"\bassociate'?s?\b", re.IGNORECASE)),
    ("high_school", re.compile(r"\bhigh school\b|\bg\.?e\.?d\.?\b", re.IGNORECASE)),
]

# Highest degree wins if multiple are mentioned.
_EDUCATION_RANK = ["high_school", "associate", "bachelor", "master", "doctorate"]


def extract_years_of_experience(text: str) -> float | None:
    match = _YEARS_PATTERN.search(text)
    if not match:
        return None
    return float(match.group(1))


def extract_education_level(text: str) -> str | None:
    found = [level for level, pattern in _EDUCATION_PATTERNS if pattern.search(text)]
    if not found:
        return None
    return max(found, key=_EDUCATION_RANK.index)
