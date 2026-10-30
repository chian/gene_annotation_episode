"""Selected native UniProt facts; real retained record plus controlled cases.

These exercise pure projection, not provider acquisition or receipt admission.
Application imports and tests run only through the root's bounded runner.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import identity
from gene_annotation_episode.uniprot_native import parse_uniprot_native
from gene_annotation_episode.uniprot_publication import bind_uniprot_publication
from gene_annotation_episode.uniprot_return_contracts import validate_uniprot_selected_values
from gene_annotation_episode.uniprot_return_projection import project_uniprot_page


FIXTURES = Path(__file__).parent / "fixtures" / "uniprot_native"
MISSING = object()


def protein(accession="P12345", sequence="MACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN"):
    return {"primaryAccession": accession, "secondaryAccessions": ["Q99999"],
            "uniProtkbId": "CONTROLLED_ECOLI", "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "sequence": {"value": sequence, "length": len(sequence)},
            "entryAudit": {"entryVersion": 3, "sequenceVersion": 2},
            "organism": {"taxonId": 83333, "scientificName": "Escherichia coli"},
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Controlled protein name"}}}}


def evidence(code="ECO:0000269", source="PubMed", identifier="123"):
    return {"evidenceCode": code, "source": source, "id": identifier}


def feature(start=10, end=20, *, modifier="EXACT", sequence=MISSING):
    location = {"start": {"value": start, "modifier": modifier},
                "end": {"value": end, "modifier": "EXACT"}}
    if sequence is not MISSING:
        location["sequence"] = sequence
    return {"type": "Domain", "description": "Selected feature description",
            "location": location, "evidences": [evidence()]}


def xref(database="GO", identifier="GO:0003824", **extra):
    return {"database": database, "id": identifier, **extra}


def inputs(body, *, request=None, headers=None, omitted=()):
    """Use the existing parser and binding authority, never a replacement reader."""
    content = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
    if request is None:
        request = {"operation": "search", "query": "controlled", "size": 10}
    parsed = parse_uniprot_native(content, request=request, response_headers=headers)
    source = "source_" + "a" * 24
    references, sequences = {}, {}
    errors = [deepcopy(issue) for issue in parsed["issues"] if issue["effect"] != "qualification"]
    for row in parsed["records"]:
        ordinal = row["identity"]["record_ordinal"]
        if ordinal in omitted:
            errors.append({"code": "uniprot_legacy_reference_unrepresentable",
                "record_ordinal": ordinal, "pointer": row["identity"]["record_pointer"] + "/primaryAccession",
                "field": "legacy_publication", "effect": "record_unpublishable",
                "primary_accession": row["identity"]["primary_accession"]})
            continue
        sequence = row["sequence"]["value"]["value"]
        sequence_ref = None
        if sequence is not None:
            sequence_ref = "artifact_" + hashlib.sha256(sequence.encode("ascii")).hexdigest()
            sequences[sequence_ref] = sequence.encode("ascii")
        record = {"reference_type": "protein", "molecule": "protein", "source_ref": source,
                  "accession": row["identity"]["primary_accession"], "label": "Controlled fixture",
                  "sequence_ref": sequence_ref, "length": row["sequence"]["observed_length_aa"],
                  "term_refs": [], "context_refs": []}
        references[ordinal] = {"id": identity("reference", {"origin": "external", "record": record}),
                               "record_type": "reference", "origin": "external", **record}
    publication = bind_uniprot_publication(parsed, source_ref=source,
        native_artifact_ref="artifact_" + parsed["content_sha256"], references_by_ordinal=references)
    return {"publication": publication, "native_content": content,
            "outer_status": "partial" if errors else "completed", "bound_record_count": len(references),
            "projection_errors": errors, "projection_qualifications": [], "sequence_contents": sequences}


def record_selection(fields=(), *, selector=None, grant=False):
    return {"record": selector or {"mode": "ordinal", "ordinal": 0},
            "fields": list(fields), "grant_sequence_artifact": grant}


def page_selection(*records, page_fields=(), grant=False):
    return {"publication": {"mode": "assigned_page"}, "records": list(records),
            "page_fields": list(page_fields), "grant_source": grant}


def projected(source, selected, *, index=0, validate=True):
    before_source, before_selection = deepcopy(source), deepcopy(selected)
    result = project_uniprot_page(**source, page_selection=selected, page_selection_index=index)
    assert source == before_source and selected == before_selection
    if validate:
        assert index == 0
        validate_uniprot_selected_values(
            {"version": "uniprot_selected_returns_v1", "pages": [result], "failures": []},
            selection={"version": "uniprot_return_selection_v1", "pages": [selected]})
    return result


def text_request(pointer="/proteinDescription/recommendedName/fullName/value", *, field="protein_name",
                 offset=0, limit=40):
    return {"kind": "text", "field": field, "pointer": pointer, "offset": offset, "limit": limit}


def feature_request(selector=None, *, evidence=False, type_window=None, description_window=None):
    return {"kind": "feature_location", "selection": selector or {"mode": "all"},
            "include_evidence": evidence, "type_window": type_window, "description_window": description_window}


def xref_request(selector=None, *, evidence=False, properties=()):
    return {"kind": "cross_reference", "selection": selector or {"mode": "all"},
            "include_evidence": evidence, "properties": list(properties)}


def overlap(start=9, end=20):
    return {"mode": "entry_interval_overlap", "start": start, "end": end,
            "coordinates": "zero_based_half_open", "unit": "aa"}


def codes(failures):
    return [failure["code"] for failure in failures]


def field_value(result, index=0):
    return result["records"][0]["fields"][index]["value"]


def test_authentic_p0aaw1_selected_go_positions_and_sequence_without_reparse(monkeypatch):
    raw = (FIXTURES / "P0AAW1.json").read_bytes()
    original = json.loads(raw)
    source = inputs(raw, request={"operation": "record", "accession": "P0AAW1"})
    fields = [{"kind": "integer", "field": "observed_sequence_length"},
              {"kind": "integer", "field": "taxon_id"},
              {"kind": "token", "field": "secondary_accession", "array_ordinal": 0},
              text_request(offset=0, limit=16),
              xref_request({"mode": "database", "database": "GO"}, evidence=True,
                properties=[{"key": "GoEvidenceType", "window": {"offset": 0, "limit": 80}}]),
              feature_request(overlap(), type_window={"offset": 0, "limit": 40}),
              {"kind": "sequence_window", "start": 9, "end": 19}]
    monkeypatch.setattr("gene_annotation_episode.uniprot_native.parse_uniprot_native",
                        lambda *args, **kwargs: pytest.fail("projection reran native parser"))
    result = projected(source, page_selection(record_selection(fields)))
    assert field_value(result)["value"] == 253
    assert field_value(result, 1)["value"] == 83333
    assert field_value(result, 2)["value"] == "P75772"
    assert field_value(result, 3)["text"] == "Uncharacterized "
    go = field_value(result, 4)
    assert (go["native_member_count"], go["matching_member_count"], go["excluded_member_count"]) == (42, 2, 40)
    assert [member["ordinal"] for member in go["members"]] == [31, 32]
    first = go["members"][0]["value"]
    assert first["database"]["value"] == "GO" and first["identifier"]["value"] == "GO:0005886"
    assert first["properties"][0]["matches"][0]["value"]["text"] == "HDA:EcoCyc"
    eco = first["evidence"]["members"][0]["value"]
    assert (eco["owner_pointer"], eco["ordinal"], eco["eco"]["value"], eco["source_identifier"]["value"]) == (
        "/uniProtKBCrossReferences/31", 0, "ECO:0007005", "32127419")
    assert field_value(result, 5)["members"][0]["value"]["exact_interval"] == [0, 253]
    assert field_value(result, 6)["value"] == original["sequence"]["value"][9:19]
    assert result["source_grant_status"] == "not_requested"
    assert result["records"][0]["sequence_grant"] is None
    serialized = json.dumps(result)
    assert original["sequence"]["value"] not in serialized
    assert "uniprot_publication" not in serialized


@pytest.mark.parametrize("value,offset,limit,expected,state,extent", [
    ("α🙂e\u0301" * 2500, 20, 40, ("α🙂e\u0301" * 2500)[20:60], "present", "window"),
    ("", 0, 40, "", "present", "empty_value"),
    ("small", 20, 40, "", "present", "offset_past_end"),
    ("small", 5, 40, "", "present", "window"),
    ("α🙂", 0, 40, "α🙂", "present", "whole_value"),
    (None, 0, 40, None, "null", "unavailable"),
    (7, 0, 40, None, "invalid", "unavailable"),
    (MISSING, 0, 40, None, "absent", "unavailable"),
])
def test_native_text_windows_preserve_unicode_extents_and_missing_states(value, offset, limit, expected, state, extent):
    row = protein()
    if value is MISSING:
        row["proteinDescription"]["recommendedName"]["fullName"].pop("value")
    else:
        row["proteinDescription"]["recommendedName"]["fullName"]["value"] = value
    row["comments"] = [{"texts": [{"value": "UNREQUESTED NEIGHBOR"}]}]
    request = text_request(offset=offset, limit=limit)
    result = projected(inputs({"results": [row]}), page_selection(record_selection([request])))
    window = field_value(result)
    assert (window["text"], window["native_state"], window["extent"]) == (expected, state, extent)
    assert window["pointer"] == "/results/0/proteinDescription/recommendedName/fullName/value"
    if state == "present":
        assert window["native_length"] == len(value)
        assert window["omitted_prefix"] == min(offset, len(value))
        assert window["omitted_suffix"] == len(value) - min(offset + limit, len(value))
    else:
        assert window["native_length"] is window["start"] is window["end"] is None
    assert "UNREQUESTED NEIGHBOR" not in json.dumps(result)


def test_all_native_and_overlapping_record_selectors_preserve_ordinals_and_binding_omissions():
    rows = [protein(), [], protein("P12345"), protein("identifier with spaces"), {"sequence": {}}]
    source = inputs({"results": rows}, omitted=(3,))
    fields = [{"kind": "integer", "field": "taxon_id"}]
    selected = page_selection(
        record_selection(fields, selector={"mode": "all_native_records"}),
        record_selection(fields, selector={"mode": "primary_accession", "accession": "P12345"}),
        record_selection(fields, selector={"mode": "ordinal", "ordinal": 12}))
    result = projected(source, selected)
    records = result["records"]
    assert [(r["record_selection_index"], r["requested_record_ordinal"]) for r in records] == [
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 0), (1, 1), (1, 2), (1, 4), (2, 12)]
    assert [r["state"] for r in records[:5]] == [
        "bound", "parser_unpublishable", "bound", "binding_omitted", "parser_unpublishable"]
    assert records[5]["witness"] == records[0]["witness"]
    assert records[6]["state"] == records[8]["state"] == "unavailable"
    assert codes(records[6]["failures"]) == ["record_selection_indeterminate"]
    assert records[-1]["state"] == "not_in_response"
    status = result["status"]
    assert (status["native_record_count"], status["parser_eligible_record_count"], status["bound_record_count"]) == (5, 3, 2)
    assert (status["record_selection_count"], status["requested_record_count"],
            status["returned_bound_record_count"], status["indeterminate_record_count"]) == (3, 6, 2, 2)
    assert all(cell["status"] == "unavailable" for r in records if r["state"] != "bound" for cell in r["fields"])


def test_primary_selection_does_not_match_secondary_and_negative_requires_decidable_rows():
    row = protein()
    selected = page_selection(record_selection(selector={"mode": "primary_accession", "accession": "Q99999"}))
    negative = projected(inputs({"results": [row]}), selected)
    assert negative["records"] == [] and codes(negative["failures"]) == ["record_selection_no_match"]
    uncertain = projected(inputs({"results": [row, None]}), selected)
    assert uncertain["failures"] == []
    assert uncertain["records"][0]["requested_record_ordinal"] == 1
    assert codes(uncertain["records"][0]["failures"]) == ["record_selection_indeterminate"]


def test_out_of_response_record_endpoint_ordinal_has_no_fabricated_native_locator():
    source = inputs(protein(), request={"operation": "record", "accession": "P12345"})
    selected = page_selection(record_selection([{"kind": "integer", "field": "taxon_id"}],
        selector={"mode": "ordinal", "ordinal": 3}, grant=True))
    result = projected(source, selected)
    record, = result["records"]
    assert record["state"] == "not_in_response" and record["requested_record_ordinal"] == 3
    assert record["witness"] is None and record["sequence_grant"] is None
    assert record["failures"][0]["native_pointer"] is None
    assert record["fields"][0]["failures"][0]["native_pointer"] is None


def test_parser_complete_outer_partial_and_exact_original_issue_origins():
    source = inputs({"results": [protein(), protein("identifier with spaces"), protein("Q12345")]},
                    omitted=(1,), headers={"x-uniprot-release": "native release with spaces"})
    source["projection_errors"].append({"code": "uniprot_legacy_label_unrepresentable", "record_ordinal": 0,
        "pointer": "/results/0/proteinDescription/recommendedName/fullName/value",
        "field": "legacy_publication", "effect": "field_partial", "message": "never returned"})
    source["projection_qualifications"] = [{"code": "uniprot_legacy_source_version_omitted",
        "record_ordinal": None, "pointer": "/headers/x-uniprot-release", "field": "legacy_source",
        "effect": "qualification", "raw": "never returned"}]
    result = projected(source, page_selection(record_selection([text_request()]), page_fields=[
        {"kind": "page_text", "field": "release", "offset": 0, "limit": 100}]))
    assert result["status"]["parser_projection_state"] == "complete"
    assert result["status"]["outer_acquisition_status"] == "partial"
    assert result["status"]["unselected_issue_count"] == 1
    assert result["page_fields"][0]["status"] == "available"
    assert result["records"][0]["fields"][0]["status"] == "available"
    assert result["issues"][-1]["origin"] == "publication_qualification"
    assert result["issues"][-1]["original_issue_index"] == 0
    assert result["records"][0]["issues"][-1]["original_issue_index"] == 1
    assert "never returned" not in json.dumps(result)


def test_go_database_selector_properties_and_indeterminate_native_members():
    row = protein()
    row["uniProtKBCrossReferences"] = [xref("InterPro", "IPR000001"), False,
        xref(properties=[{"key": "GoEvidenceType", "value": "HDA:🙂source"},
                         {"key": "Unrequested", "value": "secret"}, None,
                         {"value": "unknown key"}, {"key": "GoEvidenceType", "value": "IEA:InterPro"}],
             evidences=[evidence()]),
        {"id": "unknown-database"}, xref("PDB", "1ABC"),
        xref(identifier="GO:0005886", properties=[])]
    request = xref_request({"mode": "database", "database": "GO"}, evidence=True,
                          properties=[{"key": "GoEvidenceType", "window": {"offset": 4, "limit": 4}}])
    result = projected(inputs({"results": [row]}), page_selection(record_selection([request])))
    collection = field_value(result)
    assert [collection[key] for key in ("native_member_count", "matching_member_count",
        "indeterminate_member_count", "unavailable_member_count", "excluded_member_count")] == [6, 2, 2, 0, 2]
    assert [(r["ordinal"], r["selection_state"]) for r in collection["members"]] == [
        (1, "indeterminate"), (2, "matched"), (3, "indeterminate"), (5, "matched")]
    properties = collection["members"][1]["value"]["properties"][0]
    assert properties["indeterminate_property_count"] == 2
    assert [(r["ordinal"], r["value"]["text"]) for r in properties["matches"]] == [(0, "🙂sou"), (4, "Inte")]
    assert "secret" not in json.dumps(result) and "unknown key" not in json.dumps(result)
    assert codes(collection["members"][-1]["value"]["properties"][0]["failures"]) == ["property_not_found"]
    assert result["records"][0]["fields"][0]["status"] == "partial"


def test_feature_overlap_preserves_exact_fuzzy_other_sequence_and_malformed_members():
    row = protein()
    row["features"] = [feature(), feature(1, 9), feature(21, 25), feature(10, 20, modifier="BEFORE"),
                       feature(10, 20, sequence="P12345-2"), feature(10, 20, sequence=None),
                       None, feature(30, 70), {"type": "Unknown location"}]
    request = feature_request(overlap(), evidence=True, type_window={"offset": 1, "limit": 3},
                              description_window={"offset": 9, "limit": 7})
    result = projected(inputs({"results": [row]}), page_selection(record_selection([request])))
    collection = field_value(result)
    assert [collection[key] for key in ("native_member_count", "matching_member_count",
        "indeterminate_member_count", "unavailable_member_count", "excluded_member_count")] == [9, 1, 5, 0, 3]
    assert [r["ordinal"] for r in collection["members"]] == [0, 3, 5, 6, 7, 8]
    exact = collection["members"][0]["value"]
    assert exact["exact_interval"] == [9, 20]
    assert exact["start"]["value"] == 10 and exact["native_coordinates"] == "one_based_inclusive"
    assert exact["type_window"]["text"] == "oma"
    assert exact["description_window"]["text"] == "feature"
    for member in collection["members"][1:]:
        if member["value"] is not None:
            assert member["value"]["exact_interval"] is None


@pytest.mark.parametrize("family,native_name,selected_field", [
    ("feature", "features", feature_request()),
    ("xref", "uniProtKBCrossReferences", xref_request()),
    ("evidence", "evidences", {"kind": "evidence", "selection": {"mode": "all_at_owner", "owner_pointer": ""}}),
])
@pytest.mark.parametrize("native,state,count", [(MISSING, "absent", 0), (None, "null", None),
                                                (3, "invalid", None), ([], "present", 0)])
def test_collection_absent_null_invalid_empty_remain_distinct(family, native_name, selected_field, native, state, count):
    row = protein()
    if native is not MISSING:
        row[native_name] = native
    result = projected(inputs({"results": [row]}), page_selection(record_selection([selected_field])))
    reply = result["records"][0]["fields"][0]
    assert (reply["value"]["native_state"], reply["value"]["native_member_count"], reply["value"]["members"]) == (state, count, [])
    assert reply["status"] == ("available" if state == "present" else "partial")
    assert codes(reply["failures"]) == ([] if state == "present" else ["field_" + state])


@pytest.mark.parametrize("kind,native,selected_field", [
    ("feature_location", "features", feature_request({"mode": "ordinal", "ordinal": 2})),
    ("cross_reference", "uniProtKBCrossReferences", xref_request({"mode": "ordinal", "ordinal": 2})),
    ("evidence", "evidences", {"kind": "evidence", "selection": {"mode": "owner_ordinal", "owner_pointer": "", "ordinal": 2}}),
])
def test_original_ordinal_outside_present_collection_invents_no_member(kind, native, selected_field):
    row = protein()
    row[native] = [None]
    result = projected(inputs({"results": [row]}), page_selection(record_selection([selected_field])))
    reply = result["records"][0]["fields"][0]
    assert reply["value"]["members"] == []
    assert reply["value"]["excluded_member_count"] == 1
    assert codes(reply["failures"]) == ["selected_ordinal_unavailable"]


def test_owner_local_evidence_zero_ordinals_remain_distinct_and_nested_owners_are_not_promoted():
    row = protein()
    row["proteinDescription"]["recommendedName"]["fullName"]["evidences"] = [evidence(identifier="name")]
    row["proteinDescription"]["recommendedName"]["ecNumbers"] = [
        {"value": "1.2.3.4", "evidences": [evidence(identifier="ec")]}]
    row["features"] = [feature()]
    row["features"][0]["location"]["start"]["evidences"] = [evidence(identifier="start"), None]
    row["uniProtKBCrossReferences"] = [xref(evidences=[evidence(identifier="xref")], properties=[
        {"key": "GoTerm", "value": "source term", "evidences": [evidence(identifier="property")]}])]
    owners = ["/proteinDescription/recommendedName/fullName", "/proteinDescription/recommendedName/ecNumbers/0"]
    fields = [{"kind": "evidence", "selection": {"mode": "owner_ordinal", "owner_pointer": owner, "ordinal": 0}}
              for owner in owners]
    fields += [feature_request(evidence=True), xref_request(evidence=True),
               {"kind": "evidence", "selection": {"mode": "all_record"}}]
    result = projected(inputs({"results": [row]}), page_selection(record_selection(fields)))
    first, second = [field_value(result, i)["members"][0]["value"] for i in (0, 1)]
    assert first["ordinal"] == second["ordinal"] == 0
    assert [first["source_identifier"]["value"], second["source_identifier"]["value"]] == ["name", "ec"]
    assert [first["owner_pointer"], second["owner_pointer"]] == ["/results/0" + owner for owner in owners]
    feature_evidence = field_value(result, 2)["members"][0]["value"]["evidence"]
    assert [(r["ordinal"], r["pointer"]) for r in feature_evidence["members"]] == [
        (0, "/results/0/features/0/evidences/0"),
        (0, "/results/0/features/0/location/start/evidences/0"),
        (1, "/results/0/features/0/location/start/evidences/1")]
    assert feature_evidence["unavailable_member_count"] == 1
    xref_evidence = field_value(result, 3)["members"][0]["value"]["evidence"]
    assert [r["value"]["owner_pointer"] for r in xref_evidence["members"]] == [
        "/results/0/uniProtKBCrossReferences/0", "/results/0/uniProtKBCrossReferences/0/properties/0"]
    all_evidence = field_value(result, 4)
    assert all_evidence["native_member_count"] == 7 and all_evidence["matching_member_count"] == 6
    assert [r["value"]["source_identifier"]["value"] for r in all_evidence["members"] if r["value"]] == [
        "name", "ec", "123", "start", "xref", "property"]


@pytest.mark.parametrize("malformed", [None, "invalid container"])
def test_all_record_evidence_retains_valid_arrays_when_another_container_has_unknown_size(malformed):
    row = protein()
    row["evidences"] = [evidence()]
    row["comments"] = [{"texts": [{"value": "not selected", "evidences": malformed}]}]
    selected = page_selection(record_selection([{"kind": "evidence", "selection": {"mode": "all_record"}}]))
    result = projected(inputs({"results": [row]}), selected)
    value = field_value(result)
    assert value["native_state"] == "present"
    assert value["native_member_count"] is None and value["matching_member_count"] == 1
    assert value["members"][0]["value"]["owner_pointer"] == "/results/0"
    assert result["records"][0]["fields"][0]["status"] == "partial"


def test_ec_component_and_alternative_name_scope_are_exact_native_assignments():
    row = protein()
    row["proteinDescription"] = {
        "recommendedName": {"fullName": {"value": "entry name"}, "ecNumbers": [{"value": "1.2.3.4"}]},
        "alternativeNames": [{"fullName": {"value": "alternative"}, "ecNumbers": [{"value": "2.3.4.-"}]}],
        "contains": [{"recommendedName": {"ecNumbers": [{"value": "3.4.n2.-"}]}}],
        "includes": [{"alternativeNames": [{"ecNumbers": [{"value": "invalid EC"}]}]}]}
    paths = ["/proteinDescription/recommendedName/ecNumbers/0/value",
             "/proteinDescription/alternativeNames/0/ecNumbers/0/value",
             "/proteinDescription/contains/0/recommendedName/ecNumbers/0/value",
             "/proteinDescription/includes/0/alternativeNames/0/ecNumbers/0/value"]
    result = projected(inputs({"results": [row]}), page_selection(record_selection([
        {"kind": "ec_assignment", "pointer": path} for path in paths])))
    assert [field_value(result, i)["scope"] for i in range(4)] == ["entry", "entry", "component", "component"]
    assert field_value(result, 2)["component_pointer"] == "/results/0/proteinDescription/contains/0"
    assert field_value(result, 2)["name_group_pointer"] == "/results/0/proteinDescription/contains/0/recommendedName"
    assert field_value(result, 2)["owner_pointer"].endswith("/ecNumbers/0")
    assert field_value(result, 2)["ec"]["value"] == "3.4.n2.-"
    assert field_value(result, 3)["ec"]["native_state"] == "present"
    assert field_value(result, 3)["ec"]["representation"] == "unavailable"
    assert codes(result["records"][0]["fields"][3]["failures"]) == ["token_not_representable"]


def test_secondary_accession_native_positions_survive_invalid_sibling_and_token_representation():
    row = protein()
    row["secondaryAccessions"] = ["Q12345", None, "token with spaces", 7, "P54321"]
    fields = [{"kind": "token", "field": "secondary_accession", "array_ordinal": i} for i in range(6)]
    fields.append(text_request("/secondaryAccessions/2", field="native_text", offset=6, limit=4))
    result = projected(inputs({"results": [row]}), page_selection(record_selection(fields)))
    assert [field_value(result, i)["native_state"] for i in range(6)] == [
        "present", "null", "present", "invalid", "present", "absent"]
    assert [field_value(result, i)["value"] for i in (0, 4)] == ["Q12345", "P54321"]
    assert field_value(result, 2)["representation"] == "unavailable"
    assert field_value(result, 4)["pointer"] == "/results/0/secondaryAccessions/4"
    assert field_value(result, 6)["text"] == "with"


def test_integer_fields_and_sequence_window_copy_publication_measurements_without_rescaling():
    sequence = "MACDEFGHIK" * 31 + "LMNPQRST"
    assert len(sequence) == 318
    row = protein(sequence=sequence)
    row["sequence"]["length"] = 317
    fields = [{"kind": "integer", "field": field} for field in (
        "taxon_id", "entry_version", "sequence_version", "reported_sequence_length", "observed_sequence_length")]
    fields.append({"kind": "sequence_window", "start": 9, "end": 19})
    result = projected(inputs({"results": [row]}), page_selection(record_selection(fields)))
    assert [field_value(result, i)["value"] for i in range(5)] == [83333, 3, 2, 317, 318]
    observed = field_value(result, 4)
    assert (observed["unit"], observed["origin"], observed["pointer"]) == ("aa", "derived", "/results/0/sequence/value")
    window = field_value(result, 5)
    assert window["value"] == sequence[9:19] and len(window["value"]) == 10
    assert window["sequence_length"] == 318 and window["reported_length"] == 317
    assert window["length_relation"] == "conflict"
    assert result["records"][0]["fields"][5]["status"] == "available"


@pytest.mark.parametrize("sequence", [MISSING, None, {"value": "M?"}, {"value": ""}])
def test_missing_or_invalid_sequence_gives_no_window_overlap_or_artifact(sequence):
    row = protein()
    if sequence is MISSING:
        row.pop("sequence")
    else:
        row["sequence"] = sequence
    row["features"] = [feature()]
    selected = page_selection(record_selection([
        {"kind": "sequence_window", "start": 0, "end": 1}, feature_request(overlap())], grant=True))
    result = projected(inputs({"results": [row]}), selected)
    record = result["records"][0]
    assert [f["status"] for f in record["fields"]] == ["unavailable", "unavailable"]
    assert all(codes(f["failures"]) == ["sequence_unavailable"] for f in record["fields"])
    assert record["sequence_grant_status"] == "unavailable" and record["sequence_grant"] is None


def test_out_of_range_sequence_and_overlap_queries_are_unavailable_never_clipped():
    row = protein()
    row["features"] = [feature()]
    fields = [{"kind": "sequence_window", "start": 1, "end": 100}, feature_request(overlap(1, 100))]
    result = projected(inputs({"results": [row]}), page_selection(record_selection(fields)))
    for reply in result["records"][0]["fields"]:
        assert reply["status"] == "unavailable" and reply["value"] is None
        assert codes(reply["failures"]) == ["sequence_window_out_of_range"]


def test_explicit_grants_are_only_descriptors_and_missing_material_does_not_erase_metadata():
    row = protein()
    source = inputs({"results": [row]})
    selected = page_selection(record_selection([{"kind": "integer", "field": "taxon_id"}], grant=True), grant=True)
    result = projected(source, selected)
    source_grant, sequence_grant = result["source_grant"], result["records"][0]["sequence_grant"]
    assert source_grant["source_ref"] == result["witness"]["source_id"]
    assert source_grant["meaning"] == "explicit_whole_native_source"
    assert sequence_grant["artifact_ref"] == result["records"][0]["witness"]["sequence_artifact_id"]
    assert sequence_grant["length"] == len(row["sequence"]["value"])
    assert set(sequence_grant) == {"artifact_ref", "record_id", "record_ordinal", "sequence_sha256",
                                   "length", "unit", "molecule", "meaning"}
    assert "source_ref" not in sequence_grant and "reference_ref" not in sequence_grant
    source["sequence_contents"] = {}
    absent = projected(source, selected)
    assert absent["records"][0]["sequence_grant_status"] == "unavailable"
    assert absent["records"][0]["fields"][0]["status"] == "available"
    assert codes(absent["records"][0]["failures"]) == ["sequence_unavailable"]
    unrequested = projected(source, page_selection(record_selection([{"kind": "integer", "field": "taxon_id"}])))
    assert unrequested["source_grant"] is None and unrequested["records"][0]["sequence_grant"] is None


def test_exact_page_header_tokens_windows_query_and_unknown_next_are_distinct():
    cursor = "opaque+token/=part"
    url = "https://rest.uniprot.org/uniprotkb/search?cursor=" + cursor
    source = inputs({"results": []}, request={"operation": "search", "query": "gene:ybhP AND reviewed:true", "size": 1},
        headers={"x-total-results": "25", "x-uniprot-release": "release with spaces",
                 "x-uniprot-release-date": "2026-10-28", "link": "<" + url + ">; rel=\"next\""})
    # The native query parser decodes '+' to space, retaining that exact cursor.
    fields = [{"kind": "page_integer", "field": "total_results"},
              {"kind": "page_token", "field": "release"},
              {"kind": "page_text", "field": "release", "offset": 8, "limit": 4},
              {"kind": "page_text", "field": "next_cursor", "offset": 0, "limit": 100},
              {"kind": "page_token", "field": "next_url"},
              {"kind": "page_text", "field": "effective_query", "offset": 0, "limit": 10}]
    result = projected(source, page_selection(page_fields=fields))
    values = [cell["value"] for cell in result["page_fields"]]
    assert values[0]["value"] == 25
    assert values[1]["native_state"] == "present" and values[1]["representation"] == "unavailable"
    assert values[2]["text"] == "with"
    assert values[3]["text"] == "opaque token/=part"
    assert values[4]["value"] == url
    assert values[5]["text"] == "gene:ybhP " and values[5]["pointer"] == "/effective_request/query"
    unknown = projected(inputs({"results": []}), page_selection(page_fields=[
        {"kind": "page_token", "field": "next_cursor"}]))
    assert unknown["status"]["next_state"] == "unknown"
    assert unknown["page_fields"][0]["value"] is None
    assert codes(unknown["page_fields"][0]["failures"]) == ["page_field_unavailable"]


@pytest.mark.parametrize("headers,next_state", [({}, "absent"), ({"link": "malformed"}, "invalid")])
def test_absent_and_invalid_next_page_remain_distinct(headers, next_state):
    selected = page_selection(page_fields=[{"kind": "page_token", "field": "next_url"}])
    result = projected(inputs({"results": []}, headers=headers), selected)
    assert result["status"]["next_state"] == next_state
    cell = result["page_fields"][0]
    if next_state == "absent":
        assert cell["status"] == "partial" and cell["value"]["native_state"] == "absent"
    else:
        assert cell["status"] == "unavailable" and cell["value"] is None


@pytest.mark.parametrize("body,body_state,count", [(b"{broken", "invalid_json", None),
                                                   (b"[]", "invalid_envelope", None),
                                                   ({"results": []}, "complete_json", 0)])
def test_invalid_page_empty_response_and_explicit_empty_selection_are_not_equivalent(body, body_state, count):
    source = inputs(body)
    selected = page_selection(record_selection(selector={"mode": "all_native_records"}))
    result = projected(source, selected)
    assert result["status"]["response_body_state"] == body_state
    assert result["status"]["native_record_count"] == count and result["records"] == []
    assert codes(result["failures"]) == ([] if count == 0 else ["publication_unavailable"])
    empty = projected(source, page_selection())
    assert empty["status"]["record_selection_count"] == 0 and empty["failures"] == []


@pytest.mark.parametrize("tamper,code", [
    ("native_bytes", "uniprot_artifact_content_conflict"),
    ("count", "uniprot_binding_conflict"),
    ("source_binding", "uniprot_binding_conflict"),
    ("record_pointer", "uniprot_binding_conflict"),
    ("sequence_bytes", "uniprot_artifact_content_conflict"),
    ("sequence_artifact", "uniprot_binding_conflict"),
    ("evidence_owner", "uniprot_selected_owner_conflict"),
    ("evidence_ordinal", "uniprot_selected_owner_conflict"),
    ("evidence_source", "uniprot_selected_value_conflict"),
])
def test_conflicting_custody_or_selected_associations_raise_declared_integrity_errors(tamper, code):
    row = protein()
    row["evidences"] = [evidence()]
    source = inputs({"results": [row]})
    bound = source["publication"]["records"][0]
    if tamper == "native_bytes":
        source["native_content"] += b" "
    elif tamper == "count":
        source["bound_record_count"] += 1
    elif tamper == "source_binding":
        bound["anchor"]["source_ref"] = "source_" + "b" * 24
    elif tamper == "record_pointer":
        bound["anchor"]["record_pointer"] = "/results/1"
    elif tamper == "sequence_bytes":
        source["sequence_contents"][bound["sequence_ref"]] = b"INVALID"
    elif tamper == "sequence_artifact":
        bound["sequence_ref"] = "artifact_" + "b" * 64
    else:
        native_evidence = bound["record"]["evidence"]["items"][0]
        if tamper == "evidence_owner":
            native_evidence["owner_pointer"] = "/results/0/features/0"
        elif tamper == "evidence_ordinal":
            native_evidence["ordinal"] = 1
        else:
            native_evidence["source"]["value"] = "OtherSource"
    selected = page_selection(record_selection([
        {"kind": "sequence_window", "start": 0, "end": 1},
        {"kind": "evidence", "selection": {"mode": "owner_ordinal", "owner_pointer": "", "ordinal": 0}}]))
    with pytest.raises(ValueError, match="^" + code + "$"):
        projected(source, selected)


def test_publication_digest_and_original_page_selection_index_are_exact():
    source = inputs({"results": [protein()]})
    selected = page_selection(record_selection([text_request("/absent", field="native_text")]))
    result = projected(source, selected, index=7, validate=False)
    expected = hashlib.sha256(json.dumps(source["publication"], ensure_ascii=False, sort_keys=True,
                                        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert result["witness"]["publication_sha256"] == expected
    assert result["page_selection_index"] == 7
    assert result["records"][0]["fields"][0]["failures"][0]["page_selection_index"] == 7


def test_received_publication_selection_is_not_an_own_page_projection():
    selected = page_selection()
    selected["publication"] = {"mode": "received_publication", "source_id": "source_" + "a" * 24,
                               "publication_sha256": "b" * 64}
    with pytest.raises(ValueError, match="^uniprot_selection_mode_conflict$"):
        projected(inputs({"results": []}), selected)
