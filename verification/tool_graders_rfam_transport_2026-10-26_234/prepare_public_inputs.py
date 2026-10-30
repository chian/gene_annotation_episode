"""Freeze disclosed transformations of the public Rfam documentation example."""
import hashlib
import json
from pathlib import Path


directory = Path(__file__).resolve().parent
source = directory.parent / "tool_graders_rfam_contract_2026-10-26_232/examples/official-single-result.json"
original = json.loads(source.read_bytes())["searchSequence"]
assert len(original) == 119
complement = str.maketrans("ACGT", "TGCA")
records = [
    ("rfam_example_original", original, "unchanged public documentation sequence"),
    ("rfam_example_repeat", original, "same sequence repeated under a different FASTA header"),
    ("rfam_example_reverse_complement", original.translate(complement)[::-1],
     "reverse complement of public sequence; A:T and C:G DNA complement"),
    ("rfam_example_prefix70", original[:70], "first 70 nt of public sequence, original positions 1..70"),
    ("rfam_example_insertion", original[:60] + "A" + original[60:],
     "insert one A after original position 60"),
    ("rfam_example_deletion", original[:60] + original[61:], "delete original position 61"),
]
for name, selected in (("single", records[:1]), ("multi", records)):
    job = directory / "live" / name
    job.mkdir(parents=True)
    content = ((original + "\n").encode("ascii") if name == "single" else
               "".join(f">{header}\n{seq}\n" for header, seq, _ in selected).encode("ascii"))
    (job / "input.seq").write_bytes(content)
    manifest = {"fixture_kind": "public119nt_example_and_disclosed_transformations",
                "source_url": "https://docs.rfam.org/en/latest/api.html",
                "source_fixture": str(source.relative_to(directory.parent.parent)),
                "source_fixture_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "filename": "sequence.seq" if name == "single" else "public119-transformations.fasta",
                "file_sha256": hashlib.sha256(content).hexdigest(), "file_bytes": len(content),
                "total_sequence_nt": sum(len(seq) for _, seq, _ in selected),
                "records": [{"query_occurrence_key": f"public119-{name}-occurrence-{ordinal}",
                             "original_record_ordinal": ordinal,
                             "original_header": header if name == "multi" else None,
                             "submitted_sequence": seq, "transformation": transform,
                             "submitted_sequence_sha256": hashlib.sha256(seq.encode("ascii")).hexdigest(),
                             "submitted_length_nt": len(seq)}
                            for ordinal, (header, seq, transform) in enumerate(selected)]}
    (job / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"job": name, "records": len(selected), "total_sequence_nt": manifest["total_sequence_nt"]}))
