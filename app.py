import io
import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation

POINTS_PER_INCH = 72.0

# === Spec constants ===
PAGE_W_IN = 4.02
PAGE_H_IN = 2.1875
GAP_IN     = 0.1875  # between labels, and an extra one above the top label
SCALE_PCT  = 0.005   # scale both X and Y by +0.005% for micro-bleed

def get_box(page, use_cropbox: bool):
    return page.cropbox if use_cropbox and page.cropbox is not None else page.mediabox

def get_dims_from_box(page, use_cropbox: bool):
    box = get_box(page, use_cropbox)
    llx = float(box.left); lly = float(box.bottom)
    urx = float(box.right); ury = float(box.top)
    return llx, lly, (urx-llx), (ury-lly)

def build_two_up_fixed(pdf_bytes: bytes, page_index: int, use_cropbox: bool) -> bytes:
    """
    Build a single-page PDF that is exactly 4.02" x 2.375", with:
      - Two labels stacked vertically
      - 0.1875" gap BETWEEN labels
      - 0.1875" gap ABOVE the top label
      - Bottom label starts at y = 0 (no extra bottom gap)
      - Uploaded art is scaled by +0.005% (both axes) to create a hairline bleed
      - Each label is centered horizontally on the 4.02" page
      - Each label is centered vertically within its own 1.0" die area, so bleed is symmetric
    """
    # Read source
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")
    if not (0 <= page_index < len(reader.pages)):
        raise IndexError(f"Page index {page_index} out of range 0..{len(reader.pages)-1}")
    src = reader.pages[page_index]

    # Units
    page_w_pts = PAGE_W_IN * POINTS_PER_INCH
    page_h_pts = PAGE_H_IN * POINTS_PER_INCH
    gap_pts    = GAP_IN     * POINTS_PER_INCH

    # Source box & size
    llx, lly, w_pts, h_pts = get_dims_from_box(src, use_cropbox)

    # Intended die geometry vertically:
    # bottom label die: [0.00", 1.00"]
    # gap between:      [1.00", 1.1875"]
    # top label die:    [1.1875", 2.1875"]
    # extra top gap:    [2.1875", 2.375"]
    die_h_pts = 1.0 * POINTS_PER_INCH
    # Label centers (die centers):
    c0_y = 0.5 * POINTS_PER_INCH
    c1_y = (1.0 + GAP_IN + 0.5) * POINTS_PER_INCH  # 1.1875 + 0.5 = 1.6875 in => 121.5 pts

    # Horizontal center for the page (we center labels horizontally)
    cx_x = page_w_pts / 2.0

    # Scale (both axes) by +0.005%
    s = 1.0 + (SCALE_PCT / 100.0)
    placed_w = w_pts * s
    placed_h = h_pts * s

    # Place each label so its scaled art is centered on the die center
    # Since we scale from the origin, we translate to LL of the scaled art:
    # x_left = cx_x - placed_w/2 ; y_bottom = c_y - placed_h/2
    x_left = cx_x - (placed_w / 2.0)
    y0_bottom = c0_y - (placed_h / 2.0)
    y1_bottom = c1_y - (placed_h / 2.0)

    # Compose transforms robustly: translate LL of chosen box to (0,0) -> uniform scale -> place
    base = Transformation().translate(-llx, -lly).scale(s, s)

    t0 = base.translate(x_left, y0_bottom)
    t1 = base.translate(x_left, y1_bottom)

    # Build output page
    writer = PdfWriter()
    out_page = writer.add_blank_page(width=page_w_pts, height=page_h_pts)
    out_page.merge_transformed_page(src, t0)
    out_page.merge_transformed_page(src, t1)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

# ---------------- UI ----------------
st.set_page_config(page_title="Two-Up (4.02\" × 2.375\") w/ 0.1875\" Gaps + 0.005% Bleed", page_icon="📏", layout="centered")
st.title("Two-Up Label Builder")
st.write("Outputs a single page at **4.02\" × 2.375\"** with **two labels**, an exact **0.1875\"** gap between labels, an extra **0.1875\"** gap above the top label, and a **0.005%** scale applied for micro-bleed.")

uploaded = st.file_uploader("Upload a label PDF (any size; no rotation applied)", type=["pdf"])
box_choice = st.radio("Use which box for placement?", ["MediaBox (default)", "CropBox"], index=0, horizontal=True)
use_cropbox = (box_choice == "CropBox")

if uploaded is not None:
    data = uploaded.read()
    reader = PdfReader(io.BytesIO(data))
    total_pages = len(reader.pages)

    # Show source dimensions for page 0
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
    st.caption('Output is ALWAYS **4.0200" × 2.3750"**; art is scaled by **0.005%** and centered for bleed.')

    page_idx = 0
    if total_pages > 1:
        page_idx = st.number_input("Choose page (0-based)", min_value=0, max_value=total_pages-1, value=0, step=1)

    if st.button("Build 2-up PDF"):
        try:
            out_bytes = build_two_up_fixed(data, page_idx, use_cropbox)
            out_name = uploaded.name.replace(".pdf", "") + f"_2up_4.0200x2.3750_gap0.1875_scale0.005pct.pdf"
            st.success('Done! Download below.')
            st.download_button("Download 2-up PDF", data=out_bytes, file_name=out_name, mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.caption("Print at 100% onto your 4\" × 1\" labels. The 4.02\" page width gives horizontal bleed; the 2.375\" height fits 2 labels + gaps.")
