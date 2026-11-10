"""Original experimental roles join sequence evidence without relabelling cells.

These checks exercise saved publications and receipt boundaries. The synthetic
assays and local component calculations are not autonomous/HPC run evidence.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode import a107_qualification as partner
from gene_annotation_episode import a110_qualification as chemistry
from gene_annotation_episode import a110_experimental_qualification as experimental
from gene_annotation_episode import component_source_identity as identity
from gene_annotation_episode.a107_expression_components import calculate as expression_components
from gene_annotation_episode.a110_chemical_accounting import calculate as chemical_components
from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.component_axis_native_hpc import publish, RESULT_PROVIDER
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository, reaction_cells_schema
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from test_component_identity_regions import reference
from test_literature_partner_integration import setup_case as partner_case, binding_for as partner_binding
from test_literature_reaction_integration import setup_case as reaction_case, binding_for as reaction_binding, source
from test_literature_perturbation_assessments import identify
from test_scientific_hypervolume_runtime import assessment


FIXTURES = Path(__file__).parent / 'fixtures/a107_evaluation'


def observation(store, source_ref, subjects, *, end=None):
    record = store.get(source_ref)
    artifact = record.get('text_ref') or record['artifact_ref']
    content = store.get_artifact(artifact)
    end = len(content) if end is None else end
    return store.put('observation', {'subject_refs': [subjects[0]],
        'source_subject_refs': list(subjects), 'kind': 'source_content',
        'source_ref': source_ref, 'measurements': [], 'dependencies': [],
        'anchor': {'source_ref': source_ref, 'artifact_ref': artifact,
            'start': 0, 'end': end, 'quote': content[:end].decode('utf-8')}}, origin='extracted')['id']


def received_case(tmp_path, axis, *, finding_experiment=True):
    sequence = ''.join((FIXTURES / 'anonymous-case-01.faa').read_text().splitlines()[1:])
    if axis == 'A107':
        store, context, population = partner_case(tmp_path, case='matched',
            components=['partner_loss'], target_sequence=sequence)
        repository = LiteraturePartnerRepository(store, context.run_id)
        cells_schema, binding = partner_cells_schema, partner_binding
        components, experiment_type = ['partner_loss'], 'partner_requirement'
    else:
        store, context, population = reaction_case(tmp_path, target_sequence=sequence)
        context = replace(context, assignment={**context.assignment, 'requested_reaction_components': ['ratio_mean']})
        repository = LiteratureReactionRepository(store, context.run_id)
        cells_schema, binding = reaction_cells_schema, reaction_binding
        components, experiment_type = ['ratio_mean'], 'reaction_prediction'
    context, population = identify(store, context, population, 'selected-assay')
    population['experiment_assessment'].update(experiment_type=experiment_type,
        assessment_key='particular-source-question')
    experiment = population['experiment_assessment']['experiment_ref']
    outcome = repository.populate(context, population, 'original-assay')
    sheet = outcome['result']['sheet_ref']
    cells = repository.project_cells([sheet], permitted_record_refs=outcome['record_refs'], components=components)
    subject = cells[0]['subject_ref' if axis == 'A107' else 'assayed_subject_ref']
    role = cells[0]['partner_ref'] if axis == 'A107' else subject
    target, = context.scope['subject_refs']
    reaction = None
    if axis == 'A110':
        reaction = store.put('term', {'namespace': 'synthetic_reaction', 'accession': 'reaction-one',
            'label': 'synthetic reaction', 'term_type': 'reaction',
            'source_ref': population['source_ref'], 'anchor': None}, origin='caller')['id']
    witness = observation(store, population['source_ref'], [subject, *([experiment] if finding_experiment else [])])
    claim = {'subject_refs': [subject], 'predicate': 'requires' if axis == 'A107' else 'catalyzes',
        'value': {'type': 'reference', 'ref': role if axis == 'A107' else reaction}, 'context_refs': []}
    hypothesis = store.put('hypothesis', {**claim, 'subject_refs': [target]}, origin='reasoning')['id']
    proposed = assessment(hypothesis, witness, 'incomparable')
    proposed['relation'] = 'does_not_discriminate'
    proposed['investigation_finding'] = {'source_claim': claim,
        'qualification': {'kind': 'different_source_subject', 'context_refs': [], 'assumption_refs': []},
        'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
        'same_source_claim_as_ref': None, 'replaces_refs': []}
    finding = store.put('assessment', proposed, origin='reasoning')['id']
    known = {target, subject, role, experiment, hypothesis, witness, finding,
        *context.received_record_refs, *outcome['record_refs']}
    if reaction is not None:
        known.add(reaction)
    context = replace(context, received_record_refs=tuple(sorted(known)))
    schema = obj({'measurements': cells_schema()})
    episode = binding(store, context)
    form = form_with_facts({}, schema, episode.facts(context, {'committed_record_refs': [sheet]}))
    assert form['measurements'] == cells
    parent = replace(context, episode_id='particular-evidence-parent', role='annotation',
        path=(('annotation', 'root'),), assignment={})
    episode.received_form_references(parent, form, schema, 'original-numerical-receipt')
    return {'store': store, 'context': parent, 'known': known, 'axis': axis, 'target': target,
        'role': role, 'subject': subject, 'experiment': experiment, 'sheet': sheet, 'cells': cells,
        'repository': repository, 'original_sheet': deepcopy(repository.read(sheet)),
        'sequence': sequence, 'finding': finding, 'reaction': reaction}


def declaration(case, *, sequence=None, quoted_sequence=None, named_role=None,
                link_role=True, link_experiment=True, scope='whole_protein'):
    store = case['store']
    sequence = case['sequence'] if sequence is None else sequence
    actual = reference(store, sequence)
    label = store.get(case['role'])['label'] if named_role is None else named_role
    quoted_sequence = sequence if quoted_sequence is None else quoted_sequence
    text = f'{label}: declared synthetic assayed protein sequence.\n>declared-protein\n{quoted_sequence}\n\nEnd of sequence declaration.\n'
    evidence = source(store, text)
    subjects = [case['role'] if link_role else case['subject'], actual]
    if link_experiment:
        subjects.append(case['experiment'])
    observed = observation(store, evidence['id'], subjects)
    case['known'].update([actual, store.get(actual)['source_ref'], evidence['id'], observed])
    return {'target_ref': case['target'], 'source_role_ref': case['role'], 'actual_ref': actual,
        'observation_ref': observed, 'experiment_ref': case['experiment'], 'identity_scope': scope,
        'revises_identity_ref': None, 'revision_reason': None}


def qualify(case, operation, arguments):
    store, known = case['store'], case['known']
    context = replace(case['context'], received_record_refs=tuple(sorted(known)))
    if case['axis'] == 'A107':
        request = partner.request(store, operation, arguments, context=context, known=known)
        refresh, read = partner.refresh, lambda ref: partner._read(store, ref, graded=True)
    elif operation in {identity.TOOLS['A110'], chemistry.TOOL}:
        create = chemistry.source_identity_request if operation == identity.TOOLS['A110'] else chemistry.request
        request = create(store, arguments, context=context, known=known)
        refresh, read = chemistry.refresh, lambda ref: chemistry.read(store, ref, qualified=True)
    else:
        request = experimental.request(store, arguments, context=context, known=known)
        refresh, read = experimental.refresh, lambda ref: experimental.read(store, ref, qualified=True)
    known.add(request)
    context = replace(context, received_record_refs=tuple(sorted(known)))
    generated, needs = refresh(store, context, known)
    qualified, = [(ref, read(ref)) for ref in generated if read(ref)['request_ref'] == request]
    reference_ref, body = qualified
    known.add(reference_ref)
    assert source_tool_grading_entries(store, reference_ref)[0]['grading']['sheet'] == body
    return reference_ref, body, needs


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_identity_requires_original_role_and_native_sequence_witness(tmp_path, axis):
    case = received_case(tmp_path, axis)
    with case['store'] as store:
        original_role = deepcopy(store.get(case['role']))
        arguments = declaration(case)
        ref, body, _ = qualify(case, identity.TOOLS[axis], arguments)
        result = body['result']
        assert result['state'] == 'source_sequence_identity_retained', result
        assert not result['missing']
        assert result['native_sequence_witness']['candidate']['normalized_sequence'] == case['sequence']
        assert result['source_role_ref'] == case['role']
        assert result['actual_ref'] == arguments['actual_ref'] != case['role']
        assert store.get(case['role']) == original_role
        assert original_role['sequence_ref'] is None and original_role['molecule'] is None
        narrowed = {ref, case['role'], case['experiment'], arguments['observation_ref']}
        use, used_refs = identity.use(store, ref, case['role'], narrowed, experiment_refs=[case['experiment']])
        assert use['required_record_refs'] == [arguments['actual_ref']]
        assert arguments['actual_ref'] not in used_refs
        assert 'source_identity_endpoints_not_received' in use['missing']


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_complete_identity_quote_can_end_at_last_residue(tmp_path, axis):
    case = received_case(tmp_path, axis)
    with case['store'] as store:
        original_role = deepcopy(store.get(case['role']))
        arguments = declaration(case)
        original = store.get(arguments['observation_ref'])
        content = store.get_artifact(original['anchor']['artifact_ref'])
        sequence = case['sequence'].encode()
        end = content.index(sequence) + len(sequence)
        assert content[end:end + 2] == b'\n\n'  # Delimiter context is outside the selected quote.
        selected = observation(store, original['source_ref'],
            [case['role'], arguments['actual_ref'], case['experiment']], end=end)
        case['known'].add(selected)
        arguments['observation_ref'] = selected
        _, body, _ = qualify(case, identity.TOOLS[axis], arguments)
        result = body['result']
        assert result['state'] == 'source_sequence_identity_retained', result
        assert not result['missing']
        assert result['native_sequence_witness']['candidate']['end'] == end
        assert result['native_sequence_witness']['candidate']['normalized_sequence'] == case['sequence']
        assert result['source_declaration_anchor'] == store.get(selected)['anchor']
        assert store.get(case['role']) == original_role


@pytest.mark.parametrize('variant', ['inline_tail', 'wrapped_tail', 'cropped_quote', 'later_match'])
def test_boundary_context_does_not_admit_a_sequence_outside_the_selected_quote(tmp_path, variant):
    case = received_case(tmp_path, 'A107')
    with case['store'] as store:
        sequence = case['sequence']
        wrong = ('A' if sequence[0] != 'A' else 'M') + sequence[1:]
        quoted = {'inline_tail': sequence + 'GGGGGGGG',
            'wrapped_tail': sequence + '\nGGGGGGGG',
            'cropped_quote': sequence,
            'later_match': wrong + '\n\n>another-protein\n' + sequence}[variant]
        arguments = declaration(case, quoted_sequence=quoted)
        original = store.get(arguments['observation_ref'])
        content = store.get_artifact(original['anchor']['artifact_ref'])
        first = wrong if variant == 'later_match' else sequence
        end = content.index(first.encode()) + len(first.encode())
        if variant == 'cropped_quote':
            end -= 1
        selected = observation(store, original['source_ref'],
            [case['role'], arguments['actual_ref'], case['experiment']], end=end)
        case['known'].add(selected)
        arguments['observation_ref'] = selected
        _, body, _ = qualify(case, identity.TOOLS['A107'], arguments)
        assert body['result']['state'] == 'source_identity_unresolved'
        assert body['result']['native_sequence_witness'] is None
        assert 'actual_assayed_protein_sequence_not_established' in body['result']['missing']


@pytest.mark.parametrize('variant,expected', [
    ('name_only', 'actual_assayed_protein_sequence_not_established'),
    ('other_sequence', 'actual_assayed_protein_sequence_not_established'),
    ('other_label', 'identity_declaration_does_not_name_original_source_role'),
    ('other_experiment', 'declaration_not_bound_to_selected_experiment'),
    ('component_only', 'whole_assayed_entity_identity_not_established'),
])
def test_unsupported_declarations_remain_explicitly_unresolved(tmp_path, variant, expected):
    case = received_case(tmp_path, 'A107')
    with case['store']:
        changes = {'name_only': {'quoted_sequence': 'sequence not supplied'},
            'other_sequence': {'quoted_sequence': ('A' if case['sequence'][0] != 'A' else 'M') + case['sequence'][1:]},
            'other_label': {'named_role': 'Unrelated source role'},
            'other_experiment': {'link_experiment': False},
            'component_only': {'scope': 'protein_component'}}
        arguments = declaration(case, **changes[variant])
        _, body, needs = qualify(case, identity.TOOLS['A107'], arguments)
        assert body['result']['state'] == 'source_identity_unresolved'
        assert expected in body['result']['missing']
        assert needs


def test_unreceived_declaration_source_cannot_be_privately_opened(tmp_path, monkeypatch):
    case = received_case(tmp_path, 'A107')
    with case['store'] as store:
        arguments = declaration(case)
        source_ref = store.get(arguments['observation_ref'])['source_ref']
        case['known'].remove(source_ref)
        original = store.get
        def received_only(ref, *args, **kwargs):
            assert ref != source_ref, 'unreceived source was privately opened'
            return original(ref, *args, **kwargs)
        monkeypatch.setattr(store, 'get', received_only)
        with pytest.raises(ContractError, match='source_not_received'):
            identity.calculate(store, arguments, case['context'], case['known'])


@pytest.mark.parametrize('finding_experiment', [False, True])
def test_required_component_identity_joins_expression_without_changing_measurements(tmp_path, finding_experiment):
    case = received_case(tmp_path, 'A107', finding_experiment=finding_experiment)
    with case['store'] as store:
        identity_ref, _, _ = qualify(case, identity.TOOLS['A107'], declaration(case))
        requirement, body, _ = qualify(case, 'partner.requirement_evidence', {
            'target_ref': case['target'], 'assessment_ref': case['finding'],
            'component_ref': case['role'], 'sheet_ref': case['sheet'], 'components': ['partner_loss'],
            'component_identity_ref': identity_ref})
        assert body['result']['partner_components'] == case['cells']
        assert bool(body['result']['missing']) is (not finding_experiment)
        assert body['result']['source_role_identities']['component']['identity_ref'] == identity_ref
        document = json.loads((FIXTURES / 'declared-expression-panel.json').read_text())
        native = expression_components(document, {'condition_key': 'c1', 'left_feature_id': 'left',
            'right_feature_id': 'right', 'sample_ids': ['s1', 's2', 's3', 's4']})
        expression = publish(store, RESULT_PROVIDER, {'axis': 'A107',
            'scientific_profile': 'a107_expression_components_v2', 'scope': plain(case['context'].scope),
            'operation': 'partner.request_expression_hpc', 'native_components': native})
        case['known'].add(expression)
        _, result, _ = qualify(case, 'partner.expression_evidence', {
            'target_ref': case['target'], 'expression_ref': expression, 'feature_side': 'left',
            'actual_ref': case['target'], 'component_ref': case['target'],
            'encoded_product_ref': None, 'positions': list(range(20, 40)), 'alignment_ref': None,
            'requirement_ref': requirement})
        result = result['result']
        attached = result['source_requirement_use']
        assert attached['state'] == ('required_component_sequence_link_retained' if finding_experiment
            else 'required_component_application_unresolved'), attached
        assert attached['source_requirement_limitations'] == body['result']['missing']
        assert attached['exact_declared_required_sequence_matches_measured_sequence']
        assert attached['condition_transfer'] == 'not_established_by_molecular_identity_or_sequence_detection'
        assert result['native_components'] == native['components']
        assert result['dependence'] == native['dependence']
        assert result['biological_scope'].startswith('whole_measured_feature_quantity;')
        assert case['repository'].read(case['sheet']) == case['original_sheet']

        revised = declaration(case, scope='protein_component')
        revised.update(revises_identity_ref=identity_ref,
            revision_reason='The sequence identifies a component; the whole assayed entity is unresolved.')
        correction, _, _ = qualify(case, identity.TOOLS['A107'], revised)
        current, = partner.received_qualifications(store, [requirement], case['context'].scope,
            full=True, known_record_refs=case['known'])
        assert not current['current'] and current['source_identity_change_refs'] == [correction]
        narrow, = partner.received_qualifications(store, [requirement], case['context'].scope,
            full=True, known_record_refs=case['known'] - {correction})
        assert narrow['current']
        assert partner._read(store, requirement, graded=True) == body


def test_paged_repeated_source_sequence_is_one_dependent_identity(tmp_path):
    case = received_case(tmp_path, 'A107')
    with case['store'] as store:
        arguments = declaration(case)
        label = store.get(case['role'])['label']
        blocks = ['AAAAAAAAAC' + str(i) + '\n\n' for i in range(12)]
        text = label + ': declared synthetic assayed protein sequence.\n\n' + ''.join(blocks)
        text += '\n\n'.join([case['sequence'], case['sequence']]) + '\n\nEnd of declaration.\n'
        evidence = source(store, text)
        observed = observation(store, evidence['id'], [case['role'], arguments['actual_ref'], case['experiment']])
        case['known'].update([evidence['id'], observed])
        arguments['observation_ref'] = observed
        _, body, _ = qualify(case, identity.TOOLS['A107'], arguments)
        result = body['result']
        assert not result['missing'], result
        witness = result['native_sequence_witness']
        assert len(witness['additional_occurrences']) == 1
        assert witness['dependence'] == 'same_source_declaration; not_independent_experiments'


def test_experimental_reaction_uses_identity_but_preserves_synthetic_and_quantity_scope(tmp_path):
    case = received_case(tmp_path, 'A110')
    with case['store'] as store:
        arguments = declaration(case)
        identity_ref, _, _ = qualify(case, identity.TOOLS['A110'], arguments)
        _, body, _ = qualify(case, experimental.TOOL, {'target_ref': case['target'],
            'sheet_ref': case['sheet'], 'components': ['ratio_mean'], 'reaction_ref': case['reaction'],
            'assessment_ref': case['finding'], 'actual_ref': arguments['actual_ref'],
            'target_subject_ref': case['target'], 'source_alignment_ref': None,
            'alignment_ref': None, 'positions': list(range(20, 40)), 'source_identity_ref': identity_ref})
        result = body['result']
        assert result['selected_components'] == case['cells']
        assert result['source_assayed_subject_ref'] == case['role']
        assert result['measured_subject_correspondence']['source_identity_use']['identity_ref'] == identity_ref
        assert not result['measured_subject_correspondence']['missing']
        assert result['component_correspondence']['mapped_pair_count'] == 20
        assert result['experiment_binding']['state'] == 'matched'
        assert result['missing'] == ['synthetic_inputs_do_not_establish_physical_application']
        assert body['scientific_credit'] is None
        assert case['repository'].read(case['sheet']) == case['original_sheet']


@pytest.mark.parametrize('finding_experiment', [False, True])
def test_chemical_accounting_keeps_the_source_identity_experiment_link_separate(tmp_path, finding_experiment):
    case = received_case(tmp_path, 'A110', finding_experiment=finding_experiment)
    with case['store'] as store:
        arguments = declaration(case)
        identity_ref, _, _ = qualify(case, identity.TOOLS['A110'], arguments)
        document = json.loads((FIXTURES.parent / 'a110_evaluation/declared-chemical-panel.json').read_text())
        native = chemical_components(document, {'reaction_ids': ['r01'],
            'include_declared_pathway': False, 'include_reported_constraints': False})
        accounting = publish(store, RESULT_PROVIDER, {'axis': 'A110',
            'scientific_profile': 'a110_chemical_accounting_v2', 'scope': plain(case['context'].scope),
            'operation': 'chemistry.request_accounting_hpc', 'native_components': native})
        case['known'].add(accounting)
        _, body, _ = qualify(case, chemistry.TOOL, {'target_ref': case['target'],
            'accounting_ref': accounting, 'reaction_id': 'r01', 'reaction_ref': case['reaction'],
            'assessment_ref': case['finding'], 'actual_ref': arguments['actual_ref'],
            'target_subject_ref': case['target'], 'alignment_ref': None, 'positions': [20, 21],
            'source_identity_ref': identity_ref})
        result = body['result']
        assert result['native_reaction'] == native['reactions'][0]
        assert result['source_function_finding']['source_claim']['subject_refs'] == [case['role']]
        assert result['source_function_finding']['source_identity_use']['identity_ref'] == identity_ref
        assert result['component_correspondence']['mapped_pair_count'] == 2
        assert ('source_identity_to_function_finding_experiment_link_unestablished' in result['missing']) is (
            not finding_experiment)
        assert body['scientific_credit'] is None
