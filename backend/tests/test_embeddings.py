from app.services.embeddings import semantic_similarity


def test_similar_texts_score_highly():
    score = semantic_similarity(
        "Experienced Python backend engineer skilled in FastAPI and SQL",
        "Looking for a backend developer with Python and SQL experience",
    )
    assert score > 60


def test_dissimilar_texts_score_lower():
    score = semantic_similarity(
        "Experienced Python backend engineer skilled in FastAPI and SQL",
        "Seeking a pastry chef with 5 years of experience in French baking",
    )
    assert score < 40


def test_score_is_bounded_0_to_100():
    score = semantic_similarity("some text", "some text")
    assert 0 <= score <= 100
