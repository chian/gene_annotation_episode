"""Source-bound declarations and actual FASTQ mate joins, without acquisition.

Declarations retain their exact evidence and value. They do not certify a
recipe occurrence or turn a requested reference into an observed reference.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import re

from .bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, canonical_json, validate_contract,
    validate_metadata, validate_native_document,
)
from .bvbrc_fastqutils_identity import (
    document_ref, join_ref, library_ref, metadata_ref, requirement_ref, stage_ref,
)
from .bvbrc_fastqutils_metric_specs import metric_spec


def _check(condition, code="binding_conflict", path=""):
    if not condition:
        raise FastqUtilsContractError(code, path)


def _escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _unique(values):
    """Stable exact deduplication; never select among conflicting records."""
    result, seen = [], set()
    for value in values:
        key = canonical_json(value)
        if key not in seen:
            result.append(deepcopy(value))
            seen.add(key)
    return result


def _requirement(analysis, pointer, code, required, affected=(), sources=(), state="unavailable"):
    return validate_contract("Requirement", dict(
        id=requirement_ref(analysis, pointer, code), code=code,
        affected_refs=_unique(list(affected)), required_data=required, state=state,
        source_refs=_unique(list(sources))))


def _diagnostic(code, affected=(), sources=(), locator=None):
    return validate_contract("Diagnostic", dict(code=code, affected_refs=_unique(list(affected)),
        source_refs=_unique(list(sources)), locator=locator))


def _unknown_encoding():
    return dict(basis="unknown", encoding="unknown", metadata_id=None,
                evidence=None, declaration=None, native_locator=None)


def select_metadata(inputs: dict) -> tuple[list[dict], list[dict], list[dict]]:
    inputs = validate_contract("MetadataInputs", inputs)
    analysis = inputs["analysis_id"]
    selected, requirements, diagnostics, ids = [], [], [], set()
    for index, binding in enumerate(inputs["bindings"]):
        ident = binding["metadata_id"]
        _check(ident not in ids, "duplicate_identity", "/bindings/" + str(index))
        ids.add(ident)
        pointer = binding["evidence"]["pointer"]
        _check(re.fullmatch(r"(?:/(?:[^~/]|~[01])*)*", pointer) is not None,
               "reference_invalid", "/bindings/" + str(index) + "/evidence/pointer")
        matches = _unique([v["value"] for v in inputs["supplied_values"]
            if canonical_json(v["evidence"]) == canonical_json(binding["evidence"])])
        code = None
        if not matches:
            code = "metadata_binding_missing"
        elif len(matches) != 1:
            code = "metadata_value_conflict"
        else:
            candidate = dict(binding, value=matches[0])
            try:
                candidate = validate_contract("SelectedMetadata", candidate)
            except FastqUtilsContractError:
                code = "metadata_value_conflict"
            else:
                selected.append(candidate)
        if code:
            sources = [binding["evidence"]["content"]["source_ref"]]
            requirements.append(_requirement(analysis, "/metadata/" + _escape(ident), code,
                "source_bound_metadata", sources=sources,
                state="incompatible" if code == "metadata_value_conflict" else "unavailable"))
            diagnostics.append(_diagnostic(code, sources=sources, locator=pointer or None))
    return selected, requirements, diagnostics


def _pair_key(title, rule):
    if rule == "exact_title":
        return title if title else None
    if rule == "fastq_pair_0_3":
        token = title.split(" ", 1)[0]
        if len(token) >= 2 and token[-2] in "/_." and token[-1] in "12fr":
            token = token[:-1]  # Native 0.3 retains the delimiter.
        return token or None
    fields = title.split()
    token = fields[0] if fields else ""
    if rule == "first_token_slash_mate" and len(token) >= 2 and token[-2:] in ("/1", "/2"):
        token = token[:-2]
    return token or None


def _pair_population(item, ordinal, docs, analysis, requirements, diagnostics):
    value = item["value"]
    left = docs.get(value["left_document_id"])
    right = docs.get(value["right_document_id"])
    affected = [document_ref(analysis, value[k]) for k in ("left_document_id", "right_document_id")]
    sources = [item["evidence"]["content"]["source_ref"]]
    pointer = "/metadata/" + _escape(item["metadata_id"])

    def problem(code, required="pair_correspondence"):
        requirements.append(_requirement(analysis, pointer, code, required, affected, sources))
        diagnostics.append(_diagnostic(code, affected, sources))

    if left is None or right is None:
        problem("missing_mate", "mate_identity")
        return None, None
    sources.extend([left["artifact"]["source_ref"], right["artifact"]["source_ref"]])
    if (left["document_id"] == right["document_id"] or
        canonical_json(left["artifact"]["content_binding"]) == canonical_json(right["artifact"]["content_binding"])):
        problem("incompatible_population")
        return None, None
    parents = []
    for doc in (left, right):
        populations = [p for p in doc["populations"] if p["population_key"] == "fastq_reads"]
        if len(populations) != 1:
            problem("incompatible_population")
            return None, None
        parents.append(populations[0])
    maps = []
    for doc, parent in zip((left, right), parents):
        records = {r["id"]: r for r in doc["sequence_records"]}
        mapping = defaultdict(list)
        for ref in parent["member_record_refs"]:
            _check(ref in records, "saved_relationship_conflict")
            row = records[ref]
            mapping[_pair_key(row["title"], value["pair_key_rule"])].append(row)
        maps.append(mapping)
    ambiguous = any(k is None or len(rows) != 1 for mapping in maps for k, rows in mapping.items())
    keys = [key for key in maps[0] if key is not None and len(maps[0][key]) == 1
            and len(maps[1].get(key, [])) == 1]
    missing = set(maps[0]) != set(maps[1])
    if ambiguous:
        problem("ambiguous_pair_key")
    if missing:
        problem("missing_mate", "mate_identity")
    scope = "complete" if not ambiguous and not missing and all(p["scope"] == "complete" for p in parents) else "partial"
    if any(p["scope"] == "unknown" for p in parents):
        scope = "unknown"
    if scope != "complete" and not ambiguous and not missing:
        problem("partial_transfer", "complete_native_bytes")
    parent_refs = [p["id"] for p in parents]
    pop_ref = join_ref("population", analysis, item["metadata_id"], parent_refs)
    cell_ref = join_ref("cell", analysis, item["metadata_id"], parent_refs)
    population = dict(id=pop_ref, association_ref=None, kind="verified_read_pairs", scope=scope,
        representation="emitted_bytes", member_artifact_refs=[d["artifact"]["id"] for d in (left, right)],
        member_record_refs=[mapping[key][0]["id"] for key in keys for mapping in maps],
        parent_population_refs=parent_refs, disjoint_from_refs=[], pair_key_rule=value["pair_key_rule"],
        quality_encoding="unknown", encoding_evidence_refs=[], document_ids=[left["document_id"], right["document_id"]],
        population_key="verified_read_pairs", population_ordinal=ordinal, section_key=None,
        section_ordinal=None, encoding_basis=_unknown_encoding())
    spec = metric_spec("verified_pair_count")
    cell = dict(id=cell_ref, artifact_ref=left["artifact"]["id"], locator=dict(member=None,
        block="verified_read_pairs", block_ordinal=ordinal, row_ordinal=None, field="unique_read_key_join",
        byte_start=None, byte_end=None), metric="verified_pair_count",
        axis=dict(kind="none", label=None, lower=None, upper=None), population_ref=pop_ref,
        association_ref=None, state="available" if scope == "complete" else "partial", value=len(keys),
        native_token=None, unit="pairs", meaning=spec["meaning"], precision=spec["precision"],
        diagnostic_codes=[code for condition, code in ((ambiguous, "ambiguous_pair_key"),
            (missing, "missing_mate"), (scope != "complete", "partial_transfer")) if condition],
        section_key="fastq_summary", section_ordinal=0)
    return population, cell


def extract_fastqutils_metadata(original_task: dict, *, analysis_id: str,
    metadata_bindings: list[dict], supplied_values: list[dict], documents: list[dict]) -> dict:
    inputs = validate_contract("MetadataInputs", dict(analysis_id=analysis_id, original_task=original_task,
        bindings=metadata_bindings, supplied_values=supplied_values))
    original = inputs["original_task"]
    _check(original["native_application_id"] == original["required_application_id"] == "FastqUtils")
    selected, requirements, diagnostics = select_metadata(inputs)
    docs = {}
    for document in documents:
        validate_native_document(document)
        _check(document["analysis_id"] == analysis_id and document["artifact"]["task_ref"] == original["submission_receipt_ref"])
        _check(document["document_id"] not in docs, "duplicate_identity")
        docs[document["document_id"]] = deepcopy(document)
    task, source = original["submission_receipt_ref"], original["submission_source_ref"]
    submitted = original["submitted_parameters"]
    libraries, stages, associations = [], [], []
    platform_values = {"infer", "illumina", "pacbio", "pacbio_hifi", "nanopore", "unrecognized"}
    paths = defaultdict(list)
    for name in ("paired_end_libs", "single_end_libs", "srr_libs"):
        rows = submitted.get(name, [])
        _check(type(rows) is list, "shape_invalid", "/submitted_parameters/" + name)
        for index, value in enumerate(rows):
            pointer = "/" + name + "/" + str(index)
            ident = library_ref(analysis_id, task, pointer)
            platform = value.get("platform") if type(value) is dict else None
            _check(platform is None or type(platform) is str, "shape_invalid", "/submitted_parameters" + pointer + "/platform")
            platform = platform if platform in platform_values or platform is None else "unrecognized"
            row = dict(id=ident, task_ref=task, input_pointer=pointer, submitted_value=deepcopy(value),
                sample_ref=None, condition_ref=None, replicate_ref=None, platform=platform,
                evidence_refs=[source], metadata_ids=[])
            annotations = [m for m in selected if m["kind"] == "library_annotation" and m["value"]["input_pointer"] == pointer]
            for field in ("sample_ref", "condition_ref", "replicate_ref", "platform"):
                supplied = _unique([m["value"][field] for m in annotations if m["value"][field] is not None])
                valid_ref = field == "platform" or not supplied or all(
                    re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:/%~-]*", value) for value in supplied)
                if valid_ref and len(supplied) == 1 and (field != "platform" or platform is None or supplied[0] == platform):
                    row[field] = supplied[0]
                elif not valid_ref or len(supplied) > 1 or supplied and field == "platform" and supplied[0] != platform:
                    requirements.append(_requirement(analysis_id, "/libraries" + pointer + "/" + field,
                        "metadata_value_conflict", "source_bound_metadata", [ident], [source], "incompatible"))
            row["metadata_ids"] = [m["metadata_id"] for m in annotations]
            row["evidence_refs"] = _unique([source] + [m["evidence"]["content"]["source_ref"] for m in annotations])
            libraries.append(row)
            if type(value) is dict:
                for field in ("read", "read1", "read2"):
                    if type(value.get(field)) is str:
                        paths[value[field]].append(ident)
                if name == "paired_end_libs" and any(not value.get(k) for k in ("read1", "read2")):
                    requirements.append(_requirement(analysis_id, "/libraries" + pointer,
                        "missing_mate", "mate_identity", [ident], [source]))
    for refs in paths.values():
        if len(refs) > 1:
            diagnostics.append(_diagnostic("input_path_reused", refs, [source]))
            requirements.append(_requirement(analysis_id, "/inputs/" + str(len(requirements)),
                "input_path_reused", "stage_input_association", refs, [source], "unresolved"))
    recipe = submitted.get("recipe", [])
    _check(type(recipe) is list and all(type(token) is str for token in recipe), "shape_invalid", "/submitted_parameters/recipe")
    reference = submitted.get("reference_genome_id")
    _check(reference is None or type(reference) is str and bool(reference), "shape_invalid", "/submitted_parameters/reference_genome_id")
    for ordinal, token in enumerate(recipe):
        mode = token.upper()
        stages.append(dict(id=stage_ref(analysis_id, task, ordinal), task_ref=task,
            recipe_ordinal=ordinal, requested_token=token, mode=mode if mode in
            {"TRIM", "PAIRED_FILTER", "FASTQC", "ALIGN", "SCRUB_HUMAN"} else "UNKNOWN",
            observed_state="unknown", input_population_refs=[], output_population_refs=[],
            evidence_refs=[source], request_pointer="/submitted_parameters/recipe/" + str(ordinal),
            requested_reference_genome_id=reference))
    by_pointer = {row["input_pointer"]: row for row in libraries}
    for item in selected:
        value, kind = item["value"], item["kind"]
        sources = [item["evidence"]["content"]["source_ref"]]
        pointer = "/metadata/" + _escape(item["metadata_id"])
        if kind in ("library_annotation", "association_assertion") and value["input_pointer"] not in by_pointer:
            requirements.append(_requirement(analysis_id, pointer, "metadata_value_conflict", "stage_input_association", sources=sources, state="incompatible"))
            continue
        if kind == "association_assertion":
            ordinal = value["recipe_ordinal"]
            if ordinal is not None and ordinal >= len(stages):
                requirements.append(_requirement(analysis_id, pointer, "metadata_value_conflict", "stage_input_association", sources=sources, state="incompatible"))
                continue
            document = docs.get(value["document_id"])
            artifacts = [document["artifact"]["id"]] if document else []
            association = dict(id=metadata_ref("association", analysis_id, item["metadata_id"]),
                task_ref=task, library_ref=by_pointer[value["input_pointer"]]["id"],
                stage_ref=stages[ordinal]["id"] if ordinal is not None else None,
                mate=value["mate"], branch=value["branch"], artifact_refs=artifacts,
                evidence_refs=sources, state="unresolved", basis="explicit_assertion",
                metadata_ids=[item["metadata_id"]], document_ids=[value["document_id"]])
            associations.append(association)
            requirements.append(_requirement(analysis_id, "/documents/" + _escape(value["document_id"]),
                "stage_execution_unknown", "native_execution_evidence", artifacts or [association["id"]],
                [document["artifact"]["source_ref"]] if document else sources, "unresolved"))
        elif kind == "reference_declaration":
            requirements.append(_requirement(analysis_id, pointer, "unknown_reference", "reference_identity",
                [document_ref(analysis_id, value["document_id"])], sources, "unresolved"))
            if value["completeness"] != "declared_complete":
                requirements.append(_requirement(analysis_id, pointer, "reference_incomplete", "reference_completeness",
                    [document_ref(analysis_id, value["document_id"])], sources, "unresolved"))
    for association in associations:
        others = [row for row in associations if row["id"] != association["id"] and
                  row["document_ids"] == association["document_ids"]]
        fields = ("library_ref", "stage_ref", "mate", "branch")
        if any(any(row[k] != association[k] for k in fields) for row in others):
            association["state"] = "conflicting"
            diagnostics.append(_diagnostic("metadata_value_conflict", [association["id"]], association["evidence_refs"]))
    populations = [deepcopy(p) for doc in docs.values() for p in doc["populations"]]
    for document in docs.values():
        declarations = [m for m in selected if m["kind"] == "encoding_declaration" and m["value"]["document_id"] == document["document_id"]]
        if document["artifact"]["actual_format"] != "fastq":
            continue  # A declaration never replaces native SAM/BAM encoding.
        relevant = [p for p in populations if p["document_ids"] == [document["document_id"]]]
        affected = [p["id"] for p in relevant if p["population_key"] == "fastq_quality_characters"]
        sources = [document["artifact"]["source_ref"]]
        if len(declarations) == 1:
            item = declarations[0]
            for population in relevant:
                population.update(quality_encoding=item["value"]["encoding"],
                    encoding_evidence_refs=[item["evidence"]["content"]["source_ref"]],
                    encoding_basis=dict(basis="explicit_source_bound_declaration", encoding=item["value"]["encoding"],
                        metadata_id=item["metadata_id"], evidence=deepcopy(item["evidence"]),
                        declaration=deepcopy(item["value"]), native_locator=None))
        else:
            code = "unknown_quality_encoding" if not declarations else "encoding_declaration_conflict"
            requirements.append(_requirement(analysis_id, "/documents/" + _escape(document["document_id"]),
                code, "quality_encoding", affected, sources, "unavailable" if not declarations else "incompatible"))
            if declarations:
                diagnostics.append(_diagnostic(code, affected, sources))
    measurements = []
    for ordinal, item in enumerate(m for m in selected if m["kind"] == "pair_declaration"):
        population, cell = _pair_population(item, ordinal, docs, analysis_id, requirements, diagnostics)
        if population is not None:
            populations.append(population)
            measurements.append(cell)
    result = dict(schema_version="fastqutils_metadata_v2", analysis_id=analysis_id, task_ref=task,
        original_task=original, libraries=libraries, stages=stages, associations=associations,
        populations=populations, measurements=measurements, supplied_metadata=selected,
        native_lineage=[deepcopy(edge) for doc in docs.values() for edge in doc["native_lineage"]],
        requirements=_unique(requirements), diagnostics=_unique(diagnostics))
    validate_metadata(result)
    return result


__all__ = ["select_metadata", "extract_fastqutils_metadata"]
