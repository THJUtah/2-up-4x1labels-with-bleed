
import io
import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from typing import Tuple

POINTS_PER_INCH = 72.0

def get_box(page, use_cropbox: bool):
    return page.cropbox if use_cropbox and page.cropbox is not None else page.mediabox

def get_page_size_pts(page, use_cropbox: bool) -> Tuple[float, float, float, float]:
    box = get_box(page, use_cropbox)
    llx = float(box.left);  lly = float(box.bottom)
    urx = float(box.right); ury = float(box.top)
    return llx, lly, (urx-llx), (ury-lly)

def stack_two_labels_vert(pdf_bytes: bytes, page_index: int = 0, gap_in_inches: float = 0.12, use_cropbox: bool = False) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    n = len(reader.pages)
    if n == 0:
        raise ValueError("PDF has no pages.")
    if page_index < 0 or page_index >= n:
        raise IndexError(f"Page index {page_index} out of range 0..{n-1}")
    label_page = reader.pages[page_index]

    llx, lly, w_pts, h_pts = get_page_size_pts(label_page, use_cropbox)

    gap_pts = gap_in_inches * POINTS_PER_INCH
    out_h = h_pts * 2 + gap_pts

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=w_pts, height=out_h)

    # Translate so the chosen box's lower-left maps to (0,0)
    base_transform = Transformation().translate(tx=-llx, ty=-lly)

    # Bottom copy at y = 0
    out_page.merge_transformed_page(label_page, base_transform)

    # Top copy at y = h_pts + gap_pts
    out_page.merge_transformed_page(label_page, base_transform.translate(tx=0, ty=h_pts + gap_pts))

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

st.set_page_config(page_title="PDF Label Duplicator (Vertical Gap)", page_icon="🍯", layout="centered")

st.title("PDF Label Duplicator (Vertical • Bottom-aligned)")
st.write(
    "The first label starts **at the bottom (y=0)**. The second label is placed **above it** with the specified gap. "
    "No rotation or scaling."
)

uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
gap = st.number_input("Gap (inches)", min_value=0.0, value=0.12, step=0.01, format="%.2f")
box_choice = st.radio("Use which box for size/placement?", ["MediaBox (default)", "CropBox"], index=0, horizontal=True)
use_cropbox = (box_choice == "CropBox")

if uploaded is not None:
    data = uploaded.read()
    reader = PdfReader(io.BytesIO(data))
    total_pages = len(reader.pages)

    # Report both mediabox and cropbox sizes for the first page
    mb = reader.pages[0].mediabox
    cb = reader.pages[0].cropbox if reader.pages[0].cropbox is not None else None

    def dims(box):
        if box is None: return None
        llx = float(box.left); lly = float(box.bottom)
        urx = float(box.right); ury = float(box.top)
        return (urx-llx)/72.0, (ury-lly)/72.0

    mb_dims = dims(mb)
    cb_dims = dims(cb) if cb else None

    info = f"Detected pages: **{total_pages}**. MediaBox: **{mb_dims[0]:.3f} in × {mb_dims[1]:.3f} in**"
    if cb_dims:
        info += f" | CropBox: **{cb_dims[0]:.3f} in × {cb_dims[1]:.3f} in**"
    st.info(info)

    page_idx = 0
    if total_pages > 1:
        page_idx = st.number_input("Choose page index (0-based)", min_value=0, max_value=total_pages-1, value=0, step=1)

    if st.button("Create stacked PDF"):
        try:
            out_bytes = stack_two_labels_vert(data, page_index=page_idx, gap_in_inches=gap, use_cropbox=use_cropbox)
            out_name = uploaded.name.replace(".pdf", "") + f"_stacked_gap_{gap:.2f}in.pdf"
            st.success("Done! Download your new PDF below.")
            st.download_button("Download stacked PDF", data=out_bytes, file_name=out_name, mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.caption("Tip: If your PDF has unexpected margins, try switching to CropBox.")
