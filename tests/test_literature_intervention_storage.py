"""Synthetic source custody, revision and typed A106 assessment delivery."""
from copy import deepcopy
from dataclasses import replace
import hashlib

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_intervention_storage import (
    LiteratureInterventionRepository, REQUESTED, COMPONENTS, intervention_cells_schema,
)
from gene_annotation_episode.literature_intervention_grading import CRITERIA
from gene_annotation_episode.literature_intervention_inputs import DESIGN_FIELDS, read_analysis_operand
from gene_annotation_episode.literature_intervention_inputs import read_application_operand
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.state import Store
from test_literature_a105_assay_type_binding_322 import grading_fixture
from test_intervention_analysis import DESEQ


def intervention_fixture(store):
    context, args, _ = grading_fixture(store)
    hypothesis = store.get(args["assertion_ref"])
    alt = {key: deepcopy(value) for key, value in hypothesis.items() if key not in {"id", "record_type", "origin"}}
    term = store.get(alt["value"]["ref"])
    record = {key: deepcopy(value) for key, value in term.items() if key not in {"id", "record_type", "origin"}}
    record.update(accession="synthetic-alternative", label="Synthetic alternative")
    alt["value"]["ref"] = store.put("term", record, origin="caller")["id"]
    args["comparison_ref"] = store.put("hypothesis", alt, origin="reasoning")["id"]
    args.update(assay_type="intervention_response", quantity_kind="endpoint_ratio",
        interpretations={key: dict(status="supported", support_refs=[args["experiment_ref"]]) for key in CRITERIA},
        experimental_design=dict.fromkeys(DESIGN_FIELDS),
        experiment_assessment=dict(experiment_ref=args["experiment_ref"], experiment_type="intervention_response",
            assessment_key="synthetic-contribution", scientific_question="Synthetic contribution?",
            conclusion="Synthetic engineered comparison only.", limitations=["No biological evidence."],
            revision_reason=None, revises_sheet_ref=None))
    assignment = {key: value for key, value in context.assignment.items() if key != "requested_assay_grading_components"}
    return replace(context, assignment={**assignment, REQUESTED:list(COMPONENTS)},
                   received_record_refs=[*context.received_record_refs, args["comparison_ref"]]), args


def test_source_reader_grader_and_parent_receipt_retain_score_and_revision_identity(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, args = intervention_fixture(store)
        repo = LiteratureInterventionRepository(store, context.run_id)
        first = repo.populate(context, args, "first")
        rows = first["result"]["cells"]
        validate_schema(rows, intervention_cells_schema())
        assert next(row for row in rows if row["component"] == "source_log_evidence_ratio")["value"] == pytest.approx(7.5)
        ref = first["result"]["sheet_ref"]
        with pytest.raises(ContractError, match="latest_revision_required"):
            repo.populate(context, args, "duplicate")
        revised = deepcopy(args)
        revised["experiment_assessment"].update(revises_sheet_ref=ref, revision_reason="Resolve attribution limitation")
        revised["interpretations"]["attribution_supported"] = dict(status="unknown", support_refs=[])
        context = replace(context, received_record_refs=[*context.received_record_refs, ref])
        second = repo.populate(context, revised, "revised")
        assert len(repo.current_assessments()) == 1
        assert repo.current_assessments()[0]["sheet_ref"] == second["result"]["sheet_ref"]
        assert repo.read(ref)["sheet"]["cells"]["source_log_evidence_ratio"]["value"] == pytest.approx(7.5)
        assert repo.read(second["result"]["sheet_ref"])["sheet"]["cells"]["source_log_evidence_ratio"]["value"] is None
        with pytest.raises(ContractError, match="latest_revision_required"):
            repo.populate(context, revised, "stale")
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),),
            received_record_refs=[*context.received_record_refs, second["result"]["sheet_ref"]])
        delivered = repo.project_cells([ref], permitted_record_refs=parent.received_record_refs,
            components=["source_log_evidence_ratio"])
        repo.receive_cells(parent, delivered, "delivery")
        assert repo.fact_cells(parent, [ref], components=["source_log_evidence_ratio"]) == delivered
    def forbidden(*args, **kwargs):
        raise AssertionError("saved read re-executed scientific work")
    monkeypatch.setattr(LiteratureInterventionRepository, "read_inputs", forbidden)
    monkeypatch.setattr(LiteratureInterventionRepository, "grade", forbidden)
    with Store(tmp_path) as store:
        store.db.execute("PRAGMA query_only=ON")
        repo = LiteratureInterventionRepository(store, context.run_id)
        assert repo.fact_cells(parent, [ref], components=["source_log_evidence_ratio"]) == delivered
        assert len(repo.current_assessments()) == 1


def test_native_table_keys_survive_duplicate_acquisition_but_not_changed_values():
    def sources(raw):
        return _Sources(lambda *_: dict(artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest(), content=raw))
    selection = dict(source_ref="source_" + "a" * 24, representation="deseq2", row_ordinal=0,
        feature_id="geneA", metric="effect_variance")
    first = read_analysis_operand(selection, sources=sources(DESEQ))
    second = read_analysis_operand({**selection, "source_ref":"source_" + "b" * 24}, sources=sources(DESEQ))
    assert first["value"] == .25 and first["measurement_keys"] == second["measurement_keys"]
    changed = read_analysis_operand(selection, sources=sources(DESEQ.replace(b"0.5",b"0.6")))
    assert changed["measurement_keys"] != first["measurement_keys"]
    with pytest.raises(ContractError, match="feature_mismatch"):
        read_analysis_operand({**selection, "feature_id":"wrong"}, sources=sources(DESEQ))


def test_admitted_application_rows_supply_only_selected_native_operands():
    from test_intervention_analysis import arguments, consume, publication, returns
    args = arguments("RNASeq")
    result = consume(args)
    body = publication(args, result)
    rows = returns.project_application_facts(body, sheet=result["sheet"], components=result["components"])[returns.FACT_SOURCE]
    selected = dict(kind="application_analysis", sheet_ref=rows[0]["source_ref"], field=rows[0]["field"],
        representation="deseq2", row_ordinal=0, feature_id="geneA", metric="effect_variance")
    def read_cells(namespace, ref, fields):
        assert namespace == returns.FACT_SOURCE and ref == selected["sheet_ref"] and fields == [selected["field"]]
        return rows
    value = read_application_operand(selected, read_cells=read_cells)
    assert value["value"] == .25 and value["origin"] == "derived"
    assert "estimated_variance_from_reported_deseq2_standard_error" in value["qualifications"]
    sources = _Sources(lambda *_: dict(content=DESEQ, artifact_ref="artifact_" + hashlib.sha256(DESEQ).hexdigest()))
    raw_selected = {key: val for key, val in selected.items() if key not in {"kind", "sheet_ref", "field"}}
    raw_selected["source_ref"] = "source_" + "c" * 24
    assert value["measurement_keys"] == read_analysis_operand(raw_selected, sources=sources)["measurement_keys"]
    with pytest.raises(ContractError, match="row_not_received"):
        read_application_operand({**selected, "row_ordinal":20}, read_cells=read_cells)
    with pytest.raises(ContractError, match="field_not_received"):
        read_application_operand(selected, read_cells=lambda *_: [])


def test_sample_file_design_requires_exact_source_correspondence_and_keeps_units(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, args = intervention_fixture(store)
        witness = deepcopy(args["quantities"]["effect"]["number"]["witness"])
        sample = dict(sample_id="synthetic-sample", identity=witness,
            file_refs=[args["source_ref"]], file_correspondence=[witness], arm="intervention",
            arm_definition=witness, biological_unit=None, technical_unit=None, pairing=None,
            batch=None, sampling_time=None)
        args["sample_bindings"] = [sample]
        repo = LiteratureInterventionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "sample-map")
        assert outcome["result"]["cells"][0]["sample_bindings"] == [sample]
        sample["file_correspondence"] = []
        with pytest.raises(ContractError, match="file_correspondence_required"):
            repo.populate(context, args, "bad-map")
        sample["file_correspondence"] = [dict(witness, quote="not the retained text")]
        with pytest.raises(ExperimentalContractError, match="source_quote_mismatch"):
            repo.populate(context, args, "invented-map")


def test_selected_a106_episode_returns_its_evidence_ratio_to_parent(tmp_path):
    import asyncio
    from functools import partial
    import json
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_runtime import FixtureController, ScriptedProvider

    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, args = intervention_fixture(store)
        provider = ScriptedProvider([
            dict(selection=dict(kind="episode_child", role="literature", assignment=plain(context.assignment),
                goal="Assess this synthetic intervention", scope=plain(context.scope), purpose="Return conditional evidence",
                schema_json=json.dumps(obj({"assessment":intervention_cells_schema()})), initial_report_json="{}"), report_update={}),
            dict(selection=dict(kind="tool", tool="literature.intervention_grading.populate", arguments=args), report_update={})])
        credit = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "workflow", controller_factory=lambda path, initial: FixtureController(str(path), initial, 1),
            project_credit=credit, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, a106_intervention=True),),
            binding_definitions={"credit":credit.as_record()}))
        receipt = store.db.execute("SELECT cells FROM literature_intervention_grading_received").fetchone()
        assert receipt is not None
        rows = json.loads(receipt["cells"])
        assert next(row for row in rows if row["component"] == "source_log_evidence_ratio")["value"] == pytest.approx(7.5)
        assert result["credit"] == 0
