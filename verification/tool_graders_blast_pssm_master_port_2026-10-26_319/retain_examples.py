"""Retain exact public metadata outputs and final source identities, without scoring."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.blast_pssm_master_inputs import extract_blast_pssm_master_metadata
from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm


base = Path(__file__).resolve().parent
sources = ROOT / "verification/tool_graders_blast_pssm_2026-10-26_306/sources"
examples = []
for name in ("pssm_freq_ratios.asn", "pssm_zero_fratios.asn"):
    sheet = read_blast_pssm((sources / name).read_bytes(), format="scoremat_asn_text",
                          artifact_key="retained:" + name, source_ref="pinned-primary-source")
    examples.append(dict(name=name, origin="retained_upstream_native_input",
                         metadata=extract_blast_pssm_master_metadata(sheet)))
for name, length, encoding in (("known-gap", 3, 'ncbieaa "A-D"'),
                               ("length-conflict", 4, 'iupacaa "ACD"'),
                               ("unsupported-encoding", 3, "ncbi8aa '010304'H")):
    text = (f'Pssm ::= {{ numRows 2, numColumns 3, rowLabels {{ "A", "C" }}, '
            f'query seq {{ inst {{ length {length}, seq-data {encoding} }} }}, '
            'intermediateData { freqRatios { 0, 1, 2, 3, 4, 5 } } }')
    sheet = read_blast_pssm(text.encode(), format="scoremat_asn_text",
                          artifact_key="synthetic:" + name, source_ref="synthetic:319")
    examples.append(dict(name=name, origin="synthetic", native_text=text,
                         metadata=extract_blast_pssm_master_metadata(sheet)))
with (base / "metadata_examples.json").open("x") as handle:
    json.dump(examples, handle, indent=2, allow_nan=False)
    handle.write("\n")
paths = [ROOT / name for name in (
    "gene_annotation_episode/blast_pssm_master_inputs.py", "gene_annotation_episode/blast_pssm_calculators.py",
    "gene_annotation_episode/blast_pssm_inputs.py", "tests/test_blast_pssm_master_inputs.py",
    "gene_annotation_episode/blast_iteration_inputs.py", "gene_annotation_episode/blast_iteration_calculators.py",
    "gene_annotation_episode/native_blast_database_metadata.py", "gene_annotation_episode/native_blast_database_result_worker.py")]
paths.extend(base / name for name in ("calculator_baseline.json", "calculator_comparison.json", "metadata_examples.json",
                                    "retain_examples.py", "retain_calculator_comparison.py", "run_checks.py"))
identities = []
for path in paths:
    raw = path.read_bytes()
    identities.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
with (base / "source_hashes_after.json").open("x") as handle:
    json.dump(identities, handle, indent=2)
    handle.write("\n")
for example in examples:
    master = example["metadata"]["records"][0]["master"]
    print(json.dumps(dict(name=example["name"], origin=example["origin"], **{
        key: master[key] for key in ("status", "encoding", "reported_length", "decoded_length")},
        first_symbol=master["sequence"][:1] if master["sequence"] else None,
        last_symbol=master["sequence"][-1:] if master["sequence"] else None,
        mapped_columns=len(master["column_to_residue"]) if master["column_to_residue"] is not None else None)))
