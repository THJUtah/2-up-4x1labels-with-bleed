
import io
import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from typing import Tuple

POINTS_PER_INCH = 72.0

def get_page_size_pts(page) -> Tuple[float, float]:
    mb = page.mediabox
    width = float(mb.right) - float(mb.left)
    height = float(mb.top) - float(mb.bottom)
    return width, height

def stack_two_labels_vert(pdf_bytes: bytes, page_index: int = 0, gap_in_inches: float = 0.12) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    n = len(reader.pages)
    if n == 0:
        raise ValueError("PDF has no pages.")
    if page_index < 0 or page_index >= n:
        raise IndexError(f"Page index {page_index} out of range 0..{n-1}")
    label_page = reader.pages[page_index]

    # Original size (points)
    w_pts, h_pts = get_page_size_pts(label_page)

    gap_pts = gap_in_inches * POINTS_PER_INCH
    out_h = h_pts * 2 + gap_pts

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=w_pts, height=out_h)

    # Bottom copy at y = 0
    out_page.merge_transformed_page(label_page, Transformation().translate(tx=0, ty=0))

    # Top copy at y = h_pts + gap_pts
    out_page.merge_transformed_page(label_page, Transformation().translate(tx=0, ty=h_pts + gap_pts))

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

st.set_page_config(page_title="PDF Label Duplicator (Vertical Gap)", page_icon="🍯", layout="centered")

st.title("PDF Label Duplicator (Vertical • 0.12\" gap by default)")
st.write(
    "Upload any single‑label PDF. This tool stacks **two copies vertically** with a configurable gap (default: 0.12 inch). "
    "No rotation or scaling is applied."
)

uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
gap = st.number_input("Gap (inches)", min_value=0.0, value=0.12, step=0.01, format="%.2f")

if uploaded is not None:
    data = uploaded.read()
    reader = PdfReader(io.BytesIO(data))
    total_pages = len(reader.pages)
    w_pts, h_pts = None, None
    if total_pages > 0:
        w_pts, h_pts = float(reader.pages[0].mediabox.right) - float(reader.pages[0].mediabox.left), \
                       float(reader.pages[0].mediabox.top) - float(reader.pages[0].mediabox.bottom)

    st.info(f"Detected pages: **{total_pages}**. First page size: **{w_pts/72.0:.3f} in × {h_pts/72.0:.3f} in**.")    

    page_idx = 0
    if total_pages > 1:
        page_idx = st.number_input("Choose page index (0‑based)", min_value=0, max_value=total_pages-1, value=0, step=1)

    if st.button("Create stacked PDF"):
        try:
            out_bytes = stack_two_labels_vert(data, page_index=page_idx, gap_in_inches=gap)
            out_name = uploaded.name.replace(".pdf", "") + f"_stacked_gap_{gap:.2f}in.pdf"
            st.success("Done! Download your new PDF below.")
            st.download_button("Download stacked PDF", data=out_bytes, file_name=out_name, mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.caption("Tip: Your source PDF can be any dimensions. The output width matches the input; height = (2 × input height) + gap.")
