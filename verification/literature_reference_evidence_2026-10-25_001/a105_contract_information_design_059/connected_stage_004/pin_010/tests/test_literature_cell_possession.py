"""Actual synthetic family populations, possession and saved-only forwarding.

No primary paper, provider history or model inference is used. Reused fixtures
are explicitly synthetic; all actual repository projection overrides execute.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.state import Store
from test_literature_rate_episode_integration import service_binding


CASES = {
    "rate": ("test_literature_rate_storage", "setup_store", "Rate", "rate_cells_schema"),
    "rate_source": ("test_literature_rate_native_storage", "setup_native_store", "Rate", "rate_source_cells_schema"),
    "quantity": ("test_literature_quantity_integration", "setup_store", "Quantity", "quantity_cells_schema"),
    "assay": ("test_literature_assay_integration", "setup_store", "Assay", "assay_cells_schema"),
    "binding": ("test_literature_binding_storage", "setup_store", "Binding", "binding_cells_schema"),
    "binding_model": ("test_literature_binding_model_storage", "fixture", "BindingModel", "binding_model_cells_schema"),
    "transport": ("test_literature_transport_storage", "fixture", "Transport", "transport_response_cells_schema"),
    "perturbation": ("test_literature_perturbation_integration", "setup_case", "Perturbation", "perturbation_cells_schema"),
    "structure": ("test_literature_structure_storage", "fixture", "Structure", "structure_cells_schema"),
    "reaction": ("test_literature_reaction_storage", "fixture", "Reaction", "reaction_cells_schema"),
    "context": ("test_literature_context_storage", "fixture", "Context", "context_cells_schema"),
    "figure": ("test_literature_figure_storage", "fixture", "Figure", "figure_cells_schema"),
    "partner": ("test_literature_partner_storage", "fixture", "Partner", "partner_cells_schema"),
    "partner_source": ("test_literature_partner_native_storage", "fixture", "Partner", "partner_cells_schema"),
    "partner_defined": ("test_literature_partner_defined_storage", "fixture", "Partner", "partner_cells_schema"),
    "amount": ("test_literature_amount_storage", "setup", "Amount", "amount_cells_schema"),
    "optical": ("test_literature_optical_storage", "setup", "Optical", "optical_cells_schema"),
}


def ratio_case(path):
    # This finite synthetic prose uses no retained primary-source fixture.
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    text = ('<article><body><sec id="results"><p>Protein P variants were produced '
            'at 64% (Protein P A12G) of tagged WT levels.</p></sec></body></article>')
    artifact = store.artifact(text, "application/xml")
    source = store.put("source", {"provider": "synthetic_ratio_possession", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")
    context = BindingContext("ratio-possession-run", "ratio-child", "literature",
        (("literature", "fixture"),), store.validate_scope(), {}, {}, (source["id"],))
    args = {"source_ref": source["id"], "source_kind": "synthetic_fixture", "section_id": "results",
        "paragraph_index": 0, "subject": "Protein P", "variant": "A12G", "reference_literal": "tagged WT levels",
        "visual_source_refs": [], "signal_kind": "protein_band", "reference_role": "tagged_wt_complementation",
        "arrangement": "replacement", "interpretation_witnesses": [{"source_ref": source["id"],
            "representation": "original", "start": 0, "end": len(text.encode()), "quote": text}]}
    return store, context, args


def selected_case(kind, path):
    if kind == "ratio":
        store, context, args = ratio_case(path)
        module = importlib.import_module("gene_annotation_episode.literature_ratio_storage")
        repo_type, schema = module.LiteratureRatioRepository, module.ratio_cells_schema()
    else:
        fixture_module, fixture, class_part, schema_name = CASES[kind]
        store, context, args, *_ = getattr(importlib.import_module(fixture_module), fixture)(path)
        name = "rate" if kind == "rate_source" else "partner" if kind.startswith("partner_") else kind
        module = importlib.import_module("gene_annotation_episode.literature_" + name + "_storage")
        repo_type = getattr(module, "Literature" + class_part + "Repository")
        schema = getattr(module, schema_name)()
    context = replace(context, role="literature", path=(("literature", "owner"),),
        assignment={"version": "literature_assignment_v1", "question_context_refs": [],
                    "source_refs": list(context.received_record_refs)})
    repo = repo_type(store, context.run_id)
    if kind == "rate_source":
        repo = repo.source_projection()
        outcome = repo.populate_native(context, args, "selected")
    else:
        outcome = repo.populate(context, args, "selected")
    assert outcome["status"] == "completed"
    owner = replace(context, received_record_refs=tuple(dict.fromkeys(
        [*context.received_record_refs, *outcome["record_refs"]])))
    return store, owner, args, repo, schema, module, outcome


@pytest.mark.parametrize("kind", [*CASES, "ratio"])
def test_actual_family_owner_and_receiver_possession_reopen_without_source_or_calculator(tmp_path, monkeypatch, kind):
    store, owner, args, repo, node, module, outcome = selected_case(kind, tmp_path / "state")
    sheet = outcome["result"]["sheet_ref"]
    form_schema = obj({"requested": node})
    namespace = node["x-source"]
    repo_type = type(repo)
    try:
        services, binding = service_binding(store, owner)
        rows = repo.project_cells([sheet], permitted_record_refs=owner.received_record_refs)
        assert len(rows) > 1
        assert repo.fact_cells(owner, [sheet], components=list(repo.components)) == rows
        subset = rows[:1]
        binding.validate_report(owner, {"requested": subset}, form_schema)
        parent = replace(owner, episode_id="literature-parent", path=(("literature", "parent"),))
        assert repo.fact_cells(parent, [sheet], components=list(repo.components)) == []
        with pytest.raises(ReportBoundaryError, match="cell_not_received"):
            binding.validate_report(parent, {"requested": subset}, form_schema)
        binding.received_form_references(parent, {"requested": subset}, form_schema, "trusted-manual-admission")
        binding.received_form_references(parent, {"requested": subset}, form_schema, "trusted-manual-admission")
        assert binding.facts(parent, {"committed_record_refs": [sheet]})[namespace] == subset
        binding.validate_report(parent, {"requested": subset}, form_schema)
        # The full saved row is valid, but this reporting parent never received
        # its second cell. Whole-sheet custody must not authorize that form.
        with pytest.raises(ReportBoundaryError, match="cell_not_received"):
            binding.validate_report(parent, {"requested": rows[:2]}, form_schema)
        assert repo.fact_cells(parent, [sheet], components=[rows[1]["component"]]) == []
        outer = replace(parent, role="annotation", episode_id="annotation-parent", path=(("annotation", "root"),), assignment={})
        binding.received_form_references(outer, {"requested": subset}, form_schema, "trusted-forwarded-admission")
        assert binding.received_report_facts(outer)[namespace] == subset
        # Preserve complete typed meanings, not only the numeric value.
        assert canonical(repo.received_cells(parent)) == canonical(subset)
        scientific_artifacts = {row["artifact_ref"] for row in store.list("source")
            if not row["provider"].startswith("literature.")}
        # All lazy view tables have been constructed before read-only reopen.
        binding.facts(owner, {"committed_record_refs": [sheet]})
        original_dump = list(store.db.iterdump())
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Saved possession must not parse, calculate, reacquire or call a model")
    for name, value in list(vars(module).items()):
        if callable(value) and name.startswith(("read_", "populate_", "calculate_")):
            monkeypatch.setattr(module, name, forbidden)
    with Store(tmp_path / "state") as reopened:
        original_get = reopened.get_artifact
        def saved_only(reference):
            assert reference not in scientific_artifacts
            return original_get(reference)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        restored = repo_type(reopened, owner.run_id)
        _, rebuilt = service_binding(reopened, owner)
        reopened.db.execute("PRAGMA query_only=ON")
        before = reopened.db.total_changes
        assert restored.fact_cells(owner, [sheet], components=list(restored.components)) == rows
        assert rebuilt.facts(parent, {"committed_record_refs": [sheet]})[namespace] == subset
        assert rebuilt.received_report_facts(outer)[namespace] == subset
        rebuilt.validate_report(parent, {"requested": subset}, form_schema)
        assert reopened.db.total_changes == before
        assert list(reopened.db.iterdump()) == original_dump


@pytest.mark.parametrize("key", ["wrong-run:wrong-parent:0:typed_form", "source-rate-run:parent:x:typed_form",
    "source-rate-run:parent:01:typed_form", "source-rate-run:parent:0:other",
    "source-rate-run:parent:" + str(2**63) + ":typed_form", "source-rate-run:parent:" + "9" * 5000 + ":typed_form"])
def test_runtime_shaped_keys_cannot_claim_manual_admission(tmp_path, key):
    store, owner, _, repo, _, _, outcome = selected_case("rate", tmp_path)
    with store:
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=owner.received_record_refs,
            components=["rate_difference"])
        receiver = replace(owner, episode_id="parent")
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.receive_cells(receiver, cells, key)
        assert repo.received_cells(receiver) == []


def test_partial_runtime_state_missing_episode_table_is_structured(tmp_path):
    store, owner, _, repo, _, _, outcome = selected_case("rate", tmp_path)
    with store:
        receiver = replace(owner, episode_id="parent")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=owner.received_record_refs,
            components=["rate_difference"])
        store.db.execute("CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,"
            "form TEXT,contract TEXT,failure TEXT,child_episode_id TEXT,delivery_ref TEXT)")
        store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)",
            (owner.run_id, receiver.episode_id, 0, canonical({}), canonical({}), None, owner.episode_id, "delivery"))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.receive_cells(receiver, cells, owner.run_id + ":parent:0:typed_form")
        assert repo.received_cells(receiver) == []


def test_old_trusted_manual_receipt_without_binding_returns_limitation_without_backfill(tmp_path):
    store, owner, _, repo, _, _, outcome = selected_case("rate", tmp_path)
    with store:
        receiver = replace(owner, episode_id="parent")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=owner.received_record_refs,
            components=["rate_difference"])
        store.db.execute("INSERT INTO literature_rate_received VALUES(?,?,?,?)",
            (owner.run_id, receiver.episode_id, "old-manual", canonical(cells)))
        before = list(store.db.iterdump())
        with pytest.raises(ContractError, match="delivery_binding_unavailable"):
            repo.received_cells(receiver)
        with pytest.raises(ContractError, match="delivery_binding_unavailable"):
            repo.receive_cells(receiver, cells, "old-manual")
        assert list(store.db.iterdump()) == before


def test_wrong_native_legacy_view_never_supplies_cells_or_empty_admission(tmp_path):
    store, owner, _, native, _, _, outcome = selected_case("rate_source", tmp_path)
    with store:
        legacy = LiteratureRateRepository(store, owner.run_id)
        with pytest.raises(ContractError, match="projection_version_mismatch"):
            legacy.fact_cells(owner, [outcome["result"]["sheet_ref"]], components=[])
        with pytest.raises(ContractError, match="projection_version_mismatch"):
            legacy.validate_empty_return_family(owner)
        parent = replace(owner, episode_id="parent")
        native_cells = native.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=owner.received_record_refs,
            components=["rate_difference"])
        with pytest.raises(ContractError, match="projection_version_mismatch"):
            legacy.receive_cells(parent, native_cells, "wrong-view")
        assert native.received_cells(parent) == [] and legacy.received_cells(parent) == []


def test_owner_cannot_be_changed_by_repointing_source_request_metadata(tmp_path):
    store, owner, _, repo, _, _, outcome = selected_case("rate", tmp_path)
    with store:
        ref = outcome["result"]["sheet_ref"]
        row = store.get(ref)
        # Repointing metadata must fail even if a matching operation is planted;
        # the immutable source identity retains its original request owner.
        import json
        request = json.loads(store.get_artifact(row["request_ref"]))
        request["episode_id"] = "forged-owner"
        request_ref = store.artifact(canonical(request), "application/json")
        value = deepcopy(row); value["request_ref"] = request_ref
        store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(value), ref))
        operation = deepcopy(outcome)
        from gene_annotation_episode.domain import identity
        operation["operation_ref"] = identity("operation", {"run_id": owner.run_id, "episode_id": "forged-owner", "key": "selected"})
        store.db.execute("INSERT INTO literature_rate_operations VALUES(?,?,?,?,?)",
            (owner.run_id, "forged-owner", "selected", "forged", canonical(operation)))
        with pytest.raises(ContractError, match="owner_mismatch"):
            repo.fact_cells(replace(owner, episode_id="forged-owner"), [ref], components=["rate_difference"])
