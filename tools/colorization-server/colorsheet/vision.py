"""Finding characters on color images: person and head detection, then character matching.

Models (ONNX, run on the CPU), all from https://huggingface.co/deepghs, pinned to a commit:
- anime_person_detection, person_detect_v1.3_s (YOLOv8, MIT): one box per character;
- anime_head_detection, head_detect_v2.0_s (YOLOv8, MIT): heads, to keep only crops that show a single character;
- ccip_onnx, ccip-caformer_b36-24 (CCIP, OpenRAIL, 384 MB): a "difference" between two images of characters, below
  0.213 when they show the same character (best F1 score, 0.94, in the model card). The smaller default model of
  dghs-imgutils (ccip-caformer-24-randaug-pruned, F1 0.92) confused post-timeskip Zoro with Usopp on One Piece covers;
  this one made no such confusion on the same 64 crops (see docs/DECISIONS.md, D31).
Pre- and post-processing follow the reference implementation, dghs-imgutils 0.19 (MIT).
"""
import ast
import json

import cv2
import numpy as np

from .net import download_model

HF = "https://huggingface.co"
PERSON_MODEL = (
    "deepghs-person_detect_v1.3_s.onnx",
    f"{HF}/deepghs/anime_person_detection/resolve/e39c744c22432ad01f91dd254fe2b02c8d878b8c/person_detect_v1.3_s/model.onnx",
    "6da88929438cd442e31e45ff4f934dd2d7eb9cf7a423c22885d650ee52550f90",
)
HEAD_MODEL = (
    "deepghs-head_detect_v2.0_s.onnx",
    f"{HF}/deepghs/anime_head_detection/resolve/06604feee81983792a57c21081e539c0ae229833/head_detect_v2.0_s/model.onnx",
    "6679f9b71192298bbf174d82e9e5581c3237b0c3dc67deace7cdbf686b070a00",
)
CCIP_REVISION = f"{HF}/deepghs/ccip_onnx/resolve/eb2acdd29af1703388d3d0c04221add322bc9110/ccip-caformer_b36-24"
CCIP_FEATURES = ("deepghs-ccip-caformer_b36-24-feat.onnx", f"{CCIP_REVISION}/model_feat.onnx",
                 "c1e7333a55c2ad9e03cd340c635e96c9c1d86f0836fa7eae65720e7c9c94ee51")
CCIP_METRICS = ("deepghs-ccip-caformer_b36-24-metrics.onnx", f"{CCIP_REVISION}/model_metrics.onnx",
                "816f291e385e854896276ff283dc83eac4966e5f51ab10260fee50de3ca9b8e3")
# From the models' threshold.json at the same commits, and the CCIP model card (best F1 score)
PERSON_THRESHOLD = 0.324
HEAD_THRESHOLD = 0.413
CCIP_SAME = 0.213231
# Matching a crop to a character (spec, section 5, "threshold and gap"): a crop is that character when its difference
# to the official AniList picture is under REF_MATCH and ahead of the second best by MARGIN; a crop very close (LINK)
# to such a crop is that character too, if it isn't far from the official picture. Set on One Piece covers: on 64
# hand-labeled single-character crops, 0.14 gave 21 right and no crew member taken for another; on the 193 heads of
# the full run, 0.14 also let in a blue dragon (taken for Jinbe) and Whitebeard (taken for Usopp) at 0.136 and 0.139,
# and 0.10 links brought a green-haired Vinsmoke to Zoro at 0.085: hence 0.12 and 0.08.
REF_MATCH = 0.12
MARGIN = 0.05
LINK = 0.08
# CLIP normalization, used by CCIP
CCIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], np.float32)
CCIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], np.float32)


def model_files(cache):
    return [download_model(cache, *m) for m in (PERSON_MODEL, HEAD_MODEL, CCIP_FEATURES, CCIP_METRICS)]


def _session(path):
    import onnxruntime

    options = onnxruntime.SessionOptions()
    options.log_severity_level = 3
    return onnxruntime.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


def pil_resize(rgb, size):
    """Resize like Pillow (antialiased bilinear when shrinking), as the reference preprocessing does."""
    from PIL import Image

    return np.asarray(Image.fromarray(rgb).resize(size, Image.Resampling.BILINEAR))


def nms(boxes, scores, iou_threshold):
    """Greedy non-maximum suppression, boxes as (x0, y0, x1, y1). Returns the kept indices."""
    x0, y0, x1, y1 = boxes.T
    areas = (x1 - x0 + 1) * (y1 - y0 + 1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        w = np.maximum(0, np.minimum(x1[i], x1[order[1:]]) - np.maximum(x0[i], x0[order[1:]]) + 1)
        h = np.maximum(0, np.minimum(y1[i], y1[order[1:]]) - np.maximum(y0[i], y0[order[1:]]) + 1)
        iou = w * h / (areas[i] + areas[order[1:]] - w * h)
        order = order[1:][iou <= iou_threshold]
    return keep


class Yolo:
    """YOLOv8 detector exported by ultralytics: stretched to the model size, boxes decoded then NMS."""

    def __init__(self, path, threshold, iou):
        self.session = _session(path)
        meta = self.session.get_modelmeta().custom_metadata_map
        size = json.loads(meta["imgsz"]) if "imgsz" in meta else [640, 640]
        self.width, self.height = size  # read as (width, height), like the reference implementation
        self.threshold, self.iou = threshold, iou

    def detect(self, rgb):
        """Returns [(x0, y0, x1, y1, score)] in the image's pixels."""
        h, w = rgb.shape[:2]
        x = pil_resize(rgb, (self.width, self.height)).astype(np.float32).transpose(2, 0, 1)[None] / 255
        out = self.session.run(["output0"], {"images": x})[0][0]  # (4 + classes, candidates)
        scores = out[4:].max(axis=0)
        out = out[:, scores > self.threshold].T
        if not len(out):
            return []
        cx, cy, bw, bh = out[:, :4].T
        boxes = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], axis=1)
        scores = out[:, 4:].max(axis=1)
        keep = nms(boxes, scores, self.iou)
        sx, sy = w / self.width, h / self.height
        result = []
        for i in keep:
            b = boxes[i]
            result.append((int(np.clip(b[0] * sx, 0, w)), int(np.clip(b[1] * sy, 0, h)),
                           int(np.clip(b[2] * sx, 0, w)), int(np.clip(b[3] * sy, 0, h)), float(scores[i])))
        return result


class Ccip:
    """Character features (768 values) and pairwise differences between them."""

    def __init__(self, features_path, metrics_path):
        self.features_session = _session(features_path)
        self.metrics_session = _session(metrics_path)

    def features(self, images, batch=8):
        out = []
        for i in range(0, len(images), batch):
            data = np.stack([((pil_resize(im, (384, 384)).astype(np.float32) / 255 - CCIP_MEAN) / CCIP_STD)
                             .transpose(2, 0, 1) for im in images[i:i + batch]]).astype(np.float32)
            out.append(self.features_session.run(["output"], {"input": data})[0])
        return np.concatenate(out) if out else np.zeros((0, 768), np.float32)

    def differences(self, features):
        """Square matrix of differences (0 = same image; below CCIP_SAME = same character)."""
        return self.metrics_session.run(["output"], {"input": features.astype(np.float32)})[0]


class Detectors:

    def __init__(self, cache):
        person, head, feat, metrics = model_files(cache)
        self.person = Yolo(person, PERSON_THRESHOLD, 0.5)
        self.head = Yolo(head, HEAD_THRESHOLD, 0.7)
        self.ccip = Ccip(feat, metrics)


def load_rgb(path, max_side=None):
    """Reads an image file as RGB uint8; transparent areas become white."""
    data = np.fromfile(str(path), np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"unreadable image: {path}")
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        alpha = image[..., 3:4].astype(np.float32) / 255
        image = (image[..., :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    if max_side and max(rgb.shape[:2]) > max_side:
        s = max_side / max(rgb.shape[:2])
        rgb = cv2.resize(rgb, (round(rgb.shape[1] * s), round(rgb.shape[0] * s)), interpolation=cv2.INTER_AREA)
    return rgb


def alpha_mask(path):
    """Opaque pixels of an image file (all of them when it has no transparency)."""
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_UNCHANGED)
    if image is not None and image.ndim == 3 and image.shape[2] == 4:
        return image[..., 3] > 127
    return None


def box_iou(a, b):
    w = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w * h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def inside_fraction(inner, outer):
    """Fraction of box `inner` lying inside box `outer`."""
    w = max(0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    h = max(0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return w * h / area if area else 0.0


def single_character_crops(persons, heads, min_height):
    """Keeps the person boxes that hold exactly one head, and gives each its head box.

    A box that holds a second head (another character drawn in front or behind) is left out: one character per crop.
    """
    crops = []
    for p in persons:
        if p[3] - p[1] < min_height:
            continue
        inside = [h for h in heads if inside_fraction(h, p) > 0.6]
        if len(inside) != 1:
            continue
        crops.append({"box": [int(v) for v in p[:4]], "score": round(float(p[4]), 3),
                      "head": [int(v) for v in inside[0][:4]]})
    return crops


def around(box, shape, left, top, right, bottom):
    """A box grown by the given multiples of the box's larger side, clipped to the image."""
    x0, y0, x1, y1 = box[:4]
    s = max(x1 - x0, y1 - y0)
    h, w = shape[:2]
    return [int(max(0, x0 - left * s)), int(max(0, y0 - top * s)), int(min(w, x1 + right * s)),
            int(min(h, y1 + bottom * s))]


def identity_box(head, shape):
    """Head and shoulders, the framing of the AniList pictures, for matching."""
    return around(head, shape, 0.3, 0.3, 0.3, 0.4)


def parse_box(instance, shape):
    """What the parts model sees: the whole single-character box, or head and shoulders (the framing of the AniList
    pictures, which the model reads best)."""
    if instance.get("body"):
        return around(instance["body"], shape, 0.03, 0.03, 0.03, 0.03)
    return identity_box(instance["head"], shape)


def cover_instances(persons, heads, shape, min_head=0.035):
    """Every character drawn on a cover: one per detected head big enough to measure (min_head of the page height).

    Crowded covers rarely isolate a whole character, but heads are separate: hair, eyes and skin are measured around
    the head; the body (for the outfit) is added only when a person box holds this head and no other.
    """
    instances = []
    for head in heads:
        if max(head[2] - head[0], head[3] - head[1]) < min_head * shape[0]:
            continue
        body = None
        for p in sorted(persons, key=lambda p: (p[2] - p[0]) * (p[3] - p[1])):
            if inside_fraction(head, p) > 0.6:
                if sum(inside_fraction(h, p) > 0.6 for h in heads) == 1:
                    body = [int(v) for v in p[:4]]
                break
        instances.append({"head": [int(v) for v in head[:4]], "head_score": round(float(head[4]), 3),
                          "body": body})
    return instances


def assign(ref_diff, crop_diff, images, ref_match=REF_MATCH, margin=MARGIN, link=LINK, same=CCIP_SAME):
    """Which character each crop shows, or None. Pure function.

    ref_diff: (crops, characters) differences to each character's official picture; crop_diff: (crops, crops)
    differences between crops; images: the image each crop comes from. A crop is a character when it matches the
    official picture under `ref_match` with a gap of `margin` over the second best (seed), or when it is within `link`
    of a seed of that character with the same gap over the other characters' seeds, and under `same` from the official
    picture. One image counts once per character: the best crop is kept. Returns [(character index or None, how)].
    """
    import numpy as np

    ref_diff = np.asarray(ref_diff)
    n, k = ref_diff.shape
    result = [(None, None)] * n
    for i in range(n):
        order = np.argsort(ref_diff[i])
        best = int(order[0])
        second = ref_diff[i, order[1]] if k > 1 else np.inf
        if ref_diff[i, best] < ref_match and second - ref_diff[i, best] >= margin:
            result[i] = (best, {"by": "official", "difference": round(float(ref_diff[i, best]), 3),
                                "gap": round(float(second - ref_diff[i, best]), 3)})
    seeds = [(i, c) for i, (c, _) in enumerate(result) if c is not None]
    for j in range(n):
        if result[j][0] is not None or not seeds:
            continue
        nearest = {}
        for i, c in seeds:
            d = float(crop_diff[j][i])
            if d < nearest.get(c, (np.inf,))[0]:
                nearest[c] = (d, i)
        ranked = sorted(nearest.items(), key=lambda kv: kv[1][0])
        c, (d, i) = ranked[0]
        gap = ranked[1][1][0] - d if len(ranked) > 1 else np.inf
        if d < link and gap >= margin and ref_diff[j, c] < same:
            result[j] = (c, {"by": "crop", "crop": i, "difference": round(d, 3),
                             "official": round(float(ref_diff[j, c]), 3)})
    # One image counts once per character
    best_of = {}
    for i, (c, how) in enumerate(result):
        if c is None:
            continue
        key = (images[i], c)
        if key not in best_of or ref_diff[i, c] < ref_diff[best_of[key], c]:
            best_of[key] = i
    keep = set(best_of.values())
    return [r if i in keep else (None, None) for i, r in enumerate(result)]
