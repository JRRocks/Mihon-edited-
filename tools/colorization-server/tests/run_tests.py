# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "numpy==2.5.4",
#     "opencv-contrib-python-headless==5.0.0.93",
#     "pytest==9.2.0",
# ]
# ///
"""Tests of the color sheet's pure part (measurement and doubt rules): uv run --script tests/run_tests.py"""
import sys
from pathlib import Path

import pytest

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
sys.exit(pytest.main([str(here), "-q", "-p", "no:cacheprovider", *sys.argv[1:]]))
