"""Exact document selection and explicit saved-record calculation operands."""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_fastqutils_contracts import (
    checked_bytes, canonical_json, validate_contract, validate_parameters, validate_sheet,
)
from .bvbrc_fastqutils_identity import artifact_ref, decode_reference, document_ref, requirement_ref
from .bvbrc_fastqutils_metadata import _check, _escape, _unique, _requirement

_SAMSTAT_VERSIONS = {'samstat_html_2_2_3': '2.2.3', 'samstat_html_2_5_0': '2.5.0'}
_SAMSTAT_FORMATS = {'samstat_html', 'samstat_bvbrc_error_html', *_SAMSTAT_VERSIONS}


def _document_declaration(binding, members):
    """One declaration constraint for initial parsing and saved validation.

    Keep the requested format unchanged. A supported SAMstat member format or
    version narrows the native-version check; it never asserts byte recognition.
    """
    formats = {m['declared_format']['format'] for m in members}
    versions = {m['declared_format']['version'] for m in members
                if m['declared_format']['version'] is not None}
    requested = binding['format']
    supplied_version = binding['producer_version']
    if requested not in _SAMSTAT_FORMATS:
        if formats - {requested, 'unknown'}:
            return supplied_version, 'unsupported_format', 'supported_parser'
        if supplied_version is not None and versions - {supplied_version}:
            return supplied_version, 'unsupported_version', 'native_version'
        return supplied_version, None, None
    if formats - _SAMSTAT_FORMATS - {'unknown'}:
        return supplied_version, 'unsupported_format', 'supported_parser'
    versions.update(_SAMSTAT_VERSIONS[f] for f in formats | {requested} if f in _SAMSTAT_VERSIONS)
    if supplied_version is not None:
        versions.add(supplied_version)
    if len(versions) > 1:
        return supplied_version, 'unsupported_version', 'native_version'
    return next(iter(versions), None), None, None


def _member_content(member):
    return dict(source_ref=member["source_ref"], artifact_field="artifact_ref",
        artifact_ref=member["raw_artifact_ref"], sha256=member["sha256"], byte_count=member["byte_count"])


def _matched_contents(bundle, selection):
    if selection["kind"] == "output_requirement":
        members = [row for row in bundle["artifacts"] if selection["requirement_id"] in row.get("requirement_ids", [])]
        return _unique([_member_content(row) for row in members]), members
    chosen = canonical_json(selection["content"])
    members = [row for row in bundle["artifacts"] if canonical_json(_member_content(row)) == chosen]
    contents = [c for c in bundle.get("supplied_contents", []) if canonical_json(c) == chosen]
    return _unique([_member_content(row) for row in members] + contents), members


def resolve_documents(bundle: dict, *, artifact_bytes: dict[str, bytes],
                      parameters: dict) -> tuple[list[dict], list[dict], list[dict]]:
    bundle = validate_contract("Host_ArtifactBundle", bundle)
    parameters = validate_parameters(parameters)
    _check(type(artifact_bytes) is dict and all(type(k) is str and type(v) is bytes
        for k, v in artifact_bytes.items()), "shape_invalid", "/artifact_bytes")
    original = bundle["original_task"]
    _check(original["native_application_id"] == original["required_application_id"] == "FastqUtils")
    analysis = parameters["analysis_id"]
    contexts, resolutions, requirements = [], [], []
    # The same artifact identifier cannot denote contradictory byte bindings.
    bindings = {}
    for content in [_member_content(m) for m in bundle["artifacts"]] + bundle.get("supplied_contents", []):
        key = content["artifact_ref"]
        shape = (content["sha256"], content["byte_count"])
        _check(key not in bindings or bindings[key] == shape, "binding_conflict", "/artifacts")
        bindings[key] = shape
    for binding in parameters["documents"]:
        document = binding["document_id"]
        contents, members = _matched_contents(bundle, binding["selection"])
        resolution = dict(document_id=document, selection=deepcopy(binding["selection"]),
            state="available", matched_contents=contents, artifact_ref=None,
            requirement_refs=[], diagnostic_codes=[])
        code, required = None, "selected_document"
        if not contents:
            resolution["state"], code = "missing", "missing_artifact"
        elif len(contents) > 1:
            resolution["state"], code = "ambiguous", "selection_ambiguous"
            required = "exact_source_cardinality"
        else:
            content = contents[0]
            for member in members:
                _check(member["task_association"]["task_id"] == original["task_id"], "binding_conflict", "/artifacts")
            producer_version, declaration_code, declaration_required = _document_declaration(binding, members)
            if declaration_code:
                resolution["state"], code, required = "incompatible", declaration_code, declaration_required
            elif content["artifact_ref"] not in artifact_bytes:
                resolution["state"], code, required = "missing", "missing_artifact", "complete_native_bytes"
            else:
                checked_bytes(artifact_bytes[content["artifact_ref"]], content=content)
                scopes = [("complete" if m["transfer"]["body_complete"] and m["transfer"]["object_complete"] == "yes"
                    else "partial" if not m["transfer"]["body_complete"] or m["transfer"]["object_complete"] == "no"
                    else "unknown") for m in members]
                names = _unique([m["workspace_object"]["path"] for m in members])
                context = dict(analysis_id=analysis, document_id=document, task_ref=original["submission_receipt_ref"],
                    content=content, native_name=names[0] if len(names) == 1 else None,
                    declared_format=binding["format"], producer_version=producer_version,
                    transfer_scope=("partial" if "partial" in scopes else "unknown" if "unknown" in scopes else "complete"),
                    identity="unknown" if members else "supplied_native_artifact")
                context = validate_contract("ParseContext", context)
                resolution["artifact_ref"] = artifact_ref(context)
                contexts.append(context)
        if code is not None:
            requirement = _requirement(analysis, "/documents/" + _escape(document), code, required,
                [document_ref(analysis, document)], [c["source_ref"] for c in contents],
                "incompatible" if resolution["state"] in ("ambiguous", "incompatible") else "unavailable")
            requirements.append(requirement)
            resolution["requirement_refs"] = [requirement["id"]]
            resolution["diagnostic_codes"] = [code]
        resolutions.append(validate_contract("ResolvedDocument", resolution))
    return contexts, resolutions, requirements


def select_rows(sheet, kind, selector, components=None):
    """Match exact semantic selectors without inventing absent native rows."""
    names = {"measurement": "MeasurementSelector", "population": "PopulationSelector",
             "association": "AssociationSelector", "category": "CategorySelector", "component": "ComponentSelector"}
    selector = validate_contract(names[kind], selector)
    collections = {"measurement": "measurements", "population": "populations", "association": "associations", "category": "categories"}
    rows = (components or {}).get("components", []) if kind == "component" else (sheet or {}).get(collections[kind], [])
    if selector["selection"] == "record":
        expected = {"measurement": "cell", "population": "population", "association": "association", "category": "category", "component": "component"}[kind]
        parts = decode_reference(selector["record_ref"], expected_kind=expected)
        if sheet is not None:
            _check(parts["analysis_id"] == sheet["analysis_id"], "reference_invalid")
        return [r for r in rows if r["id"] == selector["record_ref"]]
    artifacts = {d["artifact"]["id"]: d["document_id"] for d in (sheet or {}).get("documents", [])}
    libraries = {r["id"]: r for r in (sheet or {}).get("libraries", [])}
    stages = {r["id"]: r for r in (sheet or {}).get("stages", [])}
    result = []
    for row in rows:
        if kind == "component":
            match = all(row[k] == selector[k] for k in ("calculation_id", "metric", "threshold"))
        elif kind == "population":
            match = (selector["document_id"] in row["document_ids"] and row["population_key"] == selector["population_key"]
                     and row["population_ordinal"] == selector["population_ordinal"])
        elif kind == "association":
            match = (selector["document_id"] in row["document_ids"] and
                libraries.get(row["library_ref"], {}).get("input_pointer") == selector["input_pointer"] and
                (stages.get(row["stage_ref"], {}).get("recipe_ordinal") if row["stage_ref"] else None) == selector["recipe_ordinal"] and
                row["mate"] == selector["mate"] and row["branch"] == selector["branch"])
        else:
            match = (artifacts.get(row["artifact_ref"]) == selector["document_id"] and
                row["section_key"] == selector["section_key"] and row["section_ordinal"] == selector["section_ordinal"])
            if kind == "measurement":
                match = (match and row["metric"] == selector["metric"] and
                    (selector["rows"]["kind"] == "all" or row["locator"]["row_ordinal"] == selector["rows"]["ordinal"]) and
                    (selector["axis"]["kind"] == "all" or canonical_json(row["axis"]) == canonical_json(selector["axis"]["axis"])))
        if match:
            result.append(row)
    return result


def _lineage(sheet, before, after, method):
    unknown = dict(basis="unknown", metadata_id=None, evidence=None, declaration=None, native_lineage_ref=None)
    if before is None or after is None:
        return unknown, "association_unresolved"
    native = [edge for edge in sheet["native_lineage"] if edge["before_population_ref"] == before["id"]
              and edge["after_population_ref"] == after["id"]]
    declarations = []
    for item in sheet["supplied_metadata"]:
        if item["kind"] != "lineage_declaration":
            continue
        value = item["value"]
        left, right = select_rows(sheet, "population", value["before"]), select_rows(sheet, "population", value["after"])
        if len(left) == len(right) == 1 and left[0]["id"] == before["id"] and right[0]["id"] == after["id"]:
            declarations.append(item)
    allowed = {"same_population"} if method == "report_consistency_v1" else {"successor_population", "subset_population"}
    if len(declarations) > 1 or any(item["value"]["relation"] not in allowed for item in declarations):
        return unknown, "metadata_value_conflict"
    if len(native) > 1:
        return unknown, "selection_ambiguous"
    if native:
        edge = native[0]
        if method == "report_consistency_v1" and edge["kind"] != "observed_record_correspondence":
            return unknown, "incompatible_population"
        return dict(unknown, basis="native_report" if edge["kind"] == "native_report_before_after" else "observed_record_correspondence",
                    native_lineage_ref=edge["id"]), None
    if declarations:
        item = declarations[0]
        return dict(basis="explicit_source_bound_declaration", metadata_id=item["metadata_id"],
            evidence=deepcopy(item["evidence"]), declaration=deepcopy(item["value"]), native_lineage_ref=None), "explicit_lineage_assumption"
    return unknown, "association_unresolved"


def resolve_calculation_inputs(sheet: dict, *, requests: list[dict]) -> dict:
    validate_sheet(sheet)
    _check(type(requests) is list, "shape_invalid", "/requests")
    requests = [validate_contract("CalculationRequest", r) for r in requests]
    _check(len({r["calculation_id"] for r in requests}) == len(requests), "duplicate_identity")
    jobs = []
    population_index = {p["id"]: p for p in sheet["populations"]}
    for request in requests:
        method = request["method"]
        job = dict(calculation_id=request["calculation_id"], method=method, state="ready", population_refs=[],
            operand_measurement_refs=[], comparison_kind=request.get("comparison_kind"),
            quality_thresholds=deepcopy(request.get("quality_thresholds", [])), read_key_rule=request.get("read_key_rule"),
            lineage_ref=None, lineage_basis=None, requirement_refs=[], diagnostic_codes=[])

        def problem(code, *, terminal=False, incompatible=False):
            if code not in job["diagnostic_codes"]:
                job["diagnostic_codes"].append(code)
            if terminal:
                job["state"] = "incompatible" if incompatible else "unavailable"
            if code != "explicit_lineage_assumption":
                ident = requirement_ref(sheet["analysis_id"], "/calculations/" + _escape(job["calculation_id"]), code)
                if ident not in job["requirement_refs"]:
                    job["requirement_refs"].append(ident)

        def one(kind, selector, *, terminal=True):
            if selector is None:
                return None
            rows = select_rows(sheet, kind, selector)
            if len(rows) != 1:
                problem("selection_ambiguous" if rows else "missing_denominator" if kind == "population" else "missing_requested_value",
                        terminal=terminal, incompatible=bool(rows))
                return None
            return rows[0]

        if method in ("composition_v1", "quality_phred_v1", "mapping_v1"):
            population = one("population", request["population"])
            if population:
                job["population_refs"].append(population["id"])
            if method == "composition_v1" and population:
                if population["population_key"] not in {"fastq_reads", "fastq_bases"}:
                    problem("incompatible_population", terminal=True, incompatible=True)
                else:
                    for key in ("fastq_reads", "fastq_bases"):
                        matches = [p for p in sheet["populations"] if p["population_key"] == key and
                            p["member_artifact_refs"] == population["member_artifact_refs"] and
                            p["member_record_refs"] == population["member_record_refs"] and
                            p["document_ids"] == population["document_ids"]]
                        if len(matches) == 1:
                            if matches[0]["id"] not in job["population_refs"]:
                                job["population_refs"].append(matches[0]["id"])
                        else:
                            problem("missing_denominator" if not matches else "selection_ambiguous")
                    cells = [r for r in sheet["measurements"] if r["population_ref"] in job["population_refs"]
                             and r["metric"] in {"fastq_read_count", "fastq_base_count", "fastq_symbol_count"}]
                    job["operand_measurement_refs"] = [r["id"] for r in cells]
                    if not all(any(r["metric"] == metric for r in cells) for metric in ("fastq_read_count", "fastq_base_count", "fastq_symbol_count")):
                        problem("missing_requested_value")
            elif method == "quality_phred_v1" and population:
                if population["population_key"] not in {"fastq_quality_characters", "bam_quality_bases"}:
                    problem("incompatible_population", terminal=True, incompatible=True)
                metric = "phred_histogram_count" if population["encoding_basis"]["basis"] in {"native_sam_phred", "native_bam_phred"} else "quality_character_count"
                job["operand_measurement_refs"] = [r["id"] for r in sheet["measurements"]
                    if r["population_ref"] == population["id"] and r["metric"] == metric]
                if population["quality_encoding"] == "unknown":
                    problem("unknown_quality_encoding")
                if not job["operand_measurement_refs"] and population["member_record_refs"]:
                    problem("missing_requested_value")
            elif method == "mapping_v1":
                if population and population["population_key"] != "bam_records":
                    problem("incompatible_population", terminal=True, incompatible=True)
                input_population = one("population", request["input_population"], terminal=False)
                if input_population:
                    job["population_refs"].append(input_population["id"])
                    if input_population["population_key"] == "verified_read_pairs":
                        # Explicit pair selection names its actual saved parents.
                        job["population_refs"].extend(input_population["parent_population_refs"])
                    elif input_population["population_key"] != "fastq_reads":
                        problem("incompatible_population")
                else:
                    problem("missing_denominator")
                job["population_refs"] = _unique(job["population_refs"])
                job["operand_measurement_refs"] = [r["id"] for r in sheet["measurements"] if
                    r["population_ref"] in job["population_refs"] and r["metric"] in
                    {"bam_record_count", "bam_primary_record_count", "fastq_read_count"}]
        elif method == "samstat_report_mapping_v1":
            from .bvbrc_fastqutils_samstat_mapping import _count_operands, _report_mode, _mapping_conflicts
            for selector in request["populations"]:
                population = one("population", selector)
                if population is not None:
                    if population["id"] in job["population_refs"]:
                        problem("selection_ambiguous", terminal=True, incompatible=True)
                    else:
                        job["population_refs"].append(population["id"])
                    if population["population_key"] != "samstat_report_records":
                        problem("incompatible_population", terminal=True, incompatible=True)
                # Missing populations still retain the selected document's
                # actual failure/mode/version reason, without fabricating bins.
                doc_ids = population["document_ids"] if population else [selector.get("document_id")]
                for resolution in sheet["document_resolutions"]:
                    if resolution["document_id"] in doc_ids and resolution["state"] != "available":
                        for code in resolution["diagnostic_codes"]:
                            problem(code, terminal=True,
                                    incompatible=resolution["state"] in {"incompatible", "ambiguous"})
                        job["requirement_refs"] = _unique(job["requirement_refs"] + resolution["requirement_refs"])
                for document in sheet["documents"]:
                    if document["document_id"] not in doc_ids:
                        continue
                    actual = document["artifact"]["actual_format"]
                    mode = _report_mode(document)
                    for code in _mapping_conflicts(document):
                        problem(code, terminal=True, incompatible=True)
                    if actual == "samstat_bvbrc_error_html":
                        problem("samstat_caller_failure", terminal=True)
                    elif mode in {"sequence", "conflicting"}:
                        problem("incompatible_population" if mode == "sequence" else "native_header_conflict",
                                terminal=True, incompatible=True)
                    elif actual in _SAMSTAT_VERSIONS and mode == "unknown":
                        problem("source_row_absent", terminal=True)
                    elif actual not in _SAMSTAT_VERSIONS:
                        codes = {r["code"] for r in document["diagnostics"]}
                        problem("unsupported_version" if "unsupported_version" in codes else "unsupported_format",
                                terminal=True, incompatible=True)
                    for requirement in document["requirements"]:
                        if requirement["code"] in job["diagnostic_codes"]:
                            job["requirement_refs"] = _unique(job["requirement_refs"] + [requirement["id"]])
            job["operand_measurement_refs"] = [c["id"] for c in _count_operands(sheet, job["population_refs"])]
            if set(job["diagnostic_codes"]) & {"incompatible_population", "selection_ambiguous",
                    "native_header_conflict", "unsupported_version", "unsupported_format"}:
                job["state"] = "incompatible"
        else:
            if method == "retention_v1":
                before = one("population", request["before_population"])
                after = one("population", request["after_population"])
                left = one("measurement", request["before_measurement"])
                right = one("measurement", request["after_measurement"])
            else:
                job["comparison_kind"] = "report_count_consistency"
                left = one("measurement", request["report_measurement"])
                right = one("measurement", request["observed_measurement"])
                before = population_index.get(left["population_ref"]) if left else None
                after = population_index.get(right["population_ref"]) if right else None
                if before is None or after is None:
                    problem("missing_denominator", terminal=True)
            job["population_refs"] = [p["id"] for p in (before, after) if p is not None]
            job["operand_measurement_refs"] = [r["id"] for r in (left, right) if r is not None]
            if any(row and pop and row["population_ref"] != pop["id"] for row, pop in ((left, before), (right, after))):
                problem("incompatible_population", terminal=True, incompatible=True)
            basis, code = _lineage(sheet, before, after, method)
            job["lineage_basis"] = basis
            job["lineage_ref"] = basis["native_lineage_ref"]
            if code:
                problem(code, terminal=code != "explicit_lineage_assumption",
                        incompatible=code in {"metadata_value_conflict", "selection_ambiguous", "incompatible_population"})
        jobs.append(validate_contract("CalculationBinding", job))
    return validate_contract("CalculatorParameters", dict(version="fastqutils_calculators_v2",
        analysis_id=sheet["analysis_id"], calculations=jobs))


def calculation_requirements(sheet, parameters):
    """Materialize the exact requirement identities carried by resolved jobs."""
    result = []
    known = {r["id"]: r for r in sheet["requirements"]}
    for job in parameters["calculations"]:
        for ident in job["requirement_refs"]:
            if ident in known:
                result.append(known[ident])
                continue
            parts = decode_reference(ident, expected_kind="requirement")
            pointer, code = parts["pointer"].rsplit("/", 1)
            _check(pointer == "/calculations/" + _escape(job["calculation_id"]) and code in job["diagnostic_codes"], "saved_relationship_conflict")
            required = {"unknown_quality_encoding": "quality_encoding", "association_unresolved": "stage_input_association",
                "metadata_value_conflict": "source_bound_metadata", "selection_ambiguous": "exact_source_cardinality",
                "missing_denominator": "before_population"}.get(code, "requested_measurement")
            if job["method"] == "samstat_report_mapping_v1":
                required = {"missing_denominator": "requested_measurement", "samstat_caller_failure": "native_execution_evidence",
                    "source_row_absent": "native_execution_evidence", "unsupported_version": "native_version",
                    "unsupported_format": "supported_parser"}.get(code, required)
            result.append(_requirement(sheet["analysis_id"], pointer, code, required,
                job["population_refs"] + job["operand_measurement_refs"],
                state="incompatible" if job["state"] == "incompatible" else "unavailable"))
    return _unique(result)


__all__ = ["resolve_documents", "resolve_calculation_inputs"]
