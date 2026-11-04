"""Engineering form boundaries over genuine retained HOMER measurement bytes.

These tests establish schema, value and reference-projection behavior. Source
identities are engineered pure DTO inputs, never publication/receipt evidence.
Real own-action and receiver custody belongs to the ordinary host controls.
"""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import zipfile

import pytest

from gene_annotation_episode import homer_motif_measurements as measurements
from gene_annotation_episode import homer_motif_result_contracts as contracts
from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.molecular_result_facts import (
    merge_molecular_facts, requested_molecular_fact_fields, requested_molecular_fact_sources,
)
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from test_homer_motif_measurements import descriptor, invocation, execution


SOURCE = 'source_' + 'a' * 24
FIXTURE_SHA256 = 'f4aad8991e2bceb7b555726891c4fbaf9b6c6eabfaa1f903ea629631dc9c7a68'


def _forbidden(*_args, **_kwargs):
    raise AssertionError('HOMER return validation attempted scientific or private work')


@pytest.fixture(scope='module')
def packet():
    path = Path(__file__).with_name('fixtures') / 'homer_v51_selected_regions.zip'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FIXTURE_SHA256
    roles = {'homerMotifs.motifs8': 'denovo_pwm', 'seq.tsv': 'sequence_table', 'group.adj': 'group_weights'}
    with zipfile.ZipFile(path) as archive:
        files = [descriptor(role, name, archive.read('successful/' + name)) for name, role in roles.items()]
    sheet = measurements.parse_homer_motif_sheet(files, invocation=invocation(), execution=execution())
    series = sheet['series'][0]
    components = measurements.calculate_homer_components(sheet,
        selector={'series_ids': [series['series_id']], 'offset': 0, 'limit': 1})
    return measurements.project_homer_return(components, source_ref=SOURCE)


@pytest.fixture(autouse=True)
def no_scientific_or_private_work(monkeypatch, packet):
    for name in ('parse_homer_motif_sheet', 'calculate_homer_components', 'project_homer_return'):
        monkeypatch.setattr(measurements, name, _forbidden)
    for name in ('get_artifact', 'artifact', 'put', 'commit_reasoning'):
        monkeypatch.setattr(Store, name, _forbidden)
    monkeypatch.setattr(subprocess, 'run', _forbidden)
    monkeypatch.setattr(subprocess, 'Popen', _forbidden)
    monkeypatch.setattr(os, 'system', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)


def _schema(*fields):
    fields = fields or ('motifs',)
    registered = contracts.homer_motif_fact_sources()[contracts.FACT_SOURCE]['report_schema']
    return dict(type='object', properties={field: deepcopy(registered) for field in fields},
        required=list(fields), additionalProperties=False)


def _references(form, schema):
    return ScientificProcessEpisodes.received_form_references(
        SimpleNamespace(), object(), form, schema, 'engineering-projection')


@pytest.mark.parametrize('length', [0, 1, 2])
def test_exact_registered_homer_form_uses_original_schema_and_only_source_semantics(packet, length):
    schema, form = _schema(), dict(motifs=[deepcopy(packet) for _ in range(length)])
    original, resolved = canonical(dict(schema=schema, form=form)), []
    def resolver(reference, namespace):
        resolved.append((reference, namespace))
        return (reference, namespace) == (SOURCE, 'source')
    assert validate_closed_schema(schema) == schema
    assert validate_form(form, schema, resolver) == form
    assert resolved == [(SOURCE, 'source')] * length
    assert canonical(dict(schema=schema, form=form)) == original
    assert requested_molecular_fact_sources(schema) == (contracts.FACT_SOURCE,)
    assert requested_molecular_fact_fields(schema, fact_source=contracts.FACT_SOURCE) == ['motifs']
    row = packet['selected_series'][0]['observations'][0]
    numbers = row['representations'][0]['numbers']
    assert row['consensus'] == 'TTGCCAAG'
    assert numbers['ln_p_value']['number']['raw_token'] == '-466.553334'
    assert numbers['site_threshold']['number']['raw_token'] == '8.236954'
    assert numbers['q_value']['availability'] == 'not_provided'


@pytest.mark.parametrize('fault', ['version', 'missing_id', 'extra_constraint', 'namespace', 'nested'])
def test_counterfeit_or_nested_homer_schema_is_rejected(fault):
    schema = _schema()
    field = schema['properties']['motifs']
    if fault == 'version': field['$defs']['Return']['properties']['version']['const'] = 'counterfeit'
    elif fault == 'missing_id': del field['$id']
    elif fault == 'extra_constraint': field['minItems'] = 0
    elif fault == 'namespace': field['$defs']['Return']['properties']['source_ref']['x-reference-namespace'] = 'artifact'
    else: schema = dict(type='object', properties={'nested': schema}, required=['nested'], additionalProperties=False)
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic['code'] == 'invalid_schema'


@pytest.mark.parametrize('fault', ['boolean_count', 'float_count', 'boolean_ordinal', 'float_ordinal',
    'boolean_offset', 'float_offset', 'boolean_number', 'extra_private_file', 'null_source', 'source_newline'])
def test_invalid_homer_values_fail_before_reference_resolution(packet, fault):
    value, resolved = deepcopy(packet), []
    row = value['selected_series'][0]['observations'][0]
    if fault in ('boolean_count', 'float_count'):
        value['counts'][0]['captured_occurrences'] = True if fault == 'boolean_count' else 7.0
    elif fault in ('boolean_ordinal', 'float_ordinal'):
        row['ordinal_0based'] = False if fault == 'boolean_ordinal' else 0.0
    elif fault in ('boolean_offset', 'float_offset'):
        value['selector']['offset'] = False if fault == 'boolean_offset' else 0.0
    elif fault == 'boolean_number': row['representations'][0]['numbers']['target_weight']['number']['value'] = True
    elif fault == 'extra_private_file': value['private_file'] = 'artifact_' + 'c' * 64
    elif fault == 'null_source': value['source_ref'] = None
    else: value['source_ref'] += '\n'
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(dict(motifs=[value]), _schema(), lambda *args: resolved.append(args) or True)
    assert caught.value.diagnostic == dict(category='report_format', code='homer_motif_return_invalid', field='motifs')
    assert resolved == []


def test_source_free_value_wraps_only_an_actual_supplied_source_and_keeps_original_values(packet):
    value = {key: deepcopy(item) for key, item in packet.items() if key not in ('version', 'source_ref')}
    before = canonical(value)
    assert contracts.validate_homer_motif_value(value) == value
    assert contracts.homer_motif_return(value, source_ref=SOURCE) == packet
    assert canonical(value) == before
    with pytest.raises(ValueError): contracts.homer_motif_return(value, source_ref='artifact_' + 'c' * 64)
    with pytest.raises(ValueError): contracts.validate_homer_motif_value(packet)


def test_unreceived_source_is_rejected_without_resolving_native_scientific_ids(packet):
    resolved = []
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(dict(motifs=[packet]), _schema(), lambda *args: resolved.append(args) or False)
    assert resolved == [(SOURCE, 'source')]
    assert caught.value.diagnostic['code'] == 'unknown_reference'
    assert caught.value.diagnostic['field'] == 'report.motifs[0].source_ref'


def test_scientific_form_hook_projects_only_unique_top_level_sources(packet):
    schema = _schema('first', 'second')
    value = deepcopy(packet)
    # A native label resembling an Artifact is data, never an additional grant.
    value['selected_series'][0]['observations'][0]['name'] = 'artifact_' + 'd' * 64
    form = dict(first=[value, deepcopy(value)], second=[deepcopy(value)])
    before = canonical(form)
    assert _references(form, schema) == [SOURCE]
    assert canonical(form) == before


@pytest.mark.parametrize('fault', ['not_array', 'bad_row', 'forged_schema'])
def test_scientific_hook_validates_homer_group_before_projecting(packet, fault):
    schema, form = _schema(), dict(motifs=[deepcopy(packet)])
    if fault == 'not_array': form['motifs'] = form['motifs'][0]
    elif fault == 'bad_row': form['motifs'][0]['selector']['offset'] = True
    else: schema['properties']['motifs']['minItems'] = 0
    with pytest.raises(ValueError): _references(form, schema)


def _frozen_binding(values, calls):
    def facts(context, *, fact_source):
        calls.append((context, fact_source))
        return deepcopy(values)
    return SimpleNamespace(services=SimpleNamespace(molecular_frozen_facts=facts))


def test_scientific_frozen_homer_group_is_literal_without_math_or_private_reads(packet):
    calls, context = [], object()
    assert ScientificProcessEpisodes._validate_molecular_report(
        _frozen_binding([packet], calls), context, dict(motifs=[deepcopy(packet)]), _schema()) is None
    assert calls == [(context, contracts.FACT_SOURCE)]


@pytest.mark.parametrize('fault', ['number', 'source', 'selector', 'omitted_group', 'duplicate_group'])
def test_shape_valid_changed_homer_facts_fail_against_frozen_values(packet, fault):
    actual, calls = [deepcopy(packet)], []
    if fault == 'number':
        number = actual[0]['selected_series'][0]['observations'][0]['representations'][0]['numbers']['target_weight']['number']
        number.update(raw_token='101.0', value=101.0)
    elif fault == 'source': actual[0]['source_ref'] = 'source_' + 'f' * 24
    elif fault == 'selector': actual[0]['selector']['offset'] = 1
    elif fault == 'omitted_group': actual = []
    else: actual.append(deepcopy(packet))
    for value in actual: assert contracts.validate_homer_motif_return(value) == value
    with pytest.raises(ReportBoundaryError) as caught:
        ScientificProcessEpisodes._validate_molecular_report(
            _frozen_binding([packet], calls), object(), dict(motifs=actual), _schema())
    assert caught.value.diagnostic == dict(category='report_format', code='homer_motif_frozen_source_mismatch', field='motifs')
    assert 'retained native HOMER motif measurement facts' in str(caught.value)
    assert len(calls) == 1


def test_missing_frozen_homer_group_uses_registered_label_and_code(packet):
    calls = []
    with pytest.raises(ReportBoundaryError) as caught:
        ScientificProcessEpisodes._validate_molecular_report(
            _frozen_binding(None, calls), object(), dict(motifs=[packet]), _schema())
    assert caught.value.diagnostic == dict(category='report_format', code='homer_motif_facts_not_frozen', field='motifs')
    assert 'native HOMER motif measurement' in str(caught.value)


def test_molecular_merge_deduplicates_equal_fixed_sources_and_rejects_selector_drift(packet):
    assert merge_molecular_facts([packet], [deepcopy(packet)], fact_source=contracts.FACT_SOURCE) == [packet]
    changed = deepcopy(packet)
    changed['selector']['offset'] = 1
    with pytest.raises(ContractError, match='homer_motif_facts_source_conflict'):
        merge_molecular_facts([packet], [changed], fact_source=contracts.FACT_SOURCE)
    changed['source_ref'] = 'source_' + 'f' * 24
    assert merge_molecular_facts([packet], [changed], fact_source=contracts.FACT_SOURCE) == [packet, changed]


def test_unrelated_form_and_frozen_validator_preserve_prior_behavior():
    schema = dict(type='object', properties={'count': {'type': 'integer'}}, required=['count'], additionalProperties=False)
    assert _references(dict(count=0), schema) == []
    binding = SimpleNamespace(services=SimpleNamespace(molecular_frozen_facts=_forbidden))
    assert ScientificProcessEpisodes._validate_molecular_report(binding, object(), dict(count=0), schema) is None


def _engineered_capture_case(stack, directory, *, published=False, status='completed'):
    """Real metadata owners over explicit engineering rows, never a native run."""
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import identity
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    from test_molecular_sequence_input_bindings import actual_received_input_owner

    value = stack.enter_context(actual_received_input_owner(directory, deliver=False))
    store, context = value.store, value.parent
    store.db.execute('CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT,name TEXT,'
        'arguments TEXT,scope TEXT,result TEXT)')
    inputs = [value.artifact_ref, store.artifact(b'engineered reference FASTA'),
        store.artifact(b'engineered background BED')]
    value.receipts.receive(context.episode_id, inputs, kind='initial')
    arguments = dict(mode='run_native', inputs=[dict(role=role, namespace='artifact', reference=reference)
        for role, reference in zip(('target_bed', 'reference_fasta', 'background_bed'), inputs)],
        parameters=dict(window_bp=200, motif_lengths=[8, 10, 12], num_motifs=10, threads=1,
            strand='both', statistic='binomial', motif_set='all',
            normalization=dict(composition='gc', oligo_length=3, max_iterations=160, neutral=False)),
        selection=dict(series=[dict(role='denovo_pwm', motif_length=8)], offset=0, limit=1))
    key = f'{context.run_id}:{context.episode_id}:7'
    operation = identity('operation', dict(key=key, name=contracts.TOOL, arguments=arguments))
    selected = dict(kind='tool', tool=contracts.TOOL, arguments=arguments)
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
        (context.run_id, context.episode_id, 7, canonical(selected)))

    # These deliberately inconsistent metadata rows have no execution or grant.
    altered = deepcopy(arguments)
    altered['selection']['limit'] = 2
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
        (context.run_id, context.episode_id, 8, canonical(dict(kind='tool', tool=contracts.TOOL, arguments=altered))))
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
        (context.run_id, context.episode_id, 9, canonical(selected)))
    invalid_episode = 'episode_' + '0' * 64
    store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
        (context.run_id, invalid_episode, canonical(context.path), canonical(plain(context.request))))
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)',
        (context.run_id, invalid_episode, 0, canonical(selected)))

    def capture(label, *, fault=None):
        manifest = store.artifact(('engineered private capture manifest ' + label).encode())
        control = store.artifact(('engineered private capture request ' + label).encode())
        raw = store.artifact(('engineered retained native data ' + label).encode())
        accession = operation
        if fault == 'accession': accession = 'operation_' + '0' * 24
        elif fault in ('arguments', 'key', 'context'):
            claimed_key = (f'{context.run_id}:{context.episode_id}:8' if fault == 'arguments' else
                f'{context.run_id}:{context.episode_id}:99' if fault == 'key' else
                f'{context.run_id}:{invalid_episode}:0')
            accession = identity('operation', dict(key=claimed_key, name=contracts.TOOL, arguments=arguments))
        source = store.put('source', dict(provider=contracts.TOOL, version=contracts.CAPTURE_VERSION,
            accession=accession, uri=None, artifact_ref=manifest, request_ref=control, text_ref=None,
            retrieved_at=None, parent_source_refs=[],
            # An adversarial collision cannot revoke an independently supplied File.
            auxiliary_artifact_refs=[raw, inputs[0]]), origin='tool')
        return dict(source=source['id'], manifest=manifest, control=control, raw=raw)

    refs = capture('selected')
    invalid = {fault: capture(fault, fault=fault) for fault in ('accession', 'arguments', 'key', 'context')}
    main, main_delta = None, set()
    if published:
        public = store.artifact(b'engineering public packet, not a scientific publication')
        request = store.artifact(b'engineering private publication request')
        sheet, components = store.artifact(b'engineering retained sheet'), store.artifact(b'engineering retained components')
        main = store.put('source', dict(provider=contracts.TOOL, version=contracts.SOURCE_VERSION,
            accession=None, uri=None, artifact_ref=public, request_ref=request, text_ref=None,
            retrieved_at=None, parent_source_refs=[refs['source']],
            auxiliary_artifact_refs=[refs['raw'], sheet, components]), origin='tool')
        outcome = dict(status=status, operation_ref=operation, record_refs=[main['id']],
            result=dict(source_ref=main['id']), feedback=None)
        store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)',
            (key, operation, contracts.TOOL, canonical(arguments), canonical(value.scope), canonical(outcome)))
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=7',
            (canonical(outcome), context.run_id, context.episode_id))
        before = set(value.receipts.known(context.episode_id))
        value.receipts.receive(context.episode_id, [main['id']], kind='own_action', source_index=7)
        main_delta = set(value.receipts.known(context.episode_id)) - before
        refs.update(public=public, request=request, sheet=sheet, components=components)
    receiver = value.child(1)
    before = set(value.receipts.known(context.episode_id))
    value.receipts.receive(context.episode_id, [refs['source']], kind='initial')
    capture_delta = set(value.receipts.known(context.episode_id)) - before
    explicitly_received_capture = value.child(2)
    value.owner.resolve_received_reference = lambda current, ref, namespace: molecular_reference_restriction(
        store, current, ref, namespace, providers=(contracts.TOOL,))
    return SimpleNamespace(value=value, store=store, producer=context, context=receiver,
        capture_context=explicitly_received_capture, refs=refs, invalid=invalid, inputs=inputs,
        main=main, main_delta=main_delta, capture_delta=capture_delta, operation_key=key)


@pytest.fixture(scope='module')
def homer_custody(tmp_path_factory):
    with ExitStack() as stack:
        root = tmp_path_factory.mktemp('homer-engineered-custody')
        yield dict(pending=_engineered_capture_case(stack, root / 'pending'),
            complete=_engineered_capture_case(stack, root / 'complete', published=True),
            partial=_engineered_capture_case(stack, root / 'partial', published=True, status='partial'))


@pytest.fixture
def custody_read_guard(monkeypatch, homer_custody):
    from gene_annotation_episode import homer_motif_tools as host
    before = {name: list(case.store.db.iterdump()) for name, case in homer_custody.items()}
    monkeypatch.setattr(host, '_publication_bytes', _forbidden)
    monkeypatch.setattr(host, '_regular', _forbidden)
    original = Path.open
    roots = [case.store.path / 'artifacts' for case in homer_custody.values()]
    def metadata_only(path, *args, **kwargs):
        if any(path.is_relative_to(root) for root in roots):
            raise AssertionError('privacy classification opened an Artifact body')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', metadata_only)
    yield
    assert {name: list(case.store.db.iterdump()) for name, case in homer_custody.items()} == before


@pytest.mark.parametrize('role', ['source', 'manifest', 'control', 'raw'])
def test_pending_homer_capture_is_private_before_public_source_or_toolop(homer_custody, custody_read_guard, role):
    from gene_annotation_episode.homer_motif_tools import homer_capture_reference_restriction
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = homer_custody['pending']
    assert case.main is None
    assert case.store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0
    assert case.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
        'AND decision_index=7', (case.producer.run_id, case.producer.episode_id)).fetchone()[0] is None
    namespace = 'source' if role == 'source' else 'artifact'
    reference = case.refs[role]
    assert homer_capture_reference_restriction(case.store, case.context, reference, namespace) is False
    assert molecular_reference_restriction(case.store, case.context, reference, namespace) is False
    assert reference not in set(case.value.receipts.known(case.context.episode_id))


@pytest.mark.parametrize('fault', ['accession', 'arguments', 'key', 'context'])
def test_private_capture_marker_needs_exact_recorded_action_association(homer_custody, custody_read_guard, fault):
    from gene_annotation_episode.homer_motif_tools import homer_capture_reference_restriction
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = homer_custody['pending']
    for role, reference in case.invalid[fault].items():
        namespace = 'source' if role == 'source' else 'artifact'
        assert homer_capture_reference_restriction(case.store, case.context, reference, namespace) is None
        assert molecular_reference_restriction(case.store, case.context, reference, namespace) is None


@pytest.mark.parametrize('name', ['pending', 'complete', 'partial'])
def test_homer_private_capture_cannot_revoke_independent_original_file_admission(homer_custody, custody_read_guard, name):
    from gene_annotation_episode.homer_motif_tools import homer_capture_reference_restriction
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = homer_custody[name]
    reference = case.inputs[0]
    assert reference in case.store.get(case.refs['source'])['auxiliary_artifact_refs']
    assert reference in set(case.value.receipts.known(case.context.episode_id))
    assert homer_capture_reference_restriction(case.store, case.context, reference, 'artifact') is None
    assert molecular_reference_restriction(case.store, case.context, reference, 'artifact') is None
    with case.store.read_snapshot():
        item = case.value.binding._received_file_item(case.context, reference, 'artifact', file_format='bed')
    assert item['file']['artifact_ref'] == reference
    assert item['byte_verification'] == 'unavailable'


@pytest.mark.parametrize('name', ['complete', 'partial'])
def test_homer_main_receipt_grants_only_public_source_and_no_private_lineage(homer_custody, custody_read_guard, name):
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = homer_custody[name]
    assert case.main_delta == {case.main['id']}
    known = set(case.value.receipts.known(case.context.episode_id))
    assert case.main['id'] in known
    assert molecular_reference_restriction(case.store, case.context, case.main['id'], 'source') is True
    assert molecular_reference_restriction(case.store, case.value.context, case.main['id'], 'source') is False
    assert case.refs['source'] not in known
    for role in ('manifest', 'control', 'raw', 'public', 'request', 'sheet', 'components'):
        assert case.refs[role] not in known
        assert molecular_reference_restriction(case.store, case.context, case.refs[role], 'artifact') is False


@pytest.mark.parametrize('name', ['pending', 'complete', 'partial'])
def test_explicit_engineered_capture_receipt_still_grants_no_private_files(homer_custody, custody_read_guard, name):
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = homer_custody[name]
    assert case.capture_delta == {case.refs['source']}
    known = set(case.value.receipts.known(case.capture_context.episode_id))
    assert case.refs['source'] in known
    assert molecular_reference_restriction(case.store, case.capture_context, case.refs['source'], 'source') is False
    assert all(case.refs[role] not in known for role in ('manifest', 'control', 'raw'))
