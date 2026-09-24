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


def test_rate_limiter_memory_is_bounded():
    limiter = RateLimiter(requests_per_minute=5, max_keys=100)
    for i in range(10_000):
        limiter.allow(f"10.0.{i // 256}.{i % 256}", 1000.0)
    assert len(limiter._hits) <= 100


def test_rate_limiter_sweeps_clients_outside_the_window():
    limiter = RateLimiter(requests_per_minute=5, max_keys=10)
    for i in range(10):
        limiter.allow(f"old-{i}", 1000.0)
    limiter.allow("new", 1100.0)  # table full -> sweep drops all expired keys
    assert set(limiter._hits) == {"new"}


def test_rate_limiter_eviction_keeps_the_active_client_limited():
    limiter = RateLimiter(requests_per_minute=2, max_keys=3)
    assert limiter.allow("busy", 1000.0) is True
    assert limiter.allow("busy", 1000.0) is True
    for i in range(5):  # churn through other clients within the same window
        limiter.allow(f"other-{i}", 1000.0)
        limiter.allow("busy", 1000.0)  # stays most-recently-seen
    assert limiter.allow("busy", 1000.0) is False
