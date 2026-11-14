"""A107 BLAST and HMMER bindings composed by the generic execution episode."""
from copy import deepcopy


def validate_primary_resource_bindings(configuration, kind):
    if 'native_blast_standard_database' in configuration and kind != 'hpc':
        raise ValueError('native_blast_standard_database_hpc_resource_required')
    if 'native_blast_database' in configuration and kind != 'hpc':
        raise ValueError('native_blast_database_hpc_resource_required')
    if 'native_hmmer' in configuration and kind != 'local':
        raise ValueError('native_hmmer_resource_execution_binding_unfinished:' + kind)
    if 'native_hmmer' in configuration:
        from .native_hmmer_tool_info import validate_native_hmmer_bindings
        validate_native_hmmer_bindings(configuration['native_hmmer'])
    if 'native_blast_masking' in configuration:
        from .native_blast_masking_tool_info import validate_native_blast_masking_bindings
        if kind != 'local':
            raise ValueError('native_blast_masking_resource_execution_binding_unfinished:' + kind)
        validate_native_blast_masking_bindings(configuration['native_blast_masking'])
    if 'native_blast_utility' in configuration:
        from .native_blast_utility_tool_info import validate_native_blast_utility_bindings
        if kind != 'local':
            raise ValueError('native_blast_utility_resource_execution_binding_unfinished:' + kind)
        validate_native_blast_utility_bindings(configuration['native_blast_utility'])
    if 'native_blast' in configuration and kind != 'local':
        raise ValueError('native_blast_resource_execution_binding_unfinished:' + kind)
    if 'native_blast' in configuration:
        from .native_blast_tool_info import validate_native_blast_bindings
        validate_native_blast_bindings(configuration['native_blast'])


def validate_preparation_resource_binding(configuration, kind):
    if 'native_hmmer_preparation' in configuration:
        from .native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
        if kind != 'local':
            raise ValueError('native_hmmer_preparation_resource_execution_binding_unfinished:' + kind)
        validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])


def install_primary_result_readers(owner):
    from .native_hmmer_results import NativeHMMERResults
    owner.native_hmmer_results = NativeHMMERResults(owner)
    # Retained received facts remain readable after a deployment is removed.
    from .native_blast_masking_results import NativeBLASTMaskingResults
    from .native_blast_masking_returns import NativeBLASTMaskingReturns
    owner.native_blast_masking_results = NativeBLASTMaskingResults(owner)
    owner.native_blast_masking_returns = NativeBLASTMaskingReturns(owner)
    from .native_blast_utility_results import NativeBLASTUtilityResults
    from .native_blast_utility_returns import NativeBLASTUtilityReturns
    owner.native_blast_utility_results = NativeBLASTUtilityResults(owner)
    owner.native_blast_utility_returns = NativeBLASTUtilityReturns(owner)
    owner.native_blast_results = owner.native_blast_returns = None
    owner.native_blast_standard_database_results = owner.native_blast_standard_database_returns = None
    if any(configuration.get('native_blast_standard_database') for configuration in owner.resources.values()):
        from .native_blast_standard_database_results import StandardBLASTDatabaseResults
        from .native_blast_standard_database_returns import StandardBLASTDatabaseReturns
        owner.native_blast_standard_database_results = StandardBLASTDatabaseResults(owner)
        owner.native_blast_standard_database_returns = StandardBLASTDatabaseReturns(owner)
    owner.native_blast_database_results = owner.native_blast_database_returns = None
    if any(configuration.get('native_blast_database') for configuration in owner.resources.values()):
        from .native_blast_database_results import NativeBLASTDatabaseResults
        from .native_blast_database_returns import NativeBLASTDatabaseReturns
        owner.native_blast_database_results = NativeBLASTDatabaseResults(owner)
        owner.native_blast_database_returns = NativeBLASTDatabaseReturns(owner)
    if any(configuration.get('native_blast') for configuration in owner.resources.values()):
        from .native_blast_results import NativeBLASTResults
        from .native_blast_returns import NativeBLASTReturns
        owner.native_blast_results = NativeBLASTResults(owner)
        owner.native_blast_returns = NativeBLASTReturns(owner)


def install_preparation_result_readers(owner):
    owner.native_hmmer_preparation_results = owner.native_hmmer_preparation_returns = None
    if any(configuration.get('native_hmmer_preparation') for configuration in owner.resources.values()):
        from .native_hmmer_preparation_results import NativeHmmerPreparationResults
        from .native_hmmer_preparation_returns import NativeHmmerPreparationReturns
        owner.native_hmmer_preparation_results = NativeHmmerPreparationResults(owner)
        owner.native_hmmer_preparation_returns = NativeHmmerPreparationReturns(owner)


def requested_job_schemas(configuration, kind, resource_id):
    """Return A107 alternatives for one resource's original requested job."""
    alternatives = []
    database = configuration.get('native_blast_standard_database')
    if database:
        from .native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
        alternatives.extend(row['input_schema'] for row in standard_blast_database_tool_contracts(
            database['bindings'], resource_kind=kind, resource_id=resource_id))
    database = configuration.get('native_blast_database')
    if database:
        from .native_blast_database_tool_info import native_blast_database_tool_contracts
        alternatives.extend(row['input_schema'] for row in native_blast_database_tool_contracts(
            database['bindings'], resource_kind=kind, resource_id=resource_id))
    native = configuration.get('native_hmmer', [])
    if native:
        from .native_hmmer_tool_info import native_hmmer_tool_contracts
        alternatives.extend(row['input_schema'] for row in native_hmmer_tool_contracts(
            native, resource_kind=kind, resource_id=resource_id))
    masking = configuration.get('native_blast_masking', [])
    if masking:
        from .native_blast_masking_tool_info import native_blast_masking_tool_contracts
        alternatives.extend(row['input_schema'] for row in native_blast_masking_tool_contracts(
            masking, resource_kind=kind, resource_id=resource_id))
    utility = configuration.get('native_blast_utility', [])
    if utility:
        from .native_blast_utility_tool_info import native_blast_utility_tool_contracts
        alternatives.extend(row['input_schema'] for row in native_blast_utility_tool_contracts(
            utility, resource_kind=kind, resource_id=resource_id))
    blast = configuration.get('native_blast', [])
    if blast:
        from .native_blast_tool_info import native_blast_tool_contracts
        alternatives.extend(row['input_schema'] for row in native_blast_tool_contracts(
            blast, resource_kind=kind, resource_id=resource_id))
    return alternatives


def preparation_job_schemas(configuration, kind, resource_id):
    preparation = configuration.get('native_hmmer_preparation', [])
    if not preparation:
        return []
    from .native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
    return [row['input_schema'] for row in native_hmmer_preparation_tool_contracts(
        preparation, resource_kind=kind, resource_id=resource_id)]


def native_operation_contracts(configuration, kind, resource_id):
    """Describe A107's configured native operations for root route composition."""
    entries = []
    database = configuration.get('native_blast_standard_database')
    if database:
        from .native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
        entries.extend(standard_blast_database_tool_contracts(database['bindings'],
            resource_kind=kind, resource_id=resource_id))
    database = configuration.get('native_blast_database')
    if database:
        from .native_blast_database_tool_info import native_blast_database_tool_contracts
        entries.extend(native_blast_database_tool_contracts(database['bindings'],
            resource_kind=kind, resource_id=resource_id))
    if configuration.get('native_hmmer'):
        from .native_hmmer_tool_info import native_hmmer_tool_contracts
        entries.extend(native_hmmer_tool_contracts(configuration['native_hmmer'],
            resource_kind=kind, resource_id=resource_id))
    if configuration.get('native_blast_masking'):
        from .native_blast_masking_tool_info import native_blast_masking_tool_contracts
        entries.extend(native_blast_masking_tool_contracts(configuration['native_blast_masking'],
            resource_kind=kind, resource_id=resource_id))
    if configuration.get('native_blast_utility'):
        from .native_blast_utility_tool_info import native_blast_utility_tool_contracts
        entries.extend(native_blast_utility_tool_contracts(configuration['native_blast_utility'],
            resource_kind=kind, resource_id=resource_id))
    if configuration.get('native_blast'):
        from .native_blast_tool_info import native_blast_tool_contracts
        entries.extend(native_blast_tool_contracts(configuration['native_blast'],
            resource_kind=kind, resource_id=resource_id))
    return entries


def preparation_operation_contracts(configuration, kind, resource_id):
    preparation = configuration.get('native_hmmer_preparation')
    if not preparation:
        return []
    from .native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
    return native_hmmer_preparation_tool_contracts(
        preparation, resource_kind=kind, resource_id=resource_id)


def homology_api_contracts(api_execution, resource_id, kind, service):
    if (service is None or service.service != 'bvbrc_appservice'
            or ('bvbrc_homology', '1') not in service.scientific_adapters):
        return []
    from .bvbrc_homology_tool_info import homology_tool_contracts
    return homology_tool_contracts(resource_id=resource_id,
        assignment_schema=api_execution.assignment_schema(resource_id))


def result_selector_conditions():
    from .sequence_masking_result_views import NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA
    from .blast_utility_result_views import NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA
    return [
        {'if': {'required': ['version'], 'properties': {'version': {
            'const': 'native_blast_masking_result_selector_v1'}}},
         'then': deepcopy(NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA)},
        {'if': {'required': ['version'], 'properties': {'version': {
            'enum': ['native_blast_utility_result_selector_v1',
                     'native_blast_utility_result_selector_v2']}}},
         'then': deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)},
    ]


def launch_request_schema(request_schema, resource_id, service):
    if service != 'ncbi_blast':
        return request_schema
    from .a107_blast_execution import BLAST_GRADED_REQUEST_SCHEMA
    return {'anyOf': [request_schema,
        {**deepcopy(BLAST_GRADED_REQUEST_SCHEMA), 'properties': {
            **deepcopy(BLAST_GRADED_REQUEST_SCHEMA['properties']),
            'resource_id': {'const': resource_id}}}]}
