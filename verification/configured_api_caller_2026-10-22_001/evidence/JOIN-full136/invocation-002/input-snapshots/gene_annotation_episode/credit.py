"""Current, source-bound interpretation credit; never an annotation verdict.

The user chose a softened hypervolume across evidence dimensions and equal
initial weights for the five axes. The categorical proxy weights, epsilon,
scale and input weights below remain versioned implementation settings, not
measured biological accuracy or user-approved numerical constants. Scientific episodes own interpretation,
applicability, dispositions and coherent alternative sets. This projection
does not select an annotation, accept work, or stop an episode.

Fetched material, tool activity, candidate counts and model confidence earn no
credit by themselves. Credit operands are current source-bound interpretations
of actual observations. Corrections can therefore change credit without a new
measurement, including a real signed decrease when earlier support was wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
import json
import sqlite3
import hashlib
from itertools import chain, islice
from numbers import Real
from typing import Mapping

from .sequence_mapping import map_interval
from .finding_validity import FindingValidity
from .domain import ContractError


AXES = ("empirical", "comparative", "mechanistic", "biological_context",
        "discrimination")
PROJECTION_VERSION = "source_bound_coherent_interpretation_coverage_v7"
FORMULA_VERSION = "offset_normalized_product_hypervolume_v1"
LEGACY_INTEGRATION = 'partition_product_sum_v1'
STABLE_INTEGRATION = 'equal_component_integer_mass_v1'


def _number(value, name, *, minimum=0., maximum=None):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not math.isfinite(result) or result < minimum or (
            maximum is not None and result > maximum):
        raise ValueError(f"{name} is outside its numeric domain")
    return result


def _pairs(value, name):
    if isinstance(value, Mapping):
        value = value.items()
    result = tuple((str(key), _number(number, name)) for key, number in value)
    if len({key for key, _ in result}) != len(result):
        raise ValueError(f"{name} keys must be unique")
    return result


@dataclass(frozen=True)
class CreditPolicy:
    """Caller-owned frozen operational proxy settings, persisted with a run."""

    axis_weights: tuple = tuple((axis, 1.) for axis in AXES)
    epsilon: float = .25
    scale: float = 100.
    applicability_weights: tuple = (("direct", 1.), ("transfer", .6),
        ("contextual", .35), ("scope_limited", .2), ("incomparable", 0.))
    relation_weights: tuple = (("strengthens", 1.), ("weakens", 1.),
        ("mixed", .5), ("does_not_discriminate", 0.))
    unresolved_factor: float = .5
    target_weights: tuple = ()
    observation_axes: tuple = (
        ("assay_report", "empirical"),
        ("biochemical_assay", "empirical"),
        ("genetic_phenotype", "empirical"),
        ("growth_assay", "empirical"),
        ("read_support", "empirical"),
        ("alignment", "comparative"),
        ("profile_match", "comparative"),
        ("comparison", "comparative"),
        ("gene_prediction", "comparative"),
        ("structure_match", "mechanistic"),
        ("mechanism", "mechanistic"),
        ("reaction_context", "mechanistic"),
        ("context_measurement", "biological_context"),
        ("context", "biological_context"),
        ("taxonomy_assignment", "biological_context"),
        ("sequence_composition", "biological_context"),
    )

    def __post_init__(self):
        for name in ("axis_weights", "applicability_weights", "relation_weights",
                     "target_weights"):
            object.__setattr__(self, name, _pairs(getattr(self, name), name))
        if set(dict(self.axis_weights)) != set(AXES):
            raise ValueError("axis_weights must declare the fixed evidence axes")
        if not any(weight > 0 for _, weight in self.axis_weights):
            raise ValueError("at least one evidence axis needs positive weight")
        if set(dict(self.applicability_weights)) != {
                "direct", "transfer", "contextual", "scope_limited", "incomparable"}:
            raise ValueError("applicability_weights must declare every semantic value")
        if set(dict(self.relation_weights)) != {
                "strengthens", "weakens", "mixed", "does_not_discriminate"}:
            raise ValueError("relation_weights must declare every semantic value")
        for name in ("applicability_weights", "relation_weights"):
            if any(weight > 1 for _, weight in getattr(self, name)):
                raise ValueError(f"{name} must lie in [0,1]")
        epsilon = _number(self.epsilon, "epsilon", maximum=1)
        if not 0 < epsilon < 1:
            raise ValueError("epsilon must lie strictly between zero and one")
        object.__setattr__(self, "epsilon", epsilon)
        scale = _number(self.scale, "scale")
        if not scale > 0:
            raise ValueError("scale must be positive")
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "unresolved_factor", _number(
            self.unresolved_factor, "unresolved_factor", maximum=1))
        observation_axes = tuple((str(kind), str(axis))
            for kind, axis in (self.observation_axes.items()
                if isinstance(self.observation_axes, Mapping) else self.observation_axes))
        if len(dict(observation_axes)) != len(observation_axes):
            raise ValueError("observation kind mappings must be unique")
        if any(axis not in AXES[:-1] for _, axis in observation_axes):
            raise ValueError("observation mappings must name an evidence axis")
        # These records have no scientific evidence meaning by themselves.
        if {kind for kind, _ in observation_axes} & {
                "source_content", "source_annotation", "coordinate_mapping"}:
            raise ValueError("uninterpreted sources and coordinate transforms are not evidence axes")
        object.__setattr__(self, "observation_axes", observation_axes)

    def as_record(self):
        return {"axis_weights": dict(self.axis_weights),
                "epsilon": self.epsilon, "scale": self.scale,
                "applicability_weights": dict(self.applicability_weights),
                "relation_weights": dict(self.relation_weights),
                "unresolved_factor": self.unresolved_factor,
                "target_weights": dict(self.target_weights),
                "observation_axes": [list(pair) for pair in self.observation_axes]}

    @classmethod
    def from_record(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("credit policy must be a mapping")
        unknown = set(value) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown credit policy settings: {sorted(unknown)}")
        return cls(**dict(value))


def softened_hypervolume(evidence: Mapping[str, Real], policy=None):
    """A continuous proxy in [0,1]; absent axes soften, never veto, progress."""
    policy = CreditPolicy() if policy is None else CreditPolicy.from_record(policy)
    unknown = set(evidence) - set(AXES)
    if unknown:
        raise ValueError(f"unknown evidence dimensions: {sorted(unknown)}")
    weights = dict(policy.axis_weights)
    exponent = sum(weights.values())
    baseline = policy.epsilon ** exponent
    volume = math.prod((policy.epsilon + (1-policy.epsilon) *
        _number(evidence.get(axis, 0), axis, maximum=1)) ** weights[axis]
        for axis in AXES)
    # Limits handle tiny floating-point cancellation, not scientific scores.
    return min(1., max(0., (volume-baseline)/(1-baseline)))


@dataclass(frozen=True)
class CreditProjection:
    credit: float
    axis_components: Mapping
    targets: tuple
    source_contributions: tuple
    policy: CreditPolicy = field(default_factory=CreditPolicy)
    scope: Mapping = field(default_factory=dict)
    detail_pages: Mapping = field(default_factory=dict)
    inactive_dependencies: tuple = ()
    integration_arithmetic: str | None = None
    interpretation: str | None = None

    def as_record(self):
        record = {"credit": self.credit, "axis_components": dict(self.axis_components),
                "targets": list(self.targets),
                "source_contributions": list(self.source_contributions),
                "policy": self.policy.as_record(), "scope": dict(self.scope),
                "projection_version": PROJECTION_VERSION,
                "formula_version": FORMULA_VERSION,
                "interpretation": self.interpretation or "operational_evidence_progress_proxy_not_biological_accuracy"}
        if self.detail_pages:
            record["detail_pages"] = dict(self.detail_pages)
            record["inactive_dependencies"] = list(self.inactive_dependencies)
        if self.integration_arithmetic is not None:
            record['integration_arithmetic'] = self.integration_arithmetic
        return record


def _merge(segments):
    result = []
    for start, end in sorted(segments):
        if start == end:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def _intersection(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        start, end = max(left[i][0], right[j][0]), min(left[i][1], right[j][1])
        if start < end:
            result.append((start, end))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return result


def _interpretations(coherent_set):
    value = coherent_set.get("interpretations", ())
    if not isinstance(value, (tuple, list)):
        raise ValueError("coherent set interpretations must be a sequence")
    return value


def _mapped_coverage(store, subject_refs):
    """Only genuine submitted/derived subjects can occupy original input units."""
    result = {}
    for ref in subject_refs:
        subject = store.get(ref)
        if subject.get("record_type") not in {"input", "read_subject", "feature", "product"}:
            continue
        for span in store.coverage(ref):
            result.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
    return {ref: _merge(spans) for ref, spans in result.items()}


def _span_dimension(store, span):
    """Internal keys name actual reads; public extents keep library/member IDs."""
    if "member_ref" in span:
        return store.footprint_dimension(span)["id"]
    return span["target_ref"]


class _BoundedExtentMetric(ContractError):
    """A retained threshold cannot supply this projection's scalar geometry."""


def _metric(observation, name):
    values = []
    for index, row in enumerate(observation.get("measurements", ())):
        if row["name"] != name or row["value"]["type"] != "number":
            continue
        atom = row["value"]
        if "bound" in atom:
            raise _BoundedExtentMetric("bounded_measurement_cannot_supply_exact_extent", detail={
                "observation_ref": observation["id"], "measurement_name": name,
                "field_path": ["measurements", index, "value"], "measurement_value": dict(atom),
                "required_representation": "unbounded_extent_operand",
                "meaning": "bounded_measurement_retained_without_scalar_extent_projection"})
        values.append(atom["value"])
    return values[0] if len(values) == 1 else None


def _observation_extent(store, observation):
    """Map a native interval exactly, or retain a declared fractional proxy.

    A product's explicit native derivation path can map actual query symbols
    into original input units, including reverse, framed and compound paths.
    An older aggregate parent footprint is not a residue map: its fractional
    query coverage continues to scale the evidence operand rather than invent
    coordinates. An exactly mapped interval is not scaled by coverage again.
    Reported external experiments cannot supply native target coordinates by
    reusing their reported query start/end numbers.
    """
    footprint = _mapped_coverage(store, observation["subject_refs"])
    if observation["kind"] not in {"alignment", "profile_match", "comparison", "structure_match"}:
        return footprint, 1., {"extent_mode": "subject_footprint"}
    coverage = _metric(observation, "query_coverage")
    if coverage is not None:
        coverage = _number(coverage, "query_coverage", maximum=1)
    start, end = _metric(observation, "query_start"), _metric(observation, "query_end")
    if (observation.get("origin") == "tool" and len(observation["subject_refs"]) == 1
            and start is not None and end is not None):
        subject_ref = observation["subject_refs"][0]
        subject = store.get(subject_ref)
        if (footprint and subject["record_type"] in {"input", "read_subject", "feature", "product"}
                and hasattr(store, "has_exact_mapping")
                and store.has_exact_mapping(subject_ref)):
            if (isinstance(start, bool) or isinstance(end, bool)
                    or int(start) != start or int(end) != end or not 0 <= start < end):
                raise ValueError("native query interval is outside its actual subject")
            mapped = store.map_segments(subject_ref, [{"start": int(start), "end": int(end)}])
            exact = {}
            for span in mapped:
                exact.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
            mapping = store.sequence_mapping(subject_ref)
            original_units = {span["unit"] for span in mapping["path"]}
            query_unit = ("aa" if mapping["units_per_symbol"] == 3 else
                          next(iter(original_units)) if len(original_units) == 1 else "symbol")
            return {ref: _merge(spans) for ref, spans in exact.items()}, 1., {
                "extent_mode": ("native_input_query_interval" if subject["record_type"] == "input"
                                else "native_query_interval_mapped_to_original_input"),
                "native_query_interval": {"start": int(start), "end": int(end), "unit": query_unit},
                "query_coverage": coverage, "mapping_subject_ref": subject_ref,
                "mapping_version": mapping["version"]}
        if subject["record_type"] == "input":
            if (isinstance(start, bool) or isinstance(end, bool)
                    or int(start) != start or int(end) != end
                    or not 0 <= start < end <= subject["length"]):
                raise ValueError("native query interval is outside its actual input")
            return {subject["id"]: [(int(start), int(end))]}, 1., {
                "extent_mode": "native_input_query_interval",
                "native_query_interval": {"start": int(start), "end": int(end),
                                          "unit": subject["unit"]},
                "query_coverage": coverage}
    if coverage is not None:
        return footprint, coverage, {
            "extent_mode": "fractional_query_coverage_without_residue_map",
            "query_coverage": coverage}
    return footprint, 1., {"extent_mode": "subject_footprint_no_native_interval"}


def _observation_extents(store, observation):
    """Keep native operand coordinate systems distinct from input attribution.

    Both actual operands may occupy original input units. Each uses its own
    interval and mapping, so an external query cannot turn the whole reference
    input into alignment coverage. Exact physical paths on external references
    and their derivatives do not supply any original-input footprint.
    """
    intervals = observation.get("operand_intervals")
    if observation.get("origin") != "tool" or intervals is None:
        footprint, factor, details = _observation_extent(store, observation)
        if intervals:
            details = {**details, "operand_intervals": [dict(row) for row in intervals]}
        return [(footprint, factor, details)]

    extents = []
    for operand in intervals:
        subject_ref, role = operand["subject_ref"], operand["role"]
        footprint = _mapped_coverage(store, [subject_ref])
        if not footprint:
            # A source coordinate path can be exact without belonging to the
            # caller's input. Preserve it below; never relabel its numbers.
            continue
        subject = store.get(subject_ref)
        metric = "query_coverage" if role == "query" else "target_coverage"
        coverage = _metric(observation, metric)
        if coverage is not None:
            coverage = _number(coverage, metric, maximum=1)
        interval = {"start": operand["start"], "end": operand["end"], "unit": operand["unit"]}
        # The observation retains the complete operand list. A contribution
        # needs its own interval, not another copy of every other measured site.
        details = {"native_operand_interval": dict(operand), metric: coverage}
        exact_mapping = (hasattr(store, "has_exact_mapping")
                         and store.has_exact_mapping(subject_ref))
        if exact_mapping:
            mapped = store.map_segments(subject_ref, [{"start": operand["start"], "end": operand["end"]}])
            exact = {}
            for span in mapped:
                exact.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
            if not exact:
                continue
            footprint = {ref: _merge(spans) for ref, spans in exact.items()}
            mode = ("native_input_query_interval" if role == "query" and subject["record_type"] == "input"
                    else f"native_{role}_interval_mapped_to_original_input")
            details.update(extent_mode=mode, mapping_subject_ref=subject_ref,
                           mapping_version=store.sequence_mapping(subject_ref)["version"])
            factor = 1.
        elif subject["record_type"] == "input":
            # Lightweight interface fixtures may omit the exact-map API.
            if not 0 <= operand["start"] < operand["end"] <= subject["length"]:
                raise ValueError("native operand interval is outside its actual input")
            footprint = {subject_ref: [(operand["start"], operand["end"])]}
            details["extent_mode"] = ("native_input_query_interval" if role == "query"
                                      else "native_reference_interval_mapped_to_original_input")
            factor = 1.
        else:
            # Preserve the declared aggregate-product proxy for this operand;
            # it must not rescale an exactly mapped other operand.
            details["extent_mode"] = ("fractional_query_coverage_without_residue_map" if role == "query"
                                      else "fractional_reference_coverage_without_residue_map")
            factor = coverage if coverage is not None else 1.
        details[f"native_{role}_interval"] = interval
        extents.append((footprint, factor, details))
    if extents:
        return extents
    coverage = _metric(observation, "query_coverage")
    factor = _number(coverage, "query_coverage", maximum=1) if coverage is not None else 1.
    unmeasured = _mapped_coverage(store, [*observation["subject_refs"],
                                        *observation.get("source_subject_refs", ())])
    return [({}, factor, {"extent_mode": "source_subject_operand_intervals",
        "operand_intervals": [dict(row) for row in intervals], "query_coverage": coverage,
        "unmeasured_native_target_refs": sorted(unmeasured)})]


def _assessment_extent(assessment, store=None):
    """Already validated original-unit attribution, never a source measurement.

    The state boundary validates units, bounds, hypothesis coverage and assigned
    scope. Keeping this on the assessment lets several target interpretations
    reuse one immutable source observation without relabeling its subjects.
    """
    result = {}
    for span in assessment.get("target_footprint") or ():
        result.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
    return {ref: _merge(spans) for ref, spans in result.items()}


def _inference_source_extent(store, observation):
    """Describe the measured source without converting it into target extent.

    The existing comparison proxy uses query-role coverage once per assessment,
    regardless of whether the physical source is an input, reference or derived
    product. Exact source paths are provenance, not an inferred target map.
    Native empty interval lists remain explicitly empty; a measured gap is not
    automatically classified as uninformative by this projection.
    """
    comparison = observation["kind"] in {"alignment", "profile_match", "comparison", "structure_match"}
    coverage = _metric(observation, "query_coverage") if comparison else None
    factor = _number(coverage, "query_coverage", maximum=1) if coverage is not None else 1.
    details = {"extent_mode": "assessment_inferred_target_extent",
        "source_extent_factor": factor,
        "source_extent_factor_basis": ("reported_query_coverage" if coverage is not None else
            "query_coverage_unreported_unit_factor" if comparison else "non_comparison_unit_factor"),
        "query_coverage": coverage}
    intervals = observation.get("operand_intervals")
    if intervals is not None:
        details["source_operand_intervals"] = [dict(row) for row in intervals]
    # Older native observations may contain only a query interval. Preserve its
    # actual subject and unit when those metadata exist; never guess an external
    # coordinate system from the target footprint or a length ratio.
    elif observation.get("origin") == "tool" and len(observation["subject_refs"]) == 1:
        start, end = _metric(observation, "query_start"), _metric(observation, "query_end")
        if start is not None and end is not None:
            details["source_query_interval_metrics"] = {"start": start, "end": end}
            ref = observation["subject_refs"][0]
            subject = store.get(ref)
            unit = (store.subject_unit(ref) if hasattr(store, "subject_unit") else subject.get("unit"))
            if (unit is not None and not isinstance(start, bool) and not isinstance(end, bool)
                    and int(start) == start and int(end) == end and 0 <= start < end):
                intervals = [{"role": "query", "subject_ref": ref,
                    "start": int(start), "end": int(end), "unit": unit}]
                details["source_operand_intervals"] = intervals
    mapped = []
    if observation.get("origin") == "tool" and hasattr(store, "sequence_mapping"):
        for operand in intervals or ():
            ref = operand["subject_ref"]
            if not store.has_exact_mapping(ref):
                mapped.append({"operand_interval": dict(operand),
                               "mapping_status": "subregion_mapping_unavailable"})
                continue
            mapping = store.sequence_mapping(ref)
            mapped.append({"operand_interval": dict(operand),
                "mapping_status": "exact_physical_source_path",
                "mapping_version": mapping["version"],
                "physical_source_segments": map_interval(mapping, operand["start"], operand["end"])})
    if mapped or intervals == []:
        details["source_operand_mappings"] = mapped
    return factor, details


def _account_identity(account):
    if 'id' in account:
        field = ('interpretation_account_ref' if account.get('record_type') == 'interpretation_account'
                 else 'annotation_ref')
        return {field: account['id']}
    return {key: account[key] for key in ('annotation_ref', 'interpretation_account_ref') if key in account}


def _account_context(account, allocation):
    prefix = ('interpretation_account' if account.get('record_type') == 'interpretation_account'
              else 'annotation')
    return {prefix+'_context_scope': allocation,
            prefix+'_context_account_scope': account.get('context_account_scope')}


def _operands(annotation, coherent_set, assessments, store, policy, *, validity=None):
    """Resolve current source links and their ACTUAL target footprints once."""
    method_axes = dict(policy.observation_axes)
    applicability = dict(policy.applicability_weights)
    relations = dict(policy.relation_weights)
    inactive, interpreted, observation_cache = [], [], {}
    seen_hypotheses = set()
    for interpretation in _interpretations(coherent_set):
        disposition = interpretation["disposition"]
        if disposition not in {"supported", "weakened", "unresolved"}:
            raise ValueError("unknown interpretation disposition")
        hypothesis_ref = interpretation["hypothesis_ref"]
        if hypothesis_ref in seen_hypotheses:
            raise ValueError("a coherent set cannot assign two dispositions to one hypothesis")
        seen_hypotheses.add(hypothesis_ref)
        hypothesis = store.get(hypothesis_ref)
        hypothesis_coverage = _mapped_coverage(store, hypothesis["subject_refs"])
        context_assessments = any(assessments.get(ref, {}).get("extent_basis") == "context_allocation"
            for ref in interpretation.get("assessment_refs", ()))
        if not hypothesis_coverage and not context_assessments and annotation.get("context_account_scope") is None:
            inactive.append({"hypothesis_ref": hypothesis_ref,
                             "reason": "hypothesis_has_no_submitted_target_coverage"})
            continue
        for assessment_ref in interpretation.get("assessment_refs", ()):
            assessment = assessments.get(assessment_ref)
            if validity is not None and validity.is_replaced(assessment_ref):
                inactive.append({'assessment_ref': assessment_ref,
                                 'reason': 'scientific_finding_replaced'})
                continue
            if assessment is None:
                # Superseded attribution remains durable history, not current
                # support for an annotation that names its exact old revision.
                inactive.append({"assessment_ref": assessment_ref,
                                 "reason": "not_current_assessment_revision"})
                continue
            if assessment.get('investigation_finding', {}).get('status') == 'withdrawn':
                inactive.append({'assessment_ref': assessment_ref,
                    'reason': 'scientific_finding_withdrawn',
                    'withdrawal_reason': assessment['investigation_finding']['withdrawal_reason']})
                continue
            if assessment["hypothesis_ref"] != hypothesis_ref:
                raise ValueError("assessment hypothesis differs from interpretation")
            observation_ref = assessment["observation_ref"]
            if observation_ref not in observation_cache:
                observation_cache[observation_ref] = store.get(observation_ref)
            observation = observation_cache[observation_ref]
            extent_basis = assessment["extent_basis"]
            if extent_basis not in {"observed_extent", "inferred_extent", "context_allocation"}:
                raise ValueError("unknown assessment extent_basis")
            if extent_basis == "inferred_extent" and assessment["applicability"] == "direct":
                raise ValueError("assessment_inferred_extent_cannot_be_direct")
            if extent_basis == "context_allocation":
                allocation = assessment.get("context_scope")
                annotation_allocation = annotation.get("context_scope")
                account_kind = annotation.get('record_type', 'annotation')
                missing = ("assessment" if allocation is None else
                           account_kind if annotation_allocation is None else None)
                empty = ("assessment" if allocation is not None and not allocation["subject_refs"] else
                         account_kind if annotation_allocation is not None and not annotation_allocation["subject_refs"] else None)
                if missing is not None or empty is not None:
                    inactive.append({"assessment_ref": assessment_ref,
                        "field_path": ["context_scope"],
                        "allocation_owner": missing or empty,
                        "reason": "context_allocation_unlocalized" if missing else "context_allocation_empty"})
                    continue
                axis = method_axes.get(observation["kind"])
                if axis is None:
                    continue
                try:
                    factor, details = _inference_source_extent(store, observation)
                except _BoundedExtentMetric as error:
                    inactive.append({"assessment_ref": assessment_ref,
                        "reason": str(error), **error.detail})
                    continue
                relation = assessment["relation"]
                interpreted.append({**_account_identity(annotation),
                    "coherent_set_ref": coherent_set.get("id"),
                    "hypothesis_ref": hypothesis_ref, "assessment_ref": assessment_ref,
                    "observation_ref": observation_ref, "source_ref": observation["source_ref"],
                    "observation_subject_refs": list(observation["subject_refs"]),
                    "source_subject_refs": list(observation.get("source_subject_refs", ())),
                    "origin": observation.get("origin"), "observation_kind": observation["kind"],
                    "disposition": disposition, "relation": relation,
                    "applicability": assessment["applicability"], "extent_basis": extent_basis,
                    "condition_refs": list(assessment.get("condition_refs", ())),
                    "assumption_refs": list(assessment.get("assumption_refs", ())),
                    "axis": axis, "weight": applicability[assessment["applicability"]] * relations[relation] * factor,
                    **details, "extent_mode": "assessment_context_allocation",
                    "attribution_space": "material_context",
                    "context_scope": allocation,
                    "context_account_scope": assessment.get("context_account_scope"),
                    **_account_context(annotation, annotation_allocation),
                    "footprint": {}})
                continue
            physical_coverage = _mapped_coverage(store, observation.get("source_subject_refs", ()))
            assessed_coverage = _assessment_extent(assessment, store)
            if extent_basis == "inferred_extent":
                if not assessed_coverage:
                    inactive.append({"assessment_ref": assessment_ref,
                        "field_path": ["target_footprint"],
                        "reason": "inferred_extent_requires_target_footprint"})
                    continue
                try:
                    extent_factor, extent_record = _inference_source_extent(store, observation)
                except _BoundedExtentMetric as error:
                    inactive.append({"assessment_ref": assessment_ref,
                        "reason": str(error), **error.detail})
                    continue
                # One inference belongs to this assessment, not to each source
                # operand. Source identity and measured bounds do not select
                # the inferred target region.
                extents = [(assessed_coverage, extent_factor, extent_record)]
            else:
                try:
                    extents = _observation_extents(store, observation)
                except _BoundedExtentMetric as error:
                    inactive.append({"assessment_ref": assessment_ref,
                        "reason": str(error), **error.detail})
                    continue
            native_operand_extents = (observation.get("origin") == "tool"
                                      and observation.get("operand_intervals") is not None)
            axis = method_axes.get(observation["kind"])
            if axis is None:
                continue
            matched = False
            for observed_coverage, extent_factor, extent_record in extents:
                footprint = {}
                if (extent_basis == "observed_extent" and not observed_coverage
                        and observation.get("operand_intervals") is None and physical_coverage):
                    # A legacy actual assayed/source subject may be mapped even
                    # when the query attribution is external. Its own footprint
                    # is an observed source extent; target_footprint is not.
                    observed_coverage = physical_coverage
                    extent_record = {**extent_record, "extent_mode": "observed_source_subject_footprint"}
                for target_ref, spans in hypothesis_coverage.items():
                    bounded = _intersection(spans, observed_coverage.get(target_ref, ()))
                    if (extent_basis == "observed_extent" and not native_operand_extents
                            and target_ref in physical_coverage):
                        # The native dispatcher already mapped each actual
                        # query/reference operand independently. A reference
                        # feature's location is not another spatial restriction
                        # on the query simply because both share one input.
                        # Legacy/reported assays retain their source bounds;
                        # reported interval fields alone are not native maps.
                        bounded = _intersection(bounded, physical_coverage[target_ref])
                    if assessed_coverage:
                        bounded = _intersection(bounded, assessed_coverage.get(target_ref, ()))
                    if bounded:
                        footprint[target_ref] = bounded
                if not footprint:
                    continue
                matched = True
                if assessed_coverage:
                    extent_record = {**extent_record,
                        "assessment_target_footprint": [dict(span)
                            for span in assessment["target_footprint"]]}
                relation = assessment["relation"]
                interpreted.append({**_account_identity(annotation),
                    "coherent_set_ref": coherent_set.get("id"),
                    "hypothesis_ref": hypothesis_ref, "assessment_ref": assessment_ref,
                    "observation_ref": observation_ref, "source_ref": observation["source_ref"],
                    "observation_subject_refs": list(observation["subject_refs"]),
                    "source_subject_refs": list(observation.get("source_subject_refs", ())),
                    "origin": observation.get("origin"), "observation_kind": observation["kind"],
                    "disposition": disposition, "relation": relation,
                    "applicability": assessment["applicability"],
                    "extent_basis": extent_basis,
                    "condition_refs": list(assessment.get("condition_refs", ())),
                    "assumption_refs": list(assessment.get("assumption_refs", ())),
                    "axis": axis, "weight": applicability[assessment["applicability"]]
                        * relations[relation] * extent_factor,
                    **extent_record,
                    "footprint": footprint})
            if not matched:
                inactive.append({"assessment_ref": assessment_ref,
                                 "reason": "observation_has_no_matching_target_coverage"})
    return interpreted, inactive


def _components(interpreted, footprint_kind, policy):
    """One spatial slice of one OWNER-declared compatible account."""
    positive = {axis: [] for axis in AXES}
    opposing = {axis: [] for axis in AXES}
    for row in interpreted:
        disposition, relation, axis = row["disposition"], row["relation"], row["axis"]
        if row["weight"] == 0:
            continue
        if disposition == "unresolved":
            positive[axis].append({**row, "weight": row["weight"] * policy.unresolved_factor})
            if relation in {"weakens", "mixed"}:
                positive["discrimination"].append({**row,
                    "axis": "discrimination", "weight": row["weight"] * policy.unresolved_factor,
                    "derived_meaning": "source_bound_unresolved_counterevidence"})
            continue
        supporting_relation = "strengthens" if disposition == "supported" else "weakens"
        if relation in {supporting_relation, "mixed"}:
            positive[axis].append(row)
        if relation in ({"weakens", "mixed"} if disposition == "supported"
                        else {"strengthens", "mixed"}):
            opposing[axis].append(row)
        if disposition == "weakened" and relation in {"weakens", "mixed"}:
            positive["discrimination"].append({**row, "axis": "discrimination",
                "derived_meaning": "source_bound_weakened_interpretation"})

    # SAME observation, explicit contrasting interpretations. This derived
    # distinction is neither another experiment nor another action observation.
    for row in interpreted:
        if row["disposition"] != "supported" or row["relation"] != "strengthens":
            continue
        contrasts = [other for other in interpreted
            if other["observation_ref"] == row["observation_ref"]
            and other["hypothesis_ref"] != row["hypothesis_ref"]
            and other["disposition"] in {"weakened", "unresolved"}
            and other["relation"] == "weakens"]
        if contrasts:
            contrast = max(contrasts, key=lambda item: item["weight"])
            positive["discrimination"].append({**row, "axis": "discrimination",
                "weight": min(row["weight"], contrast["weight"]),
                "contrast_assessment_ref": contrast["assessment_ref"],
                "derived_meaning": "same_observation_contrasts_explicit_alternatives"})

    components, contributions = {}, []
    for axis in AXES:
        # Maxima cannot inflate through copied evidence or candidate names.
        p = max(positive[axis], key=lambda item: (item["weight"],
                item["assessment_ref"]), default=None)
        n = max(opposing[axis], key=lambda item: (item["weight"],
                item["assessment_ref"]), default=None)
        components[axis] = (0. if p is None else p["weight"]) / (
            1. + (0. if n is None else n["weight"]))
        for role, contribution in (("supporting", p), ("opposing", n)):
            if contribution is not None and contribution["weight"] > 0:
                contributions.append({**contribution, "effect": role,
                                      "axis_value": components[axis]})
    return components, contributions


def _spatial_candidates(annotation, coherent_set, interpreted, footprints, eligible, policy):
    """No coherent grouping can expand a local observation into a whole genome."""
    result = {}
    for target_ref, annotation_segments in footprints.items():
        spans = _intersection(_merge(annotation_segments), eligible[target_ref])
        if not spans:
            continue
        boundaries = {coordinate for span in spans for coordinate in span}
        relevant = []
        for row in interpreted:
            bounded = _intersection(row["footprint"].get(target_ref, ()), spans)
            if bounded:
                relevant.append((row, bounded))
                boundaries.update(coordinate for span in bounded for coordinate in span)
        boundaries = sorted(boundaries)
        for start, end in zip(boundaries, boundaries[1:]):
            if not any(a <= start < end <= b for a, b in spans):
                continue
            rows = [row for row, covered in relevant
                    if any(a <= start < end <= b for a, b in covered)]
            components, contributions = _components(rows, annotation["footprint_kind"], policy)
            result.setdefault(target_ref, []).append({**_account_identity(annotation),
                "coherent_set_ref": coherent_set.get("id"), "segments": [(start, end)],
                "components": components, "contributions": contributions,
                "volume": softened_hypervolume(components, policy)})
    return result


def project_credit(store, scope=None, policy=None, *, details_limit=None, details_offset=0,
                   include_interpretation_accounts=False, integration_arithmetic=LEGACY_INTEGRATION):
    """Project the authoritative current state over a fixed submitted scope.

    Scope names original input subjects and may declare fixed original-unit
    segments. Each target's fixed eligible length is its denominator in its own
    recorded units (aa, nt, or symbol); absent explicit segments, this is its
    original length. Child region scopes are chosen at commission, never
    inferred from newly discovered candidate genes.
    Current annotations carry authoritative original-unit footprints. A small
    locus therefore contributes only its actual fraction of a genome. Targets
    are equally weighted by default; caller-specified target weights remain
    fixed configuration and newly acquired subjects never expand the scope.
    Each assessment declares observed extent, inferred extent or explicit
    material-context allocation. Observed attribution clips actual measurements;
    inferred non-direct attribution uses its bounded target footprint and source
    query-coverage proxy once. Context masks allocate an interpretation over
    original material without manufacturing physical measurements. Source
    subjects, coordinates and paths retain their meaning. Missing localization
    stays recorded but inactive; explicit empty allocation means withdrawal.

    Scientific scope and compatibility are supplied by the store/annotation
    owner, not guessed from labels. Values can fall after a current correction.
    This routine has no historical-best clamp and produces no yield events.

    A caller may explicitly include recorded interpretation_accounts alongside
    annotations for local scientific investigation credit. This changes eligible
    account kinds, not the evidence formula or fixed scope. Whole accounts still
    compete without automatic fusion; the default task projection remains
    annotation-only. Returned references retain the actual account kind.

    A read library uses disjoint original member-local positions and Store's
    frozen selected position mass, never a joined sequence or equal-read target
    inventory. Its default return is a summary with explicit detail page totals.
    ``details_limit``/``details_offset`` request bounded winning-operand and
    inactive-dependency pages under the SAME policy, scope and read snapshot;
    explicit paging also works for scalar inputs. Scalar calls without paging
    retain their previous complete record shape (with the new projection
    version). A summary's zero limit and next_offset=0 mean details exist but
    have not been requested; a positive caller limit advances the page.
    A nonzero offset requires an explicit limit, so a scalar full-detail call
    cannot silently ignore a supplied page offset.

    The default arithmetic retains the historical per-cell floating sum for
    recovery of existing bindings. New AnnotationSupportScore bindings select
    STABLE_INTEGRATION explicitly: equal winning component vectors accumulate
    integer position mass before floating multiplication and summation. This
    makes the value invariant to extra boundaries from losing accounts without
    changing evidence weights, the hypervolume formula or genuine corrections.
    """
    policy = CreditPolicy() if policy is None else CreditPolicy.from_record(policy)
    if integration_arithmetic not in {LEGACY_INTEGRATION, STABLE_INTEGRATION}:
        raise ValueError('unknown_integration_arithmetic')
    if type(include_interpretation_accounts) is not bool:
        raise TypeError('explicit_interpretation_account_selection_required')
    if (details_limit is not None and (type(details_limit) is not int or details_limit < 0)
            or type(details_offset) is not int or details_offset < 0):
        raise ValueError("credit detail page requires nonnegative integer limit/offset")
    if details_limit is None and details_offset:
        raise ValueError("details_offset_requires_explicit_details_limit")
    with store.read_snapshot():
        targets = store.targets()
        selected = set(scope["subject_refs"]) if scope is not None else {row["id"] for row in targets}
        scalar_full = details_limit is None and not any(
            row.get("target_kind") == "read_library" and row["id"] in selected for row in targets)
        projected = _project_context_snapshot(store, scope, policy, targets,
            details_limit=None if scalar_full else (details_limit or 0), details_offset=details_offset,
            include_interpretation_accounts=include_interpretation_accounts,
            integration_arithmetic=integration_arithmetic)
        return _scalar_full_shape(projected) if scalar_full else projected


def _dimension_metadata(store, dimension_ref):
    """Metadata only: never read sequence, quality, title or source artifacts."""
    subject = store.get(dimension_ref)
    if subject["record_type"] == "read_subject":
        return {"id": dimension_ref, "target_ref": subject["library_ref"],
            "member_ref": subject["member_ref"], "length": subject["length"],
            "unit": subject["unit"]}
    if subject["record_type"] == "input" and subject.get("target_kind") != "read_library":
        return {"id": dimension_ref, "target_ref": dimension_ref,
            "length": subject["length"], "unit": subject["unit"]}
    raise ValueError("credit dimension must be an original sequence or read subject")


def _public_footprint(store, footprint):
    result = []
    for dimension_ref, segments in footprint.items():
        metadata = _dimension_metadata(store, dimension_ref)
        identity = {key: metadata[key] for key in ("target_ref", "member_ref", "unit") if key in metadata}
        result.extend({**identity, "start": start, "end": end} for start, end in segments)
    return result


def _page_metadata(offset, limit, total, *, row_unit):
    return {"offset": offset, "limit": limit, "total": total,
        "returned": min(limit, max(0, total-offset)),
        "next_offset": offset+limit if offset+limit < total else None,
        "row_unit": row_unit}


def _candidate_order(candidate):
    return (-candidate["volume"], next(iter(_account_identity(candidate).values())),
            str(candidate["coherent_set_ref"]))


def _scalar_full_shape(projection):
    """Keep the established unpaged scalar surface on the shared cell engine."""
    targets = []
    for row in projection.targets:
        target = dict(row)
        target.pop("inactive_dependencies_location", None)
        target["inactive_dependencies"] = [{key: value for key, value in item.items() if key != "target_ref"}
            for item in projection.inactive_dependencies if item["target_ref"] == row["target_ref"]]
        target["scope_segments"] = [{"start": span["start"], "end": span["end"]}
            for span in projection.scope.get("segments", ()) if span["target_ref"] == row["target_ref"]]
        if "segments" not in projection.scope:
            target["scope_segments"] = [{"start": 0, "end": row["length"]}]
        targets.append(target)
    sources = []
    for source in projection.source_contributions:
        row = dict(source)
        # Context allocation retains explicit material coordinates in all views.
        if row.get("attribution_space") != "material_context":
            row["contributing_segments"] = [{"start": span["start"], "end": span["end"]}
                                             for span in row["contributing_segments"]]
            footprint = {}
            for span in row["footprint"]:
                footprint.setdefault(span["target_ref"], []).append((span["start"], span["end"]))
            row["footprint"] = footprint
        row.pop("dimension_ref", None)
        sources.append(row)
    return CreditProjection(projection.credit, projection.axis_components, tuple(targets), tuple(sources),
                            projection.policy, projection.scope,
                            integration_arithmetic=projection.integration_arithmetic,
                            interpretation=projection.interpretation)


def _project_context_snapshot(store, scope, policy, all_targets, *, details_limit, details_offset,
                              include_interpretation_accounts=False, integration_arithmetic=LEGACY_INTEGRATION):
    """One disjoint-cell integral; original read dimensions remain lazy.

    Full-target masks are constant descriptor tokens. Only non-full masks are
    streamed into temporary exception rows; whole-read exceptions are grouped
    by active-mask signature. Real interval-sensitive reads and scalar targets
    use the same whole-account comparison on their actual local boundaries.
    Temporary rows are derived geometry, never a second scientific authority.
    """
    effective_scope = store.validate_scope(scope)
    selected = set(effective_scope["subject_refs"])
    targets = [target for target in all_targets if target["id"] in selected]
    weights = dict(policy.target_weights)
    if not set(weights) <= {target["id"] for target in all_targets}:
        raise ValueError("target weights name a non-input target")
    total_weight = sum(weights.get(target["id"], 1.) for target in targets)
    if targets and total_weight <= 0:
        raise ValueError("the selected target scope needs positive aggregate weight")
    masses = {target["id"]: store.scope_measure(effective_scope, target["id"]) for target in targets}
    totals = {ref: {"volume": 0., "units": 0, "axes": dict.fromkeys(AXES, 0.)} for ref in selected}
    basis = hashlib.sha256(json.dumps({"scope": effective_scope, "policy": policy.as_record()},
                                     sort_keys=True).encode())
    if include_interpretation_accounts:
        basis.update(b'annotation_and_interpretation_accounts_v1')
    stable = integration_arithmetic == STABLE_INTEGRATION
    if stable:
        basis.update(STABLE_INTEGRATION.encode())
    spool = sqlite3.connect("")
    spool.row_factory = sqlite3.Row
    try:
        spool.executescript("""
            PRAGMA temp_store=FILE;
            PRAGMA cache_size=-2048;
            CREATE TABLE masks(id INTEGER PRIMARY KEY,digest TEXT UNIQUE,payload TEXT);
            CREATE TABLE mask_targets(mask_id INTEGER,target_ref TEXT,full INTEGER,
                PRIMARY KEY(mask_id,target_ref));
            CREATE TABLE mask_spans(mask_id INTEGER,dimension_ref TEXT,target_ref TEXT,
                member_ref TEXT,length INTEGER,unit TEXT,start INTEGER,end INTEGER);
            CREATE INDEX mask_dimension ON mask_spans(dimension_ref,mask_id,start,end);
            CREATE TABLE exceptions(dimension_ref TEXT PRIMARY KEY,target_ref TEXT,member_ref TEXT,
                length INTEGER,unit TEXT,sensitive INTEGER DEFAULT 0,signature TEXT);
            CREATE INDEX exception_target ON exceptions(target_ref,sensitive,signature,dimension_ref);
            CREATE TABLE dimensions(id TEXT PRIMARY KEY,target_ref TEXT,member_ref TEXT,
                length INTEGER,unit TEXT,eligible TEXT);
            CREATE TABLE local_candidates(id INTEGER PRIMARY KEY,dimension_ref TEXT,start INTEGER,
                end INTEGER,payload TEXT);
            CREATE INDEX local_dimension ON local_candidates(dimension_ref,start,end);
            CREATE TABLE accounts(id INTEGER PRIMARY KEY,payload TEXT);
            CREATE TABLE cells(id INTEGER PRIMARY KEY,target_ref TEXT,kind TEXT,signature TEXT,
                mass INTEGER,members INTEGER,payload TEXT);
            CREATE TABLE winners(id INTEGER PRIMARY KEY,dimension_ref TEXT,start INTEGER,end INTEGER,payload TEXT);
            CREATE TABLE inactive(id INTEGER PRIMARY KEY,target_ref TEXT,payload TEXT);
            CREATE TABLE numeric_mass(target_ref TEXT,components TEXT,mass INTEGER,volume REAL,
                PRIMARY KEY(target_ref,components));
        """)

        validity = FindingValidity(store, effective_scope, spool=spool)
        validity.update_basis(basis)

        def mask_id(mask):
            digest = store.context_mask_identity(mask)
            old = spool.execute("SELECT id FROM masks WHERE digest=?", (digest,)).fetchone()
            if old is not None:
                return old[0]
            key = spool.execute("INSERT INTO masks VALUES(NULL,?,?)",
                                (digest, json.dumps(mask, separators=(",", ":")))).lastrowid
            for target in targets:
                ref = target["id"]
                full = store.context_mask_target_full(mask, ref)
                spool.execute("INSERT INTO mask_targets VALUES(?,?,?)", (key, ref, int(full)))
                if full or ref not in mask["subject_refs"]:
                    continue
                query, parameters = store.context_mask_target_query(mask, ref)
                for native in store.db.execute(query, parameters):
                    row = dict(native)
                    spool.execute("INSERT INTO mask_spans VALUES(?,?,?,?,?,?,?,?)", (
                        key, row["dimension_ref"], ref, row["member_ref"], row["length"], row["unit"],
                        row["start"], row["end"]))
                    sensitive = int(row["start"] != 0 or row["end"] != row["length"])
                    spool.execute("INSERT INTO exceptions VALUES(?,?,?,?,?,?,NULL) "
                        "ON CONFLICT(dimension_ref) DO UPDATE SET sensitive=max(sensitive,excluded.sensitive)",
                        (row["dimension_ref"], ref, row["member_ref"], row["length"], row["unit"], sensitive))
            return key

        eligible_id = mask_id(effective_scope)
        for target in targets:
            if target.get("target_kind") != "read_library":
                ref = target["id"]
                spans = store.context_mask_dimension_segments(effective_scope, ref)
                spool.execute("INSERT OR REPLACE INTO dimensions VALUES(?,?,?,?,?,?)", (
                    ref, ref, None, target["length"], target["unit"], json.dumps(spans)))

        accounts = store.iter_current_annotations(effective_scope)
        if include_interpretation_accounts:
            accounts = chain(accounts, store.iter_current_accounts('interpretation_account', effective_scope))
        for annotation in accounts:
            footprints, eligible, affected = {}, {}, set()
            context_domain = annotation.get("context_account_scope")
            context_allocation = annotation.get("context_scope")
            if context_domain is not None:
                visible_mask = context_allocation if context_allocation and context_allocation["subject_refs"] else context_domain
                affected.update(selected.intersection(visible_mask["subject_refs"]))
            for span in annotation["footprint"]:
                if span["target_ref"] not in selected:
                    continue
                metadata = store.footprint_dimension(span)
                dimension = metadata["id"]
                allowed = _merge([(part["start"], part["end"]) for part in
                                  store.scope_dimension_segments(effective_scope, dimension)])
                if not _intersection([(span["start"], span["end"])], allowed):
                    continue
                footprints.setdefault(dimension, []).append((span["start"], span["end"]))
                eligible[dimension] = allowed
                affected.add(metadata["target_ref"])
                spool.execute("INSERT OR IGNORE INTO dimensions VALUES(?,?,?,?,?,?)", (
                    dimension, metadata["target_ref"], metadata.get("member_ref"), metadata["length"],
                    metadata["unit"], json.dumps([{"start": a, "end": b} for a, b in allowed])))
                if metadata.get("member_ref") is not None:
                    spool.execute("INSERT INTO exceptions VALUES(?,?,?,?,?,1,NULL) "
                        "ON CONFLICT(dimension_ref) DO UPDATE SET sensitive=1", (
                            dimension, metadata["target_ref"], metadata["member_ref"], metadata["length"], metadata["unit"]))
            if annotation["subject_ref"] in selected:
                affected.add(annotation["subject_ref"])
            refs = [ref for group in annotation["coherent_sets"]
                    for item in _interpretations(group) for ref in item.get("assessment_refs", ())]
            assessments = store.current_assessment_subset(refs)
            basis.update(json.dumps([annotation["id"], sorted(assessments)], separators=(",", ":")).encode())
            for coherent_set in annotation["coherent_sets"]:
                interpreted, inactive = _operands(annotation, coherent_set, assessments, store, policy,
                                                   validity=validity)
                physical, contextual = [], []
                for operand in interpreted:
                    if operand.get("attribution_space") == "material_context":
                        operand = dict(operand)
                        allocation = operand.get('interpretation_account_context_scope',
                                                 operand.get('annotation_context_scope'))
                        operand["_mask_ids"] = [mask_id(operand["context_scope"]), mask_id(allocation)]
                        contextual.append(operand)
                    else:
                        physical.append(operand)
                if context_domain is not None:
                    # A declared compatible account may mix allocation operands
                    # and actual molecular operands. Their own geometries stay
                    # separate, but active rows combine in this ONE account.
                    if context_allocation and context_allocation["subject_refs"]:
                        for original in physical:
                            row = dict(original)
                            spans = _public_footprint(store, row["footprint"])
                            if not spans:
                                continue
                            geometry = {"subject_refs": sorted({span["target_ref"] for span in spans}),
                                        "segments": spans}
                            row["_mask_ids"] = [mask_id(geometry), mask_id(context_allocation)]
                            contextual.append(row)
                            for span in spans:
                                if span["target_ref"] not in selected:
                                    continue
                                metadata = store.footprint_dimension(span)
                                if metadata.get("member_ref") is not None:
                                    spool.execute("INSERT INTO exceptions VALUES(?,?,?,?,?,1,NULL) "
                                        "ON CONFLICT(dimension_ref) DO UPDATE SET sensitive=1", (
                                            metadata["id"], metadata["target_ref"], metadata["member_ref"],
                                            metadata["length"], metadata["unit"]))
                    physical = []
                if contextual:
                    # Independent coherent accounts never receive automatic
                    # fusion merely because their masks or source IDs overlap.
                    spool.execute("INSERT INTO accounts VALUES(NULL,?)", (json.dumps({
                        **_account_identity(annotation), "coherent_set_ref": coherent_set.get("id"),
                        "footprint_kind": annotation["footprint_kind"], "rows": contextual},
                        separators=(",", ":")),))
                candidates = _spatial_candidates(annotation, coherent_set, physical, footprints, eligible, policy)
                for dimension, rows in candidates.items():
                    for candidate in rows:
                        if candidate["volume"] > 0:
                            start, end = candidate["segments"][0]
                            spool.execute("INSERT INTO local_candidates VALUES(NULL,?,?,?,?)", (
                                dimension, start, end, json.dumps(candidate, separators=(",", ":"))))
                for target_ref in sorted(affected):
                    for row in inactive:
                        spool.execute("INSERT INTO inactive VALUES(NULL,?,?)", (target_ref, json.dumps({
                            "target_ref": target_ref, **_account_identity(annotation),
                            "coherent_set_ref": coherent_set.get("id"), **row}, separators=(",", ":"))))

        def full_ids(target_ref):
            return {row[0] for row in spool.execute(
                "SELECT mask_id FROM mask_targets WHERE target_ref=? AND full=1", (target_ref,))}

        def context_winner(active_ids):
            best = None
            for (raw,) in spool.execute("SELECT payload FROM accounts ORDER BY id"):
                account = json.loads(raw)
                rows = [{key: value for key, value in row.items() if key != "_mask_ids"}
                        for row in account["rows"] if all(key in active_ids for key in row["_mask_ids"])]
                components, contributions = _components(rows, account["footprint_kind"], policy)
                candidate = {**_account_identity(account),
                    "coherent_set_ref": account["coherent_set_ref"], "components": components,
                    "contributions": contributions, "volume": softened_hypervolume(components, policy)}
                if candidate["volume"] > 0 and (best is None or _candidate_order(candidate) < _candidate_order(best)):
                    best = candidate
            return best

        def accumulate(target_ref, mass, winner):
            if winner is None or mass == 0:
                return
            if stable:
                # Integrate equal component values once against their exact
                # integer position mass. Losing accounts, quotation labels or
                # different geometric partitions cannot change those operands.
                components = json.dumps([winner['components'][axis] for axis in AXES], separators=(',', ':'))
                spool.execute('INSERT INTO numeric_mass VALUES(?,?,?,?) '
                    'ON CONFLICT(target_ref,components) DO UPDATE SET mass=mass+excluded.mass',
                    (target_ref, components, mass, winner['volume']))
                return
            total = totals[target_ref]
            total["volume"] += mass*winner["volume"]
            total["units"] += mass
            for axis in AXES:
                total["axes"][axis] += mass*winner["components"][axis]

        # Signature strings contain host mask integers only, in a stable order.
        spool.execute("UPDATE exceptions SET signature=(SELECT coalesce(group_concat(mask_id,','),'') "
            "FROM (SELECT DISTINCT mask_id FROM mask_spans s WHERE s.dimension_ref=exceptions.dimension_ref ORDER BY mask_id))")
        for target in targets:
            ref = target["id"]
            if target.get("target_kind") != "read_library":
                continue
            constant = full_ids(ref)
            if eligible_id in constant:
                exception_count, exception_mass = spool.execute(
                    "SELECT count(*),coalesce(sum(length),0) FROM exceptions WHERE target_ref=?", (ref,)).fetchone()
                count, mass = target["member_count"]-exception_count, masses[ref]-exception_mass
                winner = context_winner(constant)
                accumulate(ref, mass, winner)
                if winner is not None and count:
                    spool.execute("INSERT INTO cells VALUES(NULL,?,'default','',?,?,?)", (
                        ref, mass, count, json.dumps(winner, separators=(",", ":"))))
            # Whole-member masks have no local interval sensitivity. Their exact
            # native lengths/counts can be summed under one membership signature.
            for group in spool.execute("SELECT signature,sum(length) AS mass,count(*) AS members "
                    "FROM exceptions WHERE target_ref=? AND sensitive=0 GROUP BY signature ORDER BY signature", (ref,)):
                active = constant | {int(key) for key in group["signature"].split(",") if key}
                if eligible_id not in active:
                    continue
                winner = context_winner(active)
                accumulate(ref, group["mass"], winner)
                if winner is not None:
                    spool.execute("INSERT INTO cells VALUES(NULL,?,'group',?,?,?,?)", (
                        ref, group["signature"], group["mass"], group["members"],
                        json.dumps(winner, separators=(",", ":"))))

        # Only actual interval-sensitive reads acquire dimension metadata.
        for row in spool.execute("SELECT * FROM exceptions WHERE sensitive=1 ORDER BY dimension_ref"):
            spans = store.context_mask_dimension_segments(effective_scope, row["dimension_ref"])
            spool.execute("INSERT OR IGNORE INTO dimensions VALUES(?,?,?,?,?,?)", (
                row["dimension_ref"], row["target_ref"], row["member_ref"], row["length"],
                row["unit"], json.dumps(spans)))
        for dimension in spool.execute("SELECT * FROM dimensions ORDER BY id"):
            dimension_ref, target_ref = dimension["id"], dimension["target_ref"]
            allowed = dimension["eligible"]
            # Boundaries stay in SQLite; only the active cell is held in Python.
            boundaries = spool.execute("SELECT pos FROM (SELECT 0 AS pos UNION SELECT ? "
                "UNION SELECT start FROM mask_spans WHERE dimension_ref=? "
                "UNION SELECT end FROM mask_spans WHERE dimension_ref=? "
                "UNION SELECT start FROM local_candidates WHERE dimension_ref=? "
                "UNION SELECT end FROM local_candidates WHERE dimension_ref=?) ORDER BY pos",
                (dimension["length"], dimension_ref, dimension_ref, dimension_ref, dimension_ref))
            previous, pending = None, None
            for (position,) in boundaries:
                if previous is None:
                    previous = position
                    continue
                if position <= previous or not any(span["start"] <= previous < position <= span["end"]
                                                   for span in json.loads(allowed)):
                    previous = position
                    continue
                active = full_ids(target_ref) | {row[0] for row in spool.execute(
                    "SELECT DISTINCT mask_id FROM mask_spans WHERE dimension_ref=? AND start<=? AND end>=?",
                    (dimension_ref, previous, position))}
                winner = context_winner(active)
                for (raw,) in spool.execute("SELECT payload FROM local_candidates WHERE dimension_ref=? "
                        "AND start<=? AND end>=? ORDER BY id", (dimension_ref, previous, position)):
                    candidate = json.loads(raw)
                    candidate.pop("segments", None)
                    if winner is None or _candidate_order(candidate) < _candidate_order(winner):
                        winner = candidate
                accumulate(target_ref, position-previous, winner)
                if winner is not None:
                    raw = json.dumps(winner, separators=(",", ":"))
                    if pending is not None and pending[1] == previous and pending[2] == raw:
                        pending[1] = position
                    else:
                        if pending is not None:
                            spool.execute("INSERT INTO winners VALUES(NULL,?,?,?,?)", (dimension_ref, *pending))
                        pending = [previous, position, raw]
                previous = position
            if pending is not None:
                spool.execute("INSERT INTO winners VALUES(NULL,?,?,?,?)", (dimension_ref, *pending))

        if stable:
            for ref in sorted(selected):
                total = totals[ref]
                total['units'] = spool.execute('SELECT coalesce(sum(mass),0) FROM numeric_mass '
                    'WHERE target_ref=?', (ref,)).fetchone()[0]
                total['volume'] = math.fsum(row['mass']*row['volume'] for row in spool.execute(
                    'SELECT mass,volume FROM numeric_mass WHERE target_ref=? ORDER BY components', (ref,)))
                for index, axis in enumerate(AXES):
                    total['axes'][axis] = math.fsum(row['mass']*row['coefficient'] for row in spool.execute(
                        'SELECT mass,json_extract(components,?) AS coefficient FROM numeric_mass '
                        'WHERE target_ref=? ORDER BY components', ('$['+str(index)+']', ref)))

        source_total = spool.execute("SELECT coalesce(sum(members*json_array_length(payload,'$.contributions')),0) FROM cells").fetchone()[0]
        source_total += spool.execute("SELECT coalesce(sum(json_array_length(payload,'$.contributions')),0) FROM winners").fetchone()[0]

        def source_item(metadata, start, end, contribution, order):
            identity = {"target_ref": metadata["target_ref"], "unit": metadata["unit"]}
            if metadata["member_ref"] is not None:
                identity["member_ref"] = metadata["member_ref"]
            segment = {**identity, "start": start, "end": end}
            row = {**contribution, **identity, "dimension_ref": metadata["dimension_ref"]}
            if contribution.get("attribution_space") == "material_context":
                row["contributing_context_segments"] = [segment]
            else:
                row["contributing_segments"] = [segment]
            return (metadata["target_ref"], metadata["dimension_ref"], start, end, order), row

        def sensitive_details():
            query = "SELECT w.*,d.target_ref,d.member_ref,d.unit,operand.key AS ord,operand.value AS contribution FROM winners w JOIN dimensions d ON d.id=w.dimension_ref JOIN json_each(w.payload,'$.contributions') operand ORDER BY d.target_ref,d.id,w.start,w.end,operand.key"
            for row in spool.execute(query):
                yield source_item(dict(row), row["start"], row["end"], json.loads(row["contribution"]), row["ord"])

        def group_details():
            query = "SELECT e.*,operand.key AS ord,operand.value AS contribution FROM exceptions e JOIN cells c ON c.target_ref=e.target_ref AND c.kind='group' AND c.signature=e.signature JOIN json_each(c.payload,'$.contributions') operand WHERE e.sensitive=0 ORDER BY e.target_ref,e.dimension_ref,operand.key"
            for row in spool.execute(query):
                yield source_item(dict(row), 0, row["length"], json.loads(row["contribution"]), row["ord"])

        def default_details(cell):
            mask = {"subject_refs": [cell["target_ref"]]}
            query, parameters = store.context_mask_target_query(mask, cell["target_ref"])
            contributions = json.loads(cell["payload"])["contributions"]
            # SQL keyset pages return at most the requested source-page width
            # of native member rows. Prefixes skipped by the caller's global
            # offset are streamed, not retained; offset work is not constant.
            # Exception membership is tested against the derived spool, without
            # copying the authoritative native member index into it.
            cursor = ""
            page_width = max(1, details_limit or 1)
            while True:
                native_page = store.db.execute("SELECT * FROM ("+query+") "
                    "WHERE dimension_ref>? ORDER BY dimension_ref LIMIT ?",
                    (*parameters, cursor, page_width)).fetchall()
                if not native_page:
                    return
                for native in native_page:
                    cursor = native["dimension_ref"]
                    if spool.execute("SELECT 1 FROM exceptions WHERE dimension_ref=?", (cursor,)).fetchone():
                        continue
                    for index, contribution in enumerate(contributions):
                        yield source_item(dict(native), native["start"], native["end"], contribution, index)

        sources = []
        if details_limit is None or details_limit > 0:
            streams = [sensitive_details(), group_details()]
            streams.extend(default_details(dict(cell)) for cell in spool.execute(
                "SELECT * FROM cells WHERE kind='default' ORDER BY target_ref"))
            merged = heapq.merge(*streams, key=lambda item: item[0])
            stop = None if details_limit is None else details_offset+details_limit
            for _, row in islice(merged, details_offset, stop):
                row["footprint"] = _public_footprint(store, row["footprint"])
                sources.append(row)
        inactive_total = spool.execute("SELECT count(*) FROM inactive").fetchone()[0]
        sql_limit = -1 if details_limit is None else details_limit
        inactive_rows = []
        for (raw,) in spool.execute('SELECT payload FROM inactive ORDER BY target_ref,id LIMIT ? OFFSET ?',
                                     (sql_limit, details_offset)):
            row = json.loads(raw)
            if row.get('reason') == 'scientific_finding_replaced':
                witness = validity.one_witness(row['assessment_ref'])
                row.update(replacement_refs=[witness] if witness else [],
                           replacement_provenance='one_current_correction_witness')
            inactive_rows.append(row)
        inactive_rows = tuple(inactive_rows)
        pages = {"source_contributions": _page_metadata(details_offset, source_total if details_limit is None else details_limit,
                    source_total, row_unit="one_winning_original_interval_and_source_operand"),
                 "inactive_dependencies": _page_metadata(details_offset, inactive_total if details_limit is None else details_limit,
                    inactive_total, row_unit=('one_current_scientific_account_coherent_set_dependency'
                        if include_interpretation_accounts else 'one_current_annotation_coherent_set_dependency')),
                 "state_basis_sha256": basis.hexdigest(),
                 "mode": "summary" if details_limit == 0 else "paged_details"}
        root_axes, target_rows, credit = dict.fromkeys(AXES, 0.), [], 0.
        for target in targets:
            ref, mass = target["id"], masses[target["id"]]
            fraction = weights.get(ref, 1.) / total_weight if total_weight else 0.
            denominator = mass or 1
            value = totals[ref]["volume"] / denominator
            axes = {axis: value/denominator for axis, value in totals[ref]["axes"].items()}
            credit += fraction*policy.scale*value
            for axis in AXES:
                root_axes[axis] += fraction*axes[axis]
            row = {"target_ref": ref, "weight": weights.get(ref, 1.), "scoped_length": mass,
                "normalized_volume": value, "credit": value*policy.scale,
                "weighted_credit": fraction*value*policy.scale, "axis_components": axes,
                "projected_footprint_units": totals[ref]["units"],
                "footprint_meaning": "proxy_projection_extent_not_necessarily_residue_resolved_evidence",
                "inactive_dependencies_location": "projection.inactive_dependencies"}
            if target.get("target_kind") == "read_library":
                row.update(target_kind="read_library", position_mass=target["position_mass"],
                    member_count=target["member_count"], binding_version=target["binding_version"],
                    membership_sha256=target["membership_sha256"], measure=target["measure"],
                    context_extent_binding="fixed_original_position_set_v1",
                    scope_read_selection_refs=[ref for ref in effective_scope.get("read_selection_refs", ())
                        if store.get(ref)["library_ref"] == target["id"]])
            else:
                row.update(length=target["length"], unit=target["unit"])
            if "segments" in effective_scope:
                row["scope_segments"] = [dict(span) for span in effective_scope["segments"]
                                         if span["target_ref"] == ref]
            target_rows.append(row)
        if stable:
            credit = math.fsum(row['weighted_credit'] for row in target_rows)
            root_axes = {axis: math.fsum(row['weight']/total_weight*row['axis_components'][axis]
                for row in target_rows) for axis in AXES}
        return CreditProjection(credit, root_axes, tuple(target_rows), tuple(sources), policy,
                                effective_scope, pages, inactive_rows,
                                STABLE_INTEGRATION if stable else None)
    finally:
        spool.close()
