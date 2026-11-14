"""A102 native protein-structure execution bindings."""


def validate_primary_resource_bindings(configuration, kind):
    bindings = configuration.get('native_protein_structure')
    if bindings is None:
        return
    if kind != 'local':
        raise ValueError('native_protein_structure_resource_execution_binding_unfinished:' + kind)
    from .native_protein_structure_contracts import validate_protein_structure_bindings
    validate_protein_structure_bindings(bindings)


def requested_job_schemas(configuration, kind, resource_id):
    bindings = configuration.get('native_protein_structure', ())
    if not bindings:
        return []
    from .native_protein_structure_tool_info import protein_structure_tool_contracts
    return [row['input_schema'] for row in protein_structure_tool_contracts(
        bindings, resource_kind=kind, resource_id=resource_id)]


def native_operation_contracts(configuration, kind, resource_id):
    bindings = configuration.get('native_protein_structure', ())
    if not bindings:
        return []
    from .native_protein_structure_tool_info import protein_structure_tool_contracts
    return protein_structure_tool_contracts(
        bindings, resource_kind=kind, resource_id=resource_id)


