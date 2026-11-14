"""Select requested facts from saved proteome sheets and calculated components.

No native parser, calculator, Store, network or scientific execution is called.
The return binding separately authenticates the publication and episode custody.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from . import bvbrc_proteome_fact_contracts as c
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data
from .bvbrc_proteome_data_contracts import proteome_data_schema
from .bvbrc_proteome_native_contracts import native_schema

requested_form_schema = c.requested_form_schema
validate_requested_form = c.validate_requested_form
_SHEET = "/sheet/native_sheet_result/value"


def _provider_contracts():
    from . import bvbrc_proteome_bundle_contracts
    return bvbrc_proteome_bundle_contracts


def _error(code, path=""):
    raise _provider_contracts().ProteomeBundleError("proteome_" + code, path)


def _equal(left, right):
    return c.canonical(left) == c.canonical(right)


def _unique(rows):
    values, seen = [], set()
    for row in rows:
        key = c.canonical(row)
        if key not in seen:
            values.append(deepcopy(row))
            seen.add(key)
    return values


def _token(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _scope(**values):
    return {name: values.get(name) for name in c.SCOPE_SCHEMA["properties"]}


def _one(rows, path, **identity):
    found = [(row, path + "/" + str(i)) for i, row in enumerate(rows)
             if all(row[key] == value for key, value in identity.items())]
    if len(found) > 1:
        _error("requested_target_ambiguous", path)
    return found[0] if found else (None, None)


def _reports(value, schema, path):
    """Follow declared report types, never arbitrary JSON in supplied metadata."""
    definitions = schema["$defs"]

    def walk(item, node, pointer):
        if "$ref" in node:
            name = node["$ref"].removeprefix("#/$defs/")
            if name in {"Requirement", "PRequirement", "Diagnostic", "PDiagnostic"}:
                yield ("requirement" if name.endswith("Requirement") else "qualification", item, pointer)
                return
            yield from walk(item, definitions[name], pointer)
            return
        for union in ("anyOf", "oneOf"):
            if union in node:
                for branch in node[union]:
                    if c._Validator({"$defs": definitions, **branch}).is_valid(item):
                        yield from walk(item, branch, pointer)
                        break
                return
        if type(item) is dict:
            for key, child in node.get("properties", {}).items():
                if key in item:
                    yield from walk(item[key], child, pointer + "/" + _token(key))
        elif type(item) is list and type(node.get("items")) is dict:
            for i, child in enumerate(item):
                yield from walk(child, node["items"], pointer + "/" + str(i))

    yield from walk(value, schema, path)


def _validate_inputs(sheet, components, parameters, form, requirements, diagnostics):
    contracts = _provider_contracts()
    parameters = contracts.validate_parameters(parameters)
    try:
        form = validate_requested_form(form)
    except c.ProteomeFactError as error:
        raise contracts.ProteomeBundleError("proteome_projection_requested_form_invalid", error.path) from error
    if type(requirements) is not tuple or type(diagnostics) is not tuple:
        _error("saved_projection_conflict")
    codes = set(contracts.BINDING_CODES) | set(c.P_REASONS) | set(c._SHEET_DEFS["Diagnostic"]["properties"]["code"]["enum"])
    for row in requirements:
        validate_contract("AcquisitionRequirement", row)
        if row["reason_code"] not in codes:
            _error("saved_projection_conflict", "/missing_requirements")
    ids = {}
    for row in requirements:
        if row["requirement_id"] in ids and not _equal(ids[row["requirement_id"]], row):
            _error("saved_projection_conflict", "/missing_requirements")
        ids[row["requirement_id"]] = row
    for row in diagnostics:
        validate_contract("Diagnostic", row)
        if row["code"] not in codes:
            _error("saved_projection_conflict", "/diagnostics")
    if sheet is None:
        if components is not None:
            _error("saved_sheet_invalid", "/sheet")
        return None, None, parameters, form
    sheet = contracts.validate_provider_sheet(sheet)
    if not _equal(sheet["parameters"], parameters) or not _equal(sheet["requested_form"], form):
        _error("saved_identity_conflict", "/sheet")
    if sheet["analysis_id"] != parameters["analysis_id"]:
        _error("saved_identity_conflict", "/sheet/analysis_id")
    if components is not None:
        try:
            components = validate_proteome_sheet_data("NativeComponentsResult", components)
        except ValueError as error:
            raise contracts.ProteomeBundleError("proteome_saved_components_invalid", getattr(error, "path", "")) from error
        values = components["value"]
        if values is not None:
            native = sheet["native_sheet_result"]
            if native is None or native["value"] is None:
                _error("saved_sheet_invalid", "/sheet/native_sheet_result")
            expected = hashlib.sha256(c.canonical(native["value"]).encode()).hexdigest()
            if values["sheet_sha256"] != expected or not _equal(values["parameters"], parameters["calculation_parameters"]):
                _error("saved_identity_conflict", "/components/value")
    return sheet, components, parameters, form


class _Projection:
    def __init__(self, sheet, components, parameters, form, requirements, diagnostics):
        self.sheet, self.components, self.parameters, self.form = sheet, components, parameters, form
        self.root = {"sheet": sheet, "components": components,
                     "missing_requirements": _unique(requirements), "diagnostics": _unique(diagnostics)}
        self.aid = parameters["analysis_id"]
        self.generated_requirements, self.generated_diagnostics = [], []
        self.request_requirement_scopes, self.request_diagnostic_scopes = {}, {}
        self.request_reference_owners = {}
        self.native = None if sheet["native_sheet_result"] is None else sheet["native_sheet_result"]["value"]
        self.values = None if components is None else components["value"]
        self.pure_requirements, self.pure_qualifications = [], []
        self._collect_reports()

    def ref(self, kind, pointer):
        return c.encode_reference(kind, self.aid, pointer)

    def _collect_reports(self):
        roots = []
        for key, contract in (("native_results", "NativeProjectionResult"),
                              ("inventory_results", "ProteinInventoryResult"),
                              ("feature_results", "FeatureSnapshotResult"),
                              ("genome_results", "GenomeSnapshotResult"),
                              ("sequence_results", "FeatureSequenceSnapshotResult")):
            schema = native_schema(contract) if key == "native_results" else proteome_data_schema(contract)
            roots.extend((row, schema, "/sheet/" + key + "/" + str(i)) for i, row in enumerate(self.sheet[key]))
        if self.sheet["input_index_result"] is not None:
            roots.append((self.sheet["input_index_result"], proteome_data_schema("InputIndexResult"), "/sheet/input_index_result"))
        for key, contract in (("joins_result", "NativeJoinsResult"), ("native_sheet_result", "NativeSheetResult")):
            if self.sheet[key] is not None:
                roots.append((self.sheet[key], c.proteome_sheet_schema(contract), "/sheet/" + key))
        if self.components is not None:
            roots.append((self.components, c.proteome_sheet_schema("NativeComponentsResult"), "/components"))
        seen = {"requirement": set(), "qualification": set()}
        for value, schema, pointer in roots:
            for kind, row, path in _reports(value, schema, pointer):
                key = c.canonical(row)
                if key not in seen[kind]:
                    seen[kind].add(key)
                    (self.pure_requirements if kind == "requirement" else self.pure_qualifications).append((row, path))
        if self.values is not None:
            for i, track in enumerate(self.values["tracks"]):
                for j, code in enumerate(track["qualifications"]):
                    self.pure_qualifications.append((dict(code=code, scope=_scope(track_key=track["track_key"]), source_fields=[]),
                        f"/components/value/tracks/{i}/qualifications/{j}"))

    def cell(self, value, pointer):
        if value is None:
            return dict(state="missing_input", value=None, reason_codes=[], source_field_refs=[])
        return dict(state=value["state"], value=deepcopy(value["value"]), reason_codes=deepcopy(value["reason_codes"]),
                    source_field_refs=[self.ref("source_field", pointer + "/source_fields/" + str(i))
                                       for i in range(len(value["source_fields"]))])

    @staticmethod
    def availability(value):
        if value is None:
            return "unavailable"
        return {"value": "available", "invalid": "invalid", "conflicting": "incompatible",
                "ambiguous": "incompatible"}.get(value["state"], "unavailable")

    def track(self, key):
        return _one([] if self.values is None else self.values["tracks"], "/components/value/tracks", track_key=key)

    def association(self, key, *, calculated=False):
        rows = ([] if self.values is None else self.values["associations"]) if calculated else (
            [] if self.native is None else self.native["association_rows"])
        return _one(rows, "/components/value/associations" if calculated else _SHEET + "/association_rows", association_key=key)

    def inventory(self, key):
        pairs = [(r["value"], f"/sheet/inventory_results/{i}/value") for i, r in enumerate(self.sheet["inventory_results"])
                 if r["value"] is not None and r["value"]["inventory_key"] == key]
        if len(pairs) > 1:
            _error("requested_target_ambiguous", "/sheet/inventory_results")
        return pairs[0] if pairs else (None, None)

    def selected_scope(self, selector):
        """Use actual saved identities, without inventing a missing target row."""
        key = selector.get("association_key")
        if key is not None:
            row, _ = self.association(key)
            if row is not None:
                return _scope(track_key=row["track_key"], association_key=row["association_key"],
                              reference_row_ordinal=row["reference_row_ordinal"])
        track_key = selector.get("track_key", None if key is None else key.split("/row/")[0])
        if track_key is not None:
            track, _ = self.track(track_key)
            if track is not None:
                return _scope(track_key=track["track_key"])
        return _scope()

    def field_failure(self, field, selector, reason):
        role = "proteome_requested_projection"
        payload = dict(version="bvbrc_proteome_requirement_v1", analysis_id=self.aid,
            reason_code="proteome_" + reason, role=role, field=field,
            selection=deepcopy(selector), source_refs=[], pure_requirement=None)
        requirement = dict(requirement_id="proteome_requirement_" + hashlib.sha256(c.canonical(payload).encode()).hexdigest(),
            kind="scientific_metadata", role=role, source_refs=[], reason_code=payload["reason_code"])
        diagnostic = dict(code=payload["reason_code"], phase="publication", path="/facts/" + _token(field),
                          severity="qualification", evidence_refs=[])
        self.root["missing_requirements"] = _unique([*self.root["missing_requirements"], requirement])
        self.root["diagnostics"] = _unique([*self.root["diagnostics"], diagnostic])
        self.request_requirement_scopes[requirement["requirement_id"]] = self.selected_scope(selector)
        self.request_diagnostic_scopes[c.canonical(diagnostic)] = self.selected_scope(selector)
        for kind, collection, item in (("requirement", "missing_requirements", requirement),
                                       ("qualification", "diagnostics", diagnostic)):
            pointer = "/" + collection + "/" + str(self.root[collection].index(item))
            self.request_reference_owners[self.ref(kind, pointer)] = field
        self.generated_requirements.append(requirement)
        self.generated_diagnostics.append(diagnostic)

    def measurement(self, selector):
        target, metric = selector["target"], selector["metric"]
        value, path, population, quantum = None, None, None, None
        origin, unit = "derived_native_descriptive", "count"
        if target == "association":
            row, path = self.association(selector["association_key"], calculated=True)
            unit, quantum = "percent", .1
            method = "legacy_first_hsp_percent" if metric == c.ASSOCIATION_METRICS[0] else "legacy_subject_endpoint_percent"
            if row is not None:
                value, population = row[metric], self.ref("population", path)
                path += "/" + metric
        elif target == "inventory_count":
            row, path = self.inventory(selector["inventory_key"])
            method, origin = "supplied_inventory_count", "observed_supplied_inventory"
            if row is not None:
                population = self.ref("population", path + "/records")
                value = dict(state="value", value=row[metric], reason_codes=[], source_fields=[])
                path += "/" + metric
        else:
            row, path = self.track(selector["track_key"])
            method = c.TRACK_METHODS[metric] if target == "track_count" else (
                "postfilter_selection_count" if target == "selection_count" else
                "native_cell_presence_count" if metric in c.SUMMARY_COUNTS else "rounded_native_summary")
            if target == "summary" and metric in c.SUMMARY_VALUES:
                unit, quantum = "fraction", .001
            if row is not None:
                if target == "summary":
                    track_path = path
                    path += "/" + selector["summary"]
                    value = row[selector["summary"]][metric]
                    population = self.ref("population", path + "/used_association_keys" if metric in (*c.SUMMARY_VALUES, "value_count")
                                          else track_path)
                elif target == "selection_count":
                    path += "/selection_counts"
                    value = row["selection_counts"][metric]
                    population = self.ref("population", path)
                else:
                    value = row[metric]
                    population = self.ref("population", path)
                path += "/" + metric
        return dict(availability=self.availability(value), quantity=metric, cell=self.cell(value, path),
            unit=unit, origin=origin, population_ref=population, method=method, uncertainty=None,
            native_rounding_quantum=quantum), value is not None

    def ratio(self, selector):
        row, path = self.track(selector["track_key"])
        value = None if row is None else row[selector["metric"]]
        return dict(availability=self.availability(None if value is None else value["fraction"]), quantity=selector["metric"],
            **{key: self.cell(None if value is None else value[key], None if path is None else path + "/" + selector["metric"] + "/" + key)
               for key in ("numerator", "denominator", "fraction")}, unit="fraction",
            population_ref=None if path is None else self.ref("population", path),
            denominator_kind="qualified_executed_reference_occurrences", uncertainty=None), value is not None

    def population(self, selector):
        target = selector["target"]
        result = dict(availability="unavailable", population_kind={"inventory": "supplied_fasta_occurrences",
            "summary": "usable_rounded_native_cells", "track": "selected_track_input_associations"}[target],
            track_key=selector.get("track_key"), inventory_key=selector.get("inventory_key"), source_scope=None,
            materialization=None, association_keys=[], record_ordinals=[],
            membership_meaning={"inventory": "supplied_records", "summary": "exact_used_cells", "track": "input_population"}[target],
            native_source_refs=[])
        if target == "inventory":
            row, _ = self.inventory(selector["inventory_key"])
            if row is not None:
                result.update(availability="available", record_ordinals=[r["record_ordinal"] for r in row["records"]],
                    source_scope="complete_document" if row["source"]["body_complete"] and row["source"]["object_complete"] == "yes"
                    else "partial_or_unknown_artifact", native_source_refs=[row["source"]["content"]["source_ref"]])
        else:
            row, _ = self.track(selector["track_key"])
            if row is not None:
                result.update(availability="available", source_scope=row["source_scope"], materialization=row["materialization"],
                    association_keys=deepcopy(row[selector["summary"]]["used_association_keys"]) if target == "summary"
                    else [a["association_key"] for a in self.native["association_rows"] if a["track_key"] == selector["track_key"]],
                    native_source_refs=[self.native["primary_source_ref"]])
        return result, row is not None

    def selection(self, selector):
        row, path = self.association(selector["association_key"], calculated=True)
        return dict(availability="unavailable" if row is None else "available", association_key=selector["association_key"],
            selection=None if row is None else row["selection"],
            failed_conditions=[] if row is None else deepcopy(row["failed_conditions"]),
            unknown_conditions=[] if row is None else deepcopy(row["unknown_conditions"]),
            parameter_ref=None if row is None else self.ref("parameter", "/components/value/parameters"),
            population_ref=None if row is None else self.ref("population", path)), row is not None

    def association_fact(self, selector):
        key = selector["association_key"]
        track, ordinal_text = key.split("/row/")
        row, path = self.association(key)
        result = dict(availability="unavailable", association_key=key, track_key=track,
            reference_row_ordinal=int(ordinal_text), reference_identifier=None, subject_identifier=None,
            native_category=None, category_presence=None, reference_join_ref=None, subject_join_ref=None,
            metadata_join_refs=[], source_field_refs=[])
        if row is None:
            return result, False
        located = row["layout_state"] == "source_field_located"
        result["availability"] = "available" if located else "incompatible"
        category = row["native_hit_category"]
        result["category_presence"] = category["presence"]
        if category["presence"] == "value":
            result["native_category"] = category["value"] if category["value"] in {"bi (<->)", "uni (->)"} else "unrecognized"
        result["source_field_refs"].append(self.ref("source_field", path + "/native_hit_category/source_field"))
        primary_index = next(i for i, r in enumerate(self.native["native_results"]) if r["value"] is not None
            and r["value"]["source"]["content"]["source_ref"] == self.native["primary_source_ref"])
        primary = self.native["native_results"][primary_index]["value"]
        prefix = _SHEET + f"/native_results/{primary_index}/value"
        reference = primary["reference_rows"][row["reference_row_ordinal"]]
        subject, subject_path = _one(primary["associations"], prefix + "/associations", association_key=key)
        for name, native_row, native_path in (
            ("reference", reference, prefix + "/reference_rows/" + str(row["reference_row_ordinal"])),
            ("subject", subject, subject_path),
        ):
            if native_row is not None:
                identifier = native_row["patric_id"]
                result[name + "_identifier"] = identifier["value"] if located and identifier["presence"] == "value" else None
                result["source_field_refs"].append(self.ref("source_field", native_path + "/patric_id/source_field"))
        joins = self.native["joins"]
        if joins is not None:
            for name, collection in (("reference", "reference_joins"), ("subject", "subject_joins")):
                for i, join in enumerate(joins[collection]):
                    matches = (join["native"]["reference_row_ordinal"] == row["reference_row_ordinal"] if name == "reference"
                               else join["native"]["association_key"] == key)
                    if matches and join["state"] == "joined":
                        result[name + "_join_ref"] = self.ref("join", _SHEET + "/joins/" + collection + "/" + str(i))
            ref_row = self.native["reference_rows"][row["reference_row_ordinal"]]
            result["metadata_join_refs"] = [self.ref("join", _SHEET + "/joins/metadata_joins/" + str(i))
                for i in dict.fromkeys([*ref_row["metadata_links"], *row["metadata_links"]])]
        return result, True

    def requirement_rows(self):
        result, translated = [], set()
        for row, path in self.pure_requirements:
            result.append(dict(requirement_ref=self.ref("requirement", path), code=row["code"],
                required_input=row["required_input"], scope=deepcopy(row["scope"]),
                source_field_refs=[self.ref("source_field", path + "/source_fields/" + str(i)) for i in range(len(row["source_fields"]))]))
            translated.add((row["code"], tuple(dict.fromkeys(f["source_ref"] for f in row["source_fields"]))))
        for i, row in enumerate(self.root["missing_requirements"]):
            if (row["reason_code"], tuple(row["source_refs"])) in translated:
                continue
            result.append(dict(requirement_ref=self.ref("requirement", "/missing_requirements/" + str(i)),
                code=row["reason_code"], required_input=row["kind"],
                scope=deepcopy(self.request_requirement_scopes.get(row["requirement_id"], _scope())), source_field_refs=[]))
        return result

    def qualification_rows(self):
        result = [dict(qualification_ref=self.ref("qualification", path), code=row["code"], scope=deepcopy(row["scope"]),
            source_field_refs=[self.ref("source_field", path + "/source_fields/" + str(i)) for i in range(len(row["source_fields"]))])
            for row, path in self.pure_qualifications]
        translated = {(row["code"], tuple(dict.fromkeys(f["source_ref"] for f in row["source_fields"])))
                      for row, _ in self.pure_qualifications}
        result.extend(dict(qualification_ref=self.ref("qualification", "/diagnostics/" + str(i)), code=row["code"],
                           scope=deepcopy(self.request_diagnostic_scopes.get(c.canonical(row), _scope())),
                           source_field_refs=[]) for i, row in enumerate(self.root["diagnostics"])
                      if (row["code"], tuple(row["evidence_refs"])) not in translated)
        return result

    def tails(self, selector, field):
        key = selector.get("association_key")
        selected = dict(track_key=selector.get("track_key", None if key is None else key.split("/row/")[0]),
                        association_key=key, reference_row_ordinal=None if key is None else int(key.split("/row/")[1]))
        def matches(scope):
            return all(scope.get(k) is None or value is None or scope[k] == value for k, value in selected.items())
        def relevant(row, reference_key):
            owner = self.request_reference_owners.get(row[reference_key])
            return (owner is None or owner == field) and matches(row["scope"])
        return dict(requirement_refs=[r["requirement_ref"] for r in self.requirement_rows() if relevant(r, "requirement_ref")],
                    qualification_refs=[r["qualification_ref"] for r in self.qualification_rows() if relevant(r, "qualification_ref")])

    def build(self):
        selectors = {field: node["x-bvbrc-proteome"] for field, node in self.form["properties"].items()}
        facts = {}
        for field, selector in selectors.items():
            kind = selector["kind"]
            if kind in {"requirements", "qualifications", "request_status"}:
                continue
            operation = {"measurement": self.measurement, "ratio": self.ratio, "population": self.population,
                         "association": self.association_fact, "selection": self.selection}[kind]
            fact, found = operation(selector)
            if fact["availability"] != "available":
                self.field_failure(field, selector, "requested_target_missing" if not found else
                    "requested_population_unavailable" if kind == "population" else "requested_value_unavailable")
            facts[field] = fact
        # A projection from another form may not inject a foreign request failure.
        codes = {"proteome_requested_target_missing", "proteome_requested_value_unavailable", "proteome_requested_population_unavailable"}
        for key, generated, code_key in (("missing_requirements", self.generated_requirements, "reason_code"),
                                          ("diagnostics", self.generated_diagnostics, "code")):
            for row in self.root[key]:
                if row[code_key] in codes and not any(_equal(row, expected) for expected in generated):
                    _error("saved_projection_conflict", "/" + key)
        for field, selector in selectors.items():
            kind = selector["kind"]
            if kind == "requirements":
                facts[field] = dict(availability="available", requirements=self.requirement_rows())
            elif kind == "qualifications":
                facts[field] = dict(availability="available", qualifications=self.qualification_rows())
            elif kind != "request_status":
                facts[field].update(self.tails(selector, field))
        for field, selector in selectors.items():
            if selector["kind"] == "request_status":
                target = facts[selector["field"]]
                facts[field] = dict(availability="available", field=selector["field"], state=target["availability"],
                    requirement_refs=deepcopy(target.get("requirement_refs", [])),
                    qualification_refs=deepcopy(target.get("qualification_refs", [])))
        facts = {name: facts[name] for name in selectors}
        c._validate(self.form, facts, "saved_facts_invalid")
        return dict(status="ok" if all(row["availability"] == "available" for row in facts.values()) else "partial",
                    facts=facts, missing_requirements=deepcopy(self.root["missing_requirements"]),
                    diagnostics=deepcopy(self.root["diagnostics"]))


def project_requested_facts(sheet: dict | None, components: dict | None, *,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict) -> dict:
    sheet, components, parameters, form = _validate_inputs(sheet, components, parameters,
        requested_form, missing_requirements, diagnostics)
    if sheet is None:
        return dict(status="invalid", facts={}, missing_requirements=_unique(missing_requirements), diagnostics=_unique(diagnostics))
    return _Projection(sheet, components, parameters, form, missing_requirements, diagnostics).build()


def validate_saved_projection(sheet: dict | None, components: dict | None, *,
    facts: dict, status: str, missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...],
    requested_form: dict, parameters: dict, original_task: dict, bundle_sha256: str,
    bundle: dict | None = None) -> dict:
    result = project_requested_facts(sheet, components, missing_requirements=missing_requirements,
        diagnostics=diagnostics, requested_form=requested_form, parameters=parameters)
    if sheet is not None:
        _provider_contracts().validate_bundle_binding(sheet, bundle)
    elif any("requirement_id" in choice for choice in parameters["native_documents"]):
        if bundle is None:
            _error("saved_identity_conflict", "/bundle")
        actual = validate_contract("ArtifactBundle", bundle)
        if not _equal(actual["original_task"], original_task) or _provider_contracts().digest(actual) != bundle_sha256:
            _error("saved_identity_conflict", "/bundle")
    if sheet is not None and (not _equal(sheet["original_task"], original_task) or sheet["bundle_sha256"] != bundle_sha256):
        _error("saved_identity_conflict", "/sheet")
    if not _equal(result, dict(status=status, facts=facts, missing_requirements=list(missing_requirements), diagnostics=list(diagnostics))):
        _error("saved_projection_conflict")
    return deepcopy(result)


__all__ = ["requested_form_schema", "validate_requested_form", "project_requested_facts", "validate_saved_projection"]
