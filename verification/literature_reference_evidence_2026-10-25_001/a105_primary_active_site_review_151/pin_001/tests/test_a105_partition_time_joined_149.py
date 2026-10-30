"""Independent synthetic cross-family checks; no actual model investigation.

Controlled decisions run the real shared method_loop and typed delivery. Neither
these synthetic measurements nor their passing arithmetic establishes A105
adequacy. No retained paper packet is opened by this module.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_completion_time_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_completion_time_prompt import COMPLETION_TIME_TASK
from gene_annotation_episode.literature_completion_time_storage import LiteratureCompletionTimeRepository, completion_time_cells_schema
from gene_annotation_episode.literature_product_partition_inputs import MEANINGS
from gene_annotation_episode.literature_product_partition_prompt import PRODUCT_PARTITION_TASK
from gene_annotation_episode.literature_product_partition_storage import LiteratureProductPartitionRepository, product_partition_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController


RAW_NUMBERS = ("47.125713", "6.234891", "71.234567", "28.765433")
TEXT = ("Synthetic investigation. Single mixture and baseline mixture contain reference protein. "
        "Cleanup took >47.125713 h; baseline took <6.234891 min to equilibrium. "
        "Purification changed; heating also changed. Single mixture has component A 71.234567% "
        "and component B 28.765433%. NMR amount composition at equilibrium. "
        "Common selected denominator. Native construct. Fixed assay condition. "
        "Source describes these reports as approximate. One preparation; no independent repeat.")
TIME_REQUEST = ["completion_time_ratio"]
PARTITION_REQUEST = ["selected_fraction_sum"]
NUMERICAL_ENDPOINT = "71.234567% component A at 31 C"
FORM = obj({"times": completion_time_cells_schema(), "partition": product_partition_cells_schema(),
            "ordinary_credit": {"type": "number", "x-source": "credit"},
            "interpretation": {"type": "string", "enum": ["partial"]}})


def synthetic_inputs(store, *, numerical_endpoint=False):
    text = TEXT + (" For both duration reports, equilibrium is defined as " + NUMERICAL_ENDPOINT + "."
                   if numerical_endpoint else "")
    artifact = store.artifact(text, "text/plain")
    source = store.put("source", {"provider": "synthetic_joined_audit_149", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")["id"]
    def witness(quote, occurrence=0):
        start = -1
        for _ in range(occurrence + 1):
            start = text.index(quote, start + 1)
        return {"source_ref": source, "representation": "original", "start": start,
                "end": start + len(quote), "quote": quote}
    def interpreted(value, quote="equilibrium"):
        return {"value": value, "witnesses": [] if value == "unknown" else [witness(quote)]}
    broad = "Cleanup took >47.125713 h; baseline took <6.234891 min to equilibrium."
    def time(number, unit, preparation):
        unit_start = text.index(number) + len(number) + 1
        return {**dict.fromkeys(LITERAL_FIELDS), "subject": witness("reference protein"),
            "construct": witness("Native construct"), "preparation": witness(preparation),
            "condition": witness("31 C" if numerical_endpoint else "Fixed assay condition"),
            "endpoint": witness(NUMERICAL_ENDPOINT if numerical_endpoint else "equilibrium"),
            "measurement_identity": witness("Single mixture" if preparation == "Cleanup" else "baseline mixture"),
            "measurement": {"number": {"witness": witness(number), "number_start": 0,
                "number_end": len(number)}, "unit": {"source_ref": source, "representation": "original",
                    "start": unit_start, "end": unit_start + len(unit), "quote": unit}},
            "qualification": interpreted("source_qualified_approximate", "Source describes these reports as approximate")}
    times = {"source_ref": source, "source_kind": "synthetic_fixture", "experiment": witness(broad),
        "intended_change": witness("Purification"), "other_changes": [witness("heating also changed")],
        "comparison": {"endpoint_relation": interpreted("same"), "preparation_relation": interpreted("different"),
            "pair_relationship": interpreted("supported"), "other_changes_status": interpreted("partial")},
        "quantities": {"numerator": time(RAW_NUMBERS[0], "h", "Cleanup"),
                       "denominator": time(RAW_NUMBERS[1], "min", "baseline")}}
    def fraction(number, compound, occurrence):
        meanings = dict.fromkeys(MEANINGS)
        meanings.update(subject=witness("reference protein"), construct=witness("Native construct"),
            preparation=witness("Single mixture"), compound=witness(compound), endpoint=witness("equilibrium"),
            condition=witness("Fixed assay condition"), stage=witness("equilibrium"),
            denominator=witness("Single mixture has component A 71.234567% and component B 28.765433%"),
            measurement_basis=witness("NMR amount composition"),
            measurement_identity=witness("Single mixture" if occurrence == 0 else "component B"))
        return {"meanings": meanings, "measurement": {"number": {"witness": witness(number),
            "number_start": 0, "number_end": len(number)}, "unit": witness("%", occurrence)},
            "basis": interpreted("amount_fraction", "NMR amount composition"),
            "stage": interpreted("equilibrium"), "qualification": interpreted("source_qualified_approximate",
                "Source describes these reports as approximate")}
    partition = {"source_ref": source, "source_kind": "synthetic_fixture", "experiment": witness("Synthetic investigation"),
        "quantities": {"a": fraction(RAW_NUMBERS[2], "component A", 0),
                       "b": fraction(RAW_NUMBERS[3], "component B", 1)},
        "relationships": {field: interpreted("supported", "Common selected denominator")
            for field in ("same_preparation", "same_endpoint", "shared_denominator")},
        "evidence": [{"role": "repetition_basis", "witness": witness("One preparation; no independent repeat")},
            {"role": "composition", "witness": witness("component A 71.234567% and component B 28.765433%")}]}
    return source, artifact, times, partition


def assert_prompt(inputs, *, lookup_results=(), mixed=False, numerical_endpoint=False):
    prompt = render_literature_experimental_prompt(inputs, "Evaluate the assigned synthetic reference evidence.",
                                                   lookup_results=lookup_results)
    task, steering = prompt.split("\n\nSTEERING\n")
    assert COMPLETION_TIME_TASK in task and PRODUCT_PARTITION_TASK in task
    for token in RAW_NUMBERS:
        if numerical_endpoint and token == RAW_NUMBERS[2]:
            continue  # Explicitly requested source endpoint definition.
        assert token not in steering, (token, steering)
    assert "number_start" not in steering and "exact_minutes" not in steering
    if mixed:
        assert "completion_time_ratio" in steering and "selected_fraction_sum" in steering
        assert "ordinary_credit" in steering and "partial" in steering
        assert "heating also changed" in steering
        assert "component A" in steering and "component B" in steering
        assert "independent mass balance" in steering and "intrinsic rate" in steering
        if numerical_endpoint:
            assert NUMERICAL_ENDPOINT in steering and "31 C" in steering
    return prompt


@pytest.mark.parametrize("relationship_unknown", [False, True], ids=["shared-denominator", "unknown-denominator"])
def test_joined_optional_families_actual_loop_and_cold_exact_receipts(tmp_path, monkeypatch, relationship_unknown):
    _run_joined_optional_families(tmp_path, monkeypatch, relationship_unknown)


def test_necessary_numerical_endpoint_preserves_context_without_extra_components(tmp_path, monkeypatch):
    """A source-defined endpoint can share a number with another family.

    The fixture explicitly defines the scientific role. Source overlap alone
    cannot determine whether a numeric witness is incidental or necessary.
    """
    _run_joined_optional_families(tmp_path, monkeypatch, False, numerical_endpoint=True)


def _run_joined_optional_families(tmp_path, monkeypatch, relationship_unknown, *, numerical_endpoint=False):
    """A child contributes three own actions; its parent observes one child action."""
    store_path = tmp_path / "state"
    store = Store(store_path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    source, original_artifact, times, partition = synthetic_inputs(store, numerical_endpoint=numerical_endpoint)
    if relationship_unknown:
        partition["relationships"]["shared_denominator"] = {"value": "unknown", "witnesses": []}
    assignment = {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": [source],
                  "requested_completion_time_components": TIME_REQUEST,
                  "requested_product_partition_components": PARTITION_REQUEST}
    controllers, received, prompts = [], [], []
    def check_prompt(inputs, **options):
        return assert_prompt(inputs, numerical_endpoint=numerical_endpoint, **options)
    def source_subject_reason():
        commit = {key: [] for key in store.reasoning_schema()["required"]}
        quote = "Single mixture"
        start = TEXT.index(quote)
        commit["source_subjects"] = [{"alias": "synthetic_mixture", "reference_type": "assay",
            "source_ref": source, "label": quote, "anchor": {"source_ref": source,
                "artifact_ref": original_artifact, "start": start, "end": start + len(quote), "quote": quote}}]
        return commit
    def action(tool, arguments):
        return {"selection": {"kind": "tool", "tool": tool, "arguments": arguments},
                "report_update": {"interpretation": "partial"}}
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
        "goal": "Compare endpoint duration and product composition in the assigned synthetic preparation.",
        "scope": store.validate_scope(), "purpose": "Return only the requested descriptive components and their meanings.",
        "schema_json": json.dumps(FORM), "initial_report_json": '{"interpretation":"partial"}'}, "report_update": {}}
    def child_last(inputs):
        # Runtime current_report_update intentionally contains only the model's
        # restricted interpretation. Construct a complete recorded return for
        # the pure current/history renderer check from actual owned cells.
        time_operation = store.db.execute("SELECT * FROM literature_completion_time_operations").fetchone()
        product_operation = store.db.execute("SELECT * FROM literature_product_partition_operations").fetchone()
        time_outcome, product_outcome = (json.loads(row["outcome"]) for row in (time_operation, product_operation))
        owned = BindingContext(time_operation["run_id"], time_operation["episode_id"], "literature",
            (("literature", time_operation["episode_id"]),), store.validate_scope(), assignment, {},
            [source, *time_outcome["record_refs"], *product_outcome["record_refs"]])
        current = form_with_facts(inputs["current_report_update"], FORM, {"credit": 0,
            "literature_completion_time_cells": LiteratureCompletionTimeRepository(store, owned.run_id).fact_cells(
                owned, [time_outcome["result"]["sheet_ref"]], components=TIME_REQUEST),
            "literature_product_partition_cells": LiteratureProductPartitionRepository(store, owned.run_id).fact_cells(
                owned, [product_outcome["result"]["sheet_ref"]], components=PARTITION_REQUEST)})
        assert [r["component"] for r in current["times"]] == TIME_REQUEST
        assert [r["component"] for r in current["partition"]] == PARTITION_REQUEST
        history = {"result": {"view": "records", "records": [
            {"selection": {"kind": "tool", "tool": "literature.completion_time.populate", "arguments": times},
             "outcome": time_outcome,
             "admitted_report": current},
            {"selection": {"kind": "tool", "tool": "literature.product_partition.populate", "arguments": partition},
             "outcome": product_outcome,
             "admitted_report": current}]}}
        check_prompt({**inputs, "current_report_update": current},
                      lookup_results=[history, {"result": current}], mixed=True)
        return {"selection": {"kind": "reason", "commit": source_subject_reason()}, "report_update": {"interpretation": "partial"}}
    def parent_last(inputs):
        form, = inputs["child_reports"]
        form = plain(form)
        assert [r["component"] for r in form["times"]] == TIME_REQUEST
        assert [r["component"] for r in form["partition"]] == PARTITION_REQUEST
        time_row, = form["times"]
        product_row, = form["partition"]
        assert time_row["status"] == "bounded" and time_row["approximate"]
        lower = Fraction(60) * Fraction(RAW_NUMBERS[0]) / Fraction(RAW_NUMBERS[1])
        assert time_row["exact_domain"]["lower"] == {"numerator": str(lower.numerator), "denominator": str(lower.denominator)}
        assert not time_row["exact_domain"]["lower_inclusive"]
        assert all(q["reading"] is None for q in time_row["operands"])
        assert time_row["experiment"]["status"] == "withheld_time_operand"
        assert time_row["operands"][0]["meanings"]["subject"]["status"] == "selected"
        if numerical_endpoint:
            for operand in time_row["operands"]:
                assert operand["meanings"]["endpoint"]["status"] == "selected"
                assert operand["meanings"]["endpoint"]["witness"]["quote"] == NUMERICAL_ENDPOINT
                assert operand["meanings"]["condition"]["witness"]["quote"] == "31 C"
        assert product_row["approximate"] and product_row["uncertainty_calculation"] == "not_implemented"
        assert product_row["value"] == (None if relationship_unknown else 1)
        assert product_row["unavailable_reason"] == ("shared_denominator_unknown" if relationship_unknown else None)
        assert product_row["quantities"][0]["meaning_status"]["denominator"] == "withheld_unrequested_numbers"
        assert product_row["quantities"][0]["meaning_status"]["organism"] == "not_selected"
        assert all(q["basis"] == "amount_fraction" for q in product_row["quantities"])
        # The two routes preserve one shared source physical identity; their
        # different namespaces and transforms create no additional preparation.
        time_identity = time_row["operands"][0]["meanings"]["measurement_identity"]["witness"]
        partition_identity = store.get(product_row["quantities"][0]["measurement_identity_ref"])["anchor"]
        assert all(time_identity[field] == partition_identity[field]
                   for field in ("source_ref", "artifact_ref", "start", "end", "quote"))
        assert form["ordinary_credit"] == 0 and form["interpretation"] == "partial"
        check_prompt(inputs, lookup_results=[{"result": form}], mixed=True)
        received.append(form)
        return {"selection": {"kind": "reason", "commit": source_subject_reason()}, "report_update": {}}
    script = iter([child, action("literature.completion_time.populate", times),
                   action("literature.product_partition.populate", partition), child_last, parent_last])
    class ControlledProvider:
        async def complete(self, episode_id, role, instructions, context, output_schema):
            prompts.append(check_prompt(context))
            response = next(script)
            return response(context) if callable(response) else deepcopy(response)
        async def release(self, episode_id):
            pass
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 3)
        controllers.append(result)
        return result
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    factories = (partial(LiteratureEpisodes, rate_population=True, completion_time_population=True,
                         product_partition_population=True, reference_parent_sources=[source]),)
    try:
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ControlledProvider(),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[source], episode_binding_factories=factories,
            binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and len(received) == 1 and len(prompts) == 5
        assert [c.scores for c in controllers] == [[0, 0], [0, 0, 0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM literature_completion_time_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_product_partition_operations").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
        run_id, parent_id = store.db.execute("SELECT run_id,episode_id FROM literature_completion_time_received").fetchone()
        assert store.db.execute("SELECT run_id,episode_id FROM literature_product_partition_received").fetchone()[:] == (run_id, parent_id)
        rows = received[0]
        refs = list(dict.fromkeys([r["sheet_ref"] for r in [*rows["times"], *rows["partition"]]]))
        parent = BindingContext(run_id, parent_id, "annotation", (("annotation", parent_id),),
                                store.validate_scope(), {}, {}, refs)
        original_observations = store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]
        descriptor = json.loads((tmp_path / "run" / "run.json").read_text())["episode_bindings"][0]
        assert descriptor["configuration"]["completion_time_population"] is True
        assert descriptor["configuration"]["product_partition_population"] is True
    finally:
        store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("Cold reconstruction must not invoke a scientific reader")
    monkeypatch.setattr("gene_annotation_episode.literature_completion_time_storage.read_completion_time_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_product_partition_storage.read_product_partition_inputs", forbidden)
    with Store(store_path) as cold:
        original_get = cold.get_artifact
        def guarded(reference):
            assert reference != original_artifact, "Cold reconstruction must not reopen scientific source bytes"
            return original_get(reference)
        monkeypatch.setattr(cold, "get_artifact", guarded)
        cold.db.execute("PRAGMA query_only=ON")
        before = cold.db.total_changes
        # This is the actual saved-descriptor factory used by Workflow. Avoid
        # constructing a full Workflow, whose unrelated legacy setup writes.
        services = WorkflowServices(SimpleNamespace(store=cold, run_id=run_id))
        reconstructed, = compose_episode_bindings(services, store=cold,
            journal=SimpleNamespace(store=cold, run_id=run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None,
            role_credit_bindings={}).bindings
        assert reconstructed.as_record() == descriptor
        time_repo = reconstructed._completion_time_repository()
        product_repo = reconstructed._product_partition_repository()
        for repo, field in ((time_repo, "times"), (product_repo, "partition")):
            assert repo.received_cells(parent) == rows[field]
            assert repo.fact_cells(parent, [rows[field][0]["sheet_ref"]],
                                   components=list(repo.components)) == rows[field]
            other = replace(parent, episode_id="unrelated")
            assert repo.fact_cells(other, [rows[field][0]["sheet_ref"]], components=list(repo.components)) == []
            unrequested = next(name for name in repo.components if name != rows[field][0]["component"])
            expanded = repo.project_cells([rows[field][0]["sheet_ref"]], permitted_record_refs=refs, components=[unrequested])
            with pytest.raises(ContractError, match="cell_not_received"):
                repo.validate_fact_values(parent, expanded)
        assert cold.db.total_changes == before
        assert cold.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == original_observations


def test_both_optional_cold_repositories_are_lazy_under_query_only(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context = BindingContext("cold-run", "receiver", "annotation", (("annotation", "receiver"),),
                                 store.validate_scope(), {}, {}, [])
        store.db.execute("PRAGMA query_only=ON")
        before = store.db.total_changes
        for cls in (LiteratureCompletionTimeRepository, LiteratureProductPartitionRepository):
            repo = cls(store, context.run_id)
            assert repo.received_cells(context) == []
            assert repo.project_cells([], permitted_record_refs=[], components=[]) == []
        assert store.db.total_changes == before
        assert not store.db.execute("SELECT name FROM sqlite_master WHERE name IN "
            "('literature_completion_time_operations','literature_product_partition_operations')").fetchall()
