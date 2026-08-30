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

## Implemented so far

Phases 1–3 are built (`app/intake`, `app/ocr`, `app/extraction`):

- **Upload and preprocessing:** `POST /v1/documents` accepts PDF/PNG/JPEG/TIFF. Raster pages run
  through EXIF-based rotation correction, autocontrast, a median-filter denoise pass, and a
  resolution sanity check (all real Pillow operations, not stubs). Born-digital PDF pages use
  their embedded text layer directly and skip OCR entirely; scanned PDF pages are flagged
  `pdf_image` since no offline rasterizer is bundled. A keyword classifier tags the document type
  (invoice, receipt, insurance claim, onboarding form, contract summary) from the filename and
  any embedded text available at upload time.
- **OCR and vision fallback:** `POST /v1/documents/{id}/ocr` runs `pytesseract` when the
  `tesseract` binary is available (`OCR_ENGINE=auto`), else falls back to a deterministic offline
  stub. `app/ocr/confidence.py` scores each result against engine confidence, alphanumeric
  density, and text density; low-confidence pages are routed to `app/ocr/vision_fallback.py`,
  which is a stub until `VISION_API_KEY` is set.
- **Structured extraction:** `POST /v1/documents/{id}/extract` parses `Label: value` lines per
  document-type schema (`app/extraction/schemas.py`), with every scalar wrapped in a
  `SourcedValue` (value, page number, source). `app/extraction/merge.py` combines multi-page
  results — the first page's value wins, and any page that disagrees is recorded as a
  `FieldConflict` instead of silently overwritten.
- **Validation and routing:** `POST /v1/documents/{id}/validate` runs extraction first if it
  hasn't already, then checks the result in `app/validation`:
  - *Type validation* (`app/validation/rules.py::validate_type`) — every required field for the
    document's type is present, and any date-looking field (invoice/due date, purchase date,
    claim/incident date, start date, effective date) actually parses. Numeric fields and the
    `document_type` enum are already guaranteed valid by the extraction schema, so there's
    nothing further to check for those here.
  - *Business rules* (`validate_business_rules`) — invoice `subtotal + tax == total` within a
    cent, insurance claims filed within a 90-day policy window of the incident (and not before
    it), and vendor names checked against a small known-vendor allowlist (an unknown vendor is a
    warning, not a hard error).
  - *Routing* (`app/validation/routing.py::route_by_confidence`) — any error drops confidence to
    `low`; warnings only drop it to `medium`; a clean document is `high`. Only `high` confidence
    is auto-approved — `medium`/`low` are routed to `needs_review` with the specific issues
    attached so a reviewer knows exactly what to check.

- **Side-by-side review:** `GET /v1/documents/{id}/review` runs validation first if it hasn't
  already, then bundles page summaries, extracted fields (each still carrying its source page
  number), extraction conflicts, and validation issues into one `ReviewPacket` — everything a
  reviewer needs to judge one document. `GET /v1/documents/{id}/pages/{n}/image` serves the
  normalized page PNG referenced by each page summary's `image_url`, so a UI can show the image
  and jump to the page a clicked field came from.
- **Reviewer corrections:** `POST /v1/documents/{id}/review/corrections` records a reviewer's fix
  for one extracted field — original value, corrected value, reviewer, and an optional reason —
  and immediately applies it to the stored extraction result (scalar fields are re-wrapped as a
  `SourcedValue` with `source="human_correction"`, keeping the original page number; list fields
  like `line_items` are replaced outright). Unknown field names are rejected with 400.
  `GET /v1/documents/{id}/review/corrections` lists the correction history for one document.
- **Accuracy analytics:** `GET /v1/review/analytics` aggregates across every ingested document:
  auto-approval rate, total corrections, which fields get corrected most often
  (`field_accuracy`), and average review turnaround time (upload → first correction; documents
  with no corrections don't contribute a sample, since there's no separate "review started"
  event in this stub).

- **Messy-document demo:** `python demo.py` (implementation in `app/demo.py`) pushes a single
  low-resolution, sideways-scanned receipt through the full pipeline end to end: preprocessing
  reports the rotation fix and a low-resolution warning, OCR comes back empty and falls through
  to the (offline, keyless) vision-fallback stub, extraction ends up with every field `None`,
  validation flags the three missing required fields and routes the document to
  `needs_review`, a reviewer fills in the fields it couldn't read, and re-validating shows the
  document flip to `auto_approved`. `tests/test_demo.py` runs the same walkthrough as a
  regression test.
- **Operational metrics:** `python operational_metrics.py` (implementation in `app/metrics.py`)
  pushes a synthetic 20-document sample corpus — invoices, reimbursement receipts, insurance
  claims, onboarding forms, and contract summaries, mostly clean but with deliberately planted
  problems (a missing required field, an invoice total that doesn't add up, a claim filed outside
  the 90-day policy window, a vendor outside the known-vendor allowlist) — through upload,
  extraction, and validation, then reports the routing split:

  ```
  Auto-approved 55% of 20 sample documents (11 auto-approved, 9 routed to review with reasons attached).
  Top reasons routed to review:
    [warning] vendor: 2 document(s)
    [error] claim_date: 2 document(s)
    [error] total: 1 document(s)
    [error] invoice_number: 1 document(s)
    [error] vendor: 1 document(s)
    [error] email: 1 document(s)
    [error] contract_value: 1 document(s)
  ```

  `tests/test_metrics.py` pins these numbers as a regression test — the corpus and rules are both
  deterministic, so a routing regression in `app/validation` shows up here immediately.

**Case study:** hybrid document intake — OCR first, vision as a fallback rather than the default
(cheaper, and just as accurate on born-digital and high-quality scans) — auto-approved 55% of a
20-document sample corpus outright and routed the remaining 45% to human review with the specific
field and business-rule reason attached to each, rather than a bare "low confidence" flag. That
reason-per-issue design is what makes the review queue actionable instead of just a pile of
maybes.
