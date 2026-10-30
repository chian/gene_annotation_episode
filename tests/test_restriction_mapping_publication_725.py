"""Custody tests. Native science is ONLY the already retained original726 job.

Mutations below are labelled engineering failures, rolled back and restored.
Original718/719 fixtures serve file-reader checks, never fake job proofs.
"""
import builtins
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import materials_packing as packing
from gene_annotation_episode.library_targets import read_ref
from gene_annotation_episode.restriction_mapping_inputs import restriction_sequence_witness
from gene_annotation_episode.restriction_mapping_contracts import restriction_digest, validate_restriction_record
from gene_annotation_episode.restriction_mapping_bound_contracts import (
    restriction_bound_schema, validate_restriction_bound_record,
    validate_restriction_alias_arguments, restriction_native_request,
)
from gene_annotation_episode.restriction_mapping_publication import (
    retain_restriction_input, read_restriction_input, publish_restriction_result,
    read_published_restriction_result,
)
from gene_annotation_episode import restriction_mapping_publication as publication
from gene_annotation_episode.restriction_mapping_jobs import RestrictionMappingJobs
from gene_annotation_episode.native_file_capture import capture_native_file, retained_native_file


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
BASE = Path(__file__).resolve().parents[1]
PACKET = "verification/tool_graders_hmmer_map_verification_2026-10-28_529"
VALIDATION_ONLY = os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION725_VALIDATION_ONLY") == "1"


def _witness(store, tools, reference):
    return restriction_sequence_witness(store, reference,
        namespace="reference" if store.get(reference)["record_type"] == "reference" else "subject",
        scope=store.validate_scope(), permitted_record_refs=[reference],
        sequence_reader=tools._sequence, check_operand=tools._check_sequence_operand)


def _retain(store, witness, *, key="engineering-selected-input"):
    return retain_restriction_input(store, operation_key=key, tool_name="find_restriction_sites",
        arguments={"mode": "native", "sequence_ref": witness["sequence_ref"], "enzyme_names": ["EcoRI"]},
        scope=witness["scope"], witness=witness)


@pytest.fixture
def supplied(tmp_path):
    if VALIDATION_ONLY:
        pytest.skip("previously verified input path; focused proof validation followup")
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="aCGTGAATTCGGATCC", molecule="dna")
        tools = ToolRegistry(store)
        selected, = store.targets()
        yield store, tools, selected, _witness(store, tools, selected["id"])


def test_input_source_is_real_immutable_noncyclic_and_detached(supplied):
    store, tools, selected, witness = supplied
    original = deepcopy(witness)
    with store.transaction():
        kept = _retain(store, witness)
    result = read_restriction_input(store, kept["input_source_ref"])
    assert result["witness"] == original
    assert result["sequence_binding"] == kept["sequence_binding"]
    assert result["sequence_binding"]["source_ref"] == result["source"]["id"]
    assert result["sequence_binding"]["origin_mapping_ref"] is None
    assert result["source"]["retrieved_at"] is None and result["source"]["origin"] == "tool"
    assert result["source"]["id"] not in canonical(result["body"])
    assert result["source"]["operand_refs"] == [selected["id"]]
    assert result["witness"]["sequence"] == original["sequence"]
    result["witness"]["records"].clear()
    assert read_restriction_input(store, kept["input_source_ref"])["witness"] == original


def test_native_retain_reuses_resolver_without_constructor_or_catalog(supplied, monkeypatch):
    store, _, _, witness = supplied
    def denied(*args, **kwargs):
        raise AssertionError("constructor/catalog/network forbidden")
    monkeypatch.setattr(ToolRegistry, "__init__", denied)
    monkeypatch.setattr(ToolRegistry, "catalog", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    assert _retain(store, witness)["input_source_ref"]


def test_feature_forged_sequence_is_rejected_by_actual_resolver(supplied):
    store, tools, selected, _ = supplied
    feature = store.put("feature", {"subject_ref": selected["id"], "kind": "CDS",
        "segments": [{"start": 2, "end": 6}, {"start": 10, "end": 14}], "strand": "-",
        "context_refs": []}, origin="tool")
    witness = _witness(store, tools, feature["id"])
    witness["sequence"] = "T" * witness["length_nt"]
    witness["content_sha256"] = hashlib.sha256(witness["sequence"].encode()).hexdigest()
    with pytest.raises(ContractError, match="restriction_witness_changed"):
        _retain(store, witness)


@pytest.mark.skipif(VALIDATION_ONLY, reason="previously verified packed input")
def test_packed_equal_bytes_different_index_fails_retention(tmp_path):
    raw = tmp_path / "reads.fastq"
    raw.write_bytes(b"@chosen\nACGTGAATTC\n+\nIIIIIIIIII\n@sibling\nTTTTCCCCAA\n+\n!!!!!!!!!!\n")
    before = packing.CHUNK_BYTES
    packing.CHUNK_BYTES = 7
    try:
        with Store(tmp_path / "store") as store:
            store.create_problem(raw, molecule="dna")
            library, = store.targets()
            member = json.loads(store.db.execute("SELECT data FROM material_members ORDER BY ordinal LIMIT 1").fetchone()[0])
            tools = ToolRegistry(store)
            witness = _witness(store, tools, read_ref(library["id"], member["id"]))
            row = witness["packed_components"][0]
            new_index = 1 + max(r[0] for r in store.db.execute("SELECT chunk_index FROM material_pack_chunks WHERE parse_key=?", (row["parse_key"],)))
            store.db.execute("INSERT INTO material_pack_chunks VALUES(?,?,?)", (row["parse_key"], new_index, row["artifact_ref"]))
            store.db.execute("UPDATE material_component_spans SET chunk_index=? WHERE member_ref=? AND component=? AND part=?",
                (new_index, member["id"], row["component"], row["part"]))
            assert tools._sequence(witness["sequence_ref"], molecule_model="dna") == witness["sequence"]
            with pytest.raises(ContractError, match="restriction_witness_changed"):
                _retain(store, witness)
    finally:
        packing.CHUNK_BYTES = before


@pytest.mark.parametrize("fault", ["wrong_scope", "wrong_selected", "extra", "bool_length", "float_length", "nonfinite"])
def test_input_rejects_wrong_arguments_scope_and_strict_values(supplied, fault):
    store, _, _, original = supplied
    witness = deepcopy(original)
    arguments = {"mode": "native", "sequence_ref": witness["sequence_ref"], "enzyme_names": ["EcoRI"]}
    scope = witness["scope"]
    if fault == "wrong_scope": scope = {"subject_refs": []}
    elif fault == "wrong_selected": arguments["sequence_ref"] = "input_other"
    elif fault == "extra": arguments["cpu"] = 1
    elif fault == "bool_length": witness["length_nt"] = True
    elif fault == "float_length": witness["length_nt"] = float(witness["length_nt"])
    else: witness["length_nt"] = float("nan")
    with pytest.raises((ContractError, ValueError), match="restriction_"):
        retain_restriction_input(store, operation_key="engineering-invalid", tool_name="find_restriction_sites",
            arguments=arguments, scope=scope, witness=witness)


def test_alias_defaults_and_empty_population_preserve_exact_raw_selection(supplied):
    store, _, _, witness = supplied
    kept = _retain(store, witness)
    raw = {"mode": "native", "sequence_ref": witness["sequence_ref"], "enzyme_names": []}
    assert validate_restriction_alias_arguments("find_restriction_sites", raw) == raw
    sites = restriction_native_request("find_restriction_sites", raw,
        sequence=witness["sequence"], sequence_binding=kept["sequence_binding"])
    enzymes_raw = {"mode": "native", "sequence_ref": witness["sequence_ref"]}
    enzymes = restriction_native_request("find_restriction_enzymes", enzymes_raw,
        sequence=witness["sequence"], sequence_binding=kept["sequence_binding"])
    assert "topology" not in raw and sites["topology"] == "circular"
    assert sites["enzyme_selection"] == {"kind": "explicit", "names": []}
    assert "topology" not in enzymes_raw and enzymes["topology"] == "linear"
    assert enzymes["enzyme_selection"] == {"kind": "commercial_native_batch", "names": None}
    with pytest.raises(ContractError):
        validate_restriction_alias_arguments("find_restriction_sites", {"mode": "saved", "result_source_ref": "source_x", "topology": "linear"})


def test_bound_schema_detachment_and_input_operation_relationship(supplied):
    store, _, _, witness = supplied
    kept = _retain(store, witness)
    value = read_restriction_input(store, kept["input_source_ref"])["body"]
    schema = restriction_bound_schema("InputBody")
    schema["additionalProperties"] = True
    assert restriction_bound_schema("InputBody")["additionalProperties"] is False
    value["operation_ref"] = "operation_wrong"
    with pytest.raises(ContractError, match="restriction_operation_conflict"):
        validate_restriction_bound_record("InputBody", value)


@pytest.mark.parametrize("name", ["nocut_snai", "duplicate_bcgi", "short_circle_bcgi", "commercial_linear_internal"])
@pytest.mark.skipif(VALIDATION_ONLY, reason="previously verified retained file readers")
def test_original_file_reader_fixtures_preserve719_arrays_without_job_claim(tmp_path, name):
    # These files are original718/719 evidence, NOT a726-owned execution proof.
    native_path = BASE / PACKET / "check182_native718/restriction-native718" / (name + ".json")
    mapping_path = BASE / PACKET / "check183b_reader719_native/retained-reader719" / (name + ".json")
    original_native = native_path.read_bytes()
    mapping = validate_restriction_record("MappingResult", json.loads(mapping_path.read_bytes()))
    with Store(tmp_path / "store") as store:
        file = capture_native_file(store, directory=str(native_path.parent), relative_path=native_path.name, format="original718_native")
        assert retained_native_file(store, file).read_bytes() == original_native
        assert mapping["native_sha256"] == restriction_digest(json.loads(original_native))
        assert mapping["native_sha256"] != file["sha256"]
    if name == "nocut_snai":
        assert mapping["enzyme_rows"][0]["native_search_positions_1based"] == [5]
        assert mapping["enzyme_rows"][0]["positions"][0]["watson_boundary_0based"] is None
    elif name == "duplicate_bcgi":
        assert mapping["enzyme_rows"][0]["native_search_positions_1based"] == [41, 75, 75, 109]
        assert mapping["enzyme_rows"][0]["recognition_match_count"] == 2
    elif name == "short_circle_bcgi":
        assert [r["watson_boundary_0based"] for r in mapping["enzyme_rows"][0]["positions"]] == [2, 12]
        assert [r["watson_canonical_boundary_0based"] for r in mapping["enzyme_rows"][0]["positions"]] == [2, 0]
    else:
        assert mapping["population"]["selected_enzyme_count"] == 623
        assert mapping["population"]["complete_empty_enzyme_count"] == 616


@pytest.fixture(scope="module")
def original_job():
    if VALIDATION_ONLY:
        pytest.skip("original Store released; no mutation or native rerun")
    selector_path = Path(os.environ["HMMER_NATIVE_ORACLE_RESTRICTION726_FIXTURE"])
    raw = selector_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "199b817ea08e2324728bf39e098db050ee9e5f30308076a28473acef48d56288"
    selector = json.loads(raw)
    store = Store(selector["store_path"])
    state = RestrictionMappingJobs(store).publication_state(selector["operation_key"])
    # A failed assertion after successful original publication reuses that exact
    # saved memo. It never deletes the genuine source or repeats the native job.
    # Preserve received selector and frozen proof before any test assertion/mutation.
    output = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-publication725"
    output.mkdir(exist_ok=False)
    (output / "original_selector.json").write_bytes(raw)
    (output / "original_job_state.json").write_text(canonical(state) + "\n")
    yield store, selector, output
    store.close()


class _RollbackEngineeringFault(Exception):
    pass


@pytest.mark.parametrize("fault", ["missing_mapping", "malformed_mapping", "symlink_mapping", "missing_native",
    "malformed_manifest", "manifest_path", "digest_conflict", "software_conflict", "catalog_conflict", "native_binding"])
def test_original_closed_job_engineering_partial_capture_is_preserved_and_rolled_back(original_job, fault, monkeypatch):
    store, selector, evidence = original_job
    directory = Path(selector["output_directory"])
    originals = {name: (directory / name).read_bytes() for name in ("native.json", "catalog.json", "mapping.json", "manifest.json")}
    role = ("native" if fault in ("missing_native", "native_binding") else "manifest" if fault in ("malformed_manifest", "manifest_path", "digest_conflict")
        else "catalog" if fault == "catalog_conflict" else "mapping")
    path = directory / (role + ".json")
    with monkeypatch.context() as patch:
        if fault == "software_conflict":
            def mismatch(*args, **kwargs): raise ContractError("restriction_software_conflict")
            patch.setattr(publication, "_software_current", mismatch)
        elif fault.startswith("missing_"):
            path.unlink()
        elif fault == "symlink_mapping":
            path.unlink();path.symlink_to(directory / "native.json")
        elif fault.startswith("malformed_"):
            path.write_bytes(b'{"truncated":')
        else:
            value = json.loads(originals[role + ".json"])
            if fault == "manifest_path": value["native_file"]["path"] = "/tmp/foreign-native.json"
            elif fault == "digest_conflict": value["mapping_file"]["sha256"] = "0" * 64
            elif fault == "native_binding": value["request"]["sequence_binding"]["source_ref"] = "source_forged"
            elif fault == "catalog_conflict": value["selection"]["names"] = []
            path.write_text(canonical(value) + "\n")
        try:
            with pytest.raises(_RollbackEngineeringFault):
                with store.transaction():
                    # Engineering capture branch only; restore original memo on
                    # rollback. The same original closed job/proof remains authority.
                    store.db.execute("UPDATE restriction_mapping_operations SET published_source_ref=NULL,published_outcome=NULL WHERE operation_key=?", (selector["operation_key"],))
                    outcome = publish_restriction_result(store, selector["operation_key"])
                    retained = read_published_restriction_result(store, outcome["result"]["source_ref"], scope=selector["reservation_arguments"]["scope"])
                    (evidence / ("engineering_" + fault + ".json")).write_text(canonical({"outcome": outcome, "body": retained["body"]}) + "\n")
                    assert outcome["status"] != "completed"
                    if fault != "missing_native":
                        assert retained["body"]["files"]["native"] is not None
                    if fault in ("missing_mapping", "malformed_manifest", "manifest_path"):
                        assert retained["native"] is not None
                    if fault in ("malformed_mapping", "symlink_mapping", "software_conflict", "native_binding"):
                        assert outcome["result"]["mapping_artifact_ref"] is None
                    if fault == "software_conflict":
                        assert retained["native"] is None and "software_conflict" in outcome["result"]["issue_codes"]
                    raise _RollbackEngineeringFault()
        finally:
            for name, raw in originals.items():
                restored = directory / name
                if restored.is_symlink(): restored.unlink()
                restored.write_bytes(raw)
    assert RestrictionMappingJobs(store).publication_state(selector["operation_key"])["execution_proof_artifact_ref"] == selector["execution_proof_artifact_ref"]


def test_original_job_publishes_complete_bytes_once_without719_or_native(original_job, monkeypatch):
    store, selector, evidence = original_job
    from gene_annotation_episode import restriction_mapping_readers as readers
    from gene_annotation_episode import native_lifecycle as lifecycle
    def denied(*args, **kwargs): raise AssertionError("no reader/native/dispatch")
    monkeypatch.setattr(readers, "read_restriction_mapping", denied)
    monkeypatch.setattr(lifecycle, "resume_start", denied)
    monkeypatch.setattr(lifecycle, "status", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    with pytest.raises(ContractError, match="restriction_publication_transaction_required"):
        publish_restriction_result(store, selector["operation_key"])
    mapping = json.loads((Path(selector["output_directory"]) / "mapping.json").read_bytes())
    with store.transaction():
        outcome = publish_restriction_result(store, selector["operation_key"])
    # Retain publication evidence BEFORE downstream assertions; never rerun native.
    (evidence / "published_outcome.json").write_text(canonical(outcome) + "\n")
    read = read_published_restriction_result(store, outcome["result"]["source_ref"], scope=selector["reservation_arguments"]["scope"])
    (evidence / "published_body.json").write_text(canonical(read["body"]) + "\n")
    assert outcome["status"] == "completed" and outcome["feedback"] is None
    assert read["mapping"] == mapping and outcome["result"]["population"] == mapping["population"]
    assert read["body"]["files"]["native"]["sha256"] != mapping["native_sha256"]
    assert mapping["enzyme_rows"][0]["native_search_positions_1based"] == [6]
    assert mapping["enzyme_rows"][0]["positions"][0]["watson_boundary_0based"] == 5
    assert mapping["enzyme_rows"][0]["positions"][0]["crick_boundary_0based"] == 9
    for pin in selector["output_pins"]:
        role = Path(pin["path"]).stem
        file = read["body"]["files"][role]
        assert (file["sha256"], file["size_bytes"]) == (pin["sha256"], pin["size_bytes"])
    with store.transaction():
        assert publish_restriction_result(store, selector["operation_key"]) == outcome


def test_saved_reads_allow_store_io_only_and_preserve_original_without_new_input(original_job, monkeypatch):
    store, selector, _ = original_job
    state = RestrictionMappingJobs(store).publication_state(selector["operation_key"])
    source_ref = state["published_source_ref"]
    from gene_annotation_episode import restriction_mapping_readers as readers
    from gene_annotation_episode import native_lifecycle as lifecycle
    imports, read_bytes = builtins.__import__, Path.read_bytes
    def denied(*args, **kwargs): raise AssertionError("native/reader/dispatch forbidden on saved read")
    def no_native(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith("restriction_mapping_native"):
            return denied()
        return imports(name, *args, **kwargs)
    def retained_only(path):
        if Path(path).is_relative_to(Path(selector["output_directory"]).parent):
            raise AssertionError("mutable original job I/O on saved read")
        return read_bytes(path)
    monkeypatch.setattr(builtins, "__import__", no_native)
    monkeypatch.setattr(Path, "read_bytes", retained_only)
    monkeypatch.setattr(ToolRegistry, "_sequence", denied)
    monkeypatch.setattr(ToolRegistry, "__init__", denied)
    monkeypatch.setattr(readers, "read_restriction_mapping", denied)
    monkeypatch.setattr(lifecycle, "status", denied)
    monkeypatch.setattr(lifecycle, "resume_start", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    before = store.db.total_changes
    retained = read_published_restriction_result(store, source_ref, scope=selector["reservation_arguments"]["scope"])
    saved = retain_restriction_input(store, operation_key="selected-saved-read", tool_name="find_restriction_sites",
        arguments={"mode": "saved", "result_source_ref": source_ref}, scope=selector["reservation_arguments"]["scope"], witness=retained["witness"])
    assert saved["input_source_ref"] == retained["input_source"]["id"]
    assert store.db.total_changes == before


def test_published_result_rejects_wrong_scope_forged_source_and_mutated_artifact(original_job):
    store, selector, _ = original_job
    state = RestrictionMappingJobs(store).publication_state(selector["operation_key"])
    scope = selector["reservation_arguments"]["scope"]
    read = read_published_restriction_result(store, state["published_source_ref"], scope=scope)
    with pytest.raises(ContractError, match="restriction_scope_conflict"):
        read_published_restriction_result(store, read["source"]["id"], scope={"subject_refs": []})
    body = deepcopy(read["body"])
    body["operation_key"] = "forged-no-authoritative-job"
    body["operation_ref"] = identity("operation", {"key": body["operation_key"], "name": body["tool_name"], "arguments": body["arguments"]})
    source = {k: v for k, v in read["source"].items() if k not in ("id", "record_type", "origin")}
    source["artifact_ref"] = store.artifact(canonical(body), "application/json")
    forged = store.put("source", source, origin="tool")
    with pytest.raises(ContractError, match="restriction_operation_missing"):
        read_published_restriction_result(store, forged["id"], scope=scope)
    file = read["body"]["files"]["mapping"]
    path = retained_native_file(store, file)
    raw = path.read_bytes()
    path.write_bytes(b" " + raw[1:])
    try:
        with pytest.raises((ContractError, ValueError)):
            read_published_restriction_result(store, read["source"]["id"], scope=scope)
    finally:
        path.write_bytes(raw)


@pytest.mark.parametrize("fault", ["bool_returncode", "float_returncode", "bool_metadata_returncode", "float_metadata_returncode",
    "bool_scratch", "float_scratch", "bool_elapsed", "float_receipt_returncode", "nonterminal", "not_quiescent", "forged_artifact_ref"])
def test_bound_original_proof_measurements_are_strict_without_native_or_store(fault):
    path = Path(os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION725_PROOF_STATE", ""))
    if not path.is_file():
        pytest.skip("focused original-proof followup only")
    value = json.loads(path.read_bytes())["execution_proof"]
    assert validate_restriction_bound_record("ExecutionProof", value) == value
    if fault == "bool_returncode": value["returncode"] = False
    elif fault == "float_returncode": value["returncode"] = 0.0
    elif fault == "bool_metadata_returncode": value["original_view"]["metadata"]["native_returncode"] = False
    elif fault == "float_metadata_returncode": value["original_view"]["metadata"]["native_returncode"] = 0.0
    elif fault == "bool_scratch": value["original_view"]["metadata"]["observed_scratch_bytes"] = True
    elif fault == "float_scratch": value["original_view"]["metadata"]["observed_scratch_bytes"] = 4096.0
    elif fault == "bool_elapsed": value["original_view"]["metadata"]["elapsed_seconds"] = False
    elif fault == "float_receipt_returncode": value["original_view"]["native_receipt"]["native_returncode"] = 0.0
    elif fault == "nonterminal": value["original_view"]["terminal"] = False
    elif fault == "not_quiescent": value["original_view"]["quiescent"] = False
    else: value["handle_artifact_ref"] = "artifact_forged"
    with pytest.raises((ValueError, ContractError), match="restriction_"):
        validate_restriction_bound_record("ExecutionProof", value)


@pytest.mark.parametrize("case", ["malformed_mapping", "software_conflict", "native_binding"])
def test_unavailable_mapping_projection_preserves_invalid_operation_and_raw_files(case, monkeypatch):
    selected_case = os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION725_UNAVAILABLE_CASE")
    if selected_case is not None and case != selected_case:
        pytest.skip("previously passed projection cases")
    directory = os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION725_UNAVAILABLE_DIRECTORY")
    if directory is None:
        pytest.skip("focused retained engineering projection followup only")
    # Original187c engineering transaction was rolled back; this retained body
    # supplies a pure projection fixture, not a claim of another completed job.
    record = json.loads((Path(directory) / ("engineering_" + case + ".json")).read_bytes())
    body = validate_restriction_bound_record("PublishedBody", record["body"])
    original_files = deepcopy(body["files"])
    selected = {key: record["outcome"]["result"][key] for key in ("sequence_ref", "namespace")}
    def denied(*args, **kwargs): raise AssertionError("pure projection must not use Store/native/719")
    from gene_annotation_episode import restriction_mapping_readers as readers
    monkeypatch.setattr(Store, "__init__", denied)
    monkeypatch.setattr(readers, "read_restriction_mapping", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    result = publication._outcome(body, record["outcome"]["result"]["source_ref"], selected, None, None)
    assert result["status"] == record["outcome"]["status"]
    assert body["failure_code"] == ("native_unavailable" if case == "native_binding" else "mapping_invalid")
    assert result["result"]["data_status"] == "unavailable"
    assert result["result"]["mapping_artifact_ref"] is None and result["result"]["population"] is None
    assert result["result"]["topology"] is None and body["files"] == original_files
    assert body["files"]["mapping"] is not None and result["result"]["issue_codes"]
