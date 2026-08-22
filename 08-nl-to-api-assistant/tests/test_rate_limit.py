from app.core.rate_limit import RateLimiter


def test_rate_limiter_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(requests_per_minute=3)
    assert limiter.allow("client-a", now=0.0)
    assert limiter.allow("client-a", now=1.0)
    assert limiter.allow("client-a", now=2.0)
    assert not limiter.allow("client-a", now=3.0)


def test_rate_limiter_window_slides():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("client-a", now=0.0)
    assert not limiter.allow("client-a", now=1.0)
    assert limiter.allow("client-a", now=61.0)


def test_rate_limiter_tracks_clients_independently():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("client-a", now=0.0)
    assert limiter.allow("client-b", now=0.0)
