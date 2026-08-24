import pytest

from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The app's rate limiter is a single process-wide instance keyed by
    client host, and every `TestClient` call in this suite shares the same
    host — without a reset, unrelated tests would start tripping each
    other's rate limit as the suite grows (e.g. the golden workflow suite
    alone makes 40 requests).
    """
    limiter.clear()
    yield
    limiter.clear()
