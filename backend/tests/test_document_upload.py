from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from app.lib.auth import create_access_token
from app.models import Permission, Role, User, UserSession
from app.services.document_parser import (
    MAX_ARCHIVE_UNCOMPRESSED_BYTES,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    DocumentParsingTimeout,
    bounded_upload_file,
    parse_uploaded_document,
)
from app.services.malware import MalwareDetected, get_malware_scanner


def _make_docx_bytes(lines: list[str]) -> bytes:
    from docx import Document

    document = Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _make_pdf_bytes(lines: list[str]) -> bytes:
    """Build a minimal valid PDF with embedded text using raw PDF syntax."""
    from pypdf import PdfReader

    encoded = "\n".join(lines).encode("latin-1", errors="replace")
    escaped = encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    content_stream = (
        b"BT\n"
        b"/F1 12 Tf\n"
        b"100 700 Td\n"
        + b"(" + escaped + b") Tj\n"
        b"ET\n"
    )
    content_length = len(content_stream)

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"   /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>\n"
            b"   /Contents 4 0 R\n"
            b">>\nendobj\n"
        ),
        (
            b"4 0 obj\n"
            + b"<< /Length " + str(content_length).encode() + b" >>\n"
            + b"stream\n" + content_stream + b"endstream\nendobj\n"
        ),
    ]

    body = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(body))
        body += obj

    xref_offset = len(body)
    xref = (
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
    )
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = (
        b"trailer\n"
        b"<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_offset).encode() + b"\n"
        b"%%EOF\n"
    )
    pdf = body + xref + trailer

    # Verify extraction works with pypdf before returning
    reader = PdfReader(BytesIO(pdf))
    extracted = reader.pages[0].extract_text()
    if not extracted:
        pytest.skip("PDF text extraction not supported in this environment")
    return pdf


def _auth_headers(db_session, user):
    token, jti = create_access_token({"sub": str(user.id)})
    now = datetime.now(timezone.utc)
    db_session.add(
        UserSession(
            user_id=user.id,
            jti=jti,
            issued_at=now,
            expires_at=now + timedelta(hours=8),
        )
    )
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


def _make_user(db_session, permission="submit_question"):
    permission_obj = Permission(code=permission, description=permission)
    role = Role(name="Upload Role", permissions=[permission_obj])
    user = User(
        employee_id="EMP-UPLOAD-1",
        name="Upload User",
        role="Viewer",
        status="Active",
        roles=[role],
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestDocumentParser:
    def test_parse_txt_document(self):
        content = b"Subject line for the question\n\nThis is the detailed body of the parliamentary question."
        result = parse_uploaded_document(content, "question.txt")
        assert result["subject"] == "Subject line for the question"
        assert "detailed body" in result["full_text"]
        assert result["item_type"] is None

    def test_parse_txt_with_item_type_hint(self):
        content = b"Motion subject\n\nBody text here."
        result = parse_uploaded_document(content, "motion.txt", item_type="Motion")
        assert result["item_type"] == "Motion"

    def test_parse_docx_document(self):
        content = _make_docx_bytes(
            ["DOCX subject line", "", "This is the body paragraph of the document."]
        )
        result = parse_uploaded_document(content, "question.docx")
        assert result["subject"] == "DOCX subject line"
        assert "body paragraph" in result["full_text"]

    def test_parse_pdf_document(self):
        content = _make_pdf_bytes(
            ["PDF subject line", "Body paragraph of the PDF document."]
        )
        result = parse_uploaded_document(content, "question.pdf")
        assert "subject" in result["subject"].lower()
        assert "PDF" in result["subject"] or "PDF" in result["full_text"]

    def test_reject_unsupported_file_type(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_uploaded_document(b"data", "document.png")

    def test_reject_empty_text_document(self):
        with pytest.raises(ValueError, match="No readable text"):
            parse_uploaded_document(b"   \n\n   ", "empty.txt")

    def test_reject_oversized_file(self):
        huge = b"x" * (MAX_UPLOAD_BYTES + 1)
        with pytest.raises(ValueError, match="too large"):
            parse_uploaded_document(huge, "huge.txt")

    def test_reject_missing_filename(self):
        with pytest.raises(ValueError, match="Filename is required"):
            parse_uploaded_document(b"text", None)

    def test_reject_spoofed_extension_and_mime(self):
        with pytest.raises(ValueError, match="does not match"):
            parse_uploaded_document(
                b"This is plain text pretending to be a PDF.",
                "question.pdf",
                content_type="application/pdf",
            )

    def test_reject_encrypted_pdf(self):
        from pypdf import PdfWriter

        output = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("secret")
        writer.write(output)

        with pytest.raises(ValueError, match="Encrypted PDFs"):
            parse_uploaded_document(
                output.getvalue(),
                "secret.pdf",
                content_type="application/pdf",
            )

    def test_reject_pdf_with_excessive_page_count(self):
        from pypdf import PdfWriter

        output = BytesIO()
        writer = PdfWriter()
        for _ in range(MAX_PDF_PAGES + 1):
            writer.add_blank_page(width=72, height=72)
        writer.write(output)

        with pytest.raises(ValueError, match="too many pages"):
            parse_uploaded_document(
                output.getvalue(),
                "many-pages.pdf",
                content_type="application/pdf",
            )

    def test_reject_docx_archive_bomb(self):
        output = BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr(
                "word/document.xml",
                b"A" * (MAX_ARCHIVE_UNCOMPRESSED_BYTES + 1),
            )

        with pytest.raises(ValueError, match="archive limits"):
            parse_uploaded_document(
                output.getvalue(),
                "bomb.docx",
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

    def test_bounded_storage_never_uses_an_unbounded_read(self):
        class GuardedStream(BytesIO):
            def read(self, size=-1):
                assert size > 0, "upload storage attempted an unbounded read"
                return super().read(size)

        with bounded_upload_file(GuardedStream(b"Subject\n\nBody")) as path:
            assert path.read_bytes() == b"Subject\n\nBody"

        assert not path.exists()


class TestUploadEndpoint:
    def test_upload_txt_requires_authentication(self, client: TestClient):
        response = client.post(
            "/submissions/upload",
            files={"file": ("question.txt", BytesIO(b"Subject\n\nBody"), "text/plain")},
        )
        assert response.status_code == 401

    def test_upload_txt_succeeds(self, client, db_session):
        user = _make_user(db_session)
        response = client.post(
            "/submissions/upload",
            files={"file": ("question.txt", BytesIO(b"Subject line\n\nBody text here."), "text/plain")},
            headers=_auth_headers(db_session, user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Subject line"
        assert data["full_text"] == "Body text here."

    def test_upload_invalid_file_type(self, client, db_session):
        user = _make_user(db_session)
        response = client.post(
            "/submissions/upload",
            files={"file": ("image.png", BytesIO(b"not an image"), "image/png")},
            headers=_auth_headers(db_session, user),
        )
        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_with_item_type_hint(self, client, db_session):
        user = _make_user(db_session, permission="submit_motion")
        response = client.post(
            "/submissions/upload",
            data={"item_type": "Motion"},
            files={"file": ("motion.txt", BytesIO(b"Motion subject\n\nMotion body."), "text/plain")},
            headers=_auth_headers(db_session, user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item_type"] == "Motion"

    def test_upload_rejects_mime_and_magic_spoofing(self, client, db_session):
        user = _make_user(db_session)
        response = client.post(
            "/submissions/upload",
            files={
                "file": (
                    "spoofed.pdf",
                    BytesIO(b"Plain text with a fake PDF extension"),
                    "application/pdf",
                )
            },
            headers=_auth_headers(db_session, user),
        )

        assert response.status_code == 422
        assert "does not match" in response.json()["detail"]

    def test_upload_rejects_oversized_stream(self, client, db_session):
        user = _make_user(db_session)
        response = client.post(
            "/submissions/upload",
            files={
                "file": (
                    "oversized.txt",
                    BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1)),
                    "text/plain",
                )
            },
            headers=_auth_headers(db_session, user),
        )

        assert response.status_code == 422
        assert "too large" in response.json()["detail"].casefold()

    def test_malware_detection_rejects_upload(self, client, db_session):
        class RejectingScanner:
            def scan(self, _path):
                raise MalwareDetected("test signature detected")

        user = _make_user(db_session)
        from app.main import app

        app.dependency_overrides[get_malware_scanner] = lambda: RejectingScanner()
        response = client.post(
            "/submissions/upload",
            files={
                "file": (
                    "question.txt",
                    BytesIO(b"Subject\n\nA safe-looking body"),
                    "text/plain",
                )
            },
            headers=_auth_headers(db_session, user),
        )

        assert response.status_code == 422
        assert "malware" in response.json()["detail"].casefold()

    def test_parser_timeout_removes_temporary_file(
        self,
        client,
        db_session,
        monkeypatch,
    ):
        observed_path: list[Path] = []

        def time_out(path, **_kwargs):
            observed_path.append(Path(path))
            raise DocumentParsingTimeout("Document parsing timed out")

        monkeypatch.setattr(
            "app.routers.submissions.parse_document_safely",
            time_out,
        )
        user = _make_user(db_session)
        response = client.post(
            "/submissions/upload",
            files={
                "file": (
                    "question.txt",
                    BytesIO(b"Subject\n\nBody"),
                    "text/plain",
                )
            },
            headers=_auth_headers(db_session, user),
        )

        assert response.status_code == 422
        assert observed_path
        assert not observed_path[0].exists()
