from app.budgets.policy import BudgetPolicyStore


def test_load_reads_yaml():
    store = BudgetPolicyStore.load("data/budget_policies.yaml")
    policy = store.for_team("team-alpha")
    assert policy.daily_limit_usd == 5.0
    assert policy.monthly_limit_usd == 100.0


def test_unknown_team_falls_back_to_default():
    store = BudgetPolicyStore.load("data/budget_policies.yaml")
    policy = store.for_team("unknown-team")
    assert policy.daily_limit_usd == 1.0
    assert policy.monthly_limit_usd == 20.0


def test_feature_without_policy_returns_none():
    store = BudgetPolicyStore.load("data/budget_policies.yaml")
    assert store.for_feature("unconfigured-feature") is None


def test_feature_with_policy_returns_it():
    store = BudgetPolicyStore.load("data/budget_policies.yaml")
    policy = store.for_feature("support-bot")
    assert policy is not None
    assert policy.daily_limit_usd == 3.0
