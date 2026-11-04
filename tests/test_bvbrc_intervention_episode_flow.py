"""Real custody and publication with synthetic native bytes and controlled choices.

This verifies wiring, not live service availability or autonomous biology.
"""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_rnaseq_bundle_adapter as rnaseq
from gene_annotation_episode import bvbrc_tnseq_bundle_adapter as tnseq
from gene_annotation_episode.bvbrc_application_returns import FACT_SOURCE, application_fact_sources
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.intervention_execution import (received_application_rows, analysis_children,
    prepare_analysis_contract, contract_catalog)
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.literature_a106_subscore import REQUESTED, COMPONENTS
from gene_annotation_episode.state import Store
from test_api_bvbrc_appservice import CONFIG, metadata
from test_bvbrc_appservice_custody import SavedRecords, api_assignment, selector as support_selector
from test_bvbrc_appservice_inputs import receipt_row
from bvbrc_proteome_host_fixture import ProteomeDriver, ControlledClient, OUTPUT_UUID
from test_bvbrc_comparative_systems_episode_flow import declaration
from test_intervention_analysis import arguments, DESEQ, TRANSIT
from test_literature_intervention_storage import intervention_fixture
from test_literature_a106_subscore import final_arguments


class InterventionDriver(ProteomeDriver):
    def __init__(self, store, directory, application):
        self.saved, self.store, self.application = SavedRecords(store), store, application
        adapter = rnaseq if application == "RNASeq" else tnseq
        self.config = deepcopy(CONFIG)
        self.config["scientific_adapters"] = [dict(adapter_id=adapter.ADAPTER_ID,
            adapter_version="1", implementation_sha256=adapter.implementation_sha256())]
        self.family = ExecutionEpisodes(None, store=store, directory=directory, run_id=self.saved.run_id,
            resources={"selected-api":self.config}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=("stdout", "stderr"))
        self.api, self.client = self.family.api_execution, ControlledClient()
        self.api.services["selected-api"].client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None

    def start(self, assignment):
        native = arguments(self.application)
        registry = SimpleNamespace(roles=("launch", "results"), for_role=lambda _: self.family)
        services = SimpleNamespace(workflow=SimpleNamespace(episode_bindings=registry))
        assert len(contract_catalog(services)) == 1
        selected_contract = prepare_analysis_contract(services, dict(resource_id="selected-api",
            parameters=native["parameters"], fields=[dict(field=name,
                selection=node["x-bvbrc-intervention-selection"])
                for name, node in native["requested_form"]["properties"].items()]))
        self.selected = support_selector()
        self.selected.update(endpoint="requested_projection", supplied_contents=[],
            adapter=selected_contract["adapter"], requested_schema=selected_contract["requested_schema"])
        self.selected["requirements"] = [dict(requirement_id="native-genome", role="native_output", required=True,
            declared_format=declaration("tsv"), producer_rule_evidence=None, exact_object=None)]
        self.schema = obj({"analysis":application_fact_sources()[FACT_SOURCE]["report_schema"]})
        self.parent = self.saved.child(self.saved.root, "literature", assignment, 0)
        parameters = dict(reference_genome_id="fixture.reference", output_path="/controlled/intervention",
            output_file="selected", recipe="HTSeq-DESeq" if self.application == "RNASeq" else "resampling")
        if self.application == "RNASeq":
            parameters["genome_type"] = "bacteria"
            parameters["single_end_libs"] = [dict(sample_id="reference", read="/fixture/reference.fastq", condition=0),
                dict(sample_id="intervention", read="/fixture/intervention.fastq", condition=1)]
        else:
            parameters["read_files"] = {name:{"replicates":[{"read":"/fixture/" + name + ".fastq"}]}
                for name in ("reference", "intervention")}
            parameters["experimental_conditions"] = ["reference", "intervention"]
            parameters["contrasts"] = [[0, 1]]
        self.query = dict(version="bvbrc_appservice_request_v1", effect_contract="selected_api_effects_v1",
            required_application_id=self.application, parameters=parameters, start_parameters={},
            definition_inputs=[], input_bindings=[], workspace_targets=[])
        launching = dict(version="execution_launch_assignment_v1",
            requests={"selected-api":api_assignment(self.query)}, immutable_input_versions=[], constraints={"allowed_kinds":["api"]})
        self.launch = self.saved.child(self.parent, "launch", launching, 10)
        self.saved.receipts.receive(self.launch.episode_id, self.custody.initial_references(self.launch), kind="initial")
        self.context = self.saved.child(self.launch, "launch_api", api_assignment(self.query), 0)
        self.api._manifest(self.context)
        preparation = self.call("prepare", {"definition":{"kind":"packaged", "required_application_id":self.application}})
        self.client.value = {"id":"123", "application_id":self.application, "state_code":"Q"}
        self.handoff = self.call("submit", dict(preparation_receipt_ref=preparation["source_ref"], input_evidence_refs=[]))
        self.freeze_refs(self.launch, self.context, [self.handoff["source_ref"]])
        self.freeze_refs(self.parent, self.launch, [self.handoff["source_ref"]])
        self.support = self.saved.child(self.parent, "results", dict(version="execution_results_assignment_v1",
            handoff_ref=self.handoff["source_ref"], selector=support_selector()), 20)
        self.api.initialize(self.support)
        self.client.value = {"123":{"id":"123", "application_id":self.application, "state_code":"C"}}
        self.call("status", {"handoff_ref":self.handoff["source_ref"]}, context=self.support)
        self.info = self.call("task_info", {"handoff_ref":self.handoff["source_ref"], "file":"job_result_id"}, context=self.support)
        self.freeze_refs(self.parent, self.support, [self.info["source_ref"]])
        self.selected["supplied_metadata"].append({"content":self.content(self.info["source_ref"]), "pointer":"/value"})
        self.context = self.saved.child(self.parent, "results", dict(version="execution_results_assignment_v1",
            handoff_ref=self.handoff["source_ref"], selector=self.selected), 22, schema=self.schema)
        self.api.initialize(self.context)

    def acquire(self):
        obj_ref = {"kind":"task_info_object", "receipt_ref":self.info["source_ref"]}
        self.client.value = [[metadata("/controlled/intervention/manifest", type="job_result", size=None)["native_row"]]]
        observed = self.call("workspace_metadata", {"objects":[obj_ref], "options":{}})
        obj_ref = receipt_row(observed)
        def download(obj_ref, body, role, fmt, requirements, url):
            self.client.value = [url]
            cap = self.call("download_capability", dict(objects=[obj_ref], generation=0, predecessor_receipt_ref=None))
            self.client.body = body
            return self.call("download", dict(object=obj_ref, capability=dict(kind="acquired", receipt_ref=cap["source_ref"], input_index=0),
                max_bytes=1024 * 1024, byte_range=None, requirement_ids=requirements, role=role, declared_format=declaration(fmt)))
        manifest = download(obj_ref, canonical({"id":"123", "app":{"id":self.application},
            "parameters":self.query["parameters"], "success":1,
            "output_files":[["/controlled/intervention/native", OUTPUT_UUID]]}).encode(),
            "task_manifest", "json", [], "https://controlled.invalid/manifest")
        output = dict(kind="manifest_member", manifest_receipt_ref=manifest["source_ref"], output_index=0)
        download(output, DESEQ if self.application == "RNASeq" else TRANSIT,
            "native_output", "tsv", ["native-genome"], "https://controlled.invalid/native")
        facts = self.api.application_returns.facts(self.context, self.schema)
        form = {"analysis":facts[FACT_SOURCE]}
        self.api.application_returns.validate_received_report(self.context, form, self.schema)
        self.freeze_form(self.parent, self.context, form, facts)
        key = f"{self.parent.run_id}:{self.parent.episode_id}:22:typed_form"
        refs = self.api.application_returns.record_admission(self.parent, form, self.schema, key)
        self.saved.receipts.receive(self.parent.episode_id, refs, kind="child_form", source_index=22)
        return form["analysis"]


@pytest.mark.parametrize("application", ["TnSeq", "RNASeq"])
def test_selected_analysis_result_reaches_intervention_grader_and_final_sheet(tmp_path, monkeypatch, application):
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: pytest.fail("unexpected live network"))
    with Store(tmp_path / "state") as store:
        d = InterventionDriver(store, tmp_path / "execution", application)
        original, args = intervention_fixture(store)
        assignment = {**plain(original.assignment), REQUESTED:list(COMPONENTS)}
        d.start(assignment)
        rows = d.acquire()
        registry = SimpleNamespace(roles=("launch", "results"), for_role=lambda _: d.family)
        services = SimpleNamespace(workflow=SimpleNamespace(episode_bindings=registry))
        assert analysis_children(services) == ("launch", "results")
        assert received_application_rows(services, d.parent) == rows
        context = replace(d.parent, received_record_refs=[*original.received_record_refs,
            *d.saved.receipts.known(d.parent.episode_id)])
        def reader(current, namespace, ref, fields):
            assert namespace == FACT_SOURCE
            return received_application_rows(services, current, ref, fields)
        selected = dict(kind="application_analysis", sheet_ref=rows[0]["source_ref"], field=rows[0]["field"],
            representation="deseq2" if application == "RNASeq" else "transit_resampling",
            row_ordinal=0, feature_id="geneA", metric="log2_fold_change")
        args["quantities"]["effect"] = selected
        args["quantities"]["effect_variance"] = (dict(selected, metric="effect_variance") if application == "RNASeq" else None)
        args["quantity_kind"] = "log2_fold_change"
        args["prediction_model"].update(kind="fixed_predictions_estimated_normal", variance_interpretation="estimated")
        # Numeric predictions are explicit engineered source inputs, independent
        # of the controlled analysis table; they make no biological claim.
        for role, token in (("assertion_prediction", "-2"), ("alternative_prediction", "0")):
            raw = token + " log2_ratio"
            artifact = store.artifact(raw, "text/plain")
            source = store.put("source", dict(provider="synthetic-prediction", accession=None, uri=None,
                artifact_ref=artifact, text_ref=artifact, request_ref=None, version=None, retrieved_at=None), origin="caller")["id"]
            witness = dict(source_ref=source, representation="original", start=0, end=len(raw), quote=raw)
            args["quantities"][role] = dict(kind="source_number", number=dict(witness=witness, number_start=0, number_end=len(token)),
                unit=dict(witness, start=len(token)+1, quote="log2_ratio"), origin="synthetic")
            context = replace(context, received_record_refs=[*context.received_record_refs, source])
        repo = LiteratureInterventionRepository(store, context.run_id, read_cells=reader)
        graded = repo.populate(context, args, "grade-native")
        ref = graded["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, ref])
        final = LiteratureA106SubscoreRepository(store, context.run_id).populate(context, final_arguments(store, args, ref), "final")
        value = final["result"]["cells"][0]
        if application == "RNASeq":
            assert value["value"] == pytest.approx(8.)
        else:
            assert value["value"] is None and value["status"] == "unavailable"
        saved = repo.read(ref)
        assert saved["input_component_rows"][0]["rows"] == rows
        assert rows[0]["value"]["context"]["original_task"]["native_application_id"] == application
