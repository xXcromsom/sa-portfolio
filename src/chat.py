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
# Free models, in priority order; OpenRouter moves down the list if one errors or is rate-limited.
MODELS = ["nvidia/nemotron-3-super-120b-a12b:free", "thinkingmachines/inkling:free", "google/gemma-4-31b-it:free"]
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
ERRORS = {
    401: "API key rejected",
    402: "OpenRouter says the account needs credits",
    404: "no free model matches your OpenRouter privacy settings (allow free models at openrouter.ai/settings/privacy)",
    429: "free-model limit reached (50 requests a day on a free account); try later",
}


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
    }
    if mine:
        keep["your_portfolio"] = mine
    return json.dumps(keep, sort_keys=True, separators=(",", ":"), default=str)


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
    if resp.status_code != 200:
        return None, ERRORS.get(resp.status_code, f"API error {resp.status_code}")
    body = resp.json()
    if body.get("error"):
        code = body["error"].get("code")
        return None, ERRORS.get(code, f"API error {code}")
    choices = body.get("choices") or []
    text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
    return (text or None), (body.get("model", models[0]) if text else "empty answer")
