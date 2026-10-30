"""Explicit isolated verification of the released helper dependency, not dispatch.

Load only the retained fcea950a helper module for this test process. Production
modules and registries on disk are untouched. Every other dependency is installed.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import gene_annotation_episode

source = Path(__file__).resolve().parent / "helper_release_001/native_blast_database_metadata.py"
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert digest == "fcea950acf6c54d7cfcf7dd36f607789ffce54a3477f690b70aa2eadf2cc4261"
name = "gene_annotation_episode.native_blast_database_metadata"
assert name not in sys.modules
spec = importlib.util.spec_from_file_location(name, source)
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
gene_annotation_episode.native_blast_database_metadata = module
Path("selected_dependency.json").write_text(json.dumps({"verification_mode": "frozen_helper_dependency",
    "module": name, "path": str(source), "sha256": digest}, indent=2, sort_keys=True) + "\n")

import pytest

raise SystemExit(pytest.main(sys.argv[1:]))
