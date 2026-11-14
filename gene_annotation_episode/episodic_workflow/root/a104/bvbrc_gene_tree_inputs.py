"""GeneTree-specific assembly and saved-sheet validation.

The shared provider owns parsed documents, native observations and checked
member/source joins. This module adds only the locus table and the fixed tool
identity. It never acquires artifacts, reads paths or executes an analysis.
Inclusion records describe actual representations, not confidence in function.
"""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import quote

from .bvbrc_phylogeny_common_inputs import (
    extract_common_fields,
    input_member_subject_id,
)
from .bvbrc_phylogeny_common_contracts import validate_shared_fields


SCHEMA_VERSION = "bvbrc_gene_tree_sheet_v1"
TOOL = "C-L194-GeneTree"
STAGES = ("supplied", "post_align", "post_trim", "post_gap_filter",
          "final_matrix", "final_tree")
DIAGNOSTIC_CODES = frozenset({
    "gene_tree_primary_analysis_required", "gene_tree_analysis_mode_invalid",
    "gene_tree_analysis_loci_invalid", "gene_tree_locus_binding_invalid",
    "gene_tree_locus_binding_conflict", "gene_tree_locus_member_unknown",
    "gene_tree_locus_join_conflict", "gene_tree_locus_order_conflict",
    "gene_tree_locus_membership_unknown", "gene_tree_locus_table_invalid",
    "gene_tree_locus_inclusion_conflict", "gene_tree_header_conflict",
})
REQUIREMENT_REASONS = frozenset({"gene_tree_locus_membership_unknown"})


class _Invalid(ValueError):
    def __init__(self, code, path=""):
        self.code, self.path = code, path
        super().__init__(code)


def _require(ok, code, path=""):
    if not ok:
        raise _Invalid(code, path)


def _strings(values, code, path):
    _require(type(values) is list and
             all(type(item) is str and item for item in values), code, path)
    _require(len(values) == len(set(values)), code, path)


def _member_key(member):
    _require(type(member) is dict and set(member) == {"input_binding_id", "member_id"}
             and all(type(value) is str and value for value in member.values()),
             "gene_tree_locus_binding_invalid", "/assembly/locus_bindings")
    return member["input_binding_id"], member["member_id"]


def _merge_evidence(*arrays):
    out = []
    for array in arrays:
        for item in array:
            if item not in out:
                out.append(deepcopy(item))
    return out


def _same(left, right):
    """Compare closed saved values without equating booleans with integers."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _primary(common):
    analyses = common["documents"]["analyses"]
    _require(type(analyses) is list and len(analyses) == 1,
             "gene_tree_primary_analysis_required", "/documents/analyses")
    analysis = analyses[0]
    _require(analysis["mode"] in {"gene_tree", "concatenated_sequence_loci"},
             "gene_tree_analysis_mode_invalid", "/documents/analyses/0/mode")
    _strings(analysis["locus_ids"], "gene_tree_analysis_loci_invalid",
             "/documents/analyses/0/locus_ids")
    _require(analysis["analysis_id"] == common["assembly"]["analysis_id"],
             "gene_tree_primary_analysis_required", "/assembly/analysis_id")
    return analysis


def _loci(common):
    """Derive exact finite stage records from the saved input/join operands.

    A final row proves its representation exists even if every symbol is a gap.
    It does not prove alignment, trimming or filtering history. Only a matching
    explicit end_trim transformation establishes post_trim. An absent row/tip
    yields unknown, never exclusion. Input members retain distinct binding IDs.
    """
    analysis = _primary(common)
    inputs = {(binding["binding_id"], member["member_id"]): member
              for binding in common["inputs"] for member in binding["members"]}
    bindings = {}
    for index, binding in enumerate(common["assembly"]["locus_bindings"]):
        path = "/assembly/locus_bindings/" + str(index)
        _require(type(binding) is dict and set(binding) == {
            "locus_id", "input_members", "completeness", "evidence"},
            "gene_tree_locus_binding_invalid", path)
        locus_id = binding["locus_id"]
        _require(type(locus_id) is str and bool(locus_id) and
                 binding["completeness"] in {"complete", "partial", "truncated", "unknown"}
                 and type(binding["input_members"]) is list,
                 "gene_tree_locus_binding_invalid", path)
        _require(locus_id not in bindings, "gene_tree_locus_binding_conflict", path)
        keys = [_member_key(member) for member in binding["input_members"]]
        _require(len(keys) == len(set(keys)), "gene_tree_locus_binding_conflict", path)
        _require(all(key in inputs for key in keys), "gene_tree_locus_member_unknown", path)
        bindings[locus_id] = binding

    # The binding order is retained; otherwise-unbound selected/observed loci
    # survive without inventing a complete supplied member population.
    locus_ids = list(bindings)
    for locus_id in analysis["locus_ids"] + [row["locus_id"] for row in common["joins"]["input_rows"]]:
        if locus_id not in locus_ids:
            locus_ids.append(locus_id)
    transformations = {row["transformation_id"]: row
                       for row in common["joins"]["transformations"]}
    for row in transformations.values():
        _require(set(row["locus_order"]) <= set(locus_ids),
                 "gene_tree_locus_order_conflict", "/joins/transformations")
        if row["kind"] == "concatenate" and any(
                ref["alignment_id"] == analysis["aligned_document_id"]
                for ref in row["output_rows"]):
            _require(analysis["mode"] == "concatenated_sequence_loci" and
                     (not row["locus_order"] or set(row["locus_order"]) == set(analysis["locus_ids"])),
                     "gene_tree_locus_order_conflict", "/joins/transformations")
    for row in common["joins"]["input_rows"]:
        if row["transformation_id"] is not None:
            transform = transformations[row["transformation_id"]]
            _require(not transform["locus_order"] or row["locus_id"] in transform["locus_order"],
                     "gene_tree_locus_order_conflict", "/joins/input_rows")

    loci, diagnostics, requirements = [], [], []
    for locus_index, locus_id in enumerate(locus_ids):
        binding = bindings.get(locus_id)
        members = deepcopy(binding["input_members"]) if binding else []
        relevant_rows = [row for row in common["joins"]["input_rows"]
                         if row["locus_id"] == locus_id]
        member_keys = {_member_key(member) for member in members}
        for row in relevant_rows:
            key = (row["input_binding_id"], row["member_id"])
            _require(key in inputs, "gene_tree_locus_member_unknown", "/joins/input_rows")
            if key not in member_keys:
                _require(binding is None or binding["completeness"] != "complete",
                         "gene_tree_locus_join_conflict", "/joins/input_rows")
                members.append({"input_binding_id": key[0], "member_id": key[1]})
                member_keys.add(key)
        completeness = binding["completeness"] if binding else "unknown"
        if binding is None:
            code = "gene_tree_locus_membership_unknown"
            diagnostics.append({"code": code, "phase": "association",
                "path": "/loci/" + str(locus_index), "severity": "qualification",
                "evidence_refs": []})
            requirements.append({"requirement_id": "gene_tree/locus/" + quote(locus_id, safe="-._~") + "/membership",
                "kind": "scientific_metadata", "role": "locus_membership", "source_refs": [],
                "reason_code": code})
        included_analysis = locus_id in analysis["locus_ids"]
        inclusion = []
        for member in members:
            key = _member_key(member)
            subject_id = input_member_subject_id(*key)
            original = inputs[key]
            supplied_evidence = _merge_evidence(
                binding["evidence"] if binding else [],
                [original["evidence"]] if original["evidence"] is not None else [])
            rows = [row for row in relevant_rows
                    if (row["input_binding_id"], row["member_id"]) == key]
            final_rows = [row for row in rows if included_analysis and
                          row["alignment_id"] == analysis["aligned_document_id"]]
            row_refs = {(row["alignment_id"], row["row_index"]) for row in final_rows}
            trims = [row for row in transformations.values() if row["kind"] == "end_trim"
                     and member in row["input_members"] and any(
                         (ref["alignment_id"], ref["row_index"]) == (linked["alignment_id"], linked["row_index"])
                         and (linked["transformation_id"] == row["transformation_id"]
                              or locus_id in row["locus_order"])
                         for ref in row["output_rows"] for linked in rows)]
            gaps = [transformations[row["transformation_id"]] for row in final_rows
                    if row["transformation_id"] is not None and
                    transformations[row["transformation_id"]]["kind"] == "missing_locus_gap_fill"]
            tips = [row for row in common["joins"]["tip_rows"]
                    if row["tree_id"] in {analysis["raw_tree_id"], analysis["phyloxml_tree_id"]}
                    and (row["alignment_id"], row["row_index"]) in row_refs]
            records = {
                "supplied": (True, None, supplied_evidence),
                "post_align": (False, None, []),
                "post_trim": (bool(trims), None, _merge_evidence(*(row["evidence"] for row in trims))),
                "post_gap_filter": (False, None, []),
                "final_matrix": (bool(final_rows), "missing_locus_gap_fill" if gaps else None,
                    _merge_evidence(*(row["evidence"] for row in final_rows), *(row["evidence"] for row in gaps))),
                "final_tree": (bool(tips), "missing_locus_gap_fill" if tips and gaps else None,
                    _merge_evidence(*(row["evidence"] for row in final_rows), *(row["evidence"] for row in tips),
                                    *(row["evidence"] for row in gaps))),
            }
            for stage in STAGES:
                present, reason, evidence = records[stage]
                inclusion.append({"subject_id": subject_id, "stage": stage,
                    "state": "included" if present else "unknown", "reason": reason,
                    "native_reason_location": None, "evidence": evidence})
        loci.append({"locus_id": locus_id, "input_members": members,
            "analysis_ids": [analysis["analysis_id"]] if included_analysis else [],
            "inclusion": inclusion, "completeness": completeness})
    return loci, diagnostics, requirements


def validate_gene_tree_sheet(sheet: dict) -> dict:
    """Validate the full saved provider sheet, returning a detached value."""
    common = validate_shared_fields(sheet, provider="gene_tree")
    analysis = _primary(common)
    _require(sheet["schema_version"] == SCHEMA_VERSION and sheet["tool"] == TOOL and
             sheet["mode"] == analysis["mode"], "gene_tree_header_conflict", "/mode")
    loci, diagnostics, requirements = _loci(common)
    _require(type(sheet["loci"]) is list, "gene_tree_locus_table_invalid", "/loci")
    _require(_same(sheet["loci"], loci), "gene_tree_locus_inclusion_conflict", "/loci")
    _require(all(row in sheet["qualifications"] for row in diagnostics) and
             all(row in sheet["missing_requirements"] for row in requirements),
             "gene_tree_locus_inclusion_conflict", "/loci")
    return deepcopy(sheet)


def extract_gene_tree_sheet(*, documents: dict, inputs: tuple[dict, ...],
                            observed_run: dict, joins: dict, assembly: dict,
                            parameters: dict) -> dict:
    """Populate one explicit primary analysis while retaining auxiliary data."""
    common_result = extract_common_fields(provider="gene_tree", documents=documents,
        inputs=inputs, observed_run=observed_run, joins=joins, assembly=assembly,
        parameters=parameters)
    if common_result["value"] is None:
        return deepcopy(common_result)
    common = deepcopy(common_result["value"])
    try:
        analysis = _primary(common)
        loci, diagnostics, requirements = _loci(common)
        for row in diagnostics:
            if row not in common["qualifications"]:
                common["qualifications"].append(row)
        for row in requirements:
            matches = [item for item in common["missing_requirements"]
                       if item["requirement_id"] == row["requirement_id"]]
            _require(not matches or matches == [row], "gene_tree_locus_binding_conflict", "/missing_requirements")
            if not matches:
                common["missing_requirements"].append(row)
        sheet = {"schema_version": SCHEMA_VERSION, "tool": TOOL,
                 "mode": analysis["mode"], **common, "loci": loci}
        validate_gene_tree_sheet(sheet)
    except _Invalid as error:
        diagnostic = {"code": error.code, "phase": "association", "path": error.path,
                      "severity": "error", "evidence_refs": []}
        return {"status": "invalid", "value": None,
                "diagnostics": deepcopy(common_result["diagnostics"]) + [diagnostic]}
    output_diagnostics = deepcopy(common_result["diagnostics"])
    output_diagnostics.extend(row for row in diagnostics if row not in output_diagnostics)
    status = "partial" if requirements or common_result["status"] != "ok" else "ok"
    return {"status": status, "value": sheet, "diagnostics": output_diagnostics}


__all__ = ["extract_gene_tree_sheet", "validate_gene_tree_sheet", "DIAGNOSTIC_CODES",
           "REQUIREMENT_REASONS"]
