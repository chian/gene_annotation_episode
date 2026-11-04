"""Source-backed operands and experimental design for the A106 assessment."""
from copy import deepcopy
import hashlib

from .domain import REF, ContractError, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema, SOURCE_KINDS
from .literature_assay_grading_inputs import (
    assay_grading_population_schema, _literal, _unit, _support, _component,
)
from .literature_intervention_grading import (
    INPUT_VERSION, ROLES, REQUIRED_ROLES, intervention_grading_input_schema,
)
from .literature_perturbation_assessments import assessment_schema
from .intervention_analysis_native import parse_intervention_artifact, calculate_intervention_components

DESIGN_FIELDS = ("molecule", "strain", "construct", "intervention", "reference_condition",
    "restoration_arm", "endpoint", "measurement_scale", "sampling_time", "replication",
    "shared_controls", "reference_version", "analysis_protocol", "comparison_direction")
ANALYSIS_METRICS = ("reference_mean", "intervention_mean", "log2_fold_change", "mean_difference",
                    "base_mean", "standard_error", "effect_variance", "p_value", "adjusted_p_value")
COMPARISON_NAMESPACE = "literature_measurement_comparison_cells"
COMPARISON_EFFECTS = {
    **{name: "native_endpoint" for name in ("native_left", "native_right", "converted_left", "converted_right")},
    "protocol_difference": "endpoint_difference", "protocol_ratio": "endpoint_ratio",
}


def sample_bindings_schema():
    witness = _witness_schema()
    nullable = {"anyOf": [deepcopy(witness), {"type": "null"}]}
    return {"type": "array", "items": obj({
        "sample_id": {"type": "string", "minLength": 1}, "identity": deepcopy(witness),
        "file_refs": {"type": "array", "items": {**REF, "x-reference-namespace": "source"}, "uniqueItems": True},
        "file_correspondence": {"type": "array", "items": deepcopy(witness),
            "description": "One source witness per file_refs entry, in the same order, linking that file to this sample."},
        "arm": {"enum": ["reference", "intervention", "restoration", "other", "unknown"]},
        "arm_definition": deepcopy(nullable), "biological_unit": deepcopy(nullable),
        "technical_unit": deepcopy(nullable), "pairing": deepcopy(nullable),
        "batch": deepcopy(nullable), "sampling_time": deepcopy(nullable)})}


def intervention_population_schema(*, legacy=False):
    schema = intervention_grading_input_schema()
    props = schema["properties"]
    del props["version"]
    existing = assay_grading_population_schema()["properties"]
    props.update({name: deepcopy(existing[name]) for name in ("source_ref", "source_kind", "experiment_ref")})
    props["experiment_assessment"] = assessment_schema()
    props["comparison_ref"] = {**deepcopy(REF), "x-reference-namespace": "hypothesis"}
    witness = _witness_schema()
    props["experimental_design"] = obj({key: {"anyOf": [deepcopy(witness), {"type": "null"}]} for key in DESIGN_FIELDS})
    props["sample_bindings"] = sample_bindings_schema()
    native = obj({"kind": {"const": "native_analysis"}, "source_ref": deepcopy(REF),
        "representation": {"enum": ["transit_resampling", "deseq2"]},
        "row_ordinal": {"type": "integer", "minimum": 0}, "feature_id": {"type": "string", "minLength": 1},
        "metric": {"enum": list(ANALYSIS_METRICS)}})
    application = deepcopy(native)
    application["properties"].update(kind={"const": "application_analysis"},
        sheet_ref=application["properties"].pop("source_ref"),
        field={"type": "string", "minLength": 1})
    application["required"] = list(application["properties"])
    props["quantities"] = obj({role: {"anyOf": [
        *deepcopy(existing["quantities"]["properties"][role]["anyOf"][:2]), deepcopy(native), deepcopy(application), {"type": "null"}]}
        for role in ROLES}, required=list(REQUIRED_ROLES))
    for role in ROLES:
        choices = props["quantities"]["properties"][role]["anyOf"]
        received = choices[0]
        received["properties"]["namespace"]["enum"].append(COMPARISON_NAMESPACE)
        received["description"] += (
            " Published specific-activity tables with shared header units can use literature.measurement_comparison.populate. "
            "Its native/converted left or right estimates supply native_endpoint; protocol_difference supplies endpoint_difference; "
            "protocol_ratio supplies endpoint_ratio. difference_variance supplies uncertainty only for protocol_difference "
            "from the same sheet. Standardized discrepancies, weights and conditional scenarios are not intervention effects.")
        choices[1]["description"] += (
            " number_start and number_end are character offsets within number.witness.quote, starting at zero. "
            "The witness start/end fields are absolute UTF-8 byte offsets in the source. "
            "Whitespace, including Unicode thin spaces, may separate the number and unit.")
    schema["required"] = [name for name in props if name != "sample_bindings"]
    return schema


def _intervention_unit(raw):
    text = raw.strip()
    if text in {"log2_ratio", "log2FC", "log2_fold_change"}:
        return "log2_ratio", 1.
    if text in {"log2_ratio_squared", "log2FC^2", "log2_fold_change_squared"}:
        return "log2_ratio_squared", 1.
    return _unit(raw)


def read_comparison_operand(selection, *, role, quantity_kind, read_cells):
    """Use existing selected measurements, never a discrepancy score as evidence."""
    component = selection["component"]
    if role == "effect_variance":
        valid = component == "difference_variance" and quantity_kind == "endpoint_difference"
    elif role in {"effect", "assertion_prediction", "alternative_prediction"}:
        valid = COMPARISON_EFFECTS.get(component) == quantity_kind
    else:
        valid = False
    if not valid:
        raise ContractError("intervention_comparison_quantity_role_mismatch")
    from .literature_measurement_comparison_storage import measurement_comparison_cells_schema
    operand, _ = _component(selection, read_cells, schema=measurement_comparison_cells_schema())
    operand["qualifications"].append("measurement_comparison_requires_intervention_design_assessment")
    return operand


def read_analysis_operand(selection, *, sources):
    """Read the exact selected retained row; repeated acquisitions share a key.

    The source callback owns possession and integrity. No service task or sample
    identity is inferred for a deposited processed table. The design witnesses
    and intervention assessment establish those scientific relationships.
    """
    source = sources.source(selection["source_ref"], "original")
    raw = source["content"]
    digest = hashlib.sha256(raw).hexdigest()
    content = dict(source_ref=selection["source_ref"], artifact_field="artifact_ref",
        artifact_ref=source["artifact_ref"], sha256=digest, byte_count=len(raw))
    document = parse_intervention_artifact(raw, content=content, representation=selection["representation"],
        capture_complete=False, expected_task_id="retained_source:" + selection["source_ref"])
    components = calculate_intervention_components(document)
    ordinal = selection["row_ordinal"]
    if ordinal >= len(components["rows"]):
        raise ContractError("intervention_analysis_row_missing")
    row = components["rows"][ordinal]
    feature = row["metrics"].get("feature_id")
    if feature is None or feature["state"] != "available" or feature["value"] != selection["feature_id"]:
        raise ContractError("intervention_analysis_feature_mismatch")
    cell = row["metrics"].get(selection["metric"])
    if cell is None:
        raise ContractError("intervention_analysis_metric_unsupported")
    line = document["native_document"]["lines"][row["line_index"]]
    key = identity("intervention_native_measurement", {"artifact_sha256": digest,
        "byte_start": line["byte_start"], "byte_end": line["byte_end"]})
    qualifications = ["native_analysis_requires_experimental_design_assessment", "selected_retained_row_only"]
    if selection["representation"] == "deseq2" and selection["metric"] in {"effect_variance", "standard_error"}:
        qualifications.append("estimated_variance_from_reported_deseq2_standard_error")
    return dict(value=cell["value"], unit=cell["unit"], status="point" if cell["state"] == "available" else "unavailable",
        reason=None if cell["state"] == "available" else "native_metric_" + cell["state"],
        measurement_keys=[key], source_refs=[selection["source_ref"]], origin="derived",
        native_component=selection["representation"] + ":" + selection["metric"], qualifications=qualifications)


def read_application_operand(selection, *, read_cells):
    from .bvbrc_application_returns import validate_application_rows, FACT_SOURCE
    from .bvbrc_intervention_contracts import VALUE_VERSION
    rows = read_cells(FACT_SOURCE, selection["sheet_ref"], [selection["field"]])
    validate_application_rows(rows)
    if len(rows) != 1 or rows[0]["source_ref"] != selection["sheet_ref"] or rows[0]["field"] != selection["field"]:
        raise ContractError("intervention_analysis_field_not_received")
    value = rows[0]["value"]
    context = value["context"]
    if (value["version"] != VALUE_VERSION or context.get("representation") != selection["representation"]
            or value["selection"]["kind"] != "records" or context.get("content") is None):
        raise ContractError("intervention_analysis_representation_mismatch")
    matches = [row for row in value["records"] if row["requested_ordinal"] == selection["row_ordinal"]]
    if len(matches) != 1 or matches[0]["state"] != "available":
        raise ContractError("intervention_analysis_row_not_received")
    row = matches[0]["value"]
    metrics, location = row.get("measurements"), row.get("source_location")
    if metrics is None or location is None:
        raise ContractError("intervention_analysis_required_members_not_received")
    feature = metrics.get("feature_id")
    if feature is None or feature["state"] != "available" or feature["value"] != selection["feature_id"]:
        raise ContractError("intervention_analysis_feature_mismatch")
    metric = metrics.get(selection["metric"])
    if metric is None:
        raise ContractError("intervention_analysis_metric_unsupported")
    key = identity("intervention_native_measurement", {"artifact_sha256": context["content"]["sha256"],
        "byte_start": location["byte_start"], "byte_end": location["byte_end"]})
    qualifications = ["native_analysis_requires_experimental_design_assessment", "selected_received_row_only"]
    if not context["capture_complete"]:
        qualifications.append("native_capture_incomplete")
    if selection["representation"] == "deseq2" and selection["metric"] == "effect_variance":
        qualifications.append("estimated_variance_from_reported_deseq2_standard_error")
    return dict(value=metric["value"], unit=metric["unit"], status="point" if metric["state"] == "available" else "unavailable",
        reason=None if metric["state"] == "available" else "native_metric_" + metric["state"],
        measurement_keys=[key], source_refs=[selection["sheet_ref"]], origin="derived",
        native_component=selection["representation"] + ":" + selection["metric"], qualifications=qualifications)


def read_intervention_inputs(arguments, *, read_source, read_cells, read_record, read_database_request=None):
    args = deepcopy(arguments)
    validate_schema(args, intervention_population_schema())
    sources = _Sources(read_source)
    sources.source(args["source_ref"], "original")
    def support(ref, field, *, hypothesis=False):
        try:
            return _support(ref, read_record=read_record, sources=sources, hypothesis=hypothesis)
        except ContractError as error:
            if str(error) != "assay_grading_anchored_support_required":
                raise
            raise ContractError(str(error), detail=dict(field=field, reference=ref,
                expected_record_type="reference",
                requirement="Use a received reference record with an exact source anchor, such as experiment_ref. "
                    "A document source_ref alone is not an anchored interpretation witness.")) from error
    experiment = support(args["experiment_ref"], "experiment_ref")
    if experiment.get("reference_type") != "assay" or args["experiment_assessment"]["experiment_ref"] != args["experiment_ref"]:
        raise ContractError("intervention_experiment_identity_mismatch")
    previous = args["experiment_assessment"]["revises_sheet_ref"]
    if previous is not None:
        read_record(previous)
        sources.source(previous, "original")
    for key in ("assertion_ref", "comparison_ref"):
        support(args[key], key, hypothesis=True)
    if args["comparison_ref"] == args["assertion_ref"]:
        raise ContractError("intervention_distinct_comparison_required")
    for key, witness in args["experimental_design"].items():
        if witness is not None:
            sources.witness(witness, "experimental_design." + key)
    sample_ids = set()
    for sample in args.get("sample_bindings", []):
        if sample["sample_id"] in sample_ids:
            raise ContractError("intervention_duplicate_sample_identity")
        sample_ids.add(sample["sample_id"])
        for key in ("identity", "arm_definition", "biological_unit", "technical_unit", "pairing", "batch", "sampling_time"):
            if sample[key] is not None:
                sources.witness(sample[key], "sample." + key)
        if len(sample["file_refs"]) != len(sample["file_correspondence"]):
            raise ContractError("intervention_sample_file_correspondence_required")
        for witness in sample["file_correspondence"]:
            sources.witness(witness, "sample.file_correspondence")
        for ref in sample["file_refs"]:
            if read_record(ref)["record_type"] != "source":
                raise ContractError("intervention_sample_file_source_required")
    for criterion, meaning in args["interpretations"].items():
        for ref in meaning["support_refs"]:
            support(ref, "interpretations." + criterion + ".support_refs")
    if args["prediction_model"] is not None:
        for ref in args["prediction_model"]["support_refs"]:
            support(ref, "prediction_model.support_refs")
    quantities = {}
    for role, selected in args["quantities"].items():
        if selected is None:
            quantities[role] = None
        elif selected["kind"] == "source_number":
            quantities[role] = _literal(selected, sources, unit_reader=_intervention_unit)
        elif selected["kind"] == "received_component":
            if selected["namespace"] == COMPARISON_NAMESPACE:
                quantities[role] = read_comparison_operand(selected, role=role,
                    quantity_kind=args["quantity_kind"], read_cells=read_cells)
            else:
                quantities[role], _ = _component(selected, read_cells)
        else:
            if role not in {"effect", "effect_variance"}:
                raise ContractError("intervention_analysis_cannot_supply_prediction_or_control")
            if (role == "effect_variance") != (selected["metric"] == "effect_variance"):
                raise ContractError("intervention_analysis_quantity_role_mismatch")
            if selected["metric"] in {"standard_error", "p_value", "adjusted_p_value"}:
                raise ContractError("intervention_statistic_is_not_effect_or_variance")
            quantities[role] = (read_analysis_operand(selected, sources=sources)
                if selected["kind"] == "native_analysis" else read_application_operand(selected, read_cells=read_cells))
        if quantities[role] is not None and args["source_kind"] == "synthetic_fixture":
            quantities[role]["origin"] = "synthetic"
    model = args["prediction_model"]
    if model is not None and model["variance_interpretation"] == "known" and any(
            "estimated" in qualification for qualification in (quantities.get("effect_variance") or {}).get("qualifications", ())):
        raise ContractError("intervention_known_variance_conflicts_with_reader")
    effect, variance = args["quantities"].get("effect"), args["quantities"].get("effect_variance")
    if variance and variance["kind"] == "received_component" and variance["namespace"] == COMPARISON_NAMESPACE:
        if not effect or effect["kind"] != "received_component" or effect["namespace"] != COMPARISON_NAMESPACE or (
                effect["component"] != "protocol_difference" or effect["sheet_ref"] != variance["sheet_ref"]):
            raise ContractError("intervention_variance_estimate_mismatch")
    if variance and variance["kind"] in {"native_analysis", "application_analysis"}:
        keys = ("source_ref",) if variance["kind"] == "native_analysis" else ("sheet_ref", "field")
        if not effect or effect["kind"] != variance["kind"] or effect["metric"] != "log2_fold_change" or any(
                variance[key] != effect[key] for key in (*keys, "representation", "row_ordinal", "feature_id")):
            raise ContractError("intervention_variance_estimate_mismatch")
    result = {key: deepcopy(args[key]) for key in ("assay_type", "assertion_ref", "quantity_kind", "interpretations", "prediction_model")}
    result.update(version=INPUT_VERSION, quantities=quantities)
    validate_schema(result, intervention_grading_input_schema())
    return result
