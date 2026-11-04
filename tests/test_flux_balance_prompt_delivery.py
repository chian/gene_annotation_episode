"""Optional FBA text-boundary control; no scientific operation is selected.

The caller explicitly supplies a completed360 Store through
HMMER_NATIVE_ORACLE_FBA_PROMPT_RETAINED. Its original actions and public outcomes
are read immutably. A fresh metadata-only commission supplies its own explicit
model/edit/resource operands, then stops before the first scientific action.
Detached original outcomes subsequently exercise presentation updates only:
they are not actions, observations or findings of the fresh Workflow.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.flux_balance_tools import ENVIRONMENT_SELECTION, FBA_TOOL
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import (
    _operation_schema_view, _registered_return_schema_view, render_scientific_process_prompt,
)
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.schema_information_text import (
    parse_schema_information, schema_fingerprint,
)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_published_axis_workflow import (
    PUBLICATION, ScriptedDecisions, StopBeforeDecision, select,
)
from test_runtime import FixtureController
from test_scientific_process_prompt_delivery import ScientificWire


DATABASE_SHA256 = "7a3e9d961da978a8bc382539dcf21f6e224f26d4ac786d571fd4d60edfae18ae"
SCIENCE_ID = "episode_4c77b4f26cd2f7238b7a98633e86010bb485840f408a2418d9f2c8844ba183fd"
QUESTION = (
    "What objective value and BC reaction flux does the supplied model support after adding C and BC, "
    "fixing AB bounds to zero, and selecting BC as objective; what changed in its reaction inventory?"
)


def _forbidden(*args, **kwargs):
    raise AssertionError("FBA text-boundary control attempted native, HTTP or model work")


def _credit(*_args, **_kwargs):
    return 0


def _artifact(store_path, reference):
    assert reference.startswith("artifact_") and len(reference) == 73
    digest = reference[9:]
    path = store_path / "artifacts" / digest[:2] / digest
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return raw


def _retained(store_path):
    """Select original declared inputs/public outcomes; never parse a model."""
    database = store_path / "state.sqlite3"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == DATABASE_SHA256
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        request = json.loads(connection.execute(
            "SELECT request FROM runtime_episodes WHERE episode_id=?", (SCIENCE_ID,)
        ).fetchone()[0])
        assert request["goal"]["objective"] == QUESTION
        rows = list(connection.execute(
            "SELECT action,result FROM runtime_actions WHERE episode_id=? ORDER BY decision_index",
            (SCIENCE_ID,),
        ))
        actions = [json.loads(row["action"]) for row in rows]
        outcomes = [json.loads(row["result"]) for row in rows]
        assert [row["arguments"]["mode"] for row in actions] == [
            "inspect", "edit", "solve", "read_stored", "read_stored", "calculate_saved",
        ]
        assert all(row["tool"] == FBA_TOOL for row in actions)
        assert all(row["status"] == "completed" for row in outcomes)
        source = json.loads(connection.execute(
            "SELECT data FROM records WHERE id=?", (outcomes[2]["result"]["source_ref"],)
        ).fetchone()[0])
        model_ref = actions[0]["arguments"]["model"]["witness_ref"]
        metadata = dict(connection.execute("SELECT * FROM artifacts WHERE id=?", (model_ref,)).fetchone())
        assert metadata["media_type"] == "application/json" and metadata["size"] == 696
        assert connection.total_changes == 0
    finally:
        connection.close()
    capsule_bytes = _artifact(store_path, source["request_ref"])
    capsule = json.loads(capsule_bytes)
    assert capsule["prepared"]["arguments"] == actions[2]["arguments"]
    selected = capsule["prepared"]["selected"]
    raw = _artifact(store_path, model_ref)
    assert len(raw) == metadata["size"]
    return {
        "request": request, "actions": actions, "outcomes": outcomes, "selected": selected,
        "model_bytes": raw,
        "model_file": {"artifact_ref": model_ref, "sha256": metadata["sha256"],
            "size_bytes": metadata["size"], "format": "cobra_json"},
        "original_hashes": {"state.sqlite3": DATABASE_SHA256,
            model_ref: metadata["sha256"], source["request_ref"]: hashlib.sha256(capsule_bytes).hexdigest()},
    }


def _rows(store):
    tables = [row[0] for row in store.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    return {name: sorted((tuple(row) for row in store.db.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"'
    )), key=repr) for name in tables}


def test_registered_return_display_requires_exact_schema():
    source = "flux_balance_measurements"
    registered = {"type": "array", "minItems": 0, "items": {"enum": [1]}, "x-source": source}
    sources = {source: {"type": "array", "meaning": "Original positions, populations and unknown units.",
        "report_schema": registered}}
    form = {"type": "object", "additionalProperties": False, "required": ["values", "metric"],
        "properties": {"values": deepcopy(registered),
            "metric": {"type": "string", "enum": ["growth", "reaction_flux"]}}}
    original = deepcopy((form, sources))
    shown = _registered_return_schema_view(form, sources)
    assert "items" not in shown["properties"]["values"]
    assert shown["properties"]["values"]["minItems"] == 0
    assert shown["properties"]["values"]["x-source"] == source
    assert sources[source]["meaning"] in shown["properties"]["values"]["description"]
    assert shown["properties"]["metric"] == form["properties"]["metric"]
    assert (form, sources) == original
    for altered_value in (True, 1.0, 2):
        altered = deepcopy(form)
        altered["properties"]["values"]["items"]["enum"] = [altered_value]
        assert _registered_return_schema_view(altered, sources) == altered
    unknown = deepcopy(form)
    unknown["properties"]["values"]["x-source"] = "flux_balance_unregistered"
    assert _registered_return_schema_view(unknown, sources) == unknown
    assert _registered_return_schema_view(form, {source: {"meaning": "No registered schema supplied."}}) == form


def test_published_schema_display_reuses_contract_without_losing_operands():
    source = "flux_balance_measurements"
    recorded = {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"value": {"type": ["number", "null"]},
            "unit": {"enum": ["unknown", "mmol/gDW/h"]},
            "population": {"type": "integer", "minimum": 0}},
        "required": ["value", "unit", "population"]}, "x-source": source}
    form = {"type": "object", "additionalProperties": False,
        "properties": {"measurements": recorded,
            "selected_metric": {"type": "string", "enum": ["growth", "reaction_flux"],
                "description": "Caller selects growth or the specified reaction flux."}},
        "required": ["measurements", "selected_metric"]}
    scalar = {"type": ["number", "null"], "minimum": 0, "default": None,
        "description": "Exact supplied bound | unknown remains null.\nPreserve zero."}
    operands = {"$id": "urn:caller:selected-operation", "type": "object",
        "additionalProperties": False,
        "properties": {"first": deepcopy(scalar), "second": deepcopy(scalar),
            "mode": {"enum": ["growth", "reaction_flux"]},
            "selection": {"const": {"type": "object", "required": ["literal_caller_data"]}}},
        "required": ["first", "second", "mode", "selection"],
        "$defs": {"original": deepcopy(scalar)}}
    state = {"goal": {"objective": "What growth or selected reaction flux is supported?",
            "result_contract": deepcopy(form)},
        "scientific_process": {"evidence_axis": {"name": "Biochemical feasibility",
            "instruction_status": "published_investigation_instructions",
            "investigation_instructions": "Retain the assigned question and supplied model."}},
        "tools": [{"name": "selected_operation", "description": "Use caller-selected operands.",
            "input_schema": operands}],
        "requested_form": form, "available_report_facts": {source: {"type": "array",
            "meaning": "Original positions, populations and units; unknown units remain unknown.",
            "report_schema": deepcopy(recorded)}}}
    before = deepcopy(state)
    text = render_scientific_process_prompt(state, "Fixed approved scientific instructions.")
    task = text.split("\n\nSTEERING\n", 1)[0]
    assert "Assigned result contract" not in task and "result_contract.properties" not in task
    assert "return.selected_metric" in task and "growth" in task and "reaction_flux" in task
    assert "return.measurements" in task and "return.measurements[]" not in task
    assert state["available_report_facts"][source]["meaning"] in task
    start = task.index("Schema information\n")
    end = task.index("\nEnd schema information\n", start) + len("\nEnd schema information\n")
    recovered = parse_schema_information(task[start:end])
    assert schema_fingerprint(recovered) == schema_fingerprint(operands)
    assert "Definition" in task and task.count("Exact supplied bound") == 1
    assert state == before
    distinct = deepcopy(state)
    distinct["goal"]["result_contract"]["properties"]["selected_metric"]["enum"] = ["growth"]
    distinct_text = render_scientific_process_prompt(distinct, "Fixed approved scientific instructions.")
    assert "Assigned result contract" in distinct_text
    start = distinct_text.index("Schema information\n")
    end = distinct_text.index("\nEnd schema information\n", start) + len("\nEnd schema information\n")
    recovered = parse_schema_information(distinct_text[start:end])
    assert recovered["properties"]["selected_metric"]["enum"] == ["growth"]
    assert "return.selected_metric" in distinct_text and "reaction_flux" in distinct_text
    host_schema = {key: deepcopy(value) for key, value in operands.items() if key != "$id"}
    host_pin = "urn:gene-annotation:ordinary-fba-tool:" + hashlib.sha256(json.dumps(
        host_schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    host_schema["$id"] = host_pin
    assert "$id" not in _operation_schema_view(host_schema)
    assert host_schema["$id"] == host_pin
    altered_pin = {**host_schema, "$id": host_pin + "altered"}
    assert _operation_schema_view(altered_pin) == altered_pin
    referenced = deepcopy(host_schema)
    referenced["properties"]["first"] = {"$ref": "#/$defs/original"}
    del referenced["$id"]
    referenced["$id"] = "urn:gene-annotation:ordinary-fba-tool:" + hashlib.sha256(json.dumps(
        referenced, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert _operation_schema_view(referenced) == referenced


def test_published_fba_inputs_and_retained_values_reach_recurring_text_turns(tmp_path, monkeypatch):
    configured = os.environ.get("HMMER_NATIVE_ORACLE_FBA_PROMPT_RETAINED")
    if not configured:
        pytest.skip("optional rendering control requires an explicitly supplied completed360 Store")
    original_store = Path(configured).resolve()
    retained = _retained(original_store)
    assert PUBLICATION.is_dir(), "select the actual published instruction support tree"
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("subprocess.Popen", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.providers._SessionConnection._rpc", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.flux_balance_tools.run_selected_flux_balance_native", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.flux_balance_tools.run_selected_flux_balance_result_worker", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.flux_balance_model_execution.run_selected_flux_balance_model", _forbidden)

    selected = retained["selected"]
    software = selected["binding"]["software"]
    scientific_software = {
        "solver_interface": software["solver_interface"],
        "python_version": software["python_version"],
        "distributions": [row for row in software["distributions"]
            if row["name"] in {"cobra", "optlang", "swiglpk", "python-libsbml"}],
        "model_formats": selected["binding"]["model_formats"],
    }
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    resources = {selected["resource_id"]: {"kind": "local", "workspace": str(workspace),
        "policy": deepcopy(POLICY), "native_flux_balance": [deepcopy(selected["binding"])]}}
    environments = [{"resource_id": selected["resource_id"], "binding_ordinal_0based": 0,
        "environment": deepcopy(ENVIRONMENT_SELECTION)}]
    factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, flux_balance_environments=environments)
    run_id, directory = "fba-published-text-control", tmp_path / "run"
    with Store(tmp_path / "store") as store:
        # The protein is only the existing Episode scope carrier. The supplied
        # metabolic model and all hypothetical edits are separate caller inputs.
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope = store.validate_scope({"subject_refs": [target]})
        model = retained["model_file"]
        assert store.artifact(retained["model_bytes"], "application/json") == model["artifact_ref"]
        caller_source = store.put("source", {"provider": "caller", "accession": None, "uri": None,
            "artifact_ref": model["artifact_ref"], "text_ref": None, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        factory.configure_tool_registry(tools)
        application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process",),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        original_contract = retained["request"]["report_contract"]
        assignment = {
            "selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A110"), "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": FBA_TOOL, "resources": "local"}]},
            "evidence_refs": [model["artifact_ref"]],
            "constraints": {"no_external_acquisition": True, "no_gene_knockout_inference": True,
                "resource_id": selected["resource_id"], "binding_ordinal_0based": 0,
                "allocation": deepcopy(POLICY)},
            "context": {"supplied_model_file": deepcopy(model),
                "model_selector": deepcopy(retained["actions"][0]["arguments"]["model"]),
                "caller_hypothetical_edits": deepcopy(retained["actions"][1]["arguments"]["edits"]),
                "selected_objective": deepcopy(retained["actions"][2]["arguments"]["request"]["objective"]),
                "selected_software": scientific_software,
                "hypothesis_qualification": "Caller-authored C/BC additions; no database mapping or biological observation."},
        }
        commission = {"kind": "episode_child", "role": "scientific_process", "goal": QUESTION,
            "scope": deepcopy(scope), "purpose": original_contract["decision"],
            "schema_json": json.dumps(original_contract["measurements"]["schema"]),
            "initial_report_json": '{"solve_source":null}', "assignment": assignment}
        provider = ScriptedDecisions([select(commission), StopBeforeDecision()])
        workflow = Workflow(store, tools, provider, directory, run_id,
            lambda path, initial, **_kwargs: FixtureController(str(path), initial, 1), _credit,
            project_child_credit=_credit,
            episode_binding_descriptors=[descriptor, *application.episode_binding_descriptors],
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            episode_record_receipts=True, decision_protocol="decision_exchange_v1",
            initial_known_record_refs=[model["artifact_ref"], caller_source["id"]])
        root = workflow.build("annotation", "root", QUESTION, scope)
        with pytest.raises(StopBeforeDecision):
            asyncio.run(root.run_async(workflow.context))
        science_calls = [row for row in provider.calls if "scientific_process" in row["state"]]
        assert len(science_calls) == 1, {
            "captured_scientific_contexts": len(science_calls),
            "actual_commission_feedback": [{"episode_id": row["episode_id"],
                "feedback": row["state"].get("feedback")} for row in provider.calls],
        }
        call = science_calls[0]
        state = call["state"]
        assert state["scientific_process"]["assignment"]["context"] == assignment["context"]
        assert state["scientific_process"]["assignment"]["evidence_refs"] == [model["artifact_ref"]]
        assert state["scientific_process"]["evidence_axis"]["id"] == "A110"
        assert state["scientific_process"]["evidence_axis"]["instruction_status"] == "published_investigation_instructions"
        info, = state["scientific_process"]["child_tool_info"]
        assert info == workflow.scientific_process_binding.tool_library.resolve_tool_info(
            assignment["selection"]["child_tool_info"])[0]
        assert state["requested_form"] == original_contract["measurements"]["schema"]
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
        before = _rows(store)
        inputs = deepcopy((assignment, state, retained["outcomes"], call["output_schema"]))
        wire = ScientificWire(tmp_path / "controlled-wire")

        async def render():
            # Use the actual published commission's protocol schema. The wire's
            # synthetic reply is only transport data and is never admitted.
            await wire.complete(call["episode_id"], "REASONING", call["instructions"],
                call["context"], call["output_schema"])
            previous = state
            for outcome in retained["outcomes"]:
                current = deepcopy(state)
                current["last_local_outcome"] = deepcopy(outcome)
                # No fresh controller statistics or completed work are invented.
                await wire.complete(call["episode_id"], "REASONING", call["instructions"],
                    state_frame(current, previous), call["output_schema"])
                previous = current
        asyncio.run(render())
        turns = wire.turns_sent()
        assert len(turns) == 7
        texts = [turn["input"][0]["text"] for turn in turns]
        tasks = [text.split("\n\nSTEERING\n", 1)[0] for text in texts]
        assert len(set(tasks)) == 1
        host_contract = json.dumps(state["requested_form"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        output_schema = json.dumps(call["output_schema"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        # The former 2,873,762-byte TASK expanded this identical 221 KB host
        # contract twice. Measure the complete replacement, without truncation.
        assert len(tasks[0].encode()) < len(host_contract)
        model_update = call["output_schema"]["properties"]["response"]["anyOf"][1]["properties"]["report_update"]
        assert set(model_update["properties"]) == {"solve_source"}
        assert model_update["properties"]["solve_source"]["type"] == ["string", "null"]
        for turn in turns:
            assert turn["outputSchema"] == call["output_schema"]
        for text in texts:
            assert text.startswith("TASK\n\n") and text.count("\n\nSTEERING\n") == 1
            task, steering = text.split("\n\nSTEERING\n", 1)
            for value in (QUESTION, original_contract["decision"], model["artifact_ref"], model["sha256"],
                    "supplied_model_file.size_bytes | 696", "cobra_json", "caller_hypothetical_edits",
                    "metabolite_id | B", "metabolite_id | C", "coefficient | -1", "coefficient | 1",
                    "compartment_id | c", "reaction_id | AB", "lower.value | 0", "upper.value | 0",
                    "reaction_id | BC", "direction | max", "optlang.glpk_interface", "cobra", "0.32.1",
                    software["python_version"],
                    "allocation.memory_bytes | 21474836480", "allocation.scratch_bytes | 4294967296",
                    "allocation.wall_seconds | null", "Caller-authored C/BC additions", info["instructions"]):
                assert value in task
            for source in ("flux_balance_measurements", "flux_balance_model_views", "flux_balance_saved_sheets",
                    "flux_balance_edited_models", "flux_balance_failures"):
                assert source in task
                assert state["available_report_facts"][source]["meaning"] in task
            assert "Own completed actions" in steering
            assert software["python"]["path"] not in text
            assert software["python"]["sha256"] not in text
            assert selected["workspace"] not in text
            assert "base_revision" not in text and "PRIVATE_" not in text
            assert "result_contract.properties" not in task and "return.measurements[]" not in task
            assert "return.solve_source" in task and "Automatically supplied recorded values." in task
            start = task.index("Schema information\n")
            end = task.index("\nEnd schema information\n", start) + len("\nEnd schema information\n")
            shown_arguments = parse_schema_information(task[start:end])
            full_arguments = next(tool["input_schema"] for tool in state["tools"] if tool["name"] == FBA_TOOL)
            assert schema_fingerprint(shown_arguments) == schema_fingerprint(_operation_schema_view(full_arguments))
            assert full_arguments["$id"] not in task
        solve = texts[3].split("\n\nSTEERING\n", 1)[1]
        assert "native_cobra.value | 0.0" in solve and "native_cobra.state | present" in solve
        assert "native_legacy.value | null" in solve and "native_legacy.state | missing" in solve
        assert "unit.basis | unknown" in solve and "native_text | null" in solve
        bounds = texts[4].split("\n\nSTEERING\n", 1)[1]
        assert "reaction_id | AB" in bounds and "reaction_id | BC" in bounds
        assert "bounds.lower.value | 0.0" in bounds and "bounds.upper.value | 5.0" in bounds
        assert "flux.flux.value | 0.0" in bounds and "flux.unit.basis | unknown" in bounds
        population = texts[5].split("\n\nSTEERING\n", 1)[1]
        assert "expected_reaction_count | 4" in population and "partial_checks" in population
        assert (assignment, state, retained["outcomes"], call["output_schema"]) == inputs
        assert _rows(store) == before
        assert wire.turns_sent()[0]["outputSchema"] == wire.turns_sent()[-1]["outputSchema"]
        report = {"scope": "Metadata-only actual commission and controlled text transport; retained outcomes are detached presentation data.",
            "question": QUESTION, "axis": "A110", "thought_pattern": "P01", "turns": len(turns),
            "scientific_actions": 0, "scientific_observations": 0, "tool_operations": 0,
            "task_bytes": len(tasks[0].encode()), "turn_text_bytes": [len(text.encode()) for text in texts],
            "host_contract_bytes": len(host_contract), "host_contract_sha256": hashlib.sha256(host_contract).hexdigest(),
            "output_schema_bytes": len(output_schema), "output_schema_sha256": hashlib.sha256(output_schema).hexdigest(),
            "original_hashes": retained["original_hashes"], "texts": texts}
        (tmp_path / "FBA_PROMPT_DELIVERY.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    assert hashlib.sha256((original_store / "state.sqlite3").read_bytes()).hexdigest() == DATABASE_SHA256
    for reference, expected in retained["original_hashes"].items():
        if reference != "state.sqlite3":
            assert hashlib.sha256(_artifact(original_store, reference)).hexdigest() == expected


# This fixture provides engineered deployment metadata only. The actual ORF
# catalog and published-science renderer run; no native unit or ORF is executed.
from tests.test_molecular_sequence_ordinary import selected_call


@pytest.fixture
def ordinary_orf_entry(selected_call):
    from gene_annotation_episode import molecular_sequence_tools as orf
    call, calls = selected_call
    selected = call["selected"]
    binding = {"version": orf.BINDING_VERSION, "operation": orf.ORF_TOOL,
        "deployment": deepcopy(selected["deployment"]), "software": deepcopy(selected["software"])}
    resources = {selected["resource_id"]: {"kind": "local", "workspace": selected["workspace"],
        "policy": call["policy"].to_dict(), "native_molecular_sequence": [binding]}}
    environments = [{"operation": orf.ORF_TOOL, "resource_id": selected["resource_id"],
        "binding_ordinal_0based": 0, "environment": deepcopy(selected["environment"])}]
    configuration = orf.normalize_molecular_sequence_configuration(resources, environments, call["policy"])
    yield {"name": orf.ORF_TOOL, **orf.molecular_sequence_tool_catalog(configuration)[orf.ORF_TOOL]}
    assert calls == []


def _orf_schema_pin(schema):
    shown = {key: value for key, value in schema.items() if key != "$id"}
    return "urn:gene-annotation:ordinary-orf-tool:" + hashlib.sha256(json.dumps(
        shown, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def test_ordinary_orf_host_schema_pin_is_display_only(ordinary_orf_entry):
    schema = ordinary_orf_entry["input_schema"]
    original = deepcopy(ordinary_orf_entry)
    assert schema["$id"] == _orf_schema_pin(schema)
    shown = _operation_schema_view(schema)
    assert schema_fingerprint(shown) == schema_fingerprint(
        {key: value for key, value in schema.items() if key != "$id"})
    assert set(shown["properties"]) == {"subject_ref", "min_length", "search_reverse", "filter_subsets", "rows"}
    assert shown["required"] == schema["required"] and shown["additionalProperties"] is False
    assert ordinary_orf_entry == original


@pytest.mark.parametrize("identity", ("forged", "changed_schema", "custom", "$ref", "$dynamicRef", "$recursiveRef"))
def test_ordinary_orf_display_preserves_unproven_or_referenced_ids(ordinary_orf_entry, identity):
    schema = deepcopy(ordinary_orf_entry["input_schema"])
    if identity == "forged":
        schema["$id"] += "altered"
    elif identity == "changed_schema":
        schema["properties"]["min_length"]["minimum"] = 1
    elif identity == "custom":
        schema["$id"] = "urn:caller:ordinary-orf-operands"
    else:
        schema["$defs"] = {"subject": deepcopy(schema["properties"]["subject_ref"])}
        schema["properties"]["subject_ref"] = {identity: "#/$defs/subject"}
        schema["$id"] = _orf_schema_pin(schema)
    original = deepcopy(schema)
    assert _operation_schema_view(schema) == original
    assert schema == original


def test_published_orf_task_retains_question_guidance_and_operands_without_host_pins(ordinary_orf_entry):
    from gene_annotation_episode.molecular_result_facts import molecular_fact_sources
    from gene_annotation_episode.molecular_sequence_result_contracts import ORDINARY_ORF_FACT_SOURCE
    entry = ordinary_orf_entry
    question = "Which literal ORFs are retained in the supplied nucleotide sequence under the explicit scan parameters?"
    subject_ref = "input_" + "a" * 24
    sources = molecular_fact_sources()
    source = ORDINARY_ORF_FACT_SOURCE
    assert sources[source]["meaning"] == sources[source]["description"]
    form = {"type": "object", "additionalProperties": False, "required": ["orf_values"],
        "properties": {"orf_values": deepcopy(sources[source]["report_schema"])}}
    state = {"goal": {"objective": question}, "scientific_process": {
        "evidence_axis": {"name": "Literal sequence evidence",
            "instruction_status": "published_investigation_instructions",
            "investigation_instructions": "Inspect the supplied sequence without assigning biological function."},
        "assignment": {"context": {"selected_subject_ref": subject_ref, "min_length": 0,
            "search_reverse": True, "filter_subsets": False}},
        "child_tool_info": [{key: entry[key] for key in ("name", "resources", "description", "instructions")}]},
        "tools": [deepcopy(entry)], "requested_form": form, "available_report_facts": sources}
    original = deepcopy(state)
    text = render_scientific_process_prompt(state, "Fixed approved scientific instructions.")
    task, steering = text.split("\n\nSTEERING\n", 1)
    assert question in task and entry["instructions"] in task and entry["description"] in task
    for literal in (subject_ref, "min_length | 0", "search_reverse | true", "filter_subsets | false",
            "including the terminal stop codon", "zero-based half-open", "translate(to_stop=True)",
            "units, empty populations, missing values and partial results", source, sources[source]["meaning"]):
        assert literal in task
    assert f"| {source} | {sources[source]['meaning']} |" in task
    start = task.index("Schema information\n")
    end = task.index("\nEnd schema information\n", start) + len("\nEnd schema information\n")
    recovered = parse_schema_information(task[start:end])
    assert schema_fingerprint(recovered) == schema_fingerprint(_operation_schema_view(entry["input_schema"]))
    assert entry["input_schema"]["$id"] not in text
    selected, = entry["configuration"]["bindings"]
    for host_value in (selected["binding_sha256"], selected["source_sha256"], selected["resource_id"]):
        assert host_value not in text
    assert "Own completed actions" in steering
    assert state == original
