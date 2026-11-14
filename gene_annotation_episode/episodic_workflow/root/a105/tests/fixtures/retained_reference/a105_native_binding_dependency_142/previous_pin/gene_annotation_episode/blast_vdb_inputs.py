"""Supplied-data VDB sheets, three native parsers, and explicit metadata joins.

The closed interfaces are frozen in verification/tool_graders_blast_vdb_2026-10-26_312.
No acquisition, resource selection, confidence calculation or inferred alias occurs
here. Native source text is retained in each record so a saved bound sheet can
recheck extracted fields without opening its source_ref. External custody remains
the acquiring caller's responsibility. Identifiers compare namespace/value/version.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET

__all__ = ["populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo",
           "parse_blast_vdb_member_sequences", "parse_ncbi_gbseq_vdb_metadata",
           "bind_blast_vdb_metadata"]

_FORMATS = {"runinfo_csv", "blast_vdb_cmd_table", "ncbi_gbseq_xml", "ncbi_taxonomy_xml",
            "ncbi_datasets_assembly_json", "scoremat_asn_text", "supplied_explicit"}
_KINDS = {"read", "reference", "wgs_sequence", "unknown"}
_PAYLOAD = {"source_format", "source_version", "native_record", "source", "identifiers",
            "sequence", "functions", "taxid", "taxid_scope", "lineage", "assembly",
            "feature", "master_mapping", "extraction_method", "issues"}
_SHEET = {"schema", "search", "report_source", "query_binding", "dataset_records",
          "member_bindings", "sequence_identity_bindings", "feature_bindings",
          "reference_metadata", "target_context", "population_records"}


def _fail(code="record_value_invalid"):
    raise ValueError("blast_vdb_" + code)


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(x) for x in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    _fail("finite_json_required")


def _keys(value, fields, code="record_fields_invalid"):
    if type(value) is not dict or set(value) != set(fields.split() if isinstance(fields, str) else fields):
        _fail(code)


def _str(value):
    if not isinstance(value, str) or not value.strip():
        _fail()


def _int(value, minimum=0):
    if type(value) is not int or value < minimum:
        _fail()


def _num(value):
    if type(value) not in (int, float) or type(value) is float and not math.isfinite(value):
        _fail()


def _bool(value):
    if type(value) is not bool:
        _fail()


def _enum(value, values):
    if not isinstance(value, (str, int)) or type(value) is bool or value not in values:
        _fail()


def _nullable(value, validator):
    if value is not None:
        validator(value)


def _array(value, validator):
    if type(value) is not list:
        _fail()
    for item in value:
        validator(item)


def _digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        _fail()


def _pointer(value):
    if not isinstance(value, str) or (value != "" and not value.startswith("/")) or re.search(r"~(?![01])", value):
        _fail()


def _prov(value):
    _keys(value, "source_ref pointer")
    _str(value["source_ref"])
    _pointer(value["pointer"])


def _identity(value):
    _keys(value, "namespace value version")
    _str(value["namespace"])
    _str(value["value"])
    _nullable(value["version"], _str)


def _function(value):
    _keys(value, "namespace value")
    _str(value["namespace"])
    _str(value["value"])


def _interval(value):
    if type(value) is not list or len(value) != 2:
        _fail()
    _int(value[0]); _int(value[1], 1)
    if value[0] >= value[1]:
        _fail()


def _search_key(value):
    _keys(value, "artifact_key member_ordinal report_index search_pointer")
    _str(value["artifact_key"]); _nullable(value["member_ordinal"], _int)
    _int(value["report_index"]); _pointer(value["search_pointer"])


def _operand(value):
    _keys(value, "role artifact_key record_ordinal native_id native_title subject_ref molecule length selected_interval identity")
    _enum(value["role"], {"query", "subject", "database", "profile", "msa", "checkpoint"})
    _enum(value["molecule"], {"dna", "rna", "protein", "unknown"})
    for field in ("artifact_key", "native_id", "native_title", "subject_ref"):
        _nullable(value[field], _str)
    _nullable(value["record_ordinal"], _int)
    _nullable(value["length"], lambda n: _int(n, 1))
    _nullable(value["selected_interval"], _interval)
    _nullable(value["identity"], _identity)
    if value["selected_interval"] and value["length"] and value["selected_interval"][1] > value["length"]:
        _fail()


def _query(value):
    if value is None:
        return
    _keys(value, "operand axis_kind full_length coordinate_unit sequence_sha256 pssm_key master_mapping_ref")
    _operand(value["operand"]); _enum(value["axis_kind"], {"sequence", "pssm_master"})
    _int(value["full_length"], 1); _enum(value["coordinate_unit"], {"nt", "aa"})
    _nullable(value["sequence_sha256"], _digest); _nullable(value["pssm_key"], _str)
    _nullable(value["master_mapping_ref"], _prov)


def _snapshot(value):
    _keys(value, "release snapshot_id manifest_sha256")
    _nullable(value["release"], _str); _nullable(value["snapshot_id"], _str)
    _nullable(value["manifest_sha256"], _digest)


def _selected(value):
    _keys(value, "kind value")
    _enum(value["kind"], {"accession", "path", "alias"}); _str(value["value"])


def _sample_link(value):
    _keys(value, "sample_key sample_identifier biosample_identifier source")
    _str(value["sample_key"]); _identity(value["sample_identifier"])
    _nullable(value["biosample_identifier"], _identity); _prov(value["source"])


def _assembly_link(value):
    _keys(value, "assembly_identifier source")
    _identity(value["assembly_identifier"]); _prov(value["source"])


def _dataset(value):
    _keys(value, "dataset_key identifier dataset_type selected_input snapshot search_context run_identifiers sample_links assembly_links metadata_keys source")
    _str(value["dataset_key"]); _nullable(value["identifier"], _identity)
    _enum(value["dataset_type"], {"sra", "csra", "wgs", "unknown"})
    _selected(value["selected_input"]); _snapshot(value["snapshot"]); _prov(value["source"])
    context = value["search_context"]
    _keys(context, "search_key sra_mode include_filtered_reads subject_genetic_code input_pssm_key source query_extent")
    _search_key(context["search_key"]); _nullable(context["sra_mode"], lambda n: _enum(n, {0, 1, 2}))
    _nullable(context["include_filtered_reads"], _bool)
    _nullable(context["subject_genetic_code"], lambda n: _int(n, 1))
    _nullable(context["input_pssm_key"], _str); _prov(context["source"])
    extent = context["query_extent"]
    _keys(extent, "mode interval source"); _enum(extent["mode"], {"full", "interval", "unknown"})
    _nullable(extent["interval"], _interval); _nullable(extent["source"], _prov)
    if ((extent["mode"] == "interval") != (extent["interval"] is not None)
            or (extent["mode"] == "unknown") != (extent["source"] is None)):
        _fail()
    _array(value["run_identifiers"], _identity); _array(value["sample_links"], _sample_link)
    _array(value["assembly_links"], _assembly_link); _array(value["metadata_keys"], _str)


def _member(value):
    _keys(value, "search_key hit_ordinal description_ordinal native_description dataset_key member_kind member_identifier relationship read_identity reference_identity sample_key provenance")
    _search_key(value["search_key"]); _int(value["hit_ordinal"]); _int(value["description_ordinal"])
    _str(value["dataset_key"]); _enum(value["member_kind"], _KINDS)
    _identity(value["member_identifier"]); _nullable(value["sample_key"], _str)
    _enum(value["relationship"], {"reported_origin", "catalog_membership"}); _prov(value["provenance"])
    native = value["native_description"]
    _keys(native, "id accession title taxid")
    for field in ("id", "accession", "title"):
        _nullable(native[field], _str)
    _nullable(native["taxid"], lambda n: _int(n, 1))
    read, reference, kind = value["read_identity"], value["reference_identity"], value["member_kind"]
    if read is not None:
        _keys(read, "native_read_name spot_id read_index source")
        _str(read["native_read_name"]); _nullable(read["spot_id"], _str)
        _nullable(read["read_index"], _int); _prov(read["source"])
    if reference is not None:
        _keys(reference, "identifier full_length sequence_sha256 source")
        _identity(reference["identifier"]); _nullable(reference["full_length"], lambda n: _int(n, 1))
        _nullable(reference["sequence_sha256"], _digest); _prov(reference["source"])
    if (read is not None and kind != "read" or reference is not None and kind not in {"reference", "wgs_sequence"}):
        _fail()


def _member_key(value):
    _keys(value, "dataset_key member_kind member_identifier")
    _str(value["dataset_key"]); _enum(value["member_kind"], _KINDS); _identity(value["member_identifier"])


def _entity(value):
    _keys(value, "kind dataset_key member_identifier sample_key feature_identifier pssm_key")
    kind = value["kind"]
    _enum(kind, {"dataset", "sample", "member", "feature", "query_master"})
    for field in ("dataset_key", "sample_key", "pssm_key"):
        _nullable(value[field], _str)
    for field in ("member_identifier", "feature_identifier"):
        _nullable(value[field], _identity)
    required = {"dataset": {"dataset_key"}, "sample": {"dataset_key", "sample_key"},
                "member": {"dataset_key", "member_identifier"},
                "feature": {"dataset_key", "member_identifier", "feature_identifier"},
                "query_master": {"pssm_key"}}[kind]
    if {k for k, v in value.items() if k != "kind" and v is not None} != required:
        _fail()


def _lineage(value):
    _keys(value, "taxid rank name"); _int(value["taxid"], 1)
    _str(value["rank"]); _nullable(value["name"], _str)


def _issue(code, *, key=None, hit=None, hsp=None, pointer=None, **details):
    return {"code": code if code.startswith("blast_") else "blast_vdb_" + code,
            "search_key": deepcopy(key), "hit_ordinal": hit, "hsp_ordinal": hsp,
            "source_pointer": pointer, "details": details}


def _issue_shape(value):
    _keys(value, "code search_key hit_ordinal hsp_ordinal source_pointer details")
    _str(value["code"]); _nullable(value["search_key"], _search_key)
    _nullable(value["hit_ordinal"], _int); _nullable(value["hsp_ordinal"], _int)
    _nullable(value["source_pointer"], _pointer)
    if type(value["details"]) is not dict:
        _fail()


def _sequence(value):
    _keys(value, "symbols molecule length sha256")
    _str(value["symbols"]); _enum(value["molecule"], {"nt", "aa"})
    _int(value["length"], 1); _digest(value["sha256"])


def _assignment(value):
    _keys(value, "function evidence source"); _function(value["function"]); _prov(value["source"])
    _array(value["evidence"], lambda n: _keys(n, set(n)) if type(n) is dict else _fail())


def _feature(value):
    _keys(value, "feature_identifier key location segments strand partial5 partial3 codon_start genetic_code translation qualifiers member_sequence_metadata_key")
    _identity(value["feature_identifier"]); _str(value["key"]); _str(value["location"])
    _array(value["segments"], _interval)
    _nullable(value["strand"], lambda n: _enum(n, {-1, 1}))
    for field in ("partial5", "partial3"):
        _nullable(value[field], _bool)
    _nullable(value["codon_start"], lambda n: _enum(n, {1, 2, 3}))
    _nullable(value["genetic_code"], lambda n: _int(n, 1))
    _nullable(value["translation"], _str); _nullable(value["member_sequence_metadata_key"], _str)
    if type(value["qualifiers"]) is not list:
        _fail()
    for row in value["qualifiers"]:
        _keys(row, "name value"); _str(row["name"]); _nullable(row["value"], _str)


def _assembly(value):
    _keys(value, "identifier completeness_percent contamination_percent contig_count contig_n50 total_sequence_length method method_version source linkage_source")
    _identity(value["identifier"]); _prov(value["source"]); _prov(value["linkage_source"])
    for field in ("completeness_percent", "contamination_percent"):
        _nullable(value[field], _num)
    for field in ("contig_count", "contig_n50", "total_sequence_length"):
        _nullable(value[field], _int)
    _nullable(value["method"], _str); _nullable(value["method_version"], _str)


def _master(value):
    _keys(value, "pssm_key num_columns columns"); _str(value["pssm_key"]); _int(value["num_columns"], 1)
    if type(value["columns"]) is not list:
        _fail()
    for row in value["columns"]:
        _keys(row, "column master_position symbol"); _int(row["column"])
        _nullable(row["master_position"], _int); _str(row["symbol"])


def _payload(value):
    _enum(value["source_format"], _FORMATS); _nullable(value["source_version"], _str)
    if type(value["native_record"]) not in (dict, str):
        _fail()
    _prov(value["source"]); _array(value["identifiers"], _identity)
    _nullable(value["sequence"], _sequence); _array(value["functions"], _assignment)
    _nullable(value["taxid"], lambda n: _int(n, 1))
    _enum(value["taxid_scope"], {"entity_organism", "sample_context", "reported_subject", "unknown"})
    _array(value["lineage"], _lineage); _nullable(value["assembly"], _assembly)
    _nullable(value["feature"], _feature); _nullable(value["master_mapping"], _master)
    _enum(value["extraction_method"], {"native_parser", "supplied_explicit"})
    _array(value["issues"], _issue_shape)


def _metadata(value):
    _keys(value, _PAYLOAD | {"metadata_key", "entity", "linkage_source"})
    _str(value["metadata_key"]); _entity(value["entity"]); _nullable(value["linkage_source"], _prov)
    _payload(value)
    kind = value["entity"]["kind"]
    if (value["sequence"] is not None and kind not in {"member", "query_master"}
            or value["feature"] is not None and kind != "feature"
            or value["master_mapping"] is not None and kind != "query_master"):
        _fail()


def _feature_binding(value):
    _keys(value, "search_key hit_ordinal member_binding_index member_identifier feature_identifier feature_kind member_interval segments location_status strand genetic_code codon_start function feature_sequence_sha256 translation_metadata_key provenance")
    _search_key(value["search_key"]); _int(value["hit_ordinal"]); _int(value["member_binding_index"])
    _identity(value["member_identifier"]); _identity(value["feature_identifier"])
    _str(value["feature_kind"]); _interval(value["member_interval"]); _array(value["segments"], _interval)
    _enum(value["location_status"], {"exact", "partial", "unsupported"})
    _nullable(value["strand"], lambda n: _enum(n, {-1, 1}))
    _nullable(value["genetic_code"], lambda n: _int(n, 1))
    _nullable(value["codon_start"], lambda n: _enum(n, {1, 2, 3}))
    _nullable(value["function"], _function); _nullable(value["feature_sequence_sha256"], _digest)
    _nullable(value["translation_metadata_key"], _str); _prov(value["provenance"])


def _sequence_binding(value):
    _keys(value, "search_key binding"); _search_key(value["search_key"])
    row = value["binding"]
    _keys(row, "report_index hit_index kind sequence_group algorithm digest molecule sequence_length source_ref pointer linkage_source_ref linkage_pointer")
    _int(row["report_index"]); _int(row["hit_index"]); _int(row["sequence_length"], 1)
    _enum(row["kind"], {"full_sequence_digest"}); _enum(row["algorithm"], {"sha256"})
    _enum(row["molecule"], {"nt"}); _digest(row["digest"]); _str(row["sequence_group"])
    for field in ("source_ref", "linkage_source_ref"):
        _str(row[field])
    for field in ("pointer", "linkage_pointer"):
        _pointer(row[field])


def _population_entity(value):
    _keys(value, "kind member_key sequence_group_key feature_identifier sample_key", "population_entity_shape_invalid")
    kind = value["kind"]
    if kind not in {"read", "reference", "wgs_sequence", "unique_sequence", "feature", "sample"}:
        _fail("population_entity_shape_invalid")
    required = {"read": {"member_key"}, "reference": {"member_key"}, "wgs_sequence": {"member_key"},
                "unique_sequence": {"sequence_group_key"}, "feature": {"member_key", "feature_identifier"},
                "sample": {"sample_key"}}[kind]
    if {k for k, v in value.items() if k != "kind" and v is not None} != required:
        _fail("population_entity_shape_invalid")
    _nullable(value["member_key"], _member_key); _nullable(value["feature_identifier"], _identity)
    _nullable(value["sequence_group_key"], _str); _nullable(value["sample_key"], _str)
    if kind in _KINDS and value["member_key"]["member_kind"] != kind:
        _fail("population_entity_shape_invalid")


def _population(value):
    _keys(value, "population_key datasets count_unit scope total_count complete members function_counts function_members source native_record")
    _str(value["population_key"])
    _enum(value["count_unit"], {"reads", "references", "wgs_sequences", "unique_sequences", "features", "samples"})
    _enum(value["scope"], {"searched_population", "dataset_census", "supplied_subset"})
    _nullable(value["total_count"], _int); _bool(value["complete"]); _prov(value["source"])
    if type(value["native_record"]) is not dict:
        _fail()
    if type(value["datasets"]) is not list or any(value[k] is not None and type(value[k]) is not list for k in ("function_counts", "function_members")):
        _fail()
    for row in value["datasets"]:
        _keys(row, "dataset_key identifier snapshot sra_mode include_filtered_reads")
        _str(row["dataset_key"]); _nullable(row["identifier"], _identity); _snapshot(row["snapshot"])
        _nullable(row["sra_mode"], lambda n: _enum(n, {0, 1, 2})); _nullable(row["include_filtered_reads"], _bool)
    _nullable(value["members"], lambda rows: _array(rows, _population_entity))
    for row in value["function_counts"] or []:
        _keys(row, "function count assignment_scope source"); _function(row["function"]); _int(row["count"])
        _enum(row["assignment_scope"], {"whole_sequence", "feature", "sample"}); _prov(row["source"])
    for row in value["function_members"] or []:
        _keys(row, "function entities"); _function(row["function"]); _array(row["entities"], _population_entity)


def _token(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique(rows, field=None, code="duplicate_record_key"):
    values = [_token(row if field is None else row[field]) for row in rows]
    if len(values) != len(set(values)):
        _fail(code)


def _validate_sheet(sheet):
    _keys(sheet, _SHEET, "sheet_fields_invalid")
    if sheet["schema"] != "blast_vdb_search_sheet_v1":
        _fail("sheet_fields_invalid")
    search = sheet["search"]
    _keys(search, "search_key program_context stage iteration normalized row_map operand_binding reporting native issues", "search_fields_invalid")
    _search_key(search["search_key"])
    context = search["program_context"]
    _keys(context, "execution_program reported_program scientific_mode query_kind reference_kind native_version geometry_program", "search_fields_invalid")
    if context["execution_program"] not in {"blastn_vdb", "tblastn_vdb"} or context["scientific_mode"] != "database" or context["reference_kind"] not in {"vdb_read", "vdb_reference", "vdb_mixed"}:
        _fail("mode_required")
    normalized = search["normalized"]
    _keys(normalized, "schema mode resource format query search hits native issues", "search_fields_invalid")
    if normalized["schema"] != "blast_normalized_result_v1" or any(type(normalized[x]) is not dict for x in ("query", "search", "native")) or type(normalized["hits"]) is not list:
        _fail("search_fields_invalid")
    _keys(normalized["query"], "id title length", "search_fields_invalid")
    _keys(normalized["search"], "program version database parameters statistics request hit_array_present reported_hit_count", "search_fields_invalid")
    _keys(search["reporting"], "native_hit_array_present native_hit_count requested_hit_limit requested_hsp_limit native_returncode producer_complete", "search_fields_invalid")
    _bool(search["reporting"]["native_hit_array_present"])
    for field in ("native_hit_count", "requested_hit_limit", "requested_hsp_limit"):
        _nullable(search["reporting"][field], _int)
    _nullable(search["reporting"]["producer_complete"], _bool)
    if search["reporting"]["native_returncode"] is not None and type(search["reporting"]["native_returncode"]) is not int:
        _fail("search_fields_invalid")
    if type(search["native"]) is not dict or type(search["issues"]) is not list or type(search["row_map"]) is not list:
        _fail("search_fields_invalid")
    if any(type(i) is not dict or not isinstance(i.get("code"), str) or not i["code"] for i in search["issues"]):
        _fail("search_fields_invalid")
    _nullable(search["operand_binding"], _operand)
    source = sheet["report_source"]
    _keys(source, "artifact_key artifact_ref member_ordinal member_sha256")
    _str(source["artifact_key"]); _str(source["artifact_ref"])
    _nullable(source["member_ordinal"], _int); _nullable(source["member_sha256"], _digest)
    if (source["member_ordinal"] is None) != (source["member_sha256"] is None):
        _fail()
    _query(sheet["query_binding"])
    for name, validator in (("dataset_records", _dataset), ("member_bindings", _member),
                            ("sequence_identity_bindings", _sequence_binding), ("feature_bindings", _feature_binding),
                            ("reference_metadata", _metadata)):
        _array(sheet[name], validator)
    _nullable(sheet["population_records"], lambda rows: _array(rows, _population))
    for name, field in (("dataset_records", "dataset_key"), ("reference_metadata", "metadata_key"), ("population_records", "population_key")):
        _unique(sheet[name] or [], field)
    for name in ("member_bindings", "sequence_identity_bindings", "feature_bindings"):
        _unique(sheet[name], code="duplicate_binding")
    datasets = {d["dataset_key"] for d in sheet["dataset_records"]}
    metadata = {d["metadata_key"] for d in sheet["reference_metadata"]}
    for row in sheet["member_bindings"] + [r["entity"] for r in sheet["reference_metadata"]] + [d for p in sheet["population_records"] or [] for d in p["datasets"]]:
        if row["dataset_key"] is not None and row["dataset_key"] not in datasets:
            _fail("unknown_dataset_key")
    for row in sheet["dataset_records"]:
        if any(k not in metadata for k in row["metadata_keys"]):
            _fail("unknown_metadata_key")
    for row in sheet["feature_bindings"]:
        if row["member_binding_index"] >= len(sheet["member_bindings"]):
            _fail("binding_index_out_of_range")
        if row["translation_metadata_key"] is not None and row["translation_metadata_key"] not in metadata:
            _fail("unknown_metadata_key")
    for row in sheet["reference_metadata"]:
        if row["feature"] and row["feature"]["member_sequence_metadata_key"] is not None and row["feature"]["member_sequence_metadata_key"] not in metadata:
            _fail("unknown_metadata_key")
    target = sheet["target_context"]
    if target is not None:
        _keys(target, "query_operand taxid lineage independent_of_search source")
        _operand(target["query_operand"]); _nullable(target["taxid"], lambda n: _int(n, 1))
        _array(target["lineage"], _lineage); _nullable(target["independent_of_search"], _bool); _prov(target["source"])


def populate_blast_vdb_sheet(search, *, report_source, query_binding, dataset_records,
        member_bindings, sequence_identity_bindings, feature_bindings, reference_metadata,
        target_context=None, population_records=None) -> dict:
    """Retain the entire search and explicit inputs after closed-shape validation."""
    sheet = _copy(dict(schema="blast_vdb_search_sheet_v1", search=search, report_source=report_source,
        query_binding=query_binding, dataset_records=dataset_records, member_bindings=member_bindings,
        sequence_identity_bindings=sequence_identity_bindings, feature_bindings=feature_bindings,
        reference_metadata=reference_metadata, target_context=target_context, population_records=population_records))
    _validate_sheet(sheet)
    return sheet


def _parsed_start(contents, source_ref, version, format_name, context=None):
    if type(contents) is not bytes:
        _fail()
    _str(source_ref); _nullable(version, _str)
    result = dict(schema="blast_vdb_metadata_parse_v1", format=format_name, source_ref=source_ref,
        input_identity={"sha256": hashlib.sha256(contents).hexdigest(), "size_bytes": len(contents)},
        native_text=None, parse_context=_copy(context), records=[], issues=[])
    try:
        result["native_text"] = contents.decode("utf-8")
    except UnicodeError:
        result["issues"].append(_issue("format_unsupported", encoding="utf-8"))
    return result


def _id(namespace, value, version=None):
    return {"namespace": namespace, "value": value, "version": version}


def _emit(result, version, kind, native, *, identifiers=(), parent=None, dataset=None,
          member=None, sample=None, feature=None, sequence=None, taxid=None, taxid_scope="unknown",
          feature_data=None, functions=(), issues=()):
    ordinal = len(result["records"])
    key = {"source_ref": result["source_ref"], "record_ordinal": ordinal}
    source = {"source_ref": result["source_ref"], "pointer": f"/records/{ordinal}"}
    row = dict(record_key=key, source_entity=dict(kind=kind, identifiers=deepcopy(list(identifiers)),
        parent_record_key=deepcopy(parent), dataset_identifier=deepcopy(dataset), member_identifier=deepcopy(member),
        sample_identifier=deepcopy(sample), feature_identifier=deepcopy(feature), pssm_key=None),
        source_format=result["format"], source_version=version, native_record=deepcopy(native), source=source,
        identifiers=deepcopy(list(identifiers)), sequence=deepcopy(sequence), functions=deepcopy(list(functions)),
        taxid=taxid, taxid_scope=taxid_scope, lineage=[], assembly=None, feature=deepcopy(feature_data),
        master_mapping=None, extraction_method="native_parser", issues=deepcopy(list(issues)))
    result["records"].append(row)
    return row


def _native_integer(value):
    return int(value) if isinstance(value, str) and re.fullmatch(r"[0-9]+", value) else None


def _symbols(value, length=None, molecule="nt"):
    if not isinstance(value, str):
        return None
    symbols = "".join(value.splitlines()).upper()
    pattern = r"[ACGTURYSWKMBDHVN]+" if molecule == "nt" else r"[A-Z*]+"
    if not symbols or not symbols.isascii() or re.fullmatch(pattern, symbols) is None or length is not None and len(symbols) != length:
        return None
    return {"symbols": symbols, "molecule": molecule, "length": len(symbols),
            "sha256": hashlib.sha256(symbols.encode("ascii")).hexdigest()}


def parse_ncbi_sra_runinfo(contents: bytes, *, source_ref: str, source_version: str | None) -> dict:
    """Parse literal RunInfo CSV relationships; TaxID remains sample context.

    Native identifier namespaces are NCBI.SRA.Run, NCBI.SRA.Sample,
    NCBI.BioSample, NCBI.SRA.Experiment and NCBI.BioProject; values are unchanged.
    Counts retain their own spots/bases units and never populate read counts.
    """
    result = _parsed_start(contents, source_ref, source_version, "runinfo_csv")
    if result["native_text"] is None:
        return result
    reader = csv.reader(io.StringIO(result["native_text"], newline=""), strict=True)
    try:
        headers = next(reader)
        if len(headers) != len(set(headers)) or not headers or any(not h for h in headers):
            raise ValueError("headers")
        previous = reader.line_num
        for ordinal, values in enumerate(reader):
            span = [previous + 1, reader.line_num]; previous = reader.line_num
            if not values:
                continue
            if len(values) != len(headers):
                result["issues"].append(_issue("metadata_native_extraction_unverified", row_ordinal=ordinal, line_span=span, values=values))
                continue
            cells = dict(zip(headers, values))
            ids = {name: _id(namespace, cells[name]) for name, namespace in
                   (("Run", "NCBI.SRA.Run"), ("Sample", "NCBI.SRA.Sample"), ("BioSample", "NCBI.BioSample"),
                    ("Experiment", "NCBI.SRA.Experiment"), ("BioProject", "NCBI.BioProject")) if cells.get(name)}
            taxid = _native_integer(cells.get("TaxID"))
            taxid = taxid if taxid else None
            native = {"input_text": result["native_text"], "row_ordinal": ordinal, "line_span": span,
                      "headers": headers, "values": values, "fields": cells,
                      "counts": {n: _native_integer(cells.get(n)) for n in ("spots", "bases")}}
            parent = _emit(result, source_version, "dataset", native, identifiers=ids.values(),
                dataset=ids.get("Run"), taxid=taxid, taxid_scope="sample_context")
            if "Sample" in ids or "BioSample" in ids:
                _emit(result, source_version, "sample", native, identifiers=[ids[k] for k in ("Sample", "BioSample") if k in ids],
                    parent=parent["record_key"], dataset=ids.get("Run"), sample=ids.get("Sample"),
                    taxid=taxid, taxid_scope="sample_context")
    except (csv.Error, StopIteration, ValueError) as error:
        result["issues"].append(_issue("metadata_native_extraction_unverified", native_error=type(error).__name__))
    return result


def _extraction_context(value):
    _keys(value, "dataset_key selected_input snapshot entry_identifiers native_returncode producer_complete include_filtered_reads reference_selection outfmt source")
    _str(value["dataset_key"]); _selected(value["selected_input"]); _snapshot(value["snapshot"])
    _array(value["entry_identifiers"], _identity); _prov(value["source"])
    if value["native_returncode"] is not None and type(value["native_returncode"]) is not int:
        _fail()
    for field in ("producer_complete", "include_filtered_reads", "reference_selection"):
        _nullable(value[field], _bool)
    if value["outfmt"] != "%i\t%a\t%l\t%s" or any(i["value"] == "all" for i in value["entry_identifiers"]):
        _fail()


def _sra_equal(a, b):
    return (a == b or a["version"] == b["version"] and
            ((a["value"].startswith("gnl|SRA|") and a["value"][8:] == b["value"])
             or (b["value"].startswith("gnl|SRA|") and b["value"][8:] == a["value"])))


def parse_blast_vdb_member_sequences(contents: bytes, *, source_ref: str,
        source_version: str, extraction_context: dict) -> dict:
    """Read the exact four-column specific-entry output, never execute the helper."""
    _str(source_version); context = _copy(extraction_context); _extraction_context(context)
    result = _parsed_start(contents, source_ref, source_version, "blast_vdb_cmd_table", context)
    if result["native_text"] is None:
        return result
    seen = set()
    for ordinal, line in enumerate(result["native_text"].splitlines()):
        cells = line.split("\t")
        if len(cells) != 4 or any(c == "N/A" or not c for c in cells):
            result["issues"].append(_issue("metadata_native_extraction_unverified", row_ordinal=ordinal, values=cells))
            continue
        native_id, accession, size, symbols = cells
        length = _native_integer(size)
        sequence = _symbols(symbols, length) if length else None
        ids = [_id("NCBI.Seq-id", native_id), _id("NCBI.Seq-id", accession)]
        ids = list({_token(i): i for i in ids}.values())
        matches = [i for i in context["entry_identifiers"] if i["value"] in (native_id, accession)
                   or native_id.startswith("gnl|SRA|") and i["value"] == native_id[8:]]
        issues = []
        if sequence is None:
            issues.append(_issue("sequence_length_conflict", row_ordinal=ordinal, reported_length=size))
        if len(matches) != 1:
            issues.append(_issue("member_identifier_unlinked", row_ordinal=ordinal))
        else:
            # The exact selected identity is explicit invocation data. Its raw
            # spelling must appear in this output; no namespace is inferred.
            if matches[0] not in ids:
                ids.append(deepcopy(matches[0]))
            seen.add(_token(matches[0]))
        native = {"input_text": result["native_text"], "row_ordinal": ordinal, "line": ordinal + 1,
                  "values": cells, "parse_context": context}
        _emit(result, source_version, "member", native, identifiers=ids,
            member=matches[0] if len(matches) == 1 else ids[0], sequence=sequence, issues=issues)
    missing = [i for i in context["entry_identifiers"] if _token(i) not in seen]
    if missing or context["native_returncode"] != 0 or context["producer_complete"] is not True:
        result["issues"].append(_issue("execution_completion_unqualified", missing_entries=missing,
            native_returncode=context["native_returncode"], producer_complete=context["producer_complete"]))
    return result


def _xml_bool(element):
    if element is None:
        return None
    value = element.get("value", element.text)
    return {"true": True, "false": False}.get(value)


def _gb_location(location):
    match = re.fullmatch(r"(?:(complement)\()?([1-9][0-9]*)\.\.([1-9][0-9]*)(\))?", location or "")
    if not match or bool(match[1]) != bool(match[4]):
        return [], None
    a, b = int(match[2]), int(match[3])
    if a > b:
        return [], None
    return [[a - 1, b]], -1 if match[1] else 1


def parse_ncbi_gbseq_vdb_metadata(contents: bytes, *, source_ref: str,
        source_version: str | None) -> dict:
    """Retain GBSeq records/features; support exact contiguous local locations.

    Accession-version is preserved whole as NCBI.Nucleotide value (version null,
    since the native spelling already contains it). Feature custody identity is
    NCBI.GBSeq.Feature:<source_ref>#GBSeq/N/feature/M, never a global locus tag.
    """
    result = _parsed_start(contents, source_ref, source_version, "ncbi_gbseq_xml")
    text = result["native_text"]
    if text is None:
        return result
    if re.search(r"<!ENTITY", text, re.I):
        result["issues"].append(_issue("format_unsupported", xml_entities=True)); return result
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        result["issues"].append(_issue("metadata_native_extraction_unverified", position=list(error.position))); return result
    records = [root] if root.tag == "GBSeq" else list(root) if root.tag == "GBSet" else []
    if root.tag not in {"GBSeq", "GBSet"}:
        result["issues"].append(_issue("format_unsupported", root_tag=root.tag))
    for ordinal, record in enumerate(records):
        if record.tag != "GBSeq":
            result["issues"].append(_issue("format_unsupported", record_ordinal=ordinal)); continue
        accession = record.findtext("GBSeq_accession-version")
        identifier = _id("NCBI.Nucleotide", accession) if accession else None
        ids = [identifier] if identifier else []
        ids += [_id("NCBI.Seq-id", e.text) for e in record.findall("GBSeq_other-seqids/GBSeqid") if e.text]
        native = {"input_text": text, "gbseq_ordinal": ordinal, "feature_ordinal": None,
                  "record_xml": ET.tostring(record, encoding="unicode")}
        moltype = record.findtext("GBSeq_moltype")
        molecule = "aa" if moltype == "AA" else "nt" if moltype in {"DNA", "RNA", "mRNA", "tRNA", "rRNA", "ncRNA", "tmRNA"} else None
        length = _native_integer(record.findtext("GBSeq_length"))
        symbols = record.findtext("GBSeq_sequence")
        sequence = _symbols(symbols, length, molecule) if length and molecule is not None else None
        issues = []
        if symbols is not None and sequence is None:
            issues.append(_issue("sequence_length_conflict", gbseq_ordinal=ordinal))
        features = record.findall("GBSeq_feature-table/GBFeature")
        taxa = set()
        for feature in features:
            if feature.findtext("GBFeature_key") == "source":
                for q in feature.findall("GBFeature_quals/GBQualifier"):
                    value = q.findtext("GBQualifier_value", "")
                    if q.findtext("GBQualifier_name") == "db_xref" and re.fullmatch(r"taxon:[1-9][0-9]*", value):
                        taxa.add(int(value.split(":")[1]))
        if len(taxa) > 1:
            issues.append(_issue("taxonomy_lineage_conflict", taxids=sorted(taxa)))
        parent = _emit(result, source_version, "member", native, identifiers=ids, member=identifier,
            sequence=sequence, taxid=next(iter(taxa)) if len(taxa) == 1 else None,
            taxid_scope="entity_organism", issues=issues)
        for f, feature in enumerate(features):
            fid = _id("NCBI.GBSeq.Feature", f"{source_ref}#GBSeq/{ordinal}/feature/{f}")
            qualifiers = []; fissues = []
            for qordinal, q in enumerate(feature.findall("GBFeature_quals/GBQualifier")):
                name, value = q.findtext("GBQualifier_name", ""), q.findtext("GBQualifier_value")
                if not name.strip():
                    fissues.append(_issue("metadata_native_extraction_unverified", gbseq_ordinal=ordinal,
                        feature_ordinal=f, qualifier_ordinal=qordinal, missing_fields=["qualifier_name"]))
                    continue
                qualifiers.append({"name": name, "value": value if value and value.strip() else None})
            location = feature.findtext("GBFeature_location", "")
            segments, strand = _gb_location(location)
            # GBInterval is a redundant native source representation when
            # supplied, not permission to replace an unsupported location.
            intervals = feature.findall("GBFeature_intervals/GBInterval")
            if segments and intervals:
                compatible = len(intervals) == 1
                for interval in intervals:
                    first = _native_integer(interval.findtext("GBInterval_from"))
                    last = _native_integer(interval.findtext("GBInterval_to"))
                    remote = interval.findtext("GBInterval_accession")
                    comp = _xml_bool(interval.find("GBInterval_iscomp"))
                    compatible &= (first is not None and last is not None and first > 0 and last > 0
                        and [[min(first, last) - 1, max(first, last)]] == segments
                        and remote in (None, accession) and _xml_bool(interval.find("GBInterval_interbp")) is not True
                        and (comp is None or comp == (strand == -1)))
                if not compatible:
                    segments, strand = [], None
                    fissues.append(_issue("feature_location_conflict", gbseq_ordinal=ordinal, feature_ordinal=f))
            if not segments:
                fissues.append(_issue("feature_location_unavailable", gbseq_ordinal=ordinal, feature_ordinal=f, location=location))
            values = lambda name: [q["value"] for q in qualifiers if q["name"] == name]
            def scalar(name):
                v = values(name)
                return v[0] if len(v) == 1 else None
            codon = _native_integer(scalar("codon_start")); code = _native_integer(scalar("transl_table"))
            native_key = feature.findtext("GBFeature_key")
            data = dict(feature_identifier=fid, key=native_key, location=location,
                segments=segments, strand=strand, partial5=_xml_bool(feature.find("GBFeature_partial5")),
                partial3=_xml_bool(feature.find("GBFeature_partial3")), codon_start=codon if codon in (1, 2, 3) else None,
                genetic_code=code if code else None, translation=scalar("translation"), qualifiers=qualifiers,
                member_sequence_metadata_key=None)
            if not native_key or not native_key.strip() or not location or not location.strip():
                data = None
                fissues.append(_issue("metadata_native_extraction_unverified", gbseq_ordinal=ordinal, feature_ordinal=f,
                                      missing_fields=[n for n, v in (("key", native_key), ("location", location)) if not v]))
            fnative = {**native, "feature_ordinal": f, "feature_xml": ET.tostring(feature, encoding="unicode")}
            row = _emit(result, source_version, "feature", fnative, identifiers=[fid], parent=parent["record_key"],
                member=identifier, feature=fid, feature_data=data, issues=fissues)
            for q in qualifiers:
                if q["name"] in {"EC_number", "product", "function"} and q["value"]:
                    row["functions"].append({"function": {"namespace": "EC" if q["name"] == "EC_number" else "NCBI.GBSeq." + q["name"],
                        "value": q["value"]}, "evidence": [{"qualifier": deepcopy(q)}], "source": deepcopy(row["source"])})
    return result


def _record_key(value):
    _keys(value, "source_ref record_ordinal", "parsed_record_key_invalid")
    _str(value["source_ref"]); _int(value["record_ordinal"])


def _parsed_record(value):
    _keys(value, _PAYLOAD | {"record_key", "source_entity"}); _record_key(value["record_key"]); _payload(value)
    entity = value["source_entity"]
    _keys(entity, "kind identifiers parent_record_key dataset_identifier member_identifier sample_identifier feature_identifier pssm_key")
    _enum(entity["kind"], {"dataset", "sample", "member", "feature", "query_master"})
    _array(entity["identifiers"], _identity); _nullable(entity["parent_record_key"], _record_key)
    for field in ("dataset_identifier", "member_identifier", "sample_identifier", "feature_identifier"):
        _nullable(entity[field], _identity)
    _nullable(entity["pssm_key"], _str)


def _reparse(result):
    """Return supported native re-extraction; null denotes an unavailable port."""
    text = result["native_text"]
    if text is None:
        return None
    versions = {row["source_version"] for row in result["records"]}
    if len(versions) > 1:
        return None
    version = next(iter(versions), None)
    kwargs = dict(source_ref=result["source_ref"], source_version=version)
    if result["format"] == "runinfo_csv" and result["parse_context"] is None:
        return parse_ncbi_sra_runinfo(text.encode("utf-8"), **kwargs)
    if result["format"] == "ncbi_gbseq_xml" and result["parse_context"] is None:
        return parse_ncbi_gbseq_vdb_metadata(text.encode("utf-8"), **kwargs)
    if result["format"] == "blast_vdb_cmd_table" and version is not None and result["parse_context"] is not None:
        try:
            return parse_blast_vdb_member_sequences(text.encode("utf-8"), extraction_context=result["parse_context"], **kwargs)
        except ValueError:
            return None
    return None


def _recheck_metadata(row):
    if row["extraction_method"] == "supplied_explicit":
        return True
    native = row["native_record"]
    if not isinstance(native, dict) or not isinstance(native.get("input_text"), str):
        return False
    result = dict(native_text=native["input_text"], format=row["source_format"], source_ref=row["source"]["source_ref"],
                  records=[row], parse_context=native.get("parse_context"))
    parsed = _reparse(result)
    if parsed is None:
        return False
    matches = [p for p in parsed["records"] if p["source"] == row["source"]]
    if len(matches) != 1:
        return False
    actual = deepcopy(matches[0])
    if actual["feature"] is not None and row["feature"] is not None:
        actual["feature"]["member_sequence_metadata_key"] = row["feature"]["member_sequence_metadata_key"]
    return all(actual[k] == row[k] for k in _PAYLOAD)


def bind_blast_vdb_metadata(parsed_results, *, dataset_records, member_bindings,
        query_binding, bindings) -> dict:
    """Bind explicit candidates; no successful join promotes catalogue origins."""
    parsed_results, dataset_records, member_bindings, query_binding, bindings = _copy(
        [parsed_results, dataset_records, member_bindings, query_binding, bindings])
    if type(parsed_results) is not list or type(bindings) is not list:
        _fail()
    _array(dataset_records, _dataset); _array(member_bindings, _member); _query(query_binding)
    _unique(dataset_records, "dataset_key")
    datasets = {d["dataset_key"]: d for d in dataset_records}
    records, qualified = {}, {}
    for result in parsed_results:
        _keys(result, "schema format source_ref input_identity native_text parse_context records issues")
        if result["schema"] != "blast_vdb_metadata_parse_v1":
            _fail()
        _enum(result["format"], _FORMATS); _str(result["source_ref"])
        _keys(result["input_identity"], "sha256 size_bytes"); _digest(result["input_identity"]["sha256"]); _int(result["input_identity"]["size_bytes"])
        if result["native_text"] is not None and type(result["native_text"]) is not str:
            _fail()
        _array(result["records"], _parsed_record); _array(result["issues"], _issue_shape)
        rebuilt = _reparse(result)
        native_matches = rebuilt is not None and rebuilt["input_identity"] == result["input_identity"]
        for emitted, row in enumerate(result["records"]):
            if row["record_key"] != {"source_ref": result["source_ref"], "record_ordinal": emitted}:
                _fail("parsed_record_key_invalid")
            token = _token(row["record_key"])
            if token in records:
                _fail("duplicate_parsed_record_key")
            records[token] = row
            ordinal = row["record_key"]["record_ordinal"]
            qualified[token] = (row["extraction_method"] == "supplied_explicit" or native_matches
                and ordinal < len(rebuilt["records"]) and row == rebuilt["records"][ordinal])
    for row in bindings:
        _keys(row, "binding_key record_key metadata_key entity parent_metadata_key member_binding_index identifier_links source")
    _unique(bindings, "binding_key", "duplicate_binding"); _unique(bindings, "metadata_key", "duplicate_metadata_key")
    bykey = {b["metadata_key"]: b for b in bindings}
    for row in bindings:
        _keys(row, "binding_key record_key metadata_key entity parent_metadata_key member_binding_index identifier_links source")
        _str(row["binding_key"]); _str(row["metadata_key"]); _record_key(row["record_key"])
        _entity(row["entity"]); _nullable(row["parent_metadata_key"], _str)
        _nullable(row["member_binding_index"], _int); _prov(row["source"])
        if _token(row["record_key"]) not in records:
            _fail("unknown_parsed_record_key")
        if row["parent_metadata_key"] is not None and row["parent_metadata_key"] not in bykey:
            _fail("unknown_parent_metadata_key")
        if row["entity"]["dataset_key"] is not None and row["entity"]["dataset_key"] not in datasets:
            _fail("unknown_dataset_key")
        if row["member_binding_index"] is not None and row["member_binding_index"] >= len(member_bindings):
            _fail("binding_index_out_of_range")
        if type(row["identifier_links"]) is not list:
            _fail()
        for link in row["identifier_links"]:
            _keys(link, "source_identifier target_identifier representation source")
            _identity(link["source_identifier"]); _identity(link["target_identifier"])
            _enum(link["representation"], {"literal", "sra_general_tag"}); _prov(link["source"])
    visiting, finished, bound, outcomes = set(), set(), {}, {}
    def process(row):
        mk = row["metadata_key"]
        if mk in finished:
            return
        if mk in visiting:
            _fail("metadata_binding_cycle")
        visiting.add(mk)
        parent_key = row["parent_metadata_key"]
        if parent_key is not None:
            process(bykey[parent_key])
        record = records[_token(row["record_key"])]; source = record["source_entity"]
        entity = row["entity"]; kind = entity["kind"]; issues = []
        def issue(code, **facts):
            issues.append(_issue(code, binding_key=row["binding_key"], record_key=row["record_key"], **facts))
        if not qualified[_token(row["record_key"])]:
            issue("metadata_native_extraction_unverified")
        if source["kind"] != kind:
            issue("metadata_entity_conflict")
        allowed = list(record["identifiers"])
        for link in row["identifier_links"]:
            a, b = link["source_identifier"], link["target_identifier"]
            valid = a in source["identifiers"] and a in record["identifiers"]
            valid &= a == b if link["representation"] == "literal" else _sra_equal(a, b) and b in record["identifiers"]
            if not valid:
                issue("metadata_alias_unavailable", identifier_link=link)
            elif b not in allowed:
                allowed.append(b)
        parent = bound.get(parent_key)
        if source["parent_record_key"] is not None and (parent is None or bykey[parent_key]["record_key"] != source["parent_record_key"]):
            issue("metadata_parent_relation_conflict")
        dataset = datasets.get(entity["dataset_key"])
        if kind == "dataset":
            if source["dataset_identifier"] is None or source["dataset_identifier"] not in [dataset["identifier"], *dataset["run_identifiers"]]:
                issue("dataset_selection_unverified")
        elif kind == "sample":
            links = [l for l in dataset["sample_links"] if l["sample_key"] == entity["sample_key"] and l["sample_identifier"] == source["sample_identifier"]]
            if source["sample_identifier"] is None or not links or parent is None or parent["entity"]["kind"] != "dataset" or parent["entity"]["dataset_key"] != entity["dataset_key"]:
                issue("sample_link_unavailable")
            elif any(l["biosample_identifier"] is not None and l["biosample_identifier"] not in record["identifiers"] for l in links):
                issue("sample_link_conflict")
        elif kind == "member":
            index = row["member_binding_index"]
            member = member_bindings[index] if index is not None else None
            if member is None or any(member[k] != entity[k] for k in ("dataset_key", "member_identifier")) or entity["member_identifier"] not in allowed:
                issue("member_identifier_unlinked")
            if source["dataset_identifier"] is not None and source["dataset_identifier"] not in [dataset["identifier"], *dataset["run_identifiers"]]:
                issue("dataset_selection_unverified")
        elif kind == "feature":
            if (parent is None or parent["entity"]["kind"] != "member" or any(parent["entity"][k] != entity[k] for k in ("dataset_key", "member_identifier"))
                    or source["feature_identifier"] != entity["feature_identifier"]):
                issue("metadata_parent_relation_conflict")
        else:
            if (query_binding is None or query_binding["pssm_key"] != entity["pssm_key"]
                    or source["pssm_key"] != entity["pssm_key"] or record["master_mapping"] is None
                    or record["master_mapping"]["pssm_key"] != entity["pssm_key"]):
                issue("query_master_mapping_unavailable")
        status = "available" if not issues else "incompatible" if any(i["code"] in {
            "blast_vdb_metadata_native_extraction_unverified", "blast_vdb_metadata_entity_conflict",
            "blast_vdb_metadata_parent_relation_conflict", "blast_vdb_sample_link_conflict"} for i in issues) else "unavailable"
        if status == "available":
            output = {k: deepcopy(record[k]) for k in _PAYLOAD}
            output.update(metadata_key=mk, entity=deepcopy(entity), linkage_source=deepcopy(row["source"]))
            if kind == "feature" and output["feature"]:
                output["feature"]["member_sequence_metadata_key"] = parent_key
            bound[mk] = output
        outcomes[mk] = dict(binding_key=row["binding_key"], record_key=deepcopy(row["record_key"]),
            metadata_key=mk if status == "available" else None, status=status, issues=issues)
        visiting.remove(mk); finished.add(mk)
    for row in bindings:
        process(row)
    used = {_token(bykey[k]["record_key"]) for k in bound}
    return dict(schema="blast_vdb_bound_metadata_v1", reference_metadata=[bound[b["metadata_key"]] for b in bindings if b["metadata_key"] in bound],
        binding_results=[outcomes[b["metadata_key"]] for b in bindings],
        unresolved_record_keys=[deepcopy(r["record_key"]) for k, r in records.items() if k not in used],
        issues=[deepcopy(i) for b in bindings for i in outcomes[b["metadata_key"]]["issues"]])
