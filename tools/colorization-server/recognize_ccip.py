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
"""Character recognition with CCIP (task 3 of docs/PLAN.md, second try, D25).

    uv run --script recognize_ccip.py <chapter folder> <series sheet folder> --truth truth.json

Same chapter, same character boxes and same truth file as recognize.py: the boxes come from the Magi v2 run
(<chapter>/reconnaissance/recognition.json), so both models are judged on the same crops. Each crop, in gray, is
compared with the sheet's references, in gray, by the large CCIP model the color sheet uses (colorsheet/vision.py,
D31). A crop takes the nearest character's name only when it is close enough and ahead of the second character;
otherwise it stays "Other". Two rules are written: the color sheet's own (D31, set on One Piece covers) and the
model's threshold (best F1 score in its card); a sweep of thresholds shows the best any threshold could do.

Writes <chapter>/reconnaissance/ccip/: recognition.json, named pages (noms/) and, with --truth, evaluation.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from colorsheet.net import download_model
from colorsheet.vision import CCIP_FEATURES, CCIP_METRICS, CCIP_SAME, MARGIN, REF_MATCH, Ccip
from recognize import OTHER, draw, evaluate, gray_rgb, load_bank

RULES = {"regle_de_la_fiche": (REF_MATCH, MARGIN), "seuil_du_modele": (CCIP_SAME, MARGIN)}
SWEEP = (0.08, 0.10, 0.12, 0.15, 0.18, 0.213, 0.25, 0.30, 0.40, 0.60)


def nearest_characters(diff, bank_names, names):
    """Per crop: the difference to each character (its closest reference), sorted from the nearest."""
    per_name = np.stack([diff[:, [i for i, n in enumerate(bank_names) if n == name]].min(axis=1) for name in names],
                        axis=1)
    order = np.argsort(per_name, axis=1)
    return per_name, order


def name_of(per_name, order, names, row, match, margin):
    best, second = per_name[row, order[row, 0]], per_name[row, order[row, 1]]
    return names[order[row, 0]] if best < match and second - best >= margin else OTHER


def with_manga_examples(rows, diff, n_crops, bank_names, main_names, threshold, missed):
    """Like recognize.with_manga_examples, with CCIP differences: each crop is named by its nearest example among the
    sheet's references plus the characters of the other pages, as the truth file names them (optimistic)."""
    scores = {}
    for label, kept in (("sheet_only", ()), ("sheet_and_other_pages", main_names),
                        ("sheet_and_other_pages_with_supporting_cast", main_names | {"other"})):
        good = total = false_main = 0
        for row, (page, expected) in enumerate(rows):
            if expected not in main_names and expected != "other":
                continue
            examples = [j for j, (p, e) in enumerate(rows) if p != page and e in kept]
            candidates = list(range(n_crops, n_crops + len(bank_names))) + examples
            candidate_names = bank_names + [rows[j][1] if rows[j][1] in main_names else OTHER for j in examples]
            distances = diff[row, candidates]
            nearest = int(distances.argmin())
            name = candidate_names[nearest] if distances[nearest] < threshold else OTHER
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
    parser = argparse.ArgumentParser(description="Names the characters of a chapter with CCIP (task 3, D25)")
    parser.add_argument("chapter", type=Path, help="folder with page-NNN images and reconnaissance/recognition.json")
    parser.add_argument("sheet", type=Path, help="series sheet folder (characters/<id>/character.json)")
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "mihon-colorization",
                        help="model cache (shared with the colorization server and the color sheet)")
    parser.add_argument("--truth", type=Path, help="truth file: page -> {box number: name or 'other'}")
    args = parser.parse_args()

    magi = json.loads((args.chapter / "reconnaissance" / "recognition.json").read_text(encoding="utf-8"))
    out = args.chapter / "reconnaissance" / "ccip"
    (out / "noms").mkdir(parents=True, exist_ok=True)

    start = time.time()
    model = Ccip(download_model(args.cache, *CCIP_FEATURES), download_model(args.cache, *CCIP_METRICS))
    bank = load_bank(args.sheet)
    print(f"CCIP ready ({time.time() - start:.0f} s); bank: {len(bank['images'])} examples", flush=True)

    crops, where = [], []
    for page in magi["pages_detail"]:
        image = Image.open(args.chapter / f"{page['page']}.png")
        for character in page["characters"]:
            crops.append(gray_rgb(image.crop(tuple(character["box"]))))
            where.append((page["page"], character["n"]))
    started = time.time()
    features = model.features(crops + bank["images"])
    diff = model.differences(features)
    seconds = time.time() - started
    print(f"{len(crops)} crops and {len(bank['images'])} references: {seconds:.0f} s", flush=True)
    # Control: on the sheet's own references (gray), the nearest other reference should show the same character
    refs = diff[len(crops):, len(crops):].copy()
    np.fill_diagonal(refs, np.inf)
    twice = [i for i, n in enumerate(bank["names"]) if bank["names"].count(n) > 1]
    self_check = f"{sum(bank['names'][int(refs[i].argmin())] == bank['names'][i] for i in twice)} / {len(twice)}"
    print(f"Sheet references, in gray: nearest other reference is the same character {self_check}", flush=True)

    names = sorted(set(bank["names"]))
    per_name, order = nearest_characters(diff[:len(crops), len(crops):], bank["names"], names)
    report, row = {rule: [] for rule in RULES}, 0
    detail = []
    for page in magi["pages_detail"]:
        entries = {rule: {"page": page["page"], "characters": []} for rule in RULES}
        for character in page["characters"]:
            found = {"n": character["n"], "box": character["box"],
                     "nearest": names[order[row, 0]], "difference": round(float(per_name[row, order[row, 0]]), 3),
                     "second": names[order[row, 1]], "second_difference": round(float(per_name[row, order[row, 1]]), 3)}
            for rule, (match, margin) in RULES.items():
                name = name_of(per_name, order, names, row, match, margin)
                found[rule] = name
                entries[rule]["characters"].append({"n": character["n"], "name": name})
            detail.append({"page": page["page"], **found})
            row += 1
        for rule in RULES:
            report[rule].append(entries[rule])
        image = Image.open(args.chapter / f"{page['page']}.png")
        mine = [c for c in detail if c["page"] == page["page"]]
        draw(image, {"panels": page["panels"], "characters": [c["box"] for c in mine]},
             [f"{c['n']} {c['regle_de_la_fiche']}" for c in mine], out / "noms" / f"{page['page']}.jpg")

    summary = {"chapter": magi["chapter"], "boxes_from": "reconnaissance/recognition.json (Magi v2)",
               "model": CCIP_FEATURES[1].rsplit("/", 1)[0], "seconds_per_crop": round(seconds / len(crops + bank["images"]), 2),
               "rules": {rule: {"match": m, "margin": g} for rule, (m, g) in RULES.items()},
               "bank": bank["origin"], "bank_self_check": self_check, "characters": detail}
    (out / "recognition.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    if not args.truth:
        return
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    main_names = set(names)
    result = {rule: evaluate(report[rule], truth, main_names) for rule in RULES}
    labels = [truth.get(page, {}).get(str(n), "?") for page, n in where]
    detected_main = [i for i, label in enumerate(labels) if label in main_names]
    result["nearest_is_right"] = f"{sum(names[order[i, 0]] == labels[i] for i in detected_main)} / {len(detected_main)}"
    missed = sum(len(truth.get(p["page"], {}).get("missed", [])) for p in magi["pages_detail"])
    sweep = []
    for margin in (0.0, MARGIN):
        for match in SWEEP:
            good = sum(name_of(per_name, order, names, i, match, margin) == labels[i] for i in detected_main)
            false_main = sum(name_of(per_name, order, names, i, match, margin) != OTHER
                             for i, label in enumerate(labels) if label == "other")
            sweep.append({"match": match, "margin": margin, "good_names": good,
                          "rate": round(good / (len(detected_main) + missed), 3),
                          "others_given_a_main_name": false_main})
    result["sweep"] = sweep
    rows = [(page, label) for (page, _), label in zip(where, labels)]
    result["nearest_example"] = with_manga_examples(rows, diff, len(crops), bank["names"], main_names, CCIP_SAME,
                                                    missed)
    (out / "evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for rule in RULES:
        print(rule, json.dumps({k: v for k, v in result[rule].items() if k != "errors"}, ensure_ascii=False))
    print("nearest is right:", result["nearest_is_right"])
    for line in sweep:
        print("  sweep", line)
    print("manga examples:", json.dumps(result["nearest_example"], ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
