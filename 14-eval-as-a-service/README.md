# P14: Evaluation-as-a-Service Platform

**Topic:** Evals, LLM-as-Judge, Quality Gates, Judge Calibration

## What you're building

A centralized evaluation API that other AI features can call to score model outputs against rubrics. It supports custom metrics, judge calibration, batch evaluation, historical tracking, and release quality gates.

## Why this project lands interviews

> Reusable eval infrastructure is much stronger than a one-off scoring script. This build covers rubrics, judge calibration, batch scoring, history, and quality gates.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| API | FastAPI |
| Judge Models | OpenAI / Anthropic / local |
| Structured Output | Pydantic + instructor |
| Storage | PostgreSQL |
| Queue | Celery + Redis |
| Dashboard | Streamlit |
| Stats | scipy / numpy |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Design the Eval API (Day 1-3)

- Define evaluation requests: Input includes prompt, model output, optional reference answer, rubric, task type, and metadata.
- Define score output: Return overall score, dimension scores, pass/fail, explanation, evidence spans, judge confidence, and policy warnings.
- Support reusable rubrics: Store rubrics for summarization, classification, RAG faithfulness, tone, completeness, and safety.

### Phase 2: Build Judge-Based Scoring (Day 3-6)

- Write dimension-specific judge prompts: Each rubric dimension should have clear scoring rules and examples.
- Enforce structured results: Use Pydantic so every score has the same shape. Invalid judge output should retry or fail cleanly.
- Add evidence requirements: The judge must explain what part of the output caused each score.

### Phase 3: Calibrate the Judge (Day 6-8)

- Build a calibration set: Create 50 examples with human scores. Include excellent, mediocre, and bad outputs.
- Compare judge to human labels: Measure agreement, average score difference, and where the judge is too harsh or too generous.
- Tune prompts and thresholds: Adjust rubrics and pass/fail thresholds based on calibration results.

### Phase 4: Build Batch Evals and Quality Gates (Day 8-11)

- Add batch endpoint: Accept a list of outputs and run evals asynchronously.
- Generate run reports: Show score distributions, failed cases, dimension-level weakness, and examples of judge reasoning.
- Add release gates: A CI job can call the eval service and fail if pass rate, safety score, or faithfulness score drops below threshold.

### Phase 5: Build Dashboard and Analytics (Day 11-13)

- Create a run explorer: Compare eval runs over time and drill into failed examples.
- Track judge drift: If judge model or rubric changes, rerun calibration examples and compare scores.
- Add metric health: Show score variance, disagreement between judges, and human override rate.

### Phase 6: Polish for Portfolio (Day 13-14)

- Demo it across two features: Score a RAG answer and a summarization output using different rubrics.
- Write the case study: Position it as "shared evaluation infrastructure for AI platform teams." Start with calibration results.

## Interview talking point

> LLM-as-judge is useful, but it is not magic. You need calibration examples, consistency checks, and human review for high-risk decisions.

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
