"""Explicit test-only jsonschema fallback with the pinned440 native interpreter."""
import sys

# Keep reference environment h5py/NumPy first. This dependency fallback is
# recorded/pinned by run_bounded; it is not an asserted production binding.
sys.path.append('/home/chia/repos/gene_annotation_episode/.venv/lib/python3.12/site-packages')
import pytest

raise SystemExit(pytest.main(sys.argv[1:]))
