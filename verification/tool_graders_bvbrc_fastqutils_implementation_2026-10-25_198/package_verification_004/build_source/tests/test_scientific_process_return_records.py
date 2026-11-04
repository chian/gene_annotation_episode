"""Pure compatibility/projection tests; fixtures are not historical runs.

No Workflow, Store, provider, execution binding or service is constructed here.
The literal old schema is independent of the current report-source generator.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

from gene_annotation_episode.communication import (ReportBoundaryError,
    reference_resolver, validate_closed_schema, validate_form)
from gene_annotation_episode.domain import identity, obj
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import (scientific_invocation_ref,
    validate_selection)
from gene_annotation_episode.scientific_process_reports import (RETURN_VERSION,
    SELECTION_REPORT_VERSION, VERSION, build_process_result, merge_process_results,
    project_process_result, report_sources, validate_process_result)
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary


FIXTURES = Path(__file__).parent / "fixtures/scientific_process_returns"
LEGACY_SCHEMA_SHA256 = "6db9bce2b5a6526b4f3000166eed409fe3675e72cdcd266e392ec7a261fcd308"
PATH = (("annotation", "root"), ("scientific_process", "child"))
METADATA = {"credit_kind": "scientific", "credit_binding": {
    "version": "synthetic_binding_v1", "units": "synthetic_original_units"}}
SIGNED_YIELD = {"completed_actions": 2, "expected_next_gain": {
    "value": -0.25, "lower": -0.5, "upper": 0.125, "status_code": 0,
    "uncertainty_code": 2, "alpha": 0.05}, "continuation_cost": 0.125,
    "stop_requested": True}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _process_library(directory, *, legacy):
    entries = json.loads((FIXTURES / "literal-process-options.json").read_bytes())
    if not legacy:
        entries[0]["slot"] = "evidence_axis"
    source = directory / "source"
    for entry in entries:
        _write(source / "entries" / (entry["id"] + ".json"), entry)
    _write(source / "index.json", {"format": "research_three_slot_options_v1",
        "status": "Synthetic return compatibility fixture",
        "slots": [{"slot": slot, "catalog": slot + ".json",
                   "count": sum(entry["slot"] == slot for entry in entries)}
                  for slot in (entries[0]["slot"], "thought_pattern")],
        "entries": [{**{key: entry[key] for key in ("id", "slot", "name", "description")},
                     "detail_path": "entries/" + entry["id"] + ".json", "source_evidence_ids": []}
                    for entry in entries]})
    _write(source / "option_sources.json", {"meaning": "No scientific source claims", "rows": []})
    return ScientificProcessLibrary.freeze(directory / "frozen-processes", source=source)


def _contract(name, resource):
    return {"name": name, "description": "Inspect the supplied synthetic fixture on " + resource + ".",
        "resources": resource, "instructions": "Read the explicitly supplied fixture operand on " + resource + ".",
        "input_schema": obj({})}


def _libraries(tmp_path, monkeypatch, *, legacy=False, empty=False):
    # Freeze only these explicit synthetic tool contracts. A global execution
    # catalog is not needed to exercise the actual immutable library reader.
    from gene_annotation_episode import tool_information
    monkeypatch.setattr(tool_information, "workflow_execution_catalogs", lambda: {})
    library = _process_library(tmp_path, legacy=legacy)
    tools = ScientificToolLibrary.freeze(tmp_path / "frozen-tools",
        catalog=[] if empty else [_contract("fixture.inspect", "local"), _contract("fixture.remote", "api")],
        tool_info=not legacy,
        resource_catalogs=None if legacy or empty else {"hpc": [
            _contract("fixture.inspect", "hpc"), _contract("fixture.batch", "hpc")]})
    return library, tools


@pytest.fixture
def current(tmp_path, monkeypatch):
    return _libraries(tmp_path, monkeypatch)


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    return _libraries(tmp_path, monkeypatch, legacy=True)


def _full_row(library, tools, *, legacy=False, empty=False):
    if legacy:
        selection = {"version": "scientific_process_selection_v2",
            "annotation_ref": library.reference("A01"), "thought_ref": library.reference("P01"),
            "tools": [] if empty else ["fixture.inspect"]}
    else:
        choices = [] if empty else [{"name": "fixture.inspect", "resources": "hpc"},
            {"name": "fixture.remote", "resources": "api"}, {"name": "fixture.inspect", "resources": "local"}]
        selection = {"version": "scientific_process_selection_v3",
            "evidence_axis": library.reference("A01"), "thought_pattern": library.reference("P01"),
            "child_tool_info": tools.resolve_tool_info(choices)}
    return {"version": "scientific_process_result_v1",
        "invocation_ref": scientific_invocation_ref("synthetic-run", PATH),
        "parent_invocation_ref": scientific_invocation_ref("synthetic-run", PATH[:-1]),
        "origin_kind": "ordinary_child", "preparation_operation_ref": None, "selection": selection,
        "initial_credit": 15.25, "credit": 14.5, "credit_kind": "scientific",
        "credit_binding_ref": identity("scientific_credit_binding", METADATA),
        "completed_actions": 2, "episode_yield": deepcopy(SIGNED_YIELD)}


def _resolver(library, row):
    return reference_resolver({
        "scientific_process_library": {library.as_record()["library_id"]},
        "scientific_option_digest": {header["option_ref"]["entry_sha256"] for header in library.headers()},
        "scientific_invocation": {row["invocation_ref"], row["parent_invocation_ref"]},
        "scientific_preparation": {row["preparation_operation_ref"]},
        "scientific_credit_binding": {row["credit_binding_ref"]},
    })


def _schema(library, tools):
    return obj({"arbitrary_parent_field": report_sources(library, tools)["scientific_process_results"]["report_schema"]})


def _frozen(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _snapshot_bytes(*libraries):
    return {str(path): path.read_bytes() for library in libraries
            for path in library.directory.rglob("*.json")}


def test_literal_old_schema_and_legacy_record_are_independent_and_unchanged(legacy, monkeypatch):
    library, tools = legacy
    path = FIXTURES / "literal-legacy-form-schema.json"
    raw_schema = path.read_bytes()
    assert hashlib.sha256(raw_schema).hexdigest() == LEGACY_SCHEMA_SHA256
    schema = json.loads(raw_schema)
    row = _full_row(library, tools, legacy=True)
    original = json.dumps(row, separators=(",", ":"))
    before = _snapshot_bytes(library, tools)

    def unexpected_generator(*args, **kwargs):
        raise AssertionError("Literal replay must not generate a new schema")
    monkeypatch.setattr("gene_annotation_episode.scientific_process_reports.report_sources", unexpected_generator)
    assert validate_closed_schema(schema) == schema
    assert validate_form({"chosen_name": [row]}, schema, _resolver(library, row)) == {"chosen_name": [row]}
    assert validate_process_result(row, library=library, tool_library=tools) == row
    assert row["selection"]["annotation_ref"]["slot"] == "annotation_distinction"
    assert row["selection"]["version"] == "scientific_process_selection_v2"
    assert json.dumps(row, separators=(",", ":")) == original
    assert path.read_bytes() == raw_schema
    assert _snapshot_bytes(library, tools) == before


@pytest.mark.parametrize("binding", ["none", "process", "tool", "both"])
def test_full_current_row_resolves_actual_fields_without_legacy_keyerror(current, binding):
    library, tools = current
    row = _full_row(library, tools)
    kwargs = {}
    if binding in ("process", "both"):
        kwargs["library"] = library
    if binding in ("tool", "both"):
        kwargs["tool_library"] = tools
    assert validate_process_result(_frozen(row), **kwargs) == row
    assert validate_selection(row["selection"]) == row["selection"]
    assert {entry["resources"] for entry in row["selection"]["child_tool_info"]} == {"api", "local", "hpc"}


def test_current_projection_is_closed_detached_and_copies_every_other_field(current):
    library, tools = current
    row = _full_row(library, tools)
    raw = json.dumps(row)
    before = _snapshot_bytes(library, tools)
    result = project_process_result(_frozen(row), library=library, tool_library=tools)
    assert result == {**row, "version": "scientific_process_result_v2", "selection": {
        "version": "scientific_process_selection_report_v1", "source_version": "scientific_process_selection_v3",
        "evidence_axis": row["selection"]["evidence_axis"], "thought_pattern": row["selection"]["thought_pattern"],
        "child_tool_info": [{"name": "fixture.inspect", "resources": "hpc"},
            {"name": "fixture.remote", "resources": "api"}, {"name": "fixture.inspect", "resources": "local"}]}}
    assert VERSION == "scientific_process_result_v1"
    assert RETURN_VERSION == result["version"] and SELECTION_REPORT_VERSION == result["selection"]["version"]
    assert all(result[key] == row[key] for key in row if key not in {"version", "selection"})
    assert not {"description", "instructions", "input_schema"} & set(json.dumps(result).split('"'))
    schema = _schema(library, tools)
    assert validate_closed_schema(schema) == schema
    assert validate_form({"arbitrary_parent_field": [result]}, schema, _resolver(library, result)) == {
        "arbitrary_parent_field": [result]}
    assert validate_process_result(_frozen(result), library=library, tool_library=tools) == result
    repeated = project_process_result(_frozen(result), library=library, tool_library=tools)
    assert repeated == result
    repeated["selection"]["child_tool_info"].clear()
    repeated["episode_yield"]["expected_next_gain"]["value"] = 100
    assert result["episode_yield"]["expected_next_gain"]["value"] == -0.25
    assert len(result["selection"]["child_tool_info"]) == 3
    assert json.dumps(row) == raw and _snapshot_bytes(library, tools) == before
    with pytest.raises(ValueError, match="scientific_process_selection_invalid"):
        validate_selection(result["selection"])


def test_legacy_projection_preserves_exact_refs_and_unknown_resources(legacy):
    library, tools = legacy
    row = _full_row(library, tools, legacy=True)
    original = json.dumps(row)
    result = project_process_result(row, library=library, tool_library=tools)
    assert result["selection"] == {"version": SELECTION_REPORT_VERSION,
        "source_version": "scientific_process_selection_v2", "evidence_axis": row["selection"]["annotation_ref"],
        "thought_pattern": row["selection"]["thought_ref"],
        "child_tool_info": [{"name": "fixture.inspect", "resources": None}]}
    assert result["selection"]["evidence_axis"]["slot"] == "annotation_distinction"
    assert tools.resolve(["fixture.inspect"])[0]["resources"] == "local"
    validate_form({"arbitrary_parent_field": [result]}, _schema(library, tools), _resolver(library, result))
    assert validate_process_result(result, library=library, tool_library=tools) == result
    assert json.dumps(row) == original


@pytest.mark.parametrize("legacy_mode", [False, True])
def test_genuinely_empty_tool_library_and_selection_have_closed_empty_arrays(tmp_path, monkeypatch, legacy_mode):
    library, tools = _libraries(tmp_path, monkeypatch, legacy=legacy_mode, empty=True)
    row = _full_row(library, tools, legacy=legacy_mode, empty=True)
    result = project_process_result(row, library=library, tool_library=tools)
    schema = _schema(library, tools)
    choices = schema["properties"]["arbitrary_parent_field"]["items"]["properties"]["selection"]["properties"]["child_tool_info"]
    assert choices == {"type": "array", "maxItems": 0, "items": {"type": "null"}}
    assert '"enum": []' not in json.dumps(schema)
    validate_form({"arbitrary_parent_field": [result]}, schema, _resolver(library, result))


def test_current_tool_names_include_resource_only_profiles(current):
    library, tools = current
    # A variant in the resource map need not occur in the ordinary callable map.
    assert "fixture.batch" not in {entry["name"] for entry in tools.catalog()}
    row = _full_row(library, tools)
    row["selection"]["child_tool_info"] = tools.resolve_tool_info([{"name": "fixture.batch", "resources": "hpc"}])
    result = project_process_result(row, library=library, tool_library=tools)
    validate_form({"arbitrary_parent_field": [result]}, _schema(library, tools), _resolver(library, result))


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("change", ["foreign_library", "other_option_digest", "wrong_slot", "wrong_resource", "duplicate_pair"])
def test_bound_validation_rejects_wrong_refs_and_name_resource_pairs(current, compact, change):
    library, tools = current
    row = _full_row(library, tools)
    if compact:
        row = project_process_result(row, library=library, tool_library=tools)
    selection = row["selection"]
    if change == "foreign_library":
        for field in ("evidence_axis", "thought_pattern"):
            selection[field]["library_id"] = "f" * 64
    elif change == "other_option_digest":
        selection["thought_pattern"]["entry_sha256"] = library.reference("P99")["entry_sha256"]
    elif change == "wrong_slot":
        selection["evidence_axis"]["slot"] = "annotation_distinction"
    elif change == "wrong_resource":
        selection["child_tool_info"][1]["resources"] = "local"
    else:
        selection["child_tool_info"].append(deepcopy(selection["child_tool_info"][0]))
    with pytest.raises(ValueError) as error:
        validate_process_result(row, library=library, tool_library=tools)
    assert type(error.value) is ValueError
    if change in {"foreign_library", "other_option_digest", "wrong_slot"}:
        assert str(error.value) == "scientific_process_option_reference_mismatch"
    if change == "wrong_resource":
        assert str(error.value) == "scientific_tool_unknown:fixture.remote:local"


def test_schema_membership_does_not_authenticate_option_digest_or_resource_pair(current):
    library, tools = current
    row = project_process_result(_full_row(library, tools), library=library, tool_library=tools)
    schema = _schema(library, tools)
    for change in ("digest", "resource"):
        altered = deepcopy(row)
        if change == "digest":
            altered["selection"]["thought_pattern"]["entry_sha256"] = library.reference("P99")["entry_sha256"]
        else:
            altered["selection"]["child_tool_info"][1]["resources"] = "local"
        validate_form({"arbitrary_parent_field": [altered]}, schema, _resolver(library, altered))
        with pytest.raises(ValueError):
            validate_process_result(altered, library=library, tool_library=tools)


@pytest.mark.parametrize("field", ["description", "instructions"])
def test_full_current_tool_body_must_equal_its_frozen_information(current, field):
    library, tools = current
    row = _full_row(library, tools)
    row["selection"]["child_tool_info"][0][field] = "Forged information."
    with pytest.raises(ValueError, match="scientific_tool_info_changed:fixture.inspect"):
        project_process_result(row, library=library, tool_library=tools)


@pytest.mark.parametrize("legacy_mode,resource", [(True, "local"), (False, None)])
def test_source_version_qualifies_null_or_recorded_resources(current, legacy_mode, resource):
    library, tools = current
    row = project_process_result(_full_row(library, tools), library=library, tool_library=tools)
    row["selection"]["source_version"] = "scientific_process_selection_v2" if legacy_mode else "scientific_process_selection_v3"
    row["selection"]["child_tool_info"] = [{"name": "fixture.inspect", "resources": resource}]
    with pytest.raises(ValueError, match="scientific_process_selection_report_invalid"):
        validate_process_result(row, library=library, tool_library=tools)


@pytest.mark.parametrize("field", ["description", "instructions", "input_schema"])
def test_closed_return_and_parser_reject_reintroduced_tool_prose(current, field):
    library, tools = current
    row = project_process_result(_full_row(library, tools), library=library, tool_library=tools)
    row["selection"]["child_tool_info"][0][field] = "Unrestricted prose must remain in host construction."
    with pytest.raises(ValueError, match="scientific_process_selection_report_invalid"):
        validate_process_result(row)
    schema = _schema(library, tools)
    with pytest.raises(ReportBoundaryError):
        validate_form({"arbitrary_parent_field": [row]}, schema, _resolver(library, row))
    choice = schema["properties"]["arbitrary_parent_field"]["items"]["properties"]["selection"]["properties"]["child_tool_info"]["items"]
    choice["properties"][field] = {"type": "string"}
    choice["required"].append(field)
    with pytest.raises(ReportBoundaryError) as error:
        validate_closed_schema(schema)
    assert error.value.diagnostic["code"] == "unrestricted_string"


@pytest.mark.parametrize("change", ["row_version", "selection_version", "source_version", "hybrid_full", "hybrid_compact",
    "extra_top", "extra_selection", "extra_reference", "choices_mapping", "choice_mapping", "name_prose"])
def test_bad_versions_hybrids_and_open_shapes_return_valueerror(current, change):
    library, tools = current
    row = _full_row(library, tools)
    if change != "hybrid_full":
        row = project_process_result(row, library=library, tool_library=tools)
    selection = row["selection"]
    if change == "row_version":
        row["version"] = "scientific_process_result_v999"
    elif change == "selection_version":
        selection["version"] = "scientific_process_selection_v3"
    elif change == "source_version":
        selection["source_version"] = "scientific_process_selection_v999"
    elif change in {"hybrid_full", "hybrid_compact"}:
        selection["annotation_ref"] = selection.pop("evidence_axis")
    elif change == "extra_top":
        row["description"] = "Unrequested finding"
    elif change == "extra_selection":
        selection["instructions"] = "Private construction instructions"
    elif change == "extra_reference":
        selection["evidence_axis"]["description"] = "Unrequested description"
    elif change == "choices_mapping":
        selection["child_tool_info"] = {}
    elif change == "choice_mapping":
        selection["child_tool_info"] = [None]
    else:
        selection["child_tool_info"][0]["name"] = "arbitrary prose name"
    with pytest.raises(ValueError) as error:
        validate_process_result(row, library=library, tool_library=tools)
    assert type(error.value) is ValueError
    if change == "row_version":
        assert str(error.value) == "scientific_process_result_version_invalid"


@pytest.mark.parametrize("yield_value", [None, SIGNED_YIELD,
    {**SIGNED_YIELD, "expected_next_gain": {"value": -1, "lower": -1, "upper": -1,
        "status_code": -1, "uncertainty_code": -1, "alpha": -1}},
    {**SIGNED_YIELD, "expected_next_gain": {"value": -2, "lower": -2, "upper": -2,
        "status_code": -2, "uncertainty_code": -1, "alpha": -1}},
    {**SIGNED_YIELD, "expected_next_gain": {"value": -0.25, "lower": -0.25, "upper": -0.25,
        "status_code": 0, "uncertainty_code": 0, "alpha": 0}}])
@pytest.mark.parametrize("binding_known", [False, True])
def test_projection_preserves_exact_existing_numerical_and_unknown_values(current, yield_value, binding_known):
    library, tools = current
    row = _full_row(library, tools)
    row["episode_yield"] = deepcopy(yield_value)
    if not binding_known:
        row.update(credit_kind=None, credit_binding_ref=None)
    result = project_process_result(row, library=library, tool_library=tools)
    assert {key: item for key, item in result.items() if key not in {"version", "selection"}} == {
        key: item for key, item in row.items() if key not in {"version", "selection"}}
    assert result["initial_credit"] == 15.25 and result["credit"] == 14.5
    assert result["episode_yield"] == yield_value


NUMERIC_PATHS = [("initial_credit",), ("credit",), ("completed_actions",),
    ("episode_yield", "completed_actions"), ("episode_yield", "continuation_cost"),
    *[("episode_yield", "expected_next_gain", field)
      for field in ("value", "lower", "upper", "status_code", "uncertainty_code", "alpha")]]


@pytest.mark.parametrize("path", NUMERIC_PATHS)
@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf"), float("-inf")])
def test_finite_numbers_and_boolean_numeric_errors_are_rejected(current, path, invalid):
    library, tools = current
    row = project_process_result(_full_row(library, tools), library=library, tool_library=tools)
    target = row
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = invalid
    with pytest.raises(ValueError):
        validate_process_result(row)


@pytest.mark.parametrize("change", ["own_count", "yield_count", "binding_kind", "binding_ref", "parent", "origin", "stop"])
def test_compact_result_keeps_existing_cross_field_relationships(current, change):
    library, tools = current
    row = project_process_result(_full_row(library, tools), library=library, tool_library=tools)
    if change == "own_count":
        row["completed_actions"] = -1
    elif change == "yield_count":
        row["episode_yield"]["completed_actions"] = 3
    elif change == "binding_kind":
        row["credit_kind"] = None
    elif change == "binding_ref":
        row["credit_binding_ref"] = None
    elif change == "parent":
        row["parent_invocation_ref"] = row["invocation_ref"]
    elif change == "origin":
        row["origin_kind"] = "approach_revision"
    else:
        row["episode_yield"]["stop_requested"] = 1
    with pytest.raises(ValueError):
        validate_process_result(row)


def test_builder_and_projection_do_not_refit_score_discover_or_write(current, monkeypatch):
    library, tools = current
    row = _full_row(library, tools)
    assignment = {"selection": row["selection"]}
    context = SimpleNamespace(run_id="synthetic-run", path=PATH,
        assignment=_frozen(assignment), request=_frozen({"message": {
            "scientific_invocation_ref": row["invocation_ref"], "episode_assignment": assignment}}))
    snapshot = {"completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 2},
        "own_action_count": 2, "initial_credit": row["initial_credit"], "credit": row["credit"],
        "controller_credit": METADATA, "episode_yield": row["episode_yield"],
        "parent_invocation_ref": row["parent_invocation_ref"]}
    before = _snapshot_bytes(library, tools)
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Pure projection cannot refit, execute, discover or write")
    monkeypatch.setattr("gene_annotation_episode.episode_reports.closing_yield", forbidden)
    for method in ("freeze", "entry", "search", "execute"):
        monkeypatch.setattr(ScientificProcessLibrary, method, forbidden)
    for method in ("freeze", "retrieve", "retrieve_literal_test", "resolve_invocations", "catalog", "parent_tool_info"):
        monkeypatch.setattr(ScientificToolLibrary, method, forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    built = build_process_result(context, _frozen(snapshot))
    assert built == row
    assert set(built["selection"]["child_tool_info"][0]) == {"name", "description", "resources", "instructions"}
    result = project_process_result(built, library=library, tool_library=tools)
    assert result["episode_yield"] == row["episode_yield"]
    assert calls == [] and _snapshot_bytes(library, tools) == before


def test_projection_requires_pinned_libraries_and_does_not_refresh_missing_sources(current, monkeypatch):
    library, tools = current
    row = _full_row(library, tools)
    for process, tool in ((None, tools), (library, None)):
        with pytest.raises(ValueError, match="scientific_process_result_library_invalid"):
            project_process_result(row, library=process, tool_library=tool)
    def unavailable(*args, **kwargs):
        raise ValueError("scientific_process_entry_changed")
    monkeypatch.setattr(library, "resolve", unavailable)
    with pytest.raises(ValueError, match="scientific_process_entry_changed"):
        project_process_result(row, library=library, tool_library=tools)


def test_literal_hybrid_saved_schema_remains_invalid_after_new_projection(legacy):
    library, tools = legacy
    row = _full_row(library, tools, legacy=True)
    schema = json.loads((FIXTURES / "literal-legacy-form-schema.json").read_bytes())
    schema["properties"]["chosen_name"]["items"]["properties"]["selection"]["properties"]["version"]["const"] = "scientific_process_selection_v3"
    before = deepcopy(schema)
    with pytest.raises(ReportBoundaryError):
        validate_form({"chosen_name": [row]}, schema, _resolver(library, row))
    projected = project_process_result(row, library=library, tool_library=tools)
    with pytest.raises(ReportBoundaryError):
        validate_form({"chosen_name": [projected]}, schema, _resolver(library, projected))
    assert schema == before


def test_stable_union_requires_explicit_projection_before_merging(current):
    library, tools = current
    own = _full_row(library, tools)
    child = {**deepcopy(own), "invocation_ref": scientific_invocation_ref("synthetic-run", (*PATH, ("scientific_process", "revision"))),
        "parent_invocation_ref": own["invocation_ref"], "origin_kind": "approach_revision",
        "preparation_operation_ref": "operation_" + "d" * 24}
    other = {**deepcopy(own), "invocation_ref": scientific_invocation_ref("synthetic-run", (*PATH, ("scientific_process", "other")))}
    compact = project_process_result(own, library=library, tool_library=tools)
    with pytest.raises(ValueError, match="scientific_process_result_conflict"):
        merge_process_results(own, [compact])
    rows = [child, own, child, other]
    projected = [project_process_result(item, library=library, tool_library=tools) for item in rows]
    merged = merge_process_results(compact, projected)
    assert merged == [compact, projected[0], projected[3]]
    assert merge_process_results(None, projected) == [projected[0], compact, projected[3]]
    assert merged[1]["origin_kind"] == "approach_revision"
    assert merged[1]["preparation_operation_ref"] == "operation_" + "d" * 24
    with pytest.raises(ValueError, match="scientific_process_result_conflict"):
        merge_process_results(compact, [{**deepcopy(compact), "credit": 14.75}])
    merged[0]["episode_yield"]["expected_next_gain"]["value"] = 100
    assert compact["episode_yield"]["expected_next_gain"]["value"] == -0.25
