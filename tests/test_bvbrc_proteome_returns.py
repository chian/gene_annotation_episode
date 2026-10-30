"""Real provider outputs through Store/Journal and the typed return boundary.

Inputs are retained synthetic native-format bytes. ControlledPublications is an
explicit test publication envelope, not an AppService transport or full Workflow.
The parsers, input/joins/sheet constructors, calculators, custody and typed
communication classes are real; no live GenomeComparison service is claimed.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_proteome_fact_contracts as facts
from gene_annotation_episode.bvbrc_proteome_returns import (
    BVBRCProteomeReturns, FACT_SOURCES as ALL_FACT_SOURCES, IDENTIFIER_NAMESPACES, ProteomeReturnError,
    proteome_fact_sources, requested_sources, project_proteome_facts, _report_node,
)
from gene_annotation_episode.bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.communication import plain, form_with_facts, validate_closed_schema, validate_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import TypedReportContract, _object
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords, selector as base_selector, refs_schema
from test_bvbrc_proteome_bundle_resolution import fixture as provider_arguments
from test_bvbrc_proteome_bundle_projection import selected_fields, MEAN


# This retained fixture exercises the eight original v1 fact families. The
# production descriptor catalog additionally supplies the fourteen v2 families.
FACT_SOURCES = (
    'bvbrc_proteome_measurements', 'bvbrc_proteome_ratios', 'bvbrc_proteome_populations',
    'bvbrc_proteome_associations', 'bvbrc_proteome_selections', 'bvbrc_proteome_requirements',
    'bvbrc_proteome_qualifications', 'bvbrc_proteome_request_status')
MEASUREMENTS, RATIOS, POPULATIONS, ASSOCIATIONS, SELECTIONS, REQUIREMENTS, QUALIFICATIONS, STATUS = FACT_SOURCES
PIN = adapter.implementation_sha256()


def fact_form(*sources):
    descriptors = proteome_fact_sources()
    properties = {f'f{i}': descriptors[source]['report_schema'] for i, source in enumerate(sources)}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def content(value, name):
    raw = canonical(value).encode('utf-8')
    return {'source_ref': 'source_' + digest([name, value])[:24], 'artifact_field': 'artifact_ref',
        'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(),
        'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def retained_arguments(saved=None):
    """Rebind explicitly synthetic transport IDs before running real providers."""
    case = provider_arguments()
    if saved is None:
        return case
    by_artifact = {}
    sources, artifacts = {}, {}
    for ref, raw in case['artifact_bytes'].items():
        binding = saved.source(raw, accession='retained_' + ref)
        by_artifact[ref] = binding
        artifacts[ref] = binding['artifact_ref']

    def find(value):
        if type(value) is dict:
            artifact = value.get('artifact_ref', value.get('raw_artifact_ref'))
            if artifact in by_artifact and 'source_ref' in value:
                sources[value['source_ref']] = by_artifact[artifact]['source_ref']
            for child in value.values():
                find(child)
        elif type(value) is list:
            for child in value:
                find(child)
    find(case)

    def remap(value, key=None):
        if type(value) is dict:
            return {name: remap(child, name) for name, child in value.items()}
        if type(value) is list:
            return [remap(child, key) for child in value]
        if type(value) is str:
            if key in {'source_ref', 'submission_source_ref', 'primary_source_ref'}:
                return sources.get(value, value)
            if key in {'artifact_ref', 'raw_artifact_ref'}:
                return artifacts.get(value, value)
        return value
    case = remap(case)
    case['artifact_bytes'] = {artifacts[ref]: raw for ref, raw in case['artifact_bytes'].items()}
    # The SuppliedData JSON itself changed when its source operands changed.
    row = case['supplied_values'][0]
    row['evidence'] = {'content': saved.source(canonical(row['value']).encode(), accession='supplied_data'), 'pointer': ''}
    case['parameters']['supplied_data_evidence'] = deepcopy(row['evidence'])
    case['bundle']['supplied_scientific_metadata'] = [deepcopy(row['evidence']) for row in case['supplied_values']]
    return case


def example(fields=None, *, saved=None, change=None):
    case = retained_arguments(saved)
    case['requested_form'] = facts.requested_form_schema(selected_fields() if fields is None else fields)
    if change is not None:
        change(case)
    selector = base_selector()
    selector.update(endpoint='requested_projection', adapter={'adapter_id': 'bvbrc_proteome',
        'adapter_version': '1', 'parameters': deepcopy(case['parameters'])}, requested_schema=deepcopy(case['requested_form']),
        supplied_metadata=deepcopy(case['bundle']['supplied_scientific_metadata']),
        supplied_contents=deepcopy(case['bundle']['supplied_contents']))
    selector['requirements'][0].update(role='proteome_native_projection',
        declared_format=deepcopy(case['parameters']['native_documents'][0]['declared_format']))
    case['bundle']['requested_selector_sha256'] = digest(selector)
    result = adapter.consume_bundle(**case)
    bundle_content = content(case['bundle'], 'bundle')
    saved_result = {key: deepcopy(result[key]) for key in
        ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
    for name in ('sheet', 'components'):
        saved_result[name + '_content'] = None if result[name] is None else content(result[name], name)
    reference = bundle_content['source_ref']
    body = {'version': RESULT_VERSION, 'reference': reference, 'source_ref': reference, 'record_refs': [reference],
        'assignment': {'selector': deepcopy(selector)}, 'bundle': deepcopy(case['bundle']),
        'publication_inputs': {'selector': selector, 'adapter': deepcopy(selector['adapter']),
            'adapter_implementation_sha256': PIN},
        'publication': {'bundle_content': bundle_content, 'result_record_refs': [reference], 'adapter_result': saved_result}}
    return body, result['sheet'], result['components']


def project(args, sources=FACT_SOURCES):
    return project_proteome_facts(args[0], requested_sources=sources, sheet=args[1], components=args[2])


def rebind(args):
    body, sheet, components = args
    for name, value in (('sheet', sheet), ('components', components)):
        body['publication']['adapter_result'][name + '_content'] = None if value is None else content(value, name)


def forbid_science(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved return invoked scientific work, acquisition or execution')
    functions = {
        'bvbrc_proteome_bundle_adapter': ['consume_bundle', 'implementation_sha256'],
        'bvbrc_proteome_bundle_resolution': ['consume_bundle', 'parse_genome_comparison', 'index_original_inputs',
            'read_protein_fasta', 'read_feature_metadata', 'read_genome_metadata', 'read_feature_sequences',
            'build_native_joins', 'build_native_sheet', 'calculate_native_components'],
        'bvbrc_proteome_native': ['parse_genome_comparison'],
        'bvbrc_proteome_inputs': ['index_original_inputs', 'read_protein_fasta', 'read_feature_metadata',
            'read_genome_metadata', 'read_feature_sequences'],
        'bvbrc_proteome_joins': ['build_native_joins'],
        'bvbrc_proteome_sheet': ['build_native_sheet'],
        'bvbrc_proteome_calculators': ['calculate_native_components'],
    }
    for name, attrs in functions.items():
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attr in attrs:
            monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)


class ControlledPublications:
    """Controlled publication only; authentic retained Store bytes and custody."""
    def __init__(self, saved):
        self.saved, self.bodies, self.contents, self.reads = saved, {}, {}, []
        self.host = SimpleNamespace(custody=saved.custody)
        self.api = SimpleNamespace(_own_outcomes=self.outcomes)

    def add(self, context, args, index=0, *, native_custody=True):
        body, sheet, components = deepcopy(args)
        refs = []
        for name, value in (('sheet', sheet), ('components', components)):
            binding = None if value is None else self.saved.source(canonical(value).encode(), provider=DATA_PROVIDER,
                accession=f'{context.episode_id}:{index}:{name}')
            body['publication']['adapter_result'][name + '_content'] = binding
            if binding is not None:
                self.contents[binding['source_ref']] = binding
                refs.append(binding['source_ref'])
        binding = self.saved.source(canonical(body['bundle']).encode(), provider=DATA_PROVIDER,
            accession=f'{context.episode_id}:{index}:bundle')
        reference = binding['source_ref']
        body.update(reference=reference, source_ref=reference, record_refs=[reference], run_id=context.run_id,
            episode_id=context.episode_id, scope=plain(context.scope), assignment=plain(context.assignment))
        body['publication'].update(bundle_content=binding, result_record_refs=[reference], origin={
            'operation_key': f'{context.run_id}:{context.episode_id}:{index}'})
        body['publication_inputs']['current_snapshot'] = {'retrieved_at': 'synthetic:' + str(index)}
        self.bodies[reference] = body
        if native_custody:
            refs.extend(item['source_ref'] for item in body['bundle']['artifacts'])
            refs.extend(item['source_ref'] for item in body['bundle']['supplied_contents'])
            refs.extend(item['content']['source_ref'] for item in body['bundle']['supplied_scientific_metadata'])
        result = self.saved.own(context, reference, index, tool='api.bvbrc_appservice.download')
        result['record_refs'] = result['changed_record_refs'] = list(dict.fromkeys([reference, *refs]))
        self.saved.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': 'api.bvbrc_appservice.download', 'arguments': {}}),
            'result': canonical(result), 'credit': None})
        return body

    def outcomes(self, context):
        rows = self.saved.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND result IS NOT NULL ORDER BY decision_index', (context.run_id, context.episode_id))
        for row in rows:
            result = json.loads(row['result'])
            if result['status'] in {'completed', 'partial'}:
                if result['result'].get('publication_ref') is not None:
                    yield None, result
                    continue
                refs = [ref for ref in result['record_refs'] if ref in self.bodies]
                if refs:
                    yield None, {'result': {'result_record_refs': refs}}
                else:
                    yield None, result

    def read(self, reference, scope, *, episode_id=None):
        self.reads.append(reference)
        if reference not in self.bodies:
            raise ValueError('controlled_publication_missing')
        body = deepcopy(self.bodies[reference])
        context = self.saved.custody.context(body['episode_id'])
        if episode_id is not None and context.episode_id != episode_id:
            raise ValueError('controlled_publication_wrong_owner')
        self.saved.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        raw = self.saved.custody.content(context, body['publication']['bundle_content'])
        if raw != canonical(body['bundle']).encode():
            raise ValueError('controlled_publication_bundle_bytes_conflict')
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
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id, configuration={},
            appservice=SimpleNamespace(publications=self.publications, custody=self.saved.custody))
        self.host = BVBRCProteomeReturns(self.api)

    def example(self, fields=None, **kwargs):
        args = example(fields, saved=self.saved, **kwargs)
        self.api.configuration[args[0]['bundle']['original_task']['resource_id']] = {'scientific_adapters': [
            {'adapter_id': 'bvbrc_proteome', 'adapter_version': '1', 'implementation_sha256': PIN}]}
        return args

    def child(self, parent, role, body, *, index=0, sources=FACT_SOURCES, schema=None):
        assignment = {} if role != 'results' else {'version': 'execution_results_assignment_v1',
            'handoff_ref': 'source_' + 'a' * 24, 'selector': body['publication_inputs']['selector']}
        return self.saved.child(parent, role, assignment, index, schema=fact_form(*sources) if schema is None else schema)

    def candidate(self, child):
        schema = plain(child.request)['report_contract']['measurements']['schema']
        values = self.host.facts(child, schema) if child.role == 'results' else self.host.received_facts(child, schema)
        form = form_with_facts({}, schema, values)
        self.saved.journal.save('runtime_forms', {'episode_id': child.episode_id,
            'facts': canonical(values), 'form': canonical(form)})
        return form, schema

    def admit(self, parent, child):
        form, schema = self.candidate(child)
        contract = plain(child.request)['report_contract']
        values = {node['x-source']: form[name] for name, node in schema['properties'].items()}
        # One authenticated snapshot supplies reference traversal in this isolated
        # boundary. Public resolvers are separately tested; host hooks are pending.
        self.host._possessed_sources(child, values)
        typed = TypedReportContract(contract['decision'], schema,
            lambda reference, namespace: self.host._has_reference(values, reference, namespace),
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


def test_eight_exact_families_and_explicit_closed_semantic_namespaces():
    descriptors = proteome_fact_sources()
    assert FACT_SOURCES == (
        'bvbrc_proteome_measurements', 'bvbrc_proteome_ratios', 'bvbrc_proteome_populations',
        'bvbrc_proteome_associations', 'bvbrc_proteome_selections', 'bvbrc_proteome_requirements',
        'bvbrc_proteome_qualifications', 'bvbrc_proteome_request_status')
    assert tuple(descriptors) == ALL_FACT_SOURCES == FACT_SOURCES + tuple(
        'bvbrc_proteome_' + suffix for suffix in (
            'directional_counts', 'directional_fractions', 'directional_coverages',
            'directional_native_integers', 'directional_native_decimals', 'directional_states',
            'directional_extrema', 'directional_intervals', 'directional_columns',
            'directional_edges', 'directional_conflicts', 'directional_support',
            'directional_issues', 'directional_requirements'))
    assert set(IDENTIFIER_NAMESPACES) == {'bvbrc_proteome_' + kind for kind in (
        *facts.REFERENCE_KINDS, 'track', 'association', 'inventory', 'native_identifier', 'protein', 'report',
        'requested_field', 'native_category', 'document')}
    schema = fact_form(*FACT_SOURCES)
    assert validate_closed_schema(schema) == schema
    assert requested_sources(fact_form(STATUS, MEASUREMENTS, STATUS)) == (STATUS, MEASUREMENTS)
    assert BVBRCProteomeReturns.fact_sources() == descriptors
    for descriptor in descriptors.values():
        assert descriptor['report_schema']['items']['properties']['source_ref']['x-reference-namespace'] == 'execution_result'
    descriptors[MEASUREMENTS]['report_schema']['items']['properties'].clear()
    assert proteome_fact_sources()[MEASUREMENTS]['report_schema']['items']['properties']


def test_actual_provider_eight_families_mean_zero_missing_and_native_associations():
    args = example()
    before = deepcopy(args)
    values = project(args)
    assert all(values.values())
    cells = {facts.decode_reference(row['field'])[2]: row['value'] for row in values[MEASUREMENTS]}
    assert cells['/facts/mean']['cell']['value'] == .4375
    assert cells['/facts/mean']['unit'] == 'fraction'
    assert cells['/facts/zero']['cell']['value'] == 0 and cells['/facts/zero']['availability'] == 'available'
    assert cells['/facts/denominator']['cell']['value'] is None and cells['/facts/denominator']['availability'] == 'unavailable'
    ratio = values[RATIOS][0]['value']
    assert ratio['denominator']['value'] is ratio['fraction']['value'] is None
    assert values[POPULATIONS][0]['value']['association_keys'] == ['comp_genome_2/row/0', 'comp_genome_2/row/1']
    association = values[ASSOCIATIONS][0]['value']
    assert (association['reference_identifier'], association['subject_identifier'], association['native_category']) == ('r1', 's1', 'bi (<->)')
    assert association['reference_join_ref'] and association['subject_join_ref']
    assert values[SELECTIONS][0]['value']['selection'] == 'pass'
    assert values[STATUS][0]['value']['state'] == 'unavailable'
    schema = fact_form(*FACT_SOURCES)
    validate_form(form_with_facts({}, schema, values), schema, lambda *_: True)
    values[MEASUREMENTS][0]['value']['cell']['value'] = 99
    assert args == before


@pytest.mark.parametrize('field', ['mean', 'first/second', 'tilde~slash/', 'field with spaces', '研究'])
def test_original_requested_field_pointer_is_rfc6901_escaped(field):
    args = example({field: MEAN})
    row, = project(args, (MEASUREMENTS,))[MEASUREMENTS]
    kind, analysis, pointer = facts.decode_reference(row['field'])
    assert (kind, analysis, pointer) == ('field', args[1]['analysis_id'], '/facts/' + field.replace('~', '~0').replace('/', '~1'))
    assert row['value'] == args[0]['publication']['adapter_result']['facts'][field]


@pytest.mark.parametrize('schema', [
    {'oneOf': [{'type': 'number'}, {'type': 'null'}]}, {'type': 'string'},
    {'anyOf': [{'type': 'number'}, {'type': 'integer'}]},
    {'type': 'string', 'pattern': '.*'},
])
def test_unreviewed_schema_unions_and_free_strings_are_rejected(schema):
    with pytest.raises(ProteomeReturnError, match='fact_schema_unsupported'):
        _report_node(schema)


@pytest.mark.parametrize('sources', [[], (MEASUREMENTS, MEASUREMENTS), ('unknown',), None, {MEASUREMENTS}])
def test_requested_source_selection_is_finite_unique_tuple(sources):
    with pytest.raises(ProteomeReturnError, match='requested_sources_invalid'):
        project_proteome_facts({}, requested_sources=sources, sheet=None, components=None)


def test_no_requested_fields_do_not_read_any_publication(run, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('unrequested publication lookup')
    monkeypatch.setattr('gene_annotation_episode.bvbrc_proteome_returns.read_latest_adapter_result', forbidden)
    assert project_proteome_facts(None, requested_sources=(), sheet=None, components=None) == {}
    assert run.host.facts(run.saved.root, {}) == run.host.received_facts(run.saved.root, {}) == {}


@pytest.mark.parametrize('target', [
    'source', 'reference', 'result_refs', 'record_refs', 'adapter', 'version', 'selected_version',
    'input_adapter', 'pin', 'assignment', 'selector_hash', 'selector', 'schema', 'task', 'application',
    'analysis', 'numeric', 'extra_fact', 'missing_fact', 'sheet_hash', 'component_count', 'component_bytes',
    'sheet_binding', 'components_binding', 'status', 'bundle_hash', 'bundle_count', 'component_sheet_hash',
    'component_parameters', 'native_category', 'cell_state', 'nan',
])
def test_saved_integrity_and_original_relationship_corruption_rejected(target):
    args = list(example())
    body, sheet, components = args
    saved = body['publication']['adapter_result']
    selector = body['publication_inputs']['selector']
    if target == 'source': body['source_ref'] = 'artifact_' + 'a' * 64
    elif target == 'reference': body['reference'] = 'source_' + 'b' * 24
    elif target == 'result_refs': body['publication']['result_record_refs'] = []
    elif target == 'record_refs': body['record_refs'] = []
    elif target == 'adapter': saved['adapter_id'] = 'bvbrc_msa'
    elif target == 'version': saved['adapter_version'] = '2'
    elif target == 'selected_version': selector['adapter']['adapter_version'] = '2'
    elif target == 'input_adapter': body['publication_inputs']['adapter']['parameters']['analysis_id'] = 'replacement'
    elif target == 'pin': body['publication_inputs']['adapter_implementation_sha256'] = 'A' * 64
    elif target == 'assignment': body['assignment']['selector']['endpoint'] = 'requested_artifacts'
    elif target == 'selector_hash': body['bundle']['requested_selector_sha256'] = '0' * 64
    elif target == 'selector': selector['requested_schema']['properties']['mean']['x-bvbrc-proteome']['metric'] = 'sum'
    elif target == 'schema': selector['requested_schema']['properties']['mean']['additionalProperties'] = True
    elif target == 'task': body['bundle']['original_task']['task_id'] = 'other-task'
    elif target == 'application': body['bundle']['original_task'].update(required_application_id='MSA', native_application_id='MSA')
    elif target == 'analysis': sheet['analysis_id'] = 'replacement'; rebind(args)
    elif target == 'numeric': saved['facts']['mean']['cell']['value'] = .9
    elif target == 'extra_fact': saved['facts']['extra'] = deepcopy(saved['facts']['mean'])
    elif target == 'missing_fact': del saved['facts']['mean']
    elif target == 'sheet_hash': saved['sheet_content']['sha256'] = '0' * 64
    elif target == 'component_count': saved['components_content']['byte_count'] += 1
    elif target == 'component_bytes': components['value']['sheet_sha256'] = '0' * 64
    elif target == 'sheet_binding': args[1] = None
    elif target == 'components_binding': args[2] = None
    elif target == 'status': saved['status'] = 'ok'
    elif target == 'bundle_hash': body['publication']['bundle_content']['sha256'] = '0' * 64
    elif target == 'bundle_count': body['publication']['bundle_content']['byte_count'] += 1
    elif target == 'component_sheet_hash': components['value']['sheet_sha256'] = '0' * 64; rebind(args)
    elif target == 'component_parameters': components['value']['parameters']['minimum_identity_fraction'] = .9; rebind(args)
    elif target == 'native_category': saved['facts']['association']['native_category'] = 'fabricated category'
    elif target == 'cell_state': saved['facts']['mean']['cell']['state'] = 'missing_input'
    elif target == 'nan': saved['facts']['mean']['cell']['value'] = float('nan')
    if target in {'selector', 'schema'}:
        body['assignment']['selector'] = deepcopy(selector)
        body['bundle']['requested_selector_sha256'] = digest(selector)
    if target in {'selector', 'schema', 'selector_hash', 'task', 'application'}:
        old_ref = body['source_ref']
        body['publication']['bundle_content'] = {**content(body['bundle'], 'bundle'), 'source_ref': old_ref}
    with pytest.raises(ValueError):
        project(args)


def test_saved_projection_only_copies_values_with_science_network_and_file_reads_forbidden(monkeypatch):
    args = example()
    expected = project(args)
    forbid_science(monkeypatch)
    monkeypatch.setattr('builtins.open', lambda *args, **kwargs: pytest.fail('file read in pure return'))
    assert project(args) == expected


def test_real_recorded_custody_forwarding_and_zero_synthetic_observations(run, monkeypatch):
    args = run.example()
    parent = run.child(run.saved.root, 'scientific_process', args[0])
    child = run.child(parent, 'results', args[0])
    published = run.publications.add(child, args)
    forbid_science(monkeypatch)
    count = run.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
    form, schema, key, references = run.admit(parent, child)
    assert published['source_ref'] in references
    assert args[0]['bundle']['artifacts'][0]['source_ref'] in references
    received = run.host.received_facts(parent, schema)
    assert received[MEASUREMENTS][0]['value']['cell']['value'] == .4375
    assert run.host.record_admission(parent, form, schema, key) == references
    run.admit(run.saved.root, parent)
    assert run.host.received_facts(run.saved.root, schema) == received
    assert run.saved.custody.possession(run.saved.root, published['source_ref']) == 'admitted_return'
    assert run.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == count
    assert run.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('target', ['run_id', 'episode_id', 'scope', 'assignment', 'role'])
def test_wrong_own_context_rejected(run, target):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    values = dict(run_id='other', episode_id='other', scope={}, assignment={}, role='annotation')
    with pytest.raises(ValueError):
        run.host.facts(replace(child, **{target: values[target]}), fact_form(MEASUREMENTS))


@pytest.mark.parametrize('target', ['run_id', 'episode_id', 'scope', 'assignment', 'selector', 'pin', 'configuration'])
def test_original_publication_owner_selection_and_configured_pin_cannot_change(run, target):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    body = run.publications.add(child, args)
    if target == 'selector': body['publication_inputs']['selector']['endpoint'] = 'requested_artifacts'
    elif target in {'scope', 'assignment'}: body[target] = {}
    elif target == 'pin': body['publication_inputs']['adapter_implementation_sha256'] = 'f' * 64
    elif target == 'configuration': run.api.configuration = {}
    else: body[target] = 'other'
    with pytest.raises(ValueError):
        run.host.facts(child, fact_form(MEASUREMENTS))


def test_latest_partial_supersedes_prior_success_without_fallback(run):
    good = run.example({'mean': MEAN})
    bad = run.example({'mean': MEAN}, change=lambda case: case['artifact_bytes'].clear())
    child = run.child(run.saved.root, 'results', good[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, good, index=2)
    latest = run.publications.add(child, bad, index=11)
    values = run.host.facts(child, fact_form(MEASUREMENTS))
    assert values[MEASUREMENTS][0]['value']['cell']['value'] is None
    assert values[MEASUREMENTS][0]['value']['availability'] == 'unavailable'
    assert values[MEASUREMENTS][0]['source_ref'] == latest['source_ref']
    assert run.publications.reads == [latest['source_ref']] and first['source_ref'] not in run.publications.reads


def test_empty_invalid_publication_does_not_return_old_success(run):
    good = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', good[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, good)
    bad = deepcopy(good[0])
    bad['publication']['adapter_result'].update(status='invalid', facts={})
    latest = run.publications.add(child, (bad, None, None), index=10)
    assert run.host.facts(child, fact_form(MEASUREMENTS)) == {MEASUREMENTS: []}
    assert run.publications.reads == [latest['source_ref']] and first['source_ref'] not in run.publications.reads


def test_newest_publication_without_usable_result_reference_never_revives_older_success(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, args)
    # An authentic own action, carrying an explicitly controlled empty
    # publication envelope. It contains no purported numerical result source.
    partial = run.saved.source(canonical({'controlled_publication': 'no_usable_artifact'}).encode())['source_ref']
    outcome = run.saved.own(child, partial, index=10, status='partial', tool='api.bvbrc_appservice.download')
    outcome['result'] = {'publication_ref': partial, 'result_record_refs': []}
    run.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=10',
        (canonical(outcome), child.episode_id))
    assert run.host.facts(child, fact_form(MEASUREMENTS)) == {MEASUREMENTS: []}
    assert first['source_ref'] not in run.publications.reads


@pytest.mark.parametrize('adapter_id,version,guarded', [
    ('bvbrc_proteome', '1', True), ('bvbrc_proteome', '2', True),
    ('bvbrc_proteome', '3', False), ('unrelated_adapter', '1', False),
])
def test_empty_publication_guard_is_limited_to_exact_selected_results_adapter(run, monkeypatch, adapter_id, version, guarded):
    args = run.example({'mean': MEAN})
    body = deepcopy(args[0])
    body['publication_inputs']['selector']['adapter'].update(adapter_id=adapter_id, adapter_version=version)
    child = run.child(run.saved.root, 'results', body, sources=(MEASUREMENTS,))
    partial = run.saved.source(canonical({'controlled_publication': 'no_usable_artifact'}).encode())['source_ref']
    outcome = run.saved.own(child, partial, index=10, status='partial', tool='api.bvbrc_appservice.download')
    outcome['result'] = {'publication_ref': partial, 'result_record_refs': []}
    run.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=10',
        (canonical(outcome), child.episode_id))
    module = importlib.import_module('gene_annotation_episode.bvbrc_proteome_returns')
    actual, calls = module.read_latest_adapter_result, []
    def read(*args, **kwargs):
        calls.append(kwargs['adapter_ids'])
        return actual(*args, **kwargs)
    monkeypatch.setattr(module, 'read_latest_adapter_result', read)
    assert run.host.facts(child, fact_form(MEASUREMENTS)) == {MEASUREMENTS: []}
    assert calls == ([] if guarded else [('bvbrc_proteome',)])


def test_newer_unrelated_operation_does_not_supersede_published_science(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, args)
    unrelated = run.saved.source(b'{"controlled_status":"running"}')['source_ref']
    run.saved.own(child, unrelated, index=10, tool='api.bvbrc_appservice.status')
    rows = run.host.facts(child, fact_form(MEASUREMENTS))[MEASUREMENTS]
    assert rows[0]['source_ref'] == first['source_ref'] and rows[0]['value']['cell']['value'] == .4375


def test_historical_admission_uses_named_original_despite_later_partial(run, monkeypatch):
    good = run.example({'mean': MEAN})
    bad = run.example({'mean': MEAN}, change=lambda case: case['artifact_bytes'].clear())
    child = run.child(run.saved.root, 'results', good[0], sources=(MEASUREMENTS,))
    first = run.publications.add(child, good)
    form, schema, key, _ = run.admit(run.saved.root, child)
    latest = run.publications.add(child, bad, index=10)
    forbid_science(monkeypatch)
    run.publications.reads.clear()
    assert run.host.received_facts(run.saved.root, schema)[MEASUREMENTS] == form['f0']
    assert first['source_ref'] in run.publications.reads and latest['source_ref'] not in run.publications.reads
    assert run.host.record_admission(run.saved.root, form, schema, key) == [first['source_ref']]
    assert run.host.facts(child, schema)[MEASUREMENTS][0]['source_ref'] == latest['source_ref']


@pytest.mark.parametrize('boundary', ['pure', 'own', 'received'])
def test_forbidden_reexecution_at_each_return_boundary(run, monkeypatch, boundary):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    _, schema, _, _ = run.admit(run.saved.root, child)
    forbid_science(monkeypatch)
    values = project(args, (MEASUREMENTS,)) if boundary == 'pure' else (
        run.host.facts(child, schema) if boundary == 'own' else run.host.received_facts(run.saved.root, schema))
    assert values[MEASUREMENTS][0]['value']['cell']['value'] == .4375


@pytest.mark.parametrize('native_custody', [True, False])
def test_native_source_references_require_actual_possession(run, native_custody):
    args = run.example({'population': {'kind': 'population', 'target': 'track', 'track_key': 'comp_genome_2'}})
    child = run.child(run.saved.root, 'results', args[0], sources=(POPULATIONS,))
    run.publications.add(child, args, native_custody=native_custody)
    native = args[0]['bundle']['artifacts'][0]['source_ref']
    if not native_custody:
        with pytest.raises(AppServiceCustodyError, match='input_not_possessed'):
            run.host.facts(child, fact_form(POPULATIONS))
        return
    _, _, _, references = run.admit(run.saved.root, child)
    assert native in references and run.host.resolve_received(run.saved.root, native, 'source') is True


def test_source_only_return_grants_no_measurements(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], schema=refs_schema('execution_result'))
    body = run.publications.add(child, args)
    run.saved.admit(run.saved.root, child, body['source_ref'])
    assert run.saved.custody.possession(run.saved.root, body['source_ref']) == 'admitted_return'
    assert run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS)) == {MEASUREMENTS: []}
    field = project(args, (MEASUREMENTS,))[MEASUREMENTS][0]['field']
    assert run.host.resolve_received(run.saved.root, field, 'bvbrc_proteome_field') is False


def test_sibling_and_unadmitted_descendant_cannot_forward_scientific_fields(run):
    args = run.example({'mean': MEAN})
    parent = run.child(run.saved.root, 'scientific_process', args[0], sources=(MEASUREMENTS,))
    child = run.child(parent, 'results', args[0], sources=(MEASUREMENTS,))
    sibling = run.child(run.saved.root, 'scientific_process', args[0], index=1, sources=(MEASUREMENTS,))
    body = run.publications.add(child, args)
    run.admit(parent, child)
    values = run.host.received_facts(parent, fact_form(MEASUREMENTS))
    field = values[MEASUREMENTS][0]['field']
    assert run.host.resolve_received(parent, field, 'bvbrc_proteome_field') is True
    assert run.host.resolve_received(sibling, field, 'bvbrc_proteome_field') is False
    assert run.host.resolve_received(run.saved.root, field, 'bvbrc_proteome_field') is False
    assert run.host.resolve_received(sibling, body['source_ref'], 'execution_result') is None
    assert run.host.resolve_received(parent, 'made_up', 'unrelated') is None
    with pytest.raises(ValueError):
        run.host.validate_received_report(sibling, {'f0': values[MEASUREMENTS]}, fact_form(MEASUREMENTS))


def test_exact_redelivery_deduplicates_without_observation(run):
    args = run.example({'mean': MEAN})
    parent = run.saved.root
    child = run.child(parent, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    form, schema, _, _ = run.admit(parent, child)
    attempt = dict(run.store.db.execute('SELECT * FROM runtime_report_attempts WHERE parent_episode_id=?',
        (parent.episode_id,)).fetchone())
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
    assert run.host.received_facts(parent, schema)[MEASUREMENTS] == form['f0']
    assert run.saved.journal.row('runtime_actions', parent.episode_id, 1) is None
    assert run.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
    altered = deepcopy(form)
    altered['f0'][0]['value']['cell']['value'] = .9
    run.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE decision_index=1', (canonical(altered),))
    with pytest.raises(ValueError):
        run.host.received_facts(parent, schema)


def test_named_original_bytes_and_latest_corruption_are_still_validated(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    _, schema, _, _ = run.admit(run.saved.root, child)
    latest = run.publications.add(child, args, index=10)
    binding = latest['publication']['adapter_result']['components_content']
    path = run.store.path / 'artifacts' / binding['sha256'][:2] / binding['sha256']
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='artifact_digest_mismatch'):
        run.host.facts(child, schema)
    with pytest.raises(ValueError, match='artifact_digest_mismatch'):
        run.host.received_facts(run.saved.root, schema)


def test_failed_or_missing_admission_has_no_received_facts(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    _, schema, key, _ = run.admit(run.saved.root, child)
    run.store.db.execute('UPDATE runtime_report_attempts SET failure=?', ('{"code":"controlled_failure"}',))
    assert run.host.received_facts(run.saved.root, schema) == {MEASUREMENTS: []}
    with pytest.raises(ValueError):
        run.host.record_admission(run.saved.root, {}, schema, key)
    run.store.db.execute('DELETE FROM runtime_report_attempts')
    assert run.host.received_facts(run.saved.root, schema) == {MEASUREMENTS: []}
