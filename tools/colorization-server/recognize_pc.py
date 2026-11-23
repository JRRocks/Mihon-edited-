# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "numpy==2.5.4",
#     "opencv-contrib-python-headless==5.0.0.93",
#     "onnxruntime==1.31.0",
#     "pillow==13.0.0",
#     "truststore==0.10.1",
# ]
# ///
"""PC rungs of the recognition ladder (task 3b of docs/PLAN.md, D27, D28, D38).

    uv run --script recognize_pc.py <chapter folder> <series sheet folder> --truth truth.json --detect-only
    uv run --script recognize_pc.py <chapter folder> <series sheet folder> --truth truth.json --new-truth new.json

Two local models, judged on the chapter, the Magi v2 boxes and the truth file of recognize.py:
- a detector trained on Manga109 (black-and-white manga: body, face, frame, text) looks for the characters Magi v2
  left without a box. Its boxes that cover no Magi box are numbered d1, d2... on reconnaissance/pc/nouveaux/; with
  --detect-only the script stops there, so that the truth of these new boxes is written without seeing any name;
- the WD EVA02-Large tagger v3 (Danbooru tags) names each box, Magi's and the new ones: a box takes the sheet
  character whose Danbooru tag (character.json, words.danbooru_tag) is above the threshold and ahead of every other
  character tag; otherwise it stays "Other". It also reads whole pages: which sheet characters are on the page.

Writes <chapter>/reconnaissance/pc/: detection.json, tagging.json, named pages (noms/) and evaluation.json.
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from colorsheet.net import download_model
from colorsheet.vision import Yolo, box_iou, inside_fraction
from recognize import OTHER, draw, evaluate, font, gray_rgb

HF = "https://huggingface.co"
MANGA109 = ("deepghs-manga109_yolo-v2023.12.07_l_yv11.onnx",
            f"{HF}/deepghs/manga109_yolo/resolve/6b5730a9f1f34581b87468f2c609e3269a9faccf/v2023.12.07_l_yv11/model.onnx",
            "66f6fbf6435d26a6b93880ba52fdc0cecbf8634ab8e52a20f70c1625c6ae0723")
MANGA109_LABELS = ("body", "face", "frame", "text")  # labels.json at the same commit
MANGA109_THRESHOLD = 0.373  # threshold.json at the same commit (best F1 score, 0.92)
MANGA109_LONGEST = 640  # its training size; the page keeps its proportions (model exported with dynamic sizes)
WD = f"{HF}/SmilingWolf/wd-eva02-large-tagger-v3/resolve/b25b82a03f7282e41aa2f257a52c7583b710bd1c"
WD_MODEL = ("smilingwolf-wd-eva02-large-tagger-v3.onnx", f"{WD}/model.onnx",
            "9e768793060c7939b277ccb382783e8670e8a042d29d77aa736be0c8cc898bfc")
WD_TAGS = ("smilingwolf-wd-eva02-large-tagger-v3-selected_tags.csv", f"{WD}/selected_tags.csv",
           "298633d94d0031d2081c0893f29c82eab7f0df00b08483ba8f29d1e979441217")  # git blob a2a653a5 checked
CHARACTER_CATEGORY = "4"
CHARACTER_THRESHOLD = 0.85  # the tagger demo's default for character tags
PAGE_THRESHOLDS = (0.35, 0.85)
SWEEP = (0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 0.95)
SAME_CHARACTER = 0.3  # a detector box with this IoU with a Magi box, or mostly inside it, shows the same character
MOSTLY = 0.6


class Tagger:
    """WD tagger v3: the image padded to a white square, resized, BGR 0-255 (as in the model's demo)."""

    def __init__(self, model_path, tags_path):
        import onnxruntime

        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(str(model_path), options, providers=["CPUExecutionProvider"])
        model_input = self.session.get_inputs()[0]
        self.input_name, self.size = model_input.name, model_input.shape[1]
        with open(tags_path, newline="", encoding="utf-8") as tags:
            rows = list(csv.DictReader(tags))
        self.tags = [row["name"] for row in rows]
        self.characters = [i for i, row in enumerate(rows) if row["category"] == CHARACTER_CATEGORY]

    def probabilities(self, image: Image.Image):
        image = image.convert("RGB")
        side = max(image.size)
        square = Image.new("RGB", (side, side), (255, 255, 255))
        square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
        if side != self.size:
            square = square.resize((self.size, self.size), Image.Resampling.BICUBIC)
        x = np.ascontiguousarray(np.asarray(square, dtype=np.float32)[:, :, ::-1][None])
        return self.session.run(None, {self.input_name: x})[0][0]


def sheet_tags(sheet: Path, tagger: Tagger):
    """Sheet character name -> index of its Danbooru tag in the tagger's list (absent when the tagger lacks it)."""
    known, unknown = {}, []
    for path in sorted(sheet.glob("characters/*/character.json")):
        character = json.loads(path.read_text(encoding="utf-8"))
        name, tag = character["names"]["main"], character.get("words", {}).get("danbooru_tag")
        if tag in tagger.tags:
            known[name] = tagger.tags.index(tag)
        else:
            unknown.append(name)
    return known, unknown


def reading(probs, known, tagger):
    """The most likely sheet character and the most likely character tag outside the sheet, with their scores."""
    best = max(known, key=lambda name: probs[known[name]])
    sheet_indexes = set(known.values())
    rival = max((i for i in tagger.characters if i not in sheet_indexes), key=lambda i: probs[i])
    top = sorted(tagger.characters, key=lambda i: -probs[i])[:3]
    return {"best": best, "score": round(float(probs[known[best]]), 3),
            "rival": tagger.tags[rival], "rival_score": round(float(probs[rival]), 3),
            "top": [[tagger.tags[i], round(float(probs[i]), 3)] for i in top]}


def name_of(read, threshold):
    return read["best"] if read["score"] >= threshold and read["score"] > read["rival_score"] else OTHER


def candidates(found):
    """The detector's characters: each body, and each face outside every body (a character seen as a face only)."""
    bodies = [f for f in found if MANGA109_LABELS[f[5]] == "body"]
    faces = [f for f in found if MANGA109_LABELS[f[5]] == "face"
             and all(inside_fraction(f[:4], b[:4]) < MOSTLY for b in bodies)]
    return [{"box": list(f[:4]), "kind": MANGA109_LABELS[f[5]], "score": round(f[4], 3)} for f in bodies + faces]


def same_character(box, other):
    return (box_iou(box, other) >= SAME_CHARACTER or inside_fraction(box, other) >= MOSTLY
            or inside_fraction(other, box) >= MOSTLY)


def draw_new(page: Image.Image, magi_boxes, new, target: Path):
    """The page with Magi's boxes (gray, their numbers) and the detector's new boxes (orange, d1, d2...), no name."""
    image = page.convert("RGB")
    pen = ImageDraw.Draw(image)
    size = max(16, image.width // 45)
    for n, box in enumerate(magi_boxes, 1):
        pen.rectangle(box, outline=(150, 150, 150), width=2)
        pen.text((box[0] + 4, box[1] + 2), str(n), fill=(120, 120, 120), font=font(size))
    for c in new:
        box, label = c["box"], c["id"]
        pen.rectangle(box, outline=(255, 120, 0), width=5)
        x, y = box[0] + 4, max(0, box[1] - size - 6)
        width = pen.textlength(label, font=font(size))
        pen.rectangle((x - 3, y - 2, x + width + 3, y + size + 4), fill=(255, 255, 255))
        pen.text((x, y), label, fill=(255, 120, 0), font=font(size))
    image.save(target, quality=88)


def main():
    parser = argparse.ArgumentParser(description="PC rungs of the recognition ladder (task 3b, D38)")
    parser.add_argument("chapter", type=Path, help="folder with page-NNN images and reconnaissance/recognition.json")
    parser.add_argument("sheet", type=Path, help="series sheet folder (characters/<id>/character.json)")
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "mihon-colorization",
                        help="model cache (shared with the colorization server and the color sheet)")
    parser.add_argument("--truth", type=Path, help="truth file of the Magi boxes: page -> {box number: name}")
    parser.add_argument("--new-truth", type=Path, help="truth file of the new boxes: page -> {d1: name or 'other'}")
    parser.add_argument("--longest", type=int, default=MANGA109_LONGEST,
                        help="longest side of the page given to the detector (0: stretched to its square size)")
    parser.add_argument("--detect-only", action="store_true", help="stop after drawing the new boxes, unnamed")
    args = parser.parse_args()

    magi = json.loads((args.chapter / "reconnaissance" / "recognition.json").read_text(encoding="utf-8"))
    out = args.chapter / "reconnaissance" / "pc"
    for folder in ("nouveaux", "noms"):
        (out / folder).mkdir(parents=True, exist_ok=True)
    truth = json.loads(args.truth.read_text(encoding="utf-8")) if args.truth else {}

    detector = Yolo(download_model(args.cache, *MANGA109), MANGA109_THRESHOLD, 0.7, args.longest or None)
    started, detection = time.time(), []
    for page in magi["pages_detail"]:
        image = Image.open(args.chapter / f"{page['page']}.png")
        found = candidates(detector.detect_classes(gray_rgb(image)))
        magi_boxes = [c["box"] for c in page["characters"]]
        for c in found:
            c["magi"] = [n for n, box in enumerate(magi_boxes, 1) if same_character(c["box"], box)]
        new = sorted((c for c in found if not c["magi"]), key=lambda c: (c["box"][1], c["box"][0]))
        for number, c in enumerate(new, 1):
            c["id"] = f"d{number}"
        found_magi = sorted({n for c in found for n in c["magi"]})
        detection.append({"page": page["page"], "found": found, "magi_boxes_found": found_magi})
        draw_new(image, magi_boxes, new, out / "nouveaux" / f"{page['page']}.jpg")
    seconds = (time.time() - started) / len(magi["pages_detail"])
    (out / "detection.json").write_text(json.dumps({"model": MANGA109[1], "threshold": MANGA109_THRESHOLD,
                                                    "longest_side": args.longest,
                                                    "seconds_per_page": round(seconds, 2), "pages": detection},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    news = sum(1 for p in detection for c in p["found"] if not c["magi"])
    print(f"Detector: {seconds:.1f} s per page, {news} new boxes (pc/nouveaux/)", flush=True)
    if args.detect_only:
        return

    tagger = Tagger(download_model(args.cache, *WD_MODEL), download_model(args.cache, *WD_TAGS))
    known, unknown = sheet_tags(args.sheet, tagger)
    print(f"Tagger: {len(known)} sheet characters known, unknown: {', '.join(unknown) or 'none'}", flush=True)
    started, crops, pages = time.time(), [], []
    for page, found in zip(magi["pages_detail"], detection):
        image = Image.open(args.chapter / f"{page['page']}.png")
        gray = Image.fromarray(gray_rgb(image))
        probs = tagger.probabilities(gray)
        pages.append({"page": page["page"], **reading(probs, known, tagger),
                      "sheet_scores": {name: round(float(probs[i]), 3) for name, i in known.items()}})
        for c in page["characters"]:
            crops.append({"page": page["page"], "id": str(c["n"]), "box": c["box"],
                          **reading(tagger.probabilities(gray.crop(tuple(c["box"]))), known, tagger)})
        for c in found["found"]:
            if not c["magi"]:
                crops.append({"page": page["page"], "id": c["id"], "box": c["box"], "kind": c["kind"],
                              **reading(tagger.probabilities(gray.crop(tuple(c["box"]))), known, tagger)})
    seconds = (time.time() - started) / (len(crops) + len(pages))
    (out / "tagging.json").write_text(json.dumps({"model": WD_MODEL[1], "sheet_tags": {n: tagger.tags[i] for n, i in
                                                                                        known.items()},
                                                  "not_in_tagger": unknown, "seconds_per_image": round(seconds, 2),
                                                  "pages": pages, "crops": crops}, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"Tagger: {seconds:.1f} s per image, {len(crops)} crops", flush=True)
    for page, found in zip(magi["pages_detail"], detection):
        mine = [c for c in crops if c["page"] == page["page"]]
        image = Image.open(args.chapter / f"{page['page']}.png")
        draw(image, {"panels": page["panels"], "characters": [c["box"] for c in mine]},
             [f"{c['id']} {name_of(c, CHARACTER_THRESHOLD)}" for c in mine], out / "noms" / f"{page['page']}.jpg")
    if not args.truth:
        return

    main_names = set(known) | set(unknown)
    new_truth = json.loads(args.new_truth.read_text(encoding="utf-8")) if args.new_truth else {}
    result = {"detector": detector_scores(magi, detection, truth, new_truth, main_names)}
    for threshold in SWEEP:
        result[f"tagger_{threshold}"] = tagger_scores(magi, crops, truth, new_truth, main_names, threshold)
    result["pages"] = page_scores(pages, truth, new_truth, main_names)
    (out / "evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("detector", json.dumps(result["detector"], ensure_ascii=False))
    for threshold in SWEEP:
        line = {k: v for k, v in result[f"tagger_{threshold}"].items() if k != "errors"}
        print(f"tagger {threshold}", json.dumps(line, ensure_ascii=False))
    print("pages", json.dumps(result["pages"]["summary"], ensure_ascii=False))


def detector_scores(magi, detection, truth, new_truth, main_names):
    """What the detector adds to Magi (missed appearances found again) and what it finds alone."""
    framed = found_again = recovered = extra_main = new_others = 0
    for page, found in zip(magi["pages_detail"], detection):
        page_truth, page_new = truth.get(page["page"], {}), new_truth.get(page["page"], {})
        mains = [n for n in range(1, len(page["characters"]) + 1) if page_truth.get(str(n)) in main_names]
        framed += len(mains)
        found_again += sum(n in found["magi_boxes_found"] for n in mains)
        missed = list(page_truth.get("missed", []))
        for label in page_new.values():
            if label in missed:
                missed.remove(label)
                recovered += 1
            elif label in main_names:
                extra_main += 1
            elif label == "other":
                new_others += 1
    missed_total = sum(len(truth.get(p["page"], {}).get("missed", [])) for p in magi["pages_detail"])
    return {"main_framed_by_magi": framed, "of_which_detector_finds_too": found_again,
            "missed_by_magi": missed_total, "missed_found_by_detector": recovered,
            "new_main_not_in_truth": extra_main, "new_boxes_other": new_others,
            "with_detector": f"{framed + recovered} / {framed + missed_total}",
            "detector_alone": f"{found_again + recovered} / {framed + missed_total}"}


def tagger_scores(magi, crops, truth, new_truth, main_names, threshold):
    """Names on Magi's boxes (recognize.evaluate), then on the detector's new boxes, at one threshold."""
    report = [{"page": p["page"], "characters": [{"name": name_of(c, threshold)} for c in crops
                                                 if c["page"] == p["page"] and not c["id"].startswith("d")]}
              for p in magi["pages_detail"]]
    scores = evaluate(report, truth, main_names)
    good_new = wrong_new = false_new = 0
    for c in crops:
        if not c["id"].startswith("d"):
            continue
        expected, name = new_truth.get(c["page"], {}).get(c["id"], "?"), name_of(c, threshold)
        if expected in main_names:
            good_new += name == expected
            wrong_new += name != expected
            if name != expected:
                scores["errors"].append(f"{c['page']} {c['id']}: {expected} lu {name}")
        elif expected == "other" and name != OTHER:
            false_new += 1
            scores["errors"].append(f"{c['page']} {c['id']}: autre personnage lu {name}")
    scores.update({"new_boxes_good": good_new, "new_boxes_wrong": wrong_new, "new_boxes_others_named": false_new,
                   "good_with_detector": f"{scores['good_names'] + good_new} / {scores['main_instances']}"})
    return scores


def page_scores(pages, truth, new_truth, main_names):
    """Whole pages: the sheet characters the tagger sees on each page, against those the truth puts there."""
    detail, summary = [], {str(t): {"right": 0, "wrong": 0, "missing": 0} for t in PAGE_THRESHOLDS}
    for page in pages:
        page_truth = truth.get(page["page"], {})
        present = {v for k, v in page_truth.items() if k != "missed" and v in main_names}
        present |= set(page_truth.get("missed", [])) | {v for v in new_truth.get(page["page"], {}).values()
                                                         if v in main_names}
        row = {"page": page["page"], "truth": sorted(present)}
        for t in PAGE_THRESHOLDS:
            seen = {name for name, p in page["sheet_scores"].items() if p >= t}
            row[str(t)] = sorted(seen)
            summary[str(t)]["right"] += len(seen & present)
            summary[str(t)]["wrong"] += len(seen - present)
            summary[str(t)]["missing"] += len(present - seen)
        detail.append(row)
    return {"summary": summary, "detail": detail}


if __name__ == "__main__":
    sys.exit(main())
