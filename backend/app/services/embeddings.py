from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

# all-MiniLM-L6-v2 cosine similarities for real English text don't span
# the full [-1, 1] range: unrelated sentences typically land around 0.0-0.2
# (the model picks up shared "coherent sentence" structure even with no
# topical overlap), while closely related sentences reach ~0.7-0.9. A naive
# (cosine+1)/2 rescale compresses that useful range into the 50-100 band,
# making genuinely unrelated resume/job pairs look like a moderate match.
# Rescaling from this empirical range instead keeps the score discriminative.
_COSINE_FLOOR = 0.0
_COSINE_CEILING = 0.8


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def semantic_similarity(text_a: str, text_b: str) -> float:
    model = get_embedding_model()
    embeddings = model.encode([text_a, text_b])
    a, b = embeddings[0], embeddings[1]
    cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    scaled = (cosine - _COSINE_FLOOR) / (_COSINE_CEILING - _COSINE_FLOOR) * 100
    return round(max(0.0, min(100.0, scaled)), 2)
