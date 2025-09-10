import io
import streamlit as st
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

def build_two_labels(pdf_bytes: bytes,
                     page_index: int,
                     die_gap_in: float,
                     scale_percent: float,
                     use_cropbox: bool) -> bytes:
    """Create a single-page PDF with exactly TWO vertically stacked labels.
       - Vertical-only scale = 1 + scale_percent/100 (centers locked)
       - Gap is exact (die_gap_in)
       - Page height expanded so added bleed isn’t clipped
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")

    src = reader.pages[page_index]
    llx, lly, w_pts, h_pts = get_dims_from_box(src, use_cropbox)

    gap_pts = die_gap_in * POINTS_PER_INCH
    sy = 1.0 + (scale_percent / 100.0)  # vertical-only scale factor

    # Page geometry:
    # original two labels + gap = 2*h_pts + gap_pts
    # vertical scaling adds sy*H - H = (sy-1)*H total across extremes (half on bottom, half on top)
    extra_height = (sy - 1.0) * h_pts
    out_w = w_pts
    out_h = (2 * h_pts) + gap_pts + extra_height

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=out_w, height=out_h)

    # Distribute the extra height equally to bottom and top so centers stay where they should:
    bottom_margin = extra_height / 2.0

    # Base transform maps chosen box LL to origin
    base = Transformation().translate(-llx, -lly)

    # Centerlines (unchanged by scaling):
    # label 0 center: bottom_margin + h/2
    # label 1 center: bottom_margin + h + gap + h/2
    c0 = bottom_margin + (h_pts / 2.0)
    c1 = bottom_margin + h_pts + gap_pts + (h_pts / 2.0)

    # To scale about the center: T = Translate(0, c) * Scale(1, sy) * Translate(0, -c) * base
    # pypdf composes left->right on calls; we build per-label transforms accordingly
    t0 = base.translate(0, c0).scale(1.0, sy).translate(0, -c0)
    t1 = base.translate(0, c1).scale(1.0, sy).translate(0, -c1)

    out_page.merge_transformed_page(src, t0)  # bottom label
    out_page.merge_transformed_page(src, t1)  # top label

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

# ---------------- UI ----------------

st.set_page_config(page_title="Two-Label Builder (Fixed Gap + 2% Vertical Bleed)", page_icon="📏", layout="centered")
st.title("Two-Label Builder")
st.write("Outputs **exactly two labels** stacked vertically. Keeps **die gap exact**, and adds **vertical bleed** by scaling each label about its center.")

uploaded = st.file_uploader("Upload a label PDF", type=["pdf"])

# Inputs (4-decimal precision for gap; % with two decimals)
col1, col2 = st.columns(2)
with col1:
    gap_in = st.number_input("Die gap (inches)", min_value=0.0, value=0.1875, step=0.0001, format="%.4f")
with col2:
    scale_percent = st.number_input("Vertical bleed scale (%)", min_value=0.0, value=2.00, step=0.01, format="%.2f")

box_choice = st.radio("Use which box for placement?", ["MediaBox (default)", "CropBox"], index=0, horizontal=True)
use_cropbox = (box_choice == "CropBox")

if uploaded is not None:
    data = uploaded.read()
    reader = PdfReader(io.BytesIO(data))
    total_pages = len(reader.pages)

    # Show both box sizes for page 0 for clarity
    mb = reader.pages[0].mediabox
    cb = reader.pages[0].cropbox if reader.pages[0].cropbox is not None else None

    def dims(box):
        if box is None: return None
        llx = float(box.left); lly = float(box.bottom)
        urx = float(box.right); ury = float(box.top)
        return (urx-llx)/72.0, (ury-lly)/72.0

    mb_dims = dims(mb)
    cb_dims = dims(cb) if cb else None

    info = f"Pages: **{total_pages}** | MediaBox: **{mb_dims[0]:.4f}×{mb_dims[1]:.4f} in**"
    if cb_dims: info += f" | CropBox: **{cb_dims[0]:.4f}×{cb_dims[1]:.4f} in**"
    st.info(info)

    page_idx = 0
    if total_pages > 1:
        page_idx = st.number_input("Choose page (0-based)", min_value=0, max_value=total_pages-1, value=0, step=1)

    if st.button("Build 2-up PDF"):
        try:
            out_bytes = build_two_labels(
                data,
                page_idx,
                float(gap_in),
                float(scale_percent),
                use_cropbox
            )

            # Report the final output size:
            llx, lly, w_pts, h_pts = get_dims_from_box(reader.pages[page_idx], use_cropbox)
            sy = 1.0 + (float(scale_percent)/100.0)
            extra_height = (sy - 1.0) * h_pts
            out_h_in = (2*h_pts + gap_in*72.0 + extra_height)/72.0

            out_name = uploaded.name.replace(".pdf", "") + f"_2up_gap{gap_in:.4f}in_scale{scale_percent:.2f}pct.pdf"
            st.success(f"Done! Output page size: {w_pts/72.0:.4f} in × {out_h_in:.4f} in")
            st.download_button("Download 2-up PDF", data=out_bytes, file_name=out_name, mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.caption("Centers stay fixed; die gap stays exact. The page height expands so the 2% vertical bleed isn’t clipped.")
