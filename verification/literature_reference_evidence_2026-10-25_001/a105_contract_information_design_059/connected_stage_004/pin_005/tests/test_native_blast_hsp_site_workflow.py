"""One actual selected reverse BLASTX -> results -> scientific-column return.

The tiny paired native invocation is authorized by 300 addendum 002. All
decisions, scientific credit and scientific continuation horizons are explicit
test fixtures; practical completion, native execution/capture, publication and
the existing Workflow/typed communication paths are production code.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.alignment_site_returns import alignment_site_fact_sources
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_blast_local import local_blast_plan
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_alignment_site_workflow import (
    BLAST, _assert_action_counts, _assert_no_private_sheet, _commission, _context,
    _controller, _descriptor, _redeliver_frozen, _run, _site_form, _snapshot,
)
from test_blast_native_execution_workflow import (
    POLICY, bound_request, child, practical_assignment, results_form, selected, selector,
)
from test_native_blast_hsp_sites import example
from test_tool_grading_child_returns import zero_fixture_credit


def test_native_blast_result_received_by_scientific_child_returns_only_selected_columns(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        request, scope = bound_request(store, "blastx")
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        resources = {"here": {"kind": "local", "workspace": str(workspace), "policy": deepcopy(POLICY),
            "native_blast": [{key: request["native_blast"][key] for key in ("program", "mode", "software")}]}}
        factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
        assignment = practical_assignment(workspace, request)
        launch = {"version": "execution_launch_assignment_v1", "requests": {"here": assignment},
            "immutable_input_versions": [], "constraints": {"allowed_resource_ids": ["here"],
                "allowed_kinds": ["local"], "allocation": deepcopy(POLICY)}}
        handoff_form = obj({"completed": {"type": "boolean", "x-source": "execution_completed"},
            "references": {"type": "array", "uniqueItems": True, "items": {"type": "string",
                "format": "reference", "x-reference-namespace": "execution_handoff"},
                "x-source": "execution_handoff_refs"}})
        result_form = results_form("pairwise_hsp")
        result_selector = selector("pairwise_hsp", rows={"offset": 0, "limit": 1},
            metrics=["paired_positions", "query_aligned_positions"])
        tools = ToolRegistry(store)
        directory = tmp_path / "run"
        descriptor, library = _descriptor(directory, tools)
        site_calculations = []
        from gene_annotation_episode import blast_hsp_site_calculators as calculators
        original_calculator = calculators.calculate_blast_hsp_column_components
        def forbidden(*args, **kwargs):
            raise AssertionError("Closed native BLAST column return attempted calculation or acquisition")
        def once(sheet):
            value = original_calculator(sheet)
            site_calculations.append(deepcopy(value))
            monkeypatch.setattr(calculators, "calculate_blast_hsp_column_components", forbidden)
            return value
        monkeypatch.setattr(calculators, "calculate_blast_hsp_column_components", once)

        class Choices:
            parent_calls = 0
            calls = []
            hsp = child_id = requested_schema = plan = result_context = None
            received_rows = None

            async def complete(self, episode_id, role, instructions, current, output_schema):
                assert not current.get("feedback"), current.get("feedback")
                self.calls.append((episode_id, role, deepcopy(current)))
                if "practical_assignment" in current:
                    assert current["practical_assignment"] == assignment
                    return selected("practical.job.start")
                execution = current.get("execution_assignment", {})
                if execution.get("version") == "execution_launch_assignment_v1":
                    return child("launch_local", assignment, scope, handoff_form)
                if execution.get("version") == RESULTS_VERSION:
                    return selected("execution.results.collect")
                if "scientific_process" in current:
                    self.child_id = episode_id
                    assert self.hsp in set(workflow.receipts.known(episode_id))
                    assert store.count("observation") == 1
                    return selected("result.blast.hsp", {"observation_ref": self.hsp,
                        "column_offset": 1, "column_limit": 4})
                self.parent_calls += 1
                if self.parent_calls == 1:
                    assert store.count("observation") == 0
                    return child("launch", launch, scope, handoff_form)
                if self.parent_calls == 2:
                    handoff, = current["child_reports"][-1]["references"]
                    target = workflow.progress_provider.job_provider.targets.read_target(handoff, scope)
                    result = await asyncio.to_thread(native.wait_job,
                        native.NativeJobHandle(Path(target["execution_id"])))
                    assert result.returncode == 0
                    self.plan = local_blast_plan(assignment, target["execution_id"])
                    return child("results", {"version": RESULTS_VERSION,
                        "handoff_ref": handoff, "selector": result_selector}, scope, result_form)
                assert self.parent_calls == 3
                self.received_rows = current["child_reports"][-1]["rows"]
                row, = self.received_rows
                self.hsp = row["observation_ref"]
                assert self.hsp in set(workflow.receipts.known(episode_id))
                assert store.get(self.hsp).get("native_blast_pairwise")
                assert "native_blast" not in store.get(self.hsp)
                self.requested_schema = _site_form(BLAST, alignment_ref=self.hsp,
                    window={"column_offset": 1, "column_limit": 4})
                fields = self.requested_schema["properties"]["selected_sites"]["items"]["properties"]
                available = alignment_site_fact_sources()[BLAST]["report_schema"]["items"]["properties"]
                for key in ("query_frame", "query_direction", "reference_direction"):
                    fields["rows"]["items"]["properties"][key] = available["rows"]["items"]["properties"][key]
                    fields["rows"]["items"]["required"].append(key)
                fields["components"]["properties"]["reference_paired_coverage"] = available["components"]["properties"]["reference_paired_coverage"]
                fields["components"]["required"].append("reference_paired_coverage")
                for target in ("blast_pairwise_results.calculate_blast_pairwise_components",
                    "blast_report_collection.parse_blast_report_collection", "native_blast_result_worker.run"):
                    monkeypatch.setattr("gene_annotation_episode." + target, forbidden)
                return _commission(library, scope, ["result.blast.hsp"],
                    [*scope["subject_refs"], self.hsp], self.requested_schema)

            async def release(self, episode_id):
                pass

        decisions = Choices()
        def services(actual_store, **kwargs):
            execution = factory(actual_store, **kwargs)
            return EpisodeApplicationServices((descriptor, *execution.episode_binding_descriptors),
                execution.role_credit_bindings, execution.job_progress_provider,
                resource_tool_catalogs=execution.resource_tool_catalogs)
        workflow = Workflow(store, tools, decisions, directory, "native-blast-column-workflow-300",
            _controller({"annotation": 3, "scientific_process": 1}), zero_fixture_credit,
            episode_service_factory=services,
            episode_service_binding={"execution": factory.as_record(), "scientific": descriptor},
            episode_service_inputs="actual_tool_registry_v1",
            annotation_child_roles=("launch", "results", "scientific_process"),
            episode_record_receipts=True, initial_known_record_refs=[])
        parent = workflow.build("annotation", "root", "Read selected translated BLAST correspondence", scope)
        assert workflow.catalog(scope, source=parent.source) == []
        record = _run(parent, workflow)
        assert record.units_consumed == 3 and len(site_calculations) == 1
        operation, = store.db.execute("SELECT * FROM tool_operations WHERE name='result.blast.hsp'").fetchall()
        outcome = json.loads(operation["result"])
        result = outcome["result"]
        retained = json.loads(store.get_artifact(result["site_grading_artifact_ref"]))
        saved = workflow.journal.row("runtime_forms", decisions.child_id)
        returned, frozen = json.loads(saved["form"]), json.loads(saved["facts"])
        assert returned["selected_sites"] == frozen[BLAST]
        example("actual_reverse_blastx_workflow", {"input_kind": "one_new_actual_local_two_sequence_execution",
            "original_plan": decisions.plan, "received_hsp_rows": decisions.received_rows,
            "returned": returned, "complete_site_grading": retained,
            "counts": {"site_actions": 1, "site_calculator_calls": len(site_calculations),
                "scientific_observations": store.count("observation"), "parent_actions": record.units_consumed},
            "scripted_decisions": decisions.calls})
        group, = returned["selected_sites"]
        assert group["alignment_ref"] == decisions.hsp
        assert group["selection_policy"] == "matching_alignment_window"
        assert group["selection"] == {"column_offset": 1, "column_limit": 4,
            "column_end": 5, "total_columns": 62, "next_column_offset": 5}
        assert [row["query_interval"] for row in group["rows"]] == [[209, 212], [206, 209], [203, 206], [200, 203]]
        assert [row["reference_interval"] for row in group["rows"]] == [[10, 11], [11, 12], [12, 13], [13, 14]]
        assert all(row["query_frame"] == -3 and row["query_direction"] == -1
            and row["reference_direction"] == 1 and row["query_unit"] == "nt"
            and row["reference_unit"] == "aa" for row in group["rows"])
        assert group["components"]["paired_columns"] == 4
        assert group["components"]["identical_pairs"] == 4
        assert group["components"]["paired_identity"] == {"value": 1, "numerator": 4, "denominator": 4, "unit": "fraction"}
        assert group["components"]["query_paired_coverage"] == {"value": 12/244, "numerator": 12, "denominator": 244, "unit": "fraction"}
        assert group["components"]["reference_paired_coverage"] == {"value": 4/80, "numerator": 4, "denominator": 80, "unit": "fraction"}
        assert outcome["record_refs"] == [] and store.count("observation") == 1
        assert store.count("annotation") == 0
        assert len(list(workspace.rglob("blast-plan.json"))) == 1
        _assert_no_private_sheet(returned)
        _assert_action_counts(store, decisions.child_id, 1)
        _assert_action_counts(store, parent.source.episode_id, 3)
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 7
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 7
        before = _snapshot(store)
        assert tools.execute("result.blast.hsp", json.loads(operation["arguments"]), scope=scope,
            operation_key=operation["operation_key"], permitted_record_refs=[decisions.hsp]) == outcome
        workflow.receive_form(parent.source, returned, decisions.requested_schema, 2, redelivery=True)
        assert _snapshot(store) == before
        monkeypatch.setattr(WorkflowServices, "alignment_site_own_action_results", forbidden)
        workflow.scientific_process_binding.validate_report(_context(workflow, decisions.child_id),
            returned, decisions.requested_schema)
        _redeliver_frozen(workflow, parent, decisions.child_id, decisions.requested_schema, returned, 3)
        changed = deepcopy(returned)
        changed["selected_sites"][0]["components"]["paired_columns"] += 1
        with pytest.raises(ValueError, match="frozen_source_mismatch"):
            workflow.scientific_process_binding.validate_report(_context(workflow, decisions.child_id),
                changed, decisions.requested_schema)
        assert _snapshot(store) == before
