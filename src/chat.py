"""Grounded Q&A for the dashboard's "Ask the portfolio" tab.

Two modes:
- Saved answers (data/ai/qa_cache.json): rehearsed questions answered in advance
  from the project data. Always available, needs no API key.
- Live: a free-form question sent to a free model on OpenRouter, with the project's
  computed results (and the viewer's own portfolio) as the only allowed source.
  Enabled only when OPENROUTER_API_KEY is set.

Every number comes from the context block, never from the model's memory: the
architecture rule of the project (numbers are computed, not generated).
"""
from __future__ import annotations

import json

import requests

URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_URL = "https://openrouter.ai/api/v1/key"
# Free models, in priority order; OpenRouter moves down the list if one errors or is rate-limited.
# Free models get retired without notice, so the last entry is OpenRouter's own router across whichever are live.
MODELS = ["thinkingmachines/inkling:free", "google/gemma-4-31b-it:free", "openrouter/free"]
SYSTEM = (
    "You answer questions about a student group's portfolio of three NSE stocks (Hindustan Unilever, "
    "Sun Pharma, ICICI Bank), built for a Security Analysis course. Use ONLY the JSON context provided "
    "after these instructions. 'your_portfolio' is the viewer's own portfolio for their risk aversion A and "
    "amount; the rest is the project's analysis. Every number you state must appear in that context; never "
    "estimate, round differently than shown, or recall figures from memory. After each number, cite the "
    "context key it came from in square brackets, e.g. [portfolio.views.forward.tangency]. If the context "
    "does not contain what is needed, say so plainly instead of guessing. Answer in under 200 words, in "
    "plain English for a classmate. This is coursework, not investment advice, and you should say so if "
    "asked what to buy."
)


def build_context(data: dict, mine: dict | None = None) -> str:
    """Compact, deterministic JSON of the results the model may use."""
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
        "market_efficiency": data.get("emh"),
        "performance_measures": data.get("performance"),
        "street_view": {k: v for k, v in (data.get("street") or {}).items() if k != "brokers"},
        "mood": data.get("mood"),
    }
    if mine:
        keep["your_portfolio"] = mine
    return json.dumps(keep, sort_keys=True, separators=(",", ":"), default=str)


def used_today(api_key: str) -> str:
    """Free requests this key has used today. The per-minute limit and busy providers don't show in this count."""
    try:
        count = requests.get(KEY_URL, timeout=10, headers={"Authorization": f"Bearer {api_key}"}).json()
        count = count["data"]["free_model_daily_requests"]
        return f"{count['used']} of {count['limit']} free requests used today; the count resets at 05:30 IST"
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return "today's request count is unavailable"


def failure(code: int | str | None, error: dict, api_key: str) -> str:
    """Why a request failed, in OpenRouter's own words.

    A code alone can't say: 429 is the per-minute limit, the daily limit or a busy provider.
    """
    reason = str((error.get("metadata") or {}).get("raw") or error.get("message") or "no reason given")[:200]
    return f"OpenRouter {code}: {reason}" + (f"; {used_today(api_key)}" if code == 429 else "")


def ask(question: str, context: str, api_key: str, models: list[str] = MODELS,
        timeout: float = 45.0) -> tuple[str | None, str]:
    """Return (answer, status). status names the model that answered, or why there is no answer."""
    try:
        resp = requests.post(URL, timeout=timeout, headers={"Authorization": f"Bearer {api_key}"}, json={
            "model": models[0],
            "models": models,
            "messages": [{"role": "system", "content": f"{SYSTEM}\n\nCONTEXT (JSON):\n{context}"},
                         {"role": "user", "content": question}],
            "max_tokens": 1500,
            "temperature": 0.2,
            "reasoning": {"effort": "low"},  # short grounded answers; keeps the free models fast
        })
    except requests.Timeout:
        return None, "timed out"
    except requests.RequestException:
        return None, "no connection"
    try:
        body = resp.json()
    except ValueError:  # an HTML error page from a gateway, not OpenRouter's JSON
        return None, f"OpenRouter {resp.status_code}: the reply was not JSON"
    if resp.status_code != 200 or body.get("error"):
        error = body.get("error") or {}
        return None, failure(error.get("code", resp.status_code), error, api_key)
    choices = body.get("choices") or []
    text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
    return (text or None), (body.get("model", models[0]) if text else "empty answer")
