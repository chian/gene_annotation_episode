"""Finite selected preparation/report production inside the existing driver.

This module retains the supplied and P/R-generated records. It neither chooses
work nor computes gate statistics or shared scientific scores.
"""
from copy import deepcopy

from . import fluorescence_event_contracts as core
from .fluorescence_execution_common import canonical, digest, same
from .native_fluorescence_contracts import (
    validate_fluorescence_prepared_batch, validate_fluorescence_report_batch,
)
from .native_fluorescence_storage import decode_json


def _matrix_source(job, request, index):
    """Resolve the explicitly selected FCS dataset, without a biological join."""
    params = request['recipe']['parameters']
    for item in job['inputs']:
        if (same(item['source']['file'], params['matrix_file'])
                and item['source']['dataset_position'] == params['dataset_position']
                and item['parser'] == 'fcs_encoded'):
            return deepcopy(item['source'])
    return dict(key=f'preparation-matrix-support:{index}', file=deepcopy(params['matrix_file']),
        dataset_position=params['dataset_position'], format_profile='fcs_flowio_1_4_0_encoded',
        extent='unavailable', native_event_count=None, metadata=[])


def produce_selected(plan, *, event_records, retained, report_raws, publish, failure, verify):
    """Execute only the listed requests, publishing each before the next."""
    job = plan['requested_job']['native_fluorescence']
    preparations, reports, failures, prepared_records = [], [], [], []
    if job['preparations']:
        from .fluorescence_preparation_contracts import SCALE_METHOD, assemble_prepared_parse
        from .fluorescence_event_preparation import prepare_fcs_scaling, prepare_spill_compensation
        from .fluorescence_preparation_readers import read_fcs_spill_matrix
    for index, request in enumerate(job['preparations']):
        selected = request['input']
        parents = event_records if selected['kind'] == 'event_input' else prepared_records
        parent_record = parents[selected['index']]
        parent, parent_file = parent_record if parent_record is not None else (None, None)
        row = dict(preparation_index=index, parent_batch_file=deepcopy(parent_file),
            parameters_file=None, prepared_file=None, batch_file=None, status='unavailable')
        preparations.append(row)
        prepared_records.append(None)
        role = f'prepared_batch:{index}'
        recipe_raw = retained.get(canonical(request['recipe_file']))
        if (recipe_raw is None or parent is None or parent['source']['extent'] == 'unavailable'
                or parent['source']['file'] is None):
            failures.append(failure('preparation_unavailable', 'input', index=index, role=role))
            continue
        try:
            recipe = decode_json(recipe_raw)
            valid_recipe = same(recipe, request['recipe'])
        except (ValueError, UnicodeError, RecursionError):
            valid_recipe = False
        if not valid_recipe:
            row['status'] = 'incompatible'
            failures.append(failure('preparation_incompatible', 'input', index=index, role=role))
            continue
        method = request['recipe']['method']
        original = (parent['source']['file'] if method == SCALE_METHOD
            else request['recipe']['parameters']['matrix_file'])
        raw = retained.get(canonical(original))
        if raw is None:
            failures.append(failure('preparation_unavailable', 'input', index=index, role=role))
            continue
        try:
            if method == SCALE_METHOD:
                outcome = prepare_fcs_scaling(raw, parent=parent, request=request)
            else:
                params = request['recipe']['parameters']
                matrix = read_fcs_spill_matrix(raw, source=_matrix_source(job, request, index),
                    locator={name: params[name] for name in ('dataset_position', 'keyword')}, channels=parent['channels'])
                outcome = prepare_spill_compensation(parent, matrix=matrix, request=request)
        except core.FluorescenceContractError:
            # An observed parent channel can contradict the prospective caller
            # binding. No outcome or resolved parameters were produced then.
            row['status'] = 'incompatible'
            failures.append(failure('preparation_incompatible', 'input', index=index, role=role))
            continue
        verify(job['software'])
        parameters_file = publish(f'preparation_parameters:{index}', outcome['parameters'])
        prepared_file = publish(f'prepared_data:{index}', outcome['data']) if outcome['data'] is not None else None
        parsed = assemble_prepared_parse(outcome, request=request, parent=parent,
            data_file=prepared_file, parameters_file=parameters_file)
        batch = validate_fluorescence_prepared_batch(dict(version='fluorescence_prepared_batch_v1',
            original_plan_sha256=digest(plan), preparation_index=index,
            preparation_request_sha256=core.digest(request), software_sha256=digest(job['software']),
            parent_batch_file=parent_file, recipe_file=request['recipe_file'], parameters_file=parameters_file,
            prepared_file=prepared_file, parse=parsed, status=outcome['status'],
            problems=outcome['parameters']['problems']), original_plan=plan,
            preparation_index=index, parent_batch_file=parent_file)
        batch_file = publish(role, batch)
        row.update(parameters_file=parameters_file, prepared_file=prepared_file, batch_file=batch_file,
            status=outcome['status'])
        prepared_records[index] = (parsed, batch_file)
        if outcome['status'] in ('unavailable', 'failed', 'incompatible'):
            failures.append(failure('preparation_' + outcome['status'], 'input', index=index, role=role))
    if job['report_inputs']:
        from .fluorescence_native_report_contracts import make_fluorescence_report_binding
        from .fluorescence_native_reports import parse_fluorescence_native_reports
    for index, request in enumerate(job['report_inputs']):
        raw = report_raws[index]
        row = dict(report_index=index, source_file=request['file'] if raw is not None else None,
            batch_file=None, extent='unavailable')
        reports.append(row)
        role = f'report_batch:{index}'
        if raw is None:
            failures.append(failure('report_batch_unavailable', 'input', index=index, role=role))
            continue
        association_raw = retained.get(canonical(request['association_file'])) if request['association_file'] is not None else None
        binding = make_fluorescence_report_binding(request, definitions=job['definitions'],
            event_inputs=job['inputs'], preparations=job['preparations'])
        try:
            parsed = parse_fluorescence_native_reports(raw, binding=binding, association_raw=association_raw)
            batch = validate_fluorescence_report_batch(dict(version='fluorescence_report_batch_v1',
                original_plan_sha256=digest(plan), report_index=index, report_input_sha256=digest(request),
                software_sha256=digest(job['software']), report_file=request['file'],
                association_file=request['association_file'] if association_raw is not None else None, parse=parsed),
                original_plan=plan, report_index=index)
        except core.FluorescenceContractError:
            failures.append(failure('report_batch_invalid', 'input', index=index, role=role))
            continue
        verify(job['software'])
        row.update(batch_file=publish(role, batch), extent=parsed['source']['extent'])
    return preparations, reports, failures
