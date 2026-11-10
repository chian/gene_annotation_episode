"""Immutable A106 assessment sheets and typed delivery on existing custody."""
from copy import deepcopy
import json

from .domain import REF, ContractError, obj
from .literature_assay_grading_storage import LiteratureAssayGradingRepository
from .literature_intervention_grading import (
    COMPONENTS, CRITERIA, EVALUATION_SCOPE, grade_intervention,
    intervention_grading_input_schema, intervention_grading_sheet_schema,
)
from .literature_assay_grading import assay_grading_cell_schema
from .literature_intervention_inputs import intervention_population_schema, read_intervention_inputs, sample_bindings_schema
from .literature_perturbation_assessments import assessment_schema, validate_assessment

PROVIDER = "literature.a106.intervention_grading"
VERSION = "literature_intervention_grading_record_v1"
NAMESPACE = "literature_intervention_grading_cells"
REQUESTED = "requested_intervention_grading_components"
SCOPE = EVALUATION_SCOPE
OPERATION_DESCRIPTION = (
    "Assess one intervention_response experiment using authenticated source or reader operands. "
    "Retain the actual experimental design, stable experiment identity, assertion and alternative. "
    "Native TRANSIT/DESeq2 rows retain signed effects and reported uncertainty; a p/q value is not "
    "estimate variance. Use the existing fixed-prediction signed log evidence-ratio calculation "
    "when predictions, variance, model and intervention criteria are supported. Missing inputs "
    "remain unresolved. Repeated representations keep the same experiment and assessment key; "
    "a correction names the latest predecessor sheet."
)


def intervention_cells_schema():
    fields = deepcopy(assay_grading_cell_schema()["properties"])
    inputs = intervention_population_schema()["properties"]
    fields.update({key: deepcopy(inputs[key]) for key in ("assay_type", "assertion_ref", "comparison_ref",
        "experiment_ref", "quantity_kind", "interpretations", "prediction_model", "experimental_design", "experiment_assessment")})
    fields.update(sheet_ref={**REF, "x-reference-namespace": "source"},
        evidence_source_ref={**REF, "x-reference-namespace": "source"},
        evidence_measurement_keys={"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        evaluation_scope={"const": SCOPE}, annotation_credit={"type": "null"})
    fields["assertion_ref"] = {**REF, "x-reference-namespace": "hypothesis"}
    fields["sample_bindings"] = sample_bindings_schema()
    required = [*assay_grading_cell_schema()["required"], "assay_type", "assertion_ref", "comparison_ref",
        "experiment_ref", "quantity_kind", "interpretations", "prediction_model", "experimental_design", "experiment_assessment",
        "sheet_ref", "evidence_source_ref", "evidence_measurement_keys", "evaluation_scope", "annotation_credit", "sample_bindings"]
    return {"type": "array", "x-source": NAMESPACE, "items": obj(fields, required=required)}


def _rows(saved, sheet_ref, components):
    sheet, selection = saved["sheet"], saved["selection"]
    shared = {key: deepcopy(sheet[key]) for key in ("assay_type", "assertion_ref", "quantity_kind",
        "interpretations", "prediction_model", "evaluation_scope", "annotation_credit")}
    shared.update({key: deepcopy(selection[key]) for key in ("experiment_ref", "comparison_ref",
        "experimental_design", "experiment_assessment")})
    shared["sample_bindings"] = deepcopy(selection.get("sample_bindings", []))
    # Shared fixed predictions are not additional observations. Preserve the
    # ownership of the observed estimate and its uncertainty separately.
    shared["evidence_measurement_keys"] = list(dict.fromkeys(key
        for role in ("effect", "effect_variance")
        for key in (saved["extraction"]["quantities"].get(role) or {}).get("measurement_keys", ())))
    return [dict(sheet_ref=sheet_ref, evidence_source_ref=selection["source_ref"],
        **deepcopy(sheet["cells"][name]), **deepcopy(shared)) for name in components]


class LiteratureInterventionRepository(LiteratureAssayGradingRepository):
    provider = PROVIDER
    record_version = VERSION
    legacy_version = VERSION
    requested = REQUESTED
    operations_table = "literature_intervention_grading_operations"
    received_table = "literature_intervention_grading_received"
    population_schema = staticmethod(intervention_population_schema)
    read_inputs = staticmethod(read_intervention_inputs)
    input_schema = staticmethod(intervention_grading_input_schema)
    grade = staticmethod(grade_intervention)
    sheet_schema = staticmethod(intervention_grading_sheet_schema)
    rows = staticmethod(_rows)
    cells_schema = staticmethod(intervention_cells_schema)

    def current_assessments(self):
        if not self._installed(self.operations_table):
            return []
        heads, superseded = {}, set()
        for row in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=?", (self.run_id,)):
            sheet_ref = json.loads(row["outcome"])["result"]["sheet_ref"]
            saved = self.read(sheet_ref)
            assessment = saved["selection"]["experiment_assessment"]
            heads[sheet_ref] = deepcopy(assessment)
            if assessment["revises_sheet_ref"] is not None:
                superseded.add(assessment["revises_sheet_ref"])
        result = [dict(sheet_ref=ref, **value) for ref, value in heads.items() if ref not in superseded]
        keys = [(row["experiment_ref"], row["assessment_key"]) for row in result]
        if len(keys) != len(set(keys)):
            raise ContractError("intervention_conflicting_assessment_heads")
        return result

    def before_publish(self, context, arguments):
        assessment = arguments["experiment_assessment"]
        validate_assessment(assessment)
        previous = assessment["revises_sheet_ref"]
        if previous is not None:
            self._record(context, previous)
        key = assessment["experiment_ref"], assessment["assessment_key"]
        head = next((row for row in self.current_assessments()
            if (row["experiment_ref"], row["assessment_key"]) == key), None)
        if (None if head is None else head["sheet_ref"]) != previous:
            detail = {}
            if head is not None and head["sheet_ref"] in context.received_record_refs:
                self._record(context, head["sheet_ref"])
                detail = {"experiment_ref": key[0], "assessment_key": key[1],
                    "requested_predecessor": previous, "latest_sheet_ref": head["sheet_ref"]}
            raise ContractError("intervention_latest_revision_required", detail=detail)

    @staticmethod
    def cell_record_refs(cells):
        refs = LiteratureAssayGradingRepository.cell_record_refs(cells)
        for row in cells:
            refs.append(row["comparison_ref"])
            assessment = row["experiment_assessment"]
            if assessment["revises_sheet_ref"] is not None:
                refs.append(assessment["revises_sheet_ref"])
            refs.extend(value["source_ref"] for value in row["experimental_design"].values() if value is not None)
            for sample in row["sample_bindings"]:
                refs.extend(sample["file_refs"])
                refs.extend(w["source_ref"] for w in sample["file_correspondence"])
                refs.extend(sample[key]["source_ref"] for key in ("identity", "arm_definition", "biological_unit",
                    "technical_unit", "pairing", "batch", "sampling_time") if sample[key] is not None)
        return list(dict.fromkeys(refs))
