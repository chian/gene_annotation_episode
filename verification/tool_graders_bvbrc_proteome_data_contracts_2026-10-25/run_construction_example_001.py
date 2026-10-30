"""Record an actual pure-function composition over declared synthetic bytes.

No service, native scientific executable, episode or model is invoked. Input
capture wraps the real parsers solely to retain the exact supplied fixture bytes;
their original results and implementation are used unchanged.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import bvbrc_proteome_inputs as inputs
from gene_annotation_episode import bvbrc_proteome_native as native
from gene_annotation_episode.bvbrc_proteome_joins import build_native_joins
from gene_annotation_episode.bvbrc_proteome_sheet import build_native_sheet
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components


HERE = Path(__file__).parent
DEST = HERE / "construction_example_001"
DEST.mkdir(exist_ok=False)
fixture = runpy.run_path(str(ROOT / "tests/test_bvbrc_proteome_joins.py"))
captured, originals = [], []


def capture(owner, name):
    original = getattr(owner, name)
    originals.append((owner, name, original))
    def invoke(raw, **kwargs):
        result = original(raw, **kwargs)
        path = DEST / f"input_{len(captured):03d}.bin"
        path.write_bytes(raw)
        captured.append({"function": name, "path": str(path.relative_to(ROOT)),
                         "source": kwargs["source"], "byte_sha256": hashlib.sha256(raw).hexdigest(),
                         "byte_count": len(raw)})
        assert captured[-1]["byte_sha256"] == kwargs["source"]["content"]["sha256"]
        return result
    setattr(owner, name, invoke)


for owner, names in ((native, ("parse_genome_comparison",)),
                     (inputs, ("read_protein_fasta", "read_feature_metadata", "read_genome_metadata", "read_feature_sequences"))):
    for name in names:
        capture(owner, name)
original_index = inputs.index_original_inputs
originals.append((inputs, "index_original_inputs", original_index))
def capture_index(task, **kwargs):
    # The fixture explicitly constructs this submitted-parameter object. This
    # retains that synthetic object; it does not authenticate a service task.
    raw = json.dumps({"parameters": task["submitted_parameters"]}).encode()
    field = kwargs["parameter_source"]["source_field"]
    assert hashlib.sha256(raw).hexdigest() == field["sha256"]
    path = DEST / f"input_{len(captured):03d}.bin"
    path.write_bytes(raw)
    (DEST / "SYNTHETIC_ORIGINAL_TASK.json").write_text(json.dumps(task, indent=2) + "\n")
    captured.append({"function": "index_original_inputs", "path": str(path.relative_to(ROOT)),
                     "parameter_source": kwargs["parameter_source"], "byte_sha256": field["sha256"], "byte_count": len(raw)})
    return original_index(task, **kwargs)
inputs.index_original_inputs = capture_index
try:
    data = fixture["metadata_case"]()
    native_envelope = fixture["native_result"]()
finally:
    for owner, name, original in originals:
        setattr(owner, name, original)

before = deepcopy(data)
join_result = build_native_joins(**data)
sheet_result = build_native_sheet([native_envelope], primary_source_ref=data["native"]["source"]["content"]["source_ref"],
    **{key: data[key] for key in ("input_index", "inventories", "feature_snapshots", "genome_snapshots", "sequence_snapshots")},
    joins=join_result["value"], representation_links=[])
assert sheet_result["value"] is not None, sheet_result["diagnostics"]
sheet_before = deepcopy(sheet_result["value"])
parameters = {"version": "bvbrc_proteome_native_parameters_proposal_v1", "track_keys": ["comp_genome_2"],
              "minimum_identity_fraction": .6, "minimum_subject_endpoint_difference_fraction": .7,
              "allowed_hit_categories": None}
components = calculate_native_components(sheet_result["value"], parameters=parameters)
recalculated = calculate_native_components(sheet_result["value"], parameters={**parameters, "minimum_identity_fraction": .9})
assert data == before and sheet_result["value"] == sheet_before
assert components["value"] is not None and recalculated["value"] is not None
assert components["value"]["sheet_sha256"] == recalculated["value"]["sheet_sha256"]
track = components["value"]["tracks"][0]
assert track["first_hsp_identity_summary"]["mean"]["value"] == .4375
assert track["subject_endpoint_difference_summary"]["mean"]["value"] == .625
assert track["selection_counts"]["pass"]["value"] == 1
assert recalculated["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
assert track["reference_input_record_count"]["value"] is None
for name, value in (("SUPPLIED_VALUES", data), ("JOINS", join_result), ("SHEET", sheet_result),
                    ("COMPONENTS", components), ("RECALCULATED_COMPONENTS", recalculated)):
    (DEST / (name + ".json")).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
receipt = {"origin": "constructed_synthetic_inputs_real_A_B1_B2_B3_B4_no_live_service_or_episode",
           "native_inputs": captured, "identity_mean": .4375, "subject_endpoint_difference_mean": .625,
           "selected_before": 1, "selected_after": 0, "executed_reference_count": None,
           "sheet_unchanged": True, "supplied_inputs_unchanged": True,
           "files": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.iterdir())}}
(DEST / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: receipt[key] for key in ("origin", "identity_mean", "subject_endpoint_difference_mean", "selected_before", "selected_after", "executed_reference_count", "sheet_unchanged")}))
