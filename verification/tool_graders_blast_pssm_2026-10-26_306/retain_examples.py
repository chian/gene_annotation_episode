"""Save complete supplied-input sheets/components, inside a protected local job."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm, read_blast_msa_master
from gene_annotation_episode.blast_pssm_calculators import calculate_blast_pssm_components


base = Path(__file__).resolve().parent
destination = Path(sys.argv[1])
destination.mkdir()
summaries = []
for filename in ("pssm_freq_ratios.asn", "pssm_zero_fratios.asn"):
    raw = (base / "sources" / filename).read_bytes()
    sheet = read_blast_pssm(raw, format="scoremat_asn_text", artifact_key="upstream:" + filename,
        source_ref="ncbi-cxx-toolkit-public@d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05/src/algo/blast/unit_tests/api/data/" + filename)
    components = calculate_blast_pssm_components(sheet)
    for label, value in (("sheet", sheet), ("components", components)):
        (destination / (filename + "." + label + ".json")).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    result = components["matrices"][0]
    ratios, scores = result["matrix_values"]["freqRatios"], result["matrix_values"]["scores"]
    summary = {"fixture_origin": "genuine upstream input, not a locally run search", "file": filename,
        "input_identity": sheet["input_identity"], "status": components["status"], "dimensions": result["dimensions"],
        "native_order": result["native_order"], "native_statistics": result["native_statistics"],
        "native_parameters": result["native_parameters"], "master": {k: result["master"][k] for k in ("status", "encoding", "reported_length", "decoded_length")},
        "all_ratio_values_zero": all(v == 0 for row in ratios for v in row),
        "selected_ratio_cells": [{"position": p, "row": r, "value": ratios[p][r]} for p, r in ((0, 1), (116, 10), (231, 22))],
        "selected_score_cells": [{"position": p, "row": r, "value": scores[p][r]} for p, r in ((0, 0), (116, 10), (231, 27))] if scores is not None else None}
    summaries.append(summary)
for filename in ("msa.clustalw.txt", "sample_msa.txt"):
    raw = (base / "sources" / filename).read_bytes()
    sheet = read_blast_msa_master(raw, format="clustal", artifact_key="upstream:" + filename,
        source_ref="ncbi-cxx-toolkit-public@d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05/src/algo/blast/unit_tests/api/data/" + filename,
        master_record_ordinal=0, ignore_master_for_profile=False)
    (destination / (filename + ".sheet.json")).write_text(json.dumps(sheet, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    summaries.append({"fixture_origin": "genuine upstream alignment input, not a locally run alignment", "file": filename,
        "input_identity": sheet["input_identity"], "status": sheet["status"], "alignment_columns": sheet["alignment_columns"],
        "record_count": len(sheet["records"]), "master_identifier": sheet["records"][0]["identifier"],
        "master_ungapped_length": len(sheet["records"][0]["ungapped_sequence"]),
        "master_gap_columns": sum(v["master_position"] is None for v in sheet["master_column_map"]),
        "master_uppercase_selected_columns": sum(v["uppercase_selected"] for v in sheet["master_column_map"])})
synthetic = b'''Pssm ::= { numRows 2, numColumns 3, rowLabels { "A", "C" }, byRow TRUE,
  query seq { inst { repr raw, mol aa, length 3, seq-data iupacaa "ACD" } },
  finalData { scores { -2, 0, 5, 7, -32768, 9 }, lambda { 4, 2, -3 }, kappa 0.125, h 1, scalingFactor 100 } }'''
sheet = read_blast_pssm(synthetic, format="scoremat_asn_text", artifact_key="synthetic:non_square_by_row",
    source_ref="explicit hand-calculation test; not native output")
components = calculate_blast_pssm_components(sheet)
for label, value in (("sheet", sheet), ("components", components)):
    (destination / ("synthetic_non_square." + label + ".json")).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
summaries.append({"fixture_origin": "synthetic hand-calculation fixture", "dimensions": components["matrices"][0]["dimensions"],
    "scores": components["matrices"][0]["matrix_values"]["scores"], "native_statistics": components["matrices"][0]["native_statistics"]})
gap_sheet = read_blast_pssm(synthetic.replace(b'iupacaa "ACD"', b"ncbistdaa '010004'H"),
    format="scoremat_asn_text", artifact_key="synthetic:native_gap_master",
    source_ref="explicit supported-code mapping test; not native output")
gap_components = calculate_blast_pssm_components(gap_sheet)
for label, value in (("sheet", gap_sheet), ("components", gap_components)):
    (destination / ("synthetic_gap_master." + label + ".json")).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
summaries.append({"fixture_origin": "synthetic native-master gap mapping fixture",
    "master": gap_components["matrices"][0]["master"]})
(destination / "NUMERICAL_EXAMPLES.json").write_text(json.dumps(summaries, indent=2, allow_nan=False) + "\n")
manifest = [{"file": str(path.relative_to(base)), "size_bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(destination.glob("*.json"))]
(destination / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(summaries, indent=2))
