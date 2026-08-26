import pytest

from app.core.rate_limit import limiter
from app.extraction.store import extraction_result_store
from app.intake.store import document_store
from app.ocr.store import ocr_result_store


@pytest.fixture(autouse=True)
def _reset_state():
    """Every `TestClient` call in this suite shares one process-wide rate
    limiter and set of in-memory stores — without a reset, unrelated tests
    would leak documents into each other and trip each other's rate limit.
    """
    limiter.clear()
    document_store.clear()
    ocr_result_store.clear()
    extraction_result_store.clear()
    yield
    limiter.clear()
    document_store.clear()
    ocr_result_store.clear()
    extraction_result_store.clear()
