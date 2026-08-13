from app.tools.web_search import WebSearchArgs, handle


def test_returns_relevant_results():
    result = handle(WebSearchArgs(query="how do I reset my password"))
    assert result["results"]
    assert any("password" in doc["title"].lower() for doc in result["results"])


def test_no_matches_returns_empty_list():
    result = handle(WebSearchArgs(query="zzz_no_match_zzz"))
    assert result["results"] == []


def test_respects_max_results():
    result = handle(WebSearchArgs(query="plans refunds api webhooks password", max_results=2))
    assert len(result["results"]) <= 2
