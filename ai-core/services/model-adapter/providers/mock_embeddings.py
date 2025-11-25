from __future__ import annotations

from typing import List

DEFAULT_MOCK_EMBED_DIM = 1536


def build_mock_embeddings(texts: List[str], dim: int = DEFAULT_MOCK_EMBED_DIM) -> List[List[float]]:
	if dim <= 0:
		raise ValueError("dim must be positive")
	vectors: List[List[float]] = []
	for idx, text in enumerate(texts):
		length = len(text)
		base = length + idx
		vector = [float(((base * (j + 1)) % 997) / 997) for j in range(dim)]
		vectors.append(vector)
	return vectors

