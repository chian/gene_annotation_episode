"""Root delivery audit after complete reader/test review; no source images read."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / "a105_binding_visual_reader_049"


def main():
    manifest = json.loads((OWNER / "MANIFEST.json").read_bytes())
    verified = []
    for row in manifest["files"]:
        raw = (ROOT / row["path"]).read_bytes()
        assert len(raw) == row["bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], row["path"]
        verified.append(row["path"])
    rebuilt = []
    chunks = (OWNER / "implementation.patch").read_text().split("--- /dev/null\n")
    assert chunks[0] == ""
    for chunk in chunks[1:]:
        lines = chunk.splitlines(keepends=True)
        assert lines[0].startswith("+++ b/") and lines[1].startswith("@@ -0,0 +1,")
        name = lines[0][6:].strip()
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert all(line.startswith("+") for line in lines[2:])
        raw = "".join(line[1:] for line in lines[2:]).encode()
        assert raw == (ROOT / name).read_bytes()
        target = OUT / "reconstructed_001" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        rebuilt.append(name)
    terminal = json.loads((OWNER / "terminal_test_evidence.json").read_bytes())
    assert terminal["exit_code"] == 0 and terminal["stderr"] == ""
    assert terminal["stdout"].splitlines()[-1] == "579 passed in 2.41s"
    receipt = {"passed": True, "verified_manifest_files": verified,
        "reconstructed_new_files": rebuilt, "terminal_evidence": terminal,
        "parent_read_complete": ["538-line reader", "403-line synthetic test module",
                                 "PROPOSAL.md", "IMPLEMENTATION.md", "MANIFEST.json"],
        "not_proven": ["image transcription correctness", "scientific source meaning",
                       "selected native integration", "complete A105"],
        "no_redundant_pytest_or_paper_read": True}
    with (OUT / "RECEIPT_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": True, "manifest_entries": len(verified),
                      "independent_patch_reconstructions": len(rebuilt)}))


if __name__ == "__main__":
    main()
