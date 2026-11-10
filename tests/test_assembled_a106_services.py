"""Assembled A106 binding and score delivery with constructed engineering data."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import assembled_case_policy
from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.decision_context import PROTOCOL as DECISION_PROTOCOL
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_a106_subscore import COMPONENTS, NAMESPACE, REQUESTED, cells_schema
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.runtime import Workflow
from test_api_bvbrc_appservice import CONFIG as APPSERVICE_CONFIGURATION
from test_assembled_case_policy import parameters
from test_assembled_service_setup import operands, setup, ROOT_ROLES
from test_literature_a106_subscore import final_arguments
from test_literature_intervention_storage import intervention_fixture
from test_resource_service_setup import resources, forbidden
from test_runtime_decision_exchanges import ConversationProvider, select


CONFIGURATION = dict(rate_population=True, a106_intervention=True,
    reference_parent_sources=[], contract_information_profile=CONTRACT_INFORMATION_PROFILE)
PUBLICATION = Path(__file__).resolve().parents[1] / "research/slotted_process_library/publications/2026-10-24-001"


def test_assembled_root_can_commission_a106_with_configured_analysis_adapters(resources, monkeypatch):
    from gene_annotation_episode import bvbrc_tnseq_bundle_adapter as tnseq
    from gene_annotation_episode import bvbrc_rnaseq_bundle_adapter as rnaseq
    r = resources
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setenv("GENE_EPISODE_EXECUTION_MEMORY", str(r.directory / "shared-memory.sqlite3"))
    resource = deepcopy(APPSERVICE_CONFIGURATION)
    resource["scientific_adapters"] = [dict(adapter_id=module.ADAPTER_ID,
        adapter_version=module.ADAPTER_VERSION, implementation_sha256=module.implementation_sha256())
        for module in (tnseq, rnaseq)]
    r.store.create_problem(raw_sequence="MKK", molecule="protein", role="gene")
    tools = ToolRegistry(r.store)

    def factory(store, **kwargs):
        return bind_assembled_services(store, **{**operands(r), **kwargs,
            "source_directory": PUBLICATION,
            "literature_configuration": deepcopy(CONFIGURATION),
            "execution_resources": {"analysis": resource}, "initial_execution_information": {},
            "log_roles": ("stdout", "stderr")})

    provider = ConversationProvider([])
    workflow = Workflow(r.store, tools, provider, r.directory, r.run_id, forbidden, lambda *a, **k: 0.,
        job_episodes=r.homology, resource_estimator=r.estimator,
        episode_service_factory=factory, episode_service_binding={"fixture": "assembled-a106"},
        episode_service_inputs="actual_tool_registry_v1", annotation_child_roles=ROOT_ROLES,
        decision_protocol=DECISION_PROTOCOL,
        episode_record_receipts=True, initial_known_record_refs=[])
    scope = {"subject_refs": r.store.problem()["subject_refs"]}
    root = workflow.build("annotation", "root", "Investigate A106 intervention evidence", scope)
    selection = dict(kind="episode_child", role="literature",
        goal="Investigate the supplied sequence's intervention evidence", scope=scope,
        purpose="Return the A106 result and its unresolved evidence",
        schema_json=json.dumps(obj({"a106": cells_schema()})), initial_report_json='{}',
        assignment=dict(version="literature_assignment_v1", source_refs=[], question_context_refs=[],
            **{REQUESTED: list(COMPONENTS)}))
    provider.script = iter([select({"selection": selection, "report_update": {}})])
    response, index, context, schema = asyncio.run(root.source.call({
        "goal": root.goal.as_record(), "scope": scope, "visible_record_refs": [],
        "tools": workflow.catalog(scope, source=root.source)}, workflow.action_schema(root.source)))
    unit = root.source.apply_response(response, index, context, schema)
    assert unit is not None, root.source.feedback
    child = unit.child
    assert workflow.available_child_roles(child.source) == ("literature_strategy", "launch", "results")
    catalog = workflow.specialist(child.source).catalog(workflow.binding_context(child.source))
    contract = next(row for row in catalog if row["name"] == "literature.intervention_analysis.contract")
    assert contract["input_schema"]["properties"]["resource_id"] == {"enum": ["analysis"]}
    execution = workflow.episode_bindings.for_role("results")
    assert set(execution.api_execution.services["analysis"].scientific_adapters) == {
        ("bvbrc_tnseq", "1"), ("bvbrc_rnaseq", "1")}
    assert r.jobs.db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0


@pytest.mark.parametrize("wired", [False, True])
def test_assembled_a106_reconstruction_preserves_grader_and_parent_delivery(resources, monkeypatch, wired):
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: pytest.fail("unexpected network work"))
    r = resources
    tools = ToolRegistry(r.store)
    options = dict(literature_configuration=deepcopy(CONFIGURATION))
    if wired:
        options.update(execution_resources={"analysis": {"kind": "hmmer_api"}},
            initial_execution_information={}, tool_registry=tools, log_roles=("stdout", "stderr"))
    application = setup(r, **options)
    descriptor = next(row for row in application.episode_binding_descriptors if row["binding_id"] == "literature")
    options["literature_configuration"]["a106_intervention"] = False
    assert descriptor["configuration"]["a106_intervention"] is True
    assert descriptor["configuration"]["outcome_page_size"] == 7
    host = SimpleNamespace(store=r.store, run_id=r.run_id, tools=tools)
    services = WorkflowServices(host)
    # Exercise the application's ordinary reconstruction path for this binding.
    composition = compose_episode_bindings(services, store=r.store,
        journal=SimpleNamespace(store=r.store, run_id=r.run_id), execution_backend=None,
        descriptors=[descriptor], job_episodes=None, resource_estimator=None,
        role_credit_bindings={}, directory=r.directory)
    binding, = composition.bindings
    host.episode_bindings = EpisodeBindingRegistry(composition.bindings)
    assert binding.as_record() == descriptor
    r.store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    context, arguments = intervention_fixture(r.store)
    context = replace(context, run_id=r.run_id,
        assignment={**context.assignment, REQUESTED: list(COMPONENTS)})
    operations = {entry["name"] for entry in binding.catalog(context)}
    assert {"literature.intervention_grading.populate", "literature.a106.finalize"} <= operations
    assert "A106" in binding.instructions(context)
    outcome = asyncio.run(binding.execute(context, "literature.intervention_grading.populate", arguments, "assess"))
    assert outcome["status"] == "completed", outcome
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
    final = asyncio.run(binding.execute(context, "literature.a106.finalize",
        final_arguments(r.store, arguments, outcome["result"]["sheet_ref"]), "finalize"))
    assert final["status"] == "completed", final
    context = replace(context, received_record_refs=(*context.received_record_refs, *final["record_refs"]))
    rows = final["result"]["cells"]
    assert rows[0]["value"] == pytest.approx(7.5)
    form, schema = {"a106": rows}, obj({"a106": cells_schema()})
    binding.validate_report(context, form, schema)
    parent = replace(context, episode_id="assembled-parent", role="annotation", path=(("annotation", "root"),))
    references = binding.received_form_references(parent, form, schema, "assembled-final-return")
    parent = replace(parent, received_record_refs=tuple(dict.fromkeys((*parent.received_record_refs, *references))))
    assert binding.received_report_facts(parent)[NAMESPACE] == rows
    initial = binding.initial_decision_context(parent)
    assert initial["reference_evidence_parent"]["evidence_axis"] == "A106"
    assert r.jobs.db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0


def test_assembled_policy_captures_the_a106_configuration_for_resume(monkeypatch, tmp_path):
    supplied = parameters()
    supplied["services"]["literature_configuration"] = deepcopy(CONFIGURATION)
    policy = assembled_case_policy.create_policy(supplied)
    supplied["services"]["literature_configuration"]["a106_intervention"] = False
    restored = assembled_case_policy.create_policy(dict(policy=parameters()["policy"],
        services=deepcopy(policy.episode_service_binding)))
    policy.episode_service_binding["literature_configuration"]["reference_parent_sources"].append("changed")
    captured = []
    monkeypatch.setattr(assembled_case_policy, "bind_assembled_services",
        lambda store, **kwargs: captured.append(kwargs))
    for selected in (policy, restored):
        selected.episode_service_factory(object(), run_id="resume-fixture", directory=tmp_path,
            job_episodes=object(), resource_estimator=object(), tool_catalog={})
    assert [row["literature_configuration"] for row in captured] == [CONFIGURATION, CONFIGURATION]


@pytest.mark.parametrize("configuration", [
    {"a106_intervention": True},
    {"rate_population": True, "a106_intervention": "yes"},
    {"rate_population": True, "a106_intervention": True, "max_runtime_seconds": 3600},
])
def test_assembled_policy_rejects_invalid_literature_configuration_before_setup(configuration):
    supplied = parameters()
    supplied["services"]["literature_configuration"] = configuration
    with pytest.raises((ValueError, TypeError)):
        assembled_case_policy.create_policy(supplied)
