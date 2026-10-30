from copy import deepcopy
import asyncio
import json
import pytest

from test_native_rna_structure_acquisition import F
from gene_annotation_episode.communication import plain
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES, REFERENCE_SOURCE, SAVED_SOURCE, IDENTIFIER_NAMESPACES, result_receipt_key
from gene_annotation_episode.state import Store
from gene_annotation_episode.runtime import TypedReportContract


def test_null_source_failure_crosses_real_results_and_scientific_forms(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        scientific = f.child(role="scientific_process", sources=[FAMILY_SOURCES["failure"]])
        child = f.child(parent=scientific, selection=F.selector("failure", [], {"record_keys": ["synthetic-rna:failure:0", "missing"]}))
        (f.attempt / "bundle.json").unlink()
        body = f.execute(child)
        assert body["source_ref"] is None and body["record_refs"] == [] and not body["delivery_complete"]
        form = f.returned(scientific, child)
        assert [row["issue"]["code"] for row in form["value_0"]] == ["rna_capture_unavailable", "rna_requested_row_missing"]
        assert all(row["source_ref"] is None for row in form["value_0"])
        forwarded = f.returned(f.root, scientific)
        assert forwarded == form and f.returns.received_facts(f.root, F.schema_for(FAMILY_SOURCES["failure"]))[FAMILY_SOURCES["failure"]] == form["value_0"]
        assert f.returns.resolve_received(f.root, result_receipt_key(body), IDENTIFIER_NAMESPACES[2]) is True
        F.retain("null_source_failure_forwarding", original_receipt=body, child_form=form, parent_form=forwarded)


@pytest.mark.parametrize("field", ["action", "form", "facts", "receipt", "target", "context"])
def test_original_commission_receipt_frozen_form_and_context_tampering_rejected(tmp_path, field):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        f.returned(f.root, child)
        if field == "action":
            row = f.journal.row("runtime_actions", f.root.episode_id, 0)
            value = json.loads(row["action"])
            value["purpose"] = "changed"
            store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=?", (F.canonical(value), f.run_id, f.root.episode_id))
        elif field in {"form", "facts"}:
            row = store.db.execute("SELECT * FROM runtime_forms WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id)).fetchone()
            value = json.loads(row[field])
            rows = value["value_0"] if field == "form" else value[FAMILY_SOURCES["summary"]]
            rows[0]["measurements"][0]["value"] = 999
            store.db.execute(f"UPDATE runtime_forms SET {field}=? WHERE run_id=? AND episode_id=?", (F.canonical(value), f.run_id, child.episode_id))
        elif field == "receipt":
            path = f.results._saved_directory(child.episode_id, body["operation_key"]) / "receipt.json"
            body["native_success"] = False
            path.write_bytes(F.encoded(body))
        elif field == "target":
            f.target["request_sha256"] = "1" * 64
        else:
            request = plain(child.request)
            request["message"]["episode_assignment"]["selector"]["projection"]["metrics"] = ["pair_count"]
            store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?", (F.canonical(request), f.run_id, child.episode_id))
        with pytest.raises((ValueError, KeyError)):
            f.returns.received_context(f.root)


def test_source_only_old_expansion_does_not_grant_artifacts_or_numeric_sibling_rows(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child(sources=[REFERENCE_SOURCE])
        body = f.execute(child)
        f.returned(f.root, child)
        sheet = body["prepared"]["sheet_artifact_ref"]
        # Deliberately simulate historical recursive receipt expansion.
        f.receipts.receive(f.root.episode_id, [sheet], kind="child_form", source_index=0)
        assert f.results.retained_reference_access(f.root, sheet, "artifact") is False
        assert f.results.retained_reference_access(f.root, body["source_ref"], "source") is True
        assert f.returns.received_facts(f.root, F.schema_for(FAMILY_SOURCES["summary"])) == {FAMILY_SOURCES["summary"]: []}
        sibling = f.child(parent=f.root, index=1, role="scientific_process", sources=[FAMILY_SOURCES["summary"]])
        assert f.returns.resolve_received(sibling, body["rows"][0]["row_key"], IDENTIFIER_NAMESPACES[0]) is False
        assert f.results.retained_reference_access(sibling, sheet, "artifact") is False


def test_explicit_completed_action_artifact_and_actual_scope_operand_keep_access(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child(sources=[REFERENCE_SOURCE])
        body = f.execute(child)
        f.returned(f.root, child)
        artifact = body["capture"]["artifacts"][0]["artifact_ref"]
        f.journal.save("runtime_actions", {"episode_id": f.root.episode_id, "decision_index": 3,
            "action": F.canonical({"kind": "tool", "tool": "explicit.supplied.fixture", "arguments": {}}),
            "result": F.canonical({"status": "partial", "record_refs": [artifact]}), "credit": 0})
        assert f.results.retained_reference_access(f.root, artifact, "artifact") is True
        sequence = store.get(f.scope["subject_refs"][0])["sequence_ref"]
        assert f.results.retained_reference_access(f.root, sequence, "artifact") is None


def test_closed_history_exact_numbers_remain_readable_without_live_state(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        form = f.returned(f.root, child)
        store.db.execute("UPDATE runtime_episodes SET state='completed', archive=? WHERE run_id=? AND episode_id=?",
            (F.canonical({"fixture": "closed-history"}), f.run_id, child.episode_id))
        before = list(store.db.iterdump())
        assert f.returns.received_context(f.root)[0]["facts"] == form["value_0"]
        assert f.results.read_receipt_key(result_receipt_key(body), f.scope) == body
        assert list(store.db.iterdump()) == before


def test_own_requested_saved_descriptor_grants_only_its_explicit_artifact_operands(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child(sources=[SAVED_SOURCE])
        body = f.execute(child)
        descriptor = f.results.saved_descriptor(body)
        for key in ("sheet_artifact_ref", "bundle_artifact_ref"):
            assert f.results.retained_reference_access(child, descriptor[key], "artifact") is True
        assert f.results.retained_reference_access(child, body["prepared"]["components_artifact_ref"], "artifact") is False
        assert f.results.retained_reference_access(child, body["capture"]["artifacts"][-1]["artifact_ref"], "artifact") is False


def test_explicit_artifact_return_from_other_child_preserves_shared_bytes_access(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        first = f.child(sources=[REFERENCE_SOURCE])
        body = f.execute(first)
        f.returned(f.root, first)
        artifact = body["prepared"]["sheet_artifact_ref"]
        assert f.results.retained_reference_access(f.root, artifact, "artifact") is False
        schema = {"type": "object", "additionalProperties": False, "required": ["artifacts"], "properties": {
            "artifacts": {"type": "array", "x-source": "independent_artifact_refs", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "artifact"}}}}
        contract = TypedReportContract("Return the independent explicitly supplied artifact", schema, lambda *_: True)
        child = f.context((*f.root.path, ("scientific_process", "child_1")), {}, contract, f.root)
        f.journal.save("runtime_actions", {"episode_id": f.root.episode_id, "decision_index": 1,
            "action": F.canonical({"kind": "episode_child", "role": "scientific_process", "assignment": {},
                "scope": f.scope, "purpose": contract.decision, "schema_json": F.canonical(schema)}), "result": None, "credit": None})
        f.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
            "action": F.canonical({"kind": "tool", "tool": "synthetic.independent_artifact", "arguments": {}}),
            "result": F.canonical({"status": "completed", "record_refs": [artifact]}), "credit": 0})
        form = {"artifacts": [artifact]}
        f.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": F.canonical({"independent_artifact_refs": [artifact]}), "form": F.canonical(form)})
        f.journal.save("runtime_report_attempts", {"parent_episode_id": f.root.episode_id, "decision_index": 1,
            "delivery_ref": "independent-delivery", "child_episode_id": child.episode_id,
            "contract": F.canonical(plain(child.request)["report_contract"]), "form": F.canonical(form), "failure": None})
        f.receipts.receive(f.root.episode_id, [artifact], kind="child_form", source_index=1)
        assert f.results.retained_reference_access(f.root, artifact, "artifact") is True
        form["artifacts"] = []
        store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
            (F.canonical(form), f.run_id, f.root.episode_id))
        with pytest.raises(ValueError):
            f.results.retained_reference_access(f.root, artifact, "artifact")


def test_replay_keeps_one_original_identity_and_no_extra_observation_or_credit(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        before = list(store.db.iterdump())
        replay = asyncio.run(f.results.execute(child, f.target, body["tool_name"], {}, body["operation_key"]))
        assert replay["result"] == body and len(f.targets.observations) == 1
        assert list(store.db.iterdump()) == before
        assert f.results.credit_view(child, {"known_record_refs": [body["source_ref"]], "initial_known_record_refs": []})["new_acquired_record_count"] == 1
        assert f.results.credit_view(child, {"known_record_refs": [body["source_ref"]], "initial_known_record_refs": [body["source_ref"]]})["new_acquired_record_count"] == 0


def test_runtime_pending_envelope_is_validated_without_changing_adapter_receipt(tmp_path):
    with Store(tmp_path / "store") as store:
        f = F.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        row = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
            (f.run_id, child.episode_id)).fetchone()
        outcome = json.loads(row["result"])
        outcome["pending_work_after_action"]["items"] = "not a pending work list"
        store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (F.canonical(outcome), f.run_id, child.episode_id))
        with pytest.raises(ValueError):
            f.results.read_receipt_key(result_receipt_key(body), f.scope)
