"""Real Store witness checks using labelled supplied engineering sequences.

No restriction search, native producer, provider, episode or confidence scoring
is exercised. Existing extraction is used only to construct a mapped operand.
"""
import builtins
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.library_targets import read_ref
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import materials_packing as packing
from gene_annotation_episode.restriction_mapping_inputs import (
    restriction_sequence_witness, revalidate_restriction_sequence_witness,
    validate_restriction_sequence_witness, restriction_sequence_binding,
)


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


def witness(store, tools, ref, *, namespace=None, scope=None, permitted=None):
    namespace = namespace or ("reference" if store.get(ref)["record_type"] == "reference" else "subject")
    return restriction_sequence_witness(store, ref, namespace=namespace, scope=scope,
        permitted_record_refs=[ref] if permitted is None else permitted,
        sequence_reader=tools._sequence, check_operand=tools._check_sequence_operand)


def revalidate(store, tools, original):
    return revalidate_restriction_sequence_witness(store, original, scope=original["scope"],
        permitted_record_refs=[original["sequence_ref"]], sequence_reader=tools._sequence,
        check_operand=tools._check_sequence_operand)


@pytest.fixture(scope="module")
def selected_operands():
    directory = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-witness721"
    directory.mkdir(exist_ok=False)
    store = Store(directory / "store")
    store.create_problem(raw_sequence="ACGTGAATTCGGATCC", molecule="dna")
    original, = store.targets()
    tools = ToolRegistry(store)
    feature = store.put("feature", {"subject_ref": original["id"], "kind": "CDS",
        "segments": [{"start": 2, "end": 6}, {"start": 10, "end": 14}], "strand": "-",
        "context_refs": []}, origin="tool")
    extraction = tools.execute("sequence.view", {"subject_ref": original["id"], "molecule": "dna",
        "segments": [{"start": 3, "end": 10}]})
    assert extraction["status"] == "completed", extraction
    mapped = store.get(extraction["result"]["records"][0]["product_ref"])
    unmapped = store.put("product", {"parent_refs": [original["id"]], "molecule": "dna",
        "sequence_ref": store.artifact("ACGT", "text/x-sequence"), "derivation": "correction_hypothesis",
        "context_refs": [], "footprint": store.coverage(original["id"])}, origin="tool")
    source = store.put("source", {"provider": "caller.restriction721_engineering_input", "accession": None,
        "uri": None, "artifact_ref": store.artifact("aCGTRYN", "text/x-sequence"), "text_ref": None,
        "request_ref": None, "version": "fixture-v1", "retrieved_at": None}, origin="caller")
    reference = store.put("reference", {"reference_type": "dna", "source_ref": source["id"],
        "accession": "engineering721", "label": "supplied engineering sequence",
        "sequence_ref": source["artifact_ref"], "molecule": "dna", "length": 7,
        "term_refs": [], "context_refs": []}, origin="tool")
    external = store.put("product", {"parent_refs": [reference["id"]], "molecule": "dna",
        "sequence_ref": store.artifact("CGTR", "text/x-sequence"), "derivation": "correction_hypothesis",
        "context_refs": [], "footprint": []}, origin="tool")
    operands = {"input": original, "feature_reverse_segments": feature, "mapped_product": mapped,
        "unmapped_product": unmapped, "reference_original_case": reference, "external_product": external}
    retained = {}
    for name, record in operands.items():
        retained[name] = witness(store, tools, record["id"])
        (directory / (name + ".json")).write_text(json.dumps(retained[name], sort_keys=True, allow_nan=False) + "\n")
    yield store, tools, operands, retained, directory
    store.close()


def test_actual_input_reference_and_derivative_witnesses_preserve_mapping(selected_operands):
    store, tools, operands, retained, _ = selected_operands
    assert retained["input"]["sequence"] == "ACGTGAATTCGGATCC"
    assert retained["feature_reverse_segments"]["sequence"] == "ATCCTCAC"
    assert retained["mapped_product"]["sequence"] == "TGAATTC"
    assert retained["reference_original_case"]["sequence"] == "aCGTRYN"
    assert retained["feature_reverse_segments"]["mapping"]["path"] == [
        {"subject_ref": operands["input"]["id"], "start": 10, "end": 14, "unit": "nt", "strand": "-"},
        {"subject_ref": operands["input"]["id"], "start": 2, "end": 6, "unit": "nt", "strand": "-"}]
    for name, value in retained.items():
        assert value["sequence_ref"] == operands[name]["id"]
        assert value["sequence_version"] is None
        assert value["content_sha256"] == hashlib.sha256(value["sequence"].encode()).hexdigest()
        assert value["mapping"] == (store.sequence_mapping(operands[name]["id"])
            if store.has_exact_mapping(operands[name]["id"]) else None)
        assert revalidate(store, tools, value) == value
        assert value["packed_components"] == []
    assert retained["unmapped_product"]["mapping_state"] == "unavailable"
    assert retained["unmapped_product"]["mapping_issue"] == "subregion_mapping_unavailable"
    assert store.roots(operands["external_product"]["id"]) == []
    assert retained["external_product"]["mapping"] is None


def test_witness_carries_complete_actual_sources_and_artifacts_without_writing(selected_operands):
    store, tools, operands, retained, _ = selected_operands
    before = store.db.total_changes
    for name, record in operands.items():
        value = witness(store, tools, record["id"])
        assert value == retained[name]
        for row in value["records"]:
            assert row["record"] == store.get(row["record_ref"])
        for pin in value["artifacts"]:
            data = store.get_artifact(pin["artifact_ref"])
            assert hashlib.sha256(data).hexdigest() == pin["sha256"] and len(data) == pin["size_bytes"]
    assert store.db.total_changes == before
    reference = retained["reference_original_case"]
    source = next(r["record"] for r in reference["records"] if r["record_type"] == "source")
    assert source["version"] == "fixture-v1"


def test_narrow_binding_uses_retained_witness_source_without_fabricating_mapping(selected_operands):
    store, _, _, retained, _ = selected_operands
    value = retained["mapped_product"]
    body = store.artifact(canonical(value), "application/json")
    source = store.put("source", {"provider": "episode.restriction_input", "accession": None,
        "uri": None, "artifact_ref": body, "text_ref": None, "request_ref": None,
        "version": "restriction_sequence_witness_v1", "retrieved_at": None}, origin="tool")
    binding = restriction_sequence_binding(value, source_ref=source["id"])
    assert binding["source_ref"] == source["id"] and binding["sequence_ref"] == value["sequence_ref"]
    assert binding["origin_mapping_ref"] is None and binding["sequence_version"] is None
    assert json.loads(store.get_artifact(source["artifact_ref"])) == value


@pytest.mark.parametrize("failure", ["unreceived", "no_permission_list", "wrong_namespace", "outside_segment"])
def test_wrong_authority_or_scope_never_resolves_sequence(selected_operands, failure):
    store, tools, operands, _, _ = selected_operands
    ref = operands["input"]["id"]
    options = {"namespace": "subject", "scope": None, "permitted_record_refs": [ref]}
    if failure == "unreceived": options["permitted_record_refs"] = []
    elif failure == "no_permission_list": options["permitted_record_refs"] = None
    elif failure == "wrong_namespace": options["namespace"] = "reference"
    else: options["scope"] = {"subject_refs": [ref], "segments": [{"target_ref": ref, "start": 0, "end": 2, "unit": "nt"}]}
    def denied(*args, **kwargs): raise AssertionError("unauthorized sequence resolved")
    with pytest.raises(ContractError, match="restriction_"):
        restriction_sequence_witness(store, ref, **options, sequence_reader=denied, check_operand=tools._check_sequence_operand)


@pytest.mark.parametrize("molecule,sequence", [("protein", "MKWV"), ("rna", "ACGU"),
    ("dna", "ACGTZ"), ("dna", "ACG T"), ("dna", "")])
def test_explicit_non_dna_or_invalid_symbols_are_rejected(tmp_path, molecule, sequence):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="ACGT", molecule="dna")
        source = store.get(store.targets()[0]["source_ref"])
        reference = store.put("reference", {"reference_type": "sequence", "source_ref": source["id"],
            "accession": "engineering_invalid", "label": "supplied invalid engineering input",
            "sequence_ref": store.artifact(sequence, "text/x-sequence"), "molecule": molecule,
            "length": len(sequence), "term_refs": [], "context_refs": []}, origin="tool")
        with pytest.raises(ContractError, match="restriction_(dna_processing_model_required|dna_sequence_invalid)"):
            witness(store, ToolRegistry(store), reference["id"])


@pytest.fixture(scope="module")
def packed_read():
    directory = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-witness721" / "packed"
    directory.mkdir(exist_ok=False)
    path = directory / "reads.fastq"
    path.write_bytes(b"@chosen exact header\nACGTGAATTC\n+\nIIIIIIIIII\n@sibling\nTTTTCCCCAA\n+\n!!!!!!!!!!\n")
    old = packing.CHUNK_BYTES
    packing.CHUNK_BYTES = 7
    store = Store(directory / "store")
    try:
        store.create_problem(path, molecule="dna")
        library, = store.targets()
        member = json.loads(store.db.execute("SELECT data FROM material_members ORDER BY ordinal LIMIT 1").fetchone()[0])
        ref = read_ref(library["id"], member["id"])
        tools = ToolRegistry(store)
        value = witness(store, tools, ref)
        (directory / "selected_read.json").write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        yield store, tools, library, member, ref, value
    finally:
        packing.CHUNK_BYTES = old
        store.close()


def test_selected_packed_read_freezes_exact_index_not_sibling_members(packed_read):
    store, tools, library, member, ref, value = packed_read
    assert value["sequence"] == "ACGTGAATTC" and value["sequence_ref"] == ref
    assert value["mapping"]["path"] == [{"subject_ref": ref, "start": 0, "end": 10, "unit": "nt", "strand": "+"}]
    members = [r for r in value["records"] if r["record_type"] == "collection_member"]
    assert len(members) == 1 and members[0]["record_ref"] == member["id"]
    assert len(value["packed_components"]) > 3
    assert {r["member_ref"] for r in value["packed_components"]} == {member["id"]}
    assert revalidate(store, tools, value) == value
    with pytest.raises(ContractError, match="restriction_sequence_operand_required"):
        witness(store, tools, library["id"])


def test_unspecified_molecule_keeps_original_symbol_units_and_selected_dna_model(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="ACGTRYN", molecule="unspecified")
        selected, = store.targets()
        value = witness(store, ToolRegistry(store), selected["id"])
        assert value["molecule"] == "unspecified"
        assert value["mapping"]["units_per_symbol"] == 1
        assert value["mapping"]["path"][0]["unit"] == "symbol"


def test_changed_packed_chunk_ownership_with_equal_bytes_is_detected(packed_read):
    store, tools, _, member, _, original = packed_read
    chosen = original["packed_components"][0]
    key, chunk = chosen["parse_key"], chosen["chunk_index"]
    # A new SQL chunk index points to identical bytes: scientific sequence stays
    # equal, while the immutable physical index witness must change.
    replacement = max(r[0] for r in store.db.execute("SELECT chunk_index FROM material_pack_chunks WHERE parse_key=?", (key,))) + 1
    store.db.execute("INSERT INTO material_pack_chunks VALUES(?,?,?)", (key, replacement, chosen["artifact_ref"]))
    store.db.execute("UPDATE material_component_spans SET chunk_index=? WHERE member_ref=? AND component=? AND part=?",
        (replacement, member["id"], chosen["component"], chosen["part"]))
    try:
        assert tools._sequence(original["sequence_ref"], molecule_model="dna") == original["sequence"]
        with pytest.raises(ContractError, match="restriction_witness_changed"):
            revalidate(store, tools, original)
    finally:
        store.db.execute("UPDATE material_component_spans SET chunk_index=? WHERE member_ref=? AND component=? AND part=?",
            (chunk, member["id"], chosen["component"], chosen["part"]))
        store.db.execute("DELETE FROM material_pack_chunks WHERE parse_key=? AND chunk_index=?", (key, replacement))


@pytest.mark.parametrize("fault", ["extra", "bool_length", "float_revision", "duplicate_record", "duplicate_artifact", "mapping", "hash", "source_record"])
def test_pure_validation_rejects_malformed_or_conflicting_witnesses(selected_operands, fault):
    value = deepcopy(selected_operands[3]["input"])
    if fault == "extra": value["confidence"] = 1
    elif fault == "bool_length": value["length_nt"] = True
    elif fault == "float_revision": value["sequence_version"] = 0.0
    elif fault == "duplicate_record": value["records"].append(deepcopy(value["records"][0]))
    elif fault == "duplicate_artifact": value["artifacts"].append(deepcopy(value["artifacts"][0]))
    elif fault == "mapping": value["mapping"]["units_per_symbol"] = 3
    elif fault == "hash": value["content_sha256"] = "0" * 64
    else: next(r["record"] for r in value["records"] if r["record_type"] == "source")["version"] = "forged"
    with pytest.raises(ContractError, match="restriction_"):
        validate_restriction_sequence_witness(value)


@pytest.mark.parametrize("fault", ["source_version", "selected_revision", "artifact_bytes", "saved_mapping"])
def test_store_changes_and_forged_saved_mapping_fail_revalidation(selected_operands, fault):
    store, tools, operands, retained, _ = selected_operands
    original = retained["mapped_product"] if fault == "saved_mapping" else retained["input"]
    if fault == "saved_mapping":
        changed = deepcopy(original);changed["mapping"]["path"][0]["strand"] = "-"
        with pytest.raises(ContractError, match="restriction_witness_changed"):
            revalidate(store, tools, changed)
        return
    if fault == "artifact_bytes":
        artifact = store.get(operands["input"]["sequence_ref"])
        path = store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
        raw = path.read_bytes();path.write_bytes(b"T" + raw[1:])
        try:
            with pytest.raises(ContractError, match="restriction_"):revalidate(store, tools, original)
        finally:path.write_bytes(raw)
        return
    row = (next(r["record"] for r in original["records"] if r["record_type"] == "source")
        if fault == "source_version" else operands["input"])
    table = "records" if fault == "source_version" else "inputs"
    changed = {**row, "version": "changed"} if fault == "source_version" else {**row, "revision": 1}
    store.db.execute(f"UPDATE {table} SET data=? WHERE id=?", (canonical(changed), row["id"]))
    try:
        with pytest.raises(ContractError, match="restriction_"):revalidate(store, tools, original)
    finally:store.db.execute(f"UPDATE {table} SET data=? WHERE id=?", (canonical(row), row["id"]))


def test_pure_validation_and_binding_do_not_read_store_files_or_native_modules(selected_operands, monkeypatch):
    original = selected_operands[3]["input"]
    imports = builtins.__import__
    def no_native(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith("restriction_mapping_native"):
            raise AssertionError("native import")
        return imports(name, *args, **kwargs)
    def denied(*args, **kwargs):raise AssertionError("unexpected I/O or dispatch")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", no_native)
        patch.setattr(builtins, "open", denied);patch.setattr(io, "open", denied);patch.setattr(Path, "open", denied)
        patch.setattr(socket.socket, "connect", denied);patch.setattr(subprocess, "run", denied);patch.setattr(subprocess, "Popen", denied)
        checked = validate_restriction_sequence_witness(original)
        bound = restriction_sequence_binding(original, source_ref="source_" + "a" * 24)
    checked["records"].clear()
    assert original["records"] and bound["length_nt"] == 16
