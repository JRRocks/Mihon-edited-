# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "numpy==2.5.4",
#     "opencv-contrib-python-headless==5.0.0.93",
#     "onnxruntime==1.31.0",
#     "pillow==13.0.0",
#     "torch==2.15.0",
#     "truststore==0.10.1",
# ]
#
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
#
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
# ///
"""Color sheet research for Mihon (edited): the official colors of a series' main characters.

    uv run --script color_sheet.py "One Piece"
    uv run --script color_sheet.py "One Piece" --out D:/sheets --report essais/one-piece

Finds the series (AniList, cross-checked on MangaBaka and MangaDex), its main characters, their AniList picture and a
sample of the Japanese volume covers, finds each character on the covers, measures the colors of hair, eyes, skin,
top and bottom, compares them with Danbooru's tags and the series' wiki, and writes the sheet described in section 3
of docs/specs/colorisation-fidele.md. No color is asked of an AI: every color is measured on official images.

Downloads stay out of the repository: images in --work (a temporary folder), models in --cache (shared with the
colorization server). Runs on the CPU; the See-through parts model is about 12 s per image with bfloat16 support,
three times more without it.
"""
import argparse
import sys
import tempfile
import time
from pathlib import Path

import truststore

from colorsheet import report, research, store

# Certificates are checked by the OS, like a browser (as the server does)
truststore.inject_into_ssl()


def main():
    parser = argparse.ArgumentParser(description="Color sheet research for a series (task 2 of docs/PLAN.md)")
    parser.add_argument("title", help="series title, as the app shows it")
    parser.add_argument("--anilist", type=int, help="AniList id of the series, when the title is ambiguous")
    parser.add_argument("--out", type=Path, default=store.default_series_folder(),
                        help="folder of the series sheets (default: %%USERPROFILE%%\\Documents\\Mihon colorisation"
                             "\\series)")
    parser.add_argument("--covers", type=int, default=30, help="Japanese volume covers to sample (default: 30)")
    parser.add_argument("--work", type=Path, default=Path(tempfile.gettempdir()) / "mihon-color-sheet",
                        help="temporary folder for the downloaded images and answers")
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "mihon-colorization",
                        help="where models are downloaded (shared with the colorization server)")
    parser.add_argument("--report", type=Path, help="also write fiche.md, its swatches and a copy of the JSON files "
                                                    "(never the images) in this folder")
    parser.add_argument("--no-parts-model", action="store_true",
                        help="skip See-through (1.3 GB) and measure rough regions around the head instead")
    parser.add_argument("--no-refs", action="store_true", help="don't keep the reference crops (refs/ref-NN.png)")
    args = parser.parse_args()

    start = time.time()
    folder = research.Research(args.title, args.out, args.work, args.cache, covers=args.covers,
                               anilist_id=args.anilist, use_parts_model=not args.no_parts_model,
                               save_refs=not args.no_refs).run()
    if args.report:
        report.write(folder, args.report)
        print(f"Page: {args.report / 'fiche.md'}")
    print(f"Sheet: {folder} ({time.time() - start:.0f} s)")


if __name__ == "__main__":
    sys.exit(main())
