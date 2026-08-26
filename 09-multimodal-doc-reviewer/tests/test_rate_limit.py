from app.core.rate_limit import RateLimiter


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(requests_per_minute=2)
    assert limiter.allow("client-a", now=0.0) is True
    assert limiter.allow("client-a", now=0.1) is True
    assert limiter.allow("client-a", now=0.2) is False


def test_window_slides_after_60_seconds():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("client-a", now=0.0) is True
    assert limiter.allow("client-a", now=30.0) is False
    assert limiter.allow("client-a", now=61.0) is True


def test_clients_are_independent():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("client-a", now=0.0) is True
    assert limiter.allow("client-b", now=0.0) is True
