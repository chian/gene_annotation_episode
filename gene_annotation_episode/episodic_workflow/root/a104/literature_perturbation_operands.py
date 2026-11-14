"""Typed A106 operands projected from original saved perturbation measurements.

This view copies calculated cells and their original dependencies; it performs
no new scientific calculation. Historical point/summary return contracts remain
unchanged, and possession of those older views does not grant this new view.
"""
from copy import deepcopy
import hashlib

from .domain import REF, ContractError, canonical, identity, obj, validate_schema
from .literature_assay_grading import operand_schema
from .literature_perturbation_storage import LiteraturePerturbationRepository, PROVIDER, BINDINGS
from .literature_perturbation_summary_storage import LiteraturePerturbationSummaryProjection

VERSION = "perturbation_operand_return_v1"
NAMESPACE = "literature_perturbation_operand_cells"
REQUESTED = "requested_perturbation_operand_components"
ENDPOINTS = {"reference_endpoint": "W", "perturbed_endpoint": "K", "restored_endpoint": "R"}
EFFECTS = {**{name: "native_endpoint" for name in ENDPOINTS},
    "perturbation_difference": "endpoint_difference", "restoration_difference": "endpoint_difference"}
VARIANCES = {**{role + "_mean_variance": name for name, role in ENDPOINTS.items()},
    "perturbation_mean_variance": "perturbation_difference",
    "restoration_mean_variance": "restoration_difference"}
COMPONENTS = (*EFFECTS, *VARIANCES)


def cells_schema():
    from .literature_perturbation_storage import perturbation_cells_schema
    from .literature_perturbation_summary_storage import perturbation_summary_cells_schema
    source = {**REF, "x-reference-namespace": "source"}
    return {"type": "array", "x-source": NAMESPACE, "items": obj({
        "row_version": {"const": VERSION}, "sheet_ref": source,
        "component": {"enum": list(COMPONENTS)},
        "quantity_kind": {"enum": ["native_endpoint", "endpoint_difference"]},
        "variance_for": {"type": ["string", "null"], "enum": [None, *EFFECTS]},
        "cell": operand_schema(),
        "source_cell": {"anyOf": [perturbation_cells_schema()["items"],
                                    perturbation_summary_cells_schema()["items"]]},
    })}


def _roles(component):
    effect = VARIANCES.get(component, component)
    if effect in ENDPOINTS:
        return (ENDPOINTS[effect],)
    return ("W", "K") if effect == "perturbation_difference" else ("R", "K")


def _operand(saved, source_cell):
    name = source_cell["component"]
    extraction = saved["extraction"]
    roles = _roles(name)
    keys, qualifications = [], list(source_cell["conditional_on"])
    for role in roles:
        observation = extraction["primitive_observations"].get(role)
        if observation is None or observation["measurement_key"] is None:
            qualifications.append("physical_measurement_identity_unknown")
            continue
        keys.append(observation["measurement_key"])
        # Original measurement keys include an acquisition Source ID. Also
        # retain a content-bound alias so reacquiring identical bytes cannot
        # turn a shared control into an independent observation.
        keys.append(identity("perturbation_physical_measurement", {
            "artifact_ref": observation["artifact_ref"],
            "measurement_id": observation["raw_entry"]["measurement_id"]}))
    if name in VARIANCES:
        qualifications.append(source_cell["variance_status"] + "_variance")
        qualifications.append("variance_scope:" + source_cell["variance_scope"])
    for basis in source_cell.get("statistical_interpretation_basis", {}).values():
        if "conditional_assumption" in basis.values():
            qualifications.append("conditional_sampling_assumption_unresolved")
        if "unresolved" in basis.values():
            qualifications.append("statistical_interpretation_unresolved")
    for covariance in source_cell.get("covariance_interpretations", []):
        if covariance["interpretation_basis"] in {"conditional_assumption", "unresolved"}:
            qualifications.append("conditional_covariance_assumption_unresolved")
    if source_cell.get("bound_kind", "none") != "none":
        qualifications.append("reported_bound_is_not_sampling_variance")
    origin = source_cell["origin"]
    if extraction["data_origin"] == "synthetic" or extraction["source_kind"] == "synthetic_fixture":
        origin = "synthetic"
    value = source_cell["value"]
    reason = source_cell["unavailable_reason"]
    # Match the common grader's canonical unit spellings without changing a
    # value or the original source cell. These pairs have multiplier one.
    unit = {"minutes": "min", "minutes_squared": "min_squared",
        "mg_per_mL": "mg/ml", "mg_per_mL_squared": "mg/ml_squared"}.get(
            source_cell["unit"], source_cell["unit"])
    return dict(value=value, unit=unit,
        status="point" if value is not None and reason is None else "unavailable", reason=reason,
        measurement_keys=list(dict.fromkeys(keys)),
        source_refs=list(dict.fromkeys(ref for ref in (source_cell["sheet_ref"],
            source_cell["evidence_source_ref"], source_cell["data_source_ref"]) if ref)),
        origin=origin, native_component=NAMESPACE + ":" + name,
        qualifications=list(dict.fromkeys(qualifications)))


class LiteraturePerturbationOperandProjection(LiteraturePerturbationSummaryProjection):
    """Independent typed custody over the same original point or summary sheet."""

    components = COMPONENTS
    received_table = "literature_perturbation_operand_received"

    def _original(self):
        # Reconstruct a reader without DDL; the native selected operation owns
        # creation of its store. This also permits cold read-only projection.
        reader = LiteraturePerturbationRepository.__new__(LiteraturePerturbationRepository)
        reader.store, reader.run_id = self.store, self.run_id
        return reader

    def read(self, sheet_ref):
        saved = self._original().read(sheet_ref)
        source = self.store.get(sheet_ref)
        if "artifact_" + hashlib.sha256(self.store.get_artifact(source["artifact_ref"])).hexdigest() != source["artifact_ref"]:
            raise ContractError("perturbation_operand_saved_hash_mismatch")
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self.components if components is None else components
        if (not isinstance(selected, (list, tuple)) or any(name not in COMPONENTS for name in selected)
                or len(set(selected)) != len(selected)):
            raise ContractError("perturbation_operand_component_selection_invalid")
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved = self.read(ref)
            reader = self._original()
            if saved["version"] == "literature_perturbation_record_v2":
                reader = reader.summary_projection()
            # Point-only sheets have no variance cells. Their absence does not
            # license a fabricated variance or conversion of a restoration index.
            available = [name for name in selected if name in reader.components]
            for source_cell in reader.project_cells([ref], permitted_record_refs=[ref], components=available):
                name = source_cell["component"]
                result.append(dict(row_version=VERSION, sheet_ref=ref, component=name,
                    quantity_kind=EFFECTS[VARIANCES.get(name, name)], variance_for=VARIANCES.get(name),
                    cell=_operand(saved, source_cell), source_cell=deepcopy(source_cell)))
        validate_schema(result, cells_schema())
        return result

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, cells_schema())
        seen = set()
        for row in cells:
            key = row["sheet_ref"], row["component"]
            if key in seen:
                raise ContractError("duplicate_literature_rate_return_cell")
            seen.add(key)
            expected = self.project_cells([row["sheet_ref"]],
                permitted_record_refs=permitted_record_refs, components=[row["component"]])
            if not expected or canonical(expected[0]) != canonical(row):
                raise ContractError("literature_rate_return_differs_from_saved_cells")

    @staticmethod
    def cell_record_refs(cells):
        result = []
        for row in cells:
            result.extend(row["cell"]["source_refs"])
            result.extend(row["source_cell"][name] for name in BINDINGS)
            for item in row["source_cell"].get("covariance_interpretations", []):
                result.extend(item.get("support_refs", []))
        return list(dict.fromkeys(ref for ref in result if ref))


def read_operand(selection, *, role, quantity_kind, read_cells):
    name = selection["component"]
    if (name not in COMPONENTS or role not in {"effect", "effect_variance", "assertion_prediction", "alternative_prediction"}
            or (role == "effect_variance") != (name in VARIANCES)
            or EFFECTS[VARIANCES.get(name, name)] != quantity_kind):
        raise ContractError("intervention_perturbation_quantity_role_mismatch")
    rows = read_cells(NAMESPACE, selection["sheet_ref"], [name])
    validate_schema(rows, cells_schema())
    if len(rows) != 1 or rows[0]["sheet_ref"] != selection["sheet_ref"] or rows[0]["component"] != name:
        raise ContractError("intervention_perturbation_component_not_received")
    operand = deepcopy(rows[0]["cell"])
    operand["qualifications"].append("perturbation_measurement_requires_intervention_design_assessment")
    return operand
