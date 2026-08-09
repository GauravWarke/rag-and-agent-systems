from app.sampling.embeddings import cosine, embed


def test_embed_is_deterministic():
    a = embed("the export button is broken")
    b = embed("the export button is broken")
    assert (a == b).all()


def test_embed_is_normalized():
    vec = embed("a reasonably long sentence about billing issues")
    norm = (vec**2).sum() ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_similar_text_more_similar_than_unrelated():
    a = embed("the export button on the dashboard does nothing")
    b = embed("the export button on the dashboard is broken")
    c = embed("please upgrade my account to the enterprise plan")
    assert cosine(a, b) > cosine(a, c)


def test_identical_text_cosine_is_one():
    vec = embed("billing was charged twice this month")
    assert abs(cosine(vec, vec) - 1.0) < 1e-6
