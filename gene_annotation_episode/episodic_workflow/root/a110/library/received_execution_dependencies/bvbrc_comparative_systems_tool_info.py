from copy import deepcopy

def validate_comparative_request(request):
    """Check actual selected API operands without rewriting any native value."""
    parameters = request['parameters']
    for key in ('genome_ids', 'genome_groups'):
        values = parameters.get(key)
        if type(values) is not list or any((type(value) is not str or not value.strip() or value != value.strip() or ('\x00' in value) for value in values)):
            raise ValueError('comparative_systems_original_' + key + '_required')
    if not (parameters['genome_ids'] or parameters['genome_groups']):
        raise ValueError('comparative_systems_original_population_required')
    for key in ('output_path', 'output_file'):
        value = parameters.get(key)
        if type(value) is not str or not value.strip() or '\x00' in value:
            raise ValueError('comparative_systems_explicit_' + key + '_required')
    return deepcopy(request)
