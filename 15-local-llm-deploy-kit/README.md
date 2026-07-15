# P15: Local LLM Deployment Kit

**Topic:** MLOps, Inference, Local Models, Quantization, Performance Testing

## What you're building

A deployment kit that runs an open-source LLM locally or on a small server, exposes an OpenAI-compatible API, benchmarks latency and throughput across quantization levels, and includes monitoring, rollback, and model comparison reports.

## Why this project lands interviews

> Local deployment is useful when teams care about cost, data control, or vendor flexibility. This build covers serving, quantization, benchmarking, monitoring, and rollback.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Serving | vLLM, Ollama, or llama.cpp |
| Models | Llama / Mistral / Qwen / Phi |
| Quantization | GGUF / AWQ / GPTQ |
| API | FastAPI wrapper or OpenAI-compatible server |
| Benchmarking | Locust / custom async runner |
| Metrics | Prometheus |
| Dashboard | Grafana |
| Containerization | Docker + NVIDIA runtime optional |

## Build phases

### Phase 1: Pick Models and Serving Path (Day 1-3)

- Choose a target task: Pick something measurable like summarization, classification, extraction, or support reply drafting.
- Select two or three model variants: Compare a small model, a medium model, and a quantized model. Document expected tradeoffs.
- Set up serving: Use Ollama for simplicity or vLLM for higher-throughput serving. Expose a chat completion endpoint.

### Phase 2: Build the Benchmark Harness (Day 3-5)

- Create a request dataset: Use 100-200 prompts with realistic input lengths and expected output lengths.
- Measure performance: Track tokens per second, time to first token, P50/P95 latency, throughput, memory usage, and error rate.
- Test concurrency: Run benchmarks at 1, 5, 10, and 25 concurrent users.

### Phase 3: Build Quality Evaluation (Day 5-8)

- Score outputs: Use task-specific metrics and LLM-as-judge against reference answers.
- Compare against a cloud baseline: Run the same prompts against a hosted model and compare quality, cost estimate, and latency.
- Identify acceptable use cases: Some tasks may work well locally; others may need stronger hosted models. Document this honestly.

### Phase 4: Add Monitoring and Rollback (Day 8-10)

- Export metrics: Latency, throughput, token rate, GPU memory, queue depth, errors, and model version.
- Build Grafana dashboards: Show live inference health and historical benchmark results.
- Add model rollback: Support switching active model versions through config. Log every switch.

### Phase 5: Package the Deployment Kit (Day 10-12)

- Write Docker Compose files: Include server, metrics, dashboard, and optional benchmark runner.
- Add config files: Let users set model path, quantization, max context length, batching settings, and concurrency limits.
- Create setup scripts: Make it easy to pull a model, start the server, run a benchmark, and generate a report.

### Phase 6: Polish for Portfolio (Day 12-14)

- Publish benchmark results: Include a table comparing models by quality, latency, throughput, memory, and cost estimate.
- Write the deployment memo: Frame it as an internal recommendation: which model should be used for which workload, and why.

## Interview talking point

> Local models are not automatically cheaper or better. You have to measure hardware cost, latency, quality, and operational complexity together.

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
