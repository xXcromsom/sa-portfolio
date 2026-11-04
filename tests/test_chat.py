import requests

from src import chat


class Reply:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self.body = body

    def json(self):
        if self.body is None:
            raise ValueError("not JSON")
        return self.body


def counts(used, limit=50):
    return Reply(200, {"data": {"free_model_daily_requests": {"used": used, "limit": limit, "remaining": limit - used}}})


def replies(monkeypatch, post, get=None):
    monkeypatch.setattr(chat.requests, "post", lambda *a, **k: post)
    monkeypatch.setattr(chat.requests, "get", lambda *a, **k: get)


def test_a_real_daily_limit_says_so_with_the_count(monkeypatch):
    error = {"code": 429, "message": "Rate limit exceeded: free-models-per-day"}
    replies(monkeypatch, Reply(429, {"error": error}), counts(50))
    answer, status = chat.ask("hlo", "{}", "key")
    assert answer is None
    assert status.startswith("OpenRouter 429: Rate limit exceeded: free-models-per-day")
    assert "50 of 50 free requests used today" in status


def test_a_busy_provider_is_not_reported_as_the_daily_limit(monkeypatch):
    error = {"code": 429, "message": "Provider returned error",
             "metadata": {"raw": "inkling:free is temporarily rate-limited upstream"}}
    replies(monkeypatch, Reply(429, {"error": error}), counts(3))
    _, status = chat.ask("hlo", "{}", "key")
    assert "temporarily rate-limited upstream" in status
    assert "3 of 50 free requests used today" in status


def test_a_429_inside_a_200_reply_reads_the_same(monkeypatch):
    replies(monkeypatch, Reply(200, {"error": {"code": 429, "message": "Rate limit exceeded"}}), counts(7))
    answer, status = chat.ask("hlo", "{}", "key")
    assert answer is None
    assert status.startswith("OpenRouter 429: Rate limit exceeded")
    assert "7 of 50" in status


def test_a_failed_count_lookup_keeps_the_reason(monkeypatch):
    replies(monkeypatch, Reply(429, {"error": {"code": 429, "message": "Rate limit exceeded"}}))

    def down(*a, **k):
        raise requests.ConnectionError

    monkeypatch.setattr(chat.requests, "get", down)
    _, status = chat.ask("hlo", "{}", "key")
    assert status == "OpenRouter 429: Rate limit exceeded; today's request count is unavailable"


def test_other_errors_use_openrouters_words_and_skip_the_count(monkeypatch):
    def never(*a, **k):
        raise AssertionError("the count is only looked up on a 429")

    replies(monkeypatch, Reply(404, {"error": {"code": 404, "message": "No endpoints found matching your data policy"}}))
    monkeypatch.setattr(chat.requests, "get", never)
    assert chat.ask("hlo", "{}", "key") == (None, "OpenRouter 404: No endpoints found matching your data policy")


def test_a_gateway_page_that_is_not_json_does_not_crash(monkeypatch):
    replies(monkeypatch, Reply(502))
    assert chat.ask("hlo", "{}", "key") == (None, "OpenRouter 502: the reply was not JSON")


def test_a_long_reason_is_cut_short(monkeypatch):
    replies(monkeypatch, Reply(500, {"error": {"code": 500, "message": "x" * 900}}))
    _, status = chat.ask("hlo", "{}", "key")
    assert len(status) < 220


def test_an_answer_names_the_model_that_gave_it(monkeypatch):
    body = {"model": "google/gemma-4-31b-it:free", "choices": [{"message": {"content": " ICICI is 50.1% of P. "}}]}
    replies(monkeypatch, Reply(200, body))
    assert chat.ask("hlo", "{}", "key") == ("ICICI is 50.1% of P.", "google/gemma-4-31b-it:free")


def test_no_connection_and_timeout_are_named(monkeypatch):
    for fault, expected in ((requests.Timeout, "timed out"), (requests.ConnectionError, "no connection")):
        def raises(*a, fault=fault, **k):
            raise fault

        monkeypatch.setattr(chat.requests, "post", raises)
        assert chat.ask("hlo", "{}", "key") == (None, expected)
