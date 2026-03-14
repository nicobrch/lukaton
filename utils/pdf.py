import io
from pathlib import Path

import pikepdf


def unlock_pdf(pdf_bytes: bytes, password: str, output_path: Path) -> None:
    with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
        pdf.save(output_path)
