"""F saved returns with retained native data and explicit synthetic witnesses.

Numerical inputs are produced by the actual D/E modules. Store, Journal,
commission custody and TypedReportContract are real. ControlledPublications is
only a test publication envelope; these checks do not establish the native API
publication chain or a live service deployment.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_genome_alignment_bundle_contracts as contracts
from gene_annotation_episode import bvbrc_genome_alignment_bundle_projection as projection
from gene_annotation_episode.bvbrc_genome_alignment_returns import (
    BVBRCGenomeAlignmentReturns, FACT_SOURCES, IDENTIFIER_NAMESPACES,
    genome_alignment_fact_sources, requested_sources, project_genome_alignment_facts,
)
from gene_annotation_episode.bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.communication import (
    plain, form_with_facts, validate_closed_schema, validate_form, ReportBoundaryError,
)
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import TypedReportContract, _object
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords, selector as base_selector
from test_bvbrc_genome_alignment_bundle_resolution import arguments, measurement, member
from test_bvbrc_genome_alignment_bundle_projection import saved_arguments
from test_bvbrc_genome_alignment_sheet import fixture_sheet, fixture_data, plan, all_requests


MEASUREMENTS, V4, SPANS, BBCOLS, COVERAGE, NATIVE, SOURCE, ORIGINAL, INVERSE, STATUS, REQUIREMENTS, QUALIFICATIONS = FACT_SOURCES
CELL = {'block_index': 0, 'record_index': 0, 'column_0based': 0}


def fact_form(*sources):
    descriptors = genome_alignment_fact_sources()
    properties = {f'f{i}': descriptors[source]['report_schema'] for i, source in enumerate(sources)}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def content(value, name):
    raw = canonical(value).encode('utf-8')
    return {'source_ref': 'source_' + digest([name, value])[:24], 'artifact_field': 'artifact_ref',
        'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(),
        'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def all_fields():
    return {
        'identity': measurement('pairs', 'xmfa_pair', 'identity_fraction', block_index=0, member_a=1, member_b=2),
        'coverage_fraction': measurement(field='coverage_fraction'),
        'zero_gaps': measurement('anchors', 'v4_member', 'selected_gap_count', interval_index=0, segment_index=0, member=member()),
        'v4': {'kind': 'v4_segment', 'request_id': 'anchors', 'interval_index': 0, 'segment_index': 0, 'member': member()},
        'span': {'kind': 'backbone_span', 'request_id': 'backbone', 'row_index': 0, 'member': member(0, 'mauve_sidecar_member_0based')},
        'interval': {'kind': 'bbcols_interval', 'request_id': 'columns', 'native_interval_index_0based': 0},
        'coverage': {'kind': 'coverage_intervals', 'request_id': 'coverage', 'member': member(1, 'mauve1_member_1based'), 'part': 'union'},
        **{kind: {'kind': kind, 'request_id': 'cell', 'cell': CELL} for kind in (
            'xmfa_native_coordinate', 'xmfa_source_coordinate', 'xmfa_original_coordinates')},
        'inverse': {'kind': 'xmfa_inverse_coordinates', 'request_id': 'inverse', 'query': {'member_number': 1, 'position_0based': 49}},
        'status': {'kind': 'request_status', 'request_id': 'anchors'},
        'requirements': {'kind': 'missing_requirements', 'scope': 'all', 'request_id': None},
        'qualifications': {'kind': 'qualifications', 'scope': 'all', 'request_id': None},
    }


def envelope(result, parameters, requested_form, original_task):
    selection = base_selector()
    selection.update(endpoint='requested_projection', adapter={'adapter_id': 'bvbrc_genome_alignment',
        'adapter_version': '1', 'parameters': deepcopy(parameters)}, requested_schema=deepcopy(requested_form))
    selection['requirements'][0]['role'] = 'genome_alignment_primary'
    bundle = {'original_task': deepcopy(original_task)}
    bundle_content = content(bundle, 'bundle')
    saved = {k: deepcopy(result[k]) for k in ('status', 'facts', 'missing_requirements', 'diagnostics')}
    saved.update(adapter_id='bvbrc_genome_alignment', adapter_version='1')
    for name in ('sheet', 'components'):
        saved[name + '_content'] = None if result[name] is None else content(result[name], name)
    reference = bundle_content['source_ref']
    body = {'version': RESULT_VERSION, 'reference': reference, 'source_ref': reference, 'record_refs': [reference],
        'assignment': {'selector': deepcopy(selection)}, 'bundle': bundle,
        'publication_inputs': {'selector': selection, 'adapter': deepcopy(selection['adapter']),
            'adapter_implementation_sha256': 'a' * 64},
        'publication': {'bundle_content': bundle_content, 'result_record_refs': [reference], 'adapter_result': saved}}
    return body, deepcopy(result['sheet']), deepcopy(result['components'])


def example(fields=None, sheet=None):
    sheet = fixture_sheet() if sheet is None else sheet
    args = saved_arguments(sheet, all_fields() if fields is None else fields)
    projected = projection.project_genome_alignment_facts(**args)
    args.update(missing_requirements=tuple(projected['missing_requirements']), diagnostics=tuple(projected['diagnostics']))
    result = projected | {'sheet': sheet, 'components': sheet['components'],
        'status': projection.requested_projection_status(projected['facts'], **args)}
    return envelope(result, args['parameters'], args['requested_form'], sheet['data']['original_task'])


def facade_example(fmt='mauve_v4', fields=None, change=None):
    args = arguments(fmt, fields)
    if change:
        change(args)
    result = adapter.consume_bundle(**args)
    return envelope(result, args['parameters'], args['requested_form'], args['bundle']['original_task'])


def project(args, sources=FACT_SOURCES):
    return project_genome_alignment_facts(args[0], requested_sources=sources, sheet=args[1], components=args[2])


def rebind(args):
    body, sheet, components = args
    for name, value in (('sheet', sheet), ('components', components)):
        body['publication']['adapter_result'][name + '_content'] = None if value is None else content(value, name)


def forbid_science(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('scientific work or acquisition during saved return')
    functions = {
        'bvbrc_genome_alignment_bundle_adapter': ['consume_bundle', 'implementation_sha256'],
        'bvbrc_genome_alignment_bundle_resolution': ['consume_bundle', '_parse', 'extract_genome_alignment_inputs',
            'bind_genome_alignment_artifacts', 'calculate_genome_alignment_components'],
        'bvbrc_genome_alignment_calculators': ['calculate_genome_alignment_components', '_dispatch', 'bind_xmfa_sources'],
        'mauve_v4_formats': ['parse_mauve_v4'], 'mauve_backbone_formats': ['parse_mauve_backbone', 'parse_mauve_bbcols'],
        'xmfa_formats': ['parse_mauve_xmfa'], 'mauve_v4_calculators': ['calculate_mauve_v4_segments'],
        'mauve_backbone_calculators': ['calculate_mauve_backbone_components', 'calculate_mauve_bbcols_components'],
        'xmfa_calculators': ['xmfa_alignment_components', 'xmfa_interval_coverage'],
        'xmfa_coordinates': ['xmfa_column_coordinates', 'xmfa_source_positions'],
        'xmfa_sources': ['bind_xmfa_sources', 'validate_xmfa_bindings_for_document'],
        'bvbrc_genome_alignment_inputs': ['extract_genome_alignment_inputs'],
        'bvbrc_genome_alignment_associations': ['bind_genome_alignment_artifacts'],
    }
    for name, attrs in functions.items():
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attr in attrs:
            monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)


def test_all_twelve_families_use_closed_grammar_and_thirteen_exact_namespaces():
    descriptors = genome_alignment_fact_sources()
    assert tuple(descriptors) == FACT_SOURCES and len(descriptors) == 12
    assert IDENTIFIER_NAMESPACES == tuple('bvbrc_genome_alignment_' + k for k in contracts.REFERENCE_KINDS)
    assert len(IDENTIFIER_NAMESPACES) == 13
    schema = fact_form(*FACT_SOURCES)
    assert validate_closed_schema(schema) == schema
    assert requested_sources(fact_form(STATUS, NATIVE, STATUS, MEASUREMENTS)) == (STATUS, NATIVE, MEASUREMENTS)
    for source, descriptor in descriptors.items():
        assert descriptor['meaning'].startswith('Recorded GenomeAlignment ')
        assert descriptor['report_schema']['items']['properties']['source_ref']['x-reference-namespace'] == 'execution_result'


def test_retained_values_coordinates_requirements_and_detached_field_order():
    args = example(); before = deepcopy(args)
    values = project(args)
    numbers = [r['value']['value']['value'] for r in values[MEASUREMENTS]]
    assert numbers == [40 / 48, 690 / 693, 0]
    assert values[MEASUREMENTS][0]['value']['value']['denominator'] == 48
    assert values[V4][0]['value']['value']['member'] == member(0)
    assert values[SPANS][0]['value']['value']['member'] == member(0, 'mauve_sidecar_member_0based')
    assert values[BBCOLS][0]['value']['value']['known_union_intervals'] == [[0, 52]]
    assert values[COVERAGE][0]['value']['value']['intervals'] == [[0, 50]]
    native = values[NATIVE][0]['value']['value']
    assert (native['native_position_1based'], native['native_position_0based'], native['native_strand']) == (50, 49, '-')
    assert (native['aligned_symbol'], native['forward_symbol']) == ('T', 'A')
    assert values[SOURCE][0]['value']['value']['source_coordinate']['position_0based'] == 49
    assert values[ORIGINAL][0]['value']['value']['original_coordinates'] == []
    assert values[INVERSE][0]['value']['value']['matches'] == [CELL]
    assert len(values[REQUIREMENTS][0]['value']) == 11
    schema = fact_form(*FACT_SOURCES)
    validate_form(form_with_facts({}, schema, values), schema, lambda *_: True)
    values[MEASUREMENTS][0]['value']['value']['value'] = -1
    assert args == before


@pytest.mark.parametrize('fmt,expected', [('mauve_v4', 690), ('mauve_backbone', 50),
    ('mauve_bbcols', 52), ('mauve1_xmfa', 40 / 48)])
def test_actual_e_facade_publication_values_are_preserved(fmt, expected):
    args = facade_example(fmt)
    values = project(args, (MEASUREMENTS,))
    assert values[MEASUREMENTS][0]['value']['value']['value'] == expected
    assert project(args, (NATIVE,)) == {NATIVE: []}


@pytest.mark.parametrize('sources', [[], (MEASUREMENTS, MEASUREMENTS), ('unknown',), None, {MEASUREMENTS}])
def test_request_must_be_known_duplicate_free_tuple(sources):
    with pytest.raises(ValueError, match='requested_sources_invalid'):
        project_genome_alignment_facts({}, requested_sources=sources, sheet=None, components=None)


def test_no_requested_source_does_not_inspect_publication():
    assert project_genome_alignment_facts(None, requested_sources=(), sheet=None, components=None) == {}


@pytest.mark.parametrize('target', ['source', 'reference', 'result_refs', 'record_refs', 'adapter', 'version',
    'selected_adapter', 'input_adapter', 'pin', 'assignment', 'selector', 'schema', 'task', 'analysis',
    'document', 'plan', 'numeric', 'request_ref', 'extra_fact', 'missing_fact', 'sheet_hash', 'component_count',
    'component_bytes', 'sheet_binding', 'components_binding', 'status'])
def test_saved_integrity_and_original_relationship_corruption_rejected(target):
    args = list(example()); body, sheet, components = args
    saved = body['publication']['adapter_result']; selected = body['publication_inputs']['selector']['adapter']
    if target == 'source': body['source_ref'] = 'artifact_' + 'a' * 64
    elif target == 'reference': body['reference'] = 'source_' + 'b' * 24
    elif target == 'result_refs': body['publication']['result_record_refs'] = []
    elif target == 'record_refs': body['record_refs'] = []
    elif target == 'adapter': saved['adapter_id'] = 'bvbrc_msa'
    elif target == 'version': saved['adapter_version'] = '2'
    elif target == 'selected_adapter': selected['adapter_version'] = '2'
    elif target == 'input_adapter': body['publication_inputs']['adapter']['parameters']['analysis_id'] = 'replacement'
    elif target == 'pin': body['publication_inputs']['adapter_implementation_sha256'] = 'A' * 64
    elif target == 'assignment': body['assignment']['selector']['endpoint'] = 'requested_artifacts'
    elif target == 'selector':
        form = body['publication_inputs']['selector']['requested_schema']
        form['properties']['identity']['x-genome-alignment-fact']['metric']['field'] = 'substitutions'
        body['assignment']['selector'] = deepcopy(body['publication_inputs']['selector'])
    elif target == 'schema':
        body['publication_inputs']['selector']['requested_schema']['properties']['identity']['additionalProperties'] = True
        body['assignment']['selector'] = deepcopy(body['publication_inputs']['selector'])
    elif target == 'task': body['bundle']['original_task']['task_id'] = 'other-task'
    elif target == 'analysis': sheet['analysis_id'] = 'replacement'; rebind(args)
    elif target == 'document': sheet['data']['slot_resolutions'][0]['document_id'] = 'other-document'; rebind(args)
    elif target == 'plan':
        components['calculation_plan']['requests'][0]['request_id'] = 'replacement'
        sheet['components'] = deepcopy(components); rebind(args)
    elif target == 'numeric': saved['facts']['identity']['value']['value'] = 0
    elif target == 'request_ref': saved['facts']['identity']['request_ref'] = contracts.encode_reference('request', 'other', 'pairs')
    elif target == 'extra_fact': saved['facts']['extra'] = deepcopy(saved['facts']['identity'])
    elif target == 'missing_fact': del saved['facts']['identity']
    elif target == 'sheet_hash': saved['sheet_content']['sha256'] = '0' * 64
    elif target == 'component_count': saved['components_content']['byte_count'] += 1
    elif target == 'component_bytes': components['analysis_id'] = 'replacement'
    elif target == 'sheet_binding': args[1] = None
    elif target == 'components_binding': args[2] = None
    else: saved['status'] = 'ok' if saved['status'] == 'partial' else 'partial'
    with pytest.raises(ValueError): project(args)


@pytest.mark.parametrize('index', [0, 1, 2])
def test_every_missing_request_preserves_original_identity(index):
    def alter(args):
        p = args['parameters']; original = p['calculation_plan']['requests'][0]
        slot = deepcopy(p['document_slots'][0]); slot.update(slot_id='missing', source_ref=None, raw_artifact_ref=None)
        p['document_slots'].append(slot)
        reqs = [deepcopy(original) | {'request_id': f'r{i}'} for i in range(3)]
        reqs[index]['document_slot_id'] = 'missing'; slot['source_ref'] = 'absent'
        p['calculation_plan'] = plan(reqs)
        args['requested_form'] = contracts.requested_form_schema({f'f{i}': measurement(f'r{i}') for i in range(3)})
    values = project(facade_example(change=alter), (MEASUREMENTS,))[MEASUREMENTS]
    assert [contracts.decode_reference(row['value']['request_ref'])[2] for row in values] == ['r0', 'r1', 'r2']
    assert [row['value']['state'] for row in values] == ['missing' if i == index else 'resolved' for i in range(3)]
    assert values[index]['value']['value'] is None


def test_invalid_null_sheet_has_empty_facts_and_cannot_promote_older_sheet():
    def wrong_task(args):
        args['bundle']['original_task'].update(required_application_id='MSA', native_application_id='MSA')
        args['retained_records'] = ()
    args = list(facade_example(change=wrong_task))
    assert args[1] is args[2] is None
    assert project(args) == {source: [] for source in FACT_SOURCES}
    args[1] = fixture_sheet()
    with pytest.raises(ValueError, match='saved_sheet_binding_conflict'): project(args)


def test_saved_projection_forbids_all_native_science_and_io(monkeypatch):
    args = example(); expected = project(args)
    forbid_science(monkeypatch)
    monkeypatch.setattr('builtins.open', lambda *a, **k: pytest.fail('file read in pure projector'))
    assert project(args) == expected


def test_malformed_native_symbol_is_incompatible_and_independent_number_survives(monkeypatch):
    from test_bvbrc_genome_alignment_bundle_resolution import replace_native, scientific_artifact
    fields = {'bad': {'kind': 'xmfa_native_coordinate', 'request_id': 'cell', 'cell': CELL},
        'number': measurement('pairs', 'xmfa_block', 'selected_column_count', block_index=0),
        'requirements': {'kind': 'missing_requirements', 'scope': 'request', 'request_id': 'cell'}}
    def alter(args):
        raw = args['artifact_bytes'][scientific_artifact(args)['raw_artifact_ref']]
        replace_native(args, raw.replace(b'TAAGCCCTCCTAG', b'?AAGCCCTCCTAG', 1))
    args = facade_example('mauve1_xmfa', fields, alter)
    forbid_science(monkeypatch)
    values = project(args, (NATIVE, MEASUREMENTS, REQUIREMENTS))
    assert values[NATIVE][0]['value']['state'] == 'incompatible'
    assert values[NATIVE][0]['value']['value'] is None
    assert values[MEASUREMENTS][0]['value']['value']['value'] == 52
    reasons = [contracts.decode_reference(r['reason_ref'])[2] for r in values[REQUIREMENTS][0]['value']]
    assert 'bvbrc_genome_alignment_bundle_projection_target_incompatible' in reasons
    native = next(o for o in args[2]['outcomes'] if o['request_id'] == 'cell')['measurement']['value']['cells'][0]
    assert native['aligned_symbol'] == '?'


class ControlledPublications:
    """Test envelope only; authentic Store bytes and runtime custody underneath."""
    def __init__(self, saved):
        self.saved, self.bodies, self.contents, self.reads = saved, {}, {}, []
        self.host = SimpleNamespace(custody=saved.custody)
        self.api = SimpleNamespace(_own_outcomes=self.outcomes)

    def add(self, context, args, index=0):
        body, sheet, components = deepcopy(args)
        for name, value in (('sheet', sheet), ('components', components)):
            binding = None if value is None else self.saved.source(canonical(value).encode(), provider=DATA_PROVIDER)
            body['publication']['adapter_result'][name + '_content'] = binding
            if binding is not None: self.contents[binding['source_ref']] = binding
        binding = self.saved.source(canonical({'body': body, 'episode': context.episode_id, 'index': index}).encode(), provider=DATA_PROVIDER)
        reference = binding['source_ref']
        body.update(reference=reference, source_ref=reference, record_refs=[reference], run_id=context.run_id,
            episode_id=context.episode_id, scope=plain(context.scope), assignment=plain(context.assignment))
        body['publication'].update(bundle_content=binding, result_record_refs=[reference], origin={
            'operation_key': f'{context.run_id}:{context.episode_id}:{index}'})
        body['publication_inputs']['current_snapshot'] = {'retrieved_at': 'synthetic:' + str(index)}
        self.bodies[reference] = body
        self.saved.own(context, reference, index, tool='api.bvbrc_appservice.download')
        return body

    def outcomes(self, context):
        rows = self.saved.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND result IS NOT NULL ORDER BY decision_index', (context.run_id, context.episode_id))
        for row in rows:
            result = json.loads(row['result'])
            if result['status'] in {'completed', 'partial'}:
                refs = [r for r in result['record_refs'] if r in self.bodies]
                if refs: yield None, {'result': {'result_record_refs': refs}}

    def read(self, reference, scope, *, episode_id=None):
        self.reads.append(reference)
        if reference not in self.bodies:
            raise ValueError('not_an_appservice_acquired_result')
        body = deepcopy(self.bodies[reference])
        context = self.saved.custody.context(body['episode_id'])
        if episode_id is not None and context.episode_id != episode_id:
            raise ValueError('controlled_publication_wrong_owner')
        self.saved.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        self.saved.custody.possession(context, reference)
        return body

    def read_content_source(self, reference, scope):
        binding = self.contents[reference]
        raw = self.saved.store.get_artifact(binding['artifact_ref'])
        assert hashlib.sha256(raw).hexdigest() == binding['sha256'] and len(raw) == binding['byte_count']
        return json.loads(raw)

    def _content(self, binding, origin, kind, stamp):
        assert any(body['publication']['origin'] == origin
            and body['publication_inputs']['current_snapshot']['retrieved_at'] == stamp
            and body['publication']['adapter_result'][kind + '_content'] == binding for body in self.bodies.values())
        return self.read_content_source(binding['source_ref'], {})


class ReturnFixture:
    def __init__(self, store):
        self.store, self.saved = store, SavedRecords(store)
        self.publications = ControlledPublications(self.saved)
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id,
            appservice=SimpleNamespace(publications=self.publications, custody=self.saved.custody))
        self.host = BVBRCGenomeAlignmentReturns(self.api)

    def child(self, parent, role, body, *, index=0, sources=FACT_SOURCES, schema=None):
        assignment = {} if role != 'results' else {'version': 'execution_results_assignment_v1',
            'handoff_ref': 'source_' + 'a' * 24, 'selector': body['publication_inputs']['selector']}
        return self.saved.child(parent, role, assignment, index, schema=fact_form(*sources) if schema is None else schema)

    def candidate(self, child):
        schema = plain(child.request)['report_contract']['measurements']['schema']
        facts = self.host.facts(child, schema) if child.role == 'results' else self.host.received_facts(child, schema)
        form = form_with_facts({}, schema, facts)
        self.saved.journal.save('runtime_forms', {'episode_id': child.episode_id,
            'facts': canonical(facts), 'form': canonical(form)})
        return form, schema

    def admit(self, parent, child):
        form, schema = self.candidate(child)
        contract = plain(child.request)['report_contract']
        # This controlled boundary uses one fully validated fact snapshot for
        # reference traversal. Public resolvers are exercised separately below;
        # the real host's per-reference integration is root G's responsibility.
        facts = {node['x-source']: form[name] for name, node in schema['properties'].items()}
        self.host._possessed_sources(child, facts)
        typed = TypedReportContract(contract['decision'], schema,
            lambda reference, namespace: self.host._has_reference(facts, reference, namespace),
            lambda value: self.host.validate_received_report(child, value, schema))
        admitted = plain(typed.admit(form, audit_identifiers=(child.episode_id,)).as_record())
        index = int(child.path[-1][1].removeprefix('child_'))
        self.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24],
            'child_episode_id': child.episode_id, 'contract': canonical(contract), 'form': canonical(admitted), 'failure': None})
        key = f'{parent.run_id}:{parent.episode_id}:{index}:typed_form'
        references = self.host.record_admission(parent, admitted, schema, key)
        self.saved.receipts.receive(parent.episode_id, references, kind='child_form', source_index=index)
        return admitted, schema, key, references


@pytest.fixture
def run(tmp_path):
    with Store(tmp_path / 'state') as store:
        yield ReturnFixture(store)


def test_real_recorded_custody_and_recursive_returns_without_science(run, monkeypatch):
    args = example()
    parent = run.child(run.saved.root, 'scientific_process', args[0])
    child = run.child(parent, 'results', args[0])
    published = run.publications.add(child, args)
    forbid_science(monkeypatch)
    before = run.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
    form, schema, key, references = run.admit(parent, child)
    assert references == [published['source_ref']]
    received = run.host.received_facts(parent, schema)
    assert received[MEASUREMENTS][0]['value']['value']['value'] == 40 / 48
    assert run.host.record_admission(parent, form, schema, key) == references
    run.admit(run.saved.root, parent)
    assert run.host.received_facts(run.saved.root, schema) == received
    assert run.saved.custody.possession(run.saved.root, published['source_ref']) == 'admitted_return'
    assert run.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == before
    assert run.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_newest_partial_and_invalid_are_not_replaced_by_old_success(run):
    good = facade_example()
    bad = facade_example(change=lambda a: a['artifact_bytes'].clear())
    child = run.child(run.saved.root, 'results', good[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, good, index=2)
    second = run.publications.add(child, bad, index=11)
    schema = fact_form(MEASUREMENTS)
    assert run.host.facts(child, schema)[MEASUREMENTS][0]['value']['state'] == 'missing'
    assert run.publications.reads == [second['source_ref']]
    invalid = deepcopy(good)
    invalid[0]['publication']['adapter_result'].update(status='invalid', facts={})
    invalid = (invalid[0], None, None)
    run.publications.add(child, invalid, index=20)
    assert run.host.facts(child, schema) == {MEASUREMENTS: []}
    assert first['source_ref'] not in run.publications.reads


def test_original_historical_child_result_survives_newer_publication(run, monkeypatch):
    good = facade_example(); bad = facade_example(change=lambda a: a['artifact_bytes'].clear())
    child = run.child(run.saved.root, 'results', good[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, good)
    original, schema, key, _ = run.admit(run.saved.root, child)
    newest = run.publications.add(child, bad, index=10)
    forbid_science(monkeypatch)
    run.publications.reads.clear()
    assert run.host.received_facts(run.saved.root, schema)[MEASUREMENTS] == original['f0']
    assert newest['source_ref'] not in run.publications.reads
    assert first['source_ref'] in run.publications.reads
    assert run.host.record_admission(run.saved.root, original, schema, key) == [first['source_ref']]
    assert run.host.facts(child, schema)[MEASUREMENTS][0]['source_ref'] == newest['source_ref']


@pytest.mark.parametrize('field', ['run_id', 'episode_id', 'scope', 'assignment', 'role'])
def test_wrong_context_cannot_claim_own_values(run, field):
    args = example(); child = run.child(run.saved.root, 'results', args[0]); run.publications.add(child, args)
    wrong = {'run_id': 'other', 'episode_id': 'other', 'scope': {}, 'assignment': {}, 'role': 'annotation'}
    with pytest.raises(ValueError): run.host.facts(replace(child, **{field: wrong[field]}), fact_form(*FACT_SOURCES))


@pytest.mark.parametrize('target', ['run_id', 'episode_id', 'scope', 'assignment', 'selector'])
def test_publication_owner_and_original_selector_cannot_change(run, target):
    args = example(); child = run.child(run.saved.root, 'results', args[0]); body = run.publications.add(child, args)
    if target == 'selector': body['publication_inputs']['selector']['endpoint'] = 'requested_artifacts'
    elif target in ('scope', 'assignment'): body[target] = {}
    else: body[target] = 'other'
    with pytest.raises(ValueError): run.host.facts(child, fact_form(*FACT_SOURCES))


def test_sibling_unreceived_source_and_generated_identifiers_do_not_grant_possession(run):
    args = example(); child = run.child(run.saved.root, 'results', args[0]); body = run.publications.add(child, args)
    sibling = run.child(run.saved.root, 'scientific_process', args[0], index=1)
    run.admit(run.saved.root, child)
    facts = run.host.received_facts(run.saved.root, fact_form(*FACT_SOURCES))
    field = facts[MEASUREMENTS][0]['field']
    assert run.host.resolve_received(run.saved.root, field, IDENTIFIER_NAMESPACES[0]) is True
    assert run.host.resolve_received(sibling, field, IDENTIFIER_NAMESPACES[0]) is False
    assert run.host.resolve_received(sibling, body['source_ref'], 'execution_result') is None
    assert run.host.resolve_received(run.saved.root, 'made-up', 'foreign_namespace') is None
    with pytest.raises(AppServiceCustodyError, match='input_not_possessed'):
        run.saved.custody.possession(sibling, body['source_ref'])
    assert run.host.resolve_received(run.saved.root, args[1]['data']['parsed_artifacts'][0]['artifact']['source_ref'], 'source') is None


@pytest.mark.parametrize('target', ['number', 'field', 'member_zero', 'member_namespace', 'symbol', 'strand', 'source', 'frozen_form', 'schema', 'parent'])
def test_forged_admitted_and_frozen_returns_are_rejected(run, target):
    args = example(); child = run.child(run.saved.root, 'results', args[0]); run.publications.add(child, args)
    form, schema, key, _ = run.admit(run.saved.root, child)
    altered = deepcopy(form)
    if target == 'number': altered['f0'][0]['value']['value']['value'] = 0
    elif target == 'field': altered['f0'][0]['field'] = contracts.encode_reference('field', args[1]['analysis_id'], 'unrequested')
    elif target == 'member_zero': altered['f4'][0]['value']['value']['member']['index'] = 0
    elif target == 'member_namespace': altered['f1'][0]['value']['value']['member']['namespace'] = 'unknown_namespace'
    elif target == 'symbol': altered['f5'][0]['value']['value']['aligned_symbol'] = '?'
    elif target == 'strand': altered['f5'][0]['value']['value']['native_strand'] = 'unknown'
    elif target == 'source': altered['f0'][0]['source_ref'] = run.saved.source()['source_ref']
    elif target == 'frozen_form':
        run.store.db.execute('UPDATE runtime_forms SET form=? WHERE episode_id=?', (canonical({}), child.episode_id))
    elif target == 'schema':
        schema['properties']['f0']['maxItems'] = 100
    else:
        other = run.child(run.saved.root, 'scientific_process', args[0], index=1)
        with pytest.raises(ValueError): run.host.record_admission(other, form, schema, key)
        return
    if target not in ('frozen_form', 'schema'):
        # A forged matching form/facts/attempt must still fail scientific
        # schema and original saved-value validation, not merely frozen equality.
        facts = {source: altered[f'f{i}'] for i, source in enumerate(FACT_SOURCES)}
        run.store.db.execute('UPDATE runtime_forms SET form=?,facts=? WHERE episode_id=?',
            (canonical(altered), canonical(facts), child.episode_id))
        run.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE child_episode_id=?',
            (canonical(altered), child.episode_id))
    with pytest.raises(ValueError):
        run.host.record_admission(run.saved.root, altered, schema, key)


def test_exact_redelivery_deduplicates_without_new_action_or_observation(run):
    args = example(); child = run.child(run.saved.root, 'results', args[0]); run.publications.add(child, args)
    form, schema, _, _ = run.admit(run.saved.root, child)
    parent = run.saved.root
    attempt = dict(run.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
        'AND parent_episode_id=? AND decision_index=0', (parent.run_id, parent.episode_id)).fetchone())
    selected = {'kind': 'redeliver_report', 'delivery_ref': attempt['delivery_ref'],
        'schema_json': canonical(schema), 'purpose': json.loads(attempt['contract'])['decision']}
    # Authored historical direct-decision frame: the real writer retained its
    # allowed action schema even before compact contract information existed.
    branch = _object({'kind': {'type': 'string', 'const': 'redeliver_report'},
        'delivery_ref': {'type': 'string'}, 'purpose': {'type': 'string'},
        'schema_json': {'type': 'string'}})
    request = {'context': {}, 'schema': _object({'selection': {'anyOf': [branch]},
        'report_update': _object({})})}
    run.saved.journal.save('runtime_model_calls', {'episode_id': parent.episode_id, 'call_index': 1,
        'purpose': 'decision', 'request': canonical(request),
        'response': canonical({'selection': selected, 'report_update': {}})})
    run.saved.journal.save('runtime_report_attempts', {**attempt, 'decision_index': 1})
    values = run.host.received_facts(parent, schema)
    assert values[MEASUREMENTS] == form['f0']
    assert run.saved.journal.row('runtime_actions', parent.episode_id, 1) is None
    assert run.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_no_requested_source_performs_no_provider_lookup(run, monkeypatch):
    monkeypatch.setattr(run.publications, 'outcomes', lambda *a: pytest.fail('unrequested provider lookup'))
    monkeypatch.setattr('gene_annotation_episode.bvbrc_genome_alignment_returns.read_latest_adapter_result',
        lambda *a, **k: pytest.fail('unrequested provider lookup'))
    assert run.host.facts(run.saved.root, {}) == {}
    assert run.host.received_facts(run.saved.root, {}) == {}


def test_failed_report_and_deleted_original_return_supply_no_facts(run):
    args = facade_example(); child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    _, schema, key, _ = run.admit(run.saved.root, child)
    run.store.db.execute('UPDATE runtime_report_attempts SET failure=?', ('{"code":"fixture_failed"}',))
    assert run.host.received_facts(run.saved.root, schema) == {MEASUREMENTS: []}
    with pytest.raises(ValueError, match='successful_return_required'):
        run.host.record_admission(run.saved.root, {}, schema, key)
    run.store.db.execute('DELETE FROM runtime_report_attempts')
    assert run.host.received_facts(run.saved.root, schema) == {MEASUREMENTS: []}


def test_current_validation_checks_frozen_facts_and_unsupported_owner(run):
    args = facade_example(); child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    form, schema = run.candidate(child)
    run.store.db.execute('UPDATE runtime_forms SET facts=? WHERE episode_id=?',
        (canonical({MEASUREMENTS: []}), child.episode_id))
    with pytest.raises(ValueError, match='frozen_facts_conflict'):
        run.host.validate_received_report(child, form, schema)
    unsupported = run.child(run.saved.root, 'monitor', args[0], index=1, sources=(MEASUREMENTS,))
    with pytest.raises(ValueError, match='unsupported_return_owner'):
        run.host.validate_received_report(unsupported, {'f0': []}, schema)


def test_current_corrupt_content_never_falls_back_and_historical_bytes_remain_checked(run):
    args = facade_example(); child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    _, schema, _, _ = run.admit(run.saved.root, child)
    newest = run.publications.add(child, args, index=10)
    binding = newest['publication']['adapter_result']['components_content']
    path = run.store.path / 'artifacts' / binding['sha256'][:2] / binding['sha256']
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='artifact_digest_mismatch'):
        run.host.facts(child, schema)
    # Both publications share identical content-addressed saved components.
    with pytest.raises(ValueError, match='artifact_digest_mismatch'):
        run.host.received_facts(run.saved.root, schema)


@pytest.mark.parametrize('boundary', ['pure', 'own', 'received'])
def test_strict_saved_return_never_recomputes_native_arithmetic(run, monkeypatch, boundary):
    """Root owns the shared D/native repair; this barrier must not be relaxed."""
    args = example({'identity': all_fields()['identity']})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    _, schema, _, _ = run.admit(run.saved.root, child)
    forbid_science(monkeypatch)
    def forbidden(*a, **k):
        raise AssertionError('saved return recomputed scientific arithmetic')
    for name in ('mauve_v4_calculation_contracts', 'mauve_backbone_contracts', 'xmfa_calculation_contracts'):
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attr in ('union_intervals', 'interval_length', 'multiplicity_bases', 'complement_intervals'):
            if hasattr(module, attr): monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr('math.log2', forbidden)
    if boundary == 'pure':
        values = project(args, (MEASUREMENTS,))
    elif boundary == 'own':
        values = run.host.facts(child, schema)
    else:
        values = run.host.received_facts(run.saved.root, schema)
    assert values[MEASUREMENTS][0]['value']['value']['value'] == 40 / 48


@pytest.mark.parametrize('possessed', [False, True, 'artifact'])
def test_requirement_source_must_be_actual_possessed_store_source(run, possessed):
    from gene_annotation_episode.bvbrc_genome_alignment_calculators import calculate_genome_alignment_components
    from gene_annotation_episode.bvbrc_genome_alignment_sheet import build_genome_alignment_sheet
    binding = run.saved.source()
    data = fixture_data()
    required_ref = binding['artifact_ref'] if possessed == 'artifact' else binding['source_ref']
    requirement = {'requirement_id': 'explicit_requirement', 'kind': 'scientific_metadata', 'role': None,
        'source_refs': [required_ref], 'reason_code': 'explicit_metadata_missing'}
    data['requirements'].append(requirement)
    components = calculate_genome_alignment_components(data, calculation_plan=plan(all_requests()))
    args = example(sheet=build_genome_alignment_sheet(data=data, components=components))
    child = run.child(run.saved.root, 'results', args[0])
    run.publications.add(child, args)
    if possessed == 'artifact':
        run.saved.own(child, required_ref, index=1)
        with pytest.raises(ValueError, match='requirement_source_required'):
            run.host.facts(child, fact_form(*FACT_SOURCES))
    elif possessed:
        run.saved.own(child, binding['source_ref'], index=1)
        _, _, _, refs = run.admit(run.saved.root, child)
        assert binding['source_ref'] in refs
        assert run.host.resolve_received(run.saved.root, binding['source_ref'], 'source') is True
    else:
        with pytest.raises(AppServiceCustodyError, match='input_not_possessed'):
            run.host.facts(child, fact_form(*FACT_SOURCES))


def test_distinct_original_publications_remain_distinct_in_received_values(run):
    args = facade_example()
    children = [run.child(run.saved.root, 'results', args[0], index=i, sources=(MEASUREMENTS,)) for i in range(2)]
    refs = []
    for child in children:
        refs.append(run.publications.add(child, args)['source_ref'])
        run.admit(run.saved.root, child)
    values = run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))[MEASUREMENTS]
    assert [r['source_ref'] for r in values] == refs
    assert [r['value']['value']['value'] for r in values] == [690, 690]
    assert len(set(refs)) == 2


def test_original_immediate_child_cannot_be_replaced_by_sibling(run):
    args = facade_example()
    first = run.child(run.saved.root, 'results', args[0], index=0, sources=(MEASUREMENTS,))
    second = run.child(run.saved.root, 'results', args[0], index=1, sources=(MEASUREMENTS,))
    run.publications.add(first, args); run.publications.add(second, args)
    run.admit(run.saved.root, first); run.candidate(second)
    run.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE decision_index=0', (second.episode_id,))
    with pytest.raises(ValueError): run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))
