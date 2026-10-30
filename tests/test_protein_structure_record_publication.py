"""Ordinary Store publication over actual retained 005 capture artifacts.

The tiny PDBs are synthetic native-format engineering fixtures, originally run
under packet 392's bounded job. These tests establish publication, not original
runtime authority, received-use permission, biological measurements or credit.
"""
from copy import deepcopy
from importlib import import_module
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import protein_structure_publication as publication
from gene_annotation_episode.domain import canonical as domain_canonical, identity
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_protein_structure_acquisition import (
    retained_protein_structure_file, validate_protein_structure_capture,
)
from gene_annotation_episode.protein_structure_contracts import (
    issue, validate_structure_sequence,
)
from gene_annotation_episode.protein_structure_result_worker import run_protein_structure_result_worker
from gene_annotation_episode.state import Store


REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "verification/tool_graders_protein_structure_capture_2026-10-27_392"
EXAMPLES = PACKET / "FILLED_CAPTURE_EXAMPLES_001.json"


def encoded(value):
    return canonical(value).encode("utf-8")


def forbidden(*args, **kwargs):
    pytest.fail("publication performed acquisition, reconstruction or scientific work")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def retain(store, raw, format):
    ref = store.artifact(raw)
    return {"artifact_ref": ref, "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_length": len(raw), "format": format}


def case(store, name="extraction"):
    row = next(row for row in json.loads(EXAMPLES.read_bytes()) if row["case"] == name)
    original_path = REPO / row["original_example_path"]
    raw = original_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["original_example_sha256"]
    original = json.loads(raw)
    assert all(original[key] == row[key] for key in ("target", "bundle", "capture"))
    files = [row["capture"]["bundle_file"]] + [r["observed"]
        for r in row["capture"]["files"] if r["observed"] is not None]
    for file in files:
        path = original_path.parent / "store/artifacts" / file["sha256"][:2] / file["sha256"]
        # Copy actual retained bytes only. Never serialize a replacement map.
        assert retain(store, path.read_bytes(), file["format"]) == file
    assert validate_protein_structure_capture(store, row["capture"], target=row["target"]) == row["capture"]
    return row


def file_for(row, role):
    return next(item["observed"] for item in row["capture"]["files"] if item["declared"]["role"] == role)


def extracted(store, row):
    native = json.loads(retained_protein_structure_file(store, file_for(row, "native_result")).read_bytes())
    sequence = native["sequence"]
    sequence_file = file_for(row, "sequence")
    residue_map_file = file_for(row, "residue_map")
    assert validate_structure_sequence(sequence) == sequence
    return {"sequence": sequence, "sequence_file": sequence_file, "residue_map_file": residue_map_file}


def publish_source(store, row, worker_result=None):
    return publication.publish_protein_structure_source(store, bundle=row["bundle"],
        capture=row["capture"], worker_result=worker_result)


def payload(record):
    return {key: value for key, value in record.items() if key not in {"id", "record_type", "origin"}}


def source_with(store, source_ref, **updates):
    if "auxiliary_artifact_refs" in updates:
        updates["auxiliary_artifact_refs"] = list(dict.fromkeys(updates["auxiliary_artifact_refs"]))
    return store.put("source", {**payload(store.get(source_ref)), **updates}, origin="tool")["id"]


def corrupt_record(store, ref, **updates):
    record = store.get(ref)
    record.update(updates)
    store.db.execute("UPDATE records SET data=? WHERE id=?", (domain_canonical(record), ref))


def guard_publication(monkeypatch, store):
    for module, names in (
        ("native_protein_structure_acquisition", ["capture_local_protein_structure_bundle", "_producer_file"]),
        ("native_protein_structure_local", ["prepare_local_protein_structure", "local_protein_structure_plan"]),
        ("native_protein_structure_driver", ["run_protein_structure_driver"]),
        ("native_protein_structure_worker", ["execute_protein_structure_request"]),
        ("protein_structure_result_worker", ["run_protein_structure_result_worker", "calculate_protein_structure_components"]),
        ("protein_structure_formats", ["parse_pdb_structure", "parse_mmcif_structure"]),
        ("protein_structure_sequences", ["extract_structure_sequence"]),
        ("protein_structure_calculations", ["calculate_protein_structure_components", "fit_ca_transform"]),
        ("protein_structure_sheet", ["build_protein_structure_sheet", "parse_native_protein_comparison"]),
        ("sequence_ops", ["align_pair"]),
        ("native_lifecycle", ["prepare_job", "start_prepared", "start_job", "status", "collect", "wait_job"]),
    ):
        loaded = import_module("gene_annotation_episode." + module)
        for name in names:
            monkeypatch.setattr(loaded, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(store, "artifact", forbidden)


@pytest.mark.parametrize("name", ["inspection", "extraction", "comparison", "producer_deleted_replay",
    "declared_absence", "nonzero_native_exit", "changed_native_bytes", "repeated_missing_roles"])
def test_original_source_exact_bytes_payload_identity_and_replay(tmp_path, monkeypatch, name):
    with Store(tmp_path / "store") as store:
        row = case(store, name)
        original = deepcopy(row)
        guard_publication(monkeypatch, store)
        source_ref = publish_source(store, row)
        source = store.get(source_ref)
        expected = publication.protein_structure_source_payload(
            bundle=row["bundle"], capture=row["capture"], worker_result=None)
        assert payload(source) == expected
        assert source_ref == identity("source", {"origin": "tool", "record": expected})
        assert source["origin"] == "tool"
        assert publish_source(store, row) == source_ref and store.count("source") == 1
        assert store.count("reference") == store.count("observation") == 0
        assert row == original
        if name == "changed_native_bytes":
            mismatch = next(r for r in row["capture"]["files"] if r["outcome"] == "digest_mismatch")
            assert mismatch["observed"]["artifact_ref"] in source["auxiliary_artifact_refs"]
            assert "artifact_" + mismatch["declared"]["sha256"] not in source["auxiliary_artifact_refs"]
            assert mismatch["issue"]["code"] == "input_digest_mismatch"


def test_actual_extraction_publishes_normal_reference_and_subjects(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        original = deepcopy(supplied)
        guard_publication(monkeypatch, store)
        source_ref = publish_source(store, row)
        reference_ref = publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)
        record = store.get(reference_ref)
        expected = {"reference_type": "protein", "source_ref": source_ref,
            "accession": "structure_sequence_" + digest(supplied["sequence"]),
            "label": "Structure-derived protein sequence", "sequence_ref": supplied["sequence_file"]["artifact_ref"],
            "molecule": "protein", "length": 4, "term_refs": [], "context_refs": [], "anchor": None}
        assert payload(record) == expected
        assert reference_ref == identity("reference", {"origin": "tool", "record": expected})
        assert supplied["sequence"]["alignment_sequence"] == "AGST"
        assert store.subject_length(reference_ref) == 4
        assert store.subject_molecule(reference_ref) == "protein"
        assert store.subject_unit(reference_ref) == "aa"
        assert publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied) == reference_ref
        assert store.count("source") == store.count("reference") == 1
        assert store.count("product") == store.count("observation") == 0
        assert supplied == original
        (tmp_path / "filled-publication.json").write_bytes(encoded({"source": store.get(source_ref),
            "reference": record, "sequence": supplied["sequence"]["alignment_sequence"],
            "sequence_file": supplied["sequence_file"], "residue_map_file": supplied["residue_map_file"],
            "subject_length": store.subject_length(reference_ref), "subject_molecule": store.subject_molecule(reference_ref),
            "subject_unit": store.subject_unit(reference_ref), "original_example_path": row["original_example_path"],
            "original_example_sha256": row["original_example_sha256"]}))


def test_actual_original_worker_outputs_append_in_fixed_order(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        row = case(store, "comparison")
        native_file = file_for(row, "native_result")
        result = run_protein_structure_result_worker({"version": "protein_structure_result_worker_plan_v1",
            "mode": "original_native_result", "directory": str(tmp_path / "worker"),
            "expected_request": row["bundle"]["requested_job"]["native_protein_structure"]["request"],
            "expected_software": row["bundle"]["software"],
            "native_result": {"file_identity": native_file,
                "path": str(retained_protein_structure_file(store, native_file))}})
        assert result["state"] == "complete"
        for name in ("native_result_file", "sheet_file", "components_file"):
            output = result[name]
            assert retain(store, (tmp_path / "worker" / output["relative_path"]).read_bytes(),
                output["file_identity"]["format"]) == output["file_identity"]
        guard_publication(monkeypatch, store)
        source_ref = publish_source(store, row, result)
        expected = [item["observed"]["artifact_ref"] for item in row["capture"]["files"] if item["observed"] is not None]
        expected += [result[name]["file_identity"]["artifact_ref"]
            for name in ("native_result_file", "sheet_file", "components_file")]
        assert store.get(source_ref)["auxiliary_artifact_refs"] == list(dict.fromkeys(expected))
        assert publish_source(store, row, result) == source_ref
        assert store.count("source") == 1
        (tmp_path / "filled-worker-publication.json").write_bytes(encoded({"source": store.get(source_ref), "worker_result": result}))
        # Every listed worker artifact remains required even on publication
        # replay. Losing it never invokes the worker again or repairs its bytes.
        for name in ("native_result_file", "sheet_file", "components_file"):
            file = result[name]["file_identity"]
            path = retained_protein_structure_file(store, file)
            raw = path.read_bytes()
            for fault, expected_error in (("missing", "retained_artifact_missing"), ("tampered", "input_digest_mismatch")):
                if fault == "missing":
                    path.unlink()
                else:
                    path.write_bytes(b"changed worker output")
                with pytest.raises(ValueError, match="^" + expected_error + "$"):
                    publish_source(store, row, result)
                assert store.count("source") == 1
                path.write_bytes(raw)


@pytest.mark.parametrize("field", ["bundle", "capture_input", "capture_sequence", "capture_map"])
@pytest.mark.parametrize("fault", ["missing", "tampered"])
def test_missing_or_tampered_original_source_files_are_never_rebuilt(tmp_path, monkeypatch, field, fault):
    with Store(tmp_path / "store") as store:
        row = case(store)
        selected = row["capture"]["bundle_file"] if field == "bundle" else file_for(row,
            {"capture_input": "single_structure", "capture_sequence": "sequence", "capture_map": "residue_map"}[field])
        path = retained_protein_structure_file(store, selected)
        if fault == "missing":
            path.unlink()
        else:
            path.write_bytes(b"changed original bytes")
        guard_publication(monkeypatch, store)
        with pytest.raises(ValueError, match="^" + ("retained_artifact_missing" if fault == "missing" else "input_digest_mismatch") + "$"):
            publish_source(store, row)
        assert store.count("source") == 0
        assert not path.exists() if fault == "missing" else path.read_bytes() == b"changed original bytes"


@pytest.mark.parametrize("field", ["sequence_file", "residue_map_file"])
@pytest.mark.parametrize("fault", ["missing", "tampered", "length", "digest", "format"])
def test_reference_rejects_bad_retained_identity_without_reconstruction(tmp_path, monkeypatch, field, fault):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        file = supplied[field]
        path = retained_protein_structure_file(store, file)
        expected = "input_digest_mismatch"
        if fault == "missing":
            path.unlink()
            expected = "retained_artifact_missing"
        elif fault == "tampered":
            path.write_bytes(b"changed")
        elif fault == "length":
            file["byte_length"] += 1
        elif fault == "digest":
            file["sha256"] = "0" * 64
        else:
            file["format"] = "text"
            expected = "unsupported_format"
        guard_publication(monkeypatch, store)
        with pytest.raises(ValueError, match="^" + expected + "$"):
            publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)
        assert store.count("reference") == 0


@pytest.mark.parametrize("raw", [b"AGST\n", b">header\nAGST", b"agst", b"GGST", b"AGSTX", b"AG\xc3\x9fT", b""])
def test_reference_requires_exact_ascii_sequence_bytes(tmp_path, raw):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        supplied["sequence_file"] = retain(store, raw, "ascii_protein_sequence_v1")
        # Explicitly listed malformed artifacts still cannot substitute bytes.
        source_ref = source_with(store, source_ref, auxiliary_artifact_refs=[*store.get(source_ref)["auxiliary_artifact_refs"], supplied["sequence_file"]["artifact_ref"]])
        with pytest.raises(ValueError, match="^sequence_artifact_mismatch$"):
            publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)


@pytest.mark.parametrize("fault", ["newline", "pretty", "changed_residue", "changed_selection", "empty"])
def test_reference_requires_complete_exact_original_map(tmp_path, fault):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        sequence = deepcopy(supplied["sequence"])
        raw = encoded(sequence)
        if fault == "newline":
            raw += b"\n"
        elif fault == "pretty":
            raw = json.dumps(sequence, indent=2).encode()
        elif fault == "changed_residue":
            sequence["residues"][0]["ca"]["selected_atom_row_key"] = "not-the-original-atom"
            raw = encoded(sequence)
        elif fault == "changed_selection":
            sequence["selection"]["structure_role"] = "fixed"
            assert validate_structure_sequence(sequence) == sequence
            raw = encoded(sequence)
        else:
            raw = b"{}"
        supplied["residue_map_file"] = retain(store, raw, "protein_structure_sequence_v1")
        source_ref = source_with(store, source_ref, auxiliary_artifact_refs=[*store.get(source_ref)["auxiliary_artifact_refs"], supplied["residue_map_file"]["artifact_ref"]])
        with pytest.raises(ValueError, match="^sequence_artifact_mismatch$"):
            publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)


@pytest.mark.parametrize("fault", ["selection", "length", "count_bool", "extra", "unavailable", "zero"])
def test_supplied_sequence_must_validate_and_match_its_retained_map(tmp_path, fault):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        sequence = supplied["sequence"]
        expected = "sequence_artifact_mismatch"
        if fault == "selection":
            sequence["selection"]["structure_role"] = "fixed"
            assert validate_structure_sequence(sequence) == sequence
        elif fault == "length":
            sequence["sequence_length"] += 1
            expected = "conflicting_identity"
        elif fault == "count_bool":
            sequence["sequence_length"] = True
            expected = "invalid_schema"
        elif fault == "extra":
            sequence["extra"] = None
            expected = "invalid_schema"
        elif fault == "unavailable":
            row = case(store, "declared_absence")
            native = json.loads(retained_protein_structure_file(store, file_for(row, "native_result")).read_bytes())
            supplied["sequence"] = native["sequence"]
            assert validate_structure_sequence(supplied["sequence"]) == supplied["sequence"]
        else:
            sequence.update(sequence_length=0, sequence_available=False, alignment_sequence=None,
                residues=[], native_symbols=[], state="unavailable", issues=[])
            assert validate_structure_sequence(sequence) == sequence
        with pytest.raises(ValueError, match="^" + expected + "$"):
            publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)


@pytest.mark.parametrize("field", ["sequence_file", "residue_map_file"])
def test_both_explicit_files_must_belong_to_original_source(tmp_path, field):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        source_ref = source_with(store, source_ref, auxiliary_artifact_refs=[ref for ref in
            store.get(source_ref)["auxiliary_artifact_refs"] if ref != supplied[field]["artifact_ref"]])
        with pytest.raises(ValueError, match="^original_commission_mismatch$"):
            publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)


@pytest.mark.parametrize("fault", ["provider", "version", "origin", "missing", "tampered", "malformed"])
def test_original_source_schema_family_and_identity_are_required(tmp_path, fault):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        expected = "conflicting_identity"
        if fault in ("provider", "version"):
            source_ref = source_with(store, source_ref, **{fault: "unrelated"})
            expected = "original_commission_mismatch"
        elif fault == "origin":
            source_ref = store.put("source", payload(store.get(source_ref)), origin="external")["id"]
        elif fault == "missing":
            store.db.execute("DELETE FROM records WHERE id=?", (source_ref,))
        elif fault == "tampered":
            corrupt_record(store, source_ref, retrieved_at=None)
        else:
            invalid = {**payload(store.get(source_ref)), "undeclared": None}
            source_ref = identity("source", {"origin": "tool", "record": invalid})
            record = {**invalid, "id": source_ref, "record_type": "source", "origin": "tool"}
            store.db.execute("INSERT INTO records VALUES(?,?,?,?)", (source_ref, "source", "tool", domain_canonical(record)))
            expected = "invalid_schema"
        with pytest.raises(ValueError, match="^" + expected + "$"):
            publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)


@pytest.mark.parametrize("kind", ["source", "reference"])
@pytest.mark.parametrize("fault", ["payload", "id", "kind", "origin"])
def test_changed_existing_content_addressed_record_is_never_accepted(tmp_path, kind, fault):
    with Store(tmp_path / "store") as store:
        row = case(store)
        supplied = extracted(store, row)
        source_ref = publish_source(store, row)
        reference_ref = publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)
        ref = source_ref if kind == "source" else reference_ref
        changes = {"payload": {"accession": "changed"}, "id": {"id": "source_" + "0" * 24},
            "kind": {"record_type": "term"}, "origin": {"origin": "external"}}[fault]
        corrupt_record(store, ref, **changes)
        with pytest.raises(ValueError, match="^conflicting_identity$"):
            if kind == "source":
                publish_source(store, row)
            else:
                publication.publish_structure_sequence_reference(store, source_ref=source_ref, **supplied)
        assert store.count("source") == store.count("reference") == 1
        assert all(store.get(ref)[key] == value for key, value in changes.items())


@pytest.mark.parametrize("fault", ["bundle_length", "capture_format", "manifest", "saved_worker"])
def test_source_rejects_wrong_identity_format_manifest_and_saved_worker(tmp_path, fault):
    with Store(tmp_path / "store") as store:
        row = case(store, "comparison")
        result = None
        expected = "original_commission_mismatch"
        if fault == "bundle_length":
            row["capture"]["bundle_file"]["byte_length"] += 1
            expected = "input_digest_mismatch"
        elif fault == "capture_format":
            row["capture"]["files"][0]["observed"]["format"] = "text"
            expected = "unsupported_format"
        elif fault == "manifest":
            row["capture"]["files"][0]["declared"]["role"] = "moving_structure"
        else:
            result = {"version": "protein_structure_result_worker_result_v1", "mode": "saved_sheet_recalculation",
                "operation": "compare", "native_result_file": None, "sheet_file": None, "components_file": None,
                "state": "unavailable", "issues": [issue("retained_artifact_missing", stage="input", field="file_identity")]}
        with pytest.raises(ValueError, match="^" + expected + "$"):
            publish_source(store, row, result)
        assert store.count("source") == 0
