"""Pure presentation of existing HMMER/Infernal jobs and acquired results.

Display copies are not executable requests or custody evidence. Public rows and
File operands remain literal; no parser, calculator, result reader or native
operation is called here. Arbitrary scientific metadata stays opaque.
"""
from collections.abc import Mapping
from copy import deepcopy
import json

from .communication import plain
from .domain import validate_schema


_JOB_VIEW = "native_profile_scientific_job_view_v1"
_RESULT_VIEW = "native_profile_result_receipt_view_v1"
_LABEL = "Selected profile result "
_KINDS = ("native_hmmer", "native_infernal", "native_hmmer_preparation", "native_infernal_preparation")
_JOB_VERSIONS = {kind + "_job_v1": kind for kind in _KINDS}
_RESULT_VERSIONS = {kind + "_acquired_result_v1": kind for kind in _KINDS}
_PUBLIC_FIELDS = ("tool_name", "selector", "observation", "source_ref", "record_refs", "complete", "rows")
_PREPARATION_FIELDS = ("artifacts", "population")
_CHANNELS = ("last_local_outcome", "child_reports", "current_report_update")
_OPAQUE = frozenset({
    "instructions", "schema", "input_schema", "output_schema", "result_selector_schema", "schema_json", "schema_definitions",
    "input", "inputs", "working_state", "metadata", "input_metadata", "request", "requests", "arguments",
    "assignment", "episode_assignment", "selected_execution_task", "execution_assignment", "execution_target",
    "available_report_facts", "requested_form", "result_contract", "tool_info", "child_tool_info",
})
_ERRORS = (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError)


def _require(condition):
    if not condition:
        raise ValueError("native_profile_presentation_invalid")


def _copy(value):
    """Use an existing finite-JSON owner; neither aliases nor scalar coercion."""
    from .native_hmmer_contracts import finite_json_copy
    return finite_json_copy(plain(value))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _profile(kind):
    """Finite schema/validator dispatch; no scientific algorithm is selected."""
    if kind == "native_hmmer":
        from . import native_hmmer_contracts as jobs
        from . import hmmer_native_result_views as public
        return dict(job=jobs.validate_native_hmmer_job, request=jobs.validate_native_hmmer_requested_job,
            schema=jobs.NATIVE_HMMER_JOB_SCHEMA, public=public,
            selector=public.NATIVE_HMMER_RESULT_SELECTOR_SCHEMA, facts=public.native_hmmer_fact_sources)
    if kind == "native_infernal":
        from . import native_infernal_contracts as jobs
        from . import infernal_native_result_views as public
        return dict(job=jobs.validate_native_infernal_job, request=jobs.validate_native_infernal_requested_job,
            schema=jobs.NATIVE_INFERNAL_JOB_SCHEMA, public=public,
            selector=public.NATIVE_INFERNAL_RESULT_SELECTOR_SCHEMA, facts=public.native_infernal_fact_sources)
    if kind == "native_hmmer_preparation":
        from . import native_hmmer_preparation_contracts as jobs
        from . import native_hmmer_preparation_job_schema as schemas
        from . import hmmer_preparation_result_views as public
        return dict(job=jobs.validate_native_hmmer_preparation_job,
            request=jobs.validate_native_hmmer_preparation_requested_job, schema=schemas.preparation_job_schema,
            public=public, selector=public.NATIVE_HMMER_PREPARATION_RESULT_SELECTOR_SCHEMA,
            facts=public.preparation_fact_sources)
    if kind == "native_infernal_preparation":
        from . import native_infernal_preparation_contracts as jobs
        from . import native_infernal_preparation_job_schema as schemas
        from . import infernal_preparation_result_views as public
        return dict(job=jobs.validate_native_infernal_preparation_job,
            request=jobs.validate_native_infernal_preparation_requested_job, schema=schemas.preparation_job_schema,
            public=public, selector=public.NATIVE_INFERNAL_PREPARATION_RESULT_SELECTOR_SCHEMA,
            facts=public.preparation_fact_sources)
    raise ValueError("native_profile_presentation_kind_invalid")


def _drop(schema, fields):
    for name in fields:
        schema["properties"].pop(name)
        schema["required"].remove(name)


def _job_view_schema(kind, job):
    profile = _profile(kind)
    schema = profile["schema"]
    schema = deepcopy(schema(job["program"], job["mode"]) if callable(schema) else schema)
    _drop(schema, ("version", "environment"))
    _drop(schema["properties"]["software"], ("executable", "sha256"))
    for field, omitted in (("operands", "path"), ("outputs", "relative_path")):
        items = schema["properties"][field]["items"]
        for item in items.get("anyOf", [items]):
            _drop(item, (omitted,))
    return schema


def _safe_job(value):
    _require(set(value) == {"version", "kind", "job"} and value["version"] == _JOB_VIEW)
    _require(value["kind"] in _KINDS and type(value["job"]) is dict)
    # This validates a presentation copy, not omitted filesystem/stem joins.
    # Full originals pass their unchanged job validator before projection.
    validate_schema(value["job"], _job_view_schema(value["kind"], value["job"]))
    for operand in value["job"]["operands"]:
        _require(type(operand["size_bytes"]) is int)
        if "ordinal" in operand:
            _require(type(operand["ordinal"]) is int)
    for binding in value["job"].get("operand_bindings", []):
        _require(type(binding["record_ordinal"]) is int)
    return value


def native_profile_scientific_job_view(job):
    """Validate an original job, then omit its typed execution locations only."""
    job = _copy(job)
    version = job.get("version") if type(job) is dict else None
    kind = _JOB_VERSIONS.get(version) if type(version) is str else None
    _require(kind is not None)
    job = _profile(kind)["job"](job)
    shown = {key: deepcopy(value) for key, value in job.items() if key not in {"version", "environment"}}
    shown["software"] = {"engine_version": job["software"]["engine_version"]}
    shown["operands"] = [{key: deepcopy(value) for key, value in row.items() if key != "path"}
        for row in job["operands"]]
    shown["outputs"] = [{key: deepcopy(value) for key, value in row.items() if key != "relative_path"}
        for row in job["outputs"]]
    return _safe_job(dict(version=_JOB_VIEW, kind=kind, job=shown))


def _partition(row, requested):
    measured = [cell["name"] for cell in row["measurements"]]
    unavailable = [cell["name"] for cell in row["unavailable"]]
    names = measured + unavailable
    _require(len(names) == len(set(names)) and set(names) == set(requested))
    _require(measured == [name for name in requested if name in measured]
        and unavailable == [name for name in requested if name in unavailable])


def _selector(value, profile):
    validate_schema(value, profile["selector"])
    projection = value["projection"]
    if projection is not None:
        rows = projection["rows"]
        if "offset" in rows:
            _require(type(rows["offset"]) is int and type(rows["limit"]) is int)
    for artifact in value.get("artifacts", []):
        _require(type(artifact["ordinal"]) is int)


def _safe_result(value):
    kind = value["kind"]
    _require(kind in _KINDS)
    preparation = kind.endswith("_preparation")
    fields = {"version", "kind", *_PUBLIC_FIELDS, *(_PREPARATION_FIELDS if preparation else ())}
    _require(set(value) == fields and value["version"] == _RESULT_VIEW)
    profile, selector = _profile(kind), value["selector"]
    _selector(selector, profile)
    _require(value["tool_name"] in ("execution.results.status", "execution.results.collect"))
    observation = value["observation"]
    _require(type(observation) is dict and set(observation) == {"state", "returncode"})
    _require(type(observation["state"]) is str and bool(observation["state"]))
    _require(observation["returncode"] is None or type(observation["returncode"]) is int)
    _require(type(value["complete"]) is bool and type(value["record_refs"]) is list
        and all(type(item) is str and item for item in value["record_refs"]))
    source = value["source_ref"]
    _require(source is None or type(source) is str and source and source in value["record_refs"])
    _require(type(value["rows"]) is list)
    public = profile["public"]
    projection = selector["projection"]
    if preparation:
        _require(type(value["artifacts"]) is list)
        for artifact in value["artifacts"]:
            validate_schema(artifact, public.ARTIFACT_SCHEMA)
            _require(artifact["source_ref"] == source)
        if value["population"] is not None:
            population = value["population"]
            validate_schema(population, public.POPULATION_SCHEMA)
            _require(population["source_ref"] == source)
            _require(all(type(population[name]) is int for name in ("total_records", "returned_records",
                "omitted_records", "requested_artifact_count", "returned_artifact_count")))
            _require(population["returned_records"] == len(value["rows"])
                and population["returned_artifact_count"] == len(value["artifacts"])
                and population["requested_artifact_count"] == len(selector["artifacts"]))
            _require(population["collection"] == (None if projection is None else projection["collection"])
                and population["total_records"] == population["returned_records"] + population["omitted_records"])
        _require(projection is not None or not value["rows"])
        for row in value["rows"]:
            validate_schema(row, public.ROW_SCHEMA)
            _require(row["source_ref"] == source)
            paths = [cell["path"] for cell in row["quantities"]]
            checks = [cell["name"] for cell in row["checks"]]
            _require(paths == projection["quantities"])
            _require(set(checks) == set(projection["checks"]))
    else:
        family = projection["family"]
        for row in value["rows"]:
            validate_schema(row, public.row_schema(family))
            _require(row["source_ref"] == source)
            _partition(row, projection["metrics"])
    if source is None:
        _require(not value["complete"] and not value["record_refs"] and not value["rows"] and (not preparation
            or not value["artifacts"] and value["population"] is None))
    return value


def _result(value):
    version = value.get("version")
    if version == _RESULT_VIEW:
        return _safe_result(_copy(value))
    kind = _RESULT_VERSIONS.get(version) if type(version) is str else None
    if kind is None:
        return None
    # No target, capture, prepared record, private failure or action control is
    # read, validated or copied. The original owner authenticates those fields.
    observation = value["observation"]
    shown = {key: plain(value[key]) for key in _PUBLIC_FIELDS if key not in {"selector", "observation"}}
    shown.update(version=_RESULT_VIEW, kind=kind, selector=plain(value["assignment"]["selector"]),
        observation={key: observation[key] for key in ("state", "returncode")})
    if kind.endswith("_preparation"):
        shown.update({key: plain(value[key]) for key in _PREPARATION_FIELDS})
    return _safe_result(_copy(shown))


def select_native_profile_execution_values(value):
    """Select exact profile records before generic execution-field masking."""
    if not isinstance(value, Mapping):
        return None
    try:
        version = value.get("version")
        if version == _JOB_VIEW:
            return _safe_job(_copy(value))
        if type(version) is str and version in _JOB_VERSIONS:
            return native_profile_scientific_job_view(value)
        result = _result(value)
        if result is not None:
            return result
        for kind in _KINDS:
            if set(value) == {"argv", "environment", kind}:
                request = _profile(kind)["request"](_copy(value))
                return native_profile_scientific_job_view(request[kind])
            profile = _profile(kind)
            if version == profile["selector"]["properties"]["version"]["const"]:
                selected = _copy(value)
                _selector(selected, profile)
                return selected
    except _ERRORS:
        return None
    return None


def select_native_profile_presentation(state, *, lookup_results=()):
    """Gather only declared result channels; unknown/input/schema data is opaque."""
    context, lookups = deepcopy(plain(state)), deepcopy(plain(lookup_results))
    projections, keys = [], []

    def visit(value):
        if isinstance(value, Mapping):
            try:
                projected = _result(value)
            except _ERRORS:
                projected = None
            if projected is not None:
                key = _canonical(projected)
                if key not in keys:
                    keys.append(key)
                    projections.append(projected)
                return _LABEL + str(keys.index(key) + 1)
            if "version" in value:
                return deepcopy(value)
            return {key: deepcopy(child) if key in _OPAQUE else visit(child) for key, child in value.items()}
        if isinstance(value, list):
            return [visit(child) for child in value]
        return deepcopy(value)

    if isinstance(context, dict):
        for name in _CHANNELS:
            if name in context:
                context[name] = visit(context[name])
    lookups = [visit(value) for value in lookups]
    return dict(context=context, lookup_results=lookups, projections=projections)


def has_native_profile_receiver_context(context):
    """Recognize exact fact capabilities or public receipts, never row shapes."""
    if not isinstance(context, Mapping):
        return False
    supplied = context.get("available_report_facts", {})
    if isinstance(supplied, Mapping):
        for kind in _KINDS:
            for name, registered in _profile(kind)["facts"]().items():
                if name in supplied:
                    try:
                        if _canonical(plain(supplied[name])) == _canonical(registered):
                            return True
                    except _ERRORS:
                        pass
    return bool(select_native_profile_presentation(context)["projections"])


def _literal(value):
    return value if type(value) is str else json.dumps(value, ensure_ascii=False, allow_nan=False)


def _table(headers, rows):
    def escape(value):
        return _literal(value).replace("|", "\\|").replace("\n", "<br>")
    rows = list(rows)
    if not rows:
        return "[]"
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(escape(cell) for cell in row) + " |" for row in rows)])


def _section(parts, title, value):
    parts.extend(["", title, "", value])


def render_native_profile_results(projections):
    """Render existing public selections without calculating or hydrating rows."""
    parts = []
    for index, original in enumerate(projections, 1):
        value = _result(original)
        _require(value is not None)
        parts.extend([_LABEL + str(index), "", _table(("Result property", "Literal value"),
            ((key, value[key]) for key in ("kind", "tool_name", "source_ref", "record_refs", "selector", "observation", "complete")))])
        parts.extend(["", "The complete flag describes this retained scientific acquisition; action completion alone does not establish it."])
        preparation = value["kind"].endswith("_preparation")
        if preparation:
            _section(parts, "Selected preparation row associations", _table(
                ("Record key", "Kind", "Name", "Accession", "Source", "Artifact"),
                ((row["record_key"], row["kind"], row["name"], row["accession"], row["source_ref"], row["artifact_ref"])
                    for row in value["rows"])))
            _section(parts, "Selected preparation quantities", _table(
                ("Record key", "Quantity", "Literal value", "State", "Unit", "Basis when supplied"),
                ((row["record_key"], cell["path"], cell["value"], cell["state"], cell["unit"],
                    cell.get("basis", "not supplied in this public schema"))
                    for row in value["rows"] for cell in row["quantities"])))
            _section(parts, "Selected preparation checks", _table(("Record key", "Check", "Outcome", "Original occurrences"),
                ((row["record_key"], cell["name"], cell["outcome"], cell["occurrences"])
                    for row in value["rows"] for cell in row["checks"])))
            fields = ("source_ref", "direction", "role", "ordinal", "artifact_ref", "format", "size_bytes", "sha256", "completeness")
            _section(parts, "Selected and required artifact occurrences", _table(fields,
                ([row[name] for name in fields] for row in value["artifacts"])))
            population = value["population"]
            _section(parts, "Original selected-population accounting", "null" if population is None else
                _table(("Population field", "Literal value"), population.items()))
        else:
            association = ("record_key", "source_ref", "observation_ref", "subject_ref", "reference_refs")
            extra = (("query_occurrence", "target_occurrence", "iteration", "strand", "status")
                if value["kind"] == "native_hmmer" else
                ("sequence_name", "model_name", "strand", "origin", "population", "column_index", "pair_columns", "status"))
            fields = (*association, *extra)
            _section(parts, "Selected native row associations", _table(fields,
                ([row[name] for name in fields] for row in value["rows"])))
            _section(parts, "Requested native and calculated measurements", _table(("Record key", "Requested metric", "Literal value"),
                ((row["record_key"], cell["name"], cell["value"]) for row in value["rows"] for cell in row["measurements"])))
            _section(parts, "Requested unavailable measurements", _table(("Record key", "Requested metric", "Original missingness class"),
                ((row["record_key"], cell["name"], cell["reason"]) for row in value["rows"] for cell in row["unavailable"])))
        parts.append("")
    return "\n".join(parts).rstrip()


__all__ = ["native_profile_scientific_job_view", "select_native_profile_execution_values",
    "select_native_profile_presentation", "render_native_profile_results", "has_native_profile_receiver_context"]
