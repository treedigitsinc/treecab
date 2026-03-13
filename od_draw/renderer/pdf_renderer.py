from __future__ import annotations

from dataclasses import dataclass, field


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass
class PdfPage:
    width: float
    height: float
    commands: list[str] = field(default_factory=list)

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: float = 1.0,
        stroke_rgb: tuple[float, float, float] | None = None,
        dash: tuple[float, float] | None = None,
    ) -> None:
        prefix: list[str] = []
        if stroke_rgb is not None:
            prefix.append(f"{stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
        if dash is not None:
            prefix.append(f"[{dash[0]:.2f} {dash[1]:.2f}] 0 d")
        self.commands.append(
            " ".join(prefix + [f"{width} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"])
        )
        if dash is not None:
            self.commands.append("[] 0 d")

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        stroke_width: float = 1.0,
        stroke_rgb: tuple[float, float, float] | None = None,
        fill_rgb: tuple[float, float, float] | None = None,
        dash: tuple[float, float] | None = None,
    ) -> None:
        prefix: list[str] = []
        if stroke_rgb is not None:
            prefix.append(f"{stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
        if fill_rgb is not None:
            prefix.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
        if dash is not None:
            prefix.append(f"[{dash[0]:.2f} {dash[1]:.2f}] 0 d")
        self.commands.append(
            " ".join(prefix + [f"{stroke_width} w {x:.2f} {y:.2f} {width:.2f} {height:.2f} re"])
            + " "
            + ("B" if fill_rgb is not None else "S")
        )
        if dash is not None:
            self.commands.append("[] 0 d")

    def text(
        self,
        x: float,
        y: float,
        value: str,
        size: float = 10.0,
        fill_rgb: tuple[float, float, float] | None = None,
    ) -> None:
        prefix = ""
        if fill_rgb is not None:
            prefix = f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg "
        self.commands.append(
            f"{prefix}BT /F1 {size:.2f} Tf {x:.2f} {y:.2f} Td ({_escape_text(value)}) Tj ET"
        )


class PdfDocument:
    def __init__(self) -> None:
        self.pages: list[PdfPage] = []

    def add_page(self, width: float, height: float) -> PdfPage:
        page = PdfPage(width=width, height=height)
        self.pages.append(page)
        return page

    def to_bytes(self) -> bytes:
        objects: list[bytes] = []

        def add_object(data: str | bytes) -> int:
            payload = data.encode("latin-1") if isinstance(data, str) else data
            objects.append(payload)
            return len(objects)

        font_obj = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        page_refs: list[int] = []

        for page in self.pages:
            stream = "\n".join(page.commands).encode("latin-1")
            content_ref = add_object(
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            )
            page_ref = add_object(
                (
                    "<< /Type /Page /Parent 0 0 R /MediaBox [0 0 "
                    f"{page.width:.2f} {page.height:.2f}] "
                    f"/Contents {content_ref} 0 R /Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
                )
            )
            page_refs.append(page_ref)

        kids = " ".join(f"{ref} 0 R" for ref in page_refs)
        pages_obj = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>")
        catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

        for page_ref in page_refs:
            page_bytes = objects[page_ref - 1].decode("latin-1")
            objects[page_ref - 1] = page_bytes.replace("/Parent 0 0 R", f"/Parent {pages_obj} 0 R").encode("latin-1")

        chunks = [b"%PDF-1.4\n"]
        offsets = [0]
        current_offset = len(chunks[0])
        for obj_id, obj in enumerate(objects, start=1):
            offsets.append(current_offset)
            prefix = f"{obj_id} 0 obj\n".encode("ascii")
            suffix = b"\nendobj\n"
            chunks.extend([prefix, obj, suffix])
            current_offset += len(prefix) + len(obj) + len(suffix)

        xref_offset = current_offset
        chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        chunks.append(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
        chunks.append(
            (
                f"trailer << /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("ascii")
        )
        return b"".join(chunks)
