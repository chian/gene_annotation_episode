"""Deterministic database BLAST calculations and a separate bounded I/O entry.

The pure ports consume detached supplied sheets. PSI/DELTA use the iteration
calculator once; other modes use their own scientific population. Raw reported
HSP axes are calculated independently and never substituted for full axes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

from . import blast_iteration_calculators as _iteration
from . import blast_profile_calculators as _profile
from . import blast_pssm_calculators as _pssm
from . import blast_vdb_calculators as _vdb
from .blast_pairwise_grader import alignment_components
from .blast_program_context import resolve_blast_program_context
from .blast_report_collection import parse_blast_report_collection
from .domain import ContractError, canonical, identity, validate_schema
from . import native_blast_database_result_views as _views
from . import native_blast_database_contracts as _contracts


_SHEET_KEYS = {"schema", "collection", "prepared_inputs", "derived_search_bindings", "sequence", "profile", "vdb", "pssm", "msa", "iteration", "metadata_parse_results", "metadata_binding_results", "issues"}
_CALC_KEYS = {"schema", "sequence_model", "iteration", "profile", "vdb", "pssm", "search_facts", "native_hsp_components", "issues"}
_REASON_MAP = {None: "missing_input", "missing_input": "missing_input", "not_measured": "not_measured",
    "incompatible_input": "incompatible_input", "invalid_native_row": "invalid_native_row", "partial_output": "partial_output",
    "unsupported_schema": "unsupported_schema", "vdb_function_weight_model_not_defined": "not_measured",
    "model_training_membership_not_supplied": "not_measured"}


def _pointer(*parts):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _at(obj, pointer):
    for token in pointer.split("/")[1:] if pointer else ():
        token = token.replace("~1", "/").replace("~0", "~")
        if type(obj) is list:
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("native_blast_database_pointer_invalid")
            obj = obj[int(token)]
        else:
            obj = obj[token]
    return obj


def _number(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def _cell(name, value, unit, pointer, *, numerator=None, denominator=None, complete=None,
          status=None, reason=None, origin="derived"):
    if isinstance(value, dict) and "value" in value:
        original = value
        value = original["value"]
        numerator, denominator = original.get("numerator", numerator), original.get("denominator", denominator)
        complete = original.get("complete_for_reported_hsps", original.get("complete", complete))
        status = original.get("status", status)
        reason = original.get("unavailable_reason", original.get("reason", reason))
        origin = original.get("origin", origin)
    if value is not None and not _number(value):
        raise ValueError("native_blast_database_numeric_cell_invalid")
    if value is None:
        if reason not in _REASON_MAP:
            raise ValueError("native_blast_database_reason_mapping_required:" + str(reason))
        reason = _REASON_MAP[reason]
        status = "incompatible" if status == "incompatible" or reason == "incompatible_input" else "unavailable"
    else:
        status, reason = "available", None
    return dict(name=name, value=value, numerator=numerator, denominator=denominator, unit=unit,
        status=status, reason=reason, origin=origin, complete=complete, component_pointer=pointer)


def _boolean(name, value, pointer, *, status=None, reason=None, origin="derived"):
    if isinstance(value, dict):
        original = value; value = original["value"]
        status = original.get("status", status)
        reason = original.get("unavailable_reason", original.get("reason", reason))
        origin = original.get("origin", origin)
    if value is not None and type(value) is not bool:
        raise ValueError("native_blast_database_boolean_cell_invalid")
    if value is None:
        if reason not in _REASON_MAP:
            raise ValueError("native_blast_database_reason_mapping_required:" + str(reason))
        reason = _REASON_MAP[reason]
        status = "incompatible" if status == "incompatible" or reason == "incompatible_input" else "unavailable"
    else:
        status, reason = "available", None
    return dict(name=name, value=value, status=status, reason=reason, origin=origin, component_pointer=pointer)


def _model(model):
    try:
        model = _views._copy(model)
    except ValueError as error:
        raise ValueError("native_blast_database_sequence_model_invalid") from error
    if model is None:
        return None
    if type(model) is not dict or set(model) - {"temperature_bits", "function_priors"}:
        raise ValueError("native_blast_database_sequence_model_invalid")
    if "temperature_bits" in model and (not _number(model["temperature_bits"]) or model["temperature_bits"] <= 0):
        raise ValueError("native_blast_database_sequence_model_invalid")
    if "function_priors" in model:
        priors = model["function_priors"]
        if type(priors) is not dict or any(not isinstance(k, str) or not k or not _number(v) or v < 0 for k, v in priors.items()):
            raise ValueError("native_blast_database_sequence_model_invalid")
        for token in priors:
            try:
                validate_schema(token, _views._TOKEN)
            except ValueError as error:
                raise ValueError("native_blast_database_sequence_model_invalid") from error
    return model


def _hash(value):
    return hashlib.sha256(json.dumps(_views._copy(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _shape(value, schema):
    """Use the producer's strict JSON type semantics, including true integers."""
    _contracts._schema(value, schema)
    return value


def _absolute_path(value):
    if type(value) is not str or not value.startswith("/") or "\x00" in value or ".." in value.split("/"):
        raise ValueError("native_blast_database_absolute_path_required")
    return value


_MODEL = {"anyOf": [{"type": "null"}, {"type": "object", "properties": {
    "temperature_bits": {"type": "number", "exclusiveMinimum": 0},
    "function_priors": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}}}, "additionalProperties": False}]}
_ABS = {"type": "string", "minLength": 1}
_FILE_ID = dict(artifact_ref=_views._REF, sha256=_views._SHA, size_bytes=_views._I0)
_DESCRIPTOR = _views._object(dict(input_key=_views._TOKEN,
    consumer={"enum": ["query_identity", "sequence_database", "profile", "iteration", "vdb"]},
    schema_id=_views._TOKEN, **_FILE_ID, origin={"enum": ["original_job_input", "selected_results_input"]}))
_ATTEMPT = _views._object(dict(identity=_contracts.IDENTITY_SCHEMA, attempt_directory=_ABS, plan_sha256=_views._SHA))
_SNAPSHOT_ID = dict(subject_ref=_views._REF, record_type={"enum": ["input", "feature", "product", "read_subject"]},
    molecule={"enum": ["dna", "rna", "protein"]}, length={"type": "integer", "minimum": 1},
    sequence_sha256=_views._SHA, sequence_artifact_ref=_views._REF)


def native_blast_database_implementation_identity(files):
    """Identity of exact implementation bytes, independent of their paths."""
    files = _views._copy(files)
    if type(files) is not list or not files:
        raise ValueError("native_blast_database_implementation_files_required")
    projected = []
    for row in files:
        if type(row) is not dict or set(row) not in ({"module", "sha256"}, {"module", "path", "sha256"}):
            raise ValueError("native_blast_database_implementation_file_invalid")
        _shape({k: row[k] for k in ("module", "sha256")}, _views._object(dict(module=_views._TOKEN, sha256=_views._SHA)))
        if "path" in row:
            _absolute_path(row["path"])
        projected.append({k: row[k] for k in ("module", "sha256")})
    if len({r["module"] for r in projected}) != len(projected):
        raise ValueError("native_blast_database_implementation_module_duplicate")
    return _hash(dict(version="native_blast_database_implementation_identity_v1", files=sorted(projected, key=lambda r: r["module"])))


def native_blast_database_input_identity(request):
    """Identity of selected captured inputs; no path lookup or interpretation."""
    request = _views._copy(request)
    try:
        value = dict(version="native_blast_database_input_identity_v1",
            bundle=dict(artifact_ref=request["bundle_artifact_ref"], **{k: request["bundle_capture"][k] for k in ("sha256", "size_bytes")}),
            authenticated_attempt=request["authenticated_attempt"],
            artifacts=[{k: r[k] for k in ("artifact_key", "artifact_ref", "sha256", "size_bytes")} for r in request["artifacts"]],
            metadata_descriptors=request["metadata_descriptors"],
            retained_sources=[{k: r[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")} for r in request["retained_sources"]],
            subject_snapshots=[{k: r[k] for k in _SNAPSHOT_ID} for r in request["subject_snapshots"]])
        _shape(value, _views._object(dict(version={"const": "native_blast_database_input_identity_v1"}, bundle=_views._object(_FILE_ID),
            authenticated_attempt=_ATTEMPT, artifacts=_views._array(_views._object(dict(artifact_key=_views._TOKEN, **_FILE_ID))),
            metadata_descriptors=_views._array(_DESCRIPTOR), retained_sources=_views._array(_views._object(dict(source_ref=_views._REF, **_FILE_ID))),
            subject_snapshots=_views._array(_views._object(_SNAPSHOT_ID)))))
        _absolute_path(value["authenticated_attempt"]["attempt_directory"])
    except (KeyError, TypeError) as error:
        raise ValueError("native_blast_database_input_identity_invalid") from error
    return _hash(value)


def native_blast_database_calculation_identity(*, input_identity, input_implementation_sha256, sequence_model, implementation_manifest_sha256):
    """Separate input interpretation from the selected numerical generation."""
    for digest in (input_identity, input_implementation_sha256, implementation_manifest_sha256):
        _shape(digest, _views._SHA)
    model = _model(sequence_model)
    interpretation = _hash(dict(version="native_blast_database_interpretation_identity_v1",
        input_identity=input_identity, input_implementation_sha256=input_implementation_sha256))
    return dict(input_interpretation_id=interpretation, calculation_id=_hash(dict(version="native_blast_database_calculation_identity_v1",
        input_interpretation_id=interpretation, sequence_model=model, implementation_manifest_sha256=implementation_manifest_sha256)))


def _search_binding_rows(sheet_set):
    rows = []
    if sheet_set["iteration"] is not None:
        rows.extend(sheet_set["iteration"]["search_bindings"])
    else:
        for kind in ("sequence", "profile"):
            rows.extend(r["sheet"]["search_binding"] for r in sheet_set[kind])
        if not rows:
            for metadata in sheet_set["prepared_inputs"]["metadata"]:
                normalized = metadata.get("normalized")
                if metadata["status"] == "valid" and metadata["consumer"] == "query_identity" and normalized is not None:
                    rows.extend(normalized["search_bindings"])
    return deepcopy(rows)


def _source_statuses(collection):
    """Check the collector's saved source addresses, independently of scoring.

    The worker obtains these from the just-created collector or hash-verified
    immutable replay. No metadata caller supplies a source-qualified boolean.
    """
    statuses = []
    for search in collection["searches"]:
        key, norm, status = search["search_key"], search["normalized"], "available"
        artifacts = [a for a in collection["artifacts"] if a["artifact_key"] == key["artifact_key"]]
        if len(artifacts) != 1 or norm["native"].get("sha256") is None:
            status = "unavailable"
        elif artifacts[0].get("sha256") != norm["native"]["sha256"]:
            status = "incompatible"
        try:
            if norm["format"] == "json2":
                raw = _at(norm["native"]["document"], key["search_pointer"])
                if raw != search["native"]["search"] and isinstance(raw, dict):
                    status = "incompatible"
                if key["member_ordinal"] is not None:
                    member = norm["native"]["archive_member"]
                    matches = [m for m in artifacts[0].get("members", []) if m["member_ordinal"] == key["member_ordinal"]]
                    if len(matches) != 1 or matches[0].get("sha256") != member.get("sha256"):
                        status = "incompatible"
            elif norm["format"] == "tabular":
                layout = norm["native"].get("table_layout")
                if layout is None:
                    status = "unavailable"
                elif layout != {"format": artifacts[0]["format"], "declared_fields": artifacts[0]["fields"], "delimiter": artifacts[0]["delimiter"] or "\t"}:
                    status = "incompatible"
                if any(norm["native"].get(k) != v for k, v in search["native"]["search"].items()):
                    status = "incompatible"
            else:
                status = "unavailable"
        except (IndexError, KeyError, TypeError, ValueError):
            status = "incompatible"
        statuses.append(dict(search_key=deepcopy(key), status=status))
    return statuses


def populate_native_blast_database_search_facts(collection, *, source_statuses, search_bindings):
    """Count original native containers; no scoring, I/O or private 311 call."""
    collection, source_statuses, search_bindings = map(_views._copy, (collection, source_statuses, search_bindings))
    if collection.get("schema") != "blast_report_collection_v1":
        raise ValueError("native_blast_database_collection_required")
    keys = [canonical(s["search_key"]) for s in collection["searches"]]
    if (len(keys) != len(set(keys)) or type(source_statuses) is not list or len(source_statuses) != len(keys)
            or any(type(s) is not dict or set(s) != {"search_key", "status"} or s["status"] not in _views._STATUS for s in source_statuses)
            or sorted(canonical(s["search_key"]) for s in source_statuses) != sorted(keys)):
        raise ValueError("native_blast_database_source_statuses_invalid")
    statuses = {canonical(r["search_key"]): r["status"] for r in source_statuses}
    result = []
    names = tuple(_views._METRICS["search"])[:6]
    for i, search in enumerate(collection["searches"]):
        key, raw, norm = search["search_key"], search["native"]["search"], search["normalized"]
        state = statuses[canonical(key)]; base = f"/collection/searches/{i}"
        values = dict.fromkeys(names); reasons = dict.fromkeys(names, "missing_input")
        if norm["format"] == "json2":
            hits = raw.get("hits") if isinstance(raw, dict) else None
            if type(hits) is list:
                values["reported_hit_count"] = len(hits)
                arrays = [h["hsps"] for h in hits if type(h) is dict and type(h.get("hsps")) is list]
                if len(arrays) == len(hits):
                    values["reported_hsp_count"] = sum(len(a) for a in arrays)
                if arrays or not hits:
                    values["observed_hsp_count"] = sum(len(a) for a in arrays)
                if len(arrays) != len(hits) or any(type(h) is not dict for a in arrays for h in a):
                    reasons["reported_hsp_count"] = "invalid_native_row"
            reasons["declared_alignment_row_count"] = "not_measured"
        elif norm["format"] == "tabular":
            rows = raw.get("rows") if isinstance(raw, dict) else None
            declared = raw.get("declared_alignment_row_count") if isinstance(raw, dict) else None
            if type(declared) is int and declared >= 0:
                values["declared_alignment_row_count"] = declared
            else:
                reasons["declared_alignment_row_count"] = "not_measured" if declared is None else "invalid_native_row"
            if type(rows) is list and (rows or declared == 0):
                values["reported_hsp_count"] = values["observed_hsp_count"] = len(rows)
                if state == "available":
                    mapped = [j for m in search["row_map"] for j in m["hsp_ordinals"]]
                    if sorted(mapped) == list(range(len(rows))):
                        values["reported_hit_count"] = len(norm["hits"])
                    else:
                        reasons["reported_hit_count"] = "invalid_native_row"
        explicit = values["reported_hit_count"] is not None or values["observed_hsp_count"] is not None
        if state == "available" and explicit:
            values["parsed_hit_count"] = len(norm["hits"])
            values["parsed_hsp_count"] = sum(len(h["hsps"]) for h in norm["hits"])
        cells = {}
        for name in names:
            parsed = name.startswith("parsed_")
            pointer = base + ("/normalized/hits" if parsed else "/native/search")
            if not parsed:
                field = "declared_alignment_row_count" if name.startswith("declared_") else "rows" if norm["format"] == "tabular" else "hits"
                if isinstance(raw, dict) and field in raw:
                    pointer += "/" + field
            cells[name] = _cell(name, values[name], "hit" if "hit_count" in name else "hsp", pointer,
                reason="incompatible_input" if parsed and state == "incompatible" else reasons[name],
                status=state if parsed else None, origin="derived" if parsed else "native_report")
        matching = [r for r in search_bindings if r["search_key"] == key]
        binding_state, biological = state, None
        if len(matching) > 1:
            binding_state = "incompatible" if len({canonical(r) for r in matching}) > 1 else "unavailable"
        elif matching and matching[0]["provenance"] is not None and state == "available":
            biological = matching[0]["biological_round"]
        number = search["iteration"] if type(search["iteration"]) is int and search["iteration"] > 0 and state == "available" else None
        result.append(dict(search_key=deepcopy(key), status=state, native_iteration=_cell("native_iteration", number, "count", base + "/iteration",
            status=state, reason="incompatible_input" if state == "incompatible" else None, origin="native_report"),
            biological_round=_cell("biological_round", biological, "count", base, status=binding_state,
                reason="incompatible_input" if binding_state == "incompatible" else None, origin="supplied_source_record"), counts=cells))
    return result


def _native_slots(collection):
    """Yield every original HSP slot, including unassignable tabular rows."""
    for search in collection["searches"]:
        key, normalized, raw = search["search_key"], search["normalized"], search["native"]["search"]
        valid = {}
        for hit, mapping in zip(normalized["hits"], search["row_map"]):
            for native, ordinal in zip(hit["hsps"], mapping["hsp_ordinals"]):
                valid[(mapping["hit_index"], ordinal)] = (native, hit["length"])
        if normalized["format"] == "json2":
            hits = raw.get("hits") if isinstance(raw, dict) else None
            slots = []
            for hi, hit in enumerate(hits if isinstance(hits, list) else []):
                if isinstance(hit, dict) and isinstance(hit.get("hsps"), list):
                    slots.extend((hi, j) for j in range(len(hit["hsps"])))
        else:
            rows = raw.get("rows") if isinstance(raw, dict) else None
            hsp_to_hit = {j: h for h, j in valid}
            slots = [(hsp_to_hit.get(j), j) for j in range(len(rows if isinstance(rows, list) else []))]
        for hi, j in slots:
            native, length = valid.get((hi, j), (None, None))
            yield search, dict(search_key=deepcopy(key), hit_ordinal=hi, hsp_ordinal=j, description_ordinal=None), native, length


def _sheet_binding(sheet_set):
    """Validate the saved interpretation without parsing or populating it."""
    if type(sheet_set) is not dict:
        raise ValueError("native_blast_database_sheet_set_invalid")
    if sheet_set.get("schema") == "native_blast_database_sheet_set_v1" and set(sheet_set) == _SHEET_KEYS:
        return None
    if (sheet_set.get("schema") != "native_blast_database_sheet_set_v2"
            or set(sheet_set) != _SHEET_KEYS | {"native_convergence"}
            or sheet_set["collection"]["invocation"]["execution_program"] not in ("psiblast", "deltablast")):
        raise ValueError("native_blast_database_sheet_set_invalid")
    from .native_blast_database_convergence import validate_native_blast_database_convergence_binding
    binding = validate_native_blast_database_convergence_binding(sheet_set["native_convergence"], collection=sheet_set["collection"])
    native = binding["extraction"]["convergence_records"] if binding["extraction"] is not None else []
    records = sheet_set["iteration"]["convergence_records"]
    actual = [r for r in records if r["evidence"]["origin"] == "native_extractor_output"]
    # M appends the complete extraction after supplied (namespaced) records.
    # A native claim outside that exact extraction has no authority here.
    if (actual != native or native and records[-len(native):] != native
            or len({r["record_key"] for r in records}) != len(records)):
        raise ValueError("native_blast_database_convergence_record_mapping_invalid")
    return binding


def calculate_native_blast_database_sheets(sheet_set, *, sequence_model):
    """Calculate actual saved populations once, retaining all nested outputs."""
    sheet_set = _views._copy(sheet_set)
    _sheet_binding(sheet_set)
    model = _model(sequence_model)
    collection = sheet_set["collection"]; program = collection["invocation"]["execution_program"]
    if program not in _views._PROGRAMS:
        raise ValueError("native_blast_database_program_unsupported")
    out = dict(schema="native_blast_database_calculations_v1", sequence_model=model, iteration=None,
        profile=[], vdb=[], pssm=[], search_facts=[], native_hsp_components=[], issues=[])
    if program in ("psiblast", "deltablast"):
        if sheet_set["iteration"] is None:
            raise ValueError("native_blast_database_iteration_sheet_missing")
        out["iteration"] = _iteration.calculate_blast_iteration_components(sheet_set["iteration"], sequence_model=model)
        for i, row in enumerate(out["iteration"]["searches"]):
            base = f"/iteration/searches/{i}"
            cells = {n: _cell(n, c, "hit" if "hit_count" in n else "hsp", base + "/counts/" + n) for n, c in row["counts"].items()}
            out["search_facts"].append(dict(search_key=deepcopy(row["search_key"]), status=row["source_status"], counts=cells,
                native_iteration=_cell("native_iteration", row["native_iteration"], "count", base + "/native_iteration"),
                biological_round=_cell("biological_round", row["biological_round"], "count", base + "/biological_round")))
    else:
        family, calculator = ("profile", _profile.calculate_blast_profile_components) if program in ("rpsblast", "rpstblastn") else ("vdb", _vdb.calculate_blast_vdb_components)
        for row in sheet_set[family]:
            out[family].append(dict(search_key=deepcopy(row["search_key"]), components=calculator(row["sheet"])))
        seen = {}
        for sheet in sheet_set["pssm"]:
            key = sheet["artifact_key"]
            if key in seen:
                if seen[key] != sheet:
                    raise ValueError("native_blast_database_pssm_identity_conflict")
                continue
            seen[key] = sheet
            out["pssm"].append(dict(artifact_key=key, components=_pssm.calculate_blast_pssm_components(sheet)))
        out["search_facts"] = populate_native_blast_database_search_facts(collection,
            source_statuses=_source_statuses(collection), search_bindings=_search_binding_rows(sheet_set))
    for search, key, native, length in _native_slots(collection):
        context = search["program_context"]
        geometry = context["geometry_program"]
        try:
            expected = resolve_blast_program_context(**{k: v for k, v in context.items() if k != "geometry_program"})
            if expected != context:
                geometry = None
        except ValueError:
            geometry = None
        component = alignment_components(native, program=geometry,
            query_length=search["normalized"]["query"]["length"] if native is not None else None,
            reference_length=length, coordinate_convention="blast_json2" if search["normalized"]["format"] == "json2" else "directional")
        out["native_hsp_components"].append(dict(row_key=key, component=component,
            status="unavailable" if native is None else "available" if geometry is not None else "incompatible"))
    return out


class _Rows:
    def __init__(self, bundle_identity, calculation_id, sheets, calculations):
        self.attempt = bundle_identity; self.calculation_id = calculation_id
        self.sheets = sheets; self.calculations = calculations; self.rows = []
        self.collection = sheets["collection"]; self.program = self.collection["invocation"]["execution_program"]
        self.searches = {canonical(s["search_key"]): s for s in self.collection["searches"]}
        self.facts = {canonical(r["search_key"]): r for r in calculations["search_facts"]}
        self.iterations = {canonical(r["search_key"]): r for r in (calculations["iteration"] or {}).get("searches", [])}
        self.bindings = _search_binding_rows(sheets)

    def context(self, key=None):
        search = self.searches.get(canonical(key)) if key else None
        facts = self.facts.get(canonical(key)) if key else None
        bindings = [r for r in self.bindings if r["search_key"] == key]
        iteration = self.iterations.get(canonical(key)) if key else None
        stage = iteration["stage"] if iteration else bindings[0]["stage"] if len(bindings) == 1 and bindings[0]["provenance"] is not None else None
        axis = {"sequence": "sequence", "msa": "msa_master", "pssm": "pssm_master"}.get(search["program_context"]["query_kind"]) if search else None
        reference = ("vdb_member" if self.program.endswith("_vdb") else "profile_model" if self.program in ("rpsblast", "rpstblastn") or stage == "domain_database"
            else "sequence" if self.program == "psiblast" or stage == "sequence_database" else None) if search else None
        return dict(query_axis_kind=axis, reference_axis_kind=reference, stage=stage,
            native_iteration=facts["native_iteration"]["value"] if facts else None,
            biological_round=facts["biological_round"]["value"] if facts else None)

    def unit(self, family, name, context, population=None):
        unit = _views._METRICS[family][name]["units"]
        if unit == "query_unit":
            return "nt" if self.program in ("rpstblastn", "blastn_vdb") else "aa"
        if unit == "reference_unit":
            return {"profile_model": "model_position", "vdb_member": "nt", "sequence": "aa", None: "native_reference_position"}[context["reference_axis_kind"]]
        if unit == "population_unit":
            return {"reads": "member", "references": "member", "wgs_sequences": "member", "unique_sequences": "sequence_group", "features": "feature", "samples": "sample"}[population]
        return unit

    def add(self, family, row_identity, base, values, *, key=None, status="available", booleans=None, origins=None,
            details=None, refs=None, population=None, context=None):
        context = self.context(key) if context is None else context
        cells = []
        for name in _views._METRICS[family]:
            detail = dict((details or {}).get(name, {}))
            pointer = detail.pop("pointer", base + "/" + name)
            cells.append(_cell(name, values.get(name), self.unit(family, name, context, population), pointer,
                origin=(origins or {}).get(name, "derived"), **detail))
        boolean_cells = []
        for name in _views._BOOLEANS.get(family, ()):
            detail = dict((details or {}).get(name, {})); pointer = detail.pop("pointer", base + "/" + name)
            boolean_cells.append(_boolean(name, (booleans or {}).get(name), pointer,
                origin=(origins or {}).get(name, "derived"), **detail))
        component_refs = deepcopy(refs) if refs is not None else [dict(artifact_role="calculations", pointer=base)]
        documents = {"calculations": self.calculations, "sheets": self.sheets, "collection": self.collection}
        for cell in cells + boolean_cells:
            pointer = cell["component_pointer"]
            while True:
                available = []
                for role, document in documents.items():
                    try:
                        _at(document, pointer)
                    except (KeyError, IndexError, TypeError, ValueError):
                        continue
                    available.append(role)
                if available:
                    role = available[0]
                    break
                if cell["value"] is not None or not pointer:
                    raise ValueError("native_blast_database_component_pointer_unresolved")
                # A missing scalar is evidenced by the nearest real retained
                # container, never by a pointer pretending the scalar exists.
                pointer = pointer.rsplit("/", 1)[0]
            cell["component_pointer"] = pointer
            if not any(ref["artifact_role"] == role and (ref["pointer"] == pointer or pointer.startswith(ref["pointer"] + "/")) for ref in component_refs):
                component_refs.append(dict(artifact_role=role, pointer=pointer))
        row = dict(schema="native_blast_database_numeric_row_v1", family=family,
            record_key=identity("native_blast_database_row", dict(version="native_blast_database_row_identity_v1", attempt=self.attempt, family=family, identity=row_identity)),
            calculation_id=self.calculation_id, identity=deepcopy(row_identity), program=self.program, context=context,
            component_refs=component_refs,
            native_status=status, measurements=cells, booleans=boolean_cells)
        self.rows.append(row)
        return row


def _search_rows(builder):
    facts = builder.calculations["search_facts"]
    for i, f in enumerate(facts):
        key = f["search_key"]; search = builder.searches[canonical(key)]; iteration = builder.iterations.get(canonical(key))
        values = {**f["counts"], **{k: f[k] for k in ("native_iteration", "biological_round")}}
        base = f"/search_facts/{i}"; details = {}
        for name in values:
            details[name] = dict(pointer=base + ("/counts/" if name in f["counts"] else "/") + name)
        if iteration:
            j = builder.calculations["iteration"]["searches"].index(iteration); ibase = f"/iteration/searches/{j}"
            values.update(iteration["thresholds"])
            for name in iteration["thresholds"]:
                details[name] = dict(pointer=ibase + "/thresholds/" + name)
            native_converged = iteration["native_converged"]
            details["native_converged"] = dict(pointer=ibase + "/native_converged")
            status = iteration["status"]
        else:
            native_converged = None; status = f["status"]
            for name in ("reported_include", "native_inclusion_threshold", "domain_inclusion_threshold", "native_converged"):
                details[name] = dict(reason="not_measured", pointer=f"/collection/searches/{list(builder.searches).index(canonical(key))}/reporting")
        limit, count = search["reporting"]["requested_hit_limit"], f["counts"]["reported_hit_count"]["value"]
        reached = count >= limit if type(limit) is int and type(count) is int else None
        details["limit_reached"] = dict(pointer=f"/collection/searches/{list(builder.searches).index(canonical(key))}/reporting")
        builder.add("search", dict(search_key=key), base, values, key=key, status=status, details=details,
            booleans=dict(native_converged=native_converged, limit_reached=reached))


def _hsp_rows(builder):
    for i, entry in enumerate(builder.calculations["native_hsp_components"]):
        key, comp = entry["row_key"], entry["component"]; base = f"/native_hsp_components/{i}/component"
        counts, fractions, denominators = comp["counts"], comp["fractions"], comp["denominators"]
        values, details, origins = {}, {}, {}
        paths = {"native_score_bits": ("native_scores", "bit_score"), "native_raw_score": ("native_scores", "score"), "native_evalue": ("native_scores", "evalue"),
            **{n: ("counts", n) for n in ("alignment_columns", "paired_columns", "identical_pairs", "query_gap_columns", "reference_gap_columns")},
            "paired_query_units": ("counts", "paired_query_positions"), "paired_reference_units": ("counts", "paired_reference_positions"),
            "paired_identity": ("fractions", "paired_identity"), "alignment_identity": ("fractions", "alignment_identity"),
            "reported_query_coverage": ("fractions", "query_paired_coverage"), "reported_reference_coverage": ("fractions", "reference_paired_coverage"),
            "reported_query_length": ("denominators", "query_length"), "reported_reference_length": ("denominators", "reference_length")}
        invalid = any(v["code"] == "hsp_object_required" for v in comp["issues"])
        for name, (group, path) in paths.items():
            values[name] = comp[group].get(path)
            pointer = base + "/" + group + ("/" + path if path in comp[group] else "")
            reason = "invalid_native_row" if invalid else "incompatible_input" if entry["status"] == "incompatible" else "not_measured" if not comp["traceback_available"] and group in ("counts", "fractions") else "missing_input"
            if comp["traceback_available"] and not comp["geometry_available"] and (name.startswith("reported_") and name.endswith("coverage") or name.startswith("paired_") and name.endswith("units")):
                reason = "invalid_native_row"
            details[name] = dict(pointer=pointer, reason=reason)
            origins[name] = "native_traceback" if comp["traceback_available"] and group in ("counts", "fractions") else "native_report"
        for name, n, d in (("paired_identity", "identical_pairs", "paired_columns"), ("alignment_identity", "identical_pairs", "alignment_columns"),
            ("reported_query_coverage", "paired_query_positions", "query_length"), ("reported_reference_coverage", "paired_reference_positions", "reference_length")):
            details[name].update(numerator=counts.get(n), denominator=denominators.get(d), complete=comp["geometry_available"] if name.endswith("coverage") else None)
        builder.add("hsp", dict(row_key=key), base, values, key=key["search_key"],
            status="invalid" if invalid else "complete" if comp["geometry_available"] and not comp["issues"] else "partial" if entry["status"] == "available" else entry["status"], details=details, origins=origins)


def _sequence_rows(builder, result, base):
    key, status, c = result["search_key"], result["status"], result["components"]
    database, weights = c["database_sheet"], c["function_weights"]
    if database is None:
        return
    dbase = base + "/components/database_sheet"; wbase = base + "/components/function_weights"
    indices = {r["row_key"]["hit_ordinal"]: r for r in c["row_keys"]["hits"]}
    selected = {canonical(r["row_key"]): (i, r) for i, r in enumerate(c["selected_query_coverage"])}
    for i, hit in enumerate(database["hits"]):
        row = indices[hit["hit_index"]]; rkey = row["row_key"]
        b = dbase + f"/hits/{i}"; values = dict(hit["measurements"]); details = {}
        for name in _views._METRICS["sequence_hit"]:
            details[name] = dict(pointer=b + "/measurements/" + name)
        found = selected.get(canonical(rkey))
        if found:
            values["selected_query_coverage"] = found[1]
            details["selected_query_coverage"] = dict(pointer=base + f"/components/selected_query_coverage/{found[0]}")
        else:
            details["selected_query_coverage"] = dict(pointer=base + "/components/selected_query_coverage", reason="missing_input")
        query = c["coordinate_context"]["query"]
        references = [r for r in c["coordinate_context"]["references"] if r["row_key"] == rkey]
        for name, numerator, denominator in (("query_paired_coverage", values["observed_paired_query_positions"], query["full_length"]),
            ("reference_paired_coverage", values["observed_paired_reference_positions"], references[0]["full_length"] if len(references) == 1 else None)):
            details[name].update(numerator=numerator, denominator=denominator, complete=values["traceback_complete"],
                reason="partial_output" if not values["traceback_complete"] and numerator is not None else "missing_input")
        details["geometry_complete"] = dict(pointer=b + "/measurements/traceback_complete")
        builder.add("sequence_hit", dict(row_key=rkey), b, values, key=key, status=status, details=details,
            booleans={"geometry_complete": values["traceback_complete"]})
    for i, group in enumerate(database["sequence_groups"]):
        b = dbase + f"/sequence_groups/{i}"
        values = dict(maximum_bit_score=group["maximum_bit_score"], hit_representation_count=len(group["hit_indices"]), explicit_function_count=len(group["functions"]))
        builder.add("sequence_group", dict(search_key=key, hit_ordinals=sorted(group["hit_indices"])), b, values, key=key, status=status,
            details={"hit_representation_count": {"pointer": b + "/hit_indices"}, "explicit_function_count": {"pointer": b + "/functions"}})
    functions = {r["function"]: (i, r) for i, r in enumerate(database["functions"])}
    names = list(functions)
    names.extend(f for f in (weights or {}).get("function_masses", {}) if f not in functions)
    for function in names:
        fi, summary = functions.get(function, (None, {})); values = {}; details = {}
        b = dbase + f"/functions/{fi}" if fi is not None else wbase
        for name, field in (("sequence_group_count", "sequence_group_count"), ("native_hit_count", "native_hit_count"),
                ("maximum_bit_score", "maximum"), ("mean_bit_score", "mean"), ("scored_group_count", "count")):
            score = field in ("maximum", "mean", "count")
            values[name] = summary.get("bit_score", {}).get(field) if score else summary.get(field)
            details[name] = dict(pointer=b + ("/bit_score/" if score else "/") + field)
        for name, container in (("function_mass", "function_masses"), ("function_prior", "parameters/function_priors"),
            ("unadjusted_probability", "unadjusted_probabilities"), ("representation_adjusted_probability", "representation_adjusted_probabilities")):
            mapping = _at(weights, "/" + container) if weights is not None else None
            values[name] = mapping.get(function) if isinstance(mapping, dict) else None
            details[name] = dict(pointer=wbase + "/" + container + (_pointer(function) if isinstance(mapping, dict) and function in mapping else ""))
        if weights is not None:
            masses, priors = weights["function_masses"], weights["parameters"]["function_priors"]
            products = {f: priors[f] * m for f, m in masses.items() if f in priors}
            if function in products:
                details["unadjusted_probability"].update(numerator=products[function], denominator=math.fsum(products.values()))
            populations = {r["function"]: r["database_sequence_count"] for r in database["database_representation"]["function_representation"]}
            if values["representation_adjusted_probability"] is not None and all(populations.get(f) for f in products):
                corrected = {f: m / populations[f] for f, m in products.items()}
                details["representation_adjusted_probability"].update(numerator=corrected[function], denominator=math.fsum(corrected.values()))
        details["calibrated_annotation_probability"] = dict(pointer=wbase + "/calibrated_annotation_probability")
        builder.add("sequence_function", dict(search_key=key, function=function), b, values, key=key, status=status, details=details,
            booleans=dict(calibrated_annotation_probability=weights["calibrated_annotation_probability"] if weights else None),
            refs=[dict(artifact_role="calculations", pointer=b), dict(artifact_role="calculations", pointer=wbase)])
    for i, row in enumerate(database["database_representation"]["function_representation"]):
        b = dbase + f"/database_representation/function_representation/{i}"
        builder.add("sequence_population", dict(search_key=key, function=row["function"]), b, row, key=key, status=status,
            details={"database_fraction": dict(numerator=row["database_sequence_count"], denominator=row["database_total_sequence_count"])},
            origins={n: "supplied_source_record" for n in ("database_sequence_count", "database_total_sequence_count")})
    for function, owner, b in [(None, database, dbase)] + [(r["function"], r, dbase + f"/functions/{i}") for i, r in enumerate(database["functions"])]:
        _sequence_taxonomy_quality(builder, key, function, owner, b, database, dbase, status)


def _sequence_taxonomy_quality(builder, key, function, owner, base, database, dbase, status):
    taxonomy = owner["taxonomy"]
    for i, rank in enumerate(taxonomy["ranks"]):
        b = base + f"/taxonomy/ranks/{i}"; matching, conflicting = rank["target_matching_groups"], rank["target_conflicting_groups"]
        details = {"same_taxon_pair_fraction": dict(numerator=rank["same_taxon_pair_count"], denominator=rank["comparable_pair_count"]),
            "target_matching_fraction": dict(numerator=matching, denominator=matching + conflicting if matching is not None and conflicting is not None else None),
            "target_independent_of_search": dict(pointer=base + "/taxonomy/target_independent_of_search")}
        builder.add("sequence_taxonomy", dict(search_key=key, function=function, rank=rank["rank"]), b, rank, key=key, status=status, details=details,
            booleans=dict(target_independent_of_search=taxonomy["target_independent_of_search"]))
    for i, measurement in enumerate(owner["source_quality"]["assembly_measurements"]):
        b = base + f"/source_quality/assembly_measurements/{i}"; sources = {}
        for hi, hit in enumerate(database["hits"]):
            associations = hit["associations"]
            assigned = [a for a in associations if any(f["function"] == function for f in a["functions"])] if function is not None else associations
            for ai, a in enumerate(associations):
                assembly = a["assembly"]
                if not assembly or a["metadata_index"] is None:
                    continue
                if function is not None:
                    taxa = {v["taxid"] for v in associations if v["description_index"] == a["description_index"] and v["taxid"] is not None}
                    if not any(v["description_index"] == a["description_index"] and (v["taxid"] == a["taxid"] or
                        (v["taxid"] is None or a["taxid"] is None) and len(taxa) <= 1) for v in assigned):
                        continue
                expected = dict(assembly_accession=assembly.get("accession"), source=a["source"], quality_method=assembly.get("quality_method"),
                    measurement_methods=assembly.get("measurement_methods") or {}, accession=a["accession"] if not assembly.get("accession") else None,
                    measurements=a["quality_measurements"])
                if expected != measurement:
                    continue
                metadata = database["reference_metadata"][a["metadata_index"]]
                source = dict(source_ref=metadata["source"], pointer=metadata["native_pointer"])
                sources.setdefault(canonical(source), (source, []) )[1].append(dict(artifact_role="calculations", pointer=dbase + f"/hits/{hi}/associations/{ai}"))
        for source, refs in sources.values():
            builder.add("sequence_quality", dict(search_key=key, function=function, assembly_source=source), b, measurement["measurements"],
                key=key, status=status, details={n: dict(pointer=b + "/measurements/" + n) for n in _views._METRICS["sequence_quality"]},
                origins={n: "supplied_source_record" for n in _views._METRICS["sequence_quality"]},
                refs=[dict(artifact_role="calculations", pointer=b), *refs])


def _profile_rows(builder, component, base):
    key, status = component["search_key"], component["status"]
    models = {m["profile_key"]: m for m in component["models"]}
    for i, model in enumerate(component["models"]):
        record = model["profile_record"]; b = base + f"/models/{i}"
        details = {}
        for name in ("query_coverage", "selected_query_coverage", "model_coverage"):
            reason = "partial_output" if not model["geometry_complete"] and model[name]["numerator"] is not None else "missing_input"
            if name == "model_coverage" and any(p["code"] == "blast_profile_model_length_conflict" for p in model["issues"]):
                reason = "incompatible_input"
            details[name] = dict(complete=model["geometry_complete"], reason=reason)
        builder.add("profile_model", dict(search_key=key, profile_source=record["source"], model_identifier=record["model_identifier"]), b, model,
            key=key, status=model["binding_status"], details=details, booleans={"geometry_complete": model["geometry_complete"]})
    for hi, hsp in enumerate(component["hsps"]):
        for mi, match in enumerate(hsp["model_matches"]):
            model = models.get(match["profile_key"])
            if model is None:
                continue
            record = model["profile_record"]; b = base + f"/hsps/{hi}/model_matches/{mi}"
            builder.add("profile_hsp_model", dict(row_key=hsp["row_key"], profile_source=record["source"], model_identifier=record["model_identifier"]), b,
                match, key=key, status=match["binding_status"], origins={n: "supplied_source_record" for n in ("model_columns", "specific_bits_threshold", "reporting_bits_threshold")},
                details={n: dict(reason="incompatible_input" if match["binding_status"] in ("incompatible", "ambiguous") else "missing_input") for n in _views._METRICS["profile_hsp_model"]})
    for i, overlap in enumerate(component["dependence"]["query_overlaps"]):
        left, right = (models[overlap[k]]["profile_record"] for k in ("left_profile_key", "right_profile_key"))
        builder.add("profile_overlap", dict(search_key=key, left_profile_source=left["source"], right_profile_source=right["source"]),
            base + f"/dependence/query_overlaps/{i}", overlap, key=key, status=status)


def _pssm_rows(builder, artifact_key, component, base):
    for i, matrix in enumerate(component["matrices"]):
        b = base + f"/matrices/{i}"; ident = dict(artifact_key=artifact_key, record_ordinal=matrix["record_ordinal"])
        values = dict(matrix["dimensions"], **matrix["native_statistics"], master_reported_length=matrix["master"]["reported_length"], master_decoded_length=matrix["master"]["decoded_length"])
        details = {n: dict(pointer=b + "/native_statistics/" + n) for n in matrix["native_statistics"]}
        details.update({n: dict(pointer=b + "/dimensions/" + n) for n in matrix["dimensions"]})
        details.update({"master_" + n: dict(pointer=b + "/master/" + n) for n in ("reported_length", "decoded_length")})
        builder.add("pssm_matrix", ident, b, values, status=matrix["status"], details=details, origins={n: "native_report" for n in values})
        positions, residues = matrix["dimensions"]["positions"], matrix["dimensions"]["residue_rows"]
        for p in range(positions or 0):
            position_values, pd = {}, {}
            for name, array in matrix["position_diagnostics"].items():
                position_values[name] = array[p] if array is not None else None
                pd[name] = dict(pointer=b + "/position_diagnostics/" + name + (f"/{p}" if array is not None else ""),
                    status=matrix["array_status"]["pssm.intermediateData." + name],
                    reason="incompatible_input" if matrix["array_status"]["pssm.intermediateData." + name] == "incompatible" else "not_measured")
            builder.add("pssm_position", {**ident, "position": p}, b, position_values, status=matrix["status"], details=pd, origins={n: "native_report" for n in position_values})
            for r in range(residues or 0):
                values, details = {}, {}
                for name, array in matrix["matrix_values"].items():
                    values[name] = array[p][r] if array is not None else None
                    state = matrix["array_status"]["pssm." + ("finalData" if name == "scores" else "intermediateData") + "." + name]
                    details[name] = dict(pointer=b + "/matrix_values/" + name + (f"/{p}/{r}" if array is not None else ""), status=state,
                        reason="incompatible_input" if state == "incompatible" else "not_measured")
                builder.add("pssm_cell", {**ident, "position": p, "residue_row": r}, b, values, status=matrix["status"], details=details, origins={n: "native_report" for n in values})


def _iteration_rows(builder):
    component = builder.calculations["iteration"]
    if component is None:
        return
    sheet = builder.sheets["iteration"]
    binding = _sheet_binding(builder.sheets)
    native_sources = {}
    if binding is not None:
        extraction = binding["extraction"]
        records = extraction["convergence_records"] if extraction is not None else []
        for j, original in enumerate(records):
            key = original["record_key"]
            markers = [m for m, r in enumerate(extraction["markers"]) if r["record_key"] == key]
            saved = [(n, r) for n, r in enumerate(sheet["convergence_records"]) if r["record_key"] == key]
            observed = [(n, r) for n, r in enumerate(component["convergence_observations"]) if r["record_key"] == key]
            if len(markers) != 1 or len(saved) != 1 or len(observed) != 1 or saved[0][1] != original:
                raise ValueError("native_blast_database_convergence_record_mapping_invalid")
            n, row = observed[0]
            if (row["record_index"] != saved[0][0]
                    or any(row[k] != original[k] for k in ("record_key", "search_key", "query_operand", "evidence"))):
                raise ValueError("native_blast_database_convergence_record_mapping_invalid")
            native_sources[n] = (dict(source_ref=binding["extraction_artifact"]["artifact_ref"], pointer=f"/convergence_records/{j}"),
                [dict(artifact_role="calculations", pointer=f"/iteration/convergence_observations/{n}"),
                 dict(artifact_role="sheets", pointer=f"/native_convergence/extraction/convergence_records/{j}"),
                 dict(artifact_role="sheets", pointer=f"/native_convergence/extraction/markers/{markers[0]}")])
        if any(row["evidence"]["origin"] == "native_extractor_output" and i not in native_sources
                for i, row in enumerate(component["convergence_observations"])):
            raise ValueError("native_blast_database_convergence_record_mapping_invalid")
    for i, row in enumerate(component["inclusion_observations"]):
        builder.add("iteration_inclusion", dict(record_source=row["evidence"]["source"]), f"/iteration/inclusion_observations/{i}", row,
            key=row["search_key"], status=row["status"])
    for i, row in enumerate(component["convergence_observations"]):
        key, operand = row["search_key"], row["query_operand"]; query_identity = None
        scope = "search" if key is not None else "unbound"
        if key is None and operand is not None and operand["artifact_key"] is not None and operand["record_ordinal"] is not None:
            axis = {"sequence": "sequence", "msa": "msa_master", "pssm": "pssm_master"}[builder.collection["invocation"]["query_kind"]]
            query_identity = {k: deepcopy(operand[k]) for k in ("artifact_key", "record_ordinal", "selected_interval")}
            query_identity["axis_kind"] = axis; scope = "query"
        value = row["native_converged"]
        if scope == "unbound" and value["value"] is not None:
            value = {**value, "value": None, "status": "unavailable", "unavailable_reason": "missing_input"}
        context = builder.context(key)
        if query_identity:
            context["query_axis_kind"] = query_identity["axis_kind"]
        source, refs = native_sources.get(i, (row["evidence"]["source"], None))
        builder.add("iteration_convergence", dict(record_source=source, scope=scope, search_key=key, query_identity=query_identity),
            f"/iteration/convergence_observations/{i}", {}, key=key, status=row["status"], context=context,
            booleans=dict(native_converged=value), refs=refs)
    for i, row in enumerate(component["round_comparisons"]):
        pair = sheet["comparison_pairs"][row["pair_index"]]
        builder.add("iteration_comparison", {k: deepcopy(pair[k]) for k in ("earlier_search_key", "later_search_key", "relation_source", "identity_basis")},
            f"/iteration/round_comparisons/{i}", row, key=row["later_search_key"], status=row["status"])


def _unique_sources(rows):
    return [v for _, v in sorted({canonical(r): deepcopy(r) for r in rows if r is not None}.items())]


def _vdb_rows(builder, component, sheet, base, sheet_base):
    key, status = component["search_key"], component["status"]
    metadata = {m["metadata_key"]: m for m in sheet["reference_metadata"]}
    for i, subject in enumerate(component["subjects"]):
        builder.add("vdb_subject", dict(row_key=subject["row_key"]), base + f"/subjects/{i}", subject, key=key, status=status,
            booleans=dict(geometry_complete=subject["geometry_complete"]))
    membership = component["membership"]; values = dict(membership); details = {}
    for name in _views._METRICS["vdb_membership"]:
        details[name] = dict(pointer=base + "/membership/" + name)
    for i, row in enumerate(membership["counts_by_kind"]):
        for prefix in ("catalog", "origin"):
            name = prefix + "_" + row["kind"] + "_count"
            values[name] = row[prefix + "_member_count"]
            details[name] = dict(pointer=base + f"/membership/counts_by_kind/{i}/" + prefix + "_member_count")
    for field, names in (("sequence_groups", ("demonstrated_group_count", "grouped_subject_count", "ungrouped_subject_count", "duplicate_subject_representations")),
        ("sample_groups", ("observed_origin_sample_count", "catalog_sample_count", "unresolved_origin_member_count"))):
        for name in names:
            values[name] = component[field][name]; details[name] = dict(pointer=base + "/" + field + "/" + name)
    details["complete_for_origin_members"] = dict(pointer=base + "/sample_groups/complete_for_origin_members")
    builder.add("vdb_membership", dict(search_key=key), base + "/membership", values, key=key, status=status, details=details,
        booleans=dict(complete_for_reported_subjects=membership["complete_for_reported_subjects"], complete_for_origin_members=component["sample_groups"]["complete_for_origin_members"]))
    for i, row in enumerate(component["sequence_groups"]["groups"]):
        builder.add("vdb_sequence_group", dict(search_key=key, sequence_group_key=row["sequence_group_key"]), base + f"/sequence_groups/groups/{i}", row, key=key, status=status)
    for i, row in enumerate(component["sample_groups"]["groups"]):
        sources = _unique_sources([metadata[k]["source"] for k in row["metadata_keys"] if k in metadata] +
            [metadata[k]["linkage_source"] for k in row["metadata_keys"] if k in metadata] +
            [link["source"] for d in sheet["dataset_records"] if d["dataset_key"] in row["dataset_keys"]
             for link in d["sample_links"] if link["sample_key"] == row["sample_key"]] +
            [member["provenance"] for member in sheet["member_bindings"] if member["sample_key"] == row["sample_key"]
             and {k: member[k] for k in ("dataset_key", "member_kind", "member_identifier")} in row["catalog_member_keys"]])
        b = base + f"/sample_groups/groups/{i}"
        values, details = {}, {}
        for name, field in (("origin_member_count", "origin_member_keys"), ("catalog_member_count", "catalog_member_keys"), ("origin_subject_count", "origin_subject_row_keys")):
            values[name] = len({canonical(k) for k in row[field]}); details[name] = dict(pointer=b + "/" + field)
        builder.add("vdb_sample", dict(search_key=key, sample_key=row["sample_key"], sources=sources), b, values, key=key, status=status, details=details)
    for i, feature in enumerate(component["feature_components"]):
        bindings = [sheet["feature_bindings"][j] for j in feature["feature_binding_indices"]]
        sources = [binding["provenance"] for binding in bindings]
        sources.extend(sheet["member_bindings"][binding["member_binding_index"]]["provenance"] for binding in bindings)
        keys = {binding["translation_metadata_key"] for binding in bindings}
        if feature["translation_map"] is not None:
            keys.update(feature["translation_map"][name] for name in ("member_sequence_metadata_key", "translation_metadata_key"))
        for metadata_key in keys - {None}:
            if metadata_key in metadata:
                sources.extend(metadata[metadata_key][field] for field in ("source", "linkage_source"))
        sources = _unique_sources(sources)
        ident = dict(member_key=feature["member_key"], feature_identifier=feature["feature_identifier"], sources=sources)
        b = base + f"/feature_components/{i}"
        native_status = feature["relation_status"] if feature["relation_status"] in _views._NATIVE_STATUS else status
        builder.add("vdb_feature", dict(search_key=key, **ident), b, feature, key=key, status=native_status)
        for j, hsp in enumerate(feature["hsp_rows"]):
            builder.add("vdb_feature_hsp", dict(row_key=hsp["row_key"], **ident), b + f"/hsp_rows/{j}", hsp, key=key, status=native_status)
    for i, row in enumerate(component["taxonomy"]["sequence_group_ranks"]):
        builder.add("vdb_taxonomy", dict(search_key=key, rank=row["rank"]), base + f"/taxonomy/sequence_group_ranks/{i}", row, key=key, status=status,
            booleans=dict(target_independent_of_search=component["taxonomy"]["target_independent_of_search"]),
            details={"target_independent_of_search": dict(pointer=base + "/taxonomy/target_independent_of_search")})
    for i, row in enumerate(component["source_quality"]["records"]):
        m = metadata[row["metadata_key"]]
        builder.add("vdb_quality", dict(search_key=key, metadata_source=m["source"], assembly_identifier=row["assembly_identifier"]),
            base + f"/source_quality/records/{i}", row, key=key, status=status, origins={n: "supplied_source_record" for n in _views._METRICS["vdb_quality"]})
    for i, row in enumerate(component["population_components"]["records"]):
        source_rows = [(j, p) for j, p in enumerate(sheet["population_records"] or []) if p["population_key"] == row["population_key"]]
        if len(source_rows) != 1:
            raise ValueError("native_blast_database_population_identity_unresolved")
        j, source = source_rows[0]
        ident = dict(search_key=key, population_source=source["source"], population_key=row["population_key"])
        b = base + f"/population_components/records/{i}"
        builder.add("vdb_population", ident, b, row, key=key, status=row["status"], population=row["count_unit"],
            booleans=dict(population_complete=source["complete"]), details={"population_complete": dict(pointer=sheet_base + f"/population_records/{j}/complete")},
            refs=[dict(artifact_role="calculations", pointer=b), dict(artifact_role="sheets", pointer=sheet_base + f"/population_records/{j}")])
        for fi, function in enumerate(row["function_components"]):
            builder.add("vdb_population_function", dict(**ident, function=function["function"], assignment_scope=function["assignment_scope"]),
                b + f"/function_components/{fi}", function, key=key, status=row["status"], population=row["count_unit"])


def build_native_blast_database_rows(*, bundle_identity, calculation_id, sheet_set, calculations):
    """Build all families from retained components; no reparse or recalculation."""
    validate_schema(calculation_id, _views._SHA)
    sheet_set, calculations, bundle_identity = map(_views._copy, (sheet_set, calculations, bundle_identity))
    _shape(bundle_identity, _contracts.IDENTITY_SCHEMA)
    _sheet_binding(sheet_set)
    if set(calculations) != _CALC_KEYS or calculations["schema"] != "native_blast_database_calculations_v1":
        raise ValueError("native_blast_database_row_inputs_invalid")
    builder = _Rows(bundle_identity, calculation_id, sheet_set, calculations)
    _search_rows(builder); _hsp_rows(builder)
    nested = calculations["iteration"]
    if nested is not None:
        for i, search in enumerate(nested["searches"]):
            if search["sequence_components"] is not None:
                _sequence_rows(builder, search["sequence_components"], f"/iteration/searches/{i}/sequence_components")
            if search["profile_components"] is not None:
                _profile_rows(builder, search["profile_components"], f"/iteration/searches/{i}/profile_components")
        for i, pssm in enumerate(nested["pssms"]):
            _pssm_rows(builder, pssm["artifact_key"], pssm["components"], f"/iteration/pssms/{i}/components")
        _iteration_rows(builder)
    for i, row in enumerate(calculations["profile"]):
        _profile_rows(builder, row["components"], f"/profile/{i}/components")
    for i, row in enumerate(calculations["vdb"]):
        inputs = [(j, s["sheet"]) for j, s in enumerate(sheet_set["vdb"]) if s["search_key"] == row["search_key"]]
        if len(inputs) != 1:
            raise ValueError("native_blast_database_vdb_sheet_identity_unresolved")
        j, sheet = inputs[0]
        _vdb_rows(builder, row["components"], sheet, f"/vdb/{i}/components", f"/vdb/{j}/sheet")
    for i, row in enumerate(calculations["pssm"]):
        _pssm_rows(builder, row["artifact_key"], row["components"], f"/pssm/{i}/components")
    seen, rows = {}, []
    for row in builder.rows:
        _views._validate_row(row, calculation_id)
        if row["record_key"] in seen:
            previous = seen[row["record_key"]]
            if {k: v for k, v in row.items() if k != "component_refs"} != {k: v for k, v in previous.items() if k != "component_refs"}:
                raise ValueError("native_blast_database_row_identity_conflict")
            previous["component_refs"] = _unique_sources(previous["component_refs"] + row["component_refs"])
        else:
            seen[row["record_key"]] = row; rows.append(row)
    return rows


_ARTIFACT_ROLES = {"inputs": ("inputs.json", "native_blast_database_prepared_inputs_v1"),
    "collection": ("collection.json", "blast_report_collection_v1"), "sheets": ("sheets.json", "native_blast_database_sheet_set_v1"),
    "calculations": ("calculations.json", "native_blast_database_calculations_v1"),
    "rows": ("rows.ndjson", "native_blast_database_numeric_row_v1"), "row_index": ("row-index.json", "native_blast_database_row_index_v1"),
    "metric_definitions": ("metric-definitions.json", "native_blast_database_metric_definitions_v1"),
    "diagnostics": ("diagnostics.json", "native_blast_database_diagnostics_v1")}
_ARTIFACT_ROLES_V2 = {**_ARTIFACT_ROLES,
    "sheets": ("sheets.json", "native_blast_database_sheet_set_v2"),
    "native_convergence": ("native-convergence.json", "blast_native_convergence_extraction_v1")}


def _artifact_roles(version):
    if version == "native_blast_database_result_worker_manifest_v1":
        return _ARTIFACT_ROLES
    if version == "native_blast_database_result_worker_manifest_v2":
        return _ARTIFACT_ROLES_V2
    raise ValueError("native_blast_database_manifest_version_invalid")


def _request_schema():
    return _views._object(dict(version={"const": "native_blast_database_result_worker_request_v1"}, calculation_id=_views._SHA,
        bundle=_contracts.NATIVE_BLAST_DATABASE_BUNDLE_SCHEMA, bundle_artifact_ref=_views._REF,
        bundle_capture=_views._object(dict(path=_ABS, sha256=_views._SHA, size_bytes=_views._I0)),
        authenticated_attempt=_ATTEMPT, artifacts=_views._array(_views._object(dict(artifact_key=_views._TOKEN, path=_ABS, **_FILE_ID))),
        metadata_descriptors=_views._array(_DESCRIPTOR), retained_sources=_views._array(_views._object(dict(source_ref=_views._REF, path=_ABS, **_FILE_ID))),
        subject_snapshots=_views._array(_views._object(dict(**_SNAPSHOT_ID, sequence_path=_ABS))),
        implementation=_views._object(dict(manifest_sha256=_views._SHA, files=_views._array(_views._object(dict(module=_views._TOKEN, path=_ABS, sha256=_views._SHA)), minItems=1))),
        sequence_model=_MODEL, output_directory=_ABS, reuse=_views._nullable(_views._object(dict(
            manifest_path=_ABS, manifest_sha256=_views._SHA, manifest_size_bytes=_views._I0, collection_path=_ABS, sheets_path=_ABS)))))


def _manifest_schema(version="native_blast_database_result_worker_manifest_v1"):
    roles = _artifact_roles(version)
    return _views._object(dict(version={"const": version}, calculation_id=_views._SHA,
        request_sha256=_views._SHA, status={"enum": ["complete", "partial", "failed"]}, input_identity=_views._SHA,
        input_interpretation_id=_views._SHA, input_implementation_sha256=_views._SHA, implementation_manifest_sha256=_views._SHA,
        sequence_model=_MODEL, artifacts=_views._array(_views._object(dict(role={"enum": list(roles)},
            relative_path=_views._TOKEN, sha256=_views._SHA, size_bytes=_views._I0, schema=_views._TOKEN))),
        counts=_views._object(dict(searches=_views._I0, native_hsp_slots=_views._I0, numerical_rows=_views._I0)),
        failures=_views._array(_views._failure_schema())))


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("native_blast_database_duplicate_json_key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("native_blast_database_finite_json_required")
    return _views._copy(json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite))


class _WorkerFailure(Exception):
    def __init__(self, stage, code, detail, *, pointer="", artifact_key=None, input_key=None, search_key=None):
        self.failure = dict(stage=stage, code=code, detail_code=detail, pointer=pointer, artifact_key=artifact_key,
            input_key=input_key, search_key=search_key, record_key=None)
        super().__init__(code)


def _verified_bytes(path, sha256, size_bytes, *, frozen=False, pointer="", artifact_key=None):
    _absolute_path(path)
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        raise _WorkerFailure("capture", "native_blast_database_artifact_missing", "artifact_bytes_unavailable",
            pointer=pointer, artifact_key=artifact_key) from error
    if len(data) != size_bytes or hashlib.sha256(data).hexdigest() != sha256:
        raise _WorkerFailure("capture", "native_blast_database_frozen_artifact_changed" if frozen else "native_blast_database_artifact_identity_mismatch",
            "frozen_value_changed" if frozen else "artifact_digest_conflict", pointer=pointer, artifact_key=artifact_key)
    return data


_DEPENDENCY_ROOTS = {"Bio", "numpy", "jsonschema", "jsonschema_specifications", "referencing", "rpds", "attr", "attrs"}


def _implementation_modules(*, execution_program=None):
    """Actual loaded scientific dependency closure, excluding unrelated callers."""
    names = ["gene_annotation_episode." + name for name in (
        "native_blast_database_result_worker", "native_blast_database_result_views", "native_blast_database_metadata",
        "native_blast_database_contracts", "blast_report_collection", "blast_grading_inputs", "blast_program_context",
        "blast_sequence_database", "blast_database_grader", "blast_pairwise_grader", "blast_profile_inputs", "blast_profile_calculators",
        "blast_pssm_inputs", "blast_pssm_calculators", "blast_pssm_master_inputs", "blast_iteration_inputs", "blast_iteration_calculators",
        "blast_vdb_inputs", "blast_vdb_calculators", "blast_search", "domain")]
    if execution_program in ("psiblast", "deltablast"):
        names.extend("gene_annotation_episode." + name for name in
            ("native_blast_database_convergence", "blast_native_iteration_records"))
    for name in names:
        importlib.import_module(name)
    names.extend(name for name, module in tuple(sys.modules.items()) if name.split(".")[0] in _DEPENDENCY_ROOTS and getattr(module, "__file__", None))
    names.append("gene_annotation_episode")
    return {name: sys.modules[name] for name in sorted(set(names))}


def _verify_implementation(implementation, *, execution_program=None):
    expected = native_blast_database_implementation_identity(implementation["files"])
    if implementation["manifest_sha256"] != expected:
        raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/manifest_sha256")
    files = {r["module"]: r for r in implementation["files"]}
    # The parent may previously have used another mode and retained more of the
    # same allowed dependency packages. Load exactly its declared dependencies
    # in this fresh process before verifying their actual files. This does not
    # import unrelated project operations or invoke their scientific functions.
    for name in files:
        if name not in sys.modules and name.split(".")[0] in _DEPENDENCY_ROOTS:
            importlib.import_module(name)
    modules = _implementation_modules(execution_program=execution_program)
    if not set(modules) <= set(files):
        raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
    if Path(__file__).resolve() != Path(files["gene_annotation_episode.native_blast_database_result_worker"]["path"]).resolve():
        raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
    for name, row in files.items():
        module = sys.modules.get(name)
        path = getattr(module, "__file__", None)
        if path is None or Path(path).resolve() != Path(row["path"]).resolve():
            raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
        raw = Path(row["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")


def _atomic_bytes(directory, filename, raw):
    path = directory / filename
    if path.exists():
        raise FileExistsError("native_blast_database_generation_immutable")
    descriptor, temporary = tempfile.mkstemp(prefix="." + filename + ".", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        # Linking is atomic and fails rather than replacing a prior artifact.
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _json_bytes(value):
    return (json.dumps(_views._copy(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _catalog(request, failures):
    originals = {r["artifact_key"]: r for r in request["bundle"]["artifacts"]}
    entries, contents = [], {}
    if len({r["artifact_key"] for r in request["artifacts"]}) != len(request["artifacts"]):
        raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/artifacts")
    for i, row in enumerate(request["artifacts"]):
        original = originals.get(row["artifact_key"])
        if original is None or any(row[k] != original[k] for k in ("sha256", "size_bytes")):
            raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer=f"/artifacts/{i}", artifact_key=row["artifact_key"])
        entry = {k: v for k, v in original.items() if k != "content_assessment"}
        entry.update(row, source_ref=row["artifact_ref"])
        entries.append(entry)
        try:
            contents[row["artifact_key"]] = _verified_bytes(row["path"], row["sha256"], row["size_bytes"], pointer=f"/artifacts/{i}", artifact_key=row["artifact_key"])
        except _WorkerFailure as error:
            failures.append(error.failure)
    captured_keys = {r["artifact_key"] for r in entries}
    for key in originals:
        if key not in captured_keys:
            failures.append(_WorkerFailure("capture", "native_blast_database_artifact_missing", "artifact_bytes_unavailable", artifact_key=key, pointer="/artifacts").failure)
    if len({r["source_ref"] for r in request["retained_sources"]}) != len(request["retained_sources"]):
        raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/retained_sources")
    for i, row in enumerate(request["retained_sources"]):
        try:
            _verified_bytes(row["path"], row["sha256"], row["size_bytes"], pointer=f"/retained_sources/{i}")
        except _WorkerFailure as error:
            failures.append(error.failure)
    return dict(bundle_source_ref=request["bundle_artifact_ref"], bundle_artifact_ref=request["bundle_artifact_ref"],
        bundle_sha256=request["bundle_capture"]["sha256"], entries=entries, retained_sources=deepcopy(request["retained_sources"])), contents


def _metadata_payloads(request, catalog, failures):
    job = request["bundle"]["requested_job"]["native_blast_database"]
    descriptors = request["metadata_descriptors"]
    if len({(r["input_key"], r["consumer"], r["schema_id"]) for r in descriptors}) != len(descriptors):
        raise _WorkerFailure("metadata", "native_blast_metadata_payload_invalid", "metadata_shape_invalid", pointer="/metadata_descriptors")
    identities = {}
    for descriptor in descriptors:
        value = tuple(descriptor[k] for k in ("artifact_ref", "sha256", "size_bytes"))
        if descriptor["input_key"] in identities and identities[descriptor["input_key"]] != value:
            raise _WorkerFailure("metadata", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", input_key=descriptor["input_key"], pointer="/metadata_descriptors")
        identities[descriptor["input_key"]] = value
    original = [r for r in descriptors if r["origin"] == "original_job_input"]
    if [{k: r[k] for k in ("input_key", "consumer", "schema_id")} for r in original] != job["metadata_inputs"] or descriptors[:len(original)] != original:
        raise _WorkerFailure("metadata", "native_blast_metadata_payload_invalid", "metadata_shape_invalid", pointer="/metadata_descriptors")
    payloads = []
    selected_inputs = {r["input_key"]: r for r in job["inputs"]}
    for i, descriptor in enumerate(descriptors):
        original_input = selected_inputs.get(descriptor["input_key"])
        if original_input is not None and original_input["role"] != "metadata":
            raise _WorkerFailure("metadata", "native_blast_metadata_payload_invalid", "metadata_shape_invalid", input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}")
        candidates = [r for r in catalog["entries"] + catalog["retained_sources"] if r["artifact_ref"] == descriptor["artifact_ref"]]
        # Exact artifact identity is required, even when its JSON is malformed.
        unique = {canonical({k: r[k] for k in ("artifact_ref", "path", "sha256", "size_bytes")}): r for r in candidates}
        if not unique:
            failures.append(_WorkerFailure("metadata", "native_blast_metadata_source_unavailable", "metadata_address_unresolved",
                input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}").failure)
            payloads.append(dict(descriptor=deepcopy(descriptor), payload=None))
            continue
        if len(unique) != 1:
            raise _WorkerFailure("metadata", "native_blast_metadata_source_unavailable", "metadata_address_unresolved", input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}")
        row = next(iter(unique.values()))
        if any(row[k] != descriptor[k] for k in ("sha256", "size_bytes")) or original_input is not None and row.get("input_key") != descriptor["input_key"]:
            raise _WorkerFailure("metadata", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}")
        try:
            raw = _verified_bytes(row["path"], row["sha256"], row["size_bytes"], pointer=f"/metadata_descriptors/{i}")
            payload = _decode(raw)
        except _WorkerFailure as error:
            failures.append(error.failure); payload = None
        except (ValueError, UnicodeError):
            payload = None
        payloads.append(dict(descriptor=deepcopy(descriptor), payload=payload))
    return payloads


def _reuse(request, input_identity):
    reused = request["reuse"]
    raw = _verified_bytes(reused["manifest_path"], reused["manifest_sha256"], reused["manifest_size_bytes"], frozen=True, pointer="/reuse/manifest_path")
    manifest = _decode(raw); _shape(manifest, _manifest_schema(manifest.get("version")))
    roles = _artifact_roles(manifest["version"])
    identities = native_blast_database_calculation_identity(input_identity=manifest["input_identity"],
        input_implementation_sha256=manifest["input_implementation_sha256"], sequence_model=manifest["sequence_model"],
        implementation_manifest_sha256=manifest["implementation_manifest_sha256"])
    if (manifest["status"] == "failed" or manifest["input_identity"] != input_identity
            or any(manifest[k] != value for k, value in identities.items())):
        raise _WorkerFailure("inputs", "native_blast_database_frozen_artifact_changed", "frozen_value_changed", pointer="/reuse")
    artifacts = {r["role"]: r for r in manifest["artifacts"]}
    if len(artifacts) != len(manifest["artifacts"]) or not {"collection", "sheets"} <= artifacts.keys():
        raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
    for role, artifact in artifacts.items():
        if (artifact["relative_path"], artifact["schema"]) != roles[role]:
            raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
    values = {}
    for role in ("collection", "sheets"):
        artifact = artifacts[role]
        data = _verified_bytes(reused[role + "_path"], artifact["sha256"], artifact["size_bytes"], frozen=True, pointer="/reuse/" + role + "_path")
        values[role] = _decode(data)
        if values[role].get("schema") != artifact["schema"]:
            raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse/" + role + "_path")
    binding = _sheet_binding(values["sheets"])
    if (values["sheets"]["collection"] != values["collection"]
            or values["sheets"]["prepared_inputs"].get("schema") != "native_blast_database_prepared_inputs_v1"):
        raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
    if binding is not None:
        expected_context = dict(original_job=request["bundle"]["requested_job"]["native_blast_database"],
            bundle=request["bundle"], attempt_identity=request["authenticated_attempt"])
        if binding["source_context"] != expected_context:
            raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
        extraction = binding["extraction"]
        if (extraction is not None) != ("native_convergence" in artifacts):
            raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
        if extraction is not None:
            artifact = artifacts["native_convergence"]
            path = str(Path(reused["manifest_path"]).parent / artifact["relative_path"])
            data = _verified_bytes(path, artifact["sha256"], artifact["size_bytes"], frozen=True, pointer="/reuse/native_convergence")
            expected = binding["extraction_artifact"]
            if (data != _json_bytes(extraction)
                    or any(artifact[k] != expected[k] for k in ("sha256", "size_bytes"))):
                raise _WorkerFailure("inputs", "native_blast_database_frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/native_convergence")
    return values["collection"], values["sheets"], manifest["input_implementation_sha256"], manifest["version"]


def _metadata_failures(issues):
    details = {"schema_unsupported": "metadata_tuple_unregistered", "payload_invalid": "metadata_shape_invalid",
        "source_unavailable": "metadata_address_unresolved", "relation_unresolved": "metadata_address_unresolved",
        "relation_conflict": "metadata_relation_conflict", "extractor_unbound": "extractor_not_registered"}
    output = []
    for issue in issues:
        code = issue["code"]
        detail = details.get(code.removeprefix("native_blast_metadata_"))
        if detail is None:
            raise ValueError("native_blast_database_metadata_failure_mapping_required")
        output.append(_WorkerFailure("metadata", code, detail, pointer=issue["pointer"],
            input_key=issue.get("input_key"), search_key=issue.get("search_key")).failure)
    return output


def run_native_blast_database_result_worker(request_path):
    """I/O entry invoked within E's caller-owned local_jobs resource boundary."""
    request_bytes = Path(_absolute_path(str(request_path))).read_bytes()
    request = _decode(request_bytes)
    if type(request) is dict and "sequence_model" in request:
        _model(request["sequence_model"])
    _shape(request, _request_schema())
    directory = Path(_absolute_path(request["output_directory"]))
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise FileExistsError("native_blast_database_generation_directory_not_empty")
    input_identity = native_blast_database_input_identity(request)
    input_implementation = request["implementation"]["manifest_sha256"]
    initial = native_blast_database_calculation_identity(input_identity=input_identity,
        input_implementation_sha256=input_implementation, sequence_model=request["sequence_model"],
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"])
    program = request["bundle"]["requested_job"]["native_blast_database"]["program"]
    version = "native_blast_database_result_worker_manifest_v2" if program in ("psiblast", "deltablast") else "native_blast_database_result_worker_manifest_v1"
    manifest = dict(version=version, calculation_id=request["calculation_id"],
        request_sha256=hashlib.sha256(request_bytes).hexdigest(), status="failed", input_identity=input_identity,
        input_interpretation_id=initial["input_interpretation_id"], input_implementation_sha256=input_implementation,
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"], sequence_model=deepcopy(request["sequence_model"]),
        artifacts=[], counts=dict(searches=0, native_hsp_slots=0, numerical_rows=0), failures=[])
    failures, metadata_issues, errors = manifest["failures"], [], []
    stage = "capture"
    def save(role, value):
        filename, schema = _artifact_roles(manifest["version"])[role]
        record = _atomic_bytes(directory, filename, _json_bytes(value))
        manifest["artifacts"].append(dict(role=role, relative_path=filename, schema=schema, **record))
        return record
    def save_extraction(binding):
        if binding["extraction"] is not None:
            record = save("native_convergence", binding["extraction"])
            if record != {k: binding["extraction_artifact"][k] for k in ("sha256", "size_bytes")}:
                raise _WorkerFailure("population", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/native_convergence/extraction_artifact")
    try:
        capture = request["bundle_capture"]
        if _decode(_verified_bytes(**capture, pointer="/bundle_capture")) != request["bundle"]:
            raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/bundle_capture")
        bundle = _contracts.validate_native_blast_database_bundle(request["bundle"],
            original_job=request["bundle"]["requested_job"]["native_blast_database"], attempt_identity=request["authenticated_attempt"])
        _verify_implementation(request["implementation"], execution_program=program)
        catalog, contents = _catalog(request, failures)
        for i, native_failure in enumerate(bundle["failures"]):
            failures.append(_WorkerFailure("capture", "native_blast_database_capture_incomplete", "artifact_bytes_unavailable",
                artifact_key=native_failure["artifact_key"], input_key=native_failure["input_key"], pointer=f"/bundle/failures/{i}").failure)
        stage = "inputs"
        if request["reuse"] is not None:
            collection, sheets, input_implementation, saved_version = _reuse(request, input_identity)
            manifest["version"] = saved_version
            prepared = sheets["prepared_inputs"]
        else:
            metadata_payloads = _metadata_payloads(request, catalog, failures)
            from .native_blast_database_metadata import prepare_native_blast_database_inputs, populate_native_blast_database_sheets
            prepared = prepare_native_blast_database_inputs(job=bundle["requested_job"]["native_blast_database"], bundle=bundle,
                artifact_catalog=catalog, metadata_payloads=metadata_payloads, subject_snapshots=request["subject_snapshots"])
            save("inputs", prepared)
            stage = "collection"
            roles = {"primary_report": "primary_report", "stdout": "native_log", "stderr": "native_log",
                "query_msa": "query_msa", "query_pssm": "query_pssm", "checkpoint_asn": "checkpoint", "checkpoint_ascii": "checkpoint"}
            collected = [r for r in catalog["entries"] if r["role"] in roles and r["artifact_key"] in contents]
            descriptors = [{**{k: r[k] for k in ("artifact_key", "format", "fields", "delimiter")}, "role": roles[r["role"]]} for r in collected]
            for descriptor in descriptors:
                if descriptor["format"] == "json15":
                    descriptor["fields"] = None
            collection = parse_blast_report_collection({r["artifact_key"]: contents[r["artifact_key"]] for r in collected},
                artifacts=descriptors, invocation=prepared["invocation"])
            save("collection", collection)
            stage = "population"
            options = {}
            if program in ("psiblast", "deltablast"):
                from .native_blast_database_convergence import bind_native_blast_database_convergence
                binding = bind_native_blast_database_convergence(original_job=bundle["requested_job"]["native_blast_database"],
                    bundle=bundle, attempt_identity=request["authenticated_attempt"], collection=collection,
                    artifact_catalog=catalog, artifact_contents=contents)
                save_extraction(binding)
                options["native_convergence"] = binding
            sheets = populate_native_blast_database_sheets(collection, prepared_inputs=prepared, artifact_catalog=catalog, **options)
            save("sheets", sheets)
        identities = native_blast_database_calculation_identity(input_identity=input_identity, input_implementation_sha256=input_implementation,
            sequence_model=request["sequence_model"], implementation_manifest_sha256=request["implementation"]["manifest_sha256"])
        manifest.update(input_implementation_sha256=input_implementation, input_interpretation_id=identities["input_interpretation_id"])
        if request["calculation_id"] != identities["calculation_id"]:
            raise _WorkerFailure("inputs", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/calculation_id")
        if request["reuse"] is not None:
            save("inputs", prepared); save("collection", collection)
            if sheets["schema"] == "native_blast_database_sheet_set_v2":
                save_extraction(sheets["native_convergence"])
            save("sheets", sheets)
        metadata_issues.extend(sheets["issues"])
        failures.extend(_metadata_failures(metadata_issues))
        manifest["counts"]["searches"] = len(collection["searches"])
        for i, issue in enumerate(collection["issues"]):
            failures.append(_WorkerFailure("collection", "native_blast_database_report_unreadable", "native_syntax_invalid",
                artifact_key=issue.get("artifact_key"), pointer=f"/collection/issues/{i}").failure)
        stage = "calculation"
        calculations = calculate_native_blast_database_sheets(sheets, sequence_model=request["sequence_model"])
        save("calculations", calculations)
        manifest["counts"]["native_hsp_slots"] = len(calculations["native_hsp_components"])
        for i, issue in enumerate(calculations["issues"]):
            failures.append(_WorkerFailure("calculation", "native_blast_database_calculation_failed", "calculator_contract_invalid",
                pointer=f"/calculations/issues/{i}", artifact_key=issue["artifact_key"], search_key=issue["search_key"]).failure)
        stage = "rows"
        rows = build_native_blast_database_rows(bundle_identity=bundle["identity"], calculation_id=request["calculation_id"], sheet_set=sheets, calculations=calculations)
        index, chunks, position = [], [], 0
        for ordinal, row in enumerate(rows):
            data = _json_bytes(row)
            index.append(dict(family=row["family"], record_key=row["record_key"], ordinal=ordinal, byte_start=position, byte_end=position + len(data)))
            chunks.append(data); position += len(data)
        record = _atomic_bytes(directory, "rows.ndjson", b"".join(chunks))
        manifest["artifacts"].append(dict(role="rows", relative_path="rows.ndjson", schema=_ARTIFACT_ROLES["rows"][1], **record))
        save("row_index", dict(schema="native_blast_database_row_index_v1", calculation_id=request["calculation_id"], rows=index))
        manifest["counts"]["numerical_rows"] = len(rows)
        save("metric_definitions", _views.native_blast_database_metric_definitions())
        _verify_implementation(request["implementation"], execution_program=program)
        manifest["status"] = "partial" if failures else "complete"
    except _WorkerFailure as error:
        failures.append(error.failure)
        if error.__cause__ is not None:
            cause = error.__cause__
            errors.append(dict(failure_index=len(failures) - 1, exception_type=type(cause).__module__ + "." + type(cause).__qualname__, message=str(cause)))
    except MemoryError as error:
        failures.append(_WorkerFailure("worker", "native_blast_database_worker_resource_limit", "resource_limit").failure)
        errors.append(dict(failure_index=len(failures) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
    except Exception as error:
        resource = isinstance(error, OSError) and error.errno in (12, 27, 28, 122)
        code = ("native_blast_database_worker_resource_limit" if resource else "native_blast_database_sheet_invalid" if stage in ("inputs", "population")
            else "native_blast_database_calculation_failed" if stage == "calculation" else "native_blast_database_worker_failed")
        detail = "resource_limit" if resource else "calculator_contract_invalid" if isinstance(error, ValueError) and stage in ("inputs", "population", "calculation") else "implementation_failure"
        failures.append(_WorkerFailure("worker" if resource else stage, code, detail).failure)
        errors.append(dict(failure_index=len(failures) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
    save("diagnostics", dict(schema="native_blast_database_diagnostics_v1", failures=failures, metadata_issues=metadata_issues, errors=errors))
    _shape(manifest, _manifest_schema(manifest["version"]))
    _atomic_bytes(directory, "worker-manifest.json", _json_bytes(manifest))
    return manifest


__all__ = ["calculate_native_blast_database_sheets", "populate_native_blast_database_search_facts",
    "build_native_blast_database_rows", "run_native_blast_database_result_worker", "native_blast_database_implementation_identity",
    "native_blast_database_input_identity", "native_blast_database_calculation_identity"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("native_blast_database_result_worker requires one retained request path")
    result = run_native_blast_database_result_worker(sys.argv[1])
    raise SystemExit(1 if result["status"] == "failed" else 0)
