"""436 host checks using437's actual original Workflow and native authority.

Inputs and choices are synthetic; positive actions, native outputs, bounded
worker executions and returned forms come from production implementations.
Each deliberate corruption below is scoped and labeled as a negative test.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.genomic_overlap_return_views import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, retained_native_file
from gene_annotation_episode import native_genomic_overlap_results as host_module


F = import_module("verification.tool_graders_genomic_overlap_workflow_2026-10-27_437.fixture_helpers")


def deny(*args, **kwargs):
    pytest.fail("unexpected native access, retained scientific read or new worker dispatch")


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    from gene_annotation_episode import genomic_overlap_result_receipts as receipts
    import traceback
    original = receipts.require
    def traced(condition, code="genomic_overlap_result_authority_conflict"):
        if not condition:
            traceback.print_stack(limit=14)
        return original(condition, code)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(receipts, "require", traced)
        patch.setattr(host_module, "require", traced)
        value = F.workflow_case(tmp_path_factory.mktemp("actual-host436"))
    yield value
    value.store.close()


def host(case):
    return case.owner.native_genomic_overlap_results


def receipt(case, position=0):
    return case.outcomes[position]["result"]


def selected_outcome(value):
    if "pending_work_after_action" in value:
        from gene_annotation_episode.waiting import validate_pending
        validate_pending(value["pending_work_after_action"])
    return {key: item for key, item in value.items() if key != "pending_work_after_action"}


def test_catalog_and_actual_original_and_saved_exact_values(case):
    catalog = host_module.operation_catalog()
    assert [row["name"] for row in catalog] == ["execution.results.status", "execution.results.collect"]
    assert all(row["input_schema"] == {"type": "object", "properties": {}, "required": [],
        "additionalProperties": False} for row in catalog)
    original, saved = case.outcomes
    assert original["status"] == saved["status"] == "completed"
    first, second = [row["overlap"][0] for row in case.returned]
    assert [row["measurements"]["unfiltered.pairwise_overlap_bp_sum"] for row in first["pair_rows"]] == [8, 5, 2]
    assert [row["measurements"]["unfiltered.jaccard_bp"]["value"] for row in first["pair_rows"]] == pytest.approx([1/3, 1/4, 2/13])
    assert [row["measurements"]["selected.selected_pair_count"] for row in second["pair_rows"]] == [1, 1, 0]
    assert first["parameters"]["minimum_overlap_bp"] == 1 and second["parameters"]["minimum_overlap_bp"] == 4
    assert case.returned[0]["saved"] == case.returned[1]["saved"]
    assert all(row["completed"] for row in case.returned)
    assert receipt(case)["observation"]["native"]["terminal"] is True
    assert receipt(case)["observation"]["native"]["quiescent"] is True
    assert receipt(case, 1)["observation"] is None and receipt(case, 1)["native"] is None
    assert set(receipt(case, 1)["worker_plan"]) == {"version", "mode", "directory", "sheet", "selector"}
    for row in case.outcomes:
        execution = row["result"]["worker_execution"]
        assert execution["metadata"]["policy"] == F.POLICY
        assert execution["metadata"]["verified_cgroup"]["memory_swap_max"] == 0
        assert execution["metadata"]["verified_cgroup"]["runtime_max"] == "infinity"


def test_own_return_resolution_and_private_classification(case, monkeypatch):
    service = host(case)
    saved = receipt(case)["qualified_files"]["sheet"]
    with monkeypatch.context() as patch:
        patch.setattr(host_module, "retained_native_file", deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), "observe_target", deny)
        assert service.resolve_own(case.result_contexts[0], saved["artifact_ref"], "artifact")
        assert not service.resolve_own(case.result_contexts[0], saved["artifact_ref"], "source")
        for file in receipt(case)["qualified_files"].values():
            assert service.owns_reference(file["artifact_ref"])
        for spec in case.job["request"]["region_sets"]:
            assert not service.owns_reference(spec["source"]["file"]["artifact_ref"])
        for context in case.result_contexts:
            facts = service.facts(context)
            assert all(facts[key] == [] for key in ("execution_handoff_refs", "execution_result_refs", "execution_blast_hsps"))


def test_completed_replay_and_historical_facts_survive_scientific_byte_loss(case, monkeypatch):
    service = host(case)
    before = [(service.own_fact_groups(context, verify_artifacts=False), service.completion(context))
        for context in case.result_contexts]
    files = {file["artifact_ref"]: file for row in case.outcomes
        for file in row["result"]["qualified_files"].values() if file is not None}
    removed = []
    try:
        for file in files.values():
            path = retained_native_file(case.store, file)
            removed.append((path, path.read_bytes()))
            path.unlink()
        with monkeypatch.context() as patch:
            patch.setattr(host_module, "retained_native_file", deny)
            patch.setattr(host_module, "capture_genomic_overlap_native_files", deny)
            patch.setattr(host_module, "prepare_genomic_overlap_worker", deny)
            patch.setattr(type(case.owner.job_progress_provider.targets), "observe_target", deny)
            patch.setattr("gene_annotation_episode.native_genomic_overlap_local.local_genomic_overlap_plan", deny)
            for index, context in enumerate(case.result_contexts):
                actual = asyncio.run(service.execute(context, case.provider.target, "execution.results.collect", {},
                    receipt(case, index)["intent"]["operation_key"]))
                assert canonical(actual) == canonical(selected_outcome(case.outcomes[index]))
                assert (service.own_fact_groups(context, verify_artifacts=False), service.completion(context)) == before[index]
                assert service.retained_target(context, plain(context.assignment), plain(context.scope)) == case.provider.target
        with pytest.raises(NativeFileCaptureError):
            service.own_fact_groups(case.result_contexts[0], verify_artifacts=True)
    finally:
        for path, raw in removed:
            path.write_bytes(raw)


def test_credit_one_original_population_and_zero_saved_recalculation(case):
    service = host(case)
    first, saved = [service.credit_view(context, None) for context in case.result_contexts]
    assert first["new_acquired_record_count"] == 1
    assert first["operational_credit"] == case.owner.acquired_record_unit
    assert saved["new_acquired_record_count"] == 0 and saved["operational_credit"] == 0
    assert first["operational_credit_binding"]["scientific_credit"] is False
    assert first["operational_credit_binding"]["monitoring_credit"] is False
    selection = case.owner._selection(case.result_contexts[1])
    assert receipt(case)["acquired_population"] in service.receipts.baseline_populations(
        case.result_contexts[1], selection["initial_known_record_refs"])
    assert first == service.credit_view(case.result_contexts[0], None)


def test_baseline_uses_frozen_delivery_and_deduplicates_actual_received_origins(case, monkeypatch):
    """Later actual returns do not enter an earlier context's baseline."""
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    service = host(case)
    original, saved = case.result_contexts
    file, = case.returned[0]["saved"]
    population = receipt(case)["acquired_population"]
    index = EpisodeReceipts(case.store, case.owner.run_id)
    first_manifest = index.manifest(original.episode_id)
    saved_manifest = index.manifest(saved.episode_id)
    assert file["artifact_ref"] not in index.known(original.episode_id, baseline=True)
    assert file["artifact_ref"] in index.known(saved.episode_id, baseline=True)
    assert original.episode_id not in {row["child_episode_id"]
        for row in first_manifest["received_report_prefix"]["attempts"]}
    assert saved.episode_id not in {row["child_episode_id"]
        for row in saved_manifest["received_report_prefix"]["attempts"]}
    # Both actual results are now delivered to science. Their equal sheet does
    # not expand either previously frozen child's received report prefix.
    assert case.owner.native_genomic_overlap_returns.authenticate_received_saved_sheet(
        case.scientific_context, file) == (original.episode_id, saved.episode_id)
    actual_received = service.receipts.returns._received
    calls = []
    def received(context, sources, **kwargs):
        calls.append({"episode_id": context.episode_id, "allowed": deepcopy(kwargs.get("allowed"))})
        return actual_received(context, sources, **kwargs)
    monkeypatch.setattr(service.receipts.returns, "_received", received)
    duplicated = [file["artifact_ref"], file["artifact_ref"]]
    assert service.receipts.baseline_populations(original, duplicated) == set()
    first_calls = list(calls)
    calls.clear()
    assert service.receipts.baseline_populations(saved, duplicated) == {population}
    for observed, manifest in ((first_calls, first_manifest), (calls, saved_manifest)):
        direct = [row for row in observed if row["episode_id"] == case.scientific_context.episode_id]
        assert direct and direct[0]["allowed"] == manifest["received_report_prefix"]["attempts"]
    assert service.credit_view(original, None)["new_acquired_record_count"] == 1
    assert service.credit_view(saved, None)["new_acquired_record_count"] == 0
    F.write(case.directory / "FROZEN_BASELINE_CHECK.json", {"duplicate_reference_count": len(duplicated),
        "original_baseline_populations": [], "saved_baseline_populations": [population],
        "original_frozen_prefix": first_manifest["received_report_prefix"],
        "saved_frozen_prefix": saved_manifest["received_report_prefix"]})


@pytest.mark.parametrize("change", ["selector", "scope", "request", "target", "action"])
def test_original_context_target_and_selected_action_mismatch_rejected(case, change):
    service, context = host(case), case.result_contexts[0]
    target = deepcopy(case.provider.target)
    key = receipt(case)["intent"]["operation_key"]
    if change == "selector":
        assignment = plain(context.assignment)
        assignment["selector"]["parameters"]["minimum_overlap_bp"] = 17
        context = replace(context, assignment=assignment)
    elif change == "scope":
        scope = plain(context.scope)
        scope["subject_refs"] = []
        context = replace(context, scope=scope)
    elif change == "request":
        request = plain(context.request)
        request["goal"] = "injected foreign request"
        context = replace(context, request=request)
    elif change == "target":
        target["execution_id"] += ".foreign"
    else:
        key = key.rsplit(":", 1)[0] + ":117"
    with pytest.raises(ValueError):
        asyncio.run(service.execute(context, target, "execution.results.collect", {}, key))


def test_staged_receipt_does_not_become_completed_runtime_authority(case):
    """Explicit negative injection: temporarily remove the committed outcome."""
    service, context = host(case), case.result_contexts[0]
    db = case.store.db
    original = db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
        (context.run_id, context.episode_id)).fetchone()[0]
    try:
        db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0",
            (context.run_id, context.episode_id))
        assert service.own_fact_groups(context, verify_artifacts=False) == {key: [] for key in FACT_SOURCES}
        assert service.completion(context) is None
        assert not service.resolve_own(context, receipt(case)["qualified_files"]["sheet"]["artifact_ref"], "artifact")
        actual = asyncio.run(service.execute(context, case.provider.target, "execution.results.collect", {},
            receipt(case)["intent"]["operation_key"]))
        assert canonical(actual) == canonical(selected_outcome(case.outcomes[0]))
    finally:
        db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (original, context.run_id, context.episode_id))


@pytest.mark.parametrize("failure", ["invalid_c", "missing_ac_stdout"])
def test_actual_partial_inputs_preserve_independent_values_and_incomplete_delivery(tmp_path, failure):
    value = F.workflow_case(tmp_path / failure, failure=failure)
    try:
        context, = value.result_contexts
        actual = value.returned[0]
        assert actual["completed"] is False and actual["failures"]
        rows = {row["comparison_key"]: row for row in actual["overlap"][0]["pair_rows"]}
        assert rows["AB"]["measurements"]["unfiltered.pairwise_overlap_bp_sum"] == 8
        assert rows["AC"]["measurements"]["unfiltered.native_pair_count"] is None
        assert host(value).completion(context) is None
        assert len(F.worker_runs(value.directory)) == 1
        assert value.provider.turns[context.episode_id] == 2
    finally:
        value.store.close()


def test_nonterminal_observation_cannot_capture_or_finish(tmp_path, monkeypatch):
    """Negative observation injection; the underlying native attempt is real."""
    from gene_annotation_episode.execution_progress import ExecutionTargetReader
    original = ExecutionTargetReader.observe_target
    observed = []
    def nonterminal(self, *args, **kwargs):
        value = original(self, *args, **kwargs)
        observed.append(deepcopy(value))
        value.update(state="running", returncode=None, failure_code=None)
        value["native"].update(state="running", terminal=False, quiescent=False)
        for row in value["outputs"]:
            row["writer_closed"] = False
        return value
    monkeypatch.setattr(ExecutionTargetReader, "observe_target", nonterminal)
    monkeypatch.setattr(host_module, "capture_genomic_overlap_native_files", deny)
    monkeypatch.setattr(host_module, "prepare_genomic_overlap_worker", deny)
    value = F.workflow_case(tmp_path / "injected-nonterminal", failure="invalid_c")
    try:
        actual = receipt(value)
        assert observed and observed[0]["native"]["terminal"] is True
        assert actual["observation"]["native"]["terminal"] is False
        assert actual["capture"] is None and actual["worker_plan"] is None
        assert actual["facts"][PROJECTION_SOURCE] == [] and actual["facts"][SAVED_SOURCE] == []
        assert host(value).completion(value.result_contexts[0]) is None
        F.write(value.directory / "INJECTED_NONTERMINAL.json", {"actual_observations": observed,
            "injected_observation": actual["observation"], "returned_failure": actual["host_failures"]})
    finally:
        value.store.close()


def test_byte_verification_is_separate_from_semantic_output_qualification(case):
    """Negative role injection based on a real verified434 worker capture."""
    from gene_annotation_episode.genomic_overlap_result_receipts import qualified_files
    original = receipt(case)
    changed = deepcopy(original)
    capture = changed["worker_capture"]
    issue = host_module._failure("native_output_malformed", stage="parse", field="/outputs/projection",
        file=changed["qualified_files"]["projection"], expected="genomic_overlap_projection_v1")
    capture["failures"].append(issue)
    changed["qualified_files"] = qualified_files(capture, changed["worker_execution"])
    changed["projection"] = None
    assert capture["outputs"][2]["outcome"] == "verified"
    assert changed["qualified_files"]["projection"] is None
    assert changed["qualified_files"]["sheet"] == original["qualified_files"]["sheet"]
    facts, complete = host(case).receipts.publication(changed)
    assert facts[PROJECTION_SOURCE] == [] and facts[SAVED_SOURCE] == original["facts"][SAVED_SOURCE]
    assert issue in facts["genomic_overlap_failures"] and complete is False
    missing = deepcopy(original)
    missing["worker_capture"].update(result=None, worker_result_file=None, outputs=[])
    missing["qualified_files"] = qualified_files(missing["worker_capture"], missing["worker_execution"])
    missing["projection"] = None
    facts, complete = host(case).receipts.publication(missing)
    assert facts[PROJECTION_SOURCE] == facts[SAVED_SOURCE] == [] and complete is False


def test_real_worker_reservation_interruption_recovers_same_selected_action(tmp_path, monkeypatch):
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.state import Store
    class InjectedInterruption(BaseException):
        pass
    directory = tmp_path / "interrupted-real-worker"
    actual_start = native_lifecycle.start_prepared
    interrupted = []
    def start(handle, *args, **kwargs):
        if Path(handle.path).name == "worker.handle.json" and not interrupted:
            interrupted.append(json.loads(Path(handle.path).read_bytes()))
            raise InjectedInterruption("after real434 reservation, before its dispatch")
        return actual_start(handle, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(native_lifecycle, "start_prepared", start)
        with pytest.raises(InjectedInterruption):
            F.workflow_case(directory)
    assert interrupted
    class NoDecisions:
        async def complete(self, *args, **kwargs):
            pytest.fail("recovery is the original selected operation")
        async def release(self, *args):
            pass
    configuration = json.loads((directory / "fixture-configuration.json").read_bytes())
    with Store(directory / "state") as store:
        flow, _ = F.assemble(store, directory, NoDecisions(), configuration)
        owner = flow.episode_bindings.for_role("results")
        service = owner.native_genomic_overlap_results
        row, = list(store.db.execute("SELECT episode_id,decision_index,result FROM runtime_actions WHERE "
            "json_extract(action,'$.tool')='execution.results.collect'"))
        assert row["result"] is None
        context = owner.native_genomic_overlap_returns.context(row["episode_id"])
        key = f'{context.run_id}:{context.episode_id}:{row["decision_index"]}'
        root = service.receipts.action_directory(context.episode_id, key)
        intent = json.loads((root / "intent.json").read_bytes())
        assert not (root / "receipt.json").exists()
        with monkeypatch.context() as patch:
            patch.setattr(host_module, "capture_genomic_overlap_native_files", deny)
            patch.setattr(type(owner.job_progress_provider.targets), "observe_target", deny)
            patch.setattr(native_lifecycle, "prepare_job", deny)
            patch.setattr("gene_annotation_episode.native_genomic_overlap_preparation._snapshot", deny)
            recovered = asyncio.run(service.execute(context, intent["target"], "execution.results.collect", {}, key))
        after = json.loads((root / "worker/worker.handle.json").read_bytes())
        assert after["unit"] == interrupted[0]["unit"]
        assert after["request_sha256"] == interrupted[0]["request_sha256"]
        assert recovered["result"]["worker_execution"]["returncode"] == 0
        assert recovered["result"]["delivery_complete"] is True
        # Public execution stages a receipt. Only the runtime's eventual own
        # committed action can create historical facts or endpoint authority.
        assert service.completion(context) is None
        F.write(directory / "ACTUAL_INTERRUPTED_RECOVERY.json", {"before": interrupted[0], "after": after,
            "same_operation_key": key, "receipt": recovered["result"]})


@pytest.mark.parametrize("kind", ["all_invalid", "valid_zero", "analytic_empty", "never_started"])
def test_acquisition_requires_native_output_or_validated_empty_derivation(tmp_path, monkeypatch, kind):
    from types import SimpleNamespace
    from gene_annotation_episode.acquisition import AcquisitionError
    from gene_annotation_episode import native_lifecycle
    if kind == "all_invalid":
        monkeypatch.setattr(F, "DATA", [b"chr1\t10\t10\n"] * 3)
    elif kind == "valid_zero":
        monkeypatch.setattr(F, "DATA", [b"chr1\t0\t10\n", b"chr1\t10\t20\n", b"chr1\t20\t30\n"])
    elif kind == "analytic_empty":
        monkeypatch.setattr(F, "DATA", [b""] * 3)
    operational_failures = []
    if kind == "never_started":
        actual_software = F.NATIVE.software
        def unavailable_driver():
            selected = actual_software()
            selected["python_executable"] = str(tmp_path / "intentionally-unavailable-driver-python")
            return selected
        monkeypatch.setattr(F.NATIVE, "software", unavailable_driver)
        actual_wait = native_lifecycle.wait_job
        def observed_failure(handle, *args, **kwargs):
            try:
                return actual_wait(handle, *args, **kwargs)
            except AcquisitionError as error:
                # Fixture control only: allow science to commission results
                # after the real failed dispatch. The host observes the actual
                # native failure itself; no successful state is substituted.
                operational_failures.append({"code": error.code, "operational": error.operational})
                return SimpleNamespace(returncode=1, metadata=error.operational)
        monkeypatch.setattr(native_lifecycle, "wait_job", observed_failure)
    value = F.workflow_case(tmp_path / kind,
        failure="invalid_c" if kind in {"all_invalid", "never_started"} else kind)
    try:
        context, = value.result_contexts
        row = receipt(value)
        evidence = row["acquisition_evidence"]
        assert evidence["sheet_file"] == row["qualified_files"]["sheet"]
        assert [pair["comparison_key"] for pair in evidence["comparison_receipts"]] == ["AB", "AC", "BC"]
        credit = host(value).credit_view(context, None)
        if kind in {"all_invalid", "never_started"}:
            assert credit["new_acquired_record_count"] == 0 and credit["operational_credit"] == 0
            assert row["acquired_population"] is None and row["delivery_complete"] is False
        else:
            assert credit["new_acquired_record_count"] == 1
            assert row["acquired_population"] == digest(value.provider.plan["identity"])
            assert row["delivery_complete"] is True
        if kind == "valid_zero":
            assert all(pair["stdout"] is not None and pair["stdout"]["size_bytes"] == 0
                and pair["derivation"] == "bedtools_intersect" for pair in evidence["comparison_receipts"])
        if kind == "analytic_empty":
            assert all(pair["stdout"] is None and pair["derivation"] == "validated_empty_input"
                for pair in evidence["comparison_receipts"])
        if kind == "never_started":
            assert operational_failures and row["native"]["driver_started"] is False
            assert row["capture"]["driver_state"] == "not_started"
        F.write(value.directory / "ACQUISITION_CHECK.json", {"kind": kind,
            "actual_native_failures": operational_failures, "evidence": evidence, "credit": credit})
    finally:
        value.store.close()


@pytest.mark.parametrize("mode", ["native_result", "saved_sheet_recalculation"])
def test_completion_only_form_finishes_selected_work_without_new_sheet_grant(tmp_path, monkeypatch, mode):
    from gene_annotation_episode.numerical import NumericBand
    actual = F.commission
    completion_only = F.result_form(completed=True)
    def commission(role, assignment, scope, form, *, objective):
        if role == "results" and assignment["selector"]["mode"] == mode:
            form = completion_only
        return actual(role, assignment, scope, form, objective=objective)
    monkeypatch.setattr(F, "commission", commission)
    value = F.workflow_case(tmp_path / mode, failure="completion_only" if mode == "native_result" else None)
    try:
        index = 0 if mode == "native_result" else 1
        context = value.result_contexts[index]
        record = next(row for row in value.by_role["results"] if row["episode_id"] == context.episode_id)
        service = host(value)
        assert value.returned[index] == {"completed": True}
        assert all(not rows for rows in service.own_fact_groups(context, verify_artifacts=False).values())
        assert value.outcomes[index]["record_refs"] == []
        file = receipt(value, index)["qualified_files"]["sheet"]
        assert service.owns_reference(file["artifact_ref"])
        assert not service.resolve_own(context, file["artifact_ref"], "artifact")
        assert not value.owner.native_genomic_overlap_returns.resolve_received(value.root_context, file["artifact_ref"], "artifact")
        with pytest.raises(ValueError, match="saved_sheet_not_received"):
            value.owner.native_genomic_overlap_returns.authenticate_received_saved_sheet(value.root_context, file)
        proof = value.owner.completion_for_action(context, receipt(value, index)["intent"]["operation_key"])
        assert proof is not None and value.owner.verify_completion(context, proof)
        assert record["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
        assert record["controller_state"]["estimate"]["provenance"]["version"] == "verified_practical_endpoint_yield_v1"
        assert value.provider.turns[context.episode_id] == 1
        F.write(value.directory / "COMPLETION_ONLY_CHECK.json", {"mode": mode, "returned": value.returned[index],
            "proof": proof, "estimate": record["controller_state"]["estimate"], "own_saved_sheet_grant": False})
    finally:
        value.store.close()


def continued_saved_case(directory, monkeypatch, *, partial):
    """Scripted repair choices over the real437 runtime construction path."""
    from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
    from jsonschema import Draft202012Validator
    original_assemble, original_controller = F.assemble, F.controller_factory
    def controller_factory(*, saved, failure):
        base = original_controller(saved=saved, failure=failure)
        def controller(path, initial):
            if path[-1][0] == "scientific_process":
                def estimate(raw, parameters, contexts):
                    return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= (3 if partial else 4) else 1),
                        parameters, {"fixture": "scripted scientific repair continuation only"})
                return YieldController(str(path), initial, 0, YieldParameters(100, 50), estimate_with_context=estimate)
            if path[-1][0] == "results":
                return YieldController(str(path), initial, 1e9, YieldParameters(2, 1))
            return base(path, initial)
        return controller
    def assemble(store, directory, provider, configuration):
        original_complete = provider.complete
        async def complete(episode_id, role, instructions, current, schema):
            turn = provider.turns.get(episode_id, 0) + 1
            execution = current.get("execution_assignment", {})
            answer = None
            if "scientific_process" in current and turn >= 3:
                report = current["child_reports"][-1]
                sheet, = report["saved"]
                selected = F.selector(saved=sheet, minimum=4)
                if not partial and turn == 3:
                    selected["projection"] = {"kind": "occurrence_rows", "offset": 0, "limit": 1,
                        "measurement_fields": ["span_bp"], "occurrence_keys": [{"set_key": "A", "occurrence_key": "missing_occurrence"}]}
                answer = F.commission("results", {"version": "execution_results_assignment_v1",
                    "handoff_ref": provider.handoff, "selector": selected}, configuration["scope"],
                    F.result_form("overlap", "saved", "failures", completed=True),
                    objective="Calculate the explicitly received saved sheet with the selected occurrence or repaired pair projection.")
            elif execution.get("version") == "execution_results_assignment_v1" and turn >= 2:
                assert turn == 2
                answer = F.action("execution.results.status")
            if answer is None:
                return await original_complete(episode_id, role, instructions, current, schema)
            assert not current.get("feedback"), current.get("feedback")
            provider.turns[episode_id] = turn
            provider.calls.append({"episode_id": episode_id, "role": role,
                "instructions": instructions, "context": deepcopy(current)})
            F.write(directory / f"decision-{len(provider.calls) - 1}.json", provider.calls[-1])
            value = F.provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(value)
            return value
        provider.complete = complete
        return original_assemble(store, directory, provider, configuration)
    monkeypatch.setattr(F, "controller_factory", controller_factory)
    monkeypatch.setattr(F, "assemble", assemble)
    return F.workflow_case(directory, failure="invalid_c" if partial else None)


@pytest.mark.parametrize("partial", [False, True])
def test_saved_completion_uses_original_acquisition_witness_after_failed_projection(tmp_path, monkeypatch, partial):
    value = continued_saved_case(tmp_path / ("partial-original" if partial else "repaired-projection"), monkeypatch,
        partial=partial)
    try:
        service = host(value)
        assert len(value.result_contexts) == (2 if partial else 3)
        assert all(row["saved"] == value.returned[0]["saved"] for row in value.returned)
        last = value.result_contexts[-1]
        if partial:
            assert all(not row["completed"] for row in value.returned)
            assert service.completion(last) is None
            assert not service.receipts.original_acquisition_complete(receipt(value, -1))
        else:
            failed = value.result_contexts[1]
            assert value.returned[0]["completed"] is True
            assert value.returned[1]["completed"] is False and value.returned[1]["overlap"] == []
            assert value.returned[1]["failures"]
            assert value.returned[2]["completed"] is True
            assert service.completion(failed) is None and service.completion(last) is not None
            assert len(receipt(value, 2)["original_origins"]) == 2
            assert [row["measurements"]["selected.selected_pair_count"]
                for row in value.returned[2]["overlap"][0]["pair_rows"]] == [1, 1, 0]
            assert all(row["acquisition_evidence"] is None for row in (receipt(value, 1), receipt(value, 2)))
        assert len(list(value.workspace.rglob("native.json"))) == 1
        assert service.credit_view(last, None)["new_acquired_record_count"] == 0
        F.write(value.directory / "SAVED_ORIGIN_WITNESS_CHECK.json", {"partial_original": partial,
            "returned": value.returned, "origins": receipt(value, -1)["original_origins"],
            "completion": service.completion(last)})
    finally:
        value.store.close()


@pytest.mark.parametrize("failure", ["invalid_c", "missing_ac_stdout"])
def test_ab_only_failure_delivery_excludes_other_native_comparisons(tmp_path, monkeypatch, failure):
    actual_commission = F.commission
    def commission(role, assignment, scope, form, *, objective):
        if role == "results":
            assignment = deepcopy(assignment)
            assignment["selector"]["comparison_keys"] = ["AB"]
        return actual_commission(role, assignment, scope, form, objective=objective)
    monkeypatch.setattr(F, "commission", commission)
    value = F.workflow_case(tmp_path / ("ab-only-" + failure), failure=failure)
    try:
        row = receipt(value)
        assert [pair["comparison_key"] for pair in value.returned[0]["overlap"][0]["pair_rows"]] == ["AB"]
        assert all(issue["comparison_key"] in {None, "AB"} and issue["set_key"] in {None, "A", "B"}
            for issue in value.returned[0]["failures"])
        private = [*row["capture"]["failures"], *row["worker_capture"]["result"]["failures"]]
        outside = [issue for issue in private if issue["comparison_key"] in {"AC", "BC"} or issue["set_key"] == "C"]
        assert outside
        assert not any(issue in value.returned[0]["failures"] for issue in outside)
        # Explicit negative shape checks: keyless located failures stay scoped;
        # an actual-format global worker failure remains requested information.
        global_issue = host_module._failure("resource_limit", stage="native", field="/worker_execution",
            expected=F.POLICY, observed={"memory_swap_max": 0})
        keyless = {**outside[0], "comparison_key": None, "set_key": None}
        selected = host(value).receipts.selected_failures(row, [*outside, keyless, global_issue])
        assert global_issue in selected and all(issue not in selected for issue in outside)
        assert keyless not in selected
        F.write(value.directory / "SELECTED_FAILURE_CHECK.json", {"failure": failure, "requested_pairs": ["AB"],
            "returned": value.returned[0], "retained_unselected_failures": outside,
            "negative_shape_selection": selected})
    finally:
        value.store.close()


def test_ab_only_preserves_actual_global_nonzero_worker_failure(tmp_path, monkeypatch):
    actual_commission, actual_worker = F.commission, host_module.NativeGenomicOverlapResults._worker
    def commission(role, assignment, scope, form, *, objective):
        if role == "results":
            assignment = deepcopy(assignment)
            assignment["selector"]["comparison_keys"] = ["AB"]
        return actual_commission(role, assignment, scope, form, objective=objective)
    async def conflicting_output(self, action, record, plan):
        directory = Path(plan["directory"])
        directory.mkdir(parents=True)
        (directory / "sheet.json").write_bytes(b"injected conflicting output; the real worker must reject it")
        return await actual_worker(self, action, record, plan)
    monkeypatch.setattr(F, "commission", commission)
    monkeypatch.setattr(host_module.NativeGenomicOverlapResults, "_worker", conflicting_output)
    value = F.workflow_case(tmp_path / "actual-global-worker-failure", failure="worker_conflict")
    try:
        row = receipt(value)
        assert row["worker_execution"]["outcome"] == "returned" and row["worker_execution"]["returncode"] != 0
        assert row["worker_capture"]["result"] is None
        assert value.returned[0]["overlap"] == value.returned[0]["saved"] == []
        actual = [issue for issue in value.returned[0]["failures"] if issue["code"] == "native_nonzero_exit"]
        assert actual and all(issue["comparison_key"] is None and issue["set_key"] is None for issue in actual)
        assert row["delivery_complete"] is False and row["acquired_population"] is None
        assert len(F.worker_runs(value.directory)) == 1
        changed = deepcopy(row)
        keyless = {**actual[0], "field_path": None, "artifact_ref": None}
        changed["worker_capture"]["failures"] = [keyless]
        assert host(value).receipts.selected_failures(changed, [keyless]) == [keyless]
        F.write(value.directory / "ACTUAL_GLOBAL_WORKER_FAILURE.json", {"execution": row["worker_execution"],
            "returned_failures": value.returned[0]["failures"], "injection": "conflicting preexisting output bytes"})
    finally:
        value.store.close()


def test_narrow_measurement_keeps_other_actual_calculation_failures_private(tmp_path, monkeypatch):
    actual = F.commission
    monkeypatch.setattr(F, "DATA", [b""] * 3)
    def commission(role, assignment, scope, form, *, objective):
        if role == "results":
            assignment = deepcopy(assignment)
            assignment["selector"]["comparison_keys"] = ["AB"]
            assignment["selector"]["projection"]["measurement_fields"] = ["unfiltered.native_pair_count"]
        return actual(role, assignment, scope, form, objective=objective)
    monkeypatch.setattr(F, "commission", commission)
    value = F.workflow_case(tmp_path / "narrow-native-count", failure="narrow_fields")
    try:
        row = receipt(value)
        components = json.loads(retained_native_file(value.store, row["qualified_files"]["components"]).read_bytes())
        assert any(issue["code"] == "zero_denominator" and "jaccard_bp" in issue["field_path"]
            for issue in components["issues"])
        projected, = value.returned[0]["overlap"]
        assert projected["pair_rows"][0]["measurements"] == {"unfiltered.native_pair_count": 0}
        assert projected["failures"] == value.returned[0]["failures"] == []
        assert value.returned[0]["completed"] is True
        F.write(value.directory / "NARROW_CALCULATION_FAILURE_CHECK.json", {"returned": value.returned[0],
            "private_component_failures": components["issues"]})
    finally:
        value.store.close()
