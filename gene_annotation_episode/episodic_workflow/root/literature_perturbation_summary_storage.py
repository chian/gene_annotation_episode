"""Closed v2 summary return view over the one A106 operation/sheet store."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from gene_annotation_episode.domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .library.literature_perturbation_inputs import ENDPOINT_UNITS, EXPOSURE_UNITS
from .literature_perturbation_storage import LiteraturePerturbationRepository, _metadata, perturbation_cells_schema
from .library.literature_perturbation_summary import (
    COMPONENTS, ROLES, SUMMARY_KINDS, SCALES, SPREAD_KINDS, UNIT_KINDS, VARIANCE_STATUSES, VARIANCE_SCOPES,
    INTERPRETATION_BASIS_FIELDS, INTERPRETATION_BASES, covariance_descriptors,
)

from .library.literature_perturbation_summary_return_contracts import (
    RECORD_VERSION, NAMESPACE, FORMULA_CODES, NEW_REASONS, METHODS, BOUND_KINDS, _PHYSICAL_UNITS, UNITS, _contributing_roles, _basis_map_schema, perturbation_summary_cells_schema, _COVARIANCE_USES, _covariance_pairs, _covariance_schema,
)

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
