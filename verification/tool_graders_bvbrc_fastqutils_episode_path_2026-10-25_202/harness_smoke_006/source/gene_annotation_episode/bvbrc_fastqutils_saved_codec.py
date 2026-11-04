"""Native failure codec and non-recomputing saved-publication validation."""
from __future__ import annotations

from copy import deepcopy
from collections import Counter
import re

from .bvbrc_fastqutils_contracts import (
    canonical_json, validate_contract, validate_parameters, validate_sheet, validate_components,
)
from .bvbrc_fastqutils_identity import join_ref, metadata_ref
from .bvbrc_fastqutils_metadata import _check, _unique, _pair_key, _unknown_encoding
from .bvbrc_fastqutils_projection import project_fastqutils_facts
from .bvbrc_fastqutils_resolution import _matched_contents, resolve_calculation_inputs


def encode_failures(requirements: list[dict], diagnostics: list[dict]) -> dict:
    _check(type(requirements) is list and type(diagnostics) is list, "shape_invalid")
    native_requirements = [validate_contract("Requirement", r) for r in requirements]
    native_diagnostics = [validate_contract("Diagnostic", d) for d in diagnostics]
    encoded_requirements = []
    for row in native_requirements:
        required = row["required_data"]
        kind = ("parser_binding" if required in {"supported_parser", "native_version"} else
            "output_bytes" if required in {"complete_native_bytes", "full_fastqc_data", "earlier_hostile_report", "selected_document"}
            else "scientific_metadata")
        encoded_requirements.append(dict(requirement_id=row["id"], kind=kind, role=required,
            source_refs=_unique(row["source_refs"]), reason_code="bvbrc_fastqutils_" + row["code"]))
    encoded_diagnostics = [dict(code="bvbrc_fastqutils_" + row["code"], phase="native_decode",
        path="/native_diagnostics/" + str(index), severity="qualification", evidence_refs=_unique(row["source_refs"]))
        for index, row in enumerate(native_diagnostics)]
    return validate_contract("EncodedFailures", dict(missing_requirements=encoded_requirements, diagnostics=encoded_diagnostics))


def encode_saved_components(calculations: dict | None, *, projection_failure_context: dict,
    native_requirements: list[dict], native_diagnostics: list[dict]) -> dict:
    return validate_contract("SavedComponents", dict(version="fastqutils_saved_components_v2",
        calculations=calculations, projection_failure_context=projection_failure_context,
        native_requirements=native_requirements, native_diagnostics=native_diagnostics))


def decode_saved_components(value: dict) -> dict:
    return validate_contract("SavedComponents", value)


def _validate_original_inputs(sheet, parameters, original_task, bundle):
    _check(canonical_json(sheet["original_task"]) == canonical_json(original_task) == canonical_json(bundle["original_task"]),
           "saved_relationship_conflict", "/original_task")
    _check(sheet["analysis_id"] == parameters["analysis_id"], "saved_relationship_conflict", "/analysis_id")
    submitted = original_task["submitted_parameters"]
    expected_pointers = ["/" + name + "/" + str(index) for name in ("paired_end_libs", "single_end_libs", "srr_libs")
                         for index, _ in enumerate(submitted.get(name, []))]
    _check([row["input_pointer"] for row in sheet["libraries"]] == expected_pointers,
           "saved_relationship_conflict", "/libraries")
    _check([r["recipe_ordinal"] for r in sheet["stages"]] == list(range(len(submitted.get("recipe", [])))),
           "saved_relationship_conflict", "/stages")
    for row in sheet["stages"]:
        _check(row["requested_reference_genome_id"] == submitted.get("reference_genome_id") and
               row["input_population_refs"] == row["output_population_refs"] == [], "saved_relationship_conflict", "/stages")
    bindings = {r["metadata_id"]: r for r in parameters["metadata_bindings"]}
    selected = {r["metadata_id"]: r for r in sheet["supplied_metadata"]}
    selected_evidence = {canonical_json(e) for e in bundle["supplied_scientific_metadata"]}
    for item in selected.values():
        binding = bindings.get(item["metadata_id"])
        _check(binding is not None and binding == {k: item[k] for k in ("metadata_id", "kind", "evidence")} and
               canonical_json(item["evidence"]) in selected_evidence, "saved_relationship_conflict", "/supplied_metadata")
    for library in sheet["libraries"]:
        items = [r for r in selected.values() if r["kind"] == "library_annotation" and
                 r["value"]["input_pointer"] == library["input_pointer"]]
        _check(library["metadata_ids"] == [r["metadata_id"] for r in items], "saved_relationship_conflict", "/libraries")
        original_platform = library["submitted_value"].get("platform") if type(library["submitted_value"]) is dict else None
        if original_platform is not None and original_platform not in {"infer", "illumina", "pacbio", "pacbio_hifi", "nanopore", "unrecognized"}:
            original_platform = "unrecognized"
        for field in ("sample_ref", "condition_ref", "replicate_ref", "platform"):
            values = _unique([r["value"][field] for r in items if r["value"][field] is not None])
            if field == "platform":
                expected = values[0] if len(values) == 1 and (original_platform is None or values[0] == original_platform) else original_platform
            else:
                expected = values[0] if len(values) == 1 and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:/%~-]*", values[0]) else None
            _check(library[field] == expected, "saved_relationship_conflict", "/libraries")
        _check(library["evidence_refs"] == _unique([original_task["submission_source_ref"]] +
            [item["evidence"]["content"]["source_ref"] for item in items]), "saved_relationship_conflict", "/libraries")
    documents = {d["document_id"]: d for d in sheet["documents"]}
    for association in sheet["associations"]:
        _check(association["basis"] == "explicit_assertion" and len(association["metadata_ids"]) == 1,
               "saved_relationship_conflict", "/associations")
        item = selected.get(association["metadata_ids"][0])
        _check(item is not None and item["kind"] == "association_assertion", "saved_relationship_conflict")
        value = item["value"]
        libraries = {r["id"]: r for r in sheet["libraries"]}
        stages = {r["id"]: r for r in sheet["stages"]}
        _check(association["document_ids"] == [value["document_id"]] and
            libraries[association["library_ref"]]["input_pointer"] == value["input_pointer"] and
            (stages[association["stage_ref"]]["recipe_ordinal"] if association["stage_ref"] else None) == value["recipe_ordinal"] and
            all(association[k] == value[k] for k in ("mate", "branch")), "saved_relationship_conflict", "/associations")
        doc = documents.get(value["document_id"])
        _check(association["id"] == metadata_ref("association", sheet["analysis_id"], item["metadata_id"]) and
            association["artifact_refs"] == ([doc["artifact"]["id"]] if doc else []) and
            association["evidence_refs"] == [item["evidence"]["content"]["source_ref"]],
            "saved_relationship_conflict", "/associations")
        conflicts = [row for row in sheet["associations"] if row["id"] != association["id"] and
            row["document_ids"] == association["document_ids"] and any(row[k] != association[k]
                for k in ("library_ref", "stage_ref", "mate", "branch"))]
        _check(association["state"] == ("conflicting" if conflicts else "unresolved"),
               "saved_relationship_conflict", "/associations")


def _validate_metadata_links(sheet):
    """Validate recorded joins and basis links without regenerating measurements."""
    selected = sheet["supplied_metadata"]
    populations = {p["id"]: p for p in sheet["populations"]}
    cells = {r["id"]: r for r in sheet["measurements"]}
    native_population_ids, native_cell_ids = set(), set()
    documents = {d["document_id"]: d for d in sheet["documents"]}
    for doc in documents.values():
        declarations = [m for m in selected if m["kind"] == "encoding_declaration" and m["value"]["document_id"] == doc["document_id"]]
        for original in doc["populations"]:
            native_population_ids.add(original["id"])
            row = populations[original["id"]]
            expected_basis = original["encoding_basis"]
            expected_refs = original["encoding_evidence_refs"]
            if doc["artifact"]["actual_format"] == "fastq" and len(declarations) == 1:
                item = declarations[0]
                expected_basis = dict(basis="explicit_source_bound_declaration", encoding=item["value"]["encoding"],
                    metadata_id=item["metadata_id"], evidence=item["evidence"], declaration=item["value"], native_locator=None)
                expected_refs = [item["evidence"]["content"]["source_ref"]]
            _check(row["encoding_basis"] == expected_basis and row["encoding_evidence_refs"] == expected_refs and
                   row["association_ref"] is None, "saved_relationship_conflict", "/populations")
        for original in doc["cells"]:
            native_cell_ids.add(original["id"])
            _check(cells[original["id"]] == original, "saved_relationship_conflict", "/measurements")
    _check(sheet["native_lineage"] == [edge for doc in sheet["documents"] for edge in doc["native_lineage"]],
           "saved_relationship_conflict", "/native_lineage")
    expected_pair_cells = set()
    for row in sheet["populations"]:
        if row["id"] in native_population_ids:
            continue
        matches = []
        pairs = [item for item in selected if item["kind"] == "pair_declaration"]
        for ordinal, item in enumerate(pairs):
            if row["id"] == join_ref("population", sheet["analysis_id"], item["metadata_id"], row["parent_population_refs"]):
                matches.append((ordinal, item))
        _check(len(matches) == 1 and len(row["parent_population_refs"]) == 2, "saved_relationship_conflict", "/populations")
        ordinal, item = matches[0]
        value = item["value"]
        left, right = [populations[ref] for ref in row["parent_population_refs"]]
        doc_ids = [value["left_document_id"], value["right_document_id"]]
        _check(left["document_ids"] == [doc_ids[0]] and right["document_ids"] == [doc_ids[1]] and
               left["population_key"] == right["population_key"] == "fastq_reads" and
               row["document_ids"] == doc_ids and row["population_ordinal"] == ordinal and
               row["pair_key_rule"] == value["pair_key_rule"] and row["population_key"] == "verified_read_pairs" and
               row["member_artifact_refs"] == [documents[d]["artifact"]["id"] for d in doc_ids] and
               row["encoding_basis"] == _unknown_encoding() and row["association_ref"] is None,
               "saved_relationship_conflict", "/populations")
        records = {r["id"]: r for d in doc_ids for r in documents[d]["sequence_records"]}
        members = row["member_record_refs"]
        _check(len(members) % 2 == 0, "saved_relationship_conflict", "/populations")
        parent_key_counts = [Counter(_pair_key(records[ref]["title"], row["pair_key_rule"])
                                     for ref in parent["member_record_refs"]) for parent in (left, right)]
        used_keys = set()
        for index in range(0, len(members), 2):
            lref, rref = members[index:index + 2]
            _check(lref in left["member_record_refs"] and rref in right["member_record_refs"], "saved_relationship_conflict", "/populations")
            lkey, rkey = [_pair_key(records[ref]["title"], row["pair_key_rule"]) for ref in (lref, rref)]
            _check(lkey is not None and lkey == rkey and lkey not in used_keys and
                   all(counts[lkey] == 1 for counts in parent_key_counts),
                   "saved_relationship_conflict", "/populations")
            used_keys.add(lkey)
        if row["scope"] == "complete":
            _check(left["scope"] == right["scope"] == "complete" and
                   set(members) == set(left["member_record_refs"] + right["member_record_refs"]),
                   "saved_relationship_conflict", "/populations")
        reference = join_ref("cell", sheet["analysis_id"], item["metadata_id"], row["parent_population_refs"])
        expected_pair_cells.add(reference)
        cell = cells.get(reference)
        _check(cell is not None and cell["metric"] == "verified_pair_count" and cell["population_ref"] == row["id"] and
               cell["value"] == len(members) // 2 and cell["state"] == ("available" if row["scope"] == "complete" else "partial") and
               cell["artifact_ref"] == row["member_artifact_refs"][0], "saved_relationship_conflict", "/measurements")
    _check(set(cells) == native_cell_ids | expected_pair_cells, "saved_relationship_conflict", "/measurements")


def _validate_document_selection(sheet, parameters, bundle):
    _check([r["document_id"] for r in sheet["document_resolutions"]] == [b["document_id"] for b in parameters["documents"]],
           "saved_relationship_conflict", "/document_resolutions")
    documents = {d["document_id"]: d for d in sheet["documents"]}
    _check(set(documents) == {r["document_id"] for r in sheet["document_resolutions"] if r["state"] == "available"},
           "saved_relationship_conflict", "/documents")
    for binding, resolution in zip(parameters["documents"], sheet["document_resolutions"]):
        contents, members = _matched_contents(bundle, binding["selection"])
        _check(resolution["selection"] == binding["selection"] and resolution["matched_contents"] == contents,
               "saved_relationship_conflict", "/document_resolutions")
        if resolution["state"] == "available":
            _check(len(contents) == 1, "saved_relationship_conflict", "/document_resolutions")
            doc = documents[resolution["document_id"]]
            _check(doc["artifact"]["content_binding"] == contents[0] and resolution["artifact_ref"] == doc["artifact"]["id"] and
                doc["artifact"]["declared_format"] == binding["format"], "saved_relationship_conflict", "/documents")
            scopes = [("complete" if m["transfer"]["body_complete"] and m["transfer"]["object_complete"] == "yes"
                else "partial" if not m["transfer"]["body_complete"] or m["transfer"]["object_complete"] == "no"
                else "unknown") for m in members]
            expected = "partial" if "partial" in scopes else "unknown" if "unknown" in scopes else "complete"
            _check(doc["artifact"]["transfer_scope"] == expected, "saved_relationship_conflict", "/documents")
        else:
            _check(resolution["artifact_ref"] is None, "saved_relationship_conflict", "/document_resolutions")
            _check(len(contents) <= 1 or resolution["state"] == "ambiguous", "saved_relationship_conflict", "/document_resolutions")
            _check(contents or resolution["state"] == "missing", "saved_relationship_conflict", "/document_resolutions")


def validate_saved_projection(sheet: dict | None, saved_components: dict, *, facts: dict,
    status: str, missing_requirements: list[dict], diagnostics: list[dict],
    requested_form: dict, parameters: dict, original_task: dict, bundle: dict) -> None:
    """Check stored identities/relationships and reproject; never parse or score.

    The host separately authenticates the full original selector and provider
    implementation pin. Those operands are intentionally not invented here.
    """
    saved = decode_saved_components(saved_components)
    parameters = validate_parameters(parameters)
    original_task = validate_contract("Host_OriginalTask", original_task)
    bundle = validate_contract("Host_ArtifactBundle", bundle)
    _check(original_task == bundle["original_task"], "saved_relationship_conflict", "/original_task")
    calculations = saved["calculations"]
    if sheet is not None:
        validate_sheet(sheet)
        _validate_original_inputs(sheet, parameters, original_task, bundle)
        _validate_document_selection(sheet, parameters, bundle)
        _validate_metadata_links(sheet)
    if calculations is not None:
        _check(sheet is not None, "saved_relationship_conflict")
        validate_components(calculations, sheet=sheet)
        # Resolving existing semantic selectors is relationship validation;
        # no native reader, sheet constructor or numerical calculator is called.
        expected_parameters = resolve_calculation_inputs(sheet, requests=parameters["calculation_requests"])
        _check(canonical_json(calculations["parameters"]) == canonical_json(expected_parameters),
               "saved_relationship_conflict", "/calculations/parameters")
    expected = project_fastqutils_facts(sheet, calculations, requested_form=requested_form,
        parameters=parameters, failure_context=saved["projection_failure_context"])
    _check(canonical_json(facts) == canonical_json(expected["facts"]) and status == expected["status"],
           "saved_relationship_conflict", "/facts")
    _check(saved["native_requirements"] == expected["requirements"] and saved["native_diagnostics"] == expected["diagnostics"],
           "saved_relationship_conflict", "/native_failures")
    encoded = encode_failures(saved["native_requirements"], saved["native_diagnostics"])
    _check(encoded["missing_requirements"] == missing_requirements and encoded["diagnostics"] == diagnostics,
           "saved_relationship_conflict", "/encoded_failures")


__all__ = ["encode_failures", "encode_saved_components", "decode_saved_components", "validate_saved_projection"]
