from app.logs.synthetic import generate_synthetic_logs
from app.sampling.sampler import diversity_sample, failure_biased_sample, random_sample


def test_random_sample_size_and_uniqueness():
    logs = generate_synthetic_logs(n=200, seed=1)
    sample = random_sample(logs, 20, seed=5)
    assert len(sample) == 20
    assert len({log.id for log in sample}) == 20


def test_random_sample_capped_by_available_logs():
    logs = generate_synthetic_logs(n=5, seed=1)
    sample = random_sample(logs, 20, seed=5)
    assert len(sample) == 5


def test_failure_biased_sample_overselects_failures():
    logs = generate_synthetic_logs(n=500, seed=1)
    failure_rate_full = sum(
        1 for log in logs if log.error or log.malformed_output or log.safety_flag or log.user_feedback == "negative"
    ) / len(logs)

    sample = failure_biased_sample(logs, 100, seed=1)
    failure_rate_sample = sum(
        1 for log in sample if log.error or log.malformed_output or log.safety_flag or log.user_feedback == "negative"
    ) / len(sample)

    assert failure_rate_sample > failure_rate_full


def test_diversity_sample_no_duplicates():
    logs = generate_synthetic_logs(n=200, seed=1)
    sample = diversity_sample(logs, 15, seed=1)
    assert len(sample) == 15
    assert len({log.id for log in sample}) == 15


def test_empty_logs_returns_empty():
    assert random_sample([], 10) == []
    assert failure_biased_sample([], 10) == []
    assert diversity_sample([], 10) == []
