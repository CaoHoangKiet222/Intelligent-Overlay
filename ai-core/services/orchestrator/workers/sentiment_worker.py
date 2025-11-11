import ray
from workers.base import fetch_prompt, call_llm_generate


@ray.remote
async def run_sentiment(task: dict) -> dict:
	prompt_id = (task.get("prompt_ids") or {}).get("sentiment")
	template, _vars = await fetch_prompt(prompt_id)
	seg_text = "\n".join(s.get("text", "") for s in (task.get("segments") or [])[:8])
	prompt = template.replace("{{ context }}", seg_text)
	resp = await call_llm_generate(model_hint="openai", prompt=prompt, context=seg_text, language=task.get("language", "auto"))
	return {"worker": "sentiment", "ok": True, "output": {"text": resp.get("output", "")}, "llm_call": resp}


