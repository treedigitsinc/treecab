from __future__ import annotations

from pathlib import Path

import fitz


class PDFAssembler:
    def merge(self, sheet_pdfs: list[tuple[str, bytes]], output_path: str | Path) -> Path:
        merged = fitz.open()
        try:
            for _, pdf_bytes in sorted(sheet_pdfs, key=lambda item: item[0]):
                document = fitz.open(stream=pdf_bytes, filetype="pdf")
                try:
                    merged.insert_pdf(document)
                finally:
                    document.close()
            output = Path(output_path)
            merged.save(output)
            return output
        finally:
            merged.close()
