"""Run only historical BLAST callers with a hash-verified prechange module."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

directory = Path(__file__).resolve().parent
sys.path.insert(0, str(directory.parents[1]))
original = directory / "blast_database_grader.prechange.py"
expected = json.loads((directory / "legacy_prechange.json").read_text())["provenance"]["module_sha256"]
actual = hashlib.sha256(original.read_bytes()).hexdigest()
if actual != expected:
    raise ValueError("Prechange copy does not match the originally captured module SHA256")

import gene_annotation_episode

name = "gene_annotation_episode.blast_database_grader"
spec = importlib.util.spec_from_file_location(name, original)
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
gene_annotation_episode.blast_database_grader = module
print(json.dumps({"loaded_prechange_module": str(original), "sha256": actual,
                  "production_module_replaced": False}), flush=True)

import pytest

raise SystemExit(pytest.main(["-q", "tests/test_blast_binding.py",
    "--junitxml=" + str(directory / "prechange_historical.junit.xml")]))
