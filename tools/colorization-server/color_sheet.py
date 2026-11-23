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

Placeholder entry point, completed below.
"""
import sys

if __name__ == "__main__":
    import torch

    print(sys.version, torch.__version__)
