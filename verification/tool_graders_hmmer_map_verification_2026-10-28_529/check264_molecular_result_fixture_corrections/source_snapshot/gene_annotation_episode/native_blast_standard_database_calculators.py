"""Pure standard5 calculation and numerical-row population.

Public303 is called once per saved search, and the PSSM calculator once per
actual input population. Raw reported-axis HSPs remain separate. Qualified
geometry is a pointer into that existing303 result, never a recalculation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from . import blast_sequence_database as _sequence
from . import blast_pssm_calculators as _pssm
from .blast_pairwise_grader import alignment_components, alignment_component_artifacts, validate_blast_correspondence_instance
from .alignment_correspondence import ARTIFACT_SCHEMA, validate_correspondence_artifacts, _same
from .blast_program_context import resolve_blast_program_context
from .blast_fasta_record_identity import blast_record_identity
from .native_blast_database_result_worker import populate_native_blast_database_search_facts, _sequence_quality_source
from .domain import validate_schema
from . import native_blast_standard_database_result_views as views
from .native_blast_standard_database_contracts import IDENTITY_SCHEMA


CALCULATION_SCHEMA = views.PREFIX + "calculations_v1"
CALCULATION_SCHEMA_V2 = views.PREFIX + "calculations_v2"
_SHEET_FIELDS = {"schema", "collection", "prepared_inputs", "search_bindings", "sequence", "pssm",
                 "metadata_parse_results", "metadata_binding_results", "issues"}
_CALC_FIELDS = {"schema", "sequence_model", "sequence", "pssm", "search_facts", "native_search_statistics",
                "native_hsp_components", "qualified_hsp_components", "issues"}


def _at(value, pointer):
    if type(pointer) is not str or pointer and not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError(views.PREFIX + "pointer_invalid")
    for token in pointer.split("/")[1:] if pointer else ():
        token = token.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            if not re.fullmatch(r"0|[1-9][0-9]*", token): raise ValueError(views.PREFIX + "pointer_invalid")
            value = value[int(token)]
        else:
            value = value[token]
    return value


def _pointer(*parts):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _number(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def validate_sequence_model(model):
    model = views._copy(model)
    if model is None: return None
    if type(model) is not dict or set(model) - {"temperature_bits", "function_priors"}:
        raise ValueError(views.PREFIX + "sequence_model_invalid")
    if "temperature_bits" in model and (not _number(model["temperature_bits"]) or model["temperature_bits"] <= 0):
        raise ValueError(views.PREFIX + "sequence_model_invalid")
    priors = model.get("function_priors")
    if priors is not None and (type(priors) is not dict or not priors or any(type(k) is not str or not k.strip()
            or "\0" in k or not _number(v) or v < 0 for k, v in priors.items()) or not any(v > 0 for v in priors.values())):
        raise ValueError(views.PREFIX + "sequence_model_invalid")
    if priors is not None:
        try: total = math.fsum(priors.values())
        except OverflowError as error: raise ValueError(views.PREFIX + "sequence_model_invalid") from error
        if not math.isfinite(total): raise ValueError(views.PREFIX + "sequence_model_invalid")
    return model


def _failure(code="calculation_failed", *, stage="calculation", key=None, pointer="", detail="calculator_contract_invalid", record_key=None):
    return dict(stage=stage, code=views.PREFIX + code, artifact_key=key["artifact_key"] if key else None,
        input_key=None, search_key=deepcopy(key), record_key=record_key, pointer=pointer, detail_code=detail)


def _sheet_set(value):
    value = views._copy(value)
    if type(value) is not dict or set(value) != _SHEET_FIELDS or value["schema"] != views.PREFIX + "sheet_set_v1":
        raise ValueError(views.PREFIX + "sheet_set_invalid")
    collection = value["collection"]
    if collection.get("schema") != "blast_report_collection_v1" or collection["invocation"]["execution_program"] not in views.PROGRAMS:
        raise ValueError(views.PREFIX + "collection_invalid")
    if collection["invocation"] != value["prepared_inputs"]["invocation"]:
        raise ValueError(views.PREFIX + "invocation_conflict")
    keys = [views._hash(s["search_key"]) for s in collection["searches"]]
    if len(keys) != len(set(keys)) or len(value["sequence"]) != len(keys): raise ValueError(views.PREFIX + "search_population_invalid")
    if [r["search_key"] for r in value["sequence"]] != [s["search_key"] for s in collection["searches"]]:
        raise ValueError(views.PREFIX + "search_population_invalid")
    for row, search in zip(value["sequence"], collection["searches"]):
        if set(row) != {"search_key", "sheet"} or row["sheet"]["search"] != search:
            raise ValueError(views.PREFIX + "search_sheet_identity_conflict")
    return value


def _source_statuses(sheet_set):
    """Qualify saved raw source bytes and original source addresses, without I/O."""
    out = []
    prepared, collection = sheet_set["prepared_inputs"], sheet_set["collection"]
    for search in collection["searches"]:
        key, norm, state = search["search_key"], search["normalized"], "available"
        try:
            artifacts = [a for a in collection["artifacts"] if a["artifact_key"] == key["artifact_key"]]
            docs = [d for d in prepared["resolved_documents"] if d["kind"] == "captured" and d["catalog"]["artifact_key"] == key["artifact_key"]]
            if len(artifacts) != 1 or len(docs) != 1 or docs[0]["status"] != "available":
                state = "unavailable"
            else:
                artifact, document = artifacts[0], docs[0]
                raw = bytes.fromhex(document["contents_hex"])
                digest = hashlib.sha256(raw).hexdigest()
                if (digest != artifact["sha256"] or digest != document["catalog"]["sha256"] or digest != norm["native"]["sha256"]
                        or len(raw) != artifact["size_bytes"] or len(raw) != document["catalog"]["size_bytes"] or key["member_ordinal"] is not None):
                    state = "incompatible"
                elif norm["format"] == "json2":
                    native = norm["native"]["document"]
                    outer = native["BlastOutput2"]
                    report = "/BlastOutput2" + (f"/{key['report_index']}" if type(outer) is list else "") + "/report"
                    if (native != document["decoded_json"] or views._copy(json.loads(raw)) != native
                            or type(outer) is dict and key["report_index"] != 0
                            or key["search_pointer"] != report + "/results/search" or _at(native, report) != search["native"]["report"]
                            or _at(native, key["search_pointer"]) != search["native"]["search"]): state = "incompatible"
                    query = search["native"]["search"]
                    expected_query = {name: query.get(field) if type(query.get(field)) is expected and (expected is not int or query[field] > 0) else None
                        for name, field, expected in (("id", "query_id", str), ("title", "query_title", str), ("length", "query_len", int))}
                    if norm["query"] != expected_query: state = "incompatible"
                elif norm["format"] == "tabular":
                    layout = norm["native"].get("table_layout")
                    if (search["native"]["report"]["text"].encode() != raw or key["report_index"] != 0
                            or not re.fullmatch(r"/sections/(0|[1-9][0-9]*)", key["search_pointer"])
                            or layout != dict(format=artifact["format"], declared_fields=artifact["fields"], delimiter=artifact["delimiter"] or "\t")
                            or any(norm["native"].get(k) != v for k, v in search["native"]["search"].items())): state = "incompatible"
                    lines = raw.decode().splitlines()
                    for row in search["native"]["search"]["rows"]:
                        if (type(row["line"]) is not int or row["line"] < 1
                                or lines[row["line"] - 1].split(layout["delimiter"]) != row["values"]): state = "incompatible"
                else: state = "incompatible"
        except (KeyError, TypeError, IndexError, ValueError, UnicodeError):
            state = "incompatible"
        out.append(dict(search_key=deepcopy(key), status=state))
    return out


def _native_slots(collection):
    for search in collection["searches"]:
        norm, source = search["normalized"], search["native"]["search"]
        mapped = {}
        if len(norm["hits"]) != len(search["row_map"]): raise ValueError(views.PREFIX + "native_row_map_invalid")
        for hit, mapping in zip(norm["hits"], search["row_map"]):
            if hit["hit_index"] != mapping["hit_index"] or len(hit["hsps"]) != len(mapping["hsp_ordinals"]):
                raise ValueError(views.PREFIX + "native_row_map_invalid")
            for hsp, ordinal in zip(hit["hsps"], mapping["hsp_ordinals"]):
                key = mapping["hit_index"], ordinal
                if key in mapped: raise ValueError(views.PREFIX + "native_row_map_invalid")
                mapped[key] = hsp, hit["length"]
        slots = []
        if norm["format"] == "json2":
            hits = source.get("hits") if type(source) is dict else None
            for hi, hit in enumerate(hits if type(hits) is list else []):
                if type(hit) is dict and type(hit.get("hsps")) is list:
                    slots.extend((hi, j) for j in range(len(hit["hsps"])))
        else:
            rows = source.get("rows") if type(source) is dict else None
            owners = {j: hi for hi, j in mapped}
            if len(owners) != len(mapped): raise ValueError(views.PREFIX + "native_row_map_invalid")
            slots = [(owners.get(j), j) for j in range(len(rows if type(rows) is list else []))]
        for hi, ordinal in slots:
            native, length = mapped.get((hi, ordinal), (None, None))
            if norm["format"] == "json2":
                original_length = source["hits"][hi].get("len")
                if native is not None and length is not None and length != original_length: native = None
                # A malformed original HSP does not erase its valid hit's
                # independently reported length. Never infer a missing length.
                length = original_length if type(original_length) is int and original_length > 0 else None
            if native is not None:
                if norm["format"] == "json2":
                    original = source["hits"][hi]["hsps"][ordinal]
                    if type(original) is not dict or any(k not in original or original[k] != v for k, v in native.items()): native = None
                else:
                    raw = dict(zip(source["fields"], source["rows"][ordinal]["values"]))
                    aliases = dict(bit_score="bitscore", identity="nident", align_len="length", query_from="qstart", query_to="qend",
                        hit_from="sstart", hit_to="send", query_frame="qframe", hit_frame="sframe", hseq="sseq", identity_percent="pident",
                        query_coverage_percent="qcovhsp", query_subject_coverage_percent="qcovs", query_unique_subject_coverage_percent="qcovus")
                    for field, value in native.items():
                        expected = raw.get(aliases.get(field, field))
                        if field in {"query_frame", "hit_frame"} and expected is None and "frames" in raw:
                            pair = raw["frames"].split("/")
                            expected = pair[0 if field == "query_frame" else 1] if len(pair) == 2 else None
                        if field == "hit_strand" and "sstrand" in raw: expected = raw["sstrand"].title()
                        try: matches = expected == value if type(value) is str else expected is not None and float(expected) == value
                        except (TypeError, ValueError): matches = False
                        if not matches: native = None; break
            yield search, dict(search_key=deepcopy(search["search_key"]), hit_ordinal=hi, hsp_ordinal=ordinal, description_ordinal=None), native, length


def _statistic_rows(collection, statuses):
    rows = []
    native_names = ("db_num", "db_len", "hsp_len", "eff_space", "lambda", "kappa", "entropy")
    for i, (search, source) in enumerate(zip(collection["searches"], statuses)):
        raw = search["native"]["search"]
        stats = raw.get("stat") if type(raw) is dict else None
        base = f"/collection/searches/{i}/native/search"
        cells = {}
        for index, (name, native) in enumerate(zip(views.METRICS["search_statistic"], native_names)):
            value = stats.get(native) if type(stats) is dict else None
            reason = "not_measured" if search["normalized"]["format"] == "tabular" or stats is None or type(stats) is dict and native not in stats else "incompatible_input"
            valid = (_number(value) and (type(value) is int and value >= 0 if index < 4 else True))
            if source["status"] != "available": valid, reason = False, "incompatible_input" if source["status"] == "incompatible" else "missing_input"
            pointer = base + ("/stat" if type(raw) is dict and "stat" in raw else "") + ("/" + native if type(stats) is dict and native in stats else "")
            cells[name] = _cell(name, value if valid else None, views.METRICS["search_statistic"][name]["units"], pointer, reason=reason, origin="native_report")
        rows.append(dict(search_key=deepcopy(search["search_key"]), status=source["status"], measurements=cells))
    return rows


def _qualified_rows(sheet_set, calculations):
    found = {}
    for si, item in enumerate(calculations["sequence"]):
        result = item["components"]
        if result is None or result["components"]["database_sheet"] is None: continue
        components = result["components"]
        base = f"/sequence/{si}/components"
        for hit in components["row_keys"]["hits"]:
            hi = hit["component_index"]
            actual = components["database_sheet"]["hits"][hi]
            if actual["hit_index"] != hit["row_key"]["hit_ordinal"]: raise ValueError(views.PREFIX + "qualified_hit_pointer_conflict")
            references = [(i, r) for i, r in enumerate(components["coordinate_context"]["references"]) if r["row_key"] == hit["row_key"]]
            if len(references) != 1: raise ValueError(views.PREFIX + "qualified_reference_pointer_conflict")
            for hsp in hit["hsps"]:
                ci = hsp["component_index"]
                pointer = base + f"/components/database_sheet/hits/{hi}/hsp_components/{ci}"
                _at(calculations, pointer)
                key = views._hash(hsp["row_key"])
                if key in found: raise ValueError(views.PREFIX + "qualified_hsp_pointer_duplicate")
                found[key] = dict(row_key=deepcopy(hsp["row_key"]), status="available",
                    sequence_component_pointer=base, component_pointer=pointer,
                    query_binding_pointer=f"/sequence/{si}/sheet/query_binding",
                    reference_context_pointer=base + f"/components/coordinate_context/references/{references[0][0]}", issues=[])
    result = []
    for native in calculations["native_hsp_components"]:
        key = native["row_key"]
        row = found.get(views._hash(key))
        if row is None:
            row = dict(row_key=deepcopy(key), status="unavailable", sequence_component_pointer=None,
                component_pointer=None, query_binding_pointer=None, reference_context_pointer=None,
                issues=[_failure("row_unavailable", key=key["search_key"], pointer="/qualified_hsp_components", detail="native_row_invalid")])
        result.append(row)
    return result


def _calculate(sheet_set, *, sequence_model, diagnostics=None, _retain_correspondence=False):
    if type(_retain_correspondence) is not bool:
        raise ValueError(views.PREFIX + "private_retention_flag_invalid")
    sheets = _sheet_set(sheet_set)
    model = validate_sequence_model(sequence_model)
    collection, program = sheets["collection"], sheets["collection"]["invocation"]["execution_program"]
    statuses = _source_statuses(sheets)
    if any(row["status"] != "available" for row in statuses):
        raise ValueError(views.PREFIX + "saved_search_source_identity_invalid")
    out = dict(schema=CALCULATION_SCHEMA_V2 if _retain_correspondence else CALCULATION_SCHEMA, sequence_model=model, sequence=[], pssm=[], search_facts=[],
        native_search_statistics=[], native_hsp_components=[], qualified_hsp_components=[], issues=[])
    if _retain_correspondence:
        out["correspondence"] = {"version": ARTIFACT_SCHEMA, "instances": []}
    for index, row in enumerate(sheets["sequence"]):
        try:
            arguments = {"model": model}
            if _retain_correspondence:
                arguments["_retain_correspondence"] = True
            result = _sequence.calculate_blast_sequence_database_components(row["sheet"], **arguments)
            if _retain_correspondence:
                companion = result.pop("correspondence")
                for instance in companion["instances"]:
                    instance["legacy_pointer"] = f"/sequence/{index}/components" + instance["legacy_pointer"]
                    out["correspondence"]["instances"].append(instance)
        except (ValueError, TypeError, KeyError, IndexError, ArithmeticError) as error:
            result = None
            out["issues"].append(_failure(key=row["search_key"], pointer=f"/sequence/{index}"))
            if diagnostics is not None:
                diagnostics.append(dict(issue_index=len(out["issues"]) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
        out["sequence"].append(dict(search_key=deepcopy(row["search_key"]), components=result))
    if sheets["pssm"] and (program != "tblastn" or collection["invocation"]["query_kind"] != "pssm"):
        raise ValueError(views.PREFIX + "pssm_population_incompatible")
    seen = set()
    for index, sheet in enumerate(sheets["pssm"]):
        if sheet["artifact_key"] in seen: raise ValueError(views.PREFIX + "pssm_population_duplicate")
        seen.add(sheet["artifact_key"])
        try:
            result = _pssm.calculate_blast_pssm_components(sheet)
        except (ValueError, TypeError, KeyError, IndexError, ArithmeticError) as error:
            result = None
            failure = _failure(pointer=f"/pssm/{index}"); failure["artifact_key"] = sheet["artifact_key"]
            out["issues"].append(failure)
            if diagnostics is not None:
                diagnostics.append(dict(issue_index=len(out["issues"]) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
        out["pssm"].append(dict(artifact_key=sheet["artifact_key"], components=result))
    bindings = [r["sheet"]["search_binding"] for r in sheets["sequence"]]
    facts = populate_native_blast_database_search_facts(collection, source_statuses=statuses, search_bindings=bindings)
    out["search_facts"] = [{k: r[k] for k in ("search_key", "status", "counts")} for r in facts]
    # The common facts helper labels the native table control count as HSPs;
    # standard rows give it the distinct alignment-row unit mandated by327.
    for row in out["search_facts"]: row["counts"]["declared_alignment_row_count"]["unit"] = "alignment_row"
    out["native_search_statistics"] = _statistic_rows(collection, statuses)
    states = {views._hash(r["search_key"]): r["status"] for r in statuses}
    for search, key, native, length in _native_slots(collection):
        context, state = search["program_context"], states[views._hash(key["search_key"])]
        geometry = context["geometry_program"]
        try:
            if resolve_blast_program_context(**{k: v for k, v in context.items() if k != "geometry_program"}) != context: geometry = None
        except ValueError:
            geometry = None
        if state != "available": native, geometry = None, None
        calculator = alignment_component_artifacts if _retain_correspondence else alignment_components
        component = calculator(native, program=geometry,
            query_length=search["normalized"]["query"]["length"],
            reference_length=length, coordinate_convention="blast_json2" if search["normalized"]["format"] == "json2" else "directional")
        if _retain_correspondence:
            component, common_sheet, common_components = component
            out["correspondence"]["instances"].append({"legacy_pointer": f"/native_hsp_components/{len(out['native_hsp_components'])}/component",
                "axis_basis": "reported", "sheet": common_sheet, "components": common_components})
        out["native_hsp_components"].append(dict(row_key=key, component=component,
            status="unavailable" if native is None and state != "incompatible" else "incompatible" if geometry is None else "available"))
    out["qualified_hsp_components"] = _qualified_rows(sheets, out)
    if _retain_correspondence:
        validate_standard_blast_correspondence(out, admission=True)
    return views._copy(out)


def calculate_standard_blast_database_sheets(sheet_set: dict, *, sequence_model: dict | None,
        _retain_correspondence=False) -> dict:
    """Retain complete direct scientific returns; failed searches have null components."""
    return _calculate(sheet_set, sequence_model=sequence_model, _retain_correspondence=_retain_correspondence)


def validate_standard_blast_correspondence(calculations, *, admission=False):
    """Compare the required v2 common companion to its unchanged legacy cells."""
    if set(calculations) != _CALC_FIELDS | {"correspondence"} or calculations["schema"] != CALCULATION_SCHEMA_V2:
        raise ValueError(views.PREFIX + "correspondence_calculations_invalid")
    companion = validate_correspondence_artifacts(calculations["correspondence"], admission=admission)
    expected = {(f"/native_hsp_components/{i}/component", "reported")
        for i in range(len(calculations["native_hsp_components"]))}
    for si, entry in enumerate(calculations["sequence"]):
        result = entry["components"]
        database = result["components"]["database_sheet"] if result is not None else None
        if database is not None:
            expected.update((f"/sequence/{si}/components/components/database_sheet/hits/{hi}", "qualified")
                for hi in range(len(database["hits"])))
    if {(item["legacy_pointer"], item["axis_basis"]) for item in companion["instances"]} != expected:
        raise ValueError(views.PREFIX + "correspondence_population_conflict")
    for instance in companion["instances"]:
        legacy = _at(calculations, instance["legacy_pointer"])
        database = (_at(calculations, instance["legacy_pointer"].rsplit("/hits/", 1)[0])
            if instance["axis_basis"] == "qualified" else None)
        program = database["normalized_result"]["search"]["program"] if database is not None else None
        validate_blast_correspondence_instance(legacy, instance, program=program)
        if instance["axis_basis"] == "qualified":
            sequence_pointer = instance["legacy_pointer"].split("/components/components/database_sheet/")[0]
            result = _at(calculations, sequence_pointer + "/components/components")
            rowkey = next(row["row_key"] for row in result["row_keys"]["hits"] if row["row_key"]["hit_ordinal"] == legacy["hit_index"])
            selected = next(row for row in result["selected_query_coverage"] if row["row_key"] == rowkey)
            common = instance["components"]["selected"]["query"]
            expected_selected = {"numerator": common["observed_numerator"], "denominator": common["denominator"],
                "value": common["complete_value"], "complete_for_reported_hsps": common["complete_for_original_rows"]}
            if not _same(expected_selected, {key: selected[key] for key in expected_selected}):
                raise ValueError(views.PREFIX + "correspondence_selection_conflict")


def _cell(name, value, unit, pointer, *, numerator=None, denominator=None, complete=None, reason=None, origin="derived", status=None):
    if type(value) is dict:
        saved = value; value = saved["value"]
        numerator, denominator = saved.get("numerator", numerator), saved.get("denominator", denominator)
        complete = saved.get("complete_for_reported_hsps", saved.get("complete", complete))
        reason = saved.get("unavailable_reason", saved.get("reason", reason))
        status, origin = saved.get("status", status), saved.get("origin", origin)
    if any(v is not None and not _number(v) for v in (value, numerator, denominator)): raise ValueError(views.PREFIX + "numeric_cell_invalid")
    if value is None:
        reason = reason or "missing_input"
        if reason not in views.REASONS: raise ValueError(views.PREFIX + "missingness_invalid")
        status = "incompatible" if status == "incompatible" or reason == "incompatible_input" else "unavailable"
    else: status, reason = "available", None
    return dict(name=name, value=value, numerator=numerator, denominator=denominator, unit=unit, status=status,
        reason=reason, origin=origin, complete=complete, component_pointer=pointer)


def _boolean(name, value, pointer, *, reason=None, origin="derived"):
    if value is not None and type(value) is not bool: raise ValueError(views.PREFIX + "boolean_cell_invalid")
    return dict(name=name, value=value, status="available" if value is not None else "incompatible" if reason == "incompatible_input" else "unavailable",
        reason=None if value is not None else reason or "missing_input", origin=origin, component_pointer=pointer)


class _Builder:
    def __init__(self, attempt, calculation_id, sheets, calculations):
        self.attempt, self.calculation_id, self.sheets, self.calc = attempt, calculation_id, sheets, calculations
        self.collection, self.rows = sheets["collection"], []
        self.program = self.collection["invocation"]["execution_program"]
        self.searches = {views._hash(s["search_key"]): s for s in self.collection["searches"]}

    def add(self, family, identity, base, values, *, key=None, details=None, booleans=None, status="available", refs=None):
        details, booleans = details or {}, booleans or {}
        qunit, runit, aunit = views.UNITS[self.program]
        context = dict(query_axis_kind="pssm_master" if self.collection["invocation"]["query_kind"] == "pssm" else "sequence",
            reference_axis_kind="sequence", stage=None, query_unit=qunit, reference_unit=runit, alignment_unit=aunit)
        if key is not None:
            bound = [r["sheet"]["search_binding"] for r in self.sheets["sequence"] if r["search_key"] == key]
            if len(bound) == 1 and bound[0]["provenance"] is not None: context["stage"] = bound[0]["stage"]
        if family == "sequence_population": context["count_unit"] = identity["count_unit"]
        cells = []
        for name, definition in views.METRICS[family].items():
            detail = dict(details.get(name, {})); pointer = detail.pop("pointer", base + "/" + name)
            unit = definition["units"]
            unit = context[unit] if unit in ("query_unit", "reference_unit") else ("sequence" if identity["count_unit"] == "unique_sequences" else "sequence_group") if unit == "census_unit" else unit
            detail.setdefault("origin", definition["origin"])
            cells.append(_cell(name, values.get(name), unit, pointer, **detail))
        flags = []
        for name in views.BOOLEANS.get(family, ()):
            detail = dict(details.get(name, {})); pointer = detail.pop("pointer", base + "/" + name)
            flags.append(_boolean(name, booleans.get(name), pointer, **detail))
        component_refs = deepcopy(refs) if refs is not None else [dict(artifact_role="calculations", pointer=base)]
        documents = dict(calculations=self.calc, sheets=self.sheets, collection=self.collection)
        for cell in cells + flags:
            pointer = cell["component_pointer"]
            while True:
                role = None
                for candidate, document in documents.items():
                    try: _at(document, pointer)
                    except (KeyError, IndexError, ValueError, TypeError): continue
                    role = candidate; break
                if role is not None: break
                if cell["value"] is not None or not pointer: raise ValueError(views.PREFIX + "component_pointer_unresolved")
                pointer = pointer.rsplit("/", 1)[0]
            cell["component_pointer"] = pointer
            if not any(r["artifact_role"] == role and (r["pointer"] == pointer or pointer.startswith(r["pointer"] + "/")) for r in component_refs):
                component_refs.append(dict(artifact_role=role, pointer=pointer))
        row = dict(schema=views.PREFIX + "numeric_row_v1", family=family,
            record_key=views.PREFIX + "row_" + views._hash(dict(version=views.PREFIX + "row_identity_v1", attempt=self.attempt, family=family, identity=identity)),
            calculation_id=self.calculation_id, identity=deepcopy(identity), program=self.program, context=context,
            component_refs=component_refs, native_status=status, measurements=cells, booleans=flags)
        views._validate_row(row, self.calculation_id)
        self.rows.append(row)


def _search_rows(builder):
    for i, fact in enumerate(builder.calc["search_facts"]):
        key = fact["search_key"]; search = builder.searches[views._hash(key)]
        base = f"/search_facts/{i}"; limit = search["reporting"]["requested_hit_limit"]
        count = fact["counts"]["reported_hit_count"]["value"]
        reached = count >= limit if type(count) is int and type(limit) is int else None
        result = builder.calc["sequence"][i]["components"]
        status = result["status"] if result is not None else fact["status"]
        details = {name: dict(pointer=base + "/counts/" + name) for name in fact["counts"]}
        details["limit_reached"] = dict(pointer=f"/collection/searches/{i}/reporting")
        builder.add("search", dict(search_key=key), base, fact["counts"], key=key, status=status, details=details, booleans=dict(limit_reached=reached))
    for i, row in enumerate(builder.calc["native_search_statistics"]):
        base = f"/native_search_statistics/{i}"
        builder.add("search_statistic", dict(search_key=row["search_key"]), base, row["measurements"], key=row["search_key"], status=row["status"],
            details={n: dict(pointer=base + "/measurements/" + n) for n in row["measurements"]})


def _hsp_rows(builder):
    qualified = {views._hash(r["row_key"]): r for r in builder.calc["qualified_hsp_components"]}
    for i, row in enumerate(builder.calc["native_hsp_components"]):
        key, component = row["row_key"], row["component"]
        base = f"/native_hsp_components/{i}/component"
        values, details = {}, {}
        paths = {"native_score_bits": ("native_scores", "bit_score"), "native_raw_score": ("native_scores", "score"), "native_evalue": ("native_scores", "evalue"),
            **{"native_reported_" + name: ("reported_counts", field) for name, field in (("alignment_columns", "align_len"), ("identity_count", "identity"), ("positive_count", "positive"), ("gap_count", "gaps"))},
            **{"native_reported_" + name: ("reported_percentages", name) for name in ("identity_percent", "query_coverage_percent", "query_subject_coverage_percent", "query_unique_subject_coverage_percent")},
            **{n: ("counts", n) for n in ("alignment_columns", "paired_columns", "identical_pairs", "query_gap_columns", "reference_gap_columns")},
            "paired_query_units": ("counts", "paired_query_positions"), "paired_reference_units": ("counts", "paired_reference_positions"),
            "paired_identity": ("fractions", "paired_identity"), "alignment_identity": ("fractions", "alignment_identity"),
            "reported_query_length": ("denominators", "query_length"), "reported_reference_length": ("denominators", "reference_length"),
            "reported_query_coverage": ("fractions", "query_paired_coverage"), "reported_reference_coverage": ("fractions", "reference_paired_coverage")}
        invalid = any(issue["code"] == "hsp_object_required" for issue in component["issues"])
        for name, (group, field) in paths.items():
            values[name] = component[group].get(field)
            reason = "invalid_native_row" if invalid else "incompatible_input" if row["status"] == "incompatible" else "missing_input"
            geometry_field = name in ("paired_query_units", "paired_reference_units", "reported_query_coverage", "reported_reference_coverage")
            if geometry_field and not component["geometry_available"]: reason = "invalid_native_row" if component["traceback_available"] else "not_measured"
            details[name] = dict(pointer=base + "/" + group + "/" + field, reason=reason,
                origin="native_traceback" if group in ("counts", "fractions") and component["traceback_available"] else "native_report")
        for name, numerator, denominator in (("paired_identity", "identical_pairs", "paired_columns"), ("alignment_identity", "identical_pairs", "alignment_columns"),
                ("reported_query_coverage", "paired_query_positions", "query_length"), ("reported_reference_coverage", "paired_reference_positions", "reference_length")):
            details[name].update(numerator=component["counts"].get(numerator), denominator=component["denominators"].get(denominator),
                complete=component["geometry_available"] if name.endswith("coverage") else None)
        q = qualified[views._hash(key)]; pointer = q["component_pointer"]
        qualified_component = _at(builder.calc, pointer) if pointer is not None else None
        for axis in ("query", "reference"):
            for name, group, field in (("qualified_paired_" + axis + "_units", "counts", "paired_" + axis + "_positions"),
                    ("full_" + axis + "_paired_coverage", "fractions", axis + "_paired_coverage")):
                values[name] = qualified_component[group].get(field) if qualified_component else None
                details[name] = dict(pointer=pointer + "/" + group + "/" + field if pointer else f"/qualified_hsp_components/{i}",
                    reason="invalid_native_row" if qualified_component and not qualified_component["geometry_available"] else "missing_input", origin="native_traceback")
                if group == "fractions" and qualified_component:
                    details[name].update(numerator=qualified_component["counts"].get("paired_" + axis + "_positions"), denominator=qualified_component["denominators"].get(axis + "_length"), complete=qualified_component["geometry_available"])
        flag = qualified_component["geometry_available"] if qualified_component else None
        details["qualified_geometry_available"] = dict(pointer=pointer + "/geometry_available" if pointer else f"/qualified_hsp_components/{i}")
        builder.add("hsp", dict(row_key=key), base, values, key=key["search_key"], details=details,
            status="invalid" if invalid else "complete" if component["geometry_available"] and not component["issues"] else "partial",
            booleans=dict(qualified_geometry_available=flag))


def _sequence_rows(builder, index, item):
    result = item["components"]
    if result is None: return
    c, key = result["components"], item["search_key"]
    database, weights = c["database_sheet"], c["function_weights"]
    if database is None: return
    base = f"/sequence/{index}/components/components"; dbbase = base + "/database_sheet"; wbase = base + "/function_weights"
    byhit = {r["row_key"]["hit_ordinal"]: r for r in c["row_keys"]["hits"]}
    selected = {views._hash(r["row_key"]): (i, r) for i, r in enumerate(c["selected_query_coverage"])}
    for hi, hit in enumerate(database["hits"]):
        rowkey = byhit[hit["hit_index"]]["row_key"]
        b = dbbase + f"/hits/{hi}/measurements"; values = dict(hit["measurements"])
        details = {}; selection = selected.get(views._hash(rowkey))
        if selection:
            values["selected_query_coverage"] = selection[1]
            details["selected_query_coverage"] = dict(pointer=base + f"/selected_query_coverage/{selection[0]}")
        refs = [r for r in c["coordinate_context"]["references"] if r["row_key"] == rowkey]
        for axis in ("query", "reference"):
            length = c["coordinate_context"]["query"]["full_length"] if axis == "query" else refs[0]["full_length"] if len(refs) == 1 else None
            details[axis + "_paired_coverage"] = dict(numerator=values["observed_paired_" + axis + "_positions"], denominator=length,
                complete=values["traceback_complete"], reason="partial_output" if not values["traceback_complete"] else "missing_input")
        details["geometry_complete"] = dict(pointer=b + "/traceback_complete")
        builder.add("sequence_hit", dict(row_key=rowkey), b, values, key=key, details=details, status=result["status"], booleans=dict(geometry_complete=values["traceback_complete"]))
    for gi, group in enumerate(database["sequence_groups"]):
        b = dbbase + f"/sequence_groups/{gi}"
        builder.add("sequence_group", dict(search_key=key, hit_ordinals=sorted(group["hit_indices"])), b,
            dict(maximum_bit_score=group["maximum_bit_score"], hit_representation_count=len(group["hit_indices"]), explicit_function_count=len(group["functions"])),
            key=key, status=result["status"], details=dict(hit_representation_count=dict(pointer=b + "/hit_indices"), explicit_function_count=dict(pointer=b + "/functions")))
    for fi, function in enumerate(database["functions"]):
        name, b = function["function"], dbbase + f"/functions/{fi}"
        values, details = {}, {}
        for field, source in (("sequence_group_count", "sequence_group_count"), ("native_hit_count", "native_hit_count"),
                ("maximum_bit_score", "bit_score/maximum"), ("mean_bit_score", "bit_score/mean"), ("scored_group_count", "bit_score/count")):
            values[field] = _at(function, "/" + source); details[field] = dict(pointer=b + "/" + source)
        for field, source in (("function_mass", "function_masses"), ("function_prior", "parameters/function_priors"),
                ("unadjusted_probability", "unadjusted_probabilities"), ("representation_adjusted_probability", "representation_adjusted_probabilities")):
            mapping = _at(weights, "/" + source) if weights is not None else None
            values[field] = mapping.get(name) if type(mapping) is dict else None
            details[field] = dict(pointer=wbase + "/" + source + (_pointer(name) if type(mapping) is dict and name in mapping else ""))
        if weights:
            products = {f: weights["parameters"]["function_priors"][f] * m for f, m in weights["function_masses"].items()}
            if name in products: details["unadjusted_probability"].update(numerator=products[name], denominator=math.fsum(products.values()))
            census = {r["function"]: r["database_sequence_count"] for r in database["database_representation"]["function_representation"]}
            if values["representation_adjusted_probability"] is not None:
                corrected = {f: mass / census[f] for f, mass in products.items()}
                details["representation_adjusted_probability"].update(numerator=corrected[name], denominator=math.fsum(corrected.values()))
        details["calibrated_annotation_probability"] = dict(pointer=wbase + "/calibrated_annotation_probability")
        builder.add("sequence_function", dict(search_key=key, function=name), b, values, key=key, details=details, status=result["status"],
            booleans=dict(calibrated_annotation_probability=weights["calibrated_annotation_probability"] if weights else None))
    for pi, population in enumerate(database["database_representation"]["function_representation"]):
        count_unit = database["database_profile"]["count_unit"]
        if count_unit not in ("unique_sequences", "sequence_groups"): continue
        b = dbbase + f"/database_representation/function_representation/{pi}"
        builder.add("sequence_population", dict(search_key=key, function=population["function"], count_unit=count_unit), b, population, key=key,
            status=result["status"], details=dict(database_fraction=dict(numerator=population["database_sequence_count"], denominator=population["database_total_sequence_count"])))
    owners = [(None, database, dbbase)] + [(r["function"], r, dbbase + f"/functions/{i}") for i, r in enumerate(database["functions"])]
    for function, owner, b in owners:
        taxonomy = owner["taxonomy"]
        for ri, rank in enumerate(taxonomy["ranks"]):
            matching, conflicting = rank["target_matching_groups"], rank["target_conflicting_groups"]
            details = dict(same_taxon_pair_fraction=dict(numerator=rank["same_taxon_pair_count"], denominator=rank["comparable_pair_count"]),
                target_matching_fraction=dict(numerator=matching, denominator=matching + conflicting if matching is not None and conflicting is not None else None),
                target_independent_of_search=dict(pointer=b + "/taxonomy/target_independent_of_search"))
            builder.add("sequence_taxonomy", dict(search_key=key, function=function, rank=rank["rank"]), b + f"/taxonomy/ranks/{ri}", rank,
                key=key, details=details, status=result["status"], booleans=dict(target_independent_of_search=taxonomy["target_independent_of_search"]))
        for qi, quality in enumerate(owner["source_quality"]["assembly_measurements"]):
            sources = {}
            for hi, hit in enumerate(database["hits"]):
                associations = hit["associations"]
                assigned = [a for a in associations if any(f["function"] == function for f in a["functions"])] if function is not None else associations
                for ai, association in enumerate(associations):
                    assembly = association["assembly"]
                    if not assembly or association["metadata_index"] is None: continue
                    if function is not None:
                        taxa = {a["taxid"] for a in associations if a["description_index"] == association["description_index"] and a["taxid"] is not None}
                        if not any(a["description_index"] == association["description_index"] and (a["taxid"] == association["taxid"] or
                                (a["taxid"] is None or association["taxid"] is None) and len(taxa) <= 1) for a in assigned): continue
                    source = _sequence_quality_source(database, association)
                    record = dict(assembly_accession=assembly.get("accession"), source=association["source"], quality_method=assembly.get("quality_method"),
                        measurement_methods=assembly.get("measurement_methods") or {}, accession=association["accession"] if not assembly.get("accession") else None,
                        measurements=association["quality_measurements"])
                    if record == quality:
                        record_key = blast_record_identity(source_ref=source["source_ref"], pointer=source["pointer"], record_locator=source.get("record_locator"))
                        item = sources.setdefault(record_key, (source, []))
                        item[1].append(dict(artifact_role="calculations", pointer=dbbase + f"/hits/{hi}/associations/{ai}"))
                        if "record_locator" in source:
                            item[1].append(dict(artifact_role="calculations", pointer=dbbase + f"/reference_metadata/{association['metadata_index']}"))
            qb = b + f"/source_quality/assembly_measurements/{qi}"
            for source, refs in sources.values():
                family = "sequence_record_quality" if "record_locator" in source else "sequence_quality"
                builder.add(family, dict(search_key=key, function=function, assembly_source=source), qb + "/measurements", quality["measurements"],
                    key=key, status=result["status"], refs=[dict(artifact_role="calculations", pointer=qb), *refs])


def _pssm_rows(builder):
    for pi, entry in enumerate(builder.calc["pssm"]):
        if entry["components"] is None: continue
        for mi, matrix in enumerate(entry["components"]["matrices"]):
            base = f"/pssm/{pi}/components/matrices/{mi}"
            identity = dict(artifact_key=entry["artifact_key"], record_ordinal=matrix["record_ordinal"])
            values, details = {}, {}
            for name in views.METRICS["pssm_matrix"]:
                source = "dimensions/" + name if name in ("residue_rows", "positions") else "master/" + name.removeprefix("master_") if name.startswith("master_") else "native_statistics/" + name
                values[name] = _at(matrix, "/" + source); details[name] = dict(pointer=base + "/" + source)
            builder.add("pssm_matrix", identity, base, values, details=details, status=matrix["status"])
            for position in range(matrix["dimensions"]["positions"] or 0):
                values, details = {}, {}
                for name, array in matrix["position_diagnostics"].items():
                    values[name] = array[position] if array is not None else None
                    details[name] = dict(pointer=base + "/position_diagnostics/" + name + (f"/{position}" if array is not None else ""),
                        reason="incompatible_input" if matrix["array_status"]["pssm.intermediateData." + name] == "incompatible" else "not_measured")
                builder.add("pssm_position", {**identity, "position": position}, base, values, details=details, status=matrix["status"])
                for residue in range(matrix["dimensions"]["residue_rows"] or 0):
                    values, details = {}, {}
                    for name, array in matrix["matrix_values"].items():
                        values[name] = array[position][residue] if array is not None else None
                        path = "pssm." + ("finalData" if name == "scores" else "intermediateData") + "." + name
                        details[name] = dict(pointer=base + "/matrix_values/" + name + (f"/{position}/{residue}" if array is not None else ""),
                            reason="incompatible_input" if matrix["array_status"][path] == "incompatible" else "not_measured")
                    builder.add("pssm_cell", {**identity, "position": position, "residue_row": residue}, base, values, details=details, status=matrix["status"])


def build_standard_blast_database_rows(*, bundle_identity: dict, calculation_id: str, sheet_set: dict, calculations: dict) -> list:
    """Populate numerical rows by copying saved components; never run a calculator."""
    sheets, calculations, attempt = _sheet_set(sheet_set), views._copy(calculations), views._copy(bundle_identity)
    validate_schema(calculation_id, views.SHA); validate_schema(attempt, IDENTITY_SCHEMA)
    version = calculations.get("schema")
    if (version not in (CALCULATION_SCHEMA, CALCULATION_SCHEMA_V2)
            or set(calculations) != (_CALC_FIELDS | {"correspondence"} if version == CALCULATION_SCHEMA_V2 else _CALC_FIELDS)):
        raise ValueError(views.PREFIX + "calculations_invalid")
    if version == CALCULATION_SCHEMA_V2:
        validate_standard_blast_correspondence(calculations)
    keys = [r["search_key"] for r in sheets["sequence"]]
    if any([r["search_key"] for r in calculations[name]] != keys for name in ("sequence", "search_facts", "native_search_statistics")):
        raise ValueError(views.PREFIX + "calculation_search_population_conflict")
    if calculations["qualified_hsp_components"] != _qualified_rows(sheets, calculations):
        raise ValueError(views.PREFIX + "qualified_pointer_conflict")
    builder = _Builder(attempt, calculation_id, sheets, calculations)
    _search_rows(builder); _hsp_rows(builder)
    for index, row in enumerate(calculations["sequence"]): _sequence_rows(builder, index, row)
    _pssm_rows(builder)
    seen = {}
    for row in builder.rows:
        if row["record_key"] in seen:
            previous = seen[row["record_key"]]
            if {k: v for k, v in previous.items() if k != "component_refs"} != {k: v for k, v in row.items() if k != "component_refs"}:
                raise ValueError(views.PREFIX + "row_identity_conflict")
            previous["component_refs"].extend(r for r in row["component_refs"] if r not in previous["component_refs"])
        else: seen[row["record_key"]] = row
    return list(seen.values())


__all__ = ["calculate_standard_blast_database_sheets", "build_standard_blast_database_rows", "validate_sequence_model", "CALCULATION_SCHEMA"]
