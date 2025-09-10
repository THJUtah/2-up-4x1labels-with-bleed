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
    """
    Outputs ONE page with exactly TWO vertically stacked labels.
    Vertical-only scale (sy) creates bleed; centers effectively stay in place
    with a bottom margin = extra/2 and an enlarged page height.
    """
    import io
    from pypdf import PdfReader, PdfWriter, Transformation

    POINTS_PER_INCH = 72.0

    def _get_box(page, use_crop: bool):
        return page.cropbox if use_crop and page.cropbox is not None else page.mediabox

    def _dims(page, use_crop: bool):
        box = _get_box(page, use_crop)
        llx = float(box.left); lly = float(box.bottom)
        urx = float(box.right); ury = float(box.top)
        return llx, lly, (urx - llx), (ury - lly)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")

    src = reader.pages[page_index]
    llx, lly, w_pts, h_pts = _dims(src, use_cropbox)

    gap_pts = die_gap_in * POINTS_PER_INCH
    sy = 1.0 + (scale_percent / 100.0)          # vertical scale (e.g., 1.02 for 2%)
    placed_h = h_pts * sy                       # scaled height
    extra = placed_h - h_pts                    # added bleed height
    bottom_margin = extra / 2.0                 # give half of the bleed below the first label

    # Final page: width = original width; height = 2*placed_h + gap
    out_w = w_pts
    out_h = (2 * placed_h) + gap_pts

    writer = PdfWriter()
    out_page = writer.add_blank_page(width=out_w, height=out_h)

    # Base transform: move chosen box LL to origin, then scale vertically from origin
    base = Transformation().translate(-llx, -lly).scale(1.0, sy)

    # Bottom positions for each (AFTER scaling-from-origin):
    y0 = bottom_margin                      # first label bottom
    y1 = bottom_margin + h_pts + gap_pts    # second label bottom

    # Place both copies by translating upward from the origin
    t0 = base.translate(0, y0)
    t1 = base.translate(0, y1)

    out_page.merge_transformed_page(src, t0)
    out_page.merge_transformed_page(src, t1)

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
