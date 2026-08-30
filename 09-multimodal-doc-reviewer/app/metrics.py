"""Operational metrics report (Phase 6): pushes a synthetic sample corpus
of 20 documents through the full pipeline (upload -> extract -> validate)
and aggregates the routing outcomes, mirroring the kind of batch-health
summary a team would report after a production run — e.g. "Auto-approved
64% of sample documents while routing low-confidence fields to review."
`OCR_ENGINE` is forced to the deterministic `stub` engine so the numbers
do not depend on whether `tesseract` happens to be installed; every
sample document is a born-digital single-page PDF anyway, so OCR never
actually runs against it (see `app/intake/loaders.py`).
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.config import settings
from app.main import app


@dataclass(frozen=True)
class SampleDocument:
    filename: str
    text: str


class IssueReasonCount(BaseModel):
    field: str
    severity: str
    count: int


class OperationalMetricsReport(BaseModel):
    total_documents: int
    auto_approved: int
    needs_review: int
    auto_approval_rate: float
    issue_reasons: list[IssueReasonCount] = Field(default_factory=list)


# A mix of five document types with mostly-clean and deliberately-flawed
# samples: missing required fields, a failed business rule (invoice totals
# that don't add up, a claim filed outside the policy window), and vendors
# outside the known-vendor allowlist (a warning, not an error). Together
# they exercise every routing outcome the pipeline can produce.
SAMPLE_CORPUS: list[SampleDocument] = [
    SampleDocument(
        "invoice_acme_1001.pdf",
        "Invoice\nVendor: Acme Corp\nInvoice Number: INV-1001\nInvoice Date: 2026-07-01\n"
        "Due Date: 2026-07-31\nSubtotal: 100.00\nTax: 8.00\nTotal: 108.00\n",
    ),
    SampleDocument(
        "invoice_globex_1002.pdf",
        "Invoice\nVendor: Globex Inc\nInvoice Number: INV-1002\nInvoice Date: 2026-07-02\n"
        "Due Date: 2026-08-01\nSubtotal: 250.00\nTax: 20.00\nTotal: 270.00\n",
    ),
    SampleDocument(
        "invoice_acme_1003_bad_total.pdf",
        "Invoice\nVendor: Acme Corp\nInvoice Number: INV-1003\nInvoice Date: 2026-07-03\n"
        "Due Date: 2026-08-02\nSubtotal: 100.00\nTax: 8.00\nTotal: 200.00\n",
    ),
    SampleDocument(
        "invoice_initech_1004_missing_number.pdf",
        "Invoice\nVendor: Initech\nInvoice Date: 2026-07-04\nDue Date: 2026-08-03\n"
        "Subtotal: 500.00\nTax: 40.00\nTotal: 540.00\n",
    ),
    SampleDocument(
        "invoice_wayne_1005_unknown_vendor.pdf",
        "Invoice\nVendor: Wayne Enterprises\nInvoice Number: INV-1005\nInvoice Date: 2026-07-05\n"
        "Due Date: 2026-08-04\nSubtotal: 300.00\nTax: 24.00\nTotal: 324.00\n",
    ),
    SampleDocument(
        "invoice_initech_1006.pdf",
        "Invoice\nVendor: Initech\nInvoice Number: INV-1006\nInvoice Date: 2026-07-06\n"
        "Due Date: 2026-08-05\nSubtotal: 150.00\nTax: 12.00\nTotal: 162.00\n",
    ),
    SampleDocument(
        "receipt_stark.pdf",
        "Reimbursement Receipt\nVendor: Stark Industries\nPurchase Date: 2026-07-10\n"
        "Total: 42.50\nPayment Method: Corporate Card\n",
    ),
    SampleDocument(
        "receipt_umbrella.pdf",
        "Reimbursement Receipt\nVendor: Umbrella Corp\nPurchase Date: 2026-07-11\n"
        "Total: 88.00\nPayment Method: Corporate Card\n",
    ),
    SampleDocument(
        "receipt_missing_vendor.pdf",
        "Reimbursement Receipt\nPurchase Date: 2026-07-12\nTotal: 15.75\nPayment Method: Cash\n",
    ),
    SampleDocument(
        "receipt_daily_planet_unknown_vendor.pdf",
        "Reimbursement Receipt\nVendor: Daily Planet\nPurchase Date: 2026-07-13\n"
        "Total: 60.00\nPayment Method: Corporate Card\n",
    ),
    SampleDocument(
        "insurance_claim_jane_doe.pdf",
        "Insurance Claim\nClaimant Name: Jane Doe\nPolicy Number: POL-5521\n"
        "Claim Date: 2026-07-10\nIncident Date: 2026-06-15\nClaim Amount: 2500.00\n",
    ),
    SampleDocument(
        "insurance_claim_bruce_wayne.pdf",
        "Insurance Claim\nClaimant Name: Bruce Wayne\nPolicy Number: POL-5522\n"
        "Claim Date: 2026-05-20\nIncident Date: 2026-05-01\nClaim Amount: 1200.00\n",
    ),
    SampleDocument(
        "insurance_claim_clark_kent_before_incident.pdf",
        "Insurance Claim\nClaimant Name: Clark Kent\nPolicy Number: POL-5523\n"
        "Claim Date: 2026-06-01\nIncident Date: 2026-06-15\nClaim Amount: 900.00\n",
    ),
    SampleDocument(
        "insurance_claim_diana_prince_late_filing.pdf",
        "Insurance Claim\nClaimant Name: Diana Prince\nPolicy Number: POL-5524\n"
        "Claim Date: 2026-06-01\nIncident Date: 2026-01-01\nClaim Amount: 3000.00\n",
    ),
    SampleDocument(
        "onboarding_john_smith.pdf",
        "Onboarding Form\nApplicant Name: John Smith\nEmail: john.smith@example.com\n"
        "Start Date: 2026-08-01\nPosition: Software Engineer\n",
    ),
    SampleDocument(
        "onboarding_maria_garcia_missing_email.pdf",
        "Onboarding Form\nApplicant Name: Maria Garcia\nStart Date: 2026-08-05\n"
        "Position: Product Manager\n",
    ),
    SampleDocument(
        "onboarding_wei_chen.pdf",
        "Onboarding Form\nApplicant Name: Wei Chen\nEmail: wei.chen@example.com\n"
        "Start Date: 2026-08-10\nPosition: Data Analyst\n",
    ),
    SampleDocument(
        "contract_summary_acme_globex.pdf",
        "Contract Summary\nEffective Date: 2026-01-01\nTerm: 12 months\n"
        "Contract Value: 50000.00\nParties: Acme Corp, Globex Inc\n",
    ),
    SampleDocument(
        "contract_summary_missing_value.pdf",
        "Contract Summary\nEffective Date: 2026-02-01\nTerm: 24 months\n"
        "Parties: Initech, Stark Industries\n",
    ),
    SampleDocument(
        "contract_summary_umbrella_wayne.pdf",
        "Contract Summary\nEffective Date: 2026-03-01\nTerm: 6 months\n"
        "Contract Value: 15000.00\nParties: Umbrella Corp, Wayne Enterprises\n",
    ),
]


def _build_single_page_pdf(text: str) -> bytes:
    """Hand-rolled minimal single-page PDF, just enough for `pypdf` to read
    the text back out of. Kept local to this module rather than shared
    with `tests/pdf_builder.py` since the two have different jobs: this
    one always needs exactly one page of `Label: value` lines, that one
    needs to build arbitrary multi-page fixtures for the test suite.
    """
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    stream_lines = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
    for index, line in enumerate(escaped.splitlines()):
        if index > 0:
            stream_lines.append("T*")
        stream_lines.append(f"({line}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines)

    objects = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: "<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        "/MediaBox [0 0 612 792] /Contents 5 0 R >>",
        4: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        5: f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    }

    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = buffer.tell()
        buffer.write(f"{number} 0 obj\n".encode("latin-1"))
        buffer.write(objects[number].encode("latin-1"))
        buffer.write(b"\nendobj\n")

    xref_offset = buffer.tell()
    total_objects = max(objects) + 1
    buffer.write(f"xref\n0 {total_objects}\n".encode("latin-1"))
    buffer.write(b"0000000000 65535 f \n")
    for number in range(1, total_objects):
        buffer.write(f"{offsets.get(number, 0):010d} 00000 n \n".encode("latin-1"))
    buffer.write(
        f"trailer\n<< /Size {total_objects} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
    )
    return buffer.getvalue()


def run_operational_metrics() -> OperationalMetricsReport:
    original_ocr_engine = settings.ocr_engine
    settings.ocr_engine = "stub"
    reason_counts: dict[tuple[str, str], int] = {}
    auto_approved = 0
    try:
        with TestClient(app) as client:
            for sample in SAMPLE_CORPUS:
                upload = client.post(
                    "/v1/documents",
                    files={"file": (sample.filename, _build_single_page_pdf(sample.text), "application/pdf")},
                )
                document_id = upload.json()["id"]
                validation = client.post(f"/v1/documents/{document_id}/validate").json()
                if validation["routing"] == "auto_approved":
                    auto_approved += 1
                for issue in validation["issues"]:
                    key = (issue["field"], issue["severity"])
                    reason_counts[key] = reason_counts.get(key, 0) + 1
    finally:
        settings.ocr_engine = original_ocr_engine

    total = len(SAMPLE_CORPUS)
    issue_reasons = [
        IssueReasonCount(field=field, severity=severity, count=count)
        for (field, severity), count in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)
    ]
    return OperationalMetricsReport(
        total_documents=total,
        auto_approved=auto_approved,
        needs_review=total - auto_approved,
        auto_approval_rate=auto_approved / total if total else 0.0,
        issue_reasons=issue_reasons,
    )


def format_report(report: OperationalMetricsReport) -> str:
    headline = (
        f"Auto-approved {report.auto_approval_rate:.0%} of {report.total_documents} sample documents "
        f"({report.auto_approved} auto-approved, {report.needs_review} routed to review with reasons attached)."
    )
    lines = [headline]
    if report.issue_reasons:
        lines.append("Top reasons routed to review:")
        for reason in report.issue_reasons:
            lines.append(f"  [{reason.severity}] {reason.field}: {reason.count} document(s)")
    return "\n".join(lines)
