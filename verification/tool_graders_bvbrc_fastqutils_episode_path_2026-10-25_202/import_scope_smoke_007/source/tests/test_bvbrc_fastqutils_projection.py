from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_projection import project_fastqutils_facts
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import encode_failures, encode_saved_components, decode_saved_components
from gene_annotation_episode.bvbrc_fastqutils_metadata import extract_fastqutils_metadata
from gene_annotation_episode.bvbrc_fastqutils_sheet import populate_fastqutils_sheet

spec = importlib.util.spec_from_file_location("fixture_support", Path(__file__).parent / "fixtures/bvbrc_fastqutils/bundle/fixture_support.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def project(sheet, components, parameters, fields, failure=None):
    return project_fastqutils_facts(sheet, components, requested_form=f.schema(fields), parameters=parameters,
        failure_context=failure or {"requirements": [], "diagnostics": []})


def test_frozen195_exact_projection_oracle():
    sheet, components, params = [f.oracle(n) for n in ("EXPECTED_SHEET_002.json", "EXPECTED_COMPONENTS_002.json", "PROVIDER_PARAMETERS_002.json")]
    result = project_fastqutils_facts(sheet, components,
        requested_form=f.oracle("RESULT_SELECTOR_PRE_DOWNLOAD_002.json")["requested_schema"], parameters=params,
        failure_context=dict(requirements=sheet["requirements"], diagnostics=sheet["diagnostics"]))
    assert result["facts"] == f.oracle("EXPECTED_FACTS_002.json")
    assert result["status"] == "ok"


@pytest.mark.parametrize("case_index", list(range(10)))
def test_frozen_missing_partial_cardinality_oracles(case_index):
    case = f.oracle("UNAVAILABLE_AND_PARTIAL_002.json")[case_index]
    sheet, components, params = [f.oracle(n) for n in ("EXPECTED_SHEET_002.json", "EXPECTED_COMPONENTS_002.json", "PROVIDER_PARAMETERS_002.json")]
    if case_index in (1, 2):
        sheet, components, params = [f.oracle(n) for n in ("UNAVAILABLE_SHEET_002.json", "UNAVAILABLE_COMPONENTS_002.json", "UNAVAILABLE_PARAMETERS_002.json")]
    elif case_index == 7:
        doc = f.oracle("PARTIAL_NATIVE_DOCUMENT_002.json")
        metadata = extract_fastqutils_metadata(sheet["original_task"], analysis_id=sheet["analysis_id"],
            metadata_bindings=[], supplied_values=[], documents=[doc])
        binding = dict(kind="possessed_content", content=doc["artifact"]["content_binding"])
        resolutions = [dict(document_id=doc["document_id"], selection=binding, state="available", matched_contents=[doc["artifact"]["content_binding"]],
                            artifact_ref=doc["artifact"]["id"], requirement_refs=[], diagnostic_codes=[])]
        sheet = populate_fastqutils_sheet([doc], metadata=metadata, document_resolutions=resolutions)
        params.update(documents=[dict(document_id=doc["document_id"], selection=binding, format="fastq", producer_version=None)],
                      metadata_bindings=[], calculation_requests=[])
        components = None
    result = project(sheet, components, params, {"answer": case["selection"]})
    assert result["facts"]["answer"] == case["expected"]


def test_one_target_ambiguity_keeps_all_actual_rows():
    sheet, components, params = [f.oracle(n) for n in ("EXPECTED_SHEET_002.json", "EXPECTED_COMPONENTS_002.json", "PROVIDER_PARAMETERS_002.json")]
    selected = f.selection("measurement", f.measurement(metric="fastq_symbol_count", axis=dict(kind="all")))
    result = project(sheet, components, params, {"symbols": selected})
    fact = result["facts"]["symbols"]
    assert fact["state"] == "ambiguous" and fact["matched_count"] == 7 and len(fact["records"]) == 7
    assert all(r["record_ref"] is not None and r["payload"] is not None for r in fact["records"])


def test_null_sheet_preserves_specific_failure_context_and_never_invents_native_rows():
    parameters = f.oracle("PROVIDER_PARAMETERS_002.json")
    req = f.oracle("ERROR_SHAPES_002.json")["native_requirement"]
    diag = f.oracle("ERROR_SHAPES_002.json")["native_diagnostic"]
    fields = {"population": f.selection("population", f.population("qc", "fastqc_module"))}
    result = project(None, None, parameters, fields, failure=dict(requirements=[req], diagnostics=[diag]))
    fact = result["facts"]["population"]
    assert fact["satisfied"] and fact["matched_count"] == 0
    assert fact["records"][0]["payload"] is fact["records"][0]["record_ref"] is None
    assert result["failure_context"] == dict(requirements=[req], diagnostics=[diag])


@pytest.mark.parametrize("kind,selector", [
    ("population", f.population()),
    ("association", dict(selection="semantic", document_id="hostile", input_pointer="/paired_end_libs/0", recipe_ordinal=4, mate="combined", branch="clean")),
])
def test_available_value_requires_complete_population_or_established_association(kind, selector):
    if kind == "population":
        data = f.build({"reads": (f.fastq(["a"]) + b"@broken\nAC", "fastq")})
    else:
        data, _ = f.seven_family_data()
    result = f.run(data, {"target": f.selection(kind, selector, availability="available_value")})
    assert result["facts"]["target"]["state"] == "missing_value"
    result = f.run(data, {"target": f.selection(kind, selector)})
    assert result["facts"]["target"]["state"] == "satisfied"


@pytest.mark.parametrize("fields", [
    {"s": f.selection("request_status", field="s")},
    {"s": f.selection("request_status", field="absent")},
    {"a": f.selection("request_status", field="b"), "b": f.selection("request_status", field="a")},
])
def test_invalid_status_links_are_rejected(fields):
    with pytest.raises(FastqUtilsContractError):
        project(None, None, f.oracle("PROVIDER_PARAMETERS_002.json"), fields)


def test_malformed_forms_reject_extra_keywords_and_wrong_one_target_count():
    requested = f.schema({"reads": f.selection("measurement", f.measurement())})
    changed = deepcopy(requested); changed["additionalProperties"] = True
    with pytest.raises(FastqUtilsContractError): validate_requested_form(changed)
    with pytest.raises(FastqUtilsContractError):
        f.schema({"reads": f.selection("measurement", f.measurement(), count=2)})
    with pytest.raises(FastqUtilsContractError):
        project(None, None, f.oracle("PROVIDER_PARAMETERS_002.json"),
                {"other": f.selection("measurement", f.measurement("unselected_document"))})


def test_all_seven_families_keep_specific_source_links_and_assumptions():
    data, fields = f.seven_family_data()
    result = f.run(data, fields)
    assert result["status"] == "ok"
    records = {name: fact["records"][0] for name, fact in result["facts"].items()}
    assert {r["kind"] for r in records.values()} == {"measurement", "component", "category", "population", "association", "requirements", "request_status"}
    assert records["read_count"]["payload"]["value"] == 2
    assert records["gc"]["payload"]["value"] == 5 / 9
    assert records["errors"]["payload"]["value"] == .001
    assert records["retained"]["payload"]["value"] == .75
    assert records["qc"]["payload"]["value"] == "pass"
    assert records["association"]["payload"]["state"] == "unresolved"
    assert records["status"]["payload"]["satisfied"]
    assert records["errors"]["payload"]["encoding_basis"]["declaration"] == data[2][0]["value"]
    assert "source_declarations" in records["errors"]["source_refs"]


def test_failure_codec_exact_mapping_and_roundtrip_original_arrays():
    oracle = f.oracle("ERROR_SHAPES_002.json")
    req, diag = oracle["native_requirement"], oracle["native_diagnostic"]
    encoded = encode_failures([req], [diag])
    assert encoded == dict(missing_requirements=[oracle["host_requirement"]], diagnostics=[oracle["host_diagnostic"]])
    original = dict(requirements=[req, req], diagnostics=[diag, diag])
    saved = encode_saved_components(None, projection_failure_context=original,
        native_requirements=[req], native_diagnostics=[diag])
    decoded = decode_saved_components(saved)
    assert decoded["projection_failure_context"] == original
    decoded["projection_failure_context"]["requirements"].clear()
    assert len(saved["projection_failure_context"]["requirements"]) == 2


@pytest.mark.parametrize("required,kind", [("supported_parser", "parser_binding"), ("native_version", "parser_binding"),
    ("complete_native_bytes", "output_bytes"), ("full_fastqc_data", "output_bytes"),
    ("earlier_hostile_report", "output_bytes"), ("selected_document", "output_bytes"),
    ("quality_encoding", "scientific_metadata"), ("pair_correspondence", "scientific_metadata")])
def test_native_requirement_kind_mapping(required, kind):
    req = f.oracle("ERROR_SHAPES_002.json")["native_requirement"]
    req["required_data"] = required
    assert encode_failures([req], [])["missing_requirements"][0]["kind"] == kind
