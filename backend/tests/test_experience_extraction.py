from app.services.experience_extraction import (
    extract_years_of_experience,
    extract_education_level,
)


def test_extracts_plus_years():
    assert extract_years_of_experience("5+ years of experience in backend development") == 5.0


def test_extracts_plain_years():
    assert extract_years_of_experience("3 years of experience with React") == 3.0


def test_returns_none_when_no_years_mentioned():
    assert extract_years_of_experience("Skilled Python developer") is None


def test_extracts_bachelor_degree():
    assert extract_education_level("B.S. in Computer Science, State University") == "bachelor"


def test_extracts_master_degree():
    assert extract_education_level("Completed an M.S. in Data Science") == "master"


def test_extracts_doctorate():
    assert extract_education_level("Ph.D. in Information Science") == "doctorate"


def test_returns_none_when_no_degree_mentioned():
    assert extract_education_level("Self-taught developer, no formal degree") is None
