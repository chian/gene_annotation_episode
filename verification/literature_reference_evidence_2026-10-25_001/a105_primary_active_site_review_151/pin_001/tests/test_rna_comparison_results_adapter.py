from copy import deepcopy
import asyncio
import json
import shutil

import pytest

from test_rna_comparison_operand_authority import E
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_records import validate_completion_proof
from gene_annotation_episode.rna_structure_comparison_results import result_receipt_key, VALIDATION_KEYS, PREPARED_COPY_FIELDS
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store


def forbidden(*args, **kwargs):
    raise AssertionError("comparison attempted native observation/acquisition or unselected calculation")


def forbid_acquisition(monkeypatch, f):
    monkeypatch.setattr(f.targets, "observe_target", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_rna_structure_local.local_rna_structure_plan", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rna_structure_native.parse_rna_native_record", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


def test_actual_worker_selected_counts_exact_return_replay_and_completed_proof(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        original_bytes = [f.originals[i].results._saved_directory(body["episode_id"], body["operation_key"]).joinpath("receipt.json").read_bytes()
            for i, body in enumerate(f.bodies)]
        observations = list(f.targets.observations)
        for original in f.originals:
            shutil.rmtree(original.native_root)
            (original.root_path / "supplied-input.json").unlink()
        forbid_acquisition(monkeypatch, f)
        body = f.execute(child)
        assert body["delivery_complete"] and body["anchor_handoff_ref"] != f.descriptors[0]["handoff_ref"]
        for descriptor in f.descriptors:
            assert f.results.retained_reference_access(child, descriptor["handoff_ref"], "execution_handoff") is True
            assert f.results.retained_reference_access(child, descriptor["handoff_ref"], "artifact") is False
            for field in ("source_ref", "bundle_artifact_ref", "sheet_artifact_ref"):
                assert f.results.retained_reference_access(child, descriptor[field], "execution_handoff") is False
        payload = body["projection_rows"][0]["payload"]["rows"][0]
        assert {c["metric"]: c["value"] for c in payload["measurements"]} == {"preserved_pair_count": 3, "pair_symmetric_difference_count": 0}
        assert payload["pairing_change_state"] == "unchanged_in_complete_correspondence"
        assert "input_paths" not in json.dumps(body["projection_rows"])
        proof = f.results.completion(child)
        assert validate_completion_proof(proof) == proof and proof["validation_keys"] == VALIDATION_KEYS
        assert proof["receipt_sha256"] == digest(body)
        credit = f.results.credit_view(child, {"known_record_refs": [], "initial_known_record_refs": []})
        assert credit["credit"] == credit["new_acquired_record_count"] == credit["new_handoff_count"] == 0
        assert credit["operational_credit_binding"]["acquired_record_unit"] == 3
        before = list(store.db.iterdump())
        monkeypatch.setattr("gene_annotation_episode.rna_structure_comparison_publication.prepare_rna_comparison_grading", forbidden)
        outcome = asyncio.run(f.results.execute(child, f.owner._target(child), body["tool_name"], {}, body["operation_key"]))
        assert outcome["result"] == body and outcome["record_refs"] == outcome["changed_record_refs"] == []
        assert f.results.read_receipt_key(result_receipt_key(body), f.scope) == body
        assert list(store.db.iterdump()) == before and f.targets.observations == observations
        for i, original in enumerate(f.bodies):
            assert f.originals[i].results._saved_directory(original["episode_id"], original["operation_key"]).joinpath("receipt.json").read_bytes() == original_bytes[i]
        form = f.returned(f.root, child)
        assert form["comparison"] == body["projection_rows"]
        assert f.returns.received_facts(f.root, E.schema())[PROJECTION_SOURCE] == form["comparison"]
        assert f.returns.resolve_received(f.root, result_receipt_key(body), "rna_comparison_receipt") is True
        assert f.returns.resolve_received(f.root, result_receipt_key(body), "artifact") is False
        assert f.results.retained_reference_access(f.root, body["comparison_sheet_artifact_ref"], "artifact") is False
        grading = f.results._saved_directory(child.episode_id, body["operation_key"]) / "grading"
        prepared, worker, execution = [json.loads((grading / name).read_text()) for name in
            ("prepared.json", "worker-receipt.json", "execution-receipt.json")]
        internal = {value for record in (prepared, worker, execution) for key, value in record.items()
            if key.endswith("artifact_ref") and value is not None}
        internal.update(row["artifact_ref"] for row in worker["output_artifacts"])
        for artifact in internal:
            assert f.results.retained_reference_access(f.root, artifact, "artifact") is False
        E.retain("selected_counts", result=body, form=form, proof=proof, credit=credit)


def test_status_checks_retained_inputs_without_worker_native_or_completion(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        forbid_acquisition(monkeypatch, f)
        monkeypatch.setattr("gene_annotation_episode.rna_structure_comparison_publication.prepare_rna_comparison_grading", forbidden)
        monkeypatch.setattr("gene_annotation_episode.rna_structure_comparison_publication.validate_prepared_rna_comparison", forbidden)
        status = f.execute(child, name="execution.results.status")
        assert status["projection_rows"] == status["issues"] == status["selected_input_digests"] == []
        assert not status["delivery_complete"] and status["comparison_sheet_artifact_ref"] is None
        assert f.results.completion(child) is None and not f.results.facts(child)["execution_completed"]
        assert f.results.retained_reference_access(f.root, f.descriptors[0]["sheet_artifact_ref"], "artifact") is None


@pytest.mark.parametrize("problem", ["missing", "changed"])
def test_collect_records_real_custody_failure_and_replays_it_after_restoration(tmp_path, monkeypatch, problem):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        descriptor = f.descriptors[0]
        path = store.path / "artifacts" / descriptor["sheet_sha256"][:2] / descriptor["sheet_sha256"]
        original = path.read_bytes()
        path.unlink() if problem == "missing" else path.write_bytes(b"{}\n")
        forbid_acquisition(monkeypatch, f)
        monkeypatch.setattr("gene_annotation_episode.rna_structure_comparison_publication.prepare_rna_comparison_grading", forbidden)
        body = f.execute(child)
        code = "retained_sheet_missing" if problem == "missing" else "retained_sheet_digest_mismatch"
        assert [i["code"] for i in body["issues"]] == [code]
        assert body["projection_rows"] == body["selected_input_digests"] == []
        assert len(body["original_receipt_keys"]) == 2 and body["preparation_failure"] is None
        assert f.results.completion(child) is None
        path.write_bytes(original)
        replay = asyncio.run(f.results.execute(child, f.owner._target(child), body["tool_name"], {}, body["operation_key"]))
        assert replay["result"] == body and not replay["result"]["delivery_complete"]
        E.retain("custody_" + problem, result=body)


def test_two_requested_structures_are_exact_without_unrequested_measurements(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child(f.selector(structures=True))
        body = f.execute(child)
        rows = body["projection_rows"][0]["payload"]["rows"]
        assert [r["member_id"] for r in rows] == ["WT", "V"]
        assert [[v["field"] for v in r["values"]] for r in rows] == [["original_sequence", "dot_bracket"]] * 2
        assert [[v["value"] for v in r["values"]] for r in rows] == [["GGGAAACCC", "(((...)))"], ["GGGAAAUCC", "(((...)))"]]
        E.retain("two_structures", result=body)


def test_compact_scan_preserves_failure_alias_absence_without_invented_rank(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture", failure=True)
        child = f.child(f.selector(scan=True))
        body = f.execute(child)
        assert body["delivery_complete"]
        row = body["projection_rows"][0]
        cells = {c["metric"]: c for c in row["payload"]["measurements"]}
        assert cells["declared_variant_count"]["value"] == 3
        assert cells["received_failure_variant_count"]["value"] == cells["not_tested_variant_count"]["value"] == 1
        assert cells["baseline_rank_start"]["value"] is None and row["payload"]["rank_class"] == "unavailable"
        assert row["qualification"]["member_ids"] == ["WT"]
        assert "input_paths" not in json.dumps(row) and "dot_bracket" not in json.dumps(row)
        assert len(json.dumps(row)) < 12000
        assert f.results.completion(child) is not None
        E.retain("qualified_scan", result=body)


def test_actual_action_completion_required_and_changed_outcome_rejected(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child, finish=False)
        assert body["delivery_complete"] and f.results.completion(child) is None
        assert f.results.facts(child)[PROJECTION_SOURCE] == []
        outcome = f.results._outcome(body)
        outcome["result"]["projection_rows"][0]["payload"]["rows"][0]["measurements"][0]["value"] = 999
        store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(outcome), f.run_id, child.episode_id))
        with pytest.raises(ValueError, match="recorded_outcome_mismatch"):
            f.results.completion(child)


@pytest.mark.parametrize("field", ["scope_key", "selected_action_digest", "assignment_digest", "projection_rows"])
def test_rehashed_or_rewritten_receipt_cannot_substitute_selected_work(tmp_path, field):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        forged = deepcopy(body)
        if field == "projection_rows":
            forged[field][0]["payload"]["rows"][0]["measurements"][0]["value"] = 999
        else:
            forged[field] = "0" * 64
        directory = f.results._saved_directory(child.episode_id, body["operation_key"])
        (directory / "receipt.json").write_text(canonical(forged) + "\n")
        store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(f.results._outcome(forged)), f.run_id, child.episode_id))
        with pytest.raises(ValueError):
            f.results.read_receipt_key(result_receipt_key(body), f.scope)


def test_scientific_forwarding_and_unrequested_source_do_not_broaden_returns(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        scientific = f.child(role="scientific_process", index=10)
        child = f.child(parent=scientific, index=0)
        body = f.execute(child)
        direct = f.returned(scientific, child)
        assert f.returned(f.root, scientific) == direct
        assert f.returns.received_facts(f.root, E.schema(False)) == {}
        fake = deepcopy(direct)
        fake["comparison"][0]["qualification"]["baseline_member_id"] = "V"
        with pytest.raises(ValueError):
            f.returns.validate_received_report(scientific, fake, E.schema())
        other = f.child(index=11, returned=False)
        f.execute(other)
        assert f.results.facts(other)[PROJECTION_SOURCE] == []
        assert not f.results.resolve(other, result_receipt_key(body), "rna_comparison_receipt")


def test_changed_frozen_form_is_not_hidden_by_prior_reference_resolution(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        form = f.returned(f.root, child)
        key = result_receipt_key(body)
        assert f.returns.resolve_received(f.root, key, "rna_comparison_receipt")
        form["comparison"] = []
        store.db.execute("UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?",
            (canonical(form), f.run_id, child.episode_id))
        with pytest.raises(ValueError):
            f.returns.resolve_received(f.root, key, "rna_comparison_receipt")


def test_independent_explicit_artifact_return_preserves_identical_bytes_custody(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        body = f.execute(f.child())
        artifact = body["comparison_sheet_artifact_ref"]
        assert f.results.retained_reference_access(f.root, artifact, "artifact") is False
        declared = {"type": "object", "additionalProperties": False, "required": ["artifacts"], "properties": {
            "artifacts": {"type": "array", "x-source": "independent_artifact_refs", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "artifact"}}}}
        contract = TypedReportContract("Return the independently supplied exact artifact", declared, lambda *_: True)
        child = f.originals[0].context((*f.root.path, ("scientific_process", "child_11")), {}, contract, f.root)
        f.journal.save("runtime_actions", {"episode_id": f.root.episode_id, "decision_index": 11,
            "action": canonical({"kind": "episode_child", "role": child.role, "assignment": {}, "scope": f.scope,
                "purpose": contract.decision, "schema_json": canonical(declared)}), "result": None, "credit": None})
        f.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
            "action": canonical({"kind": "tool", "tool": "synthetic.independent_artifact", "arguments": {}}),
            "result": canonical({"status": "completed", "record_refs": [artifact]}), "credit": 0})
        form = {"artifacts": [artifact]}
        f.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical({"independent_artifact_refs": [artifact]}), "form": canonical(form)})
        f.journal.save("runtime_report_attempts", {"parent_episode_id": f.root.episode_id, "decision_index": 11,
            "delivery_ref": "independent-comparison-bytes", "child_episode_id": child.episode_id,
            "contract": canonical(E.plain(child.request)["report_contract"]), "form": canonical(form), "failure": None})
        f.receipts.receive(f.root.episode_id, [artifact], kind="child_form", source_index=11)
        assert f.results.retained_reference_access(f.root, artifact, "artifact") is True
        assert f.results.retained_reference_access(f.root, artifact, "source") is False
        form["artifacts"] = []
        store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=11",
            (canonical(form), f.run_id, f.root.episode_id))
        with pytest.raises(ValueError):
            f.results.retained_reference_access(f.root, artifact, "artifact")


def test_rehashed_projection_artifacts_and_receipt_still_fail_actual_recomputation(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        body = f.execute(child)
        directory = f.results._saved_directory(child.episode_id, body["operation_key"])
        prepared = json.loads((directory / "grading/prepared.json").read_text())
        worker = json.loads(store.get_artifact(prepared["worker_receipt_artifact_ref"]))
        projection = next(row for row in worker["output_artifacts"] if row["role"] == "projections")
        rows = json.loads(store.get_artifact(projection["artifact_ref"]))
        rows[0]["payload"]["rows"][0]["measurements"][0]["value"] = 999
        fresh = store.artifact((canonical(rows) + "\n").encode(), "application/json")
        projection.update(artifact_ref=fresh, sha256=store.get(fresh)["sha256"])
        prepared.update(projection_rows_artifact_ref=fresh, projection_rows=rows)
        manifest_row = next(row for row in worker["output_artifacts"] if row["role"] == "worker_result")
        manifest = json.loads(store.get_artifact(manifest_row["artifact_ref"]))
        manifest["projection_rows_sha256"] = projection["sha256"]
        fresh = store.artifact((canonical(manifest) + "\n").encode(), "application/json")
        manifest_row.update(artifact_ref=fresh, sha256=store.get(fresh)["sha256"])
        prepared["worker_receipt_artifact_ref"] = store.artifact((canonical(worker) + "\n").encode(), "application/json")
        (directory / "grading/prepared.json").write_text(canonical(prepared) + "\n")
        body.update({key: deepcopy(prepared[key]) for key in PREPARED_COPY_FIELDS})
        (directory / "receipt.json").write_text(canonical(body) + "\n")
        store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(f.results._outcome(body)), f.run_id, child.episode_id))
        with pytest.raises(ValueError, match="prepared_mismatch"):
            f.results.read_receipt_key(result_receipt_key(body), f.scope)
