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
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
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
NATIVE_DIR = BASE / "gene_annotation_episode/episodic_workflow/root/tests/fixtures/restriction_mapping/native718"
MAPPING_DIR = BASE / "gene_annotation_episode/episodic_workflow/root/tests/fixtures/restriction_mapping/retained_reader719"
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
    native_path = NATIVE_DIR / (name + ".json")
    mapping_path = MAPPING_DIR / (name + ".json")
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












