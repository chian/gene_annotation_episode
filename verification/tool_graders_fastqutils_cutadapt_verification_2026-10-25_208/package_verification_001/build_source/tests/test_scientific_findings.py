"""Synthetic scientific statements; these are not source truth judgments."""
from copy import deepcopy
import asyncio
import json

import pytest

from gene_annotation_episode.domain import ContractError, identity
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.scientific_findings import FindingIdentity
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, project_finding_progress
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.runtime import _action_generation_schema, run_workflow
from test_runtime import FixtureController, ScriptedProvider, obj
from test_scientific_hypervolume_runtime import assessment, annotation, evidence


def finding(subject, *, value='positive', qualification='none', equivalent=None, replaces=()):
    return {'source_claim': {'subject_refs': [subject], 'predicate': 'growth_capability',
                'value': {'type': 'enum', 'value': value}, 'context_refs': []},
        'qualification': {'kind': qualification, 'context_refs': [], 'assumption_refs': []},
        'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
        'same_source_claim_as_ref': equivalent, 'replaces_refs': list(replaces)}


def target_question(store):
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target],
        'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'unresolved'},
        'context_refs': []}, origin='reasoning')['id']
    return target, hypothesis


def quoted_observation(store, *, accession, start, end, label='ConstructX'):
    text = 'ConstructX grows. The measured ConstructX grows under this condition.'
    artifact = store.artifact(text)
    source = store.put('source', {'provider': 'synthetic_fixture', 'accession': accession,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': accession, 'retrieved_at': None,
        'publication_identifiers': [{'namespace': 'doi', 'value': '10.1234/synthetic'}]}, origin='external')
    anchor = {'source_ref': source['id'], 'artifact_ref': artifact,
        'start': start, 'end': end, 'quote': text[start:end]}
    subject_payload = {'reference_type': 'construct', 'source_ref': source['id'],
        'label': label, 'anchor': anchor}
    subject_payload.update(sequence_ref=None, length=None, molecule=None, term_refs=[], context_refs=[])
    # Native extracted-subject identity is source + label + exact anchor.
    subject_payload['accession'] = identity('source_entity',
        {key: subject_payload[key] for key in ('source_ref', 'label', 'anchor')})
    subject = store.put('reference', subject_payload, origin='extracted')['id']
    observation = store.put('observation', {'subject_refs': [subject],
        'source_subject_refs': [subject], 'kind': 'source_content', 'source_ref': source['id'],
        'measurements': [], 'dependencies': [], 'anchor': anchor}, origin='extracted')
    return subject, observation


def test_requotation_reimport_and_opinion_do_not_change_typed_finding_identity(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        subject_a, observation_a = quoted_observation(store, accession='first', start=0, end=17)
        subject_b, observation_b = quoted_observation(store, accession='second', start=18, end=67)
        assert subject_a != subject_b and observation_a['id'] != observation_b['id']
        saved = []
        for index, (subject, observation) in enumerate([(subject_a, observation_a), (subject_b, observation_b)]):
            payload = assessment(hypothesis, observation['id'], 'incomparable')
            payload['relation'] = 'strengthens' if index == 0 else 'does_not_discriminate'
            payload['investigation_finding'] = finding(subject, qualification='different_source_subject')
            saved.append(store.put('assessment', payload, origin='reasoning'))
        canonicalizer = FindingIdentity(store)
        assert canonicalizer.finding(saved[0]) == canonicalizer.finding(saved[1])
        payload = assessment(hypothesis, observation_b['id'], 'incomparable', revision=saved[1]['revision'])
        payload['investigation_finding'] = finding(subject_b, value='negative',
            qualification='different_source_subject')
        changed = store.put('assessment', payload, origin='reasoning')
        assert canonicalizer.finding(changed)['finding_key'] != canonicalizer.finding(saved[0])['finding_key']
        payload['expected_revision'] = changed['revision']
        payload['investigation_finding'] = finding(subject_b, qualification='measurement_does_not_establish_claim')
        changed = store.put('assessment', payload, origin='reasoning')
        assert canonicalizer.finding(changed)['finding_key'] != canonicalizer.finding(saved[0])['finding_key']
        assert len(store.targets()) == 1 and store.targets()[0]['id'] == target


def test_explicit_equivalence_and_correction_remain_structured_in_actual_commit(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        first = assessment(hypothesis, observed['id'], 'direct')
        first['investigation_finding'] = finding(target)
        previous = store.put('assessment', first, origin='reasoning')
        payload = {name: [] for name in store.reasoning_schema()['required']}
        corrected = assessment(hypothesis, observed['id'], 'incomparable',
            alias='corrected', revision=previous['revision'])
        corrected['investigation_finding'] = finding(target, equivalent=previous['id'],
            replaces=[previous['id']])
        payload['assessments'] = [corrected]
        result = store.commit_reasoning(payload, {'subject_refs': [target]}, 'synthetic-correction')
        assert result['status'] == 'completed' and result['errors'] == []
        current = store.get(result['aliases']['corrected'])
        canonicalizer = FindingIdentity(store)
        assert canonicalizer.finding(current) == canonicalizer.finding(previous)
        assert current['investigation_finding']['status'] == 'retained'
        assert current['applicability'] == 'incomparable'
        assert current['investigation_finding']['replaces_refs'] == [previous['id']]
        assert store.get(previous['id']) == previous
        assert store.current_assessments()[0] == current
        assert store.commit_reasoning(payload, {'subject_refs': [target]}, 'synthetic-correction') == result


def test_withdrawal_is_distinct_from_nontransferability_and_changes_actual_support(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        original = assessment(hypothesis, observed['id'], 'direct')
        original['investigation_finding'] = finding(target)
        saved = store.put('assessment', original, origin='reasoning')
        store.put('annotation', annotation(target, hypothesis, [saved['id']], 0), origin='reasoning')
        scorer = AnnotationSupportScore(CreditPolicy())
        initial = scorer(store, {'subject_refs': [target]}).credit
        assert initial > 0
        withdrawn = deepcopy(original)
        withdrawn['expected_revision'] = saved['revision']
        withdrawn['investigation_finding'].update(status='withdrawn', withdrawal_reason='source_misread')
        current = store.put('assessment', withdrawn, origin='reasoning')
        store.put('annotation', annotation(target, hypothesis, [current['id']], 1), origin='reasoning')
        details = scorer.read_details(store, {'subject_refs': [target]}, details_limit=10, details_offset=0)
        assert details['credit'] == 0
        inactive, = details['inactive_dependencies']
        assert inactive['reason'] == 'scientific_finding_withdrawn'
        assert inactive['withdrawal_reason'] == 'source_misread'
        assert store.get(saved['id']) == saved


@pytest.mark.parametrize('defect,code', [
    ('source_subject', 'finding_source_subject_not_in_observation'),
    ('withdrawal_reason', 'finding_status_reason_mismatch'),
    ('untyped_equivalence', 'finding_reference_has_no_typed_finding'),
])
def test_bad_finding_reference_is_actionable_and_other_commit_rows_survive(tmp_path, defect, code):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        old = store.put('assessment', assessment(hypothesis, observed['id'], 'direct'), origin='reasoning')
        payload = {name: [] for name in store.reasoning_schema()['required']}
        payload['hypotheses'] = [{'alias': 'good', 'subject_refs': [target], 'predicate': 'located_in',
            'value': {'type': 'enum', 'value': 'unknown'}, 'context_refs': []}]
        bad = assessment(hypothesis, observed['id'], 'incomparable', alias='bad', revision=old['revision'])
        bad['investigation_finding'] = finding(target)
        if defect == 'source_subject':
            # A different actual source subject, outside this observation.
            subject, _ = quoted_observation(store, accession='other', start=0, end=17)
            bad['investigation_finding']['source_claim']['subject_refs'] = [subject]
        elif defect == 'withdrawal_reason':
            bad['investigation_finding']['withdrawal_reason'] = 'wrong_subject'
        else:
            bad['investigation_finding']['same_source_claim_as_ref'] = old['id']
        payload['assessments'] = [bad]
        result = store.commit_reasoning(payload, {'subject_refs': [target]}, 'synthetic-'+defect)
        assert result['status'] == 'partial' and list(result['aliases']) == ['good']
        assert result['errors'][0]['code'] == code
        assert store.current_assessments()[0] == old


@pytest.mark.parametrize('accession', [None, 'requested-routing-id'])
def test_missing_source_identifiers_do_not_merge_unrelated_documents(tmp_path, monkeypatch, accession):
    with Store(tmp_path/'workspace') as store:
        target_question(store)
        refs = []
        for text in ['Synthetic first unidentified source', 'Synthetic second unidentified source']:
            artifact = store.artifact(text)
            refs.append(store.put('source', {'provider': 'synthetic_fixture', 'accession': accession,
                'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                'version': None, 'retrieved_at': None}, origin='external')['id'])
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('opened source contents'))
        canonicalizer = FindingIdentity(store)
        assert canonicalizer.source(refs[0]) != canonicalizer.source(refs[1])


@pytest.mark.parametrize('difference,expected', [
    ('page_only', 1), ('different_workbook', 2), ('different_claim', 2),
    ('different_qualification', 2), ('different_operation', 2),
    ('different_adapter', 2), ('multiple_parents', 2),
])
def test_selected_workbook_pages_do_not_multiply_the_same_finding(tmp_path, monkeypatch,
                                                                difference, expected):
    """Synthetic exact-cell selections, not biological findings about YbhP."""
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        workbooks = []
        for label in ('first', 'second'):
            workbooks.append(store.put('source', {'provider': 'synthetic_workbook',
                'accession': None, 'uri': None,
                'artifact_ref': store.artifact('SYNTHETIC workbook '+label),
                'text_ref': None, 'request_ref': None, 'version': None,
                'retrieved_at': None, 'publication_identifiers': [
                    {'namespace': 'doi', 'value': '10.1234/synthetic-workbooks'}]}, origin='external'))
        saved, source_refs = [], []
        for index, limit in enumerate((1, 2)):
            raw = json.dumps({'sheet': 'rId1', 'limit': limit,
                'rows': [{'row_number': 2, 'cells': [{'address': 'A2', 'value': 'positive'}]}]})
            artifact = store.artifact(raw, 'application/json')
            source = store.put('source', {'provider': ('synthetic_calculation'
                    if index and difference == 'different_operation' else 'xlsx.rows'),
                'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': None, 'request_ref': None,
                'version': 'synthetic_unknown_adapter' if index and difference == 'different_adapter'
                    else 'xlsx_selected_cells_v1',
                'retrieved_at': None, 'parent_source_refs': (
                    [row['id'] for row in workbooks] if index and difference == 'multiple_parents'
                    else [workbooks[int(bool(index and difference == 'different_workbook'))]['id']])}, origin='tool')
            source_refs.append(source['id'])
            observed = store.put('observation', {'subject_refs': [target],
                'source_subject_refs': [target], 'kind': 'source_content',
                'source_ref': source['id'], 'measurements': [], 'dependencies': [],
                'anchor': {'source_ref': source['id'], 'artifact_ref': artifact,
                    'start': 0, 'end': len(raw), 'quote': raw}}, origin='extracted')
            payload = assessment(hypothesis, observed['id'], 'direct')
            payload['investigation_finding'] = finding(target,
                value='negative' if index and difference == 'different_claim' else 'positive',
                qualification=('prediction_not_measurement'
                    if index and difference == 'different_qualification' else 'none'))
            saved.append(store.put('assessment', payload, origin='reasoning')['id'])
        assert len(set(source_refs)) == 2
        # Identity reads durable metadata, not the workbook or selected pages.
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('opened source contents'))
        projected = project_finding_progress(store, {'subject_refs': [target]},
            FindingProgressPolicy(1), known_assessment_refs=saved, details_limit=2)
        assert projected['retained_finding_count'] == expected
        assert projected['credit'] == expected
        assert len(projected['source_contributions']) == 2


def test_long_equivalence_chain_is_iterative_and_reuses_resolved_meaning(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        payload = assessment(hypothesis, observed['id'], 'direct')
        payload['investigation_finding'] = finding(target)
        first = store.put('assessment', payload, origin='reasoning')
        # Lightweight immutable revision fixtures stress dependency resolution;
        # ordinary Store/CAS/equivalence is exercised separately above.
        rows = {first['id']: first}
        previous = first
        for index in range(1100):
            current = {**first, 'id': identity('assessment', {'synthetic_revision': index}),
                'investigation_finding': finding(target, equivalent=previous['id'])}
            rows[current['id']] = current
            previous = current
        class ReadOnlyOverlay:
            def get(self, ref):
                return rows[ref] if ref in rows else store.get(ref)
        normalizer = FindingIdentity(ReadOnlyOverlay())
        assert normalizer.finding(previous) == normalizer.finding(first)
        assert len(normalizer._claims) == 1101


def test_source_domain_and_superfamily_categories_survive_commit_and_reopen(tmp_path):
    """Preserve literal source categories without relabeling earlier terms."""
    directory = tmp_path/'workspace'
    with Store(directory) as store:
        target, _ = target_question(store)
        text = 'Synthetic EEP: domain; Synthetic EEP superfamily: homologous_superfamily.'
        artifact = store.artifact(text)
        source = store.put('source', {'provider': 'synthetic_classification', 'accession': None,
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='external')
        anchor = {'source_ref': source['id'], 'artifact_ref': artifact,
                  'start': 0, 'end': len(text), 'quote': text}
        legacy = store.put('term', {'namespace': 'source_local', 'accession': identity('source_term',
            {'source_ref': source['id'], 'label': 'Synthetic EEP', 'anchor': anchor}),
            'label': 'Synthetic EEP', 'term_type': 'family',
            'source_ref': source['id'], 'anchor': anchor}, origin='extracted')
        schema = store.reasoning_schema()
        assert {'domain', 'homologous_superfamily'} <= set(
            schema['properties']['terms']['items']['properties']['term_type']['enum'])
        provider_schema = _action_generation_schema(schema)
        assert {'domain', 'homologous_superfamily'} <= set(
            provider_schema['properties']['terms']['items']['properties']['term_type']['enum'])
        payload = {name: [] for name in schema['required']}
        payload['terms'] = [{'alias': key, 'label': label, 'term_type': key,
            'source_ref': source['id'], 'anchor': anchor} for key, label in
            [('domain', 'Synthetic EEP'), ('homologous_superfamily', 'Synthetic EEP superfamily')]]
        result = store.commit_reasoning(payload, {'subject_refs': [target]}, 'source-category-fixture')
        assert result['status'] == 'completed' and result['errors'] == []
        current = {key: store.get(ref) for key, ref in result['aliases'].items()}
        assert {key: row['term_type'] for key, row in current.items()} == {
            'domain': 'domain', 'homologous_superfamily': 'homologous_superfamily'}
        assert store.get(legacy['id']) == legacy
        normalized = FindingIdentity(store)
        assert normalized.entity(current['domain']['id']) != normalized.entity(legacy['id'])
        # Recording classifications alone creates no investigation finding.
        assert project_finding_progress(store, {'subject_refs': [target]}, FindingProgressPolicy(1),
            known_assessment_refs=[])['credit'] == 0
    with Store(directory) as store:
        assert store.get(legacy['id']) == legacy
        assert {key: store.get(row['id'])['term_type'] for key, row in current.items()} == {
            'domain': 'domain', 'homologous_superfamily': 'homologous_superfamily'}


def test_iterative_child_returns_typed_findings_through_existing_parent_form(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        form = obj({'assessments': {'type': 'array', 'x-source': 'changed_assessment_refs',
            'items': {'type': 'string', 'format': 'reference',
                      'x-reference-namespace': 'assessment'}}})
        commission = {'selection': {'kind': 'child',
            'goal': 'Iteratively examine what the synthetic source establishes',
            'purpose': 'Return the actual assessment revisions and their typed qualifications',
            'scope': {'subject_refs': [target]}, 'schema_json': json.dumps(form),
            'initial_report_json': '{}'}, 'report_update': {}}
        def reason_with(row):
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['assessments'] = [row]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        first = assessment(hypothesis, observed['id'], 'transfer', alias='first')
        first['investigation_finding'] = finding(target)
        def revise(context):
            previous, = store.current_assessments()
            assert previous['investigation_finding']['status'] == 'retained'
            revised = assessment(hypothesis, observed['id'], 'scope_limited',
                alias='qualified', revision=previous['revision'])
            revised['investigation_finding'] = finding(target,
                qualification='measurement_does_not_establish_claim', equivalent=previous['id'])
            return reason_with(revised)
        received = []
        def integrate(context):
            report, = context['child_reports']
            received.append(report)
            assert set(report) == {'assessments'} and len(report['assessments']) == 2
            records = [store.get(ref) for ref in report['assessments']]
            current = max(records, key=lambda row: row['revision'])
            assert current['investigation_finding']['qualification']['kind'] == 'measurement_does_not_establish_claim'
            assert current['investigation_finding']['status'] == 'retained'
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['annotation_updates'] = [annotation(target, hypothesis, [current['id']], 0, alias='parent')]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        controllers = []
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2)
            controllers.append(value)
            return value
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([commission, reason_with(first), revise, integrate]),
            run_dir=tmp_path/'run', controller_factory=controller,
            project_credit=lambda *_: 0,
            binding_definitions={'credit': {'kind': 'synthetic_zero_progress'}}))
        assert summary['credit'] == 0
        assert [value.scores for value in controllers] == [[0, 0], [0, 0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert json.loads(store.db.execute('SELECT form FROM runtime_forms').fetchone()[0]) == received[0]
        parent, = store.current_annotations()
        assert parent['resolution'] == 'unresolved'
        assert parent['coherent_sets'][0]['interpretations'][0]['assessment_refs'] == [
            max((store.get(ref) for ref in received[0]['assessments']), key=lambda row: row['revision'])['id']]
