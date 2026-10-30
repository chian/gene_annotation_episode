"""Exact grammar and internal relations only; these fixtures prove no custody."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema,
    validate_closed_schema, validate_form,
)
from gene_annotation_episode.uniprot_return_contracts import (
    UniProtReturnValidationError, requested_uniprot_selection, uniprot_fact_sources,
    uniprot_return_selection_schema, uniprot_selected_return_schema,
    validate_uniprot_return_selection, validate_uniprot_selected_values,
)


SOURCE = "uniprot_selected_returns"
DIGEST = "a" * 64
RP = "/results/0"
SPEC = (Path(__file__).resolve().parents[1] / "verification" /
        "tool_graders_uniprot_requested_returns_2026-10-28_601" /
        "PROPOSED_SELECTED_RETURN_SCHEMA_002.json")


def form(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def selection(fields=(), *, record=None, source_grant=False, sequence_grant=False):
    return {"version": "uniprot_return_selection_v1", "pages": [{
        "publication": {"mode": "assigned_page"}, "page_fields": [],
        "records": [{"record": record or {"mode": "ordinal", "ordinal": 0},
                     "fields": deepcopy(list(fields)), "grant_sequence_artifact": sequence_grant}],
        "grant_source": source_grant}]}


def failure(code, pointer=None, *, ri=0, fi=0):
    return {"code": code, "page_selection_index": 0, "record_selection_index": ri,
            "field_selection_index": fi, "native_pointer": pointer}


def reply(request, value, *, index=0, status="available", failures=()):
    return {"request_index": index, "request": deepcopy(request), "status": status,
            "value": value, "failures": list(failures)}


def returned(cells=()):
    record = {"record_selection_index": 0, "requested_record_ordinal": 0, "state": "bound",
        "witness": {"record_id": "reference_ab", "record_ordinal": 0, "record_pointer": RP,
                    "accession_relation": "search_member", "sequence_artifact_id": "artifact_bc"},
        "fields": list(cells), "issues": [], "sequence_grant_status": "not_requested",
        "sequence_grant": None, "failures": []}
    page = {"page_selection_index": 0,
        "witness": {"source_id": "source_ab", "native_artifact_id": "artifact_ab",
                    "content_sha256": DIGEST, "publication_sha256": DIGEST},
        "status": {"operation": "search", "selection_extent": "one_selected_page",
            "response_body_state": "complete_json", "parser_projection_state": "complete",
            "outer_acquisition_status": "completed", "native_record_count": 1,
            "parser_eligible_record_count": 1, "bound_record_count": 1,
            "requested_record_count": 1, "returned_bound_record_count": 1,
            "pagination_metadata_available": True, "next_state": "absent", "whole_query_complete": True,
            "request_verification": "caller_supplied", "unselected_issue_count": 0,
            "record_selection_count": 1, "indeterminate_record_count": 0},
        "page_fields": [], "records": [record], "issues": [], "source_grant_status": "not_requested",
        "source_grant": None, "failures": []}
    return {"version": "uniprot_selected_returns_v1", "pages": [page], "failures": []}


def token(value, pointer, state="present"):
    return {"native_state": state, "representation": "exact" if value is not None else "unavailable",
            "value": value, "pointer": pointer}


def text_window(text, pointer, offset=0, limit=40):
    n = len(text)
    start, end = min(offset, n), min(offset + limit, n)
    extent = ("offset_past_end" if offset > n else "empty_value" if n == 0 and offset == 0
              else "whole_value" if start == 0 and end == n else "window")
    return {"native_state": "present", "pointer": pointer, "owner_pointer": pointer.rsplit("/", 1)[0],
        "offset": offset, "limit": limit, "native_length": n, "start": start, "end": end,
        "text": text[start:end], "omitted_prefix": start, "omitted_suffix": n - end,
        "extent": extent, "unit": "unicode_code_points"}


def collection(members=(), *, excluded=0, native_state="present", native_count=None):
    members = list(members)
    return {"native_state": native_state,
        "native_member_count": len(members) + excluded if native_count is None else native_count,
        "matching_member_count": sum(m["selection_state"] == "matched" for m in members),
        "indeterminate_member_count": sum(m["selection_state"] == "indeterminate" for m in members),
        "unavailable_member_count": sum(m["selection_state"] == "unavailable" for m in members),
        "excluded_member_count": excluded, "members": members}


def evidence_member(owner, ordinal=0):
    pointer = owner + "/evidences/" + str(ordinal)
    return {"ordinal": ordinal, "pointer": pointer, "selection_state": "matched", "failures": [],
        "value": {"ordinal": ordinal, "pointer": pointer, "owner_pointer": owner,
            "eco": token("ECO:0000269", pointer + "/evidenceCode"),
            "source": token("PubMed", pointer + "/source"),
            "source_identifier": token("12345", pointer + "/id")}}


def feature_member(ordinal=0, start=10, end=20):
    pointer = RP + "/features/" + str(ordinal)
    def position(value, key):
        p = pointer + "/location/" + key
        return {"native_state": "present", "value": value, "value_pointer": p + "/value",
                "value_state": "present", "modifier": token("EXACT", p + "/modifier")}
    return {"ordinal": ordinal, "pointer": pointer, "selection_state": "matched", "failures": [],
        "value": {"ordinal": ordinal, "pointer": pointer, "start": position(start, "start"),
            "end": position(end, "end"), "native_sequence_id": token(None, pointer + "/location/sequence", "absent"),
            "sequence_binding": "entry_sequence", "native_coordinates": "one_based_inclusive",
            "exact_interval": [start - 1, end], "derived_coordinates": "zero_based_half_open", "unit": "aa",
            "type_window": None, "description_window": None, "evidence": None}}


def test_selection_and_expanded_schema_match_frozen_artifact_exactly():
    artifact = json.loads(SPEC.read_text())
    assert uniprot_return_selection_schema() == artifact["selection_schema"]
    actual = uniprot_selected_return_schema(artifact["example_selection"])
    assert actual == artifact["example_parent_form"]["properties"]["selected_uniprot"]
    assert "$defs" not in actual and "$schema" not in actual
    assert '"$ref"' not in json.dumps(actual)
    assert requested_uniprot_selection(form({"a_different_parent_name": actual})) == artifact["example_selection"]
    advertised = uniprot_fact_sources()[SOURCE]
    assert advertised["type"] == "object"
    assert advertised["meaning"] == "Exactly requested UniProt source facts and explicit material grants."
    assert advertised["report_schema"]["x-uniprot-selection"]["pages"] == []


def test_selection_and_schema_copies_are_detached_and_unmodified():
    requested = selection([{"kind": "integer", "field": "taxon_id"}])
    before = deepcopy(requested)
    copy = validate_uniprot_return_selection(requested)
    copy["pages"][0]["records"].clear()
    assert requested == before
    schema = uniprot_selected_return_schema(requested)
    schema["x-uniprot-selection"]["pages"].clear()
    assert requested == before
    first = uniprot_return_selection_schema()
    first["$defs"]["NativeState"]["enum"].clear()
    assert uniprot_return_selection_schema()["$defs"]["NativeState"]["enum"]


@pytest.mark.parametrize("bad", [True, False, 1.0, -1, "0", None])
def test_record_ordinals_require_exact_nonnegative_integers(bad):
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selection_invalid"):
        validate_uniprot_return_selection(selection(record={"mode": "ordinal", "ordinal": bad}))


@pytest.mark.parametrize("bad", [1, 0, 1.0, "true", None])
def test_grant_switches_require_boolean_values(bad):
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selection_invalid"):
        validate_uniprot_return_selection(selection(source_grant=bad))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), (1, 2), {1: 2}, {1, 2}])
def test_selection_is_strict_finite_json(bad):
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selection_invalid"):
        validate_uniprot_return_selection(bad)


@pytest.mark.parametrize("kind", ["page", "record", "field", "property"])
def test_duplicate_criteria_fail_even_when_field_selection_differs(kind):
    request = {"kind": "cross_reference", "selection": {"mode": "database", "database": "GO"},
               "include_evidence": False, "properties": [{"key": "GoEvidenceType", "window": {"offset": 0, "limit": 40}}]}
    selected = selection([request])
    page = selected["pages"][0]
    if kind == "page":
        selected["pages"].append(deepcopy(page))
        selected["pages"][1]["grant_source"] = True
    elif kind == "record":
        page["records"].append(deepcopy(page["records"][0]))
        page["records"][1]["fields"].clear()
    elif kind == "field":
        page["records"][0]["fields"].append(deepcopy(request))
    else:
        page["records"][0]["fields"][0]["properties"] *= 2
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selection_duplicate"):
        validate_uniprot_return_selection(selected)


def test_supported_collection_record_modes_and_overlapping_clauses():
    artifact = json.loads(SPEC.read_text())
    selected = artifact["example_selection"]
    assert validate_uniprot_return_selection(selected) == selected
    records = selected["pages"][0]["records"]
    records.extend([{"record": {"mode": "ordinal", "ordinal": 0}, "fields": [], "grant_sequence_artifact": False},
                    {"record": {"mode": "primary_accession", "accession": "P0AAW1"}, "fields": [], "grant_sequence_artifact": False}])
    assert validate_uniprot_return_selection(selected) == selected
    for kind, selector in (("feature_location", {"mode": "all"}),
                           ("feature_location", {"mode": "ordinal", "ordinal": 31}),
                           ("cross_reference", {"mode": "all"}),
                           ("cross_reference", {"mode": "ordinal", "ordinal": 31}),
                           ("evidence", {"mode": "all_record"}),
                           ("evidence", {"mode": "owner_ordinal", "owner_pointer": "", "ordinal": 0})):
        field = {"kind": kind, "selection": selector}
        if kind == "feature_location":
            field.update(include_evidence=False, type_window=None, description_window=None)
        elif kind == "cross_reference":
            field.update(include_evidence=False, properties=[])
        validate_uniprot_return_selection(selection([field]))


@pytest.mark.parametrize("field,pointer", [
    ("protein_name", "/proteinDescription/includes/0/alternativeNames/1/shortNames/2/value"),
    ("gene_name", "/genes/0/orderedLocusNames/3/value"), ("entry_type", "/entryType"),
    ("protein_existence", "/proteinExistence"), ("entry_date", "/entryAudit/firstPublicDate"),
    ("taxon_name", "/organism/scientificName"), ("taxon_synonym", "/organism/synonyms/0"),
    ("taxon_lineage_name", "/organism/lineage/0"), ("feature_type", "/features/0/type"),
    ("feature_description", "/features/0/description"),
    ("xref_property_key", "/uniProtKBCrossReferences/0/properties/0/key"),
    ("xref_property_value", "/uniProtKBCrossReferences/0/properties/0/value"),
    ("comment_text", "/comments/0/texts/0/value"), ("native_text", "/weird~1key/~0value"),
])
def test_declared_text_semantics_accept_their_exact_pointer_branch(field, pointer):
    validate_uniprot_return_selection(selection([{"kind": "text", "field": field, "pointer": pointer, "offset": 0, "limit": 40}]))


@pytest.mark.parametrize("requested_field,code", [
    ({"kind": "text", "field": "protein_name", "pointer": "/comments/0/texts/0/value", "offset": 0, "limit": 40}, "pointer_conflict"),
    ({"kind": "text", "field": "native_text", "pointer": "/sequence/value", "offset": 0, "limit": 40}, "pointer_conflict"),
    ({"kind": "ec_assignment", "pointer": "/comments/0/value"}, "pointer_conflict"),
    ({"kind": "sequence_window", "start": 5, "end": 5}, "interval_invalid"),
    ({"kind": "sequence_window", "start": True, "end": 5}, "interval_invalid"),
    ({"kind": "text", "field": "native_text", "pointer": "/entryType", "offset": 0, "limit": 0}, "interval_invalid"),
    ({"kind": "token", "field": "primary_accession", "array_ordinal": 0}, "invalid"),
    ({"kind": "token", "field": "secondary_accession", "array_ordinal": None}, "invalid"),
    ({"kind": "evidence", "selection": {"mode": "ordinal", "ordinal": 0}}, "invalid"),
])
def test_unsupported_selectors_have_declared_failure_codes(requested_field, code):
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selection_" + code):
        validate_uniprot_return_selection(selection([requested_field]))


def test_mixed_publication_modes_and_duplicate_registrations_fail():
    selected = selection()
    forwarded = deepcopy(selected["pages"][0])
    forwarded["publication"] = {"mode": "received_publication", "source_id": "source_ab", "publication_sha256": DIGEST}
    selected["pages"].append(forwarded)
    with pytest.raises(UniProtReturnValidationError, match="mode_conflict"):
        validate_uniprot_return_selection(selected)
    schema = uniprot_selected_return_schema(selection())
    with pytest.raises(UniProtReturnValidationError, match="selection_duplicate"):
        requested_uniprot_selection(form({"first": schema, "second": schema}))
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(form({"first": schema, "second": schema}))
    assert caught.value.diagnostic["code"] == "uniprot_selection_duplicate"
    assert requested_uniprot_selection(form({"nested": form({"inner": schema})})) is None
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"nested": form({"inner": schema})}))


@pytest.mark.parametrize("change", ["float", "bool", "extra", "prose", "missing_selection"])
def test_registered_compiler_accepts_only_the_exact_generated_tree(change):
    schema = uniprot_selected_return_schema(selection())
    valid = deepcopy(schema)
    assert validate_closed_schema(form({"arbitrary_name": valid}))
    status = schema["properties"]["pages"]["items"]["properties"]["status"]
    if change == "float":
        status["properties"]["bound_record_count"]["minimum"] = 0.0
    elif change == "bool":
        status["properties"]["bound_record_count"]["minimum"] = False
    elif change == "extra":
        schema["description"] = "Not registered"
    elif change == "prose":
        schema["properties"]["unrequested"] = {"type": "string"}
        schema["required"].append("unrequested")
    else:
        del schema["x-uniprot-selection"]
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"arbitrary_name": schema}))


@pytest.mark.parametrize("text,offset,limit", [("x" * 10000, 20, 40), ("α🧬é", 1, 1), ("", 0, 40), ("", 3, 40), ("abc", 3, 40), ("abc", 9, 40)])
def test_text_windows_keep_exact_code_point_lengths_and_omission_extents(text, offset, limit):
    request = {"kind": "text", "field": "protein_name", "pointer": "/proteinDescription/recommendedName/fullName/value", "offset": offset, "limit": limit}
    window = text_window(text, RP + request["pointer"], offset, limit)
    value = returned([reply(request, window)])
    selected = selection([request])
    validate_uniprot_selected_values(value, selection=selected)
    window["omitted_suffix"] += 1
    with pytest.raises(UniProtReturnValidationError, match="selected_value_conflict"):
        validate_uniprot_selected_values(value, selection=selected)


@pytest.mark.parametrize("state,code", [("absent", "field_absent"), ("null", "field_null"), ("invalid", "text_pointer_not_string")])
def test_unavailable_native_text_keeps_typed_partial_state(state, code):
    request = {"kind": "text", "field": "entry_type", "pointer": "/entryType", "offset": 0, "limit": 20}
    window = text_window("", RP + "/entryType", 0, 20)
    window.update(native_state=state, text=None, native_length=None, start=None, end=None,
                  omitted_prefix=None, omitted_suffix=None, extent="unavailable")
    cell = reply(request, window, status="partial", failures=[failure(code, RP + "/entryType")])
    validate_uniprot_selected_values(returned([cell]), selection=selection([request]))
    cell["status"] = "available"
    with pytest.raises(UniProtReturnValidationError):
        validate_uniprot_selected_values(returned([cell]), selection=selection([request]))


def test_sequence_window_and_reported_length_conflict_preserve_different_meanings():
    request = {"kind": "sequence_window", "start": 9, "end": 19}
    window = {"start": 9, "end": 19, "sequence_length": 318, "sequence_sha256": DIGEST,
        "value": "ACDEFGHIKL", "coordinates": "zero_based_half_open", "unit": "aa",
        "reported_length_state": "present", "reported_length": 317, "length_relation": "conflict"}
    cell = reply(request, window)
    validate_uniprot_selected_values(returned([cell]), selection=selection([request]))
    for key, wrong in (("end", 20), ("sequence_length", 18), ("length_relation", "agree"), ("value", "ACDEFGHIK")):
        bad = deepcopy(cell)
        bad["value"][key] = wrong
        with pytest.raises(UniProtReturnValidationError):
            validate_uniprot_selected_values(returned([bad]), selection=selection([request]))


@pytest.mark.parametrize("bad", [True, 1.0])
def test_integer_values_keep_exact_json_integer_type_at_report_boundary(bad):
    request = {"kind": "integer", "field": "taxon_id"}
    cell = reply(request, {"native_state": "present", "value": bad, "pointer": RP + "/organism/taxonId", "origin": "native", "unit": "taxon_id"})
    schema = form({"chosen": uniprot_selected_return_schema(selection([request]))})
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"chosen": returned([cell])}, schema)
    assert caught.value.diagnostic["code"] == "uniprot_selected_value_conflict"
    assert caught.value.diagnostic["field"].startswith("chosen.")


def test_owner_local_evidence_ordinals_and_pointer_tuple_cannot_be_reassigned():
    request = {"kind": "evidence", "selection": {"mode": "all_record"}}
    first = evidence_member(RP + "/features/0")
    second = evidence_member(RP + "/proteinDescription/recommendedName/fullName")
    cell = reply(request, collection([first, second]))
    selected = selection([request])
    validate_uniprot_selected_values(returned([cell]), selection=selected)
    for key, bad_value in (("owner_pointer", RP + "/features/1"), ("ordinal", 1), ("pointer", first["pointer"])):
        bad = deepcopy(cell)
        bad["value"]["members"][1]["value"][key] = bad_value
        with pytest.raises(UniProtReturnValidationError, match="selected_owner_conflict"):
            validate_uniprot_selected_values(returned([bad]), selection=selected)
    bad = deepcopy(cell)
    bad["value"]["members"][0]["value"]["eco"]["value"] = "ECO:269"
    with pytest.raises(UniProtReturnValidationError, match="selected_value_conflict"):
        validate_uniprot_selected_values(returned([bad]), selection=selected)


def test_collection_counts_and_explicit_ordinal_use_native_positions():
    request = {"kind": "feature_location", "selection": {"mode": "ordinal", "ordinal": 31},
               "include_evidence": False, "type_window": None, "description_window": None}
    cell = reply(request, collection([feature_member(31)], excluded=31))
    validate_uniprot_selected_values(returned([cell]), selection=selection([request]))
    cell["value"]["excluded_member_count"] = 30
    with pytest.raises(UniProtReturnValidationError):
        validate_uniprot_selected_values(returned([cell]), selection=selection([request]))


def test_overlap_selector_rejects_disjoint_other_sequence_and_invented_exact_interval():
    request = {"kind": "feature_location", "selection": {"mode": "entry_interval_overlap", "start": 9, "end": 20,
        "coordinates": "zero_based_half_open", "unit": "aa"}, "include_evidence": False, "type_window": None, "description_window": None}
    cell = reply(request, collection([feature_member()], excluded=2))
    selected = selection([request])
    validate_uniprot_selected_values(returned([cell]), selection=selected)
    for alteration in ("disjoint", "other", "fuzzy"):
        bad = deepcopy(cell)
        feature = bad["value"]["members"][0]["value"]
        if alteration == "disjoint":
            feature["start"]["value"], feature["end"]["value"] = 30, 40
            feature["exact_interval"] = [29, 40]
        elif alteration == "other":
            feature["sequence_binding"] = "explicit_other_sequence"
        else:
            feature["start"]["modifier"]["value"] = "UNSURE"
        with pytest.raises(UniProtReturnValidationError):
            validate_uniprot_selected_values(returned([bad]), selection=selected)


def test_go_database_property_windows_and_owned_descendant_evidence():
    request = {"kind": "cross_reference", "selection": {"mode": "database", "database": "GO"},
               "include_evidence": True, "properties": [{"key": "GoEvidenceType", "window": {"offset": 0, "limit": 80}}]}
    members = []
    for ordinal in (2, 31):
        pointer = RP + "/uniProtKBCrossReferences/" + str(ordinal)
        prop = pointer + "/properties/0"
        cell = {"ordinal": ordinal, "pointer": pointer, "database": token("GO", pointer + "/database"),
            "identifier": token("GO:0000001", pointer + "/id"), "properties_state": "present",
            "evidence": collection([evidence_member(prop)]),
            "properties": [{"request_index": 0, "request": deepcopy(request["properties"][0]), "native_state": "present",
                "matches": [{"ordinal": 0, "pointer": prop, "value": text_window("IEA:UniProtKB-KW", prop + "/value", 0, 80)}],
                "indeterminate_property_count": 0, "failures": []}]}
        members.append({"ordinal": ordinal, "pointer": pointer, "selection_state": "matched", "value": cell, "failures": []})
    field = reply(request, collection(members, excluded=30))
    selected = selection([request])
    validate_uniprot_selected_values(returned([field]), selection=selected)
    bad = deepcopy(field)
    bad["value"]["members"][0]["value"]["database"]["value"] = "Pfam"
    with pytest.raises(UniProtReturnValidationError):
        validate_uniprot_selected_values(returned([bad]), selection=selected)
    bad = deepcopy(field)
    evidence = bad["value"]["members"][0]["value"]["evidence"]["members"][0]
    evidence["value"]["owner_pointer"] = RP + "/uniProtKBCrossReferences/31"
    with pytest.raises(UniProtReturnValidationError, match="selected_owner_conflict"):
        validate_uniprot_selected_values(returned([bad]), selection=selected)


def test_count_relations_and_unavailable_records_are_not_empty_successes():
    selected = selection()
    original = returned()
    for key, bad in (("bound_record_count", 2), ("returned_bound_record_count", 0),
                     ("record_selection_count", 0), ("requested_record_count", 0), ("native_record_count", 0)):
        value = deepcopy(original)
        value["pages"][0]["status"][key] = bad
        with pytest.raises(UniProtReturnValidationError):
            validate_uniprot_selected_values(value, selection=selected)
    value = returned()
    page = value["pages"][0]
    page["records"][0].update(state="binding_omitted", witness=None,
                             failures=[failure("record_binding_omitted", RP, fi=None)])
    page["status"].update(bound_record_count=0, returned_bound_record_count=0, outer_acquisition_status="partial")
    validate_uniprot_selected_values(value, selection=selected)
    assert page["status"]["parser_eligible_record_count"] == 1
    assert page["status"]["parser_projection_state"] == "complete"


def test_unrequested_witnesses_do_not_resolve_and_explicit_grants_do():
    selected = selection()
    schema = form({"parent_name": uniprot_selected_return_schema(selected)})
    value = returned()
    calls = []
    assert validate_form({"parent_name": value}, schema, lambda *args: calls.append(args) or False)
    assert calls == []
    selected = selection(source_grant=True, sequence_grant=True)
    schema = form({"parent_name": uniprot_selected_return_schema(selected)})
    page = value["pages"][0]
    page.update(source_grant_status="available", source_grant={"source_ref": "source_ab", "native_artifact_id": "artifact_ab",
                "content_sha256": DIGEST, "meaning": "explicit_whole_native_source"})
    page["records"][0].update(sequence_grant_status="available", sequence_grant={"artifact_ref": "artifact_bc",
        "record_id": "reference_ab", "record_ordinal": 0, "sequence_sha256": DIGEST, "length": 318,
        "unit": "aa", "molecule": "protein", "meaning": "explicit_full_sequence_artifact"})
    calls.clear()
    validate_form({"parent_name": value}, schema, lambda *args: calls.append(args) or True)
    assert set(calls) == {("source_ab", "source"), ("artifact_bc", "artifact")}
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"parent_name": value}, schema, lambda *_: False)
    assert caught.value.diagnostic["code"] == "unknown_reference"
    page["source_grant"]["source_ref"] = "source_cd"
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"parent_name": value}, schema, lambda *_: True)
    assert caught.value.diagnostic["code"] == "uniprot_selected_owner_conflict"


def test_unrelated_sources_prose_rules_and_explicit_reference_fields_keep_their_meaning():
    selected = selection()
    schema = form({"chosen": uniprot_selected_return_schema(selected), "score": {"type": "number", "x-source": "credit"},
                   "deliberate": {"type": "string", "format": "reference", "x-reference-namespace": "source"}})
    assert set(interpretation_schema(schema)["properties"]) == {"deliberate"}
    value = form_with_facts({"deliberate": "source_ab"}, schema, {SOURCE: returned(), "credit": 1.25})
    calls = []
    validate_form(value, schema, lambda *args: calls.append(args) or True)
    assert calls == [("source_ab", "source")]
    assert requested_uniprot_selection(form({"score": {"type": "number", "x-source": "credit"}})) is None
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(form({"free_prose": {"type": "string"}}))
    assert caught.value.diagnostic["code"] == "unrestricted_string"


def test_empty_selection_and_distinct_top_level_acquisition_failures():
    empty = {"version": "uniprot_return_selection_v1", "pages": []}
    value = {"version": "uniprot_selected_returns_v1", "pages": [], "failures": []}
    validate_uniprot_selected_values(value, selection=empty)
    for code in ("not_acquired", "publication_unavailable", "publication_not_received"):
        value["failures"] = [failure(code, ri=None, fi=None)]
        validate_uniprot_selected_values(value, selection=selection())
    with pytest.raises(UniProtReturnValidationError):
        validate_uniprot_selected_values({"version": "uniprot_selected_returns_v1", "pages": [], "failures": []}, selection=selection())


@pytest.mark.parametrize("where", ["accession", "database", "source_id", "digest"])
def test_typed_selection_tokens_require_the_complete_pattern(where):
    selected = selection()
    page = selected["pages"][0]
    if where == "accession":
        page["records"][0]["record"] = {"mode": "primary_accession", "accession": "P12345\n"}
    elif where == "database":
        page["records"][0]["fields"] = [{"kind": "cross_reference", "selection": {"mode": "database", "database": "GO\n"},
            "include_evidence": False, "properties": []}]
    else:
        page["publication"] = {"mode": "received_publication", "source_id": "source_ab", "publication_sha256": DIGEST}
        page["publication"]["source_id" if where == "source_id" else "publication_sha256"] += "\n"
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selection_invalid"):
        validate_uniprot_return_selection(selected)


@pytest.mark.parametrize("where", ["record_id", "digest", "native_token"])
def test_return_tokens_and_witness_ids_reject_trailing_newlines(where):
    request = {"kind": "token", "field": "primary_accession", "array_ordinal": None}
    value = returned([reply(request, token("P12345", RP + "/primaryAccession"))])
    page = value["pages"][0]
    if where == "record_id":
        page["records"][0]["witness"]["record_id"] += "\n"
    elif where == "digest":
        page["witness"]["content_sha256"] += "\n"
    else:
        page["records"][0]["fields"][0]["value"]["value"] += "\n"
    with pytest.raises(UniProtReturnValidationError, match="uniprot_selected_value_conflict"):
        validate_uniprot_selected_values(value, selection=selection([request]))


def test_explicit_native_text_still_accepts_newlines_as_selected_characters():
    request = {"kind": "text", "field": "native_text", "pointer": "/native~1text", "offset": 0, "limit": 40}
    cell = reply(request, text_window("source paragraph\n", RP + request["pointer"], 0, 40))
    validate_uniprot_selected_values(returned([cell]), selection=selection([request]))


@pytest.mark.parametrize("kind", ["feature_location", "cross_reference", "evidence"])
@pytest.mark.parametrize("count,ordinal", [(3, 2), (3, 3), (0, 0)])
def test_present_collection_ordinal_cannot_return_a_false_empty_success(kind, count, ordinal):
    selected_member = {"mode": "ordinal", "ordinal": ordinal}
    request = {"kind": kind, "selection": selected_member}
    if kind == "feature_location":
        request.update(include_evidence=False, type_window=None, description_window=None)
    elif kind == "cross_reference":
        request.update(include_evidence=False, properties=[])
    else:
        selected_member.update(mode="owner_ordinal", owner_pointer="")
    cell = reply(request, collection(excluded=count))
    selected = selection([request])
    with pytest.raises(UniProtReturnValidationError):
        validate_uniprot_selected_values(returned([cell]), selection=selected)
    if ordinal >= count:
        cell.update(status="partial", failures=[failure("selected_ordinal_unavailable")])
        validate_uniprot_selected_values(returned([cell]), selection=selected)


def test_ordinal_evidence_membership_is_known_even_when_selected_data_is_partial():
    request = {"kind": "evidence", "selection": {"mode": "owner_ordinal", "owner_pointer": "", "ordinal": 0}}
    member = evidence_member(RP)
    member["selection_state"] = "indeterminate"
    cell = reply(request, collection([member]), status="partial")
    with pytest.raises(UniProtReturnValidationError):
        validate_uniprot_selected_values(returned([cell]), selection=selection([request]))
