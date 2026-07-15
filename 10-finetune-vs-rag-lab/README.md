# P10: Fine-Tune vs RAG Decision Lab

**Topic:** MLOps, Fine-Tuning, RAG, Benchmarking, Model Selection

## What you're building

An experiment framework that compares three approaches for a domain-specific AI task: prompt-only, RAG, and LoRA fine-tuning. It evaluates quality, cost, latency, maintainability, and failure modes so you can justify which approach is best.

## Why this project lands interviews

> Fine-tuning sounds impressive, but only if you can justify it. This build compares prompt-only, RAG, and LoRA with the same benchmark so the decision is evidence-based.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Base Model | Llama / Mistral / Phi |
| Fine-Tuning | Hugging Face PEFT + TRL |
| RAG | ChromaDB / Qdrant |
| Training Efficiency | QLoRA / Unsloth |
| Experiment Tracking | MLflow or Weights & Biases |
| Evals | Custom benchmark + LLM judge |
| Serving | vLLM / Ollama |
| Containerization | Docker |

## Build phases

### Phase 1: Choose a Narrow Domain Task (Day 1-3)

- Pick a measurable task: Good examples: support macro selection, policy clause classification, bug report severity prediction, or domain-specific email rewrite.
- Build a dataset: Create 500-1,500 examples with instruction, input, expected output, category, and difficulty. Clean duplicates and formatting issues.
- Create a benchmark: Hold out 100 examples as a fixed test set. Add 30 hard edge cases by hand.

### Phase 2: Build the Prompt-Only Baseline (Day 3-4)

- Write a strong prompt: Include task instructions, output schema, and a few examples.
- Run baseline evals: Measure accuracy, quality score, schema validity, latency, and cost.
- Store outputs: Keep raw outputs so you can compare where each approach succeeds or fails.

### Phase 3: Build the RAG Variant (Day 4-7)

- Create a small knowledge base: Add policies, examples, guidelines, or domain references that can help the task.
- Retrieve context for each input: Use embeddings and metadata filters to find the most relevant reference examples.
- Evaluate the RAG version: Compare quality to the prompt-only baseline. Track retrieval failures separately from generation failures.

### Phase 4: Build the LoRA Fine-Tuned Variant (Day 7-10)

- Prepare training data: Format data for instruction tuning. Split train/validation/test cleanly.
- Fine-tune with LoRA: Start with modest settings: rank 8 or 16, low learning rate, early stopping, and validation tracking.
- Track experiments: Log hyperparameters, training curves, validation metrics, GPU memory, and selected checkpoint.

### Phase 5: Compare All Three Approaches (Day 10-12)

- Run the same benchmark: Evaluate prompt-only, RAG, and fine-tuned model on the same test set.
- Compare beyond accuracy: Include latency, cost, setup complexity, update difficulty, failure modes, and operational risk.
- Write a recommendation: For example: "RAG wins when knowledge changes often; LoRA wins when style and label consistency matter most."

### Phase 6: Polish for Portfolio (Day 12-14)

- Build a comparison dashboard: Show side-by-side outputs and metrics for all three approaches.
- Write the decision memo: Make it read like an internal architecture decision record. Reviewers notice judgment, not only implementation.

## Interview talking point

> The baseline is not a formality. It is the only way to know whether fine-tuning was worth the effort.

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
