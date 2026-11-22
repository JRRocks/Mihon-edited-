"""Guided colorization engine ("guided"), after the architecture of ColorComic (https://github.com/vikast908/ColorComic).

    page -> manga-colorization-v2 (GPU)        base colors and shading
         -> trapped-ball segmentation           regions closed by the line art
         -> CLIP zero-shot labels (GPU)         skin, sky, foliage, water, speech bubble...
         -> color director                      palette and style of the series: static, or picked by a local LLM
         -> per-region flat colors              cel look: one chroma per region, palette colors on labeled regions,
                                                neutral speech bubbles, luminance of the original page

Unlike ColorComic, the palette isn't fed to the hint channel of the model: the ONNX export used here barely reacts to
it, so the palette is applied to the regions after the model instead.

Models run with ONNX Runtime on the graphics card through DirectML (any DirectX 12 GPU), or on the CPU elsewhere. The
optional LLM runs with llama.cpp (Vulkan build, also on the graphics card) and only reads text: it gets the series
title and picks the palette once per series, it never sees the pages.
"""
import json
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import zipfile

import cv2
import numpy as np

HF = "https://huggingface.co"
CLIP_REVISION = f"{HF}/Xenova/clip-vit-base-patch32/resolve/6b7c523703ae26e39be4b03774966f8571c7f523"
CLIP_FILES = {
    "vision": ("clip-vision_model_fp16.onnx", f"{CLIP_REVISION}/onnx/vision_model_fp16.onnx",
               "35c4e0fb0aeee527dcde1693520b214a34424a786babd530f35366bad5844efd"),
    "text": ("clip-text_model_fp16.onnx", f"{CLIP_REVISION}/onnx/text_model_fp16.onnx",
             "df587ffbf248bf20d44fa6e16adc5ebc27ead691860e5333dbdaab5fd6bf3f6e"),
    "tokenizer": ("clip-tokenizer.json", f"{CLIP_REVISION}/tokenizer.json",
                  "f7f3b7af117d467b58374797691a6438d3e6b9e9cef800dfd5dced7f697a90cd"),
}
LLAMA_CPP = ("llama-b12237-bin-win-vulkan-x64.zip",
             "https://github.com/ggml-org/llama.cpp/releases/download/b12237/llama-b12237-bin-win-vulkan-x64.zip",
             "287206f220004c6ece23d574161c623f5c56b987f450511667ac9aa99aabb1a2")
CLIP_MEAN = np.array([0.4815, 0.4578, 0.4082], np.float32)
CLIP_STD = np.array([0.2686, 0.2613, 0.2758], np.float32)

# Zero-shot classes. Only the ones with a palette color change the page; the others compete so that a region isn't
# labeled "skin" just because nothing fits better.
LABELS = {
    "skin": "a person's face or bare skin",
    "hair": "a person's hair",
    "clothing": "clothes, a shirt or a jacket",
    "sky": "the sky with clouds",
    "foliage": "trees, leaves or grass",
    "building": "a building or a wall",
    "ground": "the ground, a street or a floor",
    "water": "water or the sea",
    "wood": "a wooden surface",
    "bubble": "a white speech bubble with text",
    "object": "an object",
}
# Minimum CLIP probability for a label to recolor its region
THRESHOLDS = {"skin": 0.45, "sky": 0.5, "foliage": 0.55, "water": 0.7, "bubble": 0.4}
STATIC_PALETTE = {"style": "natural", "skin": "#f6d3bd", "sky": "#8cc4ec", "foliage": "#7fb069", "water": "#6fa8dc"}
# Chroma multiplier and lightness lift of each style
STYLES = {"vivid": (1.3, 0), "natural": (1.0, 0), "pastel": (0.8, 4), "muted": (0.7, 0), "dark": (0.85, -4)}

DIRECTOR_PROMPT = """You are the color director of a manga colorization tool. Pick the color palette for the series
"{title}". Use what you know about this series (genre, tone, setting, era). Answer with JSON only:
{{"style": one of "vivid", "natural", "pastel", "muted", "dark",
 "skin": main characters' skin color as "#rrggbb",
 "sky": "#rrggbb", "foliage": "#rrggbb", "water": "#rrggbb"}}
Natural, believable colors: skin in the peach/tan/brown range, never gray, green or saturated red."""


def gpu_providers(onnxruntime):
    available = onnxruntime.get_available_providers()
    return [p for p in ("DmlExecutionProvider", "CPUExecutionProvider") if p in available]


def session(onnxruntime, path, providers):
    options = onnxruntime.SessionOptions()
    # Required by DirectML
    options.enable_mem_pattern = False
    options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    return onnxruntime.InferenceSession(str(path), options, providers=providers)


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def line_mask(gray):
    """Ink: pixels clearly darker than the paper around them, or dark in absolute terms."""
    u8 = (gray * 255).astype(np.uint8)
    background = cv2.dilate(u8, disk(3)).astype(np.int16)
    return ((background - u8 > 40) | (u8 < 110)).astype(np.uint8)


def segment(gray, radii=(7, 4, 2), min_areas=(60, 30, 15)):
    """Trapped-ball segmentation, returns (labels, region count).

    Balls of decreasing size seed the areas they fit in, so a gap in the line art narrower than the ball doesn't merge
    two regions. Large ink areas are regions too. A watershed then gives every pixel, lines included, to a region.
    """
    lines = line_mask(gray)
    free = 1 - lines
    markers = np.zeros(gray.shape, np.int32)
    count = 0

    def add(seeds, min_area, grow=0):
        nonlocal markers, count
        n, components = cv2.connectedComponents(seeds, connectivity=4)
        keep = np.bincount(components.ravel(), minlength=n) >= min_area
        keep[0] = False
        ids = np.zeros(n, np.int32)
        ids[keep] = np.arange(count + 1, count + 1 + keep.sum())
        new = ids[components]
        if grow:  # The ball paints back the area it was rolled in
            new = cv2.dilate(new.astype(np.float32), disk(grow)).astype(np.int32) * free
        markers = np.where(markers > 0, markers, new)
        count += int(keep.sum())

    for r, min_area in zip(radii, min_areas):
        claimed = cv2.dilate((markers > 0).astype(np.uint8), disk(r + 1))
        add(cv2.erode(free, disk(r)) & (1 - claimed), min_area, grow=r)
    add(cv2.morphologyEx(lines, cv2.MORPH_OPEN, disk(2)) & (markers == 0).astype(np.uint8), 80)
    markers = cv2.watershed(cv2.cvtColor((gray * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR), markers)
    boundaries = markers <= 0
    markers = np.where(boundaries, 0, markers).astype(np.float32)
    markers = np.where(boundaries, cv2.dilate(markers, np.ones((3, 3), np.uint8)), markers)
    return markers.astype(np.int32), count


def hex_to_lab(color):
    rgb = np.array([[[int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]]], np.float32)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[0, 0]


class RegionClassifier:
    """CLIP ViT-B/32 zero-shot classifier of page regions."""

    def __init__(self, files, onnxruntime, providers):
        from tokenizers import Tokenizer

        self.vision = session(onnxruntime, files["vision"], providers)
        text = session(onnxruntime, files["text"], providers)
        tokenizer = Tokenizer.from_file(str(files["tokenizer"]))
        tokenizer.enable_padding(length=77, pad_id=49407)
        tokenizer.enable_truncation(77)
        prompts = [f"a black and white manga drawing of {v}" for v in LABELS.values()]
        ids = np.array([e.ids for e in tokenizer.encode_batch(prompts)], np.int64)
        embeddings = text.run(None, {"input_ids": ids})[0]
        self.text = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.names = list(LABELS)

    def classify(self, gray, labels, regions):
        """Returns {region: (label, probability)}."""
        if not regions:
            return {}
        crops = np.stack([self.crop(gray, labels, i) for i in regions])[..., None].repeat(3, -1)
        pixels = ((crops - CLIP_MEAN) / CLIP_STD).transpose(0, 3, 1, 2).astype(np.float32)
        image = np.concatenate([self.vision.run(None, {"pixel_values": pixels[k:k + 32]})[0]
                                for k in range(0, len(pixels), 32)])
        image /= np.linalg.norm(image, axis=1, keepdims=True)
        logits = 100 * image @ self.text.T
        probabilities = np.exp(logits - logits.max(axis=1, keepdims=True))
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        best = probabilities.argmax(axis=1)
        return {i: (self.names[k], float(p[k])) for i, k, p in zip(regions, best, probabilities)}

    @staticmethod
    def crop(gray, labels, region):
        """Square crop around the region, with the surroundings faded so CLIP looks at the region in context."""
        ys, xs = np.nonzero(labels == region)
        cy, cx = (ys.min() + ys.max() + 1) / 2, (xs.min() + xs.max() + 1) / 2
        half = max(ys.max() + 1 - ys.min(), xs.max() + 1 - xs.min()) * 0.6 + 8
        y0, y1 = int(max(0, cy - half)), int(min(gray.shape[0], cy + half))
        x0, x1 = int(max(0, cx - half)), int(min(gray.shape[1], cx + half))
        crop = gray[y0:y1, x0:x1]
        crop = np.where(labels[y0:y1, x0:x1] == region, crop, crop * 0.35 + 0.65)
        side = max(crop.shape)
        square = np.ones((side, side), np.float32)
        top, left = (side - crop.shape[0]) // 2, (side - crop.shape[1]) // 2
        square[top:top + crop.shape[0], left:left + crop.shape[1]] = crop
        return cv2.resize(square, (224, 224), interpolation=cv2.INTER_AREA)


class ColorDirector:
    """Picks the palette of each series: the static one, or one chosen by a text-only LLM from the series title.

    The LLM is any OpenAI-compatible chat server; with `local`, llama.cpp is started on the graphics card with Qwen3 4B.
    Its choices are saved in the cache so each series is asked once.
    """

    def __init__(self, cache, url=None, model=None):
        self.url = url
        self.model = model or "local"
        self.path = cache / "director-palettes.json"
        self.palettes = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {}
        self.lock = threading.Lock()

    def palette(self, title):
        if not self.url or not title:
            return STATIC_PALETTE
        key = title.strip().lower()
        with self.lock:
            if key not in self.palettes:
                try:
                    self.palettes[key] = self.ask(title)
                    print(f"Color director, {title}: {self.palettes[key]}", flush=True)
                except Exception as e:
                    print(f"Color director failed, static palette used: {e!r}", flush=True)
                    return STATIC_PALETTE
                self.path.write_text(json.dumps(self.palettes, indent=1, ensure_ascii=False), "utf-8")
            return self.palettes[key]

    def ask(self, title):
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": DIRECTOR_PROMPT.format(title=title.replace('"', "'"))}],
            "temperature": 0.2,
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request = urllib.request.Request(self.url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=120) as response:
            content = json.load(response)["choices"][0]["message"]["content"]
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
        answer = json.loads(content[content.index("{"):content.rindex("}") + 1])
        palette = dict(STATIC_PALETTE)
        if answer.get("style") in STYLES:
            palette["style"] = answer["style"]
        for key in ("skin", "sky", "foliage", "water"):
            value = str(answer.get(key, ""))
            if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                palette[key] = value.lower()
        # Small models sometimes answer a grayish or odd skin color: keep it only in the warm skin hue band
        _, a, b = hex_to_lab(palette["skin"])
        if not (8 <= np.hypot(a, b) <= 45 and 20 <= np.degrees(np.arctan2(b, a)) <= 85):
            palette["skin"] = STATIC_PALETTE["skin"]
        return palette


def start_local_llm(cache, download, model_entry, port):
    """Starts llama.cpp's server (Vulkan build) with Qwen3 4B on the graphics card, returns its URL."""
    if sys.platform != "win32":
        raise SystemExit("--director local needs Windows, use --director-url with your own LLM server")
    folder = cache / LLAMA_CPP[0].removesuffix(".zip")
    exe = folder / "llama-server.exe"
    if not exe.exists():
        archive = download(cache, *LLAMA_CPP)
        with zipfile.ZipFile(archive) as z:
            z.extractall(folder)
        archive.unlink()
    model = download(cache, *model_entry)
    log_path = cache / "llama-server.log"
    command = [str(exe), "-m", str(model), "--host", "127.0.0.1", "--port", str(port), "-ngl", "99", "-c", "2048"]
    process = subprocess.Popen(command, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)
    import atexit

    atexit.register(process.terminate)
    url = f"http://127.0.0.1:{port}"
    print("Loading the color director (Qwen3 4B)...", flush=True)
    while True:
        if process.poll() is not None:
            raise SystemExit(f"llama.cpp stopped, see {log_path}")
        try:
            urllib.request.urlopen(url + "/health", timeout=2).close()
            return url
        except OSError:
            time.sleep(1)


class GuidedEngine:

    def __init__(self, cache, download, mc2_entry, director):
        import onnxruntime

        onnxruntime.set_default_logger_severity(3)
        providers = gpu_providers(onnxruntime)
        self.device = "GPU (DirectML)" if providers[0] == "DmlExecutionProvider" else "CPU"
        files = {key: download(cache, *entry) for key, entry in CLIP_FILES.items()}
        # DirectML crashes (access violation) when the colorizer session is created before the CLIP ones
        self.classifier = RegionClassifier(files, onnxruntime, providers)
        self.model = session(onnxruntime, download(cache, *mc2_entry), providers)
        self.director = director
        print(f"Guided engine on {self.device}", flush=True)

    def predict(self, gray):
        h, w = gray.shape
        x = np.zeros((1, 5, (h + 31) // 32 * 32, (w + 31) // 32 * 32), np.float32)
        x[0, 0] = 1
        x[0, 0, :h, :w] = gray
        out = self.model.run(None, {"sketch_and_hints": x})[0][0]
        return np.clip(out[:, :h, :w].transpose(1, 2, 0) * 0.5 + 0.5, 0, 1).astype(np.float32)

    def colorize(self, gray, series=None):
        palette = self.director.palette(series)
        rgb = self.predict(gray)
        labels, n = segment(gray)
        flat = labels.ravel()
        area = np.bincount(flat, minlength=n + 1)
        mean_gray = np.bincount(flat, gray.ravel(), minlength=n + 1) / np.maximum(area, 1)
        regions = [i for i in range(1, n + 1) if area[i] >= 0.002 * gray.size]
        names = {}
        for region, (name, probability) in self.classifier.classify(gray, labels, regions).items():
            if probability >= THRESHOLDS.get(name, 2):
                names[region] = name
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        # Flat color of each region: its mean chroma, weighted toward paper-like pixels where the model is reliable.
        # Small regions (eyes, details) keep more of the model's own colors.
        weight = np.clip((gray - 0.15) / 0.5, 0, 1).ravel() + 1e-3
        total = np.bincount(flat, weight, minlength=n + 1)
        target = np.stack([np.bincount(flat, weight * lab[..., c].ravel(), minlength=n + 1) / np.maximum(total, 1e-6)
                           for c in (1, 2)], axis=1)
        strength = 0.75 * np.clip(area / (0.003 * gray.size), 0.2, 1)
        for region, name in names.items():
            if name == "bubble":
                if mean_gray[region] > 0.85:  # Speech bubbles stay white
                    target[region], strength[region] = 0, 1
            else:
                target[region], strength[region] = hex_to_lab(palette[name])[1:], 0.9
        s = strength[labels][..., None]
        ab = lab[..., 1:] * (1 - s) + target[labels] * s
        saturation, lift = STYLES[palette.get("style", "natural")]
        chroma = np.linalg.norm(ab, axis=2, keepdims=True)
        ab *= saturation * (1 + 0.25 * np.exp(-chroma / 25))  # Vibrance: weak colors get the biggest boost
        # Luminance of the original page keeps line art and screentones; colored surfaces get a ceiling so that white
        # paper still shows their color
        chroma = np.linalg.norm(ab, axis=2)
        lightness = cv2.cvtColor(np.repeat(gray[..., None], 3, axis=2), cv2.COLOR_RGB2LAB)[..., 0] + lift
        lightness = np.minimum(lightness, 100 - np.clip(chroma, 0, 60) * 0.3)
        out = cv2.cvtColor(np.dstack([lightness, ab]).astype(np.float32), cv2.COLOR_LAB2RGB)
        return np.clip(np.round(out * 255), 0, 255).astype(np.uint8)


def series_title(header):
    """The app sends the series title percent-encoded, HTTP headers being ASCII."""
    return urllib.parse.unquote(header).strip() if header else None
