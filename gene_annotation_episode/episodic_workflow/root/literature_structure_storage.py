"""Persist selected conditional reference geometry; own no episode decisions.

Original operands stay in the immutable extraction. Returns expose only selected
numerical cells and finite meanings; replay never reads original source bytes.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .library.literature_structure_types import EXPERIMENT_TYPES
from .library import literature_experiment_assessments as assessments
from .library.literature_structure_calculations import (
    COMPONENTS, CONDITIONAL_CODES, REASONS, populate_source_geometry,
)
from .library.literature_structure_input_contracts import structure_population_schema
from .library.literature_structure_inputs import read_structure_inputs

from .library.literature_structure_return_contracts import (
    PROVIDER, FORMULA_CODES, BINDINGS, SOURCE_KINDS, VALIDATION_BINDINGS, _FIXED_METADATA, _metadata, _direct_references, structure_cells_schema,
)

class LiteratureStructureRepository(LiteratureRateRepository):
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_structure_record_v1"
    operations_table = "literature_structure_operations"
    received_table = "literature_structure_received"
    binding_fields = tuple(BINDINGS)

    def _provenance(self, context, reference):
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError("literature_source_outside_scope")
        row = self.store.get(reference)
        if row["record_type"] != "source":
            raise ContractError("literature_source_required")
        return row

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        source = self._provenance(context, reference)
        page = context.assignment if context.role == "literature_page" else context.assignment.get("page")
        if page:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(context, current)
                if current == page["source_ref"]:
                    break
                pending.extend(ancestor.get("parent_source_refs", ()))
            else:
                raise ContractError("literature_reading_outside_assigned_source")
        return source

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, structure_population_schema())
        signature = canonical({"arguments": args, "scope": plain(context.scope)})
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for ref in saved["direct_input_source_refs"]:
                self._source(context, ref)
            for ref in saved["input_source_refs"]:
                self._provenance(context, ref)
            if "experiment_assessment" in args:
                assessments.authorize_assessment(self, context, args["experiment_assessment"])
            return outcome

        assessment = args.get("experiment_assessment")
        if assessment is not None:
            assessments.authorize_assessment(self, context, assessment)
        # Validate every declared direct input before consuming any bytes.
        direct = _direct_references(args)
        for ref in direct:
            self._source(context, ref)
        source = self.store.get(args["source_ref"])
        def read_source(reference, representation):
            row = self._source(context, reference)
            if representation not in ("original", "text"):
                raise ContractError("literature_source_representation_required")
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}
        extraction = read_structure_inputs(args, read_source=read_source)
        if set(extraction["source_refs"]) != set(direct):
            raise ContractError("literature_structure_direct_source_mismatch")
        sheet = populate_source_geometry(extraction["calculation_inputs"])
        parents = list(direct)
        for ref in direct:
            for parent in self.store.get(ref).get("parent_source_refs", ()):
                self._provenance(context, parent)
                parents.append(parent)
        if assessment is not None:
            parents.append(self.store.get(assessment["experiment_ref"])["source_ref"])
            if assessment["revises_sheet_ref"] is not None:
                parents.append(assessment["revises_sheet_ref"])
        parents = list(dict.fromkeys(parents))
        payload = {"version": self.record_version, "input_source_ref": source["id"],
            "input_artifact_ref": source["artifact_ref"], "input_source_refs": parents,
            "direct_input_source_refs": direct, "extraction": extraction, "sheet": sheet,
            "coordinate_source_ref": args["coordinate_source_ref"],
            "validation_source_ref": args["validation_source_ref"]}
        with self.store.transaction():
            if assessment is not None:
                assessments.check_revision(self, assessment)
            created = []
            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                row = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if existed is None:
                    created.append(row["id"])
                return row["id"]
            bindings = {}
            for field, (literal, kind) in BINDINGS.items():
                if field == "experiment_ref" and assessment is not None:
                    bindings[field] = assessment["experiment_ref"]
                    continue
                item = extraction["literals"][literal]
                if item is None:
                    bindings[field] = None
                    continue
                witness = item["witness"]
                anchor = {key: witness[key] for key in (
                    "source_ref", "artifact_ref", "start", "end", "quote")}
                common = {"source_ref": witness["source_ref"], "anchor": anchor}
                if kind == "reference":
                    record = {**common, "reference_type": "assay",
                        "accession": identity("structure_literal", {"field": literal, **anchor}),
                        "label": item["value"], "sequence_ref": None, "molecule": None,
                        "length": None, "term_refs": [], "context_refs": []}
                else:
                    # Field-specific type plus the complete witness makes the
                    # immutable identity distinguish conditions from systems.
                    record = {**common, "context_type": "sample" if literal == "experimental_system"
                        else "assay_condition", "name": item["value"], "attributes": [], "related_refs": []}
                bindings[field] = publish(kind, record)
            if assessment is not None:
                bindings["experiment_ref"] = assessment["experiment_ref"]
                payload["experiment_assessment"] = deepcopy(assessment)
            payload["experimental_bindings"] = bindings
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args, "scope": plain(context.scope)}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None, "parent_source_refs": parents})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *parents,
                    *(ref for ref in bindings.values() if ref)])), "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": sheet["cells"],
                    "assay_interpretation": extraction["literals"], **_metadata(extraction)}, "feedback": None}
            if assessment is not None:
                outcome["result"]["experiment_assessment"] = deepcopy(assessment)
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        args, extraction = request["arguments"], saved["extraction"]
        definitions = _metadata(extraction)
        operation = self.store.db.execute(f"SELECT signature FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        if (source["version"] != self.record_version
                or operation["signature"] != canonical({"arguments": args, "scope": request["scope"]})
                or saved["direct_input_source_refs"] != _direct_references(args)
                or set(extraction["source_refs"]) != set(saved["direct_input_source_refs"])
                or self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]
                or any(extraction[key] != args[key] for key in ("source_ref", "coordinate_source_ref",
                    "validation_source_ref", "source_kind", "evaluation_scope", "model_number"))
                or definitions["geometry_definition"] != args["geometry_panel"]
                or definitions["local_validation_definition"] != args["local_panel"]
                or any(saved[key] != args[key] for key in ("coordinate_source_ref", "validation_source_ref"))):
            raise ContractError("literature_structure_sheet_source_mismatch")
        assessments.validate_saved_assessment(self, saved, request)
        return saved

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_structure_component_selection_invalid")
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(ref)
            for name in components:
                rows.append({"sheet_ref": ref, "evidence_source_ref": saved["input_source_ref"],
                    "coordinate_source_ref": saved["coordinate_source_ref"],
                    "validation_source_ref": saved["validation_source_ref"],
                    **saved["experimental_bindings"], "component": name,
                    **deepcopy(saved["sheet"]["cells"][name]), **_metadata(saved["extraction"])})
        validate_schema(rows, structure_cells_schema())
        return rows

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, structure_cells_schema())
        super().validate_returned_values(cells, permitted_record_refs=permitted_record_refs)


__all__ = ["LiteratureStructureRepository", "COMPONENTS", "PROVIDER",
           "structure_population_schema", "structure_cells_schema"]
