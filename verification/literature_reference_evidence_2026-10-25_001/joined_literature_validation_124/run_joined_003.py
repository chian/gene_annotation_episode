"""Root combined engineering verification; never a scientific/model proof."""
from pathlib import Path
import hashlib
import json
import sys

import pytest
import gene_annotation_episode.literature_episodes as binding_module


BASE = Path(__file__).resolve().parent
PIN = BASE / "pin_003"
assert Path.cwd().resolve() == PIN
assert Path(binding_module.__file__).resolve().is_relative_to(PIN)
SELECTION = [
    "tests/test_literature_gel_prompt.py",
    "tests/test_literature_gel_storage.py",
    "tests/test_literature_gel_episode_integration.py::test_actual_independent_worker_original_c1_c4_form_and_saved_parent_decision",
    "tests/test_literature_controlled_response_prompt.py"
]

with (BASE / "COMMAND_003.json").open("x") as stream:
    json.dump({"cwd": str(PIN), "python": sys.executable,
               "pytest_arguments": ["-q", "-x", "--junitxml=" + str(BASE / "TESTS_003.xml"), *SELECTION],
               "claim": "Constructed engineering plus existing primary-byte fixture tests; no new model call or scientific interpretation."}, stream, indent=2)

result = pytest.main(["-q", "-x", "--junitxml=" + str(BASE / "TESTS_003.xml"), *SELECTION])
imports = {}
for name, module in tuple(sys.modules.items()):
    file = getattr(module, "__file__", None)
    if not file or not name.startswith(("gene_annotation_episode", "method_loop", "test_literature")):
        continue
    path = Path(file).resolve()
    if path.suffix != ".py":
        continue
    assert path.is_relative_to(PIN), (name, str(path))
    imports[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
with (BASE / "ACTUAL_PARENT_IMPORTS_003.json").open("x") as stream:
    json.dump(imports, stream, indent=2)
manifest = json.loads((BASE / "PIN_MANIFEST_003.json").read_text())
changed = [name for name, digest in manifest["files"].items()
           if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
with (BASE / "RESULT_003.json").open("x") as stream:
    json.dump({"pytest_exit": int(result), "original_pin_files_checked": len(manifest["files"]),
               "changed_pin_files": changed, "actual_parent_imports": len(imports),
               "limits": "Parent/test imports audited; worker import paths are not independently enumerated here. No configured-model scientific-use claim."}, stream, indent=2)
assert not changed, changed
raise SystemExit(int(result))
