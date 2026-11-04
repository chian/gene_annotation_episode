"""A106 access to already configured execution roles and admitted result rows."""
from copy import deepcopy

from .domain import ContractError


CONTRACT_OPERATION = "literature.intervention_analysis.contract"


def contract_catalog(services):
    """Describe only locally bound scientific contracts; perform no service I/O."""
    from .bvbrc_intervention_contracts import parameters_schema, selection_schema
    binding = _execution(services)
    if binding is None:
        return []
    resources = [name for name, service in binding.api_execution.services.items()
        if service.service == "bvbrc_appservice" and any(key in service.scientific_adapters
            for key in (("bvbrc_tnseq", "1"), ("bvbrc_rnaseq", "1")))]
    if not resources:
        return []
    return [dict(name=CONTRACT_OPERATION, description=(
        "Construct the exact native adapter and requested_schema for an existing AppService results selector. "
        "Select the configured resource, application, document-to-requirement bindings and result fields. "
        "For intervention operands select records with measurements and source_location members, or all members. "
        "The returned schema describes native selected fields; request bvbrc_application_outcomes in the child's "
        "typed parent report. This local information operation acquires nothing and establishes no service availability."),
        input_schema=dict(type="object", properties=dict(resource_id=dict(enum=resources),
            parameters=parameters_schema(), fields=dict(type="array", minItems=1, items=dict(type="object",
                properties=dict(field=dict(type="string", minLength=1), selection=selection_schema()),
                required=["field", "selection"], additionalProperties=False))),
            required=["resource_id", "parameters", "fields"], additionalProperties=False))]


def prepare_analysis_contract(services, arguments):
    from .bvbrc_appservice_adapters import selected_adapter
    binding = _execution(services)
    service = None if binding is None else binding.api_execution.services.get(arguments["resource_id"])
    if service is None or service.service != "bvbrc_appservice":
        raise ContractError("intervention_analysis_execution_unbound")
    parameters = arguments["parameters"]
    adapter_id = {"TnSeq":"bvbrc_tnseq", "RNASeq":"bvbrc_rnaseq"}.get(parameters.get("application_id"))
    selection = dict(adapter_id=adapter_id, adapter_version="1", parameters=parameters)
    selected = selected_adapter(service, selection)
    if selected is None:
        raise ContractError("intervention_analysis_adapter_unbound")
    implementation, digest = selected
    try:
        parameters = implementation.validate_parameters(parameters)
        schema = implementation.requested_form_schema(arguments["fields"])
    except ValueError as error:
        raise ContractError(str(error)) from error
    documents = {row["document_id"] for row in parameters["documents"]}
    if any(row["selection"]["document_id"] not in documents for row in arguments["fields"]):
        raise ContractError("intervention_analysis_selected_document_unbound")
    return dict(resource_id=arguments["resource_id"], adapter=deepcopy(selection), requested_schema=schema,
        adapter_implementation_sha256=digest, parent_report_source="bvbrc_application_outcomes",
        service_availability="not_observed")


def _execution(services):
    registry = getattr(getattr(services, "workflow", None), "episode_bindings", None)
    if registry is None or "results" not in registry.roles:
        return None
    binding = registry.for_role("results")
    api = getattr(binding, "api_execution", None)
    if api is None or not any(value.service == "bvbrc_appservice" for value in api.services.values()):
        return None
    return binding


def analysis_children(services):
    binding = _execution(services)
    return () if binding is None else ("launch", "results")


def received_application_rows(services, context, source_ref=None, fields=None):
    """Use exact typed receipts, never reopen a child's unrequested sheet."""
    binding = _execution(services)
    if binding is None:
        if source_ref is not None:
            raise ContractError("intervention_analysis_execution_unbound")
        return []
    groups = binding.api_execution.application_returns.received_context(context)
    rows = [row for group in groups for row in group["facts"]]
    if source_ref is None:
        return deepcopy(rows)
    result = [row for row in rows if row["source_ref"] == source_ref and row["field"] in fields]
    by_field = {row["field"]: row for row in result}
    if len(result) != len(by_field) or set(by_field) != set(fields):
        raise ContractError("intervention_analysis_field_not_received")
    return [deepcopy(by_field[name]) for name in fields]
