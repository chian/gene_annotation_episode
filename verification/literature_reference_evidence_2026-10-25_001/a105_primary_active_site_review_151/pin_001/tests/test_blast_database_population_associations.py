"""Synthetic supplied population assertions; no BLAST or acquisition runs."""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.blast_database_population_associations import (
    validate_blast_database_population_context as validate,
    qualify_blast_database_population_context as qualify,
)


PREFIX = "blast_database_population_"
OPERAND = "/project/db/release1/proteins"


def retained(value, source, pointer=""):
    raw = json.dumps(value, sort_keys=True).encode()
    return dict(source_ref=source, artifact_ref="artifact:" + source,
        sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), pointer=pointer, value=deepcopy(value))


def population_inputs(*, key=None, operand=OPERAND, identity=None, profile=None):
    key = deepcopy(key or dict(artifact_key="report", member_ordinal=None, report_index=0,
        search_pointer="/BlastOutput2/0/report/results/search"))
    identity = deepcopy(identity or dict(namespace="native_blast_database", value="curated-proteins",
        version="1", release="release1", scope="searched_database", preparation_type="sequence_database",
        source=dict(source_ref="manifest", pointer="/database")))
    profile = deepcopy(profile or dict(database="curated-proteins", release="release1", scope="searched_database",
        count_unit="unique_sequences", total_count=110, function_counts={"F": 100, "G": 10}, source="census"))
    census = retained({k: v for k, v in profile.items() if k != "source"}, profile["source"])
    assertion = retained(dict(schema="blast_database_population_assertion_v1", relation="same_population",
        native_database_operand=operand, database_manifest_sha256="1" * 64,
        population_identity={k: v for k, v in identity.items() if k != "source"},
        census_artifact={k: census[k] for k in ("sha256", "size_bytes", "pointer")}), "assertion")
    row = dict(schema="blast_database_population_association_input_v1", association_key="synthetic-association",
        search_key=deepcopy(key), database_key="db", metadata_source=dict(source_ref="metadata", pointer="/searches/0"),
        assertion_source={k: assertion[k] for k in ("source_ref", "pointer")},
        census_source={k: census[k] for k in ("source_ref", "pointer")},
        selected_database=dict(native_database_operand=operand, native_paths=operand.split(" "), identity=identity,
            manifest_sha256="1" * 64, manifest_size_bytes=123,
            invocation_source=dict(source_ref="invocation", pointer="/argv"), manifest_source=identity["source"]),
        assertion_record=assertion, census_record=census)
    normalized = dict(schema="blast_normalized_result_v1", mode="database", resource="hpc", format="json2",
        search=dict(database=operand, request={"database": operand}),
        source_locator=dict(artifact_ref="native-report", source_ref="source:native-report", report_index=key["report_index"],
            pointer=key["search_pointer"], search_key=deepcopy(key), member_ordinal=key["member_ordinal"], member_sha256=None),
        native=dict(sha256="2" * 64, archive_member=None))
    return dict(context=dict(schema="blast_database_population_context_v1", search_key=key, associations=[row]),
        normalized_result=normalized, database_identity=deepcopy(identity), database_profile=profile)


def reason(result, suffix):
    return PREFIX + suffix in result["reason_codes"]


def test_closed_context_detached_unchanged_and_qualification_is_not_a_score():
    args = population_inputs()
    before = deepcopy(args)
    detached = validate(args["context"])
    assert detached == args["context"] and detached is not args["context"]
    out = qualify(**args)
    assert args == before
    assert out == dict(schema="blast_database_population_relation_v1", search_key=args["context"]["search_key"],
        status="available", association_results=[dict(metadata_source=args["context"]["associations"][0]["metadata_source"],
            association_key="synthetic-association", status="available", reason_codes=[])], reason_codes=[])


@pytest.mark.parametrize("change", [
    lambda v: v.update(verified=True),
    lambda v: v["search_key"].update(report_index=True),
    lambda v: v["associations"][0].update(available=True),
    lambda v: v["associations"][0]["selected_database"].update(manifest_size_bytes=True),
    lambda v: v["associations"][0]["assertion_record"].update(pointer="/bad~2pointer"),
    lambda v: v["associations"][0]["assertion_record"].update(extra=1),
    lambda v: v["associations"][0]["selected_database"]["identity"].update(extra=1),
])
def test_structural_caller_errors(change):
    context = population_inputs()["context"]
    change(context)
    with pytest.raises(ValueError, match="^" + PREFIX + "context_fields_invalid$"):
        validate(context)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), (1, 2), {1: "not-json"}, object()])
def test_finite_original_json_is_required(value):
    context = population_inputs()["context"]
    context["associations"][0]["assertion_record"]["value"] = value
    with pytest.raises(ValueError, match="^" + PREFIX + "finite_json_required$"):
        validate(context)


@pytest.mark.parametrize("field,value", [("artifact_key", "other-report"), ("member_ordinal", 1),
    ("report_index", 1), ("search_pointer", "/BlastOutput2/0/report/results/iterations/1/search")])
def test_all_original_search_key_fields_checked(field, value):
    args = population_inputs()
    args["context"]["associations"][0]["search_key"][field] = value
    out = qualify(**args)
    assert out["status"] == "incompatible" and reason(out, "search_key_mismatch")


def test_normalized_locator_cannot_borrow_another_search():
    args = population_inputs()
    args["normalized_result"]["source_locator"]["search_key"]["artifact_key"] = "other"
    assert reason(qualify(**args), "search_key_mismatch")


@pytest.mark.parametrize("field", ["selected_database", "assertion_record", "census_record"])
def test_missing_selected_fact_stays_unavailable_even_beside_valid_sibling(field):
    args = population_inputs()
    row = deepcopy(args["context"]["associations"][0])
    row["association_key"] = "unresolved"
    row[field] = None
    args["context"]["associations"].append(row)
    out = qualify(**args)
    assert out["status"] == "unavailable"
    assert out["association_results"][0]["status"] == "available"
    assert out["association_results"][1]["status"] == "unavailable"


@pytest.mark.parametrize("value", [None, [], {}, {"relation": "same_population"},
    {"schema": "blast_database_population_assertion_v1", "available": True}])
def test_malformed_original_assertion_is_retained_and_incompatible(value):
    args = population_inputs()
    args["context"]["associations"][0]["assertion_record"]["value"] = value
    assert validate(args["context"]) == args["context"]
    out = qualify(**args)
    assert out["status"] == "incompatible" and reason(out, "source_record_invalid")


@pytest.mark.parametrize("field,value,suffix", [
    ("native_database_operand", "/other/proteins", "native_operand_conflict"),
    ("database_manifest_sha256", "4" * 64, "manifest_identity_conflict"),
    ("population_identity", dict(namespace="other", value="curated-proteins", version="1", release="release1",
        scope="searched_database", preparation_type="sequence_database"), "population_identity_conflict"),
    ("census_artifact", dict(sha256="3" * 64, size_bytes=0, pointer=""), "census_record_conflict"),
])
def test_assertion_cannot_overwrite_independent_facts(field, value, suffix):
    args = population_inputs()
    args["context"]["associations"][0]["assertion_record"]["value"][field] = value
    out = qualify(**args)
    assert out["status"] == "incompatible" and reason(out, suffix)


def test_ordered_multi_prefix_operand_is_literal():
    args = population_inputs(operand="/db/first /db/second")
    assert qualify(**args)["status"] == "available"
    args["context"]["associations"][0]["selected_database"]["native_paths"].reverse()
    assert reason(qualify(**args), "native_operand_conflict")


@pytest.mark.parametrize("field", ["database", "db", "database_release", "database_scope", "database_namespace", "database_version"])
def test_every_present_native_request_identity_field_is_checked(field):
    args = population_inputs()
    args["normalized_result"]["search"]["request"][field] = "third-spelling"
    out = qualify(**args)
    assert out["status"] == "incompatible"
    assert reason(out, "native_operand_conflict" if field in ("database", "db") else "population_identity_conflict")


def test_unknown_release_is_not_equality_evidence():
    args = population_inputs()
    args["database_identity"]["release"] = None
    args["database_profile"]["release"] = None
    args = population_inputs(identity=args["database_identity"], profile=args["database_profile"])
    out = qualify(**args)
    assert out["status"] == "unavailable" and reason(out, "population_release_unavailable")


def test_unknown_scope_remains_unavailable():
    args = population_inputs()
    args["database_identity"]["scope"] = None
    args = population_inputs(identity=args["database_identity"])
    out = qualify(**args)
    assert out["status"] == "unavailable" and reason(out, "population_scope_unavailable")


@pytest.mark.parametrize("field", ["release", "scope"])
@pytest.mark.parametrize("location", ["assertion", "selected", "binding"])
def test_one_unknown_required_identity_fact_is_unavailable_not_a_known_contradiction(field, location):
    args = population_inputs()
    row = args["context"]["associations"][0]
    identity = (row["assertion_record"]["value"]["population_identity"] if location == "assertion" else
                row["selected_database"]["identity"] if location == "selected" else args["database_identity"])
    identity[field] = None
    out = qualify(**args)
    assert out["status"] == "unavailable" and reason(out, "population_" + field + "_unavailable")


@pytest.mark.parametrize("record", ["assertion_record", "census_record"])
@pytest.mark.parametrize("alias", ["artifact_ref", "source_ref", "sha256", "member_digest"])
def test_native_report_alias_cannot_supply_population_record(record, alias):
    args = population_inputs()
    selected = args["context"]["associations"][0][record]
    if alias == "member_digest":
        key = args["context"]["search_key"]
        key["member_ordinal"] = 2
        args["context"]["associations"][0]["search_key"] = deepcopy(key)
        args["normalized_result"]["source_locator"].update(search_key=deepcopy(key), member_ordinal=2, member_sha256=selected["sha256"])
        args["normalized_result"]["native"]["archive_member"] = dict(ordinal=2, name="report.json", sha256=selected["sha256"])
    else:
        selected[alias] = (args["normalized_result"]["native"]["sha256"] if alias == "sha256" else
                           "source:native-report" if alias == "source_ref" else "native-report")
    out = qualify(**args)
    assert out["status"] == "incompatible" and reason(out, "report_used_as_population_source")


def test_exact_duplicates_retained_and_conflicting_identity_has_no_order_winner():
    args = population_inputs()
    rows = args["context"]["associations"]
    rows.append(deepcopy(rows[0]))
    assert qualify(**args)["status"] == "available"
    assert len(validate(args["context"])["associations"]) == 2
    rows[1]["database_key"] = "other"
    first = qualify(**args)
    rows.reverse()
    second = qualify(**args)
    assert first["status"] == second["status"] == "incompatible"
    assert first["reason_codes"] == second["reason_codes"]
    assert reason(first, "association_record_conflict")


def test_same_source_different_bytes_is_conflicting_even_with_new_association_key():
    args = population_inputs()
    row = deepcopy(args["context"]["associations"][0])
    row["association_key"] = "other-declaration"
    row["assertion_record"]["sha256"] = "4" * 64
    args["context"]["associations"].append(row)
    out = qualify(**args)
    assert out["status"] == "incompatible" and reason(out, "source_address_conflict")


def test_empty_declarations_grant_no_population_relation():
    args = population_inputs()
    args["context"]["associations"] = []
    out = qualify(**args)
    assert out["status"] == "unavailable" and reason(out, "association_missing")


def test_distinct_report_source_and_artifact_handles_still_detect_source_alias():
    args = population_inputs()
    args["normalized_result"]["source_locator"]["source_ref"] = "source:original-report"
    row = args["context"]["associations"][0]
    row["assertion_source"]["source_ref"] = "source:original-report"
    row["assertion_record"]["source_ref"] = "source:original-report"
    assert row["assertion_record"]["artifact_ref"] != args["normalized_result"]["source_locator"]["artifact_ref"]
    assert reason(qualify(**args), "report_used_as_population_source")


def test_missing_original_report_source_identity_cannot_skip_source_alias_check():
    args = population_inputs()
    args["normalized_result"]["source_locator"].pop("source_ref")
    out = qualify(**args)
    assert out["status"] == "unavailable" and reason(out, "source_record_unavailable")


def test_source_and_artifact_namespaces_are_not_cross_compared():
    args = population_inputs()
    row = args["context"]["associations"][0]
    row["assertion_source"]["source_ref"] = args["normalized_result"]["source_locator"]["artifact_ref"]
    row["assertion_record"]["source_ref"] = row["assertion_source"]["source_ref"]
    assert qualify(**args)["status"] == "available"
