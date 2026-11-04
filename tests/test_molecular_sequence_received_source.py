"""Real Store/receipt metadata reads under explicitly engineered commissions.

No Workflow, scientific producer or native publication is exercised. Source
admission is not File access or producer proof; ordinary source ownership must
authenticate its retained publication before reading associated private bytes.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode import molecular_sequence_input_bindings as bindings
from gene_annotation_episode import molecular_sequence_input_contracts as contracts

from test_molecular_sequence_input_bindings import actual_received_input_owner


COMMON = {"receiver", "scope", "inheritance_manifest", "witness"}


def read_source(value, *, context=None, reference=None):
    return value.binding.read_received_source(context or value.context,
        value.source_ref if reference is None else reference)


def assert_denied(result, code):
    assert result["input"] is None
    assert result["failure"] == {"stage": "authority", "code": code}
    assert set(result) == {"version", "selection", "input", "failure"}
    assert result["selection"]["namespace"] == "source"
    assert result == contracts.validate_molecular_sequence_received_source(result)
    validate_schema(result, contracts.molecular_sequence_received_source_schema())


def forbid_associated_file_ports(monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("Source-only metadata must not inspect associated File metadata, representations or bytes")
    for name in ("_metadata", "retained_native_file", "read_bytes",
            "decode_molecular_sequence_input", "source_window_selection"):
        monkeypatch.setattr(bindings, name, forbidden)
    monkeypatch.setattr(value.store, "get_artifact", forbidden)
    monkeypatch.setattr(value.store, "artifact", forbidden)


def test_inherited_protected_source_is_admitted_without_any_file_receipt_or_file_port(tmp_path, monkeypatch):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True) as value:
        source = value.store.get(value.source_ref)
        known = set(value.receipts.known(value.context.episode_id, baseline=True))
        assert value.source_ref in known and value.artifact_ref not in known and value.text_ref not in known
        forbid_associated_file_ports(monkeypatch, value)
        result = read_source(value)
        assert result["version"] == contracts.RECEIVED_SOURCE_VERSION and result["failure"] is None
        item = result["input"]
        assert set(item) == COMMON
        assert item["witness"]["record"] == source
        assert item["witness"]["record_sha256"] == contracts.input_record_digest(source)
        assert item["witness"]["source_version"] == source["version"]
        assert item["receiver"]["episode_id"] == value.context.episode_id
        assert item["inheritance_manifest"] == value.receipts.manifest(value.context.episode_id)
        assert item["witness"]["record"]["artifact_ref"] == value.artifact_ref
        assert value.verdicts == [(value.source_ref, "source")]
        assert known == set(value.receipts.known(value.context.episode_id, baseline=True))
        assert result == contracts.validate_molecular_sequence_received_source(result)
        validate_schema(result, contracts.molecular_sequence_received_source_schema())


def test_source_metadata_survives_withdrawn_native_bytes_without_implying_availability(tmp_path, monkeypatch):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True) as value:
        before = read_source(value)
        artifact = value.store.get(value.artifact_ref)
        path = value.store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
        path.unlink()
        forbid_associated_file_ports(monkeypatch, value)
        after = read_source(value)
        assert canonical(after) == canonical(before)
        assert set(after["input"]) == COMMON
        assert "byte_verification" not in after["input"] and "file" not in after["input"]
        assert value.artifact_ref not in set(value.receipts.known(value.context.episode_id, baseline=True))


def test_source_receipt_inheritance_remains_the_original_frozen_prefix(tmp_path, monkeypatch):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True, deliver=False) as value:
        value.receipts.receive(value.parent.episode_id, [value.source_ref], kind="initial")
        forbid_associated_file_ports(monkeypatch, value)
        assert_denied(read_source(value), "reference_not_received")
        later = value.child(1)
        result = read_source(value, context=later)
        assert result["failure"] is None and result["input"]["receiver"]["episode_id"] == later.episode_id
        assert result["input"]["inheritance_manifest"] == value.receipts.manifest(later.episode_id)
        assert value.artifact_ref not in set(value.receipts.known(later.episode_id, baseline=True))


@pytest.mark.parametrize("change,code", [
    ("unreceived", "reference_not_received"), ("owner_denied", "reference_denied"),
    ("forged_source", "source_identity_conflict"), ("missing_source", "reference_unavailable")])
def test_source_authority_failures_do_not_return_metadata_or_follow_artifacts(tmp_path, monkeypatch, change, code):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True,
            deliver=change != "unreceived") as value:
        if change == "owner_denied":
            value.denied.add((value.source_ref, "source"))
        elif change == "forged_source":
            record = value.store.get(value.source_ref)
            record["version"] = "forged_saved_version"
            value.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(record), value.source_ref))
        elif change == "missing_source":
            value.store.db.execute("DELETE FROM records WHERE id=?", (value.source_ref,))
        if change in {"unreceived", "owner_denied"}:
            original_get = value.store.get
            def no_denied_record(reference):
                assert reference != value.source_ref, "unreceived or denied Source metadata was read"
                return original_get(reference)
            monkeypatch.setattr(value.store, "get", no_denied_record)
        forbid_associated_file_ports(monkeypatch, value)
        assert_denied(read_source(value), code)


@pytest.mark.parametrize("change,code", [
    ("context", "invalid_context"), ("foreign_run", "invalid_context"),
    ("commission", "invalid_commission"), ("inheritance", "invalid_inheritance"),
    ("scope", "scope_denied")])
def test_source_port_uses_actual_context_commission_inheritance_and_parent_scope(tmp_path, monkeypatch, change, code):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True) as value:
        context = value.context
        if change == "context":
            request = plain(context.request)
            request["message"]["episode_assignment"]["foreign"] = True
            context = BindingContext(context.run_id, context.episode_id, context.role, context.path,
                context.scope, request["message"]["episode_assignment"], request)
        elif change == "foreign_run":
            context = BindingContext("different-run", context.episode_id, context.role, context.path,
                context.scope, context.assignment, context.request)
        elif change == "commission":
            selected = json.loads(value.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=?",
                (value.parent.episode_id,)).fetchone()[0])
            selected["assignment"] = {"foreign": "selection"}
            value.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=?",
                (canonical(selected), value.parent.episode_id))
        elif change == "inheritance":
            request = plain(context.request)
            request["message"]["knowledge_inheritance"]["through_receipt_index"] += 1
            value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                (canonical(request), context.episode_id))
            context = BindingContext(context.run_id, context.episode_id, context.role, context.path,
                context.scope, context.assignment, request)
        else:
            request = plain(value.parent.request)
            request["message"]["scope"]["segments"] = [dict(target_ref=value.scope["subject_refs"][0],
                start=0, end=4, unit="nt")]
            value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                (canonical(request), value.parent.episode_id))
        forbid_associated_file_ports(monkeypatch, value)
        assert_denied(read_source(value, context=context), code)


def test_received_artifact_cannot_be_relabelled_as_source_metadata(tmp_path, monkeypatch):
    with actual_received_input_owner(tmp_path, namespace="artifact") as value:
        forbid_associated_file_ports(monkeypatch, value)
        assert_denied(read_source(value, reference=value.artifact_ref), "reference_type_conflict")


@pytest.mark.parametrize("file_state", ["unreceived", "owner_denied", "admitted"])
def test_source_metadata_does_not_bypass_or_change_json_and_raw_file_admission(tmp_path, file_state):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True,
            grant_artifact=file_state != "unreceived") as value:
        if file_state == "owner_denied":
            value.denied.add((value.artifact_ref, "artifact"))
        source = read_source(value)
        assert source["failure"] is None and set(source["input"]) == COMMON
        json_result = value.binding.read_received(value.context, value.source_ref, "source", tag_key="version")
        raw_result, path = value.binding.read_received_file(value.context, value.source_ref, "source", file_format="json")
        if file_state == "admitted":
            assert json_result["failure"] is None and raw_result["failure"] is None and path is not None
            assert canonical(source["input"]) == canonical({key: json_result["input"][key] for key in COMMON})
            assert canonical(source["input"]) == canonical({key: raw_result["input"][key] for key in COMMON})
        else:
            code = "artifact_not_received" if file_state == "unreceived" else "artifact_denied"
            assert json_result["input"] is raw_result["input"] is path is None
            assert json_result["failure"] == raw_result["failure"] == {"stage": "authority", "code": code}


@pytest.mark.parametrize("change", ["extra", "version", "namespace", "file", "artifact_record", "content", "path",
    "byte_verification", "source_version", "record_digest", "receiver_digest", "artifact_failure", "missing_failure"])
def test_source_metadata_contract_is_closed_and_preserves_original_record_relationships(tmp_path, change):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True) as value:
        result = deepcopy(read_source(value))
        if change == "extra": result["attempt_ref"] = "invented"
        elif change == "version": result["version"] = contracts.RECEIVED_FILE_VERSION
        elif change == "namespace": result["selection"]["namespace"] = "artifact"
        elif change in {"file", "artifact_record", "content", "path", "byte_verification"}:
            result["input"][change] = "not-source-metadata"
        elif change == "source_version": result["input"]["witness"]["source_version"] = "invented"
        elif change == "record_digest": result["input"]["witness"]["record_sha256"] = "0" * 64
        elif change == "receiver_digest": result["input"]["receiver"]["request_sha256"] = True
        elif change == "artifact_failure":
            result.update(input=None, failure={"stage": "artifact", "code": "artifact_bytes_unavailable"})
        else:
            result.update(input=None, failure=None)
        with pytest.raises(ValueError):
            contracts.validate_molecular_sequence_received_source(result)


@pytest.mark.parametrize("kind", ["json", "raw"])
def test_source_only_shape_is_not_an_alternative_file_validation_branch(tmp_path, kind):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True, grant_artifact=True) as value:
        source = read_source(value)
        if kind == "json":
            file = value.binding.read_received(value.context, value.source_ref, "source", tag_key="version")
            validator = contracts.validate_molecular_sequence_received_input
            source["version"] = contracts.RECEIVED_INPUT_VERSION
        else:
            file, path = value.binding.read_received_file(value.context, value.source_ref, "source", file_format="json")
            assert path is not None
            validator = contracts.validate_molecular_sequence_received_file
            source["version"] = contracts.RECEIVED_FILE_VERSION
        assert validator(file) == file
        with pytest.raises(ValueError):
            validator(source)
        file["version"] = contracts.RECEIVED_SOURCE_VERSION
        with pytest.raises(ValueError):
            contracts.validate_molecular_sequence_received_source(file)


def test_source_metadata_reads_change_no_records_actions_artifacts_receipts_or_grants(tmp_path, monkeypatch):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True) as value:
        tables = ("records", "artifacts", "runtime_actions", "runtime_episodes",
            "runtime_record_receipts", "runtime_receipt_inheritance")
        def rows():
            return {name: [tuple(row) for row in value.store.db.execute("SELECT * FROM " + name + " ORDER BY rowid")]
                for name in tables}
        before, changes = rows(), value.store.db.total_changes
        known = set(value.receipts.known(value.context.episode_id))
        forbid_associated_file_ports(monkeypatch, value)
        first, second = read_source(value), read_source(value)
        assert canonical(first) == canonical(second)
        assert rows() == before and value.store.db.total_changes == changes
        assert set(value.receipts.known(value.context.episode_id)) == known


@pytest.mark.parametrize("reference", [None, "", "source\ninvalid"])
def test_invalid_source_selection_fails_before_authority(tmp_path, monkeypatch, reference):
    with actual_received_input_owner(tmp_path) as value:
        def forbidden(*args, **kwargs):
            pytest.fail("invalid Source selection must precede authority access")
        monkeypatch.setattr(value.binding, "_authority", forbidden)
        with pytest.raises(ValueError, match="^molecular_sequence_input_invalid_selection$"):
            value.binding.read_received_source(value.context, reference)
