"""Closed v2 summary return view over the one A106 operation/sheet store."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_perturbation_inputs import ENDPOINT_UNITS, EXPOSURE_UNITS
from .literature_perturbation_storage import LiteraturePerturbationRepository, _metadata, perturbation_cells_schema
from .literature_perturbation_summary import (
    COMPONENTS, ROLES, SUMMARY_KINDS, SCALES, SPREAD_KINDS, UNIT_KINDS, VARIANCE_STATUSES, VARIANCE_SCOPES,
    INTERPRETATION_BASIS_FIELDS, INTERPRETATION_BASES, covariance_descriptors,
)

RECORD_VERSION = "literature_perturbation_record_v2"
NAMESPACE = "literature_perturbation_summary_cells"
FORMULA_CODES = {name: "perturbation_summary_"+name+"_v2" for name in COMPONENTS}
NEW_REASONS = ("summary_value_unreported", "spread_value_unreported", "count_unreported",
    "raw_unit_variation_unavailable", "mean_variance_unavailable", "cross_arm_covariance_unknown",
    "shared_contrast_covariance_unavailable", "no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge",
    "pixel_tolerance_outside_image", "truncated_error_cap", "graph_spread_scale_unresolved",
    "asymmetric_graph_error_readings", "graph_spread_unavailable")
METHODS = ("none", "point_component", "equal_unit_descriptive_mean", "selected_reported_summary", "reported_count",
    "descriptive_sample_sd", "raw_independent_unit_mean", "reported_sem_squared", "sd_squared_over_independent_n",
    "mean_covariance_contrast", "conditional_marginal_covariance_enclosure", "shared_control_mean_covariance",
    *("reported_"+name for name in SPREAD_KINDS))
BOUND_KINDS = ("none", "conditional_digitization_not_confidence_interval", "reported_confidence_interval",
               "reported_detection_limit", "covariance_enclosure_not_confidence_interval")
_PHYSICAL_UNITS = tuple(dict.fromkeys((*ENDPOINT_UNITS, *EXPOSURE_UNITS, "unreported", "dimensionless")))
UNITS = (*_PHYSICAL_UNITS, "count", *(f"{scale}_{u}" for scale in ("log10", "ln") for u in _PHYSICAL_UNITS))
UNITS = (*UNITS, *(u+"_squared" for u in UNITS if u != "count"))


def _contributing_roles(component):
    """Statistical premise custody, including operands of derived components.

    Include roles used by validity prerequisites as well as the arithmetic.
    This mapping does not select work or assign scientific credit.
    """
    for role in ROLES:
        if component.startswith(role + "_"):
            return (role,)
    endpoints = {"reference_endpoint": "W", "perturbed_endpoint": "K", "restored_endpoint": "R"}
    if component in endpoints:
        return (endpoints[component],)
    if component in ("perturbation_difference", "symmetric_effect", "perturbation_mean_variance",
            "perturbation_variance_lower", "perturbation_variance_upper"):
        return ("W", "K")
    if component in ("restoration_difference", "restoration_mean_variance",
            "restoration_variance_lower", "restoration_variance_upper"):
        return ("K", "R")
    if component in ("restoration_fraction_raw", "restoration_agreement", "shared_contrast_covariance"):
        return ("W", "K", "R")
    if component == "amount_comparability":
        return ("A_reference", "A_restored")
    if component == "perturbation_isolation":
        return ("W", "K", "B_pert")
    if component == "restoration_isolation":
        return ("W", "K", "R", "B_rest")
    if component == "effect_isolation":
        return ("W", "K", "R", "B_pert", "B_rest")
    if component in ("reference_restoration_index", "reference_index_lower", "reference_index_upper"):
        return ROLES
    raise ContractError("literature_perturbation_summary_component_selection_invalid")


def _basis_map_schema(roles):
    basis = {"type": "object", "properties": {name: {"type": "string", "enum": list(INTERPRETATION_BASES)}
        for name in INTERPRETATION_BASIS_FIELDS}, "required": list(INTERPRETATION_BASIS_FIELDS),
        "additionalProperties": False}
    return {"type": "object", "properties": {role: deepcopy(basis) for role in roles},
        "required": [], "minProperties": 1, "additionalProperties": False}


def perturbation_summary_cells_schema(*, include_interpretation_basis=True, include_covariance_interpretations=True):
    """Original point meanings plus numerical summary and covariance cells."""
    schema = deepcopy(perturbation_cells_schema())
    properties = schema["items"]["properties"]
    properties["component"]["enum"] = list(COMPONENTS)
    properties["component"]["description"] = (
        "Source perturbation/restoration point components, retained reported summary/spread/count, descriptive raw-unit variation, "
        "conditional mean-variance estimates and shared-control covariance. Digitization constraints, covariance enclosures and "
        "reported confidence intervals have separate meanings; none is a probability of function or annotation credit.")
    properties["unit"]["enum"] = list(UNITS)
    properties["formula_code"]["enum"] = list(FORMULA_CODES.values())
    properties["unavailable_reason"]["enum"] += list(NEW_REASONS)
    properties["conditional_on"]["items"]["enum"] += ["selected_same_endpoint_mean_estimators", "retained_marginal_mean_variances", "shared_K_measurement"]
    properties["uncertainty_basis"]["enum"] = ["per_measurement"]
    properties.update({
        "statistic_method": {"type":"string", "enum":list(METHODS)},
        "variance_status": {"type":"string", "enum":list(VARIANCE_STATUSES)},
        "variance_scope": {"type":"string", "enum":list(VARIANCE_SCOPES)},
        "lower": {"type":["number","null"]}, "upper": {"type":["number","null"]},
        "bound_kind": {"type":"string", "enum":list(BOUND_KINDS)},
        "lower_error_cap":{"type":["number","null"]},"upper_error_cap":{"type":["number","null"]},
        "error_cap_scale":{"type":"string","enum":list(SCALES)},
        "spread_reading":{"type":"string","enum":["not_applicable","unresolved","symmetric_compatible","asymmetric_readings","reported_interval"]},
        "measurement_role": {"type":["string","null"], "enum":[None,*ROLES]},
        "summary_kind": {"type":"string", "enum":list(SUMMARY_KINDS)},
        "value_scale": {"type":"string", "enum":list(SCALES)},
        "summary_scale": {"type":"string", "enum":list(SCALES)},
        "spread_kind": {"type":"string", "enum":list(SPREAD_KINDS)},
        "spread_scale": {"type":"string", "enum":list(SCALES)},
        "count_unit": {"type":"string", "enum":list(UNIT_KINDS)},
        "independence": {"type":"string", "enum":["independent","not_independent","unknown"]},
        "n": {"type":["integer","null"], "minimum":1},
        "reported_coverage": {"type":["number","null"], "exclusiveMinimum":0,"exclusiveMaximum":1},
    })
    schema["items"]["required"] = list(properties)
    schema["x-source"] = NAMESPACE
    if not include_interpretation_basis:
        # Exact original55-field contract for actual historical v2 forms.
        return schema
    # Optional only for historical records that never supplied basis metadata.
    # Exact saved-value validation forbids dropping it from basis-bearing rows.
    properties["statistical_interpretation_basis"] = _basis_map_schema(ROLES)
    groups = {}
    for component in COMPONENTS:
        groups.setdefault(_contributing_roles(component), []).append(component)
    schema["items"]["allOf"] = [{"if": {"properties": {"component": {"enum": names}}},
        "then": {"properties": {"statistical_interpretation_basis": _basis_map_schema(roles)}}}
        for roles, names in groups.items()]
    if not include_covariance_interpretations:
        # Exact122 registered56-field contract, including its original allOf.
        return schema
    properties["covariance_interpretations"] = _covariance_schema()
    for pairs in ((), (("W", "K"),), (("K", "R"),), (("W", "K"), ("W", "R"), ("K", "R"))):
        names = [name for name in COMPONENTS if _covariance_pairs(name) == pairs]
        schema["items"]["allOf"].append({"if": {"properties": {"component": {"enum": names}}},
            "then": {"properties": {"covariance_interpretations": _covariance_schema(pairs) if pairs else False}}})
    return schema


_COVARIANCE_USES = ("used_selected_covariance", "unknown_covariance_enclosure", "component_unavailable")


def _covariance_pairs(component):
    if component in ("perturbation_mean_variance", "perturbation_variance_lower", "perturbation_variance_upper"):
        return (("W", "K"),)
    if component in ("restoration_mean_variance", "restoration_variance_lower", "restoration_variance_upper"):
        return (("K", "R"),)
    if component == "shared_contrast_covariance":
        return (("W", "K"), ("W", "R"), ("K", "R"))
    return ()


def _covariance_schema(pairs=None):
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "reference"}
    fields = {"first": {"type": "string", "enum": ["W", "K", "R"]},
        "second": {"type": "string", "enum": ["W", "K", "R"]},
        "selection": {"type": "string", "enum": ["selected", "unreported"]},
        "kind": {"type": "string", "enum": ["unknown", "mean_covariance", "uncorrelated", "paired_units"]},
        "interpretation_basis": {"type": ["string", "null"], "enum": [None, *INTERPRETATION_BASES]},
        "variance_status": {"type": "string", "enum": list(VARIANCE_STATUSES)},
        "use": {"type": "string", "enum": list(_COVARIANCE_USES)},
        "support_refs": {"type": "array", "uniqueItems": True, "items": reference}}
    result = {"type": "array", "minItems": 1, "maxItems": 3, "items": obj(fields)}
    if pairs is not None:
        result.update(minItems=len(pairs), maxItems=len(pairs), items=False,
            prefixItems=[obj({**deepcopy(fields), "first": {"type": "string", "const": first},
                "second": {"type": "string", "const": second}}) for first, second in pairs])
    return result


def _publish_covariance_support(descriptors, publish):
    result = {}
    for row in descriptors:
        references = []
        for witness in row["witnesses"]:
            anchor = {name: witness[name] for name in ("source_ref", "artifact_ref", "start", "end", "quote")}
            references.append(publish("reference", {"reference_type": "literature_result",
                "source_ref": witness["source_ref"], "accession": identity("perturbation_literal", {
                    "field": "covariance_support", "first": row["first"], "second": row["second"], **anchor}),
                "label": "Covariance interpretation support", "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": [], "anchor": anchor}))
        result[row["first"] + "_" + row["second"]] = list(dict.fromkeys(references))
    return result


def _qualified_covariance_cells(sheet, descriptors, bindings):
    selected = {(row["first"], row["second"]): row for row in descriptors}
    result = {}
    for name, cell in sheet["cells"].items():
        pairs = _covariance_pairs(name)
        if not pairs:
            continue
        qualifiers = []
        for pair in pairs:
            source = selected[pair]
            use = ("component_unavailable" if cell["value"] is None else
                "unknown_covariance_enclosure" if source["kind"] == "unknown" else "used_selected_covariance")
            qualifiers.append({**{key: deepcopy(value) for key, value in source.items() if key != "witnesses"},
                "use": use, "support_refs": deepcopy(bindings[pair[0] + "_" + pair[1]])})
        result[name] = qualifiers
    return result


def publish_covariance_meanings(extraction, sheet, publish):
    """Publish only deliberate new covariance metadata, with no arithmetic."""
    descriptors = sheet.get("covariance_descriptors")
    if descriptors is None:
        return None, []
    if descriptors != covariance_descriptors(extraction["summary_data"]):
        raise ContractError("literature_perturbation_covariance_saved_mismatch")
    bindings = _publish_covariance_support(descriptors, publish)
    for name, qualifiers in _qualified_covariance_cells(sheet, descriptors, bindings).items():
        sheet["cells"][name]["covariance_interpretations"] = qualifiers
    return bindings, list(dict.fromkeys(ref for rows in bindings.values() for ref in rows))


def validate_covariance_meanings(saved, store):
    """Validate original saved meanings/references without source I/O or fitting."""
    expected = covariance_descriptors(saved["extraction"]["summary_data"])
    sheet = saved["sheet"]
    if expected is None:
        if ("covariance_descriptors" in sheet or "covariance_support_bindings" in saved
                or any("covariance_interpretations" in cell for cell in sheet["cells"].values())):
            raise ContractError("literature_perturbation_covariance_saved_mismatch")
        return
    if expected != sheet.get("covariance_descriptors"):
        raise ContractError("literature_perturbation_covariance_saved_mismatch")
    def published(kind, record):
        reference = identity(kind, {"origin": "tool", "record": record})
        if store.get(reference) != {"id": reference, "record_type": kind, "origin": "tool", **record}:
            raise ContractError("literature_perturbation_covariance_support_mismatch")
        return reference
    bindings = _publish_covariance_support(expected, published)
    if bindings != saved.get("covariance_support_bindings"):
        raise ContractError("literature_perturbation_covariance_support_mismatch")
    qualifiers = _qualified_covariance_cells(sheet, expected, bindings)
    for name, cell in sheet["cells"].items():
        if ((name in qualifiers and cell.get("covariance_interpretations") != qualifiers[name])
                or (name not in qualifiers and "covariance_interpretations" in cell)):
            raise ContractError("literature_perturbation_covariance_saved_mismatch")


class LiteraturePerturbationSummaryProjection(LiteraturePerturbationRepository):
    """Independent possession of a versioned view, not a second numerical sheet."""

    record_version = RECORD_VERSION
    components = COMPONENTS
    received_table = "literature_perturbation_summary_received"

    def __init__(self, store, run_id):
        if not isinstance(run_id,str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        # No DDL during discovery/reconstruction on an old read-only database.
        self.store, self.run_id = store, run_id

    def _installed(self):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (self.received_table,)).fetchone() is not None

    def read(self, sheet_ref):
        saved = LiteratureRateRepository.read(self, sheet_ref)
        source = self.store.get(sheet_ref)
        payload = self.store.get_artifact(source["artifact_ref"])
        if "artifact_"+hashlib.sha256(payload).hexdigest() != source["artifact_ref"]:
            raise ContractError("literature_perturbation_summary_artifact_mismatch")
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        operation = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id,request["episode_id"],request["operation_key"])).fetchone()
        outcome = json.loads(operation["outcome"])
        if (saved.get("version") != RECORD_VERSION or source.get("version") != RECORD_VERSION
                or saved.get("data_source_ref") != request["arguments"].get("data_source_ref")
                or saved.get("extraction",{}).get("version") != "a106_perturbation_inputs_v2"
                or saved.get("sheet",{}).get("version") != "a106_source_summary_restoration_v2"
                or saved["sheet"]["cells"] != outcome.get("result",{}).get("cells")
                or self.store.get(saved["input_source_ref"])["artifact_ref"] != saved["input_artifact_ref"]):
            raise ContractError("literature_perturbation_summary_saved_mismatch")
        validate_covariance_meanings(saved, self.store)
        from .literature_perturbation_assessments import validate_saved_assessment
        validate_saved_assessment(self, saved, request)
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components,(list,tuple)) or any(not isinstance(c,str) or c not in COMPONENTS for c in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_perturbation_summary_component_selection_invalid")
        rows=[]
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            saved=self.read(reference)
            for name in components:
                cell={k:deepcopy(v) for k,v in saved["sheet"]["cells"][name].items() if k != "formula"}
                role=next((r for r in ROLES if name.startswith(r+"_")),None)
                if role is None:
                    role={"reference_endpoint":"W","perturbed_endpoint":"K","restored_endpoint":"R"}.get(name)
                descriptor=deepcopy(saved["sheet"]["summary_descriptors"][role]) if role else {
                    "summary_kind":"unknown","value_scale":"unknown","summary_scale":"unknown",
                    "spread_kind":"unreported","spread_scale":"unknown","count_unit":"unknown",
                    "independence":"unknown","n":None}
                descriptor.pop("interpretation_basis", None)
                coverage=(saved["extraction"]["summary_data"]["measurements"][role]["uncertainty"]["coverage"] if role else None)
                row = {"sheet_ref":reference,"evidence_source_ref":saved["input_source_ref"],
                    "data_source_ref":saved["data_source_ref"],**saved["experimental_bindings"],
                    "component":name,**cell,"formula_code":FORMULA_CODES[name],**_metadata(saved["extraction"]),
                    "measurement_role":role,**descriptor,"reported_coverage":coverage}
                bases = {operand: deepcopy(saved["sheet"]["summary_descriptors"][operand]["interpretation_basis"])
                    for operand in _contributing_roles(name)
                    if "interpretation_basis" in saved["sheet"]["summary_descriptors"][operand]}
                if bases:
                    row["statistical_interpretation_basis"] = bases
                rows.append(row)
        validate_schema(rows,perturbation_summary_cells_schema())
        return rows

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed() else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self.store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self.received_table}(
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                cells TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))""")
            super().receive_cells(context,cells,operation_key)


__all__=["RECORD_VERSION","NAMESPACE","COMPONENTS","LiteraturePerturbationSummaryProjection","perturbation_summary_cells_schema"]
