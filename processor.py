
"""
CLI/Library module to duplicate any PDF page vertically with a configurable gap.
Usage (CLI):
    python processor.py input.pdf output.pdf --page 0 --gap 0.12
"""
import io
import argparse
from pypdf import PdfReader, PdfWriter, Transformation

POINTS_PER_INCH = 72.0

def stack_two_labels_vert_bytes(pdf_bytes: bytes, page_index: int = 0, gap_in_inches: float = 0.12) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")

    label_page = reader.pages[page_index]
    w = float(label_page.mediabox.right) - float(label_page.mediabox.left)
    h = float(label_page.mediabox.top) - float(label_page.mediabox.bottom)
    gap_pts = gap_in_inches * POINTS_PER_INCH
    out_h = h * 2 + gap_pts

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=w, height=out_h)
    out_page.merge_transformed_page(label_page, Transformation().translate(0, 0))
    out_page.merge_transformed_page(label_page, Transformation().translate(0, h + gap_pts))

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def stack_two_labels_vert_file(in_path: str, out_path: str, page_index: int = 0, gap_in_inches: float = 0.12) -> None:
    with open(in_path, "rb") as f:
        pdf_bytes = f.read()
    out = stack_two_labels_vert_bytes(pdf_bytes, page_index, gap_in_inches)
    with open(out_path, "wb") as f:
        f.write(out)

def _cli():
    p = argparse.ArgumentParser(description="Duplicate a PDF page vertically with a gap.")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--page", type=int, default=0, help="0-based page index to duplicate (default 0)")
    p.add_argument("--gap", type=float, default=0.12, help="Gap in inches between the two copies (default 0.12)")
    args = p.parse_args()
    stack_two_labels_vert_file(args.input, args.output, page_index=args.page, gap_in_inches=args.gap)

if __name__ == "__main__":
    _cli()
