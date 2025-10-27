import cv2, numpy as np, os, glob

SCALES = np.linspace(0.22, 0.36, 10)     # tuned to 512×256 -> ~180×130 ROI
THRESH  = 0.78                           # same as your test
STRICT_COLOR = 0.86
STRICT_EDGE  = 0.42

def _load_tpl(path):
    tpl = cv2.imread(path, cv2.IMREAD_UNCHANGED)          # BGRA
    if tpl is None or tpl.shape[2] < 4:
        raise RuntimeError(f"bad template: {path}")
    b,g,r,a = cv2.split(tpl)
    tpl_bgr = cv2.merge([b,g,r])
    tpl_g   = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
    mask    = (a > 8).astype(np.uint8) * 255
    return tpl_g, mask

def _safe_scales(scene_w, scene_h, tpl_w, tpl_h):
    # the largest scale that still fits into the scene
    max_s = min((scene_w - 2) / tpl_w, (scene_h - 2) / tpl_h)
    max_s = float(max(0.10, min(1.0, max_s)))         # clamp to [0.10, 1.0]
    # if the crop is extremely small, bail out
    if max_s <= 0.12:
        return []
    # start a little below max to keep room for erosion
    return np.linspace(0.18, max_s, 10)

class RaceBannerDB:
    def __init__(self, dir):
        self.items = []  # list[(name, tpl_gray, mask)]
        for p in sorted(glob.glob(os.path.join(dir, "*.png"))):
            name = os.path.splitext(os.path.basename(p))[0]
            tpl_g, mask = _load_tpl(p)
            self.items.append((name, tpl_g, mask))

    def _score_one(self, scene_g, edges, tpl_g, mask):
        H, W = scene_g.shape[:2]
        th, tw = tpl_g.shape[:2]
        best = (0.0, None, None, 0.0, 0.0)  # score, tl, (w,h), v1, v2
        for s in _safe_scales(W, H, tw, th):
            t = cv2.resize(tpl_g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            m = cv2.resize(mask, (t.shape[1], t.shape[0]), interpolation=cv2.INTER_NEAREST)
            m = cv2.erode(m, np.ones((5,5), np.uint8), 1)
            if t.shape[0] > H or t.shape[1] > W:
                continue
            r1 = cv2.matchTemplate(scene_g, t, cv2.TM_CCORR_NORMED, mask=m)
            _, v1, _, p1 = cv2.minMaxLoc(r1)
            te = cv2.Canny(t, 60, 120)
            r2 = cv2.matchTemplate(edges, te, cv2.TM_CCORR_NORMED)
            _, v2, _, _ = cv2.minMaxLoc(r2)
            score = 0.7 * v1 + 0.3 * v2
            if score > best[0]:
                best = (score, p1, (t.shape[1], t.shape[0]), v1, v2)
        return best

    def detect_name(self, crop_bgr, wanted_name, thresh=THRESH,
                    color_floor=STRICT_COLOR, edge_floor=STRICT_EDGE):
        scene_g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        edges   = cv2.Canny(scene_g, 60, 120)
        for name, tpl_g, mask in self.items:
            if name == wanted_name:
                score, tl, wh, v1, v2 = self._score_one(scene_g, edges, tpl_g, mask)
                if tl and score >= thresh and v1 >= color_floor and v2 >= edge_floor:
                    (x,y), (w,h) = tl, wh
                    return score, (x,y,w,h)
                return 0.0, None
        return 0.0, None

    def detect_any(self, crop_bgr, thresh=THRESH):
        scene_g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        edges   = cv2.Canny(scene_g, 60, 120)
        best = (0.0, None, None, None)  # score, name, (x,y), (w,h)
        for name, tpl_g, mask in self.items:
            score, tl, wh = self._score_one(scene_g, edges, tpl_g, mask)
            if score > best[0]:
                best = (score, name, tl, wh)
        score, name, tl, wh = best
        if tl and score >= thresh:
            (x,y), (w,h) = tl, wh
            return name, score, (x,y,w,h)
        return None, 0.0, None
