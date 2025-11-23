PRICES = {
	("openai", "gpt-4o-mini"): {"prompt": 0.15, "completion": 0.60},
	("openai", "gpt-4.1-mini"): {"prompt": 0.20, "completion": 0.80},
	("anthropic", "claude-3-sonnet-20240229"): {"prompt": 0.30, "completion": 1.50},
	("mistral", "mistral-large"): {"prompt": 0.15, "completion": 0.45},
	("mistral", "mistral-large-latest"): {"prompt": 0.15, "completion": 0.45},
	("ollama", "llama3.1:8b"): {"prompt": 0.0, "completion": 0.0},
}


def estimate_cost(provider: str, model: str, tokens_in: int | None, tokens_out: int | None) -> float:
	price = PRICES.get((provider, model))
	if not price:
		return 0.0
	return (float(tokens_in or 0) / 1000.0) * price["prompt"] + (float(tokens_out or 0) / 1000.0) * price["completion"]


