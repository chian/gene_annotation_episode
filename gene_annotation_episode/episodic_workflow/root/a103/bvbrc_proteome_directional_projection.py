"""Small requested projections of already produced directional measurements.

No native parsing, sheet construction, geometry, numerical calculation, service
or process execution occurs here. Saved returns additionally authenticate through
the provider's check-only port and the host's original immutable publication.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from . import bvbrc_proteome_directional_fact_contracts as c
from . import bvbrc_proteome_fact_contracts as old
from .bvbrc_proteome_bundle_projection import _Projection, _unique, _token
from .bvbrc_appservice_contracts import validate_contract

_OBSERVED = "/sheet/directional_sheet_result/sheet/reader_results"
_CALCULATED = "/components/directional/components/reports"
_REQUEST_CODES = {"proteome_directional_requested_target_missing", "proteome_directional_requested_value_unavailable"}
_TRACE_UNITS = {name: ("gap_run" if name.endswith("gap_runs") else
    "displayed_position" if name.endswith("non_gap_symbols") else
    "alignment_column" if name in {"alignment_columns", "query_gap_columns", "subject_gap_columns"} else
    "paired_column") for name in c.TRACE_COUNTS}


def _same(a, b):
    return old.canonical(a) == old.canonical(b)


def _require(condition, path=""):
    old.require(condition, "directional_saved_projection_conflict", path)


def _at(value, pointer):
    """Follow a generated, finite-table pointer. Selectors never supply pointers."""
    if pointer is None:
        return None
    try:
        for token in pointer.lstrip("/").split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            value = value[int(token)] if type(value) is list else value[token]
        return value
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _availability(cell):
    if cell is None:
        return "unavailable"
    return {"value": "available", "present": "available", "conflict": "incompatible", "invalid": "invalid"}.get(cell["state"], "unavailable")


def _native(cell, *, decimal=False):
    return {"state": None if cell is None else cell["state"], "value": None if cell is None or cell["state"] != "present"
            else c.exact_decimal(cell["value"]) if decimal else cell["value"]}


def _cell(cell, *, unit, ratio=False):
    value = None if cell is None else deepcopy(cell["value"])
    if ratio and value is not None:
        value = {"numerator": value["numerator"], "denominator": value["denominator"],
                 "rendered_decimal": c.exact_decimal(value["decimal"])}
    return {"state": None if cell is None else cell["state"], "value": value,
        "unit": unit if cell is None else cell["unit"], "reason_codes": [] if cell is None else deepcopy(cell["reasons"]),
        "uncertainty": None}


def _expectation(cell):
    if cell is None:
        return None
    if cell["state"] != "present":
        return cell["state"]
    number = c.exact_decimal(cell["value"])
    return "invalid" if number["sign"] else ("printed_zero_precision_unknown" if number["digits"] == [0]
                                                else "positive_reported_decimal")


class _LegacyProjection(_Projection):
    """Read the unchanged v1 projection with references into the v2 envelope."""
    def __init__(self, *args, global_root, **kwargs):
        self.global_root = global_root
        super().__init__(*args, **kwargs)

    def ref(self, kind, pointer):
        if pointer == "/components" or pointer.startswith("/components/"):
            pointer = "/components/legacy" + pointer[len("/components"):]
        for name in ("missing_requirements", "diagnostics"):
            prefix = "/" + name + "/"
            if pointer.startswith(prefix):
                index, sep, tail = pointer[len(prefix):].partition("/")
                row = self.root[name][int(index)]
                if row not in self.global_root[name]:
                    self.global_root[name].append(deepcopy(row))
                pointer = prefix + str(self.global_root[name].index(row)) + ("/" + tail if sep else "")
        return super().ref(kind, pointer)


class _DirectionalProjection:
    def __init__(self, sheet, components, parameters, form, requirements, diagnostics):
        self.sheet, self.components, self.parameters, self.form = sheet, components, parameters, form
        self.root = {"sheet": sheet, "components": components,
            "missing_requirements": _unique(requirements), "diagnostics": _unique(diagnostics)}
        self.aid = parameters["analysis_id"]
        self.generated_requirements, self.generated_diagnostics = [], []
        self.field_requirements = {}
        self.field_diagnostics = {}

    def ref(self, kind, pointer):
        return old.encode_reference(kind, self.aid, pointer)

    def operand(self, field):
        return self.ref("source_field", _OBSERVED + "/" + str(field["report_ordinal"]) + field["pointer"])

    def locate(self, selector):
        index = next((i for i, row in enumerate(self.parameters["directional_documents"])
            if row["document_id"] == selector["document_id"]), None)
        _require(index is not None, "/document_id")
        resolution = next((row for row in self.sheet["input_resolution"]
            if row["selector_kind"] == "directional_document" and row["selection_index"] == index), None)
        _require(resolution is not None, "/sheet/input_resolution")
        r = resolution["result_index"]
        report_path = None if r is None else _OBSERVED + "/" + str(r)
        calculated_path = None if r is None else _CALCULATED + "/" + str(r)
        op, cp = report_path, calculated_path
        for key, collection in (("query_ordinal", "queries"), ("subject_ordinal", "subjects"),
            ("hsp_ordinal", "hsps"), ("block_ordinal", "traceback_blocks"),
            ("description_ordinal", "descriptions"), ("database_header_ordinal", "database_headers"),
            ("statistic_ordinal", "statistics")):
            if key in selector and op is not None:
                suffix = "/" + collection + "/" + str(selector[key])
                op += suffix
                cp += suffix.replace("/traceback_blocks/", "/blocks/")
        retained_path = None if r is None else '/sheet/directional_results/' + str(r)
        retained = _at(self.root, retained_path)
        native = _at(self.root, op)
        retained_target = None if op is None else _at(self.root, retained_path + op[len(report_path):])
        return dict(selection=self.parameters["directional_documents"][index], resolution=resolution,
            report_ordinal=r, report_path=report_path, native_path=op, calculated_path=cp,
            native=native, target_exists=retained_target is not None, calculated=_at(self.root, cp),
            report=_at(self.root, report_path) or retained,
            report_source_path=report_path if _at(self.root, report_path) is not None else retained_path)

    def context(self, selector, located, pointer=None, *, operands=(), numerical=False):
        report, r = located["report"], located["report_ordinal"]
        source = None if report is None else report["source"]
        declared = located["selection"]["declared_format"]["version"]
        resolution = located["resolution"]
        declaration = None if report is None else ("unconstrained_version" if declared is None else
            "conflicting_version" if any(row["reason_code"] == "proteome_directional_declared_version_conflict"
                and row["requirement_id"] in resolution["requirement_ids"] for row in self.root["missing_requirements"])
            else "matching_version")
        subject_path = None if r is None or "subject_ordinal" not in selector else (
            _CALCULATED + f"/{r}/queries/{selector['query_ordinal']}/subjects/{selector['subject_ordinal']}")
        subject = _at(self.root, subject_path)
        result = dict(target={"document_id": selector["document_id"], **{key: r if key == "report_ordinal"
            else selector.get(key) for key in c.ORDINALS}}, native_source_ref=None if source is None else source["content"]["source_ref"],
            value_ref=None if pointer is None else self.ref("field", pointer),
            parameter_ref=self.ref("parameter", "/components/directional/components/parameters")
                if numerical and _at(self.root, "/components/directional/components/parameters") is not None else None,
            operand_refs=list(dict.fromkeys(operands)), report_parse_state=None if report is None else report["parse_state"],
            body_complete=None if source is None else source["body_complete"],
            object_complete=None if source is None else source["object_complete"], declaration_state=declaration,
            operand_binding="unbound", supports=[], mapping_state=None if subject is None else subject["correspondence"]["mapping_state"],
            qualification_refs=[], requirement_refs=[self.ref("requirement", "/missing_requirements/" + str(i))
                for i, row in enumerate(self.root["missing_requirements"]) if row["requirement_id"] in resolution["requirement_ids"]])
        # Exact operand overlap identifies relevant saved numerical issues. An
        # array membership operand does not qualify every descendant quantity.
        scope = selector['scope'] if selector['scope'] not in {'correspondence', 'compatible_pairs'} else 'subject'
        if scope in {'report', 'query', 'subject', 'hsp', 'block'}:
            issue_selector = {**selector, 'scope': scope, 'layer': 'numerical'}
            for issue, path in self.issue_locations(issue_selector, located):
                if any(self.operand(field) in result['operand_refs'] for field in issue['fields']):
                    result['qualification_refs'].append(self.ref('qualification', path))
        if report is not None:
            for index, issue in enumerate(report['issues']):
                if issue['code'] in {'source_body_incomplete', 'source_object_incomplete', 'source_object_completeness_unknown'}:
                    result['qualification_refs'].append(self.ref('qualification', located['report_source_path'] + '/issues/' + str(index)))
        result['qualification_refs'] = list(dict.fromkeys(result['qualification_refs']))
        return result

    def support(self, context, support, path, basis):
        if support is not None:
            context["supports"].append(dict(basis=basis, support_ref=self.ref("population", path),
                included_block_count=len(support["included_blocks"]), excluded_block_count=len(support["excluded_blocks"]),
                hsps_without_traceback_count=len(support["hsps_without_traceback"]),
                complete_for_displayed_blocks=support["complete_for_displayed_blocks"]))

    def compatible_support(self, context, row, path):
        if row is not None:
            self.support(context, row["correspondence"]["pair_geometry_support"], path + "/correspondence/pair_geometry_support", "pair_geometry")

    def coverage_location(self, selector, located):
        metric = selector.get("metric", selector.get("collection"))
        suffix = "/" + metric if selector["scope"] == "query" else "/coverage/" + metric
        path = None if located["calculated_path"] is None else located["calculated_path"] + suffix
        return _at(self.root, path), path

    @staticmethod
    def population(counts, *, compatible=False, graph=None):
        names = ("resolved_pairs", "unresolved_pairs", "stop_containing_pairs") if compatible else (
            "resolved_amino_acid_pairs", "unresolved_symbol_pairs", "stop_containing_pairs")
        cells = [None if graph is None else graph["distinct_pair_count"]] if compatible else [None if counts is None else counts["paired_columns"]]
        cells += [None if counts is None else counts[name] for name in names]
        return {name: None if cell is None else cell["value"] for name, cell in zip(
            ("total_pairs", "resolved_pairs", "unresolved_pairs", "stop_containing_pairs"), cells)}

    @staticmethod
    def count_unit(scope, metric):
        if scope in {"hsp", "block"} and metric in _TRACE_UNITS:
            return _TRACE_UNITS[metric]
        if metric.startswith("displayed_"):
            return metric[len("displayed_"):-len("_count")] + "_occurrence"
        if metric in {"reported_paired_column_count", "reported_nonidentical_paired_count", "nonoverlapping_hsp_reported_identity_count"}:
            return "paired_column"
        if metric == "nonoverlapping_hsp_reported_alignment_columns": return "alignment_column"
        if metric == "repeated_pair_occurrence_count": return "pair_representation"
        return "coordinate_pair"

    @staticmethod
    def native_unit(scope, metric):
        if metric in {"length", "letter_count"}: return "aa"
        if metric == "sequence_count": return "sequence_occurrence"
        if metric in {"bit_score", "bits"}: return "bits"
        if metric in {"expect", "evalue"}: return "expected_count"
        if metric == "raw_score": return "native_raw_score"
        if metric.endswith("printed_percent"): return "percent"
        if metric == "expect_group_count": return "native_expect_group_count"
        if scope == "statistic": return "native_reported_integer" if metric == "integer_value" else "native_reported_decimal"
        return "alignment_column"

    def numerical(self, selector, located):
        kind, scope, metric = selector["kind"], selector["scope"], selector["metric"]
        row, path = located["calculated"], located["calculated_path"]
        if kind == "directional_coverage":
            union, path = self.coverage_location(selector, located)
            count, ratio = (None, None) if union is None else (union["count"], union["coverage"])
            operands = [] if ratio is None else [self.operand(f) for f in ratio["inputs"]]
            context = self.context(selector, located, path if union is not None else None, operands=operands, numerical=True)
            side = "subject" if metric.startswith("subject_") else "query"
            denominator = None if located["report_path"] is None else located["report_path"] + f"/queries/{selector['query_ordinal']}"
            if denominator is not None and side == "subject": denominator += f"/subjects/{selector['subject_ordinal']}"
            if denominator is not None: denominator += "/length"
            if union is not None:
                basis = "reported_interval" if "reported_interval" in metric else "trace_occupied" if "trace_occupied" in metric else "trace_paired"
                self.support(context, union["support"], path + "/support", basis)
            return dict(availability=_availability(ratio), quantity=metric, context=context,
                count=_cell(count, unit="displayed_position"), reported_length=_native(None if union is None else union["reported_length"]),
                denominator_ref=None if union is None else self.ref("source_field", denominator),
                coverage=_cell(ratio, unit="fraction", ratio=True), interval_count=0 if union is None else len(union["intervals"]),
                intervals_ref=None if union is None else self.ref("population", path + "/intervals"))
        suffix = "/" + metric
        if scope == "hsp":
            suffix = ("/trace_counts/" if metric in c.TRACE_COUNTS else "/trace_fractions/" if metric in c.TRACE_FRACTIONS else "/reported/") + metric
        elif scope == "block": suffix = ("/counts/" if kind == "directional_count" else "/fractions/") + metric
        elif scope == "correspondence": suffix = "/correspondence/" + metric
        elif scope == "compatible_pairs": suffix = "/compatible_pair_counts/" + metric
        pointer = None if path is None else path + suffix
        cell = _at(self.root, pointer)
        context = self.context(selector, located, pointer if cell is not None else None,
            operands=[] if cell is None else [self.operand(f) for f in cell["inputs"]], numerical=True)
        if scope == "hsp" and metric in (*c.TRACE_COUNTS, *c.TRACE_FRACTIONS) and row is not None:
            self.support(context, row["strings_support"], path + "/strings_support", "strings")
        if scope in {"correspondence", "compatible_pairs"} or metric.startswith("compatible_unique_pair_"):
            self.compatible_support(context, row, path)
        fact = dict(availability=_availability(cell), quantity=metric, context=context,
            cell=_cell(cell, unit="fraction" if kind == "directional_fraction" else self.count_unit(scope, metric),
                       ratio=kind == "directional_fraction"))
        if kind == "directional_fraction":
            population = None
            if metric in c.TRACE_FRACTIONS:
                population = self.population(None if row is None else row["trace_counts" if scope == "hsp" else "counts"])
            elif metric.startswith("compatible_unique_pair_"):
                population = self.population(None if row is None else row["compatible_pair_counts"], compatible=True,
                                             graph=None if row is None else row["correspondence"])
            fact["pair_population"] = population
        return fact

    def native(self, selector, located):
        metric, scope = selector["metric"], selector["scope"]
        path = None if located["native_path"] is None else located["native_path"] + "/" + metric
        cell = _at(self.root, path)
        decimal = selector["kind"] == "directional_native_decimal"
        group = scope == "hsp" and metric == "expect"
        operands = [] if cell is None else [self.ref("source_field", path)]
        group_path = None if located["native_path"] is None else located["native_path"] + "/expect_group_count"
        if cell is not None and group: operands.append(self.ref("source_field", group_path))
        result = dict(availability=_availability(cell), quantity=metric,
            context=self.context(selector, located, path if cell is not None else None, operands=operands),
            cell=_native(cell, decimal=decimal), unit=self.native_unit(scope, metric),
            statistic_kind=located["native"]["kind"] if scope == "statistic" and located["native"] is not None else None)
        if decimal:
            result.update(expectation_display=_expectation(cell) if metric in {"expect", "evalue"} else None,
                expect_group_count=_native(_at(self.root, group_path)) if group else None)
        return result

    def state(self, selector, located):
        metric = selector["metric"]
        path = located["native_path"] if metric in {"parse_state", "boundary"} else located["calculated_path"]
        if metric in {"body_complete", "object_complete"}: path = None if located["report_path"] is None else located["report_path"] + "/source"
        if metric == "operand_binding": path = "/sheet/numerical_sheet/directional_operand_binding"
        elif path is not None:
            path += ("/correspondence" if metric == "mapping_state" else "/native_scores" if metric == "expectation_display" else "") + "/" + metric
        value = _at(self.root, path) if located["native"] is not None else None
        return dict(availability="unavailable" if value is None else "available", quantity=metric,
            context=self.context(selector, located, path if value is not None else None,
                numerical=path is not None and path.startswith("/components/")),
            value_boolean=value if metric == "body_complete" else None,
            value_code=None if metric == "body_complete" else value)

    def extremum(self, selector, located):
        path = None if located["calculated_path"] is None else located["calculated_path"] + "/" + selector["metric"]
        value = _at(self.root, path)
        field = None if value is None else value["selected_field"]
        pointer = None if field is None else _OBSERVED + "/" + str(field["report_ordinal"]) + field["pointer"]
        cell = _at(self.root, pointer)
        raw = selector["metric"] == "maximum_reported_hsp_raw_score"
        expect = selector["metric"] == "minimum_reported_hsp_expectation"
        group_path = None if pointer is None else pointer.rsplit("/", 1)[0] + "/expect_group_count"
        operands = [] if field is None else [self.operand(field)]
        if expect and group_path is not None: operands.append(self.ref("source_field", group_path))
        return dict(availability=_availability(value), quantity=selector["metric"],
            context=self.context(selector, located, path if value is not None else None, operands=operands, numerical=True),
            state=None if value is None else value["state"], native_integer=_native(cell) if raw and cell is not None else None,
            native_decimal=_native(cell, decimal=True) if not raw and cell is not None else None,
            selected_operand_ref=None if field is None else self.operand(field),
            tied_hsp_count=0 if value is None else len(value["tied_hsps"]),
            excluded_hsp_count=0 if value is None else len(value["excluded_hsps"]),
            tied_hsps_ref=None if value is None else self.ref("population", path + "/tied_hsps"),
            excluded_hsps_ref=None if value is None else self.ref("population", path + "/excluded_hsps"),
            reason_codes=[] if value is None else deepcopy(value["reason_codes"]),
            expectation_display=_expectation(cell) if expect else None,
            expect_group_count=_native(_at(self.root, group_path)) if expect and field is not None else None)

    def issue_locations(self, selector, located):
        layer = selector["layer"]
        path = located["native_path"] if layer == "reader" else located["calculated_path"]
        name = "issues" if layer == "reader" else "diagnostics"
        issues = []
        if path is not None:
            issues.extend((row, path + "/" + name + "/" + str(i))
                for i, row in enumerate(_at(self.root, path + "/" + name) or []))
        if layer == "numerical" and selector["scope"] == "report":
            r = located["report_ordinal"]
            for root in ("/sheet/directional_sheet_result/sheet/diagnostics", "/components/directional/components/diagnostics"):
                for i, row in enumerate(_at(self.root, root) or []):
                    if any(f["report_ordinal"] == r for group in ("fields", "columns", "hsps") for f in row[group]):
                        issues.append((row, root + "/" + str(i)))
        return issues

    def issue_item(self, layer, row, path):
        return dict(layer=layer, code=row["code"], issue_ref=self.ref("qualification", path),
            operand_refs=[self.ref("source_field", path + "/locations/" + str(i)) for i in range(len(row["locations"]))]
                if layer == "reader" else [self.operand(f) for f in row["fields"]],
            column_keys=[] if layer == "reader" else deepcopy(row["columns"]),
            hsp_keys=[] if layer == "reader" else deepcopy(row["hsps"]))

    def page(self, selector, located):
        kind, scope = selector["kind"], selector["scope"]
        path, collection, rows = located["calculated_path"], None, None
        supports = None
        if kind == "directional_intervals":
            union, path = self.coverage_location(selector, located)
            collection = selector["metric"]
            if union is not None:
                rows = [dict(start=a, end=b) for a, b in union["intervals"]]
                supports = (union["support"], path + "/support", "reported_interval" if "reported_interval" in collection else
                    "trace_occupied" if "trace_occupied" in collection else "trace_paired")
            if path is not None: path += "/intervals"
        elif kind == "directional_issues":
            collection = selector["layer"]
            base = located["native_path"] if collection == "reader" else located["calculated_path"]
            path = None if base is None else base + ("/issues" if collection == "reader" else "/diagnostics")
            if _at(self.root, path) is not None:
                rows = [self.issue_item(collection, row, pointer) for row, pointer in self.issue_locations(selector, located)]
        elif kind == "directional_support":
            collection, member = selector["collection"], selector["member"]
            if collection in c.EXTREMA:
                path = None if path is None else path + "/" + collection
            elif collection in (*c.COVERAGES, "any_displayed_subject_query_paired_union"):
                _, path = self.coverage_location(selector, located)
                if path is not None: path += "/support"
            elif path is not None:
                path += ("/correspondence" if scope == "subject" else "") + "/" + collection
            container = _at(self.root, path)
            if container is not None:
                block = member in {"included_blocks", "excluded_blocks"}
                rows = [dict(block_key=deepcopy(k) if block else None, hsp_key=None if block else deepcopy(k)) for k in container[member]]
                if collection not in c.EXTREMA:
                    basis = ("strings" if collection == "strings_support" else "pair_geometry" if collection == "pair_geometry_support" else
                        "reported_interval" if "reported_interval" in collection else "trace_occupied" if "trace_occupied" in collection else "trace_paired")
                    supports = (container, path, basis)
            if path is not None: path += "/" + member
        else:
            collection = {"directional_columns": "columns", "directional_edges": "edges", "directional_conflicts": "conflicts"}[kind]
            if path is not None: path += ("/correspondence" if scope == "subject" else "") + "/" + collection
            rows = deepcopy(_at(self.root, path))
            if kind == "directional_conflicts" and rows is not None:
                for row in rows:
                    for side in ("query_intervals", "subject_intervals"):
                        row[side] = [dict(start=a, end=b) for a, b in row[side]]
        context = self.context(selector, located, path if rows is not None else None, numerical=selector.get("layer") != "reader")
        if supports is not None: self.support(context, *supports)
        if kind in {"directional_edges", "directional_conflicts"}:
            self.compatible_support(context, located["calculated"], located["calculated_path"])
        offset, limit = selector["offset"], selector["limit"]
        items = [] if rows is None else rows[offset:offset + limit]
        count = 0 if rows is None else len(rows)
        return dict(availability="unavailable" if rows is None else "available", context=context, collection=collection,
            offset=offset, limit=limit, total_count=count, returned_count=len(items),
            next_offset=offset + len(items) if offset + len(items) < count else None, items=items)

    def field_failure(self, field, selector, reason):
        code = "proteome_directional_" + reason
        payload = dict(version="bvbrc_proteome_directional_requirement_v2", analysis_id=self.aid,
            reason_code=code, role="proteome_requested_projection", field=field, selection=deepcopy(selector), source_refs=[])
        requirement = dict(requirement_id="proteome_requirement_" + hashlib.sha256(old.canonical(payload).encode()).hexdigest(),
            kind="scientific_metadata", role="proteome_requested_projection", source_refs=[], reason_code=code)
        diagnostic = dict(code=code, phase="publication", path="/facts/" + _token(field), severity="qualification", evidence_refs=[])
        self.generated_requirements.append(requirement)
        self.generated_diagnostics.append(diagnostic)
        for name, row in (("missing_requirements", requirement), ("diagnostics", diagnostic)):
            if row not in self.root[name]: self.root[name].append(row)
        self.field_requirements[field] = requirement["requirement_id"]
        self.field_diagnostics[field] = diagnostic

    def requirement_rows(self):
        result = []
        selections = self.parameters["directional_documents"]
        for i, row in enumerate(self.root["missing_requirements"]):
            if row["reason_code"] not in c.BINDING_CODES: continue
            document, field_ref = None, None
            owners = [selections[r["selection_index"]]["document_id"] for r in self.sheet["input_resolution"]
                if r["selector_kind"] == "directional_document" and row["requirement_id"] in r["requirement_ids"]]
            if len(set(owners)) == 1: document = owners[0]
            fields = [field for field, rid in self.field_requirements.items() if rid == row["requirement_id"]]
            if fields:
                _require(len(fields) == 1)
                field = fields[0]
                document = self.form["properties"][field]["x-bvbrc-proteome"]["document_id"]
                field_ref = self.ref("field", "/facts/" + _token(field))
            result.append(dict(requirement_ref=self.ref("requirement", "/missing_requirements/" + str(i)),
                code=row["reason_code"], required_input=row["kind"], document_id=document, field_ref=field_ref,
                native_source_refs=deepcopy(row["source_refs"])))
        return result

    def build(self):
        selectors = {name: node["x-bvbrc-proteome"] for name, node in self.form["properties"].items()}
        facts = {}
        for field, selector in selectors.items():
            kind = selector["kind"]
            if kind not in c.FAMILIES or kind == "directional_requirements": continue
            located = self.locate(selector)
            operation = (self.numerical if kind in {"directional_count", "directional_fraction", "directional_coverage"} else
                self.native if kind in {"directional_native_integer", "directional_native_decimal"} else
                self.state if kind == "directional_state" else self.extremum if kind == "directional_extremum" else self.page)
            fact = operation(selector, located)
            if fact["context"]["declaration_state"] == "conflicting_version": fact["availability"] = "incompatible"
            if fact["availability"] != "available":
                self.field_failure(field, selector, "requested_target_missing" if not located["target_exists"] else "requested_value_unavailable")
            facts[field] = fact
        for name, generated, code_key in (("missing_requirements", self.generated_requirements, "reason_code"),
                                         ("diagnostics", self.generated_diagnostics, "code")):
            _require(all(row[code_key] not in _REQUEST_CODES or row in generated for row in self.root[name]), "/" + name)
        legacy_selectors = {field: selector for field, selector in selectors.items()
            if selector["kind"] not in c.FAMILIES and selector["kind"] != "request_status"}
        if legacy_selectors:
            requirements = tuple(row for row in self.root["missing_requirements"] if not row["reason_code"].startswith("proteome_directional_"))
            diagnostics = tuple(row for row in self.root["diagnostics"] if not row["code"].startswith("proteome_directional_"))
            legacy_result = _LegacyProjection(self.sheet, None if self.components is None else self.components["legacy"],
                self.parameters, old.requested_form_schema(legacy_selectors), requirements, diagnostics, global_root=self.root).build()
            facts.update(legacy_result["facts"])
            for name in ("missing_requirements", "diagnostics"):
                self.root[name] = _unique([*self.root[name], *legacy_result[name]])
        for field, fact in facts.items():
            if "context" not in fact: continue
            if field in self.field_requirements:
                index = next(i for i, row in enumerate(self.root["missing_requirements"]) if row["requirement_id"] == self.field_requirements[field])
                fact["context"]["requirement_refs"].append(self.ref("requirement", "/missing_requirements/" + str(index)))
                index = self.root["diagnostics"].index(self.field_diagnostics[field])
                fact["context"]["qualification_refs"].append(self.ref("qualification", "/diagnostics/" + str(index)))
        for field, selector in selectors.items():
            if selector["kind"] == "directional_requirements":
                facts[field] = dict(availability="available", requirements=self.requirement_rows())
        for field, selector in selectors.items():
            if selector["kind"] == "request_status":
                target = facts[selector["field"]]
                tails = target.get("context", target)
                facts[field] = dict(availability="available", field=selector["field"], state=target["availability"],
                    **{key: deepcopy(tails.get(key, [])) for key in ("requirement_refs", "qualification_refs")})
        for field, fact in facts.items():
            kind = selectors[field]["kind"]
            if kind in c.FAMILIES: c.validate_directional_fact(kind, fact, selector=selectors[field])
        old._validate(self.form, facts, "saved_facts_invalid")
        return dict(status="ok" if all(row["availability"] == "available" for row in facts.values()) else "partial",
            facts={field: facts[field] for field in selectors}, missing_requirements=deepcopy(self.root["missing_requirements"]),
            diagnostics=deepcopy(self.root["diagnostics"]))


def project_requested_facts_v2(sheet: dict | None, components: dict | None, *,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict) -> dict:
    from .bvbrc_proteome_bundle_v2_contracts import validate_parameters_v2
    parameters = validate_parameters_v2(parameters)
    form = c.validate_requested_form_v2(requested_form)
    _require(type(missing_requirements) is tuple and type(diagnostics) is tuple)
    for row in missing_requirements: validate_contract("AcquisitionRequirement", row)
    for row in diagnostics: validate_contract("Diagnostic", row)
    if sheet is None:
        _require(components is None, "/components")
        return dict(status="invalid", facts={}, missing_requirements=_unique(missing_requirements), diagnostics=_unique(diagnostics))
    _require(_same(sheet["parameters"], parameters) and _same(sheet["requested_form"], form) and sheet["analysis_id"] == parameters["analysis_id"], "/sheet")
    return _DirectionalProjection(sheet, components, parameters, form, missing_requirements, diagnostics).build()


def validate_saved_projection_v2(sheet: dict | None, components: dict | None, *,
    facts: dict, status: str, missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...],
    requested_form: dict, parameters: dict, original_task: dict, bundle_sha256: str, bundle: dict | None = None) -> dict:
    from .bvbrc_proteome_bundle_v2_contracts import validate_saved_provider_v2
    _require(bundle is not None, "/bundle")
    sheet, components = validate_saved_provider_v2(sheet, components, parameters=parameters,
        requested_form=requested_form, original_task=original_task, bundle_sha256=bundle_sha256, bundle=bundle)
    result = project_requested_facts_v2(sheet, components, missing_requirements=missing_requirements,
        diagnostics=diagnostics, requested_form=requested_form, parameters=parameters)
    _require(_same(result, dict(status=status, facts=facts, missing_requirements=list(missing_requirements), diagnostics=list(diagnostics))))
    return deepcopy(result)


__all__ = ["project_requested_facts_v2", "validate_saved_projection_v2"]
