"""One finite retained-data ATAC operation with exhaustive stream finalization.

Native byte acquisition is an earlier host operation. Saved calculations read
only the supplied sheet and numerical tables. No BAM, service or MACS2 call is
made by this worker. Emitted prefixes survive failure without a fabricated EOF.
"""
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

from .atac_differential_result_contracts import (
    PLAN_VERSION, RESULT_VERSION, SHEET_FORMAT, TABLE_FORMAT, ROLES, CATEGORIES,
    canonical, digest, require, validate_atac_result_record,
)
from .atac_differential_contracts import BEDGRAPH_COLUMNS, AtacTableReadError, issue
from .atac_differential_inputs import (
    iter_atac_bedgraph_records, iter_atac_track_table_rows, parse_atac_bedgraph,
    parse_macs2_peaks_xls, parse_macs2_narrowpeak, parse_macs2_summits_bed, parse_macs2_bdgdiff_bed,
)
from .atac_differential_sheet import build_atac_differential_sheet, select_atac_depth_counts
from .atac_reference_observations import parse_atac_bam_reference
from .atac_differential_calculation_inputs import prepare_atac_calculation_inputs
from .atac_differential_calculations import iter_atac_track_segments, iter_atac_interval_components, iter_atac_differential_regions
from .atac_differential_result_views import project_atac_result, native_counts
from .native_atac_differential_contracts import (
    failure, unique_failures, path_value, producer_ref, validate_atac_run_plan,
    validate_atac_native_bundle, validate_atac_command_seal,
)
from .native_atac_differential_driver import (
    _regular, _directory, _writing, _immutable, _read_control, file_identity, confined_file, decode_json,
)


FIXED_OUTPUTS = (('sheet', 'sheet.json', SHEET_FORMAT),
    ('calculations', 'calculations.json', 'atac_differential_calculations_v1'),
    ('projection', 'projection.json', 'atac_differential_projection_v1'),
    ('diagnostics', 'diagnostics.json', 'atac_differential_diagnostics_v1'))
DERIVED_FORMATS = {'partitions': 'atac_interval_partitions_jsonl_v1', 'components': 'atac_interval_components_jsonl_v1',
                   'regions': 'atac_differential_regions_jsonl_v1'}


def track_table_identity(table):
    return dict(artifact_ref=table['artifact_ref'], sha256=table['sha256'], size_bytes=table['byte_count'], format=table['format'])


def worker_output_specs(plan):
    """Every selected occurrence, including absent raw/derived output roles."""
    specs = [dict(role=role, table_key=None, relative_path=name, format=fmt) for role, name, fmt in FIXED_OUTPUTS]
    if plan['mode'] == 'native_result':
        keys = dict(zip(ROLES, ROLES))
    else:
        # A saved sheet can use different logical track keys. The local bundle
        # order is comparison-role order; absent/inline tracks have no raw file.
        keys = {str(i): row['track_key'] for i, row in enumerate(plan['sheet_bundle']['tables'])}
    specs.extend(dict(role='track_table', table_key=key, relative_path='tracks/' + role + '.jsonl', format=TABLE_FORMAT)
                 for role, key in keys.items())
    specs.extend(dict(role=role, table_key=role, relative_path=role + '.jsonl', format=fmt) for role, fmt in DERIVED_FORMATS.items())
    return specs


def validate_atac_result_worker_plan(value):
    value = validate_atac_result_record('WorkerPlan', value)
    selector = validate_atac_result_record('ResultSelector', value['selector'])
    directory = path_value(value['directory'], absolute=True)
    require(selector['mode'] == value['mode'], 'atac_worker_mode_mismatch')
    if value['mode'] == 'native_result':
        original = validate_atac_run_plan(value['original_plan'])
        from .native_atac_differential_capture import validate_atac_native_capture
        validate_atac_native_capture(dict(version='atac_native_capture_v1', **{key: value[key] for key in (
            'bundle', 'files', 'source_action_receipt_ref', 'writer_closure_receipt_ref', 'driver_state', 'failures')}), original_plan=original)
        request = original['requested_job']['native_atac_differential']['request']
        require(request['comparison_key'] == selector['comparison_key'], 'atac_result_comparison_conflict')
        require([r['specification'] for r in value['files']] == original['outputs'], 'atac_worker_manifest_mismatch')
        retained = ([value['bundle']] if value['bundle'] else []) + [r['retained'] for r in value['files'] if r['retained']]
        for row in value['files']:
            spec, declared, actual = row['specification'], row['declared'], row['retained']
            if declared is not None:
                require(all(declared[k] == spec[k] for k in ('relative_path', 'format')), 'atac_worker_manifest_mismatch')
            if actual is not None:
                require(actual['file']['format'] == spec['format'], 'atac_worker_manifest_mismatch')
            if row['outcome'] == 'verified':
                require(declared is not None and declared['state'] == 'present' and actual is not None
                    and all(declared[k] == actual['file'][k] for k in ('sha256', 'size_bytes', 'format')), 'atac_worker_capture_mismatch')
            elif row['outcome'] == 'declared_absent':
                require(declared is not None and declared['state'] == 'absent' and actual is None, 'atac_worker_capture_mismatch')
    else:
        saved = value['sheet_bundle']
        public = dict(sheet=saved['sheet']['file'], tables=[dict(track_key=r['track_key'], file=r['file']) for r in saved['tables']])
        require(selector['saved_sheet_bundle'] == public, 'atac_worker_saved_bundle_mismatch')
        validate_atac_result_record('SavedSheetBundle', public)
        retained = [saved['sheet'], *saved['tables']]
    paths = {}
    for record in retained:
        validate_atac_result_record('NativeFileIdentity', record['file'])
        path = path_value(record['path'], absolute=True)
        require(path != directory and directory not in path.parents and path not in directory.parents, 'atac_worker_input_output_overlap')
        content = {k: record['file'][k] for k in ('artifact_ref', 'sha256', 'size_bytes')}
        require(path not in paths or paths[path] == content, 'atac_worker_path_identity_conflict')
        paths[path] = content
    return value


def validate_atac_result_worker_result(value):
    value = validate_atac_result_record('WorkerResult', value)
    validate_atac_result_record('Parameters', value['parameters'])
    require(value['parameters']['maximum_gap_bp'] < value['parameters']['minimum_length_bp'], 'atac_worker_parameters_mismatch')
    for output, expected in zip(value['outputs'][:4], FIXED_OUTPUTS):
        role, name, fmt = expected
        require(output['role'] == role and output['table_key'] is None
            and output['declaration']['relative_path'] == name and output['declaration']['format'] == fmt, 'atac_worker_outputs_mismatch')
    require(len(value['outputs']) >= 7, 'atac_worker_outputs_mismatch')
    require([r['role'] for r in value['outputs'][-3:]] == list(DERIVED_FORMATS), 'atac_worker_outputs_mismatch')
    for row in value['outputs'][-3:]:
        key = row['role']
        require(row['table_key'] == key and row['declaration']['relative_path'] == key + '.jsonl'
            and row['declaration']['format'] == DERIVED_FORMATS[key], 'atac_worker_outputs_mismatch')
    raw = value['outputs'][4:-3]
    require(all(r['role'] == 'track_table' and r['table_key'] is not None and r['declaration']['format'] == TABLE_FORMAT for r in raw), 'atac_worker_outputs_mismatch')
    require(len({r['table_key'] for r in raw}) == len(raw), 'atac_worker_outputs_mismatch')
    paths = []
    for row in value['outputs']:
        declaration = row['declaration']
        paths.append(str(path_value(declaration['relative_path'], absolute=False)))
        require((declaration['sha256'] is not None and declaration['size_bytes'] is not None) == (declaration['state'] == 'present'), 'atac_worker_declaration_mismatch')
    require(len(set(paths)) == len(paths) and value['outputs'][3]['declaration']['state'] == 'present', 'atac_worker_outputs_mismatch')
    return value


class _Unavailable(Exception):
    def __init__(self, problem):
        self.problem = problem
        super().__init__(problem['code'])


def _read_json(retained, *, kind, field_path):
    try:
        with _regular(retained['path']) as stream:
            raw = stream.read()
    except (OSError, ValueError) as error:
        raise _Unavailable(failure('saved_attachment_unavailable', 'capture', artifact_ref=retained['file']['artifact_ref'],
            field_path=field_path, requirement='complete_saved_bundle')) from error
    if len(raw) != retained['file']['size_bytes'] or hashlib.sha256(raw).hexdigest() != retained['file']['sha256']:
        raise _Unavailable(failure('artifact_digest_mismatch', 'capture', artifact_ref=retained['file']['artifact_ref'],
            field_path=field_path, requirement='matching_file_identity'))
    try:
        parsed = decode_json(raw)
        if kind is not None:
            parsed = validate_atac_result_record(kind, parsed)
    except ValueError as error:
        raise _Unavailable(failure('original_attempt_mismatch', 'parse', artifact_ref=retained['file']['artifact_ref'],
            field_path=field_path, requirement='matching_file_identity')) from error
    return parsed, raw


def _chunks(path):
    with _regular(path) as stream:
        while True:
            raw = stream.read(65536)
            if not raw:
                return
            yield raw


def _table_file(path, fmt):
    identity = file_identity(path)
    return dict(artifact_ref='artifact_' + identity['sha256'], format=fmt, **identity)


def _track_parser(row, *, binding, artifact, directory, failures):
    if row['retained'] is None:
        return parse_atac_bedgraph(None, artifact=artifact, binding=binding)
    path = confined_file(directory, 'tracks/' + binding['track_key'] + '.jsonl')
    arrays = dict(headers=[], invalid_records=[], issues=[], overlap_groups=[], ordered_row_index=None)
    summary, count = None, 0
    with _writing(path) as output:
        try:
            for event in iter_atac_bedgraph_records(_chunks(row['retained']['path']), artifact=artifact, binding=binding):
                kind = event['kind']
                if kind == 'row':
                    output.write(canonical(event['row']) + b'\n')
                    count += 1
                elif kind == 'summary':
                    summary = event['summary']
                else:
                    field, item = {'header': ('headers', 'header'), 'invalid': ('invalid_records', 'record'), 'issue': ('issues', 'issue')}[kind]
                    arrays[field].append(event[item])
        except AtacTableReadError as error:
            summary = error.partial_summary
            arrays['issues'].extend(summary['issues'])
            arrays['issues'].append(error.issue)
            failures.append(_stream_failure(error, binding['track_key']))
    require(summary is not None, 'atac_track_summary_unavailable')
    identity = _table_file(path, TABLE_FORMAT)
    summary.update(arrays, version='atac_bedgraph_parsed_v1', rows=dict(storage='retained_table',
        artifact_ref=identity['artifact_ref'], format=TABLE_FORMAT, columns=list(BEDGRAPH_COLUMNS), row_count=count,
        sha256=identity['sha256'], byte_count=identity['size_bytes'], order='native_file_order', source_artifact_ref=artifact['artifact_ref']))
    return summary


def _native_sheet(plan, directory, failures):
    original = plan['original_plan']
    request = original['requested_job']['native_atac_differential']['request']
    files = {r['specification']['file_key']: r for r in plan['files']}
    seals, bundle = {}, None
    if plan['bundle'] is not None:
        try:
            value, _ = _read_json(plan['bundle'], kind=None, field_path='/bundle')
            bundle = validate_atac_native_bundle(value, plan=original)
            seals = {row['step_key']: row for row in bundle['steps']}
            failures.extend(bundle['failures'])
        except _Unavailable as error:
            failures.append(error.problem)
        except ValueError:
            failures.append(failure('original_attempt_mismatch', 'capture', file_key='bundle'))
    for key in ('callpeak1', 'callpeak2', 'bdgdiff'):
        row = files[key + '.seal']
        if key not in seals and row['retained'] is not None:
            try:
                value, _ = _read_json(row['retained'], kind=None, field_path='/files/' + key + '.seal')
                seals[key] = validate_atac_command_seal(value, plan=original, step_key=key)
            except _Unavailable as error:
                failures.append(error.problem)
            except ValueError:
                failures.append(failure('original_attempt_mismatch', 'capture', step_key=key, file_key=key + '.seal'))
    for seal in seals.values():
        failures.extend(seal['failures'])
        for declared in seal['outputs']:
            require(files[declared['specification']['file_key']]['declared'] == declared['declaration'], 'atac_worker_seal_capture_mismatch')
    if bundle is not None:
        for declared in bundle['outputs']:
            require(files[declared['specification']['file_key']]['declared'] == declared['declaration'], 'atac_worker_bundle_capture_mismatch')
    def source_ref(key):
        row = files[key]
        return row['retained']['file']['artifact_ref'] if row['retained'] is not None else None
    samples = {row['sample_id']: row for row in request['samples']}
    def artifact(key, producer, origin):
        row = files[key]
        retained, declared = row['retained'], row['declared']
        # Preserve the original declaration on mismatch, never replace its hash
        # with the observed identity merely to make parser verification pass.
        expected = declared if declared is not None and declared['state'] == 'present' else retained['file'] if retained else None
        return dict(artifact_ref=source_ref(key), format=row['specification']['format'],
            expected_sha256=expected['sha256'] if expected else None, expected_size_bytes=expected['size_bytes'] if expected else None,
            supplied_extent=row['supplied_extent'], producer_run_ref=producer, producer_outcome=row['producer_outcome'],
            writer_closed=True, producer_name='MACS2' if not key.startswith('header') else 'BAM_original_header_reader',
            producer_version='2.2.9.1' if not key.startswith('header') else None, producer_source_ref=None, origin=origin)
    bindings, tracks, xls, narrow, summits, headers = [], [], [], [], [], []
    for i, selected in enumerate(request['inputs'], 1):
        key = 'callpeak' + str(i)
        seal = seals.get(key)
        origin = samples[selected['sample_id']]['origin']
        binding = dict(run_key=key, condition_id=selected['condition_id'], sample_ids=[selected['sample_id']], reference_id=selected['reference_id'],
            treatment_input_refs=[selected['file']['artifact_ref']], supplied_control_sample_ids=[], supplied_control_input_refs=[],
            selected_format='BAM', paired_end=False, selected_argv=seal['argv'] if seal else [],
            selected_parameters={**request['callpeak'], 'effective_genome_size_bp': None, 'pvalue_cutoff': None,
                                 'small_local_window_bp': None, 'large_local_window_bp': None},
            artifact_roles={role: source_ref(key + '.' + suffix) for role, suffix in
                (('peaks_xls', 'peaks_xls'), ('narrowpeak', 'narrowpeak'), ('summits', 'summits'), ('signal_track', 'signal'), ('background_track', 'background'))},
            producer_ref=producer_ref(original, key))
        bindings.append(binding)
        for suffix, parser, target in (('peaks_xls', parse_macs2_peaks_xls, xls), ('narrowpeak', parse_macs2_narrowpeak, narrow),
                                       ('summits', parse_macs2_summits_bed, summits)):
            row = files[key + '.' + suffix]
            art = artifact(key + '.' + suffix, binding['producer_ref'], origin)
            with ExitStack() as stack:
                try:
                    stream = stack.enter_context(_regular(row['retained']['path'])) if row['retained'] else None
                except (OSError, ValueError):
                    stream = None
                    failures.append(failure('native_output_unavailable', 'parse', step_key=key, file_key=key + '.' + suffix))
                target.append(parser(stream, artifact=art, callpeak=binding))
        for suffix, role in (('signal', 'signal'), ('background', 'model_background')):
            file_key = key + '.' + suffix
            art = artifact(file_key, binding['producer_ref'], origin)
            track_binding = dict(track_key=suffix + str(i), condition_id=selected['condition_id'], sample_ids=[selected['sample_id']],
                role=role, callpeak_run_key=key, reference_id=selected['reference_id'],
                value_unit='extended_tag_pileup' if suffix == 'signal' else 'model_expected_extended_tag_pileup', normalization='raw_pileup',
                background_origin='unknown' if suffix == 'signal' else 'self_model', source_artifact_ref=art['artifact_ref'])
            tracks.append(_track_parser(files[file_key], binding=track_binding, artifact=art, directory=directory, failures=failures))
        header_key = 'header' + str(i)
        # Name the actual recorded inspection separately from callpeak. The
        # authenticated bundle binds its input/run/ordinal and byte identity;
        # no inspection record means no asserted inspection producer.
        inspection = next((row for row in bundle['input_inspections']
            if row['input_key'] == selected['input_key'] and row['callpeak_run_key'] == key
            and row['input_ordinal'] == 0 and row['input_file'] == selected['file']), None) if bundle else None
        header_producer = 'atac_header_inspection:' + digest([original['identity'], inspection]) if inspection else None
        art = artifact(header_key, header_producer, origin)
        if inspection:
            art['producer_source_ref'] = plan['bundle']['file']['artifact_ref']
        with ExitStack() as stack:
            try:
                stream = stack.enter_context(_regular(files[header_key]['retained']['path'])) if files[header_key]['retained'] else None
            except (OSError, ValueError):
                stream = None
                failures.append(failure('native_output_unavailable', 'reference', file_key=header_key, requirement='actual_bam_header'))
            headers.append(parse_atac_bam_reference(stream, artifact=art, callpeak_run_key=key, input_ordinal=0,
                input_artifact_ref=selected['file']['artifact_ref']))
    selected_argv = seals['bdgdiff']['argv'] if 'bdgdiff' in seals else []
    def argument(flag):
        return selected_argv[selected_argv.index(flag) + 1] if flag in selected_argv else None
    comparison = dict(comparison_key=request['comparison_key'], condition1_id=request['conditions'][0]['condition_id'],
        condition2_id=request['conditions'][1]['condition_id'], reference_id=request['reference']['reference_id'], track_keys=dict(zip(ROLES, ROLES)),
        selected_argv=selected_argv, selected_parameters={**request['bdgdiff'], 'depth1_lexeme': argument('--d1'), 'depth2_lexeme': argument('--d2'),
            'depth_unit': 'million_tags', 'native_pseudocount': 0.01},
        artifact_roles={category: source_ref('bdgdiff.' + category) for category in CATEGORIES}, producer_ref=producer_ref(original, 'bdgdiff'))
    differential = []
    for category in CATEGORIES:
        row = files['bdgdiff.' + category]
        art = artifact('bdgdiff.' + category, comparison['producer_ref'], 'unknown')
        with ExitStack() as stack:
            try:
                stream = stack.enter_context(_regular(row['retained']['path'])) if row['retained'] else None
            except (OSError, ValueError):
                stream = None
                failures.append(failure('native_output_unavailable', 'parse', file_key='bdgdiff.' + category))
            differential.append(parse_macs2_bdgdiff_bed(stream, artifact=art, comparison=comparison, category=category))
    depths = select_atac_depth_counts(xls, conditions=tuple(c['condition_id'] for c in request['conditions']), callpeak_bindings=bindings)
    return build_atac_differential_sheet(reference=request['reference'], samples=request['samples'], conditions=request['conditions'],
        callpeak_bindings=bindings, comparison=comparison, tracks=tracks, peaks_xls=xls, narrowpeaks=narrow, summits=summits,
        native_differential=differential, depth_selection=depths, bam_references=headers)


def _stream_failure(error, key):
    source = error.issue if isinstance(error, AtacTableReadError) else None
    return failure('calculation_stream_failed', 'calculation', binding_key=key,
        artifact_ref=source['artifact_ref'] if source else None, locator=source['locations'][0] if source and source['locations'] else None,
        field_path='/tracks/' + key, requirement='ordered_track_rows')


def _saved_stream_failures(error, key, file):
    """Keep attachment custody failure distinct from the interrupted calculation."""
    code = error.issue['code'] if isinstance(error, AtacTableReadError) else None
    if code == 'identity_mismatch':
        return [failure('artifact_digest_mismatch', 'capture', binding_key=key,
            artifact_ref=file['artifact_ref'], field_path='/sheet_bundle/tables/' + key, requirement='matching_file_identity')]
    if code == 'stream_read_failed' or isinstance(error, OSError):
        return [failure('saved_attachment_unavailable', 'capture', binding_key=key,
            artifact_ref=file['artifact_ref'], field_path='/sheet_bundle/tables/' + key, requirement='complete_saved_bundle')]
    return []


class _Tracked:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.exhausted = False
        self.failed = False
    def __iter__(self):
        return self
    def __next__(self):
        try:
            return next(self.rows)
        except StopIteration:
            if not self.failed:
                self.exhausted = True
            raise
        except (OSError, ValueError, TypeError):
            self.failed = True
            raise


def _calculate_sheet(sheet, *, selector, streams, directory, failures):
    """Persist iterator outputs; on failure drain, but never resume calculation."""
    bridge = prepare_atac_calculation_inputs(sheet, intervals=selector['intervals'], ordered_track_rows=streams)
    parameters = selector['parameters']
    ports = {}
    for role, port in bridge['tracks'].items():
        ports[role] = _Tracked(port['rows'])
        port['rows'] = ports[role]
    counts = dict(partitions=0, components=0, regions=0)
    coverage = dict(all_four_observed_bp=0, unavailable_or_invalid_bp=0, extent='complete')
    categories = {c: dict(category=c, count=0, qualifying_bp=0, span_bp=0, extent='complete') for c in CATEGORIES}
    outputs, error_seen = {}, False
    def write_through(rows, output, key):
        for row in rows:
            output.write(canonical(row) + b'\n')
            counts[key] += 1
            if key == 'partitions':
                field = 'all_four_observed_bp' if all(v == 'observed' for v in row['states'].values()) else 'unavailable_or_invalid_bp'
                coverage[field] += row['end'] - row['start']
            elif key == 'regions':
                summary = categories[row['category']]
                summary['count'] += 1
                summary['qualifying_bp'] += row['qualifying_bp']
                summary['span_bp'] += row['span_bp']
                if row['source_extent'] == 'partial':
                    summary['extent'] = 'partial'
            yield row
    with ExitStack() as stack:
        for key in DERIVED_FORMATS:
            if key != 'partitions' and bridge['depth_unit'] is None:
                continue
            outputs[key] = stack.enter_context(_writing(confined_file(directory, key + '.jsonl')))
        try:
            partitions = write_through(iter_atac_track_segments(bridge['tracks'], intervals=bridge['intervals']), outputs['partitions'], 'partitions')
            if bridge['depth_unit'] is None:
                failures.append(failure('calculation_input_unavailable', 'calculation', field_path='/depth_unit', requirement='matching_count_population'))
                for _ in partitions:
                    pass
            else:
                components = write_through(iter_atac_interval_components(partitions, depth1=bridge['depth1'], depth2=bridge['depth2'],
                    depth_unit=bridge['depth_unit'], pseudocount=parameters['pseudocount']), outputs['components'], 'components')
                regions = iter_atac_differential_regions(components, cutoff=parameters['cutoff_log10_lr'],
                    min_length_bp=parameters['minimum_length_bp'], max_gap_bp=parameters['maximum_gap_bp'])
                for _ in write_through(regions, outputs['regions'], 'regions'):
                    pass
        except (AtacTableReadError, OSError, ValueError, TypeError) as error:
            error_seen = True
            failed_keys = [sheet['comparison']['track_keys'][role] for role, rows in ports.items() if rows.failed]
            failures.append(_stream_failure(error, failed_keys[0] if len(failed_keys) == 1 else sheet['comparison']['comparison_key']))
            if isinstance(error, AtacTableReadError) and error.issue not in bridge['issues']:
                bridge['issues'].append(error.issue)
        finally:
            # Every other supplied port is drained independently. One failure
            # must not prevent a second source's final digest/order check.
            for role, rows in ports.items():
                try:
                    for _ in rows:
                        pass
                except (AtacTableReadError, OSError, ValueError, TypeError) as error:
                    error_seen = True
                    failures.append(_stream_failure(error, sheet['comparison']['track_keys'][role]))
                    if isinstance(error, AtacTableReadError) and error.issue not in bridge['issues']:
                        bridge['issues'].append(error.issue)
            # A projected ordering exception can close its wrapper while the
            # underlying supplied table still has unchecked bytes/rows.
            for key, rows in streams.items():
                try:
                    for _ in rows:
                        pass
                except (AtacTableReadError, OSError, ValueError, TypeError) as error:
                    error_seen = True
                    failures.append(_stream_failure(error, key))
                    if isinstance(error, AtacTableReadError) and error.issue not in bridge['issues']:
                        bridge['issues'].append(error.issue)
    failed = error_seen or any(not row.exhausted or row.failed for row in ports.values())
    if failed:
        coverage['extent'] = 'partial'
    if bridge['eligibility']['population'] == 'unavailable':
        coverage.update(all_four_observed_bp=None, unavailable_or_invalid_bp=None, extent='unavailable')
        failures.append(failure('calculation_input_unavailable', 'reference', field_path='/intervals', requirement='matching_reference_dictionary'))
    table_extent = 'partial' if failed or bridge['eligibility']['population'] == 'unavailable' else 'complete'
    tables = []
    for key in outputs:
        sources = [sheet['comparison']['track_keys'][role] for role in ROLES] if key == 'partitions' else ['partitions'] if key == 'components' else ['components']
        tables.append(dict(table_key=key, role=key, file=_table_file(directory / (key + '.jsonl'), DERIVED_FORMATS[key]),
            row_count=counts[key], extent=table_extent, source_table_keys=sources))
    for row in categories.values():
        if bridge['depth_unit'] is None or bridge['eligibility']['population'] == 'unavailable':
            row.update(count=None, qualifying_bp=None, span_bp=None, extent='unavailable')
        elif failed:
            row['extent'] = 'partial'
    peaks, native_regions = native_counts(sheet)
    depths = {key: bridge[key] for key in ('depth1', 'depth2', 'depth_unit')}
    summary = dict(depth_selection=deepcopy(sheet['depth_selection']), depth_operands=depths,
        selected_population_bp=sum(r['end'] - r['start'] for r in selector['intervals']), partition_coverage=coverage,
        native_peak_counts=peaks, native_region_counts=native_regions, derived_region_counts=list(categories.values()),
        **{k: sheet[k] for k in ('reference_relation', 'normalization_compatibility', 'coverage_completeness')}, uncertainty=dict(kind='not_estimated', value=None))
    return validate_atac_result_record('Calculations', dict(version='atac_differential_calculations_v1',
        comparison_key=sheet['comparison']['comparison_key'], reference_id=sheet['reference']['reference_id'],
        condition_ids=[sheet['comparison']['condition1_id'], sheet['comparison']['condition2_id']], selected_intervals=selector['intervals'],
        parameters=parameters, depth_operands=depths, eligibility=bridge['eligibility'], issues=bridge['issues'], tables=tables, summary=summary,
        stream_states=[dict(track_key=sheet['comparison']['track_keys'][r], extent=bridge['tracks'][r]['extent'],
            exhausted=rows.exhausted and not rows.failed and (sheet['comparison']['track_keys'][r] not in streams
                or streams[sheet['comparison']['track_keys'][r]].exhausted and not streams[sheet['comparison']['track_keys'][r]].failed))
            for r, rows in ports.items()], failures=unique_failures(failures), uncertainty=dict(kind='not_estimated', value=None)))


def _jsonl(path):
    with _regular(path) as stream:
        for raw in stream:
            yield decode_json(raw)


def run_atac_result_worker(plan):
    plan = validate_atac_result_worker_plan(plan)
    directory = _directory(plan['directory'])
    directory.mkdir(parents=True, exist_ok=True)
    require(not (directory / 'worker-result.json').exists(), 'atac_worker_already_sealed')
    failures, values, streams, raw_paths = deepcopy(plan.get('failures', [])), {}, {}, {}
    diagnostics = dict(version='atac_differential_diagnostics_v1', mode=plan['mode'], issues=[], failures=[], stream_states=[])
    with ExitStack() as stack:
        try:
            if plan['mode'] == 'native_result':
                sheet = _native_sheet(plan, directory, failures)
                _immutable(directory / 'sheet.json', sheet)
                values['sheet'] = sheet
                for track in sheet['tracks']:
                    if isinstance(track['rows'], dict):
                        path = directory / 'tracks' / (track['binding_key'] + '.jsonl')
                        raw_paths[track['binding_key']] = path
                        streams[track['binding_key']] = _Tracked(iter_atac_track_table_rows(_chunks(path), table=track['rows']))
            else:
                saved = plan['sheet_bundle']
                sheet, raw = _read_json(saved['sheet'], kind='NativeSheet', field_path='/sheet_bundle/sheet')
                values['sheet'] = sheet
                with _writing(directory / 'sheet.json') as out:
                    out.write(raw)
                expected = [dict(track_key=t['binding_key'], file=track_table_identity(t['rows'])) for t in sheet['tracks'] if isinstance(t['rows'], dict)]
                supplied = [dict(track_key=r['track_key'], file=r['file']) for r in saved['tables']]
                require(expected == supplied, 'atac_saved_table_association_mismatch')
                descriptors = {t['binding_key']: t['rows'] for t in sheet['tracks'] if isinstance(t['rows'], dict)}
                for i, retained in enumerate(saved['tables']):
                    key, path = retained['track_key'], directory / 'tracks' / (str(i) + '.jsonl')
                    output = stack.enter_context(_writing(path))
                    raw_paths[key] = path
                    def chunks(retained=retained, output=output):
                        for raw in _chunks(retained['path']):
                            output.write(raw)
                            yield raw
                    def rows(chunks=chunks, retained=retained, key=key):
                        try:
                            yield from iter_atac_track_table_rows(chunks(), table=descriptors[key])
                        except (AtacTableReadError, OSError, ValueError, TypeError) as error:
                            failures.extend(_saved_stream_failures(error, key, retained['file']))
                            raise
                    streams[key] = _Tracked(rows())
            calculation = _calculate_sheet(sheet, selector=plan['selector'], streams=streams, directory=directory, failures=failures)
            values['calculations'] = calculation
            diagnostics.update(issues=calculation['issues'], stream_states=calculation['stream_states'])
            tables = {r['table_key']: r for r in calculation['tables']}
            values['projection'] = project_atac_result(sheet, calculation, selector=plan['selector'],
                component_rows=_jsonl(directory / 'components.jsonl') if 'components' in tables else None,
                region_rows=_jsonl(directory / 'regions.jsonl') if 'regions' in tables else None)
        except _Unavailable as error:
            failures.append(error.problem)
        except (OSError, ValueError) as error:
            failures.append(failure('saved_attachment_unavailable' if plan['mode'] == 'saved_sheet_recalculation' else 'calculation_input_unavailable',
                'calculation', field_path='/calculations', requirement='complete_saved_bundle' if plan['mode'] == 'saved_sheet_recalculation' else 'requested_selected_field'))
    diagnostics['failures'] = unique_failures(failures)
    values['diagnostics'] = validate_atac_result_record('Diagnostics', diagnostics)
    for role, name, _ in FIXED_OUTPUTS:
        if role in values and role != 'sheet':
            _immutable(directory / name, values[role])
    outputs = []
    for spec in worker_output_specs(plan):
        path = confined_file(directory, spec['relative_path'])
        present = path.is_file()
        declaration = dict(relative_path=spec['relative_path'], format=spec['format'], state='present' if present else 'absent',
            **(file_identity(path) if present else dict(sha256=None, size_bytes=None)))
        outputs.append(dict(role=spec['role'], table_key=spec['table_key'], declaration=declaration))
    produced = all(k in values for k in ('sheet', 'calculations', 'projection'))
    partial_stream = 'calculations' in values and any(t['extent'] != 'complete' for t in values['calculations']['tables'])
    state = 'produced' if produced and not partial_stream else 'partial' if 'sheet' in values else 'unavailable'
    result = validate_atac_result_worker_result(dict(version=RESULT_VERSION, mode=plan['mode'], parameters=plan['selector']['parameters'],
        state=state, outputs=outputs, failures=diagnostics['failures']))
    _immutable(directory / 'worker-result.json', result)
    return result


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    require(len(arguments) == 1, 'atac_worker_plan_argument_required')
    run_atac_result_worker(_read_control(Path(arguments[0])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


__all__ = ['validate_atac_result_worker_plan', 'validate_atac_result_worker_result', 'run_atac_result_worker',
    'worker_output_specs', 'track_table_identity', 'main']
