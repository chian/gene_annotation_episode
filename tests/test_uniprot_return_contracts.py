"""Exact grammar and internal relations only; these fixtures prove no custody."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema,
    validate_closed_schema, validate_form,
)
from gene_annotation_episode.episodic_workflow.root.library.uniprot_return_contracts import UniProtReturnValidationError, requested_uniprot_selection, uniprot_selected_return_schema, validate_uniprot_return_selection


SOURCE = "uniprot_selected_returns"
DIGEST = "a" * 64
RP = "/results/0"


def form(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def selection(fields=(), *, record=None, source_grant=False, sequence_grant=False):
    return {"version": "uniprot_return_selection_v1", "pages": [{
        "publication": {"mode": "assigned_page"}, "page_fields": [],
        "records": [{"record": record or {"mode": "ordinal", "ordinal": 0},
                     "fields": deepcopy(list(fields)), "grant_sequence_artifact": sequence_grant}],
        "grant_source": source_grant}]}


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


@pytest.mark.parametrize("bad", [True, 1.0])
def test_integer_values_keep_exact_json_integer_type_at_report_boundary(bad):
    request = {"kind": "integer", "field": "taxon_id"}
    cell = reply(request, {"native_state": "present", "value": bad, "pointer": RP + "/organism/taxonId", "origin": "native", "unit": "taxon_id"})
    schema = form({"chosen": uniprot_selected_return_schema(selection([request]))})
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"chosen": returned([cell])}, schema)
    assert caught.value.diagnostic["code"] == "uniprot_selected_value_conflict"
    assert caught.value.diagnostic["field"].startswith("chosen.")


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


