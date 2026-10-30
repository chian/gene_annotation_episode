"""Root audit of the bounded new-file delivery; no paper/source interpretation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / "a105_binding_interaction_048"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OWNER / "SHA256.json").read_bytes())
    checked = {}
    for name, expected in manifest.items():
        actual = sha(ROOT / name)
        assert actual == expected, name
        checked[name] = actual
    # Independently reconstruct every delivered all-new file from the patch.
    chunks = (OWNER / "IMPLEMENTATION.patch").read_text().split("--- /dev/null\n")
    assert chunks[0] == ""
    reconstructed = []
    for chunk in chunks[1:]:
        lines = chunk.splitlines(keepends=True)
        assert lines[0].startswith("+++ b/")
        name = lines[0][6:].strip()
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert lines[1].startswith("@@ -0,0 +1,")
        assert all(line.startswith("+") for line in lines[2:])
        content = "".join(line[1:] for line in lines[2:]).encode()
        assert content == (ROOT / name).read_bytes(), name
        target = OUT / "reconstructed_001" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        reconstructed.append(name)
    receipt = {
        "scope": "new pure four-cell binding component delivery only",
        "manifest_verified": checked,
        "independent_patch_reconstruction_matches": reconstructed,
        "owner_terminal_test_receipt": (OWNER / "TEST_RECEIPT.txt").read_text(),
        "parent_read_complete": [
            "606-line calculator", "466-line synthetic test module",
            "PROPOSAL.md (previous goal execution)",
            "CONTRACT_REFINEMENTS_002.md", "HANDOFF.md", "SHA256.json",
        ],
        "no_redundant_pytest_run": True,
        "not_proven": ["scientific source interpretation", "source custody",
                       "selected LiteratureEpisodes execution", "complete A105"],
    }
    with (OUT / "RECEIPT_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"verified_manifest_entries": len(checked),
                      "reconstructed_files": len(reconstructed), "passed": True}))


if __name__ == "__main__":
    main()
