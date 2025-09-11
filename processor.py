import io
import argparse
from pypdf import PdfReader, PdfWriter, Transformation

POINTS_PER_INCH = 72.0
PAGE_W_IN = 4.02
PAGE_H_IN = 2.30
GAP_IN     = 0.1875
SCALE_PCT  = 0.005

def _get_box(page, use_cropbox: bool):
    return page.cropbox if use_cropbox and page.cropbox is not None else page.mediabox

def _dims(page, use_cropbox: bool):
    box = _get_box(page, use_cropbox)
    llx = float(box.left); lly = float(box.bottom)
    urx = float(box.right); ury = float(box.top)
    return llx, lly, (urx-llx), (ury-lly)

def build_two_up_fixed_bytes(pdf_bytes: bytes, page_index: int, use_cropbox: bool) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")

    src = reader.pages[page_index]
    llx, lly, w_pts, h_pts = _dims(src, use_cropbox)

    page_w_pts = PAGE_W_IN * POINTS_PER_INCH
    page_h_pts = PAGE_H_IN * POINTS_PER_INCH
    gap_pts    = GAP_IN     * POINTS_PER_INCH

    # Die centers at 0.5" and 1.6875"
    c0_y = 0.5 * POINTS_PER_INCH
    c1_y = (1.0 + GAP_IN + 0.5) * POINTS_PER_INCH

    cx_x = (PAGE_W_IN * POINTS_PER_INCH) / 2.0

    s = 1.0 + (SCALE_PCT / 100.0)
    placed_w = w_pts * s
    placed_h = h_pts * s

    x_left    = cx_x - (placed_w / 2.0)
    y0_bottom = c0_y - (placed_h / 2.0)
    y1_bottom = c1_y - (placed_h / 2.0)

    base = Transformation().translate(-llx, -lly).scale(s, s)
    t0 = base.translate(x_left, y0_bottom)
    t1 = base.translate(x_left, y1_bottom)

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=page_w_pts, height=page_h_pts)
    out_page.merge_transformed_page(src, t0)
    out_page.merge_transformed_page(src, t1)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def build_two_up_fixed_file(in_path: str, out_path: str, page_index: int, use_cropbox: bool):
    with open(in_path, "rb") as f:
        pdf_bytes = f.read()
    out = build_two_up_fixed_bytes(pdf_bytes, page_index, use_cropbox)
    with open(out_path, "wb") as f:
        f.write(out)

def _cli():
    p = argparse.ArgumentParser(description="Two-up label builder: 4.02\"×2.375\" page, 0.1875\" gaps, +0.005% scale bleed.")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--page", type=int, default=0, help="0-based page index (default 0)")
    p.add_argument("--use-cropbox", action="store_true", help="Use CropBox (default uses MediaBox)")
    args = p.parse_args()
    build_two_up_fixed_file(args.input, args.output, args.page, args.use_cropbox)

if __name__ == "__main__":
    _cli()
