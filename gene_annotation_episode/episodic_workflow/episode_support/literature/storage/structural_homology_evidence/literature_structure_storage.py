"""Persist selected conditional reference geometry; own no episode decisions.

Original operands stay in the immutable extraction. Returns expose only selected
numerical cells and finite meanings; replay never reads original source bytes.

Carried from ``root/a102/literature_structure_storage.py`` at ``97308b94c`` onto the custody-scoped store
(``store``: ``ctx.store`` of the populating tool unit, or ``records`` for reads). What was the old Store's:

* the source an Episode may read was "received" (``context.received_record_refs``); it is now a source the
  Episode holds (``store.holds``), in the commission's scope and, for a reading below a page, derived from the
  page's source;
* the ``literature_structure_operations`` ledger (re-entry on the same operation key) is deleted: the system
  journals each unit's attempt. The sheets one Episode saved are the work table ``OPERATIONS``;
* ``literature_structure_received`` is deleted: that is custody;
* the saved cells are rows of ``CELLS`` (``SheetCustody.publish_cells``), passed on by their row references;
* the revision rule of ``literature_sheet_updates.py`` (A102 copy: ``_policy_for`` is ``None``, so a sheet's family
  is the provider and its arguments, and the latest sheet of a family is its current one) is the work table
  ``CURRENT``; an ``experiment_assessment`` revision (``revises_sheet_ref``) must name the current head of its
  experiment and question (``literature_experiment_assessments.check_revision``) and supersedes it.
"""
from __future__ import annotations

from copy import deepcopy
import json

from episode_runtime import TableDeclaration

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.structural_homology_evidence.literature_structure_calculations import (
    COMPONENTS, CONDITIONAL_CODES, REASONS, populate_source_geometry)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.structural_homology_evidence.literature_structure_types import (
    EXPERIMENT_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading import (
    literature_experiment_assessments as assessments)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_inputs import (
    materialize_text_witness_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.structural_homology_evidence.literature_structure_inputs import (
    read_structure_inputs, structure_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_sheet_custody import (
    SheetCustody)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    canonical, identity, obj, plain, source_location_inputs, validate_schema)

PROVIDER = "literature.experimental.structure"
SOURCE_NAME = "literature_structure_cells"
RECORD_VERSION = "literature_structure_record_v1"
FORMULA_CODES = {name: "structure_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {
    "assayed_subject_ref": ("molecule", "reference"),
    "construct_ref": ("construct", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "partner_ref": ("partner", "reference"),
    "experimental_system_ref": ("experimental_system", "context"),
    "condition_ref": ("condition", "context"),
}
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
VALIDATION_BINDINGS = ("matching_entry_revision", "entry_mismatch", "revision_mismatch",
                       "binding_unreported", "not_supplied")
_FIXED_METADATA = {
    "evaluation_scope": "conditional_deposited_model_geometry",
    "bound_kind": "conditional_arithmetic_outer",
    "unconditional_uncertainty": "unreported",
    "occupancy_basis": "conditioned_selected_model",
    "comparability_basis": "single_state_no_causal_comparison",
    "isolation_basis": "conditioned_atom_assignments",
    "local_validation_granularity": "residue",
    "transform_basis": "identity_coordinates_only",
}

OPERATIONS = TableDeclaration(name='structural_homology_literature_structure_operations', columns=('sheet_ref',),
                              key=('sheet_ref',), record_refs=('sheet_ref',))
CELLS = TableDeclaration(name='structural_homology_literature_structure_cells',
                         columns=('sheet_ref', 'component', 'cell'), key=('sheet_ref', 'component'),
                         record_refs=('sheet_ref',))
CURRENT = TableDeclaration(name='structural_homology_literature_structure_current', columns=('family', 'sheet_ref'),
                           key=('family',), record_refs=('sheet_ref',))


def _metadata(extraction):
    return {**_FIXED_METADATA,
        "validation_binding": extraction["calculation_inputs"]["validation_binding"],
        "operand_source_kind": extraction["source_kind"],
        "model_number": extraction["model_number"],
        "geometry_definition": [{
            "endpoint_a": deepcopy(member["endpoint_a"]["selector"]),
            "endpoint_b": deepcopy(member["endpoint_b"]["selector"]),
            "positive_max_A": member["positive_max_A"],
            "incompatible_min_A": member["incompatible_min_A"],
        } for member in extraction["native_geometry"]],
        "local_validation_definition": [deepcopy(member["selector"])
            for member in extraction["native_local"]]}


def _direct_references(args):
    return list(dict.fromkeys([args["source_ref"], args["coordinate_source_ref"],
        *([args["validation_source_ref"]] if args["validation_source_ref"] else []),
        *(args["literals"][literal]["source_ref"] for literal, _ in BINDINGS.values()
          if args["literals"][literal] is not None)]))


def family(args):
    """The revision family of a sheet (the A102 ``literature_sheet_updates._family`` with no provider policy and no
    input sheets): its provider and its arguments, the assessment's revision fields left out."""
    use = {key: value for key, value in args.items() if key != "experiment_assessment"}
    return identity("literature_scientific_sheet_use", {"provider": PROVIDER, "use": use})


class LiteratureStructureRepository(SheetCustody):
    """Saved source-model geometry sheets over the custody-scoped store (``store``) of the running unit."""
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = RECORD_VERSION
    operations = OPERATIONS
    cells_table = CELLS
    binding_fields = tuple(BINDINGS)

    def __init__(self, store):
        self.store = store

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError("literature_source_outside_scope")
        row = self.store.get(reference)
        if row["record_type"] != "source":
            raise ContractError("literature_source_required")
        return row

    def _source(self, scope, page_source_ref, reference):
        """A direct input: a source this Episode holds, in scope, derived from the assigned page's source when the
        Episode reads below a page."""
        if not self.store.holds(reference):
            raise ContractError("literature_source_not_received")
        source = self._provenance(scope, reference)
        if page_source_ref is not None:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(scope, current)
                if current == page_source_ref:
                    break
                pending.extend(ancestor.get("parent_source_refs", ()))
            else:
                raise ContractError("literature_reading_outside_assigned_source")
        return source

    def _authorize_assessment(self, scope, page_source_ref, value):
        """The old ``authorize_assessment``: an explicitly held, sourced assay identity; never inferred."""
        assessments.validate_assessment(value, self.experiment_types)
        ref = value["experiment_ref"]
        if not self.store.holds(ref):
            raise ContractError("experimental_experiment_not_received")
        record = self.store.get(ref)
        if record["record_type"] != "reference" or record.get("reference_type") != "assay":
            raise ContractError("experimental_experiment_reference_required")
        if not self.store.reference_subset([ref], plain(scope)):
            raise ContractError("experimental_experiment_outside_scope")
        self._source(scope, page_source_ref, record["source_ref"])
        if value["revises_sheet_ref"] is not None:
            self._source(scope, None, value["revises_sheet_ref"])

    def populate(self, scope, page_source_ref, arguments, operation_key):
        """Read the selected coordinate/validation bytes, calculate the six cells and save the sheet, its cells, its
        revision family and its assessment in one transaction. ``page_source_ref`` is the assigned page's source, or
        ``None`` for an Episode that reads no assigned page."""
        args = plain(arguments)
        validate_schema(args, structure_population_schema())
        assessment = args.get("experiment_assessment")
        if assessment is not None:
            self._authorize_assessment(scope, page_source_ref, assessment)
        # Validate every declared direct input before consuming any bytes.
        direct = _direct_references(args)
        for ref in direct:
            self._source(scope, page_source_ref, ref)
        source = self.store.get(args["source_ref"])

        def read_source(reference, representation):
            row = self._source(scope, page_source_ref, reference)
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
                self._provenance(scope, parent)
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
                new = not self.store.holds(identity(kind, {"origin": "tool", "record": record}))
                row = self.store.put(kind, record, origin="tool", scope=plain(scope))
                if new:
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
                anchor = {key: witness[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}
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
                payload["experiment_assessment"] = deepcopy(assessment)
            payload["experimental_bindings"] = bindings
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"operation_key": operation_key, "arguments": args,
                                                     "scope": plain(scope)}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None, "parent_source_refs": parents})
            self.store.table(OPERATIONS).put({"sheet_ref": sheet_ref})
            self.store.table(CURRENT).put({"family": family(args), "sheet_ref": sheet_ref})
            if assessment is not None:
                assessments.record_assessment(self.store, sheet_ref, assessment)
            self.publish_cells(sheet_ref)
            outcome = {"status": "completed", "operation_ref": identity("operation", {"key": operation_key}),
                "record_refs": list(dict.fromkeys([sheet_ref, *parents, *(ref for ref in bindings.values() if ref)])),
                "changed_record_refs": created,
                "result": {"sheet_ref": sheet_ref, "cells": sheet["cells"], **_metadata(extraction)},
                "feedback": None}
            if assessment is not None:
                outcome["result"]["experiment_assessment"] = deepcopy(assessment)
        return outcome

    def read(self, sheet_ref):
        """The saved sheet, checked against the request it was saved for."""
        source = self.store.get(sheet_ref)
        saved = json.loads(self.store.get_artifact(source["artifact_ref"]))
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        args, extraction = request["arguments"], saved["extraction"]
        definitions = _metadata(extraction)
        if (source["provider"] != self.provider or source["version"] != self.record_version
                or saved["version"] != self.record_version
                or saved["direct_input_source_refs"] != _direct_references(args)
                or set(extraction["source_refs"]) != set(saved["direct_input_source_refs"])
                or self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]
                or any(extraction[key] != args[key] for key in ("source_ref", "coordinate_source_ref",
                    "validation_source_ref", "source_kind", "evaluation_scope", "model_number"))
                or definitions["geometry_definition"] != args["geometry_panel"]
                or definitions["local_validation_definition"] != args["local_panel"]
                or any(saved[key] != args[key] for key in ("coordinate_source_ref", "validation_source_ref"))):
            raise ContractError("literature_structure_sheet_source_mismatch")
        assessments.validate_saved_assessment(self, saved, request, sheet_ref)
        return saved

    def current_sheet_refs(self):
        """The current sheets of this Episode: the latest sheet of each revision family, less every sheet an
        assessment revision superseded. Earlier versions are retained, not current."""
        heads = {row["family"]: row["sheet_ref"] for row in self.store.table(CURRENT).select()}
        superseded = {row["assessment"]["revises_sheet_ref"]
                      for row in self.store.table(assessments.ASSESSMENTS).select()}
        return [ref for ref in heads.values() if ref not in superseded]

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)

    def project_cells(self, sheet_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_structure_component_selection_invalid")
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            saved = self.read(ref)
            for name in components:
                rows.append({"sheet_ref": ref, "evidence_source_ref": saved["input_source_ref"],
                    "coordinate_source_ref": saved["coordinate_source_ref"],
                    "validation_source_ref": saved["validation_source_ref"],
                    **saved["experimental_bindings"], "component": name,
                    **deepcopy(saved["sheet"]["cells"][name]), **_metadata(saved["extraction"])})
        validate_schema(rows, structure_cells_schema())
        return rows


TOOL_DESCRIPTION = ('Populate source-model geometry and local residue RSCC components from received coordinates and '
                    'optional matching deposited validation. Select exact model/author atom groups and fixed physical '
                    'criteria. Preserve missing endpoints, validation entry/revision mismatch and unreported coordinate '
                    'uncertainty. The explicit scope is conditional deposited-model geometry; it does not establish '
                    'population occupancy, causal mechanism, target correspondence or annotation credit.')


def population_input_schema():
    """What the model supplies: the population arguments with each literal witness as a source location (the host
    reads the quotation)."""
    return source_location_inputs(structure_population_schema())


def populate_structure_sheet(store, scope, page_source_ref, arguments, operation_key):
    """The ``literature.structure.populate`` operation (old ``execute`` and ``_materialize_text_arguments``): fill
    each selected literal witness's quotation from the held source bytes, then populate and save the sheet."""
    repository = LiteratureStructureRepository(store)

    def read_source(reference, representation):
        source = repository._source(scope, page_source_ref, reference)
        artifact = source["artifact_ref"] if representation == "original" else source.get("text_ref")
        if artifact is None:
            raise ContractError("literature_source_representation_unavailable")
        return {"artifact_ref": artifact, "content": store.get_artifact(artifact)}
    materialized = materialize_text_witness_inputs(plain(arguments), read_source=read_source)
    return repository.populate(scope, page_source_ref, materialized, operation_key)


def structure_cells_schema():
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    inputs = structure_population_schema()["properties"]
    properties = {"sheet_ref": dict(source), "evidence_source_ref": dict(source),
        **{field: {**source, "type": ["string", "null"]} for field in (
            "coordinate_source_ref", "validation_source_ref")},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        **{field: {"type": ["number", "null"], "minimum": -1, "maximum": 1}
            for field in ("value", "lower", "upper")},
        "unit": {"type": "string", "enum": ["dimensionless"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "origin": {"type": "string", "enum": ["proposed"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        "validation_binding": {"type": "string", "enum": list(VALIDATION_BINDINGS)},
        "operand_source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "model_number": deepcopy(inputs["model_number"]),
        "geometry_definition": deepcopy(inputs["geometry_panel"]),
        "local_validation_definition": deepcopy(inputs["local_panel"]),
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": SOURCE_NAME}


__all__ = ["LiteratureStructureRepository", "COMPONENTS", "PROVIDER", "SOURCE_NAME", "OPERATIONS", "CELLS",
           "CURRENT", "TOOL_DESCRIPTION", "population_input_schema", "populate_structure_sheet",
           "structure_population_schema", "structure_cells_schema"]
