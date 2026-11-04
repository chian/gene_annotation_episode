from copy import deepcopy
import hashlib
import importlib
import importlib.util
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as provider
from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, canonical_json, bytes_sha256, json_sha256
from gene_annotation_episode.bvbrc_fastqutils_resolution import resolve_documents, resolve_calculation_inputs
from gene_annotation_episode.bvbrc_fastqutils_calculators import calculate_fastqutils
from gene_annotation_episode.bvbrc_fastqutils_native import parse_unsupported_artifact
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection, encode_saved_components, encode_failures
from gene_annotation_episode.bvbrc_fastqutils_projection import project_fastqutils_facts

spec = importlib.util.spec_from_file_location("fixture_support", Path(__file__).parent / "fixtures/bvbrc_fastqutils/bundle/fixture_support.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def validate(result, data, fields):
    return validate_saved_projection(result["sheet"], result["components"], facts=result["facts"], status=result["status"],
        missing_requirements=result["missing_requirements"], diagnostics=result["diagnostics"],
        requested_form=f.schema(fields), parameters=data[3], original_task=data[0]["original_task"], bundle=data[0])


def test_provider_actual_frozen_bytes_and_immutable_predownload_selection():
    data = f.fixture195()
    selector = f.oracle("RESULT_SELECTOR_PRE_DOWNLOAD_002.json")
    before = canonical_json([data[0], data[3], selector])
    result = provider.consume_bundle(data[0], artifact_bytes=data[1], supplied_values=data[2],
                                    requested_form=selector["requested_schema"], parameters=data[3])
    assert canonical_json([data[0], data[3], selector]) == before
    assert result["adapter_id"] == "bvbrc_fastqutils" and result["adapter_version"] == "2"
    assert result["status"] == "ok"
    assert [result["facts"][name]["records"][0]["payload"]["value"] for name in
        ("read_count", "gc_fraction", "expected_errors", "retained_native_report")] == [2, 5 / 9, .001, .75]
    assert result["facts"]["qc_status"]["records"][0]["payload"] is None
    assert all(s["observed_state"] == "unknown" for s in result["sheet"]["stages"])


def test_exact_requirement_matching_deduplicates_identical_receipts_but_not_versions():
    data = f.build({"reads": (f.fastq(["a"]), "fastq")})
    bundle, raw, _, params = data
    bundle["artifacts"].append(deepcopy(bundle["artifacts"][0]))
    contexts, resolutions, reqs = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    assert len(contexts) == 1 and len(resolutions[0]["matched_contents"]) == 1 and not reqs
    assert len(bundle["artifacts"]) == 2
    second = bundle["artifacts"][1]
    second.update(raw_artifact_ref="artifact_revised", sha256=bytes_sha256(f.fastq(["b"])))
    raw["artifact_revised"] = f.fastq(["b"])
    contexts, resolutions, reqs = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    assert not contexts and resolutions[0]["state"] == "ambiguous" and len(resolutions[0]["matched_contents"]) == 2
    assert reqs[0]["required_data"] == "exact_source_cardinality"


def test_same_native_name_cannot_select_an_unrelated_source():
    data = f.build({"left": (f.fastq(["a"]), "fastq"), "right": (f.fastq(["a", "b"]), "fastq")})
    bundle, raw, _, params = data
    bundle["artifacts"][1]["workspace_object"]["path"] = bundle["artifacts"][0]["workspace_object"]["path"]
    contexts, _, _ = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    assert contexts[0]["content"]["source_ref"] == "source_left"
    assert contexts[1]["content"]["source_ref"] == "source_right"
    bundle["artifacts"][1]["requirement_ids"] = []
    contexts, resolutions, _ = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    assert len(contexts) == 1 and resolutions[1]["state"] == "missing"


def test_exact_possessed_content_and_bytes_not_just_hash_or_filename():
    bundle, raw, values, _ = f.fixture195()
    params = f.oracle("POSSESSED_PARAMETERS_002.json")
    contexts, resolutions, _ = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    assert contexts and resolutions[0]["state"] == "available"
    changed = deepcopy(params)
    changed["documents"][0]["selection"]["content"]["artifact_field"] = "text_ref"
    contexts, resolutions, _ = resolve_documents(bundle, artifact_bytes=raw, parameters=changed)
    assert not contexts and resolutions[0]["state"] == "missing"
    selected = deepcopy(params["documents"][0]["selection"]["content"])
    bundle["artifacts"] = []
    bundle["supplied_contents"] = [selected]
    contexts, _, _ = resolve_documents(bundle, artifact_bytes=raw, parameters=params)
    assert len(contexts) == 1 and contexts[0]["native_name"] is None
    wrong = dict(raw); wrong[selected["artifact_ref"]] += b"x"
    with pytest.raises(FastqUtilsContractError, match="binding_conflict"):
        resolve_documents(bundle, artifact_bytes=wrong, parameters=params)


@pytest.mark.parametrize("change", ["duplicate_document", "conflicting_byte_id", "task", "nonbytes"])
def test_global_api_and_binding_failures_are_contract_errors(change):
    data = f.build({"reads": (f.fastq(["a"]), "fastq")})
    bundle, raw, _, params = data
    if change == "duplicate_document": params["documents"].append(deepcopy(params["documents"][0]))
    elif change == "conflicting_byte_id":
        bundle["artifacts"].append(deepcopy(bundle["artifacts"][0])); bundle["artifacts"][1]["sha256"] = "0" * 64
    elif change == "task": bundle["artifacts"][0]["task_association"]["task_id"] = "wrong_task"
    else: raw["artifact_reads"] = "not bytes"
    with pytest.raises(FastqUtilsContractError): resolve_documents(bundle, artifact_bytes=raw, parameters=params)


def test_missing_bytes_and_missing_document_leave_sibling_available():
    data = f.build({"left": (f.fastq(["a"]), "fastq"), "right": (f.fastq(["b"]), "fastq")})
    del data[1]["artifact_left"]
    contexts, resolutions, reqs = resolve_documents(data[0], artifact_bytes=data[1], parameters=data[3])
    assert [c["document_id"] for c in contexts] == ["right"]
    assert resolutions[0]["matched_contents"] and resolutions[0]["state"] == "missing"
    assert reqs[0]["required_data"] == "complete_native_bytes"
    result = f.run(data, dict(left=f.selection("measurement", f.measurement("left")),
        right=f.selection("measurement", f.measurement("right"), availability="available_value")))
    assert result["facts"]["left"]["records"][0]["payload"] is None
    assert result["facts"]["right"]["records"][0]["payload"]["value"] == 1


def test_malformed_document_does_not_erase_intact_sibling():
    data = f.build({"broken": (f.fastq(["a"]) + b"@b\nACTG\n+\nI", "fastq"),
        "valid": (f.fastq(["x", "y"]), "fastq")})
    result = f.run(data, dict(broken=f.selection("measurement", f.measurement("broken"), availability="available_value"),
        valid=f.selection("measurement", f.measurement("valid"), availability="available_value")))
    assert result["status"] == "partial"
    assert result["facts"]["broken"]["records"][0]["payload"]["value"] == 1
    assert result["facts"]["broken"]["records"][0]["state"] == "partial"
    assert result["facts"]["valid"]["satisfied"] and result["facts"]["valid"]["records"][0]["payload"]["value"] == 2


def test_unknown_encoding_preserves_composition_and_quality_nulls():
    data = f.fixture195()
    data[3]["metadata_bindings"] = [r for r in data[3]["metadata_bindings"] if r["kind"] != "encoding_declaration"]
    fields = dict(reads=f.selection("measurement", f.measurement(), availability="available_value"),
        gc=f.selection("component", dict(selection="semantic", calculation_id="composition_reads", metric="gc_acgt_fraction", threshold=None), availability="available_value"),
        errors=f.selection("component", dict(selection="semantic", calculation_id="quality_reads", metric="phred_implied_expected_errors", threshold=None)))
    result = f.run(data, fields)
    assert result["status"] == "ok"
    assert result["facts"]["reads"]["records"][0]["payload"]["value"] == 2
    assert result["facts"]["gc"]["records"][0]["payload"]["value"] == 5 / 9
    assert result["facts"]["errors"]["records"][0]["payload"]["value"] is None
    assert result["facts"]["errors"]["records"][0]["payload"]["encoding_basis"]["basis"] == "unknown"


@pytest.mark.parametrize("format_name", ["bai", "samstat_html", "sra_metadata", "native_text", "native_json", "unknown"])
def test_unsupported_formats_remain_retained_and_explicit(format_name):
    data = f.build({"unsupported": (b"retained exact bytes", format_name)})
    contexts, _, _ = resolve_documents(data[0], artifact_bytes=data[1], parameters=data[3])
    doc = parse_unsupported_artifact(data[1]["artifact_unsupported"], context=contexts[0])
    assert doc["artifact"]["sha256"] == bytes_sha256(b"retained exact bytes")
    assert doc["parse_scope"] == "unsupported" and not doc["cells"] and not doc["populations"]
    assert doc["requirements"][0]["required_data"] == "supported_parser"


def test_mapping_binds_complete_denominator_and_preserves_primary_fraction_without_input():
    sam = b"@HD\tVN:1.6\n@SQ\tSN:r\tLN:10\na\t0\tr\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\nb\t4\t*\t0\t255\t*\t*\t0\t0\tACGT\tIIII\n"
    data = f.build({"reads": (f.fastq(["a", "b"]), "fastq"), "alignment": (sam, "sam_1_6")})
    request = dict(calculation_id="mapping", method="mapping_v1", population=f.population("alignment", "bam_records"),
                   input_population=f.population(), read_key_rule="first_token")
    data[3]["calculation_requests"] = [request]
    sheet = f.sheet_for(data)
    params = resolve_calculation_inputs(sheet, requests=[request])
    job = params["calculations"][0]
    assert {r["metric"] for r in sheet["measurements"] if r["id"] in job["operand_measurement_refs"]} == {"bam_record_count", "bam_primary_record_count", "fastq_read_count"}
    values = {c["metric"]: c["value"] for c in calculate_fastqutils(sheet, parameters=params)["components"]}
    assert values == {"distinct_mapped_read_fraction": .5, "primary_record_fraction": 1.0}
    request["input_population"] = None
    params = resolve_calculation_inputs(sheet, requests=[request])
    values = {c["metric"]: c["value"] for c in calculate_fastqutils(sheet, parameters=params)["components"]}
    assert values == {"distinct_mapped_read_fraction": None, "primary_record_fraction": 1.0}


def test_saved_validation_with_all_parsers_calculators_and_sheet_builders_disabled(monkeypatch):
    data, fields = f.seven_family_data()
    result = f.run(data, fields)
    def forbidden(*args, **kwargs): raise AssertionError("saved validation attempted scientific recomputation")
    names = ("fastq_reader", "sam_reader", "bam_reader", "fastqc_reader", "trim_reader", "pair_report_reader", "hostile_reader",
             "composition", "quality", "mapping", "retention", "consistency", "calculators", "native", "sheet", "metadata", "bundle_adapter")
    for suffix in names:
        module = importlib.import_module("gene_annotation_episode.bvbrc_fastqutils_" + suffix)
        for name in list(vars(module)):
            if name.startswith(("parse_", "calculate_", "populate_", "extract_")) or name == "consume_bundle":
                monkeypatch.setattr(module, name, forbidden)
    validate(result, data, fields)


@pytest.mark.parametrize("change", ["number", "source", "selection", "original", "parameter", "codec", "assumption"])
def test_saved_relationship_and_hash_tampering_rejected(change):
    data, fields = f.seven_family_data()
    result = f.run(data, fields)
    if change == "number": result["sheet"]["measurements"][0]["value"] += 1
    elif change == "source": data[0]["artifacts"][0]["source_ref"] = "wrong_source"
    elif change == "selection": fields["read_count"]["target"]["selector"]["metric"] = "fastq_base_count"
    elif change == "original": data[0]["original_task"]["submitted_parameters"]["recipe"] = []
    elif change == "parameter": data[3]["calculation_requests"][1]["quality_thresholds"] = [20]
    elif change == "codec": result["missing_requirements"] = []
    else: result["sheet"]["supplied_metadata"][0]["value"]["encoding"] = "phred64"
    with pytest.raises(FastqUtilsContractError): validate(result, data, fields)


def test_original_projection_failure_context_roundtrip_not_subtracted():
    data, fields = f.seven_family_data()
    result = f.run(data, fields)
    original = dict(requirements=[result["sheet"]["requirements"][0]] * 2,
                    diagnostics=[f.oracle("ERROR_SHAPES_002.json")["native_diagnostic"]] * 2)
    projection = project_fastqutils_facts(result["sheet"], result["components"]["calculations"],
        requested_form=f.schema(fields), parameters=data[3], failure_context=original)
    result["components"] = encode_saved_components(result["components"]["calculations"], projection_failure_context=original,
        native_requirements=projection["requirements"], native_diagnostics=projection["diagnostics"])
    encoded = encode_failures(projection["requirements"], projection["diagnostics"])
    result.update(facts=projection["facts"], status=projection["status"], **encoded)
    assert result["components"]["projection_failure_context"] == original
    validate(result, data, fields)


def test_module_facade_pins_exact_scientific_dependency_bytes():
    expected = hashlib.sha256()
    base = Path(provider.__file__).parent
    for name in sorted(provider._DEPENDENCIES):
        raw = (base / name).read_bytes()
        expected.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
    assert len(provider._DEPENDENCIES) == 27 and provider.implementation_sha256() == expected.hexdigest()
    assert {'bvbrc_fastqutils_cutadapt_reader.py', 'bvbrc_fastqutils_cutadapt_specs.py',
            'bvbrc_fastqutils_legacy_v2_schemas.json'} <= set(provider._DEPENDENCIES)
    assert provider.FastqUtilsBundleAdapter.adapter_id == provider.ADAPTER_ID


@pytest.mark.parametrize("change", ["association_artifact", "omit_library", "lineage_injection", "promote_association"])
def test_saved_source_relationship_rejection_survives_rehashed_empty_calculations(change):
    data, all_fields = f.seven_family_data()
    data[3]["calculation_requests"] = []
    fields = {k: v for k, v in all_fields.items() if k in ("read_count", "association", "population")}
    result = f.run(data, fields)
    sheet = result["sheet"]
    if change == "association_artifact":
        sheet["associations"][0]["artifact_refs"] = [sheet["documents"][0]["artifact"]["id"]]
    elif change == "omit_library":
        # Add a real original unused library, then omit its retained identity.
        data[0]["original_task"]["submitted_parameters"]["single_end_libs"] = [dict(read="/another")]
        sheet["original_task"] = deepcopy(data[0]["original_task"])
    elif change == "lineage_injection":
        edge = deepcopy(sheet["native_lineage"][0]); edge["id"] += "extra"
        sheet["native_lineage"].append(edge)
    else:
        sheet["associations"][0]["state"] = "established"
    result["components"]["calculations"]["sheet_sha256"] = json_sha256(sheet)
    # Deliberately reproject internally consistent changed facts. Validation
    # must still check source/metadata relationships, not merely fact equality.
    if change != "promote_association":
        projected = project_fastqutils_facts(sheet, result["components"]["calculations"],
            requested_form=f.schema(fields), parameters=data[3],
            failure_context=result["components"]["projection_failure_context"])
        result.update(facts=projected["facts"], status=projected["status"])
    with pytest.raises(FastqUtilsContractError): validate(result, data, fields)


def test_saved_actual_pair_membership_validates_without_rejoining_all_input():
    data = f.build({"left": (f.fastq(["a/1", "b/1"]), "fastq"), "right": (f.fastq(["b/2", "a/2"]), "fastq")},
        [("mates", "pair_declaration", f.pair())])
    fields = dict(pairs=f.selection("measurement", f.measurement("left", "verified_pair_count")))
    result = f.run(data, fields)
    assert result["facts"]["pairs"]["records"][0]["payload"]["value"] == 2
    validate(result, data, fields)


def test_saved_pair_rejects_duplicate_key_outside_selected_partial_members():
    data = f.build({"left": (f.fastq(["a/1", "a/1", "b/1"]), "fastq"),
                    "right": (f.fastq(["a/2", "b/2"]), "fastq")},
        [("mates", "pair_declaration", f.pair())])
    fields = dict(pairs=f.selection("measurement", f.measurement("left", "verified_pair_count")))
    result = f.run(data, fields)
    sheet = result["sheet"]
    joined = next(p for p in sheet["populations"] if p["population_key"] == "verified_read_pairs")
    assert joined["scope"] == "partial" and len(joined["member_record_refs"]) == 2
    validate(result, data, fields)
    parents = [next(p for p in sheet["populations"] if p["id"] == ref) for ref in joined["parent_population_refs"]]
    # Substitute a matching but ambiguous key while retaining the same saved
    # count, partial scope, valid references and recomputed whole-sheet hash.
    joined["member_record_refs"] = [p["member_record_refs"][0] for p in parents]
    result["components"]["calculations"]["sheet_sha256"] = json_sha256(sheet)
    with pytest.raises(FastqUtilsContractError):
        validate(result, data, fields)


def test_all_unavailable_jobs_have_typed_null_components_and_only_actual_refs():
    data = f.build({"reads": (b"@broken\n", "fastq")})
    sheet = f.sheet_for(data)
    # Select nonexisting populations from this actual selected document.
    before, after = f.population(key="hostile_in"), f.population(key="hostile_out")
    requests = [dict(calculation_id="c", method="composition_v1", population=before),
        dict(calculation_id="q", method="quality_phred_v1", population=before, quality_thresholds=[30]),
        dict(calculation_id="m", method="mapping_v1", population=before, input_population=None, read_key_rule=None),
        dict(calculation_id="r", method="retention_v1", comparison_kind="read_retention", before_population=before,
             after_population=after, before_measurement=f.measurement(metric="hostile_reads_in"), after_measurement=f.measurement(metric="hostile_reads_out")),
        dict(calculation_id="s", method="report_consistency_v1", report_measurement=f.measurement(metric="hostile_reads_in"), observed_measurement=f.measurement(metric="hostile_reads_out"))]
    params = resolve_calculation_inputs(sheet, requests=requests)
    result = calculate_fastqutils(sheet, parameters=params)
    assert len(result["components"]) == 14
    assert all(c["value"] is None and not c["operand_measurement_refs"] and not c["population_refs"] for c in result["components"])
    assert result["requirements"]


@pytest.mark.parametrize("kind", ["base_retention", "pair_retention"])
def test_provider_resolves_base_and_actual_pair_retention_with_explicit_lineage(kind):
    pair_mode = kind == "pair_retention"
    documents = {"before": (f.fastq(["a/1", "b/1"]), "fastq"), "after": (f.fastq(["a/1"]), "fastq")}
    declarations = []
    if pair_mode:
        documents.update(before_mate=(f.fastq(["b/2", "a/2"]), "fastq"), after_mate=(f.fastq(["a/2"]), "fastq"))
        declarations.extend([("before_pair", "pair_declaration", f.pair("before", "before_mate")),
                             ("after_pair", "pair_declaration", f.pair("after", "after_mate"))])
    before = f.population("before", "verified_read_pairs" if pair_mode else "fastq_bases", 0)
    after = f.population("after", "verified_read_pairs" if pair_mode else "fastq_bases", 1 if pair_mode else 0)
    lineage = dict(version="fastqutils_lineage_declaration_v1", before=before, after=after,
                   relation="subset_population", basis="explicit_assumption")
    declarations.append(("lineage", "lineage_declaration", lineage))
    data = f.build(documents, declarations)
    metric = "verified_pair_count" if pair_mode else "fastq_base_count"
    data[3]["calculation_requests"] = [dict(calculation_id="retain", method="retention_v1", comparison_kind=kind,
        before_population=before, after_population=after, before_measurement=f.measurement("before", metric), after_measurement=f.measurement("after", metric))]
    selected = "pair_retention_fraction" if pair_mode else "base_retention_fraction"
    fields = dict(retention=f.selection("component", dict(selection="semantic", calculation_id="retain", metric=selected, threshold=None),
                                         availability="available_value"))
    result = f.run(data, fields)
    payload = result["facts"]["retention"]["records"][0]["payload"]
    assert payload["value"] == .5 and payload["numerator"] == (1 if pair_mode else 4) and payload["denominator"] == (2 if pair_mode else 8)
    assert payload["lineage_basis"]["declaration"] == lineage
    validate(result, data, fields)


def test_paired_mapping_resolves_exact_pair_parents_as_four_actual_input_reads():
    sam = b"@HD\tVN:1.6\n@SQ\tSN:r\tLN:10\na\t65\tr\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\na\t133\t*\t0\t255\t*\t*\t0\t0\tACGT\tIIII\nb\t65\tr\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\nb\t129\tr\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\n"
    data = f.build({"left": (f.fastq(["a/1", "b/1"]), "fastq"), "right": (f.fastq(["b/2", "a/2"]), "fastq"),
                   "alignment": (sam, "sam_1_6")}, [("mates", "pair_declaration", f.pair())])
    data[3]["calculation_requests"] = [dict(calculation_id="mapped", method="mapping_v1", population=f.population("alignment", "bam_records"),
        input_population=f.population("left", "verified_read_pairs"), read_key_rule="first_token_slash_mate")]
    fields = dict(mapped=f.selection("component", dict(selection="semantic", calculation_id="mapped", metric="distinct_mapped_read_fraction", threshold=None),
        availability="available_value"))
    result = f.run(data, fields)
    payload = result["facts"]["mapped"]["records"][0]["payload"]
    assert payload["value"] == .75 and payload["numerator"] == 3 and payload["denominator"] == 4
    job = result["components"]["calculations"]["parameters"]["calculations"][0]
    assert len(job["population_refs"]) == 4
    validate(result, data, fields)
