"""Synthetic native rate custody, original saved cells and typed subsets."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import sqlite3

import pytest

from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.domain import ContractError, obj, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository, rate_cells_schema, rate_source_cells_schema
from gene_annotation_episode.state import Store
from test_literature_rate_native_inputs import synthetic_case, defined_case


def setup_native_store(path, *, defined=False, approximate=False, reference=None):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    raw, args = defined_case() if defined else synthetic_case()
    if approximate:
        raw, args = synthetic_case(reference="about 12")
        args["arms"]["reference"]["rate"]["number"]["number_start"] += len("about ")
    if reference is not None:
        raw, args = synthetic_case(reference=reference)
        args["arms"]["reference"]["rate"]["number"]["number_start"] += reference.index("12")
    artifact = store.artifact(raw, "text/plain")
    source = store.put("source", {"provider": "synthetic_native_rate_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")
    def bind(value):
        if isinstance(value, dict):
            return {key: source["id"] if key == "source_ref" else bind(child) for key, child in value.items()}
        if isinstance(value, list):
            return [bind(child) for child in value]
        return value
    args = bind(args)
    assignment = {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": [source["id"]]}
    context = BindingContext("native-rate-run", "native-rate-episode", "literature",
        (("literature", "native-case"),), store.validate_scope(), assignment, {}, (source["id"],))
    return store, context, args


def test_native_sheet_projects_distinct_arm_bindings_and_preserves_original_required_fields(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id).source_projection()
        result = repo.populate_native(context, args, "selected")
        sheet = result["result"]["sheet_ref"]
        received = (*context.received_record_refs, *result["record_refs"])
        cells = repo.project_cells([sheet], permitted_record_refs=received, components=("rate_difference", "difference_se"))
        first = cells[0]
        assert first["value"] == pytest.approx(.009)
        assert first["assayed_subject_ref"] is None
        for role, expected in (("reference", ["enzyme Alpha", "WT", "prepR"]), ("test", ["enzyme Beta", "variant", "prepT"])):
            assert [store.get(first[role + "_" + name + "_ref"])["label"] for name in ("subject", "construct", "preparation")] == expected
        assert cells[1]["value"] is None and first["approximate"] is False
        node = rate_source_cells_schema()["items"]
        assert not set(first).difference(node["properties"])
        assert set(node["required"]) == set(node["properties"])
        assert "reference_subject_ref" not in rate_cells_schema()["items"]["properties"]
        schema = obj({"caller_selected_reference_results": rate_source_cells_schema()})
        form = form_with_facts({}, schema, {"literature_rate_source_cells": cells})
        assert validate_form(form, schema, lambda ref, ns: ref in received and store.get(ref)["record_type"] == ns) == form
        repo.validate_returned_values(cells, permitted_record_refs=received)
        parent = replace(context, role="annotation", episode_id="parent", path=(("annotation", "root"),), assignment={})
        repo.receive_cells(parent, cells, "admitted")
        repo.receive_cells(parent, cells, "admitted")
        assert repo.received_cells(parent) == cells
        assert store.db.execute("select count(*) from literature_rate_source_received").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_rate_received").fetchone()[0] == 0
        assert LiteratureRateRepository(store, context.run_id).received_cells(parent) == []
        wrong = deepcopy(cells);wrong[0]["reference_construct_ref"] = first["test_construct_ref"]
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(wrong, permitted_record_refs=received)
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


@pytest.mark.parametrize("defined", [False, True])
def test_native_reopen_is_read_only_and_replay_never_reacquires_or_reinterprets_source(tmp_path, monkeypatch, defined):
    store, context, args = setup_native_store(tmp_path, defined=defined)
    repo = LiteratureRateRepository(store, context.run_id).source_projection()
    outcome = repo.populate_native(context, args, "selected")
    reference = outcome["result"]["sheet_ref"]
    permitted = (*context.received_record_refs, *outcome["record_refs"])
    original = repo.read(reference)
    cells = repo.project_cells([reference], permitted_record_refs=permitted)
    parent = replace(context, role="annotation", episode_id="parent", path=(("annotation", "root"),), assignment={})
    repo.receive_cells(parent, cells[:2], "received")
    scientific_artifacts = {store.get(ref)["artifact_ref"] for ref in original["input_source_refs"]}
    store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved restoration must not extract source operands or refit")
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
    with Store(tmp_path) as reopened:
        reopened.db.close()
        reopened.db = sqlite3.connect(f"file:{tmp_path / 'state.sqlite3'}?mode=ro", uri=True)
        reopened.db.row_factory = sqlite3.Row
        original_get = reopened.get_artifact
        def saved_artifacts_only(ref):
            if ref in scientific_artifacts:
                raise AssertionError("original paper bytes must not be reopened")
            return original_get(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_artifacts_only)
        restored = LiteratureRateRepository(reopened, context.run_id).source_projection()
        before = reopened.db.total_changes
        assert restored.populate_native(context, args, "selected") == outcome
        assert restored.read(reference) == original
        assert restored.project_cells([reference], permitted_record_refs=permitted) == cells
        assert restored.received_cells(parent) == cells[:2]
        assert reopened.db.total_changes == before


def test_native_approximation_survives_projection_validation_and_receive(tmp_path):
    store, context, args = setup_native_store(tmp_path, approximate=True)
    try:
        repo = LiteratureRateRepository(store, context.run_id).source_projection()
        outcome = repo.populate_native(context, args, "selected")
        sheet = outcome["result"]["sheet_ref"]
        permitted = (*context.received_record_refs, *outcome["record_refs"])
        cells = repo.project_cells([sheet], permitted_record_refs=permitted, components=("reference_rate", "rate_difference"))
        assert all(row["approximate"] for row in cells)
        wrong = deepcopy(cells);wrong[0]["approximate"] = False
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(wrong, permitted_record_refs=permitted)
    finally:
        store.close()


@pytest.mark.parametrize("reference,bound", [("< approximately 12", "lt"), ("> 12", "gt")])
def test_requested_native_bound_survives_typed_subset_receive_and_saved_only_reopen(tmp_path, monkeypatch, reference, bound):
    store, context, args = setup_native_store(tmp_path, reference=reference)
    repo = LiteratureRateRepository(store, context.run_id).source_projection()
    outcome = repo.populate_native(context, args, "bounded")
    sheet = outcome["result"]["sheet_ref"]
    permitted = (*context.received_record_refs, *outcome["record_refs"])
    cells = repo.project_cells([sheet], permitted_record_refs=permitted, components=("reference_rate",))
    assert len(cells) == 1 and cells[0]["component"] == "reference_rate"
    assert cells[0]["value"] is None and cells[0]["threshold"] == pytest.approx(.012)
    assert cells[0]["bound"] == bound and cells[0]["unit"] == "umol/min/mg"
    assert cells[0]["approximate"] == ("approximately" in reference)
    assert "test_threshold" not in cells[0]
    schema = obj({"requested_reference_only": rate_source_cells_schema()})
    report = form_with_facts({}, schema, {"literature_rate_source_cells": cells})
    assert validate_form(report, schema, lambda ref, ns: ref in permitted and store.get(ref)["record_type"] == ns) == report
    repo.validate_returned_values(cells, permitted_record_refs=permitted)
    for field, value in (("threshold", 12), ("bound", "none")):
        changed = deepcopy(cells);changed[0][field] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(changed, permitted_record_refs=permitted)
    parent = replace(context, role="annotation", episode_id="parent", path=(("annotation", "root"),), assignment={})
    repo.receive_cells(parent, cells, "bounded-return")
    original = repo.read(sheet)
    source_artifacts = {store.get(ref)["artifact_ref"] for ref in original["input_source_refs"]}
    store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved bound restoration must not extract or refit")
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
    with Store(tmp_path) as reopened:
        reopened.db.close()
        reopened.db = sqlite3.connect(f"file:{tmp_path / 'state.sqlite3'}?mode=ro", uri=True)
        reopened.db.row_factory = sqlite3.Row
        original_get = reopened.get_artifact
        def saved_only(ref):
            if ref in source_artifacts:
                raise AssertionError("scientific source bytes must not be reread")
            return original_get(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        restored = LiteratureRateRepository(reopened, context.run_id).source_projection()
        before = reopened.db.total_changes
        assert restored.populate_native(context, args, "bounded") == outcome
        assert restored.project_cells([sheet], permitted_record_refs=permitted, components=("reference_rate",)) == cells
        assert restored.received_cells(parent) == cells
        assert reopened.db.total_changes == before


def test_native_replay_rechecks_source_receipt_scope_and_exact_selection(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        outcome = repo.populate_native(context, args, "selected")
        with pytest.raises(ContractError, match="not_received"):
            repo.populate_native(replace(context, received_record_refs=()), args, "selected")
        changed = deepcopy(args)
        changed["arms"]["test"]["construct"] = changed["arms"]["reference"]["construct"]
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate_native(context, changed, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            repo.populate_native(replace(context, run_id="another"), args, "new")
        with pytest.raises(ContractError, match="sheet_not_received"):
            repo.source_projection().project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=())
        with pytest.raises(ContractError, match="projection_version_mismatch"):
            repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 1
    finally:
        store.close()


def test_invalid_native_witness_has_no_partially_published_sheet(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        before = {r[0]:r[1] for r in store.db.execute("select record_type,count(*) from records group by record_type")}
        args["arms"]["reference"]["subject"]["quote"] = "invented molecule"
        with pytest.raises(ValueError, match="source_quote_mismatch"):
            repo.populate_native(context, args, "invalid")
        assert before == {r[0]:r[1] for r in store.db.execute("select record_type,count(*) from records group by record_type")}
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 0
    finally:
        store.close()


def test_interrupted_native_publication_rolls_back_records_and_recovers_original_selected_key(tmp_path, monkeypatch):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        original_put = store.put
        def fail_sheet(kind, value, **kwargs):
            if kind == "source" and value.get("provider") == repo.provider:
                raise RuntimeError("synthetic interruption before native sheet commit")
            return original_put(kind, value, **kwargs)
        monkeypatch.setattr(store, "put", fail_sheet)
        with pytest.raises(RuntimeError, match="synthetic interruption"):
            repo.populate_native(context, args, "selected")
        assert not store.list("reference") and not store.list("context")
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", original_put)
        first = repo.populate_native(context, args, "selected")
        assert repo.populate_native(context, args, "selected") == first
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 1
    finally:
        store.close()


def test_native_return_view_cannot_publish_a_legacy_table(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        native = LiteratureRateRepository(store, context.run_id).source_projection()
        with pytest.raises(ContractError, match="cannot_publish_legacy"):
            native.populate(context, args, "wrong-entrypoint")
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 0
    finally:
        store.close()


def test_legacy_projection_schema_is_exactly_the_original_closed_fifteen_field_contract():
    # Computed from the pre-edit f3d68824 storage module, not from the native
    # implementation. The original unavailable-reason enum is included.
    assert hashlib.sha256(canonical(rate_cells_schema()).encode()).hexdigest() == "3d6a3623b9387e5931a401c3d1446236fb5cbff793f5dec656ab2063cbd3b011"
    assert len(rate_cells_schema()["items"]["required"]) == 15


def test_native_projection_explicitly_rejects_a_legacy_saved_sheet(tmp_path):
    from test_literature_rate_storage import setup_store
    store, context, args = setup_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        result = repo.populate(context, args, "legacy-selected")
        with pytest.raises(ContractError, match="projection_version_mismatch"):
            repo.source_projection().project_cells([result["result"]["sheet_ref"]], permitted_record_refs=result["record_refs"])
    finally:
        store.close()
