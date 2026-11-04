"""Selected child operations deliver numerical records through real typed forms.

Choices and continuation estimates are explicit engineering fixtures. Native
local algorithms are real. The API BLAST case uses the existing offline provider
fixture; it submits no external job and establishes no live API availability.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.blast_database_grader import calculate_database_probabilities
from gene_annotation_episode.blast_result_views import BLAST_HSP_FACT_SCHEMA, blast_hsp_facts
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_blast_service import Client
from test_api_service_integration import assignment
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_published_axis_workflow import PUBLICATION, ScriptedDecisions, select
from test_tool_grading_publication import gene_input, numerical, only_grading, operation_count, quality_library


RETURN_FORM = {"type": "object", "additionalProperties": False,
    "properties": {"records": {"type": "array", "items": {"type": "string", "format": "reference"},
        "x-source": "committed_record_refs",
        "description": "Records actually returned by this child's completed selected operation."}},
    "required": ["records"]}


def zero_fixture_credit(*args, **kwargs):
    """No scientific scoring policy is asserted by communication verification."""
    return 0


zero_fixture_credit.requires_episode_receipts = True


def fixed_completion_estimate(path, initial):
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if history else 1), parameters,
                             {"fixture": "one_selected_action_per_episode"})
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


@pytest.mark.parametrize("operation,molecule,alignment_mode", [
    *[(operation, "dna", "global") for operation in
      ("sequence.align", "genes.predict", "sequence.inspect", "reads.inspect", "reads.align")],
    ("sequence.align", "dna", "local"),
    ("sequence.align", "rna", "local"), ("sequence.align", "rna", "global"),
    ("sequence.align", "protein", "local"), ("sequence.align", "protein", "global"),
])
def test_selected_scientific_child_returns_qualified_numbers_as_one_parent_action(
        tmp_path, operation, molecule, alignment_mode):
    with Store(tmp_path / "state") as store:
        tools = ToolRegistry(store)
        if operation.startswith("reads."):
            target, reads, _ = quality_library(store, tmp_path)
            supplied = [target, *(row["id"] for row in reads)]
            args = {"subject_refs": [row["id"] for row in reads]}
            if operation == "reads.align":
                args.update(reference_ref=reads[0]["id"], molecule="dna", mode="global")
            sequence = None
        else:
            region = (gene_input() if operation == "genes.predict" else
                      {"dna": "ACGTTGCA", "rna": "ACGUUGCA", "protein": "MACDEFGH"}[molecule])
            sequence = "N" * 13 + region + "N" * 11 if operation == "genes.predict" else region
            target, = store.create_problem(raw_sequence=sequence, molecule=molecule)["subject_refs"]
            supplied = [target]
            args = ({"query_ref": target, "reference_ref": target, "molecule": molecule, "mode": alignment_mode}
                    if operation == "sequence.align" else
                    {"subject_ref": target, "code": 11, "mode": "meta", "start": 13, "end": 319}
                    if operation == "genes.predict" else {"subject_ref": target})
        scope = store.validate_scope({"subject_refs": [target]})
        directory = tmp_path / "run"
        descriptor = prepare_scientific_binding(run_directory=directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(), child_roles=("scientific_process",))
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        commission = {"kind": "episode_child", "role": "scientific_process",
            "goal": "Measure the supplied sequence material with the assigned native operation.",
            "scope": scope, "purpose": "Return the recorded native numerical evidence, with function unresolved.",
            "schema_json": json.dumps(RETURN_FORM), "initial_report_json": "{}",
            "assignment": {"selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": operation, "resources": "local"}]},
                "evidence_refs": supplied, "constraints": {"no_external_acquisition": True},
                "context": {"molecule": molecule, "supplied_sequence": sequence}}}
        decisions = ScriptedDecisions([select(commission),
            select({"kind": "tool", "tool": operation, "arguments": args})])
        workflow = Workflow(store, tools, decisions, directory, "b001-" + operation,
            fixed_completion_estimate, zero_fixture_credit, episode_binding_descriptors=[descriptor],
            episode_record_receipts=True, initial_known_record_refs=[], decision_protocol="decision_exchange_v1")
        root = workflow.build("annotation", "root", "Investigate the supplied unnamed sequence", scope)
        assert workflow.catalog(scope, source=root.source) == []
        assert not workflow.permits_common_action(root.source, "tool")
        assert list(workflow.receipts.known(root.source.episode_id, record_type="observation")) == []
        parent_info, = [row for row in workflow.scientific_process_binding.tool_library.parent_tool_info()
                       if row["name"] == operation and row["resources"] == "local"]
        assert set(parent_info) == {"name", "description", "resources"}
        assert parent_info["description"] == tools.catalog()[operation]["description"]

        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        assert record.units_consumed == 1
        root_id = root.source.episode_id
        child_id = decisions.calls[1]["episode_id"]
        child_info, = decisions.calls[1]["state"]["scientific_process"]["child_tool_info"]
        assert {key: child_info[key] for key in parent_info} == parent_info
        guidance_file = ("pairwise-correspondence.md" if operation.endswith("align") else
                         "gene-prediction.md" if operation == "genes.predict" else
                         "sequence-read-composition.md")
        guidance = (PUBLICATION.parents[3] / "gene_annotation_episode/knowledge" / guidance_file).read_text().strip()
        assert guidance in child_info["instructions"]
        assert set(child_info) == {"name", "description", "resources", "instructions"}
        returned = json.loads(workflow.journal.row("runtime_forms", child_id)["form"])
        publication_row = store.db.execute("SELECT * FROM tool_operations WHERE name=?", (operation,)).fetchone()
        publication = json.loads(publication_row["result"])
        assert publication["status"] == "completed", publication
        assert returned == {"records": publication["record_refs"]}
        root_receipts = set(workflow.receipts.known(root_id))
        assert set(returned["records"]) <= root_receipts
        observations = [store.get(ref) for ref in returned["records"] if store.get(ref)["record_type"] == "observation"]
        assert len(observations) == (2 if operation.startswith("reads.") else 1)
        assert {row["id"] for row in observations} <= set(workflow.receipts.known(root_id, record_type="observation"))
        state = workflow.working_state(root.source)
        assert {row["id"] for row in state["observations"]} == {row["id"] for row in observations}
        for observation in observations:
            source = store.get(observation["source_ref"])
            assert source["id"] in root_receipts
            grading = only_grading(store, source["id"])
            assert grading
            values = numerical(observation)
            if operation.endswith("align"):
                assert values["paired_positions"] == 8 and values["paired_identity"] == 1
                if operation == 'sequence.align':
                    assert grading['sheet']['mode'] == alignment_mode
                    assert grading['sheet']['molecule'] == molecule
                    assert {span['model_unit'] for span in observation['operand_intervals']} == {
                        'aa' if molecule == 'protein' else 'nt'}
            elif operation == "genes.predict":
                assert values["start"] == 15 and values["end"] == 318
                assert values["interval_length_nt"] == 303 and values["protein_length_aa"] == 101
                assert grading["sheet"]["input_start"] == 13
            else:
                assert values["gc_count"] == 4 and values["gc_denominator"] == 8
        if operation == "reads.inspect":
            by_subject = {row["subject_refs"][0]: numerical(row) for row in observations}
            assert by_subject[reads[0]["id"]]["mean_phred"] == 35
            assert by_subject[reads[1]["id"]]["mean_phred"] == 0
        # Admission carries typed records, never the full source auxiliary sheets.
        presented = json.dumps(state)
        for full_sheet_key in ("native_result", "measured_column_counts", "quality_measurements",
                               "biopython_pairwise_sheet_v1", "prodigal_sheet_v1"):
            assert full_sheet_key not in presented
        for episode_id in (root_id, child_id):
            assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
            assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
        assert len(decisions.calls) == 2  # No grader or result-composer model call.
        assert operation_count(store, operation) == 1 and store.count("annotation") == 0
        before = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")]
        receipt_count = store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0]
        # Exact saved operation replay and repeated admitted return do no work.
        assert tools.execute(operation, args, scope=scope, operation_key=publication_row["operation_key"]) == publication
        root_action = store.db.execute("SELECT decision_index FROM runtime_actions WHERE episode_id=?", (root_id,)).fetchone()[0]
        workflow.receive_form(root.source, returned, RETURN_FORM, root_action, redelivery=True)
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == receipt_count
        assert [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")] == before
        assert store.count("observation") == len(observations) and operation_count(store, operation) == 1


def test_offline_api_blast_full_grading_and_original_hsp_typed_return_are_retained(tmp_path):
    class Responses(Client):
        fetched = None
        def blast(self, action, **arguments):
            response = super().blast(action, **arguments)
            if action == "fetch":
                body = json.loads(response.content)
                hsp = body["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]
                hsp.update(qseq="MACDEFGH", hseq="MACAEFGH", midline="||| ||||")
                response = replace(response, content=json.dumps(body).encode())
                self.fetched = response.content
            return response

    client = Responses()
    resources = {"blast": {"kind": "api", "service": "ncbi_blast"}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5)
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]
        scope = {"subject_refs": [target]}
        request = assignment("blast", "ncbi_blast", {"subject_ref": target, "program": "blastp", "database": "swissprot"})
        launch = launch_assignment({"blast": request})
        handoff_form = form("execution_handoff_refs")
        result_form = {"type": "object", "additionalProperties": False,
            "properties": {"complete": {"type": "boolean", "x-source": "execution_completed"},
                "matches": {**deepcopy(BLAST_HSP_FACT_SCHEMA), "x-source": "execution_blast_hsps"}},
            "required": ["complete", "matches"]}

        class Choices:
            calls = 0
            handoff = None
            async def complete(self, episode_id, role, instructions, current, schema):
                assert not current.get("feedback"), current.get("feedback")
                execution = current.get("execution_assignment", {})
                if execution.get("version") == "execution_launch_assignment_v1":
                    return child("launch_api", request, scope, handoff_form)
                if execution.get("version") == "api_service_assignment_v1":
                    return selected("api.blast.submit")
                if execution.get("version") == "execution_results_assignment_v1":
                    return selected("api.blast.fetch")
                self.calls += 1
                if self.calls == 1:
                    return child("launch", launch, scope, handoff_form)
                assert self.calls == 2
                self.handoff, = current["child_reports"][-1]["references"]
                return child("results", {"version": "execution_results_assignment_v1",
                    "handoff_ref": self.handoff, "selector": {}}, scope, result_form)
            async def release(self, episode_id):
                pass

        def controller(path, initial):
            if path[-1][0] != "annotation":
                return YieldController(str(path), initial, 0)
            def estimate(history, parameters, contexts):
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1),
                                     parameters, {"fixture": "two_parent_commissions"})
            return YieldController(str(path), initial, 0, estimate_with_context=estimate)

        workflow = Workflow(store, ToolRegistry(store, clients=client), Choices(), tmp_path / "run",
            "b001-offline-blast", controller_factory=controller, project_credit=zero_fixture_credit,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs="actual_tool_registry_v1", annotation_child_roles=("launch", "results"),
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build("annotation", "root", "Obtain native BLAST measurements", scope)
        assert workflow.catalog(scope, source=root.source) == []
        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record
        record = asyncio.run(run())
        assert record.units_consumed == 2
        row = store.db.execute("SELECT episode_id,path,request FROM runtime_episodes WHERE run_id=? "
            "AND json_extract(path,'$[#-1][0]')='results'", (workflow.run_id,)).fetchone()
        returned = json.loads(workflow.journal.row("runtime_forms", row["episode_id"])["form"])
        match, = returned["matches"]
        assert returned["complete"] is True
        assert match == {"hsp_ref": match["hsp_ref"], "reference_ref": match["reference_ref"],
            "bitscore": 31.5, "alignment_score": 60.0, "evalue": 1e-5,
            "query_coverage": 1.0, "target_coverage": 1.0, "identity_fraction": .75}
        observation = store.get(match["hsp_ref"])
        source = store.get(observation["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == client.fetched
        grading = only_grading(store, source["id"])
        assert grading["sheet"] and "probabilities" in grading
        assert calculate_database_probabilities(json.loads(json.dumps(grading["sheet"]))) == grading["probabilities"]
        assert blast_hsp_facts(store, [match["hsp_ref"]]) == returned["matches"]
        known = tuple(workflow.receipts.known(root.source.episode_id))
        assert match["hsp_ref"] in known and match["reference_ref"] in known
        assert store.count("observation") == 1 and store.count("annotation") == 0
        assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (row["episode_id"],)).fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?", (row["episode_id"],)).fetchone()[0] == 1
        assert [name for name, _ in client.calls] == ["submit", "fetch"]
        original = json.loads(row["request"])
        context = BindingContext(workflow.run_id, row["episode_id"], "results",
            tuple(tuple(part) for part in json.loads(row["path"])), scope,
            original["message"]["episode_assignment"], original)
        reopened = ExecutionEpisodes(None, store=store, directory=tmp_path / "run", run_id=workflow.run_id,
            resources=resources, initial_information={}, tool_registry=workflow.tools,
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=8192, log_roles=("stdout", "stderr"))
        reopened.validate_report(context, returned, result_form)
        assert reopened.facts(context, {})["execution_blast_hsps"] == returned["matches"]
        assert [name for name, _ in client.calls] == ["submit", "fetch"]
        assert store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0
