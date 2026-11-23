# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "einops==0.8.0",
#     "matplotlib==3.9.2",
#     "networkx==3.4.2",
#     "numpy==2.1.3",
#     "pillow==11.0.0",
#     "pulp==2.9.0",
#     "scipy==1.14.1",
#     "shapely==2.0.6",
#     "timm==1.0.11",
#     "torch==2.5.1",
#     "torchvision==0.20.1",
#     "transformers==4.46.3",
#     "truststore==0.10.1",
# ]
#
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
# torchvision = { index = "pytorch-cpu" }
#
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
# ///
"""Character recognition on a whole chapter, with the names of a series color sheet (task 3 of docs/PLAN.md).

    uv run --script recognize.py <chapter folder> <series sheet folder> [--truth truth.json]

The chapter folder holds page-NNN.png/jpg in reading order (a test set kept by the server with --capture, or a CBZ
unpacked the same way). The sheet is the one written by color_sheet.py: characters/<id>/character.json, with its
references (official color images). Missing reference crops are downloaded from the sheet's URLs and cut out with
its boxes, into characters/<id>/refs/, outside the repository.

Model: Magi v2 (ragavsachdeva/magiv2, fixed commit, personal and research use), on the CPU, without its OCR. It finds
panels, texts and characters, groups the characters of a page, and names them from a bank of examples; a character
too far from every example stays "Other". Pages already in color are left out, as the app does.

Writes <chapter>/reconnaissance/: recognition.json (boxes, names, distances), numbered pages (numeros/, to write the
truth file without seeing the names) and named pages (noms/). With --truth (page -> {box number: name or "other"}),
also writes the rate of good names on the main characters, in evaluation.json.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import truststore
from PIL import Image, ImageDraw, ImageFont

truststore.inject_into_ssl()

MAGI_REPO = "ragavsachdeva/magiv2"
MAGI_REVISION = "fbc890fec52977142e8ee00bfe26e9458b65517c"
MAGI_FILES = {  # file -> SHA-256 (weights) or None (code and config, read before first use)
    "config.json": None, "configuration_magiv2.py": None, "modelling_magiv2.py": None,
    "processing_magiv2.py": None, "utils.py": None,
    "pytorch_model.bin": "56392403204d3a4cca38694a3a260a6929d741869d802d6b14de35b4eab4c4b8",
}
USER_AGENT = "mihon-colorization-recognize/0.1"
OTHER = "Other"


def magi_folder(cache: Path):
    folder = cache / f"magiv2-{MAGI_REVISION[:7]}"
    missing = [name for name in MAGI_FILES if not (folder / name).exists()]
    if missing:
        sys.exit(f"Magi v2 is missing in {folder}: {', '.join(missing)} (from huggingface.co/{MAGI_REPO}, "
                 f"commit {MAGI_REVISION})")
    return folder


def load_magi(cache: Path):
    os.environ.setdefault("HF_HOME", str(cache / "hf"))
    os.environ["HF_HUB_OFFLINE"] = "1"
    import torch
    from transformers import AutoConfig, AutoModel
    torch.set_num_threads(os.cpu_count() or 4)
    folder = magi_folder(cache)
    config = AutoConfig.from_pretrained(folder, trust_remote_code=True)
    config.disable_ocr = True  # names only: no text reading, no extra download
    config.detection_model_config.use_pretrained_backbone = False  # Magi's own weights replace ImageNet's
    model = AutoModel.from_pretrained(folder, config=config, trust_remote_code=True).eval()
    return model, torch


def gray_rgb(image: Image.Image):
    """What Magi v2 expects: the page in gray, as three channels."""
    return np.array(image.convert("L").convert("RGB"))


def is_color(image: Image.Image, share=0.03):
    hsv = np.array(image.convert("RGB").convert("HSV"))
    colored = (hsv[..., 1] > 60) & (hsv[..., 2] > 40)
    return colored.mean() > share


def download(url, target: Path):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        target.write_bytes(response.read())
    time.sleep(1)


def load_bank(sheet: Path):
    """One example per reference image of each character: the sheet's crop, in gray."""
    images, names, origin = [], [], []
    for path in sorted(sheet.glob("characters/*/character.json")):
        character = json.loads(path.read_text(encoding="utf-8"))
        name = character["names"]["main"]
        for ref in character.get("refs", []):
            crop = path.parent / "refs" / f"{ref['id']}.png"
            if not crop.exists():
                source = path.parent / "refs" / "sources" / Path(ref["url"].split("?")[0]).name
                source.parent.mkdir(parents=True, exist_ok=True)
                if not source.exists():
                    download(ref["url"], source)
                image = Image.open(source).convert("RGB")
                if ref.get("box"):
                    image = image.crop(tuple(ref["box"]))
                image.save(crop)
            images.append(gray_rgb(Image.open(crop)))
            names.append(name)
            origin.append(f"{character['id']}/{ref['id']} ({ref.get('kind')})")
    return {"images": images, "names": names, "origin": origin}


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def draw(page: Image.Image, result, labels, target: Path):
    image = page.convert("RGB")
    pen = ImageDraw.Draw(image)
    size = max(16, image.width // 45)
    for box in result["panels"]:
        pen.rectangle(box, outline=(150, 150, 150), width=2)
    for n, (box, label) in enumerate(zip(result["characters"], labels), 1):
        color = (0, 130, 255) if label in (str(n),) else ((120, 120, 120) if label.endswith(OTHER) else (230, 30, 30))
        pen.rectangle(box, outline=color, width=4)
        x, y = box[0] + 4, max(0, box[1] - size - 6)
        width = pen.textlength(label, font=font(size))
        pen.rectangle((x - 3, y - 2, x + width + 3, y + size + 4), fill=(255, 255, 255))
        pen.text((x, y), label, fill=color, font=font(size))
    image.save(target, quality=88)


def evaluate(pages, truth, main_names):
    good = wrong = missed = false_main = other = 0
    errors = []
    for page in pages:
        page_truth = truth.get(page["page"], {})
        for n, character in enumerate(page["characters"], 1):
            expected = page_truth.get(str(n), "?")
            name = character["name"]
            if expected in main_names:
                if name == expected:
                    good += 1
                else:
                    wrong += 1
                    errors.append(f"{page['page']} #{n}: {expected} lu {name}")
            elif expected == "other":
                other += 1
                if name != OTHER:
                    false_main += 1
                    errors.append(f"{page['page']} #{n}: autre personnage lu {name}")
        for name in page_truth.get("missed", []):
            missed += 1
            errors.append(f"{page['page']}: {name} non détecté")
    total = good + wrong + missed
    return {"main_instances": total, "good_names": good, "wrong_names": wrong, "not_detected": missed,
            "rate": round(good / total, 3) if total else None, "other_instances": other,
            "others_given_a_main_name": false_main, "errors": errors}


def with_manga_examples(report, truth, crops, refs, bank_names, main_names, eta):
    """What gray examples taken from the manga would bring: each page is named by its nearest example among the
    sheet's references plus the characters of the other pages of the chapter, as the truth file names them.
    Optimistic (same chapter, same outfits), so it is an upper bound for examples from earlier chapters."""
    rows, row = [], 0
    for index, page in enumerate(report):
        page_truth = truth.get(page["page"], {})
        for character in page["characters"]:
            rows.append((index, row, page_truth.get(str(character["n"]), "?")))
            row += 1
    missed = sum(len(truth.get(page["page"], {}).get("missed", [])) for page in report)
    scores = {}
    # sheet only; + main characters seen on the other pages; + every character seen on the other pages, the ones
    # outside the sheet standing for the supporting cast a fuller sheet would hold (nearest one = no main name)
    for label, kept in (("sheet_only", ()), ("sheet_and_other_pages", main_names),
                        ("sheet_and_other_pages_with_supporting_cast", main_names | {"other"})):
        good = total = false_main = 0
        for index, row, expected in rows:
            if expected not in main_names and expected != "other":
                continue
            examples = [(r, e) for i, r, e in rows if i != index and e in kept]
            candidates = np.concatenate([refs, crops[[r for r, e in examples]]]) if examples else refs
            names = bank_names + [e if e in main_names else OTHER for r, e in examples]
            distances = np.linalg.norm(candidates - crops[row], axis=1)
            nearest = int(distances.argmin())
            name = names[nearest] if distances[nearest] < eta else OTHER
            if expected in main_names:
                total += 1
                good += name == expected
            elif name != OTHER:
                false_main += 1
        scores[label] = {"good_names": good, "main_instances": total + missed,
                         "rate": round(good / (total + missed), 3) if total + missed else None,
                         "others_given_a_main_name": false_main}
    return scores


def main():
    parser = argparse.ArgumentParser(description="Names the characters of a chapter from a series sheet (task 3)")
    parser.add_argument("chapter", type=Path, help="folder with page-NNN images in reading order")
    parser.add_argument("sheet", type=Path, help="series sheet folder (characters/<id>/character.json)")
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "mihon-colorization",
                        help="model cache (shared with the colorization server)")
    parser.add_argument("--eta", type=float, default=0.75, help="distance above which a character stays Other")
    parser.add_argument("--truth", type=Path, help="truth file: page -> {box number: name or 'other'}")
    parser.add_argument("--out", type=Path, help="output folder (default: <chapter>/reconnaissance)")
    args = parser.parse_args()

    out = args.out or args.chapter / "reconnaissance"
    for sub in ("numeros", "noms"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in args.chapter.glob("page-*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    kept, skipped = [], []
    for path in files:
        (skipped if is_color(Image.open(path)) else kept).append(path)
    print(f"{len(kept)} pages, {len(skipped)} already in color left out: {[p.name for p in skipped]}", flush=True)

    start = time.time()
    bank = load_bank(args.sheet)
    print(f"Bank: {len(bank['images'])} examples of {len(set(bank['names']))} characters", flush=True)
    model, torch = load_magi(args.cache)
    print(f"Magi v2 ready ({time.time() - start:.0f} s)", flush=True)

    pages = [gray_rgb(Image.open(p)) for p in kept]
    started = time.time()
    with torch.no_grad():
        results = model.do_chapter_wide_prediction(pages, bank, eta=args.eta, batch_size=2, do_ocr=False)
        boxes = [r["characters"] for r in results]
        crops = torch.cat(model.predict_crop_embeddings(pages, boxes), dim=0)
        refs = torch.cat(model.predict_crop_embeddings(
            bank["images"], [[[0, 0, x.shape[1], x.shape[0]]] for x in bank["images"]]), dim=0)
        crops = torch.nn.functional.normalize(crops, p=2, dim=1).numpy()
        refs = torch.nn.functional.normalize(refs, p=2, dim=1).numpy()
    seconds = time.time() - started
    distances = np.linalg.norm(crops[:, None, :] - refs[None, :, :], axis=2)
    names = sorted(set(bank["names"]))
    per_name = np.stack([distances[:, [i for i, n in enumerate(bank["names"]) if n == name]].min(axis=1)
                         for name in names], axis=1) if len(crops) else np.zeros((0, len(names)))

    report, row = [], 0
    for path, page, result in zip(kept, pages, results):
        characters = []
        for n, (box, name, cluster) in enumerate(zip(result["characters"], result["character_names"],
                                                     result["character_cluster_labels"]), 1):
            order = np.argsort(per_name[row])
            characters.append({"n": n, "box": [round(float(v)) for v in box], "name": name, "group": int(cluster),
                               "nearest": names[order[0]], "distance": round(float(per_name[row][order[0]]), 3),
                               "second": names[order[1]] if len(order) > 1 else None,
                               "second_distance": round(float(per_name[row][order[1]]), 3) if len(order) > 1 else None})
            row += 1
        entry = {"page": path.stem, "panels": [[round(float(v)) for v in b] for b in result["panels"]],
                 "texts": len(result["texts"]), "characters": characters}
        report.append(entry)
        image = Image.open(path)
        draw(image, {"panels": entry["panels"], "characters": [c["box"] for c in characters]},
             [str(c["n"]) for c in characters], out / "numeros" / f"{path.stem}.jpg")
        draw(image, {"panels": entry["panels"], "characters": [c["box"] for c in characters]},
             [f"{c['n']} {c['name']}" for c in characters], out / "noms" / f"{path.stem}.jpg")

    summary = {"chapter": str(args.chapter.name), "pages": len(kept), "left_out": [p.name for p in skipped],
               "seconds_per_page": round(seconds / max(1, len(kept)), 1), "eta": args.eta,
               "model": f"{MAGI_REPO}@{MAGI_REVISION}", "bank": bank["origin"], "pages_detail": report}
    (out / "recognition.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    found = sum(len(p["characters"]) for p in report)
    print(f"{found} characters on {len(kept)} pages, {summary['seconds_per_page']} s per page; "
          f"named: {sum(c['name'] != OTHER for p in report for c in p['characters'])}", flush=True)

    if args.truth:
        truth = json.loads(args.truth.read_text(encoding="utf-8"))
        result = evaluate(report, truth, set(names))
        result["nearest_example"] = with_manga_examples(report, truth, crops, refs, bank["names"], set(names),
                                                        args.eta)
        (out / "evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "errors"}, ensure_ascii=False))
        for line in result["errors"]:
            print("  " + line)


if __name__ == "__main__":
    sys.exit(main())
