"""Retain concrete metadata340 examples; no native search or acquisition."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode import native_blast_standard_database_metadata as standard
from gene_annotation_episode import native_blast_database_metadata as native
from gene_annotation_episode import blast_fasta_record_identity as fasta
from gene_annotation_episode.native_blast_standard_database_calculators import calculate_standard_blast_database_sheets
from gene_annotation_episode.native_blast_database_result_worker import calculate_native_blast_database_sheets
from test_native_blast_standard_database_metadata import run, encoded

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
OUTPUT = Path.cwd()
TESTS = PACKET / "check003/temporary/pytest"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(name, value):
    (OUTPUT / name).write_bytes(encoded(value))


def forbidden(*args, **kwargs):
    raise AssertionError("saved recalculation attempted acquisition, preparation or native parsing")


example = next(TESTS.glob("test_record_v2_retained337_byt*/sheets.json"))
sheets = read(example)
supplied = read(example.with_name("supplied_inputs.json"))
inputs = supplied["inputs"]
inputs.update(contents={k: bytes.fromhex(v) for k, v in supplied["contents_hex"].items()},
              subject_contents={k: bytes.fromhex(v) for k, v in supplied["subject_contents_hex"].items()})
descriptor = deepcopy(inputs["metadata_payloads"][0]["descriptor"])
payload = deepcopy(inputs["metadata_payloads"][0]["payload"])
public = ROOT / "verification/tool_graders_blast_fasta_record_public_associations_2026-10-26_339/check008"
census = (public / "retained_inputs/original_census.json").read_bytes()
assert json.loads(census) == {"total": 1000, "F": 100, "G": 10}
source = dict(source_ref="source-census-v2-340", artifact_ref="artifact-census-v2-340",
              sha256=sha(census), size_bytes=len(census))
inputs["artifact_catalog"]["retained_sources"].append(source)
inputs["contents"][source["artifact_ref"]] = census
payload["documents"].append(dict(document_key="retained-census", artifact=dict(kind="received", **source), format="json"))
payload["searches"][0]["database_profile"] = dict(database="target", release="r1", scope="selected_sequences",
    count_unit="unique_sequences", total_count=1000, function_counts={"F": 100, "G": 10}, source="retained-census")
raw = encoded(payload)
descriptor.update(input_key="metadata-v2-340-census", artifact_ref="artifact-metadata-v2-340-census",
                  sha256=sha(raw), size_bytes=len(raw))
inputs["artifact_catalog"]["retained_sources"].append(dict(source_ref="source-metadata-v2-340-census",
    **{k: descriptor[k] for k in ("artifact_ref", "sha256", "size_bytes")}))
inputs["contents"][descriptor["artifact_ref"]] = raw
inputs["metadata_payloads"] = [dict(descriptor=descriptor, payload=payload)]
census_sheets = run(inputs)
native_examples = [read(path) for path in sorted(TESTS.glob("test_record_v2_native_iter*/native-v2-sheets.json"))
                   if not path.parent.is_symlink()]
assert len(native_examples) == 2
frozen = [sha(encoded(value)) for value in (sheets, census_sheets, *native_examples)]
with ExitStack() as blocked:
    for obj, names in ((standard, ("prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets",
                       "parse_sequences", "validate_native_blast_database_metadata_payload")),
                      (native, ("prepare_native_blast_database_inputs", "populate_native_blast_database_sheets",
                       "parse_sequences", "parse_blast_fasta_source_records")),
                      (fasta, ("parse_sequences", "parse_blast_fasta_source_records")),
                      (socket, ("socket",)), (subprocess, ("Popen", "run")),
                      (Path, ("read_bytes", "read_text"))):
        for name in names:
            blocked.enter_context(patch.object(obj, name, forbidden))
    standard.validate_standard_blast_database_sheet_set(sheets)
    standard.validate_standard_blast_database_sheet_set(census_sheets)
    first = calculate_standard_blast_database_sheets(sheets, sequence_model=None)
    second = calculate_standard_blast_database_sheets(sheets, sequence_model={"temperature_bits": 2})
    adjusted = calculate_standard_blast_database_sheets(census_sheets, sequence_model=None)
    iterations = [calculate_native_blast_database_sheets(value, sequence_model={"temperature_bits": 2}) for value in native_examples]
assert frozen == [sha(encoded(value)) for value in (sheets, census_sheets, *native_examples)]
components = first["sequence"][0]["components"]["components"]
summary = dict(evidence="retained_synthetic_metadata_and_native_format_fixtures_only",
    input_descriptor=inputs["metadata_payloads"][0]["descriptor"],
    original_record_ordinals=[p["proof"]["record_ordinal"] for p in sheets["prepared_inputs"]["sequence_proofs"]],
    normalized_lengths=[p["proof"]["length"] for p in sheets["prepared_inputs"]["sequence_proofs"]],
    normalized_symbol_sha256=[p["proof"]["sha256"] for p in sheets["prepared_inputs"]["sequence_proofs"]],
    masses=components["function_weights"]["function_masses"],
    weights_T1=components["function_weights"]["unadjusted_probabilities"],
    weights_T2=second["sequence"][0]["components"]["components"]["function_weights"]["unadjusted_probabilities"],
    weights_census=adjusted["sequence"][0]["components"]["components"]["function_weights"]["representation_adjusted_probabilities"],
    native_bits=[h["measurements"]["maximum_bit_score"] for h in components["database_sheet"]["hits"]],
    native_iteration_T2=[dict(program=s["prepared_inputs"]["invocation"]["execution_program"],
        weights=c["iteration"]["searches"][0]["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"])
        for s, c in zip(native_examples, iterations)],
    forbidden_parser_recalculation=True, unchanged_saved_sheet_sha256=frozen,
    live_database_search=False, worker_request_and_episode_integration="root_owned_not_run_by340")
for name, value in (("standard_v2_sheets.json", sheets), ("standard_v2_T1.json", first),
                    ("standard_v2_T2.json", second), ("census_v2_sheets.json", census_sheets),
                    ("census_v2_T1.json", adjusted), ("census_v2_payload.json", payload),
                    ("census_v2_descriptor.json", descriptor), ("native_iteration_T2.json", iterations),
                    ("summary.json", summary)):
    write(name, value)
print(json.dumps(summary, indent=2))
