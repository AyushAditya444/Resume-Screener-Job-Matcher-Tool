from app.services.skill_taxonomy import extract_skills


def test_extracts_known_skills_case_insensitively():
    text = "Experienced in Python, SQL and React. Familiar with docker and Kubernetes."
    skills = extract_skills(text)
    assert set(skills) == {"python", "sql", "react", "docker", "kubernetes"}


def test_ignores_unknown_terms():
    text = "Skilled in Python and the ancient art of underwater basket weaving."
    skills = extract_skills(text)
    assert skills == ["python"]


def test_deduplicates_repeated_mentions():
    text = "Python developer. Also did Python scripting and more Python work."
    skills = extract_skills(text)
    assert skills == ["python"]
