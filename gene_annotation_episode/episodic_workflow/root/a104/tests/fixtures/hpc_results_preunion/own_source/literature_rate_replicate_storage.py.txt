"""Selected raw-table rate summaries and exact, source-bound saved returns.

The existing reader and calculator own measurement parsing and arithmetic.
This adapter owns selection, persistence and custody, and never reinterprets or
recalculates scientific inputs when reading a committed sheet.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_experimental_contracts import ORIGINS, RATE_UNITS, REPRESENTATIONS, SAMPLING_BASES
from .literature_rate_replicate_inputs import GROUP_FIELDS, read_rate_replicate_table
from .literature_rate_replicate_calculations import populate_rate_replicate_contrast
from .literature_rate_storage import LiteratureRateRepository


PROVIDER = "literature.a105.rate_replicate_population"
VERSION = "literature_rate_replicate_record_v1"
NAMESPACE = "literature_rate_replicate_cells"
REQUESTED = "requested_rate_replicate_components"
COMPONENTS = ("reference_rate", "test_rate", "rate_difference", "retained_fraction",
    "fractional_decrease", "paired_sample_sd", "difference_se", "reference_sample_sd",
    "test_sample_sd", "reference_mean_se", "test_mean_se")
CONTRAST_COMPONENTS = COMPONENTS[:7]
REASONS = ("numerical_model_range", "no_point_observations", "insufficient_measurement_count",
    "conflicting_observation_identity", "censored_measurement", "nondetection_without_point",
    "source_measurement_unavailable", "sampling_basis_mismatch", "incompatible_rate_dimensions",
    "incomplete_sampling_units", "unit_model_unspecified", "missing_reference_group",
    "missing_test_group", "endpoint_mismatch", "normalization_mismatch", "zero_reference_rate",
    "dependence_unknown", "paired_model_not_selected", "shared_sampling_units", "pairing_incomplete")
CONDITIONS = ("iid_units", "independent_groups", "iid_unit_pairs")
UNIT_CODES = (*RATE_UNITS, "fraction", None)
_TEXT = {"type": "string", "minLength": 1}
_NATURAL = {"type": "integer", "minimum": 0}
_NUMBER = {"type": ["number", "null"]}


def _array(schema, *, unique=False):
    return {"type": "array", "items": deepcopy(schema), **({"uniqueItems": True} if unique else {})}


def _nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def _selection_schema():
    return obj({name: deepcopy(_TEXT) for name in GROUP_FIELDS})


def rate_replicate_population_schema():
    """No measured scientific numbers are accepted as operation arguments."""
    return obj({"source_ref": {"type": "string", "format": "reference"},
        "source_representation": {"type": "string", "enum": ["original", "text"]},
        "table_kind": {"type": "string", "enum": list(REPRESENTATIONS)},
        "delimiter": {"type": "string", "enum": [",", "\t"]},
        "subject": deepcopy(_TEXT), "experiment": deepcopy(_TEXT),
        "reference": _selection_schema(), "test": _selection_schema(),
        "unit_model": {"type": "string", "enum": ["none", "iid_units"]},
        "dependence": {"type": "string", "enum": ["unknown", "independent", "paired_units"]}})


def _exact_schema():
    return _nullable(obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}}))


def _source_row_schema():
    return obj({"source_ref": deepcopy(_TEXT), "artifact_ref": deepcopy(_TEXT),
        "representation": {"enum": list(REPRESENTATIONS)}, "row_number": {"type": "integer", "minimum": 2},
        "header": deepcopy(_TEXT), "raw_row": {"type": "string"}})


def _cell_schema(*, exact=False):
    fields = {"value": deepcopy(_NUMBER), "unit": {"enum": list(UNIT_CODES)},
        "formula": deepcopy(_TEXT), "origin": {"const": "derived"},
        "status": {"enum": ["populated", "unavailable"]},
        "unavailable_reason": {"enum": [*REASONS, None]},
        "conditional_on": _array({"enum": list(CONDITIONS)}, unique=True),
        "approximate": {"type": "boolean"}, "input_rows": _array(_source_row_schema()),
        "input_origins": _array({"enum": list(ORIGINS)}, unique=True)}
    if exact:
        fields["source_exact_value"] = _exact_schema()
    return obj(fields)


def _unit_schema(*, numeric):
    fields = {"sampling_unit": deepcopy(_TEXT), "sampling_basis": {"enum": [*SAMPLING_BASES, None]},
        "observation_ids": _array(_TEXT, unique=True), "measurement_count": deepcopy(_NATURAL),
        "point_observation_ids": _array(_TEXT, unique=True), "point_count": deepcopy(_NATURAL),
        "representation_count": deepcopy(_NATURAL), "conflicting_identity": {"type": "boolean"},
        "complete": {"type": "boolean"}, "limitations": _array({"enum": list(REASONS)}, unique=True)}
    if numeric:
        fields["cells"] = obj({name: _cell_schema() for name in ("observed_point_mean", "observed_point_sd", "mean")})
    return obj(fields)


def _group_schema(*, numeric):
    fields = {**_selection_schema()["properties"], "sampling_basis": {"enum": [*SAMPLING_BASES, None]},
        **{name: deepcopy(_NATURAL) for name in ("measurement_count", "representation_count", "sampling_unit_count", "complete_unit_count")},
        "units": _array(_unit_schema(numeric=numeric))}
    if numeric:
        fields["cells"] = obj({name: _cell_schema() for name in ("mean", "sample_sd", "mean_se")})
    return obj(fields)


def _extraction_schema():
    table = obj({"source_ref": deepcopy(_TEXT), "artifact_ref": deepcopy(_TEXT), "text": deepcopy(_TEXT),
        "representation": {"enum": list(REPRESENTATIONS)}, "delimiter": {"enum": [",", "\t"]}})
    row = obj({**_selection_schema()["properties"], "sampling_unit": deepcopy(_TEXT),
        "sampling_basis": {"enum": list(SAMPLING_BASES)}, "observation_id": deepcopy(_TEXT),
        "value": deepcopy(_NUMBER), "raw_value": {"type": "string"}, "unit": {"enum": list(RATE_UNITS)},
        "status": {"enum": ["observed", "not_detected", "censored", "unavailable"]},
        "bound": {"enum": ["none", "lt", "le", "gt", "ge"]}, "approximate": {"type": "boolean"},
        "origin": {"enum": list(ORIGINS)}, "source": _source_row_schema()})
    return obj({"version": {"const": "a105_rate_replicates_v1"}, "subject": deepcopy(_TEXT),
        "experiment": deepcopy(_TEXT), "table": table, "rows": _array(row)})


def _sheet_schema():
    summary = obj({"version": {"const": "a105_rate_replicate_summary_v1"}, "axis": {"const": "A105"},
        "scope": {"const": "source_preparation_endpoint"}, "subject": deepcopy(_TEXT), "experiment": deepcopy(_TEXT),
        "model": obj({"unit_model": {"enum": ["none", "iid_units"]}, "sampling_basis_inferred": {"const": False}}),
        "extraction": _extraction_schema(), "groups": _array(_group_schema(numeric=True)),
        "annotation_credit": {"type": "null"}, "assay_error_rate": {"type": "null"}})
    return obj({"version": {"const": "a105_rate_replicate_contrast_v1"}, "axis": {"const": "A105"},
        "scope": {"const": "source_preparation_endpoint"}, "subject": deepcopy(_TEXT), "experiment": deepcopy(_TEXT),
        "reference": _selection_schema(), "test": _selection_schema(), "summary": summary,
        "dependence": {"enum": ["unknown", "independent", "paired_units"]},
        "pairing": obj({key: _array(_TEXT, unique=True) for key in ("shared_units", "reference_only", "test_only")}),
        "cells": obj({name: _cell_schema(exact=name in ("rate_difference", "retained_fraction", "fractional_decrease"))
                      for name in CONTRAST_COMPONENTS}),
        "annotation_credit": {"type": "null"}, "assay_error_rate": {"type": "null"}})


def _selected_group(sheet, role):
    return next((group for group in sheet["summary"]["groups"] if all(
        group[field] == sheet[role][field] for field in GROUP_FIELDS)), None)


def _project_saved(saved, reference, components):
    sheet = saved["sheet"]
    rows = sheet["summary"]["extraction"]["rows"]
    groups = {}
    for role in ("reference", "test"):
        group = _selected_group(sheet, role)
        observed = None if group is None else {field: deepcopy(value) for field, value in group.items() if field != "cells"}
        if observed is not None:
            observed["units"] = [{field: deepcopy(value) for field, value in unit.items() if field != "cells"} for unit in group["units"]]
        groups[role] = {"selection": deepcopy(sheet[role]), "status": "observed" if group is not None else "not_observed",
            "observed": observed}
    result = []
    for component in components:
        if component in CONTRAST_COMPONENTS:
            cell = sheet["cells"][component]
        else:
            role, statistic = component.split("_", 1)
            group = _selected_group(sheet, role)
            cell = group["cells"][statistic] if group is not None else {
                "value": None, "unit": None, "formula": statistic, "status": "unavailable", "origin": "derived",
                "unavailable_reason": "missing_" + role + "_group", "conditional_on": [], "approximate": False}
        result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
            "evaluation_scope": "source_raw_rate_replicates", "component": component,
            **{key: deepcopy(cell[key]) for key in ("value", "unit", "formula", "status", "origin", "unavailable_reason", "conditional_on", "approximate")},
            "source_exact_value": deepcopy(cell.get("source_exact_value")),
            "observed_subject": sheet["subject"] if rows else None,
            "observed_experiment": sheet["experiment"] if rows else None,
            "groups": deepcopy(groups), "unit_model": sheet["summary"]["model"]["unit_model"],
            "dependence": sheet["dependence"], "pairing": deepcopy(sheet["pairing"]),
            "input_origins": list(dict.fromkeys(row["origin"] for row in rows if any(
                all(row[field] == sheet[role][field] for field in GROUP_FIELDS) for role in ("reference", "test"))))})
    return result


def rate_replicate_cells_schema():
    """Complete registered fact view; source strings are never model-authored."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    group = obj({"selection": _selection_schema(), "status": {"enum": ["observed", "not_observed"]},
        "observed": _nullable(_group_schema(numeric=False))})
    fields = {"sheet_ref": deepcopy(reference), "evidence_source_ref": deepcopy(reference),
        "evaluation_scope": {"const": "source_raw_rate_replicates"}, "component": {"enum": list(COMPONENTS)},
        "value": deepcopy(_NUMBER), "unit": {"enum": list(UNIT_CODES)}, "formula": deepcopy(_TEXT),
        "status": {"enum": ["populated", "unavailable"]}, "origin": {"const": "derived"},
        "unavailable_reason": {"enum": [*REASONS, None]}, "conditional_on": _array({"enum": list(CONDITIONS)}, unique=True),
        "approximate": {"type": "boolean"}, "source_exact_value": _exact_schema(),
        "observed_subject": _nullable(_TEXT), "observed_experiment": _nullable(_TEXT),
        "groups": obj({role: deepcopy(group) for role in ("reference", "test")}),
        "unit_model": {"enum": ["none", "iid_units"]}, "dependence": {"enum": ["unknown", "independent", "paired_units"]},
        "pairing": obj({key: _array(_TEXT, unique=True) for key in ("shared_units", "reference_only", "test_only")}),
        "input_origins": _array({"enum": list(ORIGINS)}, unique=True)}
    return {"type": "array", "items": obj(fields), "x-source": NAMESPACE}


class LiteratureRateReplicateRepository(LiteratureRateRepository):
    provider, components, record_version = PROVIDER, COMPONENTS, VERSION
    operations_table = "literature_rate_replicate_operations"
    received_table = "literature_rate_replicate_received"
    binding_fields = ()

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    @staticmethod
    def _components(components):
        if (not isinstance(components, (tuple, list))
                or any(type(name) is not str or name not in COMPONENTS for name in components)
                or len(set(components)) != len(components)):
            raise ContractError("literature_rate_replicate_component_selection_invalid")
        return list(components)

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, rate_replicate_population_schema())
        source = self._native_source(context, args["source_ref"])
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {"run_id": self.run_id, "episode_id": context.episode_id, "operation_key": operation_key,
            "arguments": args, "scope": plain(context.scope), "components": requested}
        signature = canonical(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for reference in saved["input_source_refs"]:
                self._native_provenance(context.scope, reference)
            return outcome
        artifact = source["artifact_ref"] if args["source_representation"] == "original" else source.get("text_ref")
        if artifact is None:
            raise ContractError("literature_source_representation_unavailable")
        try:
            content = self.store.get_artifact(artifact).decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContractError("literature_utf8_table_required") from error
        extraction = read_rate_replicate_table({"source_ref": args["source_ref"], "artifact_ref": artifact,
            "text": content, "representation": args["table_kind"], "delimiter": args["delimiter"]},
            expected_subject=args["subject"], expected_experiment=args["experiment"])
        sheet = populate_rate_replicate_contrast(extraction, **{field: args[field] for field in
            ("reference", "test", "unit_model", "dependence")})
        validate_schema(sheet, _sheet_schema())
        ancestors = [args["source_ref"]]
        for reference in ancestors:
            for ancestor in self._native_provenance(context.scope, reference).get("parent_source_refs", ()):
                if ancestor not in ancestors:
                    ancestors.append(ancestor)
        payload = {"version": VERSION, "input_source_ref": args["source_ref"], "input_artifact_ref": artifact,
            "input_source_refs": ancestors, "selection": args, "sheet": sheet}
        with self.store.transaction():
            self._install()
            sheet_artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(canonical(request), "application/json")
            value = {"provider": PROVIDER, "accession": None, "uri": None, "artifact_ref": sheet_artifact,
                "text_ref": sheet_artifact, "request_ref": request_ref, "version": VERSION,
                "retrieved_at": None, "parent_source_refs": ancestors}
            reference = identity("source", {"origin": "tool", "record": value})
            existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (reference,)).fetchone()
            self.store.put("source", value, origin="tool", scope=plain(context.scope))
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": [reference], "changed_record_refs": [] if existed else [reference],
                "result": {"sheet_ref": reference, "view": "raw_rate_replicate_components",
                    "cells": _project_saved(payload, reference, requested)}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json_artifact(self, reference):
        content = self.store.get_artifact(reference)
        if "artifact_" + hashlib.sha256(content).hexdigest() != reference:
            raise ContractError("rate_replicate_saved_artifact_hash_mismatch")
        try:
            return json.loads(content)
        except (TypeError, ValueError) as error:
            raise ContractError("rate_replicate_saved_json_invalid") from error

    def read(self, sheet_ref):
        """Validate stored closed structures/identities, without scientific IO."""
        source = self.store.get(sheet_ref)
        value = {key: child for key, child in source.items() if key not in ("id", "record_type", "origin")}
        if (source.get("record_type") != "source" or source.get("origin") != "tool"
                or source.get("provider") != PROVIDER or source.get("version") != VERSION
                or identity("source", {"origin": "tool", "record": value}) != sheet_ref):
            raise ContractError("literature_rate_replicate_sheet_required")
        request = self._json_artifact(source["request_ref"])
        if (set(request) != {"run_id", "episode_id", "operation_key", "arguments", "scope", "components"}
                or request["run_id"] != self.run_id):
            raise ContractError("rate_replicate_saved_request_mismatch")
        validate_schema(request["arguments"], rate_replicate_population_schema())
        self._components(request["components"])
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation["signature"] != canonical(request):
            raise ContractError("literature_sheet_not_selected_output")
        saved = self._json_artifact(source["artifact_ref"])
        if (set(saved) != {"version", "input_source_ref", "input_artifact_ref", "input_source_refs", "selection", "sheet"}
                or saved["version"] != VERSION or saved["selection"] != request["arguments"]
                or saved["input_source_ref"] != request["arguments"]["source_ref"]
                or saved["input_source_refs"] != source["parent_source_refs"]):
            raise ContractError("rate_replicate_saved_selection_mismatch")
        validate_schema(saved["sheet"], _sheet_schema())
        self._validate_saved_bindings(saved, request)
        outcome = json.loads(operation["outcome"])
        expected = {"sheet_ref": sheet_ref, "view": "raw_rate_replicate_components",
            "cells": _project_saved(saved, sheet_ref, request["components"])}
        if (outcome.get("status") != "completed" or canonical(outcome.get("result")) != canonical(expected)
                or outcome.get("record_refs") != [sheet_ref] or outcome.get("feedback") is not None
                or outcome.get("operation_ref") != identity("operation", {"run_id": self.run_id,
                    "episode_id": request["episode_id"], "key": request["operation_key"]})):
            raise ContractError("rate_replicate_saved_outcome_mismatch")
        return saved

    def _validate_saved_bindings(self, saved, request):
        args, sheet = saved["selection"], saved["sheet"]
        summary = sheet["summary"]
        extraction = summary["extraction"]
        table = extraction["table"]
        original = self._native_provenance(request["scope"], saved["input_source_ref"])
        artifact = original["artifact_ref"] if args["source_representation"] == "original" else original.get("text_ref")
        ancestors = [saved["input_source_ref"]]
        for reference in ancestors:
            for ancestor in self._native_provenance(request["scope"], reference).get("parent_source_refs", ()):
                if ancestor not in ancestors:
                    ancestors.append(ancestor)
        # Hashing retained text authenticates its original bytes; no parsing,
        # token conversion, averaging or contrast calculation occurs here.
        if (artifact != saved["input_artifact_ref"] or ancestors != saved["input_source_refs"]
                or table["artifact_ref"] != artifact or table["source_ref"] != saved["input_source_ref"]
                or "artifact_" + hashlib.sha256(table["text"].encode("utf8")).hexdigest() != artifact
                or table["representation"] != args["table_kind"] or table["delimiter"] != args["delimiter"]
                or any(container[field] != args[field] for container in (sheet, summary, extraction) for field in ("subject", "experiment"))
                or sheet["reference"] != args["reference"] or sheet["test"] != args["test"]
                or sheet["dependence"] != args["dependence"] or summary["model"]["unit_model"] != args["unit_model"]):
            raise ContractError("rate_replicate_saved_source_binding_mismatch")
        row_sources = []
        for row in extraction["rows"]:
            provenance = row["source"]
            if any(provenance[field] != table[field] for field in ("source_ref", "artifact_ref", "representation")):
                raise ContractError("rate_replicate_saved_source_binding_mismatch")
            row_sources.append(provenance)
        if len({row["row_number"] for row in row_sources}) != len(row_sources):
            raise ContractError("rate_replicate_saved_row_identity_mismatch")
        keys = [tuple(group[field] for field in GROUP_FIELDS) for group in summary["groups"]]
        if len(set(keys)) != len(keys) or set(keys) != {tuple(row[field] for field in GROUP_FIELDS) for row in extraction["rows"]}:
            raise ContractError("rate_replicate_saved_group_binding_mismatch")
        for group in summary["groups"]:
            rows = [row for row in extraction["rows"] if all(row[field] == group[field] for field in GROUP_FIELDS)]
            units = group["units"]
            if (group["representation_count"] != len(rows)
                    or group["measurement_count"] != len({row["observation_id"] for row in rows})
                    or group["sampling_unit_count"] != len(units)
                    or group["complete_unit_count"] != sum(unit["complete"] for unit in units)
                    or len({unit["sampling_unit"] for unit in units}) != len(units)
                    or {unit["sampling_unit"] for unit in units} != {row["sampling_unit"] for row in rows}):
                raise ContractError("rate_replicate_saved_group_binding_mismatch")
            bases = {row["sampling_basis"] for row in rows}
            if group["sampling_basis"] != (next(iter(bases)) if len(bases) == 1 else None):
                raise ContractError("rate_replicate_saved_group_binding_mismatch")
            for unit in units:
                members = [row for row in rows if row["sampling_unit"] == unit["sampling_unit"]]
                ids = list(dict.fromkeys(row["observation_id"] for row in members))
                unit_bases = {row["sampling_basis"] for row in members}
                if (unit["observation_ids"] != ids or unit["measurement_count"] != len(ids)
                        or unit["representation_count"] != len(members)
                        or unit["point_count"] != len(unit["point_observation_ids"])
                        or not set(unit["point_observation_ids"]).issubset(ids)
                        or unit["sampling_basis"] != (next(iter(unit_bases)) if len(unit_bases) == 1 else None)):
                    raise ContractError("rate_replicate_saved_unit_binding_mismatch")
        reference_group, test_group = (_selected_group(sheet, role) for role in ("reference", "test"))
        reference_units = {unit["sampling_unit"] for unit in reference_group["units"]} if reference_group else set()
        test_units = {unit["sampling_unit"] for unit in test_group["units"]} if test_group else set()
        if sheet["pairing"] != {"shared_units": sorted(reference_units & test_units),
                "reference_only": sorted(reference_units - test_units), "test_only": sorted(test_units - reference_units)}:
            raise ContractError("rate_replicate_saved_pairing_binding_mismatch")
        allowed_sources = {canonical(row) for row in row_sources}
        def cells(value):
            if isinstance(value, dict):
                if "input_rows" in value:
                    yield value
                else:
                    for child in value.values():
                        yield from cells(child)
            elif isinstance(value, list):
                for child in value:
                    yield from cells(child)
        for cell in cells(sheet):
            if (any(canonical(row) not in allowed_sources for row in cell["input_rows"])
                    or (cell["value"] is None) != (cell["status"] == "unavailable")
                    or (cell["status"] == "populated" and cell["unavailable_reason"] is not None)):
                raise ContractError("rate_replicate_saved_cell_binding_mismatch")

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self._components(COMPONENTS if components is None else components)
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            result.extend(_project_saved(self.read(reference), reference, selected))
        return result

    def fact_cells(self, context, sheet_refs, *, components):
        sheet_refs = list(dict.fromkeys(sheet_refs))
        if self.store.reference_subset(sheet_refs, plain(context.scope)) != sheet_refs:
            raise ContractError("literature_source_outside_scope")
        return super().fact_cells(context, sheet_refs, components=components)

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self._install()
            return super().receive_cells(context, cells, operation_key)

    @staticmethod
    def cell_record_refs(cells):
        return list(dict.fromkeys(ref for row in cells for ref in (row["sheet_ref"], row["evidence_source_ref"])))
