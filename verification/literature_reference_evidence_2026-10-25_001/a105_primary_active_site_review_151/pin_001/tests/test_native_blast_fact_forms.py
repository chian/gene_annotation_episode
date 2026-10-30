"""Exact native BLAST recorded forms at the existing communication boundary.

All contracts come from the production descriptors. Filled payloads are synthetic
boundary fixtures, not native search measurements or episode integration claims.
"""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import communication as boundary
from gene_annotation_episode.form_reference_validation import form_validation_value
from gene_annotation_episode.native_blast_database_result_views import native_blast_database_fact_sources
from gene_annotation_episode.runtime import TypedReportContract, _compile_form


SOURCES = native_blast_database_fact_sources()
PREFIX = "execution_blast_database_"
ROW_KEY = "native_blast_database_row:one"
SEARCH_POINTER = "/BlastOutput2/0/report/results/search"


def object_form(fields):
    return dict(type="object", properties=fields, required=list(fields), additionalProperties=False)


def fact_form(source):
    return object_form({"facts": deepcopy(SOURCES[source]["report_schema"])})


def row_form(family="search"):
    return fact_form(PREFIX + family + "_rows")


def search_identity():
    return dict(artifact_key="artifact:report", member_ordinal=None,
        report_index=0, search_pointer=SEARCH_POINTER)


def provenance():
    return dict(source_ref="source:identity", pointer="/records/0")


def numeric_row(family="search", *, scope="search"):
    if family == "iteration_convergence":
        identity = dict(record_source=provenance(), scope=scope,
            search_key=search_identity() if scope == "search" else None,
            query_identity=dict(artifact_key="artifact:query", record_ordinal=0,
                axis_kind="sequence", selected_interval=[2, 5]) if scope == "query" else None)
    elif family == "sequence_taxonomy":
        identity = dict(search_key=search_identity(), function="function:EC2.1.1", rank="species")
    elif family == "hsp":
        identity = dict(row_key=dict(search_key=search_identity(), hit_ordinal=0,
            hsp_ordinal=0, description_ordinal=None))
    else:
        assert family == "search"
        identity = dict(search_key=search_identity())
    return dict(schema="native_blast_database_numeric_row_v1", family=family,
        record_key=ROW_KEY, calculation_id="a" * 64, identity=identity, program="psiblast",
        context=dict(query_axis_kind="sequence", reference_axis_kind="sequence",
            stage="sequence_database", native_iteration=None, biological_round=None),
        component_refs=[dict(artifact_role="calculations", pointer="/searches/0")],
        native_status="available", measurements=[], booleans=[],
        source_ref="source:bundle", observation_ref="observation:one", subject_ref="subject:query",
        reference_refs=["source:reference"], publication_status="published")


def measurement(**changes):
    return dict(dict(name="reported_hit_count", value=0, status="available", reason=None,
        origin="native_report", component_pointer="/counts/reported_hit_count",
        numerator=None, denominator=None, unit="hit", complete=True), **changes)


def boolean(**changes):
    return dict(dict(name="native_converged", value=False, status="available", reason=None,
        origin="native_report", component_pointer="/converged"), **changes)


def failure():
    return dict(stage="projection", code="native_blast_database_selector_unavailable",
        artifact_key="artifact:report", input_key=None, search_key=search_identity(),
        record_key=ROW_KEY, pointer="/projections/0", detail_code="explicit_row_missing")


def registry():
    return {
        "execution_result": {"source:bundle", "source:identity", "source:reference", "observation:one"},
        "subject": {"subject:query"},
        "native_blast_database_row": {ROW_KEY, "native_blast_database_row:two"},
        "native_blast_database_artifact_key": {"artifact:report", "artifact:query"},
        "native_blast_database_search_pointer": {SEARCH_POINTER},
        "native_blast_database_entity_key": {"function:EC2.1.1"},
    }


def resolver(calls=None, values=None):
    resolve = boundary.reference_resolver(registry() if values is None else values)
    def checked(reference, namespace):
        if calls is not None:
            calls.append((reference, namespace))
        return resolve(reference, namespace)
    return checked


@pytest.mark.parametrize("source", SOURCES)
def test_all_registered_sources_compile_and_admit(source):
    # The original thirty plus record quality, four VDB function result
    # families, and the received saved-function-input descriptor.
    assert len(SOURCES) == 36
    schema = fact_form(source)
    expected = SOURCES[source]["report_schema"]
    value = {key: False for key in expected["properties"]} if expected["type"] == "object" else []
    payload = {"facts": value}
    assert boundary.validate_closed_schema(schema) == schema
    assert _compile_form(json.dumps(schema), SOURCES) == schema
    contract = TypedReportContract("retain_requested_native_facts", schema, resolver())
    assert contract.admit(payload, audit_identifiers=()).as_record() == payload
    assert schema["properties"]["facts"] == expected


@pytest.mark.parametrize("mutation", [
    "unknown_source", "different_source", "open_replacement", "closed_replacement",
    "missing_unique_by", "missing_unique_items", "missing_pattern", "missing_conditionals",
    "extra_field", "extra_annotation", "changed_namespace", "boolean_bound", "float_bound",
])
def test_exact_registration_rejects_tampering(mutation):
    schema = row_form()
    node = schema["properties"]["facts"]
    row = node["items"]
    if mutation == "unknown_source":
        node["x-source"] = PREFIX + "unknown_rows"
    elif mutation == "different_source":
        node["x-source"] = PREFIX + "hsp_rows"
    elif mutation == "open_replacement":
        schema["properties"]["facts"] = {"type": "object", "x-source": PREFIX + "search_rows"}
    elif mutation == "closed_replacement":
        schema["properties"]["facts"] = {"type": "number", "x-source": PREFIX + "search_rows"}
    elif mutation == "missing_unique_by":
        node.pop("x-unique-by")
    elif mutation == "missing_unique_items":
        node.pop("uniqueItems")
    elif mutation == "missing_pattern":
        row["properties"]["record_key"].pop("pattern")
    elif mutation == "missing_conditionals":
        row["properties"]["measurements"]["items"].pop("allOf")
    elif mutation == "extra_field":
        row["properties"]["extra"] = {"type": "number"}
        row["required"].append("extra")
    elif mutation == "extra_annotation":
        node["description"] = "Changed from the registered contract."
    elif mutation == "changed_namespace":
        row["properties"]["source_ref"]["x-reference-namespace"] = "subject"
    elif mutation == "boolean_bound":
        row["properties"]["record_key"]["minLength"] = True
    elif mutation == "float_bound":
        row["properties"]["record_key"]["minLength"] = 1.0
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_closed_schema(schema)
    assert error.value.diagnostic["code"] == "invalid_schema"


def test_generic_shaped_acquisition_still_requires_its_exact_contract():
    schema = fact_form(PREFIX + "acquisition")
    node = schema["properties"]["facts"]
    node["properties"]["complete"] = {"type": "number"}
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_closed_schema(schema)


@pytest.mark.parametrize("placement", ["object", "array", "nested_source", "unbound"])
def test_registered_meaning_is_only_a_whole_top_level_recorded_field(placement):
    node = deepcopy(SOURCES[PREFIX + "search_rows"]["report_schema"])
    if placement == "object":
        schema = object_form({"nested": object_form({"facts": node})})
    elif placement == "array":
        schema = object_form({"nested": {"type": "array", "items": object_form({"facts": node})}})
    elif placement == "nested_source":
        node["items"]["properties"]["source_ref"]["x-source"] = PREFIX + "result_refs"
        schema = object_form({"facts": node})
    else:
        node.pop("x-source")
        schema = object_form({"facts": node})
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_closed_schema(schema)


@pytest.mark.parametrize("updates", [
    {"value": None}, {"status": "unavailable"}, {"reason": "missing_input"},
    {"value": None, "status": "unavailable", "reason": None}, {"unit": "nt"},
    {"name": "undefined_measurement"}, {"value": True}, {"component_pointer": "not/a/pointer"},
])
def test_native_numeric_status_reason_metric_unit_and_pattern_constraints(updates):
    row = numeric_row()
    row["measurements"] = [measurement(**updates)]
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form({"facts": [row]}, row_form(), resolver())


@pytest.mark.parametrize("value,status,reason", [
    (0, "available", None), (None, "unavailable", "missing_input"),
    (None, "unavailable", "not_measured"), (None, "incompatible", "incompatible_input"),
])
def test_zero_and_native_missingness_remain_distinct(value, status, reason):
    row = numeric_row()
    row["measurements"] = [measurement(value=value, status=status, reason=reason)]
    payload = {"facts": [row]}
    assert boundary.validate_form(payload, row_form(), resolver()) == payload


@pytest.mark.parametrize("updates", [
    {"value": None}, {"value": 0}, {"status": "unavailable"}, {"reason": "missing_input"},
])
def test_native_boolean_conditional_contract(updates):
    row = numeric_row()
    row["booleans"] = [boolean(**updates)]
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form({"facts": [row]}, row_form(), resolver())


def test_not_constraint_excludes_cells_for_a_family_without_those_metrics():
    row = numeric_row("iteration_convergence")
    row["measurements"] = [measurement()]
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form({"facts": [row]}, row_form("iteration_convergence"), resolver())
    assert error.value.diagnostic["code"] == "not"


@pytest.mark.parametrize("scope", ["search", "query", "unbound"])
def test_tagged_identity_and_base_references_reach_the_live_resolver(scope):
    row = numeric_row("iteration_convergence", scope=scope)
    row["booleans"] = [boolean()]
    calls = []
    payload = {"facts": [row]}
    assert boundary.validate_form(payload, row_form("iteration_convergence"), resolver(calls)) == payload
    expected = {(ROW_KEY, "native_blast_database_row"), ("source:identity", "execution_result"),
        ("source:bundle", "execution_result"), ("observation:one", "execution_result"),
        ("subject:query", "subject"), ("source:reference", "execution_result")}
    if scope == "search":
        expected |= {("artifact:report", "native_blast_database_artifact_key"),
            (SEARCH_POINTER, "native_blast_database_search_pointer")}
    elif scope == "query":
        expected.add(("artifact:query", "native_blast_database_artifact_key"))
    assert set(calls) == expected


@pytest.mark.parametrize("interval", [[2], [2, 5, 6], [-1, 5], [2, 0], ["2", 5], [2, .5]])
def test_tagged_query_tuple_constraints_keep_actual_prefix_positions(interval):
    row = numeric_row("iteration_convergence", scope="query")
    row["identity"]["query_identity"]["selected_interval"] = interval
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_form({"facts": [row]}, row_form("iteration_convergence"), resolver())


def test_tagged_identity_rejects_mismatched_scope_and_payload():
    row = numeric_row("iteration_convergence", scope="query")
    row["identity"]["scope"] = "search"
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form({"facts": [row]}, row_form("iteration_convergence"), resolver())
    assert error.value.diagnostic["code"] == "oneOf"


@pytest.mark.parametrize("field", ["observation_ref", "subject_ref", "nullable_function", "tagged_source", "tagged_query_artifact"])
def test_unknown_references_cannot_hide_in_nullable_or_tagged_branches(field):
    family = "sequence_taxonomy" if field == "nullable_function" else "iteration_convergence"
    row = numeric_row(family, scope="query")
    target = row
    key = field
    if field == "nullable_function":
        target, key = row["identity"], "function"
    elif field == "tagged_source":
        target, key = row["identity"]["record_source"], "source_ref"
    elif field == "tagged_query_artifact":
        target, key = row["identity"]["query_identity"], "artifact_key"
    target[key] = "wrong_namespace_or_unavailable"
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form({"facts": [row]}, row_form(family), resolver())
    assert error.value.diagnostic["code"] == "unknown_reference"
    assert error.value.diagnostic["field"].endswith("." + key)


def test_nullable_entity_references_keep_their_namespaces():
    row = numeric_row("sequence_taxonomy")
    calls = []
    schema = row_form("sequence_taxonomy")
    assert boundary.validate_form({"facts": [row]}, schema, resolver(calls))
    assert ("function:EC2.1.1", "native_blast_database_entity_key") in calls
    row["identity"]["function"] = row["subject_ref"] = row["observation_ref"] = None
    calls.clear()
    assert boundary.validate_form({"facts": [row]}, schema, resolver(calls))
    assert all(ref not in {None, "function:EC2.1.1", "subject:query", "observation:one"} for ref, _ in calls)


def test_failure_locators_can_name_unavailable_addresses_without_claiming_possession():
    missing = failure()
    missing.update(artifact_key="artifact:missing", record_key="native_blast_database_row:missing")
    missing["search_key"].update(artifact_key="artifact:missing", search_pointer="/missing/search")
    payload, calls = {"facts": [missing]}, []
    assert boundary.validate_form(payload, fact_form(PREFIX + "failures"), resolver(calls)) == payload
    assert calls == []
    # The same failed address cannot become an authenticated returned row.
    row = numeric_row()
    row["identity"]["search_key"] = missing["search_key"]
    with pytest.raises(boundary.ReportBoundaryError, match="reference is unavailable"):
        boundary.validate_form({"facts": [row]}, row_form(), resolver())
    missing["search_key"]["search_pointer"] = "not/a/pointer"
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form(payload, fact_form(PREFIX + "failures"), resolver())
    assert error.value.diagnostic["code"] == "anyOf"


def test_distinct_rows_with_the_same_actual_identity_tuple_are_rejected():
    row = numeric_row()
    row["measurements"] = [measurement()]
    other = deepcopy(row)
    other["measurements"][0]["value"] = 4
    payload = {"facts": [row, other]}
    schema = row_form()
    assert Draft202012Validator(schema).is_valid(payload)  # uniqueItems alone passes.
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form(payload, schema, resolver())
    assert error.value.diagnostic == dict(category="report_format", code="duplicate_identity", field="report.facts[1]")
    other["calculation_id"] = "b" * 64
    assert boundary.validate_form(payload, schema, resolver()) == payload
    other["calculation_id"] = row["calculation_id"]
    other["record_key"] = "native_blast_database_row:two"
    assert boundary.validate_form(payload, schema, resolver()) == payload


def test_identical_rows_still_fail_the_original_unique_items_constraint():
    row = numeric_row()
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form({"facts": [row, deepcopy(row)]}, row_form(), resolver())
    assert error.value.diagnostic["code"] == "uniqueItems"


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_native_measurements_remain_rejected(number):
    row = numeric_row()
    row["measurements"] = [measurement(value=number)]
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form({"facts": [row]}, row_form(), resolver())
    assert error.value.diagnostic["code"] == "nonfinite_number"


def test_all_recorded_fields_are_excluded_and_copied_from_facts():
    fields = {"field_" + str(i): descriptor["report_schema"] for i, descriptor in enumerate(SOURCES.values())}
    fields["assessment"] = {"type": "string", "enum": ["retained"]}
    schema = object_form(fields)
    original = deepcopy(schema)
    interpret = boundary.interpretation_schema(schema)
    assert interpret == object_form({"assessment": fields["assessment"]})
    assert boundary.generation_schema(interpret) == interpret
    facts = {source: {key: False for key in node["report_schema"]["properties"]}
        if node["type"] == "object" else [] for source, node in SOURCES.items()}
    facts[PREFIX + "search_rows"] = [numeric_row()]
    form = boundary.form_with_facts({"assessment": "retained"}, schema, facts)
    assert boundary.validate_form(form, schema, resolver()) == form
    assert schema == original
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.form_with_facts({**form, "assessment": "retained"}, schema, facts)
    assert error.value.diagnostic["code"] == "interpretation_fields"
    key = next(name for name, node in fields.items() if node.get("x-source") == PREFIX + "search_rows")
    form[key][0]["source_ref"] = "changed"
    assert facts[PREFIX + "search_rows"][0]["source_ref"] == "source:bundle"


def test_generation_translates_every_native_branch_without_changing_runtime_schema():
    schema = object_form({source: descriptor["report_schema"] for source, descriptor in SOURCES.items()})
    original = deepcopy(schema)
    generated = boundary.generation_schema(schema)
    def check(node):
        if isinstance(node, dict):
            assert not {"x-source", "x-reference-namespace", "x-unique-by", "format", "uniqueItems", "const"} & node.keys()
            for child in node.values():
                check(child)
        elif isinstance(node, list):
            for child in node:
                check(child)
    check(generated)
    convergence = generated["properties"][PREFIX + "iteration_convergence_rows"]["items"]["properties"]
    query = convergence["identity"]["oneOf"][1]["properties"]
    assert query["scope"] == {"enum": ["query"]}
    interval = query["query_identity"]["properties"]["selected_interval"]["anyOf"][0]
    assert interval["prefixItems"] == [{"type": "integer", "minimum": 0}, {"type": "integer", "minimum": 1}]
    assert schema == original
    Draft202012Validator.check_schema(generated)
    assert boundary.validate_closed_schema(schema) == schema


def test_schema_cache_retains_only_successes_and_detaches_each_return():
    boundary._compiled_schema_content.cache_clear()
    schema = row_form()
    first = boundary.validate_closed_schema(schema)
    first["properties"]["facts"]["items"]["properties"]["record_key"].pop("pattern")
    assert boundary.validate_closed_schema(schema) == schema
    assert boundary._compiled_schema_content.cache_info().hits == 1
    assert boundary._compiled_schema_content.cache_info().currsize == 1
    for _ in range(2):
        with pytest.raises(boundary.ReportBoundaryError):
            boundary.validate_closed_schema(first)
        assert boundary._compiled_schema_content.cache_info().currsize == 1
    # A caller mutation must miss the content cache and be checked afresh.
    schema["properties"]["facts"]["x-unique-by"] = ["record_key"]
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_closed_schema(schema)
    boundary._compiled_schema_content.cache_clear()


def test_cached_native_schema_does_not_cache_reference_authority_across_forms():
    schema, payload = row_form(), {"facts": [numeric_row()]}
    live, produced = registry(), []
    def produce():
        produced.append(True)
        return live
    def resolve(reference, namespace):
        actual = form_validation_value(("native_fixture",), produce)
        return boundary.reference_resolver(actual)(reference, namespace)
    assert boundary.validate_form(payload, schema, resolve) == payload
    assert len(produced) == 1
    live["execution_result"].remove("observation:one")
    with pytest.raises(boundary.ReportBoundaryError, match="reference is unavailable"):
        boundary.validate_form(payload, schema, resolve)
    assert len(produced) == 2
    live["execution_result"].add("observation:one")
    assert boundary.validate_form(payload, schema, resolve) == payload
    assert len(produced) == 3


@pytest.mark.parametrize("node", [
    {"type": "string"}, {"type": "string", "pattern": "^[a-z]+$"},
    {"type": "string", "pattern": "^[a-z]+$", "x-source": "unregistered_source"},
    {"type": "object", "properties": {}, "additionalProperties": True},
    {"type": "object", "properties": {"number": {"type": "number"}}, "additionalProperties": False},
    {"type": "array"}, {"anyOf": [{"type": "number"}, {"type": "null"}]},
    {"type": "number", "x-unique-by": ["record_key"]},
])
def test_generic_closed_grammar_has_no_new_escape(node):
    with pytest.raises(boundary.ReportBoundaryError):
        boundary.validate_closed_schema(object_form({"value": node}))


def test_ordinary_generation_and_recorded_facts_keep_their_existing_behavior():
    schema = object_form({"credit": {"type": "number", "x-source": "credit"},
        "unit": {"type": ["string", "null"], "format": "unit"},
        "result": {"type": "string", "const": "retained"}})
    payload = boundary.form_with_facts({"unit": "bits", "result": "retained"}, schema, {"credit": 2.5})
    assert boundary.validate_form(payload, schema) == payload
    generated = boundary.generation_schema(schema)
    assert generated["properties"]["credit"] == {"type": "number"}
    assert generated["properties"]["unit"] == {"type": ["string", "null"], "enum": sorted(boundary.UNITS) + [None]}
    assert generated["properties"]["result"] == {"type": "string", "enum": ["retained"]}


def test_generic_reference_error_preserves_payload_field_order():
    declared = {"type": "string", "format": "reference", "x-reference-namespace": "subject"}
    schema = object_form({"first": declared, "second": declared})
    with pytest.raises(boundary.ReportBoundaryError) as error:
        boundary.validate_form({"second": "absent", "first": "also_absent"}, schema, resolver())
    assert error.value.diagnostic == dict(category="report_format", code="unknown_reference", field="report.second")


def test_nonfinite_generic_schema_retains_its_uncached_diagnostic():
    schema = object_form({"number": {"type": "number", "enum": [float("nan")]}})
    before = boundary._compiled_schema_content.cache_info()
    for _ in range(2):
        with pytest.raises(boundary.ReportBoundaryError) as error:
            boundary.validate_closed_schema(schema)
        assert error.value.diagnostic == dict(category="report_format", code="nonfinite_number", field="report.properties.number.enum[0]")
    assert boundary._compiled_schema_content.cache_info() == before
