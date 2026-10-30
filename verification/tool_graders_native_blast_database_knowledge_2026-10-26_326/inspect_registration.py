"""Inspect the actual instruction registration; execute no scientific tool."""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.native_blast_database_contracts import PROGRAMS
from gene_annotation_episode.tool_knowledge import ToolKnowledge

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "gene_annotation_episode/knowledge"


def descriptor(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


before = json.loads((HERE / "index_before_001.json").read_text())
current = json.loads((SOURCE / "index.json").read_text())
assert current["version"] == before["version"]
assert current["entries"][1:] == before["entries"]
entry = current["entries"][0]
assert entry["entry_id"] == "native-blast-database"
assert set(entry["tool_names"]) == {"native." + p for p in PROGRAMS}
assert entry["resource_kinds"] == ["hpc"]
assert len(entry["sections"]) == 2
snapshot = HERE / "registration001/frozen-knowledge"
library = ToolKnowledge.freeze(snapshot)
found = library.search(query="BLAST database HPC", offset=0, limit=100)
assert any(e["entry_id"] == entry["entry_id"] for e in found["entries"])
returned = []
for name in entry["tool_names"]:
    assert entry["entry_id"] in library.entries_for_tool(name)
for section in entry["sections"]:
    actual = library.read(entry_id=entry["entry_id"], section_id=section["section_id"], offset=0, limit=10000)
    assert actual["text"].encode() == (SOURCE / section["path"]).read_bytes()
    assert actual["next_query"] is None
    returned.append(dict(section_id=section["section_id"], lines=actual["returned_lines"],
        sha256=actual["section_sha256"]))
files = [SOURCE / "index.json", *[SOURCE / s["path"] for s in entry["sections"]],
    ROOT / "gene_annotation_episode/native_blast_database_tool_info.py",
    ROOT / "gene_annotation_episode/tool_knowledge.py"]
result = dict(status="verified", added_entry=entry["entry_id"], tool_names=entry["tool_names"],
    resource_kinds=entry["resource_kinds"], all_prior_entries_unchanged=True,
    frozen_library=library.context(), sections=returned, files=[descriptor(p) for p in files],
    scientific_operations_executed=0, new_tests_written=0,
    limitation="Instruction discovery only; not native deployment or complete episode integration.")
with (HERE / "registration001/receipt.json").open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps(result))
