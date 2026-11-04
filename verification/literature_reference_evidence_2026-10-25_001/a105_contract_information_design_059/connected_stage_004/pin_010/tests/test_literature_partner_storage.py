"""Selected retained-fixture custody, scientific returns and saved-only replay."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import form_with_facts, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_partner_storage import (
    BINDINGS, COMPONENTS, FORMULA_CODES, LiteraturePartnerRepository, PROVIDER,
    partner_cells_schema, partner_population_schema,
)
from gene_annotation_episode.state import Store


def source(store, content, *, parents=(), text=False):
    artifact = store.artifact(content)
    return store.put("source", {"provider": "synthetic_partner_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if text else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")


def arm(role, value):
    return {"subject_ref": "synthetic_subject", "partner_ref": "synthetic_partner",
        "partner_state": "absent" if role == "omitted" else "present",
        "endpoint_ref": "synthetic_product", "normalization_ref": "per_mg_subject",
        "unit": "pmol/min/mg", "conditions": {"coverage": "complete", "factors": [
            {"factor": "nitrogen_source", "level": "glutamine", "unit": "identity"},
            {"factor": "temperature", "level": 37, "unit": "degC"}]},
        "measurement": {"measurement_id": "synthetic_measurement_" + role,
            "status": "observed", "value": value, "origin": "synthetic",
            "spread": {"kind": "unreported", "magnitude": None}}}


def fixture(path, *, page=False, mode="matched"):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    records = {"ancestor": source(store, "Synthetic provenance.")}
    records["root"] = source(store, b"\xff\x00Synthetic binary paper.", parents=[records["ancestor"]["id"]])
    root = records["root"]["id"]
    text = "Subject|Partner|Experiment|Endpoint|Normalization|Reference condition|Omission condition|Addback condition|Function"
    records["literal"] = source(store, text, parents=[root], text=True)
    quote = "Synthetic condition and measurement interpretations."
    records["interpretation"] = source(store, quote, parents=[root])
    document = {"version": "literature_partner_selection_v1", "inputs": {
        "version": "literature_partner_inputs_v1", "arms": {
            role: arm(role, value) for role, value in (("reference", 100), ("omitted", 20), ("addback", 90))}}}
    arms = document["inputs"]["arms"]
    if mode == "censored":
        arms["omitted"]["measurement"].update(status="upper_bound", value=5)
    elif mode == "crossed":
        arms["reference"]["measurement"].update(value=774, spread={"kind": "unspecified", "magnitude": 58})
        arms["omitted"]["measurement"].update(value=284, spread={"kind": "unspecified", "magnitude": 33})
        for role in ("reference", "omitted"):
            arms[role]["normalization_ref"] = None
            arms[role]["conditions"]["coverage"] = "partial"
        arms["omitted"]["conditions"]["factors"][0]["level"] = "ammonium_sulfate"
        arms["addback"] = None
    elif mode == "missing":
        arms["addback"] = None
    elif mode == "all_missing":
        document["inputs"]["arms"] = dict.fromkeys(("reference", "omitted", "addback"))
    records["recipe"] = source(store, json.dumps(document), parents=[root])
    literals, offset = {}, 0
    for (literal, _), text_quote in zip(BINDINGS.values(), text.split("|")):
        literals[literal] = {"source_ref": records["literal"]["id"], "representation": "text",
            "start": offset, "end": offset + len(text_quote), "quote": text_quote}
        offset += len(text_quote) + 1
    args = {"source_ref": root, "data_source_ref": records["recipe"]["id"],
        "source_kind": "synthetic_fixture", "literals": literals,
        "interpretation_witnesses": [{"source_ref": records["interpretation"]["id"],
            "representation": "original", "start": 0, "end": len(quote), "quote": quote}]}
    context = BindingContext("synthetic-partner-run", "partner-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": root}} if page else {}, {},
        tuple(row["id"] for key, row in records.items() if key != "ancestor"))
    return store, context, args, records, document


def retain_recipe(store, context, args, records, document):
    row = source(store, json.dumps(document), parents=[records["root"]["id"]])
    args["data_source_ref"] = row["id"]
    records["recipe"] = row
    return replace(context, received_record_refs=(*context.received_record_refs, row["id"]))


def test_selected_sheet_has_eight_actual_components_and_nine_anchored_bindings(tmp_path):
    store, context, args, records, document = fixture(tmp_path, page=True)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        validate_schema(args, partner_population_schema())
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        saved = repo.read(reference)
        assert store.get(reference)["provider"] == PROVIDER
        assert saved["version"] == "literature_partner_record_v1"
        assert saved["extraction"]["recipe"] == document
        assert saved["direct_input_source_refs"] == [records[key]["id"] for key in
            ("root", "recipe", "literal", "interpretation")]
        assert saved["input_source_refs"] == [*saved["direct_input_source_refs"], records["ancestor"]["id"]]
        assert saved["factor_bindings"] == {}
        rows = repo.project_cells([reference, reference], permitted_record_refs=outcome["record_refs"])
        assert [row["component"] for row in rows] == list(COMPONENTS)
        assert [row["value"] for row in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
        for row in rows:
            assert row["formula_code"] == FORMULA_CODES[row["component"]]
            assert row["evaluation_scope"] == "reference_experimental_partner_components"
            assert row["statistical_uncertainty"] == row["target_correspondence"] == "not_evaluated"
            assert row["partner_necessity"] == "not_inferred"
            assert row["arm_metadata"]["reference"]["spread"] == {"kind": "unreported", "magnitude": None}
            assert row["comparison_checks"]["reference_omitted"] == {
                "status": "matched", "differing_factor_refs": [], "unavailable_reason": None}
            assert not {"inputs", "recipe", "interpretations", "formula"} & set(row)
        for field, (literal, kind) in BINDINGS.items():
            binding = store.get(saved["experimental_bindings"][field])
            entry = saved["extraction"]["literals"][literal]
            assert binding["record_type"] == kind
            assert binding.get("label", binding.get("name")) == entry["value"]
            assert binding["anchor"] == {key: entry["witness"][key] for key in
                ("source_ref", "artifact_ref", "start", "end", "quote")}
            if kind == "context":
                assert store.get(binding["related_refs"][0])["anchor"] == binding["anchor"]
        schema = obj({"cells": partner_cells_schema()})
        validate_closed_schema(schema)
        form = form_with_facts({}, schema, {"literature_partner_cells": rows})
        assert validate_form(form, schema, lambda ref, ns:
            ref in outcome["record_refs"] and store.get(ref)["record_type"] == ns) == form
        assert not store.list("observation") and not store.list("assessment")


def test_crossed_conditions_keep_native_spreads_and_return_actual_factor_terms(tmp_path):
    store, context, args, records, _ = fixture(tmp_path, mode="crossed")
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        saved = repo.read(reference)
        factor_ref = saved["factor_bindings"]["nitrogen_source"]
        factor = store.get(factor_ref)
        assert factor["namespace"] == "literature_partner_condition_factor"
        assert factor["source_ref"] == records["recipe"]["id"]
        assert factor["label"] == "nitrogen_source" and factor["anchor"] is None
        assert factor_ref in outcome["record_refs"] and factor_ref in outcome["changed_record_refs"]
        assert saved["extraction"]["calculation"]["comparison_checks"]["reference_omitted"]["differing_factors"] == ["nitrogen_source"]
        rows = repo.project_cells([reference], permitted_record_refs=outcome["record_refs"])
        assert rows[0]["value"] == 774 and rows[1]["value"] == 284
        assert all(row["value"] is None for row in rows[3:])
        assert rows[0]["comparison_checks"]["reference_omitted"] == {
            "status": "different", "differing_factor_refs": [factor_ref],
            "unavailable_reason": "nonpartner_conditions_differ"}
        assert rows[0]["arm_metadata"]["reference"]["spread"] == {"kind": "unspecified", "magnitude": 58}
        assert rows[0]["arm_metadata"]["omitted"]["spread"] == {"kind": "unspecified", "magnitude": 33}
        assert rows[0]["arm_metadata"]["addback"] is None
        schema = obj({"cells": partner_cells_schema()})
        validate_form({"cells": rows}, schema,
            lambda ref, ns: ref in outcome["record_refs"] and store.get(ref)["record_type"] == ns)


@pytest.mark.parametrize("mode", ["censored", "missing", "all_missing"])
def test_censor_domains_and_missing_arms_survive_save_and_projection(tmp_path, mode):
    store, context, args, _, _ = fixture(tmp_path, mode=mode)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        rows = repo.project_cells([out["result"]["sheet_ref"]], permitted_record_refs=out["record_refs"])
        if mode == "censored":
            row = next(row for row in rows if row["component"] == "addback_fraction")
            assert row["status"] == "bounded" and row["value"] is None
            assert Fraction(row["lower"]) <= Fraction(85, 95)
            assert Fraction(row["upper"]) >= Fraction(9, 10)
            assert row["bound_kind"] == "conditional_input_domain_not_CI"
        else:
            assert rows[2]["value"] is rows[2]["origin"] is rows[2]["unit"] is None
            assert rows[2]["unavailable_reason"] == "arm_unreported"
            assert rows[4]["value"] == (.8 if mode == "missing" else None)


@pytest.mark.parametrize("part", ["root", "recipe", "literal", "interpretation"])
def test_each_direct_source_requires_actual_receipt_initial_and_replay(tmp_path, part):
    store, context, args, records, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != records[part]["id"]))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, key)
        assert store.db.execute("select count(*) from literature_partner_operations").fetchone()[0] == 1


@pytest.mark.parametrize("part", ["root", "recipe", "literal", "interpretation", "ancestor"])
def test_direct_and_transitive_sources_need_scope_on_population_and_replay(tmp_path, monkeypatch, part):
    store, context, args, records, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if records[part]["id"] in refs else subset(refs, scope))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


@pytest.mark.parametrize("part", ["root", "recipe", "literal", "interpretation"])
def test_every_direct_source_requires_assigned_page_lineage(tmp_path, part):
    store, context, args, records, _ = fixture(tmp_path, page=True)
    with store:
        foreign = source(store, store.get_artifact(records[part]["artifact_ref"]))
        if part == "literal":
            for witness in args["literals"].values():
                witness["source_ref"] = foreign["id"]
        elif part == "interpretation":
            args["interpretation_witnesses"][0]["source_ref"] = foreign["id"]
        else:
            args["source_ref" if part == "root" else "data_source_ref"] = foreign["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, foreign["id"]))
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(context, args, "new")
        assert not store.list("context") and not store.list("reference")


@pytest.mark.parametrize("mode", ["matched", "crossed", "censored", "missing"])
def test_saved_only_reopen_blocks_original_bytes_and_all_reader_calculator_aliases(tmp_path, monkeypatch, mode):
    store, context, args, records, _ = fixture(tmp_path, page=True, mode=mode)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        saved = repo.read(reference)
        rows = repo.project_cells([reference], permitted_record_refs=outcome["record_refs"], components=("addback_fraction", "reference_rate"))
        parent = replace(context, episode_id="parent", received_record_refs=tuple(outcome["record_refs"]))
        repo.receive_cells(parent, rows, "delivery")
        originals = {row["artifact_ref"] for row in records.values()}
        for artifact in originals:
            digest = artifact.removeprefix("artifact_")
            (Path(tmp_path) / "artifacts" / digest[:2] / digest).unlink()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved replay attempted source reading or numerical recomputation")

    import gene_annotation_episode.literature_assay_inputs as assay
    import gene_annotation_episode.literature_partner_inputs as inputs
    import gene_annotation_episode.literature_partner_calculations as core
    import gene_annotation_episode.literature_partner_storage as storage
    monkeypatch.setattr(storage, "read_partner_inputs", forbidden)
    monkeypatch.setattr(inputs, "read_partner_inputs", forbidden)
    monkeypatch.setattr(inputs, "populate_partner_components", forbidden)
    for name, value in vars(core).copy().items():
        if callable(value) and getattr(value, "__module__", None) == core.__name__:
            monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr(assay._Sources, "source", forbidden)
    monkeypatch.setattr(assay._Sources, "witness", forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteraturePartnerRepository(reopened, context.run_id)
        read = reopened.get_artifact
        def saved_only(reference):
            assert reference not in originals
            return read(reference)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("pragma query_only=ON")
        assert repo.populate(context, json.loads(json.dumps(args, sort_keys=True)), "selected") == outcome
        assert repo.read(reference) == saved
        assert repo.project_cells([reference], permitted_record_refs=outcome["record_refs"], components=("addback_fraction", "reference_rate")) == rows
        assert repo.received_cells(parent) == rows
        repo.validate_cells(rows, sheet_refs=[reference], permitted_record_refs=outcome["record_refs"], components=("addback_fraction", "reference_rate"))


def test_transaction_rolls_back_all_bindings_terms_sheet_and_operation(tmp_path, monkeypatch):
    store, context, args, _, _ = fixture(tmp_path, mode="crossed")
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        artifact_count = store.db.execute("select count(*) from artifacts").fetchone()[0]
        put = store.put
        def fail(kind, record, **kwargs):
            if kind == "source" and record["provider"] == PROVIDER:
                raise RuntimeError("synthetic publication interruption")
            return put(kind, record, **kwargs)
        monkeypatch.setattr(store, "put", fail)
        with pytest.raises(RuntimeError, match="publication interruption"):
            repo.populate(context, args, "atomic")
        assert [store.list(kind) for kind in kinds] == before
        assert store.db.execute("select count(*) from artifacts").fetchone()[0] == artifact_count
        assert store.db.execute("select count(*) from literature_partner_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", put)
        assert repo.populate(context, args, "atomic")["status"] == "completed"


def test_operation_run_identity_authority_and_idempotence(tmp_path):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        reference = out["result"]["sheet_ref"]
        actual = store.get(reference)
        record = {key: value for key, value in actual.items() if key not in ("id", "record_type", "origin")}
        caller_copy = store.put("source", record, origin="caller")
        with pytest.raises(ContractError, match="sheet_required"):
            repo.read(caller_copy["id"])
        record["retrieved_at"] = "2026-01-01T00:00:00Z"
        copy = store.put("source", record, origin="tool")
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.read(copy["id"])
        with pytest.raises(ContractError, match="sheet_run_mismatch"):
            LiteraturePartnerRepository(store, "other-run").read(reference)
        with pytest.raises(ContractError, match="run_mismatch"):
            repo.populate(replace(context, run_id="other-run"), args, "new")
        with pytest.raises(ContractError, match="operation_key_required"):
            repo.populate(context, args, "")
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate(context, {**args, "source_kind": "retained_extraction"}, "selected")
        second = repo.populate(context, args, "second")
        assert second["changed_record_refs"] == [second["result"]["sheet_ref"]]
        out["result"]["cells"]["reference_rate"]["value"] = 999
        assert repo.populate(context, args, "selected")["result"]["cells"]["reference_rate"]["value"] == 100


def test_equal_spans_preserve_nine_roles_and_missing_bindings_are_null(tmp_path):
    store, context, args, _, document = fixture(tmp_path)
    with store:
        args["literals"] = {field: deepcopy(args["literals"]["subject"]) for field in args["literals"]}
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "equal")
        assert len(set(repo.read(out["result"]["sheet_ref"])["experimental_bindings"].values())) == 9
        args["literals"] = dict.fromkeys(args["literals"])
        out = repo.populate(context, args, "missing")
        saved = repo.read(out["result"]["sheet_ref"])
        assert all(value is None for value in saved["experimental_bindings"].values())


def test_exact_subset_admission_and_forwarding_no_extra_observations(tmp_path):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        ref = out["result"]["sheet_ref"]
        rows = repo.project_cells([ref], permitted_record_refs=out["record_refs"], components=("partner_loss_fraction",))
        parent = replace(context, episode_id="parent")
        repo.receive_cells(parent, rows, "delivery")
        repo.receive_cells(parent, rows, "delivery")
        assert repo.received_cells(parent) == rows
        grandparent = replace(parent, episode_id="grandparent")
        repo.receive_cells(grandparent, repo.received_cells(parent), "forward")
        assert repo.received_cells(grandparent) == rows
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_cells(rows, sheet_refs=[ref], permitted_record_refs=out["record_refs"])
        with pytest.raises(ContractError, match="duplicate_literature"):
            repo.validate_returned_values(rows * 2, permitted_record_refs=out["record_refs"])
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            repo.receive_cells(parent, [], "delivery")
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([ref], permitted_record_refs=())
        for components in (("unknown",), ({},), (COMPONENTS[0], COMPONENTS[0])):
            with pytest.raises(ContractError, match="component_selection_invalid"):
                repo.project_cells([ref], permitted_record_refs=out["record_refs"], components=components)
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("field,value", [("value", 999), ("lower", -1), ("upper", 1000),
    ("unit", "per_min"), ("origin", "reported"), ("formula_code", "native_partner_omitted_v1"),
    ("subject_ref", None), ("partner_ref", None), ("experiment_ref", None), ("endpoint_ref", None),
    ("normalization_ref", None), ("reference_condition_ref", None), ("omitted_condition_ref", None),
    ("addback_condition_ref", None), ("function_ref", None), ("source_kind", "retained_extraction")])
def test_forged_valid_cells_and_bindings_fail_exact_saved_value_validation(tmp_path, field, value):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        rows = repo.project_cells([out["result"]["sheet_ref"]], permitted_record_refs=out["record_refs"], components=("partner_loss",))
        assert rows[0][field] != value
        rows[0][field] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=out["record_refs"])


@pytest.mark.parametrize("change", [
    lambda row: row.update(value=float("nan")),
    lambda row: row.update(lower=float("inf")),
    lambda row: row.update(partner_necessity="necessary"),
    lambda row: row.update(statistical_uncertainty="SD"),
    lambda row: row.update(explanation="arbitrary prose"),
    lambda row: row["arm_metadata"]["reference"]["spread"].update(extra="unrestricted prose"),
    lambda row: row["comparison_checks"]["reference_omitted"].update(differing_factors=["nitrogen_source"]),
])
def test_closed_forms_reject_prose_and_changed_meanings(tmp_path, change):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        rows = repo.project_cells([out["result"]["sheet_ref"]], permitted_record_refs=out["record_refs"])
        change(rows[0])
        with pytest.raises(ContractError, match="representation_error"):
            repo.validate_returned_values(rows, permitted_record_refs=out["record_refs"])


@pytest.mark.parametrize("mode", ["signature", "outcome_cells", "sheet_cells", "extraction_args", "binding", "factor_binding", "native_spread", "check_status"])
def test_saved_authority_headers_bindings_and_meanings_are_verified(tmp_path, monkeypatch, mode):
    store, context, args, _, _ = fixture(tmp_path, mode="crossed")
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        ref = out["result"]["sheet_ref"]
        if mode == "signature":
            store.db.execute("update literature_partner_operations set signature='{}'")
        elif mode == "outcome_cells":
            altered = deepcopy(out)
            altered["result"]["cells"]["reference_rate"]["value"] = 999
            store.db.execute("update literature_partner_operations set outcome=?", (canonical(altered),))
        else:
            saved = repo.read(ref)
            if mode == "sheet_cells":
                saved["sheet"]["cells"]["reference_rate"]["value"] = 999
            elif mode == "extraction_args":
                saved["extraction"]["arguments"]["source_kind"] = "retained_extraction"
            elif mode == "binding":
                saved["experimental_bindings"]["subject_ref"] = saved["experimental_bindings"]["partner_ref"]
            elif mode == "factor_binding":
                saved["factor_bindings"]["nitrogen_source"] = saved["experimental_bindings"]["endpoint_ref"]
            elif mode == "native_spread":
                saved["extraction"]["recipe"]["inputs"]["arms"]["reference"]["measurement"]["spread"]["kind"] = "SD"
            else:
                saved["extraction"]["calculation"]["comparison_checks"]["reference_omitted"]["status"] = "matched"
            artifact = store.get(ref)["artifact_ref"]
            read = store.get_artifact
            monkeypatch.setattr(store, "get_artifact", lambda key: canonical(saved).encode() if key == artifact else read(key))
        with pytest.raises(ContractError, match="sheet_source_mismatch"):
            repo.read(ref)


@pytest.mark.parametrize("mode", ["false_matched_check", "false_condition_difference", "incompatible_populated_loss", "fraction_unit", "baseline_reuse_addback"])
def test_saved_relationship_validation_rejects_consistently_repeated_corruption(tmp_path, monkeypatch, mode):
    # Corrupt all repeated saved copies, so equality between payload/outcome
    # alone cannot excuse a contradicted experimental meaning.
    store, context, args, records, document = fixture(tmp_path, mode="crossed" if mode.startswith("false_") or mode == "incompatible_populated_loss" else "matched")
    with store:
        if mode == "baseline_reuse_addback":
            document["inputs"]["arms"]["addback"] = deepcopy(document["inputs"]["arms"]["reference"])
            context = retain_recipe(store, context, args, records, document)
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        if mode in ("false_matched_check", "false_condition_difference"):
            check = saved["extraction"]["calculation"]["comparison_checks"]["reference_omitted"]
            if mode == "false_matched_check":
                check.update(status="matched", differing_factors=[], unavailable_reason=None)
                outcome["result"]["comparison_checks"]["reference_omitted"].update(
                    status="matched", differing_factor_refs=[], unavailable_reason=None)
            else:
                check["differing_factors"] = ["temperature"]
                # Temperature is shared but numerically equal; a subset-of-field
                # check must not call that an observed condition difference.
        else:
            name = "addback_gain" if mode == "baseline_reuse_addback" else "partner_loss_fraction"
            for cells in (saved["sheet"]["cells"], saved["extraction"]["cells"],
                    saved["extraction"]["calculation"]["cells"], outcome["result"]["cells"]):
                if mode == "fraction_unit":
                    cells[name]["unit"] = "per_min"
                else:
                    cells[name].update(value=.8, lower=.8, upper=.8, status="populated", unavailable_reason=None)
        store.db.execute("update literature_partner_operations set outcome=?", (canonical(outcome),))
        artifact = store.get(ref)["artifact_ref"]
        read = store.get_artifact
        monkeypatch.setattr(store, "get_artifact", lambda key: canonical(saved).encode() if key == artifact else read(key))
        with pytest.raises(ContractError, match="sheet_source_mismatch"):
            repo.read(ref)


@pytest.mark.parametrize("mode", ["bad_witness", "extra_argument", "duplicate_json", "nonfinite_json"])
def test_bad_selected_inputs_never_publish_bindings_or_operations(tmp_path, mode):
    store, context, args, records, _ = fixture(tmp_path)
    with store:
        if mode == "bad_witness":
            args["literals"]["subject"]["quote"] = "Different"
        elif mode == "extra_argument":
            args["rate"] = 999
        else:
            raw = '{"version":1,"version":2}' if mode == "duplicate_json" else '{"value":NaN}'
            record = source(store, raw, parents=[records["root"]["id"]])
            args["data_source_ref"] = record["id"]
            context = replace(context, received_record_refs=(*context.received_record_refs, record["id"]))
        repo = LiteraturePartnerRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        with pytest.raises((ContractError, ValueError)):
            repo.populate(context, args, "invalid")
        assert [store.list(kind) for kind in kinds] == before
        assert store.db.execute("select count(*) from literature_partner_operations").fetchone()[0] == 0
