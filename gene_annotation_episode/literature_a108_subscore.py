"""Publish the selected, claim-bound A108 compatibility result.

Sources are combined as requirements/routes/contexts by the existing context
calculator. This publication binds that question's result to its assertion and
preserves its scope; it does not add scores from papers or invent a reducer.
"""
from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, REF, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_context_storage import LiteratureContextRepository, context_semantic_cells_schema

PROVIDER = "literature.a108.subscore"
VERSION = "literature_a108_subscore_v1"
NAMESPACE = "literature_a108_subscore_cells"
REQUESTED = "requested_a108_subscore_components"
COMPONENTS = ("selected_lower", "selected_upper", "selected_point", "sampling_lower", "sampling_upper")

TASK = """Complete the A108 assessment for the declared functional assertion and biological scope. A108 evaluates organism capability or sample-context coverage. Choose the question from the assertion and retain it through source assessment. Sources contribute evidence to one explicit set of requirements, alternative routes and physical contexts; papers are not independent score units. Populate literature.context.populate with source_selection to assess acquired evidence, then select literature.a108.finalize for that assessment. Its selected_lower, selected_upper and selected_point are the existing calculator's answer to the declared question. Sampling bounds retain their separate conditional meaning. There is no sum across papers, new weighting, annotation probability or overall annotation-credit calculation.

Use actual received subject and hypothesis references in source_selection.question. The hypothesis states the possible function; question.scope fixes the organism/strain, relevant biological situation and sample frame. Record why this question follows from that claim. Define the question's permitted biological states from the claim and legitimate supplied context. Keep each experiment's observed conditions attached to its witness within that scope. An observed setting limits what that experiment establishes; it does not by itself define every permitted state of an organism-capability question. Record and explain any change to the chosen question before using its recalculated result. Cite requirement definitions and observations separately. Read native numerical operands from exact source spans; for qualitative state relations preserve the supported/incompatible/unresolved interpretation and its evidence. Include relevant unresolved requirements. Source observations must establish the actual scope; an assay setting alone is not an organism or habitat witness. Retain all applicable requirements, joint support, genuine alternative routes, original sample identities and shared measurements in the assessment.

For retained work from another episode, use state.query pages and source.read to inspect saved assessments and publications. Establish the latest publication for the fixed question through the saved revision relationships and query continuations; immutable source records can include superseded publications even when current_only is true. Numerical possession comes from an assessment or publication created by this episode, or exact cells admitted through a typed return. When recovery supplies source records or worksheet bytes without those cells, review the saved interpretation against the received underlying evidence and use literature.context.populate with source_selection to create this episode's assessment. Preserve the saved question, original measurement identities and dependence, and make evidence corrections explicit. Then finalize its five selected/sampling components, including unavailable ones, against the latest predecessor. Recreating a calculation is not a new experiment or an independent evidence unit.

Finalize only an assessment whose selected numerical components you possess. Return requested literature_a108_subscore_cells through the parent's typed form, together with the biological conclusion and limitations. Include supporting_evidence_refs for received sources, observations, assessments or contexts used to support the conclusion, limitations or revision explanation beyond the numerical assessment's existing provenance. These references preserve evidence access; they do not add numerical operands or independent score units. Finalization retains the selected assessment and copies its question rationale into every returned row. When that assessment's rationale, source interpretation, requirement, route, context relation or numerical operand needs correction, populate a corrected assessment and select it as the publication's source_ref, even when the component values stay the same. The publication's conclusion, limitations and revision reason describe the result and correction alongside that assessment. A publication revision keeps the same subject_ref, assertion_ref, question_kind and exact question.scope text. Put additional explanations of an unchanged scope in the rationale, conclusion or limitations. Name the latest revises_subscore_ref and explain the evidence correction. A genuinely different scope is a separate question and publication; preserve its relationship to the original question explicitly in the conclusion and limitations. Duplicate representations are not extra scores. A bound with an unavailable point is a useful unresolved result. A zero lower bound alone does not establish incompatibility. Keep the original scope visible when proposing a different claim or question."""


def _supporting_evidence_schema():
    return {"type": "array", "items": {**deepcopy(REF), "format": "reference"}, "uniqueItems": True,
        "description": "Actually received source, observation, assessment or context references supporting the publication's conclusion, limitations or revision explanation. These preserve access to additional interpretive evidence; they do not change the assessment's operands, numerical result or measurement independence. An empty array adds no evidence references."}


def population_schema():
    schema = obj({"source_ref": {**REF, "x-reference-namespace": "source",
        "description": "Saved claim-bound assessment to publish. Its numerical components and question rationale are retained. To correct that assessment's rationale or source interpretation, first populate a corrected assessment and select its source_ref here, even when the numerical values are unchanged."},
        "conclusion": {"type": "string", "minLength": 1},
        "limitations": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "revises_subscore_ref": {**REF, "type": ["string", "null"], "x-reference-namespace": "source",
            "description": "Latest publication for the same subject, assertion, question kind and exact scope text; null for a new question."},
        "revision_reason": {"type": ["string", "null"], "minLength": 1}})
    # Older saved requests remain valid; omitted supporting evidence means none.
    schema["properties"]["supporting_evidence_refs"] = _supporting_evidence_schema()
    return schema


def cells_schema():
    schema = context_semantic_cells_schema()
    schema["x-source"] = NAMESPACE
    fields = schema["items"]["properties"]
    fields["component"]["enum"] = list(COMPONENTS)
    reference = {**deepcopy(REF), "format": "reference"}
    additions = {"assessment_sheet_ref": {**reference, "x-reference-namespace": "source"},
        "subject_ref": deepcopy(reference), "assertion_ref": {**reference, "x-reference-namespace": "hypothesis"},
        "scope_statement": {"type": "string", "minLength": 1},
        "question_rationale": {"type": "string", "minLength": 1},
        "conclusion": {"type": "string", "minLength": 1},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "revises_subscore_ref": {**reference, "type": ["string", "null"], "x-reference-namespace": "source"},
        "revision_reason": {"type": ["string", "null"]},
        "axis": {"type": "string", "const": "A108"},
        "score_meaning": {"type": "string", "const": "scoped_context_compatibility"}}
    fields.update(additions)
    schema["items"]["required"].extend(additions)
    # Optional for already-published rows, whose original contents stay exact.
    fields["supporting_evidence_refs"] = _supporting_evidence_schema()
    return schema


class LiteratureA108SubscoreRepository(LiteratureRateRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = "literature_a108_subscore_operations"
    received_table = "literature_a108_subscore_received"
    binding_fields = ()

    def cells_schema(self):
        return cells_schema()

    def _record(self, context, ref, kind=None):
        if ref not in context.received_record_refs:
            raise ContractError("a108_record_not_received")
        if not self.store.reference_subset([ref], plain(context.scope)):
            raise ContractError("a108_record_outside_scope")
        record = self.store.get(ref)
        if kind is not None and record["record_type"] != kind:
            raise ContractError("a108_record_type_mismatch")
        return record

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, population_schema())
        if (args["revises_subscore_ref"] is None) != (args["revision_reason"] is None):
            raise ContractError("a108_revision_reason_required")
        request = {"run_id": self.run_id, "episode_id": context.episode_id,
            "operation_key": operation_key, "arguments": args, "scope": plain(context.scope)}
        signature = canonical(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for ref in saved["direct_record_refs"]:
                self._record(context, ref)
            return outcome
        source = self._record(context, args["source_ref"], "source")
        contexts = LiteratureContextRepository(self.store, self.run_id).semantic_projection()
        rows = contexts.fact_cells(context, [args["source_ref"]], components=list(COMPONENTS))
        if [row["component"] for row in rows] != list(COMPONENTS):
            raise ContractError("a108_assessment_components_not_received")
        assessment = contexts.read(args["source_ref"])
        selected = assessment["extraction"]["arguments"].get("source_selection")
        if selected is None:
            raise ContractError("a108_claim_bound_assessment_required")
        question = selected["question"]
        self._record(context, question["subject_ref"])
        self._record(context, question["assertion_ref"], "hypothesis")
        supporting_refs = args.get("supporting_evidence_refs", [])
        supporting_sources = []
        for ref in supporting_refs:
            evidence = self._record(context, ref)
            if evidence["record_type"] not in {"source", "observation", "assessment", "context"}:
                raise ContractError("a108_supporting_evidence_type_mismatch")
            if evidence["record_type"] == "source":
                supporting_sources.append(ref)
        question_key = identity("a108_question", {key: question[key] for key in
            ("subject_ref", "assertion_ref", "scope")} | {"question_kind": selected["settings"]["question_kind"]})
        prior = args["revises_subscore_ref"]
        if prior is not None:
            self._record(context, prior, "source")
            predecessor = self.read(prior)
            if predecessor["question_key"] != question_key:
                previous_binding = {key: predecessor["question"][key] for key in
                    ("subject_ref", "assertion_ref", "scope")}
                previous_binding["question_kind"] = predecessor["sheet"]["cells"]["selected_lower"]["question_kind"]
                proposed_binding = {key: question[key] for key in
                    ("subject_ref", "assertion_ref", "scope")}
                proposed_binding["question_kind"] = selected["settings"]["question_kind"]
                raise ContractError("a108_revision_question_mismatch", detail={
                    "revises_subscore_ref": prior,
                    "different_fields": [key for key in previous_binding
                        if previous_binding[key] != proposed_binding[key]],
                    "previous_question": previous_binding,
                    "proposed_question": proposed_binding})
        extra = {"assessment_sheet_ref": args["source_ref"], "axis": "A108",
            "score_meaning": "scoped_context_compatibility", "subject_ref": question["subject_ref"],
            "assertion_ref": question["assertion_ref"], "scope_statement": question["scope"],
            "question_rationale": question["rationale"],
            "supporting_evidence_refs": deepcopy(supporting_refs),
            **{key: deepcopy(args[key]) for key in ("conclusion", "limitations", "revises_subscore_ref", "revision_reason")}}
        input_sources = list(dict.fromkeys([args["source_ref"], *source.get("parent_source_refs", ()),
            *supporting_sources, *([prior] if prior else [])]))
        direct = list(dict.fromkeys([args["source_ref"], question["subject_ref"],
            question["assertion_ref"], *supporting_refs, *([prior] if prior else [])]))
        with self.store.transaction():
            heads, superseded = [], set()
            for operation in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=?", (self.run_id,)):
                result = json.loads(operation["outcome"])["result"]
                if result["question_key"] == question_key:
                    heads.append(result["sheet_ref"])
                    if result["revises_subscore_ref"] is not None:
                        superseded.add(result["revises_subscore_ref"])
            current = [ref for ref in heads if ref not in superseded]
            if current != ([] if prior is None else [prior]):
                raise ContractError("a108_latest_subscore_revision_required")
            payload = {"version": VERSION, "input_source_ref": args["source_ref"],
                "input_source_refs": input_sources, "direct_record_refs": direct,
                "question_key": question_key, "question": deepcopy(question),
                "source_cells": deepcopy(rows), "return_metadata": extra,
                "sheet": {"cells": {row["component"]: deepcopy(row) for row in rows}}}
            artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(signature, "application/json")
            record = self.store.put("source", {"provider": PROVIDER, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request_ref,
                "version": VERSION, "retrieved_at": None, "parent_source_refs": input_sources},
                origin="tool", scope=plain(context.scope))
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([record["id"], *direct, *input_sources])),
                "changed_record_refs": [record["id"]],
                "result": {"sheet_ref": record["id"], "question_key": question_key,
                    "revises_subscore_ref": prior, "cells": payload["sheet"]["cells"],
                    "final_rows": [{**deepcopy(row), "sheet_ref": record["id"], **extra} for row in rows]},
                "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        body = self.store.get_artifact(source["artifact_ref"])
        if "artifact_" + hashlib.sha256(body).hexdigest() != source["artifact_ref"]:
            raise ContractError("a108_saved_subscore_mismatch")
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        result = json.loads(operation["outcome"])["result"]
        if (operation["signature"] != canonical(request) or result["question_key"] != saved["question_key"]
                or result["cells"] != saved["sheet"]["cells"]):
            raise ContractError("a108_saved_subscore_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple)) or len(set(components)) != len(components)
                or any(name not in self.components for name in components)):
            raise ContractError("a108_component_selection_invalid")
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(ref)
            rows.extend({**deepcopy(saved["sheet"]["cells"][name]), "sheet_ref": ref,
                **deepcopy(saved["return_metadata"])} for name in components)
        validate_schema(rows, self.cells_schema())
        return rows
