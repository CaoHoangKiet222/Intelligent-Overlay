from typing import List, Sequence

MAX_VECTOR_DIM = 16000


def expand_vector_to_max_dim(vector: Sequence[float], actual_dim: int) -> List[float]:
	vec_list = list(vector)
	if len(vec_list) != actual_dim:
		raise ValueError(f"vector_dimension_mismatch: expected {actual_dim}, got {len(vec_list)}")
	if actual_dim > MAX_VECTOR_DIM:
		raise ValueError(f"vector_dimension_too_large: got {actual_dim}, max is {MAX_VECTOR_DIM}")
	if actual_dim == MAX_VECTOR_DIM:
		return vec_list
	padding = [0.0] * (MAX_VECTOR_DIM - actual_dim)
	return vec_list + padding


def reduce_vector_from_max_dim(vector: Sequence[float], actual_dim: int) -> List[float]:
	vec_list = list(vector)
	if len(vec_list) < actual_dim:
		raise ValueError(f"vector_too_short: got {len(vec_list)}, need at least {actual_dim}")
	return vec_list[:actual_dim]

