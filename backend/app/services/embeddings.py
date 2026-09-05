from functools import lru_cache

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MAX_SEQ_LENGTH = 256

# all-MiniLM-L6-v2 cosine similarities for real English text don't span
# the full [-1, 1] range: unrelated sentences typically land around 0.0-0.2
# (the model picks up shared "coherent sentence" structure even with no
# topical overlap), while closely related sentences reach ~0.7-0.9. A naive
# (cosine+1)/2 rescale compresses that useful range into the 50-100 band,
# making genuinely unrelated resume/job pairs look like a moderate match.
# Rescaling from this empirical range instead keeps the score discriminative.
_COSINE_FLOOR = 0.0
_COSINE_CEILING = 0.8


class EmbeddingModel:
    """Runs all-MiniLM-L6-v2 via ONNX Runtime instead of sentence-transformers/torch.

    The full torch + transformers + sentence-transformers stack uses ~380MB
    of resident memory just to import and load this model, which alone
    exceeds Render's free-tier 512MB limit once the rest of the app is
    running. ONNX Runtime + tokenizers loads the same model (numerically
    verified to match to 4 decimal places) in ~170MB, comfortably leaving
    room for FastAPI/spaCy/etc.

    Reimplements sentence-transformers' own pooling exactly: mean-pool
    token embeddings weighted by the attention mask, then L2-normalize
    (see the model's 1_Pooling/config.json and modules.json on the Hub).
    """

    def __init__(self) -> None:
        model_path = hf_hub_download(MODEL_REPO, "onnx/model.onnx")
        tokenizer_path = hf_hub_download(MODEL_REPO, "tokenizer.json")
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self._tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
        self._session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    def encode(self, texts: list[str]) -> np.ndarray:
        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)

        token_embeddings = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )[0]

        mask = attention_mask[..., None].astype(np.float32)
        summed = (token_embeddings * mask).sum(axis=1)
        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        mean_pooled = summed / counts

        norms = np.linalg.norm(mean_pooled, axis=1, keepdims=True)
        return mean_pooled / norms


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()


def semantic_similarity(text_a: str, text_b: str) -> float:
    model = get_embedding_model()
    embeddings = model.encode([text_a, text_b])
    # Embeddings are already L2-normalized, so the dot product is cosine similarity.
    cosine = float(np.dot(embeddings[0], embeddings[1]))
    scaled = (cosine - _COSINE_FLOOR) / (_COSINE_CEILING - _COSINE_FLOOR) * 100
    return round(max(0.0, min(100.0, scaled)), 2)
