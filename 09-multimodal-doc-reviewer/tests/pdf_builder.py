"""Hand-rolled minimal single/multi-page PDF builder for tests, so the
test suite doesn't need a heavyweight PDF-authoring dependency just to
produce a document `pypdf` can read text back out of.
"""
from __future__ import annotations

import io


def build_text_pdf(pages_text: list[str]) -> bytes:
    n = len(pages_text)
    font_obj_num = 3 + n
    content_obj_start = font_obj_num + 1

    objects: dict[int, str] = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{' '.join(f'{3 + i} 0 R' for i in range(n))}] /Count {n} >>",
        font_obj_num: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }

    for i, text in enumerate(pages_text):
        page_num = 3 + i
        content_num = content_obj_start + i
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {content_num} 0 R >>"
        )

        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream_lines = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
        for j, line in enumerate(escaped.split("\n")):
            if j > 0:
                stream_lines.append("T*")
            stream_lines.append(f"({line}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        objects[content_num] = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in sorted(objects):
        offsets[num] = buf.tell()
        buf.write(f"{num} 0 obj\n".encode("latin-1"))
        buf.write(objects[num].encode("latin-1"))
        buf.write(b"\nendobj\n")

    xref_offset = buf.tell()
    total_objs = max(objects) + 1
    buf.write(f"xref\n0 {total_objs}\n".encode("latin-1"))
    buf.write(b"0000000000 65535 f \n")
    for num in range(1, total_objs):
        buf.write(f"{offsets.get(num, 0):010d} 00000 n \n".encode("latin-1"))
    buf.write(f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1"))
    return buf.getvalue()
