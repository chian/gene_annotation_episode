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


def test_genuine_single_prediction_child_publishes_and_returns_all_candidate_numbers(tmp_path, monkeypatch):
    """One real single-model worker call; choices and zero credit are fixtures.

    A103 supplies existing preparatory coding-context guidance. P11 preserves
    the distinction between possible coding capacity and demonstrated native
    use; this control does not establish its biological alternatives. Neither
    the FASTA title nor predictions verify genome identity, actual neighbors,
    expression, function or calibrated annotation accuracy.
    """
    import hashlib
    import os
    from pathlib import Path
    import traceback

    from gene_annotation_episode.prodigal_grader import calculate_prodigal_scores
    from gene_annotation_episode.sequence_mapping import VERSION as MAPPING_VERSION
    from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries

    if os.environ.get("HMMER_NATIVE_ORACLE_PRODIGAL_SINGLE_CHILD") != "1":
        pytest.skip("explicit selected native single-model child verification only")
    data = Path(__file__).resolve().parents[1] / "verification/tool_graders_batch_001/prodigal"
    input_path, reference_path = data / "single.input.fna", data / "single.native.json"
    input_bytes, reference_bytes = input_path.read_bytes(), reference_path.read_bytes()
    input_sha = hashlib.sha256(input_bytes).hexdigest()
    reference_sha = hashlib.sha256(reference_bytes).hexdigest()
    assert input_sha == "07cc14da390e0616418b0973f61b8c4386c87bf097b3e88a92a42227c9b6f93b"
    assert reference_sha == "f2714264a204c3b93c2f426aafe269111d48443e987708efd2478a011be88f39"
    region = "".join(line for line in input_bytes.decode("ascii").splitlines() if not line.startswith(">"))
    reference = json.loads(reference_bytes)
    assert len(region) == 100000 and len(reference["candidates"]) == 103
    offset = 13
    capture = {"schema": "prodigal_single_child_return_verification_v1",
        "qualification": "one genuine single-mode child operation on a retained numerical control; scripted choices and zero credit do not establish biological truth or a model investigation",
        "biological_limits": ["genome_identity_not_independently_verified", "actual_neighbors_unestablished",
            "coding_candidates_not_function_or_native_use", "native_confidence_not_annotation_accuracy"],
        "input_file": {"path": str(input_path), "sha256": input_sha, "size_bytes": len(input_bytes)},
        "retained_native_reference": {"path": str(reference_path), "sha256": reference_sha,
            "size_bytes": len(reference_bytes), "meaning": "previously retained native result, not another execution in this case"},
        "worker_calls": []}
    failure = None
    try:
        with Store(tmp_path / "state") as store:
            target, = store.create_problem(raw_sequence="N" * offset + region + "N" * 11,
                molecule="dna")["subject_refs"]
            scope = store.validate_scope({"subject_refs": [target]})
            tools = ToolRegistry(store)
            original_worker = tools._sequence_worker_async

            async def observe_genuine_worker(operation, arguments, *, directory):
                assert not store.db.in_transaction
                assert operation == "predict_genes"
                assert arguments == {"sequence": region, "code": 11, "mode": "single"}
                call = {"operation": operation, "arguments": deepcopy(arguments)}
                capture["worker_calls"].append(call)
                work = await original_worker(operation, arguments, directory=directory)
                native_bytes = work.output_path.read_bytes()
                call.update(native_result=json.loads(native_bytes),
                    native_output_text=native_bytes.decode("utf-8"),
                    native_bytes_sha256=hashlib.sha256(native_bytes).hexdigest(),
                    native_byte_length=len(native_bytes), local_job=deepcopy(work.metadata))
                return work

            monkeypatch.setattr(tools, "_sequence_worker_async", observe_genuine_worker)
            directory = tmp_path / "run"
            descriptor = prepare_scientific_binding(run_directory=directory,
                source_directory=PUBLICATION, tool_catalog=tools.catalog(), child_roles=("scientific_process",))
            library = ScientificProcessLibrary(directory / "scientific-process-library")
            commission = {"kind": "episode_child", "role": "scientific_process",
                "goal": "Measure coding-region candidates in the supplied control interval under the chosen single-genome prediction model.",
                "scope": scope, "purpose": "Return actual candidate measurements and coordinates; genome context and function remain unresolved.",
                "schema_json": json.dumps(RETURN_FORM), "initial_report_json": "{}",
                "assignment": {"selection": {"version": "scientific_process_selection_v3",
                    "evidence_axis": library.reference("A103"), "thought_pattern": library.reference("P11"),
                    "child_tool_info": [{"name": "genes.predict", "resources": "local"}]},
                    "evidence_refs": [target], "constraints": {"no_external_acquisition": True,
                        "selected_native_model": {"mode": "single", "code": 11,
                            "input_interval": [offset, offset + len(region)]}},
                    "context": {"molecule": "dna", "preparatory_coding_context_only": True,
                        "sequence_origin": "retained native numerical control; its title is not verified genome identity",
                        "actual_genome_and_neighbors": "unestablished", "function_and_native_use": "unresolved"}}}
            arguments = {"subject_ref": target, "code": 11, "mode": "single",
                "start": offset, "end": offset + len(region)}
            selections = [select(commission), select({"kind": "tool", "tool": "genes.predict", "arguments": arguments})]
            assert all(row["response"]["report_update"] == {} for row in selections)
            decisions = ScriptedDecisions(selections)
            workflow = Workflow(store, tools, decisions, directory, "prodigal-single-child-return",
                fixed_completion_estimate, zero_fixture_credit, episode_binding_descriptors=[descriptor],
                episode_record_receipts=True, initial_known_record_refs=[], decision_protocol="decision_exchange_v1")
            root = workflow.build("annotation", "root", "Inspect candidate coding regions in the supplied material", scope)
            assert workflow.catalog(scope, source=root.source) == []
            assert not workflow.permits_common_action(root.source, "tool")
            assert list(workflow.receipts.known(root.source.episode_id, record_type="observation")) == []

            async def run():
                record = await root.run_async(workflow.context)
                result = await root.build_result(record)
                return record, result.as_record()

            record, result = asyncio.run(run())
            assert record.units_consumed == 1 and result["credit"] == 0
            assert len(decisions.calls) == 2 and len(capture["worker_calls"]) == 1
            root_id, child_id = root.source.episode_id, decisions.calls[1]["episode_id"]
            process = decisions.calls[1]["state"]["scientific_process"]
            axis, thought = library.resolve(library.reference("A103")), library.resolve(library.reference("P11"))
            assert process["evidence_axis"]["id"] == "A103"
            assert process["evidence_axis"]["investigation_instructions"] == axis["investigation_instructions"]
            assert process["thought_pattern"]["id"] == "P11"
            assert process["thought_pattern"]["decision_guidance"] == thought["decision_guidance"]
            child_info, = process["child_tool_info"]
            parent_info, = [row for row in workflow.scientific_process_binding.tool_library.parent_tool_info()
                if row["name"] == "genes.predict" and row["resources"] == "local"]
            assert {key: child_info[key] for key in parent_info} == parent_info
            assert parent_info["description"] == tools.catalog()["genes.predict"]["description"]
            guidance = (Path(__file__).resolve().parents[1] / "gene_annotation_episode/knowledge/gene-prediction.md").read_text().strip()
            assert guidance in child_info["instructions"]
            assert set(child_info) == {"name", "description", "resources", "instructions"}
            publication_row, = store.db.execute("SELECT * FROM tool_operations WHERE name='genes.predict'").fetchall()
            publication = json.loads(publication_row["result"])
            capture["publication"] = publication
            assert publication["status"] == "completed", publication
            assert json.loads(publication_row["arguments"]) == arguments
            assert publication["result"]["count"] == publication["published_batch"]["published_rows_total"] == 103
            assert publication["result"]["preview_limit"] == len(publication["result"]["records"]) == 12
            assert publication["result"]["more_records_available_through_state_query"] is True
            source = store.get(publication["result"]["source_ref"])
            source_bytes = store.get_artifact(source["artifact_ref"])
            published_native = json.loads(source_bytes)
            grading_entry, = source_tool_grading_entries(store, source["id"])
            grading = grading_entry["grading"]
            sheet, scores = grading["sheet"], grading["scores"]
            raw = capture["worker_calls"][0]["native_result"]
            # The old control is a retained comparator, never an injected worker
            # output or a second native baseline invocation in this test.
            assert raw == reference
            assert raw["mode"] == sheet["mode"] == "single" and raw["pyrodigal_version"] == "3.7.1"
            assert sheet["native_result"] == raw and sheet["input_length"] == 100000
            assert sheet["input_start"] == offset and sheet["input_interval"] == [13, 100013]
            assert sheet["translation_code"] == 11 and sheet["status"] == "complete"
            assert json.loads(store.get_artifact(grading_entry["artifact_ref"])) == {
                "schema": "tool_grading_artifact_v1", "provider": "genes.predict",
                "native_artifact_ref": source["artifact_ref"], "grading": grading}
            assert published_native["input_interval"] == [13, 100013]
            assert published_native["mapping_version"] == MAPPING_VERSION
            assert published_native["subject_ref"] == target
            assert published_native["local_job"] == capture["worker_calls"][0]["local_job"]
            assert published_native["omitted_terminal_stop"] is False
            assert {key: published_native[key] for key in raw if key != "candidates"} == {
                key: value for key, value in raw.items() if key != "candidates"}
            returned_row = workflow.journal.row("runtime_forms", child_id)
            returned, frozen_facts = json.loads(returned_row["form"]), json.loads(returned_row["facts"])
            assert returned == {"records": publication["record_refs"]}
            assert frozen_facts["committed_record_refs"] == returned["records"]
            assert len(returned["records"]) == 311
            received = set(workflow.receipts.known(root_id))
            assert set(returned["records"]) <= received
            observation_refs = [reference for reference in returned["records"]
                if store.get(reference)["record_type"] == "observation"]
            assert len(observation_refs) == 103
            assert set(observation_refs) <= set(workflow.receipts.known(root_id, record_type="observation"))
            observations, expected_values = [], {}
            for index, (original, shifted, populated, calculated, observation_ref) in enumerate(zip(
                    raw["candidates"], published_native["candidates"], sheet["candidates"],
                    scores["candidates"], observation_refs, strict=True)):
                interval = [original["start"], original["end"]]
                parent_interval = [original["start"] + offset, original["end"] + offset]
                assert shifted == {**original, "start": parent_interval[0], "end": parent_interval[1]}
                assert populated["native_candidate"] == original
                assert populated["candidate_index"] == calculated["candidate_index"] == index
                assert populated["relative_interval"] == calculated["relative_interval"] == interval
                assert populated["parent_interval"] == calculated["parent_interval"] == parent_interval
                assert populated["native_frame"] is None
                observation = store.get(observation_ref)
                feature, product = (store.get(reference) for reference in observation["subject_refs"])
                assert observation["kind"] == "gene_prediction" and observation["source_ref"] == source["id"]
                assert feature["record_type"] == "feature" and feature["subject_ref"] == target
                assert feature["segments"] == [{"start": parent_interval[0], "end": parent_interval[1]}]
                assert feature["strand"] == original["strand"]
                assert product["record_type"] == "product" and product["parent_refs"] == [feature["id"]]
                assert product["molecule"] == "protein"
                protein = original["protein_sequence"]
                assert store.get_artifact(product["sequence_ref"]).decode("ascii") == protein
                values = {"genetic_code": 11, "start": parent_interval[0], "end": parent_interval[1],
                    "native_confidence": original["native_confidence"], "model_score": original["native_score"],
                    "interval_length_nt": original["end"] - original["start"],
                    "protein_length_aa": len(protein) - protein.count("*"),
                    "internal_stop_count": protein[:-1].count("*"), "terminal_stop_count": int(protein.endswith("*"))}
                assert numerical(observation) == values
                assert calculated["native_score"] == values["model_score"]
                assert calculated["native_confidence_percent"] == values["native_confidence"]
                assert calculated["interval_length_nt"] == values["interval_length_nt"]
                assert calculated["protein_length_aa"] == values["protein_length_aa"]
                assert calculated["internal_stop_count"] == values["internal_stop_count"]
                assert calculated["terminal_stop_count"] == values["terminal_stop_count"]
                observations.append(observation)
                expected_values[observation_ref] = values
            covered = {position for row in raw["candidates"] for position in range(row["start"], row["end"])}
            assert len(covered) == scores["summary"]["union_coding_bases"] == 85743
            assert scores["summary"]["coding_coverage"] == 85743 / 100000
            assert scores["summary"]["coding_coverage_denominator_nt"] == 100000
            assert scores["summary"]["reported_candidate_count"] == 103
            assert scores["summary"]["partial_candidate_count"] == 2
            assert scores["summary"]["coverage_complete_for_reported_candidates"] is True
            assert {row["strand"] for row in scores["candidates"]} == {"+", "-"}
            assert expected_values[observation_refs[0]]["start"] == 13
            assert expected_values[observation_refs[0]]["end"] == 1672
            assert expected_values[observation_refs[0]]["protein_length_aa"] == 552
            assert expected_values[observation_refs[-1]]["start"] == 99829
            assert expected_values[observation_refs[-1]]["end"] == 100012
            assert expected_values[observation_refs[-1]]["protein_length_aa"] == 60
            state = workflow.working_state(root.source)
            # Ordinary presentation can be bounded. All refs are admitted, but
            # this case does not claim all 103 rows occur in one model prompt.
            assert state["observations"]
            for presented in state["observations"]:
                assert presented["id"] in observation_refs and presented == store.get(presented["id"])
                assert numerical(presented) == expected_values[presented["id"]]
            assert "prodigal_sheet_v1" not in json.dumps(state) and "native_result" not in json.dumps(state)
            for episode_id in (root_id, child_id):
                assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
                assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
            assert store.count("observation") == store.count("feature") == store.count("product") == 103
            assert store.count("annotation") == store.count("hypothesis") == store.count("assessment") == 0
            before_observations = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")]
            before_actions = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id")]
            receipt_count = store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0]
            saved_sheet = json.loads(json.dumps(sheet, allow_nan=False))
            before_sheet = deepcopy(saved_sheet)
            root_action = store.db.execute("SELECT decision_index FROM runtime_actions WHERE episode_id=?", (root_id,)).fetchone()[0]

            async def forbidden_worker(*args, **kwargs):
                pytest.fail("closed single-mode operation attempted another native invocation")

            def forbidden_sequence(*args, **kwargs):
                pytest.fail("saved single-mode facts attempted mutable sequence reread")

            with monkeypatch.context() as guarded:
                guarded.setattr(tools, "_sequence_worker_async", forbidden_worker)
                guarded.setattr(tools, "_sequence", forbidden_sequence)
                assert calculate_prodigal_scores(saved_sheet) == scores
                assert tools.execute("genes.predict", arguments, scope=scope,
                    operation_key=publication_row["operation_key"]) == publication
                workflow.receive_form(root.source, returned, RETURN_FORM, root_action, redelivery=True)
            assert saved_sheet == before_sheet
            assert len(capture["worker_calls"]) == 1 and operation_count(store, "genes.predict") == 1
            assert store.get_artifact(source["artifact_ref"]) == source_bytes
            assert workflow.journal.row("runtime_forms", child_id)["facts"] == returned_row["facts"]
            assert store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == receipt_count
            assert [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")] == before_observations
            assert [tuple(row) for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id")] == before_actions
            assert store.count("observation") == 103 and store.count("annotation") == 0
            capture.update(source=source, source_body=published_native, grading_artifact_ref=grading_entry["artifact_ref"],
                grading=grading, observations=observations, child_form=returned,
                child_committed_record_refs=frozen_facts["committed_record_refs"], parent_received_record_refs=sorted(received),
                parent_presented_observations=state["observations"],
                presentation_qualification="every actually presented row checked; all 103 observation refs received; no unlimited prompt claim",
                scripted_selections=selections, completed_actions_per_boundary=1,
                runtime_observations_per_boundary=1, replay_and_redelivery_without_native_rerun=True)
    except BaseException as error:
        failure = {"exception_type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        raise
    finally:
        capture["verification_error"] = failure
        (Path(os.environ["HMMER529_ATTEMPT"]) / "prodigal-single-child-return.json").write_text(
            json.dumps(capture, allow_nan=False, indent=2))
