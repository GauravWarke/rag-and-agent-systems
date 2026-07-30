from app.core.rate_limit import RateLimiter


def test_rate_limiter_allows_up_to_limit():
    limiter = RateLimiter(requests_per_minute=3)
    now = 1000.0
    assert limiter.allow("client-a", now) is True
    assert limiter.allow("client-a", now) is True
    assert limiter.allow("client-a", now) is True
    assert limiter.allow("client-a", now) is False


def test_rate_limiter_resets_after_window():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("client-b", 1000.0) is True
    assert limiter.allow("client-b", 1000.5) is False
    assert limiter.allow("client-b", 1061.0) is True


def test_rate_limiter_tracks_clients_independently():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("client-c", 1000.0) is True
    assert limiter.allow("client-d", 1000.0) is True
