# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "numpy==2.5.4",
#     "opencv-contrib-python-headless==5.0.0.93",
#     "onnxruntime-directml==1.24.4; sys_platform == 'win32'",
#     "onnxruntime==1.31.0; sys_platform != 'win32'",
#     "tokenizers==0.22.1",
#     "truststore==0.10.1",
# ]
# ///
"""Colorization server for Mihon (edited).

GET  /          health check, returns a small JSON document.
POST /colorize  body: the page already converted to grayscale and downscaled by the app (PNG or JPEG). Returns the
                colorized prediction as an RGB PNG of the same size; the app restores the original line art at full
                resolution itself, by multiplying the prediction by the ratio between the original and this image.
                Optional header X-Series-Title: the percent-encoded series title, used by the guided engine's color
                director.

Engines:
  guided  manga-colorization-v2, region segmentation, CLIP region labels and a per-series palette, on the graphics
        card through DirectML (any DirectX 12 GPU), see guided.py. With --director, a local LLM picks the palette.
  mc2   manga-colorization-v2 (ONNX) on the CPU, the model of the app's on-device engine.
  flux  FLUX.2 klein 4B through stable-diffusion.cpp on an NVIDIA GPU. The model redraws the whole page, so only its
        colors are kept: its output is aligned on the original page and turned into a multiply color layer, filled
        inside the original line art. Line art, screentones and text stay the original ones.

Run with `uv run --script colorization_server.py` (start-server.bat does it). Models are downloaded on first run.
"""
import argparse
import atexit
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

import guided
import truststore

# Certificates are checked by the OS, like a browser: Python alone misses some intermediate certificates
truststore.inject_into_ssl()

HF = "https://huggingface.co"
# manga-colorization-v2 generator (https://github.com/qweasdd/manga-colorization-v2), INT8 ONNX export
MC2_MODEL = (
    "manga-colorizer-int8.onnx",
    f"{HF}/lookx2/manga-colorization/resolve/9b421e3e89598aa3563be53f94cfd58b65b49702/manga-colorizer-int8.onnx",
    "cbf5f19c289107f37de2add52b03c6ed713800a33ac2baf80ad3188c22c152f3",
)
# FLUX.2 klein 4B and its components, all Apache 2.0, as stable-diffusion.cpp option -> file
FLUX_MODELS = {
    "diffusion-model": (
        "flux-2-klein-4b-Q8_0.gguf",
        f"{HF}/leejet/FLUX.2-klein-4B-GGUF/resolve/3b1f5a9dc3abb32238b053aeb3d823c30afdacbd/flux-2-klein-4b-Q8_0.gguf",
        "0bba6951258ec8f92d51114a8fa13e66828297bfff58a738f52729b3ef66fa28",
    ),
    "llm": (
        "Qwen3-4B-Q4_K_M.gguf",
        f"{HF}/unsloth/Qwen3-4B-GGUF/resolve/22c9fc8a8c7700b76a1789366280a6a5a1ad1120/Qwen3-4B-Q4_K_M.gguf",
        "f6f851777709861056efcdad3af01da38b31223a3ba26e61a4f8bf3a2195813a",
    ),
    "vae": (
        "full_encoder_small_decoder.safetensors",
        f"{HF}/black-forest-labs/FLUX.2-small-decoder/resolve/a3efc24f613ef42d9428af62fdbd6f5fd8856c4a/"
        "full_encoder_small_decoder.safetensors",
        "ea4273f02d1fafbf8e1d1c2cf6018ed8748652eb0bf34f2dd91171f16f15ab62",
    ),
}
SD_CPP_VERSION = "master-987-a77d362"
SD_CPP_ARCHIVES = [
    ("sd-master-a77d362-bin-win-cuda12-x64.zip", "eb4cc6be2d365258a8f4380f8ac8473090d93810f32dfc15b3d90914483b817c"),
    ("cudart-sd-bin-win-cu12-x64.zip", "fe20366827d357c00797eebb58244dddab7fd9a348d70090c3871004c320f38d"),
]

PROMPT = (
    "Colorize this black and white manga page into a full-color, professionally colored anime-style page. "
    "Vivid natural colors: blue sky, natural skin tones, consistent hair and clothing colors. "
    "Keep every line, panel border, speech bubble and text exactly as they are; do not redraw, move, add or "
    "remove anything. Speech bubbles stay white."
)
# How much the color layer may lighten the original: screentoned areas get the generated color without losing ink
MAX_GAIN = 1.8


def download(cache, name, url, sha256):
    path = cache / name
    if path.exists():
        return path
    cache.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(name + ".tmp")
    digest = hashlib.sha256()
    print(f"Downloading {name}...", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, open(tmp, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done, shown = 0, 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if total and done * 10 // total > shown:
                shown = done * 10 // total
                print(f"  {shown * 10}% of {total / 1e9:.2f} GB", flush=True)
    if digest.hexdigest() != sha256:
        tmp.unlink()
        raise SystemExit(f"{name} is corrupted, start the server again")
    tmp.replace(path)
    return path


def to_gray(bgr):
    """Luminance (ITU-R 601, like the app) in [0,1]."""
    b, g, r = (bgr[..., i].astype(np.int32) for i in range(3))
    return ((r * 299 + g * 587 + b * 114 + 500) // 1000).astype(np.float32) / 255


def to_rgb8(rgb):
    return np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8)


class Mc2Engine:

    def __init__(self, cache):
        import onnxruntime

        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
        options.inter_op_num_threads = 1
        model = download(cache, *MC2_MODEL)
        self.session = onnxruntime.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])

    def colorize(self, gray):
        # Input: grayscale padded with white to a multiple of 32, followed by four empty color hint channels
        h, w = gray.shape
        x = np.zeros((1, 5, (h + 31) // 32 * 32, (w + 31) // 32 * 32), np.float32)
        x[0, 0] = 1
        x[0, 0, :h, :w] = gray
        out = self.session.run(None, {"sketch_and_hints": x})[0][0]  # RGB in [-1,1]
        return to_rgb8(out[:, :h, :w].transpose(1, 2, 0) * 0.5 + 0.5)


def flux_files(cache):
    """Downloads stable-diffusion.cpp (CUDA build) and FLUX.2 klein, returns the sd-server command."""
    folder = cache / f"sd-cpp-{SD_CPP_VERSION}"
    exe = folder / "sd-server.exe"
    if not exe.exists() or not (folder / "cudart64_12.dll").exists():
        for name, sha256 in SD_CPP_ARCHIVES:
            url = f"https://github.com/leejet/stable-diffusion.cpp/releases/download/{SD_CPP_VERSION}/{name}"
            archive = download(cache, name, url, sha256)
            with zipfile.ZipFile(archive) as z:
                z.extractall(folder)
            archive.unlink()
    command = [str(exe)]
    for option, entry in FLUX_MODELS.items():
        command += [f"--{option}", str(download(cache, *entry))]
    # 4-step distilled model; weights stay in RAM and move to the GPU as needed, so 8 GB of VRAM are enough
    return command + ["--cfg-scale", "1.0", "--sampling-method", "euler", "--steps", "4", "--seed", "42",
                      "--offload-to-cpu"]


class FluxEngine:

    def __init__(self, cache, sd_port):
        if sys.platform != "win32":
            raise SystemExit("The flux engine needs Windows and an NVIDIA graphics card, use --engine mc2")
        command = flux_files(cache) + ["--listen-ip", "127.0.0.1", "--listen-port", str(sd_port)]
        self.url = f"http://127.0.0.1:{sd_port}"
        log_path = cache / "sd-server.log"
        self.process = subprocess.Popen(command, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)
        atexit.register(self.process.terminate)
        print("Loading FLUX.2 klein...", flush=True)
        while True:
            if self.process.poll() is not None:
                raise SystemExit(f"stable-diffusion.cpp stopped, see {log_path}")
            try:
                urllib.request.urlopen(self.url + "/v1/models", timeout=2).close()
                return
            except OSError:
                time.sleep(1)

    def colorize(self, gray):
        generated = align(gray, self.generate(gray))
        return to_rgb8(color_layer(gray, generated) * gray[..., None])

    def generate(self, gray):
        """Asks FLUX.2 klein to colorize the page, at a size it supports (multiples of 16)."""
        h, w = gray.shape
        size = (max(16, round(w / 16) * 16), max(16, round(h / 16) * 16))
        png = cv2.imencode(".png", cv2.resize(to_rgb8(gray), size, interpolation=cv2.INTER_AREA))[1].tobytes()
        boundary = uuid.uuid4().hex
        fields = {"prompt": PROMPT, "n": "1", "size": f"{size[0]}x{size[1]}", "output_format": "png"}
        body = b"".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
            for k, v in fields.items()
        )
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="page.png"\r\n'
                 f"Content-Type: image/png\r\n\r\n").encode() + png + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(self.url + "/v1/images/edits", data=body,
                                         headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(request, timeout=600) as response:
            data = base64.b64decode(json.load(response)["data"][0]["b64_json"])
        bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        return cv2.cvtColor(cv2.resize(bgr, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB) / 255.0


def luminance(rgb):
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def align(gray, rgb):
    """Warps the generated page onto the original: global affine transform (ECC), then smoothed optical flow."""
    h, w = gray.shape
    rgb = rgb.astype(np.float32)
    template = cv2.GaussianBlur(gray, (0, 0), 1.5)
    moving = cv2.GaussianBlur(luminance(rgb), (0, 0), 1.5)
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5)
        _, warp = cv2.findTransformECC(template, moving, warp, cv2.MOTION_AFFINE, criteria, None, 5)
    except cv2.error:
        pass  # Keep the plain resize when ECC doesn't converge
    rgb = cv2.warpAffine(rgb, warp, (w, h), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_REPLICATE)
    flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(
        to_rgb8(gray), to_rgb8(np.clip(luminance(rgb), 0, 1)), None)
    # Only keep smooth, small local shifts: the model's redrawn details must not distort the colors
    flow = np.dstack([cv2.GaussianBlur(flow[..., i], (0, 0), max(h, w) / 128) for i in range(2)])
    limit = max(h, w) / 40
    flow *= np.minimum(1, limit / np.maximum(np.linalg.norm(flow, axis=2, keepdims=True), 1e-6))
    x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(rgb, x + flow[..., 0], y + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def color_layer(gray, rgb):
    """Multiply layer such that layer * gray ~= rgb, filled edge-aware inside the original line art.

    Pixels where the original or the generated page is dark (ink, redrawn lines) carry no color information: their
    color comes from the neighboring flat areas, without crossing the original lines.
    """
    layer = rgb / np.maximum(gray, 0.05)[..., None]
    layer /= np.maximum(layer.max(axis=2, keepdims=True) / MAX_GAIN, 1.0)  # Keep the hue when clipping
    layer = cv2.medianBlur(layer.astype(np.float32), 5)
    weight = (smoothstep(0.2, 0.55, gray) * smoothstep(0.06, 0.25, luminance(rgb))).astype(np.float32) + 1e-4
    smoother = cv2.ximgproc.createFastGlobalSmootherFilter(to_rgb8(gray), 600.0, 10.0)
    filled = smoother.filter(layer * weight[..., None]) / np.maximum(smoother.filter(weight), 1e-4)[..., None]
    return np.maximum(filled, 0)


def main():
    default_cache = Path.home() / ".cache" / "mihon-colorization"
    parser = argparse.ArgumentParser(description="Colorization server for Mihon (edited)")
    parser.add_argument("--engine", choices=["guided", "mc2", "flux"], default="guided")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sd-port", type=int, default=8766, help="local port of stable-diffusion.cpp (flux)")
    parser.add_argument("--director", nargs="?", const="local", metavar="URL",
                        help="guided: let an LLM pick each series' palette; alone, runs Qwen3 4B locally with "
                             "llama.cpp on the graphics card, or give the URL of an OpenAI-compatible server")
    parser.add_argument("--director-model", help="model name sent to the --director server")
    parser.add_argument("--llm-port", type=int, default=8767, help="local port of llama.cpp (--director)")
    parser.add_argument("--cache", type=Path, default=default_cache, help="where models are downloaded")
    parser.add_argument("--download-only", action="store_true", help="download the models and exit")
    args = parser.parse_args()

    if args.download_only:
        if args.engine == "flux":
            flux_files(args.cache)
        else:
            download(args.cache, *MC2_MODEL)
        if args.engine == "guided":
            for entry in guided.CLIP_FILES.values():
                download(args.cache, *entry)
        return
    if args.engine == "guided":
        director_url = args.director
        if director_url == "local":
            director_url = guided.start_local_llm(args.cache, download, FLUX_MODELS["llm"], args.llm_port)
        director = guided.ColorDirector(args.cache, director_url, args.director_model)
        engine = guided.GuidedEngine(args.cache, download, MC2_MODEL, director)
    elif args.engine == "flux":
        engine = FluxEngine(args.cache, args.sd_port)
    else:
        engine = Mc2Engine(args.cache)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        # Keep-alive, as OkHttp reuses its connections
        protocol_version = "HTTP/1.1"

        def respond(self, code, content_type, body):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            info = {"status": "ok", "service": "manga-colorization", "engine": args.engine}
            self.respond(200, "application/json", json.dumps(info).encode())

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path != "/colorize":
                return self.respond(404, "text/plain", b"POST an image to /colorize")
            image = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                return self.respond(400, "text/plain", b"Unsupported image format")
            start = time.time()
            try:
                # The model already uses the whole CPU or GPU: one page at a time
                with lock:
                    if args.engine == "guided":
                        title = guided.series_title(self.headers.get("X-Series-Title"))
                        rgb = engine.colorize(to_gray(image), title)
                    else:
                        rgb = engine.colorize(to_gray(image))
            except Exception as e:
                print(f"Colorization failed: {e!r}", flush=True)
                return self.respond(500, "text/plain", str(e).encode())
            self.respond(200, "image/png", cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))[1].tobytes())
            print(f"Colorized {image.shape[1]}x{image.shape[0]} in {time.time() - start:.1f} s", flush=True)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"Colorization server ready ({args.engine}). In Mihon, use one of:")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    except OSError:
        addresses = set()
    for address in sorted(addresses - {"127.0.0.1"}):
        print(f"  http://{address}:{args.port}")
    print(f"  http://10.0.2.2:{args.port}   (Android emulator on this PC)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
