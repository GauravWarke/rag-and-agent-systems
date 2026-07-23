import pytest

from app.ingestion.loader import load_sample_corpus


def test_load_sample_corpus_defaults_to_heading_strategy():
    chunks = load_sample_corpus()
    assert chunks
    assert all(c.chunking_strategy == "heading" for c in chunks)


def test_load_sample_corpus_supports_fixed_strategy():
    chunks = load_sample_corpus(chunking_strategy="fixed")
    assert chunks
    assert all(c.chunking_strategy == "fixed" for c in chunks)


def test_load_sample_corpus_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="Unknown chunking strategy"):
        load_sample_corpus(chunking_strategy="bogus")
