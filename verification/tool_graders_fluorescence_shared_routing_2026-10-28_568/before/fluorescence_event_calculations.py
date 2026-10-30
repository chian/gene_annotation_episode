"""One numerical authority for explicitly supplied fluorescence event analyses.

These descriptive measurements do not estimate annotation confidence. Inputs
are saved operands: this module neither acquires nor prepares measurements.
"""

from copy import deepcopy
import math

from .fluorescence_event_contracts import (
    COMPONENTS_SCHEMA,
    canonical,
    digest,
    finite,
    issue,
    validate_calculation_parameters,
    validate_components,
)
from .fluorescence_event_sheet import validate_fluorescence_sheet


_POPULATION_METRICS = (
    "retained_event_count", "parent_event_count", "parent_unknown_count",
    "evaluable_event_count", "selected_event_count", "rejected_event_count",
    "unknown_gate_event_count",
)


def _unique_issues(*groups):
    result, seen = [], set()
    for group in groups:
        for entry in group:
            identity = canonical(entry)
            if identity not in seen:
                seen.add(identity)
                result.append(deepcopy(entry))
    return result


def _request(kind, metric, *, gate_key=None, domain_key=None, channel_key=None,
             control_key=None, native_report_key=None, denominator="none"):
    return dict(kind=kind, gate_key=gate_key, domain_key=domain_key,
                channel_key=channel_key, control_key=control_key,
                native_report_key=native_report_key, denominator=denominator,
                metric=metric)


def _population(*, sample_key=None, gate_key=None, domain_key=None,
                channel_key=None, denominator="none", extent="complete"):
    return dict(sample_key=sample_key, gate_key=gate_key, domain_key=domain_key,
                channel_key=channel_key, denominator=denominator, extent=extent)


def _cell(request, value, unit, population, operands, issues=(), *, qualified=False):
    return dict(request=deepcopy(request), value=value,
                state="unavailable" if value is None else
                ("qualified" if qualified else "present"), unit=unit,
                population=deepcopy(population), operands=list(dict.fromkeys(operands)),
                issues=_unique_issues(issues))


class _Operands:
    """Indexes over validated saved data, with exact JSON-pointer provenance."""

    def __init__(self, sheet):
        self.sheet = sheet
        for collection, attribute in (
            ("input_sources", "sources"), ("samples", "samples"),
            ("channels", "channels"), ("measurement_domains", "domains"),
            ("population_definitions", "populations"), ("gate_definitions", "gates"),
            ("control_pairs", "controls"), ("native_reports", "reports"),
        ):
            setattr(self, attribute, {row["key"]: row for row in sheet[collection]})
        self.pointers = {
            (collection, row["key"]): f"sheet:/{collection}/{index}"
            for collection in (
                "input_sources", "samples", "channels", "measurement_domains",
                "population_definitions", "gate_definitions", "control_pairs",
                "native_reports",
            ) for index, row in enumerate(sheet[collection])
        }
        self.events = {}
        self.values = {}
        for index, event in enumerate(sheet["events"]):
            self.events[(event["domain_key"], event["event_ordinal"])] = event
            for column, value in enumerate(event["values"]):
                self.values[(event["domain_key"], event["event_ordinal"],
                             value["channel_key"])] = (
                    value["measurement"], f"sheet:/events/{index}/values/{column}/measurement"
                )
        self.roots = {}

    def pointer(self, collection, key):
        return self.pointers[(collection, key)]

    def root(self, gate_key):
        if gate_key not in self.roots:
            path = []
            key = gate_key
            while key not in self.roots:
                path.append(key)
                parent = self.gates[key]["parent"]
                if parent["kind"] == "population":
                    root = self.populations[parent["key"]]
                    break
                key = parent["key"]
            else:
                root = self.roots[key]
            for key in path:
                self.roots[key] = root
        return self.roots[gate_key]

    def primary(self, sample_key):
        domain = self.domains[self.samples[sample_key]["primary_domain_key"]]
        source = self.sources[domain["source_key"]]
        return domain, source

    def available(self, sample_key):
        domain, source = self.primary(sample_key)
        return domain["state"] == "available" and source["extent"] != "unavailable"

    def measurement(self, domain_key, channel_key, ordinal):
        domain = self.domains[domain_key]
        source = self.sources[domain["source_key"]]
        entry = self.values.get((domain_key, ordinal, channel_key))
        if domain["state"] != "available" or source["extent"] == "unavailable":
            return None, entry
        if entry is None or entry[0]["state"] not in {"observed", "supplied_predicted"}:
            return None, entry
        return entry[0]["value"], entry

    def gate_issue(self, code, gate, *, stage="calculation", event_ordinal=None):
        domain = self.domains.get(gate["domain_key"])
        return issue(code, stage, sample_key=gate["sample_key"], gate_key=gate["key"],
                     domain_key=gate["domain_key"], channel_key=gate["channel_key"],
                     source_key=domain["source_key"] if domain else None,
                     event_ordinal=event_ordinal)

    def primary_issues(self, gate, *, stage="calculation"):
        domain, source = self.primary(gate["sample_key"])
        result = []
        if source["extent"] == "unavailable":
            result.append(issue("source_unavailable", stage, source_key=source["key"],
                                sample_key=gate["sample_key"], domain_key=domain["key"],
                                gate_key=gate["key"]))
        if domain["state"] != "available":
            result.append(issue("measurement_domain_unavailable", stage,
                                source_key=source["key"], sample_key=gate["sample_key"],
                                domain_key=domain["key"], gate_key=gate["key"]))
        return result


def _predicate(operands, gate, ordinal):
    if gate["kind"] == "pass_all":
        return True
    value, _ = operands.measurement(gate["domain_key"], gate["channel_key"], ordinal)
    if value is None:
        return None
    lower, upper = gate["lower"], gate["upper"]
    if lower is not None and (value < lower["value"] or
                              (value == lower["value"] and not lower["inclusive"])):
        return False
    if upper is not None and (value > upper["value"] or
                              (value == upper["value"] and not upper["inclusive"])):
        return False
    return True


def _evaluate(operands):
    resolved = {}
    for requested in operands.sheet["gate_definitions"]:
        pending = []
        gate = requested
        while gate["key"] not in resolved:
            pending.append(gate)
            parent = gate["parent"]
            if parent["kind"] == "population":
                break
            gate = operands.gates[parent["key"]]
        for gate in reversed(pending):
            key, parent = gate["key"], gate["parent"]
            root = operands.root(key)
            domain, source = operands.primary(gate["sample_key"])
            available = operands.available(gate["sample_key"])
            if root["kind"] == "subset":
                universe = sorted(root["event_ordinals"])
            else:
                universe = sorted(ordinal for domain_key, ordinal in operands.events
                                  if domain_key == domain["key"])
            complete = available and (root["kind"] == "subset" or
                                      source["extent"] == "complete")
            if parent["kind"] == "population":
                parent_true, parent_false, parent_unknown = universe, [], []
            else:
                previous = resolved[parent["key"]]
                parent_true, parent_false, parent_unknown = (
                    previous["selected"], previous["rejected"], previous["unknown"]
                )
            true_set, false_set = set(parent_true), set(parent_false)
            selected, rejected, unknown, evaluable, nonevaluable = [], [], [], [], []
            gate_issues = operands.primary_issues(gate, stage="gate")
            if available and not complete:
                gate_issues.append(operands.gate_issue("incomplete_population", gate, stage="gate"))
            if parent_unknown:
                gate_issues.append(operands.gate_issue("unknown_parent_membership", gate, stage="gate"))
            if gate["kind"] == "threshold":
                gate_domain = operands.domains[gate["domain_key"]]
                if (gate_domain["state"] != "available" or
                        operands.sources[gate_domain["source_key"]]["extent"] == "unavailable"):
                    gate_issues.append(operands.gate_issue("measurement_domain_unavailable", gate, stage="gate"))
            for ordinal in universe:
                predicate = _predicate(operands, gate, ordinal)
                if ordinal in true_set:
                    (nonevaluable if predicate is None else evaluable).append(ordinal)
                if ordinal in false_set or predicate is False:
                    rejected.append(ordinal)
                elif ordinal in true_set and predicate is True:
                    selected.append(ordinal)
                else:
                    unknown.append(ordinal)
                if predicate is None and ordinal not in false_set:
                    gate_issues.append(operands.gate_issue(
                        "unknown_gate_membership", gate, stage="gate", event_ordinal=ordinal
                    ))
            resolved[key] = dict(
                gate_key=key, sample_key=gate["sample_key"], parent=deepcopy(parent),
                universe_event_ordinals=universe, parent_true=list(parent_true),
                parent_false=list(parent_false), parent_unknown=list(parent_unknown),
                selected=selected, rejected=rejected, unknown=unknown,
                parent_evaluable=evaluable, parent_nonevaluable=nonevaluable,
                population_complete=complete, issues=_unique_issues(gate_issues),
            )
    return [resolved[gate["key"]] for gate in operands.sheet["gate_definitions"]]


def evaluate_gate_membership(sheet: dict) -> list[dict]:
    """Retain original event ordinals with true/false/unknown gate membership."""
    validate_fluorescence_sheet(sheet)
    return _evaluate(_Operands(sheet))


class _Calculation:
    def __init__(self, sheet, parameters):
        self.operands = _Operands(sheet)
        self.parameters = parameters
        self.memberships = _evaluate(self.operands)
        self.membership = {row["gate_key"]: (index, row)
                           for index, row in enumerate(self.memberships)}
        self.cells = []
        self.cell_indices = {}

    def add(self, cell):
        identity = canonical(cell["request"])
        self.cell_indices[identity] = len(self.cells)
        self.cells.append(cell)
        return cell

    def saved(self, request):
        index = self.cell_indices.get(canonical(request))
        return (self.cells[index], f"components:/cells/{index}/value") if index is not None else (None, None)

    def membership_pointer(self, gate_key, field):
        return f"components:/memberships/{self.membership[gate_key][0]}/{field}"

    def extent(self, gate_key, *, include_parent=True):
        gate = self.operands.gates[gate_key]
        membership = self.membership[gate_key][1]
        if not self.operands.available(gate["sample_key"]):
            return "unavailable"
        if not membership["population_complete"]:
            return "incomplete"
        if membership["unknown"] or (include_parent and membership["parent_unknown"]):
            return "confirmed_subset"
        return "complete"

    def base_pointers(self, gate_key):
        gate = self.operands.gates[gate_key]
        root = self.operands.root(gate_key)
        domain, source = self.operands.primary(gate["sample_key"])
        return [self.operands.pointer("gate_definitions", gate_key),
                self.operands.pointer("population_definitions", root["key"]),
                self.operands.pointer("measurement_domains", domain["key"]),
                self.operands.pointer("input_sources", source["key"])]

    def population_cells(self, gate):
        key = gate["key"]
        membership = self.membership[key][1]
        available = self.operands.available(gate["sample_key"])
        incomplete = not membership["population_complete"]
        ancestry_unknown = bool(membership["parent_unknown"])
        fields = (
            ("universe_event_ordinals",), ("parent_true",), ("parent_unknown",),
            ("parent_evaluable",), ("selected",), ("parent_true", "rejected"),
            ("parent_nonevaluable",),
        )
        qualified = (
            incomplete, incomplete or ancestry_unknown, incomplete,
            incomplete or ancestry_unknown, incomplete or bool(membership["unknown"]),
            incomplete or ancestry_unknown or bool(membership["parent_nonevaluable"]),
            incomplete or ancestry_unknown,
        )
        for metric, names, uncertain in zip(_POPULATION_METRICS, fields, qualified):
            numbers = membership[names[0]]
            value = (len(set(numbers).intersection(membership[names[1]]))
                     if len(names) == 2 else len(numbers)) if available else None
            problems = self.operands.primary_issues(gate)
            if available and incomplete:
                problems.append(self.operands.gate_issue("incomplete_population", gate))
            if uncertain and ancestry_unknown:
                problems.append(self.operands.gate_issue("unknown_parent_membership", gate))
            if uncertain and membership["parent_nonevaluable"] and metric in {
                    "selected_event_count", "rejected_event_count"}:
                problems.append(self.operands.gate_issue("unknown_gate_membership", gate))
            extent = "unavailable" if not available else (
                "incomplete" if incomplete else ("confirmed_subset" if uncertain else "complete")
            )
            self.add(_cell(
                _request("population", metric, gate_key=key), value, "events",
                _population(sample_key=gate["sample_key"], gate_key=key, extent=extent),
                [self.membership_pointer(key, name) for name in names] + self.base_pointers(key),
                problems, qualified=uncertain,
            ))

    def fraction(self, gate_key, denominator, parameter_pointer):
        request = _request("fraction", "selected_fraction", gate_key=gate_key,
                           denominator=denominator)
        saved, _ = self.saved(request)
        if saved is not None:
            return saved
        gate = self.operands.gates[gate_key]
        membership = self.membership[gate_key][1]
        problems = self.operands.primary_issues(gate)
        numerator, numerator_ref = self.saved(_request(
            "population", "selected_event_count", gate_key=gate_key))
        denominator_cell, denominator_ref = self.saved(_request(
            "population", "parent_event_count" if denominator == "parent" else
            "evaluable_event_count", gate_key=gate_key))
        if self.operands.available(gate["sample_key"]):
            if not membership["population_complete"]:
                problems.append(self.operands.gate_issue("incomplete_population", gate))
            if membership["parent_unknown"]:
                problems.append(self.operands.gate_issue("unknown_parent_membership", gate))
            if denominator == "parent" and membership["parent_nonevaluable"]:
                problems.append(self.operands.gate_issue("unknown_gate_membership", gate))
            if denominator_cell["value"] == 0:
                problems.append(self.operands.gate_issue(
                    "empty_parent_population" if denominator == "parent" else
                    "empty_evaluable_population", gate))
        value = None if problems else numerator["value"] / denominator_cell["value"]
        qualified = denominator == "evaluable" and bool(membership["parent_nonevaluable"])
        if qualified:
            problems.append(self.operands.gate_issue("unknown_gate_membership", gate))
        population = _population(sample_key=gate["sample_key"], gate_key=gate_key,
                                 denominator=denominator, extent=self.extent(gate_key))
        fraction = self.add(_cell(
            request, value, "dimensionless", population,
            [numerator_ref, denominator_ref, parameter_pointer,
             self.membership_pointer(gate_key, "parent_unknown"),
             self.membership_pointer(gate_key, "parent_nonevaluable"),
             self.membership_pointer(gate_key, "population_complete")],
            problems, qualified=qualified,
        ))
        _, fraction_ref = self.saved(request)
        self.add(_cell(
            _request("fraction", "selected_percent", gate_key=gate_key, denominator=denominator),
            None if value is None else 100 * value, "percent", population,
            [fraction_ref], problems, qualified=qualified,
        ))
        return fraction

    def intensity(self, request, parameter_pointer):
        gate_key, domain_key, channel_key = (
            request["gate_key"], request["domain_key"], request["channel_key"]
        )
        gate = self.operands.gates[gate_key]
        membership = self.membership[gate_key][1]
        domain = self.operands.domains[domain_key]
        channel = self.operands.channels[channel_key]
        problems = self.operands.primary_issues(gate)
        if not membership["population_complete"] and self.operands.available(gate["sample_key"]):
            problems.append(self.operands.gate_issue("incomplete_population", gate))
        if membership["unknown"]:
            problems.append(self.operands.gate_issue("unknown_gate_membership", gate))
        finite_values, finite_pointers, missing_pointers = [], [], []
        missing_count = 0
        for ordinal in membership["selected"]:
            value, entry = self.operands.measurement(domain_key, channel_key, ordinal)
            if value is None:
                missing_count += 1
                if entry is not None:
                    missing_pointers.append(entry[1])
                code = ("measurement_domain_unavailable" if entry is None or
                        domain["state"] != "available" or
                        self.operands.sources[domain["source_key"]]["extent"] == "unavailable"
                        else "invalid_numeric_token" if entry[0]["state"] == "invalid"
                        else "channel_missing")
                problems.append(issue(
                    code, "calculation", source_key=domain["source_key"],
                    sample_key=gate["sample_key"], domain_key=domain_key,
                    channel_key=channel_key, event_ordinal=ordinal, gate_key=gate_key,
                ))
            else:
                finite_values.append(value)
                finite_pointers.append(entry[1] + "/value")
        available = self.operands.available(gate["sample_key"])
        qualified = bool(problems)
        extent = self.extent(gate_key, include_parent=False)
        if extent == "complete" and missing_count:
            extent = "confirmed_subset"
        population = _population(sample_key=gate["sample_key"], gate_key=gate_key,
                                 domain_key=domain_key, channel_key=channel_key,
                                 denominator="selected_finite", extent=extent)
        base = [parameter_pointer, self.membership_pointer(gate_key, "selected"),
                self.operands.pointer("measurement_domains", domain_key),
                self.operands.pointer("input_sources", domain["source_key"]),
                self.operands.pointer("channels", channel_key)]

        def add(metric, value, unit, pointers, extra=()):
            cell_request = _request("intensity", metric, gate_key=gate_key,
                                    domain_key=domain_key, channel_key=channel_key)
            result = self.add(_cell(cell_request, value if available else None,
                                    unit, population, base + pointers,
                                    _unique_issues(problems, extra),
                                    qualified=qualified or bool(extra)))
            return result, self.saved(cell_request)[1]

        count = len(finite_values)
        _, count_ref = add("selected_intensity_count", count, "events", finite_pointers)
        add("selected_intensity_missing_count", missing_count, "events", missing_pointers)
        overflow = [issue("derived_numeric_overflow", "calculation",
                          source_key=domain["source_key"], sample_key=gate["sample_key"],
                          domain_key=domain_key, channel_key=channel_key, gate_key=gate_key)]
        total = _finite_sum(finite_values)
        sum_issues = overflow if total is None else []
        _, sum_ref = add("selected_intensity_sum", total, channel["unit"],
                         finite_pointers + [count_ref], sum_issues)
        mean = None
        if count:
            # Scaling only when the unscaled sum overflows preserves a finite
            # arithmetic mean, without inventing a finite unscaled sum.
            mean = total / count if total is not None else _scaled_sum(finite_values, count)
            if not finite(mean):
                mean = None
        mean_issues = overflow if count and (total is None or mean is None) else []
        add("selected_intensity_mean", mean, channel["unit"],
            [sum_ref, count_ref] + finite_pointers, mean_issues)
        median = None
        median_issues = []
        if count:
            ordered = sorted(finite_values)
            middle = count // 2
            if count % 2:
                median = ordered[middle]
            else:
                pair = [ordered[middle - 1], ordered[middle]]
                middle_sum = _finite_sum(pair)
                median = (middle_sum / 2 if middle_sum is not None else
                          _scaled_sum(pair, 2))
                if middle_sum is None:
                    median_issues = overflow
            if not finite(median):
                median, median_issues = None, overflow
        add("selected_intensity_median", median, channel["unit"],
            [count_ref] + finite_pointers, median_issues)

    def control_compatible(self, pair):
        expected_basis = pair["comparison_basis"]
        target = self.operands.gates[pair["target_gate_key"]]
        control = self.operands.gates[pair["control_gate_key"]]
        pointers = []
        for gate in (target, control):
            root = self.operands.root(gate["key"])
            primary, _ = self.operands.primary(gate["sample_key"])
            pointers.extend([self.operands.pointer("population_definitions", root["key"]),
                             self.operands.pointer("measurement_domains", primary["key"])])
            if root["kind"] != "all" or primary["comparison_basis"] != expected_basis:
                return False, pointers
        while True:
            pointers.extend([self.operands.pointer("gate_definitions", target["key"]),
                             self.operands.pointer("gate_definitions", control["key"])])
            if target["kind"] != control["kind"]:
                return False, pointers
            if target["kind"] == "threshold":
                if target["lower"] != control["lower"] or target["upper"] != control["upper"]:
                    return False, pointers
                channels = [self.operands.channels[gate["channel_key"]] for gate in (target, control)]
                domains = [self.operands.domains[gate["domain_key"]] for gate in (target, control)]
                pointers.extend(self.operands.pointer("channels", channel["key"]) for channel in channels)
                pointers.extend(self.operands.pointer("measurement_domains", domain["key"]) for domain in domains)
                if any(channel["analyte"] is None or channel["unit"] is None for channel in channels):
                    return False, pointers
                if channels[0]["unit"] != channels[1]["unit"]:
                    return False, pointers
                if any(channels[0]["analyte"][field] != channels[1]["analyte"][field]
                       for field in ("namespace", "identifier")):
                    return False, pointers
                if any(domain["comparison_basis"] != expected_basis for domain in domains):
                    return False, pointers
            left, right = target["parent"], control["parent"]
            if left["kind"] != right["kind"]:
                return False, pointers
            if left["kind"] == "population":
                return True, pointers
            target, control = self.operands.gates[left["key"]], self.operands.gates[right["key"]]

    def control(self, request, parameter_pointer):
        pair = self.operands.controls[request["control_key"]]
        compatible, compatibility_pointers = self.control_compatible(pair)
        left, left_ref = self.saved(_request(
            "fraction", "selected_fraction", gate_key=pair["target_gate_key"],
            denominator=pair["denominator"]))
        right, right_ref = self.saved(_request(
            "fraction", "selected_fraction", gate_key=pair["control_gate_key"],
            denominator=pair["denominator"]))
        problems = _unique_issues(left["issues"], right["issues"])
        if not compatible:
            problems.append(issue("control_pair_incompatible", "calculation", control_key=pair["key"]))
        available = compatible and left["value"] is not None and right["value"] is not None
        value = left["value"] - right["value"] if available else None
        qualified = left["state"] == "qualified" or right["state"] == "qualified"
        extents = {left["population"]["extent"], right["population"]["extent"]}
        extent = "unavailable" if not compatible else next(
            item for item in ("unavailable", "incomplete", "confirmed_subset", "complete") if item in extents
        )
        population = _population(denominator="paired_controls", extent=extent)
        difference_request = _request("control", "control_difference_fraction", control_key=pair["key"])
        self.add(_cell(difference_request, value, "dimensionless", population,
                       [left_ref, right_ref, parameter_pointer,
                        self.operands.pointer("control_pairs", pair["key"])] + compatibility_pointers,
                       problems, qualified=qualified))
        _, difference_ref = self.saved(difference_request)
        points = None if value is None else 100 * value
        points_request = _request("control", "control_difference_percentage_points", control_key=pair["key"])
        self.add(_cell(points_request, points, "percentage_points", population,
                       [difference_ref], problems, qualified=qualified))
        if request["include_legacy_clipping"]:
            _, points_ref = self.saved(points_request)
            self.add(_cell(
                _request("control", "legacy_nonnegative_difference_percentage_points", control_key=pair["key"]),
                None if points is None else max(0, points), "percentage_points", population,
                [points_ref, parameter_pointer + "/include_legacy_clipping"],
                problems, qualified=qualified,
            ))

    def native_comparison(self, report_key, parameter_pointer):
        report = self.operands.reports[report_key]
        report_ref = self.operands.pointer("native_reports", report_key)
        native_missing = [issue("native_report_uninterpretable", "calculation",
                                source_key=report["source_key"])] if report["value"] is None else []
        native_request = _request("native_comparison", "native_value", native_report_key=report_key)
        self.add(_cell(native_request, report["value"], report["unit"],
                       _population(extent="unavailable" if native_missing else "complete"),
                       [report_ref, report_ref + "/value", report_ref + "/unit", parameter_pointer],
                       native_missing))
        linked, linked_ref = self.saved(report["component_request"]) if report["component_request"] else (None, None)
        available = (report["value"] is not None and linked is not None and
                     linked["value"] is not None and report["unit"] is not None and
                     linked["unit"] == report["unit"])
        try:
            value = report["value"] - linked["value"] if available else None
        except OverflowError:
            value = None
        problems = []
        if not available:
            problems.append(issue("native_report_uninterpretable", "calculation",
                                  source_key=report["source_key"]))
        elif not finite(value):
            value = None
            problems.append(issue("derived_numeric_overflow", "calculation", source_key=report["source_key"]))
        if linked is not None:
            problems = _unique_issues(linked["issues"], problems)
        _, native_ref = self.saved(native_request)
        pointers = [native_ref, report_ref + "/component_request", report_ref + "/decimal_places"]
        if linked_ref is not None:
            pointers.append(linked_ref)
        self.add(_cell(
            _request("native_comparison", "native_minus_calculated", native_report_key=report_key),
            value, report["unit"],
            _population(extent=linked["population"]["extent"] if available else "unavailable"),
            pointers, problems, qualified=available and linked["state"] == "qualified",
        ))


def _finite_sum(values):
    try:
        value = math.fsum(values)
    except (OverflowError, ValueError):
        return None
    return value if finite(value) else None


def _scaled_sum(values, count):
    try:
        return _finite_sum([value / count for value in values])
    except OverflowError:
        # A JSON integer may be finite but outside binary floating-point range.
        return None


def calculate_fluorescence_sheet(sheet: dict, *, parameters: dict) -> dict:
    """Calculate requested descriptive cells from saved numerical operands only."""
    validate_fluorescence_sheet(sheet)
    validate_calculation_parameters(parameters, sheet=sheet)
    calculation = _Calculation(sheet, parameters)
    for gate in sheet["gate_definitions"]:
        calculation.population_cells(gate)
    for index, request in enumerate(parameters["fraction_requests"]):
        calculation.fraction(request["gate_key"], request["denominator"],
                             f"parameters:/fraction_requests/{index}")
    for index, request in enumerate(parameters["intensity_requests"]):
        calculation.intensity(request, f"parameters:/intensity_requests/{index}")
    for index, request in enumerate(parameters["control_requests"]):
        pair = calculation.operands.controls[request["control_key"]]
        for gate_key in (pair["target_gate_key"], pair["control_gate_key"]):
            calculation.fraction(gate_key, pair["denominator"],
                                 f"parameters:/control_requests/{index}")
    for index, request in enumerate(parameters["control_requests"]):
        calculation.control(request, f"parameters:/control_requests/{index}")
    for index, report_key in enumerate(parameters["native_comparison_requests"]):
        calculation.native_comparison(report_key, f"parameters:/native_comparison_requests/{index}")
    problems = _unique_issues(sheet["issues"], *(row["issues"] for row in calculation.memberships),
                              *(cell["issues"] for cell in calculation.cells))
    if not any(cell["state"] != "unavailable" for cell in calculation.cells):
        status = "unavailable"
    elif problems or any(cell["state"] != "present" for cell in calculation.cells):
        status = "partial"
    else:
        status = "calculated"
    result = dict(schema=COMPONENTS_SCHEMA, sheet_sha256=digest(sheet),
                  parameters=deepcopy(parameters), memberships=calculation.memberships,
                  cells=calculation.cells, status=status, issues=problems)
    validate_components(result, sheet=sheet)
    return result
