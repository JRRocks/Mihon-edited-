"""Color measurement on official color images (pure functions: numpy and OpenCV only).

Spec, section 4: drop black and white images, remove the line art and the edges of each part, work in OKLab (a
perceptual color space), take the most frequent tone and never the mean (the mean of a base tone and its shadow is a
color that isn't in the drawing), then keep the densest group over several images. A part gets three tones, like the
color models of animation studios: base, shadow, highlight.
"""
import math

import cv2
import numpy as np

# --- OKLab (Björn Ottosson, https://bottosson.github.io/posts/oklab/) ---------------------------------------------

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])
_M2_INV = np.linalg.inv(_M2)
_M1_INV = np.linalg.inv(_M1)


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def rgb_to_oklab(rgb):
    """sRGB (uint8, or float in [0, 1]) of shape (..., 3) to OKLab (L in [0, 1], a and b around [-0.4, 0.4])."""
    rgb = np.asarray(rgb)
    c = rgb.astype(np.float64) / 255 if rgb.dtype == np.uint8 else rgb.astype(np.float64)
    lms = srgb_to_linear(c) @ _M1.T
    return np.cbrt(lms) @ _M2.T


def oklab_to_rgb(lab):
    """OKLab to sRGB floats in [0, 1] (out-of-gamut values are clipped)."""
    lms = (np.asarray(lab, np.float64) @ _M2_INV.T) ** 3
    return linear_to_srgb(lms @ _M1_INV.T)


def oklab_to_hex(lab):
    r, g, b = np.round(oklab_to_rgb(lab) * 255).astype(int)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_oklab(code):
    code = code.lstrip("#")
    return rgb_to_oklab(np.array([int(code[i:i + 2], 16) for i in (0, 2, 4)], np.uint8))


def lch(lab):
    """Lightness, chroma and hue angle (degrees) of an OKLab color."""
    L, a, b = (float(v) for v in lab)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def delta_e(x, y):
    """Distance in OKLab (a just noticeable difference is about 0.02)."""
    return float(np.linalg.norm(np.asarray(x, np.float64) - np.asarray(y, np.float64)))


def hue_distance(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


# --- Black and white images ------------------------------------------------------------------------------------------

def colorfulness(rgb, mask=None):
    """Share of the pixels that carry a visible color (OKLab chroma above 0.05)."""
    small = rgb if max(rgb.shape[:2]) <= 512 else cv2.resize(
        rgb, None, fx=512 / max(rgb.shape[:2]), fy=512 / max(rgb.shape[:2]), interpolation=cv2.INTER_AREA)
    lab = rgb_to_oklab(small)
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    if mask is not None:
        mask = cv2.resize(mask.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        chroma = chroma[mask]
    return float((chroma > 0.05).mean()) if chroma.size else 0.0


def is_color_image(rgb, mask=None, min_share=0.03):
    """False for black and white (or nearly: a small colored logo on a gray page) images."""
    return colorfulness(rgb, mask) >= min_share


# --- One part on one image ---------------------------------------------------------------------------------------

def line_mask(rgb):
    """Ink lines: pixels clearly darker than the paper or paint around them (dark flat areas, like black hair, stay)."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    background = cv2.dilate(gray, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))).astype(np.int16)
    return (background - gray) > 40


def clean_part_mask(rgb, mask, erode=2, remove_lines=True):
    """Part pixels without their edges (anti-aliasing, neighboring parts) and without the line art."""
    mask = mask.astype(np.uint8)
    if erode:
        mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * erode + 1, 2 * erode + 1)))
    mask = mask > 0
    if remove_lines:
        mask &= ~line_mask(rgb)
    return mask


def _density(lab, l_step, ab_step):
    """Pixel counts on an OKLab grid, smoothed over the 27 neighboring cells; returns (density, cell index per pixel)."""
    il = np.clip((lab[:, 0] / l_step).astype(int), 0, int(1 / l_step))
    ia = np.clip(((lab[:, 1] + 0.5) / ab_step).astype(int), 0, int(1 / ab_step))
    ib = np.clip(((lab[:, 2] + 0.5) / ab_step).astype(int), 0, int(1 / ab_step))
    shape = (int(1 / l_step) + 3, int(1 / ab_step) + 3, int(1 / ab_step) + 3)
    counts = np.zeros(shape, np.float64)
    np.add.at(counts, (il + 1, ia + 1, ib + 1), 1)
    smooth = np.zeros_like(counts)
    for dl in (-1, 0, 1):
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                smooth += np.roll(counts, (dl, da, db), axis=(0, 1, 2))
    return smooth


def tone_peaks(lab, radius=0.045, max_peaks=6, min_share=0.02, l_step=0.025, ab_step=0.0125):
    """The most frequent tones of a set of OKLab pixels, largest first: [(tone, share)].

    Greedy mode seeking: the densest cell of a smoothed 3D histogram gives a starting point, moved to the median of the
    pixels around it until it settles; those pixels form the tone and are set aside, then the next densest cell is
    taken. Each tone is a median of real pixels close together, never an average across tones.
    """
    lab = np.asarray(lab, np.float64).reshape(-1, 3)
    total = len(lab)
    peaks = []
    remaining = lab
    while len(remaining) and len(peaks) < max_peaks:
        density = _density(remaining, l_step, ab_step)
        il, ia, ib = np.unravel_index(np.argmax(density), density.shape)
        center = np.array([(il - 1 + 0.5) * l_step, (ia - 1 + 0.5) * ab_step - 0.5, (ib - 1 + 0.5) * ab_step - 0.5])
        for _ in range(5):
            near = np.linalg.norm(remaining - center, axis=1) < radius
            if not near.any():
                break
            new = np.median(remaining[near], axis=0)
            if np.linalg.norm(new - center) < 1e-4:
                break
            center = new
        near = np.linalg.norm(remaining - center, axis=1) < radius
        share = near.sum() / total
        if share < min_share:
            break
        peaks.append((center, float(share)))
        remaining = remaining[~near]
    return peaks


def three_tones(lab, achromatic_chroma=0.035):
    """Base (most frequent tone), shadow and highlight of a part, as OKLab arrays (shadow, highlight may be None).

    The shadow is the largest darker tone of the same hue (or also gray for a gray base), the highlight the largest
    lighter one; tones of another hue belong to something else (a pattern, a neighbor's color) and are ignored.
    """
    peaks = tone_peaks(lab)
    if not peaks:
        return None
    base, base_share = peaks[0]
    bl, bc, bh = lch(base)
    shadow = highlight = None
    for tone, share in peaks[1:]:
        tl, tc, th = lch(tone)
        if bc < achromatic_chroma or tc < achromatic_chroma:
            same_family = bc < 0.08 and tc < 0.08
        else:
            same_family = hue_distance(bh, th) < 40
        if tl < bl - 0.05 and same_family and share >= 0.06 * base_share * 2 and shadow is None:
            shadow = tone
        # Highlights are often whiter than the base: same hue or less saturated
        if tl > bl + 0.05 and (same_family or tc < bc * 0.6) and share >= 0.02 and highlight is None:
            highlight = tone
    return {"base": base, "shadow": shadow, "highlight": highlight, "share": base_share}


# Minimum clean pixels for a part to be measured on one image
MIN_PIXELS = {"eyes": 12, "skin": 60, "hair": 80, "top": 120, "bottom": 120}


def measure_part(rgb, mask, part):
    """Measures one part of one character on one image. Returns None when too few pixels are left."""
    if part == "eyes":
        # Eyes are small and mostly drawn lines: no erosion, no line removal; the white of the eye is dropped
        clean = mask.astype(bool)
        lab = rgb_to_oklab(rgb[clean])
        L, C = lab[:, 0], np.hypot(lab[:, 1], lab[:, 2])
        lab = lab[~((L > 0.85) & (C < 0.05))]
    else:
        clean = clean_part_mask(rgb, mask, erode=1 if mask.sum() < 2000 else 2)
        lab = rgb_to_oklab(rgb[clean])
    if len(lab) < MIN_PIXELS.get(part, 80):
        return None
    tones = three_tones(lab)
    if tones is None:
        return None
    tones["pixels"] = int(len(lab))
    return tones


# --- Several images ------------------------------------------------------------------------------------------------

def densest_groups(values, weights=None, radius=0.08, max_groups=3):
    """Groups of close colors over several images, densest first: [{"value", "members", "weight"}].

    The center of a group is the observation with the most (weighted) neighbors within `radius`; the group value is
    the median of its members, so one odd image can't pull it.
    """
    values = np.asarray(values, np.float64).reshape(-1, 3)
    weights = np.ones(len(values)) if weights is None else np.asarray(weights, np.float64)
    left = list(range(len(values)))
    groups = []
    while left and len(groups) < max_groups:
        sub = values[left]
        dist = np.linalg.norm(sub[:, None] - sub[None], axis=2)
        support = ((dist < radius) * weights[left][None]).sum(axis=1)
        center = int(np.argmax(support))
        members = [left[i] for i in np.flatnonzero(dist[center] < radius)]
        groups.append({"value": np.median(values[members], axis=0), "members": members,
                       "weight": float(weights[members].sum())})
        left = [i for i in left if i not in members]
    return groups


# --- Words ---------------------------------------------------------------------------------------------------------

# Upper hue limits (OKLCh degrees) of the basic color names, as used by Danbooru's color tags. Measured on reference
# colors: red #ff0000 29°, orange #ff8000 53°, yellow #ffff00 110°, green 144°, cyan 195°, blue 262°, purple 304°,
# magenta 328°, pink #ff9ccf 348°
_HUES = [(40, "red"), (75, "orange"), (120, "yellow"), (175, "green"), (230, "aqua"), (290, "blue"),
         (335, "purple"), (360, "pink")]


def color_word(lab, part="hair"):
    """Basic color name of a tone, in Danbooru's vocabulary ("black", "green", "blonde"...)."""
    L, C, h = lch(lab)
    if L < 0.30 and C < 0.09:
        return "black"
    if C < 0.04 or (C < 0.06 and L > 0.8):
        if L > 0.86:
            return "white"
        return "black" if L < 0.36 else "grey"
    name = next(n for limit, n in _HUES if h < limit)
    if name == "red" and h < 15 and L > 0.72:
        name = "pink"
    if name == "pink" and L < 0.55:
        name = "red"
    if 35 < h < 105 and L < 0.56 and C < 0.16:
        name = "brown"
    if name == "yellow" and part == "hair":
        name = "blonde"
    return name


# Neighboring names: a measure and a control word this close are not counted as a contradiction
_NEIGHBORS = {
    frozenset(p) for p in [("red", "orange"), ("red", "pink"), ("red", "brown"), ("orange", "brown"),
                           ("orange", "blonde"), ("orange", "yellow"), ("blonde", "yellow"), ("blonde", "brown"),
                           ("blonde", "white"), ("yellow", "brown"), ("yellow", "green"), ("green", "aqua"),
                           ("aqua", "blue"), ("blue", "purple"), ("purple", "pink"), ("black", "grey"),
                           ("grey", "white"), ("black", "brown"), ("black", "blue"), ("grey", "silver"),
                           ("white", "silver")]
}


def words_agree(a, b):
    """Same color name, or two neighboring names."""
    return a == b or frozenset((a, b)) in _NEIGHBORS


# Natural skin tones in OKLCh (lightness, chroma, hue), wide on purpose: a colored skin (blue fish-men, green
# monsters) falls outside
def is_natural_skin(lab):
    L, C, h = lch(lab)
    return 0.4 <= L <= 0.97 and C <= 0.16 and (30 <= h <= 95 or C < 0.03)


def skin_word(lab):
    if not is_natural_skin(lab):
        return color_word(lab, "skin")
    L, _, _ = lch(lab)
    return "pale" if L > 0.9 else "light" if L > 0.78 else "tan" if L > 0.62 else "dark"
