"""Explicit retained-artifact selections for assembly and CGA components.

The shared application return owner attaches publication custody. Nested FASTA
headers, report tokens and ContentBindings remain data, never granted Sources.
The common literal-value grammar is reused from the annotation contracts.
"""
from copy import deepcopy

from jsonschema import Draft202012Validator

from .bvbrc_annotation_contracts import selected_field_schema as _literal_field_schema
from .bvbrc_annotation_native import _canonical, _finite_json
from .bvbrc_assembly_native import REPRESENTATIONS


PARAMETERS_VERSION = "bvbrc_assembly_parameters_v1"
SELECTION_VERSION = "bvbrc_assembly_selection_v1"
VALUE_VERSION = "bvbrc_assembly_selected_field_v1"
APPLICATIONS = ("GenomeAssembly2", "ViralAssembly", "SARS2Assembly", "ComprehensiveGenomeAnalysis")
KINDS = ("native_document", "records", "components")


def _require(condition, code="bvbrc_assembly_contract_invalid"):
    if not condition:
        raise ValueError(code)


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _text():
    return dict(type="string", minLength=1)


def selection_schema():
    return _object(dict(version=dict(const=SELECTION_VERSION), document_id=_text(),
        kind=dict(enum=list(KINDS)),
        ordinals=dict(type=["array", "null"], items=dict(type="integer", minimum=0)),
        offset=dict(type="integer", minimum=0), limit=dict(type="integer", minimum=0),
        member_names=dict(type=["array", "null"], items=dict(type="string"), uniqueItems=True)))


def validate_selection(value):
    _finite_json(value)
    _require(type(value) is dict and set(value) == set(selection_schema()["properties"]))
    _require(value["version"] == SELECTION_VERSION and type(value["kind"]) is str and value["kind"] in KINDS
        and type(value["document_id"]) is str and bool(value["document_id"])
        and type(value["offset"]) is int and value["offset"] >= 0
        and type(value["limit"]) is int and value["limit"] >= 0)
    ordinals, names = value["ordinals"], value["member_names"]
    _require(ordinals is None or type(ordinals) is list and all(type(n) is int and n >= 0 for n in ordinals))
    _require(value["kind"] == "records" or ordinals is None)
    _require(names is None or type(names) is list and all(type(name) is str for name in names)
        and len(set(names)) == len(names))
    return deepcopy(value)


def parameters_schema():
    return _object(dict(version=dict(const=PARAMETERS_VERSION), analysis_id=_text(),
        application_id=dict(enum=list(APPLICATIONS)), documents=dict(type="array", minItems=1,
            items=_object(dict(document_id=_text(), requirement_id=_text(),
                representation=dict(enum=list(REPRESENTATIONS)))))))


def validate_parameters(value):
    _finite_json(value)
    try:
        Draft202012Validator(parameters_schema()).validate(value)
    except Exception as error:
        raise ValueError("bvbrc_assembly_parameters_invalid") from error
    documents = value["documents"]
    _require(len({row["document_id"] for row in documents}) == len(documents),
        "bvbrc_assembly_document_identity_ambiguous")
    for row in documents:
        allowed = {"genome_assembly_details": {"GenomeAssembly2", "ComprehensiveGenomeAnalysis"},
            "sars2_assembly_details": {"SARS2Assembly"}}.get(
            row["representation"])
        _require(allowed is None or value["application_id"] in allowed,
            "bvbrc_assembly_representation_application_conflict")
    return deepcopy(value)


def selected_field_schema():
    result = _literal_field_schema()
    result["properties"]["version"] = dict(const=VALUE_VERSION)
    result["properties"]["selection"] = selection_schema()
    return result


def requested_form_schema(fields):
    """One closed return field per caller selection, retaining caller order."""
    _finite_json(fields)
    _require(type(fields) is list)
    names, properties, definitions = [], {}, None
    for field in fields:
        _require(type(field) is dict and set(field) == {"field", "selection"}
            and type(field["field"]) is str and bool(field["field"]) and field["field"] not in names)
        name, selection = field["field"], validate_selection(field["selection"])
        schema = selected_field_schema()
        definitions = schema.pop("$defs")
        schema["properties"]["selection"] = dict(const=selection)
        schema["x-bvbrc-assembly-selection"] = selection
        properties[name] = schema
        names.append(name)
    if definitions is None:
        definitions = selected_field_schema()["$defs"]
    return dict(type="object", properties=properties, required=names, additionalProperties=False, **{"$defs": definitions})


def validate_requested_form(value):
    _finite_json(value)
    _require(type(value) is dict and set(value) == {"type", "properties", "required", "additionalProperties", "$defs"}
        and type(value["properties"]) is dict and type(value["required"]) is list)
    fields = []
    for name in value["required"]:
        _require(type(name) is str and name in value["properties"] and type(value["properties"][name]) is dict)
        fields.append(dict(field=name, selection=value["properties"][name].get("x-bvbrc-assembly-selection")))
    _require(_canonical(value) == _canonical(requested_form_schema(fields)), "bvbrc_assembly_requested_form_invalid")
    return deepcopy(value)


def validate_facts(value, *, requested_form):
    form = validate_requested_form(requested_form)
    _finite_json(value)
    try:
        Draft202012Validator(form).validate(value)
    except Exception as error:
        raise ValueError("bvbrc_assembly_facts_invalid") from error
    for field in value.values():
        accounting = field["record_accounting"]
        _require(all(accounting[key] is None or type(accounting[key]) is int for key in
            ("retained_total", "requested_occurrences", "matched_occurrences"))
            and type(accounting["returned_occurrences"]) is int
            and accounting["returned_occurrences"] == len(field["records"]), "bvbrc_assembly_facts_invalid")
        _require(all(row["requested_ordinal"] is None or type(row["requested_ordinal"]) is int
            for row in field["records"]), "bvbrc_assembly_facts_invalid")
        requested, matched = accounting["requested_occurrences"], accounting["matched_occurrences"]
        _require(matched is None or requested is not None and matched <= requested, "bvbrc_assembly_facts_invalid")
    return deepcopy(value)


def validate_selected_field(value):
    _finite_json(value)
    _require(type(value) is dict and "selection" in value)
    selection = validate_selection(value["selection"])
    form = requested_form_schema([dict(field="selected", selection=selection)])
    return validate_facts(dict(selected=value), requested_form=form)["selected"]


__all__ = ["PARAMETERS_VERSION", "SELECTION_VERSION", "VALUE_VERSION", "APPLICATIONS", "KINDS",
    "parameters_schema", "validate_parameters", "selection_schema", "validate_selection",
    "requested_form_schema", "validate_requested_form", "validate_facts", "selected_field_schema", "validate_selected_field"]
