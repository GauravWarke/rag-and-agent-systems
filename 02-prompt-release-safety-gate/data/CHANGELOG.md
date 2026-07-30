# Golden Test Set Changelog

The golden test set (`golden_test_set.jsonl`) is a managed artifact, not a
one-time file. Every change to it is recorded here so reviewers can see how
the eval bar has evolved.

## v1 — 2026-07-30

- Initial version: 75 hand-written messy customer notes for the CRM
  summary feature (`crm_summary` prompt).
- Categories: `spelling_mistakes` (8), `vague_request` (8),
  `emotional_customer` (8), `missing_context` (8), `mixed_intent` (8),
  `billing_dispute` (6), `bug_report` (6), `feature_question` (6),
  `cancellation_request` (5), `positive_feedback` (4),
  `safety_sensitive` (4), `pii_present` (4).
- Each case is labeled with `difficulty` (easy/medium/hard), `risk_area`
  (billing, product, product_bug, churn, safety, compliance, none), and
  `why_this_case_exists` so the dataset reads as intentionally curated
  rather than randomly generated.
- IDs are stable (`c001`-`c075`); future edits to a case should keep its ID
  unless the case is fully replaced.
