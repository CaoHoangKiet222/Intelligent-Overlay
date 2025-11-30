from domain.models import GenerationResult
from controllers.schemas import ModelGenerateResponse


def build_generate_response(provider_name: str, cost_per_1k: float, result: GenerationResult) -> ModelGenerateResponse:
	token_total = (result.tokens_in or 0) + (result.tokens_out or 0)
	cost_usd = round((token_total / 1000) * cost_per_1k, 6) if token_total else None
	return ModelGenerateResponse(
		provider=provider_name,
		model=result.model,
		output=result.text,
		tokens_in=result.tokens_in,
		tokens_out=result.tokens_out,
		latency_ms=result.latency_ms,
		cost_usd=cost_usd,
	)

