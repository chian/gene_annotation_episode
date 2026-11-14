"""Explicit native/saved FBA result selection, without execution or calculation."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.flux_balance_result_contracts import validate_fba_projection_selector, validate_fba_saved_sheet_reference

def validate_flux_balance_result_selector(value: dict, *, job: dict | None=None) -> dict:
    """Validate explicit parameters and selected fields; grant no source access."""
    if type(value) is not dict or set(value) != {'version', 'mode', 'saved_sheet_file', 'calculation_parameters', 'projection'} or value['version'] != 'flux_balance_result_selector_v1' or (type(value['mode']) is not str) or (value['mode'] not in ('native_result', 'saved_sheet_recalculation')):
        raise ValueError('fba_result_selector_invalid:/selector')
    if value['mode'] == 'native_result':
        if value['saved_sheet_file'] is not None:
            raise ValueError('fba_result_selector_invalid:/selector/saved_sheet_file')
        saved = None
    else:
        saved = validate_fba_saved_sheet_reference(value['saved_sheet_file'])
    parameters = validate_flux_balance_record('FBACalculationParameters', value['calculation_parameters'])
    projection = validate_fba_projection_selector(value['projection'])
    if job is not None:
        if value['mode'] != 'native_result':
            raise ValueError('fba_result_selector_invalid:/job')
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_flux_balance_contracts import validate_flux_balance_requested_job
        validate_flux_balance_requested_job(job)
    return {'version': value['version'], 'mode': value['mode'], 'saved_sheet_file': deepcopy(saved), 'calculation_parameters': parameters, 'projection': projection}
