from app.routing.overrides import RoutingOverrides


def test_load_reads_yaml():
    overrides = RoutingOverrides.load("data/routing_overrides.yaml")
    assert overrides.forced_tier("legal-review") == 3


def test_unconfigured_feature_returns_none():
    overrides = RoutingOverrides.load("data/routing_overrides.yaml")
    assert overrides.forced_tier("unconfigured-feature") is None
