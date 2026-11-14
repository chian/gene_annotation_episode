"""Shared A102 scientific return-form examples and iterative-child contract.

Scientific content shared by the explicitly recorded private consumers; these
are not generic serialization rules and do not select a child implementation.
"""
from __future__ import annotations

def form_examples():
    form_example = _runtime._object({
        "changed_annotation_refs": {"type": "array", "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "annotation"},
            "x-source": "changed_annotation_refs",
            "description": "Actual annotation revisions changed during this investigation; these references are not a claim that every revision is still current."},
        "changed_assessment_refs": {"type": "array", "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "assessment"},
            "x-source": "changed_assessment_refs",
            "description": "Actual changed source-linked assessment revisions, retaining their hypotheses, observations, relations and applicability."},
        "changed_interpretation_account_refs": {"type": "array", "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "interpretation_account"},
            "x-source": "changed_interpretation_account_refs",
            "description": _runtime.FACT_MEANINGS['changed_interpretation_account_refs']},
        "scoped_credit": {"type": "number", "x-source": "credit",
            "description": "Credit projected for the fixed child scope at completion, not an accuracy verdict or a stopping instruction."},
    })
    interpretive_example = _runtime._object({
        "interpreted_assessment_refs": _runtime._array({"type": "string", "format": "reference",
            "x-reference-namespace": "assessment",
            "description": "Assessments the child selects as bearing on the assigned distinction. Each resolves to its actual hypothesis, observation, relation, conditions and assumptions; a non-discriminating result remains useful information."}),
        "unresolved_hypothesis_refs": _runtime._array({"type": "string", "format": "reference",
            "x-reference-namespace": "hypothesis",
            "description": "In-scope alternatives the child currently considers unresolved; an empty array makes no claim that every possible explanation was tested."}),
        "changed_annotation_refs": form_example["properties"]["changed_annotation_refs"],
        "interpretation_basis_refs": {"type": "array", "items": {
            "type": "string", "format": "reference"}, "x-source": "interpretation_basis_refs",
            "description": _runtime.FACT_MEANINGS["interpretation_basis_refs"]},
        "observations_after_report_basis": {"type": "array", "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "observation"},
            "x-source": "observations_after_report_basis",
            "description": _runtime.FACT_MEANINGS["observations_after_report_basis"]},
    })
    scope_schema = {"type": "object", "additionalProperties": False,
        "required": ["subject_refs"], "properties": {
            "subject_refs": _runtime._array({"type": "string"}),
            "read_selection_refs": _runtime._array({"type": "string"}),
            "segments": _runtime._array({"type": "object", "additionalProperties": False,
                "required": ["target_ref", "start", "end", "unit"], "properties": {
                "target_ref": {"type": "string"}, "member_ref": {"type": "string"},
                "start": {"type": "integer", "minimum": 0},
                "end": {"type": "integer", "minimum": 1},
                "unit": {"type": "string", "enum": ["nt", "aa", "symbol"]}}})}}
    return form_example, interpretive_example, scope_schema

def scientific_child_contract(form_example, interpretive_example, scope_schema):
    scientific_child = _runtime._object({"kind": {"type": "string", "const": "child"},
        "goal": {"type": "string", "description": "A substantive improvement the child can pursue iteratively and revise from outcomes. A fully specified one-off lookup/calculation belongs to an ordinary tool. Numerical yield controls the child's continuation."},
        "scope": scope_schema,
        "purpose": {"type": "string", "description": "Explain what information you need for your later scientific decision and what your selected form fields mean."},
        "schema_json": {"type": "string", "description": "JSON encoding of your parent-defined closed return form: explicit required fields, additionalProperties false, typed arrays, and strings restricted to enum codes or declared semantic formats. A reference can declare format reference and x-reference-namespace. Optional top-level x-source selectors bind recorded facts named in available_report_facts; do not ask a model to invent those facts. These examples are optional API guidance; choose fields and meanings for your actual later decision. Fact-only example: " + _runtime._json(form_example) + " Interpretive example, selecting actual assessment records rather than a findings paragraph: " + _runtime._json(interpretive_example)},
        "initial_report_json": {"type": "string", "description": "JSON containing exactly the interpretation fields you chose (those without x-source), with parent-supplied initial values. Use {} for the fact-only example; for the interpretive example use {\"interpreted_assessment_refs\":[],\"unresolved_hypothesis_refs\":[]}. Those initial arrays are not new child judgments. If you request other interpreted fields, define their allowed meanings and initialize them explicitly. The runtime does not choose fields or unknown values for you."}})
    return scientific_child

# Bind original module providers after definitions to admit either import order.
from .. import runtime as _runtime
