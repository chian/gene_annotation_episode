"""Freeze 340's tested sources and retained evidence; no scientific execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
OWNED = {
    "gene_annotation_episode/native_blast_database_metadata.py": "4292386638f1a624358d52109914d54d34562741c4d5eeada753465d4b29a19b",
    "gene_annotation_episode/native_blast_standard_database_metadata.py": "f378270daadb53b6925664934b951a6a09295b3ba77e65aa169eb5abdbfaccc3",
    "tests/test_native_blast_database_metadata.py": "0f2f72ae7b4e1695440dba56d178cbc6d3a32607c183b67d5258c0b498b8c575",
    "tests/test_native_blast_standard_database_metadata.py": "f42e64b49c585cfdfb86a704217e1488eaadd74e7ff31341cf0c98fbaafdaab4",
}
DEPENDENCIES = {
    "gene_annotation_episode/blast_fasta_record_identity.py": "e2c2ee8308c37a457d290ba617ff3ca019306c25dbdc74409dd2426b4c5b2f1c",
    "gene_annotation_episode/blast_sequence_database.py": "1d087ae80979cf75caa0ead61cf58dd8e66e41d37e2e1474e019efd2b487585f",
    "gene_annotation_episode/blast_database_grader.py": "b2d376d1f12cff80d051ac987beaa46c77ffe3ad05743e84ca1ff07e627515cf",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def describe(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(raw), size_bytes=len(raw))


goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(goal.read_bytes()) == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
before = read(PACKET / "before.json")
for row in before:
    assert sha((PACKET / "before" / row["path"]).read_bytes()) == row["sha256"]
for path, expected in (OWNED | DEPENDENCIES).items():
    assert sha((ROOT / path).read_bytes()) == expected, path
for path in OWNED:
    target = PACKET / "final_sources" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / path).read_bytes())

stable = []
for name in ("check003", "check004"):
    initial = {r["path"]: r["sha256"] for r in read(PACKET / name / "source_snapshot.json")}
    final = {r["path"]: r["sha256"] for r in read(PACKET / name / "source_after.json")}
    changed = sorted(path for path in initial if initial[path] != final[path])
    assert all(initial[path] == final[path] == expected for path, expected in OWNED.items())
    if name == "check003":
        assert changed == []
    stable.append(dict(check=name, changed_sources=changed, owned_sources_equal_final=True,
                       receipt=read(PACKET / name / "receipt.json")))

native_path = "gene_annotation_episode/native_blast_database_metadata.py"
original = (PACKET / "before" / native_path).read_bytes().splitlines(keepends=True)
current = (ROOT / native_path).read_bytes().splitlines(keepends=True)
preserved = []
for fragment in (b'if expected is None or row["artifact_key"] != _metadata_capture_key',
                 b'if key is not None and key != _metadata_capture_key'):
    old = [(i + 1, line) for i, line in enumerate(original) if fragment in line]
    new = [(i + 1, line) for i, line in enumerate(current) if fragment in line]
    assert len(old) == len(new) == 1 and old[0][1] == new[0][1]
    preserved.append(dict(before_line=old[0][0], final_line=new[0][0],
        exact_bytes_sha256=sha(old[0][1]), text=old[0][1].decode().rstrip("\n")))

examples = list((PACKET / "check004").glob("*.json"))
tests = PACKET / "check003/temporary/pytest"
for directory in ("test_record_v2_retained337_byt0", "test_record_v2_native_iteratio0",
                  "test_record_v2_native_iteratio1", "test_M3_multiple_fasta_records0"):
    examples.extend(path for path in (tests / directory).iterdir() if path.is_file())
evidence = dict(
    schema="blast_fasta_record_metadata_handoff_evidence_v1",
    authoritative_goal_sha256=sha(goal.read_bytes()),
    before=before, final_owned=[describe(ROOT / path) for path in OWNED],
    frozen_public339_dependencies=[describe(ROOT / path) for path in DEPENDENCIES],
    source_stability=stable, preserved335_lines=preserved,
    test_results=[dict(check="check001", passed=140, failed=0),
                  dict(check="check002", passed=188, failed=1,
                       detail="wrong_expected_rejection_code_in_test_corrected_without_production_change"),
                  dict(check="check003", passed=649, failed=0)],
    numerical_replay=read(PACKET / "check004/summary.json"),
    examples=[describe(path) for path in sorted(set(examples))],
    integration_boundary="complete_worker_request_reuse_publication_typed_episode_return_owned_by343_and_root",
    live_database_execution=False)
(PACKET / "HANDOFF_EVIDENCE_001.json").write_text(json.dumps(evidence, indent=2) + "\n")
(PACKET / "final.sha256").write_text("".join(f"{digest}  {path}\n" for path, digest in (OWNED | DEPENDENCIES).items()))
print(json.dumps(dict(source_snapshot_verified=True, regression_passed=649,
    preserved335_lines=preserved, numerical_replay=evidence["numerical_replay"]), indent=2))
