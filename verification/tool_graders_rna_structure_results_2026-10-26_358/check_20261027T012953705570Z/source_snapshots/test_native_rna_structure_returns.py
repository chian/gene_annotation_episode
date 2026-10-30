from copy import deepcopy
import json
import pytest

from test_native_rna_structure_acquisition import F
from gene_annotation_episode.communication import plain
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES, REFERENCE_SOURCE, SAVED_SOURCE, IDENTIFIER_NAMESPACES, result_receipt_key
from gene_annotation_episode.state import Store


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
