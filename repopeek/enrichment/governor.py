"""Cost governor tracking token consumption and enforcing budget thresholds."""

from typing import Any, Dict


class CostGovernor:
    """Enforces strict token and financial spend ceilings across enrichment runs."""

    # Default rate estimates in USD per 1M tokens
    RATES_PER_1M = {
        "qwen/qwen3.8-27b": {"input": 0.20, "output": 0.20},
        "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
        "openai/gpt-oss-20b": {"input": 0.15, "output": 0.20},
        "openai/gpt-oss-120b": {"input": 0.60, "output": 1.00},
        "default": {"input": 0.20, "output": 0.20},
    }

    def __init__(
        self,
        max_tokens: int = 100_000,
        max_cost_usd: float = 1.00,
        dry_run: bool = False,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.dry_run = dry_run

        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.cached_tokens: int = 0
        self.llm_calls: int = 0
        self.fallback_calls: int = 0
        self.estimated_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def can_call_llm(self, estimated_tokens: int = 200) -> bool:
        """Check if an LLM completion can be made within budget and run-mode limits."""
        if self.dry_run:
            return False
        if (self.total_tokens + estimated_tokens) > self.max_tokens:
            return False
        if self.estimated_cost_usd >= self.max_cost_usd:
            return False
        return True

    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
        model: str = "default",
    ) -> None:
        """Account for tokens processed and update cumulative dollar spend."""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.cached_tokens += cached_tokens
        self.llm_calls += 1

        rate = self.RATES_PER_1M.get(model, self.RATES_PER_1M["default"])
        # Cached tokens receive ~50% discount on prompt input
        billable_prompt = max(0, prompt_tokens - (cached_tokens // 2))
        cost = (billable_prompt / 1_000_000.0) * rate["input"] + (
            completion_tokens / 1_000_000.0
        ) * rate["output"]
        self.estimated_cost_usd += cost

    def record_fallback(self) -> None:
        """Record an operation delegated to zero-cost deterministic fallback."""
        self.fallback_calls += 1

    def get_summary(self) -> Dict[str, Any]:
        """Return cumulative financial and volume audit figures."""
        return {
            "llm_calls": self.llm_calls,
            "fallback_calls": self.fallback_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cached_tokens": self.cached_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "budget_tokens_limit": self.max_tokens,
            "budget_cost_limit": self.max_cost_usd,
            "budget_exhausted": not self.can_call_llm(0),
        }
