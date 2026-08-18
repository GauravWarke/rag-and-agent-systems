import pytest

from app.core.models import AccessLevel, DocType
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


def test_policy_documents_are_restricted_by_default():
    chunks = load_sample_corpus()
    policy_chunks = [c for c in chunks if c.metadata.doc_type == DocType.policy]
    assert policy_chunks
    assert all(c.metadata.access_level == AccessLevel.restricted for c in policy_chunks)


def test_non_policy_documents_default_to_internal():
    chunks = load_sample_corpus()
    non_policy = [c for c in chunks if c.metadata.doc_type != DocType.policy]
    assert non_policy
    assert all(c.metadata.access_level == AccessLevel.internal for c in non_policy)
