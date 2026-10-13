"""Grounded Q&A for the dashboard's "Ask the portfolio" tab.

Two modes:
- Saved answers (data/ai/qa_cache.json): rehearsed questions answered in advance
  from the project data. Always available, needs no API key.
- Live: a free-form question sent to Claude with the project's computed results
  as the only allowed source. Enabled only when ANTHROPIC_API_KEY is set.

Every number comes from the context block, never from the model's memory: the
architecture rule of the project (numbers are computed, not generated).
"""
from __future__ import annotations

import json

MODEL = "claude-opus-5-5"
SYSTEM = (
    "You answer questions about a student group's portfolio of three NSE stocks (Hindustan Unilever, "
    "Sun Pharma, ICICI Bank), built for a Security Analysis course. Use ONLY the JSON context provided "
    "after these instructions. Every number you state must appear in that context; never estimate, round "
    "differently than shown, or recall figures from memory. After each number, cite the context key it came "
    "from in square brackets, e.g. [portfolio.views.forward.tangency]. If the context does not contain what "
    "is needed, say so plainly instead of guessing. Answer in under 200 words, in plain English for a "
    "classmate. This is coursework, not investment advice, and you should say so if asked what to buy."
)


def build_context(data: dict) -> str:
    """Compact, deterministic JSON of the results the model may use (sorted keys keep the cache prefix stable)."""
    keep = {
        "metrics": {k: data["metrics"][k] for k in ("as_of", "assumptions", "securities", "correlation_check")},
        "valuation": data["valuation"],
        "portfolio": {k: data["portfolio"][k] for k in ("profiles", "out_of_sample", "certainty_equivalents")}
        | {"views": {v: {k: x for k, x in data["portfolio"]["views"][v].items() if k != "frontier"}
                     for v in data["portfolio"]["views"]}},
        "monte_carlo": data["mc"]["results"],
        "sip": data["sip"]["results"],
        "ai_analysis": {k: data["ai"].get(k) for k in ("technical_analysis", "risk", "forecasts", "extraction",
                                                       "sentiment", "framing")},
        "concall_aspects": data.get("aspects", {}),
    }
    return json.dumps(keep, sort_keys=True, separators=(",", ":"), default=str)


def ask(question: str, context: str, api_key: str, timeout: float = 30.0) -> tuple[str | None, str]:
    """Return (answer, status). On any API problem the answer is None and the caller falls back to saved answers."""
    import anthropic  # only needed in live mode

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1)
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            # Server-side fallback: if a safety classifier declines, the API re-runs the
            # request on a fallback model inside the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low"},  # short grounded answers; Opus 5.5 defaults to medium
            system=[{"type": "text", "text": SYSTEM},
                    {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": question}],
        )
    except anthropic.APITimeoutError:
        return None, "timed out"
    except anthropic.RateLimitError:
        return None, "rate limited"
    except anthropic.AuthenticationError:
        return None, "API key rejected"
    except anthropic.APIStatusError as e:
        return None, f"API error {e.status_code}"
    except anthropic.APIConnectionError:
        return None, "no connection"
    if resp.stop_reason == "refusal":
        return None, "declined"
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return (text or None), ("live" if text else "empty answer")
