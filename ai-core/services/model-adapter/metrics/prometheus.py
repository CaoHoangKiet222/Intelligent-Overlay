from prometheus_client import Counter

guard_pii_masked = Counter("guard_pii_masked_total", "Total PII entities masked", ["entity_type"])
guard_blocked = Counter("guard_blocked_total", "Total prompts blocked by policy", ["reason"])
guard_jailbreak = Counter("guard_jailbreak_total", "Total jailbreak attempts detected")


