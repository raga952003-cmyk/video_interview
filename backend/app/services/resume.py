import io
import os


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text_from_upload(file_storage) -> str:
    filename = (file_storage.filename or "").lower()
    ext = os.path.splitext(filename)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type {ext or '(none)'}. Use PDF, DOCX, or TXT."
        )
    file_storage.stream.seek(0)
    raw = file_storage.read()
    if not raw:
        raise ValueError("Empty file")

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
        text = "\n".join(parts).strip()
    elif ext == ".docx":
        import docx

        doc = docx.Document(io.BytesIO(raw))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
    else:
        text = raw.decode("utf-8", errors="replace").strip()

    if len(text) < 40:
        raise ValueError(
            "Could not extract enough text from the file. Try a text-based PDF or DOCX."
        )
    return text
