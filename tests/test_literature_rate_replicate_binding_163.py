"""Synthetic raw tables and controlled choices; no paper/model validation."""
import asyncio
from copy import deepcopy
import csv
from dataclasses import replace
from functools import partial
import io
import json
import math
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionError

from gene_annotation_episode.communication import (ReportBoundaryError, form_with_facts, plain,
    validate_closed_schema, validate_form)
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.composition_information import CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episode_contract_information import operation_contract_information
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.literature_rate_replicate_inputs import HEADERS
from gene_annotation_episode.literature_rate_replicate_prompt import RATE_REPLICATE_TASK, render_received
from gene_annotation_episode.literature_rate_replicate_storage import (
    COMPONENTS, NAMESPACE, REQUESTED, LiteratureRateReplicateRepository, rate_replicate_cells_schema)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot


REQUEST = ["rate_difference", "retained_fraction", "difference_se"]
FORM = obj({"requested_rates": rate_replicate_cells_schema()})


def test_child_task_repeats_in_actual_provider_delta_lookup_and_cold_transport(tmp_path):
    first = snapshot()
    first["goal"]["objective"] = "Examine synthetic raw rate measurements, actual units and pairing."
    first["requested_form"] = FORM
    first["literature_assignment"][REQUESTED] = REQUEST
    second = deepcopy(first)
    second["last_local_outcome"] = {"status": "completed", "result": {
        "text": "Synthetic assay: two technical readings share one preparation; dependence remains unknown."}}
    lookup_result = {"status": "completed", "text": "Synthetic source: measurement identity is repeated, not a new unit."}
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result", "decision_index": 2,
        "exchange_index": 1, "result": lookup_result}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=2, restored_public_exchanges=[{
        "lookup_result": lookup_result, "response": {"private_extra": "DO_NOT_RENDER_PRIVATE_HISTORY"}}])
    wire, cold = LiteratureWire(tmp_path / "wire"), LiteratureWire(tmp_path / "cold")
    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(wire, lookup)
        await complete(cold, restored)
    asyncio.run(exercise())
    tasks = []
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        task, steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)
        assert task.count(RATE_REPLICATE_TASK) == 1
        assert first["goal"]["objective"] in task
        assert RATE_REPLICATE_TASK not in steering and "DO_NOT_RENDER_PRIVATE_HISTORY" not in steering
        tasks.append(task)
    assert all(task == tasks[0] for task in tasks)
    assert lookup_result["text"] in wire.turns_sent()[-1]["input"][0]["text"]
    assert lookup_result["text"] in cold.turns_sent()[0]["input"][0]["text"]


def test_raw_operation_contract_lookup_preserves_scientific_task_on_cold_transport(tmp_path):
    from gene_annotation_episode.literature_episodes import _population_catalog
    state = snapshot()
    state["contract_information_profile"] = CONTRACT_INFORMATION_PROFILE
    operation = next(row for row in _population_catalog() if row["name"] == "literature.rate.replicates.populate")
    state["tools"] = [{**operation, "argument_transport": CONTRACT_ARGUMENT_TRANSPORT}]
    information = operation_contract_information(catalog=[operation], operation=operation["name"])
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result", "decision_index": 1,
        "exchange_index": 1, "result": information, "pending_contract_information": [information]}
    restored = state_frame(state)
    restored.update(restored_pending_decision_index=1, restored_public_exchanges=[{"lookup_result": information}])
    wire, cold = LiteratureWire(tmp_path / "wire"), LiteratureWire(tmp_path / "cold")
    async def exercise():
        await complete(wire, state_frame(state))
        await complete(wire, lookup)
        await complete(cold, restored)
    asyncio.run(exercise())
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        task, steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)
        assert task.count(RATE_REPLICATE_TASK) == 1 and RATE_REPLICATE_TASK not in steering
        assert information["result"]["schema_sha256"] not in task + steering
    for turn in (wire.turns_sent()[-1], cold.turns_sent()[0]):
        task, steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)
        assert information["result"]["text"] in task and information["result"]["text"] not in steering


def paired_rows(*, independent=False):
    return [{"arm": role, "sampling_unit": f'{role if independent else "pair"}-{index}',
             "observation_id": f"{role}-{index}", "value": str(value)}
            for index, values in enumerate(((10, 8), (20, 19), (30, 25)))
            for role, value in zip(("reference", "test"), values)]


def setup(path, *, rows=None, delimiter="\t", subject="Measured construct", endpoint="product formation", unit="umol/min", requested=REQUEST):
    store = Store(path)
    manifest = store.path / "empty-supplied-input-manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "entries": []}))
    store.create_problem(manifest_path=manifest)
    assert store.targets() == []
    args, source = add_source(store, paired_rows() if rows is None else rows,
        subject=subject, endpoint=endpoint, unit=unit, delimiter=delimiter)
    assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
        "source_refs": [source["id"]], REQUESTED: list(requested)}
    context = BindingContext("replicate-synthetic-run", "raw-child", "literature",
        (("literature", "synthetic-child"),), store.validate_scope(), assignment, {}, (source["id"],))
    return store, context, args


def add_source(store, rows, *, subject="Measured construct", endpoint="product formation", unit="umol/min", delimiter="\t"):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator="\n")
    writer.writerow(HEADERS)
    for index, changes in enumerate(rows):
        row = {"subject": subject, "experiment": "raw experiment", "arm": "reference", "condition": "matched buffer",
            "endpoint": endpoint, "normalization": "preparation", "sampling_unit": "preparation-A",
            "sampling_basis": "biological_preparations", "observation_id": f"physical-{index}",
            "value": "10", "unit": unit, "origin": "synthetic", **changes}
        writer.writerow([row[field] for field in HEADERS])
    artifact = store.artifact(stream.getvalue(), "text/tab-separated-values" if delimiter == "\t" else "text/csv")
    source = store.put("source", {"provider": "synthetic_raw_rate_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")
    args = {"source_ref": source["id"], "source_representation": "original", "table_kind": "synthetic_fixture",
        "delimiter": delimiter, "subject": subject, "experiment": "raw experiment",
        **{role: {"arm": role, "condition": "matched buffer", "endpoint": endpoint, "normalization": "preparation"}
            for role in ("reference", "test")}, "unit_model": "iid_units", "dependence": "paired_units"}
    return args, source


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    services = WorkflowServices(host)
    binding = LiteratureEpisodes(services, rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return services, binding


def populated(store, context, args, key="selected"):
    repository = LiteratureRateReplicateRepository(store, context.run_id)
    outcome = repository.populate(context, args, key)
    current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
    return repository, outcome, current


@pytest.mark.parametrize("delimiter", [",", "\t"])
def test_actual_raw_selected_cells_and_paired_precision_are_not_fictitious_summaries(tmp_path, delimiter):
    store, context, args = setup(tmp_path, delimiter=delimiter, requested=COMPONENTS)
    try:
        repository, outcome, current = populated(store, context, args)
        saved = repository.read(outcome["result"]["sheet_ref"])
        cells = {row["component"]: row for row in outcome["result"]["cells"]}
        assert cells["reference_rate"]["value"] == 20
        assert cells["test_rate"]["value"] == pytest.approx(52/3)
        assert cells["rate_difference"]["value"] == pytest.approx(8/3)
        assert cells["retained_fraction"]["value"] == pytest.approx(13/15)
        assert cells["paired_sample_sd"]["value"] == pytest.approx(math.sqrt(13/3))
        assert cells["difference_se"]["value"] == pytest.approx(math.sqrt(13)/3)
        assert cells["difference_se"]["conditional_on"] == ["iid_unit_pairs"]
        assert cells["reference_sample_sd"]["value"] == 10
        assert cells["reference_mean_se"]["value"] == pytest.approx(10/math.sqrt(3))
        assert len(saved["sheet"]["summary"]["extraction"]["rows"]) == 6
        assert saved["sheet"]["annotation_credit"] is saved["sheet"]["assay_error_rate"] is None
        assert "observed_point_mean" not in canonical(outcome["result"])
        assert "raw_value" not in canonical(outcome["result"])
        assert repository.populate(context, args, "selected") == outcome
        assert repository.fact_cells(current, outcome["record_refs"], components=REQUEST) == [cells[name] for name in REQUEST]
        assert store.db.execute("SELECT count(*) FROM literature_rate_replicate_operations").fetchone()[0] == 1
    finally:
        store.close()


@pytest.mark.parametrize("dependence,independent,reason", [("independent", True, None),
    ("independent", False, "shared_sampling_units"), ("unknown", False, "dependence_unknown")])
def test_selected_dependence_is_preserved_and_never_inferred_from_grouping(tmp_path, dependence, independent, reason):
    store, context, args = setup(tmp_path, rows=paired_rows(independent=independent))
    try:
        _, outcome, _ = populated(store, context, {**args, "dependence": dependence})
        cell = outcome["result"]["cells"][2]
        assert cell["dependence"] == dependence and cell["unavailable_reason"] == reason
        assert (cell["value"] is None) == (reason is not None)
        if reason is None:
            expected = math.sqrt((100 + 223/3) / 3)
            assert cell["value"] == pytest.approx(expected)
            assert cell["conditional_on"] == ["iid_units", "independent_groups"]
    finally:
        store.close()


def test_unbalanced_readings_and_duplicate_representations_keep_real_denominators(tmp_path):
    rows = [{"sampling_unit": "A", "value": "9", "observation_id": "a1"},
        {"sampling_unit": "A", "value": "11", "observation_id": "a2"},
        {"sampling_unit": "B", "value": "19"}, {"sampling_unit": "B", "value": "20"},
        {"sampling_unit": "B", "value": "21"},
        {"sampling_unit": "A", "value": "9000", "unit": "nmol/min", "observation_id": "a1"}]
    store, context, args = setup(tmp_path, rows=rows, requested=["reference_rate", "reference_sample_sd", "reference_mean_se"])
    try:
        repository, outcome, _ = populated(store, context, args)
        first = outcome["result"]["cells"][0]
        assert first["value"] == 15  # equal unit weights, not five-point mean 16
        group = first["groups"]["reference"]["observed"]
        assert (group["measurement_count"], group["representation_count"], group["sampling_unit_count"]) == (5, 6, 2)
        assert [unit["measurement_count"] for unit in group["units"]] == [2, 3]
        assert first["groups"]["test"]["observed"] is None
        assert first["groups"]["test"]["status"] == "not_observed"
        assert repository.read(first["sheet_ref"])["sheet"]["summary"]["groups"][0]["units"][0]["cells"]["mean"]["value"] == 10
        assert "cells" not in group and all("cells" not in unit for unit in group["units"])
    finally:
        store.close()


@pytest.mark.parametrize("token,limitation", [("", "source_measurement_unavailable"),
    ("ND", "nondetection_without_point"), ("<5", "censored_measurement"), ("~>5", "censored_measurement")])
def test_missing_and_censored_measurements_keep_partial_unit_work_and_no_imputation(tmp_path, token, limitation):
    rows = [{"sampling_unit": "A", "value": "10"}, {"sampling_unit": "A", "value": token},
        {"sampling_unit": "B", "value": "20"}]
    store, context, args = setup(tmp_path, rows=rows, requested=["reference_rate", "difference_se"])
    try:
        repository, outcome, _ = populated(store, context, args)
        cell = outcome["result"]["cells"][0]
        assert cell["value"] is None and cell["unavailable_reason"] == "incomplete_sampling_units"
        group = cell["groups"]["reference"]["observed"]
        assert group["measurement_count"] == 3 and group["complete_unit_count"] == 1
        assert group["units"][0]["limitations"] == [limitation]
        saved_units = repository.read(cell["sheet_ref"])["sheet"]["summary"]["groups"][0]["units"]
        assert saved_units[0]["cells"]["observed_point_mean"]["value"] == 10
        assert saved_units[1]["cells"]["mean"]["value"] == 20
    finally:
        store.close()


def test_conflicting_physical_id_preserves_unaffected_units_and_source_limits(tmp_path):
    rows = [{"observation_id": "conflict", "value": "10"}, {"observation_id": "conflict", "value": "11"},
        {"sampling_unit": "B", "value": "20"}]
    store, context, args = setup(tmp_path, rows=rows, requested=["reference_rate"])
    try:
        repository, outcome, _ = populated(store, context, args)
        cell, = outcome["result"]["cells"]
        unit = cell["groups"]["reference"]["observed"]["units"][0]
        assert unit["measurement_count"] == 1 and unit["representation_count"] == 2
        assert unit["conflicting_identity"] and unit["limitations"] == ["conflicting_observation_identity"]
        assert repository.read(cell["sheet_ref"])["sheet"]["summary"]["groups"][0]["units"][1]["cells"]["mean"]["value"] == 20
    finally:
        store.close()


@pytest.mark.parametrize("field,value,reason", [("endpoint", "oxygen depletion", "endpoint_mismatch"),
    ("normalization", "total protein", "normalization_mismatch")])
def test_incompatible_group_meanings_preserve_native_results_and_unknown_contrast(tmp_path, field, value, reason):
    rows = paired_rows()
    for row in rows:
        if row["arm"] == "test":
            row[field] = value
    store, context, args = setup(tmp_path, rows=rows, requested=["reference_rate", "test_rate", "rate_difference"])
    try:
        args["test"][field] = value
        _, outcome, _ = populated(store, context, args)
        assert [cell["value"] for cell in outcome["result"]["cells"][:2]] == pytest.approx([20, 52/3])
        assert outcome["result"]["cells"][2]["unavailable_reason"] == reason
        assert outcome["result"]["cells"][2]["groups"]["test"]["observed"][field] == value
    finally:
        store.close()


def test_empty_table_has_requested_comparison_but_no_measured_subject_or_group(tmp_path):
    store, context, args = setup(tmp_path, rows=[])
    try:
        _, outcome, _ = populated(store, context, args)
        for cell in outcome["result"]["cells"]:
            assert cell["observed_subject"] is cell["observed_experiment"] is None
            assert cell["groups"]["reference"]["observed"] is cell["groups"]["test"]["observed"] is None
            assert cell["groups"]["reference"]["selection"] == args["reference"]
            assert cell["value"] is None
    finally:
        store.close()


def test_page_ancestry_and_selected_text_representation_are_actual_operands(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        root = store.get(args["source_ref"])
        other_args, other = add_source(store, paired_rows(), subject="Unrelated source molecule")
        page_assignment = {"version": "page_assignment_v1", "source_ref": root["id"], "representation": "original",
            "artifact_ref": root["artifact_ref"], "question_context_refs": [], "prior_delivery_refs": [], REQUESTED: REQUEST}
        page = replace(context, role="literature_page", path=(("literature_page", "page"),), assignment=page_assignment,
            received_record_refs=(root["id"], other["id"]))
        _, binding = binding_for(store, context)
        rejected = asyncio.run(binding.execute(page, "literature.rate.replicates.populate", other_args, "unrelated"))
        assert rejected["status"] == "invalid" and rejected["feedback"]["code"] == "literature_reading_outside_assigned_source"
        opaque = store.artifact(b"\xff original representation is not a raw table")
        derivative = store.put("source", {"provider": "synthetic_retained_table", "accession": None,
            "uri": None, "artifact_ref": opaque, "text_ref": root["artifact_ref"], "request_ref": None,
            "version": None, "retrieved_at": None, "parent_source_refs": [root["id"]]}, origin="caller")
        selected = {**args, "source_ref": derivative["id"], "source_representation": "text"}
        page = replace(page, received_record_refs=(*page.received_record_refs, derivative["id"]))
        outcome = asyncio.run(binding.execute(page, "literature.rate.replicates.populate", selected, "selected-text"))
        assert outcome["status"] == "completed", outcome
        repository = LiteratureRateReplicateRepository(store, context.run_id)
        saved = repository.read(outcome["result"]["sheet_ref"])
        assert saved["input_artifact_ref"] == root["artifact_ref"]
        assert saved["input_source_refs"] == [derivative["id"], root["id"]]
        assert saved["sheet"]["summary"]["extraction"]["table"]["artifact_ref"] != opaque
    finally:
        store.close()


@pytest.mark.parametrize("field", ["unit_basis", "pairing", "cell_shape"])
def test_saved_metadata_relationship_validation_needs_no_source_or_calculator(tmp_path, monkeypatch, field):
    store, context, args = setup(tmp_path)
    try:
        repository, outcome, _ = populated(store, context, args)
        saved = repository.read(outcome["result"]["sheet_ref"])
        source = store.get(outcome["result"]["sheet_ref"])
        request = json.loads(store.get_artifact(source["request_ref"]))
        def forbidden(*_args, **_kwargs):
            raise AssertionError("scientific source parsing must stay disabled")
        monkeypatch.setattr("gene_annotation_episode.literature_rate_replicate_storage.read_rate_replicate_table", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_rate_replicate_storage.populate_rate_replicate_contrast", forbidden)
        if field == "unit_basis":
            saved["sheet"]["summary"]["groups"][0]["units"][0]["sampling_basis"] = "technical_measurements"
            with pytest.raises(ContractError, match="unit_binding_mismatch"):
                repository._validate_saved_bindings(saved, request)
        elif field == "pairing":
            saved["sheet"]["pairing"]["shared_units"] = []
            with pytest.raises(ContractError, match="pairing_binding_mismatch"):
                repository._validate_saved_bindings(saved, request)
        else:
            saved["sheet"]["cells"]["rate_difference"]["invented_reliability"] = 1
            original_get = store.get_artifact
            monkeypatch.setattr(store, "get_artifact", lambda reference: canonical(saved).encode()
                if reference == source["artifact_ref"] else original_get(reference))
            with pytest.raises(ContractError, match="artifact_hash_mismatch"):
                repository.read(outcome["result"]["sheet_ref"])
    finally:
        store.close()


def test_selected_binding_closed_arguments_and_source_custody(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        services, binding = binding_for(store, context)
        assert "literature.rate.replicates.populate" in {row["name"] for row in binding.catalog(context)}
        assert "literature.rate.replicates.populate" not in {row["name"] for row in LiteratureEpisodes(services).catalog(context)}
        for changed in ({**args, "mean": 99}, {**args, "subject": "Unrelated global subject"}):
            failed = asyncio.run(binding.execute(context, "literature.rate.replicates.populate", changed, "bad"))
            assert failed["status"] == "invalid" and not failed["record_refs"]
        missing = asyncio.run(binding.execute(replace(context, received_record_refs=()), "literature.rate.replicates.populate", args, "not-received"))
        assert missing["feedback"]["code"] == "literature_source_not_received"
        outcome = asyncio.run(binding.execute(context, "literature.rate.replicates.populate", args, "selected"))
        assert outcome["status"] == "completed", outcome
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        facts = binding.facts(current, {"committed_record_refs": outcome["record_refs"]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(current, form, FORM)
        assert [row["component"] for row in form["requested_rates"]] == REQUEST
        altered = deepcopy(form)
        altered["requested_rates"][0]["value"] = 999
        with pytest.raises(ReportBoundaryError, match="differs_from_saved"):
            binding.validate_report(current, altered, FORM)
        omitted = deepcopy(form)
        omitted["requested_rates"].pop()
        with pytest.raises(ReportBoundaryError, match="requested_subset_mismatch"):
            binding.validate_report(current, omitted, FORM)
        no_request = replace(current, assignment={key: value for key, value in current.assignment.items() if key != REQUESTED})
        assert binding.facts(no_request, {"committed_record_refs": outcome["record_refs"]})[NAMESPACE] == []
        with pytest.raises(ReportBoundaryError, match="unrequested"):
            binding.validate_report(no_request, form, FORM)
        with pytest.raises(ContractError, match="reused_for_different_work"):
            services.literature_rate_replicate_repository().populate(context, {**args, "dependence": "unknown"}, "selected")
        with pytest.raises(ContractError, match="component_selection_invalid"):
            services.literature_rate_replicate_repository().project_cells([], permitted_record_refs=(), components=[{}])
        wrong_schema = deepcopy(FORM)
        wrong_schema["properties"]["requested_rates"]["items"]["properties"]["observed_subject"] = {"type": ["string", "null"]}
        with pytest.raises(ReportBoundaryError, match="registered source"):
            validate_closed_schema(wrong_schema)
    finally:
        store.close()


def test_parent_has_only_actually_admitted_subset_and_two_sheet_meanings_stay_distinct(tmp_path):
    store, context, args = setup(tmp_path, requested=["rate_difference"])
    try:
        repository, first, child = populated(store, context, args)
        other_args, other_source = add_source(store, paired_rows(independent=True),
            subject="Distinct measured molecule", endpoint="substrate consumption", unit="uM/min")
        second_child = replace(context, episode_id="other-child", received_record_refs=(other_source["id"],))
        second_args = {**other_args, "unit_model": "none", "dependence": "unknown"}
        _, second, _ = populated(store, second_child, second_args, "other-selected")
        parent = replace(child, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
        repository.receive_cells(parent, first["result"]["cells"], "first-manual-trusted")
        repository.receive_cells(parent, second["result"]["cells"], "second-manual-trusted")
        parent = replace(parent, received_record_refs=(*parent.received_record_refs, *second["record_refs"]))
        received = repository.received_cells(parent)
        assert len(received) == 2 and all(row["component"] == "rate_difference" for row in received)
        assert repository.fact_cells(parent, [first["result"]["sheet_ref"], second["result"]["sheet_ref"]], components=COMPONENTS) == received
        with pytest.raises(ContractError, match="cell_not_received"):
            repository.validate_fact_values(parent, repository.project_cells(first["record_refs"],
                permitted_record_refs=parent.received_record_refs, components=["reference_rate"]))
        state = {"literature_experimental_work": {"version": "literature_experimental_task_v1", "aspect": "reference_evidence_parent"},
            "reference_evidence_parent": {"version": "reference_evidence_parent_v1", "source_refs": [args["source_ref"]]},
            "goal": {"objective": "Compare two distinct actual measured subjects."}, "working_state": {},
            "child_reports": [{"requested_rates": received}], "current_report_update": {"requested_rates": received}}
        prompt = render_literature_experimental_prompt(state, "Caller question remains the same.")
        task, steering = prompt.split("\n\nSTEERING\n")
        assert "Caller question remains the same." in task and REFERENCE_PARENT_TASK in task
        assert RATE_REPLICATE_TASK not in task
        sections = steering.split("Requested raw rate replicate components")[1:]
        assert len(sections) == 4
        for section in (sections[0], sections[2]):
            assert "Measured construct" in section and "Distinct measured molecule" not in section
            assert "product formation" in section and "umol/min" in section and "paired_units" in section
        for section in (sections[1], sections[3]):
            assert "Distinct measured molecule" in section and "substrate consumption" in section
            assert "uM/min" in section and "unknown" in section
        assert "| reference_rate |" not in steering and "| test_rate |" not in steering
        # The pure renderer also handles a direct mixed-sheet input safely.
        from gene_annotation_episode.literature_experimental_prompt import _section, _table
        parts = []
        render_received(parts, received, section=_section, table=_table)
        assert "\n".join(parts).count("Requested raw rate replicate components") == 2
    finally:
        store.close()


def test_cold_factory_and_saved_forwarding_require_no_source_or_analysis_and_no_writes(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    try:
        services, binding = binding_for(store, context)
        repository, outcome, child = populated(store, context, args)
        parent = replace(child, episode_id="receiving-parent", role="annotation", path=(("annotation", "parent"),), assignment={})
        repository.receive_cells(parent, outcome["result"]["cells"], "trusted-manual")
        descriptor = binding.as_record()
        journal = Journal(store, context.run_id)
        original_artifact = store.get(args["source_ref"])["artifact_ref"]
        original_get = store.get_artifact
        def guarded(reference):
            assert reference != original_artifact, "original scientific source is blocked"
            return original_get(reference)
        def forbidden(*_args, **_kwargs):
            raise AssertionError("source acquisition/parsing/summary/calculation is blocked before factory")
        monkeypatch.setattr(store, "get_artifact", guarded)
        for module_name, names in {
            "literature_rate_replicate_storage": ("read_rate_replicate_table", "populate_rate_replicate_contrast"),
            "literature_rate_replicate_inputs": ("read_rate_replicate_table", "validate_rate_replicate_extraction"),
            "literature_rate_replicate_calculations": ("summarize_rate_replicates", "populate_rate_replicate_contrast", "validate_rate_replicate_extraction"),
        }.items():
            for name in names:
                monkeypatch.setattr(f"gene_annotation_episode.{module_name}.{name}", forbidden)
        monkeypatch.setattr(services, "execute_tool", forbidden)
        changes = store.db.total_changes
        before = {str(path.relative_to(store.path)): path.read_bytes() for path in store.path.rglob("*") if path.is_file()}
        store.db.execute("PRAGMA query_only=ON")
        restored, = compose_episode_bindings(services, store=store, journal=journal, execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        fresh_services = WorkflowServices(services.workflow)
        fresh_services.workflow.episode_bindings = EpisodeBindingRegistry((restored,))
        reopened = fresh_services.literature_rate_replicate_repository()
        assert restored.as_record() == descriptor
        assert reopened.received_cells(parent) == outcome["result"]["cells"]
        assert reopened.fact_cells(parent, outcome["record_refs"], components=COMPONENTS) == outcome["result"]["cells"]
        assert reopened.populate(context, args, "selected") == outcome
        assert store.db.total_changes == changes
        assert {str(path.relative_to(store.path)): path.read_bytes() for path in store.path.rglob("*") if path.is_file()} == before
        obsolete = deepcopy(descriptor)
        obsolete["implementation_sha256"] = "0" * 64
        with pytest.raises(DurableExecutionError, match="identity_conflict"):
            compose_episode_bindings(services, store=store, journal=journal, execution_backend=None,
                descriptors=[obsolete], job_episodes=None, resource_estimator=None, role_credit_bindings={})
    finally:
        store.close()


def test_controlled_shared_episode_execution_typed_parent_return_and_observation_accounting(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / "state")
    received, controllers, tasks = [], [], []
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": plain(context.assignment),
        "goal": "Compare the synthetic reference molecule's raw rate measurements.", "scope": plain(context.scope),
        "purpose": "Return exactly the requested raw-rate comparison and precision cells.",
        "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
    def work(inputs):
        prompt = render_literature_experimental_prompt(inputs, "Evaluate the source raw repetition design.")
        tasks.append(prompt.split("\n\nSTEERING\n")[0])
        return {"selection": {"kind": "tool", "tool": "literature.rate.replicates.populate", "arguments": args}, "report_update": {}}
    def uses_return(inputs):
        form, = inputs["child_reports"]
        assert [row["component"] for row in form["requested_rates"]] == REQUEST
        assert form["requested_rates"][0]["observed_subject"] == "Measured construct"
        assert form["requested_rates"][0]["groups"]["reference"]["observed"]["sampling_unit_count"] == 3
        prompt = render_literature_experimental_prompt(inputs, "Retain the source evidence question.")
        task, steering = prompt.split("\n\nSTEERING\n")
        assert REFERENCE_PARENT_TASK in task and RATE_REPLICATE_TASK not in task and "Measured construct" in steering
        assert "| reference_rate |" not in steering and "| test_rate |" not in steering
        received.append(form)
        commit = {field: [] for field in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"])
        text = store.get_artifact(source["artifact_ref"]).decode("utf8")
        start = text.index("Measured construct")
        commit["source_subjects"] = [{"alias": "actual_measured_subject", "reference_type": "assay",
            "source_ref": args["source_ref"], "label": "Measured construct", "anchor": {
                "source_ref": args["source_ref"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": start + len("Measured construct"), "quote": "Measured construct"}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        provider = ScriptedProvider([child, work, uses_return])
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=[args["source_ref"]]),),
            binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1 and summary["credit"] == 0
        assert store.targets() == []
        assert any(row["label"] == "Measured construct" for row in store.list("reference"))
        assert all(RATE_REPLICATE_TASK in task for task in tasks)
        assert [controller.scores for controller in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_rate_replicate_operations").fetchone()[0] == 1
        assert len(provider.contexts) == 3
        assert not store.list("observation") and not store.list("assessment")
        saved_form, = store.db.execute("SELECT form FROM runtime_forms").fetchall()
        assert json.loads(saved_form[0]) == received[0]
        receipt, = store.db.execute("SELECT cells FROM literature_rate_replicate_received").fetchall()
        assert json.loads(receipt[0]) == received[0]["requested_rates"]
        # Reopen the actual original child/parent admission, not a constructed
        # replacement receipt, with acquisition and analysis disabled first.
        actual_run = store.db.execute("SELECT run_id FROM literature_rate_replicate_operations").fetchone()[0]
        parent_episode = store.db.execute("SELECT episode_id FROM literature_rate_replicate_received").fetchone()[0]
        parent = replace(context, run_id=actual_run, episode_id=parent_episode, role="annotation",
            path=(("annotation", parent_episode),), assignment={},
            received_record_refs=(received[0]["requested_rates"][0]["sheet_ref"], args["source_ref"]))
        services, _ = binding_for(store, parent)
        original = LiteratureEpisodes(services, rate_population=True, reference_parent_sources=[args["source_ref"]])
        descriptor = original.as_record()
        journal = Journal(store, actual_run)
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        original_get = store.get_artifact
        def guarded(reference):
            assert reference != source_artifact, "original scientific artifact blocked before factory"
            return original_get(reference)
        def forbidden(*_args, **_kwargs):
            raise AssertionError("original analysis/acquisition blocked before factory")
        monkeypatch.setattr(store, "get_artifact", guarded)
        monkeypatch.setattr(services, "execute_tool", forbidden)
        for module_name, names in {
            "literature_rate_replicate_storage": ("read_rate_replicate_table", "populate_rate_replicate_contrast"),
            "literature_rate_replicate_inputs": ("read_rate_replicate_table", "validate_rate_replicate_extraction"),
            "literature_rate_replicate_calculations": ("summarize_rate_replicates", "populate_rate_replicate_contrast", "validate_rate_replicate_extraction"),
        }.items():
            for name in names:
                monkeypatch.setattr(f"gene_annotation_episode.{module_name}.{name}", forbidden)
        before = store.db.total_changes
        store.db.execute("PRAGMA query_only=ON")
        restored, = compose_episode_bindings(services, store=store, journal=journal, execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        assert restored.as_record() == descriptor
        assert restored.received_report_facts(parent)[NAMESPACE] == received[0]["requested_rates"]
        assert store.db.total_changes == before
    finally:
        store.close()
