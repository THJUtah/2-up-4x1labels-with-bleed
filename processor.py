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

def build_strip_bytes(pdf_bytes: bytes, page_index: int, count: int, die_gap_in: float, bleed_in: float, use_cropbox: bool, scale_for_bleed: bool) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")

    src = reader.pages[page_index]
    llx, lly, w_pts, h_pts = _get_dims(src, use_cropbox)
    gap_pts = die_gap_in * POINTS_PER_INCH
    bleed_pts = bleed_in * POINTS_PER_INCH

    out_w = w_pts
    out_h = count * h_pts + (count - 1) * gap_pts + 2 * bleed_pts

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=out_w, height=out_h)

    base_t = Transformation().translate(-llx, -lly)

    if scale_for_bleed and h_pts > 0:
        scale_y = (h_pts + 2 * bleed_pts) / h_pts
        base_t = base_t.scale(1.0, scale_y)
        placed_h = h_pts * scale_y
    else:
        placed_h = h_pts + 2 * bleed_pts

    for i in range(count):
        y_center = bleed_pts + i * (h_pts + gap_pts) + h_pts / 2.0
        y_bottom = y_center - placed_h / 2.0
        t = base_t.translate(0, y_bottom)
        out_page.merge_transformed_page(src, t)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def build_strip_file(in_path: str, out_path: str, page_index: int, count: int, die_gap_in: float, bleed_in: float, use_cropbox: bool, scale_for_bleed: bool) -> None:
    with open(in_path, "rb") as f:
        pdf_bytes = f.read()
    out = build_strip_bytes(pdf_bytes, page_index, count, die_gap_in, bleed_in, use_cropbox, scale_for_bleed)
    with open(out_path, "wb") as f:
        f.write(out)

def _cli():
    p = argparse.ArgumentParser(description="Build a strip of N labels with fixed die gap and bleed.")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--page", type=int, default=0, help="0-based page index to duplicate (default 0)")
    p.add_argument("--count", type=int, default=10, help="Number of labels to stack")
    p.add_argument("--gap", type=float, default=0.1875, help="Die gap in inches between labels (default 0.1875)")
    p.add_argument("--bleed", type=float, default=0.06, help="Bleed in inches (top & bottom)")
    p.add_argument("--use-cropbox", action="store_true", help="Use the PDF CropBox instead of MediaBox")
    p.add_argument("--scale-for-bleed", action="store_true", help="Scale vertically so placed art height = label_h + 2*bleed")
    args = p.parse_args()
    build_strip_file(args.input, args.output, args.page, args.count, args.gap, args.bleed, args.use_cropbox, args.scale_for_bleed)

if __name__ == "__main__":
    _cli()
