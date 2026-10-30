"""Retain additive test receipts; never invoke a scientific program or service."""

import hashlib
import json
from pathlib import Path
import sys

import pytest

import gene_annotation_episode.bvbrc_codon_tree_native as native
import gene_annotation_episode.phylogeny_format_contracts as formats


EVIDENCE = Path(__file__).resolve().parent
STAGING = EVIDENCE.parent / "staging"
REPOSITORY = EVIDENCE.parents[2]
GOAL = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
CONTRACT = EVIDENCE.parent / "CODON_NATIVE_TABLES_CONTRACT.md"


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)}


assert Path(sys.executable) == REPOSITORY / ".venv/bin/python"
assert Path.cwd() == STAGING
assert Path(native.__file__).resolve() == STAGING / "gene_annotation_episode/bvbrc_codon_tree_native.py"
assert Path(formats.__file__).resolve() == STAGING / "gene_annotation_episode/phylogeny_format_contracts.py"
assert identity(GOAL)["sha256"] == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
assert identity(CONTRACT)["sha256"] == "c6021e7c0d5870efd2a0da0af11c9e83f7869ae2b4ae20d8e5bf7f6da36b4ee4"

label = sys.argv[1]
assert label and all(character.isalnum() or character == "-" for character in label)
report_path = EVIDENCE / (label + ".xml")
receipt_path = EVIDENCE / (label + ".json")
assert not report_path.exists() and not receipt_path.exists()


class CollectedTests:
    def __init__(self):
        self.nodeids = []

    def pytest_collection_modifyitems(self, items):
        self.nodeids = [item.nodeid for item in items]


collection = CollectedTests()
arguments = ["-q", "-p", "no:cacheprovider", "tests/test_bvbrc_codon_tree_native.py",
             "--junitxml=" + str(report_path), *sys.argv[2:]]
receipt = {
    "label": label, "python": sys.executable, "python_version": sys.version,
    "cwd": str(Path.cwd()), "pytest_arguments": arguments,
    "module_paths": {"native": native.__file__, "formats": formats.__file__},
    "inputs": [identity(path) for path in [
        GOAL, CONTRACT, Path(native.__file__), Path(formats.__file__),
        STAGING / "tests/test_bvbrc_codon_tree_native.py", Path(__file__),
    ]],
    "prior_receipt_identities": [identity(path) for path in sorted(
        (EVIDENCE.parent / "codon-native-verification").rglob("*")) if path.is_file()],
}
print(json.dumps({"label": label, "module_paths": receipt["module_paths"]}))
exit_code = int(pytest.main(arguments, plugins=[collection]))
receipt.update({"exit_code": exit_code, "collected_nodeids": collection.nodeids,
                "report": identity(report_path)})
with receipt_path.open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
raise SystemExit(exit_code)
