"""Scripted actual Workflow, tiny real bedtools jobs, production typed returns.

Run through packet437/run_bounded.py only. Native outputs and original runtime
records are generated afresh. No result, action, authority or completion double
substitutes for the public production ports.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.genomic_overlap_return_views import PROJECTION_SOURCE, SAVED_SOURCE
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

F = import_module("verification.tool_graders_genomic_overlap_workflow_2026-10-27_437.fixture_helpers")


def deny(*args, **kwargs):
    raise AssertionError("received-only saved calculation/replay attempted scientific acquisition or a new native invocation")


def worker_output(run, role):
    declaration, = [row["declaration"] for row in run["capture"]["result"]["outputs"] if row["role"] == role]
    captured, = [row for row in run["capture"]["outputs"] if row["declared"] == declaration]
    assert captured["outcome"] == "verified", captured
    return captured["observed"]


def projection_values(projection):
    return {row["comparison_key"]: row["measurements"] for row in projection["pair_rows"]}


def contained_versions(value):
    if isinstance(value, dict):
        # Schema declarations also have a properties.version object. Only a
        # serialized record's literal version identifies an embedded sheet.
        if isinstance(value.get("version"), str):
            yield value["version"]
        for item in value.values():
            yield from contained_versions(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from contained_versions(item)


@pytest.fixture(scope="module")
def connected_case(tmp_path_factory):
    directory = tmp_path_factory.mktemp("genomic-overlap437")
    evidence = {}
    patch = pytest.MonkeyPatch()

    def before_saved(case):
        original, = F.worker_runs(directory)
        assert original["plan"]["mode"] == "native_result"
        evidence["original_worker"] = original
        evidence["sheet_identity"] = deepcopy(case.sheet)
        evidence["sheet_bytes"] = case.store.get_artifact(case.sheet["artifact_ref"])
        components = worker_output(original, "components")
        evidence["components_identity"] = components
        evidence["components_bytes"] = case.store.get_artifact(components["artifact_ref"])
        evidence["observations"] = F.rows(case.store, "runtime_observations")
        evidence["completed_actions"] = [row for row in F.rows(case.store, "runtime_actions") if row["result"] is not None]
        evidence["source_action_key"] = case.provider.plan["identity"]["operation_key"]
        evidence["native_plans"] = {str(p): p.read_bytes() for p in case.workspace.rglob("genomic-overlap-plan.json")}
        evidence["origins_before_saved"] = case.owner.native_genomic_overlap_returns.authenticate_received_saved_sheet(
            case.science_context, case.sheet)
        removed = []
        scientific_roles = {"original_input", "rejected_input", "parsed_set", "canonical_set",
            "overlap_stdout", "overlap_stderr", "version_stdout", "version_stderr"}
        for spec in case.provider.plan["requested_job"]["native_genomic_overlap"]["outputs"]:
            if spec["role"] not in scientific_roles:
                continue
            raw = case.provider.native_bytes.get(spec["file_key"])
            producer = Path(case.provider.plan["attempt_directory"]) / spec["relative_path"]
            if producer.exists():
                producer.unlink()
                removed.append({"kind": "producer", "path": str(producer), "file_key": spec["file_key"], "bytes": len(raw)})
            if raw is not None:
                sha = hashlib.sha256(raw).hexdigest()
                retained = case.store.path / "artifacts" / sha[:2] / sha
                if retained.exists():
                    retained.unlink()
                    removed.append({"kind": "retained_native_scientific_bytes", "path": str(retained),
                        "sha256": sha, "bytes": len(raw)})
        for selected in case.provider.plan["requested_job"]["native_genomic_overlap"]["inputs"]:
            path = Path(selected["path"])
            if path.exists():
                size = path.stat().st_size
                path.unlink()
                removed.append({"kind": "producer_input", "path": str(path), "bytes": size})
        assert removed
        evidence["removed"] = removed
        evidence["dispatches"] = []
        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ["-B", "-S", "-m", "gene_annotation_episode.genomic_overlap_result_worker"]
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan["mode"] == "saved_sheet_recalculation"
            assert set(plan) == {"version", "mode", "directory", "sheet", "selector"}
            assert plan["sheet"]["file"] == case.sheet
            assert kwargs["policy"].to_dict() == F.POLICY
            evidence["dispatches"].append({"command": list(command), "plan": deepcopy(plan)})
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, "prepare_job", saved_worker_only)
        patch.setattr("gene_annotation_episode.native_genomic_overlap_results.capture_genomic_overlap_native_files", deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), "observe_target", deny)
        patch.setattr("socket.create_connection", deny)

    try:
        case = F.workflow_case(directory, before_saved=before_saved)
        case.saved_evidence = evidence
        F.write(directory / "SAVED_CHECK.json", {key: value for key, value in evidence.items()
            if key not in {"sheet_bytes", "components_bytes", "native_plans"}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_selected_library_launch_native_sheet_calculation_and_exact_typed_return(connected_case):
    case = connected_case
    assert {role: len(rows) for role, rows in case.by_role.items()} == {
        "annotation": 1, "scientific_process": 1, "launch": 1, "launch_local": 1, "results": 2}
    assert "analyze_genomic_region_overlap" not in case.tools.catalog()
    selected = plain(case.scientific_context.assignment)["selection"]
    information, = selected["child_tool_info"]
    assert information["name"] == "analyze_genomic_region_overlap" and information["resources"] == "local"
    assert information["description"] and information["instructions"]
    plan = case.provider.plan
    assert plan["requested_job"]["native_genomic_overlap"] == case.job
    assert plan["policy"] == F.POLICY
    assert [[int(line.split(b"\t")[-1]) for line in case.provider.native_bytes[f"p{i}:stdout"].splitlines()]
            for i in range(3)] == [[3, 5], [5], [2]]
    batch = json.loads(case.provider.native_bytes["batch_manifest"])
    assert batch["batch_status"] == "complete"
    assert [r["manifest"]["returncode"] for r in batch["pairs"]] == [0, 0, 0]
    assert all(r["manifest"]["realized_argv"][-2:] == ["-wo", "-sorted"] for r in batch["pairs"])
    assert all(r["manifest"]["derivation"] == "bedtools_intersect" for r in batch["pairs"])
    sheet = json.loads(case.saved_evidence["sheet_bytes"])
    baseline = json.loads(case.saved_evidence["components_bytes"])
    assert case.outcomes[0]["result"]["acquisition_evidence"] == {
        "version": "genomic_overlap_acquisition_evidence_v1",
        "sheet_file": case.saved_evidence["sheet_identity"],
        "comparison_receipts": [pair["receipt"] for pair in sheet["comparisons"]]}
    assert case.outcomes[0]["result"]["acquired_population"] == digest(plan["identity"])
    assert sheet["request"] == case.job["request"]
    assert [[row["native_overlap_bp"] for row in pair["valid_pairs"]] for pair in sheet["comparisons"]] == [[3, 5], [5], [2]]
    assert [pair["unfiltered"]["pairwise_overlap_bp_sum"] for pair in baseline["pairs"]] == [8, 5, 2]
    assert [pair["unfiltered"]["intersection_union_bp"] for pair in baseline["pairs"]] == [5, 5, 2]
    assert [pair["unfiltered"]["combined_union_bp"] for pair in baseline["pairs"]] == [15, 20, 13]
    first, second = [form["overlap"][0] for form in case.returned]
    assert first["measurement_fields"] == F.FIELDS
    assert first["page"] == {"offset": 0, "limit": 3, "total_rows": 3, "returned_rows": 3}
    expected = {"AB": (2, 8, 5, 15, 1/3), "AC": (1, 5, 5, 20, 1/4), "BC": (1, 2, 2, 13, 2/13)}
    for row in first["pair_rows"]:
        count, width, intersection, union, jaccard = expected[row["comparison_key"]]
        assert row["reference_relation"] == "same_supplied_reference"
        assert row["result_extent"] == "complete" and not row["issues"]
        assert row["measurements"] == {"unfiltered.native_pair_count": count,
            "unfiltered.pairwise_overlap_bp_sum": width, "unfiltered.intersection_union_bp": intersection,
            "unfiltered.combined_union_bp": union,
            "unfiltered.jaccard_bp": {"numerator": intersection, "denominator": union,
                "value": jaccard, "missing_reason": None},
            "selected.selected_pair_count": count, "selected.selected_pairwise_bp_sum": width}
    assert case.forwarded == {"overlap": [first, second]}
    actual_received = case.owner.native_genomic_overlap_returns.received_facts(case.root_context, case.parent_form)
    assert actual_received == {PROJECTION_SOURCE: [first, second]}
    for call in case.provider.calls:
        # Provider transport calls use REASONING; the durable episode context
        # carries the actual receiving role under test.
        if case.contexts[call["episode_id"]].role in {"annotation", "scientific_process"}:
            assert not {"genomic_region_overlap_sheet_v1", "genomic_region_overlap_components_v1"}.intersection(
                contained_versions(call["context"]))
    # Inspect actual commissions rather than creating matching control fixtures.
    actions = F.rows(case.store, "runtime_actions")
    commissions = [json.loads(row["action"]) for row in actions if json.loads(row["action"])["kind"] == "episode_child"]
    assert [sum(row["role"] == role for row in commissions) for role in
        ("scientific_process", "launch", "launch_local", "results")] == [1, 1, 1, 2]
    for context, form in zip(case.result_contexts, case.returned):
        groups = case.owner.native_genomic_overlap_results.own_fact_groups(context, verify_artifacts=False)
        assert form == {"overlap": groups[PROJECTION_SOURCE], "saved": groups[SAVED_SOURCE],
            "failures": groups[F.FAILURE_SOURCE], "completed": True}


def test_explicitly_received_sheet_recalculates_after_native_source_loss(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert len(saved["dispatches"]) == 1
    assert saved["dispatches"][0]["plan"]["selector"]["parameters"]["minimum_overlap_bp"] == 4
    assert saved["origins_before_saved"] == (case.result_contexts[0].episode_id,)
    assert case.outcomes[1]["result"]["acquisition_evidence"] is None
    assert case.outcomes[1]["result"]["acquired_population"] is None
    assert case.returned[0]["saved"] == case.returned[1]["saved"] == [saved["sheet_identity"]]
    assert case.store.get_artifact(saved["sheet_identity"]["artifact_ref"]) == saved["sheet_bytes"]
    assert case.store.get_artifact(saved["components_identity"]["artifact_ref"]) == saved["components_bytes"]
    assert all(not Path(row["path"]).exists() for row in saved["removed"] if row["bytes"] > 0)
    assert {str(p): p.read_bytes() for p in case.workspace.rglob("genomic-overlap-plan.json")} == saved["native_plans"]
    runs = F.worker_runs(case.directory)
    assert [r["plan"]["mode"] for r in runs].count("native_result") == 1
    assert [r["plan"]["mode"] for r in runs].count("saved_sheet_recalculation") == 1
    original, recalculated = [projection_values(form["overlap"][0]) for form in case.returned]
    assert [recalculated[pair]["selected.selected_pair_count"] for pair in ("AB", "AC", "BC")] == [1, 1, 0]
    assert [recalculated[pair]["selected.selected_pairwise_bp_sum"] for pair in ("AB", "AC", "BC")] == [5, 5, 0]
    for pair in original:
        assert {k: v for k, v in original[pair].items() if k.startswith("unfiltered.")} == {
            k: v for k, v in recalculated[pair].items() if k.startswith("unfiltered.")}
    current_observations = F.rows(case.store, "runtime_observations")
    assert all(row in current_observations for row in saved["observations"])
    current_actions = F.rows(case.store, "runtime_actions")
    assert all(row in current_actions for row in saved["completed_actions"])


def test_projection_only_forwarding_grants_no_hidden_saved_sheet(connected_case):
    case = connected_case
    file = case.saved_evidence["sheet_identity"]
    reader = case.owner.native_genomic_overlap_returns
    assert reader.authenticate_received_saved_sheet(case.scientific_context, file) == tuple(
        context.episode_id for context in case.result_contexts)
    assert reader.resolve_received(case.scientific_context, file["artifact_ref"], "artifact")
    assert not reader.resolve_received(case.root_context, file["artifact_ref"], "artifact")
    with pytest.raises(ValueError, match="saved_sheet_not_received"):
        reader.authenticate_received_saved_sheet(case.root_context, file)
    facts = json.loads(case.flow.journal.row("runtime_forms", case.scientific_context.episode_id)["facts"])
    assert facts[PROJECTION_SOURCE] == case.forwarded["overlap"]
    assert "genomic_overlap_received_report_prefix" in facts
    assert len(facts["genomic_overlap_received_report_prefix"]["attempts"]) == 2
    assert SAVED_SOURCE not in {row.get("x-source") for row in case.parent_form["properties"].values()}


def test_validated_practical_endpoints_preserve_final_gain_without_extra_turn(connected_case):
    case = connected_case
    for row in case.records:
        context = case.contexts[row["episode_id"]]
        actions = [r for r in F.rows(case.store, "runtime_actions") if r["episode_id"] == context.episode_id]
        observations = [r for r in F.rows(case.store, "runtime_observations") if r["episode_id"] == context.episode_id]
        assert len(actions) == len(observations) == row["units_consumed"] == case.provider.turns[context.episode_id]
        if context.role in {"launch", "launch_local", "results"}:
            assert len(actions) == 1
            estimate = row["controller_state"]["estimate"]
            assert estimate["expected_next_gain"] == NumericBand.exact(0).as_record()
            assert estimate["provenance"]["version"] == "verified_practical_endpoint_yield_v1"
            proof = case.owner.completion_for_action(context, f"{F.RUN_ID}:{context.episode_id}:0")
            assert proof is not None and case.owner.verify_completion(context, proof)
    assert [F.history(row) for row in case.by_role["launch_local"]] == [[7]]
    assert [F.history(row) for row in case.by_role["launch"]] == [[3]]
    assert [F.history(row) for row in case.by_role["results"]] == [[2], [0]]
    assert F.history(case.by_role["annotation"][0]) == [0]
    assert F.history(case.by_role["scientific_process"][0]) == [0, 0, 0]
    assert case.store.count("annotation") == 0


def test_reconstructed_finished_workflow_replays_original_actions_and_proofs(connected_case, monkeypatch):
    case = connected_case
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", deny)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.start_prepared", deny)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.resume_start", deny)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.status", deny)
    monkeypatch.setattr("gene_annotation_episode.native_genomic_overlap_results.capture_genomic_overlap_native_files", deny)
    monkeypatch.setattr("gene_annotation_episode.native_genomic_overlap_results.prepare_genomic_overlap_worker", deny)
    monkeypatch.setattr("socket.create_connection", deny)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError("closed Workflow replay requested a new scripted/model decision")

        async def release(self, episode_id):
            pass

    with Store(case.directory / "state") as store:
        before = {table: F.rows(store, table) for table in F.TABLES}
        retained = {str(path): path.read_bytes() for path in (case.directory / "run").rglob("*.json")}
        flow, _ = F.assemble(store, case.directory, NoNewDecisions(), case.configuration)
        owner = flow.episode_bindings.for_role("results")
        proofs = []
        for original_context, original_outcome in zip(case.result_contexts, case.outcomes):
            context = owner.native_genomic_overlap_returns.context(original_context.episode_id)
            key = f"{F.RUN_ID}:{context.episode_id}:0"
            proof = owner.completion_for_action(context, key)
            replay = asyncio.run(owner.execute(context, "execution.results.collect", {}, key))
            # The ordinary runtime attaches this separate current-action field.
            expected = {k: v for k, v in original_outcome.items() if k != "pending_work_after_action"}
            assert replay == expected
            assert owner.completion_for_action(context, key) == proof
            assert owner.verify_completion(context, proof)
            proofs.append(proof)
        _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: F.rows(store, table) for table in F.TABLES} == before
        assert {str(path): path.read_bytes() for path in (case.directory / "run").rglob("*.json")} == retained
        F.write(case.directory / "REPLAY_CHECK.json", {"reopened_store": True, "new_decisions": 0,
            "new_native_or_calculation_workers": 0, "unchanged_tables": list(F.TABLES),
            "unchanged_archive": True, "original_completion_proofs": proofs})


@pytest.mark.parametrize("failure", ["invalid_c", "missing_ac_stdout"])
def test_actual_incomplete_native_results_preserve_independent_pairs_without_endpoint(tmp_path, failure):
    case = F.workflow_case(tmp_path / failure, failure=failure)
    try:
        returned, = case.returned
        projection, = returned["overlap"]
        assert not returned["completed"] and returned["failures"]
        assert projection["result_extent"] == "partial"
        by_pair = {row["comparison_key"]: row for row in projection["pair_rows"]}
        assert by_pair["AB"]["result_extent"] == "complete"
        assert by_pair["AB"]["measurements"]["unfiltered.jaccard_bp"] == {
            "numerator": 5, "denominator": 15, "value": 1/3, "missing_reason": None}
        affected = ("AC", "BC") if failure == "invalid_c" else ("AC",)
        for key in affected:
            assert by_pair[key]["result_extent"] != "complete"
            assert by_pair[key]["measurements"]["unfiltered.native_pair_count"] is None
            assert by_pair[key]["measurements"]["unfiltered.jaccard_bp"]["value"] is None
            assert by_pair[key]["issues"]
        if failure == "invalid_c":
            assert any(row["set_key"] == "C" and row["code"] == "zero_width_interval"
                for row in returned["failures"])
            batch = json.loads(case.provider.native_bytes["batch_manifest"])
            assert [row["disposition"] for row in batch["pairs"]] == ["native_succeeded", "invalid_input", "invalid_input"]
        else:
            assert by_pair["BC"]["result_extent"] == "complete"
            assert by_pair["BC"]["measurements"]["unfiltered.jaccard_bp"]["value"] == 2/13
            assert any(row["comparison_key"] == "AC" and row["code"] == "native_output_unavailable"
                for row in returned["failures"])
            assert not Path(case.provider.loss["path"]).exists()
        context, = case.result_contexts
        assert case.owner.native_genomic_overlap_results.completion(context) is None
        assert case.owner.completion_for_action(context, f"{F.RUN_ID}:{context.episode_id}:0") is None
        actions = [json.loads(row["action"]) for row in F.rows(case.store, "runtime_actions")
            if row["episode_id"] == context.episode_id]
        assert [row["tool"] for row in actions] == ["execution.results.collect", "execution.results.status"]
        observations = [row for row in F.rows(case.store, "runtime_observations") if row["episode_id"] == context.episode_id]
        assert len(observations) == 2
        # Both cases still acquired the genuine complete AB population. The
        # failed independent comparisons do not erase that actual contribution.
        assert F.history(case.by_role["results"][0]) == [2, 0]
        estimate = case.by_role["results"][0]["controller_state"]["estimate"]
        assert estimate["provenance"].get("version") != "verified_practical_endpoint_yield_v1"
        assert estimate["expected_next_gain"] != NumericBand.exact(0).as_record()
        assert len(F.worker_runs(case.directory)) == 1
        assert len(list(case.workspace.rglob("native.json"))) == 1
    finally:
        case.store.close()
