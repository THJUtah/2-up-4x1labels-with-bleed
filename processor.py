
"""
CLI/Library module to duplicate any PDF page vertically with a configurable gap.
Bottom-aligned: first label at y=0; second at y = h + gap.

Usage (CLI):
    python processor.py input.pdf output.pdf --page 0 --gap 0.12 [--use-cropbox]
"""
import io
import argparse
from pypdf import PdfReader, PdfWriter, Transformation

POINTS_PER_INCH = 72.0

def _get_box(page, use_cropbox: bool):
    return page.cropbox if use_cropbox and page.cropbox is not None else page.mediabox

def _get_dims(page, use_cropbox: bool):
    box = _get_box(page, use_cropbox)
    llx = float(box.left);  lly = float(box.bottom)
    urx = float(box.right); ury = float(box.top)
    return llx, lly, (urx-llx), (ury-lly)

def stack_two_labels_vert_bytes(pdf_bytes: bytes, page_index: int = 0, gap_in_inches: float = 0.12, use_cropbox: bool=False) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")

    label_page = reader.pages[page_index]
    llx, lly, w, h = _get_dims(label_page, use_cropbox)

    gap_pts = gap_in_inches * POINTS_PER_INCH
    out_h = h * 2 + gap_pts

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=w, height=out_h)

    base_t = Transformation().translate(-llx, -lly)

    out_page.merge_transformed_page(label_page, base_t)  # bottom at y=0
    out_page.merge_transformed_page(label_page, base_t.translate(0, h + gap_pts))  # second above with gap

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def stack_two_labels_vert_file(in_path: str, out_path: str, page_index: int = 0, gap_in_inches: float = 0.12, use_cropbox: bool=False) -> None:
    with open(in_path, "rb") as f:
        pdf_bytes = f.read()
    out = stack_two_labels_vert_bytes(pdf_bytes, page_index, gap_in_inches, use_cropbox)
    with open(out_path, "wb") as f:
        f.write(out)

def _cli():
    p = argparse.ArgumentParser(description="Duplicate a PDF page vertically with a gap (bottom-aligned).")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--page", type=int, default=0, help="0-based page index to duplicate (default 0)")
    p.add_argument("--gap", type=float, default=0.12, help="Gap in inches between the two copies (default 0.12)")
    p.add_argument("--use-cropbox", action="store_true", help="Use the PDF CropBox instead of MediaBox for sizing/placement")
    args = p.parse_args()
    stack_two_labels_vert_file(args.input, args.output, page_index=args.page, gap_in_inches=args.gap, use_cropbox=args.use_cropbox)

if __name__ == "__main__":
    _cli()
