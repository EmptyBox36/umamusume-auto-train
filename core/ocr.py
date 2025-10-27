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
  # read only digits and % to cut noise
  result = reader.readtext(np.array(pil_img), allowlist="0123456789%")  # keeps '%', drops letters:contentReference[oaicite:0]{index=0}
  s = " ".join(t[1] for t in result)

  s = s.replace("O", "0").replace("o", "0").replace("l", "1")
  # capture up to 3 digits immediately before % allowing spaces between digits
  matches = re.findall(r"(\d{1,3})\s*%?", s)
  if not matches:
      return -1

  # normalize spaces, keep 0–100, prefer 2–3 digit candidates
  cands = []
  for m in matches:
      v = int(re.sub(r'\s+', '', m))
      if 0 <= v <= 100:
          cands.append(v)
  if not cands:
      return -1

  # prefer longer numbers to avoid 3 from 33
  cands.sort(key=lambda x: (len(str(x)), x), reverse=True)
  v = cands[0]
  return v if v >= 5 else -1