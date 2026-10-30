"""Real tiny Bio.Seq execution, distinct from deliberately corrupt test results."""
from importlib.metadata import version
from pathlib import Path
import hashlib
import json
import sys
import warnings

from Bio.Data import CodonTable
from gene_annotation_episode.sequence_ops import translate

output = Path(sys.argv[1])
cases = [
    ("ordinary_stops_trailing", "ATGTAGAAATAACC", {"code": 1}),
    ("code1_reassignment", "ATATGAAGA", {"code": 1}),
    ("code2_reassignment", "ATATGAAGA", {"code": 2}),
    ("alternative_cds_start", "GTGAAATAA", {"code": 11, "cds": True}),
    ("ambiguous", "GCNRAYWTAATNTARTANNNN", {"code": 1}),
    ("ambiguous_cds", "HTGAAATAR", {"code": 11, "cds": True}),
    ("dual27", "ATGTGATGA", {"code": 27, "cds": True}),
    ("dual28", "ATGTAATGA", {"code": 28, "cds": True}),
    ("dual31", "ATGTAATAG", {"code": 31, "cds": True}),
]
for strand in ("+", "-"):
    for frame in (0, 1, 2):
        cases.append((f"strand_{'plus' if strand == '+' else 'minus'}_frame{frame}",
            "CCATGAAATAACCCGG", {"code": 1, "strand": strand, "frame": frame, "start": 2, "end": 14}))
results = []
for name, sequence, parameters in cases:
    request = {"code": 1, "strand": "+", "frame": 0, "start": 0, "end": len(sequence), "cds": False, **parameters}
    code, cds = request["code"], request["cds"]
    table = CodonTable.unambiguous_dna_by_id[code]
    frozen = {"code": code, "names": list(table.names), "start_codons": list(table.start_codons),
              "stop_codons": list(table.stop_codons), "forward_table": dict(table.forward_table),
              "biopython_version": version("biopython")}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        native = translate(sequence, **request)
    result = {"fixture_kind": "actual_tiny_native_translation", "name": name, "input_sequence": sequence,
        "request": request, "native": native, "genetic_code": frozen,
        "warnings": [str(w.message) for w in caught]}
    try:
        from gene_annotation_episode.sequence_translation_grader import grade_translation
    except ImportError:
        pass
    else:
        mapping = {"version": "oriented_source_subject_path_v2", "units_per_symbol": 1,
            "symbol_length": len(sequence), "path": [{"subject_ref": "supplied:native-example",
            "start": 0, "end": len(sequence), "unit": "nt", "strand": "+"}]}
        result["grading"] = grade_translation(native, input_sequence=sequence,
            subject_ref="supplied:native-example", parent_mapping=mapping, request=request, genetic_code=frozen)
    artifact = output / (name + ".json")
    artifact.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    results.append({"name": name, "product": native["sequence"], "code": code, "cds": cds,
                    "artifact": artifact.name, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    **({"summary": result["grading"]["scores"]["summary"]} if "grading" in result else {})})
(output / "examples.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
