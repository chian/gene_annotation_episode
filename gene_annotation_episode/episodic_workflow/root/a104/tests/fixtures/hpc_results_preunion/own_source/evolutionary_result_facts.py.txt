"""A104 conservation and phylogeny facts from saved actions and typed returns.

Live groups use the existing publication reader. Frozen and received groups
authenticate original forms and receipt prefixes without reopening their Files.
DTO validation alone confers neither publication authority nor File access.
"""
from collections.abc import Mapping
from copy import deepcopy
import json

from .domain import ContractError, canonical


_PROFILES = {
    "protein_conservation_outcomes": ("analyze_protein_conservation", "protein_conservation_"),
    "protein_phylogeny_outcomes": ("analyze_protein_phylogeny", "protein_phylogeny_"),
}


def _profile(fact_source):
    try:
        return _PROFILES[fact_source]
    except (KeyError, TypeError) as error:
        raise ContractError("molecular_fact_source_invalid") from error


def _sources(fact_source):
    _profile(fact_source)
    if fact_source == "protein_phylogeny_outcomes":
        from .protein_phylogeny_result_contracts import phylogeny_fact_sources
        return phylogeny_fact_sources()
    from .protein_conservation_result_contracts import conservation_fact_sources
    return conservation_fact_sources()


def molecular_fact_sources():
    """Declare the finite complete Source-group contracts."""
    return {name: _sources(name)[name] for name in _PROFILES}


def requested_molecular_fact_sources(schema):
    """Unrelated historical forms do not enter the new validation path."""
    properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
    if not isinstance(properties, Mapping):
        return ()
    present = {node.get("x-source") for node in properties.values()
        if isinstance(node, Mapping) and isinstance(node.get("x-source"), str)}
    return tuple(name for name in _PROFILES if name in present
        and requested_molecular_fact_fields(schema, fact_source=name))


def requested_molecular_fact_fields(schema, *, fact_source):
    """A requested group retains its exact complete registered schema."""
    _, prefix = _profile(fact_source)
    properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
    if not isinstance(properties, Mapping) or not any(isinstance(node, Mapping)
            and node.get("x-source") == fact_source for node in properties.values()):
        return []
    from .communication import plain, validate_closed_schema
    schema = validate_closed_schema(plain(schema))
    available = _sources(fact_source)[fact_source]["report_schema"]
    fields = []
    for name, node in schema["properties"].items():
        if node.get("x-source") == fact_source:
            if canonical(node) != canonical(available):
                raise ContractError(prefix + "requested_schema_conflict")
            fields.append(name)
    return fields


def validate_molecular_fact(value, *, fact_source):
    _, prefix = _profile(fact_source)
    from .communication import plain
    if fact_source == "protein_phylogeny_outcomes":
        from .protein_phylogeny_result_contracts import validate_phylogeny_return as validate
    else:
        from .protein_conservation_result_contracts import validate_conservation_return as validate
    try:
        return validate(plain(value))
    except ValueError as error:
        raise ContractError(prefix + "return_invalid") from error


def merge_molecular_facts(*groups, fact_source):
    """Deduplicate equal complete Source groups; conflicting copies fail."""
    _, prefix = _profile(fact_source)
    result, seen = [], {}
    for group in groups:
        if type(group) is not list:
            raise ContractError(prefix + "facts_array_required")
        for item in group:
            value = validate_molecular_fact(item, fact_source=fact_source)
            reference, body = value["source_ref"], canonical(value)
            reference = (reference, canonical(value["selection"]))
            if reference in seen and seen[reference] != body:
                raise ContractError(prefix + "facts_source_conflict")
            if reference not in seen:
                result.append(value)
                seen[reference] = body
    return result


def _project(stored, source_ref, fact_source):
    value = validate_molecular_fact(stored, fact_source=fact_source)
    if value["source_ref"] != source_ref:
        raise ContractError(_profile(fact_source)[1] + "fact_source_conflict")
    return value


def own_molecular_facts(registry, context, *, read_received, fact_source):
    """Authenticate current own actions, then project their original Sources."""
    from .communication import plain
    from .episode_return_records import EpisodeReturnRecords
    tool_name, prefix = _profile(fact_source)
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix=prefix).authenticate(context)
    if context.role != "scientific_process":
        raise ContractError(prefix + "scientific_context_required")
    result = []
    rows = registry.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND json_extract(action,'$.kind')='tool' AND json_extract(action,'$.tool')=? "
        "AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
        (context.run_id, context.episode_id, tool_name))
    for row in rows:
        action, actual = json.loads(row["action"]), json.loads(row["result"])
        key = f'{context.run_id}:{context.episode_id}:{row["decision_index"]}'
        operation = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        if (operation is None or operation["name"] != tool_name
                or operation["arguments"] != canonical(action["arguments"])
                or operation["scope"] != canonical(plain(context.scope))
                or operation["id"] != actual.get("operation_ref")
                or canonical({k: v for k, v in actual.items() if k != "pending_work_after_action"}) != operation["result"]):
            raise ContractError(prefix + "action_conflict")
        if fact_source == "protein_phylogeny_outcomes":
            from .protein_phylogeny_publication import read_protein_phylogeny_action_result as read_action_result
        else:
            from .protein_conservation_publication import read_protein_conservation_action_result as read_action_result
        value = read_action_result(registry, context,
            action["arguments"], key, reader=read_received)
        if (value["source_ref"] not in actual.get("record_refs", [])
                or canonical(value) != canonical(actual.get("result"))):
            raise ContractError(prefix + "action_source_conflict")
        result.append(_project(value, value["source_ref"], fact_source))
    return merge_molecular_facts(result, fact_source=fact_source)


def frozen_molecular_facts(store, run_id, context, *, fact_source):
    """Read a literal frozen group; absence remains unknown, not empty."""
    from .episode_return_records import EpisodeReturnRecords
    _, prefix = _profile(fact_source)
    EpisodeReturnRecords(store, run_id, failure_prefix=prefix).authenticate(context)
    row = store.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (run_id, context.episode_id)).fetchone()
    if row is None:
        return None
    facts = json.loads(row["facts"])
    if fact_source not in facts:
        return None
    values = facts[fact_source]
    if type(values) is not list:
        raise ContractError(prefix + "frozen_source_invalid")
    for value in values:
        validate_molecular_fact(value, fact_source=fact_source)
    return deepcopy(values)


def validate_frozen_molecular_return(form, schema, frozen, *, fact_source):
    """Compare original typed values without native or private File reads."""
    from .communication import ReportBoundaryError, plain
    _, prefix = _profile(fact_source)
    for name in requested_molecular_fact_fields(schema, fact_source=fact_source):
        actual = plain(form).get(name)
        try:
            if type(frozen) is not list or type(actual) is not list:
                raise ContractError(prefix + "frozen_source_unavailable")
            for item in [*actual, *frozen]:
                validate_molecular_fact(item, fact_source=fact_source)
            if canonical(actual) != canonical(frozen):
                raise ContractError(prefix + "frozen_source_mismatch")
        except ValueError as error:
            message = {
                "protein_conservation_outcomes": "Return differs from the retained literal conservation facts",
                "protein_phylogeny_outcomes": "Return differs from the retained native phylogeny facts",
            }[fact_source]
            raise ReportBoundaryError(message, code=str(error), field=name) from error


def received_molecular_facts(store, run_id, context, *, fact_source):
    """Consume authenticated child forms and original ancestor prefixes."""
    from .episode_receipts import EpisodeReceipts
    from .episode_return_records import EpisodeReturnRecords
    from .execution_contracts import digest
    from .evolutionary_reference_privacy import molecular_reference_restriction
    tool_name, failure_prefix = _profile(fact_source)
    records = EpisodeReturnRecords(store, run_id, failure_prefix=failure_prefix)
    records.authenticate(context)
    groups, current, prefix, seen = [], context, None, set()
    while True:
        if current.episode_id in seen:
            raise ContractError(failure_prefix + "receipt_lineage_cycle")
        seen.add(current.episode_id)
        if prefix is None:
            attempts = [dict(row) for row in store.db.execute("SELECT decision_index,delivery_ref,child_episode_id,"
                "contract,form FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
                "AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index", (run_id, current.episode_id))]
        else:
            attempts = []
            for frozen in prefix["attempts"]:
                row = store.db.execute("SELECT decision_index,delivery_ref,child_episode_id,contract,form,failure "
                    "FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
                    (run_id, current.episode_id, frozen["decision_index"])).fetchone()
                if (row is None or row["failure"] is not None or row["form"] is None
                        or any(row[name] != frozen[name] for name in ("delivery_ref", "child_episode_id"))
                        or digest(json.loads(row["contract"])) != frozen["contract_sha256"]
                        or digest(json.loads(row["form"])) != frozen["form_sha256"]):
                    raise ContractError(failure_prefix + "received_prefix_conflict")
                attempts.append(dict(row))
        for attempt in attempts:
            schema = json.loads(attempt["contract"])["measurements"]["schema"]
            fields = requested_molecular_fact_fields(schema, fact_source=fact_source)
            if not fields:
                continue
            _, form, authenticated_schema = records._attempt(current, attempt["decision_index"])
            if canonical(schema) != canonical(authenticated_schema):
                raise ContractError(failure_prefix + "received_schema_conflict")
            for name in fields:
                group = form[name]
                if type(group) is not list:
                    raise ContractError(failure_prefix + "received_array_required")
                for value in group:
                    validate_molecular_fact(value, fact_source=fact_source)
                    if molecular_reference_restriction(store, context, value["source_ref"], "source",
                            providers=(tool_name,)) is not True:
                        raise ContractError(failure_prefix + "received_source_not_granted")
                groups.append(group)
        manifest = EpisodeReceipts.read_manifest(store.db, run_id, current.episode_id)
        parent = manifest["parent_episode_id"]
        if parent is None:
            break
        if "received_report_prefix" not in manifest:
            raise ContractError(failure_prefix + "received_prefix_unavailable")
        prefix = manifest["received_report_prefix"]
        parent_context = records.context(parent)
        if current.path[:-1] != parent_context.path:
            raise ContractError(failure_prefix + "received_lineage_conflict")
        current = parent_context
    return merge_molecular_facts(*groups, fact_source=fact_source)


__all__ = ["molecular_fact_sources", "requested_molecular_fact_sources", "requested_molecular_fact_fields",
    "validate_molecular_fact", "merge_molecular_facts", "own_molecular_facts", "frozen_molecular_facts",
    "received_molecular_facts", "validate_frozen_molecular_return"]
