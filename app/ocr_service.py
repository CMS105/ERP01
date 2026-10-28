import io
import re
from datetime import datetime
from typing import Any, Optional, List, Dict, Tuple

try:
    import pytesseract
    from PIL import Image, ImageOps
except ImportError:
    pytesseract = None
    Image = None
    ImageOps = None

MAX_BYTES = 8 * 1024 * 1024  # 8 MB upload limit

CUSTOMER_RE = re.compile(r"\bC\d{5}\b", re.IGNORECASE)
LOOSE_ID_RE = re.compile(r"\bC[0-9OQDIlSB]{5}\b")
_FIX = str.maketrans("OQDIlSB", "0001158")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
MODE_RE = re.compile(r"\b(CASH|UPI)\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(?<![\w.])(\d{2,5})(?:\.\d{1,2})?(?![\w])")


def available_lang(preferred: str = "eng") -> str:
    """Use English + Kannada if installed, otherwise English only."""
    if not pytesseract:
        return "eng"
    try:
        installed = set(pytesseract.get_languages(config=""))
        wanted = preferred.split("+")
        ok = [l for l in wanted if l in installed]
        return "+".join(ok) if ok else "eng"
    except Exception:
        return "eng"


def preprocess(img) -> Any:
    if not ImageOps:
        return img
    img = ImageOps.exif_transpose(img)      # fix phone-camera rotation
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    if img.width < 1500:                    # small photos OCR badly, so upscale
        scale = 1500 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    return img


def extract_lines(image_bytes: bytes, lang: str | None = None):
    """Returns (lines, avg_confidence). Each line is {'text', 'conf'}."""
    if not pytesseract or not Image:
        raise ValueError("OCR service unavailable: pytesseract/Pillow library not installed on host")
    if len(image_bytes) > MAX_BYTES:
        raise ValueError("Image too large (max 8 MB)")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        raise ValueError("Not a valid image file")

    img = preprocess(img)
    data = pytesseract.image_to_data(
        img, lang=lang or available_lang(), output_type=pytesseract.Output.DICT
    )

    grouped = {}
    for i, word in enumerate(data["text"]):
        word = word.strip()
        conf = float(data["conf"][i])
        if not word or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        grouped.setdefault(key, []).append((word, conf))

    lines, all_conf = [], []
    for key in sorted(grouped):
        words = grouped[key]
        text = " ".join(w for w, _ in words)
        confs = [c for _, c in words]
        lines.append({"text": text, "conf": round(sum(confs) / len(confs), 1)})
        all_conf.extend(confs)

    avg = round(sum(all_conf) / len(all_conf), 1) if all_conf else 0.0
    return lines, avg


def _normalise_date(raw: str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_lines(lines):
    """Pull customer_id, date, mode and amount out of each line.
    Every row is marked for human review; OCR is never trusted blindly."""
    rows = []
    for ln in lines:
        text = ln["text"]
        cust = CUSTOMER_RE.search(text)
        repaired = False
        if not cust:
            cust = LOOSE_ID_RE.search(text)
            repaired = cust is not None
        date = DATE_RE.search(text)
        mode = MODE_RE.search(text)

        # Remove the pieces already matched so their digits aren't read as amounts
        rest = text
        for m in (cust, date):
            if m:
                rest = rest.replace(m.group(0), " ")
        amounts = AMOUNT_RE.findall(rest)

        if not (cust or amounts):
            continue  # headings, noise

        row = {
            "customer_id": ("C" + cust.group(0)[1:].translate(_FIX)) if cust else None,
            "id_corrected": repaired,
            "date": _normalise_date(date.group(1)) if date else None,
            "mode": mode.group(1).upper() if mode else None,
            "amount": float(amounts[0]) if amounts else None,
            "source_text": text,
            "line_confidence": ln["conf"],
        }
        row["needs_attention"] = (
            row["customer_id"] is None or row["amount"] is None
            or repaired or ln["conf"] < 60
        )
        rows.append(row)
    return rows
