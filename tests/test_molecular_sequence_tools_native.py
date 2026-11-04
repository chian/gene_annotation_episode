"""Opt-in ordinary ORF production and separate retained-only controls.

The sole new scan uses the original pinned module through the real registry,
factory, Workflow and result owner. Scripted decisions choose its supplied
engineering DNA and requested fields; they calculate no scientific values.
Retained controls require separately selected, pinned evidence. Recovery
forbids scanning and calculation. Public saved controls use actual saved-only
runs, preserve their Source qualifiers, and admit no private worksheet File.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from types import SimpleNamespace
import sys

import pytest
from jsonschema import Draft202012Validator
from method_loop import ClosedChildUnit

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.genomic_overlap_result_receipts import same
from gene_annotation_episode.molecular_result_facts import validate_frozen_molecular_return
from gene_annotation_episode.molecular_sequence_execution_contracts import SOFTWARE_VERSION, molecular_sequence_adapter_argv
from gene_annotation_episode.molecular_sequence_input_contracts import input_record_digest
from gene_annotation_episode import molecular_sequence_driver as driver
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import molecular_sequence_tools as molecular_tools
from gene_annotation_episode import orf_measurements
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.runtime import INSTRUCTIONS, Workflow, _decode_action_response
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController


ROOT = Path(__file__).resolve().parents[1]
PREFIX_VERSION = "ordinary_orf_native_integration_prefix_v1"
PREFIX_NAME = "ORF_NATIVE_PREFIX.json"
RUN_ID = "ordinary-orf-genuine-public-workflow"
DNA = "ATGAAATAA"
DNA_SHA256 = "c5fc760ddfbe43faada474e3d39342b30a0542dd9e4583b655cec28b53867498"
PYTHON_SHA256 = "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f"
SOURCE_SHA256 = "de47e1dc0013cd6e8d2941d8945835d585f938e486a69bb2ba3333403a3efba4"
CALLABLE_SHA256 = "bc32fff2924e09ec940f6d9b8d74732a8ef86d0894761430a3ad57ea7148269b"
PUBLICATION = "research/slotted_process_library/publications/2026-10-24-001"
REFERENCE_SITE = "reference/episode_tools/.venv/lib/python3.12/site-packages"
ORIGINAL_MODULE = REFERENCE_SITE + "/biomni/tool/molecular_biology.py"
SUPPORT_TREES = [PUBLICATION, *[REFERENCE_SITE + "/" + name for name in (
    "bs4", "beautifulsoup4-4.15.0.dist-info", "soupsieve", "soupsieve-2.8.4.dist-info")]]
QUESTION = ("For the supplied DNA ATGAAATAA, using min_length 9, search_reverse false and "
    "filter_subsets false, what are original ORF row 0 and its interval length in nucleotides? "
    "Return the requested retained values and their qualifications.")
ROWS = [{"row_id": {"kind": "orf", "row_index": 0}, "fields": ["native_row", "interval_length_nt"]}]
COUNTS = dict(runtime_episodes=2, runtime_actions=2, runtime_observations=2,
    runtime_model_calls=2, tool_operations=1, runtime_forms=1, runtime_report_attempts=1)
# Actual module/METADATA byte joins read from the retained234 native receipt.
# Paths below select only the new bounded dependency tree and declared support.
LIBRARY_PINS = (
    ("dependencies", "pandas/__init__.py", "108be8ca3ae1a2a5c765ee6f87e8867d87c2fb5a89107e6c2d3a6acc96612b7b"),
    ("dependencies", "pandas-2.3.3.dist-info/METADATA", "40ee953dc7ca155840b639a1881ff84578075187fce0ac20eeda55a7fa0d9a90"),
    ("dependencies", "requests/__init__.py", "311157e7fa4aa9166c827d5237e6fd694eeb5ca549ee40e2e90f89f21abcd56e"),
    ("dependencies", "requests-2.34.2.dist-info/METADATA", "8c384ba3e979480faae2859d3c5e6c1276dd2c3616e322e124d52c8cfc556f27"),
    ("dependencies", "Bio/__init__.py", "badc0a610aaa5c5c3dd20bd579d30040c2ab4ce8df43ec5d9457d0e2afe3065b"),
    ("dependencies", "biopython-1.88.dist-info/METADATA", "d8049c9ad2de2dc720ad57aba95e2ec1df148e8eaaa90285b99070cad0066ea3"),
    ("dependencies", "numpy/__init__.py", "09295a80660f17925ae23765ce8cbd7ff7ceae968d5f2f89349f1cb74c0b9e11"),
    ("dependencies", "numpy-2.5.4.dist-info/METADATA", "e2b909d6a37d76c2bc130f528d7fed0c517322bce16dc7846b6a6df30e200403"),
    ("dependencies", "typing_extensions.py", "4040ca1a1ecbee00d1385c12a93084d1c5bd46f0b774f07e5ae7e91c4f55e696"),
    ("dependencies", "typing_extensions-4.16.0.dist-info/METADATA", "b05084ca1d50879865178d9fff9fabeab61bdfb1f361bfbde95421ffc8f9be46"),
    ("reference", "bs4/__init__.py", "90e007f82a9fc5bcf22a8df3b395b7bc5245e54d65cd68fd51ca12a414718d4e"),
    ("reference", "beautifulsoup4-4.15.0.dist-info/METADATA", "b2f888103259f1607c85f3b1163be1bc49fc9941a3243c3b89a21075bfc6d4fb"),
    ("reference", "soupsieve/__init__.py", "155e0e97615195dcbbac6f789d01cd1e82536487506d425d6641a15e4237b621"),
    ("reference", "soupsieve-2.8.4.dist-info/METADATA", "4f8f5d855dabd8b3c10706cbc01d7517bd5f027cc47b59183b604a2080e6b626"),
)


class PublishedORFProvider:
    """Two selected decisions under the actual published instruction contract."""

    def __init__(self, script, *, library=None):
        self.script = deepcopy(script)
        self.contexts, self.dispatches, self.released = [], [], []
        self.library = library

    async def complete(self, episode_id, role, instructions, context, output_schema):
        index = len(self.contexts)
        self.contexts.append(deepcopy(context))
        dispatch = dict(episode_id=episode_id, role=role, instructions=instructions,
            output_schema_sha256=digest(output_schema), response=None)
        self.dispatches.append(dispatch)
        assert role == "REASONING" and index < len(self.script) == 2
        assert context["goal"]["objective"] == QUESTION
        assert context["goal"]["task_context"]["root_objective"] == QUESTION
        assert context["scope"] == self.script[0]["selection"]["scope"]
        assert context["feedback"] is None and context["current_report_update"] == {}
        assert context["available_report_facts"]["orf_measurements"]["type"] == "array"
        if index == 0:
            assert instructions.startswith(INSTRUCTIONS)
            assert "scientific_process" not in context
            assert context["requested_form"] is None and context["tools"] == []
        else:
            assert instructions.startswith("Determine what the supplied target does within the parent's assigned question, scope and constraints.")
            selected = self.script[0]["selection"]["assignment"]["selection"]
            process = context["scientific_process"]
            assert self.library is not None and process["selection"] == selected
            assert process["evidence_axis"] == instruction_view(self.library.resolve(selected["evidence_axis"]))
            thought = self.library.resolve(selected["thought_pattern"])
            thought_fields = ("id", "name", "description", "use_when", "live_alternatives",
                "decision_guidance", "outcome_contingencies", "boundary")
            assert process["thought_pattern"] == {key: thought[key] for key in thought_fields if key in thought}
            assert context["requested_form"] == _form_schema()
            assert context["requested_report_purpose"] == self.script[0]["selection"]["purpose"]
            assert any(row["name"] == contracts.ORDINARY_ORF_TOOL and row["resources"] == "local"
                for row in context["tools"])
        response = deepcopy(self.script[index])
        selected = response["selection"]
        discriminators = ("kind", "role", "tool")
        branches = [branch for branch in output_schema["properties"]["selection"]["anyOf"]
            if all(selected[key] in branch["properties"].get(key, {}).get("enum", [])
                for key in discriminators if key in selected)]
        assert len(branches) == 1
        fields = branches[0]["properties"]
        for key in ("assignment", "arguments"):
            if key in selected and fields[key].get("type") == "string":
                selected[key] = json.dumps(selected[key], allow_nan=False)
        if selected["kind"] == "episode_child":
            for key in fields["scope"]["required"]:
                if key not in selected["scope"]:
                    assert {"type": "null"} in fields["scope"]["properties"][key]["anyOf"]
                    selected["scope"][key] = None
        Draft202012Validator(output_schema).validate(response)
        dispatch["response"] = deepcopy(response)
        return response

    async def release(self, episode_id):
        self.released.append(episode_id)


def _json(path):
    return json.loads(Path(path).read_bytes())


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _inventory(directory):
    return {str(path.relative_to(directory)): {key: value for key, value in _pin(path).items() if key != "path"}
        for path in sorted(Path(directory).rglob("*")) if path.is_file() and not path.is_symlink()}


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}


def _counts(store):
    return {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in COUNTS}


def _credit(*args, **kwargs):
    return 0


def _controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _forbidden(*args, **kwargs):
    raise AssertionError("retained-only ORF control attempted new decisions, native work or calculation")


def _selected_closure(directory):
    attempt = Path(os.environ["HMMER529_ATTEMPT"]).resolve(strict=True)
    assert ROOT == attempt / "source_snapshot"
    selected = _json(attempt / "selected_request.json")
    assert selected["support_files"] == [ORIGINAL_MODULE]
    assert set(selected["support_trees"]) == set(SUPPORT_TREES)
    assert selected["default_hmmer_fixtures"] is False
    assert selected["native_executables"] == selected["existing_native_executables"] == selected["native_libraries"] == []
    assert selected["policy"] == ordinary.POLICY and selected["swap_bytes"] == 0
    assert selected["selected_python_source_pin"]["sha256"] == PYTHON_SHA256
    python = _pin(attempt / "runtime/bin/python")
    assert python["sha256"] == PYTHON_SHA256 and python["size_bytes"] == 8020928
    assert Path(sys.executable).resolve(strict=True) == Path(python["path"])
    assert Path(sys.prefix).resolve(strict=True) == attempt / "runtime"
    module = _pin(ROOT / ORIGINAL_MODULE)
    assert module["sha256"] == SOURCE_SHA256 and module["size_bytes"] == 91223
    libraries = []
    for kind, relative, expected in LIBRARY_PINS:
        base = attempt / "dependencies" if kind == "dependencies" else ROOT / REFERENCE_SITE
        observed = _pin(base / relative)
        assert observed["sha256"] == expected
        libraries.append(observed)
    files = {}
    for name in ("source", "dependency", "stdlib", "binary"):
        for row in _json(attempt / (name + "_pins_before.json")):
            assert _pin(row["path"]) == row
            assert row["path"] not in files
            files[row["path"]] = row
    manifest = directory / "selected-software-files.json"
    _write(manifest, [files[key] for key in sorted(files)])
    manifest_pin = _pin(manifest)
    roots = [str(ROOT), str(attempt / "dependencies"), str(ROOT / REFERENCE_SITE)]
    software = dict(version=SOFTWARE_VERSION, python=python,
        python_home=str(attempt / "runtime"), python_version=sys.version, import_roots=roots,
        software_files_file=manifest_pin, software_files_ref="artifact_" + manifest_pin["sha256"])
    deployment = dict(version="molecular_sequence_deployment_v1", runtime=dict(executable=python,
        home=software["python_home"]), module=module, import_roots=roots,
        software_files_file=manifest_pin, software_files_ref=software["software_files_ref"])
    return deployment, software, dict(selected_request_file=_pin(attempt / "selected_request.json"),
        module=module, python=python, library_pins=libraries, manifest_file=manifest_pin,
        qualification="New explicit current adapter closure; retained234 source/runtime/library pins checked, old234 paths not restored")


def _configuration(directory, deployment, software):
    workspace = directory / "native-workspace"
    workspace.mkdir()
    resources = {"ordinary-selected": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY),
        native_molecular_sequence=[dict(version=molecular_tools.BINDING_VERSION,
            operation=contracts.ORDINARY_ORF_TOOL, deployment=deployment, software=software)])}
    environments = [dict(operation=contracts.ORDINARY_ORF_TOOL, resource_id="ordinary-selected",
        binding_ordinal_0based=0, environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


def _arguments(subject_ref):
    return dict(subject_ref=subject_ref, min_length=9, search_reverse=False, filter_subsets=False, rows=deepcopy(ROWS))


def _form_schema():
    return obj({"measurements": contracts.ordinary_orf_fact_sources()["orf_measurements"]["report_schema"]})


def _workflow(store, tools, provider, directory, factory, scientific_binding, initial, *, run_id=RUN_ID):
    application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
    return Workflow(store, tools, provider, directory, run_id, _controller, _credit,
        project_child_credit=_credit, episode_binding_descriptors=[scientific_binding,
            *application.episode_binding_descriptors], role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider, episode_record_receipts=True,
        initial_known_record_refs=initial)


def _commission(library, scope):
    return dict(selection=dict(kind="episode_child", role="scientific_process", goal=QUESTION,
        scope=scope, purpose="Return the requested original ORF row and interval length through the controlled ORF form.",
        schema_json=json.dumps(_form_schema()), initial_report_json="{}", assignment=dict(
            selection=dict(version="scientific_process_selection_v3", evidence_axis=library.reference("A103"),
                thought_pattern=library.reference("P01"), child_tool_info=[dict(name=contracts.ORDINARY_ORF_TOOL, resources="local")]),
            evidence_refs=[], constraints={}, context={})), report_update={})


def _artifact_json(store, identity):
    return _json(retained_native_file(store, identity))


def _prefix(store, workflow, base):
    """Write actual available audit before any later success assertions."""
    result = deepcopy(base)
    result.update(counts=_counts(store), runtime_episodes=[dict(row) for row in store.db.execute(
        "SELECT * FROM runtime_episodes ORDER BY json_array_length(path)")], runtime_actions=[dict(row)
        for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id,decision_index")],
        tool_operations=[dict(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY operation_key")])
    result["native_controls"] = []
    resources = base["factory"]["resources"]
    workspace = Path(resources["ordinary-selected"]["workspace"])
    for row in result["runtime_actions"]:
        selection = json.loads(row["action"])
        if selection.get("kind") != "tool" or selection.get("tool") != contracts.ORDINARY_ORF_TOOL:
            continue
        key = f'{row["run_id"]}:{row["episode_id"]}:{row["decision_index"]}'
        root = workspace / ".episode-operations" / digest({"run": RUN_ID, "episode": row["episode_id"]}) / digest(key)
        observed = dict(operation_key=key, directory=str(root), files={})
        for name in ("native.json", ordinary.BINDING_FILENAME, "molecular-sequence-plan.json",
                ordinary.DRIVER_REQUEST_FILENAME, "molecular-sequence-attempt/attempt-bundle.json",
                "molecular-sequence-attempt/driver-output/declaration.json"):
            path = root / name
            if path.is_file():
                item = dict(file=_pin(path), value=None, decode_failure=None)
                try:
                    item["value"] = _json(path)
                except (ValueError, UnicodeError) as error:
                    item["decode_failure"] = dict(exception_type=type(error).__name__, message=str(error))
                observed["files"][name] = item
        result["native_controls"].append(observed)
    result["scripted_dispatches"] = len(workflow.provider.contexts)
    result["scripted_provider_dispatches"] = deepcopy(workflow.provider.dispatches)
    return result


def _publication(store, workflow, tools):
    operation, = list(store.db.execute("SELECT * FROM tool_operations"))
    outcome = json.loads(operation["result"])
    reference = outcome["result"]["source_ref"]
    records = EpisodeReturnRecords(store, RUN_ID, failure_prefix="ordinary_orf_native_proof_")
    episodes = list(store.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
    parent, science = [records.context(row["episode_id"]) for row in episodes]
    execution = workflow.episode_bindings.for_role("results")
    owner = tools.molecular_sequence_results_for(RUN_ID)
    assert owner is execution.molecular_sequence_results and owner.owner is execution
    assert owner.owner.services is workflow.services and owner.owner.tool_registry is tools
    publication = owner.read_ordinary_orf_publication(science, reference,
        read_received=workflow.services.read_received_molecular_input)
    return operation, outcome, publication, parent, science


def _assert_native_publication(store, workflow, tools, base, prefix_path, *, recorded_calls=None):
    operation, outcome, publication, parent, science = _publication(store, workflow, tools)
    custody, public, source = publication["control"], publication["stored"], publication["source"]
    assert outcome["status"] == "completed" and outcome["result"] == public
    assert json.loads(operation["arguments"]) == _arguments(base["subject_ref"])
    key = f"{RUN_ID}:{science.episode_id}:0"
    assert operation["operation_key"] == key
    action = store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
        (RUN_ID, science.episode_id)).fetchone()
    assert json.loads(action["action"]) == dict(kind="tool", tool=contracts.ORDINARY_ORF_TOOL, arguments=_arguments(base["subject_ref"]))
    assert same({k: v for k, v in json.loads(action["result"]).items() if k != "pending_work_after_action"}, outcome)
    assert source["origin"] == "tool" and source["provider"] == contracts.ORDINARY_ORF_TOOL
    assert source["version"] == contracts.ORDINARY_ORF_SOURCE_VERSION
    assert public["source_ref"] == source["id"] and outcome["record_refs"] == [source["id"]]
    assert all(value == "retained" for value in public["file_states"].values()) and public["failures"] == []
    original = custody["original"]
    execution = _artifact_json(store, original["execution_file"])
    binding = _artifact_json(store, custody["request"]["input_binding_file"])
    plan = _artifact_json(store, original["plan_file"])
    request = _artifact_json(store, original["driver_request_file"])
    native_request = _artifact_json(store, original["native_request_file"])
    bundle = _artifact_json(store, original["bundle_file"])
    declaration = _artifact_json(store, original["declaration_file"])
    assert execution["terminal"] is execution["quiescent"] is True
    assert execution["returncode"] == 0 and execution["failure"] is None
    assert execution["metadata"]["policy"] == ordinary.POLICY
    assert execution["plan"] == plan and plan["identity"]["operation_key"] == key
    assert binding["context"] == science.as_record()
    assert plan["identity"]["run_id"] == RUN_ID and plan["identity"]["episode_id"] == science.episode_id
    assert plan["identity"]["assignment_sha256"] == digest(plain(science.assignment))
    assert plan["identity"]["resource_id"] == "ordinary-selected"
    assert native_request["command"] == molecular_sequence_adapter_argv(plan)
    assert execution["handle"]["command"] == native_request["command"]
    assert execution["handle"]["request_sha256"] == original["native_request_file"]["sha256"]
    assert native_request["env"] == plan["selected_environment"]
    assert native_request["file_bytes"] == ordinary.POLICY["scratch_bytes"]
    assert bundle["invocation"]["invocation_count"] == bundle["invocation"]["launch_attempt_count"] == 1
    assert bundle["invocation"]["process_exit_observed"] is True
    assert declaration["native_call_state"] == "returned"
    assert declaration["native_failure"] is declaration["driver_failure"] is None
    operand = binding["frozen_operand"]
    owner = tools.molecular_sequence_results_for(RUN_ID)
    host_file = owner.action_directory(science.episode_id, key) / molecular_tools.HOST_BINDING_FILENAME
    host_binding = _json(host_file)
    assert host_binding["version"] == molecular_tools.HOST_BINDING_VERSION
    assert same(host_binding["frozen_operand"], operand) and host_binding["policy"] == ordinary.POLICY
    selected_row = host_binding["configuration_selection"]
    assert selected_row["resource_id"] == "ordinary-selected" and selected_row["binding_ordinal_0based"] == 0
    assert selected_row["binding"] == owner.owner.resources["ordinary-selected"]["native_molecular_sequence"][0]
    admitted = host_binding["subject_admission"]
    assert admitted["failure"] is None and admitted["selection"] == dict(reference=base["subject_ref"], namespace="input")
    assert admitted["input"]["witness"]["record"] == store.get(base["subject_ref"])
    assert admitted["input"]["receiver"] == dict(run_id=RUN_ID, episode_id=science.episode_id,
        request_sha256=input_record_digest(plain(science.request)), assignment_sha256=input_record_digest(plain(science.assignment)))
    assert operand["subject"] == store.get(base["subject_ref"])
    assert operand["sequence"] == DNA and operand["input_file"] == base["input_file"]
    assert operand["parent_mapping"] == store.sequence_mapping(base["subject_ref"])
    assert operand["mapping_failure"] is None
    assert request["selection"]["arguments"] == dict(sequence=DNA, min_length=9, search_reverse=False, filter_subsets=False)
    assert request["scientific_context"] == dict(subject_ref=base["subject_ref"], parent_mapping=operand["parent_mapping"])
    roles = custody["source_files"]
    capture, sheet, components = [_artifact_json(store, roles[role]["file"]) for role in ("capture", "sheet", "components")]
    assert capture["native_call_state"] == "returned" and capture["failure"] is None
    receipt = capture["execution_receipt"]
    assert receipt["module_load"]["source_file"] == request["selection"]["deployment"]["module"]
    assert receipt["module_load"]["source_file"]["sha256"] == SOURCE_SHA256
    assert receipt["observed_callable"]["name"] == contracts.ORDINARY_ORF_TOOL
    assert receipt["observed_callable"]["sha256"] == CALLABLE_SHA256
    assert receipt["runtime"]["executable"]["sha256"] == PYTHON_SHA256
    assert capture["native_record"]["result"]["orfs"] == [[DNA, "MK", 0, 9, "+", 1]]
    assert sheet["inputs"]["native_record"] == capture["native_record"]
    assert sheet["inputs"]["input_sequence"] == DNA and sheet["inputs"]["parent_mapping"] == operand["parent_mapping"]
    assert sheet["inputs"]["genetic_code"] == capture["reference_data"]["genetic_code_snapshot"]
    assert components["rows"][0]["native_row"] == [DNA, "MK", 0, 9, "+", 1]
    assert components["rows"][0]["interval_length_nt"] == 9
    assert public["selection"]["rows"] == ROWS and public["values"]["original_attempt_association"] == "verified"
    cells = public["values"]["rows"]
    assert [(cell["row_id"], cell["field"]) for cell in cells] == [
        ({"kind": "orf", "row_index": 0}, "native_row"), ({"kind": "orf", "row_index": 0}, "interval_length_nt")]
    for cell, field, expected, unit in zip(cells, ("native_row", "interval_length_nt"),
            ([DNA, "MK", 0, 9, "+", 1], 9), ("native_field_units", "nt")):
        assert cell["value_state"] == "stored_value" and same(cell["value"], expected)
        assert cell["source_pointer"] == "/rows/0/" + field and cell["unit"] == unit
        assert cell["source_ref"] == roles["components"]["file"]["artifact_ref"]
        assert cell["population_id"] == "orf_retained_row" and cell["denominators"] == []
    native_evidence = dict(source=source, public=public, custody=custody,
        parent_episode_id=parent.episode_id, science_episode_id=science.episode_id,
        original_native_unit=execution["handle"]["unit"], original_invocation_count=1,
        host_binding_file=_pin(host_file), subject_admission=admitted,
        role_files={role: roles[role]["file"] for role in ("capture", "sheet", "components")})
    base.update(native_evidence, native_execution_verified=True)
    _write(prefix_path, base)
    form, = list(store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?", (science.episode_id,)))
    returned = json.loads(form["form"])
    assert returned == {"measurements": [public]}
    attempt, = list(store.db.execute("SELECT * FROM runtime_report_attempts WHERE parent_episode_id=?", (parent.episode_id,)))
    assert attempt["failure"] is None and json.loads(attempt["form"]) == returned
    assert workflow.services.molecular_received_facts(parent, fact_source="orf_measurements") == [public]
    assert workflow.services.molecular_frozen_facts(science, fact_source="orf_measurements") == [public]
    assert _counts(store) == COUNTS
    calls = list(store.db.execute("SELECT * FROM runtime_model_calls ORDER BY rowid"))
    if recorded_calls is None:
        assert len(calls) == len(workflow.provider.contexts) == len(workflow.provider.dispatches) == 2
        for call, context, dispatch in zip(calls, workflow.provider.contexts, workflow.provider.dispatches):
            assert call["episode_id"] == dispatch["episode_id"]
            assert json.loads(call["request"])["context"] == context
            assert json.loads(call["response"]) == dispatch["response"]
    else:
        assert workflow.provider.contexts == workflow.provider.dispatches == []
        assert [dict(row) for row in calls] == recorded_calls
    private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
    assert base["input_file"]["artifact_ref"] not in private
    permissions = []
    for context in (parent, science):
        known = set(workflow.receipts.known(context.episode_id))
        assert {base["subject_ref"], base["input_file"]["artifact_ref"], source["id"]} <= known
        assert private.isdisjoint(known)
        resolver = workflow.resolver(plain(context.scope), context=context)
        for reference in private:
            assert resolver(reference, "artifact") is False
        admitted, path = workflow.services.read_received_molecular_input(context,
            base["input_file"]["artifact_ref"], "artifact", file_format="ascii_sequence")
        assert admitted["failure"] is None and path.read_bytes() == DNA.encode("ascii")
        for role in ("capture", "sheet", "components"):
            denied, path = workflow.services.read_received_molecular_input(context,
                roles[role]["file"]["artifact_ref"], "artifact", file_format="json")
            assert denied["failure"] is not None and path is None
        assert set(workflow.receipts.known(context.episode_id)) == known
        permissions.append(dict(episode_id=context.episode_id, input_file_received=True, private_outputs_received=False))
    assert base["input_file"]["artifact_ref"] not in source["auxiliary_artifact_refs"]
    return dict(**native_evidence, returned=returned, permissions=permissions)


def test_genuine_public_orf_native_and_automatic_parent_delivery(tmp_path):
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_WORKFLOW") != "1" or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("requires explicit bounded ordinary ORF native selection")
    prefix_path, store_directory = tmp_path / PREFIX_NAME, tmp_path / "store"
    proof = dict(version=PREFIX_VERSION, run_id=RUN_ID, question=QUESTION, test_root=str(tmp_path),
        store_directory=str(store_directory), workflow_directory=str(tmp_path / "run"), native_execution_verified=False, native_proof_passed=False,
        qualification="Supplied nine-symbol DNA, original selected callable and scripted choices; no gene prediction or annotation confidence")
    _write(prefix_path, proof)
    try:
        deployment, software, closure = _selected_closure(tmp_path)
        resources, environments = _configuration(tmp_path, deployment, software)
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, molecular_sequence_environments=environments)
        proof.update(closure=closure, factory=factory.as_record())
        with Store(store_directory) as store:
            subject, = store.create_problem(raw_sequence=DNA, molecule="dna")["subject_refs"]
            record = store.get(subject)
            input_file = dict(artifact_ref=record["sequence_ref"], sha256=DNA_SHA256, size_bytes=9, format="ascii_sequence")
            assert _pin(store.path / "artifacts" / DNA_SHA256[:2] / DNA_SHA256)["sha256"] == DNA_SHA256
            scope = store.validate_scope()
            initial = [subject, input_file["artifact_ref"]]
            tools = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
            factory.configure_tool_registry(tools)
            directory = tmp_path / "run"
            scientific = prepare_scientific_binding(run_directory=directory, source_directory=ROOT / PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(directory / "scientific-process-library")
            provider = PublishedORFProvider([_commission(library, scope), dict(selection=dict(kind="tool",
                tool=contracts.ORDINARY_ORF_TOOL, arguments=_arguments(subject)), report_update={})], library=library)
            workflow = _workflow(store, tools, provider, directory, factory, scientific, initial)
            proof.update(subject_ref=subject, input_file=input_file, scope=scope, initial_known_record_refs=initial,
                scientific_binding=scientific, scientific_library=library.as_record())
            root = workflow.build("annotation", "root", QUESTION, scope)
            try:
                completed = asyncio.run(root.run_async(workflow.context))
            finally:
                proof = _prefix(store, workflow, proof)
                _write(prefix_path, proof)
            # The original native/ToolOperation prefix above survives every
            # later assertion. A failure never selects another invocation.
            verified = _assert_native_publication(store, workflow, tools, proof, prefix_path)
            final = plain(asyncio.run(root.build_result(completed)).as_record())
            assert final == {"credit": 0, "pending_handles": []}
            proof.update(verified, final_result=final, native_proof_passed=True,
                public_saved_read_or_recalculation_verified=False)
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (store_directory / "state.sqlite3").is_file():
            proof["database_file"] = _pin(store_directory / "state.sqlite3")
        _write(prefix_path, proof)


def _retained_prefix(*, require_delivery=True, require_native=True):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_RETAINED_PREFIX")
    selected_sha = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_RETAINED_SHA256")
    if not supplied or not selected_sha or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("requires an explicit successful native prefix and its selected byte digest")
    path = Path(supplied).resolve(strict=True)
    assert _pin(path)["sha256"] == selected_sha
    value = _json(path)
    assert value["version"] == PREFIX_VERSION and value["run_id"] == RUN_ID
    if require_native:
        assert value["native_execution_verified"] is True
    if require_delivery:
        assert value["native_proof_passed"] is True
    assert value["question"] == QUESTION and value["input_file"]["sha256"] == DNA_SHA256
    assert _pin(value["database_file"]["path"]) == value["database_file"]
    assert not Path(value["database_file"]["path"] + "-wal").exists()
    return path, value


def _readonly_store(directory):
    store = Store.__new__(Store)
    store.path = Path(directory).resolve(strict=True)
    store.db = sqlite3.connect((store.path / "state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    return store


def _clone_retained(prefix, directory):
    directory.mkdir()
    target = directory / "store"
    target.mkdir()
    original = _readonly_store(prefix["store_directory"])
    try:
        before = _tables(original)
        connection = sqlite3.connect(target / "state.sqlite3")
        try:
            original.db.backup(connection)
        finally:
            connection.close()
        assert original.db.total_changes == 0
    finally:
        original.close()
    for name in ("artifacts", "cache"):
        source = Path(prefix["store_directory"]) / name
        if source.exists(): shutil.copytree(source, target / name)
    shutil.copytree(prefix["workflow_directory"], directory / "run")
    return target, before


def _reopen(prefix, store, directory, provider, *, run_id=RUN_ID):
    tools = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
    factory = ExecutionServiceFactory.from_record(prefix["factory"])
    factory.configure_tool_registry(tools)
    workflow = _workflow(store, tools, provider, directory / "run", factory,
        deepcopy(prefix["scientific_binding"]), prefix["initial_known_record_refs"], run_id=run_id)
    return tools, workflow


def _forbid_native(monkeypatch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", _forbidden)
    monkeypatch.setattr(ordinary, "run_ordinary_orf_attempt", _forbidden)
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)


def test_retained_orf_frozen_parent_and_direct_child_replay(tmp_path, monkeypatch):
    prefix_path, prefix = _retained_prefix()
    original_before = _closed_orf_inventory(Path(prefix["test_root"]))
    copied, original_tables, original_schema, family = _clone_closed_orf_store(
        prefix["store_directory"], tmp_path / "owned-frozen", prefix["database_file"])
    shutil.copytree(prefix["workflow_directory"], copied.parent / "run", symlinks=True)
    _forbid_native(monkeypatch)
    _forbid_orf_calculation(monkeypatch)
    with Store(copied) as store:
        assert _tables(store) == original_tables and len(original_tables) == 47
        assert _closed_orf_schema(store.db) == original_schema
        tools, workflow = _reopen(prefix, store, copied.parent, PublishedORFProvider([]))
        records = EpisodeReturnRecords(store, RUN_ID, failure_prefix="ordinary_orf_frozen_")
        parent, science = [records.context(prefix[name]) for name in ("parent_episode_id", "science_episode_id")]
        with monkeypatch.context() as authenticated:
            input_reads = _forbid_original_input_bytes(authenticated, prefix["input_file"]["artifact_ref"])
            assert workflow.services.molecular_own_facts(science, fact_source="orf_measurements") == [prefix["public"]]
            assert workflow.services.molecular_frozen_facts(science, fact_source="orf_measurements") == [prefix["public"]]
            assert workflow.services.molecular_received_facts(parent, fact_source="orf_measurements") == [prefix["public"]]
            assert input_reads == []
        with monkeypatch.context() as private:
            denied_reads = _forbid_scientific_files(private)
            _saved_orf_privacy(store, workflow, (parent, science), sources=[prefix["source"]],
                input_file=prefix["input_file"], baseline_artifacts={prefix["input_file"]["artifact_ref"]})
            assert denied_reads == []
        validate_frozen_molecular_return(prefix["returned"], _form_schema(), [prefix["public"]], fact_source="orf_measurements")
        changed = deepcopy(prefix["returned"])
        changed["measurements"][0]["values"]["rows"][1]["value"] = 8
        with pytest.raises(ValueError):
            validate_frozen_molecular_return(changed, _form_schema(), [prefix["public"]], fact_source="orf_measurements")
        source = prefix["source"]
        guarded = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"], prefix["input_file"]["artifact_ref"]}
        before_tables = _tables(store)
        before_files = _closed_orf_inventory(copied.parent, sqlite_files=False)
        blocked, actual_get = [], Store.get_artifact
        def guarded_get(current, reference):
            if reference in guarded:
                blocked.append(reference)
                raise AssertionError("closed ORF replay reopened a scientific File")
            return actual_get(current, reference)
        monkeypatch.setattr(Store, "get_artifact", guarded_get)
        monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
        monkeypatch.setattr(workflow.provider, "complete", _forbidden)
        final, child_result = _closed_orf_return(workflow, scope=prefix["scope"], parent=parent, science=science)
        assert final == prefix["final_result"] and child_result == {"form": prefix["returned"]}
        assert workflow.provider.contexts == [] and _counts(store) == COUNTS
        assert _tables(store) == before_tables == original_tables
        assert _closed_orf_schema(store.db) == original_schema
        assert _closed_orf_inventory(copied.parent, sqlite_files=False) == before_files and blocked == []
    assert _closed_orf_inventory(Path(prefix["test_root"])) == original_before
    _write(tmp_path / "ORF_FROZEN_REPLAY.json", dict(prefix_file=_pin(prefix_path),
        original_native_unit=prefix["original_native_unit"], original_regular_file_bytes_unchanged=True,
        original_file_modes_unchanged=True, original_sqlite_family=family, raw_table_count=47,
        frozen_selected_values=prefix["public"], parent_result=final, direct_child_result=child_result,
        guarded_artifact_refs=sorted(guarded), reopened_scientific_files=blocked,
        qualification="Retained-only original completed child and frozen parent delivery; no new scan, calculation, model call or File grant"))


def test_retained_orf_private_saved_sheet_calculation(tmp_path, monkeypatch):
    prefix_path, prefix = _retained_prefix(require_delivery=False)
    original_before = _inventory(Path(prefix["test_root"]))
    copied, original_tables = _clone_retained(prefix, tmp_path / "owned-saved")
    _forbid_native(monkeypatch)
    with Store(copied) as store:
        assert _tables(store) == original_tables
        tools, workflow = _reopen(prefix, store, copied.parent, PublishedORFProvider([]))
        before_tables = _tables(store)
        counts = _counts(store)
        with monkeypatch.context() as literal:
            literal.setattr(driver, "calculate_orf_components", _forbidden)
            literal.setattr(orf_measurements, "calculate_orf_components", _forbidden)
            literal.setattr(driver, "build_orf_sheet", _forbidden)
            literal.setattr(orf_measurements, "build_orf_sheet", _forbidden)
            operation, outcome, publication, parent, science = _publication(store, workflow, tools)
        assert publication["stored"] == prefix["public"] and outcome["result"] == prefix["public"]
        identity = publication["control"]["source_files"]["sheet"]["file"]
        path = retained_native_file(store, identity)
        original_bytes = path.read_bytes()
        original_components = _artifact_json(store, publication["control"]["source_files"]["components"]["file"])
        # This is host-selected private saved data after original Source
        # authentication. It is not a received-sheet receipt or public action.
        assert identity["artifact_ref"] not in set(workflow.receipts.known(parent.episode_id))
        assert identity["artifact_ref"] not in set(workflow.receipts.known(science.episode_id))
        request = dict(version=driver.REQUEST_VERSION, mode="saved_sheet", attempt_identity=dict(
            run_id="private-saved-control-" + Path(os.environ["HMMER529_ATTEMPT"]).name,
            episode_id="private-saved-control-not-a-runtime-action", resource_id="private-selected-outer-bounded-runtime",
            operation_key="private-saved-control-" + identity["sha256"], execution_id=str(tmp_path / "private-saved-driver")),
            selection=dict(operation=contracts.ORDINARY_ORF_TOOL, sheet_file=_pin(path)), scientific_context=None)
        request_path = tmp_path / "private-saved-request.json"
        _write(request_path, request)
        output = tmp_path / "private-saved-driver"
        observed = []
        code = orf_measurements.calculate_orf_components.__code__
        assert driver.calculate_orf_components is orf_measurements.calculate_orf_components
        previous = sys.getprofile()
        def observe(frame, event, value):
            if frame.f_code is code and event in ("call", "return"):
                observed.append(event)
        try:
            sys.setprofile(observe)
            declaration = driver.run_molecular_sequence_driver(request_file=_pin(request_path), output_directory=str(output))
        finally:
            sys.setprofile(previous)
        assert observed == ["call", "return"]
        assert declaration["native_call_state"] == "not_requested"
        assert declaration["native_failure"] is declaration["driver_failure"] is None
        assert (output / "sheet.json").read_bytes() == original_bytes == path.read_bytes()
        assert _json(output / "components.json") == original_components
        assert not (output / "capture.json").exists()
        for role in ("sheet", "components"):
            observed_file = _pin(output / (role + ".json"))
            assert declaration["files"][role]["state"] == "present"
            assert all(declaration["files"][role][key] == observed_file[key] for key in ("sha256", "size_bytes"))
        assert _tables(store) == before_tables and _counts(store) == counts
        assert workflow.provider.contexts == []
    assert _inventory(Path(prefix["test_root"])) == original_before
    _write(tmp_path / "ORF_PRIVATE_SAVED_DATA.json", dict(prefix_file=_pin(prefix_path), original_source_ref=prefix["source"]["id"],
        original_native_unit=prefix["original_native_unit"], input_sheet_file=identity, request_file=_pin(request_path),
        declaration=declaration, calculator_events=observed, native_invocation="not_requested", original_regular_file_bytes_unchanged=True,
        source_prefix_delivery_verified=prefix["native_proof_passed"], preserved_counts=counts,
        public_saved_read_or_recalculation_verified=False,
        qualification="One existing pure calculator over authenticated private retained sheet bytes in the explicitly selected outer bounded runtime; caller-asserted driver identity is not episode/producer custody; no Source, receipt or public saved mode is created"))


def _forbid_orf_calculation(monkeypatch):
    for module in (driver, orf_measurements):
        monkeypatch.setattr(module, "calculate_orf_components", _forbidden)
        monkeypatch.setattr(module, "build_orf_sheet", _forbidden)


def _recorded_orf_model_calls(store, prefix, *, run_id=RUN_ID):
    """Join original dispatch evidence to its actual immutable journal payloads."""
    calls = [dict(row) for row in store.db.execute("SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid", (run_id,))]
    dispatches = prefix["scripted_provider_dispatches"]
    assert len(calls) == len(dispatches) == prefix["scripted_dispatches"] == 2
    for call, dispatch in zip(calls, dispatches):
        request = json.loads(call["request"])
        assert call["run_id"] == run_id and call["episode_id"] == dispatch["episode_id"]
        assert call["call_index"] == 0 and call["purpose"] == "decision" and dispatch["role"] == "REASONING"
        assert json.loads(call["response"]) == dispatch["response"]
        # The original prefix retains the actually supplied generation-schema
        # digest. Regenerating after canonical JSON reordered properties would
        # reorder strict required arrays and cannot prove its original bytes.
        generation_sha = dispatch["output_schema_sha256"]
        assert type(generation_sha) is str and len(generation_sha) == 64 and set(generation_sha) <= set("0123456789abcdef")
        Draft202012Validator(request["schema"]).validate(
            _decode_action_response(json.loads(call["response"]), request["schema"]))
        assert request["context"]["goal"]["objective"] == QUESTION
        assert request["context"]["scope"] == prefix["scope"]
    return calls


def _closed_orf_return(workflow, *, scope, parent, science):
    """Use the authenticated closed unit, retaining the existing live-child path."""
    root = workflow.build("annotation", "root", QUESTION, scope)
    completed = asyncio.run(root.run_async(workflow.context))
    final = plain(asyncio.run(root.build_result(completed)).as_record())
    commission = workflow.journal.row("runtime_actions", parent.episode_id, 0)
    selected = workflow.selected(root.source, json.loads(commission["action"]), 0)
    if isinstance(selected, ClosedChildUnit):
        assert selected.record.run_id == science.run_id
        assert selected.record.episode_id == science.episode_id and selected.record.path == science.path
        assert selected.record.archived_record is not None
        assert plain(selected.request.as_record()) == plain(science.request)
        assert plain(selected.record.request.as_record()) == plain(science.request)
        return final, plain(selected.result.as_record())
    child = selected.child
    assert child.source.episode_id == science.episode_id and plain(child.request.as_record()) == plain(science.request)
    current = workflow.context
    boundary = type(current).from_commission(tree=current.tree, run_id=workflow.run_id,
        parent_path=root.source.path, parent_goal_id=root.goal.goal_id,
        child_goal_id=child.goal.goal_id, grain=child.grain.name, key=child.key)
    try:
        workflow.context = boundary
        closed = asyncio.run(child.run_async(boundary))
        returned = plain(asyncio.run(child.build_result(closed)).as_record())
    finally:
        workflow.context = current
    return final, returned


def _forbid_scientific_files(monkeypatch):
    blocked = []
    def reject(*args, **kwargs):
        blocked.append(dict(arguments=[str(value) for value in args[1:]], keywords=sorted(kwargs)))
        raise AssertionError("closed ORF replay reopened a scientific File")
    monkeypatch.setattr(Store, "get_artifact", reject)
    monkeypatch.setattr("gene_annotation_episode.materials._verified_artifact_path", reject)
    monkeypatch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", reject)
    return blocked


def test_retained_orf_original_parent_recovery_without_new_science(tmp_path, monkeypatch):
    selected_path, selected = _retained_prefix(require_delivery=False, require_native=False)
    assert selected["native_execution_verified"] is selected["native_proof_passed"] is False
    assert selected["factory"].get("molecular_sequence_saved_modes", False) is False
    original_before = _inventory(Path(selected["test_root"]))
    owned = tmp_path / "owned-native-recovery"
    copied, original_tables = _clone_retained(selected, owned)
    prefix_path = owned / PREFIX_NAME
    proof = deepcopy(selected)
    proof.pop("test_failure", None)
    proof.update(test_root=str(owned), store_directory=str(copied), workflow_directory=str(owned / "run"),
        original_native_prefix_file=_pin(selected_path), original_test_failure=selected.get("test_failure"),
        original_scripted_provider_dispatches=deepcopy(selected["scripted_provider_dispatches"]),
        native_execution_verified=False, native_proof_passed=False,
        recovery=dict(kind="original_pending_parent_delivery", new_model_dispatches=0,
            new_native_calls=0, new_calculator_calls=0, original_factory_unchanged=True))
    _write(prefix_path, proof)
    _forbid_native(monkeypatch)
    _forbid_orf_calculation(monkeypatch)
    try:
        with Store(copied) as store:
            assert _tables(store) == original_tables
            calls = _recorded_orf_model_calls(store, selected)
            calls_path = owned / "ORF_ORIGINAL_MODEL_CALLS.json"
            _write(calls_path, dict(original_prefix_file=_pin(selected_path), original_database_file=selected["database_file"], calls=calls))
            proof["original_model_calls_file"] = _pin(calls_path)
            tools, workflow = _reopen(selected, store, owned, PublishedORFProvider([]))
            monkeypatch.setattr(workflow.provider, "complete", _forbidden)
            operation, outcome, publication, parent, science = _publication(store, workflow, tools)
            assert outcome["status"] == "completed" and publication["stored"] == outcome["result"]
            execution = _artifact_json(store, publication["control"]["original"]["execution_file"])
            original_unit = execution["handle"]["unit"]
            original_artifacts = _inventory(store.path / "artifacts")
            original_source = deepcopy(publication["source"])
            root = workflow.build("annotation", "root", QUESTION, selected["scope"])
            try:
                completed = asyncio.run(root.run_async(workflow.context))
            finally:
                proof = _prefix(store, workflow, proof)
                _write(prefix_path, proof)
            verified = _assert_native_publication(store, workflow, tools, proof, prefix_path, recorded_calls=calls)
            final = plain(asyncio.run(root.build_result(completed)).as_record())
            assert final == {"credit": 0, "pending_handles": []}
            assert verified["original_native_unit"] == original_unit
            assert store.get(original_source["id"]) == original_source
            assert _inventory(store.path / "artifacts") == original_artifacts
            before_tables, before_run = _tables(store), _inventory(owned / "run")
            with monkeypatch.context() as replay:
                replay.setattr(ToolRegistry, "execute_async", _forbidden)
                blocked = _forbid_scientific_files(replay)
                replay_final, replay_child = _closed_orf_return(workflow, scope=selected["scope"], parent=parent, science=science)
            assert replay_final == final and replay_child == {"form": verified["returned"]}
            assert blocked == [] and workflow.provider.contexts == workflow.provider.dispatches == []
            assert _tables(store) == before_tables and _inventory(owned / "run") == before_run
            assert [dict(row) for row in store.db.execute("SELECT * FROM runtime_model_calls ORDER BY rowid")] == calls
            assert _inventory(Path(selected["test_root"])) == original_before
            proof.update(verified, final_result=final, native_execution_verified=True, native_proof_passed=True,
                recovery_child_result=replay_child, public_saved_read_or_recalculation_verified=False)
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (copied / "state.sqlite3").is_file():
            proof["database_file"] = _pin(copied / "state.sqlite3")
        _write(prefix_path, proof)


def _orf_run_counts(store, run_id):
    result = {name: store.db.execute("SELECT count(*) FROM " + name + " WHERE run_id=?", (run_id,)).fetchone()[0]
        for name in COUNTS if name != "tool_operations"}
    result["tool_operations"] = store.db.execute("SELECT count(*) FROM tool_operations operation JOIN runtime_actions action "
        "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index WHERE action.run_id=?",
        (run_id,)).fetchone()[0]
    return result


def _saved_orf_privacy(store, workflow, contexts, *, sources, input_file, baseline_artifacts):
    private = set()
    for source in sources:
        private.update((source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]))
    private.discard(input_file["artifact_ref"])
    evidence = []
    for context in contexts:
        known = set(workflow.receipts.known(context.episode_id))
        assert {reference for reference in known if reference.startswith("artifact_")} == baseline_artifacts
        assert private.isdisjoint(known)
        resolver = workflow.resolver(plain(context.scope), context=context)
        assert resolver(input_file["artifact_ref"], "artifact") is True
        for reference in private:
            assert resolver(reference, "artifact") is False
        for reference in sorted(private):
            denied, path = workflow.services.read_received_molecular_input(context, reference, "artifact", file_format="json")
            assert denied["failure"] is not None and path is None
        assert set(workflow.receipts.known(context.episode_id)) == known
        evidence.append(dict(episode_id=context.episode_id, known_refs=sorted(known),
            baseline_artifact_refs=sorted(baseline_artifacts), new_artifact_refs=[], private_output_artifact_refs=[]))
    return evidence


def _forbid_original_input_bytes(monkeypatch, reference):
    """Guard a saved operation/read while preserving its real baseline receipt."""
    blocked = []
    actual_get = Store.get_artifact
    actual_verified = retained_native_file.__globals__["_verified_artifact_path"]
    def check(selected):
        if selected == reference:
            blocked.append(selected)
            raise AssertionError("saved ORF work reopened the original Input File")
    def get(current, selected, *args, **kwargs):
        check(selected)
        return actual_get(current, selected, *args, **kwargs)
    def verified(current, selected, *args, **kwargs):
        check(selected)
        return actual_verified(current, selected, *args, **kwargs)
    monkeypatch.setattr(Store, "get_artifact", get)
    monkeypatch.setattr("gene_annotation_episode.materials._verified_artifact_path", verified)
    monkeypatch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", verified)
    return blocked


def _assert_saved_orf_values(public, custody, prefix):
    """Keep literal science equal while checking its actual retention authority."""
    source = custody["source_files"]["components"]
    derived = custody["version"] == contracts.ORDINARY_ORF_SAVED_CUSTODY_VERSION
    expected_state = "retained_undeclared" if derived else "retained"
    assert source["state"] == expected_state and source["failure"] is None
    if derived:
        assert source["declared"] is None
    else:
        assert source == prefix["custody"]["source_files"]["components"]
    assert source["observed_identity"] == {key: source["file"][key] for key in ("sha256", "size_bytes")}
    assert custody["source_files"]["sheet"] == prefix["custody"]["source_files"]["sheet"]
    assert public["file_states"] == {role: custody["source_files"][role]["state"]
        for role in ("capture", "sheet", "components")}
    assert public["values"]["source_states"] == dict(sheet="retained", components=expected_state)
    assert public["values"]["source_sheet_ref"] == prefix["role_files"]["sheet"]["artifact_ref"]
    assert public["values"]["source_components_ref"] == source["file"]["artifact_ref"]
    assert public["values"]["source_kind"] == ("selected_saved_calculation" if derived else "original_stored")
    original_values = prefix["public"]["values"]
    for field in ("schema", "operation", "components_schema", "original_attempt_association", "failures"):
        assert same(public["values"][field], original_values[field])
    assert len(public["values"]["rows"]) == len(original_values["rows"]) == 2
    for cell, original, expected in zip(public["values"]["rows"], original_values["rows"], ([DNA, "MK", 0, 9, "+", 1], 9)):
        assert cell["value_state"] == "stored_value" and same(cell["value"], expected)
        assert cell["source_ref"] == source["file"]["artifact_ref"] and cell["source_state"] == expected_state
        for field in ("row_id", "field", "value_state", "value", "source_pointer", "unit", "population_id", "denominators"):
            assert same(cell[field], original[field])
        assert cell["denominators"] == []  # Neither selected field has a denominator operand.
        qualifiers, original_qualifiers = cell["scientific_qualifiers"], original["scientific_qualifiers"]
        assert {key: value for key, value in qualifiers.items() if key != "states"} == {
            key: value for key, value in original_qualifiers.items() if key != "states"}
        assert set(qualifiers["states"]) == set(original_qualifiers["states"])
        for name, state in qualifiers["states"].items():
            assert state["source_ref"] == source["file"]["artifact_ref"] and state["source_state"] == expected_state
            assert {key: value for key, value in state.items() if key not in ("source_ref", "source_state")} == {
                key: value for key, value in original_qualifiers["states"][name].items()
                if key not in ("source_ref", "source_state")}


def _verify_public_saved_orf_phase(store, prefix, directory, *, record, tools, workflow, sources,
        monkeypatch, recorded=False, calls_path=None):
    """One post-execution verifier for fresh work and an authenticated old action."""
    run_id, mode, arguments = record["run_id"], record["mode"], record["arguments"]
    result_ref = arguments["result_ref"]
    baseline_artifacts = set(record["baseline_artifact_refs"])
    assert baseline_artifacts == {prefix["input_file"]["artifact_ref"]}
    assert record["initial_known_record_refs"] == [result_ref]
    assert record["calculator_events"] == (["call", "return"] if mode == "calculate_saved" else [])
    assert _orf_run_counts(store, run_id) == record["counts"] == COUNTS
    assert [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? ORDER BY rowid", (run_id,))] == record["actual_actions"]
    factory_record = record["factory"]
    assert factory_record.get("molecular_sequence_saved_modes") is True
    assert "molecular_sequence_environments" not in factory_record
    assert not any("native_molecular_sequence" in resource for resource in factory_record["resources"].values())
    assert list((directory / "saved-workspace").iterdir()) == []
    records = EpisodeReturnRecords(store, run_id, failure_prefix="ordinary_orf_saved_proof_")
    episodes = list(store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
    assert len(episodes) == 2
    parent, science = [records.context(row["episode_id"]) for row in episodes]
    key = f"{run_id}:{science.episode_id}:0"
    operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
    assert operation is not None and json.loads(operation["arguments"]) == arguments
    outcome = json.loads(operation["result"])
    assert outcome["status"] == "completed" and outcome["record_refs"] == [outcome["result"]["source_ref"]]
    assert outcome["changed_record_refs"] == ([] if mode == "read_stored" else outcome["record_refs"])
    action = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
        (run_id, science.episode_id)).fetchone()
    assert json.loads(action["action"]) == dict(kind="tool", tool=contracts.ORDINARY_ORF_TOOL, arguments=arguments)
    assert same({key: value for key, value in json.loads(action["result"]).items() if key != "pending_work_after_action"}, outcome)
    owner = tools.molecular_sequence_results_for(run_id)
    assert owner is workflow.episode_bindings.for_role("results").molecular_sequence_results
    assert owner.owner.services is workflow.services and owner.owner.tool_registry is tools
    with monkeypatch.context() as guarded:
        attempts = _forbid_original_input_bytes(guarded, prefix["input_file"]["artifact_ref"])
        try:
            public = owner.read_ordinary_orf_action_result(science, arguments, key,
                read_received=workflow.services.read_received_molecular_input)
            assert public == outcome["result"]
            publication = owner.read_ordinary_orf_publication(science, public["source_ref"],
                read_received=workflow.services.read_received_molecular_input)
        finally:
            record["input_file_read_attempts"].extend(attempts)
    assert publication["stored"] == public and public["selection"]["rows"] == ROWS and public["failures"] == []
    source, custody = publication["source"], publication["control"]
    if mode == "read_stored":
        assert source["id"] == result_ref
    else:
        assert source["id"] != result_ref and source["parent_source_refs"] == [result_ref]
        assert custody["version"] == contracts.ORDINARY_ORF_SAVED_CUSTODY_VERSION
        assert custody["original_source"]["source_ref"] == result_ref
        assert custody["calculation"]["native_call_state"] == "not_requested"
        assert custody["calculation"]["state"] == "returned" and custody["calculation"]["call_count"] == 1
        assert public["file_states"] == dict(capture="not_requested", sheet="retained", components="retained_undeclared")
        admitted = _artifact_json(store, custody["request"]["source_admission_file"])
        assert admitted["failure"] is None and admitted["selection"] == dict(reference=result_ref, namespace="source")
        assert admitted["input"]["receiver"]["run_id"] == run_id
        assert admitted["input"]["receiver"]["episode_id"] == science.episode_id
    assert source["provider"] == contracts.ORDINARY_ORF_TOOL and source["version"] == contracts.ORDINARY_ORF_SOURCE_VERSION
    _assert_saved_orf_values(public, custody, prefix)
    producers = [dict(row) for row in store.db.execute("SELECT operation.operation_key,action.run_id,action.episode_id "
        "FROM tool_operations operation JOIN runtime_actions action "
        "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index "
        "WHERE operation.name=? AND json_extract(operation.result,'$.result.source_ref')=? "
        "AND (json_extract(operation.arguments,'$.mode') IS NULL OR json_extract(operation.arguments,'$.mode')='calculate_saved')",
        (contracts.ORDINARY_ORF_TOOL, source["id"]))]
    assert len(producers) == 1
    assert (producers[0]["operation_key"] == key) is (mode == "calculate_saved")
    with monkeypatch.context() as guarded:
        attempts = _forbid_original_input_bytes(guarded, prefix["input_file"]["artifact_ref"])
        try:
            assert workflow.services.molecular_own_facts(science, fact_source="orf_measurements") == [public]
            assert workflow.services.molecular_frozen_facts(science, fact_source="orf_measurements") == [public]
            assert workflow.services.molecular_received_facts(parent, fact_source="orf_measurements") == [public]
        finally:
            record["input_file_read_attempts"].extend(attempts)
    form, = list(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?", (run_id, science.episode_id)))
    returned = json.loads(form["form"])
    assert returned == {"measurements": [public]}
    delivery, = list(store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=?", (run_id, parent.episode_id)))
    assert delivery["failure"] is None and json.loads(delivery["form"]) == returned
    privacy = _saved_orf_privacy(store, workflow, (parent, science), sources=[*sources, source],
        input_file=prefix["input_file"], baseline_artifacts=baseline_artifacts)
    assert record["input_file_read_attempts"] == []
    calls = _recorded_orf_model_calls(store, dict(scripted_provider_dispatches=record["scripted_provider_dispatches"],
        scripted_dispatches=2, scope=prefix["scope"]), run_id=run_id)
    calls_path = directory / "ORF_SAVED_MODEL_CALLS.json" if calls_path is None else calls_path
    _write(calls_path, dict(run_id=run_id, calls=calls))
    with monkeypatch.context() as closed:
        _forbid_orf_calculation(closed)
        closed.setattr(workflow.provider, "complete", _forbidden)
        closed.setattr(ToolRegistry, "execute_async", _forbidden)
        first_blocked = _forbid_scientific_files(closed)
        final, child = _closed_orf_return(workflow, scope=prefix["scope"], parent=parent, science=science)
    assert final == {"credit": 0, "pending_handles": []} and child == {"form": returned} and first_blocked == []
    assert _orf_run_counts(store, run_id) == COUNTS
    before_tables, before_artifacts, before_run = _tables(store), _inventory(store.path / "artifacts"), _inventory(directory)
    with monkeypatch.context() as frozen:
        _forbid_orf_calculation(frozen)
        frozen.setattr(workflow.provider, "complete", _forbidden)
        frozen.setattr(ToolRegistry, "execute_async", _forbidden)
        blocked = _forbid_scientific_files(frozen)
        frozen_final, frozen_child = _closed_orf_return(workflow, scope=prefix["scope"], parent=parent, science=science)
    assert frozen_final == final and frozen_child == {"form": returned} and blocked == []
    assert _tables(store) == before_tables and _inventory(store.path / "artifacts") == before_artifacts
    assert _inventory(directory) == before_run
    if recorded:
        assert workflow.provider.contexts == workflow.provider.dispatches == []
    else:
        assert len(workflow.provider.contexts) == len(workflow.provider.dispatches) == 2
        assert workflow.provider.dispatches == record["scripted_provider_dispatches"]
    assert calls == [dict(row) for row in store.db.execute("SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid", (run_id,))]
    record.update(passed=True, source=source, public=public, custody_version=custody["version"], custody_intent=custody["intent"],
        source_files=custody["source_files"], original_source=custody.get("original_source"), calculation=custody.get("calculation"),
        operation=dict(operation), producer=producers[0], returned=returned, final_result=final, privacy=privacy,
        model_calls_file=_pin(calls_path), frozen_direct_child=frozen_child, reopened_scientific_files=blocked,
        recorded_phase_recovery=recorded, new_model_dispatches=0 if recorded else 2)
    return record


def _public_saved_orf_phase(store, prefix, directory, *, mode, result_ref, sources, monkeypatch):
    """One real commission/tool/form in a new saved-only run on the owned Store."""
    directory.mkdir()
    run_id = RUN_ID + "-saved-" + directory.name
    arguments = dict(mode=mode, result_ref=result_ref, rows=deepcopy(ROWS))
    initial = [result_ref]
    workspace = directory / "saved-workspace"
    workspace.mkdir()
    resources = {"saved-only": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY))}
    factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
        molecular_sequence_environments=[], molecular_sequence_saved_modes=True)
    record = dict(run_id=run_id, mode=mode, arguments=arguments, initial_known_record_refs=initial,
        factory=factory.as_record(), passed=False, native_call_state="not_requested", calculator_events=[], input_file_read_attempts=[],
        input_file_read_guard_scope=["saved_operation", "Source_owner_reads", "molecular_fact_reads"],
        initial_context_input_handling="preserved_scoped_baseline_admission")
    phase_path = directory / "ORF_SAVED_PHASE.json"
    _write(phase_path, record)
    try:
        tools = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
        factory.configure_tool_registry(tools)
        scientific = prepare_scientific_binding(run_directory=directory, source_directory=ROOT / PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=["scientific_process"])
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        provider = PublishedORFProvider([_commission(library, prefix["scope"]), dict(selection=dict(kind="tool",
            tool=contracts.ORDINARY_ORF_TOOL, arguments=arguments), report_update={})], library=library)
        workflow = _workflow(store, tools, provider, directory, factory, scientific, initial, run_id=run_id)
        root = workflow.build("annotation", "root", QUESTION, prefix["scope"])
        baseline = set(workflow.receipts.known(root.source.episode_id))
        baseline_artifacts = {reference for reference in baseline if reference.startswith("artifact_")}
        # Workflow.build always admits scoped subjects; INPUT forward refs
        # legitimately carry their sequence File. The received ORF Source adds
        # no private File. Saved work below must not depend on that Input File.
        assert {prefix["subject_ref"], result_ref, prefix["input_file"]["artifact_ref"]} <= baseline
        assert baseline_artifacts == {prefix["input_file"]["artifact_ref"]}
        record.update(baseline_record_refs=sorted(baseline), baseline_artifact_refs=sorted(baseline_artifacts))
        previous = sys.getprofile()
        code = orf_measurements.calculate_orf_components.__code__
        def observe(frame, event, value):
            if previous is not None:
                previous(frame, event, value)
            if frame.f_code is code and event in ("call", "return"):
                record["calculator_events"].append(event)
        try:
            if mode == "calculate_saved":
                sys.setprofile(observe)
            with monkeypatch.context() as saved_work:
                actual_execute = molecular_tools.OrdinaryMolecularSequenceTools.execute
                async def execute_without_input(current, arguments, *, scope, operation_key, authority):
                    with saved_work.context() as guarded:
                        attempts = _forbid_original_input_bytes(guarded, prefix["input_file"]["artifact_ref"])
                        try:
                            return await actual_execute(current, arguments, scope=scope, operation_key=operation_key, authority=authority)
                        finally:
                            record["input_file_read_attempts"].extend(attempts)
                saved_work.setattr(molecular_tools.OrdinaryMolecularSequenceTools, "execute", execute_without_input)
                for name in ("molecular_own_facts", "molecular_frozen_facts", "molecular_received_facts"):
                    actual_fact = getattr(type(workflow.services), name)
                    def fact_without_input(current, *args, _actual=actual_fact, **kwargs):
                        with saved_work.context() as guarded:
                            attempts = _forbid_original_input_bytes(guarded, prefix["input_file"]["artifact_ref"])
                            try:
                                return _actual(current, *args, **kwargs)
                            finally:
                                record["input_file_read_attempts"].extend(attempts)
                    saved_work.setattr(type(workflow.services), name, fact_without_input)
                completed = asyncio.run(root.run_async(workflow.context))
        finally:
            sys.setprofile(previous)
            record.update(counts=_orf_run_counts(store, run_id), actual_actions=[dict(row) for row in store.db.execute(
                "SELECT * FROM runtime_actions WHERE run_id=? ORDER BY rowid", (run_id,))],
                scripted_provider_dispatches=deepcopy(provider.dispatches))
            _write(phase_path, record)
        assert factory.as_record() == record["factory"]
        return _verify_public_saved_orf_phase(store, prefix, directory, record=record, tools=tools,
            workflow=workflow, sources=sources, monkeypatch=monkeypatch)
    except BaseException as error:
        record["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        _write(phase_path, record)


def test_retained_orf_public_saved_modes_and_closed_replay(tmp_path, monkeypatch):
    prefix_path, prefix = _retained_prefix()
    assert prefix["recovery"]["kind"] == "original_pending_parent_delivery"
    assert prefix["recovery"]["new_model_dispatches"] == 0
    assert prefix["factory"].get("molecular_sequence_saved_modes", False) is False
    assert _pin(prefix["original_native_prefix_file"]["path"]) == prefix["original_native_prefix_file"]
    original_before = _inventory(Path(prefix["test_root"]))
    owned = tmp_path / "owned-public-saved"
    copied, original_tables = _clone_retained(prefix, owned)
    _forbid_native(monkeypatch)
    monkeypatch.setattr(driver, "run_molecular_sequence_driver", _forbidden)
    monkeypatch.setattr(driver, "build_orf_sheet", _forbidden)
    monkeypatch.setattr(orf_measurements, "build_orf_sheet", _forbidden)
    proof = dict(prefix_file=_pin(prefix_path), original_native_prefix_file=prefix["original_native_prefix_file"],
        original_source_ref=prefix["source"]["id"], original_native_unit=prefix["original_native_unit"], phases=[], passed=False)
    proof_path = tmp_path / "ORF_PUBLIC_SAVED_MODES.json"
    _write(proof_path, proof)
    try:
        with Store(copied) as store:
            assert _tables(store) == original_tables
            source = deepcopy(store.get(prefix["source"]["id"]))
            original_artifacts = _inventory(store.path / "artifacts")
            execution = _artifact_json(store, prefix["custody"]["original"]["execution_file"])
            assert execution["handle"]["unit"] == prefix["original_native_unit"]
            assert execution["terminal"] is execution["quiescent"] is True and execution["returncode"] == 0
            with monkeypatch.context() as literal:
                _forbid_orf_calculation(literal)
                read_original = _public_saved_orf_phase(store, prefix, owned / "read-original", mode="read_stored",
                    result_ref=source["id"], sources=[source], monkeypatch=literal)
            proof["phases"].append(read_original)
            _write(proof_path, proof)
            assert read_original["public"] == prefix["public"]
            calculated = _public_saved_orf_phase(store, prefix, owned / "calculate-original", mode="calculate_saved",
                result_ref=source["id"], sources=[source], monkeypatch=monkeypatch)
            proof["phases"].append(calculated)
            _write(proof_path, proof)
            with monkeypatch.context() as literal:
                _forbid_orf_calculation(literal)
                read_derived = _public_saved_orf_phase(store, prefix, owned / "read-derived", mode="read_stored",
                    result_ref=calculated["source"]["id"], sources=[source, calculated["source"]], monkeypatch=literal)
            proof["phases"].append(read_derived)
            assert read_derived["public"] == calculated["public"]
            assert read_original["producer"]["run_id"] == RUN_ID
            assert calculated["producer"]["run_id"] == calculated["run_id"]
            assert read_derived["producer"] == calculated["producer"]
            assert store.get(source["id"]) == source == prefix["source"]
            current_artifacts = _inventory(store.path / "artifacts")
            assert all(current_artifacts[name] == pin for name, pin in original_artifacts.items())
            current_tables = _tables(store)
            assert all(set(rows) <= set(current_tables[name]) for name, rows in original_tables.items())
            assert _artifact_json(store, prefix["role_files"]["components"])["rows"][0]["native_row"] == [DNA, "MK", 0, 9, "+", 1]
            assert _artifact_json(store, prefix["role_files"]["components"])["rows"][0]["interval_length_nt"] == 9
            assert _artifact_json(store, prefix["custody"]["original"]["execution_file"]) == execution
            assert _inventory(Path(prefix["test_root"])) == original_before
            proof.update(passed=True, original_factory_unchanged=True, original_artifact_bytes_unchanged=True,
                original_rows_unchanged=True, new_native_calls=0, public_saved_read_or_recalculation_verified=True,
                calculator_events=calculated["calculator_events"], baseline_input_file_receipt_preserved=True,
                new_source_output_file_receipts=0,
                qualification="Three fresh actual saved-only runs; one existing calculator call; scoped Input File receipt preserved while saved operations/owner/facts require no Input File bytes; Source outputs grant no additional Files")
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (copied / "state.sqlite3").is_file():
            proof["owned_database_file"] = _pin(copied / "state.sqlite3")
        _write(proof_path, proof)


def _retained_public_saved_checkpoint():
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_SAVED_RETAINED_PREFIX")
    selected_sha = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_SAVED_RETAINED_SHA256")
    if not supplied or not selected_sha or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("requires the separately selected saved-phase checkpoint and its byte digest")
    path = Path(supplied).resolve(strict=True)
    assert path.name == "ORF_PUBLIC_SAVED_MODES.json" and _pin(path)["sha256"] == selected_sha
    checkpoint = _json(path)
    assert checkpoint["passed"] is False and checkpoint["test_failure"]["exception_type"] == "AssertionError"
    assert len(checkpoint["phases"]) == 1
    assert _pin(checkpoint["prefix_file"]["path"]) == checkpoint["prefix_file"]
    prefix = _json(checkpoint["prefix_file"]["path"])
    assert prefix["version"] == PREFIX_VERSION and prefix["run_id"] == RUN_ID
    assert prefix["question"] == QUESTION and prefix["input_file"]["sha256"] == DNA_SHA256
    assert prefix["native_execution_verified"] is prefix["native_proof_passed"] is True
    assert prefix["factory"].get("molecular_sequence_saved_modes", False) is False
    assert prefix["source"]["id"] == checkpoint["original_source_ref"]
    assert prefix["original_native_unit"] == checkpoint["original_native_unit"]
    assert prefix["original_native_prefix_file"] == checkpoint["original_native_prefix_file"]
    assert _pin(checkpoint["original_native_prefix_file"]["path"]) == checkpoint["original_native_prefix_file"]
    original = path.parent / "owned-public-saved"
    assert Path(checkpoint["owned_database_file"]["path"]) == original / "store" / "state.sqlite3"
    assert _pin(checkpoint["owned_database_file"]["path"]) == checkpoint["owned_database_file"]
    assert not Path(checkpoint["owned_database_file"]["path"] + "-wal").exists()
    phases = []
    for name, mode in (("read-original", "read_stored"), ("calculate-original", "calculate_saved")):
        phase_path = original / name / "ORF_SAVED_PHASE.json"
        phase = _json(phase_path)
        assert phase["run_id"] == RUN_ID + "-saved-" + name and phase["mode"] == mode
        assert phase["arguments"] == dict(mode=mode, result_ref=prefix["source"]["id"], rows=ROWS)
        assert phase["counts"] == COUNTS and phase["native_call_state"] == "not_requested"
        assert phase["input_file_read_attempts"] == []
        assert phase["calculator_events"] == (["call", "return"] if mode == "calculate_saved" else [])
        if mode == "read_stored":
            assert phase["passed"] is True and phase == checkpoint["phases"][0]
        else:
            assert phase["passed"] is False and phase["test_failure"]["exception_type"] == "AssertionError"
        phases.append(dict(directory=name, file=_pin(phase_path), record=phase))
    return path, checkpoint, prefix, original, phases


def _reopen_public_saved_phase(store, phase, directory):
    """Bind the actual retained libraries and factory, without recompiling a catalog."""
    tools = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
    factory = ExecutionServiceFactory.from_record(phase["factory"])
    assert factory.as_record() == phase["factory"]
    factory.configure_tool_registry(tools)
    scientific = ScientificProcessEpisodes(None,
        library=ScientificProcessLibrary(directory / "scientific-process-library"),
        tool_library=ScientificToolLibrary(directory / "scientific-tool-library"),
        child_roles=["scientific_process"]).as_record()
    workflow = _workflow(store, tools, PublishedORFProvider([]), directory, factory, scientific,
        phase["initial_known_record_refs"], run_id=phase["run_id"])
    return tools, workflow


def test_retained_orf_completed_saved_calculation_recovery_and_public_derived_read(tmp_path, monkeypatch):
    selected_path, selected, prefix, original, phases = _retained_public_saved_checkpoint()
    original_before = _inventory(selected_path.parent)
    owned = tmp_path / "owned-saved-recovery"
    copied, original_tables = _clone_retained(dict(store_directory=str(original / "store"),
        workflow_directory=str(original / "run")), owned)
    for phase in phases:
        shutil.copytree(original / phase["directory"], owned / phase["directory"])
    proof_path = tmp_path / "ORF_PUBLIC_SAVED_RECOVERY.json"
    proof = dict(version="ordinary_orf_saved_phase_recovery_v1", original_checkpoint_file=_pin(selected_path),
        original_checkpoint_failure=deepcopy(selected["test_failure"]), original_phase_files=[phase["file"] for phase in phases],
        original_database_file=selected["owned_database_file"], native_prefix_file=selected["prefix_file"],
        original_native_prefix_file=selected["original_native_prefix_file"], original_source_ref=selected["original_source_ref"],
        original_native_unit=selected["original_native_unit"], recovered_phases=[], passed=False,
        new_native_calls=0, new_calculator_calls=0, retained_recovery_model_dispatches=0)
    _write(proof_path, proof)
    calculator_code = orf_measurements.calculate_orf_components.__code__
    previous = sys.getprofile()
    def forbid_calculator(frame, event, value):
        if previous is not None:
            previous(frame, event, value)
        if event == "call" and frame.f_code is calculator_code:
            raise AssertionError("retained saved recovery invoked the existing ORF calculator")
    _forbid_native(monkeypatch)
    _forbid_orf_calculation(monkeypatch)
    monkeypatch.setattr(driver, "run_molecular_sequence_driver", _forbidden)
    sys.setprofile(forbid_calculator)
    try:
        with Store(copied) as store:
            assert _tables(store) == original_tables
            original_source = deepcopy(store.get(prefix["source"]["id"]))
            assert original_source == prefix["source"]
            original_artifacts = _inventory(store.path / "artifacts")
            execution = _artifact_json(store, prefix["custody"]["original"]["execution_file"])
            assert execution["handle"]["unit"] == prefix["original_native_unit"]
            assert execution["terminal"] is execution["quiescent"] is True and execution["returncode"] == 0
            recovered = []
            for phase in phases:
                record = deepcopy(phase["record"])
                record.update(original_phase_file=phase["file"], original_passed=record["passed"],
                    original_test_failure=record.pop("test_failure", None))
                tools, workflow = _reopen_public_saved_phase(store, record, owned / phase["directory"])
                monkeypatch.setattr(workflow.provider, "complete", _forbidden)
                with monkeypatch.context() as retained:
                    retained.setattr(ToolRegistry, "execute_async", _forbidden)
                    verified = _verify_public_saved_orf_phase(store, prefix, owned / phase["directory"],
                        record=record, tools=tools, workflow=workflow, sources=[original_source], monkeypatch=retained,
                        recorded=True, calls_path=owned / (phase["directory"] + "-ORIGINAL_MODEL_CALLS.json"))
                recovered.append(verified)
                proof["recovered_phases"].append(verified)
                _write(proof_path, proof)
                assert _tables(store) == original_tables
                assert _pin(owned / phase["directory"] / "ORF_SAVED_PHASE.json")["sha256"] == phase["file"]["sha256"]
            read_original, calculated = recovered
            assert read_original["public"] == prefix["public"]
            derived_source = deepcopy(store.get(calculated["source"]["id"]))
            assert derived_source == calculated["source"] and derived_source["id"] != original_source["id"]
            derived_before = _inventory(store.path / "artifacts")
            # The only new scientific action is a genuine public literal read.
            read_derived = _public_saved_orf_phase(store, prefix, owned / "read-derived-recovery", mode="read_stored",
                result_ref=derived_source["id"], sources=[original_source, derived_source], monkeypatch=monkeypatch)
            proof["derived_read"] = read_derived
            assert read_derived["public"] == calculated["public"]
            assert read_original["producer"]["run_id"] == RUN_ID
            assert calculated["producer"]["run_id"] == calculated["run_id"]
            assert read_derived["producer"] == calculated["producer"]
            assert read_derived["calculator_events"] == [] and read_derived["new_model_dispatches"] == 2
            assert store.get(original_source["id"]) == original_source and store.get(derived_source["id"]) == derived_source
            assert _artifact_json(store, prefix["custody"]["original"]["execution_file"]) == execution
            assert _artifact_json(store, prefix["role_files"]["components"])["rows"][0]["native_row"] == [DNA, "MK", 0, 9, "+", 1]
            assert _artifact_json(store, prefix["role_files"]["components"])["rows"][0]["interval_length_nt"] == 9
            current_artifacts = _inventory(store.path / "artifacts")
            assert all(current_artifacts[name] == pin for name, pin in original_artifacts.items())
            assert all(current_artifacts[name] == pin for name, pin in derived_before.items())
            current_tables = _tables(store)
            assert all(set(rows) <= set(current_tables[name]) for name, rows in original_tables.items())
            assert _inventory(selected_path.parent) == original_before
            proof.update(passed=True, public_saved_read_or_recalculation_verified=True,
                original_factory_unchanged=True, original_failed_checkpoint_unchanged=True,
                original_rows_and_sources_unchanged=True, retained_qualification="retained_undeclared",
                original_calculator_events=calculated["calculator_events"], fresh_public_read_count=1,
                fresh_public_read_model_dispatches=2, baseline_input_file_receipt_preserved=True,
                new_source_output_file_receipts=0)
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        sys.setprofile(previous)
        if (copied / "state.sqlite3").is_file():
            proof["owned_database_file"] = _pin(copied / "state.sqlite3")
        _write(proof_path, proof)



def _closed_orf_inventory(directory, *, sqlite_files=True):
    """Byte and mode inventory; SQLite contents are also compared as raw rows."""
    result = {}
    for path in sorted(Path(directory).rglob("*")):
        if not sqlite_files and path.name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"):
            continue
        relative = str(path.relative_to(directory))
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            result[relative] = dict(kind="symlink", target=os.readlink(path), mode=mode)
        elif path.is_file():
            result[relative] = dict(kind="file", mode=mode,
                **{key: value for key, value in _pin(path).items() if key != "path"})
        elif path.is_dir():
            result[relative] = dict(kind="directory", mode=mode)
    return result


def _closed_orf_schema(connection):
    return [tuple(row) for row in connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]


def _closed_orf_sqlite_family(directory):
    result = []
    for name in ("state.sqlite3", "state.sqlite3-shm", "state.sqlite3-wal"):
        path = Path(directory) / name
        if path.exists():
            assert path.is_file() and not path.is_symlink()
            result.append(dict(name=name, **{key: value for key, value in _pin(path).items() if key != "path"}))
    assert result and result[0]["name"] == "state.sqlite3"
    return result


def _clone_closed_orf_store(original_directory, directory, database_pin, *, family_sha256=None):
    """Copy the physical family before SQLite opens, then use standard backup."""
    original = Path(original_directory).resolve(strict=True)
    assert _pin(original / "state.sqlite3") == database_pin
    before = _closed_orf_sqlite_family(original)
    if family_sha256 is not None:
        assert digest(before) == family_sha256
    directory.mkdir()
    staging, target = directory / "sqlite-staging", directory / "store"
    staging.mkdir(); target.mkdir()
    for row in before:
        shutil.copy2(original / row["name"], staging / row["name"])
    assert _closed_orf_sqlite_family(staging) == before
    source = sqlite3.connect((staging / "state.sqlite3").as_uri() + "?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    destination = sqlite3.connect(target / "state.sqlite3")
    try:
        tables = _tables(SimpleNamespace(db=source))
        schema = _closed_orf_schema(source)
        assert len(tables) == 47
        source.backup(destination)
        assert source.total_changes == destination.total_changes == 0
        assert _tables(SimpleNamespace(db=destination)) == tables
        assert _closed_orf_schema(destination) == schema
    finally:
        destination.close(); source.close()
    assert _closed_orf_sqlite_family(original) == before
    for name in ("artifacts", "cache"):
        source_directory = original / name
        if source_directory.exists():
            shutil.copytree(source_directory, target / name, symlinks=True)
    return target, tables, schema, before


def _retained_closed_orf_saved_proof():
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_SAVED_CLOSED_PREFIX")
    selected_sha = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_SAVED_CLOSED_SHA256")
    family_sha = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ORF_SAVED_CLOSED_SQLITE_PINS_SHA256")
    if not supplied or not selected_sha or not family_sha or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("requires the explicit passed392 proof and original SQLite-family digest")
    path = Path(supplied).resolve(strict=True)
    assert path.name == "ORF_PUBLIC_SAVED_RECOVERY.json" and _pin(path)["sha256"] == selected_sha
    proof = _json(path)
    assert proof["version"] == "ordinary_orf_saved_phase_recovery_v1" and proof["passed"] is True
    assert proof["public_saved_read_or_recalculation_verified"] is True
    assert proof["new_native_calls"] == proof["new_calculator_calls"] == proof["retained_recovery_model_dispatches"] == 0
    assert proof["original_checkpoint_failure"]["exception_type"] == "AssertionError"
    for selected_pin in [proof["original_checkpoint_file"], proof["native_prefix_file"],
            proof["original_native_prefix_file"], *proof["original_phase_files"]]:
        assert _pin(selected_pin["path"]) == selected_pin
    prefix = _json(proof["native_prefix_file"]["path"])
    assert prefix["question"] == QUESTION and prefix["native_execution_verified"] is prefix["native_proof_passed"] is True
    assert prefix["source"]["id"] == proof["original_source_ref"]
    assert prefix["original_native_unit"] == proof["original_native_unit"]
    phases = [*proof["recovered_phases"], proof["derived_read"]]
    assert [(item["mode"], item["run_id"]) for item in phases] == [
        ("read_stored", RUN_ID + "-saved-read-original"),
        ("calculate_saved", RUN_ID + "-saved-calculate-original"),
        ("read_stored", RUN_ID + "-saved-read-derived-recovery")]
    assert all(item["passed"] is True and item["counts"] == COUNTS for item in phases)
    assert phases[1]["calculator_events"] == ["call", "return"]
    assert phases[0]["calculator_events"] == phases[2]["calculator_events"] == []
    database = Path(proof["owned_database_file"]["path"])
    assert database.parent.parent == path.parent / "owned-saved-recovery"
    assert _pin(database) == proof["owned_database_file"]
    assert digest(_closed_orf_sqlite_family(database.parent)) == family_sha
    return path, proof, prefix, phases, family_sha


def test_retained_orf_completed_saved_three_phase_closed_replay(tmp_path, monkeypatch):
    """Replay only the three already-closed392 paths with their literal bindings."""
    path, selected, prefix, phases, family_sha = _retained_closed_orf_saved_proof()
    original_before = _closed_orf_inventory(path.parent)
    original = Path(selected["owned_database_file"]["path"]).parent.parent
    owned = tmp_path / "owned-saved-closed"
    copied, tables, schema, family = _clone_closed_orf_store(original / "store", owned,
        selected["owned_database_file"], family_sha256=family_sha)
    for name in ("run", "read-original", "calculate-original", "read-derived-recovery"):
        shutil.copytree(original / name, owned / name, symlinks=True)
    evidence_path = tmp_path / "ORF_SAVED_CLOSED_REPLAY.json"
    evidence = dict(version="ordinary_orf_saved_closed_replay_v1", selected_proof=_pin(path),
        original_database=selected["owned_database_file"], original_sqlite_family=family,
        passed=False, phases=[], new_native_calls=None, new_calculator_calls=None,
        new_model_calls=None, new_actions=None, new_sources=None, new_receipts=None)
    _write(evidence_path, evidence)
    _forbid_native(monkeypatch)
    _forbid_orf_calculation(monkeypatch)
    monkeypatch.setattr(driver, "run_molecular_sequence_driver", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    monkeypatch.setattr(Store, "artifact", _forbidden)
    try:
        with Store(copied) as store:
            assert _tables(store) == tables and _closed_orf_schema(store.db) == schema
            for phase, name in zip(phases, ("read-original", "calculate-original", "read-derived-recovery")):
                run_id = phase["run_id"]
                records = EpisodeReturnRecords(store, run_id, failure_prefix="ordinary_orf_closed_")
                rows = list(store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
                assert len(rows) == 2 and all(row["state"] == "yielded" for row in rows)
                parent, science = [records.context(row["episode_id"]) for row in rows]
                descriptor = deepcopy(plain(science.request)["message"]["scientific_process"]["mechanics_binding"])
                assert descriptor["implementation_sha256"] == "eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa"
                assert descriptor["configuration"]["tool_library"]["catalog_sha256"] == (
                    "3b420f4821892b1b4a5c103ed075a15c9beec01fb1128438f2379459c840924d" if name == "read-derived-recovery" else
                    "852e642db380eaf7ba8ab42b70af0ddfc81d3faec17534f98610bb66a97c0638")
                factory = ExecutionServiceFactory.from_record(phase["factory"])
                assert factory.as_record() == phase["factory"]
                tools = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
                factory.configure_tool_registry(tools)
                provider = PublishedORFProvider([])
                provider.complete = _forbidden
                workflow = _workflow(store, tools, provider, owned / name, factory, descriptor,
                    phase["initial_known_record_refs"], run_id=run_id)
                assert workflow.scientific_process_binding.library.as_record() == descriptor["configuration"]["library"]
                assert workflow.scientific_process_binding.tool_library.as_record() == descriptor["configuration"]["tool_library"]
                with monkeypatch.context() as authenticated:
                    input_reads = _forbid_original_input_bytes(authenticated, prefix["input_file"]["artifact_ref"])
                    owner = tools.molecular_sequence_results_for(run_id)
                    key = f"{run_id}:{science.episode_id}:0"
                    public = owner.read_ordinary_orf_action_result(science, phase["arguments"], key,
                        read_received=workflow.services.read_received_molecular_input)
                    assert public == phase["public"]
                    assert workflow.services.molecular_own_facts(science, fact_source="orf_measurements") == [public]
                    assert workflow.services.molecular_frozen_facts(science, fact_source="orf_measurements") == [public]
                    assert workflow.services.molecular_received_facts(parent, fact_source="orf_measurements") == [public]
                    validate_frozen_molecular_return(phase["returned"], _form_schema(), [public], fact_source="orf_measurements")
                    assert input_reads == []
                with monkeypatch.context() as private:
                    denied_reads = _forbid_scientific_files(private)
                    privacy = _saved_orf_privacy(store, workflow, (parent, science),
                        sources=[store.get(selected["original_source_ref"]), store.get(phase["source"]["id"])],
                        input_file=prefix["input_file"], baseline_artifacts=set(phase["baseline_artifact_refs"]))
                    assert denied_reads == []
                assert _tables(store) == tables and _closed_orf_schema(store.db) == schema
                before_files = _closed_orf_inventory(owned, sqlite_files=False)
                with monkeypatch.context() as replay:
                    blocked = _forbid_scientific_files(replay)
                    final, child = _closed_orf_return(workflow, scope=prefix["scope"], parent=parent, science=science)
                    assert final == phase["final_result"] and child == {"form": phase["returned"]}
                    assert provider.contexts == provider.dispatches == [] and blocked == []
                assert _tables(store) == tables and _closed_orf_schema(store.db) == schema
                assert _closed_orf_inventory(owned, sqlite_files=False) == before_files
                evidence["phases"].append(dict(run_id=run_id, mode=phase["mode"], descriptor=descriptor,
                    source_ref=public["source_ref"], public_sha256=digest(public),
                    final_result=final, child_result_sha256=digest(child), permissions=privacy,
                    raw_tables_unchanged=True, files_and_modes_unchanged=True, reopened_scientific_files=blocked))
                _write(evidence_path, evidence)
            assert _tables(store) == tables and len(tables) == 47
            assert _closed_orf_schema(store.db) == schema
        assert _closed_orf_inventory(path.parent) == original_before
        for selected_pin in [selected["original_checkpoint_file"], selected["native_prefix_file"],
                selected["original_native_prefix_file"], *selected["original_phase_files"]]:
            assert _pin(selected_pin["path"]) == selected_pin
        evidence.update(passed=True, original_files_and_modes_unchanged=True,
            raw_table_count=47, all_raw_tables_unchanged=True, original_failures_preserved=True,
            new_native_calls=0, new_calculator_calls=0, new_model_calls=0,
            new_actions=0, new_sources=0, new_receipts=0)
    except BaseException as error:
        evidence["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        evidence["owned_database"] = _pin(copied / "state.sqlite3")
        _write(evidence_path, evidence)
