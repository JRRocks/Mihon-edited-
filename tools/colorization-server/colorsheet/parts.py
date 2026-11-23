"""Body parts of a character on a color image: See-through's parsing model, or rough regions when it fails.

See-through (https://github.com/shitagaki-lab/see-through, Apache-2.0): SAM-HQ ViT-H fine-tuned to split an anime
character into 19 parts, weights 24yearsold/l2d_sam_iter2 on Hugging Face (Apache-2.0, 1.3 GB). The SAM building
blocks are fetched from See-through's repository at a pinned commit, each file checked against its SHA-256, and loaded
from the model cache; the semantic head below follows See-through's SemanticSam (common/modules/semanticsam.py,
"mlp_variant"), with the same parameter names so that the checkpoint loads as is. Runs on the CPU (PyTorch).
"""
import importlib
import sys
import time
from functools import partial
from pathlib import Path

import cv2
import numpy as np

from .net import download_model

SEE_THROUGH_COMMIT = "fc4440db7c076518e313f378e28b1504e9886a95"
SEE_THROUGH_FILES = {
    "__init__.py": "47f6363b86c0bfaa7a6abf723975136d17fae4a5f002d2814a5cce8834d18980",
    "common.py": "59a53bfa5d0a4d446df7f2bb57d2e95808b130601592b934600fb663d256ce17",
    "image_encoder.py": "963c667ff8c1dfb85a768c548e5540033dfb51836cb571279a7d5edcc93d8b52",
    "mask_decoder.py": "7448a5168b93f274ef42d9b8d0c7791a8d705a670c3fe32d54f92b02ce92df6f",
    "prompt_encoder.py": "16dc685fc87f26372918b0cc0ed800b93a78c649864bfc3e8d3887d147863884",
    "sam.py": "b7c18c9d932ece40d76bfdff21ec9cebc23dcdbaa3fe7c3b0664ba1a1a837feb",
    "transformer.py": "996d0a0d27342ac6b84deec34a6dedb38d2ca414879eaab10fdf080aaaf1d91a",
}
CHECKPOINT = (
    "seethrough-l2d_sam_iter2-checkpoint-18000.pt",
    "https://huggingface.co/24yearsold/l2d_sam_iter2/resolve/0b0608310fb7a89e32ecd7397147a249540cf1e7/"
    "checkpoint-18000.pt",
    "dda82b916f6c340bc5a6c3a077ff1214f9906906abe3707b1076d55b508f253f",
)
# See-through's 19 classes (VALID_BODY_PARTS_V2), in the order of the model's outputs
CLASSES = ["hair", "headwear", "face", "eyes", "eyewear", "ears", "earwear", "nose", "mouth", "neck", "neckwear",
           "topwear", "handwear", "bottomwear", "legwear", "footwear", "tail", "wings", "objects"]
SAM_MEAN = [123.675, 116.28, 103.53]
SAM_STD = [58.395, 57.12, 57.375]


def fetch_modeling(cache: Path):
    """Downloads the SAM modeling package of See-through (7 small files) and returns it as a Python module."""
    folder = cache / f"see-through-{SEE_THROUGH_COMMIT[:7]}"
    package = folder / "seethrough_sam"
    base = (f"https://raw.githubusercontent.com/shitagaki-lab/see-through/{SEE_THROUGH_COMMIT}/"
            "common/modules/sam/modeling/")
    for name, sha256 in SEE_THROUGH_FILES.items():
        download_model(package, name, base + name, sha256)
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    return importlib.import_module("seethrough_sam")


def build_model(modeling, torch):
    """SemanticSam (SAM-HQ ViT-H, 19 classes) with the module names of See-through's checkpoint."""
    nn = torch.nn
    MLP = sys.modules["seethrough_sam.mask_decoder"].MLP
    encoder = modeling.ImageEncoderViT(
        depth=32, embed_dim=1280, img_size=1024, mlp_ratio=4, norm_layer=partial(nn.LayerNorm, eps=1e-6),
        num_heads=16, patch_size=16, qkv_bias=True, use_rel_pos=True, global_attn_indexes=[7, 15, 23, 31],
        window_size=14, out_chans=256)
    prompt = modeling.PromptEncoder(embed_dim=256, image_embedding_size=(64, 64), input_image_size=(1024, 1024),
                                    mask_in_chans=16)
    decoder = modeling.MaskDecoder(
        num_multimask_outputs=3, transformer=modeling.TwoWayTransformer(depth=2, embedding_dim=256, mlp_dim=2048,
                                                                        num_heads=8),
        transformer_dim=256, iou_head_depth=3, iou_head_hidden_dim=256, vit_dim=1280, is_hq=True)
    del decoder.output_hypernetworks_mlps, decoder.hf_mlp

    class Holder(nn.Module):
        pass

    class SemanticSam(nn.Module):

        def __init__(self):
            super().__init__()
            self.img_adapter, self.prompt_adapter, self.mask_adapter = Holder(), Holder(), Holder()
            self.img_adapter.sam_img_encoder = encoder
            self.prompt_adapter.sam_prompt_encoder = prompt
            self.mask_adapter.sam_mask_decoder = decoder
            self.mask_adapter.output_hypernetworks_mlps = nn.ModuleList(
                [MLP(256, 256, 32, 3) for _ in CLASSES])
            self.mask_adapter.hf_mlps = nn.ModuleList([MLP(256, 256, 32, 3) for _ in CLASSES])

        def forward(self, x):
            embeddings, interm = encoder(x, get_interm_embeds=True)
            sparse, dense = prompt(points=None, boxes=None, masks=None)
            image_pe = prompt.get_dense_pe()
            d = decoder
            hq_features = d.embedding_encoder(embeddings) + d.compress_vit_feat(interm[0].permute(0, 3, 1, 2))
            tokens = torch.cat([d.iou_token.weight, d.mask_tokens.weight, d.hf_token.weight], dim=0)
            tokens = torch.cat((tokens.unsqueeze(0).expand(sparse.size(0), -1, -1), sparse), dim=1)
            src = torch.repeat_interleave(embeddings, tokens.shape[0], dim=0) + dense
            pos_src = torch.repeat_interleave(image_pe, tokens.shape[0], dim=0)
            b, c, h, w = src.shape
            hs, src = d.transformer(src, pos_src, tokens)
            # Tokens: iou, 4 SAM mask tokens, HQ token; the semantic heads read the second mask token
            n_mask_tokens = d.num_mask_tokens
            up = d.output_upscaling(src.transpose(1, 2).view(b, c, h, w))
            hyper = torch.stack([m(hs[:, 2, :]) for m in self.mask_adapter.output_hypernetworks_mlps], dim=1)
            hyper_hq = torch.stack([m(hs[:, n_mask_tokens, :]) for m in self.mask_adapter.hf_mlps], dim=1)
            b, c, h, w = up.shape
            masks = (hyper @ up.view(b, c, h * w)).view(b, -1, h, w)
            up_hq = d.embedding_maskfeature(up) + hq_features
            return masks + (hyper_hq @ up_hq.view(b, c, h * w)).view(b, -1, h, w)

    return SemanticSam()


class PartsModel:

    def __init__(self, cache: Path, threads=None):
        import torch

        self.torch = torch
        if threads:
            torch.set_num_threads(threads)
        modeling = fetch_modeling(cache)
        checkpoint = download_model(cache, *CHECKPOINT)
        with torch.device("meta"):
            model = build_model(modeling, torch)
        # Weights only: the checkpoint is a plain state dict (bfloat16), no code is unpickled
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state.get("state_dict", state), strict=True, assign=True)
        self.model = model.float().eval()
        self.bf16 = torch.backends.mkldnn.is_available() and _has_bf16_cpu()

    def parse(self, rgb):
        """Masks of the 19 classes for one image (uint8 RGB), as a dict name -> bool array at the image size."""
        torch = self.torch
        h, w = rgb.shape[:2]
        x = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))[None].float()
        scale = 1024 / max(h, w)
        nh, nw = int(h * scale + 0.5), int(w * scale + 0.5)
        x = torch.nn.functional.interpolate(x, (nh, nw), mode="bilinear", align_corners=False, antialias=True)
        top, left = (1024 - nh) // 2, (1024 - nw) // 2
        x = torch.nn.functional.pad(x, (left, 1024 - nw - left, top, 1024 - nh - top))
        mean = torch.tensor(SAM_MEAN).view(1, 3, 1, 1)
        std = torch.tensor(SAM_STD).view(1, 3, 1, 1)
        x = (x - mean) / std
        with torch.inference_mode(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=self.bf16):
            logits = self.model(x).float()
        logits = torch.nn.functional.interpolate(logits, (1024, 1024), mode="bilinear", align_corners=False)
        logits = logits[..., top:top + nh, left:left + nw]
        logits = torch.nn.functional.interpolate(logits, (h, w), mode="bilinear", align_corners=False)[0]
        masks = (logits > 0).numpy()
        return {name: masks[i] for i, name in enumerate(CLASSES)}


def _has_bf16_cpu():
    """AMX or AVX-512 BF16 makes bfloat16 inference several times faster on the CPU; without it, stay in float32."""
    try:
        with open("/proc/cpuinfo") as f:
            flags = f.read()
        return "amx_bf16" in flags or "avx512_bf16" in flags
    except OSError:
        return False


# --- Parts used by the color sheet --------------------------------------------------------------------------------

def sheet_parts(masks):
    """Hair, eyes, skin, top and bottom masks from See-through's classes (overlaps removed)."""
    hair = masks["hair"] & ~masks["headwear"]
    eyes = masks["eyes"] & ~masks["eyewear"]
    skin = masks["face"] & ~(masks["eyes"] | masks["mouth"] | masks["nose"] | masks["hair"] | masks["eyewear"]
                             | masks["headwear"])
    if skin.sum() < 200:
        skin = skin | (masks["neck"] & ~masks["neckwear"])
    top = masks["topwear"] & ~(masks["hair"] | masks["handwear"] | masks["neckwear"] | masks["objects"])
    bottom = masks["bottomwear"] & ~(masks["topwear"] | masks["handwear"] | masks["objects"])
    return {"hair": hair, "eyes": eyes, "skin": skin, "top": top, "bottom": bottom}


def region_parts(rgb, head_box, person_box):
    """Fallback without the parsing model: rough regions from the head and person boxes.

    Skin: pixels of the head box in the range of natural skin tones; hair: the other pixels of the upper half of the
    head box; top and bottom: bands of the person box under the head. No eyes (too small to place without a model).
    """
    from .measure import rgb_to_oklab, is_natural_skin

    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = head_box
    lab = rgb_to_oklab(rgb[y0:y1, x0:x1])
    natural = np.zeros(lab.shape[:2], bool)
    L = lab[..., 0]
    C = np.hypot(lab[..., 1], lab[..., 2])
    hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    natural = (L > 0.45) & (C > 0.02) & (C < 0.16) & (hue > 30) & (hue < 95)
    skin = np.zeros((h, w), bool)
    skin[y0:y1, x0:x1] = natural
    hair = np.zeros((h, w), bool)
    hy = y0 + (y1 - y0) // 2
    hair[y0:hy, x0:x1] = ~natural[:hy - y0]
    px0, py0, px1, py1 = person_box
    body_h = py1 - y1
    top = np.zeros((h, w), bool)
    bottom = np.zeros((h, w), bool)
    cx0, cx1 = px0 + (px1 - px0) // 5, px1 - (px1 - px0) // 5
    if body_h > (y1 - y0):
        top[y1 + body_h // 10:y1 + body_h * 4 // 10, cx0:cx1] = True
        bottom[y1 + body_h * 5 // 10:y1 + body_h * 8 // 10, cx0:cx1] = True
    return {"hair": hair, "eyes": np.zeros((h, w), bool), "skin": skin, "top": top, "bottom": bottom}


def timed(fn, *args):
    start = time.time()
    result = fn(*args)
    return result, time.time() - start
