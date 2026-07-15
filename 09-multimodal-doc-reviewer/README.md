# P9: Multimodal Document Intake Reviewer

**Topic:** Multimodal AI, OCR, Structured Extraction, Human-in-the-Loop

## What you're building

A document intake system that accepts scanned forms, PDFs, screenshots, and images; extracts structured fields; validates them against business rules; and sends low-confidence results to a human review queue.

## Why this project lands interviews

> Document intake is a common enterprise use case. This build combines OCR, vision fallback, structured extraction, validation, and human review in one practical workflow.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| OCR | Tesseract + EasyOCR |
| PDF Parsing | PyMuPDF |
| Vision LLM | GPT-4o vision / Claude vision |
| Structured Output | Pydantic + instructor |
| Queue | Celery + Redis |
| Storage | PostgreSQL + local object storage |
| Review UI | Streamlit or React |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Build Document Upload and Preprocessing (Day 1-3)

- Accept multiple formats: Support PDFs, PNGs, JPEGs, and TIFFs. Store the original file and a normalized page image for each page.
- Detect document type: Classify documents like invoice, reimbursement receipt, insurance claim, onboarding form, or contract summary.
- Preprocess images: Add rotation correction, contrast enhancement, noise removal, and resolution checks. Track preprocessing steps in metadata.

### Phase 2: Build OCR and Vision Fallback (Day 3-5)

- Run OCR first: Extract text with Tesseract or EasyOCR. Store text by page and line if possible.
- Estimate OCR confidence: Use OCR confidence scores, text density, and format sanity checks to decide whether OCR is usable.
- Use vision fallback: If OCR confidence is low, send the page image to a vision-capable model and ask it to preserve layout.

### Phase 3: Extract Structured Data (Day 5-8)

- Define schemas by document type: For invoices, extract vendor, invoice number, dates, line items, tax, and total. For forms, extract applicant details and required fields.
- Use structured output: The LLM should return data that validates against Pydantic. Include field-level source references where each value came from.
- Handle long documents: Process by page or section and merge outputs. If two pages disagree, flag the conflict instead of hiding it.

### Phase 4: Validate and Route (Day 8-10)

- Add type validation: Dates parse, totals are numbers, required fields exist, and enums are valid.
- Add business rules: Invoice totals must equal line items plus tax. Claim dates must be within policy windows. Vendor names must match known vendors.
- Route by confidence: High confidence goes auto-approved. Medium and low confidence go to review with reasons.

### Phase 5: Build Human Review and Analytics (Day 10-12)

- Create side-by-side review: Show the document image and extracted fields. Clicking a field highlights its source area or page.
- Let reviewers correct fields: Store original value, corrected value, reviewer, and correction reason.
- Track accuracy by field: Show which fields fail most often, average review time, and auto-approval rate.

### Phase 6: Polish for Portfolio (Day 12-14)

- Demo a messy document: Use a slightly rotated scan or screenshot where OCR is imperfect. Show extraction, validation, review, and correction.
- Use operational metrics: Example: "Auto-approved 64% of sample documents while routing low-confidence fields to review."

## Interview talking point

> Explain that vision models are powerful but expensive. A production design should use them as fallback, not as the default for every page.

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
