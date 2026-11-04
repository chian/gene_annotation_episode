"""Pure, explicit VDB function kernels over a validated saved v2 sheet.

The accepted 338 contract defines these model-conditional weights.  Target
identity, HSP attribution and source qualification are supplied by the separate
input module.  This module neither populates nor repairs those measurements.
All logarithms retained in the result are finite binary64 base-2 values.  A
positive value outside the linear range is distinct from mathematical zero.
"""
from __future__ import annotations

from copy import deepcopy as _deepcopy
from fractions import Fraction as _Fraction
import hashlib as _hashlib
import json as _json
import math as _math

from . import blast_vdb_function_inputs as _inputs

__all__ = ["validate_blast_vdb_function_model", "calculate_blast_vdb_function_components"]

_PREFIX = "blast_vdb_function_"
_SCOPES = {"whole_sequence", "feature"}
_GROUPINGS = {"target_duplicates_only", "known_source_blocks"}


def _fail(suffix):
    raise ValueError(_PREFIX + suffix)


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and _math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    _fail("finite_json_required")


def _token(value):
    return _json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _key(kind, value):
    return kind + ":" + _hashlib.sha256(_token(value).encode("utf-8")).hexdigest()


def _unique(rows):
    values = {_token(v): v for v in rows}
    return [values[k] for k in sorted(values)]


def _closed(value, fields, code="model_parameters_invalid"):
    if type(value) is not dict or set(value) != set(fields.split()):
        _fail(code)


def _string(value):
    return type(value) is str and bool(value.strip())


def _number(value, *, positive=False):
    if type(value) not in (int, float):
        return False
    try:
        return _math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False


def validate_blast_vdb_function_model(model: dict) -> dict:
    """Return a detached unchanged explicit model; candidates are checked later."""
    result = _copy(model)
    _closed(result, "version temperature_bits grouping_model unknown_source_dependency function_priors census_selection")
    if (result["version"] != "vdb_function_kernel_v1"
            or not _number(result["temperature_bits"], positive=True)
            or type(result["grouping_model"]) is not str or result["grouping_model"] not in _GROUPINGS
            or type(result["unknown_source_dependency"]) is not str
            or result["unknown_source_dependency"] not in {"qualify_separate", "withhold_weights"}):
        _fail("model_parameters_invalid")
    priors = result["function_priors"]
    if priors is not None:
        if type(priors) is not list:
            _fail("model_parameters_invalid")
        seen = set()
        for row in priors:
            _closed(row, "assignment_scope namespace function weight")
            _closed(row["function"], "namespace value")
            if (type(row["assignment_scope"]) is not str or row["assignment_scope"] not in _SCOPES
                    or not _string(row["namespace"]) or not _string(row["function"]["namespace"])
                    or not _string(row["function"]["value"]) or row["function"]["namespace"] != row["namespace"]
                    or not _number(row["weight"])):
                _fail("model_parameters_invalid")
            key = (row["assignment_scope"], row["namespace"], _token(row["function"]))
            if key in seen:
                _fail("model_parameters_invalid")
            seen.add(key)
    if type(result["census_selection"]) is not list:
        _fail("census_selector_invalid")
    seen = set()
    for row in result["census_selection"]:
        _closed(row, "assignment_scope namespace census_key", "census_selector_invalid")
        if (type(row["assignment_scope"]) is not str or row["assignment_scope"] not in _SCOPES
                or not _string(row["namespace"]) or not _string(row["census_key"])):
            _fail("census_selector_invalid")
        key = (row["assignment_scope"], row["namespace"])
        if key in seen:
            _fail("census_selector_invalid")
        seen.add(key)
    return result


class _ArithmeticOutOfRange(ArithmeticError):
    pass


def _finite(value):
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise _ArithmeticOutOfRange from None
    if not _math.isfinite(number):
        raise _ArithmeticOutOfRange
    return number


def _scaled_difference(a, b, temperature):
    # The final quotient may be representable when naive a-b overflows.
    return _finite((_Fraction(a) - _Fraction(b)) / _Fraction(temperature))


def _log_add(a, b):
    return None if a is None or b is None else _finite(_Fraction(a) + _Fraction(b))


def _log_difference(a, b):
    return None if a is None else _finite(_Fraction(a) - _Fraction(b))


def _logsum(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    largest = max(values)
    # This exponentiation is used only to sum finite logs.  The original logs
    # remain intact even when a negligible summand is below binary64 range.
    terms = []
    for value in sorted(values):
        delta = _Fraction(value) - _Fraction(largest)
        terms.append(0.0 if delta < -1075 else 2.0 ** float(delta))
    return _finite(_Fraction(largest) + _Fraction(_math.log2(_math.fsum(terms))))


def _kernel(log_value, unit):
    if log_value is None:
        return dict(value=0.0, log2_value=None, unit=unit, linear_status="zero", reason_code=None)
    log_value = _finite(log_value)
    try:
        value = 2.0 ** log_value
    except OverflowError:
        raise _ArithmeticOutOfRange from None
    if not _math.isfinite(value):
        raise _ArithmeticOutOfRange
    if value == 0.0:
        return dict(value=None, log2_value=log_value, unit=unit, linear_status="underflow",
                    reason_code=_PREFIX + "linear_underflow")
    return dict(value=value, log2_value=log_value, unit=unit, linear_status="available", reason_code=None)


def _missing(unit, reason, *, incompatible=False):
    return dict(value=None, log2_value=None, unit=unit,
                linear_status="incompatible" if incompatible else "unavailable", reason_code=_PREFIX + reason)


def _measure(value, unit, reason=None, *, incompatible=False):
    return dict(value=value, unit=unit, status="available" if value is not None else "incompatible" if incompatible else "unavailable",
                unavailable_reason=None if value is not None else _PREFIX + (reason or "assignment_namespace_unscored"))


def _fraction(numerator, denominator, complete, reason=None):
    available = complete and numerator is not None and denominator is not None and denominator > 0 and reason is None
    return dict(numerator=numerator, denominator=denominator, value=numerator / denominator if available else None,
                unit="fraction", complete=complete, unavailable_reason=None if available else _PREFIX + (reason or "census_zero_conflict"))


def _issue(sheet, suffix, **details):
    return dict(code=_PREFIX + suffix, search_key=_deepcopy(sheet["base_sheet"]["search"]["search_key"]),
                hit_ordinal=None, hsp_ordinal=None, source_pointer=None, details=details)


def _source_provenance(sheet, entity, sample=None):
    source = sheet["base_sheet"]
    refs = []
    for i in entity["member_binding_indices"]:
        member = source["member_bindings"][i]
        if sample is None or member["sample_key"] == sample:
            refs.append(member["provenance"])
    for meta in source["reference_metadata"]:
        if meta["metadata_key"] in entity["metadata_keys"] or sample is not None and meta["entity"]["sample_key"] == sample:
            refs += [meta["source"]] + ([meta["linkage_source"]] if meta["linkage_source"] is not None else [])
    if sample is not None:
        for dataset in source["dataset_records"]:
            refs += [link["source"] for link in dataset["sample_links"] if link["sample_key"] == sample]
    return _unique(refs)


def _partition(entities, dependencies, *, grouping, sources, unresolved=(), parent_verified=None, prefix="observed"):
    """Retain target identities; apply only the selected, separately saved cap."""
    by_identity = {}
    by_entity = {e["entity_key"]: e for e in entities}
    for entity in entities:
        if entity["target_identity"] is not None:
            by_identity.setdefault(_token(entity["target_identity"]), []).append(entity)
    units, entity_unit = [], {}
    for token in sorted(by_identity):
        rows = by_identity[token]
        key = _key("target-unit", [prefix, rows[0]["target_identity"]])
        keys = sorted(e["entity_key"] for e in rows)
        units.append(dict(target_unit_key=key, target_identity=_deepcopy(rows[0]["target_identity"]), entity_keys=keys))
        entity_unit.update({k: key for k in keys})
    unit_map = {u["target_unit_key"]: u for u in units}
    edges = []
    def connect(keys, relation, relation_key, provenance):
        keys = sorted(set(keys))
        # A deterministic spanning star retains the entire sourced relation
        # through its entity list without quadratic redundant graph edges.
        for other in keys[1:]:
            edges.append(dict(edge_key=_key("dependency-edge", [prefix, relation, relation_key, keys[0], other]),
                relation=relation, left_target_unit_key=keys[0], right_target_unit_key=other,
                sources=_deepcopy(_unique(provenance)), used_by_model=grouping == "known_source_blocks"))
    samples = {}
    for entity in entities:
        if entity["sample_relation_status"] == "available":
            for sample in entity["origin_sample_keys"]:
                samples.setdefault(sample, []).append(entity)
    sample_groups = []
    for sample, rows in sorted(samples.items()):
        keys = sorted({entity_unit[e["entity_key"]] for e in rows if e["entity_key"] in entity_unit})
        provenance = _unique([p for e in rows for p in sources(e, sample)])
        sample_groups.append(dict(sample_key=sample, entity_keys=sorted(e["entity_key"] for e in rows), target_unit_keys=keys, sources=provenance))
        connect(keys, "same_origin_sample", sample, provenance)
    parents = {}
    for entity in entities:
        key = entity["entity_key"]
        if (entity["address"]["assignment_scope"] == "feature" and entity["parent_sequence_identity"] is not None
                and key in entity_unit and (parent_verified is None or key in parent_verified)):
            parents.setdefault(_token(entity["parent_sequence_identity"]), []).append(entity)
    for token, rows in sorted(parents.items()):
        connect([entity_unit[e["entity_key"]] for e in rows], "same_parent_sequence", token,
                [p for e in rows for p in sources(e, None)])
    addresses = {_token(e["address"]): e["entity_key"] for e in entities}
    unresolved = set(unresolved)
    for record in sorted(dependencies, key=lambda r: r["dependency_key"]):
        keys = [addresses.get(_token(a)) for a in record["entities"]]
        if record["dependency_key"] in unresolved or any(k not in entity_unit for k in keys):
            unresolved.add(record["dependency_key"])
            continue
        connect([entity_unit[k] for k in keys], record["relation"], record["dependency_key"], record["sources"])
    parents = {k: k for k in unit_map}
    def find(key):
        while key != parents[key]:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key
    if grouping == "known_source_blocks":
        for edge in edges:
            a, b = find(edge["left_target_unit_key"]), find(edge["right_target_unit_key"])
            parents[max(a, b)] = min(a, b)
    components = {}
    for key in sorted(unit_map):
        components.setdefault(find(key), []).append(key)
    groups, entity_group = [], {}
    for target_keys in components.values():
        entity_keys = sorted(k for target in target_keys for k in unit_map[target]["entity_keys"])
        key = _key("model-group", [prefix, grouping, target_keys])
        used = sorted(e["edge_key"] for e in edges if e["used_by_model"]
                      and e["left_target_unit_key"] in target_keys and e["right_target_unit_key"] in target_keys)
        groups.append(dict(group_key=key, target_unit_keys=target_keys, entity_keys=entity_keys, graph_edge_keys=used))
        entity_group.update({k: key for k in entity_keys})
    return dict(units=sorted(units, key=lambda u: u["target_unit_key"]), edges=sorted(edges, key=lambda e: e["edge_key"]),
                samples=sample_groups, groups=sorted(groups, key=lambda g: g["group_key"]),
                unknown_samples=sorted(e["entity_key"] for e in entities if e["sample_relation_status"] != "available"),
                unresolved=sorted(unresolved), entity_unit=entity_unit, entity_group=entity_group, entities=by_entity)


def _observed_partition(sheet, model):
    unresolved = [r["record_key"] for r in sheet["link_results"] if r["record_kind"] == "dependency" and r["status"] != "available"]
    return _partition(sheet["entities"], sheet["dependency_records"], grouping=model["grouping_model"],
                      sources=lambda e, s: _source_provenance(sheet, e, s), unresolved=unresolved)


def _census_result(sheet, census, model):
    link = next(r for r in sheet["link_results"] if r["record_kind"] == "census" and r["record_key"] == census["census_key"])
    issues = _deepcopy(link["issues"])
    invalid_target, invalid_parent = set(), set()
    for issue in issues:
        detail = issue["details"]
        entity_key = detail.get("census_entity_key")
        if entity_key is not None and issue["code"] == _PREFIX + "census_membership_unverified":
            entity = next((e for e in census["entities"] if e["entity_key"] == entity_key), None)
            normalization = detail.get("normalization")
            if entity and (normalization == entity["target_identity"]["representation"] or detail.get("coding_proof_conflict")):
                invalid_target.add(entity_key)
            if normalization == "full_member_nt_v1" or detail.get("parent_identity_conflict"):
                invalid_parent.add(entity_key)
        if detail.get("conflicting_identity_proofs"):
            invalid_target.add(entity_key); invalid_parent.add(entity_key)
    entities = _deepcopy(census["entities"])
    for entity in entities:
        if entity["entity_key"] in invalid_target:
            entity["target_identity"] = None
    parent_verified = {p["entity_key"] for p in census["identity_proofs"] if p["normalization"] == "full_member_nt_v1"} - invalid_parent
    unresolved = {i["details"]["dependency_key"] for i in issues if "dependency_key" in i["details"]}
    def sources(entity, sample):
        key = entity["entity_key"]
        return _unique([entity["source"], *entity["function_assignment_sources"],
            *[p[f] for p in census["identity_proofs"] if p["entity_key"] == key for f in ("sequence_source", "linkage_source")]])
    partition = _partition(entities, census["dependency_records"], grouping=model["grouping_model"], sources=sources,
                           unresolved=unresolved, parent_verified=parent_verified, prefix="census:" + census["census_key"])
    enumeration = census["enumeration"]
    addresses = {_token(e["address"]) for e in entities}
    complete = (enumeration["complete"] and enumeration["pagination_complete"] is True
                and enumeration["reported_total"] == len(entities) == len(addresses)
                and not invalid_target and not invalid_parent)
    cap_unknown = bool(partition["unknown_samples"] or partition["unresolved"])
    correction = link["status"] == "available"
    if model["grouping_model"] == "known_source_blocks" and cap_unknown:
        issues.append(_issue(sheet, "dependency_unknown", census_key=census["census_key"],
                             entity_keys=partition["unknown_samples"], dependency_keys=partition["unresolved"]))
        if model["unknown_source_dependency"] == "withhold_weights":
            correction = False
    status = link["status"] if not correction else "available"
    if status == "available" and not correction:
        status = "unavailable"
    groups = []
    for group in partition["groups"]:
        functions = _unique([f for key in group["entity_keys"] for f in partition["entities"][key]["functions"]
                             if f["namespace"] == census["function_namespace"]])
        groups.append({k: _deepcopy(group[k]) for k in ("group_key", "target_unit_keys", "entity_keys")} | {"functions": functions})
    unit = "target_unit" if model["grouping_model"] == "target_duplicates_only" else "dependence_block"
    functions = _unique([f for e in entities for f in e["functions"] if f["namespace"] == census["function_namespace"]])
    function_counts = []
    for function in functions:
        count = sum(function in g["functions"] for g in groups)
        function_counts.append(dict(function=function, count=_measure(count, unit),
            fraction=_fraction(count, len(groups), complete, None if complete else "census_partial")))
    by_address = {}
    for entity in entities:
        by_address.setdefault(_token(entity["address"]), []).append(entity)
    observed_links = []
    for entity in sheet["entities"]:
        matches = by_address.get(_token(entity["address"]), [])
        if (entity["eligible_hsp_rows"] and len(matches) == 1
                and matches[0]["target_identity"] == entity["target_identity"]
                and matches[0]["parent_sequence_identity"] == entity["parent_sequence_identity"]
                and matches[0]["entity_key"] in partition["entity_group"]):
            observed_links.append(dict(entity_key=entity["entity_key"], census_entity_key=matches[0]["entity_key"],
                                       group_key=partition["entity_group"][matches[0]["entity_key"]]))
    result = dict(census_key=census["census_key"], status=status, assignment_scope=census["assignment_scope"],
        namespace=census["function_namespace"], enumeration_complete=complete, correction_available=correction,
        base_entity_count=_measure(len(addresses), "member_instance" if census["assignment_scope"] == "whole_sequence" else "feature_instance"),
        target_unit_count=_measure(len(partition["units"]), "target_unit"), model_group_count=_measure(len(groups), unit),
        function_counts=function_counts,
        target_units=[{k: _deepcopy(u[k]) for k in ("target_unit_key", "entity_keys")} for u in partition["units"]],
        model_groups=groups, observed_entity_links=sorted(observed_links, key=lambda r: r["entity_key"]), issues=_unique(issues))
    return result, partition, cap_unknown


def _report_complete(sheet):
    search = sheet["base_sheet"]["search"]
    reporting = search["reporting"]
    if (reporting["native_returncode"] != 0 or reporting["producer_complete"] is not True
            or reporting["requested_hit_limit"] is not None or reporting["requested_hsp_limit"] is not None
            or not reporting["native_hit_array_present"] or search["issues"]):
        return False
    subjects, hsps = sheet["base_components"]["subjects"], sheet["base_components"]["hsps"]
    if reporting["native_hit_count"] != len(subjects):
        return False
    if search["normalized"]["format"] == "json2":
        hits = search["native"]["search"].get("hits")
        if type(hits) is not list or len(hits) != len(subjects):
            return False
        for i, hit in enumerate(hits):
            if type(hit) is not dict or type(hit.get("hsps")) is not list:
                return False
            if {h["row_key"]["hsp_ordinal"] for h in hsps if h["row_key"]["hit_ordinal"] == i} != set(range(len(hit["hsps"]))):
                return False
    return sheet["base_components"]["status"] not in {"unavailable", "incompatible"}


def _buckets(sheet, scope, namespace, partition, entity_alias=None):
    """Each literal function keeps only its own qualified HSP maxima."""
    entities = {e["entity_key"]: e for e in sheet["entities"] if e["address"]["assignment_scope"] == scope}
    entity_alias = entity_alias or {k: k for k in entities}
    available = [o for o in sheet["observations"] if o["entity_key"] in entities and o["qualification"] == "available"]
    assigned = [o for o in available if o["function"] is not None and o["function"]["namespace"] == namespace]
    entity_unit = {k: partition["entity_unit"][v] for k, v in entity_alias.items() if v in partition["entity_unit"]}
    entity_group = {k: partition["entity_group"][v] for k, v in entity_alias.items() if v in partition["entity_group"]}
    labels = {}
    for observation in assigned:
        key = observation["entity_key"]
        if key in entity_unit:
            labels.setdefault(entity_unit[key], set()).add(_token(observation["function"]))
    buckets = {}
    for observation in available:
        entity_key = observation["entity_key"]
        if entity_key not in entity_group:
            continue
        function = observation["function"]
        if function is None:
            if labels.get(entity_unit[entity_key]):
                continue
        elif function["namespace"] != namespace:
            continue
        buckets.setdefault(entity_group[entity_key], {}).setdefault(_token(function), []).append(observation)
    groups = []
    for group in partition["groups"]:
        # Observed strata never include the other assignment scope. Census
        # groups can include unreturned bridge entities but receive no HSPs.
        if not any(e in entity_group and entity_group[e] == group["group_key"] for e in entities):
            if entity_alias and not any(k in entity_alias.values() for k in group["entity_keys"]):
                continue
        if group["entity_keys"] and partition["entities"][group["entity_keys"][0]]["address"]["assignment_scope"] != scope:
            continue
        contributions = []
        for token, observations in sorted(buckets.get(group["group_key"], {}).items()):
            best = max(o["native_bit_score"]["value"] for o in observations)
            function = observations[0]["function"]
            raw = observations if function is None else [o for o in sheet["observations"]
                if o["entity_key"] in entity_group and entity_group[o["entity_key"]] == group["group_key"] and o["function"] == function]
            contributions.append(dict(function=_deepcopy(function), best_bit_score=_measure(best, "bits"),
                observation_keys=sorted(o["observation_key"] for o in raw),
                winning_observation_keys=sorted(o["observation_key"] for o in observations if o["native_bit_score"]["value"] == best),
                within_group_kernel=_missing("kernel_weight", "assignment_namespace_unscored"),
                split_denominator=_missing("kernel_weight", "assignment_namespace_unscored"),
                function_baseline_mass=_missing("function_mass", "assignment_namespace_unscored"),
                global_baseline_mass=_missing("kernel_weight", "assignment_namespace_unscored")))
        own = [i for o in sheet["observations"] if o["entity_key"] in entity_group
               and entity_group[o["entity_key"]] == group["group_key"] and o["function"] is not None
               and o["function"]["namespace"] == namespace for i in o["issues"]]
        groups.append(_deepcopy(group) | dict(function_contributions=contributions, issues=_unique(own)))
    return groups, assigned, labels, entity_unit


def _mass(groups, temperature):
    assigned_scores = [c["best_bit_score"]["value"] for g in groups for c in g["function_contributions"] if c["function"] is not None]
    all_scores = [c["best_bit_score"]["value"] for g in groups for c in g["function_contributions"]]
    largest_function = max(assigned_scores) if assigned_scores else None
    largest_all = max(all_scores) if all_scores else None
    function_logs, assigned_global, unknown_global = {}, [], []
    for group in groups:
        contributions = group["function_contributions"]
        if not contributions:
            continue
        largest = max(c["best_bit_score"]["value"] for c in contributions)
        logs = [_scaled_difference(c["best_bit_score"]["value"], largest, temperature) for c in contributions]
        denominator = _logsum(logs)
        for contribution, log in zip(contributions, logs):
            score = contribution["best_bit_score"]["value"]
            global_log = _log_difference(_scaled_difference(score, largest_all, temperature), denominator)
            contribution["within_group_kernel"] = _kernel(log, "kernel_weight")
            contribution["split_denominator"] = _kernel(denominator, "kernel_weight")
            contribution["global_baseline_mass"] = _kernel(global_log, "kernel_weight")
            function = contribution["function"]
            if function is None:
                # Unknown mass has no assigned-function baseline meaning.
                unknown_global.append(global_log)
            else:
                function_log = _log_difference(_scaled_difference(score, largest_function, temperature), denominator)
                contribution["function_baseline_mass"] = _kernel(function_log, "function_mass")
                function_logs.setdefault(_token(function), []).append(function_log)
                assigned_global.append(global_log)
    return dict(masses={k: _logsum(v) for k, v in function_logs.items()},
                assigned=_logsum(assigned_global), unknown=_logsum(unknown_global),
                total=_logsum([*assigned_global, *unknown_global]), largest_function=largest_function, largest_all=largest_all)


def _priors(model, candidates):
    expected = {(scope, namespace, _token(function)) for (scope, namespace), functions in candidates.items() for function in functions}
    priors = model["function_priors"]
    if priors is None:
        return {key: { _token(f): -_math.log2(len(fs)) for f in fs} for key, fs in candidates.items()}
    actual = {(p["assignment_scope"], p["namespace"], _token(p["function"])) for p in priors}
    if actual != expected:
        _fail("prior_candidate_set_mismatch")
    result = {}
    for key, functions in candidates.items():
        rows = [p for p in priors if (p["assignment_scope"], p["namespace"]) == key]
        if functions and not any(p["weight"] > 0 for p in rows):
            _fail("model_parameters_invalid")
        logs = {_token(p["function"]): _math.log2(p["weight"]) if p["weight"] > 0 else None for p in rows}
        denominator = _logsum(logs.values())
        result[key] = {k: _log_difference(v, denominator) for k, v in logs.items()}
    return result


def _statistical_failure(stratum, reason):
    """Withhold derived statistics, retaining native maxima, counts and groups."""
    for name in ("unknown_reference_kernel_mass", "assigned_reference_kernel_mass", "total_reference_kernel_mass",
                 "unknown_reference_kernel_fraction", "conditional_weight_denominator", "representation_adjusted_weight_denominator"):
        stratum[name] = _missing(stratum[name]["unit"], reason)
    for function in stratum["functions"]:
        for name, value in list(function.items()):
            if type(value) is dict and "linear_status" in value:
                function[name] = _missing(value["unit"], reason)
    for group in stratum["groups"]:
        for contribution in group["function_contributions"]:
            for name in ("within_group_kernel", "split_denominator", "function_baseline_mass", "global_baseline_mass"):
                contribution[name] = _missing(contribution[name]["unit"], reason)


def _underflow_issues(sheet, value, path=""):
    issues = []
    if type(value) is dict:
        if value.get("linear_status") == "underflow":
            issues.append(_issue(sheet, "linear_underflow", component_pointer=path, log2_value=value["log2_value"]))
        else:
            for key, item in value.items():
                if key != "issues":
                    issues += _underflow_issues(sheet, item, path + "/" + key)
    elif type(value) is list:
        for index, item in enumerate(value):
            issues += _underflow_issues(sheet, item, path + "/" + str(index))
    return issues


def _stratum(sheet, model, scope, namespace, partition, groups, assigned, labels, entity_unit, prior_logs, selected_census):
    base = sheet["base_components"]
    entities = [e for e in sheet["entities"] if e["address"]["assignment_scope"] == scope]
    eligible = [e for e in entities if e["eligible_hsp_rows"]]
    functions = _unique([o["function"] for o in assigned])
    assignment_keys = {a["assignment_key"] for a in sheet["assignment_records"]
                       if a["assignment_scope"] == scope and a["function"]["namespace"] == namespace}
    observations = [o for o in sheet["observations"] if o["entity_key"] in {e["entity_key"] for e in entities}
                    and o["assignment_key"] in assignment_keys]
    links = [l for l in sheet["link_results"] if l["record_kind"] == "assignment" and l["record_key"] in assignment_keys]
    issues = [i for e in entities for i in e["issues"]] + [i for o in observations for i in o["issues"]] + [i for l in links for i in l["issues"]]
    assigned_entities = {o["entity_key"] for o in assigned}
    missing_annotation = sorted(e["entity_key"] for e in eligible if e["entity_key"] not in assigned_entities)
    if missing_annotation:
        issues.append(_issue(sheet, "assignment_namespace_unscored", assignment_scope=scope, namespace=namespace,
                             entity_keys=missing_annotation, target_unit_keys=sorted({entity_unit[k] for k in missing_annotation if k in entity_unit})))
    unknown_origins = { _token(o["row_key"]) for o in base["membership"]["origins"] if o["status"] != "available"}
    relevant_dependencies = {d["dependency_key"] for d in sheet["dependency_records"]
                             if any(a["assignment_scope"] == scope for a in d["entities"])}
    unresolved = sorted(relevant_dependencies & set(partition["unresolved"]))
    unknown_samples = [e["entity_key"] for e in eligible if e["sample_relation_status"] != "available"]
    dependency_complete = not unresolved and not unknown_samples
    report_complete = _report_complete(sheet)
    metadata_complete = (len(eligible) == len(entities) and not unknown_origins and not missing_annotation
                         and all(o["qualification"] == "available" for o in observations)
                         and all(l["status"] == "available" for l in links))
    if not report_complete:
        issues.append(_issue(sheet, "native_output_partial", assignment_scope=scope, namespace=namespace))
    cap = model["grouping_model"] == "known_source_blocks"
    if not dependency_complete:
        issues.append(_issue(sheet, "dependency_unknown", assignment_scope=scope, namespace=namespace,
                             entity_keys=sorted(unknown_samples), dependency_keys=unresolved))
    count_units = {u["target_unit_key"] for u in partition["units"] if u["target_identity"]["assignment_scope"] == scope}
    unit_eligible = {entity_unit[e["entity_key"]] for e in eligible if e["entity_key"] in entity_unit}
    rate_unit = "function_mass_per_dependence_block" if cap else "function_mass_per_target_unit"
    census_result, census_partition, census_cap_unknown = selected_census if selected_census else (None, None, False)
    census_reason = "census_missing" if census_result is None else (
        census_result["issues"][0]["code"].removeprefix(_PREFIX) if not census_result["correction_available"] and census_result["issues"] else None)
    if census_result and not census_result["correction_available"]:
        issues += census_result["issues"]
    score_values = [c["best_bit_score"]["value"] for g in groups for c in g["function_contributions"]]
    assigned_scores = [c["best_bit_score"]["value"] for g in groups for c in g["function_contributions"] if c["function"] is not None]
    result = dict(assignment_scope=scope, namespace=namespace,
        query_axis_kind=sheet["base_sheet"]["query_binding"]["axis_kind"] if sheet["base_sheet"]["query_binding"] else (
            "pssm_master" if sheet["base_sheet"]["search"]["program_context"]["query_kind"] == "pssm" else "sequence"),
        grouping_model=model["grouping_model"], status="complete",
        counts=dict(source_entities=len(entities), eligible_entities=len(eligible), excluded_entities=len(entities)-len(eligible),
            eligible_hsps=len({_token(r) for e in eligible for r in e["eligible_hsp_rows"]}), duplicate_target_units=len(count_units),
            model_groups=len(groups), multilabel_target_units=sum(len(v) > 1 for v in labels.values()),
            unassigned_target_units=len(unit_eligible - labels.keys()), unscored_entities=len(entities)-len(eligible),
            unknown_origin_subjects=len(unknown_origins), unresolved_sample_entities=len(unknown_samples)),
        native_reporting=_deepcopy(sheet["base_sheet"]["search"]["reporting"]), report_complete=report_complete,
        metadata_complete=metadata_complete, dependency_complete=dependency_complete,
        largest_assigned_bit_score=_measure(max(assigned_scores) if assigned_scores else None, "bits"),
        largest_all_bit_score=_measure(max(score_values) if score_values else None, "bits"), groups=groups, functions=[],
        unknown_reference_kernel_mass=_missing("kernel_weight", "assignment_namespace_unscored"),
        assigned_reference_kernel_mass=_missing("kernel_weight", "assignment_namespace_unscored"),
        total_reference_kernel_mass=_missing("kernel_weight", "assignment_namespace_unscored"),
        unknown_reference_kernel_fraction=_missing("fraction", "assignment_namespace_unscored"),
        conditional_weight_denominator=_missing("function_mass", "assignment_namespace_unscored"),
        representation_adjusted_weight_denominator=_missing(rate_unit, census_reason or "assignment_namespace_unscored"),
        census_key=census_result["census_key"] if census_result else None, issues=[])
    qualified_census = bool(census_result and census_result["correction_available"])
    for function in functions:
        own = [o for o in assigned if o["function"] == function]
        census_count = next((r for r in census_result["function_counts"] if r["function"] == function), None) if qualified_census else None
        unit = "dependence_block" if cap else "target_unit"
        reason = census_reason or "census_function_missing"
        row = dict(function=function, assignment_keys=sorted({o["assignment_key"] for o in own}),
            group_keys=sorted(g["group_key"] for g in groups if any(c["function"] == function for c in g["function_contributions"])),
            source_entity_count=len({o["entity_key"] for o in own}), target_unit_count=len({entity_unit[o["entity_key"]] for o in own}),
            function_mass=_missing("function_mass", "assignment_namespace_unscored"), prior=_missing("fraction", "assignment_namespace_unscored"),
            prior_weighted_mass=_missing("function_mass", "assignment_namespace_unscored"),
            conditional_function_weight=_missing("fraction", "assignment_namespace_unscored"),
            census_function_unit_count=_deepcopy(census_count["count"]) if census_count else _measure(None, unit, reason),
            census_total_unit_count=_deepcopy(census_result["model_group_count"]) if qualified_census else _measure(None, unit, reason),
            census_function_fraction=_deepcopy(census_count["fraction"]) if census_count else _fraction(None, None, False, reason),
            census_partition_function_mass=_missing("function_mass", reason),
            census_partition_prior_weighted_mass=_missing("function_mass", reason), representation_rate=_missing(rate_unit, reason),
            representation_adjusted_function_weight=_missing("fraction", reason), issues=[])
        result["functions"].append(row)
    if base["status"] in {"no_reported_hits", "unavailable", "incompatible"}:
        result["status"] = base["status"]
        reason = "base_source_conflict" if base["status"] == "incompatible" else "base_source_unavailable"
        if base["status"] != "no_reported_hits":
            _statistical_failure(result, reason)
            result["issues"] = _unique([*issues, _issue(sheet, reason)])
            return result
    elif not functions:
        result["status"] = "no_eligible_functions"
    elif (not report_complete or not metadata_complete or cap and not dependency_complete
          or census_result and (not qualified_census or cap and census_cap_unknown)):
        result["status"] = "partial"
    if cap and not dependency_complete and model["unknown_source_dependency"] == "withhold_weights":
        _statistical_failure(result, "dependency_unknown")
        result["status"] = "unavailable"
        result["issues"] = _unique(issues)
        return result
    try:
        masses = _mass(groups, model["temperature_bits"])
        for name, key in (("unknown_reference_kernel_mass", "unknown"), ("assigned_reference_kernel_mass", "assigned"), ("total_reference_kernel_mass", "total")):
            result[name] = _kernel(masses[key], "kernel_weight")
        if masses["total"] is not None:
            result["unknown_reference_kernel_fraction"] = _kernel(_log_difference(masses["unknown"], masses["total"]), "fraction")
        weighted = {k: _log_add(v, prior_logs[k]) for k, v in masses["masses"].items()}
        denominator = _logsum(weighted.values())
        result["conditional_weight_denominator"] = _kernel(denominator, "function_mass")
        for row in result["functions"]:
            key = _token(row["function"])
            row["function_mass"] = _kernel(masses["masses"][key], "function_mass")
            row["prior"] = _kernel(prior_logs[key], "fraction")
            row["prior_weighted_mass"] = _kernel(weighted[key], "function_mass")
            row["conditional_function_weight"] = _kernel(_log_difference(weighted[key], denominator), "fraction")
        if qualified_census:
            aliases = {r["entity_key"]: r["census_entity_key"] for r in census_result["observed_entity_links"]}
            cg, _, _, _ = _buckets(sheet, scope, namespace, census_partition, aliases)
            cm = _mass(cg, model["temperature_bits"])
            rates = {}
            for row in result["functions"]:
                key = _token(row["function"])
                count = row["census_function_unit_count"]["value"]
                if count is None or count <= 0 or key not in cm["masses"]:
                    # The input link normally catches this; retain a closed
                    # scientific failure if no actual grouped count exists.
                    qualified_census = False
                    issues.append(_issue(sheet, "census_zero_conflict" if count == 0 else "census_function_missing", census_key=census_result["census_key"], function=row["function"]))
                    break
                rates[key] = _log_difference(_log_add(prior_logs[key], cm["masses"][key]), _math.log2(count))
            if qualified_census:
                rate_total = _logsum(rates.values())
                result["representation_adjusted_weight_denominator"] = _kernel(rate_total, rate_unit)
                for row in result["functions"]:
                    key = _token(row["function"])
                    row["census_partition_function_mass"] = _kernel(cm["masses"][key], "function_mass")
                    row["census_partition_prior_weighted_mass"] = _kernel(_log_add(prior_logs[key], cm["masses"][key]), "function_mass")
                    row["representation_rate"] = _kernel(rates[key], rate_unit)
                    row["representation_adjusted_function_weight"] = _kernel(_log_difference(rates[key], rate_total), "fraction")
    except _ArithmeticOutOfRange:
        _statistical_failure(result, "kernel_arithmetic_out_of_range")
        result["status"] = "unavailable"
        issues.append(_issue(sheet, "kernel_arithmetic_out_of_range", assignment_scope=scope, namespace=namespace,
                             temperature_bits=model["temperature_bits"]))
    issues += _underflow_issues(sheet, result)
    result["issues"] = _unique(issues)
    return result


def calculate_blast_vdb_function_components(sheet: dict, *, model: dict) -> dict:
    """Calculate the selected model from an actual validated, saved v2 sheet."""
    sheet = _inputs.validate_blast_vdb_function_sheet(sheet)
    model = validate_blast_vdb_function_model(model)
    censuses = {c["census_key"]: c for c in sheet["census_records"]}
    selectors = {}
    for selection in model["census_selection"]:
        census = censuses.get(selection["census_key"])
        if census is None or census["assignment_scope"] != selection["assignment_scope"] or census["function_namespace"] != selection["namespace"]:
            _fail("census_selector_invalid")
        selectors[(selection["assignment_scope"], selection["namespace"])] = selection["census_key"]
    strata_keys = {(a["assignment_scope"], a["function"]["namespace"]) for a in sheet["assignment_records"] if a["assignment_scope"] in _SCOPES} | selectors.keys()
    partition = _observed_partition(sheet, model)
    census_values = {key: _census_result(sheet, c, model) for key, c in sorted(censuses.items())}
    prepared = {key: _buckets(sheet, *key, partition) for key in sorted(strata_keys)}
    candidates = {key: _unique([o["function"] for o in values[1]]) for key, values in prepared.items()}
    prior_logs = _priors(model, candidates)
    strata = [_stratum(sheet, model, *key, partition, *values, prior_logs[key], census_values.get(selectors.get(key)))
              for key, values in prepared.items()]
    base_status = sheet["base_components"]["status"]
    statuses = {s["status"] for s in strata}
    if base_status in {"no_reported_hits", "unavailable", "incompatible"}:
        status = base_status
    elif not strata or statuses == {"no_eligible_functions"}:
        status = "no_eligible_functions"
    elif statuses == {"complete"}:
        status = "complete"
    elif statuses <= {"unavailable", "incompatible"}:
        status = "incompatible" if statuses == {"incompatible"} else "unavailable"
    else:
        status = "partial"
    assumptions = ["target_duplicate_equivalence", "uniform_candidate_prior" if model["function_priors"] is None else "explicit_candidate_prior"]
    unused = ["taxonomy", "target_compatibility", "assembly_quality", "annotation_evidence", "native_evalue", "alignment_coverage", "alignment_identity"]
    if model["grouping_model"] == "known_source_blocks":
        assumptions.append("source_block_mass_cap")
        if model["unknown_source_dependency"] == "qualify_separate" and (partition["unknown_samples"] or partition["unresolved"]):
            assumptions.append("unknown_dependency_separate")
    else:
        unused += ["sample_relations", "explicit_dependency_relations"]
    if any(not s["report_complete"] for s in strata):
        assumptions.append("conditional_on_retained_output")
    if any(census_values[key][0]["correction_available"] for key in selectors.values()):
        assumptions.append("complete_matching_census")
    issues = _unique([*sheet["issues"], *[i for s in strata for i in s["issues"]],
                      *[i for c, _, _ in census_values.values() for i in c["issues"]]])
    return dict(schema="blast_vdb_function_components_v2", search_key=_deepcopy(sheet["base_sheet"]["search"]["search_key"]),
        status=status, model=model, calibrated_annotation_probability=False, strata=strata,
        assignment_results=_deepcopy([r for r in sheet["link_results"] if r["record_kind"] == "assignment"]),
        dependency_measurements=dict(target_units=partition["units"], edges=partition["edges"], sample_groups=partition["samples"],
                                     unknown_sample_entity_keys=partition["unknown_samples"], unresolved_dependency_keys=partition["unresolved"]),
        census_results=[v[0] for v in census_values.values()], issues=issues,
        retained_measurements_not_used=unused, assumptions=assumptions)
