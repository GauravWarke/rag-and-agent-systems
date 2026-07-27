from app.core.models import Chunk, ChunkMetadata, DocType, RetrievedChunk
from app.generation.prompts import SYSTEM_PROMPT, build_context_block, build_user_prompt


def _retrieved(cid, text):
    chunk = Chunk(chunk_id=cid, text=text,
                  metadata=ChunkMetadata(source_name="t", doc_type=DocType.faq))
    return RetrievedChunk(chunk=chunk, fused_score=0.5)


def test_system_prompt_requires_citations_and_context_only():
    assert "chunk" in SYSTEM_PROMPT.lower()
    assert "context" in SYSTEM_PROMPT.lower()


def test_build_context_block_tags_each_chunk_with_its_id():
    block = build_context_block([_retrieved("c1", "Error 429 means too many requests.")])
    assert "[c1]" in block
    assert "Error 429" in block


def test_build_user_prompt_includes_question_and_context():
    prompt = build_user_prompt("What does 429 mean?", [_retrieved("c1", "Rate limit info.")])
    assert "What does 429 mean?" in prompt
    assert "[c1]" in prompt
