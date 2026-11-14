"""Labelled synthetic material allocations; no model or external measurements."""
from copy import deepcopy

import pytest

from gene_annotation_episode.credit import AXES, CreditPolicy, project_credit, softened_hypervolume
from gene_annotation_episode.state import Store
from gene_annotation_episode import library_targets


def library_fixture(tmp_path):
    path = tmp_path / 'three-original-reads.fastq'
    path.write_text('@A synthetic\nACGT\n+\nIIII\n@B synthetic\nACGTAC\n+\nIIIIII\n@C synthetic\nACGTACGTAC\n+\nIIIIIIIIII\n')
    store = Store(tmp_path / 'state')
    store.create_problem(path, molecule='dna')
    target, = store.targets()
    native, parameters = store.context_mask_target_query({'subject_refs': [target['id']]}, target['id'])
    members = sorted([dict(row) for row in store.db.execute(native, parameters)], key=lambda row: row['length'])
    source = source_fixture(store, 'sample-observations')
    sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic actual sample',
        'source_ref': source['id'], 'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')
    return store, target, members, source, sample


def source_fixture(store, label):
    artifact = store.artifact('Labelled synthetic fixture: '+label)
    return store.put('source', {'provider': 'synthetic_fixture', 'accession': label,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')


def select_mask(store, target, members):
    selected = library_targets.select(store, target['id'], member_refs=[row['member_ref'] for row in members])
    return {'subject_refs': [target['id']], 'read_selection_refs': [selected['id']]}


def context_account(store, target, source, sample, label, rows, *, allocation=None, account=None):
    """Rows explicitly declare kind, applicability, mask, and optional disposition."""
    full = {'subject_refs': [target['id']]}
    account = full if account is None else account
    allocation = full if allocation is None else allocation
    interpretations, saved = [], []
    for index, values in enumerate(rows):
        kind, applicability, mask = values[:3]
        relation, disposition = values[3:] if len(values) > 3 else ('strengthens', 'supported')
        observation = store.put('observation', {'subject_refs': [sample['id']],
            'source_subject_refs': [sample['id']], 'kind': kind, 'source_ref': source['id'],
            'measurements': [], 'dependencies': [], 'anchor': None}, origin='external')
        hypothesis = store.put('hypothesis', {'subject_refs': [sample['id']],
            'predicate': 'biological_role', 'value': {'type': 'enum', 'value': ('growth', 'present', 'intact')[index]},
            'context_refs': []}, origin='reasoning')
        assessment = store.put('assessment', {'hypothesis_ref': hypothesis['id'],
            'observation_ref': observation['id'], 'relation': relation, 'applicability': applicability,
            'extent_basis': 'context_allocation', 'context_account_scope': account,
            'context_scope': mask, 'condition_refs': [], 'assumption_refs': [],
            'expected_revision': 0}, origin='reasoning')
        interpretations.append({'hypothesis_ref': hypothesis['id'], 'disposition': disposition,
                                'assessment_refs': [assessment['id']]})
        saved.append((observation, hypothesis, assessment))
    annotation = store.put('annotation', {'subject_ref': sample['id'],
        'footprint_kind': 'whole_input_context', 'context_account_scope': account,
        'context_scope': allocation, 'coherent_sets': [{'interpretations': interpretations,
            'context_refs': []}], 'alternative_refs': [], 'resolution': 'selected',
        'expected_revision': 0}, origin='reasoning')
    return annotation, saved


def test_full_context_summary_uses_descriptor_without_native_dimensions(tmp_path, monkeypatch):
    store, target, members, source, sample = library_fixture(tmp_path)
    with store:
        full = {'subject_refs': [target['id']]}
        annotation, saved = context_account(store, target, source, sample, 'growth', [
            ('growth_assay', 'direct', full)])
        original_get = store.get
        def no_read_subject(ref):
            if ref.startswith('read_subject_'):
                pytest.fail('full-context summary resolved an untouched original read')
            return original_get(ref)
        monkeypatch.setattr(store, 'get', no_read_subject)
        monkeypatch.setattr(store, 'iter_scope_coverage', lambda *a, **k: pytest.fail('enumerated scope'))
        monkeypatch.setattr(store, 'context_mask_target_query', lambda *a, **k: pytest.fail('enumerated full context'))
        monkeypatch.setattr(store, 'get_artifact', lambda *a, **k: pytest.fail('hydrated source artifact'))
        projected = project_credit(store)
        assert projected.credit == pytest.approx(100*softened_hypervolume({'empirical': 1}))
        assert projected.axis_components['empirical'] == 1
        assert projected.targets[0]['scoped_length'] == projected.targets[0]['projected_footprint_units'] == 20
        assert projected.detail_pages['source_contributions']['total'] == 3
        assert projected.source_contributions == ()
        assert store.get(saved[0][0]['id']) == saved[0][0]
        assert store.get(annotation['id'])['footprint'] == []


def test_context_native_axes_refutation_and_explicit_detail_provenance(tmp_path):
    store, target, members, source, sample = library_fixture(tmp_path)
    with store:
        full = {'subject_refs': [target['id']]}
        annotation, saved = context_account(store, target, source, sample, 'counterevidence', [
            ('growth_assay', 'direct', full, 'weakens', 'weakened'),
            ('reaction_context', 'contextual', full)])
        projected = project_credit(store, details_limit=100)
        expected = {'empirical': 1, 'mechanistic': .35, 'discrimination': 1}
        assert projected.credit == pytest.approx(100*softened_hypervolume(expected))
        assert projected.axis_components == {axis: expected.get(axis, 0) for axis in AXES}
        assert projected.detail_pages['source_contributions']['total'] == len(members)*3
        assert {row['observation_kind'] for row in projected.source_contributions} == {'growth_assay', 'reaction_context'}
        for row in projected.source_contributions:
            assert row['annotation_ref'] == annotation['id']
            assert row['footprint'] == []
            assert row['attribution_space'] == 'material_context'
            assert row['source_subject_refs'] == row['observation_subject_refs'] == [sample['id']]
            assert row['source_ref'] == source['id']
            assert 'contributing_segments' not in row
            assert row['contributing_context_segments'] == [{
                'target_ref': target['id'], 'member_ref': row['member_ref'], 'unit': 'nt',
                'start': 0, 'end': next(m['length'] for m in members if m['member_ref'] == row['member_ref'])}]
        assert all(store.get(observation['id']) == observation for observation, _, _ in saved)


def test_compact_masks_overlap_and_local_molecular_envelope_match_position_oracle(tmp_path):
    store, target, members, source, sample = library_fixture(tmp_path)
    with store:
        a, b, c = members
        full = {'subject_refs': [target['id']]}
        ab, bc = select_mask(store, target, [a, b]), select_mask(store, target, [b, c])
        # Different actual subjects make separate scientific accounts, while
        # two declared rows of ONE account can combine on their exact overlap.
        combined, _ = context_account(store, target, source, sample, 'joint', [
            ('growth_assay', 'transfer', ab), ('reaction_context', 'direct', bc)])
        other_sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic other account',
            'source_ref': source['id'], 'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')
        base, _ = context_account(store, target, source, other_sample, 'baseline', [
            ('context_measurement', 'contextual', full)])
        # Actual proper interval: a context mask is allocation, not a molecular map.
        partial = {'subject_refs': [target['id']], 'segments': [{
            'target_ref': target['id'], 'member_ref': c['member_ref'], 'unit': 'nt', 'start': 3, 'end': 8}]}
        third_sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic interval account',
            'source_ref': source['id'], 'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')
        interval, _ = context_account(store, target, source, third_sample, 'interval', [
            ('growth_assay', 'direct', partial), ('reaction_context', 'direct', partial)], allocation=partial)
        # One local physical account with two compatible native source kinds.
        read = store.get(c['dimension_ref'])
        feature = store.put('feature', {'subject_ref': read['id'], 'kind': 'CDS',
            'segments': [{'start': 1, 'end': 4}], 'strand': '+', 'context_refs': []}, origin='reasoning')
        local_interpretations = []
        for kind in ('alignment', 'mechanism'):
            observation = store.put('observation', {'subject_refs': [feature['id']],
                'source_subject_refs': [feature['id']], 'kind': kind, 'source_ref': source['id'],
                'measurements': [], 'dependencies': [], 'anchor': None}, origin='tool')
            hypothesis = store.put('hypothesis', {'subject_refs': [feature['id']], 'predicate': 'biological_role',
                'value': {'type': 'enum', 'value': 'positive' if kind == 'alignment' else 'present'}, 'context_refs': []}, origin='reasoning')
            assessment = store.put('assessment', {'hypothesis_ref': hypothesis['id'],
                'observation_ref': observation['id'], 'relation': 'strengthens', 'applicability': 'direct',
                'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
                'expected_revision': 0}, origin='reasoning')
            local_interpretations.append({'hypothesis_ref': hypothesis['id'], 'disposition': 'supported',
                                          'assessment_refs': [assessment['id']]})
        local = store.put('annotation', {'subject_ref': feature['id'], 'footprint_kind': 'localized',
            'coherent_sets': [{'interpretations': local_interpretations, 'context_refs': []}],
            'alternative_refs': [], 'resolution': 'selected', 'expected_revision': 0}, origin='reasoning')
        # Tiny explicit-position oracle is deliberately restricted to this fixture.
        expected, integral, axes = {}, 0., dict.fromkeys(AXES, 0.)
        for member in members:
            for position in range(member['length']):
                vector = {'empirical': .6 if member in (a, b) else 0,
                          'mechanistic': 1 if member in (b, c) else 0}
                candidates = [(combined['id'], vector), (base['id'], {'biological_context': .35})]
                if member == c and 3 <= position < 8:
                    candidates.append((interval['id'], {'empirical': 1, 'mechanistic': 1}))
                if member == c and 1 <= position < 4:
                    candidates.append((local['id'], {'comparative': 1, 'mechanistic': 1}))
                winner, components = min(candidates, key=lambda item: (-softened_hypervolume(item[1]), item[0]))
                value = softened_hypervolume(components)
                expected[member['member_ref'], position] = (winner, value)
                integral += value
                for axis in AXES:
                    axes[axis] += components.get(axis, 0)
        summary = project_credit(store)
        assert summary.credit == pytest.approx(100*integral/20)
        assert summary.axis_components == pytest.approx({axis: value/20 for axis, value in axes.items()})
        details = project_credit(store, details_limit=100)
        assert details.credit == summary.credit
        assert details.detail_pages['state_basis_sha256'] == summary.detail_pages['state_basis_sha256']
        seen = set()
        for row in details.source_contributions:
            segment, = row.get('contributing_context_segments', row.get('contributing_segments'))
            for position in range(segment['start'], segment['end']):
                assert expected[row['member_ref'], position][0] == row['annotation_ref']
                seen.add((row['member_ref'], position))
        assert seen == set(expected)
        assert details.detail_pages['source_contributions']['total'] == len(details.source_contributions)
        paged = []
        for offset in range(len(details.source_contributions)):
            page = project_credit(store, details_limit=1, details_offset=offset)
            assert page.credit == summary.credit
            paged.extend(page.source_contributions)
        assert paged == list(details.source_contributions)
        # Exact child denominator and clipping use the same frozen projection.
        child = project_credit(store, {'subject_refs': [target['id']], 'segments': [{
            'target_ref': target['id'], 'member_ref': c['member_ref'], 'unit': 'nt', 'start': 2, 'end': 7}]}, details_limit=100)
        assert child.targets[0]['scoped_length'] == 5
        assert child.credit == pytest.approx(100*sum(expected[c['member_ref'], p][1] for p in range(2, 7))/5)
        assert all(2 <= segment['start'] < segment['end'] <= 7 for row in child.source_contributions
                   for segment in row.get('contributing_context_segments', row.get('contributing_segments')))


def revision_payload(row):
    from gene_annotation_episode.domain import RECORD_SCHEMAS
    payload = {key: deepcopy(value) for key, value in row.items()
               if key in RECORD_SCHEMAS[row['record_type']]['properties']}
    if row['record_type'] == 'annotation':
        for group in payload['coherent_sets']:
            group.pop('id', None)
    payload['expected_revision'] = row['revision']
    return payload


def test_current_allocation_corrections_and_stale_links_have_signed_credit(tmp_path):
    from gene_annotation_episode.numerical import YieldController
    store, target, members, source, sample = library_fixture(tmp_path)
    with store:
        full = {'subject_refs': [target['id']]}
        only_a = select_mask(store, target, members[:1])
        empty = {'subject_refs': []}
        annotation, saved = context_account(store, target, source, sample, 'lineage', [
            ('growth_assay', 'direct', full)])
        observation, hypothesis, assessment = saved[0]
        first = project_credit(store)
        unit = first.credit
        controller = YieldController('synthetic-selected-revisions', unit, .001)
        history = []
        for mask, expected in [(only_a, unit*.2), (empty, 0), (full, unit)]:
            payload = revision_payload(annotation)
            payload['context_scope'] = mask
            annotation = store.put('annotation', payload, origin='reasoning')
            projected = project_credit(store, details_limit=100)
            assert projected.credit == pytest.approx(expected)
            history.append(controller.observe('annotation-revision-'+str(annotation['revision']), projected).marginal_credit)
            if not mask['subject_refs']:
                assert projected.targets[0]['projected_footprint_units'] == 0
                assert projected.inactive_dependencies[0]['reason'] == 'context_allocation_empty'
                assert projected.detail_pages['state_basis_sha256'] != first.detail_pages['state_basis_sha256']
        assert history == pytest.approx([-unit*.8, -unit*.2, unit])
        # An exact old assessment link does not silently follow a new revision.
        original_assessment = deepcopy(assessment)
        for mask, expected in [(only_a, unit*.2), (empty, 0), (full, unit)]:
            payload = revision_payload(assessment)
            payload['context_scope'] = mask
            assessment = store.put('assessment', payload, origin='reasoning')
            stale = project_credit(store, details_limit=100)
            assert stale.credit == 0
            assert stale.inactive_dependencies[0]['reason'] == 'not_current_assessment_revision'
            payload = revision_payload(annotation)
            payload['coherent_sets'][0]['interpretations'][0]['assessment_refs'] = [assessment['id']]
            annotation = store.put('annotation', payload, origin='reasoning')
            current = project_credit(store, details_limit=100)
            assert current.credit == pytest.approx(expected)
            if mask['subject_refs']:
                assert {row['assessment_ref'] for row in current.source_contributions} == {assessment['id']}
            else:
                assert current.inactive_dependencies[0]['reason'] == 'context_allocation_empty'
        assert store.get(original_assessment['id']) == original_assessment
        assert store.get(observation['id']) == observation
        assert store.get(hypothesis['id']) == hypothesis
        assert store.count('annotation', current=True) == store.count('assessment', current=True) == 1
        payload = revision_payload(annotation)
        payload.pop('context_scope')
        annotation = store.put('annotation', payload, origin='reasoning')
        unlocalized = project_credit(store, details_limit=100)
        assert unlocalized.credit == 0
        assert unlocalized.inactive_dependencies[0]['reason'] == 'context_allocation_unlocalized'
        assert unlocalized.inactive_dependencies[0]['allocation_owner'] == 'annotation'
        assert 'context_scope' not in store.get(annotation['id'])
        payload = revision_payload(annotation)
        payload['context_scope'] = full
        annotation = store.put('annotation', payload, origin='reasoning')
        assert project_credit(store).credit == pytest.approx(unit)
        frozen = project_credit(store, details_limit=100).as_record()
    with Store(tmp_path / 'state') as reopened:
        assert project_credit(reopened, details_limit=100).as_record() == frozen


def test_scalar_mixed_declared_account_uses_same_cell_integral_in_all_views(tmp_path):
    with Store(tmp_path / 'scalar') as store:
        target_ref = store.create_problem(raw_sequence='ACGTACGTAA', molecule='dna')['subject_refs'][0]
        target = store.get(target_ref)
        full = {'subject_refs': [target_ref]}
        source = source_fixture(store, 'scalar-mixed-account')
        annotation, saved = context_account(store, target, source, target, 'scalar-context', [
            ('growth_assay', 'transfer', full)])
        observation = store.put('observation', {'subject_refs': [target_ref],
            'source_subject_refs': [target_ref], 'kind': 'mechanism', 'source_ref': source['id'],
            'measurements': [], 'dependencies': [], 'anchor': None}, origin='tool')
        hypothesis = store.put('hypothesis', {'subject_refs': [target_ref], 'predicate': 'sequence_integrity',
            'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []}, origin='reasoning')
        assessment = store.put('assessment', {'hypothesis_ref': hypothesis['id'], 'observation_ref': observation['id'],
            'relation': 'strengthens', 'applicability': 'direct', 'extent_basis': 'observed_extent',
            'target_footprint': [{'target_ref': target_ref, 'unit': 'nt', 'start': 1, 'end': 4}],
            'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0}, origin='reasoning')
        payload = revision_payload(annotation)
        payload['coherent_sets'][0]['interpretations'].append({'hypothesis_ref': hypothesis['id'],
            'disposition': 'supported', 'assessment_refs': [assessment['id']]})
        annotation = store.put('annotation', payload, origin='reasoning')
        policy = CreditPolicy(epsilon=.37, scale=7, target_weights=((target_ref, 2),))
        expected = policy.scale*(.7*softened_hypervolume({'empirical': .6}, policy)
            + .3*softened_hypervolume({'empirical': .6, 'mechanistic': 1}, policy))
        full_view = project_credit(store, policy=policy)
        summary = project_credit(store, policy=policy, details_limit=0)
        details = project_credit(store, policy=policy, details_limit=100)
        assert full_view.credit == summary.credit == details.credit == pytest.approx(expected)
        assert full_view.axis_components == details.axis_components
        assert full_view.axis_components['empirical'] == .6
        assert full_view.axis_components['mechanistic'] == .3
        assert any(row.get('attribution_space') == 'material_context' and row['footprint'] == []
                   for row in details.source_contributions)
        physical = [row for row in details.source_contributions if row['assessment_ref'] == assessment['id']]
        assert len(physical) == 1
        assert physical[0]['contributing_segments'] == [{'target_ref': target_ref, 'unit': 'nt', 'start': 1, 'end': 4}]
        assert physical[0]['footprint'] == [{'target_ref': target_ref, 'unit': 'nt', 'start': 1, 'end': 4}]
        scope = {'subject_refs': [target_ref], 'segments': [
            {'target_ref': target_ref, 'unit': 'nt', 'start': 2, 'end': 7}]}
        clipped = project_credit(store, scope, policy, details_limit=100)
        assert clipped.targets[0]['scoped_length'] == 5
        assert clipped.credit == pytest.approx(policy.scale*(.6*softened_hypervolume({'empirical': .6}, policy)
            + .4*softened_hypervolume({'empirical': .6, 'mechanistic': 1}, policy)))
        assert all(2 <= segment['start'] < segment['end'] <= 7 for row in clipped.source_contributions
            for segment in row.get('contributing_context_segments', row.get('contributing_segments')))


def test_scalar_empty_partial_scope_retains_fixed_mass_without_candidates(tmp_path):
    with Store(tmp_path / 'empty-scalar') as store:
        ref = store.create_problem(raw_sequence='ACGTACGTAA', molecule='dna')['subject_refs'][0]
        scope = {'subject_refs': [ref], 'segments': [{'target_ref': ref, 'unit': 'nt', 'start': 2, 'end': 6}]}
        full = project_credit(store, scope)
        summary = project_credit(store, scope, details_limit=0)
        assert full.credit == summary.credit == 0
        assert full.targets[0]['scoped_length'] == summary.targets[0]['scoped_length'] == 4
        assert summary.targets[0]['projected_footprint_units'] == 0
        assert summary.detail_pages['source_contributions']['total'] == 0


def test_alias_masks_and_duplicate_interpretations_preserve_source_fraction_once(tmp_path):
    store, target, members, source, sample = library_fixture(tmp_path)
    with store:
        a, b, _ = members
        full = {'subject_refs': [target['id']]}
        ab = select_mask(store, target, [a, b])
        single_a, single_b = select_mask(store, target, [a]), select_mask(store, target, [b])
        alias = {'subject_refs': [target['id']], 'read_selection_refs': [
            single_b['read_selection_refs'][0], single_a['read_selection_refs'][0],
            single_b['read_selection_refs'][0]]}
        assert store.context_mask_identity(ab) == store.context_mask_identity(alias)
        reference = store.put('reference', {'reference_type': 'dna', 'source_ref': source['id'],
            'accession': 'synthetic-physical-source', 'label': 'Synthetic source sequence',
            'sequence_ref': store.artifact('ACGTA'), 'molecule': 'dna', 'length': 5,
            'term_refs': [], 'context_refs': []}, origin='external')
        interval = {'role': 'query', 'subject_ref': reference['id'], 'start': 1, 'end': 3, 'unit': 'nt'}
        observation = store.put('observation', {'subject_refs': [reference['id']],
            'source_subject_refs': [], 'kind': 'comparison', 'source_ref': source['id'],
            'measurements': [{'name': 'query_coverage', 'value': {'type': 'number', 'value': .4, 'unit_ref': None}}],
            'dependencies': [], 'anchor': None, 'operand_intervals': [interval]}, origin='tool')
        interpretations = []
        for value, mask in [('growth', ab), ('present', alias)]:
            hypothesis = store.put('hypothesis', {'subject_refs': [sample['id']], 'predicate': 'biological_role',
                'value': {'type': 'enum', 'value': value}, 'context_refs': []}, origin='reasoning')
            assessment = store.put('assessment', {'hypothesis_ref': hypothesis['id'],
                'observation_ref': observation['id'], 'relation': 'strengthens', 'applicability': 'transfer',
                'extent_basis': 'context_allocation', 'context_account_scope': full, 'context_scope': mask,
                'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0}, origin='reasoning')
            interpretations.append({'hypothesis_ref': hypothesis['id'], 'disposition': 'supported',
                                    'assessment_refs': [assessment['id']]})
        annotation = store.put('annotation', {'subject_ref': sample['id'], 'footprint_kind': 'whole_input_context',
            'context_account_scope': full, 'context_scope': full,
            'coherent_sets': [{'interpretations': interpretations[:1], 'context_refs': []}],
            'alternative_refs': [], 'resolution': 'selected', 'expected_revision': 0}, origin='reasoning')
        baseline = project_credit(store, details_limit=100)
        payload = revision_payload(annotation)
        payload['coherent_sets'][0]['interpretations'] = interpretations
        store.put('annotation', payload, origin='reasoning')
        duplicate = project_credit(store, details_limit=100)
        assert duplicate.credit == baseline.credit == pytest.approx(
            100*.5*softened_hypervolume({'comparative': .6*.4}))
        assert duplicate.targets[0]['projected_footprint_units'] == 10
        assert len(duplicate.source_contributions) == 2
        for row in duplicate.source_contributions:
            assert row['weight'] == .6*.4
            assert row['source_extent_factor'] == .4
            assert row['source_operand_intervals'] == [interval]
            assert row['source_operand_mappings'][0]['physical_source_segments'] == [{
                'subject_ref': reference['id'], 'unit': 'nt', 'start': 1, 'end': 3, 'strand': '+'}]
            assert row['footprint'] == []
            assert row['source_subject_refs'] == []
            assert row['observation_subject_refs'] == [reference['id']]
            assert row['member_ref'] in (a['member_ref'], b['member_ref'])
