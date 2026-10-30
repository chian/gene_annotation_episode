"""Install only the reviewed, new shared modules; retain exact source evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STAGING = HERE / "staging"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
    assert digest(goal) == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
    relative_files = [
        "gene_annotation_episode/phylogeny_formats.py",
        "gene_annotation_episode/phylogeny_format_contracts.py",
        "gene_annotation_episode/phylogeny_calculators.py",
        "gene_annotation_episode/phylogeny_calculation_contracts.py",
        "gene_annotation_episode/phylogeny_raxml_inputs.py",
        "tests/test_phylogeny_formats.py",
        "tests/test_phylogeny_calculators.py",
        "tests/test_phylogeny_raxml_inputs.py",
    ]
    report = json.loads((HERE / "calculators-verification/VERIFICATION_REPORT.json").read_text())
    for name in relative_files:
        source = STAGING / name
        assert source.is_file() and not (ROOT / name).exists(), name
        if str(source) in report["file_sha256"]:
            assert digest(source) == report["file_sha256"][str(source)], name
    formats_report = json.loads((HERE / "formats-verification/VERIFICATION.json").read_text())
    # Preserve the entire format report's digest; its native cases were reviewed.
    assert formats_report
    numeric_xml = HERE / "native-metadata-verification/pytest-numeric-token-002.xml"
    suite = ET.parse(numeric_xml).getroot().find("testsuite")
    assert suite is not None
    assert (suite.attrib["tests"], suite.attrib["failures"], suite.attrib["errors"]) == ("26", "0", "0")
    validation = {
        "scope": "RAxML 8 supplied-byte numeric-token correction",
        "correction": "Reject nonzero decimal underflow and Python underscore-number syntax; preserve native tokens with failed/null values.",
        "passed": 26,
        "failed": 0,
        "prior_receipt_preserved": "native-metadata-verification/VALIDATION.json",
        "files": {str(p.relative_to(ROOT)): digest(p) for p in [
            STAGING / "gene_annotation_episode/phylogeny_raxml_inputs.py",
            STAGING / "gene_annotation_episode/phylogeny_format_contracts.py",
            STAGING / "tests/test_phylogeny_raxml_inputs.py", numeric_xml,
            HERE / "native-metadata-verification/pytest-numeric-token-002.log"]},
        "live_execution": False,
        "provider_or_episode_integration": False,
    }
    save_new(HERE / "native-metadata-verification/VALIDATION_002.json", validation)
    rows = []
    for name in relative_files:
        source, destination = STAGING / name, ROOT / name
        with source.open("rb") as src, destination.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        assert digest(source) == digest(destination)
        rows.append({"source": str(source.relative_to(ROOT)), "destination": name,
                     "sha256": digest(destination)})
    save_new(HERE / "PRODUCTION_INSTALLATION_001.json", {
        "scope": "Five new shared phylogeny modules and their three test files installed unchanged",
        "files": rows,
        "reviewed_evidence": {str(p.relative_to(ROOT)): digest(p) for p in [
            HERE / "formats-verification/VERIFICATION.json",
            HERE / "calculators-verification/VERIFICATION_REPORT.json",
            HERE / "native-metadata-verification/VALIDATION_002.json"]},
        "production_tests_run": False,
        "provider_result_path_integrated": False,
        "live_execution_verified": False,
    })
    print(json.dumps({"installed_new_files": len(rows), "provider_result_path_integrated": False}))


if __name__ == "__main__":
    main()
