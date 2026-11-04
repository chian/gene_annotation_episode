"""Synthetic selected kinetic persistence, source custody and saved-only facts."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_storage import (
    LiteratureKineticRepository, COMPONENTS, kinetic_cells_schema,
)
from gene_annotation_episode.literature_kinetic_validation import validate_saved_kinetic
from gene_annotation_episode.state import Store
from test_literature_kinetic_inputs import fixture, SOURCE_REF, Source
from test_literature_rate_episode_integration import service_binding


def setup(path, *, kind="catalytic_efficiency", unit="uM^-1min^-1", n="8", d="2", change=None, extra=""):
    original, args = fixture(kind, unit, n, d, extra=extra)
    for role, printed in (("numerator", n), ("denominator", d)):
        if printed.startswith("<") or printed.startswith("about "):
            prefix = 1 if printed.startswith("<") else len("about ")
            args[role]["measurement"]["number"]["number_start"] += prefix
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(original.raw, "application/xml")
    source = store.put("source", {"provider": "synthetic_kinetic_fixture", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
    def bind(value):
        if isinstance(value, dict):
            return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        return source if value == SOURCE_REF else value
    args = bind(args)
    if change:
        change(args)
    context = BindingContext("kinetic-run", "kinetic-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": [source]}, {}, (source,))
    return store, context, args


def project(repo, outcome, components=None):
    return repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=components)


@pytest.mark.parametrize("kind,unit,n,expected", [("Km", "mM", ".008", 8), ("kcat", "s^-1", ".2", 12),
    ("catalytic_efficiency", "M^-1s^-1", "1000000", 60)])
def test_selected_native_dimensions_and_closed_projection(tmp_path, kind, unit, n, expected):
    store, context, args = setup(tmp_path, kind=kind, unit=unit, n=n, d=".001")
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = project(repo, outcome)
        assert len(rows) == 5 and rows[0]["value"] == pytest.approx(expected)
        assert [r["component"] for r in rows] == list(COMPONENTS)
        assert all(r["model_reader_capability"] == "unimplemented" for r in rows)
        validate_form({"numbers": rows}, obj({"numbers": kinetic_cells_schema()}), lambda *_: True)
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert len(saved["calculation"]["cells"]) == 9
        assert all(saved["calculation"]["cells"][k]["value"] is None for k in (
            "log_contrast_variance", "log_contrast_standard_uncertainty", "source_profile_log_ratio", "source_signed_index"))
        assert not store.list("assessment") and not store.list("observation")


@pytest.mark.parametrize("n,expected", [("<8", None), ("about 8", 8), ("-8", -8), ("0", 0)])
def test_source_qualifications_survive_selected_population(tmp_path, n, expected):
    store, context, args = setup(tmp_path, n=n)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        rows = project(repo, repo.populate(context, args, "selected"))
        assert rows[0]["value"] == expected
        if n == "<8":
            assert rows[0]["threshold"] == 8 and rows[0]["relation"] == "lt"
            assert rows[3]["value"] is None
        if n.startswith("about"):
            assert rows[0]["approximate"] and rows[3]["approximate"]
        if n in ("-8", "0"):
            assert rows[4]["unavailable_reason"] == "positive_parameters_required_for_log"


@pytest.mark.parametrize("change,reason", [
    (lambda a: a["numerator"]["measurement"].update(unit=None), "source_kinetic_unit_unreported"),
    (lambda a: a["numerator"].update(qualification={"value": "unknown", "witnesses": []}), "source_operand_qualification_unknown"),
    (lambda a: a["comparison"].update(subject_relationship={"value": "unknown", "witnesses": []}), "subject_relationship_unknown"),
])
def test_useful_partial_and_precise_unknowns_remain(tmp_path, change, reason):
    store, context, args = setup(tmp_path, change=change)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        rows = project(repo, repo.populate(context, args, "selected"))
        assert rows[1]["value"] == 2 and rows[3]["unavailable_reason"] == reason


def test_private_model_cells_cannot_be_requested_or_invented_as_missing_science(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        with pytest.raises(ContractError, match="component_selection_invalid"):
            repo.populate(replace(context, assignment={**context.assignment, "requested_kinetic_components": ["source_profile_log_ratio"]}), args, "invalid")
        outcome = repo.populate(context, args, "selected")
        assert set(outcome["result"]["cells"]) == set(COMPONENTS)
        with pytest.raises(ContractError, match="component_selection_invalid"):
            project(repo, outcome, ["log_contrast_variance"])


def test_subject_owner_and_exact_admitted_subset_survive_saved_only_reopen(tmp_path, monkeypatch):
    path = tmp_path / "state"
    store, context, args = setup(path)
    repo = LiteratureKineticRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
    parent = replace(owner, episode_id="parent", path=(("literature", "parent"),))
    rows = project(repo, outcome)
    assert repo.fact_cells(owner, [outcome["result"]["sheet_ref"]], components=COMPONENTS) == rows
    assert repo.fact_cells(parent, [outcome["result"]["sheet_ref"]], components=COMPONENTS) == []
    subset = [rows[3]]
    repo.receive_cells(parent, subset, "trusted-admission")
    assert repo.fact_cells(parent, [outcome["result"]["sheet_ref"]], components=COMPONENTS) == subset
    with pytest.raises(ContractError, match="cell_not_received"):
        repo.validate_fact_values(parent, rows)
    before = list(store.db.iterdump())
    paper_artifact = store.get(args["source_ref"])["artifact_ref"]
    store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Saved reads may not parse source, calculate or call a model")
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
    with Store(path) as reopened:
        restored = LiteratureKineticRepository(reopened, context.run_id)
        get = reopened.get_artifact
        def saved_only(ref):
            assert ref != paper_artifact
            return get(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("PRAGMA query_only=ON")
        assert restored.populate(context, args, "selected") == outcome
        assert restored.fact_cells(parent, [outcome["result"]["sheet_ref"]], components=COMPONENTS) == subset
        assert list(reopened.db.iterdump()) == before


def test_source_receipt_and_assigned_page_ancestry_are_actual(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        with pytest.raises(ContractError, match="source_not_received"):
            repo.populate(replace(context, received_record_refs=()), args, "not-received")
        artifact = store.artifact("unrelated", "text/plain")
        unrelated = store.put("source", {"provider": "synthetic_other", "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")
        page = {"source_ref": unrelated["id"]}
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(replace(context, role="literature_targeted", path=(("literature_targeted", "case"),), assignment={"page": page}), args, "wrong-page")
        descendant = store.put("source", {"provider": "synthetic_child", "accession": None, "uri": None,
            "artifact_ref": store.get(args["source_ref"])["artifact_ref"], "text_ref": store.get(args["source_ref"])["text_ref"],
            "request_ref": None, "version": None, "retrieved_at": None, "parent_source_refs": [unrelated["id"]]}, origin="caller")
        def bind(value):
            if isinstance(value, dict):
                return {k: bind(v) for k, v in value.items()}
            if isinstance(value, list):
                return [bind(v) for v in value]
            return descendant["id"] if value == args["source_ref"] else value
        out = repo.populate(replace(context, role="literature_targeted", path=(("literature_targeted", "case"),), assignment={"page": page},
            received_record_refs=(descendant["id"],)), bind(args), "assigned-descendant")
        assert out["status"] == "completed"


@pytest.mark.parametrize("target", ["payload", "request", "binding", "outcome"])
def test_changed_saved_record_does_not_become_original_fact(tmp_path, target):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        sheet = store.get(outcome["result"]["sheet_ref"])
        if target in ("payload", "request"):
            key = sheet["artifact_ref" if target == "payload" else "request_ref"]
            raw = store.get_artifact(key)
            from gene_annotation_episode.materials import artifact_path
            artifact_path(store, key).write_bytes(raw.replace(b'"synthetic_fixture"', b'"primary_source"', 1))
        elif target == "binding":
            reference = project(repo, outcome)[0]["numerator"]["subject"]["molecule"]
            value = store.get(reference); value["label"] = "forged molecule"
            store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(value), reference))
        else:
            forged = deepcopy(outcome); forged["result"]["cells"]["parameter_ratio"]["value"] = True
            store.db.execute("UPDATE literature_kinetic_operations SET outcome=?", (canonical(forged),))
        with pytest.raises(ContractError):
            repo.read(sheet["id"])


def test_reused_key_changes_and_detached_validation_mismatches_are_specific(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        changed = deepcopy(args); changed["source_kind"] = "primary_source"
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate(context, changed, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        saved["extraction"]["calculation_inputs"]["numerator"]["subject"]["molecule"] = "wrong"
        with pytest.raises(ExperimentalContractError, match="kinetic_saved_mismatch"):
            validate_saved_kinetic(args, saved["extraction"], saved["calculation"])


@pytest.mark.parametrize("target", ["boolean_parameter", "boolean_count", "measurement_key", "physical_owner", "malformed_nested"])
def test_detached_saved_contract_rejects_invalid_types_and_identity_associations(tmp_path, target):
    store, context, args = setup(tmp_path)
    with store:
        for role in ("numerator", "denominator"):
            args[role]["measurement_identity"] = deepcopy(args[role]["measurement"]["number"]["witness"])
        repo = LiteratureKineticRepository(store, context.run_id)
        saved = repo.read(repo.populate(context, args, "selected")["result"]["sheet_ref"])
        extraction, calculation = saved["extraction"], saved["calculation"]
        numerator = extraction["operands"]["numerator"]
        if target == "boolean_parameter":
            numerator["canonical_value"] = True
            numerator["calculation_operand"]["value"] = True
            extraction["calculation_inputs"]["numerator"]["value"] = True
            calculation["inputs"]["numerator"]["value"] = True
        elif target == "boolean_count":
            numerator["uncertainty"]["canonical"]["count"] = True
            numerator["calculation_operand"]["uncertainty"]["count"] = True
            extraction["calculation_inputs"]["numerator"]["uncertainty"]["count"] = True
            calculation["inputs"]["numerator"]["uncertainty"]["count"] = True
        elif target == "measurement_key":
            calculation["measurement_keys"]["numerator"] = calculation["measurement_keys"]["denominator"]
        elif target == "physical_owner":
            calculation["physical_measurement_ids"]["numerator"] = calculation["physical_measurement_ids"]["denominator"]
        else:
            numerator["uncertainty"] = None
        with pytest.raises(ExperimentalContractError, match="kinetic_saved_mismatch"):
            validate_saved_kinetic(args, extraction, calculation)


def test_reused_physical_observation_and_preparation_identity_remain_distinct(tmp_path):
    store, context, args = setup(tmp_path, extra="preparation shared")
    with store:
        repo = LiteratureKineticRepository(store, context.run_id)
        raw = store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode()
        preparation = Source(raw).witness("preparation shared")
        preparation["source_ref"] = args["source_ref"]
        for role in ("numerator", "denominator"):
            args[role]["context"]["preparation"] = deepcopy(preparation)
            args[role]["measurement_identity"] = deepcopy(args[role]["measurement"]["number"]["witness"])
        # The same declared preparation does not make two fitted estimates one
        # physical observation, nor establish independent biological replication.
        args["denominator"]["context"]["preparation"] = deepcopy(args["numerator"]["context"]["preparation"])
        original = repo.populate(context, args, "distinct-estimates")
        rows = project(repo, original)
        assert rows[3]["value"] == 4
        assert rows[3]["numerator"]["context"]["preparation"] == rows[3]["denominator"]["context"]["preparation"]
        assert rows[3]["numerator"]["physical_observation_ref"] != rows[3]["denominator"]["physical_observation_ref"]
        assert repo.read(original["result"]["sheet_ref"])["calculation"]["independent_preparation_count"] is None
        args["denominator"]["measurement_identity"] = deepcopy(args["numerator"]["measurement_identity"])
        repeated = project(repo, repo.populate(context, args, "same-physical-estimate"))
        assert repeated[0]["value"] == 8 and repeated[1]["value"] == 2
        assert repeated[3]["value"] is None
        assert repeated[3]["unavailable_reason"] == "conflicting_source_observation"


def test_saved_estimate_identity_retains_unicode_source_subject_and_byte_offsets(tmp_path):
    store, context, args = setup(tmp_path, kind="Km", unit="µM", extra="Molecule ProteinFixture μ")
    with store:
        raw = store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode()
        witness = Source(raw).witness("ProteinFixture μ")
        witness["source_ref"] = args["source_ref"]
        for role in ("numerator", "denominator"):
            args[role]["subject"]["molecule"] = deepcopy(witness)
            args[role]["measurement_identity"] = deepcopy(args[role]["measurement"]["number"]["witness"])
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["calculation"]["inputs"]["numerator"]["subject"]["molecule"] == "ProteinFixture μ"
        assert saved["cells"]["parameter_ratio"]["value"] == 4


@pytest.mark.parametrize("target", ["number_relation", "number_approximation", "row_approximation",
    "source_qualification", "canonical_censor", "populated_reason", "missing_unavailable_reason", "raw_value", "wrong_partial_reason"])
def test_detached_semantic_contract_rejects_qualification_and_cell_contradictions(target, monkeypatch):
    from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
    from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
    source, selection = fixture()
    if target == "wrong_partial_reason":
        selection["numerator"]["measurement"]["unit"] = None
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    calculation = populate_kinetic_contrast(extraction["calculation_inputs"])
    numerator = extraction["operands"]["numerator"]
    if target == "number_relation":
        numerator["number"]["relation"] = "gt"
    elif target == "number_approximation":
        numerator["number"]["approximate"] = True
    elif target == "row_approximation":
        numerator["approximate"] = True
    elif target == "source_qualification":
        selection["numerator"]["qualification"]["value"] = "source_qualified_approximate"
        numerator["qualification"]["value"] = "source_qualified_approximate"
    elif target == "canonical_censor":
        for operand in (numerator["calculation_operand"], extraction["calculation_inputs"]["numerator"], calculation["inputs"]["numerator"]):
            operand.update(status="censored", relation="lt")
    elif target == "populated_reason":
        calculation["cells"]["numerator_parameter"]["unavailable_reason"] = "source_measurement_unreported"
    elif target == "raw_value":
        calculation["cells"]["numerator_parameter"]["value"] = 77
    elif target == "wrong_partial_reason":
        calculation["cells"]["numerator_parameter"]["unavailable_reason"] = "source_measurement_unreported"
    else:
        calculation["cells"]["log_contrast_variance"]["unavailable_reason"] = None
    def forbidden(*_a, **_kw):
        raise AssertionError("Detached invariants may not reread sources or rerun scientific calculations")
    monkeypatch.setattr(source, "read", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_inputs.read_kinetic_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_calculations.populate_kinetic_contrast", forbidden)
    with pytest.raises(ExperimentalContractError, match="kinetic_saved_mismatch"):
        validate_saved_kinetic(selection, extraction, calculation)


@pytest.mark.parametrize("case", ["censored", "approximate", "qualified_approximate", "unknown_qualification",
    "conflicting_qualification", "missing_unit", "missing_measurement", "missing_operand", "zero"])
def test_detached_semantic_invariants_preserve_valid_native_partials(case):
    from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
    from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
    n = "<8" if case == "censored" else "about 8" if case == "approximate" else "0" if case == "zero" else "8"
    source, selection = fixture(n=n)
    numerator = selection["numerator"]
    if case in ("censored", "approximate"):
        numerator["measurement"]["number"]["number_start"] += 1 if case == "censored" else len("about ")
    elif case == "qualified_approximate":
        numerator["qualification"]["value"] = "source_qualified_approximate"
    elif case == "unknown_qualification":
        numerator["qualification"] = {"value": "unknown", "witnesses": []}
    elif case == "conflicting_qualification":
        numerator["qualification"] = {"value": "conflicting", "witnesses": [source.witness("substrateN"), source.witness("substrateD")]}
    elif case == "missing_unit":
        numerator["measurement"]["unit"] = None
    elif case == "missing_measurement":
        numerator["measurement"] = None
    elif case == "missing_operand":
        selection["numerator"] = None
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    calculation = populate_kinetic_contrast(extraction["calculation_inputs"])
    assert validate_saved_kinetic(selection, extraction, calculation) == (extraction, calculation)
