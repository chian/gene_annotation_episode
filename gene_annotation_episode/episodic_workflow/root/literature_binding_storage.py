"""Persist selected source binding contrasts and forward exact requested cells.

Visual tables are retained transcriptions, with original image custody checked
here. This adapter neither reads pixels nor decides an experiment's meaning.
"""
from __future__ import annotations

from io import BytesIO
import json

from PIL import Image, UnidentifiedImageError

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, REF, canonical, identity, obj, validate_schema
from .literature_assay_inputs import _Sources
from .library.literature_rate_unit_witness_schema import _witness_schema
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import COMPONENTS, REASONS
from .library.literature_binding_calculations import FORMULAS, populate_binding_contrast
from .library.literature_binding_reader import read_binding_parameter_table
from .literature_rate_storage import LiteratureRateRepository


PROVIDER = "literature.experimental.binding_parameter"
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import PARAMETER_KINDS
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import DESIGNS
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import ARRANGEMENTS
REPRESENTATIONS = ("retained_visual_transcription", "primary_table", "synthetic_fixture")
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import BINDINGS
COMPARISON_FIELDS = ("subject", "state", "experiment", "reference_ligand", "test_ligand",
                     "parameter_kind", "design", "protein_arrangement")
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import FORMULA_CODES
FORMULA_MEANINGS = {FORMULA_CODES[name]: FORMULAS[name] for name in COMPONENTS}


def binding_population_schema():
    """Only source selections and witnessed scientific interpretations are inputs."""
    text = {"type": "string", "minLength": 1, "pattern": r"\S"}
    return obj({"source_ref": REF, "representation": {"enum": list(REPRESENTATIONS)},
        **{name: dict(text) for name in ("subject", "state", "experiment", "reference_ligand", "test_ligand")},
        "parameter_kind": {"enum": list(PARAMETER_KINDS)}, "design": {"enum": list(DESIGNS)},
        "protein_arrangement": {"enum": list(ARRANGEMENTS)},
        "interpretation_witnesses": {"type": "array", "items": _witness_schema()}})


class LiteratureBindingRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_binding_parameter_record_v1"
    operations_table = "literature_binding_operations"
    received_table = "literature_binding_received"
    binding_fields = BINDINGS

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError("literature_source_outside_scope")
        row = self.store.get(reference)
        if row["record_type"] != "source":
            raise ContractError("literature_source_required")
        page = context.assignment if context.role == "literature_page" else context.assignment.get("page")
        if page:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                if not self.store.reference_subset([current], plain(context.scope)):
                    raise ContractError("literature_source_outside_scope")
                ancestor = self.store.get(current)
                if ancestor["record_type"] != "source":
                    raise ContractError("literature_source_required")
                if current == page["source_ref"]:
                    break
                pending.extend(ancestor.get("parent_source_refs", ()))
            else:
                raise ContractError("literature_reading_outside_assigned_source")
        return row

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, binding_population_schema())
        signature = canonical({"arguments": args, "scope": plain(context.scope)})
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            for reference in self.read(outcome["result"]["sheet_ref"])["input_source_refs"]:
                self._source(context, reference)
            return outcome

        source = self._source(context, args["source_ref"])
        try:
            text = self.store.get_artifact(source["artifact_ref"]).decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContractError("literature_utf8_table_required") from error
        extraction = read_binding_parameter_table({"source_ref": source["id"],
            "artifact_ref": source["artifact_ref"], "text": text, "representation": args["representation"]},
            expected_subject=args["subject"], expected_state=args["state"], expected_experiment=args["experiment"],
            reference_ligand=args["reference_ligand"], test_ligand=args["test_ligand"],
            parameter_kind=args["parameter_kind"])

        def read_source(reference, representation):
            row = self._source(context, reference)
            artifact = row["artifact_ref"] if representation == "original" else row.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

        sources = _Sources(read_source)
        witnesses = [sources.witness(item, f"interpretation_witnesses[{i}]")
                     for i, item in enumerate(args["interpretation_witnesses"])]
        unique_witnesses = {(row["source_ref"], row["artifact_ref"], row["representation"], row["start"], row["end"])
                            for row in witnesses}
        if any(args[name] != "unknown" for name in ("design", "protein_arrangement")) and not witnesses:
            raise ContractError("binding_interpretation_witness_required")
        if any(args[name] == "conflicting" for name in ("design", "protein_arrangement")) and len(unique_witnesses) < 2:
            raise ContractError("binding_conflict_witnesses_required")
        parents = list(dict.fromkeys([source["id"], *sources.references]))
        if args["representation"] == "retained_visual_transcription":
            # The reader validates the full table, including unselected rows.
            # Inspect all its locators for custody without selecting new science.
            for row in json.loads(text)["rows"]:
                locator = row["locator"]
                original = self._source(context, locator["original_source_ref"])
                if (original["artifact_ref"] != locator["original_artifact_ref"]
                        or original["id"] not in source.get("parent_source_refs", ())):
                    raise ContractError("retained_visual_lineage_mismatch")
                parents.append(original["id"])
                try:
                    with Image.open(BytesIO(self.store.get_artifact(original["artifact_ref"]))) as picture:
                        picture.load()
                        width, height = picture.size
                except (UnidentifiedImageError, OSError, ValueError) as error:
                    raise ContractError("retained_visual_original_image_required") from error
                x0, y0, x1, y1 = locator["image_region"]
                if not 0 <= x0 < x1 <= width or not 0 <= y0 < y1 <= height:
                    raise ContractError("retained_visual_region_outside_image")
        # Every declared input parent remains part of custody and replay, even
        # when it is not the image used by the selected rows (e.g. unit Methods).
        for reference in source.get("parent_source_refs", ()):
            self._source(context, reference)
            parents.append(reference)
        sheet = populate_binding_contrast(extraction)
        payload = {"version": self.record_version, "input_source_ref": source["id"],
            "input_source_refs": list(dict.fromkeys(parents)), "input_artifact_ref": source["artifact_ref"],
            "sheet": sheet, "comparison": {name: args[name] for name in COMPARISON_FIELDS},
            "interpretation_kind": "episode_source_interpretation", "interpretation_witnesses": witnesses}
        with self.store.transaction():
            created = []

            def publish(kind, record):
                candidate = identity(kind, {"origin": "tool", "record": record})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                published = self.store.put(kind, record, origin="tool", scope=plain(context.scope))
                if existed is None:
                    created.append(published["id"])
                return published["id"]

            bindings = {}
            any_rows = bool(sheet["reference_rows"] or sheet["test_rows"])
            for name, label_field in zip(BINDINGS, ("subject", "state", "experiment", "reference_ligand", "test_ligand")):
                present = (bool(sheet[label_field.split("_")[0] + "_rows"])
                           if label_field.endswith("_ligand") else any_rows)
                bindings[name] = publish("reference", {"reference_type": "literature_result",
                    "source_ref": source["id"], "accession": identity("binding_label", {
                        "source": source["id"], "role": name, "label": args[label_field]}),
                    "label": args[label_field], "sequence_ref": None, "molecule": None, "length": None,
                    "term_refs": [], "context_refs": []}) if present else None
            payload["experimental_bindings"] = bindings
            artifact = self.store.artifact(canonical(payload), "application/json")
            request = self.store.artifact(canonical({"run_id": self.run_id, "episode_id": context.episode_id,
                "operation_key": operation_key, "arguments": args}), "application/json")
            sheet_ref = publish("source", {"provider": self.provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": artifact, "request_ref": request,
                "version": self.record_version, "retrieved_at": None,
                "parent_source_refs": payload["input_source_refs"]})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": [sheet_ref, *dict.fromkeys(ref for ref in bindings.values() if ref)],
                "changed_record_refs": created, "result": {"sheet_ref": sheet_ref, "cells": sheet["cells"],
                    "comparison": payload["comparison"], "interpretation_kind": payload["interpretation_kind"]},
                "feedback": None}
            outcome["result"].update({field: sheet[field] for field in (
                "uncertainty_basis", "minimum_experiment_count", "independent_preparation_count")})
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple)) or len(set(components)) != len(components)
                or any(name not in self.components for name in components)):
            raise ContractError("literature_binding_component_selection_invalid")
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(reference)
            sheet = saved["sheet"]
            for name in components:
                cell = {key: value for key, value in sheet["cells"][name].items() if key != "formula"}
                result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    **saved["experimental_bindings"], "component": name, **cell, "formula_code": FORMULA_CODES[name],
                    **{field: sheet[field] for field in ("parameter_kind", "uncertainty_basis",
                        "minimum_experiment_count", "independent_preparation_count")},
                    "source_origins": sorted({row["origin"] for row in sheet["reference_rows"] + sheet["test_rows"]}),
                    **{field: saved["comparison"][field] for field in ("design", "protein_arrangement")},
                    "interpretation_kind": saved["interpretation_kind"]})
        return result


from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import binding_cells_schema
__all__ = ["LiteratureBindingRepository", "PROVIDER", "COMPONENTS", "FORMULA_CODES", "FORMULA_MEANINGS",
           "binding_population_schema", "binding_cells_schema"]
