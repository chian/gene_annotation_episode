"""Real Store/runtime/form authentication with an explicit results-port fixture.

The input sheets/calculations and native artifact bytes were retained by earlier
native runs. This suite selects them using the real pure projector, then supplies
an explicit completed-results port. It does not claim production acquisition or
Workflow dispatch, which root verifies separately, and starts no native program.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.infernal_preparation_result_views import (
    preparation_fact_sources, project_preparation_result,
)
from gene_annotation_episode.native_infernal_preparation_returns import (
    FACT_SOURCES, REFERENCE_SOURCE, NativeInfernalPreparationReturns, requested_sources,
)
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / 'verification'
ROWS, ARTIFACTS, POPULATION, FAILURES = FACT_SOURCES
GENERIC = 'execution_result_refs'
COMPLETE = 'execution_completed'
PREFIX = 'native_infernal_preparation_return_'
EMISSION = VERIFY / 'tool_graders_infernal_preparation_emission_2026-10-26_250/examples'
MODELS = VERIFY / 'tool_graders_infernal_preparation_models_2026-10-26_248/examples'
BOUNDARIES = VERIFY / 'tool_graders_infernal_preparation_boundaries_2026-10-26_246/native'
PRESSED = VERIFY / 'tool_graders_infernal_search_2026-10-26_219/native/cmpress'


def schema_for(*sources):
    descriptors, fields = preparation_fact_sources(), {}
    for index, source in enumerate(sources):
        if source in descriptors:
            node = deepcopy(descriptors[source]['report_schema'])
        elif source == COMPLETE:
            node = {'type': 'boolean', 'x-source': source}
        else:
            node = {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
                'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': source}
        fields['requested_' + str(index)] = node
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def selector(collection='input_records', quantities=('fields.CLEN',), checks=(), *, keys=None,
        artifacts=(), projection=True):
    return {'version': 'native_infernal_preparation_result_selector_v1',
        'acquisition': 'complete_bound_bundle', 'artifacts': list(artifacts),
        'projection': {'collection': collection,
            'rows': {'record_keys': keys} if keys is not None else {'offset': 0, 'limit': 100},
            'quantities': list(quantities), 'checks': list(checks)} if projection else None}


def retained_projection(store, case, source, selected=None):
    if case == 'consensus':
        sheet_path = EMISSION / 'prior_cmemit_consensus.sheet.json'
        calculation_path = EMISSION / 'prior_cmemit_consensus.calculations.json'
    else:
        directory = MODELS / {'press': 'cmpress_retained_219', 'binary': 'cmconvert_binary'}[case]
        sheet_path, calculation_path = directory / 'sheet.json', directory / 'calculations.json'
    sheet = json.loads(sheet_path.read_text())
    calculations = json.loads(calculation_path.read_text())
    # These are explicit fixture occurrence bindings of retained native bytes,
    # not claims of a production capture, producer receipt or live invocation.
    bundle = store.artifact(canonical({'fixture': case, 'source_ref': source}), 'application/json')
    replacements, occurrences, counters = {}, [], {}
    for artifact in sheet['artifacts']:
        role = artifact['role']
        if case == 'consensus':
            path = ROOT / artifact['artifact_ref']
        elif case == 'press':
            path = PRESSED / ('two_models.cm' if role == 'models' else
                'two_models.cm.' + role if role.startswith('i1') else role + '.txt')
        else:
            path = BOUNDARIES / 'cmconvert_binary' / {
                'models': 'model.cm', 'converted_models': 'converted.out',
                'stdout': 'stdout.txt', 'stderr': 'stderr.txt'}[role]
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifact['sha256']
        assert len(content) == artifact['size_bytes']
        actual_ref = store.artifact(content)
        direction = 'input' if role == 'models' else 'output'
        ordinal = counters.get((direction, role), 0)
        counters[direction, role] = ordinal + 1
        index = sum(row['direction'] == direction for row in occurrences)
        occurrence = bundle + ('#/inputs/' if direction == 'input' else '#/artifacts/') + str(index)
        replacements[artifact['artifact_ref']] = occurrence
        occurrences.append({**artifact, 'artifact_ref': actual_ref, 'occurrence_ref': occurrence,
            'direction': direction, 'ordinal': ordinal, 'relative_path': 'retained/' + role})

    def rebind(value, field=''):
        if isinstance(value, dict):
            return {name: rebind(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [rebind(item, field) for item in value]
        if isinstance(value, str) and (field.endswith(('_ref', '_refs', '_keys'))
                or field in {'record_key', 'sequence_key', 'alignment_key'}):
            for old, new in replacements.items():
                if value == old or value.startswith(old + '#'):
                    return new + value[len(old):]
        return value

    grading = rebind({'version': 'native_infernal_preparation_grading_v1',
        'operation': sheet['operation'], 'sheet': sheet, 'calculations': calculations})
    selected = selector() if selected is None else deepcopy(selected)
    # Native keys are deliberately selected by their exact retained identity.
    if selected['projection'] is not None and selected['projection']['rows'].get('record_keys') == ['first', 'missing-native-key']:
        collection = selected['projection']['collection']
        rows = grading['calculations']['rows'] if collection == 'calculations' else grading['sheet'][collection]
        selected['projection']['rows']['record_keys'][0] = rows[0]['record_key']
    result = project_preparation_result(grading, selector=selected, source_ref=source, occurrences=occurrences)
    return result, grading, occurrences


class SuppliedResultsPort:
    """Explicit result port; real runtime tables back its completed fixtures."""
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id
        self.saved, self.records, self.contexts, self.calls = {}, {}, {}, []

    def applies(self, context):
        return context.role == 'results' and context.assignment.get('provider') == 'infernal_preparation'

    def register(self, context, facts):
        self.saved[context.episode_id] = deepcopy(facts)
        self.contexts[context.episode_id] = plain(context.as_record())
        for reference in facts[GENERIC]:
            self.records[reference] = deepcopy(self.store.get(reference))
        Journal(self.store, self.run_id).save('runtime_actions', {
            'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
            'result': canonical({'status': 'completed', 'fixture_facts': facts}), 'credit': None})

    def facts(self, context):
        self.calls.append(context.episode_id)
        if plain(context.as_record()) != self.contexts[context.episode_id]:
            raise ValueError('supplied_results_original_context_conflict')
        row = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=0', (self.run_id, context.episode_id)).fetchone()
        if row is None or row['result'] is None:
            raise ValueError('supplied_results_completed_action_required')
        outcome = json.loads(row['result'])
        if outcome != {'status': 'completed', 'fixture_facts': self.saved[context.episode_id]}:
            raise ValueError('supplied_results_completed_action_conflict')
        result = deepcopy(self.saved[context.episode_id])
        for reference in result[GENERIC]:
            if self.store.get(reference) != self.records[reference]:
                raise ValueError('supplied_results_original_record_conflict')
        wanted = requested_sources(context.request['report_contract']['measurements']['schema'])
        for source in FACT_SOURCES:
            if source not in wanted:
                result[source] = []
        return result

    def read_result(self, *args, **kwargs):
        raise AssertionError('Return authentication reopened an original result')

    def result_identity(self, *args, **kwargs):
        raise AssertionError('Return authentication confused bundle and received-fact identity')

    def resolve(self, *args, **kwargs):
        raise AssertionError('Return authentication broadened received facts through an own-result resolver')


class SavedReturns:
    def __init__(self, store):
        self.store, self.run_id = store, 'infernal-preparation-return-fixture'
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGTACGTACGT', molecule='dna')['subject_refs']}
        self.results = SuppliedResultsPort(store, self.run_id)
        self.boundary = NativeInfernalPreparationReturns(SimpleNamespace(
            store=store, run_id=self.run_id, native_infernal_preparation_results=self.results))
        self.root = self.context((('annotation', 'root'),), {}, None)

    def context(self, path, assignment, contract, parent=None, scope=None):
        scope = plain(self.scope if scope is None else scope)
        episode_id = EpisodeRef(self.run_id, path).episode_id
        self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective='Verify supplied preparation facts', result_contract={'role': path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
                objective='Verify supplied preparation facts', result_contract=contract.schema))
        message = {'scope': scope, 'initial_report': {}, 'episode_assignment': deepcopy(assignment)}
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, scope, assignment, request)
        self.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        return context

    def child(self, parent, schema, *, index=0, role='results', provider='infernal_preparation', scope=None):
        contract = TypedReportContract('Return requested original operational facts', schema, lambda *_: True)
        assignment = {'provider': provider} if role == 'results' else {}
        child = self.context((*parent.path, (role, 'child_' + str(index))), assignment, contract, parent,
            scope=parent.scope if scope is None else scope)
        selection = {'kind': 'episode_child', 'role': role, 'assignment': deepcopy(assignment),
            'scope': plain(child.scope), 'purpose': contract.decision, 'schema_json': canonical(schema)}
        self.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
            'action': canonical(selection), 'result': None, 'credit': None})
        return child

    def source(self, label):
        artifact = self.store.artifact(canonical({'explicit_fixture_binding': label}), 'application/json')
        return self.store.put('source', {'provider': 'episode.execution_result', 'accession': None,
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': 'native_infernal_preparation_bundle_v1', 'retrieved_at': '2026-10-26T00:00:00+00:00'},
            origin='tool')['id']

    def publication(self, child, case='consensus', selected=None, *, source=None):
        source = self.source(child.episode_id) if source is None else source
        projection, grading, occurrences = retained_projection(self.store, case, source, selected)
        refs = [source]
        for row in projection['rows']:
            if row['artifact_ref'] is not None:
                refs.append(row['artifact_ref'])
            refs.extend(o['artifact_ref'] for c in row['checks'] for o in c['occurrences'])
        refs.extend(row['artifact_ref'] for row in projection['artifacts'])
        refs = list(dict.fromkeys(refs))
        facts = {ROWS: projection['rows'], ARTIFACTS: projection['artifacts'], POPULATION: [projection['population']],
            FAILURES: [], GENERIC: refs, REFERENCE_SOURCE: refs, COMPLETE: True}
        self.results.register(child, facts)
        self.receipts.receive(child.episode_id, refs, kind='own_action', source_index=0)
        return projection, grading, occurrences

    def returned(self, parent, child, facts=None):
        contract = plain(child.request)['report_contract']
        facts = self.results.facts(child) if facts is None else deepcopy(facts)
        form = form_with_facts({}, contract['measurements']['schema'], facts)
        self.journal.save('runtime_forms', {'episode_id': child.episode_id,
            'facts': canonical(facts), 'form': canonical(form)})
        index = int(child.path[-1][1].removeprefix('child_'))
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24],
            'child_episode_id': child.episode_id, 'contract': canonical(contract), 'form': canonical(form), 'failure': None})
        return form

    def redeliver(self, parent, child, schema, *, index=1):
        original_index = int(child.path[-1][1].removeprefix('child_'))
        original = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE '
            'run_id=? AND parent_episode_id=? AND decision_index=?',
            (self.run_id, parent.episode_id, original_index)).fetchone()
        contract = TypedReportContract('Return selected frozen operational facts', schema, lambda *_: True).as_record()
        facts = json.loads(self.journal.row('runtime_forms', child.episode_id)['facts'])
        form = form_with_facts({}, schema, facts)
        selection = {'kind': 'redeliver_report', 'delivery_ref': original['delivery_ref'],
            'schema_json': canonical(schema), 'purpose': contract['decision']}
        self.journal.save('runtime_model_calls', {'episode_id': parent.episode_id, 'call_index': index,
            'purpose': 'decision', 'request': '{}', 'response': canonical({'selection': selection})})
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': original['delivery_ref'], 'child_episode_id': child.episode_id,
            'contract': canonical(contract), 'form': canonical(form), 'failure': None})
        return form

    def operation(self, parent, index=0):
        return f'{self.run_id}:{parent.episode_id}:{index}:typed_form'


@pytest.fixture(autouse=True)
def no_native_acquisition_or_grading(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Return verification attempted native/acquisition/parser/calculator work')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    for module, functions in (
        ('native_infernal_preparation_worker', ['grade_infernal_preparation', 'recalculate_infernal_preparation']),
        ('native_infernal_preparation_acquisition', ['capture_local_bundle']),
        ('infernal_preparation_models', ['extract_infernal_models']),
        ('infernal_preparation_artifacts', ['populate_infernal_artifact_sheet']),
        ('infernal_preparation_statistics', ['populate_infernal_statistics_sheet']),
        ('infernal_preparation_calculations', ['calculate_infernal_statistics']),
        ('infernal_preparation_emission', ['populate_cmemit_sheet']),
        ('infernal_preparation_emission_calculations', ['calculate_cmemit_components']),
    ):
        for function in functions:
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + function, forbidden)


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / 'state') as store:
        fixture = SavedReturns(store)
        yield fixture
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('case,selected', [
    ('consensus', selector('calculations', ('components.residue_count', 'components.gc_count',
        'components.gc_denominator', 'components.gc_fraction_canonical'), ('cmemit_counts_consistent',),
        artifacts=[{'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}])),
    ('press', selector('calculations', (), ('artifact_signature', 'artifact_payload_identity'))),
    ('binary', selector('calculations', ('components.output_model_count',), artifacts=[
        {'direction': 'output', 'role': role, 'ordinal': 0} for role in ('stdout', 'stderr', 'converted_models')])),
])
def test_actual_retained_projection_crosses_exact_form_without_new_work(saved, case, selected, monkeypatch):
    schema = schema_for(*FACT_SOURCES, REFERENCE_SOURCE)
    child = saved.child(saved.root, schema)
    projected, _, _ = saved.publication(child, case, selected)
    form = saved.returned(saved.root, child)
    def forbidden(*args, **kwargs):
        raise AssertionError('Return authentication reprojected retained grading')
    monkeypatch.setattr('gene_annotation_episode.infernal_preparation_result_views.project_preparation_result', forbidden)
    before = list(saved.store.db.iterdump())
    saved.boundary.validate_received_report(child, form, schema)
    assert validate_form(form, schema, lambda ref, ns: saved.boundary.resolve_received(saved.root, ref, ns)) == form
    received = saved.boundary.received_facts(saved.root, schema)
    assert received[ROWS] == projected['rows']
    assert received[ARTIFACTS] == projected['artifacts']
    assert received[POPULATION] == [projected['population']]
    refs = saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert refs == received[REFERENCE_SOURCE]
    for row in projected['rows']:
        for check in row['checks']:
            assert all(occurrence['artifact_ref'] in refs for occurrence in check['occurrences'])
    if case == 'consensus':
        row = next(row for row in received[ROWS] if row['quantities'][0]['state'] == 'present')
        assert [q['value'] for q in row['quantities']] == [12, 8, 12, 2/3]
    elif case == 'press':
        checks = received[ROWS][0]['checks']
        assert len(checks) > 4
        assert {o['role'] for check in checks for o in check['occurrences']} == {'i1m', 'i1i', 'i1f', 'i1p'}
    else:
        assert received[ROWS][0]['quantities'][0]['value'] is None
        assert received[ARTIFACTS][0]['artifact_ref'] == received[ARTIFACTS][1]['artifact_ref']
        assert [row['size_bytes'] for row in received[ARTIFACTS]] == [0, 0, 7166]
    assert list(saved.store.db.iterdump()) == before


@pytest.mark.parametrize('source', [GENERIC, REFERENCE_SOURCE])
def test_reference_only_forms_do_not_grant_rows_names_digests_or_population(saved, source):
    schema = schema_for(source)
    child = saved.child(saved.root, schema)
    projection, _, _ = saved.publication(child, selected=selector(artifacts=[
        {'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}]))
    form = saved.returned(saved.root, child)
    saved.boundary.validate_received_report(child, form, schema)
    refs = saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert refs == form['requested_0']
    assert saved.boundary.received_context(saved.root) == []
    assert saved.boundary.received_facts(saved.root, schema_for(*FACT_SOURCES)) == {source: [] for source in FACT_SOURCES}
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['record_key'], 'native_infernal_preparation_row') is False
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['name'], 'native_infernal_preparation_name') is False
    assert saved.boundary.resolve_received(saved.root, projection['artifacts'][0]['sha256'], 'native_infernal_preparation_sha256') is False
    artifact = projection['rows'][0]['artifact_ref']
    assert saved.boundary.resolve_received(saved.root, artifact, 'artifact') is True
    assert saved.boundary.resolve_received(saved.root, artifact, 'source') is False
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['source_ref'], 'artifact') is False
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['source_ref'], 'source') is True
    for ref in refs:
        assert saved.boundary.resolve_received(saved.root, ref, 'execution_result') is True


@pytest.mark.parametrize('forward', [ROWS, ARTIFACTS, POPULATION, REFERENCE_SOURCE, COMPLETE])
def test_each_scientific_boundary_forwards_only_requested_facts(saved, forward):
    outer = schema_for(forward)
    science = saved.child(saved.root, outer, role='scientific_process')
    inner = schema_for(*FACT_SOURCES, REFERENCE_SOURCE)
    leaf = saved.child(science, inner)
    projection, _, _ = saved.publication(leaf, selected=selector(artifacts=[
        {'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}]))
    saved.returned(science, leaf)
    facts = saved.boundary.received_facts(science, outer)
    facts[COMPLETE] = True
    form = saved.returned(saved.root, science, facts)
    saved.boundary.validate_received_report(science, form, outer)
    saved.boundary.record_admission(saved.root, form, outer, saved.operation(saved.root))
    received = saved.boundary.received_facts(saved.root, schema_for(*FACT_SOURCES))
    for source, expected in [(ROWS, projection['rows']), (ARTIFACTS, projection['artifacts']), (POPULATION, [projection['population']])]:
        assert received[source] == (expected if source == forward else [])
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['name'],
        'native_infernal_preparation_name') is (forward == ROWS)
    assert saved.boundary.resolve_received(saved.root, projection['artifacts'][0]['sha256'],
        'native_infernal_preparation_sha256') is (forward == ARTIFACTS)


def test_missing_record_key_is_a_returned_diagnostic_without_row_or_name_access(saved):
    schema = schema_for(POPULATION)
    child = saved.child(saved.root, schema)
    projection, _, _ = saved.publication(child, selected=selector(keys=['first', 'missing-native-key']))
    form = saved.returned(saved.root, child)
    assert validate_form(form, schema, lambda ref, ns: saved.boundary.resolve_received(saved.root, ref, ns)) == form
    assert saved.boundary.resolve_received(saved.root, 'missing-native-key', 'native_infernal_preparation_row') is True
    assert saved.boundary.resolve_received(saved.root, 'another-missing-key', 'native_infernal_preparation_row') is False
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['record_key'], 'native_infernal_preparation_row') is False
    assert saved.boundary.received_facts(saved.root, schema_for(ROWS)) == {ROWS: []}
    assert saved.boundary.resolve_received(saved.root, 'missing-native-key', 'native_infernal_preparation_name') is False


@pytest.mark.parametrize('same_source', [False, True])
def test_population_and_artifact_associations_survive_forwarding_and_redelivery(saved, same_source):
    schema = schema_for(POPULATION, ARTIFACTS)
    science = saved.child(saved.root, schema, role='scientific_process')
    sources, projections = [], []
    for index in range(2):
        leaf = saved.child(science, schema, index=index)
        projected, _, _ = saved.publication(leaf, 'binary', selector(projection=False, artifacts=[
            {'direction': 'output', 'role': 'converted_models', 'ordinal': 0}]),
            source=sources[0] if same_source and sources else None)
        sources.append(projected['population']['source_ref'])
        projections.append(projected)
        saved.returned(science, leaf)
        if index == 0:
            first = leaf
    saved.redeliver(science, first, schema, index=2)
    facts = saved.boundary.received_facts(science, schema)
    expected_count = 1 if same_source else 2
    assert len(facts[POPULATION]) == len(facts[ARTIFACTS]) == expected_count
    assert len({row['artifact_ref'] for row in facts[ARTIFACTS]}) == 1
    form = saved.returned(saved.root, science, facts)
    saved.redeliver(saved.root, science, schema, index=1)
    before = list(saved.store.db.iterdump())
    saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert saved.boundary.received_facts(saved.root, schema) == facts
    assert [row['source_ref'] for row in facts[POPULATION]] == list(dict.fromkeys(sources))
    assert list(saved.store.db.iterdump()) == before
    assert saved.journal.row('runtime_actions', science.episode_id, 2) is None


def test_frozen_scientific_return_remains_original_subset_after_later_delivery(saved):
    schema = schema_for(*FACT_SOURCES, REFERENCE_SOURCE)
    science = saved.child(saved.root, schema, role='scientific_process')
    first = saved.child(science, schema)
    saved.publication(first)
    saved.returned(science, first)
    frozen = saved.boundary.received_facts(science, schema)
    form = saved.returned(saved.root, science, frozen)
    second = saved.child(science, schema, index=1)
    saved.publication(second)
    saved.returned(science, second)
    assert len(saved.boundary.received_facts(science, schema)[POPULATION]) == 2
    before = list(saved.store.db.iterdump())
    saved.boundary.validate_received_report(science, form, schema)
    saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))
    assert saved.boundary.received_facts(saved.root, schema) == frozen
    assert list(saved.store.db.iterdump()) == before


def test_duplicate_frozen_population_rows_cannot_invent_a_second_original_fact(saved):
    schema = schema_for(POPULATION)
    science = saved.child(saved.root, schema, role='scientific_process')
    leaf = saved.child(science, schema)
    saved.publication(leaf)
    saved.returned(science, leaf)
    facts = saved.boundary.received_facts(science, schema)
    facts[POPULATION] *= 2
    form = saved.returned(saved.root, science, facts)
    with pytest.raises(ValueError, match=PREFIX + 'returned_facts_conflict'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))


def test_sibling_or_inherited_source_possession_does_not_supply_requested_facts(saved):
    schema = schema_for(*FACT_SOURCES, REFERENCE_SOURCE)
    science = saved.child(saved.root, schema, role='scientific_process')
    sibling = saved.child(saved.root, schema, index=1)
    saved.publication(sibling)
    saved.returned(saved.root, sibling)
    sibling_facts = saved.results.facts(sibling)
    saved.receipts.receive(science.episode_id, sibling_facts[GENERIC], kind='own_action', source_index=0)
    form = form_with_facts({}, schema, sibling_facts)
    with pytest.raises(ValueError, match=PREFIX + 'returned_facts_conflict'):
        saved.boundary.validate_received_report(science, form, schema)
    assert saved.boundary.received_facts(science, schema) == {source: [] for source in (*FACT_SOURCES, REFERENCE_SOURCE)}


def test_other_provider_generic_refs_and_unrelated_forms_remain_unhandled(saved):
    schema = schema_for(GENERIC)
    child = saved.child(saved.root, schema, provider='other')
    reference = saved.source('other-provider')
    form = saved.returned(saved.root, child, {GENERIC: [reference]})
    saved.boundary.validate_received_report(child, form, schema)
    assert saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root)) == []
    assert saved.boundary.received_context(saved.root) == []
    assert saved.boundary.received_facts(saved.root, schema) == {}
    assert saved.boundary.resolve_received(saved.root, reference, 'execution_result') is None
    assert saved.boundary.resolve_received(saved.root, reference, 'unrelated_namespace') is None
    assert saved.results.calls == []


@pytest.mark.parametrize('field', ['quantity', 'state', 'name', 'accession', 'source', 'artifact',
    'check_outcome', 'check_occurrence', 'population', 'missing_key', 'artifact_source', 'digest'])
def test_forged_facts_reject_even_when_saved_forms_and_attempts_agree(saved, field):
    schema = schema_for(*FACT_SOURCES)
    child = saved.child(saved.root, schema)
    saved.publication(child, selected=selector('calculations', ('components.residue_count',),
        ('cmemit_counts_consistent',), artifacts=[{'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}]))
    facts = saved.results.facts(child)
    row = next(row for row in facts[ROWS] if row['quantities'][0]['state'] == 'present')
    if field == 'quantity':
        row['quantities'][0]['value'] = 13
    elif field == 'state':
        row['quantities'][0].update(value=None, state='missing')
    elif field in {'name', 'accession'}:
        row[field] = 'forged'
    elif field == 'source':
        row['source_ref'] = saved.source('forged')
    elif field == 'artifact':
        row['artifact_ref'] = saved.store.artifact('forged')
    elif field == 'check_outcome':
        row['checks'][0]['outcome'] = 'fail'
    elif field == 'check_occurrence':
        row['checks'][0]['occurrences'].append({'direction': 'output', 'role': 'stderr', 'ordinal': 0,
            'artifact_ref': saved.store.artifact('not-a-selected-check')})
    elif field == 'population':
        facts[POPULATION][0]['total_records'] += 1
    elif field == 'missing_key':
        facts[POPULATION][0]['missing_record_keys'].append('forged-missing-key')
    elif field == 'artifact_source':
        facts[ARTIFACTS][0]['source_ref'] = saved.source('other-producer')
    else:
        facts[ARTIFACTS][0]['sha256'] = '0' * 64
    form = saved.returned(saved.root, child, facts)
    with pytest.raises(ValueError, match=PREFIX + 'returned_facts_conflict'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))


@pytest.mark.parametrize('change', ['scope', 'assignment', 'role', 'purpose', 'schema', 'deleted'])
@pytest.mark.parametrize('redelivery', [False, True])
def test_original_commission_is_required_for_original_and_redelivered_facts(saved, change, redelivery):
    schema = schema_for(GENERIC)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    if redelivery:
        schema = schema_for(REFERENCE_SOURCE)
        form = saved.redeliver(saved.root, child, schema)
    action = json.loads(saved.journal.row('runtime_actions', saved.root.episode_id, 0)['action'])
    if change == 'scope':
        action['scope'] = {'subject_refs': []}
    elif change == 'assignment':
        action['assignment'] = {'provider': 'other'}
    elif change == 'role':
        action['role'] = 'annotation'
    elif change == 'purpose':
        action['purpose'] = 'changed purpose'
    elif change == 'schema':
        action['schema_json'] = canonical(schema_for(COMPLETE))
    if change == 'deleted':
        saved.store.db.execute('DELETE FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
            (saved.run_id, saved.root.episode_id))
    else:
        saved.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(action), saved.run_id, saved.root.episode_id))
    with pytest.raises(ValueError, match=PREFIX):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root, int(redelivery)))


@pytest.mark.parametrize('change', ['frozen_form', 'frozen_facts', 'context_request', 'closed_facts_missing',
    'child_owner', 'redelivery_identity', 'source_record', 'completed_action'])
def test_saved_context_closure_and_underlying_port_mutations_reject(saved, change):
    schema = schema_for(GENERIC)
    child = saved.child(saved.root, schema)
    projection, _, _ = saved.publication(child)
    form = saved.returned(saved.root, child)
    index = 0
    if change in {'frozen_form', 'frozen_facts'}:
        column = 'form' if change == 'frozen_form' else 'facts'
        saved.store.db.execute(f'UPDATE runtime_forms SET {column}=? WHERE run_id=? AND episode_id=?',
            ('{}', saved.run_id, child.episode_id))
    elif change == 'context_request':
        request = plain(child.request)
        request['message']['scope'] = {'subject_refs': []}
        with pytest.raises(ValueError, match=PREFIX + 'context_conflict'):
            saved.boundary.validate_received_report(replace(child, request=request), form, schema)
        return
    elif change == 'closed_facts_missing':
        saved.store.db.execute('DELETE FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (saved.run_id, child.episode_id))
    elif change == 'child_owner':
        science = saved.child(saved.root, schema_for(COMPLETE), role='scientific_process', index=1)
        grandchild = saved.child(science, schema)
        saved.publication(grandchild)
        saved.returned(science, grandchild)
        saved.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=0', (grandchild.episode_id, saved.run_id, saved.root.episode_id))
    elif change == 'redelivery_identity':
        form = saved.redeliver(saved.root, child, schema)
        index = 1
        saved.store.db.execute('UPDATE runtime_report_attempts SET delivery_ref=? WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=1', ('forged-delivery', saved.run_id, saved.root.episode_id))
    elif change == 'source_record':
        reference = projection['population']['source_ref']
        record = saved.store.get(reference)
        record['provider'] = 'other.provider'
        saved.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), reference))
    else:
        saved.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0',
            (saved.run_id, child.episode_id))
    with pytest.raises(ValueError, match=PREFIX + '|supplied_results_'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root, index))


def test_redelivery_cannot_recover_unrequested_rows_but_preserves_reference_alias(saved):
    schema = schema_for(GENERIC)
    child = saved.child(saved.root, schema)
    projection, _, _ = saved.publication(child)
    original = saved.returned(saved.root, child)
    numeric = schema_for(*FACT_SOURCES)
    no_rows = saved.redeliver(saved.root, child, numeric)
    assert no_rows == {f'requested_{i}': [] for i in range(len(FACT_SOURCES))}
    assert saved.boundary.record_admission(saved.root, no_rows, numeric, saved.operation(saved.root, 1)) == []
    alias = schema_for(REFERENCE_SOURCE)
    again = saved.redeliver(saved.root, child, alias, index=2)
    before = list(saved.store.db.iterdump())
    assert saved.boundary.record_admission(saved.root, again, alias, saved.operation(saved.root, 2)) == original['requested_0']
    assert saved.boundary.received_facts(saved.root, alias) == {REFERENCE_SOURCE: original['requested_0']}
    assert saved.boundary.resolve_received(saved.root, projection['rows'][0]['record_key'], 'native_infernal_preparation_row') is False
    assert list(saved.store.db.iterdump()) == before
    assert saved.journal.row('runtime_actions', saved.root.episode_id, 1) is None
    assert saved.journal.row('runtime_actions', saved.root.episode_id, 2) is None


def test_parent_child_scope_containment_and_opposite_direction_are_enforced(saved):
    scope = {**saved.scope, 'segments': [{'target_ref': saved.scope['subject_refs'][0], 'start': 0, 'end': 6, 'unit': 'nt'}]}
    schema = schema_for(ROWS)
    science = saved.child(saved.root, schema, role='scientific_process', scope=scope)
    valid = saved.child(science, schema, scope=scope)
    projection, _, _ = saved.publication(valid)
    saved.returned(science, valid)
    assert saved.boundary.received_facts(science, schema)[ROWS] == projection['rows']
    # A child's inherited parent references are not a return from its child.
    assert saved.boundary.received_facts(valid, schema) == {ROWS: []}
    invalid = saved.child(science, schema, index=1, scope=saved.scope)
    saved.publication(invalid)
    form = saved.returned(science, invalid)
    with pytest.raises(ValueError, match=PREFIX + 'commission_scope_conflict'):
        saved.boundary.record_admission(science, form, schema, saved.operation(science, 1))


def test_form_schema_and_duplicate_source_fields_are_authenticated(saved):
    schema = schema_for(ROWS, ROWS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    altered = deepcopy(form)
    altered['requested_1'] = []
    with pytest.raises(ValueError, match=PREFIX + 'conflicting_fields'):
        saved.boundary.validate_received_report(child, altered, schema)
    renamed = deepcopy(schema)
    renamed['properties']['changed'] = renamed['properties'].pop('requested_1')
    renamed['required'] = list(renamed['properties'])
    with pytest.raises(ValueError, match=PREFIX + 'admitted_form_conflict'):
        saved.boundary.record_admission(saved.root, form, renamed, saved.operation(saved.root))


def test_reference_type_cannot_be_relabelled_by_a_supplied_port(saved):
    schema = schema_for(ROWS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    facts = deepcopy(saved.results.saved[child.episode_id])
    facts[ROWS][0]['source_ref'] = facts[ROWS][0]['artifact_ref']
    saved.results.register(child, facts)
    form = saved.returned(saved.root, child)
    with pytest.raises(ValueError, match=PREFIX + 'returned_reference_kind_conflict'):
        saved.boundary.record_admission(saved.root, form, schema, saved.operation(saved.root))


def test_authentication_cache_lasts_only_one_synchronous_form_check(saved):
    schema = schema_for(ROWS)
    child = saved.child(saved.root, schema)
    saved.publication(child)
    form = saved.returned(saved.root, child)
    saved.results.calls.clear()
    resolver = lambda ref, ns: saved.boundary.resolve_received(saved.root, ref, ns)
    assert validate_form(form, schema, resolver) == form
    assert saved.results.calls == [child.episode_id]
    reference = form['requested_0'][0]['source_ref']
    record = saved.store.get(reference)
    record['provider'] = 'mutated.after.first.validation'
    saved.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), reference))
    with pytest.raises(ValueError, match='supplied_results_original_record_conflict'):
        validate_form(form, schema, resolver)
    assert saved.results.calls == [child.episode_id, child.episode_id]
