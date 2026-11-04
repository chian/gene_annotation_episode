"""Real slotted child operation/return with explicitly scripted test decisions."""
import asyncio
import json

import pytest

from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry
from test_published_axis_workflow import PUBLICATION, ScriptedDecisions, select
from test_sequence_derivation_publication import CASES, calculator
from test_sequence_views_integration import LocalOnly
from test_tool_grading_child_returns import RETURN_FORM, fixed_completion_estimate, zero_fixture_credit
from test_tool_grading_publication import numerical, operation_count


@pytest.mark.parametrize("operation,sequence,molecule,arguments,expected,quantities", CASES)
def test_selected_derivation_delivers_actual_numerical_records_once(
        tmp_path, operation, sequence, molecule, arguments, expected, quantities):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence=sequence, molecule=molecule)["subject_refs"]
        registry = ToolRegistry(store, clients=LocalOnly())
        scope = {"subject_refs": [target]}
        directory = tmp_path / "run"
        descriptor = prepare_scientific_binding(run_directory=directory,
            source_directory=PUBLICATION, tool_catalog=registry.catalog(),
            child_roles=("scientific_process",))
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        commission = {"kind": "episode_child", "role": "scientific_process",
            "goal": "Prepare the supplied sequence for its assigned molecular comparison.",
            "scope": scope,
            "purpose": "Return the actual derived sequence and coordinate measurements; assign no function.",
            "schema_json": json.dumps(RETURN_FORM), "initial_report_json": "{}",
            "assignment": {"selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A101"),
                "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": operation, "resources": "local"}]},
                "evidence_refs": [target], "constraints": {"no_external_acquisition": True},
                "context": {"molecule": molecule}}}
        args = {"subject_ref": target, **arguments}
        choices = ScriptedDecisions([select(commission),
            select({"kind": "tool", "tool": operation, "arguments": args})])
        workflow = Workflow(store, registry, choices, directory, "derivation-native-fixture",
            fixed_completion_estimate, zero_fixture_credit,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[], decision_protocol="decision_exchange_v1")
        parent = workflow.build("annotation", "root", "Investigate the supplied sequence", scope)
        assert workflow.catalog(scope, source=parent.source) == []
        assert not workflow.permits_common_action(parent.source, "tool")
        async def run():
            record = await parent.run_async(workflow.context)
            await parent.build_result(record)
            return record
        record = asyncio.run(run())
        assert record.units_consumed == 1 and len(choices.calls) == 2
        child_id = choices.calls[1]["episode_id"]
        info, = choices.calls[1]["state"]["scientific_process"]["child_tool_info"]
        assert set(info) == {"name", "description", "resources", "instructions"}
        assert info["name"] == operation and info["resources"] == "local"
        family = "translation" if operation == "sequence.translate" else "extraction"
        guidance = (PUBLICATION.parents[3] / "gene_annotation_episode/knowledge" /
                    ("sequence-" + family + ".md")).read_text().strip()
        assert guidance in info["instructions"]
        returned = json.loads(workflow.journal.row("runtime_forms", child_id)["form"])
        row = store.db.execute("SELECT * FROM tool_operations WHERE name=?", (operation,)).fetchone()
        publication = json.loads(row["result"])
        assert publication["status"] == "completed", publication
        assert returned == {"records": publication["record_refs"]}
        known = set(workflow.receipts.known(parent.source.episode_id))
        assert set(returned["records"]) <= known
        observation, = [store.get(ref) for ref in returned["records"]
                        if store.get(ref)["record_type"] == "observation"]
        grading, = source_tool_gradings(store, observation["source_ref"])
        for name, value in quantities.items():
            assert numerical(observation)[name] == pytest.approx(value), name
        assert calculator(operation)(json.loads(json.dumps(grading["sheet"], sort_keys=True))) == grading["scores"]
        presented = json.dumps(workflow.working_state(parent.source))
        for key in ("genetic_code_snapshot", "forward_table", "native_result", "input_sequence"):
            assert key not in presented
        for episode_id in (parent.source.episode_id, child_id):
            assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?",
                                    (episode_id,)).fetchone()[0] == 1
            assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?",
                                    (episode_id,)).fetchone()[0] == 1
        before = [tuple(r) for r in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")]
        receipt_count = store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0]
        assert registry.execute(operation, args, scope=scope, operation_key=row["operation_key"]) == publication
        action = store.db.execute("SELECT decision_index FROM runtime_actions WHERE episode_id=?",
                                  (parent.source.episode_id,)).fetchone()[0]
        workflow.receive_form(parent.source, returned, RETURN_FORM, action, redelivery=True)
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == receipt_count
        assert [tuple(r) for r in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")] == before
        assert operation_count(store, operation) == store.count("observation") == 1
        assert store.count("annotation") == 0
