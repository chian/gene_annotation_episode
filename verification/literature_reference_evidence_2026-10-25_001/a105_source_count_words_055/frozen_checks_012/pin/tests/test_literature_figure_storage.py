"""Synthetic native images exercise selected custody and saved-only receipts.

These pixel fixtures are not scientific measurements or an episode run.
"""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from gene_annotation_episode.communication import form_with_facts, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_figure_storage import (
    BINDINGS, COMPONENTS, FORMULA_CODES, LiteratureFigureRepository, PROVIDER,
    figure_cells_schema, figure_population_schema,
)
from gene_annotation_episode.state import Store


def source(store, content, *, parents=(), text=False):
    artifact = store.artifact(content)
    return store.put("source", {"provider": "synthetic_figure_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if text else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")


def image_bytes(rows):
    image = Image.new("RGB", (12, 12), "white")
    for y in rows:
        for x in range(2, 10):
            image.putpixel((x, y), (20, 80, 160))
    output = BytesIO()
    image.save(output, format="PNG")
    image.close()
    return output.getvalue()


def selection(unit="relative_turnover_percent"):
    return {"roi": {"left": 2, "top": 0, "right": 10, "bottom": 10},
        "rgb_min": [20, 80, 160], "rgb_max": [20, 80, 160],
        "minimum_row_fraction": 1, "minimum_run_rows": 2, "edge_tolerance_pixels": 0,
        "calibration": {"first": {"pixel": 0, "value": 100},
            "second": {"pixel": 10, "value": 0}, "unit": unit}}


def fixture(path, *, page=False, second=True, rows=range(3, 7), unit="relative_turnover_percent"):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    records = {}
    records["ancestor"] = source(store, "Synthetic source provenance.")
    # Root custody must not require decoding the original paper bytes.
    records["root"] = source(store, b"\xff\x00Synthetic paper bytes.", parents=[records["ancestor"]["id"]])
    root = records["root"]["id"]
    records["firstimage"] = source(store, image_bytes(rows), parents=[root])
    records["secondimage"] = source(store, image_bytes(range(5, 9)), parents=[root])
    text = "Subject A|Partner A|Subject B|Partner B|Experiment|Endpoint|Condition A|Condition B|Normalization|Function"
    records["literal"] = source(store, text, parents=[root], text=True)
    records["interpretation"] = source(store, "Supplied synthetic experimental design.", parents=[root])
    repeat = {"reported_n": 3, "repeat_kind": "technical", "independent_preparation_count": None,
        "spread_kind": "SD", "spread_numeric_status": "not_extracted"}
    document = {"version": "literature_figure_selection_v1",
        "first": {"image_source_ref": records["firstimage"]["id"], "image_origin": "synthetic",
            "axis_scale": "linear", "selection": selection()},
        "second": {"image_source_ref": records["secondimage"]["id"], "image_origin": "synthetic",
            "axis_scale": "linear", "selection": selection(unit)} if second else None,
        "design": {"arrangement": "coexisting_sequential_catalysts", "contrast_kind": "partner_swap",
            "endpoint_scope": "coupled_final_product", "normalization_basis": "reported_relative_turnover",
            "measurement_relation": "distinct_physical_measurements", "first_repeat": repeat,
            "second_repeat": deepcopy(repeat) if second else None}}
    records["recipe"] = source(store, json.dumps(document), parents=[root])
    literals, offset = {}, 0
    for field, quote in zip((literal for literal, _ in BINDINGS.values()), text.split("|")):
        literals[field] = {"source_ref": records["literal"]["id"], "representation": "text",
            "start": offset, "end": offset + len(quote), "quote": quote}
        offset += len(quote) + 1
    quote = "Supplied synthetic experimental design."
    args = {"source_ref": root, "data_source_ref": records["recipe"]["id"],
        "source_kind": "synthetic_fixture", "literals": literals,
        "interpretation_witnesses": [{"source_ref": records["interpretation"]["id"],
            "representation": "original", "start": 0, "end": len(quote), "quote": quote}]}
    context = BindingContext("synthetic-figure-run", "figure-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": root}} if page else {}, {},
        tuple(row["id"] for key, row in records.items() if key != "ancestor"))
    return store, context, args, records, document


def retain_recipe(store, context, args, records, document):
    row = source(store, json.dumps(document), parents=[records["root"]["id"]])
    args["data_source_ref"] = row["id"]
    records["recipe"] = row
    return replace(context, received_record_refs=(*context.received_record_refs, row["id"]))


def test_native_selected_sheet_scientific_rows_and_ten_anchored_bindings(tmp_path):
    store, context, args, records, document = fixture(tmp_path, page=True)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        validate_schema(args, figure_population_schema())
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        saved = repo.read(reference)
        assert store.get(reference)["provider"] == PROVIDER
        assert saved["version"] == "literature_figure_record_v1"
        assert saved["extraction"]["recipe"] == document
        assert saved["direct_input_source_refs"] == [records[key]["id"] for key in
            ("root", "recipe", "firstimage", "secondimage", "literal", "interpretation")]
        assert saved["input_source_refs"] == [*saved["direct_input_source_refs"], records["ancestor"]["id"]]
        cells = saved["sheet"]["cells"]
        assert cells["first_ordinate"]["value"] == 65
        assert cells["second_ordinate"]["value"] == 45
        assert cells["ordinate_difference"]["value"] == 20
        assert cells["ordinate_difference"]["unit"] == "relative_turnover_percentage_points"
        assert (cells["ordinate_difference"]["lower"], cells["ordinate_difference"]["upper"]) == (10, 30)
        rows = repo.project_cells([reference, reference], permitted_record_refs=outcome["record_refs"])
        assert [row["component"] for row in rows] == list(COMPONENTS)
        for row in rows:
            assert row["formula_code"] == FORMULA_CODES[row["component"]]
            assert row["design"] == document["design"]
            assert row["first_image_origin"] == row["second_image_origin"] == "synthetic"
            assert row["first_axis_unit"] == row["second_axis_unit"] == "relative_turnover_percent"
            assert row["evaluation_scope"] == "reference_experimental_figure_ordinates"
            assert row["statistical_uncertainty"] == "not_extracted"
            assert row["partner_necessity"] == row["target_correspondence"] == "not_evaluated"
            assert row["bound_kind"] == "conditional_digitization_not_confidence_interval"
            assert not {"selection", "image_sha256", "interpretations", "formula"} & set(row)
        for field, (literal, kind) in BINDINGS.items():
            binding = store.get(saved["experimental_bindings"][field])
            entry = saved["extraction"]["literals"][literal]
            assert binding["record_type"] == kind
            assert binding.get("label", binding.get("name")) == entry["value"]
            assert binding["anchor"] == {key: entry["witness"][key] for key in
                ("source_ref", "artifact_ref", "start", "end", "quote")}
            if kind == "context":
                assert binding["context_type"] == "assay_condition"
                assert store.get(binding["related_refs"][0])["anchor"] == binding["anchor"]
        schema = obj({"cells": figure_cells_schema()})
        validate_closed_schema(schema)
        form = form_with_facts({}, schema, {"literature_figure_cells": rows})
        assert validate_form(form, schema, lambda ref, ns:
            ref in outcome["record_refs"] and store.get(ref)["record_type"] == ns) == form
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("rows,reason", [((), "no_bar_pixels"),
    ((0, 1, 2), "truncated_mean_edge"), ((1, 2, 5, 6), "ambiguous_bar_runs")])
def test_partial_native_failures_retain_second_raw_measurement(tmp_path, rows, reason):
    store, context, args, _, _ = fixture(tmp_path, rows=rows)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "partial")
        cells = repo.read(outcome["result"]["sheet_ref"])["sheet"]["cells"]
        assert cells["first_ordinate"]["value"] is None
        assert cells["first_ordinate"]["unavailable_reason"] == reason
        assert cells["second_ordinate"]["value"] == 45
        assert cells["ordinate_difference"]["unavailable_reason"] == "missing_ordinate"


@pytest.mark.parametrize("second,unit,reason", [(False, "relative_turnover_percent", "second_ordinate_unreported"),
    (True, "arbitrary_signal", "ordinate_unit_mismatch")])
def test_missing_second_or_unit_mismatch_preserves_unknowns(tmp_path, second, unit, reason):
    store, context, args, _, _ = fixture(tmp_path, second=second, unit=unit)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "partial")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert rows[0]["value"] == 65
        assert rows[2]["value"] is rows[2]["unit"] is None
        assert rows[2]["unavailable_reason"] == reason
        assert rows[1]["value"] == (45 if second else None)
        assert rows[1]["second_image_origin"] == ("synthetic" if second else None)
        assert (rows[1]["design"]["second_repeat"] is None) == (not second)


@pytest.mark.parametrize("part", ["root", "recipe", "firstimage", "secondimage", "literal", "interpretation"])
def test_every_direct_source_requires_receipt_initial_and_replay(tmp_path, part):
    store, context, args, records, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs
            if ref != records[part]["id"]))
        for operation in ("new", "selected"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, operation)
        assert store.db.execute("select count(*) from literature_figure_operations").fetchone()[0] == 1


@pytest.mark.parametrize("part", ["root", "recipe", "firstimage", "secondimage", "literal", "interpretation", "ancestor"])
def test_all_direct_sources_and_scoped_ancestors_checked_on_replay(tmp_path, monkeypatch, part):
    store, context, args, records, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if records[part]["id"] in refs else subset(refs, scope))
        for operation in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, operation)


@pytest.mark.parametrize("part", ["root", "recipe", "firstimage", "secondimage", "literal", "interpretation"])
def test_all_direct_sources_including_recipe_images_need_page_lineage(tmp_path, part):
    store, context, args, records, document = fixture(tmp_path, page=True)
    with store:
        foreign = source(store, store.get_artifact(records[part]["artifact_ref"]))
        if part == "literal":
            for witness in args["literals"].values():
                witness["source_ref"] = foreign["id"]
        elif part == "interpretation":
            args["interpretation_witnesses"][0]["source_ref"] = foreign["id"]
        elif part in ("firstimage", "secondimage"):
            document[part.removesuffix("image")]["image_source_ref"] = foreign["id"]
            context = retain_recipe(store, context, args, records, document)
        else:
            args["source_ref" if part == "root" else "data_source_ref"] = foreign["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, foreign["id"]))
        repo = LiteratureFigureRepository(store, context.run_id)
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(context, args, "invalid")
        assert not store.list("context") and not store.list("reference")


def test_transitive_provenance_order_dedup_and_receipt_independence(tmp_path):
    store, context, args, records, document = fixture(tmp_path, page=True)
    with store:
        middle = source(store, "Intermediate source.", parents=[records["root"]["id"]])
        image = source(store, store.get_artifact(records["firstimage"]["artifact_ref"]), parents=[middle["id"]])
        document["first"]["image_source_ref"] = image["id"]
        document["second"] = deepcopy(document["first"])
        context = retain_recipe(store, context, args, records, document)
        context = replace(context, received_record_refs=(*context.received_record_refs, image["id"]))
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["direct_input_source_refs"] == [records["root"]["id"], records["recipe"]["id"],
            image["id"], records["literal"]["id"], records["interpretation"]["id"]]
        assert saved["input_source_refs"][-2:] == [records["ancestor"]["id"], middle["id"]]
        assert middle["id"] not in context.received_record_refs
        assert saved["sheet"]["cells"]["ordinate_difference"]["value"] == 0


def test_native_range_failure_remains_a_saved_partial_sheet(tmp_path):
    store, context, args, records, document = fixture(tmp_path)
    with store:
        document["first"]["selection"]["calibration"]["first"]["value"] = 10 ** 400
        context = retain_recipe(store, context, args, records, document)
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "range")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["sheet"]["cells"]["first_ordinate"]["unavailable_reason"] == "numerical_model_range"
        assert saved["sheet"]["cells"]["second_ordinate"]["value"] == 45
        assert saved["sheet"]["cells"]["ordinate_difference"]["unavailable_reason"] == "missing_ordinate"


@pytest.mark.parametrize("second", [True, False])
def test_saved_only_reopen_blocks_definitions_aliases_and_original_bytes_with_query_only(tmp_path, monkeypatch, second):
    store, context, args, records, _ = fixture(tmp_path, second=second)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        saved = repo.read(reference)
        rows = repo.project_cells([reference], permitted_record_refs=outcome["record_refs"],
            components=("ordinate_difference", "first_ordinate"))
        parent = replace(context, episode_id="parent", received_record_refs=tuple(outcome["record_refs"]))
        repo.receive_cells(parent, rows, "delivery")
        original_artifacts = {row["artifact_ref"] for row in records.values()}
        for artifact in original_artifacts:
            digest = artifact.removeprefix("artifact_")
            (Path(tmp_path) / "artifacts" / digest[:2] / digest).unlink()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved replay attempted source reading or digitization")

    import gene_annotation_episode.literature_assay_inputs as assay
    import gene_annotation_episode.literature_figure_inputs as inputs
    import gene_annotation_episode.literature_figure_measurements as native
    import gene_annotation_episode.literature_figure_storage as storage
    monkeypatch.setattr(storage, "read_figure_inputs", forbidden)
    monkeypatch.setattr(inputs, "read_figure_inputs", forbidden)
    monkeypatch.setattr(assay._Sources, "source", forbidden)
    monkeypatch.setattr(assay._Sources, "witness", forbidden)
    for module in (inputs, native):
        monkeypatch.setattr(module, "read_bar_ordinate", forbidden)
        monkeypatch.setattr(module, "compare_ordinate_cells", forbidden)
    monkeypatch.setattr(native, "_validate_selection", forbidden)
    monkeypatch.setattr(native, "_validate_cell", forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteratureFigureRepository(reopened, context.run_id)
        read = reopened.get_artifact
        def saved_only(reference):
            assert reference not in original_artifacts
            return read(reference)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("pragma query_only=ON")
        reordered = json.loads(json.dumps(args, sort_keys=True))
        assert repo.populate(context, reordered, "selected") == outcome
        assert repo.read(reference) == saved
        assert repo.project_cells([reference], permitted_record_refs=outcome["record_refs"],
            components=("ordinate_difference", "first_ordinate")) == rows
        assert repo.received_cells(parent) == rows
        repo.validate_cells(rows, sheet_refs=[reference], permitted_record_refs=outcome["record_refs"],
            components=("ordinate_difference", "first_ordinate"))


def test_transaction_rolls_back_bindings_sheet_and_operation(tmp_path, monkeypatch):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
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
        assert store.db.execute("select count(*) from literature_figure_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", put)
        assert repo.populate(context, args, "atomic")["status"] == "completed"


def test_authority_operation_identity_and_immutable_idempotence(tmp_path):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
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
            LiteratureFigureRepository(store, "different-run").read(reference)
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate(context, {**args, "source_kind": "retained_extraction"}, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            repo.populate(replace(context, run_id="different-run"), args, "new")
        with pytest.raises(ContractError, match="operation_key_required"):
            repo.populate(context, args, "")
        second = repo.populate(context, args, "second")
        assert second["changed_record_refs"] == [second["result"]["sheet_ref"]]
        outcome["result"]["cells"]["first_ordinate"]["value"] = 999
        assert repo.populate(context, args, "selected")["result"]["cells"]["first_ordinate"]["value"] == 65


def test_equal_spans_keep_ten_field_meanings_and_missing_fields_remain_null(tmp_path):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        witness = args["literals"]["first_subject"]
        args["literals"] = {field: deepcopy(witness) for field in args["literals"]}
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "equal")
        bindings = repo.read(outcome["result"]["sheet_ref"])["experimental_bindings"]
        assert len(set(bindings.values())) == 10
        for field in args["literals"]:
            args["literals"][field] = None
        args["interpretation_witnesses"] = []
        empty = repo.populate(context, args, "no-witnesses")
        saved = repo.read(empty["result"]["sheet_ref"])
        assert all(ref is None for ref in saved["experimental_bindings"].values())
        assert len(saved["direct_input_source_refs"]) == 4


def test_exact_requested_subset_admission_and_forwarding_add_no_observations(tmp_path):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        rows = repo.project_cells([reference], permitted_record_refs=outcome["record_refs"],
            components=("ordinate_difference",))
        parent = replace(context, episode_id="parent")
        repo.receive_cells(parent, rows, "delivery")
        repo.receive_cells(parent, rows, "delivery")
        assert repo.received_cells(parent) == rows
        grandparent = replace(context, episode_id="grandparent")
        repo.receive_cells(grandparent, repo.received_cells(parent), "forward")
        assert repo.received_cells(grandparent) == rows
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_cells(rows, sheet_refs=[reference], permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="duplicate_literature"):
            repo.validate_returned_values(rows * 2, permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            repo.receive_cells(parent, [], "delivery")
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([reference], permitted_record_refs=())
        for components in (("unknown",), ({},), (COMPONENTS[0], COMPONENTS[0])):
            with pytest.raises(ContractError, match="component_selection_invalid"):
                repo.project_cells([reference], permitted_record_refs=outcome["record_refs"], components=components)
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("field,value", [("value", 999), ("lower", 40), ("upper", 90),
    ("unit", "nanomolar"), ("origin", "derived"), ("formula_code", "native_first_minus_second_v1"),
    ("first_subject_ref", None), ("first_partner_ref", None), ("second_subject_ref", None),
    ("second_partner_ref", None), ("experiment_ref", None), ("endpoint_ref", None),
    ("first_condition_ref", None), ("second_condition_ref", None), ("normalization_ref", None),
    ("function_ref", None), ("second_image_source_ref", None), ("source_kind", "retained_extraction"),
    ("first_image_origin", "published"), ("second_image_origin", "published"),
    ("first_axis_unit", "nanomolar"), ("second_axis_unit", None)])
def test_forged_valid_numbers_bindings_and_scientific_meanings_rejected(tmp_path, field, value):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
            components=("first_ordinate",))
        assert rows[0][field] != value
        rows[0][field] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])


@pytest.mark.parametrize("mutate", [
    lambda row: row.update(value=float("nan")),
    lambda row: row.update(lower=float("inf")),
    lambda row: row.update(bound_kind="95 percent confidence interval"),
    lambda row: row.update(partner_necessity="necessary"),
    lambda row: row.update(statistical_uncertainty="SD"),
    lambda row: row.update(explanation="arbitrary prose"),
    lambda row: row["design"].update(explanation="arbitrary prose"),
    lambda row: row["design"]["first_repeat"].update(reported_n=True),
    lambda row: row["design"]["first_repeat"].update(independent_preparation_count=0),
])
def test_closed_rows_reject_prose_nonfinite_and_unsupported_meanings(tmp_path, mutate):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        mutate(rows[0])
        with pytest.raises(ContractError, match="representation_error"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])


def test_syntactically_valid_forged_design_meaning_rejected(tmp_path):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        rows[0]["design"]["first_repeat"]["repeat_kind"] = "biological"
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])


@pytest.mark.parametrize("mode", ["signature", "outcome_cells", "sheet_cells", "extraction_args", "image_hash", "binding"])
def test_saved_request_headers_bindings_and_exact_cells_are_verified(tmp_path, monkeypatch, mode):
    store, context, args, _, _ = fixture(tmp_path)
    with store:
        repo = LiteratureFigureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        if mode == "signature":
            store.db.execute("update literature_figure_operations set signature='{}'")
        elif mode == "outcome_cells":
            altered = deepcopy(outcome)
            altered["result"]["cells"]["first_ordinate"]["value"] = 999
            store.db.execute("update literature_figure_operations set outcome=?", (canonical(altered),))
        else:
            saved = repo.read(reference)
            if mode == "sheet_cells":
                saved["sheet"]["cells"]["first_ordinate"]["value"] = 999
            elif mode == "extraction_args":
                saved["extraction"]["arguments"]["source_kind"] = "retained_extraction"
            elif mode == "image_hash":
                saved["extraction"]["measurements"]["first"]["image_sha256"] = "0" * 64
            else:
                saved["experimental_bindings"]["first_subject_ref"] = saved["experimental_bindings"]["second_subject_ref"]
            artifact = store.get(reference)["artifact_ref"]
            read = store.get_artifact
            monkeypatch.setattr(store, "get_artifact", lambda ref:
                canonical(saved).encode() if ref == artifact else read(ref))
        with pytest.raises(ContractError, match="sheet_source_mismatch"):
            repo.read(reference)


@pytest.mark.parametrize("mode", ["unknown_axis", "unsupported_unit", "bad_witness", "extra_argument", "duplicate_json", "nonfinite_json"])
def test_invalid_selected_input_cannot_publish_records(tmp_path, mode):
    store, context, args, records, document = fixture(tmp_path)
    with store:
        if mode == "unknown_axis":
            document["first"]["axis_scale"] = "unknown"
            context = retain_recipe(store, context, args, records, document)
        elif mode == "unsupported_unit":
            document["first"]["selection"]["calibration"]["unit"] = "percent"
            context = retain_recipe(store, context, args, records, document)
        elif mode == "bad_witness":
            args["literals"]["first_subject"]["quote"] = "Different"
        elif mode == "extra_argument":
            args["measurements"] = {"first": 100}
        else:
            raw = ('{"version":1,"version":2}' if mode == "duplicate_json" else '{"value":NaN}')
            row = source(store, raw, parents=[records["root"]["id"]])
            args["data_source_ref"] = row["id"]
            context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        repo = LiteratureFigureRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        with pytest.raises((ContractError, ValueError)):
            repo.populate(context, args, "invalid")
        assert [store.list(kind) for kind in kinds] == before
        assert store.db.execute("select count(*) from literature_figure_operations").fetchone()[0] == 0
