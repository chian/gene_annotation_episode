"""Original native_blast_database_result_worker scientific values and explicit received-record contracts."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_database_contracts as _contracts
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_iteration_calculators as _iteration
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_profile_calculators as _profile
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_pssm_calculators as _pssm
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_vdb_calculators as _vdb
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_database_result_views as _views
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_grader import alignment_components
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_fasta_record_identity import blast_record_identity
from gene_annotation_episode.episodic_workflow.root.a101.domain import canonical
from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a101.domain import identity
import json
import math
import re
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_program_context import resolve_blast_program_context
from gene_annotation_episode.episodic_workflow.root.a101.domain import validate_schema

_SHEET_KEYS = {"schema", "collection", "prepared_inputs", "derived_search_bindings", "sequence", "profile", "vdb", "pssm", "msa", "iteration", "metadata_parse_results", "metadata_binding_results", "issues"}

_CALC_KEYS = {"schema", "sequence_model", "iteration", "profile", "vdb", "pssm", "search_facts", "native_hsp_components", "issues"}

_FUNCTION_REQUEST = "native_blast_database_result_worker_request_vdb_function_v1"

_FUNCTION_SHEETS = "native_blast_database_sheet_set_vdb_function_v1"

_FUNCTION_CALCULATIONS = "native_blast_database_calculations_vdb_function_v1"

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

_ABS = {"type": "string", "minLength": 1}

_FILE_ID = dict(artifact_ref=_views._REF, sha256=_views._SHA, size_bytes=_views._I0)

_DESCRIPTOR = _views._object(dict(input_key=_views._TOKEN,
    consumer={"enum": ["query_identity", "sequence_database", "profile", "iteration", "vdb"]},
    schema_id=_views._TOKEN, **_FILE_ID, origin={"enum": ["original_job_input", "selected_results_input"]}))

def _descriptor(function_mode=False):
    value = deepcopy(_DESCRIPTOR)
    if function_mode:
        value["properties"]["consumer"]["enum"].append("vdb_function")
    return value

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
            metadata_descriptors=_views._array(_descriptor(request.get("version") == _FUNCTION_REQUEST)), retained_sources=_views._array(_views._object(dict(source_ref=_views._REF, **_FILE_ID))),
            subject_snapshots=_views._array(_views._object(_SNAPSHOT_ID)))))
        _absolute_path(value["authenticated_attempt"]["attempt_directory"])
    except (KeyError, TypeError) as error:
        raise ValueError("native_blast_database_input_identity_invalid") from error
    return _hash(value)

def native_blast_database_calculation_identity(*, input_identity, input_implementation_sha256, sequence_model, implementation_manifest_sha256, vdb_function_model=None):
    """Separate input interpretation from the selected numerical generation."""
    for digest in (input_identity, input_implementation_sha256, implementation_manifest_sha256):
        _shape(digest, _views._SHA)
    model = _model(sequence_model)
    interpretation = _hash(dict(version="native_blast_database_interpretation_identity_v1",
        input_identity=input_identity, input_implementation_sha256=input_implementation_sha256))
    if vdb_function_model is not None:
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_vdb_function_calculators import validate_blast_vdb_function_model
        function_model = validate_blast_vdb_function_model(vdb_function_model)
        return dict(input_interpretation_id=interpretation, calculation_id=_hash(dict(
            version="native_blast_vdb_function_calculation_identity_v1", input_interpretation_id=interpretation,
            base_calculation_contract=dict(schema="native_blast_database_calculations_v1", sequence_model=model),
            model=function_model, calculator_implementation_identity=implementation_manifest_sha256)))
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
    _population_sheet_binding(sheet_set)
    if sheet_set.get("schema") == "native_blast_database_sheet_set_v1" and set(sheet_set) == _SHEET_KEYS:
        return None
    if sheet_set.get("schema") == _FUNCTION_SHEETS:
        if (set(sheet_set) != _SHEET_KEYS | {"vdb_function"}
                or sheet_set["collection"]["invocation"]["execution_program"] not in ("blastn_vdb", "tblastn_vdb")):
            raise ValueError("native_blast_database_sheet_set_invalid")
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_vdb_function_inputs import validate_blast_vdb_function_sheet
        seen = set()
        for row in sheet_set["vdb_function"]:
            if type(row) is not dict or set(row) != {"search_key", "sheet"}:
                raise ValueError("native_blast_database_sheet_set_invalid")
            key = canonical(row["search_key"])
            matches = [r for r in sheet_set["vdb"] if r["search_key"] == row["search_key"]]
            if key in seen or len(matches) != 1 or row["sheet"]["base_sheet"] != matches[0]["sheet"]:
                raise ValueError("native_blast_database_sheet_set_invalid")
            validate_blast_vdb_function_sheet(row["sheet"])
            seen.add(key)
        return None
    if (sheet_set.get("schema") != "native_blast_database_sheet_set_v2"
            or set(sheet_set) != _SHEET_KEYS | {"native_convergence"}
            or sheet_set["collection"]["invocation"]["execution_program"] not in ("psiblast", "deltablast")):
        raise ValueError("native_blast_database_sheet_set_invalid")
    from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_convergence import validate_native_blast_database_convergence_binding
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

def _population_sheet_binding(sheet_set):
    """Validate the saved v3 handoff using the metadata owner's validator."""
    from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_population_metadata import SEQUENCE_POPULATION_METADATA_SCHEMA, validate_native_blast_database_population_associations, _population_search_units
    prepared = sheet_set.get("prepared_inputs", {})
    validations = [v for v in prepared.get("metadata", []) if v.get("schema_id") == SEQUENCE_POPULATION_METADATA_SCHEMA]
    sequence_rows = sheet_set.get("sequence", [])
    selected = [r for r in sequence_rows if r["sheet"].get("schema") == "blast_sequence_database_result_sheet_v3"]
    if not validations and not selected:
        return
    records = [r for v in validations for r in v["population_source_records"]]
    iteration = sheet_set.get("iteration")
    if iteration is None:
        raise ValueError("blast_database_population_saved_relation_conflict")
    expected = []
    for row in sequence_rows:
        scientific, key = row["sheet"], row["search_key"]
        searches = [s for s in sheet_set["collection"]["searches"] if s["search_key"] == key]
        if len(searches) != 1:
            raise ValueError("blast_database_population_saved_relation_conflict")
        has_population = any(_population_search_units(searches[0], prepared, records))
        if has_population != (scientific.get("schema") == "blast_sequence_database_result_sheet_v3"):
            raise ValueError("blast_database_population_saved_relation_conflict")
        if not has_population:
            continue
        metadata = [r for r in iteration["sequence_metadata"] if r["search_key"] == key]
        sources = [r["report_source"] for r in iteration["report_sources"] if r["search_key"] == key]
        if (len(searches) != 1 or len(metadata) != 1 or sources != [scientific["report_source"]]
                or scientific["search"] != searches[0]
                or scientific["search_binding"]["stage"] != "sequence_database"
                or metadata[0].get("database_population_associations") != scientific["database_population_associations"]
                or metadata[0]["database_profile"] != scientific["database_profile"]):
            raise ValueError("blast_database_population_saved_relation_conflict")
        validate_native_blast_database_population_associations(scientific["database_population_associations"],
            search=searches[0], prepared_inputs=prepared, source_records=records,
            database_profile=scientific["database_profile"])
        expected.append(key)
    actual = [r["search_key"] for r in iteration["sequence_metadata"] if r.get("database_population_associations") is not None]
    original = [s["search_key"] for s in sheet_set["collection"]["searches"]
        if any(b["search_key"] == s["search_key"] and b["stage"] == "sequence_database" for b in iteration["search_bindings"])
        and any(_population_search_units(s, prepared, records))]
    if (sorted(map(canonical, actual)) != sorted(map(canonical, expected))
            or sorted(map(canonical, original)) != sorted(map(canonical, expected))
            or bool(expected) != (iteration["schema"] == "blast_iteration_sheet_v3")):
        raise ValueError("blast_database_population_saved_relation_conflict")

def calculate_native_blast_database_sheets(sheet_set, *, sequence_model, vdb_function_model=None, saved_calculations=None):
    """Calculate actual saved populations once, retaining all nested outputs."""
    sheet_set = _views._copy(sheet_set)
    _sheet_binding(sheet_set)
    model = _model(sequence_model)
    collection = sheet_set["collection"]; program = collection["invocation"]["execution_program"]
    if program not in _views._PROGRAMS:
        raise ValueError("native_blast_database_program_unsupported")
    function_mode = sheet_set["schema"] == _FUNCTION_SHEETS
    if function_mode:
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_vdb_function_calculators import validate_blast_vdb_function_model, calculate_blast_vdb_function_components
        vdb_function_model = validate_blast_vdb_function_model(vdb_function_model)
    elif vdb_function_model is not None or saved_calculations is not None:
        raise ValueError("native_blast_database_sheet_set_invalid")
    if saved_calculations is not None:
        out = _views._copy(saved_calculations)
        if (set(out) != _CALC_KEYS | {"vdb_function_model", "vdb_function"}
                or out["schema"] != _FUNCTION_CALCULATIONS or out["sequence_model"] != model):
            raise ValueError("native_blast_database_saved_calculations_invalid")
        # These are authenticated saved values. No native/base calculator runs.
        out["vdb_function_model"] = vdb_function_model
        out["vdb_function"] = []
        out["issues"] = [r for r in out["issues"] if not r["code"].startswith("blast_vdb_function_")]
        for row in sheet_set["vdb_function"]:
            try:
                component = calculate_blast_vdb_function_components(row["sheet"], model=vdb_function_model)
            except ValueError as error:
                out["issues"].append(dict(artifact_key=row["search_key"]["artifact_key"], search_key=deepcopy(row["search_key"]),
                    code=str(error)))
            else:
                out["vdb_function"].append(dict(search_key=deepcopy(row["search_key"]), components=component))
        return out
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
            saved_base = [r["sheet"]["base_components"] for r in sheet_set.get("vdb_function", []) if r["search_key"] == row["search_key"]]
            out[family].append(dict(search_key=deepcopy(row["search_key"]),
                components=deepcopy(saved_base[0]) if function_mode and len(saved_base) == 1 else calculator(row["sheet"])))
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
    if function_mode:
        out.update(schema=_FUNCTION_CALCULATIONS, vdb_function_model=vdb_function_model, vdb_function=[])
        for row in sheet_set["vdb_function"]:
            try:
                component = calculate_blast_vdb_function_components(row["sheet"], model=vdb_function_model)
            except ValueError as error:
                out["issues"].append(dict(artifact_key=row["search_key"]["artifact_key"], search_key=deepcopy(row["search_key"]),
                    code=str(error)))
            else:
                out["vdb_function"].append(dict(search_key=deepcopy(row["search_key"]), components=component))
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

def _sequence_quality_source(database, association):
    """Retain the exact saved metadata address and its accepted association."""
    metadata = database["reference_metadata"][association["metadata_index"]]
    source = dict(source_ref=metadata["source"], pointer=metadata["native_pointer"])
    locator = metadata.get("record_locator")
    if locator is not None:
        blast_record_identity(**source, record_locator=locator)
        binding = association.get("description_binding")
        index = association.get("binding_index")
        if (database["schema"] not in ("blast_database_sheet_v2", "blast_database_sheet_v3") or type(index) is not int or index < 0
                or index >= len(database.get("description_bindings", [])) or type(binding) is not dict
                or database["description_bindings"][index] != binding
                or any(binding.get(k) != association.get(k) for k in ("report_index", "hit_index", "description_index", "metadata_index"))
                or binding.get("metadata_source_ref") != source["source_ref"]
                or binding.get("metadata_pointer") != source["pointer"]
                or binding.get("metadata_record_locator") != locator
                or binding.get("metadata_identifier") != dict(namespace=metadata["identifier_namespace"], value=metadata["accession"])
                or association.get("source") != source["source_ref"] or association.get("assembly") != metadata.get("assembly")
                or any(value is not None and value != metadata["assembly"].get(name)
                    for name, value in association["quality_measurements"].items())):
            raise ValueError("native_blast_database_record_quality_relation_invalid")
        source["record_locator"] = deepcopy(locator)
    return source

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
                source = _sequence_quality_source(database, a)
                expected = dict(assembly_accession=assembly.get("accession"), source=a["source"], quality_method=assembly.get("quality_method"),
                    measurement_methods=assembly.get("measurement_methods") or {}, accession=a["accession"] if not assembly.get("accession") else None,
                    measurements=a["quality_measurements"])
                if expected != measurement:
                    continue
                record_key = blast_record_identity(source_ref=source["source_ref"], pointer=source["pointer"], record_locator=source.get("record_locator"))
                refs = sources.setdefault(record_key, (source, []))[1]
                refs.append(dict(artifact_role="calculations", pointer=dbase + f"/hits/{hi}/associations/{ai}"))
                if "record_locator" in source:
                    refs.append(dict(artifact_role="calculations", pointer=dbase + f"/reference_metadata/{a['metadata_index']}"))
        for source, refs in sources.values():
            family = "sequence_record_quality" if "record_locator" in source else "sequence_quality"
            builder.add(family, dict(search_key=key, function=function, assembly_source=source), b, measurement["measurements"],
                key=key, status=status, details={n: dict(pointer=b + "/measurements/" + n) for n in _views._METRICS[family]},
                origins={n: "supplied_source_record" for n in _views._METRICS[family]},
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

def _function_cell(name, component, pointer, *, unit=None, complete=None, numerator=None, denominator=None, log=False):
    """Copy a saved scalar and qualification; no statistical arithmetic here."""
    if type(component) is dict:
        value = component["log2_value" if log else "value"]
        unit = unit or component["unit"]
        reason = component.get("reason_code", component.get("unavailable_reason"))
        status = component.get("linear_status", component.get("status"))
        complete = component.get("complete", complete)
        numerator = component.get("numerator", numerator)
        denominator = component.get("denominator", denominator)
    else:
        value, reason, status = component, None, None
    if value is not None:
        status, reason = "available", None
    else:
        suffix = (reason or "").removeprefix("blast_vdb_function_")
        if log and type(component) is dict and component.get("linear_status") == "zero":
            reason = "not_measured"
        elif suffix in {"linear_underflow", "kernel_arithmetic_out_of_range"}:
            reason = "linear_underflow" if suffix == "linear_underflow" else "arithmetic_out_of_range"
        elif status == "incompatible" or suffix.endswith(("conflict", "mismatch")):
            reason = "incompatible_input"
        else:
            reason = "missing_input" if suffix else "not_measured"
        status = "incompatible" if status == "incompatible" else "unavailable"
    return dict(name=name, value=value, numerator=numerator, denominator=denominator, unit=unit,
        status=status, reason=reason, origin="derived", complete=complete, component_pointer=pointer)

def _vdb_function_rows(builder, component, base):
    key = component["search_key"]
    def add(family, ident, status, cells, booleans=(), refs=None):
        for cell in [*cells, *booleans]:
            # Exact pointers must resolve, including null-valued cells.
            _at(builder.calculations, cell["component_pointer"])
        builder.rows.append(dict(schema="native_blast_vdb_function_numeric_row_v1", family=family,
            record_key=identity("native_blast_database_row", dict(version="native_blast_database_row_identity_v1",
                attempt=builder.attempt, family=family, identity=ident)), calculation_id=builder.calculation_id,
            identity=deepcopy(ident), program=builder.program, context=builder.context(key),
            component_refs=refs or [dict(artifact_role="calculations", pointer=base)], native_status=status,
            measurements=cells, booleans=list(booleans)))
    calibration = _boolean("calibrated_annotation_probability", component["calibrated_annotation_probability"], base + "/calibrated_annotation_probability")
    aliases = dict(source_entity_count="source_entities", eligible_entity_count="eligible_entities", excluded_entity_count="excluded_entities",
        eligible_hsp_count="eligible_hsps", target_unit_count="duplicate_target_units", model_group_count="model_groups",
        unknown_origin_subject_count="unknown_origin_subjects", unassigned_target_unit_count="unassigned_target_units",
        unresolved_sample_entity_count="unresolved_sample_entities")
    for si, stratum in enumerate(component["strata"]):
        pointer = base + f"/strata/{si}"
        ident = dict(search_key=key, **{k: stratum[k] for k in ("assignment_scope", "namespace", "grouping_model")})
        group_unit = "target_unit" if stratum["grouping_model"] == "target_duplicates_only" else "dependence_block"
        units = dict(hsp="hsp", hit="hit", target_unit="target_unit", model_group_unit=group_unit,
            entity_unit="member" if stratum["assignment_scope"] == "whole_sequence" else "feature")
        cells = [_function_cell(name, stratum["counts"][field], pointer + "/counts/" + field,
            unit=units[_views._METRICS["vdb_function_summary"][name]["units"]], complete=stratum["report_complete"])
            for name, field in aliases.items()]
        cells.append(_function_cell("unknown_reference_kernel_fraction", stratum["unknown_reference_kernel_fraction"],
            pointer + "/unknown_reference_kernel_fraction/value", complete=stratum["report_complete"],
            numerator=stratum["unknown_reference_kernel_mass"]["value"], denominator=stratum["total_reference_kernel_mass"]["value"]))
        add("vdb_function_summary", ident, stratum["status"], cells,
            [_boolean(name, stratum[name], pointer + "/" + name) for name in ("report_complete", "metadata_complete", "dependency_complete")] + [calibration])
        for fi, function in enumerate(stratum["functions"]):
            fp = pointer + f"/functions/{fi}"
            cells = []
            for name in _views._METRICS["vdb_function"]:
                log = name.startswith("log2_"); field = name.removeprefix("log2_")
                kwargs = dict(complete=stratum["report_complete"])
                if log:
                    kwargs["unit"] = "log2_function_mass" if field == "function_mass" else "log2_fraction"
                if field == "conditional_function_weight" and not log:
                    kwargs.update(numerator=function["prior_weighted_mass"]["value"], denominator=stratum["conditional_weight_denominator"]["value"])
                if field == "representation_adjusted_function_weight" and not log:
                    kwargs.update(numerator=function["representation_rate"]["value"], denominator=stratum["representation_adjusted_weight_denominator"]["value"])
                cells.append(_function_cell(name, function[field], fp + "/" + field + ("/log2_value" if log else "/value"), log=log, **kwargs))
            add("vdb_function", dict(**ident, function=function["function"], census_key=stratum["census_key"]), stratum["status"], cells, [calibration])
        for gi, group in enumerate(stratum["groups"]):
            for ci, contribution in enumerate(group["function_contributions"]):
                cp = pointer + f"/groups/{gi}/function_contributions/{ci}"
                cells = [_function_cell(name, contribution[name], cp + "/" + name + "/value", complete=stratum["report_complete"])
                    for name in _views._METRICS["vdb_function_contribution"]]
                add("vdb_function_contribution", dict(**ident, group_key=group["group_key"], function=contribution["function"]), stratum["status"], cells,
                    refs=[dict(artifact_role="calculations", pointer=pointer + f"/groups/{gi}")])
    for ci, census in enumerate(component["census_results"]):
        cp = base + f"/census_results/{ci}"
        ident = dict(search_key=key, assignment_scope=census["assignment_scope"], namespace=census["namespace"],
            grouping_model=component["model"]["grouping_model"], census_key=census["census_key"])
        cells = [_function_cell(name, census[name], cp + "/" + name + "/value", complete=census["enumeration_complete"])
            for name in _views._METRICS["vdb_function_census"]]
        add("vdb_function_census", ident, census["status"], cells,
            [_boolean("census_complete", census["enumeration_complete"], cp + "/enumeration_complete")])

def build_native_blast_database_rows(*, bundle_identity, calculation_id, sheet_set, calculations):
    """Build all families from retained components; no reparse or recalculation."""
    validate_schema(calculation_id, _views._SHA)
    sheet_set, calculations, bundle_identity = map(_views._copy, (sheet_set, calculations, bundle_identity))
    _shape(bundle_identity, _contracts.IDENTITY_SCHEMA)
    _sheet_binding(sheet_set)
    function_mode = sheet_set["schema"] == _FUNCTION_SHEETS
    if (set(calculations) != _CALC_KEYS | ({"vdb_function_model", "vdb_function"} if function_mode else set())
            or calculations["schema"] != (_FUNCTION_CALCULATIONS if function_mode else "native_blast_database_calculations_v1")):
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
    for i, row in enumerate(calculations.get("vdb_function", [])):
        _vdb_function_rows(builder, row["components"], f"/vdb_function/{i}/components")
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
