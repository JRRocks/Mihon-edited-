"""Finding characters on color images: person and head detection, then character matching.

Models (ONNX, run on the CPU), all from https://huggingface.co/deepghs, pinned to a commit:
- anime_person_detection, person_detect_v1.3_s (YOLOv8, MIT): one box per character;
- anime_head_detection, head_detect_v2.0_s (YOLOv8, MIT): heads, to keep only crops that show a single character;
- ccip_onnx, ccip-caformer-24-randaug-pruned (CCIP, OpenRAIL): a "difference" between two images of characters,
  below 0.178 when they show the same character (threshold from the model's metrics.json).
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
CCIP_REVISION = f"{HF}/deepghs/ccip_onnx/resolve/eb2acdd29af1703388d3d0c04221add322bc9110/ccip-caformer-24-randaug-pruned"
CCIP_FEATURES = ("deepghs-ccip-caformer-24-randaug-pruned-feat.onnx", f"{CCIP_REVISION}/model_feat.onnx",
                 "4ea118d16496274f4f6e08d3afc768cc592389e8f7f32f8732ce2215c228ac5f")
CCIP_METRICS = ("deepghs-ccip-caformer-24-randaug-pruned-metrics.onnx", f"{CCIP_REVISION}/model_metrics.onnx",
                "7e4646fdfbe369ad485b227ec47ac4092c98b8deef3af44e19fdbd8ba7bc25c1")
# From the models' threshold.json / metrics.json at the same commits (best F1 score)
PERSON_THRESHOLD = 0.324
HEAD_THRESHOLD = 0.413
CCIP_SAME = 0.17847511429108218
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
