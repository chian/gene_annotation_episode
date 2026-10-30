"""Synthetic custody, exact-subset communication, rendering and source-free replay."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import plain, validate_form, validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_product_partition_storage import (LiteratureProductPartitionRepository,
    product_partition_cells_schema, binding_references)
from gene_annotation_episode.literature_product_partition_render import render_received, is_row
from test_literature_product_partition_inputs import fixture, SOURCE, TEXT


def setup(path, raw=TEXT, arguments=None):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(raw, "text/plain")
    source = store.put("source", {"provider": "retained_primary_pmc12051542" if arguments and arguments["source_kind"] == "primary_source" else "synthetic_partition_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")["id"]
    args, _, witness = fixture(raw) if arguments is None else (deepcopy(arguments), None, None)
    # A deliberately overbroad witness containing both native operands must
    # never disclose them through a derived-only or one-fraction typed return.
    if arguments is None:
        args["quantities"]["a"]["meanings"]["denominator"] = witness("R5P 60.3% and Ru5P 39.7%")
        args["evidence"] = [{"role": "composition", "witness": witness("R5P 60.3% and Ru5P 39.7%")},
                            {"role": "competing_contribution", "witness": witness("HFP preparation")}]
    def replace_ref(value):
        if isinstance(value, dict): return {k: replace_ref(v) for k, v in value.items()}
        if isinstance(value, list): return [replace_ref(v) for v in value]
        return source if value == SOURCE else value
    args = replace_ref(args)
    context = BindingContext("partition-run", "partition-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": [source]}, {}, [source])
    return store, context, args


def test_exact_parent_subset_keeps_meaning_without_disclosing_unrequested_operands(tmp_path):
    validate_closed_schema(obj({"partition": product_partition_cells_schema()}))
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref, refs = outcome["result"]["sheet_ref"], outcome["record_refs"]
        assert repo.project_cells([ref], permitted_record_refs=refs) == []
        rows = repo.project_cells([ref], permitted_record_refs=refs, components=["selected_fraction_sum"])
        validate_schema(rows, product_partition_cells_schema())
        validate_form({"partition": rows}, obj({"partition": product_partition_cells_schema()}),
            lambda reference, namespace: store.reference_subset([reference], plain(context.scope)))
        assert len(rows) == 1 and rows[0]["value"] == 1
        assert rows[0]["quantities"][0]["denominator_ref"] is None
        assert rows[0]["evidence"][0]["witness_ref"] is None
        assert rows[0]["evidence"][0]["availability"] == "withheld_unrequested_numbers"
        assert rows[0]["evidence"][1]["witness_ref"] is not None
        assert all("value" not in q for q in rows[0]["quantities"])
        records = {r: store.get(r) for r in binding_references(rows)}
        display = []
        render_received(display, rows, records,
            section=lambda parts, title, value: parts.append(title + "\n" + str(value)),
            table=lambda header, body: str(list(header)) + str(list(body)))
        text = "\n".join(display)
        assert "60.3" not in text and "39.7" not in text and "0.603" not in text and "0.397" not in text
        assert "R5P" in text and "Ru5P" in text and "equilibrium" in text
        assert is_row(rows[0])
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


@pytest.mark.parametrize("mutation", [lambda r: r.update(value=99),
    lambda r: r["quantities"][0].update(basis="signal_fraction"),
    lambda r: r["relationships"].update(shared_denominator="unknown")])
def test_changed_returned_number_or_meaning_is_rejected(tmp_path, mutation):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=["partition_a_over_b"])
        mutation(rows[0])
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])
    finally: store.close()


def test_source_free_read_reconstruction_and_replay_preserve_only_admitted_subset(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    repo = LiteratureProductPartitionRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    ref = outcome["result"]["sheet_ref"]
    rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=["partition_a_over_b"])
    parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={}, received_record_refs=[ref])
    repo.receive_cells(parent, rows, "delivery")
    repo.receive_cells(parent, rows, "delivery")
    artifact = store.get(args["source_ref"])["artifact_ref"]
    assert repo.fact_cells(parent, [ref], components=["partition_a_fraction", "partition_a_over_b"]) == rows
    store.close()
    def forbidden(*args, **kwargs): raise AssertionError("Source reader must not run on replay")
    monkeypatch.setattr("gene_annotation_episode.literature_product_partition_storage.read_product_partition_inputs", forbidden)
    with Store(tmp_path) as reopened:
        original = reopened.get_artifact
        def get(reference):
            assert reference != artifact, "Scientific source bytes must not be reopened"
            return original(reference)
        monkeypatch.setattr(reopened, "get_artifact", get)
        repo = LiteratureProductPartitionRepository(reopened, context.run_id)
        reopened.db.execute("PRAGMA query_only=ON")
        before = reopened.db.total_changes
        assert repo.populate(context, args, "selected") == outcome
        assert repo.received_cells(parent) == rows
        assert repo.fact_cells(parent, [ref], components=["selected_fraction_sum"]) == []
        assert reopened.db.total_changes == before
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=[]), args, "selected")


def test_source_scope_and_assigned_page_limit_access(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=[]), args, "no-receipt")
        artifact = store.artifact("Other paper", "text/plain")
        other = store.put("source", {"provider": "other", "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(replace(context, role="literature_page", path=(("literature_page", "page"),), assignment={"source_ref": other}), args, "outside")
        assert not repo._installed()
    finally: store.close()


def test_cold_query_only_discovery_and_received_lookup_create_no_tables(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        store.db.execute("PRAGMA query_only=ON")
        before = store.db.total_changes
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        assert repo.received_cells(context) == []
        assert repo.project_cells([], permitted_record_refs=[]) == []
        assert not repo._installed()
        assert store.db.total_changes == before
    finally: store.close()


def test_own_population_outcome_has_only_original_requested_typed_subset(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        context = replace(context, assignment={**plain(context.assignment),
            "requested_product_partition_components": ["selected_fraction_sum"]})
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        assert [row["component"] for row in outcome["result"]["cells"]] == ["selected_fraction_sum"]
        assert outcome["result"]["cells"][0]["quantities"][0]["meaning_status"]["denominator"] == "withheld_unrequested_numbers"
        assert len(repo.read(outcome["result"]["sheet_ref"])["sheet"]["cells"]) == 5
        records = [store.get(ref) for ref in outcome["record_refs"] if store.get(ref)["record_type"] == "reference"]
        assert all("60.3" not in row["label"] and "39.7" not in row["label"] for row in records)
        changed = replace(context, assignment={**plain(context.assignment), "requested_product_partition_components": ["partition_a_fraction"]})
        with pytest.raises(ContractError, match="operation_key_reused"):
            repo.populate(changed, args, "selected")
    finally: store.close()
