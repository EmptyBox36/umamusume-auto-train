import easyocr
from PIL import Image
import numpy as np
import re

reader = easyocr.Reader(["en"], gpu=False)

def extract_text(pil_img: Image.Image) -> str:
  img_np = np.array(pil_img)
  result = reader.readtext(img_np)
  texts = [text[1] for text in result]
  return " ".join(texts)

def extract_number(pil_img: Image.Image) -> int:
  img_np = np.array(pil_img)
  result = reader.readtext(img_np, allowlist="0123456789")
  texts = [text[1] for text in result]
  joined_text = "".join(texts)

  digits = re.sub(r"[^\d]", "", joined_text)

  if digits:
    return int(digits)
  
  return -1

def extract_percent(pil_img: Image.Image) -> int:
    """
    Reads OCR text and extracts the most plausible percent (0–100).
    Returns -1 if no valid percent found.
    """
    img_np = np.array(pil_img)
    result = reader.readtext(img_np, allowlist="0123456789%")
    texts = [t[1] for t in result]
    txt = "".join(texts)

    import re
    matches = re.findall(r"\d{1,3}", txt)
    if not matches:
        return -1

    vals = [int(m) for m in matches if 0 <= int(m) <= 100]
    if not vals:
        return -1

    # pick the largest plausible value to avoid OCR truncation like 3→33
    v = max(vals)
    if v < 5:   # discard small isolated misreads
        return -1
    return v