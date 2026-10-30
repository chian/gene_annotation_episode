"""Copy requested definitions behind the actual paginated saved cells."""
from copy import deepcopy

from .fluorescence_event_contracts import validate_components, validate_selection
from .fluorescence_result_contracts import CONTEXT_FIELDS, CONTEXT_SCHEMA, validate_context_fields, validate_fluorescence_context
from .fluorescence_result_views import project_fluorescence_result


def project_fluorescence_context(sheet, components, *, selection, context_fields):
    """Resolve dependencies internally; expose only requested definition arrays.

    The shared result projector supplies the actual saved page. This copier
    neither evaluates gates nor traverses numerical operand arrays.
    """
    validate_components(components, sheet=sheet)
    validate_selection(selection, components=components)
    fields = validate_context_fields(context_fields)
    view = project_fluorescence_result(sheet, components, selection=selection)
    collections = dict(sources="input_sources", samples="samples", channels="channels",
        domains="measurement_domains", populations="population_definitions", gates="gate_definitions",
        control_pairs="control_pairs", native_reports="native_reports")
    indexes = {name: {row["key"]: row for row in sheet[collection]} for name, collection in collections.items()}
    needed = {name: set() for name in CONTEXT_FIELDS}
    pending = []

    def add(name, key):
        if key is not None and key not in needed[name]:
            needed[name].add(key)
            pending.append((name, key))

    def request(value):
        for name, key in (("gates", "gate_key"), ("domains", "domain_key"), ("channels", "channel_key"),
                          ("control_pairs", "control_key"), ("native_reports", "native_report_key")):
            add(name, value[key])

    for cell in view["rows"]:
        request(cell["request"])
        for name, key in (("samples", "sample_key"), ("gates", "gate_key"),
                          ("domains", "domain_key"), ("channels", "channel_key")):
            add(name, cell["population"][key])
    while pending:
        name, key = pending.pop()
        row = indexes[name][key]
        if name == "gates":
            add("samples", row["sample_key"])
            add("gates" if row["parent"]["kind"] == "gate" else "populations", row["parent"]["key"])
            add("domains", row["domain_key"])
            add("channels", row["channel_key"])
        elif name == "control_pairs":
            add("gates", row["target_gate_key"])
            add("gates", row["control_gate_key"])
        elif name == "native_reports":
            add("sources", row["source_key"])
            if row["component_request"] is not None:
                request(row["component_request"])
        elif name == "populations":
            add("samples", row["sample_key"])
        elif name == "samples":
            add("domains", row["primary_domain_key"])
            for association in row["associations"]:
                add("sources", association["source_key"])
        elif name == "domains":
            add("samples", row["sample_key"])
            add("sources", row["source_key"])
            add("domains", row["parent_domain_key"])
        elif name == "channels":
            add("domains", row["domain_key"])
            if row["analyte"] is not None:
                add("sources", row["analyte"]["source_key"])
    excluded = {"sources": {"metadata"}, "domains": {"correspondence"}, "populations": {"event_ordinals"}}
    result = dict(schema=CONTEXT_SCHEMA, selection=deepcopy(selection), context_fields=fields)
    for name, collection in collections.items():
        result[name] = [deepcopy({key: value for key, value in row.items() if key not in excluded.get(name, ())})
            for row in sheet[collection] if name in fields and row["key"] in needed[name]]
    return validate_fluorescence_context(result)
