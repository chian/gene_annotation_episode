"""Run declared engineering checks from one immutable code/test generation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    pin = Path(__file__).resolve().parent
    sys.path[:0] = [str(pin), str(pin / "tests")]
    manifest_path = pin / "PIN_MANIFEST.json"
    assert digest(manifest_path) == args.manifest_sha256
    manifest = json.loads(manifest_path.read_bytes())
    def verify_pin():
        for name, row in manifest["files"].items():
            path = pin / name
            assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], name
    verify_pin()
    import gene_annotation_episode
    import method_loop
    import pytest
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    for module in (gene_annotation_episode, method_loop):
        assert Path(module.__file__).resolve().is_relative_to(pin)
    before = LiteratureEpisodes(None, rate_population=True).as_record()
    files = ["tests/test_literature_kinetic_count_inputs.py", "tests/test_literature_kinetic_count_integration.py",
        "tests/test_literature_kinetic_calculations.py", "tests/test_literature_kinetic_inputs.py",
        "tests/test_literature_kinetic_storage.py", "tests/test_literature_kinetic_integration.py",
        "tests/test_literature_kinetic_witness_publication.py"]
    selected = ["-q", *files, "--tb=short", "-p", "no:cacheprovider", "--basetemp=" + str(args.output / "pytest")]
    code = pytest.main(selected)
    assert LiteratureEpisodes(None, rate_population=True).as_record() == before
    imported = 0
    for name, module in tuple(sys.modules.items()):
        if name.startswith(("gene_annotation_episode", "method_loop", "test_literature_kinetic")) and getattr(module, "__file__", None):
            assert Path(module.__file__).resolve().is_relative_to(pin), name
            imported += 1
    verify_pin()
    receipt = {"pytest_exit_code": int(code), "pytest_arguments": selected,
        "pin_manifest_sha256": args.manifest_sha256, "pin_files_verified": len(manifest["files"]),
        "all_manifested_files_exact_before_after": True, "C7_binding_before_after_exact": True,
        "C7_binding": before, "application_and_test_imports_verified_from_pin": imported,
        "controlled_synthetic_engineering_tests": True, "configured_model_or_primary_source_execution": False}
    with (args.output / "WORKER_RECEIPT.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"pytest_exit_code": int(code), "pin_files_verified": len(manifest["files"]),
        "C7_binding_stable": True, "pinned_imports": imported}))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
