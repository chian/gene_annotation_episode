"""Immutable A106 final results on the existing numerical-cell custody path."""
from copy import deepcopy
from hashlib import sha256
import json

from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema
from .literature_assay_grading_storage import LiteratureAssayGradingRepository
from .literature_assay_inputs import _Sources
from .literature_intervention_storage import LiteratureInterventionRepository, intervention_cells_schema
from .literature_a106_subscore import (
    COMPONENTS, REQUESTED, NAMESPACE, SCORE_COMPONENT, population_schema,
    cell_schema, cells_schema, finalize_a106, TASK,
)

PROVIDER = "literature.a106.subscore"
VERSION = "literature_a106_subscore_record_v1"
OPERATION_DESCRIPTION = TASK
QUESTION_FIELDS = ("subject_ref", "assertion_ref", "comparison_ref", "scope_statement")


def _rows(saved, sheet_ref, components):
    return [{"sheet_ref": sheet_ref, **deepcopy(saved["sheet"]["cells"][name])} for name in components]


class LiteratureA106SubscoreRepository(LiteratureAssayGradingRepository):
    # Reuse only immutable persistence, projection and receipt helpers. Final
    # publication reads possessed assessment cells; it never reruns a grader.
    provider = PROVIDER
    record_version = legacy_version = VERSION
    requested = REQUESTED
    components = COMPONENTS
    operations_table = "literature_a106_subscore_operations"
    received_table = "literature_a106_subscore_received"
    rows = staticmethod(_rows)
    cells_schema = staticmethod(cells_schema)

    def _question_key(self, args):
        return identity("a106_question", {key: args[key] for key in QUESTION_FIELDS})

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, population_schema())
        requested = list(context.assignment.get(REQUESTED, ()))
        if len(requested) != len(set(requested)) or any(name not in COMPONENTS for name in requested):
            raise ContractError("a106_component_selection_invalid")
        request = dict(run_id=self.run_id, episode_id=context.episode_id, operation_key=operation_key,
            arguments=args, scope=plain(context.scope), requested_components=requested)
        signature = canonical(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?", (self.run_id, context.episode_id, operation_key)
        ).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            for ref in self.read(outcome["result"]["sheet_ref"])["direct_record_refs"]:
                self._record(context, ref)
            return outcome
        direct, bindings = [], {}
        def retain(ref, kind=None, possessed=True):
            record = self._record(context, ref) if possessed else self._native_provenance(context.scope, ref)
            if kind is not None and record["record_type"] != kind:
                raise ContractError("a106_record_type_mismatch")
            bindings[ref] = identity("a106_subscore_input", record)
            if possessed and ref not in direct:
                direct.append(ref)
            return record
        retain(args["subject_ref"])
        for key in ("assertion_ref", "comparison_ref"):
            claim = retain(args[key], "hypothesis")
            if args["subject_ref"] not in claim["subject_refs"]:
                raise ContractError("a106_subject_assertion_mismatch")
        def read_source(ref, representation):
            source = retain(ref, "source")
            field = "artifact_ref" if representation == "original" else "text_ref"
            artifact = source.get(field)
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            raw = self.store.get_artifact(artifact)
            if artifact != "artifact_" + sha256(raw).hexdigest():
                raise ContractError("a106_subscore_input_hash_mismatch")
            return {"artifact_ref": artifact, "content": raw}
        sources = _Sources(read_source)
        for witness in args["dependence"]["witnesses"]:
            sources.witness(witness, "between_experiment_dependence")
        native = LiteratureInterventionRepository(self.store, self.run_id)
        source_rows = []
        for experiment in args["experiments"]:
            record = retain(experiment["experiment_ref"], "reference")
            if record.get("reference_type") != "assay":
                raise ContractError("a106_experiment_reference_required")
            ref = experiment["sheet_ref"]
            if ref is not None:
                retain(ref, "source")
                rows = native.fact_cells(context, [ref], components=[SCORE_COMPONENT])
                if len(rows) != 1:
                    raise ContractError("a106_assessment_component_not_received")
                source_rows.extend(rows)
        prior = args["revises_subscore_ref"]
        question = self._question_key(args)
        if prior is not None:
            retain(prior, "source")
            predecessor = self.read(prior)
            if predecessor["question_key"] != question:
                previous = {key: predecessor["selection"][key] for key in QUESTION_FIELDS}
                proposed = {key: args[key] for key in QUESTION_FIELDS}
                raise ContractError("a106_revision_question_mismatch", detail={
                    "revises_subscore_ref": prior,
                    "different_fields": [key for key in QUESTION_FIELDS if previous[key] != proposed[key]],
                    "previous_question": previous, "proposed_question": proposed,
                    "requirement": "A revision must retain its predecessor's exact question binding. For a different biological scope, create a separate question without a predecessor."})
        cell = finalize_a106(args, source_rows)
        input_sources = [ref for ref in bindings if self.store.get(ref)["record_type"] == "source"]
        input_sources.extend(record["source_ref"] for ref in list(bindings)
            if (record := self.store.get(ref)).get("source_ref"))
        input_sources = list(dict.fromkeys(input_sources))
        for ref in input_sources:
            source = retain(ref, "source", possessed=False)
            for ancestor in source.get("parent_source_refs", ()):
                if ancestor not in input_sources:
                    input_sources.append(ancestor)
        payload = dict(version=VERSION, selection=args, question_key=question, source_cells=source_rows,
            direct_record_refs=direct, record_bindings=bindings, input_source_refs=input_sources,
            sheet={"cells": {COMPONENTS[0]: cell}})
        with self.store.transaction():
            self._install()
            current_assessments = {row["sheet_ref"] for row in native.current_assessments()}
            if any(row["sheet_ref"] not in current_assessments for row in source_rows):
                raise ContractError("a106_current_assessment_required")
            heads, superseded = [], set()
            for row in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=?", (self.run_id,)):
                ref = json.loads(row["outcome"])["result"]["sheet_ref"]
                saved = self.read(ref)
                if saved["question_key"] == question:
                    heads.append(ref)
                    superseded.add(saved["selection"]["revises_subscore_ref"])
            if [ref for ref in heads if ref not in superseded] != ([] if prior is None else [prior]):
                raise ContractError("a106_latest_subscore_revision_required")
            artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(signature, "application/json")
            record = self.store.put("source", dict(provider=PROVIDER, accession=None, uri=None,
                artifact_ref=artifact, text_ref=artifact, request_ref=request_ref, version=VERSION,
                retrieved_at=None, parent_source_refs=input_sources), origin="tool", scope=plain(context.scope))
            outcome = dict(status="completed", operation_ref=identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                record_refs=[record["id"]], changed_record_refs=[record["id"]], feedback=None,
                result={"sheet_ref": record["id"], "cells": _rows(payload, record["id"], requested)})
            validate_schema(outcome["result"]["cells"], cells_schema())
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get("record_type") != "source" or source.get("origin") != "tool"
                or source.get("provider") != PROVIDER or source.get("version") != VERSION):
            raise ContractError("a106_subscore_sheet_required")
        value = {key: val for key, val in source.items() if key not in {"id", "record_type", "origin"}}
        if identity("source", {"origin": "tool", "record": value}) != sheet_ref:
            raise ContractError("a106_subscore_identity_mismatch")
        request = self._artifact_json(source["request_ref"])
        if request.get("run_id") != self.run_id:
            raise ContractError("a106_subscore_run_mismatch")
        scope = self.store.validate_scope(request["scope"])
        self._native_provenance(scope, sheet_ref)
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])
        ).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation["signature"] != canonical(request):
            raise ContractError("a106_subscore_operation_mismatch")
        saved = self._artifact_json(source["artifact_ref"])
        outcome = json.loads(operation["outcome"])
        if (saved.get("version") != VERSION or saved.get("selection") != request["arguments"]
                or saved.get("question_key") != self._question_key(request["arguments"])
                or saved.get("input_source_refs") != source["parent_source_refs"]
                or outcome.get("status") != "completed" or outcome.get("record_refs") != [sheet_ref]
                or outcome.get("result", {}).get("sheet_ref") != sheet_ref
                or outcome.get("operation_ref") != identity("operation", {
                    "run_id": self.run_id, "episode_id": request["episode_id"], "key": request["operation_key"]})):
            raise ContractError("a106_subscore_saved_mismatch")
        validate_schema(saved["selection"], population_schema())
        validate_schema(saved["source_cells"], intervention_cells_schema())
        validate_schema(saved["sheet"]["cells"][COMPONENTS[0]], cell_schema())
        for ref, digest in saved["record_bindings"].items():
            if (not self.store.reference_subset([ref], plain(scope))
                    or identity("a106_subscore_input", self.store.get(ref)) != digest):
                raise ContractError("a106_subscore_input_mismatch")
        if not set(saved["direct_record_refs"]) <= set(saved["record_bindings"]):
            raise ContractError("a106_subscore_input_mismatch")
        native = LiteratureInterventionRepository(self.store, self.run_id)
        for row in saved["source_cells"]:
            expected = native.project_cells([row["sheet_ref"]], permitted_record_refs=[row["sheet_ref"]],
                components=[SCORE_COMPONENT])
            if canonical(expected) != canonical([row]):
                raise ContractError("a106_subscore_input_mismatch")
        rows = _rows(saved, sheet_ref, request["requested_components"])
        if canonical(rows) != canonical(outcome["result"]["cells"]):
            raise ContractError("a106_subscore_saved_cells_mismatch")
        return saved

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        for row in cells:
            refs.extend(row[key] for key in ("sheet_ref", "subject_ref", "assertion_ref", "comparison_ref", "revises_subscore_ref"))
            refs.extend(row["source_refs"])
            refs.extend(item["experiment_ref"] for item in row["experiments"])
            refs.extend(LiteratureInterventionRepository.cell_record_refs(row["selected_components"]))
        return list(dict.fromkeys(ref for ref in refs if ref is not None))
