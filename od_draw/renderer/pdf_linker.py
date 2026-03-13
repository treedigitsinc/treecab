from __future__ import annotations

import fitz


class PDFLinker:
    def rasterize_page(self, pdf_path: str, page: int, dpi: int = 150) -> tuple[bytes, int, int]:
        document = fitz.open(pdf_path)
        try:
            page_object = document[page]
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            pixmap = page_object.get_pixmap(matrix=matrix, alpha=False)
            return pixmap.tobytes("png"), pixmap.width, pixmap.height
        finally:
            document.close()

    def extract_vectors(self, pdf_path: str, page: int) -> list[dict]:
        document = fitz.open(pdf_path)
        try:
            return document[page].get_drawings()
        finally:
            document.close()
