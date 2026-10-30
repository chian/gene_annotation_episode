"""Install reviewed pure Codon components without altering staged evidence."""
from pathlib import Path
import hashlib
import json


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGING = HERE / "staging"
FILES = {
    "gene_annotation_episode/bvbrc_codon_tree_native.py": "3f83d5c0268b8efa43c593a873cebe212f6acaf0f4626f064c14272f70d86340",
    "tests/test_bvbrc_codon_tree_native.py": "ff708a1c2a7587d12d4ad4d03a5a69c7bf39b6339c8a72ef43f32541db43311e",
    "gene_annotation_episode/bvbrc_codon_tree_calculators.py": "e23d8aa26b90d9089819b1e8faac5a8b6c9f8b4da39fbfcb5a89934158ba4904",
    "tests/test_bvbrc_codon_tree_calculators.py": "9ff70ea1f10eccced4cb3a0ac597e16a597542e6eae40344b7b003e991d5cd0f",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
    assert digest(goal.read_bytes()) == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
    contents = {}
    for name, expected in FILES.items():
        data = (STAGING / name).read_bytes()
        assert digest(data) == expected, name
        assert not (ROOT / name).exists(), name
        contents[name] = data
    # Only the copied test fixture roots differ. Native bytes, arithmetic,
    # assertions and all original staging receipts remain unchanged.
    changes = {
        "tests/test_bvbrc_codon_tree_native.py": (
            "VERIFICATION = Path(__file__).resolve().parents[3]",
            'VERIFICATION = STAGING / "verification"',
        ),
        "tests/test_bvbrc_codon_tree_calculators.py": (
            'VERIFY = STAGING.parent / "codon-calculators-verification"\n'
            'BOUNDARIES = STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"',
            'BOUNDARIES = STAGING / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"',
        ),
    }
    rows = []
    for name, data in contents.items():
        if name in changes:
            before, after = changes[name]
            text = data.decode()
            assert text.count(before) == 1, name
            data = text.replace(before, after).encode()
        with (ROOT / name).open("xb") as stream:
            stream.write(data)
        assert digest((ROOT / name).read_bytes()) == digest(data)
        rows.append({"path": name, "staged_sha256": FILES[name],
                     "installed_sha256": digest(data),
                     "only_fixture_root_adjusted": name in changes})
    evidence = [
        HERE / "codon-native-numeric-correction-125/VALIDATION.json",
        HERE / "codon-calculators-verification/VERIFICATION_REPORT_004.json",
        HERE / "codon-calculators-verification/SAVED_RECALCULATION_004.json",
    ]
    record = {
        "scope": "Install two pure Codon modules and their tests; adjust copied test fixture paths only",
        "files": rows,
        "reviewed_evidence": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in evidence},
        "provider_or_episode_integration": False,
        "live_execution_verified": False,
        "production_tests_run": False,
    }
    with (HERE / "PRODUCTION_CODON_INSTALLATION_001.json").open("x") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"installed_files": len(rows), "scientific_modules_unchanged": 2,
                      "test_fixture_roots_adjusted": len(changes)}))


if __name__ == "__main__":
    main()
