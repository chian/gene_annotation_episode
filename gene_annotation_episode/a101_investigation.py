"""Construct and receive A101 work in the ordinary recursive scientific role.

The caller assembles the existing scientific, literature and execution services
and freezes its publication/tool catalog first. This module supplies an explicit
commission, bounded return vocabulary and an A101-only workflow factory with
numerical credit installed. It owns no decision loop, tool bundle, scientific
conclusion or continuation policy.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .domain import ContractError, obj
from .evidence_axis_instructions import validate_instruction_entry
from .scientific_process_library import ScientificProcessLibrary
from .scientific_process_records import (SELECTION_VERSION, selector_selection,
    validate_child_selection, validate_revision_origin, validate_selection)
from .scientific_tool_library import ScientificToolLibrary


VERSION = "a101_investigation_v1"
CLAIMS = ("family", "activity", "specificity", "physiological_role")
LIMITATIONS = (
    "fragment_input", "unknown_full_length", "uncharacterized_reference",
    "partial_comparison", "missing_traceback", "ambiguous_correspondence",
    "incompatible_feature", "unobserved_feature", "conflicting_functions",
    "reference_subject_unlinked", "conditions_limit_transfer",
    "partial_acquisition", "no_informative_match", "unassessed_alternatives",
)
_PREDICATES = {
    "family": {"functional_family"},
    "activity": {"catalyzes", "transports", "binds"},
    "specificity": {"catalyzes", "transports", "binds", "uses", "produces"},
    "physiological_role": {"biological_role", "participates_in", "regulates"},
}


def _references(namespace=None, *, source=None, description=None):
    item = {"type": "string", "format": "reference"}
    if namespace is not None:
        item["x-reference-namespace"] = namespace
    result = {"type": "array", "items": item, "uniqueItems": True}
    if source is not None:
        result["x-source"] = source
    if description is not None:
        result["description"] = description
    return result


def report_schema(*, include_sequence_credit=True):
    """An opt-in parent contract; references retain the full scientific records."""
    claim = obj({
        "status": {"type": "string", "enum": [
            "not_assessed", "unresolved", "supported", "limited", "contradicted"],
            "description": "The child's bounded interpretation at its last visible decision; no probability or completion verdict."},
        "hypothesis_refs": _references("hypothesis"),
        "assessment_refs": _references("assessment"),
    })
    claim_fields = {}
    for name in CLAIMS:
        field = deepcopy(claim)
        predicates = ", ".join(sorted(_PREDICATES[name]))
        field["properties"]["hypothesis_refs"]["description"] = (
            f"Target hypotheses for the {name} conclusion, using only these predicates: "
            f"{predicates}. Keep hypotheses for other claim types in their own fields.")
        field["properties"]["assessment_refs"]["description"] = (
            "Assessments of exactly the hypotheses selected in this claim's hypothesis_refs. "
            "Supported, limited and contradicted conclusions require both hypotheses and assessments.")
        claim_fields[name] = field
    result = obj({**claim_fields,
        "alternative_hypothesis_refs": _references("hypothesis"),
        "limitations": {"type": "array", "items": {"type": "string", "enum": list(LIMITATIONS)},
            "uniqueItems": True},
        "records": _references(source="committed_record_refs"),
        "changed_assessment_refs": _references("assessment", source="changed_assessment_refs"),
        "interpretation_basis_refs": _references(source="interpretation_basis_refs"),
        "observations_after_report_basis": _references("observation", source="observations_after_report_basis"),
        "sequence_credit": {"type": "number", "x-source": "credit",
            "description": "Host-calculated A101 native correspondence credit; not a function probability."},
    })
    if not include_sequence_credit:
        del result['properties']['sequence_credit']
        result['required'].remove('sequence_credit')
    validate_closed_schema(result)
    return result


def initial_report():
    """Caller-visible unknowns, without inventing hypotheses or evidence."""
    return {**{name: {"status": "not_assessed", "hypothesis_refs": [], "assessment_refs": []}
        for name in CLAIMS}, "alternative_hypothesis_refs": [], "limitations": []}


class A101Subtree:
    """Use one run's frozen published A101 and actual tool/resource selections."""

    def __init__(self, run_directory):
        directory = Path(run_directory)
        self.library = ScientificProcessLibrary(directory / "scientific-process-library")
        self.tools = ScientificToolLibrary(directory / "scientific-tool-library")
        self.axis = self.library.reference("A101")
        entry = validate_instruction_entry(self.library.resolve(self.axis))
        if entry["name"] != "Sequence homology":
            raise ContractError("a101_sequence_homology_instructions_required")

    def selection(self, *, child_tool_info, thought_id="P01"):
        # Resolve now for actionable errors; the scientific binding materializes
        # these exact selectors again against its actual callables at commission.
        information = self.tools.resolve_tool_info(child_tool_info)
        return selector_selection(validate_selection({"version": SELECTION_VERSION,
            "evidence_axis": deepcopy(self.axis),
            "thought_pattern": self.library.reference(thought_id),
            "child_tool_info": information}))

    def commission(self, store, *, target_ref, scope, completeness,
                   child_tool_info, question, thought_id="P01", evidence_refs=(),
                   constraints=None, context=None, schema=None, initial=None, revision=None):
        """Return a normal ``episode_child`` selection, without starting work.

        A file containing multiple records must already have an explicit selected
        subject. A subregion must be an actual mapped feature/product. Completeness
        is the caller's biological declaration; symbol length is measured metadata.
        A candidate annotation and a public name are intentionally unnecessary.
        """
        if completeness not in {"complete", "fragment", "unknown"}:
            raise ContractError("a101_material_completeness_required")
        if not isinstance(question, str) or not question.strip():
            raise ContractError("a101_investigation_question_required")
        scope = store.validate_scope(plain(scope))
        target = store.get(target_ref)
        if target["record_type"] not in {"input", "product", "feature", "read_subject"}:
            raise ContractError("a101_supplied_target_required")
        footprint = store.coverage(target_ref)
        if not footprint or not store.scope_covers(footprint, scope):
            raise ContractError("a101_material_outside_scope")
        inherited = list(dict.fromkeys([target_ref, *evidence_refs]))
        if set(store.reference_subset(inherited, scope)) != set(inherited):
            raise ContractError("a101_evidence_outside_scope")
        material = {"version": VERSION, "subject_ref": target_ref,
            "supplied_length": store.subject_length(target_ref),
            "unit": store.subject_unit(target_ref),
            "molecule": store.subject_molecule(target_ref),
            "completeness": completeness, "original_intervals": footprint}
        supplied_context = deepcopy(context or {})
        if "a101_material" in supplied_context:
            raise ContractError("a101_material_context_reserved")
        supplied_context["a101_material"] = material
        schema = report_schema() if schema is None else deepcopy(schema)
        validate_closed_schema(schema)
        initial = initial_report() if initial is None else deepcopy(initial)
        validate_form(initial, interpretation_schema(schema),
            lambda reference, namespace: reference in store.reference_subset([reference], scope)
            and (namespace is None or store.get(reference)["record_type"] == namespace))
        assignment = {"selection": self.selection(child_tool_info=child_tool_info, thought_id=thought_id),
            "evidence_refs": inherited, "constraints": deepcopy(constraints or {}), "context": supplied_context}
        if revision is not None:
            try:
                if revision["status"] != "completed":
                    raise ValueError("unfinished_revision")
                prepared = validate_child_selection(revision["result"])
                origin = validate_revision_origin(revision["revision_origin"])
            except (KeyError, TypeError, ValueError) as error:
                raise ContractError("a101_completed_revision_required") from error
            if selector_selection(prepared["selection"]) != assignment["selection"]:
                raise ContractError("a101_revision_selection_mismatch")
            # The tool retains full canonical information. The child action
            # accepts selectors; its binding materializes and authenticates the
            # exact original preparation before constructing the new episode.
            assignment["revision_origin"] = origin
        return {"kind": "episode_child", "role": "scientific_process", "goal": question,
            "scope": scope,
            "purpose": "Return bounded sequence-to-function conclusions, actual scientific evidence and unresolved alternatives; preserve the distinction between family, activity, specificity and physiological role.",
            "schema_json": json.dumps(schema, allow_nan=False),
            "initial_report_json": json.dumps(initial, allow_nan=False),
            "assignment": assignment}


def create_a101_workflow(store, tools, provider, directory, run_id, controller_factory, *,
                         initial_known_record_refs, **options):
    """Construct the ordinary Workflow with A101 numerical credit installed.

    Resources, service assembly, continuation parameters and model providers
    remain caller-owned. The root cannot silently use a finding counter. A
    general child fallback is permitted for other axes; A101's binding always
    selects its native sheet by code.
    """
    from .a101_credit import A101SequenceCredit
    from .runtime import Workflow
    if 'project_credit' in options or 'credit_binding' in options:
        raise ValueError('a101_root_numeric_credit_binding_is_host_owned')
    if options.get('episode_record_receipts', True) is not True:
        raise ValueError('a101_numeric_credit_requires_episode_receipts')
    scorer = A101SequenceCredit()
    options['episode_record_receipts'] = True
    if options.get('project_child_credit') is None:
        options['project_child_credit'] = scorer
        options.setdefault('child_credit_binding', scorer.as_record())
    return Workflow(store, tools, provider, directory, run_id, controller_factory, scorer,
        credit_binding=scorer.as_record(), initial_known_record_refs=initial_known_record_refs,
        **options)


def resolve_report(store, report, *, scope):
    """Resolve an admitted default return for its receiving scientific parent.

    This checks evidence relationships and preserves the actual source subject,
    endpoint, conditions and dependency witnesses. It does not rejudge science,
    acquire records, update credit or replace the frozen interpretation basis.
    """
    scope = store.validate_scope(plain(scope))

    def available(reference, namespace):
        return (reference in store.reference_subset([reference], scope)
            and (namespace is None or store.get(reference)["record_type"] == namespace))

    # Old admitted reports retain their original shape and recorded score.
    validate_form(report, report_schema(include_sequence_credit='sequence_credit' in report), available)
    claims = {}
    for name in CLAIMS:
        claim = report[name]
        hypotheses = [store.get(ref) for ref in claim["hypothesis_refs"]]
        assessments = [store.get(ref) for ref in claim["assessment_refs"]]
        if any(not store.roots(row["id"]) or not set(store.roots(row["id"])) <= set(scope["subject_refs"])
                for row in hypotheses):
            raise ContractError("a101_claim_requires_supplied_target", detail={"claim": name})
        if any(row["predicate"] not in _PREDICATES[name] for row in hypotheses):
            raise ContractError("a101_claim_predicate_mismatch", detail={"claim": name})
        if any(row["hypothesis_ref"] not in claim["hypothesis_refs"] for row in assessments):
            raise ContractError("a101_assessment_hypothesis_mismatch", detail={"claim": name})
        if claim["status"] in {"supported", "limited", "contradicted"} and (
                not hypotheses or not assessments):
            raise ContractError("a101_conclusion_requires_evidence", detail={"claim": name})
        observations = [store.get(row["observation_ref"]) for row in assessments]
        claims[name] = {"status": claim["status"], "hypotheses": hypotheses,
            "assessments": assessments, "observations": observations}
    return {"claims": claims, "sequence_credit": report.get("sequence_credit"),
        "limitations": list(report["limitations"]),
        "alternatives": [store.get(ref) for ref in report["alternative_hypothesis_refs"]],
        "interpretation_basis_refs": list(report["interpretation_basis_refs"]),
        "observations_after_report_basis": list(report["observations_after_report_basis"])}
