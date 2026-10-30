"""Supplied JSON contract checks; synthetic references prove no source custody."""
from copy import deepcopy
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.bvbrc_minhash_contracts import (
    minhash_result_selector_schema,
    validate_minhash_pair_metadata,
    validate_minhash_publication_inputs,
    validate_minhash_result_selector,
)


FIELDS = ("kmer_length", "query_length", "reference_length", "alphabet_size")
OPERANDS = ("query", "max_pvalue", "max_distance", "max_hits", "include_reference",
            "include_representative", "bacterial", "viral")
SOURCE = "source_" + "a" * 32
SAVED_SOURCE = "source_" + "e" * 32
ARTIFACT = "artifact_" + "b" * 64


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("contract validation must not acquire data or execute jobs")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def request(mode="genome"):
    return {"mode": mode, "query": "123.1" if mode == "genome" else "/owner/ws/input.fa",
            "max_pvalue": 1.0, "max_distance": 1.0, "max_hits": 10,
            "include_reference": 1, "include_representative": 1, "bacterial": 1, "viral": 0}


def metadata(index=0, genome="456.2", *, mode="genome", **values):
    record = {"row_index": index, "genome_id": genome, "kmer_length": 1,
              "query_length": 2, "reference_length": 2, "alphabet_size": 2, **values}
    record["provenance"] = {
        "kind": "explicit_retained_pair_inputs", "query_mode": mode,
        "query_operand": request(mode)["query"], "native_parameter_equivalence": "unestablished",
        "fields": [{"field": name, "source_ref": SOURCE, "artifact_ref": ARTIFACT,
                    "record_path": f"/pairs/{index}/{name}"}
                   for name in FIELDS if record[name] is not None],
    }
    return record


def selector(records=None, *, mode="native_result"):
    return {"version": "bvbrc_minhash_result_selector_v2", "mode": mode,
            "saved_result_ref": SAVED_SOURCE if mode == "saved_sheet" else None,
            "pair_metadata": deepcopy([] if records is None else records)}


def saved_result(service_request):
    # Empty common-sheet fixture: this is structure, not an acquired result.
    return {
        "source_ref": SAVED_SOURCE, "native_artifact_ref": "artifact_" + "c" * 64,
        "native_sha256": "c" * 64, "grading_artifact_ref": "artifact_" + "d" * 64,
        "grading_sha256": "d" * 64,
        "sheet": {"schema": "bvbrc_minhash_sheet_v1", "mode": service_request["mode"],
                  "request": {"version": "1.1", "id": "synthetic-original-rpc",
                              "method": f"Minhash.compute_genome_distance_for_{service_request['mode']}2",
                              "params": [service_request[name] for name in OPERANDS]},
                  "provenance": {"kind": "synthetic_saved_contract_fixture"},
                  "native_result": [], "rows": [],
                  "search_metadata": dict.fromkeys(("population_size", "reference_release", "truncated",
                                                     "kmer_length", "hash_seed", "sketch_size"))},
        "original_components": {"schema": "bvbrc_minhash_components_v1", "rows": [],
                                "diagnostics": [{"code": "empty_result_completeness_unknown",
                                                 "path": "native_result", "severity": "warning"}]},
    }


def publication(selected, *, service_request=None):
    records = selected["pair_metadata"]
    return {
        "version": "bvbrc_minhash_publication_inputs_v1", "selector": deepcopy(selected),
        "pair_metadata": deepcopy(records),
        "metadata_bindings": [
            {"pair_metadata_index": index, **deepcopy(item),
             "artifact_sha256": item["artifact_ref"].removeprefix("artifact_"),
             "value": record[item["field"]]}
            for index, record in enumerate(records) for item in record["provenance"]["fields"]],
        "saved_result": saved_result(request() if service_request is None else service_request)
                        if selected["mode"] == "saved_sheet" else None,
    }


def assert_error(code, function, *args, **kwargs):
    with pytest.raises(ValueError) as error:
        function(*args, **kwargs)
    assert str(error.value) == code


def test_legacy_selector_and_empty_v2_are_preserved():
    legacy = {}
    actual = validate_minhash_result_selector(legacy)
    assert actual == legacy and actual is not legacy
    for mode in ("native_result", "saved_sheet"):
        selected = selector(mode=mode)
        assert validate_minhash_result_selector(selected) == selected


@pytest.mark.parametrize("mode", ["genome", "fasta"])
@pytest.mark.parametrize("values", [{}, dict.fromkeys(FIELDS),
                                    {"query_length": None, "reference_length": None, "alphabet_size": None}])
def test_full_null_and_k_only_inputs_preserve_explicit_values(mode, values):
    supplied = [metadata(mode=mode, **values)]
    frozen = deepcopy(supplied)
    validated = validate_minhash_pair_metadata(supplied, request=request(mode))
    assert validated == frozen == supplied
    assert validated is not supplied and validated[0] is not supplied[0]
    validated[0]["provenance"]["fields"].clear()
    assert supplied == frozen
    selected = selector(supplied)
    assert validate_minhash_result_selector(selected) == selected
    inputs = publication(selected)
    assert validate_minhash_publication_inputs(inputs, request=request(mode), selector=selected) == inputs


def test_duplicate_candidates_and_unmatched_row_keys_are_never_filtered():
    records = [metadata(9, "999.9"), metadata(0, "456.2"), metadata(0, "456.2")]
    records[0]["provenance"]["fields"].reverse()
    assert validate_minhash_pair_metadata(records, request=request()) == records
    selected = selector(records)
    assert validate_minhash_result_selector(selected)["pair_metadata"] == records
    inputs = publication(selected)
    inputs["metadata_bindings"].reverse()
    result = validate_minhash_publication_inputs(inputs, request=request(), selector=selected)
    assert result == inputs
    assert [item["row_index"] for item in result["pair_metadata"]] == [9, 0, 0]
    assert {item["pair_metadata_index"] for item in result["metadata_bindings"]} == {0, 1, 2}
    result["selector"]["pair_metadata"][0]["kmer_length"] = 5
    result["pair_metadata"][1]["provenance"]["fields"][0]["record_path"] = "/changed"
    result["metadata_bindings"].clear()
    assert selected["pair_metadata"] == records
    assert len(inputs["metadata_bindings"]) == 12


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [True, False, 0, -1, 2.0, "2", float("nan"), float("inf")])
def test_metadata_values_are_positive_integers_or_explicit_null_without_coercion(field, value):
    record = metadata()
    record[field] = value
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [record], request=request())
    assert_error("minhash_result_selector_invalid", validate_minhash_result_selector, selector([record]))


@pytest.mark.parametrize("key,value", [("row_index", True), ("row_index", -1), ("row_index", 1.0),
                                      ("row_index", "1"), ("genome_id", "a"),
                                      ("genome_id", "456.2\n"), ("genome_id", 456.2)])
def test_pair_key_shapes_are_closed_without_attempting_a_native_join(key, value):
    record = metadata()
    record[key] = value
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [record], request=request())


@pytest.mark.parametrize("level", ["record", "provenance", "evidence"])
@pytest.mark.parametrize("change", ["extra", "missing"])
def test_each_metadata_object_has_exact_closed_fields(level, change):
    record = metadata()
    target = record if level == "record" else record["provenance"]
    if level == "evidence":
        target = target["fields"][0]
    if change == "extra":
        target["unselected"] = 1
    else:
        target.pop(next(iter(target)))
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [record], request=request())


@pytest.mark.parametrize("change", ["missing_evidence", "duplicate_evidence", "null_with_evidence", "wrong_field"])
def test_exactly_one_evidence_record_per_nonnull_field(change):
    record = metadata()
    evidence = record["provenance"]["fields"]
    if change == "missing_evidence":
        evidence.pop()
    elif change == "duplicate_evidence":
        evidence.append(deepcopy(evidence[0]))
    elif change == "null_with_evidence":
        record["kmer_length"] = None
    else:
        evidence[0]["field"] = "sketch_size"
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [record], request=request())
    assert not Draft202012Validator(minhash_result_selector_schema()).is_valid(selector([record]))


@pytest.mark.parametrize("pointer", ["", "/", "/pairs/0/kmer_length", "/a~1b/~0/0", "/~01"])
def test_rfc6901_pointer_strings_are_retained_without_resolution(pointer):
    record = metadata()
    record["provenance"]["fields"][0]["record_path"] = pointer
    assert validate_minhash_pair_metadata([record], request=request())[0] == record


@pytest.mark.parametrize("key,value", [("source_ref", "source_missing"), ("artifact_ref", "artifact_missing"),
                                      ("record_path", "pairs/0"), ("record_path", "#/pairs/0"),
                                      ("record_path", "/~2"), ("record_path", "/a~"), ("record_path", 0)])
def test_evidence_reference_and_pointer_shapes_are_checked(key, value):
    record = metadata()
    record["provenance"]["fields"][0][key] = value
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [record], request=request())


@pytest.mark.parametrize("key,value", [("query_mode", "fasta"), ("query_operand", "123.2")])
def test_query_mode_and_operand_must_match_original_service_request(key, value):
    record = metadata()
    record["provenance"][key] = value
    # Selector-only validation has no request authority.
    selected = validate_minhash_result_selector(selector([record]))
    assert_error("minhash_metadata_query_conflict", validate_minhash_pair_metadata,
                 [record], request=request())
    assert_error("minhash_metadata_query_conflict", validate_minhash_publication_inputs,
                 publication(selected), request=request(), selector=selected)


@pytest.mark.parametrize("key,value", [("kind", "inferred"), ("native_parameter_equivalence", "established"),
                                      ("query_operand", "  "), ("query_mode", "local")])
def test_provenance_has_only_the_declared_meanings(key, value):
    record = metadata()
    record["provenance"][key] = value
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [record], request=request())


@pytest.mark.parametrize("bad_request", [None, {}, {"mode": "genome", "query": "123.1"},
    {"version": "1.1", "method": "Minhash.compute_genome_distance_for_genome2", "params": [], "id": "rpc"}])
def test_request_is_the_complete_service_request_not_the_rpc_envelope(bad_request):
    assert_error("minhash_pair_metadata_invalid", validate_minhash_pair_metadata,
                 [], request=bad_request)


@pytest.mark.parametrize("field", ["version", "mode", "saved_result_ref", "pair_metadata"])
def test_selector_requires_all_declared_fields(field):
    value = selector()
    del value[field]
    assert_error("minhash_result_selector_invalid", validate_minhash_result_selector, value)


@pytest.mark.parametrize("replacement", [None, [], {"version": "other"}, {"extra": None}])
def test_selector_outer_shape_is_closed(replacement):
    assert_error("minhash_result_selector_invalid", validate_minhash_result_selector, replacement)


@pytest.mark.parametrize("mode,reference", [("native_result", SAVED_SOURCE), ("saved_sheet", None),
                                            ("saved_sheet", "result_missing"), ("other", None)])
def test_selector_mode_and_saved_reference_relationship(mode, reference):
    value = selector()
    value.update(mode=mode, saved_result_ref=reference)
    assert_error("minhash_result_selector_invalid", validate_minhash_result_selector, value)


def test_schema_is_detached_and_supports_legacy_native_saved_and_null_inputs():
    schema = minhash_result_selector_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for value in ({}, selector(), selector([metadata()]), selector([metadata(**dict.fromkeys(FIELDS))]),
                  selector([metadata(query_length=None, reference_length=None, alphabet_size=None)]),
                  selector([metadata(), metadata()], mode="saved_sheet")):
        assert validator.is_valid(value)
    assert not validator.is_valid({"extra": 1})
    trailing_newline = selector([metadata()])
    trailing_newline["pair_metadata"][0]["genome_id"] += "\n"
    assert not validator.is_valid(trailing_newline)
    trailing_newline = selector([metadata()])
    trailing_newline["pair_metadata"][0]["provenance"]["fields"][0]["source_ref"] += "\n"
    assert not validator.is_valid(trailing_newline)
    schema["oneOf"][1]["properties"]["pair_metadata"]["items"]["properties"].clear()
    assert minhash_result_selector_schema() != schema


@pytest.mark.parametrize("field", ["version", "selector", "pair_metadata", "metadata_bindings", "saved_result"])
def test_publication_requires_all_closed_fields(field):
    selected = selector([metadata()])
    value = publication(selected)
    del value[field]
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)


@pytest.mark.parametrize("replacement", [None, {}, [], "saved"])
def test_malformed_publication_envelope_has_stable_failure(replacement):
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 replacement, request=request(), selector=selector())


def test_publication_copies_selector_and_complete_metadata_exactly():
    selected = selector([metadata()])
    for field in ("selector", "pair_metadata"):
        value = publication(selected)
        if field == "selector":
            value[field]["pair_metadata"] = []
        else:
            value[field][0]["kmer_length"] = 2
        assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                     value, request=request(), selector=selected)
    value = publication(selected)
    value["extra"] = None
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 None, request=request(), selector={})


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra_field", "missing_field", "null_field"])
def test_publication_has_one_closed_binding_for_each_nonnull_occurrence_field(change):
    selected = selector([metadata(alphabet_size=None)])
    value = publication(selected)
    if change == "missing":
        value["metadata_bindings"].pop()
    elif change == "duplicate":
        value["metadata_bindings"].append(deepcopy(value["metadata_bindings"][0]))
    elif change == "extra_field":
        value["metadata_bindings"][0]["extra"] = None
    elif change == "missing_field":
        del value["metadata_bindings"][0]["artifact_ref"]
    else:
        value["metadata_bindings"][0]["field"] = "alphabet_size"
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)


@pytest.mark.parametrize("field,replacement", [
    ("pair_metadata_index", True), ("pair_metadata_index", -1), ("pair_metadata_index", 9),
    ("pair_metadata_index", 0.0), ("pair_metadata_index", 1),
    ("source_ref", "source_" + "f" * 32), ("artifact_ref", "artifact_" + "f" * 64),
    ("artifact_sha256", "f" * 64), ("artifact_sha256", "B" * 64),
    ("record_path", "/other/kmer_length"), ("field", "query_length"),
    ("value", True), ("value", 1.0), ("value", "1"), ("value", None), ("value", 2),
])
def test_bindings_identify_the_exact_list_occurrence_evidence_and_integer(field, replacement):
    # Row 9 is list occurrence 0; row identity is not the metadata-list index.
    selected = selector([metadata(9), metadata(2, kmer_length=2)])
    value = publication(selected)
    value["metadata_bindings"][0][field] = replacement
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_saved_sheet_envelope_keeps_original_common_schemas_and_detached_copies(mode):
    selected = selector([metadata(mode=mode)], mode="saved_sheet")
    value = publication(selected, service_request=request(mode))
    frozen = deepcopy(value)
    actual = validate_minhash_publication_inputs(value, request=request(mode), selector=selected)
    assert actual == frozen == value
    actual["saved_result"]["sheet"]["request"]["params"][0] = "changed"
    actual["saved_result"]["original_components"]["diagnostics"].clear()
    assert value == frozen


@pytest.mark.parametrize("change", ["missing_saved", "wrong_source", "native_digest", "grading_digest",
                                    "extra_saved", "wrong_sheet_schema", "wrong_components_schema",
                                    "wrong_mode", "wrong_query", "wrong_native_operand", "row_count"])
def test_saved_envelope_copy_and_request_associations_are_checked(change):
    selected = selector(mode="saved_sheet")
    value = publication(selected)
    saved = value["saved_result"]
    if change == "missing_saved":
        value["saved_result"] = None
    elif change == "wrong_source":
        saved["source_ref"] = SOURCE
    elif change == "native_digest":
        saved["native_sha256"] = "e" * 64
    elif change == "grading_digest":
        saved["grading_sha256"] = "e" * 64
    elif change == "extra_saved":
        saved["extra"] = 1
    elif change == "wrong_sheet_schema":
        saved["sheet"]["schema"] = "other_sheet"
    elif change == "wrong_components_schema":
        saved["original_components"]["schema"] = "other_components"
    elif change == "wrong_mode":
        saved["sheet"]["mode"] = "fasta"
    elif change == "wrong_query":
        saved["sheet"]["request"]["params"][0] = "123.2"
    elif change == "wrong_native_operand":
        saved["sheet"]["request"]["params"][4] = True
    else:
        saved["sheet"]["native_result"].append(["456.2", 0, 1, "0/0"])
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)


def test_native_result_envelope_cannot_smuggle_a_saved_result():
    selected = selector()
    value = publication(selected)
    value["saved_result"] = saved_result(request())
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)


@pytest.mark.parametrize("kind", ["tuple", "nonstring_key", "cyclic", "nonfinite"])
def test_non_json_publication_values_fail_with_the_stable_code(kind):
    selected = selector()
    value = publication(selected)
    if kind == "tuple":
        value["metadata_bindings"] = ()
    elif kind == "nonstring_key":
        value[1] = None
    elif kind == "cyclic":
        value["pair_metadata"].append(value)
    else:
        value["unselected"] = float("nan")
    assert_error("minhash_publication_inputs_conflict", validate_minhash_publication_inputs,
                 value, request=request(), selector=selected)
