"""Pure selection over retained native examples; no new native execution.

The occurrence envelopes below are explicitly synthetic test bindings of the
retained descriptors. They preserve actual native digests/bytes/measurements;
root publication and return authentication own real Store/episode bindings.
"""
from copy import deepcopy
import builtins
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.communication import reference_resolver, validate_closed_schema, validate_form
from gene_annotation_episode import infernal_preparation_result_views as views
from gene_annotation_episode import infernal_preparation_models as models
from gene_annotation_episode import infernal_preparation_artifacts as artifacts
from gene_annotation_episode import infernal_preparation_statistics as statistics
from gene_annotation_episode import infernal_preparation_calculations as calculations
from gene_annotation_episode import infernal_preparation_emission as emission
from gene_annotation_episode import infernal_preparation_emission_calculations as emission_calculations
from gene_annotation_episode import native_infernal_preparation_worker as worker


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "verification"
A = VERIFY / "tool_graders_infernal_preparation_models_2026-10-26_248/examples"
B = VERIFY / "tool_graders_infernal_preparation_statistics_2026-10-26_249/examples003"
C = VERIFY / "tool_graders_infernal_preparation_emission_2026-10-26_250/examples"
R = VERIFY / "tool_graders_infernal_preparation_2026-10-26_247/pure_combined_002/temporary/pytest"
SOURCE_REF = "execution_result:preparation-test"


def retained_cases():
    result = [("A/" + p.parent.name, p, p.with_name("calculations.json")) for p in sorted(A.glob("*/sheet.json"))]
    result.extend(("B/" + p.stem, p, None) for p in sorted(B.glob("*.json")) if p.name not in {"INDEX.json", "receipt.json"})
    result.extend(("C/" + p.name.removesuffix(".sheet.json"), p, p.with_name(p.name.replace(".sheet.json", ".calculations.json")))
                  for p in sorted(C.glob("*.sheet.json")))
    result.extend(("root/" + p.stem, p, None) for p in sorted(R.glob("test_real_compiled_artifacts_p*/*.json")))
    return result


CASES = retained_cases()


def load_case(name):
    case = next(c for c in CASES if c[0] == name)
    data = json.loads(case[1].read_text())
    if case[2] is not None:
        data = {"sheet": data, "calculations": json.loads(case[2].read_text())}
    return {"version": worker.GRADING_SCHEMA, "operation": deepcopy(data["sheet"]["operation"]),
            "sheet": data["sheet"], "calculations": data["calculations"]}


def supplied(name):
    grading = load_case(name)
    # These are custody fixtures only, not a claim of live Store authentication.
    refs, occurrences, counters = {}, [], {}
    for artifact in grading["sheet"]["artifacts"]:
        direction = "input" if artifact["role"] in {"models", "alignment", "keys", "request"} else "output"
        role = artifact["role"]
        ordinal = counters.get((direction, role), 0)
        counters[(direction, role)] = ordinal + 1
        entry_index = sum(row["direction"] == direction for row in occurrences)
        pointer = "inputs" if direction == "input" else "artifacts"
        occurrence_ref = f"artifact:test-bundle#/{pointer}/{entry_index}"
        refs[artifact["artifact_ref"]] = occurrence_ref
        occurrences.append({**artifact, "occurrence_ref": occurrence_ref, "direction": direction,
            "ordinal": ordinal, "relative_path": f"retained/{role}/{ordinal}",
            "artifact_ref": "artifact:" + artifact["sha256"]})

    def remap(item, field=None):
        if type(item) is dict:
            return {key: remap(value, key) for key, value in item.items()}
        if type(item) is list:
            return [remap(value, field) for value in item]
        if type(item) is str and field is not None and (field.endswith(("_ref", "_refs", "_keys")) or field in {"record_key", "sequence_key", "alignment_key"}):
            for old, new in refs.items():
                if item == old:
                    return new
                if item.startswith(old + "#"):
                    return new + item[len(old):]
        return item

    bound = remap(grading)
    # Rebinding must not change native names/accessions or any measured number.
    for collection in ("input_records", "output_records", "native_rows"):
        for old, new in zip(grading["sheet"][collection], bound["sheet"][collection], strict=True):
            assert old.get("name") == new.get("name") and old.get("accession") == new.get("accession")
    return bound, occurrences


def selector(collection="calculations", quantities=(), checks=(), *, rows=None, selected_artifacts=(), projection=True):
    return {"version": "native_infernal_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"collection": collection, "rows": rows or {"offset": 0, "limit": 100000},
                       "quantities": list(quantities), "checks": list(checks)} if projection else None,
        "artifacts": list(selected_artifacts)}


def project(grading, occurrences, selected):
    return views.project_preparation_result(grading, selector=selected, source_ref=SOURCE_REF, occurrences=occurrences)


def cell_at(row, path):
    for name in path.split("."):
        if type(row) is not dict or name not in row:
            return None
        row = row[name]
    return row


def scalar_value_paths(row, prefix=""):
    """Independent schema-coverage audit; arrays deliberately stay retained."""
    if type(row) is not dict:
        return set()
    if set(row) == {"value", "state", "basis", "unit", "inputs", "native_token"}:
        return {prefix}
    result = set()
    for name, value in row.items():
        if type(value) is dict:
            result |= scalar_value_paths(value, prefix + "." + name if prefix else name)
    return result


@pytest.mark.parametrize("case", [c[0] for c in CASES])
def test_retained_native_sheets_select_all_declared_scalar_cells_without_recalculation(case):
    grading, occurrences = supplied(case)
    before = deepcopy((grading, occurrences))
    catalog = views.preparation_projection_catalog(grading["operation"]["program"], grading["operation"]["mode"])
    for collection, entry in catalog.items():
        originals = grading["calculations"]["rows"] if collection == "calculations" else grading["sheet"][collection]
        # Every actual scalar cell is catalogued from declarations, including
        # model fits absent from many of the finite native examples.
        for original in originals:
            assert scalar_value_paths(original) <= set(entry["quantities"])
        if not entry["quantities"] and not entry["checks"]:
            assert originals == []
            continue
        result = project(grading, occurrences, selector(collection, entry["quantities"], entry["checks"]))
        assert result["population"]["total_records"] == len(originals)
        assert result["population"]["returned_records"] == len(originals)
        assert result["population"]["omitted_records"] == 0
        for original, row in zip(originals, result["rows"], strict=True):
            validate_schema(row, views.ROW_SCHEMA)
            assert row["record_key"] == original["record_key"]
            assert [q["path"] for q in row["quantities"]] == list(entry["quantities"])
            for quantity in row["quantities"]:
                cell = cell_at(original, quantity["path"])
                if cell is None:
                    assert quantity["value"] is None and quantity["state"] == "missing"
                else:
                    assert {k: quantity[k] for k in ("value", "state", "basis", "unit")} == {
                        k: cell[k] for k in ("value", "state", "basis", "unit")}
            if collection == "calculations":
                actual = row["checks"][:len(original["checks"])]
                assert [(c["name"], c["outcome"]) for c in actual] == [(c["check"], c["outcome"]) for c in original["checks"]]
        assert "native_token" not in json.dumps(result) and "sequence_keys" not in json.dumps(result)
    assert (grading, occurrences) == before


def test_schema_catalogue_has_unsampled_model_fit_fields_and_no_array_expressions():
    catalog = views.preparation_projection_catalog("cmstat", "summary")
    quantities = catalog["input_records"]["quantities"]
    expected = {"fields." + key for key in models.FIELD_UNITS}
    expected |= {"filter_hmm.fields." + key for key in models.HMM_UNITS}
    expected |= {"topology." + key for key in models.TOPOLOGY_FIELDS}
    expected |= {f"calibration.{tag}.{field}" for tag in models.CALIBRATION_ALGORITHMS for field in statistics.VALUE_UNITS["calibration"]}
    expected |= {"efp7gf.location", "efp7gf.scale"}
    assert set(quantities) == expected
    assert quantities["calibration.ECMGI.lambda"]["unit"] == "inverse_bit"
    assert all(entry["meaning"] for entry in quantities.values())
    assert not any(path.startswith(("null_background", "filter_hmm.stats", "series")) for path in quantities)
    catalog["input_records"]["quantities"].clear()
    assert views.preparation_projection_catalog("cmstat", "summary")["input_records"]["quantities"]


def test_known_generated_denominators_and_measured_zero_remain_exact():
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    rows = [r for r in grading["sheet"]["output_records"] if r["kind"] == "generated_sequence"]
    selected = selector(quantities=["components.residue_count", "components.gc_count", "components.gc_denominator",
                                   "components.gc_fraction_canonical", "components.gap_count", "components.column_count", "components.gap_fraction"],
                        rows={"record_keys": [r["record_key"] for r in rows]})
    result = project(grading, occurrences, selected)
    numbers = [{q["path"].split(".")[-1]: q["value"] for q in r["quantities"]} for r in result["rows"]]
    assert numbers[0] == {"residue_count": 11, "gc_count": 8, "gc_denominator": 11, "gc_fraction_canonical": 8/11,
                          "gap_count": 1, "column_count": 12, "gap_fraction": 1/12}
    assert numbers[1]["gap_count"] == 0 and numbers[1]["gc_fraction_canonical"] == 2/3
    assert result["rows"][0]["name"] == rows[0]["name"]
    assert result["rows"][0]["checks"] == []
    result["rows"][0]["quantities"][0]["value"] = 99
    assert project(grading, occurrences, selected)["rows"][0]["quantities"][0]["value"] == 11


def test_native_signed_fit_values_are_not_clamped_or_relabelled():
    grading, occurrences = supplied("B/cmcalibrate_all_sidecars")
    row = next(r for r in grading["sheet"]["native_rows"] if r["kind"] == "calibration" and r["values"]["mu_orig"]["value"] < 0)
    result = project(grading, occurrences, selector("native_rows", ["values.mu_orig", "values.lambda"], rows={"record_keys": [row["record_key"]]}))
    assert result["rows"][0]["quantities"][0]["value"] == row["values"]["mu_orig"]["value"] < 0
    assert result["rows"][0]["quantities"][0]["unit"] == "bit"
    assert result["rows"][0]["name"] == row["identity"]["name"]


def test_original_value_units_override_static_missing_cell_catalogue():
    grading, occurrences = supplied("B/cmstat_T")
    result = project(grading, occurrences, selector(quantities=["components.native_conversion_residual", "components.native_rounding_half_width"]))
    originals = grading["calculations"]["rows"]
    for row, original in zip(result["rows"], originals, strict=True):
        for quantity in row["quantities"]:
            assert quantity["unit"] == original["components"][quantity["path"].split(".")[-1]]["unit"]
    assert any(q["unit"] == "expected_count" for row in result["rows"] for q in row["quantities"])


@pytest.mark.parametrize("state", ["missing", "not_measured", "failed", "truncated", "incompatible", "invalid"])
def test_explicit_unavailable_state_is_preserved_on_retained_native_row(state):
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    row = next(r for r in grading["sheet"]["output_records"] if r["kind"] == "generated_sequence")
    # Explicit synthetic unavailable-cell mutation of a full retained native sheet.
    row["values"]["gc_count"].update(value=None, state=state)
    result = project(grading, occurrences, selector("output_records", ["values.gc_count"], rows={"record_keys": [row["record_key"]]}))
    assert result["rows"][0]["quantities"] == [{"path": "values.gc_count", "value": None, "state": state, "basis": "derived", "unit": "nt"}]


def test_absent_and_inapplicable_fields_return_missing_with_catalogue_units():
    grading, occurrences = supplied("A/cmconvert_ascii")
    row = next(r for r in grading["sheet"]["output_records"] if r["kind"] == "artifact_operation")
    result = project(grading, occurrences, selector("output_records", ["fields.CLEN"], rows={"record_keys": [row["record_key"]]}))
    assert result["rows"][0]["quantities"] == [{"path": "fields.CLEN", "value": None, "state": "missing", "basis": "model_header", "unit": "nt"}]
    model = grading["sheet"]["input_records"][0]
    del model["fields"]["CLEN"]
    result = project(grading, occurrences, selector("input_records", ["fields.CLEN"]))
    assert result["rows"][0]["quantities"][0]["state"] == "missing"


def test_binary_retained_artifact_and_empty_bytes_keep_distinct_roles():
    grading, occurrences = supplied("A/cmconvert_binary")
    wanted = [{"direction": "output", "role": role, "ordinal": 0} for role in ("stdout", "stderr", "converted_models", "i1i")]
    result = project(grading, occurrences, selector(quantities=["components.output_model_count"], selected_artifacts=wanted))
    assert result["rows"][0]["quantities"][0]["value"] is None
    assert result["rows"][0]["artifact_ref"] is None  # aggregate, not stdout provenance
    assert [a["role"] for a in result["artifacts"]] == ["stdout", "stderr", "converted_models"]
    assert result["artifacts"][0]["artifact_ref"] == result["artifacts"][1]["artifact_ref"]
    assert result["artifacts"][0]["size_bytes"] == 0
    assert result["artifacts"][2]["size_bytes"] == 7166
    assert result["population"]["missing_artifacts"] == [wanted[-1]]
    assert result["population"]["requested_artifact_count"] == 4
    assert result["population"]["returned_artifact_count"] == 3
    assert all("relative_path" not in a and "occurrence_ref" not in a for a in result["artifacts"])


def test_repeated_companion_checks_preserve_each_original_artifact_association():
    grading, occurrences = supplied("A/cmpress_retained_219")
    result = project(grading, occurrences, selector(checks=["artifact_signature", "artifact_payload_identity"]))
    original = grading["calculations"]["rows"][0]
    selected = [c for c in original["checks"] if c["check"] in {"artifact_signature", "artifact_payload_identity"}]
    actual = result["rows"][0]["checks"]
    assert len(actual) == len(selected) > 4
    assert [(c["name"], c["outcome"]) for c in actual] == [(c["check"], c["outcome"]) for c in selected]
    assert {o["role"] for c in actual for o in c["occurrences"]} == {"i1m", "i1i", "i1f", "i1p"}
    assert all(c["occurrences"] for c in actual)
    assert result["rows"][0]["artifact_ref"] is None


def test_differing_repeated_outcomes_and_repeated_field_inputs_keep_occurrence_order():
    grading, occurrences = supplied("A/cmpress_retained_219")
    checks = [c for c in grading["calculations"]["rows"][0]["checks"] if c["check"] == "artifact_signature"]
    checks[1]["outcome"] = "fail"  # explicit synthetic validation-failure fixture
    checks[1]["inputs"] *= 2
    result = project(grading, occurrences, selector(checks=["artifact_signature"]))
    projected = result["rows"][0]["checks"]
    assert [c["outcome"] for c in projected] == [c["outcome"] for c in checks]
    assert projected[1]["outcome"] == "fail" and len(projected[1]["occurrences"]) == 1
    assert projected[1]["occurrences"][0]["role"] == next(o["role"] for o in occurrences
        if o["occurrence_ref"] == checks[1]["inputs"][0]["locator"]["artifact_ref"])


@pytest.mark.parametrize("completeness", ["partial", "unknown"])
def test_partial_or_unknown_capture_is_not_relabelled_complete(completeness):
    grading, occurrences = supplied("A/cmconvert_binary")
    artifact = next(a for a in grading["sheet"]["artifacts"] if a["role"] == "converted_models")
    occurrence = next(o for o in occurrences if o["occurrence_ref"] == artifact["artifact_ref"])
    # Synthetic capture-status mutation of actual retained binary descriptors.
    artifact["completeness"] = occurrence["completeness"] = completeness
    result = project(grading, occurrences, selector(projection=False,
        selected_artifacts=[{"direction": "output", "role": "converted_models", "ordinal": 0}]))
    assert result["artifacts"][0]["completeness"] == completeness
    assert result["artifacts"][0]["size_bytes"] == 7166
    assert result["population"]["collection"] is None and result["rows"] == []


def test_same_bytes_in_input_and_working_copy_are_independent_occurrences():
    grading, occurrences = supplied("A/cmconvert_binary")
    model = next(o for o in occurrences if o["role"] == "models")
    working = {**model, "occurrence_ref": "artifact:test-bundle#/working_copies/0",
               "direction": "working_copy", "relative_path": "work/models.cm"}
    occurrences.append(working)
    selected = selector(projection=False, selected_artifacts=[
        {"direction": "working_copy", "role": "models", "ordinal": 0},
        {"direction": "input", "role": "models", "ordinal": 0}])
    result = project(grading, occurrences, selected)
    assert [a["direction"] for a in result["artifacts"]] == ["working_copy", "input"]
    assert result["artifacts"][0]["artifact_ref"] == result["artifacts"][1]["artifact_ref"]
    assert result["population"]["returned_artifact_count"] == 2


def test_orphan_calculation_cannot_inherit_a_nearby_name_or_artifact():
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    # A calculation without an original exact key is permitted only as an
    # unattributed aggregate; native names from neighboring rows never fill it.
    grading["calculations"]["rows"][0]["record_key"] = "unattributed-aggregate"
    result = project(grading, occurrences, selector(quantities=["components.actual_sequence_count"],
        rows={"record_keys": ["unattributed-aggregate"]}))
    row = result["rows"][0]
    assert row["name"] is None and row["accession"] is None and row["artifact_ref"] is None


def test_checks_keep_not_applicable_and_absent_check_is_unknown():
    grading, occurrences = supplied("C/new_aligned_afa")
    alignment = next(r for r in grading["sheet"]["output_records"] if r["kind"] == "generated_alignment")
    result = project(grading, occurrences, selector(checks=["cmemit_annotation_geometry", "cmemit_trace_decoded"], rows={"record_keys": [alignment["record_key"]]}))
    assert result["rows"][0]["checks"] == [
        {"name": "cmemit_annotation_geometry", "outcome": "not_applicable", "occurrences": []},
        {"name": "cmemit_trace_decoded", "outcome": "unknown", "occurrences": []}]


def test_exact_keys_preserve_requested_order_and_report_missing_records():
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    rows = grading["sheet"]["output_records"]
    keys = [rows[-1]["record_key"], "missing-native-key", rows[0]["record_key"]]
    result = project(grading, occurrences, selector("output_records", ["values.column_count"], rows={"record_keys": keys}))
    assert [r["record_key"] for r in result["rows"]] == [keys[0], keys[2]]
    assert result["population"]["missing_record_keys"] == ["missing-native-key"]
    assert result["population"]["omitted_records"] == len(rows) - 2
    out_of_range = project(grading, occurrences, selector("output_records", ["values.column_count"], rows={"offset": 999, "limit": 2}))
    assert out_of_range["rows"] == [] and out_of_range["population"]["omitted_records"] == len(rows)


def test_artifact_only_population_has_no_numerical_row_claim():
    grading, occurrences = supplied("A/cmconvert_binary")
    selected = selector(projection=False, selected_artifacts=[{"direction": "output", "role": "converted_models", "ordinal": 0}])
    result = project(grading, occurrences, selected)
    assert result["rows"] == []
    assert result["population"] == {"source_ref": SOURCE_REF, "collection": None, "total_records": 0, "returned_records": 0, "omitted_records": 0,
        "missing_record_keys": [], "requested_artifact_count": 1, "returned_artifact_count": 1, "missing_artifacts": []}
    validate_schema(result["population"], views.POPULATION_SCHEMA)
    validate_schema(result["artifacts"][0], views.ARTIFACT_SCHEMA)


def test_equal_populations_retain_distinct_original_result_sources():
    grading, occurrences = supplied("A/cmconvert_binary")
    selected = selector(projection=False, selected_artifacts=[{"direction": "output", "role": "converted_models", "ordinal": 0}])
    first = views.project_preparation_result(grading, selector=selected,
        source_ref="execution_result:first", occurrences=occurrences)["population"]
    second = views.project_preparation_result(grading, selector=selected,
        source_ref="execution_result:second", occurrences=occurrences)["population"]
    assert first["source_ref"] == "execution_result:first" and second["source_ref"] == "execution_result:second"
    assert {k: v for k, v in first.items() if k != "source_ref"} == {k: v for k, v in second.items() if k != "source_ref"}
    assert first != second
    validate_schema(first, views.POPULATION_SCHEMA)
    assert views.POPULATION_SCHEMA["properties"]["source_ref"]["x-reference-namespace"] == "execution_result"


def test_same_retained_bytes_keep_each_original_result_artifact_association():
    grading, occurrences = supplied("A/cmconvert_binary")
    selected = selector(projection=False, selected_artifacts=[{"direction": "output", "role": "converted_models", "ordinal": 0}])
    first = views.project_preparation_result(grading, selector=selected,
        source_ref="execution_result:first", occurrences=occurrences)["artifacts"][0]
    second = views.project_preparation_result(grading, selector=selected,
        source_ref="execution_result:second", occurrences=occurrences)["artifacts"][0]
    assert first["source_ref"] == "execution_result:first" and second["source_ref"] == "execution_result:second"
    assert first["artifact_ref"] == second["artifact_ref"]
    assert {k: v for k, v in first.items() if k != "source_ref"} == {k: v for k, v in second.items() if k != "source_ref"}
    assert first != second and all("source_ref" not in o for o in occurrences)
    validate_schema(first, views.ARTIFACT_SCHEMA)
    assert views.ARTIFACT_SCHEMA["properties"]["source_ref"]["x-reference-namespace"] == "execution_result"


@pytest.mark.parametrize("program,mode,selected", [
    ("cmsearch", "search", selector(quantities=["components.residue_count"])),
    ("cmemit", "build", selector(quantities=["components.residue_count"])),
    ("cmemit", "consensus", selector(quantities=["components.output_model_count"])),
    ("cmemit", "consensus", selector("input_records", ["values.gc_count"])),
    ("cmconvert", "binary", selector("output_records", ["fields.CLEN"])),
    ("cmbuild", "build", selector("native_rows", ["values.bit_score_sum"])),
    ("cmstat", "summary", selector("input_records", [], ["model_reference_valid"])),
    ("cmstat", "summary", selector("input_records", ["filter_hmm.stats.0.location"])),
    ("cmstat", "summary", selector("input_records", ["fields.CLEN+fields.W"])),
    ("cmemit", "consensus", selector(quantities=["components.gc_count", "components.gc_count"])),
    ("cmemit", "consensus", selector()),
    ("cmemit", "consensus", selector(projection=False)),
    ("cmemit", "consensus", selector(quantities=["components.gc_count"], rows={"offset": True, "limit": 1})),
    ("cmemit", "consensus", selector(quantities=["components.gc_count"], rows={"offset": 0.0, "limit": 1})),
    ("cmemit", "consensus", selector(quantities=["components.gc_count"], rows={"record_keys": ["same", "same"]})),
])
def test_wrong_program_mode_collection_field_and_expression_rejected(program, mode, selected):
    with pytest.raises(ValueError):
        views.validate_preparation_result_selector(selected, program=program, mode=mode)


def test_selector_copy_and_closed_fields():
    selected = selector(quantities=["components.gc_count"])
    copy = views.validate_preparation_result_selector(selected, program="cmemit", mode="consensus")
    copy["projection"]["quantities"].append("components.residue_count")
    assert selected["projection"]["quantities"] == ["components.gc_count"]
    selected["instructions"] = "arbitrary prose"
    with pytest.raises(ValueError):
        views.validate_preparation_result_selector(selected, program="cmemit", mode="consensus")


@pytest.mark.parametrize("mutation", ["digest", "size", "format", "duplicate_occurrence", "duplicate_selection", "row_key", "unknown_check_source", "nonfinite", "bool_value", "operation"])
def test_bad_associations_or_values_are_rejected(mutation):
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    if mutation in {"digest", "size", "format"}:
        field = {"digest": "sha256", "size": "size_bytes", "format": "format"}[mutation]
        occurrences[0][field] = {"digest": "0" * 64, "size": 0, "format": "text"}[mutation]
    elif mutation == "duplicate_occurrence":
        occurrences[1]["occurrence_ref"] = occurrences[0]["occurrence_ref"]
    elif mutation == "duplicate_selection":
        occurrences.append({**occurrences[0], "occurrence_ref": "different-reference"})
    elif mutation == "row_key":
        grading["sheet"]["output_records"][1]["record_key"] = grading["sheet"]["output_records"][0]["record_key"]
    elif mutation == "unknown_check_source":
        check = next(c for r in grading["calculations"]["rows"] for c in r["checks"] if c["inputs"])
        check["inputs"][0]["locator"]["artifact_ref"] = "unknown-occurrence"
    elif mutation in {"nonfinite", "bool_value"}:
        grading["sheet"]["input_records"][0]["fields"]["CLEN"]["value"] = float("nan") if mutation == "nonfinite" else True
    else:
        grading["calculations"]["operation"]["mode"] = "consensus"
    with pytest.raises(ValueError):
        project(grading, occurrences, selector(quantities=["components.gc_count"]))


def test_saved_replay_forbids_parsers_calculators_network_native_and_file_access(monkeypatch):
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    selected = selector(quantities=["components.gc_fraction_canonical", "components.gc_denominator"], checks=["cmemit_counts_consistent"])
    expected = project(grading, occurrences, selected)
    grading = json.loads(json.dumps(grading, allow_nan=False))

    def forbidden(*args, **kwargs):
        pytest.fail("projection attempted acquisition, parsing, calculation or native execution")

    for module, names in (
        (models, ["extract_infernal_models"]),
        (artifacts, ["populate_infernal_artifact_sheet", "validate_infernal_artifact_sheet", "parse_infernal_artifact_operation"]),
        (statistics, ["populate_infernal_statistics_sheet", "parse_cmbuild_summary", "parse_cmcalibrate_output", "parse_cmcalibrate_sidecar", "parse_cmstat_output"]),
        (calculations, ["calculate_infernal_statistics"]),
        (emission, ["populate_cmemit_sheet"]),
        (emission_calculations, ["calculate_cmemit_components"]),
        (worker, ["grade_infernal_preparation", "recalculate_infernal_preparation"]),
        (builtins, ["open"]), (io, ["open"]), (socket, ["socket", "create_connection"]),
        (subprocess, ["run", "Popen"]),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert project(grading, occurrences, selected) == expected


def test_fact_source_arrays_are_closed_and_independent():
    sources = views.preparation_fact_sources()
    assert set(sources) == {"execution_infernal_preparation_" + suffix for suffix in ("rows", "artifacts", "population", "result_refs", "failures")}
    assert all(d["type"] == d["report_schema"]["type"] == "array" for d in sources.values())
    assert sources["execution_infernal_preparation_rows"]["report_schema"]["items"] == views.ROW_SCHEMA
    assert sources["execution_infernal_preparation_result_refs"]["report_schema"]["items"]["x-reference-namespace"] == "execution_result"
    assert views.ROW_SCHEMA["properties"]["artifact_ref"]["x-reference-namespace"] == "artifact"
    sources["execution_infernal_preparation_rows"]["report_schema"]["items"].clear()
    assert views.FACT_SOURCES["execution_infernal_preparation_rows"]["report_schema"]["items"] == views.ROW_SCHEMA
    assert len(CASES) >= 90


def test_actual_projection_passes_existing_closed_typed_communication_boundary():
    grading, occurrences = supplied("C/prior_cmemit_stockholm")
    selected = selector(quantities=["components.gc_count", "components.gc_denominator"],
        checks=["cmemit_counts_consistent"], selected_artifacts=[{"direction": "output", "role": "generated_alignment", "ordinal": 0}])
    result = project(grading, occurrences, selected)
    sources = views.preparation_fact_sources()
    properties = {suffix: sources["execution_infernal_preparation_" + suffix]["report_schema"]
                  for suffix in ("rows", "artifacts", "population", "result_refs")}
    schema = {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}
    validate_closed_schema(schema)
    payload = {"rows": result["rows"], "artifacts": result["artifacts"],
               "population": [result["population"]], "result_refs": [SOURCE_REF]}
    registry = {
        "execution_result": [SOURCE_REF],
        "artifact": [o["artifact_ref"] for o in occurrences],
        "native_infernal_preparation_row": [r["record_key"] for r in result["rows"]],
        "native_infernal_preparation_name": [r["name"] for r in result["rows"] if r["name"] is not None],
        "native_infernal_preparation_accession": [r["accession"] for r in result["rows"] if r["accession"] is not None],
        "native_infernal_preparation_sha256": [a["sha256"] for a in result["artifacts"]],
    }
    assert validate_form(payload, schema, reference_resolver(registry)) == payload
    payload["artifacts"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_form(payload, schema, reference_resolver(registry))


def test_strict_occurrence_digest_shape_survives_report_schema_adaptation():
    grading, occurrences = supplied("A/cmconvert_binary")
    occurrences[0]["sha256"] = "not-a-digest"
    with pytest.raises(ValueError):
        project(grading, occurrences, selector(quantities=["components.output_model_count"]))
