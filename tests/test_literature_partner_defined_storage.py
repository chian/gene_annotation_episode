"""Source-defined units preserve authority, custody and saved-only delivery."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_partner_storage import (
    LiteraturePartnerRepository, partner_cells_schema, partner_source_population_schema,
)
from gene_annotation_episode.state import Store
from test_literature_partner_defined_inputs import fixture as input_fixture, ROOT, DATA, DEFINITION


def source(store, raw, *, parents=()):
    artifact = store.artifact(raw)
    return store.put("source", {"provider": "synthetic_defined_partner_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None, "parent_source_refs": list(parents)}, origin="caller")


def fixture(path, **kwargs):
    selected, payloads, *_ = input_fixture(**kwargs)
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    records = {"ancestor": source(store, b"Synthetic source custody.")}
    records["root"] = source(store, payloads[ROOT]["content"], parents=[records["ancestor"]["id"]])
    for name, token in (("data", DATA), ("definition", DEFINITION)):
        records[name] = source(store, payloads[token]["content"], parents=[records["root"]["id"]])
    mapping = {ROOT: records["root"]["id"], DATA: records["data"]["id"],
               DEFINITION: records["definition"]["id"]}

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(child) for key, child in value.items()}
        if isinstance(value, list):
            return [remap(child) for child in value]
        return mapping.get(value, value) if isinstance(value, str) else value

    args = remap(selected)
    context = BindingContext("defined-partner-run", "defined-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": records["root"]["id"]}}, {},
        tuple(records[key]["id"] for key in ("root", "data", "definition")))
    return store, context, args, records


def snapshot(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [tuple(row) for row in store.db.execute('SELECT * FROM "' + name + '" ORDER BY rowid')]
            for name in names}


def test_defined_population_projects_exact_v3_cells_through_the_unchanged_typed_form(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        validate_schema(args, partner_source_population_schema())
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "defined")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["extraction"]["version"] == "literature_partner_inputs_extraction_v3"
        assert saved["direct_input_source_refs"] == [records[key]["id"] for key in ("root", "data", "definition")]
        assert saved["input_source_refs"] == [*saved["direct_input_source_refs"], records["ancestor"]["id"]]
        native = saved["extraction"]["native_evidence"]["reference"]["rate"]
        assert native["unit"]["definition"]["amount"]["raw_number"] == "1"
        assert native["canonical_value"] == 7000000 and native["canonical_spread"] == 200000
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert len(rows) == 8 and rows[3]["value"] == 6900000
        assert rows[4]["value"] == pytest.approx(69/70)
        assert rows[0]["unit"] == "pmol/min/mg"
        assert rows[0]["statistical_uncertainty"] == "not_evaluated"
        schema = obj({"measurements": partner_cells_schema()})
        form = form_with_facts({}, schema, {"literature_partner_cells": rows})
        validate_form(form, schema, lambda ref, namespace: ref in outcome["record_refs"]
            and store.get(ref)["record_type"] == namespace)
        parent = replace(context, episode_id="defined-parent")
        repo.receive_cells(parent, rows, "received")
        assert repo.received_cells(parent) == form["measurements"]
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("mode", ["limit", "partial", "defined_spread", "plain_only"])
def test_existing_numerical_meanings_survive_defined_or_plain_population(tmp_path, mode):
    kwargs = {"limit": {"omitted": "<0.01"}, "partial": {"partial": True},
        "defined_spread": {"mean_unit": "plain", "spread_unit": "defined", "coefficient": "2"},
        "plain_only": {"mean_unit": "plain"}}[mode]
    store, context, args, _ = fixture(tmp_path, **kwargs)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "defined")
        saved = repo.read(out["result"]["sheet_ref"])
        rows = repo.project_cells([out["result"]["sheet_ref"]], permitted_record_refs=out["record_refs"])
        assert saved["extraction"]["version"] == "literature_partner_inputs_extraction_v" + ("2" if mode == "plain_only" else "3")
        if mode == "limit":
            assert rows[1]["value"] is None and rows[1]["upper"] == 10000
            assert saved["extraction"]["native_evidence"]["omitted"]["rate"]["value"]["relation"] == "lt"
        elif mode == "partial":
            assert rows[0]["value"] == 7000000 and rows[1]["value"] == 100000
            assert rows[3]["unavailable_reason"] == "conditions_incomplete"
        elif mode == "defined_spread":
            assert rows[0]["arm_metadata"]["reference"]["spread"] == {"kind": "SD", "magnitude": 400000}


def test_valid_padded_definition_tokens_keep_original_quotes_through_read_and_replay(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = store.get_artifact(records["definition"]["artifact_ref"])
        for arm in args["arms"].values():
            definition = arm["rate"]["unit"]["definition"]
            for name, trailing in (("amount_unit", 1), ("time_unit", 0)):
                selected = definition[name]
                selected["start"] -= 1
                selected["end"] += trailing
                selected["quote"] = raw[selected["start"]:selected["end"]].decode()
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "padded")
        saved = repo.read(outcome["result"]["sheet_ref"])
        definition = saved["extraction"]["native_evidence"]["reference"]["rate"]["unit"]["definition"]
        assert definition["amount_unit"]["quote"] == " μmol "
        assert definition["time_unit"]["quote"] == " min"
        assert saved["sheet"]["cells"]["reference_rate"]["value"] == 7000000
        assert repo.populate(context, args, "padded") == outcome
        assert repo.read(outcome["result"]["sheet_ref"]) == saved


@pytest.mark.parametrize("name", ["root", "data", "definition"])
def test_nested_definition_source_requires_receipt_for_new_work_and_replay(tmp_path, name):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        repo.populate(context, args, "defined")
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs
            if ref != records[name]["id"]))
        for key in ("defined", "new"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, key)


@pytest.mark.parametrize("name", ["definition", "ancestor"])
def test_nested_definition_and_transitive_sources_require_scope(tmp_path, monkeypatch, name):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        repo.populate(context, args, "defined")
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if records[name]["id"] in refs else subset(refs, scope))
        for key in ("defined", "new"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


def test_foreign_definition_bridge_cannot_cross_the_assigned_source_page(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        original = store.get_artifact(records["definition"]["artifact_ref"])
        foreign = source(store, original)
        for arm in args["arms"].values():
            definition = arm["rate"]["unit"]["definition"]
            for key, value in definition.items():
                if key == "amount":
                    value = value["witness"]
                if value.get("source_ref") == records["definition"]["id"]:
                    value["source_ref"] = foreign["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, foreign["id"]))
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(context, args, "foreign")
        assert store.db.execute("SELECT count(*) FROM literature_partner_operations").fetchone()[0] == 0


def test_saved_only_defined_replay_projection_and_forwarding_do_not_read_or_recalculate(tmp_path, monkeypatch):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "defined")
        sheet_ref = outcome["result"]["sheet_ref"]
        saved = repo.read(sheet_ref)
        rows = repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"],
                                 components=("reference_rate", "partner_loss_fraction"))
        parent = replace(context, episode_id="defined-parent")
        repo.receive_cells(parent, rows, "received")
        for row in records.values():
            digest = row["artifact_ref"].removeprefix("artifact_")
            (Path(tmp_path)/"artifacts"/digest[:2]/digest).unlink()
        sheet = store.get(sheet_ref)
        allowed = {sheet["artifact_ref"], sheet["request_ref"]}

    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only result used source or calculator work")

    import gene_annotation_episode.literature_partner_native_inputs as native
    import gene_annotation_episode.literature_partner_source_fields as scalar
    import gene_annotation_episode.literature_partner_defined_units as defined
    import gene_annotation_episode.literature_partner_calculations as core
    import gene_annotation_episode.literature_partner_storage as storage
    import gene_annotation_episode.literature_partner_inputs as dispatcher
    import gene_annotation_episode.literature_assay_inputs as assay
    origins = {module.__name__ for module in (native, scalar, defined, core)}
    for module in (native, scalar, defined, core, storage, dispatcher):
        for name, value in tuple(vars(module).items()):
            if callable(value) and getattr(value, "__module__", None) in origins:
                monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(storage, "read_partner_inputs", forbidden)
    monkeypatch.setattr(assay._Sources, "source", forbidden)
    monkeypatch.setattr(assay._Sources, "witness", forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteraturePartnerRepository(reopened, context.run_id)
        get_artifact, reads = reopened.get_artifact, []
        def saved_only(ref):
            assert ref in allowed
            reads.append(ref)
            return get_artifact(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("PRAGMA query_only=ON")
        before = snapshot(reopened)
        assert repo.populate(context, json.loads(json.dumps(args)), "defined") == outcome
        assert repo.read(sheet_ref) == saved
        assert repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"],
            components=("reference_rate", "partner_loss_fraction")) == rows
        assert repo.received_cells(parent) == rows
        assert snapshot(reopened) == before
        assert set(reads) == allowed


def test_original_payload_authority_rejects_consistently_changed_definition_metadata(tmp_path, monkeypatch):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "defined")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        artifact_ref = store.get(ref)["artifact_ref"]
        original = store.get_artifact
        for mode in ("coefficient_value", "multiplier", "version", "raw_number", "canonical", "endpoint"):
            changed = deepcopy(saved)
            rate = changed["extraction"]["native_evidence"]["reference"]["rate"]
            if mode == "coefficient_value":
                rate["unit"]["definition"]["amount"]["value"] = 2
            elif mode == "multiplier":
                rate["unit"]["multiplier"] = 2000000
            elif mode == "version":
                changed["extraction"]["version"] = "literature_partner_inputs_extraction_v2"
            elif mode == "raw_number":
                rate["unit"]["definition"]["amount"]["raw_number"] = "2"
            elif mode == "canonical":
                rate["canonical_value"] = 999
            else:
                rate["unit"]["definition"]["endpoint"] = deepcopy(changed["extraction"]["native_evidence"]["reference"]["subject"])
            with monkeypatch.context() as patch:
                patch.setattr(store, "get_artifact", lambda key:
                    canonical(changed).encode() if key == artifact_ref else original(key))
                with pytest.raises(ContractError, match="sheet_source_mismatch"):
                    repo.read(ref)


def test_saved_nested_relationship_validation_is_not_only_a_payload_digest_check(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "defined")
        extraction = repo.read(out["result"]["sheet_ref"])["extraction"]
        for mode in ("endpoint_link", "entity", "partial_entity", "coefficient_token", "unit_meaning", "time_meaning", "version"):
            selected, evidence, core = deepcopy((args, extraction["native_evidence"], extraction["recipe"]["inputs"]))
            chosen = selected["arms"]["reference"]["rate"]["unit"]["definition"]
            found = evidence["reference"]["rate"]["unit"]["definition"]
            version = "literature_partner_inputs_extraction_v3"
            if mode == "endpoint_link":
                chosen["endpoint"] = deepcopy(selected["arms"]["reference"]["subject"])
                found["endpoint"] = deepcopy(evidence["reference"]["subject"])
            elif mode == "entity":
                chosen["endpoint_entity"] = deepcopy(selected["arms"]["reference"]["endpoint"])
                found["endpoint_entity"] = deepcopy(evidence["reference"]["endpoint"])
            elif mode == "partial_entity":
                for key in ("endpoint_entity", "definition_entity"):
                    for entry in (chosen[key], found[key]):
                        entry["end"] -= 1
                        entry["quote"] = entry["quote"][:-1]
            elif mode == "coefficient_token":
                found["amount"]["raw_number"] = "2"
            elif mode == "unit_meaning":
                for entry in (chosen["amount_unit"], found["amount_unit"]):
                    entry["quote"] = "grams"
            elif mode == "time_meaning":
                for entry in (chosen["time_unit"], found["time_unit"]):
                    entry["quote"] = "hour"
            else:
                version = "literature_partner_inputs_extraction_v2"
            with pytest.raises(ContractError):
                repo._validate_native_saved(selected, evidence, core, version=version)


def test_v2_validation_does_not_accept_a_defined_field_or_a_v3_label(tmp_path):
    store, context, args, _ = fixture(tmp_path, mean_unit="plain")
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "plain")
        extraction = repo.read(out["result"]["sheet_ref"])["extraction"]
        evidence, core = extraction["native_evidence"], extraction["recipe"]["inputs"]
        with pytest.raises(ContractError, match="sheet_source_mismatch"):
            repo._validate_native_saved(args, evidence, core, version="literature_partner_inputs_extraction_v3")
        evidence["reference"]["rate"]["unit"]["definition"] = {}
        with pytest.raises(ContractError):
            repo._validate_native_saved(args, evidence, core, version="literature_partner_inputs_extraction_v2")


def test_defined_publication_interruption_rolls_back_bindings_and_selected_result(tmp_path, monkeypatch):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        before = snapshot(store)
        put = store.put
        def interrupted(kind, value, **kwargs):
            if kind == "source" and value["provider"] == repo.provider:
                raise RuntimeError("synthetic defined publication interruption")
            return put(kind, value, **kwargs)
        monkeypatch.setattr(store, "put", interrupted)
        with pytest.raises(RuntimeError, match="publication interruption"):
            repo.populate(context, args, "defined")
        assert snapshot(store) == before
