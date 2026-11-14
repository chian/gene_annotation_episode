"""Expose the repository's generic test controllers to A110 checks."""

from pathlib import Path
import sys

_ROOT_TESTS = Path(__file__).resolve().parents[5] / 'tests'
if str(_ROOT_TESTS) not in sys.path:
    sys.path.insert(0, str(_ROOT_TESTS))
