from app.logs.synthetic import generate_synthetic_logs
from app.sampling.cluster import cluster_assignments, cluster_logs


def test_cluster_logs_covers_all_logs():
    logs = generate_synthetic_logs(n=200, seed=1)
    clusters = cluster_logs(logs, k=4, seed=1)
    assert sum(c.size for c in clusters) == len(logs)


def test_cluster_logs_has_labels_and_representatives():
    logs = generate_synthetic_logs(n=100, seed=1)
    clusters = cluster_logs(logs, k=3, seed=1)
    for cluster in clusters:
        assert cluster.label
        assert cluster.representative_prompt
        assert 1 <= len(cluster.example_log_ids) <= 5


def test_cluster_assignments_aligned_with_logs():
    logs = generate_synthetic_logs(n=50, seed=1)
    assignments, vectors, k = cluster_assignments(logs, k=3, seed=1)
    assert len(assignments) == len(logs)
    assert vectors.shape[0] == len(logs)
    assert set(assignments.tolist()).issubset(set(range(k)))


def test_empty_logs_returns_no_clusters():
    assert cluster_logs([], k=3) == []
