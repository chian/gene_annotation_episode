"""End-to-end A101 investigations of invented contrasting functional cases."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.a101_investigation import resolve_report
from gene_annotation_episode.state import Store
from a101_subtree_fixture import Scenario, InterruptedAfterSubmission


@pytest.mark.parametrize("fragment", [False, True], ids=["misleading-close-homolog", "unseen-required-site"])
def test_a101_subtree_returns_auditable_functional_distinctions(tmp_path, fragment):
    with Store(tmp_path / "state") as store:
        case = Scenario(tmp_path, store, fragment=fragment)
        try:
            record = asyncio.run(case.run())
            report = case.received
            resolved = resolve_report(store, report, scope=case.scope)
            assert resolved["claims"]["family"]["status"] == "supported"
            assert resolved["claims"]["activity"]["status"] == "limited"
            assert resolved["claims"]["specificity"]["status"] == ("unresolved" if fragment else "limited")
            assert resolved["claims"]["physiological_role"]["status"] == "not_assessed"
            assert len(resolved["alternatives"]) == 2
            assert len(report["changed_assessment_refs"]) == 3
            assert record.controller_state.current_credit == 3
            assert store.count("annotation") == 0
            assert store.count("interpretation_account") == 1
            assert len(store.targets()) == 1
            assert len(case.comparisons) == 2
            assert {case.native_sources[k]["native_identifier"] for k in ("A", "B")} == {"RefA", "RefB"}
            a = store.get(case.comparisons["A"])
            b = store.get(case.comparisons["B"])
            measurements = lambda row: {m["name"]: m["value"].get("value") for m in row["measurements"]}
            assert {"bitscore", "evalue", "identity_fraction", "query_coverage", "target_coverage"} <= set(measurements(a))
            assert measurements(a)["identity_fraction"] > measurements(b)["identity_fraction"]
            assert case.jobs.db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
            assert case.jobs.db.execute("SELECT sum(submission_requested) FROM orders").fetchone()[0] == 1
            assert case.native_pages[1]["changed_record_refs"] == []
            sites = {group["alignment_ref"]: group for group in case.forms["features"]["sites"]}
            row = sites[case.comparisons["A"]]["rows"][0]
            assert row["reference_position"] == 60
            if fragment:
                assert row["relationship"] == "outside_alignment" and row["query_position"] is None
                assert "unobserved_feature" in report["limitations"]
            else:
                assert row["relationship"] == "substituted"
                assert (row["reference_symbol"], row["query_symbol"]) == ("H", "Q")
                assert "incompatible_feature" in report["limitations"]
            # The assayed molecule remains a source subject, separately linked
            # to the search reference; it never becomes an annotation target.
            experiment = store.get(case.extracted["experimentB"])
            assert store.get(experiment["source_subject_refs"][0])["label"] == "ConstructB"
            assert case.references["B"] in experiment["dependencies"]
            assert experiment["subject_refs"] != [case.target]
            assert case.extracted["conditions"] in experiment["dependencies"]
            actions = [json.loads(row[0]) for row in store.db.execute("SELECT action FROM runtime_actions")]
            assert any(a.get("tool") == "process.revise" for a in actions)
            assert any(a.get("tool") == "progress.observe" for a in actions)
            monitor = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='monitor'").fetchone()[0]
            monitoring_credit = [row[0] for row in store.db.execute(
                "SELECT credit FROM runtime_actions WHERE episode_id=? ORDER BY decision_index", (monitor,))]
            assert len(monitoring_credit) == 2 and monitoring_credit[1] == monitoring_credit[0]
            assert report["observations_after_report_basis"] == []
            # Redelivery reuses the frozen child form without another search,
            # interpretation, source read, controller observation or provider.
            before = {table: store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in ("runtime_actions", "runtime_observations", "records")}
            calls_before = len(case.frames)
            saved = deepcopy(report)
            attempt = store.db.execute("SELECT delivery_ref,contract FROM runtime_report_attempts WHERE parent_episode_id=? ORDER BY decision_index LIMIT 1",
                (case.root.source.episode_id,)).fetchone()
            declaration = json.loads(attempt["contract"])
            replay = case.flow.redeliver(case.root.source, {"delivery_ref": attempt["delivery_ref"],
                "schema_json": json.dumps(declaration["measurements"]["schema"]),
                "purpose": declaration["decision"]}, 2)
            assert replay.failure is None and replay.report.as_record() == saved
            assert len(case.frames) == calls_before
            assert before == {table: store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in before}
        finally:
            case.jobs.close()


def test_a101_missing_traceback_returns_partial_findings_and_preserves_native_scores(tmp_path):
    from gene_annotation_episode.a101_investigation import A101Subtree, initial_report
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
    from a101_subtree_fixture import PUBLICATION, action, reasoning

    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")["subject_refs"]
        artifact = store.artifact(json.dumps({"fixture": "retained summary without original traceback", "bitscore": 43}))
        source = store.put("source", {"provider": "retained_alignment_summary_fixture", "accession": "summary",
            "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
            "version": "1", "retrieved_at": None}, origin="caller")["id"]
        reference = store.put("reference", {"reference_type": "protein", "source_ref": source,
            "accession": "SummaryReference", "label": "SummaryReference", "sequence_ref": None,
            "molecule": "protein", "length": 100, "term_refs": [], "context_refs": []}, origin="external")["id"]
        comparison = store.put("observation", {"subject_refs": [target], "source_subject_refs": [reference],
            "kind": "alignment", "source_ref": source, "measurements": [{"name": "bitscore",
                "value": {"type": "number", "value": 43, "unit_ref": None}}], "dependencies": [reference],
            "anchor": None}, origin="external")["id"]
        scope = {"subject_refs": [target]}
        tools, directory = ToolRegistry(store), tmp_path / "run"
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process",))
        subtree, calls = A101Subtree(directory), {}
        received, outcomes = [], []

        class Choices:
            async def complete(self, episode_id, role, instructions, current, schema):
                index = calls.get(episode_id, 0)
                calls[episode_id] = index + 1
                if "scientific_process" not in current:
                    assert not current.get("feedback"), current.get("feedback")
                    if index == 0:
                        return {"selection": subtree.commission(store, target_ref=target, scope=scope,
                            completeness="fragment", child_tool_info=[{"name": name, "resources": "local"}
                                for name in ("sequence.sites", "state.query")],
                            question="Determine what survives when a retained comparison has no original traceback.",
                            evidence_refs=[comparison]), "report_update": {}}
                    received.append(current["child_reports"][-1])
                    return reasoning(store, hypotheses=[{"alias": "unresolved_family",
                        "subject_refs": [target], "predicate": "functional_family",
                        "value": {"type": "enum", "value": "unresolved"}, "context_refs": []}])
                if index == 0:
                    return action("sequence.sites", {"alignment_ref": comparison, "positions": [5]}, initial_report())
                if current.get("last_local_outcome"):
                    outcomes.append(deepcopy(current["last_local_outcome"]))
                report = initial_report()
                report["limitations"] = ["fragment_input", "missing_traceback", "unobserved_feature"]
                return action("state.query", {"kind": "observation", "limit": 10, "offset": 0}, report)
            async def release(self, episode_id):
                pass

        def controller(path, initial):
            def estimate(history, parameters, contexts):
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1),
                    parameters, {"fixture": "two_completed_actions"})
            return YieldController(str(path), initial, 0, estimate_with_context=estimate)
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        flow = Workflow(store, tools, Choices(), directory, "a101-missing-traceback", controller, progress,
            project_child_credit=progress, episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[comparison])
        root = flow.build("annotation", "root", "Investigate the supplied incomplete comparison.", scope)
        async def run():
            record = await root.run_async(flow.context)
            await root.build_result(record)
            return record
        record = asyncio.run(run())
        assert "missing_traceback" in received[0]["limitations"]
        assert all(value["status"] == "not_assessed" for value in resolve_report(store, received[0], scope=scope)["claims"].values())
        assert store.get(comparison)["measurements"][0]["value"]["value"] == 43
        assert store.count("observation") == 1 and record.controller_state.current_credit == 0
        assert any(outcome["status"] in {"failed", "invalid"} for outcome in outcomes)
        assert any("native_alignment_site_mapping_unavailable" in json.dumps(outcome) for outcome in outcomes)


def test_a101_preserves_partial_acquisition_without_claiming_exact_function(tmp_path):
    with Store(tmp_path / "state") as store:
        case = Scenario(tmp_path, store, partial=True)
        try:
            record = asyncio.run(case.run())
            report = case.received
            resolved = resolve_report(store, report, scope=case.scope)
            assert all(row["status"] == "not_assessed" for row in resolved["claims"].values())
            assert "partial_acquisition" in report["limitations"]
            assert any(store.get(ref)["record_type"] == "observation" for ref in report["records"])
            assert not store.current_assessments() and record.controller_state.current_credit == 0
            result_id, = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='results'").fetchone()
            form = json.loads(case.flow.journal.row("runtime_forms", result_id)["form"])
            assert form["coverage"]["all_parsed_rows_acquired"] is False
            assert form["coverage"]["native_result_complete"] is True
        finally:
            case.jobs.close()


def test_a101_interrupted_submission_resumes_same_subtree_and_native_job(tmp_path):
    with Store(tmp_path / "state") as store:
        case = Scenario(tmp_path, store)
        case.interrupt_once = True
        try:
            with pytest.raises(InterruptedAfterSubmission):
                asyncio.run(case.run())
            assert case.jobs.db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
            assert case.jobs.db.execute("SELECT sum(submission_requested) FROM orders").fetchone()[0] == 1
            asyncio.run(case.run())
            assert resolve_report(store, case.received, scope=case.scope)["claims"]["family"]["status"] == "supported"
            assert case.jobs.db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
            assert case.jobs.db.execute("SELECT sum(submission_requested) FROM orders").fetchone()[0] == 1
        finally:
            case.jobs.close()
