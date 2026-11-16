"""Result-library descriptions; no claims of native execution or authority."""
from types import SimpleNamespace
import json


from gene_annotation_episode.episodic_workflow.root.library.execution_progress import ExecutionTargetReader
from test_protein_structure_selection import native


def collect(value):
    return next(row for row in value["extractors"] if row["operation"] == "execution.results.collect")


def test_ordinary_local_target_keeps_existing_information():
    from gene_annotation_episode.episodic_workflow.root.library.local_practical_operations import LocalPracticalOperations
    reader = object.__new__(ExecutionTargetReader)
    reader.api_execution = None
    reader.operations = {"local": object.__new__(LocalPracticalOperations)}
    reader.read_target = lambda handle, scope: {"resource_kind": "local", "resource_id": "local",
        "assignment": {"requested_job": {"argv": ["ordinary-program"]}}}
    reader.store = SimpleNamespace(get=lambda handle: {"artifact_ref": "handoff-fixture"},
        get_artifact=lambda reference: json.dumps({"receipt": {"tool_name": "practical.job.start"}}).encode())
    result = reader.describe_target("synthetic-handoff", {})
    assert result["service_or_program"] == "ordinary-program"
    assert result["acquisition_operations"] == ["execution.results.status", "execution.results.collect", "execution.results.read"]
