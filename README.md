# AI Engineering Projects

A monorepo of 15 production-minded AI engineering projects, based on Kushal Vijay's *AI Engineering Projects Guide*. Each project is built like an internal tool a real AI team would use — not a tutorial clone — with architecture choices, tests, evals, and real metrics.

Built incrementally by a scheduled agent that advances [`ROADMAP.md`](./ROADMAP.md) one item at a time and opens a PR for each change.

## Projects

| # | Project | Primary Topic | Folder |
|---|---------|---------------|--------|
| 1 | Support Knowledge Copilot with Verified Citations | RAG | [`01-support-knowledge-copilot/`](./01-support-knowledge-copilot) |
| 2 | Prompt Release Safety Gate | LLMOps | [`02-prompt-release-safety-gate/`](./02-prompt-release-safety-gate) |
| 3 | LLM Spend Control Center | LLMOps | [`03-llm-spend-control-center/`](./03-llm-spend-control-center) |
| 4 | AI Output Policy Guardrail Service | Guardrails | [`04-output-policy-guardrail/`](./04-output-policy-guardrail) |
| 5 | Production Log-to-Eval Dataset Builder | Evals | [`05-log-to-eval-dataset-builder/`](./05-log-to-eval-dataset-builder) |
| 6 | Permissioned Tool-Using Agent Sandbox | Agents | [`06-agent-sandbox/`](./06-agent-sandbox) |
| 7 | RAG Freshness and Drift Monitor | RAG | [`07-rag-freshness-monitor/`](./07-rag-freshness-monitor) |
| 8 | Natural Language to API Assistant | Tool Calling | [`08-nl-to-api-assistant/`](./08-nl-to-api-assistant) |
| 9 | Multimodal Document Intake Reviewer | Multimodal | [`09-multimodal-doc-reviewer/`](./09-multimodal-doc-reviewer) |
| 10 | Fine-Tune vs RAG Decision Lab | MLOps | [`10-finetune-vs-rag-lab/`](./10-finetune-vs-rag-lab) |
| 11 | AI Trace Explorer for LLM Workflows | LLMOps | [`11-ai-trace-explorer/`](./11-ai-trace-explorer) |
| 12 | Semantic Cache Gateway for LLM APIs | LLMOps | [`12-semantic-cache-gateway/`](./12-semantic-cache-gateway) |
| 13 | AI Feature Rollout Monitor | LLMOps | [`13-feature-rollout-monitor/`](./13-feature-rollout-monitor) |
| 14 | Evaluation-as-a-Service Platform | Evals | [`14-eval-as-a-service/`](./14-eval-as-a-service) |
| 15 | Local LLM Deployment Kit | MLOps | [`15-local-llm-deploy-kit/`](./15-local-llm-deploy-kit) |

## Repo conventions

- **Language:** Python 3.11+, FastAPI for services, Pydantic for schemas.
- **Each project** is self-contained in its folder with its own `requirements.txt`, `README.md`, `Dockerfile`, tests, and (where relevant) `docker-compose.yml`.
- **Every project ships:** a clean architecture note, reproducible Docker setup, an intentional evaluation dataset, and a report/dashboard with real numbers.
- **Status:** P1 (Support Knowledge Copilot) is the active flagship. See `ROADMAP.md` for progress.

## Getting started (per project)

```bash
cd 01-support-knowledge-copilot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys
uvicorn app.main:app --reload
```

## Attribution

Project blueprints adapted from *AI Engineering Projects Guide* by Kushal Vijay.
