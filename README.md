
# PDF Label Duplicator (Vertical)

This tool takes **any PDF** (typically a single-label design), and outputs a **single page** PDF containing **two copies stacked vertically** with a configurable **gap** (default **0.12 inch**). No rotation, scaling, or overlay effects are applied.

- Input example: 4" × 1" label PDF
- Output: 4" × (2 × 1" + 0.12") = 4" × 2.12"

## Features
- Accepts any PDF size (uses the input width; height becomes `2 × input_height + gap`)
- Choose which page to duplicate if the input has multiple pages
- Streamlit web UI for drag‑and‑drop & download
- CLI module for batch/automation

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## CLI Usage

```bash
python processor.py input.pdf output.pdf --page 0 --gap 0.12
```

## Deploy on Streamlit Cloud
1. Push this folder to a **GitHub repo**.
2. In Streamlit Community Cloud, create a new app → point to `app.py`.
3. Add `requirements.txt`; Streamlit will install dependencies automatically.
4. Done — upload a PDF and download your stacked output.

## Notes
- PDF units are **points** (1 in = 72 pt). The gap is converted from inches to points.
- The output page **width** equals input page width; **height** equals `input_height*2 + gap`.
- If the input PDF has rotations or cropboxes, this app keeps the media box as-is (no additional rotation/scale).
