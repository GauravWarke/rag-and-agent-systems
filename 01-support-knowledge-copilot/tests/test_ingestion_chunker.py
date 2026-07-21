import pytest

from app.core.models import DocType
from app.ingestion.chunker import chunk_fixed_size, chunk_markdown


def test_chunk_markdown_tracks_heading_strategy():
    text = "# Title\nBody one.\n\n## Sub\nBody two.\n"
    chunks = chunk_markdown(text, source_name="faq", doc_type=DocType.faq)

    assert len(chunks) == 2
    assert all(c.chunking_strategy == "heading" for c in chunks)
    assert chunks[0].metadata.section_heading == "Title"
    assert chunks[1].metadata.section_heading == "Sub"


def test_chunk_fixed_size_splits_into_overlapping_windows():
    words = [f"word{i}" for i in range(50)]
    text = " ".join(words)

    chunks = chunk_fixed_size(text, source_name="doc", doc_type=DocType.faq,
                               chunk_size=20, overlap=5)

    assert len(chunks) == 3
    assert all(c.chunking_strategy == "fixed" for c in chunks)
    # consecutive windows overlap by the configured amount
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-5:] == second_words[:5]


def test_chunk_fixed_size_covers_all_words_without_duplicating_the_last_window():
    words = [f"word{i}" for i in range(45)]
    text = " ".join(words)

    chunks = chunk_fixed_size(text, source_name="doc", doc_type=DocType.faq,
                               chunk_size=20, overlap=5)

    # last window should end exactly at the final word, not repeat as its own chunk
    assert chunks[-1].text.split()[-1] == "word44"
    reconstructed = set()
    for c in chunks:
        reconstructed.update(c.text.split())
    assert reconstructed == set(words)


def test_chunk_fixed_size_chunk_ids_are_unique_and_tagged():
    text = " ".join(f"w{i}" for i in range(30))
    chunks = chunk_fixed_size(text, source_name="policy", doc_type=DocType.policy,
                               chunk_size=10, overlap=2)

    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(cid.startswith("policy::fixed::") for cid in ids)


def test_chunk_fixed_size_empty_text_returns_no_chunks():
    assert chunk_fixed_size("   \n  ", source_name="doc", doc_type=DocType.faq) == []


def test_chunk_fixed_size_rejects_overlap_not_smaller_than_chunk_size():
    with pytest.raises(ValueError, match="overlap"):
        chunk_fixed_size("a b c", source_name="doc", doc_type=DocType.faq,
                          chunk_size=5, overlap=5)


def test_chunk_fixed_size_rejects_non_positive_chunk_size():
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_fixed_size("a b c", source_name="doc", doc_type=DocType.faq, chunk_size=0)
