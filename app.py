import io
import streamlit as st
from typing import Tuple
from pypdf import PdfReader, PdfWriter, Transformation

POINTS_PER_INCH = 72.0

def get_box(page, use_cropbox: bool):
    return page.cropbox if use_cropbox and page.cropbox is not None else page.mediabox

def get_dims_from_box(page, use_cropbox: bool):
    box = get_box(page, use_cropbox)
    llx = float(box.left); lly = float(box.bottom)
    urx = float(box.right); ury = float(box.top)
    w = urx - llx; h = ury - lly
    return llx, lly, w, h

def build_strip(pdf_bytes: bytes,
                page_index: int,
                count: int,
                die_gap_in: float,
                bleed_in: float,
                use_cropbox: bool,
                scale_for_bleed: bool) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")
    src = reader.pages[page_index]

    llx, lly, w_pts, h_pts = get_dims_from_box(src, use_cropbox)
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

st.set_page_config(page_title="Label Strip Builder (Fixed Die Gap + Bleed)", page_icon="📏", layout="centered")
st.title("Label Strip Builder")
st.write("Build a **single PDF strip** of N labels with a fixed **die gap** and optional **top/bottom bleed**.")
st.caption("First label is bottom-aligned. Centers stay locked; bleed adjusts the overlap only.")

uploaded = st.file_uploader("Upload a label PDF", type=["pdf"])
col1, col2 = st.columns(2)
with col1:
    count = st.number_input("Number of labels (N)", min_value=1, value=10, step=1)
    gap_in = st.number_input("Die gap (inches)", min_value=0.0, value=0.1875, step=0.01, format="%.2f")
with col2:
    bleed_in = st.number_input("Bleed (inches, top & bottom)", min_value=0.0, value=0.06, step=0.01, format="%.2f")
    scale_for_bleed = st.checkbox("Scale vertically to create bleed if needed", value=False)

box_choice = st.radio("Use which box for placement?", ["MediaBox (default)", "CropBox"], index=0, horizontal=True)
use_cropbox = (box_choice == "CropBox")

if uploaded is not None:
    data = uploaded.read()
    reader = PdfReader(io.BytesIO(data))
    total_pages = len(reader.pages)

    mb = reader.pages[0].mediabox
    cb = reader.pages[0].cropbox if reader.pages[0].cropbox is not None else None

    def dims(box):
        if box is None: return None
        llx = float(box.left); lly = float(box.bottom)
        urx = float(box.right); ury = float(box.top)
        return (urx-llx)/72.0, (ury-lly)/72.0

    mb_dims = dims(mb)
    cb_dims = dims(cb) if cb else None

    info = f"Pages: **{total_pages}** | MediaBox: **{mb_dims[0]:.3f}×{mb_dims[1]:.3f} in**"
    if cb_dims: info += f" | CropBox: **{cb_dims[0]:.3f}×{cb_dims[1]:.3f} in**"
    st.info(info)

    page_idx = 0
    if total_pages > 1:
        page_idx = st.number_input("Choose page (0-based)", min_value=0, max_value=total_pages-1, value=0, step=1)

    if st.button("Build strip PDF"):
        try:
            out_bytes = build_strip(data, page_idx, int(count), float(gap_in), float(bleed_in), use_cropbox, bool(scale_for_bleed))
            _, _, w_pts, h_pts = get_dims_from_box(reader.pages[page_idx], use_cropbox)
            out_h_in = (int(count)*h_pts + (int(count)-1)*gap_in*72.0 + 2*bleed_in*72.0)/72.0
            out_name = uploaded.name.replace(".pdf", "") + f"_strip_{count}x_gap{gap_in:.2f}in_bleed{bleed_in:.2f}in.pdf"
            st.success(f"Done! Output page size: {w_pts/72.0:.3f} in × {out_h_in:.3f} in")
            st.download_button("Download strip PDF", data=out_bytes, file_name=out_name, mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.caption("Tip: If your printer rounds to two decimals, the engine still uses exact math internally to keep centerlines and die gap precise.")
