"""Engineering provider-wire views; no native measurement or model dispatch.

The native-format tokens below are explicit engineering examples. Post-result
own/received/frozen placements exercise rendering, not new runtime admissions.
The independently gated genuine Workflow owns native/custody verification.
"""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import scientific_process_prompt as prompt
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.macs2_peak_presentation import render_macs2_peak_result
from gene_annotation_episode.macs2_peak_request_binding import (
    ASSIGNMENT_VERSION, resource_assignment_schema, launch_assignment_schema,
)
from gene_annotation_episode.macs2_peak_result_contracts import (
    VERSION, macs2_peak_fact_sources, macs2_peak_result_schema, validate_macs2_peak_return,
)
from gene_annotation_episode import native_macs2_peak_execution as native
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.state import Store
from test_native_atac_differential_contracts import fake_software as atac_engineering_software


QUESTION = 'Which native narrow enrichment intervals are reported for the supplied treatment and matched control?'
PRIVATE_PATH = '/private-engineering-runtime/host-controls'
PRIVATE_SHA = 'e7' * 32
SOURCE = 'source_' + 'a' * 24


def _forbidden(*args, **kwargs):
    raise AssertionError('pure presentation attempted File/scientific/provider work')


@pytest.fixture(autouse=True)
def no_work(monkeypatch):
    monkeypatch.setattr(Store, 'get_artifact', _forbidden)
    for name in ('complete', '_rpc', '_session'):
        monkeypatch.setattr(_SessionConnection, name, _forbidden)
    for name in ('prepare_local_macs2_peak', 'run_macs2_peak'):
        monkeypatch.setattr(native, name, _forbidden)
    monkeypatch.setattr('gene_annotation_episode.macs2_peak_components.build_macs2_peak_components', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.macs2_peak_components.native_peak_counts', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.macs2_peak_components.project_native_peak_window', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)


def _software():
    software = atac_engineering_software()
    software['driver_runtime']['implementation_files'].append(dict(module=native.DRIVER_MODULE,
        sha256=digest(native.DRIVER_MODULE)))
    software['macs2_runtime']['files'].extend(dict(path=PRIVATE_PATH + '/library/' + str(index),
        sha256=PRIVATE_SHA, size_bytes=1) for index in range(945))
    assert len(software['macs2_runtime']['files']) == 950
    return software


def _job():
    reference = dict(reference_id='engineering-reference', assembly_accession_version=None,
        source_refs=[], contigs=[dict(chromosome='chrToy', length_bp=12010000,
            sequence_accession_version=None, sequence_sha256=None, source_refs=[])], aliases=[])
    files = [dict(artifact_ref='artifact_' + character * 64, sha256=character * 64,
        size_bytes=123, format='bed6') for character in ('1', '2')]
    request = dict(version=native.REQUEST_VERSION, operation=native.OPERATION, mode=native.MODE,
        run_key='chipseq', condition_id='chip', reference=reference,
        samples=[dict(sample_id=role, input_artifact_refs=[file['artifact_ref']],
            reference_id=reference['reference_id'], biospecimen_id=None, replicate_id=None,
            origin='synthetic_engineering_fixture') for role, file in zip(('treatment', 'control'), files)],
        inputs=[dict(input_key=role, role=role, sample_id=role, reference_id=reference['reference_id'], file=file)
            for role, file in zip(('treatment', 'control'), files)],
        callpeak=dict(genome_size_argument='12010000', qvalue_cutoff=0.05), output_prefix='chip')
    return dict(request=request, software=_software(), input_bindings=[dict(input_key=role, file=file,
        path=PRIVATE_PATH + '/' + role) for role, file in zip(('treatment', 'control'), files)])


def _compact():
    request = deepcopy(_job()['request'])
    for row in request['inputs']:
        row['file'] = {key: row['file'][key] for key in ('artifact_ref', 'format')}
    return dict(version=ASSIGNMENT_VERSION, resource_id='selected-local', resource_kind='local',
        binding_ordinal_0based=0, endpoint='usable_handoff', request=request,
        progress_requirements=[dict(key='handoff', credit=1, predicate=dict(kind='requested_job_handoff'))],
        completion_keys=['handoff'], constraints=deepcopy(native.POLICY))


def _packet():
    numbers = {name: dict(value=None, lexeme=None, state='missing', locations=[]) for name in (
        'effective_genome_size_bp', 'band_width_bp', 'model_fold_lower', 'model_fold_upper',
        'qvalue_cutoff', 'pvalue_cutoff', 'large_local_window_bp', 'tag_size_bp', 'fragment_size_bp',
        'treatment_total_tags', 'treatment_postfilter_tags', 'treatment_max_duplicates', 'treatment_redundant_rate',
        'control_total_tags', 'control_postfilter_tags', 'control_max_duplicates', 'control_redundant_rate',
        'treatment_total_fragments', 'treatment_postfilter_fragments', 'control_total_fragments',
        'control_postfilter_fragments', 'shift_bp', 'd_bp')}
    for name, value, lexeme in [('effective_genome_size_bp', 12000000, '1.20e+07'), ('d_bp', 199, '199'),
            ('treatment_postfilter_tags', 12010, '12010'), ('control_redundant_rate', 0.0, '0.00')]:
        numbers[name] = dict(value=value, lexeme=lexeme, state='present',
            locations=[dict(line_number=10, byte_start=100, byte_end=120)])
    metadata = dict(macs_version='2.2.9.1', command_line='callpeak -t ' + PRIVATE_PATH + '/treatment',
        name='chip', format='AUTO', treatment_paths=[PRIVATE_PATH + '/treatment'],
        control_paths=[PRIVATE_PATH + '/control'], control_presence='present', paired_end=False,
        broad=False, scaling_direction='larger_to_smaller', local_lambda='enabled', field_locations={})
    source = dict(artifact_ref='artifact_' + 'b' * 64, format='macs2_narrowpeak10',
        expected_sha256=PRIVATE_SHA, expected_size_bytes=100, supplied_extent='complete',
        producer_run_ref='private-native-tracking', producer_outcome='succeeded', writer_closed=True,
        producer_name='MACS2', producer_version='2.2.9.1', producer_source_ref='private-provider-tracking',
        origin='synthetic_engineering_fixture')
    locator = dict(line_number=1, byte_start=0, byte_end=80)
    common = dict(row_ordinal=0, locator=locator, chromosome='chrToy')
    xls = dict(**common, original_fields=['chrToy','2910','3190','281','3021','100','108.597','23.3077','104.594','chip_peak_1'],
        start1=2910, end1=3190, length_bp=281, abs_summit1=3021, pileup=100,
        minus_log10_pvalue=108.597, fold_enrichment=23.3077, minus_log10_qvalue=104.594, name='chip_peak_1')
    narrow = dict(**common, original_fields=['chrToy','2909','3190','chip_peak_1','1045','.','23.3077','108.597','104.594','111'],
        start0=2909, end0=3190, name='chip_peak_1', display_score=1045, strand='.', signal_value=23.3077,
        minus_log10_pvalue=108.597, minus_log10_qvalue=104.594, summit_offset0=111)
    summit = dict(**common, original_fields=['chrToy','3020','3021','chip_peak_1','104.594'],
        start0=3020, end0=3021, name='chip_peak_1', score=104.594)
    link = dict(callpeak_run_key='chipseq', name='chip_peak_1', xls_row_ordinals=[0],
        narrowpeak_row_ordinals=[0], summit_row_ordinals=[0], status='matched')
    rows = [dict(callpeak_run_key='chipseq', representation=representation, source={**deepcopy(source), 'format': {
            'xls':'macs2_peaks_xls_narrow','narrowpeak':'macs2_narrowpeak10','summit':'macs2_summits_bed5'}[representation]}, row=row,
        geometry=dict(row_ordinal=0, start0=2909, end0=3190, summit0=3020, span_bp=281, status='valid')
            if representation == 'xls' else None, peak_link=deepcopy(link))
        for representation, row in [('xls', xls), ('narrowpeak', narrow), ('summit', summit)]]
    return validate_macs2_peak_return(dict(version=VERSION, source_ref=SOURCE, status='complete',
        native_outcome='succeeded', run_key='chipseq', reference_id='engineering-reference',
        native_peak_counts=[dict(run_key='chipseq', representation=representation, count=1, extent='complete')
            for representation in ('xls', 'narrowpeak', 'summit')], reported_metadata=metadata,
        reported_numbers=numbers, peak_window=dict(row_window=dict(offset=0, limit=3), total_rows=3,
            row_extent='complete', rows=rows), issues=[], failures=[]))


def _connection():
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    return connection


def _science_state():
    binding = dict(operation=native.OPERATION, mode=native.MODE, software=_software())
    tool, = native.macs2_peak_tool_contracts([binding], resource_kind='local', resource_id='selected-local')
    return dict(goal=dict(objective=QUESTION), scope={}, scientific_process=dict(assignment={},
        evidence_axis=dict(instruction_status=prompt.INSTRUCTION_STATUS, name='Experimental molecular activity',
            investigation_instructions='Engineering literal axis instructions.'),
        thought_pattern=dict(name='Distinguish transformation from proxy readout', description='Engineering thought text.'),
        child_tool_info=[{key: tool[key] for key in ('name','resources','description','instructions')}]),
        tools=[tool], available_report_facts=macs2_peak_fact_sources(), last_local_outcome=None,
        child_reports=[], current_report_update={})


@pytest.mark.parametrize('placement', ['own','received','frozen'])
@pytest.mark.parametrize('transport', ['full','bootstrap','update','lookup'])
def test_engineered_native_packet_uses_actual_provider_wire_without_work(placement, transport):
    packet, base = _packet(), _science_state()
    outcome = dict(status='completed', record_refs=[SOURCE], changed_record_refs=[SOURCE], result=packet)
    state = deepcopy(base)
    if placement == 'own': state['last_local_outcome'] = outcome
    elif placement == 'received': state['child_reports'] = [dict(peaks=[packet])]
    else: state['current_report_update'] = dict(peaks=[packet])
    before = canonical(state)
    connection = _connection()
    if transport in ('update','lookup'):
        connection._presentation('engineering', 'REASONING', 'Unchanged instructions.', state_frame(base))
    supplied = state if transport == 'full' else state_frame(state) if transport == 'bootstrap' else (
        state_frame(state, base) if transport == 'update' else dict(version='decision_context_v1',
            kind='decision_lookup_result', decision_index=1, exchange_index=0, result=outcome))
    text, instructions = connection._presentation('engineering','REASONING','Unchanged instructions.',supplied)
    assert text.startswith('TASK\n') and 'STEERING' in text and instructions == 'Unchanged instructions.'
    assert QUESTION in text and 'Engineering literal axis instructions.' in text and 'Engineering thought text.' in text
    assert base['scientific_process']['child_tool_info'][0]['instructions'] in text
    assert text.count(SOURCE) == 1
    assert '| display_score | 1045 | native display score |' in text
    assert '| d_bp | 199 | "199" | present | bp |' in text
    assert '| control_redundant_rate | 0.0 | "0.00" | present | fraction |' in text
    assert '| start1 | 2910 | bp; one_based_inclusive |' in text
    assert '| start0 | 2909 | bp; zero_based_half_open |' in text
    assert '| pvalue_cutoff | null | null | missing | 1 |' in text
    assert '["chrToy","2909","3190","chip_peak_1","1045",".","23.3077","108.597","104.594","111"]' in text
    for private in (PRIVATE_PATH, PRIVATE_SHA, 'private-native-tracking','private-provider-tracking','artifact_'+'b'*64):
        assert private not in text
    assert canonical(state) == before


@pytest.mark.parametrize('role', ['launch','launch_local','results'])
def test_engineered_selected_execution_view_keeps_public_science_and_hides_only_compiled_fields(role):
    state = _science_state(); state.pop('scientific_process')
    job = _job()
    state['selected_execution_task'] = dict(version='selected_execution_task_v1', scientific_question=QUESTION,
        selected_tool_info=_science_state()['scientific_process']['child_tool_info'], constraints={}, selector=None,
        requests=[dict(resource_id='selected-local', resource_kind='local', endpoint='usable_handoff', constraints={},
            resource=dict(resource_id='selected-local', native_macs2_peak=[dict(operation=native.OPERATION,
                mode=native.MODE, software=job['software'])]), job=job)])
    state['tools'] = [dict(name='engineering-private-schema-view', description='Private retained schema projection',
        input_schema=native.macs2_peak_execution_schema('RequestedJob', bindings=[dict(operation=native.OPERATION,
            mode=native.MODE, software=job['software'])]))]
    before = canonical(state)
    text, _ = _connection()._presentation('engineering-' + role, 'REASONING', 'Same instructions.', state_frame(state))
    assert QUESTION in text and 'genome_size_argument' in text and '12010000' in text and 'qvalue_cutoff' in text
    assert 'binding_ordinal_0based' in text and 'chipseq' in text and 'engineering-reference' in text
    assert 'artifact_'+'1'*64 in text and 'bed6' in text
    assert 'Host-compiled native execution' in text
    assert PRIVATE_SHA not in text and PRIVATE_PATH not in text and '/fixture/' not in text
    assert canonical(state) == before


def test_actual_public_toolinfo_and_outer_launch_schema_are_complete_compiler_operands():
    compact = _compact()
    binding = dict(operation=native.OPERATION, mode=native.MODE, software=_software())
    tool, = native.macs2_peak_tool_contracts([binding], resource_kind='local', resource_id='selected-local')
    assert tool['input_schema'] == resource_assignment_schema('selected-local', bindings=[binding])
    Draft202012Validator(tool['input_schema']).validate(compact)
    launch = dict(version='macs2_peak_scientific_launch_v1', requests={'selected-local': compact}, constraints={})
    schema = launch_assignment_schema({'selected-local': dict(native_macs2_peak=[binding])})
    Draft202012Validator(schema).validate(launch)
    assert prompt._operation_schema_view(tool['input_schema']) == tool['input_schema']
    assert prompt._execution_schema_view(schema) == schema
    for name in ('resource_id','binding_ordinal_0based','endpoint','request','progress_requirements','completion_keys','constraints'):
        assert name in tool['input_schema']['properties']
    assert PRIVATE_SHA not in canonical(schema) and 'software' not in canonical(schema)


@pytest.mark.parametrize('state', ['missing','invalid','conflicting','not_measured'])
def test_reported_number_states_and_observed_empty_are_literal(state):
    packet = _packet()
    packet['reported_numbers']['d_bp'].update(value=None, lexeme='not-a-number' if state=='invalid' else None, state=state)
    packet['peak_window'].update(total_rows=0, rows=[])
    for row in packet['native_peak_counts']: row['count'] = 0
    text = render_macs2_peak_result(packet)
    assert '| d_bp | null | ' + ('"not-a-number"' if state=='invalid' else 'null') + ' | '+state+' | bp |' in text
    assert '| xls | 0 | native rows | complete |' in text and 'Selected native row 1' not in text


def test_top_failures_and_partial_unknown_counts_do_not_disappear_or_become_zero():
    packet = _packet(); packet.update(status='partial',native_outcome='failed')
    packet['native_peak_counts'][0].update(count=None,extent='unavailable')
    packet['failures'] = [dict(code='native_nonzero_exit',stage='execution',step_key=None,file_key='peaks_xls',
        binding_key='chipseq',artifact_ref='private-failure-ref',locator=None,field_path=None,
        requirement='original_native_outcome',partial_artifact_refs=['private-prefix-ref'])]
    text = render_macs2_peak_result(packet)
    assert '| xls | null | native rows | unavailable |' in text and 'native_nonzero_exit' in text
    assert 'private-failure-ref' not in text and 'private-prefix-ref' not in text


def test_scientific_strings_are_never_scrubbed_and_equal_packets_share_one_source():
    packet = _packet()
    packet['peak_window']['rows'][0]['row']['name'] = PRIVATE_PATH + PRIVATE_SHA
    text = prompt._values([packet,deepcopy(packet)])
    assert text.count(SOURCE)==1 and PRIVATE_PATH + PRIVATE_SHA in text
    other=deepcopy(packet); other['source_ref']='source_'+'f'*24
    assert prompt._values([packet,other]).count('Callable result Source')==2


def test_malformed_unknown_and_old_profiles_keep_prior_generic_behavior():
    malformed=_packet();malformed.pop('source_ref')
    for value in (malformed,dict(version='unknown',payload=_packet()),dict(native_atac_differential={'software':PRIVATE_SHA})):
        assert prompt._values(value)==prompt._table(('Field','Supplied value'),prompt._rows(value))
    schema=dict(type='object',properties={'native_atac_differential':{'const':PRIVATE_SHA}})
    assert prompt._execution_schema_view(schema)==schema


def test_units_cover_the_registered_reported_numbers_and_instruction_units_are_unchanged():
    from gene_annotation_episode.macs2_peak_presentation import _NUMBER_UNITS
    schema=macs2_peak_result_schema()
    assert set(_NUMBER_UNITS)==set(schema['$defs']['Macs2PeakReturn']['properties']['reported_numbers']['properties'])
    source=Path(prompt.__file__).read_text();tree=ast.parse(source)
    for name, expected in dict(_task='fdffd84c9f19fa8705f55b74153e35288d319c524344458dd3f1126ebaa8c0bc',
            _steering='286cc38ec22fe2a7f2c1bd3c05c0a3ddf5a332c4f127407b630ae3fb97c1f9f1').items():
        unit=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
        assert hashlib.sha256(ast.get_source_segment(source,unit).encode()).hexdigest()==expected


def _capture_outcome():
    """Literal acquisition controls, not a native producer or custody witness."""
    from gene_annotation_episode.local_file_capture_results import ORIGIN
    files = []
    for index, (fmt, availability, size, failure) in enumerate((
        ('macs2_peaks_xls_narrow', 'retained', 15, None),
        ('native_stderr', 'retained', 0, None),
        ('macs2_peak_command_seal_v1', 'unavailable', None, {'code': 'original_missing'}),
        ('macs2_model_r', 'not_acquired', None, None),
    )):
        files.append(dict(path=PRIVATE_PATH + '/captured-' + str(index), format=fmt,
            source_ref='source_' + str(index + 1) * 24 if availability == 'retained' else None,
            availability=availability, size_bytes=size, failure=failure))
    return dict(version='execution_file_source_outcome_v1', operation='execution.results.collect',
        job=dict(state='completed', returncode=0, failure_code=None), files=files,
        provenance=deepcopy(ORIGIN), failure=None)


def _capture_state():
    from gene_annotation_episode.local_file_capture_results import OUTCOMES_SCHEMA
    state = _science_state()
    state['available_report_facts']['execution_file_capture_outcomes'] = dict(type='array',
        meaning='Engineering declared original capture facts.', report_schema=deepcopy(OUTCOMES_SCHEMA))
    return state


@pytest.mark.parametrize('placement', ['own', 'child', 'frozen'])
@pytest.mark.parametrize('transport', ['full', 'bootstrap', 'update'])
def test_declared_macs2_capture_wire_keeps_acquisition_and_sources_without_host_paths(placement, transport):
    state, capture = _capture_state(), _capture_outcome()
    if placement == 'own':
        state['last_local_outcome'] = dict(status='completed', record_refs=[SOURCE], result=capture)
    elif placement == 'child':
        state['child_reports'] = [dict(outcomes=[capture])]
    else:
        state['current_report_update'] = dict(outcomes=[capture])
    before = canonical(state)
    connection = _connection()
    if transport == 'update':
        connection._presentation('capture', 'REASONING', 'Same instructions.', state_frame(_capture_state()))
    supplied = state if transport == 'full' else state_frame(state,
        _capture_state() if transport == 'update' else None)
    text, _ = connection._presentation('capture', 'REASONING', 'Same instructions.', supplied)
    assert text.startswith('TASK\n') and 'STEERING' in text and QUESTION in text
    assert '| Requested file role | Format | Acquisition state | Callable Source | Retained bytes | Failure |' in text
    assert '| stderr | native_stderr | retained | "source_' + '2' * 24 + '" | 0 | null |' in text
    assert '| seal | macs2_peak_command_seal_v1 | unavailable | null | null |' in text
    assert '| model | macs2_model_r | not_acquired | null | null | null |' in text
    assert 'original_missing' in text and '"attempt_output_version":"unverified"' in text
    assert '"writer_closure":"not_established"' in text
    assert PRIVATE_PATH not in text and PRIVATE_SHA not in text
    assert canonical(state) == before


@pytest.mark.parametrize('wrapped', [False, True])
def test_declared_macs2_capture_lookup_uses_same_human_view(wrapped):
    state, connection = _capture_state(), _connection()
    connection._presentation('capture-lookup', 'REASONING', 'Same instructions.', state_frame(state))
    capture = _capture_outcome()
    result = dict(status='completed', record_refs=[SOURCE], result=capture) if wrapped else dict(outcomes=[capture])
    before = canonical(result)
    text, _ = connection._presentation('capture-lookup', 'REASONING', 'Same instructions.',
        dict(version='decision_context_v1', kind='decision_lookup_result', decision_index=1,
            exchange_index=0, result=result))
    assert QUESTION in text and 'Selected MACS2 file capture 1' in text
    assert PRIVATE_PATH not in text and 'original_missing' in text
    assert canonical(result) == before


@pytest.mark.parametrize('fault', ['unrelated', 'undeclared', 'altered_schema', 'malformed', 'stdout_only'])
def test_capture_projection_does_not_adopt_unknown_or_unrelated_contracts(fault):
    from gene_annotation_episode.macs2_peak_presentation import select_macs2_peak_capture_presentation
    state, capture = _capture_state(), _capture_outcome()
    if fault == 'unrelated':
        state['scientific_process']['child_tool_info'] = []
    elif fault == 'undeclared':
        del state['available_report_facts']['execution_file_capture_outcomes']
    elif fault == 'altered_schema':
        state['available_report_facts']['execution_file_capture_outcomes']['report_schema']['minItems'] = 0
    elif fault == 'malformed':
        capture['files'][0]['size_bytes'] = -1
    else:
        capture['files'] = [capture['files'][1]]
    state['child_reports'] = [dict(outcomes=[capture])]
    before = canonical(state)
    selected = select_macs2_peak_capture_presentation(state)
    assert selected['captures'] == [] and canonical(selected['context']) == before
    assert canonical(state) == before


def test_empty_capture_and_literal_scientific_strings_are_preserved():
    from gene_annotation_episode.macs2_peak_presentation import select_macs2_peak_capture_presentation
    state, capture, packet = _capture_state(), _capture_outcome(), _packet()
    capture['files'] = []
    capture['job'].update(state='failed', returncode=7, failure_code='native_nonzero_exit')
    capture['failure'] = {'code': 'capture_unavailable'}
    packet['peak_window']['rows'][0]['row']['name'] = PRIVATE_PATH + PRIVATE_SHA
    state['child_reports'] = [dict(outcomes=[capture], peaks=[packet])]
    selected = select_macs2_peak_capture_presentation(state)
    assert selected['captures'][0]['files'] == []
    assert selected['captures'][0]['job'] == capture['job']
    assert selected['captures'][0]['failure'] == capture['failure']
    assert selected['context']['child_reports'][0]['peaks'] == [packet]
    text, _ = _connection()._presentation('capture-empty', 'REASONING', 'Same instructions.', state_frame(state))
    assert 'capture_unavailable' in text and 'native_nonzero_exit' in text
    assert PRIVATE_PATH + PRIVATE_SHA in text


def _monitor_service_ports(*, known=True, inside=True, parent_is_macs2=True, role='monitor'):
    """Engineered owner callbacks test ordering, not actual receipt authority."""
    from types import SimpleNamespace
    from gene_annotation_episode.episode_services import WorkflowServices
    events, store = [], object()
    assignment = dict(version='monitor_assignment_v1', target_handle=SOURCE,
        requested_fields=['execution_status', 'result_available'], known_progress_refs=[],
        permitted_committed_record_types=[])
    context = SimpleNamespace(run_id='engineering-run', episode_id='engineering-receiver', role=role,
        scope={'subject_refs': []}, assignment=assignment,
        request=dict(goal=dict(objective=QUESTION)))
    parent = dict(scientific_question=QUESTION,
        selected_tool_info=deepcopy(_science_state()['scientific_process']['child_tool_info']))
    if not parent_is_macs2:
        parent['selected_tool_info'] = []
    def received(episode_id):
        events.append('receipt')
        assert episode_id == context.episode_id
        return [SOURCE] if known else []
    workflow = SimpleNamespace(run_id=context.run_id, store=store,
        receipts=SimpleNamespace(known=received))
    service = WorkflowServices(workflow)
    def parent_task(actual):
        assert actual is context
        events.append('parent')
        return deepcopy(parent)
    service.scientific_parent_task = parent_task
    def scope(reference, selected_scope, namespace):
        events.append('scope')
        assert reference == SOURCE and selected_scope == context.scope and namespace == 'execution_handle'
        return inside
    service.reference_in_scope = scope
    job = _job()
    def read_target(reference, selected_scope):
        events.append('target')
        assert reference == SOURCE and selected_scope == context.scope
        return dict(resource_id='selected-local', resource_kind='local', assignment=dict(
            resource_kind='local', endpoint='usable_handoff', constraints=deepcopy(native.POLICY),
            requested_job=dict(native_macs2_peak=job)))
    owner = SimpleNamespace(store=store, run_id=context.run_id, services=service,
        job_progress_provider=SimpleNamespace(targets=SimpleNamespace(read_target=read_target)),
        _resource_information=lambda resource_id: dict(resource_id=resource_id,
            resource_kind='local', availability='declared_uninstalled_engineering_fixture', workspace=PRIVATE_PATH))
    workflow.episode_bindings = SimpleNamespace(for_role=lambda selected: owner if selected == 'results' else None)
    workflow.scientific_process_binding = SimpleNamespace(validate_context=lambda actual: events.append('scientific-context'))
    if role == 'scientific_process':
        context.assignment = dict(selection=dict(child_tool_info=deepcopy(parent['selected_tool_info'])))
    return service, context, assignment, events, job


@pytest.mark.parametrize('role', ['monitor', 'scientific_process'])
def test_macs2_monitor_task_uses_current_admission_before_original_target_controls(role):
    service, context, assignment, events, job = _monitor_service_ports(role=role)
    original = canonical(job)
    task = service.macs2_peak_monitor_task(context, **({'assignment': assignment} if role == 'scientific_process' else {}))
    assert events == [('parent' if role == 'monitor' else 'scientific-context'), 'receipt', 'scope', 'target']
    assert task['version'] == 'selected_execution_task_v1' and task['scientific_question'] == QUESTION
    assert task['selector'] == assignment and task['requests'][0]['job']['request']['callpeak'] == job['request']['callpeak']
    assert all(set(row['file']) == {'artifact_ref', 'format'} for row in task['requests'][0]['job']['request']['inputs'])
    assert 'software' not in task['requests'][0]['job'] and canonical(job) == original


@pytest.mark.parametrize('fault', ['unreceived', 'outside_scope', 'malformed'])
def test_macs2_monitor_denial_does_not_read_original_target_controls(fault):
    service, context, assignment, events, _ = _monitor_service_ports(
        known=fault != 'unreceived', inside=fault != 'outside_scope')
    if fault == 'malformed':
        context.assignment = {**assignment, 'extra': True}
    with pytest.raises(ValueError):
        service.macs2_peak_monitor_task(context)
    assert 'target' not in events
    if fault in ('unreceived', 'malformed'):
        assert 'scope' not in events


def test_non_macs2_monitor_keeps_optional_port_inactive():
    service, context, _, events, _ = _monitor_service_ports(parent_is_macs2=False)
    assert service.macs2_peak_monitor_task(context) is None
    assert events == ['parent']


@pytest.mark.parametrize('transport', ['bootstrap', 'update', 'lookup'])
def test_actual_monitor_task_uses_existing_selected_execution_wire(transport):
    service, context, _, _, _ = _monitor_service_ports()
    task = service.macs2_peak_monitor_task(context)
    state = _capture_state()
    state.pop('scientific_process')
    state.update(selected_execution_task=task, monitor_assignment=context.assignment)
    state['child_reports'] = [dict(outcomes=[_capture_outcome()])]
    before = canonical(state)
    connection = _connection()
    if transport != 'bootstrap':
        connection._presentation('monitor', 'REASONING', 'Unchanged monitor instructions.', state_frame(state))
    supplied = (dict(version='decision_context_v1', kind='decision_lookup_result', decision_index=1,
        exchange_index=0, result=dict(outcomes=[_capture_outcome()])) if transport == 'lookup' else
        state_frame(state, state if transport == 'update' else None))
    text, instructions = connection._presentation('monitor', 'REASONING', 'Unchanged monitor instructions.', supplied)
    assert text.startswith('TASK\n') and 'STEERING' in text and QUESTION in text
    assert 'genome_size_argument' in text and 'qvalue_cutoff' in text and '12010000' in text
    assert 'artifact_' + '1' * 64 in text and 'native input-detection' in text
    assert 'Selected MACS2 file capture 1' in text and 'original_missing' in text
    assert PRIVATE_PATH not in text and PRIVATE_SHA not in text
    assert instructions == 'Unchanged monitor instructions.' and canonical(state) == before


def test_monitor_calls_optional_admission_port_before_assignment_metadata(monkeypatch):
    from types import SimpleNamespace
    from gene_annotation_episode.episode_monitoring import MonitorEpisodes
    events = []
    task = dict(version='selected_execution_task_v1')
    services = SimpleNamespace(macs2_peak_monitor_task=lambda *args, **kwargs: events.append('admission') or task,
        describe_progress_target=lambda *args: {}, dependencies=lambda *args: [])
    binding = MonitorEpisodes(services)
    monkeypatch.setattr(binding, '_assignment', lambda value, scope: events.append('assignment') or value)
    monkeypatch.setattr(binding, '_received', lambda context: [])
    context = SimpleNamespace(role='monitor', assignment={'target_handle': SOURCE}, scope={})
    assert binding.decision_context(context, {})['selected_execution_task'] == task
    assert events == ['admission', 'assignment']
    events.clear()
    parent = SimpleNamespace(role='scientific_process')
    assert binding.prepare_assignment(parent, 'monitor', context.assignment, {}, 'selected') == context.assignment
    assert events == ['admission', 'assignment']


def _progress_capture_state():
    """A pure valid metadata plan/status; no unit, files or native output exist."""
    import os
    from gene_annotation_episode.native_atac_differential_contracts import _dependency_roots
    from gene_annotation_episode.progress_records import resource_status
    job = _job()
    workspace, operation = PRIVATE_PATH + '/workspace', 'engineering-start'
    driver = job['software']['driver_runtime']
    environment = dict(PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]),
        PYTHONHOME=workspace + '/python-home',
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
        TMP=workspace + '/tmp', TEMP=workspace + '/tmp', TMPDIR=workspace + '/tmp',
        XDG_CACHE_HOME=workspace + '/cache', PIP_CACHE_DIR=workspace + '/cache/pip')
    selected = native.requested_job_from_macs2_peak(job, environment=environment)
    assignment = dict(version='practical_assignment_v1', assignment_id='engineering-assignment',
        resource_id='selected-local', resource_kind='local', workspace=workspace,
        endpoint='usable_handoff', requested_job=selected, progress_requirements=[dict(key='handoff', credit=1,
            predicate=dict(kind='requested_job_handoff'))], completion_keys=['handoff'],
        initial_context=dict(revision=0, cwd=workspace, environment={}), inventory_snapshot={}, constraints=deepcopy(native.POLICY))
    root = Path(workspace) / '.episode-operations' / digest(dict(run='engineering-run', episode='engineering-local')) / digest(operation)
    identity = dict(run_id='engineering-run', episode_id='engineering-local', resource_id='selected-local',
        execution_id=str(root / 'native.json'), attempt_id=digest(operation), operation_key=operation,
        requested_job_sha256=digest(selected), assignment_sha256=digest(assignment))
    plan = native.macs2_peak_plan(assignment, identity, policy=native.POLICY)
    spec = next(row for row in plan['outputs'] if row['role'] == 'peaks_xls')
    output_path = str(Path(plan['attempt_directory']) / spec['relative_path'])
    observation = dict(observed_at='2026-10-31T00:00:00+00:00', state='completed', returncode=0,
        failure_code=None, result_available=True, measurements=[dict(measure='selected_seconds', seconds=0.0)],
        outputs=[dict(role='requested_output:' + output_path, available=True, bytes=0, writer_closed=True)],
        logs=[], provenance_refs=[], native=dict(native_macs2_peak_plan=plan,
            metadata=dict(elapsed_seconds=0.0, duration_measure='monotonic_wall_seconds', observed_scratch_bytes=0)))
    status = resource_status(dict(handle=SOURCE, resource_id='selected-local', resource_kind='local',
        execution_id=identity['execution_id'], request_sha256=digest(selected)), observation)
    progress = dict(version='progress_snapshot_v1', target_handle=SOURCE, progress_ref='progress_' + 'e' * 64,
        observed_at=observation['observed_at'], result_available=True, execution_status=status,
        committed_record_refs=[], measurements=[], log_windows=[], dependencies=[])
    state = _capture_state()
    state['waiting_support'] = dict(progress_records=[progress])
    return state


@pytest.mark.parametrize('selection', ['declared', 'unmatched', 'other_envelope'])
def test_progress_projection_uses_only_supplied_macs2_plan_output_declarations(selection):
    from gene_annotation_episode.macs2_peak_presentation import select_macs2_peak_capture_presentation
    state = _progress_capture_state()
    progress = state['waiting_support']['progress_records'][0]
    if selection == 'unmatched':
        progress['execution_status']['native']['outputs'][0]['role'] = 'requested_output:' + PRIVATE_PATH + '/not-declared'
    elif selection == 'other_envelope':
        del progress['execution_status']['native']['native']['native_macs2_peak_plan']
    before = canonical(state)
    shown = select_macs2_peak_capture_presentation(state)['context']['waiting_support']['progress_records'][0]
    if selection == 'other_envelope':
        assert shown == progress
    else:
        native_status = shown['execution_status']['native']
        output = native_status['outputs'][0]
        assert output['role'] == ('peaks_xls' if selection == 'declared' else 'requested_output')
        assert output['format'] == ('macs2_peaks_xls_narrow' if selection == 'declared' else None)
        assert output['bytes'] == 0 and output['writer_closed'] is True
        assert native_status['elapsed_seconds'] == 0.0 and native_status['observed_scratch_bytes'] == 0
        assert 'native' not in native_status and PRIVATE_PATH not in canonical(shown)
    assert canonical(state) == before
