"""Summarize preserved verification attempts without rewriting earlier receipts."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
STAGING = HERE.parent / "staging"


def file_fact(path):
    data = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


notes = {
    "pytest-initial.xml": "28 passed; native LGF partition vs LG log association rejected. Corrected documented empirical-frequency F suffix handling.",
    "pytest-model-correction.xml": "29 passed after model suffix correction.",
    "pytest-validation-expansion.xml": "29 passed after saved-source relationship expansion.",
    "pytest-adversarial-expansion.xml": "39 passed,9 failed: one real declared-matrix-scope calculator defect;8 misplaced test-tail NameErrors. Test placement corrected; calculator issue separately assigned.",
    "pytest-model-request-expansion.xml": "68 passed,3 failed assertions: malformed FASTA retained a value; actual parameter name is freq pi(...); duplicate index uses duplicate_index. Assertions corrected without weakening required behavior.",
    "pytest-scoped-matrix-before-dependency.xml": "81 passed,2 failures reproduced the actual old calculator's complete-main and complete-empty scope defect. Historical staged calculator remains unchanged.",
    "pytest-corrected-dependency.xml": "83 passed with exact corrected production calculator through the real filesystem dependency overlay.",
    "pytest-combined.xml": "584 passed+9subtests; one historical calculator source-path assertion rejects the intentionally corrected production dependency. No numerical or relationship failure.",
    "pytest-model-conflict.xml": "1 selected test passed;83 deselected. Conflicting fitted model records retained separately with error diagnostic.",
    "pytest-identity-correction.xml": "89 passed with exact original-content/member-pointer identity correction.",
    "pytest-final-combined.xml": "590 passed+9subtests; obsolete source-path assertion still ran because the relative --deselect node prefix did not match its repository-qualified nodeid. This is the same location-only failure; no numerical failure.",
    "pytest-final-location-selection.xml": "590 passed+9subtests,1 deselected: only the uniquely named historical calculator source-path assertion. run_tests.py independently verifies11 actual imported paths and hashes, including corrected production calculator.",
}
history = []
for path in sorted(HERE.glob("pytest-*.xml")):
    tree = ET.parse(path)
    suites = tree.getroot().findall("testsuite")
    history.append({"file": file_fact(path), "suites": [dict(s.attrib) for s in suites],
        "failures": [{"name": t.attrib.get("name"), "classname": t.attrib.get("classname"),
            "message": t.find("failure").attrib.get("message")} for s in suites for t in s.findall("testcase") if t.find("failure") is not None],
        "interpretation": notes.get(path.name)})
examples = HERE / "examples"
native_sheet = json.loads((examples / "retained_native_nine_row.sheet.json").read_text())
native = json.loads((examples / "retained_native_nine_row.components.json").read_text())
hand = json.loads((examples / "source_syntax_hand_components.components.json").read_text())
historical = json.loads((examples / "historical_frequency_hand_values.components.json").read_text())
own = [STAGING / "gene_annotation_episode" / name for name in ("bvbrc_codon_tree_inputs.py", "bvbrc_codon_tree_grader.py")]
own.append(STAGING / "tests" / "test_bvbrc_codon_tree_provider.py")
receipt = {"owned_files": [file_fact(p) for p in own], "test_history": history,
    "imports": json.loads((HERE / "verified-imports.json").read_text()),
    "native_numeric_examples": {"literal_statistics": native["literal_statistics"][0],
        "tree_tip_count": native["trees"][0]["tip_count"], "tree_branch_sum": native["trees"][0]["branch_length_sum"],
        "family_count": len(native_sheet["families"]),
        "membership_record_count": sum(len(f["memberships"]) for f in native_sheet["families"]),
        "native_log_likelihoods": [o for o in native_sheet["native_measurements"] if o["field"] == "log_likelihood"]},
    "hand_numeric_examples": {"literal_statistics": hand["literal_statistics"][0],
        "family_population": hand["family_populations"][0], "historical": historical["worst_sequence_ratios"]},
    "offline_replays": json.loads((HERE / "offline-replays.json").read_text()),
    "scope": {"live_scientific_jobs": 0, "source_byte_custody_authenticated": False,
        "new_episode_actions": 0, "annotation_credit_change": False, "full_episode_integration_verified": False}}
(HERE / "VERIFICATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"attempts_preserved": len(history), "offline_replays": len(receipt["offline_replays"]),
    "owned_files": receipt["owned_files"]}, indent=2))
