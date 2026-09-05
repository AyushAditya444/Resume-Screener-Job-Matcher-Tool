import spacy
from spacy.matcher import PhraseMatcher

# A starter taxonomy — extend this list over time as real resumes/postings
# surface skills it misses. Kept as plain lowercase strings; multi-word
# skills are matched as phrases.
SKILL_TAXONOMY = [
    "python", "java", "javascript", "typescript", "sql", "nosql", "react",
    "vue", "angular", "node.js", "fastapi", "django", "flask", "docker",
    "kubernetes", "aws", "azure", "gcp", "git", "linux", "html", "css",
    "machine learning", "deep learning", "nlp", "pandas", "numpy",
    "scikit-learn", "pytorch", "tensorflow", "postgresql", "mysql",
    "mongodb", "redis", "graphql", "rest api", "ci/cd", "terraform",
    "communication", "leadership", "project management", "agile", "scrum",
]

_nlp = spacy.blank("en")
_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_matcher.add("SKILLS", [_nlp.make_doc(skill) for skill in SKILL_TAXONOMY])


def extract_skills(text: str) -> list[str]:
    doc = _nlp.make_doc(text)
    matches = _matcher(doc)
    found = []
    seen = set()
    for match_id, start, end in matches:
        skill = doc[start:end].text.lower()
        if skill not in seen:
            seen.add(skill)
            found.append(skill)
    return found
