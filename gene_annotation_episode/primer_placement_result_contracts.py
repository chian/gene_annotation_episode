"""Finite ordinary views of the existing all-placement scientific authority.

This module copies stored cells and supplied operand metadata. It enumerates no
placements, calculates no mismatch statistic and grants no nested reference.
"""
from copy import deepcopy
import hashlib
import re

from jsonschema import Draft202012Validator, validators

from . import molecular_sequence_result_contracts as stored
from .execution_contracts import canonical
from .native_file_capture import _identity as file_identity


TOOL = "align_sequences"
PACKET_VERSION = "ordinary_primer_placement_values_v1"
SOURCE_VERSION = "ordinary_primer_placement_result_v1"
FACT_SOURCE = "primer_placement_outcomes"
CONTEXT_VERSION = "primer_placement_public_context_v1"
OPERANDS_VERSION = "ordinary_primer_placement_operands_v1"
SOURCE_ASSUMPTIONS = ("All complete ungapped windows, <=1 literal mismatch, source uppercasing, A/C/G/T-only reverse complement; "
    "retained occurrences are not PCR, primer-design, significance or confidence evidence. Candidate windows are structural counts, not execution attestations.")
_KINDS = ({"kind": "summary"}, {"kind": "placement_group", "group_ordinal": 0},
    {"kind": "placement_hit", "group_ordinal": 0, "native_hit_ordinal": 0},
    {"kind": "placement_mismatch", "group_ordinal": 0, "native_hit_ordinal": 0, "native_mismatch_ordinal": 0})
_INPUT_KEYS = ("target_sequence", "primers", "target_ref", "primer_refs", "target_mapping", "primer_mappings")
_GROUP_KEYS = ("group_ordinal", "primer_occurrence_ordinal", "native_group_ordinal", "primer_length_symbols",
    "native_primer_length_symbols", "candidate_windows_per_orientation", "candidate_oriented_windows",
    "reported_hit_count", "native_sequence_matches_occurrence", "issues")
_SOURCE = re.compile(r"source_[0-9a-f]{24}")
_STRICT = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _checker, value: type(value) is int))
_LITERAL = {"$ref": "#/$defs/PrimerLiteral"}
_DEFS = {"PrimerLiteral": {"anyOf": [{"type": ["string", "number", "boolean", "null"]},
    {"type": "array", "items": _LITERAL}, {"type": "object", "additionalProperties": _LITERAL}]}}


def _require(condition, code="contract_invalid"):
    if not condition:
        raise ValueError("ordinary_primer_placement_" + code)


def _obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _document(schema, *, definitions=None):
    merged = deepcopy(_DEFS)
    if definitions is not None:
        _require(type(definitions) is dict and not set(merged).intersection(definitions), "local_definition_collision")
        merged.update(deepcopy(definitions))
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": merged, **deepcopy(schema)}


def _shape(value, schema):
    value = stored.copy_json(value)
    try:
        _STRICT(schema).validate(value)
    except Exception as error:
        raise ValueError("ordinary_primer_placement_closed_shape_required") from error
    return value


def profile():
    stem = "ordinary_primer_placement"
    return dict(operation=TOOL, fact_source=FACT_SOURCE, native_source="molecular",
        native_request_version="molecular_sequence_request_v1", deployment_version="molecular_sequence_deployment_v1",
        driver_request_version="molecular_sequence_driver_request_v1", native_argument_names=[], molecule_model="dna",
        operand_version=stem + "_sequence_operand_v1", prepared_version=stem + "_prepared_v1",
        execution_version=stem + "_execution_v1", binding_version=stem + "_attempt_binding_v1",
        binding_filename="ordinary-primer-placement-input-binding.json", intent_version=stem + "_intent_v1",
        saved_intent_version=stem + "_saved_intent_v1", custody_version=stem + "_publication_v1",
        saved_custody_version=stem + "_saved_publication_v1", public_version=PACKET_VERSION,
        source_version=SOURCE_VERSION, packet_format=stem + "_values_packet_v1",
        publication_request_version=stem + "_publication_request_v1", saved_request_version=stem + "_saved_request_v1",
        read_receipt_version=stem + "_read_receipt_v1", calculation_started_version=stem + "_calculation_started_v1",
        calculation_result_version=stem + "_calculation_result_v1", calculation_diagnostic_version=stem + "_calculation_diagnostic_v1",
        calculator_id="primer_placement_measurements.calculate_primer_placement_components",
        selector_version=stored.PLACEMENT_SELECTOR_VERSION, projection_version=stored.PLACEMENT_PROJECTION_VERSION,
        selected_values_version=stored.PLACEMENT_PUBLIC_VERSION)


def _rows_schema():
    variants = []
    for identity in _KINDS:
        fields = stored.field_table(TOOL, identity, profile=stored._PLACEMENT_PROFILE)
        variants.append(_obj(dict(row_id=_obj({key: {"const": value} if key == "kind" else
            {"type": "integer", "minimum": 0} for key, value in identity.items()}),
            fields=dict(type="array", minItems=1, uniqueItems=True, items={"enum": list(fields)}))))
    return dict(type="array", items={"anyOf": variants})


def argument_schema(*, native=True, saved=True):
    reference = {"type": "string", "minLength": 1}
    variants = []
    if native:
        variants.append(_obj(dict(mode={"const": "run_native"}, target_ref=reference,
            primer_refs={"anyOf": [reference, {"type": "array", "items": reference}]}, rows=_rows_schema())))
    if saved:
        variants.extend(_obj(dict(mode={"const": mode}, result_ref={"type": "string", "pattern": "^source_[0-9a-f]{24}$"},
            rows=_rows_schema())) for mode in ("calculate_saved", "read_stored"))
    _require(bool(variants), "modes_required")
    return _document({"anyOf": variants})


def validate_arguments(arguments):
    arguments = _shape(arguments, argument_schema())
    selector(arguments)
    return arguments


def selector(arguments):
    return stored.validate_molecular_sequence_result_selector(dict(version=profile()["selector_version"],
        mode="original_attempt", operation=TOOL, saved_sheet_ref=None, rows=deepcopy(arguments["rows"]), return_files=[]))


def operand_records(operand):
    primers = operand["primers"]
    return [operand["target"], *(primers if type(primers) is list else [primers])]


def admission_matches(operand, admissions):
    primers = admissions["primers"]
    records = [admissions["target"], *(primers if type(primers) is list else [primers])]
    return ((type(operand["primers"]) is list) == (type(primers) is list)
        and len(operand_records(operand)) == len(records)
        and all(canonical(value["subject"]) == canonical(received["input"]["witness"]["record"])
            for value, received in zip(operand_records(operand), records)))


def operand_files(operand):
    primers = operand["primers"]
    return dict(target=deepcopy(operand["target"]["input_file"]),
        primers=[deepcopy(row["input_file"]) for row in primers] if type(primers) is list else deepcopy(primers["input_file"]))


def validate_operands(operand, arguments):
    operand = stored.copy_json(operand)
    stored.closed(operand, ("version", "target", "primers"))
    _require(operand["version"] == OPERANDS_VERSION, "operands_version_invalid")
    requested = arguments["primer_refs"]
    _require((type(requested) is list) == (type(operand["primers"]) is list), "primer_input_form_conflict")
    refs = [arguments["target_ref"], *(requested if type(requested) is list else [requested])]
    records = operand_records(operand)
    _require(len(records) == len(refs), "primer_occurrence_population_conflict")
    seen = {}
    for reference, value in zip(refs, records):
        stored.closed(value, ("version", "subject", "sequence", "parent_mapping", "mapping_failure", "input_file", "associations", "footprint"))
        _require(value["version"] == profile()["operand_version"] and type(value["subject"]) is dict
            and value["subject"].get("id") == reference and type(value["sequence"]) is str
            and type(value["associations"]) is dict and type(value["footprint"]) is list, "operand_invalid")
        _require(value["parent_mapping"] is None or type(value["parent_mapping"]) is dict, "operand_mapping_invalid")
        _require(value["mapping_failure"] in (None, {"code": "subregion_mapping_unavailable"})
            and (value["parent_mapping"] is None) == (value["mapping_failure"] is not None), "operand_mapping_failure_conflict")
        file = file_identity(value["input_file"])
        raw = value["sequence"].encode("ascii")
        _require(file["artifact_ref"] == "artifact_" + file["sha256"]
            and file["format"] == "ascii_sequence" and file["sha256"] == hashlib.sha256(raw).hexdigest()
            and file["size_bytes"] == len(raw), "operand_file_identity_conflict")
        _require(not value["subject"].get("sequence_ref") or value["subject"]["sequence_ref"] == file["artifact_ref"],
            "operand_file_identity_conflict")
        encoded = canonical(value)
        _require(reference not in seen or seen[reference] == encoded, "duplicate_operand_conflict")
        seen[reference] = encoded
    return operand


def native_arguments(arguments, operand):
    operand = validate_operands(operand, arguments)
    primers = operand["primers"]
    return dict(long_seq=operand["target"]["sequence"], short_seqs=[row["sequence"] for row in primers]
        if type(primers) is list else primers["sequence"])


def scientific_context(arguments, operand):
    operand = validate_operands(operand, arguments)
    records = operand_records(operand)[1:]
    return dict(target_ref=arguments["target_ref"], primer_refs=[row["subject"]["id"] for row in records],
        target_mapping=operand["target"]["parent_mapping"], primer_mappings=[row["parent_mapping"] for row in records])


def context(*, sheet, components, source_files, original_files=None, frozen_input=None):
    sheet_available = source_files["sheet"]["file"] is not None
    components_available = source_files["components"]["file"] is not None
    inputs = sheet.get("inputs") if sheet_available and type(sheet) is dict else None
    groups = components.get("groups") if components_available and type(components) is dict else None
    if type(inputs) is dict and frozen_input is not None:
        _require(canonical({key: inputs.get(key) for key in _INPUT_KEYS}) == canonical(frozen_input), "sheet_operand_conflict")
    return dict(version=CONTEXT_VERSION, sheet_state=source_files["sheet"]["state"],
        components_state=source_files["components"]["state"],
        input=deepcopy(frozen_input) if type(inputs) is not dict else {key: deepcopy(inputs.get(key)) for key in _INPUT_KEYS},
        original_operand_files=deepcopy(original_files),
        native_outcome=None if not sheet_available or type(sheet) is not dict else deepcopy(sheet.get("native_outcome")),
        component_status=None if not components_available or type(components) is not dict else deepcopy(components.get("status")),
        population=None if not components_available or type(components) is not dict else deepcopy(components.get("summary")),
        group_populations=None if type(groups) is not list else [dict(state=row.get("state", "present"),
            **{key: deepcopy(row.get(key)) for key in _GROUP_KEYS}) for row in groups],
        definitions=None if not components_available or type(components) is not dict else deepcopy(components.get("definitions")),
        issues=None if not components_available or type(components) is not dict else deepcopy(components.get("issues")),
        source_assumptions=SOURCE_ASSUMPTIONS)


def packet(custody):
    return dict(version=PACKET_VERSION, selection={"rows": deepcopy(custody["intent"]["arguments"]["rows"])},
        values=deepcopy(custody["projection"]["public"]), context=deepcopy(custody["context"]),
        file_states={role: custody["source_files"][role]["state"] for role in ("capture", "sheet", "components")},
        failures=deepcopy(custody["failures"]))


def _context_schema():
    count = {"anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]}
    file = _obj(dict(artifact_ref={"type": "string", "pattern": "^artifact_[0-9a-f]{64}$"},
        sha256={"type": "string", "pattern": "^[0-9a-f]{64}$"}, size_bytes={"type": "integer", "minimum": 0},
        format={"const": "ascii_sequence"}))
    nullable = lambda value: {"anyOf": [value, {"type": "null"}]}
    group = _obj(dict(state={"enum": ["present", "incompatible"]},
        **{key: deepcopy(count) for key in _GROUP_KEYS if key not in ("native_sequence_matches_occurrence", "issues")},
        native_sequence_matches_occurrence=nullable({"type": "boolean"}), issues=deepcopy(_LITERAL)))
    return _obj(dict(version={"const": CONTEXT_VERSION},
        sheet_state={"enum": list(stored.FILE_STATES)}, components_state={"enum": list(stored.FILE_STATES)},
        input=nullable(_obj({key: deepcopy(_LITERAL) for key in _INPUT_KEYS})),
        original_operand_files=nullable(_obj(dict(target=file, primers={"anyOf": [file, {"type": "array", "items": file}]}))),
        native_outcome={"enum": [None, "completed", "failed", "partial", "truncated", "unknown"]},
        component_status={"enum": [None, "complete", "partial"]},
        population=nullable(_obj({key: deepcopy(count) for key in stored.PLACEMENT_SUMMARY})),
        group_populations=nullable(dict(type="array", items=group)), definitions=deepcopy(_LITERAL),
        issues=deepcopy(_LITERAL), source_assumptions={"const": SOURCE_ASSUMPTIONS}))


def _return_schema():
    sources = stored.molecular_sequence_fact_sources(profile=stored._PLACEMENT_PROFILE)
    candidates = sources[stored.PROJECTION_SOURCE]["report_schema"]["items"]["anyOf"]
    projection = deepcopy(next(row for row in candidates if row["properties"]["operation"].get("const") == TOOL))
    issue = deepcopy(sources[stored.FAILURE_SOURCE]["report_schema"]["items"])
    def opaque(value):
        if type(value) is dict:
            if value.get("x-reference-namespace") == "artifact":
                value.pop("format", None); value.pop("x-reference-namespace", None)
            for child in value.values(): opaque(child)
        elif type(value) is list:
            for child in value: opaque(child)
    opaque(projection); opaque(issue)
    return _document(_obj(dict(version={"const": PACKET_VERSION},
        source_ref={"type": "string", "pattern": "^source_[0-9a-f]{24}$", "format": "reference", "x-reference-namespace": "source"},
        selection=_obj(dict(rows=_rows_schema())), values=projection, context=_context_schema(),
        file_states=_obj({role: {"enum": [state for state in stored.FILE_STATES if state != "produced_unretained"]}
            for role in ("capture", "sheet", "components")}), failures=dict(type="array", items=issue))),
        definitions=sources[stored.PROJECTION_SOURCE]["report_schema"].get("$defs", {}))


def validate_packet(value):
    if type(value) is dict:
        stored._validate_placement_copy_inputs(value.get("values"))
    value = stored.copy_json(value)
    schema = _return_schema()
    schema["properties"].pop("source_ref"); schema["required"].remove("source_ref")
    value = _shape(value, schema)
    stored.validate_molecular_sequence_fact_values(stored.PROJECTION_SOURCE, [value["values"]])
    expected = [(item["row_id"], field) for item in value["selection"]["rows"] for field in item["fields"]]
    _require([(row["row_id"], row["field"]) for row in value["values"]["rows"]] == expected, "selection_conflict")
    selector({"rows": value["selection"]["rows"]})
    for role in ("sheet", "components"):
        _require(value["context"][role + "_state"] == value["file_states"][role] == value["values"]["source_states"][role], "state_conflict")
    files = value["context"]["original_operand_files"]
    if files is not None:
        for file in [files["target"], *(files["primers"] if type(files["primers"]) is list else [files["primers"]])]:
            file_identity(file)
            _require(file["artifact_ref"] == "artifact_" + file["sha256"], "operand_file_identity_conflict")
        inputs = value["context"]["input"]
        _require(type(inputs) is dict and (type(inputs["primers"]) is list) == (type(files["primers"]) is list),
            "operand_input_form_conflict")
        sequences = [inputs["target_sequence"], *(inputs["primers"] if type(inputs["primers"]) is list else [inputs["primers"]])]
        identities = [files["target"], *(files["primers"] if type(files["primers"]) is list else [files["primers"]])]
        _require(len(sequences) == len(identities), "operand_input_population_conflict")
        for sequence, file in zip(sequences, identities):
            _require(type(sequence) is str, "operand_sequence_invalid")
            raw = sequence.encode("ascii")
            _require(file["sha256"] == hashlib.sha256(raw).hexdigest() and file["size_bytes"] == len(raw), "operand_file_identity_conflict")
    for row in value["values"]["rows"]:
        path, _type, unit, population, _denominators = stored.field_table(TOOL, row["row_id"], profile=stored._PLACEMENT_PROFILE)[row["field"]]
        _require(row["source_pointer"] == path and row["unit"] == unit
            and row["population_id"] == population, "field_meaning_conflict")
        if row["row_id"]["kind"] == "summary" and row["value_state"] in ("stored_value", "stored_null"):
            _require(type(value["context"]["population"]) is dict
                and canonical(row["value"]) == canonical(value["context"]["population"].get(row["field"])), "population_conflict")
        for operand in row["denominators"]:
            if operand["source_pointer"].startswith("/summary/") and operand["value_state"] in ("stored_value", "stored_null"):
                population = value["context"]["population"]
                _require(type(population) is dict and canonical(operand["value"]) == canonical(
                    population.get(operand["source_pointer"].removeprefix("/summary/"))), "population_operand_conflict")
    return value


def validate_return(value):
    _require(type(value) is dict and type(value.get("source_ref")) is str and _SOURCE.fullmatch(value["source_ref"]), "source_required")
    validate_packet({key: item for key, item in value.items() if key != "source_ref"})
    return stored.copy_json(value)


def fact_sources():
    item = _return_schema()
    description = "Selected retained literal short-sequence placement occurrences, full original operands and separate native/checked/structural populations; not PCR, design or confidence. Only the top Source grants a reference."
    return {FACT_SOURCE: dict(type="array", report_schema={"$schema": item["$schema"], "$defs": item["$defs"],
        "type": "array", "items": {key: child for key, child in item.items() if key not in ("$schema", "$defs")},
        "x-source": FACT_SOURCE}, description=description, meaning=description)}


def schema(kind="Return"):
    if kind == "Arguments": return argument_schema()
    if kind == "Context": return _document(_context_schema())
    value = _return_schema()
    if kind == "Packet":
        value["properties"].pop("source_ref"); value["required"].remove("source_ref")
    else:
        _require(kind == "Return", "schema_kind_invalid")
    return value


ordinary_primer_placement_fact_sources = fact_sources
validate_ordinary_primer_placement_return = validate_return
