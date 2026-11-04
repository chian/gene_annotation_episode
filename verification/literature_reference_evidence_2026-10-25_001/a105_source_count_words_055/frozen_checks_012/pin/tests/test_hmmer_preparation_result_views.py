"""V1 selection over retained native D1 envelopes; synthetic corruptions labeled.

Native bytes are graded before projection. The projection purity test disables
all readers/calculators and IO after preparing saved envelopes. These tests do
not claim capture authentication or parent/child publication integration.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import hmmer_preparation_result_views as views
from gene_annotation_episode import native_hmmer_preparation_worker as worker
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.state import Store
from tests import test_native_hmmer_preparation_worker as native


MODES = [(program, mode) for program, modes in PROGRAM_MODES.items() for mode in modes]


def prepared(args):
    grading = worker.grade_hmmer_preparation(**args)
    occurrences = [{**item["occurrence"], "format": args["formats"][item["occurrence"]["occurrence_id"]],
        "relative_path": direction + "/" + role + "/" + str(item["occurrence"]["ordinal"])}
        for direction, group in (("input", args["inputs"]), ("output", args["outputs"]))
        for role, items in group.items() for item in items]
    return grading, occurrences


def selection(collection="calculations", *, quantities=None, checks=None, rows=None, artifacts=None):
    return {"version": "native_hmmer_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": None if collection is None else {"collection": collection,
            "rows": {"offset": 0, "limit": 100000} if rows is None else rows,
            "quantities": [] if quantities is None else quantities, "checks": [] if checks is None else checks},
        "artifacts": [] if artifacts is None else artifacts}


def project(grading, occurrences, selector):
    return views.project_preparation_result(grading, selector=selector, source_ref="source:original", occurrences=occurrences)


def scalar_values(result, path):
    return [(r["record_key"], q["value"], q["state"]) for r in result["rows"] for q in r["quantities"] if q["path"] == path]


def all_selections(grading, occurrences):
    catalog = views.preparation_projection_catalog(**{k: grading["operation"][k] for k in ("program", "mode")})
    for collection, entry in catalog.items():
        yield collection, project(grading, occurrences, selection(collection, quantities=list(entry["quantities"]), checks=entry["checks"]))


@pytest.mark.parametrize("case", native.CASES, ids=lambda case: case["case"])
def test_every_retained_native_execution_variant(case):
    grading, occurrences = prepared(native.bundle_arguments(native.P1 / case["bundle"], case["bundle_sha256"]))
    for collection, result in all_selections(grading, occurrences):
        source = grading["calculations"]["rows"] if collection == "calculations" else grading["sheet"][collection]
        assert result["population"]["total_records"] == len(source)


@pytest.mark.parametrize("program,mode", MODES)
def test_direct_saved_mode_envelopes_cover_all_fixed_scalar_component_cells(program, mode):
    # D1's saved mode envelopes use actual270 corrected S1 operations, plus267.
    directory = native.ROOT / "verification/tool_graders_hmmer_preparation_grading_2026-10-26_271/modes001"
    manifest = json.loads((directory / "manifest.json").read_text())
    item = next(r for r in manifest if (r["program"], r["mode"]) == (program, mode))
    raw = (directory / item["grading"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item["grading_sha256"]
    grading = json.loads(raw)
    occurrences = [{**o, "format": grading["formats"][o["occurrence_id"]],
        "relative_path": o["direction"] + "/" + o["role"] + "/" + str(o["ordinal"])} for o in grading["sheet"]["artifact_occurrences"]]
    projected = {}
    for collection, result in all_selections(grading, occurrences):
        assert result["population"]["omitted_records"] == 0
        if collection == "calculations":
            projected = {r["record_key"]: {q["path"]: q for q in r["quantities"]} for r in result["rows"]}
    definitions, _ = views._definitions(program, mode)
    def cells(value, prefix=""):
        if type(value) is dict:
            if set(value) == {"value", "state", "unit", "inputs"}:
                yield prefix
            else:
                for key, child in value.items():
                    if key != "symbol_counts":  # A dynamic symbol table, retained like the other arrays.
                        yield from cells(child, (prefix + "." if prefix else "") + key)
    for row in grading["calculations"]["rows"]:
        kind = views._kind(row, views._FAMILIES[program], "calculations")
        assert set(cells(row)) <= set(definitions["calculations"][kind])
        key = views._key(row, views._FAMILIES[program], "calculations")
        for path in cells(row):
            original = row
            for part in path.split("."):
                original = original[part]
            assert projected[key][path] == {"path": path, **{field: original[field] for field in ("value", "state", "unit")}}


@pytest.mark.parametrize("program,mode", MODES)
def test_every_mode_projects_every_declared_scalar_and_check(program, mode):
    grading, occurrences = prepared(native.selected(program, mode))
    original = deepcopy((grading, occurrences))
    catalog = views.preparation_projection_catalog(program, mode)
    for collection, entry in catalog.items():
        selected = selection(collection, quantities=list(entry["quantities"]), checks=entry["checks"])
        result = project(grading, occurrences, selected)
        source = grading["calculations"]["rows"] if collection == "calculations" else grading["sheet"][collection]
        assert result["population"]["total_records"] == result["population"]["returned_records"] == len(source)
        assert result["population"]["omitted_records"] == 0
        for name, schema in (("rows", views.ROW_SCHEMA), ("artifacts", views.ARTIFACT_SCHEMA)):
            validate_form({name: result[name]}, {"type": "object", "additionalProperties": False,
                "properties": {name: {"type": "array", "items": schema}}, "required": [name]}, lambda *_: True)
        validate_form(result["population"], views.POPULATION_SCHEMA, lambda *_: True)
        assert all(set(row) == set(views.ROW_SCHEMA["properties"]) for row in result["rows"])
    assert (grading, occurrences) == original


def test_independently_known_native_numerical_answers():
    examples = [
        (native.dna_statistics(), "components.mean_match_relative_entropy", 1.0074921672642938),
        (native.legacy_simulation(), "components.mean", -5.619071923450204),
        (native.selected("hmmemit", "consensus_simple"), "length", 12),
        (native.selected("makehmmerdb", "build"), "components.source_symbol_total", 28),
        (native.selected("makehmmerdb", "build"), "components.actual_database_bytes", 314),
        (native.legacy_artifact("hmmpress_success"), "bundle_byte_sum", 16024),
        (native.selected("hmmbuild", "build_alignment"), "components.input_sequence_count", 3),
        (native.selected("hmmbuild", "build_alignment"), "components.input_column_count", 14),
        (native.selected("hmmbuild", "build_alignment"), "components.model_length", 12),
        (native.legacy_mask(), "components.masked_fraction", 5 / 14),
    ]
    for args, path, expected in examples:
        grading, occurrences = prepared(args)
        result = project(grading, occurrences, selection(quantities=[path]))
        measured = [value for _, value, state in scalar_values(result, path) if state == "present"]
        assert any(value == pytest.approx(expected) for value in measured), (path, measured)


@pytest.mark.parametrize("indexed,expected", [(False, 1), (True, 2)])
def test_actual_alias_counts_and_duplicate_representation_are_preserved(indexed, expected):
    grading, occurrences = prepared(native.legacy_artifact("hmmfetch_" + ("indexed" if indexed else "unindexed") + "_alias"))
    result = project(grading, occurrences, selection(quantities=["returned_model_occurrence_count", "expected_returned_model_occurrence_count"],
        rows={"record_keys": ["key_population"]}))
    assert [q["value"] for q in result["rows"][0]["quantities"]] == [expected, expected]
    outputs = project(grading, occurrences, selection("output_records", quantities=["length"]))
    assert len({r["record_key"] for r in outputs["rows"]}) == expected


def test_actual_empty_output_and_unknown_abi_do_not_become_measurements():
    args = native.selected("hmmbuild", "build_single_sequence_matrix", case="supplied_matrix")
    assert args["outputs"]["resaved_alignment"][0]["content"] == b""
    grading, occurrences = prepared(args)
    empty = project(grading, occurrences, selection(None, artifacts=[{"direction": "output", "role": "resaved_alignment", "ordinal": 0}]))
    assert empty["artifacts"][0]["size_bytes"] == 0
    assert empty["artifacts"][0]["completeness"] == "complete"
    args = native.legacy_simulation()
    args["native_abi"] = None  # Synthetic removal of the original declaration.
    grading, occurrences = prepared(args)
    result = project(grading, occurrences, selection(quantities=["components.observed_count", "components.mean"]))
    scores = [r for r in result["rows"] if r["kind"] == "score_statistics"]
    assert scores and all(q["value"] is None and q["state"] != "present" for r in scores for q in r["quantities"])


def test_exact_selective_disclosure_and_same_bytes_in_separate_roles():
    grading, occurrences = prepared(native.selected("hmmconvert", "ascii"))
    output = next(o for o in occurrences if o["role"] == "converted_models")
    stdout = next(o for o in occurrences if o["role"] == "stdout")
    assert output["sha256"] == stdout["sha256"]
    result = project(grading, occurrences, selection("output_records", quantities=["length"]))
    assert {(o["direction"], o["role"]) for o in result["artifacts"]} == {("output", "converted_models")}
    assert result["rows"][0]["artifact_ref"] == output["artifact_ref"]
    requested = [{k: o[k] for k in ("direction", "role", "ordinal")} for o in (stdout, output)]
    both = project(grading, occurrences, selection(None, artifacts=requested))
    assert [o["role"] for o in both["artifacts"]] == ["stdout", "converted_models"]
    assert both["population"]["returned_artifact_count"] == 2
    assert all(o["sha256"] == output["sha256"] for o in both["artifacts"])
    assert all("sequence" not in r and "positions" not in r and "inputs" not in r for r in result["rows"])


def test_explicit_keys_windows_missing_artifacts_and_order():
    grading, occurrences = prepared(native.selected("hmmconvert", "ascii"))
    keys = [r["row_key"] for r in grading["calculations"]["rows"]]
    result = project(grading, occurrences, selection(quantities=["decoded_model_count"],
        rows={"record_keys": [keys[1], "absent:key", keys[0]]},
        artifacts=[{"direction": "output", "role": "converted_models", "ordinal": 8}]))
    assert [r["record_key"] for r in result["rows"]] == [keys[1], keys[0]]
    assert result["population"]["missing_record_keys"] == ["absent:key"]
    assert result["population"]["missing_artifacts"] == [{"direction": "output", "role": "converted_models", "ordinal": 8}]
    assert result["population"]["omitted_records"] == len(keys) - 2
    empty = project(grading, occurrences, selection(quantities=["decoded_model_count"], rows={"offset": len(keys), "limit": 2**30}))
    assert empty["rows"] == [] and empty["population"]["omitted_records"] == len(keys)


def test_artifact_only_with_unavailable_numerical_grading():
    grading, occurrences = prepared(native.selected("hmmconvert", "ascii"))
    grading.update(sheet=None, calculations=None)
    selector = selection(None, artifacts=[{"direction": "output", "role": "converted_models", "ordinal": 0}])
    result = project(grading, occurrences, selector)
    assert len(result["artifacts"]) == 1 and result["rows"] == []
    assert result["population"]["collection"] is None
    assert result["population"]["total_records"] == result["population"]["returned_records"] == result["population"]["omitted_records"] == 0
    with pytest.raises(ContractError, match="saved_numerical_grading_unavailable"):
        project(grading, occurrences, selection(quantities=["decoded_model_count"]))


@pytest.mark.parametrize("mutation", ["unknown_path", "arbitrary_array", "duplicate_quantity", "bool_limit", "zero_limit", "bool_ordinal", "extra_field", "wrong_collection", "wrong_role", "duplicate_artifact"])
def test_selector_rejects_undeclared_or_ambiguous_requests(mutation):
    selector = selection(quantities=["decoded_model_count"])
    if mutation == "unknown_path": selector["projection"]["quantities"] = ["confidence"]
    elif mutation == "arbitrary_array": selector["projection"]["quantities"] = ["positions.0.match.cells.0.probability"]
    elif mutation == "duplicate_quantity": selector["projection"]["quantities"] *= 2
    elif mutation == "bool_limit": selector["projection"]["rows"]["limit"] = True
    elif mutation == "zero_limit": selector["projection"]["rows"]["limit"] = 0
    elif mutation == "bool_ordinal": selector["artifacts"] = [{"direction": "output", "role": "stdout", "ordinal": False}]
    elif mutation == "extra_field": selector["scores"] = []
    elif mutation == "wrong_collection": selector["projection"]["collection"] = "positions"
    elif mutation == "wrong_role": selector["artifacts"] = [{"direction": "input", "role": "queries", "ordinal": 0}]
    elif mutation == "duplicate_artifact": selector["artifacts"] = [{"direction": "output", "role": "stdout", "ordinal": 0}] * 2
    with pytest.raises(ContractError):
        views.validate_preparation_result_selector(selector, program="hmmconvert", mode="ascii")


@pytest.mark.parametrize("mutation", ["schema", "operation", "occurrence", "digest", "bool_value", "nonfinite", "wrong_unit", "duplicate_key", "cell_reference"])
def test_malformed_saved_grading_is_specific_contract_error(mutation):
    grading, occurrences = prepared(native.selected("hmmconvert", "ascii"))
    cell = grading["calculations"]["rows"][0]["decoded_model_count"]
    if mutation == "schema": grading["sheet"]["schema"] = "hmmer_emission_sheet_v1"
    elif mutation == "operation": grading["calculations"]["operation"]["mode"] = "binary"
    elif mutation == "occurrence": occurrences[0]["ordinal"] = 3
    elif mutation == "digest": occurrences[0]["sha256"] = "0" * 64
    elif mutation == "bool_value": cell["value"] = True
    elif mutation == "nonfinite": cell["value"] = float("nan")
    elif mutation == "wrong_unit": cell["unit"] = "annotation_confidence"
    elif mutation == "duplicate_key": grading["calculations"]["rows"].append(deepcopy(grading["calculations"]["rows"][0]))
    elif mutation == "cell_reference": cell["inputs"][0]["occurrence_id"] = next(o["occurrence_id"] for o in occurrences if o["role"] == "stderr")
    with pytest.raises(ContractError):
        project(grading, occurrences, selection(quantities=["decoded_model_count"]))


def test_component_states_preserve_measured_zero_and_partial_nonzero():
    # Deliberate saved-cell perturbations exercise copying, not recalculation.
    grading, occurrences = prepared(native.legacy_artifact("hmmpress_success"))
    bundle = next(r for r in grading["calculations"]["rows"] if r["kind"] == "bundle")
    for value, state in ((0, "present"), (3, "incomplete"), (-2, "failed"), (None, "missing"), (None, "incompatible"), (None, "nonfinite")):
        bundle["bundle_byte_sum"].update(value=value, state=state)
        result = project(grading, occurrences, selection(quantities=["bundle_byte_sum"], rows={"record_keys": ["pressed_bundle"]}))
        assert result["rows"][0]["quantities"] == [{"path": "bundle_byte_sum", "value": value, "state": state, "unit": "byte"}]
        assert result["rows"][0]["artifact_ref"] is None


def test_e1_distinct_projection_identity_and_check_meanings():
    grading, occurrences = prepared(native.selected("hmmemit", "consensus_simple"))
    model = grading["sheet"]["model_extraction"]["records"][0]["record_key"]
    result = project(grading, occurrences, selection(quantities=["captured_sample_count", "mismatch_count"],
        checks=["sample_population_count", "consensus_agreement"], rows={"record_keys": [model + "#model", model + "#consensus"]}))
    assert [r["kind"] for r in result["rows"]] == ["model", "consensus"]
    assert result["rows"][0]["checks"][1]["outcome"] == "unknown"
    assert result["rows"][1]["checks"][0]["outcome"] == "unknown"
    assert result["rows"][1]["checks"][1]["outcome"] == "pass"
    assert all(r["artifact_ref"] is None for r in result["rows"])


def test_h1_repeated_check_names_keep_all_native_instances_and_outcomes():
    grading, occurrences = prepared(native.dna_statistics())
    # Synthetic contradiction demonstrates that projection does not collapse checks.
    extra = deepcopy(grading["calculations"]["checks"][0])
    extra["state"] = "fail"
    grading["calculations"]["checks"].append(extra)
    result = project(grading, occurrences, selection(checks=["native_rounding_agreement"]))
    checks = result["rows"][0]["checks"]
    assert len(checks) == 5
    assert [c["outcome"] for c in checks] == ["pass"] * 4 + ["fail"]
    assert all(len(c["occurrences"]) == 2 for c in checks)


def test_f1_null_key_aggregate_check_partition():
    args = native.selected("hmmerfm-exactmatch", "locations")
    for item in args["inputs"].pop("fm_database"):
        del args["formats"][item["occurrence"]["occurrence_id"]]
    grading, occurrences = prepared(args)
    result = project(grading, occurrences, selection(checks=["decoded_layout", "native_query_population"],
        rows={"record_keys": ["aggregate/database_summary", "aggregate/exactmatch_summary"]}))
    assert len(result["rows"]) == 2 and all(r["artifact_ref"] is None for r in result["rows"])
    first, second = result["rows"]
    assert first["checks"][1] == {"name": "native_query_population", "outcome": "unknown", "occurrences": []}
    assert second["checks"][0] == {"name": "decoded_layout", "outcome": "unknown", "occurrences": []}
    check = next(c for c in grading["calculations"]["checks"] if c["record_key"] is None)
    check["scope"] = "undeclared aggregate scope"
    with pytest.raises(ContractError, match="null_key_check_scope_undeclared"):
        project(grading, occurrences, selection(checks=["decoded_layout"]))


def test_s1_explicit_check_calculation_identity_prevents_source_set_fallback():
    grading, occurrences = prepared(native.legacy_simulation())
    rows = grading["calculations"]["rows"]
    a, b = next((a, b) for a in rows for b in rows if a["record_key"] != b["record_key"] and
        a["source_record_keys"] and set(a["source_record_keys"]) == set(b["source_record_keys"]))
    grading["calculations"]["checks"] = [{"name": "native_filter_count", "state": "fail",
        "source_record_keys": deepcopy(a["source_record_keys"]), "details": {"calculation_record_key": a["record_key"]}}]
    result = project(grading, occurrences, selection(checks=["native_filter_count"], rows={"record_keys": [a["record_key"], b["record_key"]]}))
    assert [r["checks"][0]["outcome"] for r in result["rows"]] == ["fail", "unknown"]
    grading["calculations"]["checks"][0]["details"] = {}
    result = project(grading, occurrences, selection(checks=["native_filter_count"], rows={"record_keys": [a["record_key"], b["record_key"]]}))
    assert [r["checks"][0]["outcome"] for r in result["rows"]] == ["fail", "fail"]


@pytest.mark.parametrize("mutation", ["wrong_known_same_bytes_occurrence", "bad_locator", "unhashable_state", "abi_bool", "metadata_unrelated", "engine_version", "cyclic"])
def test_malformed_structure_is_contract_error(mutation):
    grading, occurrences = prepared(native.selected("hmmconvert", "ascii"))
    row = grading["sheet"]["native_rows"][0]
    if mutation == "wrong_known_same_bytes_occurrence":
        output = next(o for o in occurrences if o["role"] == "converted_models")
        stdout = next(o for o in occurrences if o["role"] == "stdout")
        row = next(r for r in grading["sheet"]["native_rows"] if r.get("occurrence_id") == output["occurrence_id"])
        row["occurrence_id"] = stdout["occurrence_id"]
    elif mutation == "bad_locator": grading["sheet"]["input_records"][0]["locator"] = []
    elif mutation == "unhashable_state": grading["calculations"]["rows"][0]["decoded_model_count"]["state"] = []
    elif mutation == "abi_bool": grading["native_abi"]["c_long_bytes"] = True
    elif mutation == "metadata_unrelated": grading["metadata"]["annotation_confidence"] = 1
    elif mutation == "engine_version": grading["operation"]["engine_version"] = "4.0"
    elif mutation == "cyclic": grading["cycle"] = grading
    with pytest.raises(ContractError):
        project(grading, occurrences, selection(quantities=["decoded_model_count"]))


def test_catalog_units_are_exact_per_kind_and_not_guessed_for_absence():
    grading, occurrences = prepared(native.selected("hmmerfm-exactmatch", "locations"))
    path = "components.valid_location_count"
    assert views.preparation_projection_catalog("hmmerfm-exactmatch", "locations")["calculations"]["quantities"][path]["unit"] == ["emitted_location_occurrences", "location_occurrences"]
    result = project(grading, occurrences, selection(quantities=[path, "components.expected_literal_location_count"]))
    for row in result["rows"]:
        first, second = row["quantities"]
        if row["kind"] == "query_validation": assert first["unit"] == "location_occurrences"
        elif row["kind"] == "exactmatch_summary": assert first["unit"] == "emitted_location_occurrences"
        else: assert first["unit"] is None
        if row["kind"] != "exactmatch_summary": assert second["unit"] is None


def test_known_model_reference_in_wrong_direction_is_rejected():
    grading, occurrences = prepared(native.selected("hmmconvert", "ascii"))
    pair = next(a for a in grading["sheet"]["associations"] if a["kind"] == "model_pair")
    row = next(r for r in grading["calculations"]["rows"] if r["kind"] == "model_comparison")
    # Both claims are perturbed together: known existence and agreement alone
    # cannot turn the saved output into the source operand.
    pair["source_record_keys"] = pair["output_record_keys"][:]
    row["source_record_key"] = pair["source_record_keys"][0]
    with pytest.raises(ContractError, match="association_source_direction_invalid"):
        project(grading, occurrences, selection(quantities=["source_length"]))


def test_f1_categorical_parameters_are_not_numeric_measurements():
    grading, occurrences = prepared(native.selected("makehmmerdb", "build"))
    result = project(grading, occurrences, selection("native_rows", quantities=["payload.value"]))
    native_rows = {r["record_key"]: r for r in grading["sheet"]["native_rows"]}
    for row in result["rows"]:
        original = native_rows[row["record_key"]]
        if original["kind"] == "index_parameters" and original["payload"]["parameter"] not in {"bin_length", "suffix array sample rate"}:
            assert row["quantities"][0] == {"path": "payload.value", "value": None, "state": "missing", "unit": None}


def test_projection_forbids_all_io_parsing_calculation_and_store(monkeypatch):
    sources = [prepared(args) for args in (native.selected("hmmconvert", "ascii"),
        native.selected("hmmbuild", "build_alignment"), native.selected("hmmemit", "consensus_simple"),
        native.legacy_simulation(), native.dna_statistics(), native.selected("makehmmerdb", "build"))]
    def forbidden(*args, **kwargs):
        raise AssertionError("projection attempted parsing/calculation/acquisition")
    with monkeypatch.context() as patch:
        for name, value in vars(Store).items():
            if callable(value): patch.setattr(Store, name, forbidden)
        for target, name in ((builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
            (Path, "read_bytes"), (Path, "read_text"), (socket, "socket"), (socket, "create_connection"), (subprocess, "run"), (subprocess, "Popen")):
            patch.setattr(target, name, forbidden)
        for module in (worker, worker.model_data, worker.artifact_data, worker.artifact_calculations,
            worker.alignment_data, worker.alignment_calculations, worker.emission_data, worker.emission_calculations,
            worker.simulation_data, worker.simulation_calculations, worker.statistics_data, worker.statistics_calculations,
            worker.fm_data, worker.fm_calculations):
            for name, value in vars(module).items():
                if callable(value) and name.startswith(("populate_", "parse_", "extract_", "calculate_", "recalculate_", "grade_", "iter_")):
                    patch.setattr(module, name, forbidden)
        for grading, occurrences in sources:
            entry = views.preparation_projection_catalog(**{k: grading["operation"][k] for k in ("program", "mode")})["calculations"]
            assert project(grading, occurrences, selection(quantities=list(entry["quantities"]), checks=entry["checks"]))["rows"]


def test_fact_schemas_and_catalogues_are_detached_and_closed():
    facts = views.preparation_fact_sources()
    assert set(facts) == {"execution_hmmer_preparation_" + k for k in ("rows", "artifacts", "population", "result_refs", "failures")}
    for source, descriptor in facts.items():
        validate_form({"facts": []}, {"type": "object", "additionalProperties": False,
            "properties": {"facts": descriptor["report_schema"]}, "required": ["facts"]}, lambda *_: True)
    facts["execution_hmmer_preparation_rows"]["report_schema"]["items"].clear()
    assert views.preparation_fact_sources()["execution_hmmer_preparation_rows"]["report_schema"]["items"]["type"] == "object"
    assert "preflight" in views.FAILURE_STAGES


def test_save_native_projection_examples_and_hashes(tmp_path):
    examples = {"H1": native.dna_statistics(), "S1": native.legacy_simulation(),
        "E1": native.selected("hmmemit", "consensus_simple"), "F1": native.selected("makehmmerdb", "build"),
        "A1": native.legacy_artifact("hmmpress_success"), "B1": native.selected("hmmbuild", "build_alignment")}
    report = {}
    for name, args in examples.items():
        grading, occurrences = prepared(args)
        entry = views.preparation_projection_catalog(**{k: grading["operation"][k] for k in ("program", "mode")})["calculations"]
        result = project(grading, occurrences, selection(quantities=list(entry["quantities"]), checks=entry["checks"]))
        path = tmp_path / (name + "_projection.json")
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        report[name] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "occurrences": occurrences}
    (tmp_path / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
