"""Pure Ensembl BioMart contract controls with retained engineered captures."""
from copy import deepcopy
from dataclasses import replace
import base64
import hashlib
from urllib.parse import parse_qs, urlencode
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.ensembl_acquisition import (
    ARGUMENTS_SCHEMA, MAX_GENE_IDS, MAX_RESPONSE_BYTES, OPERATIONS, RESOURCE, TOOL, URL,
    ensembl_discovery_refs, ensembl_request_spec, ensembl_result, ensembl_result_schema, validate_ensembl_arguments,
    validate_ensembl_discovery, validate_ensembl_result,
)


REGISTRY = "source_" + "a" * 64
DATASETS = "source_" + "b" * 64
SOURCE_CONFIG = "source_" + "c" * 64
TARGET_CONFIG = "source_" + "d" * 64
RESULT = "source_" + "e" * 64
SOURCE_DATASET, TARGET_DATASET = "hsapiens_gene_ensembl", "mmusculus_gene_ensembl"
GENE = "ENSG00000139618"
CONTEXT = {"virtual_schema": "default", "mart": "ENSEMBL_MART_ENSEMBL"}
REGISTRY_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<MartRegistry nativeExtra="unchanged"><virtualSchema name="default">
<!-- keep this comment --><MartURLLocation name="ENSEMBL_MART_ENSEMBL"
 host="advertised.example.org" path="/do-not-follow" port="443"
 serverVirtualSchema="default" displayName="Ensembl Genes 116" visible="1" unknown="native"/>
</virtualSchema></MartRegistry>'''
DATASETS_TSV = (" \r\nTableSet\thsapiens_gene_ensembl\tHuman genes (GRCh38.p14)\t1\tGRCh38.p14\t200\t50000\tdefault\t2026-06-01\r\n"
    " \nTableSet\tmmusculus_gene_ensembl\tMouse genes (GRCm39)\t1\tGRCm39\t200\t50000\tdefault\t2026-06-01\n").encode()
ATTRIBUTES = ["ensembl_gene_id", "chromosome_name", "start_position", "end_position", "strand",
    "homologs_ensembl_gene_id", "homologs_chromosome_name", "homologs_start_position",
    "homologs_end_position", "homologs_strand", "mmusculus_homolog_ensembl_gene",
    "mmusculus_homolog_chromosome", "mmusculus_homolog_chrom_start", "mmusculus_homolog_chrom_end",
    "mmusculus_homolog_orthology_type", "mmusculus_homolog_perc_id",
    "mmusculus_homolog_perc_id_r1", "mmusculus_homolog_orthology_confidence"]


def arguments(selected_operation, **changes):
    operands = {
        "registry": {},
        "datasets": {**CONTEXT, "registry_source_ref": REGISTRY},
        "configuration": {**CONTEXT, "dataset": SOURCE_DATASET, "datasets_source_ref": DATASETS},
        "gene_homologies": {**CONTEXT, "source_dataset": SOURCE_DATASET, "target_dataset": TARGET_DATASET,
            "source_configuration_ref": SOURCE_CONFIG, "target_configuration_ref": TARGET_CONFIG,
            "source_attribute_style": "homologs", "gene_ids": [GENE],
            "include_identity_percentages": True, "include_confidence": True},
    }
    return {"operation": selected_operation, "resource": RESOURCE, **deepcopy(operands[selected_operation]),
        "max_bytes": 65536, **changes}


def configuration(dataset=SOURCE_DATASET, *, attributes=None):
    root = ET.Element("DatasetConfig", {"internalName": dataset, "displayName": "Native species label",
        "interfaces": "default", "version": "assembly-not-release", "softwareVersion": "0.6", "unknown": "0"})
    page = ET.SubElement(root, "AttributePage", {"internalName": "homologs", "unknown": "retained"})
    for name in ATTRIBUTES if attributes is None else attributes:
        ET.SubElement(page, "AttributeDescription", {"internalName": name,
            "displayName": "Native " + name, "unknown": "false"})
    filters = ET.SubElement(root, "FilterDescription", {"internalName": "id_list_limit_xrefs_filters"})
    ET.SubElement(filters, "Option", {"internalName": "ensembl_gene_id", "multipleValues": "1", "qualifier": "="})
    ET.SubElement(root, "UnknownNative", {"a": "1e-9999"}).text = "untouched & unicode β"
    return ET.tostring(root, encoding="utf-8")


def snapshot(selected, raw, **transport_changes):
    spec = ensembl_request_spec(selected)
    address = spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")
    headers = {"Accept": spec["media_type"]}
    request = {"method": spec["method"], "url": address, "headers": headers}
    if spec["body"] is not None:
        headers["Content-type"] = spec["content_type"]
        request.update(body_base64=base64.b64encode(spec["body"]).decode("ascii"),
            body_sha256=hashlib.sha256(spec["body"]).hexdigest())
    transport = {"status": 200, "headers": {"content-type": spec["media_type"]},
        "request": request, "effective_url": address,
        "request_policy": {"timeout_seconds": 30, "automatic_redirects": False},
        "body_complete": True, "retained_body_bytes": len(raw), "observed_body_bytes": len(raw),
        "declared_body_bytes": len(raw), "response_byte_limit": selected["max_bytes"], **transport_changes}
    return SourceSnapshot("ensembl", URL, deepcopy(selected), "2026-10-31T00:00:00+00:00",
        raw, spec["media_type"], transport)


def retained(selected, raw, **transport_changes):
    item = snapshot(selected, raw, **transport_changes)
    return {"snapshot": item, "artifact_ref": "artifact_" + hashlib.sha256(raw).hexdigest()}


def evidence():
    return {REGISTRY: retained(arguments("registry"), REGISTRY_XML),
        DATASETS: retained(arguments("datasets"), DATASETS_TSV),
        SOURCE_CONFIG: retained(arguments("configuration"), configuration()),
        TARGET_CONFIG: retained(arguments("configuration", dataset=TARGET_DATASET), configuration(TARGET_DATASET))}


def table(*rows, style="homologs", percentages=True, confidence=True, stamp=True):
    selected = arguments("gene_homologies", source_attribute_style=style,
        include_identity_percentages=percentages, include_confidence=confidence)
    xml = ET.fromstring(parse_qs(ensembl_request_spec(selected)["body"].decode())["query"][0])
    names = [node.attrib["name"] for node in xml.iter("Attribute")]
    header = "\t".join("Native " + name for name in names) + "\n"
    body = header + "".join("\t".join(row) + "\n" for row in rows)
    return (body + ("[success]\n" if stamp else "")).encode()


def row(*, source=GENE, target="ENSMUSG00000041147", kind="ortholog_one2one", start="1", end="10"):
    return [source, "13", start, end, "-1", target, "5", "20", "30", kind,
        "80.00000000000000001", "90", "1"]


def result(selected=None, raw=None, *, selected_evidence=None, **transport_changes):
    selected = arguments("gene_homologies") if selected is None else selected
    raw = table(row()) if raw is None else raw
    item = retained(selected, raw, **transport_changes)
    return ensembl_result(item["snapshot"], arguments=selected, source_ref=RESULT,
        artifact_ref=item["artifact_ref"], evidence=evidence() if selected_evidence is None else selected_evidence)


def codes(value):
    return {issue["code"] for issue in value["issues"]}


def replace_evidence(captured, source_ref, raw=None, selected=None, **transport_changes):
    previous = captured[source_ref]["snapshot"]
    captured[source_ref] = retained(previous.request if selected is None else selected,
        previous.content if raw is None else raw, **transport_changes)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_one_fixed_legacy_resource_and_finite_native_transport(operation):
    selected = arguments(operation)
    before = deepcopy(selected)
    spec = ensembl_request_spec(selected)
    assert validate_ensembl_arguments(selected) == selected and selected == before
    assert spec["service"] == "ensembl" and spec["url"] == URL
    assert spec["follow_redirects"] is False and spec["max_bytes"] == selected["max_bytes"]
    if operation == "gene_homologies":
        assert spec["method"] == "POST" and spec["params"] == {}
        assert spec["content_type"] == "application/x-www-form-urlencoded; charset=UTF-8"
    else:
        assert spec["method"] == "GET" and spec["body"] is None and spec["content_type"] is None
        assert spec["params"]["type"] == operation
        if operation != "registry":
            assert spec["params"]["virtualSchema"] == "default" and spec["params"]["mart"] == CONTEXT["mart"]
        if operation == "configuration":
            assert spec["params"]["dataset"] == SOURCE_DATASET and spec["params"]["interface"] == "default"


def test_generated_xml_has_only_selected_source_dataset_ids_and_native_ordered_fields():
    selected = arguments("gene_homologies", gene_ids=[GENE, GENE, "CUSTOM:gene.2"])
    spec = ensembl_request_spec(selected)
    root = ET.fromstring(parse_qs(spec["body"].decode())["query"][0])
    assert root.attrib == {"virtualSchemaName": "default", "formatter": "TSV", "header": "1",
        "uniqueRows": "0", "count": "0", "completionStamp": "1", "datasetConfigVersion": "0.6"}
    datasets = list(root.iter("Dataset"))
    assert len(datasets) == 1 and datasets[0].attrib == {"name": SOURCE_DATASET, "interface": "default"}
    assert list(root.iter("Filter"))[0].attrib == {"name": "ensembl_gene_id", "value": GENE + "," + GENE + ",CUSTOM:gene.2"}
    names = [node.attrib["name"] for node in root.iter("Attribute")]
    assert names[:5] == ["homologs_ensembl_gene_id", "homologs_chromosome_name",
        "homologs_start_position", "homologs_end_position", "homologs_strand"]
    assert names[9:] == ["mmusculus_homolog_orthology_type", "mmusculus_homolog_perc_id",
        "mmusculus_homolog_perc_id_r1", "mmusculus_homolog_orthology_confidence"]
    assert "limitStart" not in root.attrib and "limitSize" not in root.attrib


@pytest.mark.parametrize("operation,changes", [
    ("registry", {"resource": "ensembl_current"}), ("registry", {"endpoint": "https://example.org"}),
    ("registry", {"query": "arbitrary XML"}), ("registry", {"max_bytes": True}),
    ("registry", {"max_bytes": 0}), ("registry", {"max_bytes": MAX_RESPONSE_BYTES + 1}),
    ("datasets", {"virtual_schema": "default\n"}), ("datasets", {"mart": " choose"}),
    ("datasets", {"registry_source_ref": "artifact_" + "a" * 64}),
    ("configuration", {"dataset": "Human"}), ("configuration", {"dataset": SOURCE_DATASET + "\n"}),
    ("gene_homologies", {"source_dataset": TARGET_DATASET}),
    ("gene_homologies", {"target_configuration_ref": SOURCE_CONFIG}),
    ("gene_homologies", {"source_attribute_style": "auto"}),
    ("gene_homologies", {"include_identity_percentages": 1}),
    ("gene_homologies", {"include_confidence": "true"}),
    ("gene_homologies", {"gene_ids": []}), ("gene_homologies", {"gene_ids": [GENE] * (MAX_GENE_IDS + 1)}),
    ("gene_homologies", {"gene_ids": ["gene,other"]}), ("gene_homologies", {"gene_ids": ["gene\n"]}),
    ("gene_homologies", {"gene_ids": ["<Filter/>"]}), ("gene_homologies", {"gene_ids": [True]}),
    ("gene_homologies", {"offset": 10}), ("gene_homologies", {"limit_size": 10}),
])
def test_closed_typed_arguments_forbid_implicit_species_queries_fallbacks_and_fake_paging(operation, changes):
    with pytest.raises(ValueError):
        validate_ensembl_arguments(arguments(operation, **changes))


def test_retained_discovery_chain_preserves_native_identity_versions_and_does_not_follow_advertised_urls():
    selected, captured = arguments("gene_homologies"), evidence()
    before = deepcopy(captured)
    joined = validate_ensembl_discovery(selected, evidence=captured)
    assert [item["source_ref"] for item in joined["discovery_evidence"]] == [REGISTRY, DATASETS, SOURCE_CONFIG, TARGET_CONFIG]
    assert [item["dataset"] for item in joined["dataset_contexts"]] == [SOURCE_DATASET, TARGET_DATASET]
    assert [item["dataset_version"] for item in joined["dataset_contexts"]] == ["GRCh38.p14", "GRCm39"]
    assert all(item["version_meaning"] == "native_assembly_or_genebuild_not_ensembl_release"
        for item in joined["dataset_contexts"])
    assert joined["columns"][10]["denominator"] == "target_sequence"
    assert joined["columns"][11]["denominator"] == "query_sequence"
    assert captured == before


@pytest.mark.parametrize("operation,direct", [("registry", []), ("datasets", [REGISTRY]),
    ("configuration", [DATASETS]), ("gene_homologies", [SOURCE_CONFIG, TARGET_CONFIG])])
def test_only_direct_selected_source_refs_are_operand_refs_and_ancestry_witnesses_are_not_grants(operation, direct):
    assert ensembl_discovery_refs(arguments(operation)) == direct


@pytest.mark.parametrize("damage", ["missing_registry", "missing_datasets", "missing_source_config", "wrong_operation",
    "wrong_mart", "wrong_schema", "wrong_dataset", "duplicate_dataset", "wrong_interface",
    "config_identity", "config_interface", "missing_filter", "missing_attribute", "duplicate_attribute",
    "registry_duplicate", "registry_other_schema", "incomplete_capture", "http_error", "artifact", "actual_request"])
def test_selected_discovery_must_be_exact_complete_unambiguous_retained_native_evidence(damage):
    captured = evidence()
    if damage.startswith("missing_") and damage in {"missing_registry", "missing_datasets", "missing_source_config"}:
        del captured[{"missing_registry": REGISTRY, "missing_datasets": DATASETS,
            "missing_source_config": SOURCE_CONFIG}[damage]]
    elif damage == "wrong_operation":
        captured[SOURCE_CONFIG] = deepcopy(captured[REGISTRY])
    elif damage in {"wrong_mart", "wrong_schema", "wrong_dataset"}:
        key, value = {"wrong_mart": ("mart", "other_mart"), "wrong_schema": ("virtual_schema", "other"),
            "wrong_dataset": ("dataset", TARGET_DATASET)}[damage]
        replace_evidence(captured, SOURCE_CONFIG, selected=arguments("configuration", **{key: value}))
    elif damage == "duplicate_dataset":
        replace_evidence(captured, DATASETS, DATASETS_TSV + DATASETS_TSV)
    elif damage == "wrong_interface":
        replace_evidence(captured, DATASETS, DATASETS_TSV.replace(b"\tdefault\t", b"\tother\t"))
    elif damage in {"config_identity", "config_interface", "missing_filter", "missing_attribute", "duplicate_attribute"}:
        raw = configuration()
        if damage == "config_identity":
            raw = raw.replace(SOURCE_DATASET.encode(), TARGET_DATASET.encode(), 1)
        elif damage == "config_interface":
            raw = raw.replace(b'interfaces="default"', b'interfaces="other"')
        elif damage == "missing_filter":
            raw = raw.replace(b'internalName="ensembl_gene_id" multipleValues', b'internalName="other_filter" multipleValues')
        elif damage == "missing_attribute":
            raw = configuration(attributes=[name for name in ATTRIBUTES if name != "mmusculus_homolog_perc_id"])
        else:
            raw = configuration(attributes=ATTRIBUTES + ["homologs_ensembl_gene_id"])
        replace_evidence(captured, SOURCE_CONFIG, raw)
    elif damage == "registry_duplicate":
        location = b'<MartURLLocation name="ENSEMBL_MART_ENSEMBL" serverVirtualSchema="default"/>'
        replace_evidence(captured, REGISTRY, REGISTRY_XML.replace(b"</virtualSchema>", location + b"</virtualSchema>"))
    elif damage == "registry_other_schema":
        replace_evidence(captured, REGISTRY, REGISTRY_XML.replace(b'="default"', b'="other"'))
    elif damage == "incomplete_capture":
        replace_evidence(captured, DATASETS, body_complete=False)
    elif damage == "http_error":
        replace_evidence(captured, DATASETS, status=503)
    elif damage == "artifact":
        captured[SOURCE_CONFIG]["artifact_ref"] = "artifact_" + "0" * 64
    else:
        captured[SOURCE_CONFIG]["snapshot"].transport["request"]["url"] += "&extra=1"
    with pytest.raises(ValueError):
        validate_ensembl_discovery(arguments("gene_homologies"), evidence=captured)


@pytest.mark.parametrize("style", ["base", "homologs"])
@pytest.mark.parametrize("percentages,confidence", [(False, False), (False, True), (True, False), (True, True)])
def test_caller_selected_native_aliases_and_optional_columns_are_never_automatically_substituted(style, percentages, confidence):
    selected = arguments("gene_homologies", source_attribute_style=style,
        include_identity_percentages=percentages, include_confidence=confidence)
    cells = row()[:10] + (row()[10:12] if percentages else []) + ([row()[12]] if confidence else [])
    value = result(selected, table(cells, style=style, percentages=percentages, confidence=confidence))
    assert value["issues"] == [] and len(value["columns"]) == len(cells)
    assert value["columns"][0]["attribute"] == ("homologs_" if style == "homologs" else "") + "ensembl_gene_id"
    assert validate_ensembl_result(value, evidence=evidence()) == value


def test_original_xml_unknown_elements_comments_entities_and_attribute_order_remain_available():
    value = result(arguments("registry"), REGISTRY_XML, selected_evidence={})
    assert value["native_text"].encode() == REGISTRY_XML and value["parse_state"] == "xml"
    schema = value["xml_document"]["children"][0]
    assert schema["children"][0]["tag"] == "#comment"
    assert schema["children"][1]["attributes"][-1] == {"name": "unknown", "value": "native"}
    assert value["discovery_evidence"] == [] and value["dataset_contexts"] == []
    assert validate_ensembl_result(value) == value


def test_tsv_order_duplicate_mappings_blank_targets_and_lexical_numbers_are_not_a_dictionary_conversion():
    missing = [GENE, "13", "1", "10", "1"] + [""] * 8
    rows = [row(), row(target="ENSMUSG00000000001", kind="ortholog_one2many"), row(), missing]
    raw = table(*rows).replace(b"\n", b"\r\n")
    value = result(raw=raw)
    actual = [item["cells"] for item in value["tsv_lines"] if item["role"] == "row"]
    assert actual == rows and value["native_text"].encode() == raw
    assert actual[0][10] == "80.00000000000000001" and actual[3][-1] == ""
    assert value["retained_row_count"] == 4 and value["requested_id_count"] == 1
    assert value["matching_population_count"] is None and value["population_coverage"] == "selected_response_only"
    assert value["native_completion"] == "reported_complete" and value["issues"] == []
    assert value["coordinate_convention"] == "native_one_based_inclusive"
    assert actual[0][2:5] == ["1", "10", "-1"] and actual[0][7:9] == ["20", "30"]
    assert "mapping" not in value and "reference_ref" not in value and "score" not in value


def test_repeated_requested_ids_count_operands_and_do_not_invent_repeated_native_results():
    selected = arguments("gene_homologies", gene_ids=[GENE, GENE, "UNKNOWN_ID"])
    value = result(selected)
    assert value["requested_id_count"] == 3 and value["retained_row_count"] == 1
    assert value["matching_population_count"] is None and value["native_pagination"] == "not_exposed"
    empty = result(raw=table())
    assert empty["retained_row_count"] == 0 and empty["native_completion"] == "reported_complete"
    assert empty["native_response_state"] == "data" and empty["issues"] == []


def test_native_one_to_one_type_is_not_a_claim_that_only_one_target_can_be_returned():
    rows = [row(), row(target="ENSMUSG00000000001")]
    value = result(raw=table(*rows))
    assert [line["cells"] for line in value["tsv_lines"] if line["role"] == "row"] == rows
    assert value["retained_row_count"] == 2 and value["issues"] == []


@pytest.mark.parametrize("damage", ["header_omitted", "header_reordered", "header_context_missing"])
def test_missing_or_mismatched_native_headers_cannot_turn_the_first_data_row_into_a_successful_empty_answer(damage):
    raw, captured = table(row()), evidence()
    if damage == "header_omitted":
        raw = raw.split(b"\n", 1)[1]
    elif damage == "header_reordered":
        lines = raw.split(b"\n")
        cells = lines[0].split(b"\t")
        cells[5], cells[6] = cells[6], cells[5]
        lines[0] = b"\t".join(cells)
        raw = b"\n".join(lines)
    else:
        root = ET.fromstring(configuration())
        for node in root.iter("AttributeDescription"):
            del node.attrib["displayName"]
        replace_evidence(captured, SOURCE_CONFIG, ET.tostring(root, encoding="utf-8"))
    value = result(raw=raw, selected_evidence=captured)
    assert value["tsv_lines"][0]["role"] == "unclassified"
    assert value["representation_state"] == "partial" and value["native_text"].encode() == raw
    assert ("native_header_context_missing" if damage == "header_context_missing" else
        "native_header_context_conflict") in codes(value)


def test_native_pointer_header_resolution_does_not_substitute_the_selected_attribute_alias():
    captured, raw = evidence(), table(row())
    root = ET.fromstring(configuration())
    for node in root.iter("AttributeDescription"):
        name = node.attrib["internalName"]
        if name.startswith("homologs_"):
            del node.attrib["displayName"]
            node.attrib.update(pointerDataset=SOURCE_DATASET, pointerInterface="default",
                pointerAttribute=name[len("homologs_"):])
            raw = raw.replace(("Native " + name).encode(), ("Native " + name[len("homologs_"):]).encode())
    replace_evidence(captured, SOURCE_CONFIG, ET.tostring(root, encoding="utf-8"))
    value = result(raw=raw, selected_evidence=captured)
    assert value["columns"][0]["attribute"] == "homologs_ensembl_gene_id"
    assert value["columns"][0]["native_display_name"] == "Native ensembl_gene_id"
    assert value["issues"] == []


def test_one_unassociated_requested_header_position_qualifies_the_answer_even_when_all_other_labels_match():
    captured = evidence()
    root = ET.fromstring(configuration())
    for node in root.iter("AttributeDescription"):
        if node.attrib["internalName"] == "homologs_ensembl_gene_id":
            del node.attrib["displayName"]
    replace_evidence(captured, SOURCE_CONFIG, ET.tostring(root, encoding="utf-8"))
    value = result(selected_evidence=captured)
    assert value["representation_state"] == "partial"
    assert value["issues"] == [{"code": "native_header_context_missing", "pointer": "/tsv_lines/0/cells/0"}]
    assert value["columns"][0]["native_display_name"] is None
    assert value["tsv_lines"][1]["cells"] == row() and value["retained_row_count"] == 1
    assert validate_ensembl_result(value, evidence=captured) == value


@pytest.mark.parametrize("start_index,end_index,start,end,invalid", [
    (2, 3, "10", "1", True), (7, 8, "31", "30", True),
    (2, 3, "9" * 5000, "1" * 5000, True),
    (7, 8, "1" + "0" * 5000, "9" * 5000, True),
    (2, 3, "9" * 4999, "1" + "0" * 4999, False),
    (7, 8, "1" * 5000, "1" * 5000, False),
])
def test_native_source_and_target_gene_bounds_compare_exact_decimal_strings_without_int_coercion(
        start_index, end_index, start, end, invalid):
    cells = row()
    cells[start_index], cells[end_index] = start, end
    value = result(raw=table(cells))
    assert value["tsv_lines"][1]["cells"] == cells
    assert ("native_coordinate_invalid" in codes(value)) is invalid
    if invalid:
        assert {"code": "native_coordinate_invalid", "pointer": "/tsv_lines/1/cells/" + str(end_index)} in value["issues"]
        assert value["representation_state"] == "partial"
    else:
        assert value["issues"] == [] and value["representation_state"] == "complete"


def test_a_row_of_blank_cells_is_retained_as_a_row_with_missing_identity_not_dropped_as_spacing():
    value = result(raw=table([""] * 13))
    rows = [line for line in value["tsv_lines"] if line["role"] == "row"]
    assert len(rows) == 1 and rows[0]["cells"] == [""] * 13
    assert value["retained_row_count"] == 1 and "native_source_id_missing" in codes(value)


@pytest.mark.parametrize("damage,expected", [("missing_stamp", "native_completion_missing"),
    ("duplicate_stamp", "native_completion_conflict"), ("after_stamp", "native_data_after_completion"),
    ("short_row", "native_column_arity_conflict"), ("long_row", "native_column_arity_conflict"),
    ("missing_header", "native_header_missing"), ("wrong_source", "native_source_id_not_requested"),
    ("no_source", "native_source_id_missing"), ("coordinate", "native_coordinate_invalid"),
    ("strand", "native_strand_invalid"), ("association", "native_homology_association_incomplete")])
def test_native_query_qualifications_locate_the_original_cells_without_repair_or_clipping(damage, expected):
    cells = row()
    if damage == "missing_stamp":
        raw = table(cells, stamp=False)
    elif damage == "duplicate_stamp":
        raw = table(cells) + b"[success]\n"
    elif damage == "after_stamp":
        raw = table(cells) + "\t".join(cells).encode() + b"\n"
    elif damage == "short_row":
        raw = table(cells[:-1])
    elif damage == "long_row":
        raw = table(cells + ["unknown"])
    elif damage == "missing_header":
        raw = b"[success]\n"
    else:
        index, replacement = {"wrong_source": (0, "OTHER"), "no_source": (0, ""),
            "coordinate": (2, "0"), "strand": (4, "+"), "association": (5, "")}[damage]
        cells[index] = replacement
        raw = table(cells)
    value = result(raw=raw)
    assert expected in codes(value) and value["native_text"].encode() == raw
    assert value["representation_state"] in {"partial", "invalid"}
    assert validate_ensembl_result(value, evidence=evidence()) == value


@pytest.mark.parametrize("status", [200, 400, 429, 500])
def test_complete_native_query_errors_and_partial_rows_survive_independent_http_status(status):
    raw = table(row(), stamp=False) + b"Query ERROR: caught BioMart::Exception::Usage: Unknown attribute native_new_field"
    value = result(raw=raw, status=status, headers={"content-type": "text/plain", "retry-after": "30"})
    assert value["native_response_state"] == "error" and "native_error_response" in codes(value)
    assert value["retained_row_count"] == 1 and value["native_text"].encode() == raw
    assert value["response"]["http_status"] == status and value["response"]["retry_after"] == "30"
    assert ("http_not_success" in codes(value)) is (status != 200)
    assert value["response"]["body_complete"] is True and value["native_completion"] == "missing"


@pytest.mark.parametrize("raw,error", [(b"\xff", "invalid_native_utf8"),
    (b"<DatasetConfig", "invalid_native_xml"),
    (b'<!DOCTYPE DatasetConfig [<!ENTITY x "expanded">]><DatasetConfig>&x;</DatasetConfig>', "native_xml_doctype_forbidden"),
    (b'<!DOCTYPE DatasetConfig SYSTEM "https://do-not-open.example.org/data"><DatasetConfig/>', "native_xml_doctype_forbidden")])
def test_invalid_xml_and_utf8_retain_raw_identity_without_external_entity_resolution(raw, error):
    value = result(arguments("configuration"), raw)
    assert value["decode_error"] == error and value["parse_state"] == "decode_failed"
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    if error == "invalid_native_utf8":
        assert value["native_text"] is None
    else:
        assert value["native_text"].encode() == raw
    assert validate_ensembl_result(value, evidence=evidence()) == value


def test_native_configuration_error_text_is_preserved_even_with_http_success_and_xml_decode_failure():
    raw = b"Query ERROR: caught BioMart::Exception::Usage: configuration not found"
    value = result(arguments("configuration"), raw)
    assert value["native_response_state"] == "error" and value["native_text"].encode() == raw
    assert {"native_error_response", "invalid_native_xml"} <= codes(value)
    assert value["response"]["http_status"] == 200


def test_capture_completion_and_native_completion_are_separate_facts():
    value = result(body_complete=False, body_capture_failure="provider_response_byte_limit",
        observed_body_bytes=65537)
    assert value["native_completion"] == "reported_complete" and value["retained_row_count"] == 1
    assert {"response_incomplete", "response_capture_failure", "response_byte_limit_exceeded"} <= codes(value)
    value = result(retained_body_bytes=0)
    assert "transport_count_conflict" in codes(value)
    value = result(status=True, body_complete=1, retained_body_bytes=True)
    assert value["response"]["http_status"] is None and value["response"]["body_complete"] is None
    assert "transport_metadata_unavailable" in codes(value)


@pytest.mark.parametrize("damage", ["selected", "service", "url", "effective_url", "method", "body_base64",
    "body_hash", "accept", "duplicate_accept", "content_type", "redirects", "timeout_bool", "timeout_huge", "artifact", "source"])
def test_constructor_binds_selected_arguments_exact_form_body_raw_hash_and_transport_policy(damage):
    selected = arguments("gene_homologies")
    item = retained(selected, table(row()))
    snap, source = item["snapshot"], RESULT
    if damage == "selected":
        snap = replace(snap, request={**selected, "include_confidence": False})
    elif damage == "service":
        snap = replace(snap, service="other")
    elif damage == "url":
        snap = replace(snap, url="https://www.ensembl.org/biomart/martservice")
    elif damage == "effective_url":
        snap.transport["effective_url"] = "https://other.example.org/biomart/martservice"
    elif damage == "method":
        snap.transport["request"]["method"] = "GET"
    elif damage in {"body_base64", "body_hash"}:
        snap.transport["request"]["body_base64" if damage == "body_base64" else "body_sha256"] = "changed"
    elif damage in {"accept", "duplicate_accept", "content_type"}:
        headers = snap.transport["request"]["headers"]
        if damage == "duplicate_accept":
            headers["accept"] = "text/plain"
        else:
            headers["Accept" if damage == "accept" else "Content-type"] = "application/json"
    elif damage == "redirects":
        snap.transport["request_policy"]["automatic_redirects"] = True
    elif damage.startswith("timeout"):
        snap.transport["request_policy"]["timeout_seconds"] = True if damage == "timeout_bool" else 10 ** 500
    elif damage == "artifact":
        item["artifact_ref"] = "artifact_" + "0" * 64
    else:
        source = "artifact_" + "0" * 64
    with pytest.raises(ValueError):
        ensembl_result(snap, arguments=selected, source_ref=source, artifact_ref=item["artifact_ref"], evidence=evidence())


@pytest.mark.parametrize("damage", ["extra", "source_namespace", "artifact_namespace", "collapse_rows", "round_number",
    "completion", "denominator", "dataset_release", "evidence", "request_body", "row_count_bool", "timeout_huge"])
def test_closed_result_and_derived_native_qualifications_reject_tampering(damage):
    value = result(raw=table(row(), row()))
    if damage == "extra":
        value["new_workflow"] = True
    elif damage == "source_namespace":
        value["source_ref"] = value["raw_artifact_ref"]
    elif damage == "artifact_namespace":
        value["raw_artifact_ref"] = RESULT
    elif damage == "collapse_rows":
        del value["tsv_lines"][2]
    elif damage == "round_number":
        value["tsv_lines"][1]["cells"][10] = "80"
    elif damage == "completion":
        value["native_completion"] = "missing"
    elif damage == "denominator":
        value["columns"][10]["denominator"] = "query_sequence"
    elif damage == "dataset_release":
        value["dataset_contexts"][0]["dataset_version"] = "116"
    elif damage == "evidence":
        value["discovery_evidence"][0]["raw_artifact_ref"] = "artifact_" + "0" * 64
    elif damage == "request_body":
        value["response"]["request_body_sha256"] = "0" * 64
    elif damage == "row_count_bool":
        value["retained_row_count"] = True
    else:
        value["response"]["timeout_seconds"] = 10 ** 500
    with pytest.raises(ValueError):
        validate_ensembl_result(value, evidence=evidence())


@pytest.mark.parametrize("position,code", [("source", "ensembl_source_reference_invalid"),
    ("artifact", "ensembl_artifact_reference_invalid"),
    ("context_config", "ensembl_source_reference_invalid"),
    ("context_datasets", "ensembl_source_reference_invalid"),
    ("witness_source", "ensembl_source_reference_invalid"),
    ("witness_artifact", "ensembl_artifact_reference_invalid")])
def test_every_typed_result_reference_uses_full_namespace_matching_including_native_decode_failures(position, code):
    value = result(raw=b"\xff")
    if position in {"source", "artifact"}:
        key = "source_ref" if position == "source" else "raw_artifact_ref"
        value[key] += "\n"
    elif position.startswith("context"):
        key = "configuration_source_ref" if position == "context_config" else "datasets_source_ref"
        value["dataset_contexts"][0][key] += "\n"
    else:
        key = "source_ref" if position == "witness_source" else "raw_artifact_ref"
        value["discovery_evidence"][0][key] += "\n"
    with pytest.raises(ValueError, match=code):
        validate_ensembl_result(value, evidence=evidence())


def test_schema_copies_are_detached_and_source_file_namespaces_remain_closed():
    Draft202012Validator.check_schema(ARGUMENTS_SCHEMA)
    schema = ensembl_result_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["source_ref"]["x-reference-namespace"] == "source"
    assert schema["properties"]["raw_artifact_ref"]["x-reference-namespace"] == "artifact"
    schema["properties"]["source_ref"] = {"type": "number"}
    assert ensembl_result_schema()["properties"]["source_ref"]["type"] == "string"
