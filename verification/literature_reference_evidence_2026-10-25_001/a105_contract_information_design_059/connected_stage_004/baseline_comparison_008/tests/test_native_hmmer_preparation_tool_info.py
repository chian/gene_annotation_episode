"""I1 information/schema verification against retained actual P1 requests.

No native program is executed here. Complete episode dispatch is verified by the
separate integration workload, not inferred from these information constructors.
"""
import builtins
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.native_hmmer_preparation_contracts import (
    PROGRAM_MODES, operand_contract, output_contract,
    validate_native_hmmer_preparation_requested_job,
)
from gene_annotation_episode.native_hmmer_preparation_job_schema import preparation_requested_job_schema
from gene_annotation_episode.native_hmmer_preparation_tool_info import (
    native_hmmer_preparation_tool_contracts,
    native_hmmer_preparation_tool_information,
    validate_native_hmmer_preparation_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "verification/tool_graders_hmmer_preparation_producer_2026-10-26_267"
NATIVE_CASES = PRODUCER / "check005_native_cases.json"
NATIVE_CASES_SHA256 = "1ac655502d673ce9d61c8eada0d7d95c17a812222568a07b8d3dde1dd5cc5bae"
# Independent fixed enumeration: adding/removing a P1 mode must not silently
# present it as a reviewed instruction set in this information-only workload.
EXPECTED_MODES = {
    "alimask": ("mask_alignment", "mask_model", "model_to_alignment", "alignment_to_model"),
    "hmmbuild": ("build_alignment", "build_single_sequence_matrix"),
    "hmmconvert": ("ascii", "binary", "legacy_hmmer2"),
    "hmmemit": ("sample_core_unaligned", "sample_core_aligned", "consensus_simple", "consensus_thresholded", "sample_profile"),
    "hmmfetch": ("single_key", "key_file", "index"),
    "hmmpress": ("index",),
    "hmmsim": ("viterbi", "msv", "forward", "hybrid"),
    "hmmstat": ("summary",),
    "makehmmerdb": ("build",),
    "hmmerfm-exactmatch": ("locations", "count_only"),
}
CASES = [(program, mode) for program, modes in EXPECTED_MODES.items() for mode in modes]
INFORMATION_FIELDS = {"name", "description", "resources", "instructions"}
CONTRACT_FIELDS = INFORMATION_FIELDS | {"input_schema", "invocation_route"}


@pytest.fixture(scope="module")
def retained_requests():
    raw = NATIVE_CASES.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == NATIVE_CASES_SHA256
    requests = {}
    for case in json.loads(raw)["cases"]:
        if "/test_actual_all_selected_modes" not in case["case"]:
            continue
        raw = (PRODUCER / case["bundle"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == case["bundle_sha256"]
        bundle = json.loads(raw)
        pair = (bundle["program"], bundle["mode"])
        assert pair not in requests and bundle["returncode"] == 0 and bundle["failures"] == []
        requests[pair] = bundle["requested_job"]
    assert set(requests) == set(CASES)
    return requests


def binding(program="hmmstat", mode="summary"):
    # Deliberately unprobed path: syntax is not proof of installation.
    return {"program": program, "mode": mode, "software": {
        "executable": "/explicitly-supplied/unprobed/" + program,
        "sha256": "a" * 64, "engine_version": "3.4"}}


def contracts(rows):
    return native_hmmer_preparation_tool_contracts(rows, resource_kind="local", resource_id="local274")


def information(rows):
    return native_hmmer_preparation_tool_information(rows, resource_kind="local", resource_id="local274")


def test_fixed_native_tool_mode_scope_and_empty_configuration():
    assert PROGRAM_MODES == EXPECTED_MODES
    assert len(EXPECTED_MODES) == 10 and len(CASES) == 26
    assert contracts([]) == information([]) == validate_native_hmmer_preparation_bindings([]) == []
    entries = contracts([binding(*pair) for pair in CASES])
    assert len({entry["name"] for entry in entries}) == 26
    assert len({entry["description"] for entry in entries}) == 26
    assert len({entry["instructions"] for entry in entries}) == 26


@pytest.mark.parametrize("program,mode", CASES)
def test_all_native_backed_requests_have_exact_schema_and_commission_route(retained_requests, program, mode):
    request = deepcopy(retained_requests[program, mode])
    job = request["native_hmmer_preparation"]
    configured = [{key: deepcopy(job[key]) for key in ("program", "mode", "software")}]
    entry, = contracts(configured)
    shown, = information(configured)
    assert set(entry) == CONTRACT_FIELDS and set(shown) == INFORMATION_FIELDS
    assert shown == {key: entry[key] for key in INFORMATION_FIELDS}
    assert entry["name"] == "native." + program + "." + mode
    assert entry["resources"] == "local"
    assert entry["invocation_route"] == {"kind": "commission", "routes": [{
        "entry_role": "launch", "resource_id": "local274", "resource_role": "launch_local"}]}
    expected = preparation_requested_job_schema(program, mode)
    expected["properties"]["native_hmmer_preparation"]["properties"]["software"] = {"const": job["software"]}
    assert entry["input_schema"] == expected
    Draft202012Validator.check_schema(entry["input_schema"])
    Draft202012Validator(entry["input_schema"]).validate(request)
    assert validate_native_hmmer_preparation_requested_job(request) == request
    for contract in (operand_contract, output_contract):
        for roles in contract(program, mode):
            for role, formats in roles.items():
                assert role in entry["instructions"]
                assert all(fmt in entry["instructions"] for fmt in formats)
    assert "practical.job.start" in entry["instructions"]
    assert "generic local-resource task instructions" in entry["instructions"]
    assert "execution.results.collect" in entry["instructions"]
    assert "preparation_projection_catalog(program, mode)" in entry["instructions"]
    assert "native_hmmer_preparation_result_selector_v1" in entry["instructions"]
    assert job["software"]["sha256"] not in entry["instructions"]
    assert job["software"]["executable"] not in entry["instructions"]
    assert "TASK" not in entry["instructions"] and "STEERING" not in entry["instructions"]


@pytest.mark.parametrize("program,mode", CASES)
@pytest.mark.parametrize("field,value", [("executable", "/another/selected/program"), ("sha256", "0" * 64), ("engine_version", "3.3.2")])
def test_actual_bound_software_is_pinned_in_every_schema(retained_requests, program, mode, field, value):
    request = deepcopy(retained_requests[program, mode])
    job = request["native_hmmer_preparation"]
    entry, = contracts([{key: deepcopy(job[key]) for key in ("program", "mode", "software")}])
    job["software"][field] = value
    assert list(Draft202012Validator(entry["input_schema"]).iter_errors(request))


def test_constructors_perform_no_file_network_native_discovery_or_environment_io(monkeypatch, retained_requests):
    rows = [deepcopy({key: request["native_hmmer_preparation"][key]
        for key in ("program", "mode", "software")}) for request in retained_requests.values()]
    for row in rows:
        row["software"]["executable"] = "/not-discovered/" + row["program"]
    original = deepcopy(rows)

    def forbidden(*args, **kwargs):
        raise AssertionError("information construction attempted I/O or discovery")

    with monkeypatch.context() as denied:
        for target, names in (
            (builtins, ("open",)), (io, ("open",)),
            (Path, ("open", "read_bytes", "read_text", "write_bytes", "write_text", "stat", "exists", "resolve", "iterdir")),
            (os, ("open", "stat", "lstat", "scandir", "listdir", "access", "getenv", "system")),
            (subprocess, ("run", "Popen", "check_output", "check_call")),
            (shutil, ("which",)), (socket, ("socket", "create_connection")),
        ):
            for name in names:
                denied.setattr(target, name, forbidden)
        validated = validate_native_hmmer_preparation_bindings(rows)
        described = contracts(rows)
        shown = information(rows)
    assert rows == original == validated
    assert len(described) == len(shown) == 26


@pytest.mark.parametrize("value", [None, {}, "[]", 0, False, (), [None], [0], [[]], [{}]])
def test_exact_binding_array_and_row_shapes(value):
    with pytest.raises(ValueError):
        validate_native_hmmer_preparation_bindings(value)


@pytest.mark.parametrize("field,value", [
    ("program", "hmmsearch"), ("program", "unknown"), ("program", False), ("program", []),
    ("mode", "index"), ("mode", "build"), ("mode", None), ("mode", []),
    ("software", {}), ("software", None), ("software", []),
])
def test_unknown_modes_and_invalid_binding_fields(field, value):
    row = binding()
    row[field] = value
    with pytest.raises(ValueError):
        validate_native_hmmer_preparation_bindings([row])


@pytest.mark.parametrize("target,field", [("binding", "program"), ("binding", "mode"), ("binding", "software"),
    ("software", "executable"), ("software", "sha256"), ("software", "engine_version")])
def test_missing_and_extra_binding_fields_are_rejected(target, field):
    row = binding()
    selected = row if target == "binding" else row["software"]
    selected.pop(field)
    with pytest.raises(ValueError):
        contracts([row])
    row = binding()
    selected = row if target == "binding" else row["software"]
    selected["unrequested"] = True
    with pytest.raises(ValueError):
        contracts([row])


@pytest.mark.parametrize("program,mode", CASES)
def test_duplicate_program_mode_is_rejected_even_with_distinct_software(program, mode):
    first, second = binding(program, mode), binding(program, mode)
    second["software"]["sha256"] = "b" * 64
    with pytest.raises(ValueError, match="duplicate_bound_mode"):
        contracts([first, second])


@pytest.mark.parametrize("field,value", [
    ("executable", "hmmstat"), ("executable", "/bin/../bin/hmmstat"),
    ("executable", "/bin/./hmmstat"), ("executable", "/bin//hmmstat"),
    ("executable", "//bin/hmmstat"), ("executable", "/bin/hmmstat/"),
    ("executable", "/"), ("executable", "/bin\\hmmstat"), ("executable", "/bin/hmmstat\n"),
    ("executable", "/bin/hmmstat\x00"), ("executable", None), ("executable", False),
    ("sha256", "a" * 63), ("sha256", "a" * 65), ("sha256", "A" * 64),
    ("sha256", "g" * 64), ("sha256", None), ("sha256", 3),
    ("engine_version", "3.3.2"), ("engine_version", "3.4\n"), ("engine_version", None),
    ("engine_version", 3.4), ("engine_version", False),
])
def test_software_identity_has_normalized_absolute_path_digest_and_exact_version(field, value):
    row = binding()
    row["software"][field] = value
    with pytest.raises(ValueError):
        contracts([row])


@pytest.mark.parametrize("resource_kind", ["api", "hpc", "ssh", "remote", "", None, False])
@pytest.mark.parametrize("constructor", [native_hmmer_preparation_tool_contracts, native_hmmer_preparation_tool_information])
def test_unfinished_resources_fail_explicitly_without_deployment_inference(resource_kind, constructor):
    with pytest.raises(ValueError, match="native_hmmer_preparation_resource_binding_unfinished"):
        constructor([binding()], resource_kind=resource_kind, resource_id="selected-resource")


@pytest.mark.parametrize("resource_id", [None, "", False, 7, [], "local\x00", "local\n", "local\r"])
def test_resource_identity_is_explicit_text(resource_id):
    with pytest.raises(ValueError, match="resource_id_invalid"):
        native_hmmer_preparation_tool_contracts([binding()], resource_kind="local", resource_id=resource_id)


def test_input_and_return_copies_are_independent_and_preserve_selection_order():
    rows = [binding("hmmemit", "sample_profile"), binding("hmmconvert", "binary")]
    original = deepcopy(rows)
    validated = validate_native_hmmer_preparation_bindings(rows)
    entries, shown = contracts(rows), information(rows)
    assert [entry["name"] for entry in entries] == ["native.hmmemit.sample_profile", "native.hmmconvert.binary"]
    rows[0]["software"]["executable"] = "/changed/by/caller"
    assert validated == original
    assert entries[0]["input_schema"]["properties"]["native_hmmer_preparation"]["properties"]["software"]["const"] == original[0]["software"]
    validated[1]["software"]["sha256"] = "b" * 64
    entries[0]["input_schema"]["properties"]["native_hmmer_preparation"]["properties"]["software"]["const"]["sha256"] = "c" * 64
    entries[0]["input_schema"]["properties"]["native_hmmer_preparation"]["properties"]["operands"]["items"]["anyOf"][0]["properties"]["role"]["const"] = "changed"
    entries[0]["invocation_route"]["routes"][0]["resource_id"] = "changed"
    shown[0]["instructions"] = "changed"
    fresh = contracts(original)
    assert fresh[0]["input_schema"]["properties"]["native_hmmer_preparation"]["properties"]["software"]["const"] == original[0]["software"]
    assert fresh[0]["input_schema"]["properties"]["native_hmmer_preparation"]["properties"]["operands"]["items"]["anyOf"][0]["properties"]["role"]["const"] == "models"
    assert fresh[0]["invocation_route"]["routes"][0]["resource_id"] == "local274"
    assert information(original)[0]["instructions"] != "changed"
    assert entries[1] == fresh[1]


@pytest.mark.parametrize("program,mode,required", [
    ("alimask", "mask_alignment", ("--alirange", "--appendmask", "one-based inclusive", "100 ranges", "first MSA", "components.masked_fraction")),
    ("alimask", "mask_model", ("--modelrange", "including inserts", "coordinates differ")),
    ("alimask", "model_to_alignment", ("--model2ali", "stdout even when -o", "no masked_alignment")),
    ("alimask", "alignment_to_model", ("--ali2model", "requested and returned coordinates", "GSC/BLOSUM", "50,000", "does not substitute")),
    ("hmmbuild", "build_alignment", ("--fast", "--hand", "HMMER_NCPU", "Original/source and resaved", "components.input_sequence_count")),
    ("hmmbuild", "build_single_sequence_matrix", ("--singlemx", "--mxfile", "--popen", "multi-sequence", "empty", "model NAME")),
    ("hmmconvert", "ascii", ("--outfmt", "3/a through 3/f", "stdout and converted_models", "one model population")),
    ("hmmconvert", "binary", ("-b", "never be decoded or monitored as an ordinary text log", "unsupported")),
    ("hmmconvert", "legacy_hmmer2", ("-2", "quantized log-odds", "unknown")),
    ("hmmemit", "sample_core_unaligned", ("-N", "FASTA", "no native trace", "generated model data")),
    ("hmmemit", "sample_core_aligned", ("-a", "Stockholm", "RF column", "sample populations")),
    ("hmmemit", "consensus_simple", ("-c", "first maximum", "masked model state", "near-tie")),
    ("hmmemit", "consensus_thresholded", ("-C", "--minl", "--minu", "lowercase", "round")),
    ("hmmemit", "sample_profile", ("-p", "--local", "--unilocal", "--glocal", "--uniglocal", "-L", "not observed sample length")),
    ("hmmfetch", "single_key", ("positional key", "first name/accession match", "no ambient sidecar")),
    ("hmmfetch", "key_file", ("-f", "source order", "key order", "exit zero", "valid earlier model prefix")),
    ("hmmfetch", "index", ("--index", "private model copy", ".ssi", "accession-key counts")),
    ("hmmpress", "index", (".h3m", ".h3i", ".h3f", ".h3p", "private staging", "bundle_byte_sum", "internal profile validation")),
    ("hmmsim", "viterbi", ("--vit", "-a", "M+D+I", "--fast=false", "--tlinear=false", "byte order", "components.x10")),
    ("hmmsim", "msv", ("--msv", "--nu", "without claiming independent measurements")),
    ("hmmsim", "forward", ("--fwd", "--tmin/--tmax/--tpoints", "empty after exit zero", "not a measured zero")),
    ("hmmsim", "hybrid", ("--hyb", "undetermined calibration", "--fast is undefined")),
    ("hmmstat", "summary", ("background", "length_probability (p1)", "never filled automatically", "Source sequence counts are not model counts", "components.position_relative_entropy")),
    ("makehmmerdb", "build", ("2147", "--sa_freq", "format has no magic", "DNA-only", "Stored segments", "FASTA", "components.source_symbol_total")),
    ("hmmerfm-exactmatch", "locations", ("not FASTA", "254", "Current binding rejects U", "producer_contract", "source_binding", "not an extra native argument", "not reverse complement", "reverse-boundary defects")),
    ("hmmerfm-exactmatch", "count_only", ("--count_only", "empty hits file is expected", "raw FM intervals", "locations are unmeasured", "Q+R", "post-free occ/sec")),
])
def test_mode_instructions_preserve_native_meanings_and_known_limits(program, mode, required):
    text = information([binding(program, mode)])[0]["instructions"]
    for phrase in required:
        assert phrase in text


@pytest.mark.parametrize("program,mode,paths", [
    ("alimask", "mask_alignment", ("components.actual_masked_count", "components.masked_fraction")),
    ("alimask", "alignment_to_model", ("components.native_mapping_row_count",)),
    ("hmmbuild", "build_alignment", ("components.input_sequence_count", "components.resaved_column_count", "components.model_alignment_fraction")),
    ("hmmconvert", "binary", ("decoded_model_count", "compared_cell_count", "max_absolute_probability_difference")),
    ("hmmemit", "sample_core_aligned", ("captured_sample_count", "total_length", "alignment_width", "rf_match_column_count")),
    ("hmmemit", "consensus_thresholded", ("mismatch_count", "ambiguous_position_count")),
    ("hmmfetch", "key_file", ("requested_key_count", "missing_key_count", "returned_model_occurrence_count")),
    ("hmmfetch", "index", ("native_model_count", "native_primary_name_count", "native_accession_count")),
    ("hmmpress", "index", ("member_count", "bundle_byte_sum")),
    ("hmmsim", "viterbi", ("components.mean", "components.x10", "components.E10")),
    ("hmmstat", "summary", ("components.mean_match_information", "components.position_relative_entropy", "components.composition_relative_entropy")),
    ("makehmmerdb", "build", ("components.source_occurrence_count", "components.stored_segment_count", "components.actual_database_bytes")),
    ("hmmerfm-exactmatch", "locations", ("components.native_H", "components.valid_location_count", "components.invalid_location_count")),
    ("hmmerfm-exactmatch", "count_only", ("components.native_Q", "components.native_H", "components.native_R")),
])
def test_named_result_fields_exist_in_the_actual_separate_projection_catalog(program, mode, paths):
    from gene_annotation_episode.hmmer_preparation_result_views import preparation_projection_catalog
    quantities = preparation_projection_catalog(program, mode)["calculations"]["quantities"]
    text = information([binding(program, mode)])[0]["instructions"]
    for path in paths:
        assert path in quantities and path in text
        assert quantities[path]["meaning"] and quantities[path]["source"] and quantities[path]["unit"]


@pytest.mark.parametrize("fault", ["program", "mode", "unknown_field", "operand_format", "missing_output", "boolean_ordinal", "reserved_environment"])
def test_schema_rejects_malformed_or_different_selected_job(retained_requests, fault):
    request = deepcopy(retained_requests["hmmemit", "consensus_simple"])
    job = request["native_hmmer_preparation"]
    entry, = contracts([{key: deepcopy(job[key]) for key in ("program", "mode", "software")}])
    if fault == "program":
        job["program"] = "hmmstat"
    elif fault == "mode":
        job["mode"] = "sample_profile"
    elif fault == "unknown_field":
        job["extra"] = True
    elif fault == "operand_format":
        job["operands"][0]["format"] = "invented"
    elif fault == "missing_output":
        job["outputs"] = [row for row in job["outputs"] if row["role"] != "generated_sequences"]
    elif fault == "boolean_ordinal":
        job["operands"][0]["ordinal"] = False
    else:
        job["environment"]["TMPDIR"] = "/outside"
    assert list(Draft202012Validator(entry["input_schema"]).iter_errors(request))


def test_relational_request_validation_stays_with_the_existing_producer(retained_requests):
    request = deepcopy(retained_requests["hmmconvert", "binary"])
    job = request["native_hmmer_preparation"]
    entry, = contracts([{key: deepcopy(job[key]) for key in ("program", "mode", "software")}])
    outputs = {row["role"]: row for row in job["outputs"]}
    assert outputs["stdout"]["relative_path"] == outputs["converted_models"]["relative_path"]
    assert outputs["stdout"]["format"] == outputs["converted_models"]["format"] == "hmmer_binary"
    request["argv"].append("--unselected")
    Draft202012Validator(entry["input_schema"]).validate(request)
    with pytest.raises(ValueError, match="compiler_mismatch"):
        validate_native_hmmer_preparation_requested_job(request)


def test_retain_reviewable_catalogue_from_actual_selected_requests(tmp_path, retained_requests):
    rows = [{key: deepcopy(retained_requests[pair]["native_hmmer_preparation"][key])
        for key in ("program", "mode", "software")} for pair in CASES]
    described, shown = contracts(rows), information(rows)
    assert [entry["name"] for entry in described] == ["native." + program + "." + mode for program, mode in CASES]
    assert shown == [{key: entry[key] for key in ("name", "description", "resources", "instructions")} for entry in described]
    (tmp_path / "tool_contracts.json").write_text(json.dumps(described, indent=2) + "\n")
    (tmp_path / "tool_information.json").write_text(json.dumps(shown, indent=2) + "\n")
