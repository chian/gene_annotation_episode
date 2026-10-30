"""Synthetic structural boundaries through scalar readers and typed episodes."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_calculations import COMPONENTS
from gene_annotation_episode.literature_partner_native_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_partner_source_fields import (
    convert_source_number, read_source_number, read_source_rate_unit, validate_source_spread_unit,
)
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'b' * 64
FORM = obj({'measurements': partner_cells_schema()})


def sources(text):
    return _Sources(lambda reference, representation: {'artifact_ref': ARTIFACT, 'content': text.encode()})


def witness(text, quote, *, reference=SOURCE):
    start = text.encode().index(quote.encode())
    return {'source_ref': reference, 'representation': 'original', 'start': start,
        'end': start + len(quote.encode()), 'quote': quote}


def selector(text, token, *, quote=None, reference=SOURCE):
    selected = witness(text, token if quote is None else quote, reference=reference)
    start = selected['quote'].index(token)
    return {'witness': selected, 'number_start': start, 'number_end': start + len(token)}


def number(text, token, *, role='rate', quote=None):
    return read_source_number(selector(text, token, quote=quote), sources=sources(text), role=role)


@pytest.mark.parametrize('text,token', [
    ('<table><tr><td>Partner</td><td>7</td></tr></table>', '7'),
    ('<TABLE><TR><TH>Partner</TH><TD class="rate">7</TD></TR></TABLE>', '7'),
    ('<table><tr><td>1</td><td>2</td></tr></table>', '1'),
    ('<table><tr><td>1</td><td>2</td></tr></table>', '2'),
    ('<p>Label</p><p>7</p>', '7'),
    ('<div>Label</div><div>7</div>', '7'),
    ('Label<br/>7<br/>9', '7'),
    ('Label<break/>7', '7'),
])
def test_structural_separators_do_not_join_adjacent_tokens(text, token):
    result = number(text, token)
    assert (result['raw_number'], result['value'], result['relation']) == (token, float(token), 'point')


@pytest.mark.parametrize('marker,relation', [('&lt;', 'lt'), ('&lt;=', 'le'), ('≤', 'le'),
    ('less than', 'lt'), ('at most', 'le')])
@pytest.mark.parametrize('separator', ['<br/>', '<p>', '<div>', '<em>'])
def test_same_cell_qualifiers_survive_structural_and_inline_markup(marker, relation, separator):
    text = '<table><tr><td>' + marker + (' ' if marker[-1:].isalpha() else '') + separator + '7</td></tr></table>'
    assert number(text, '7')['relation'] == relation


@pytest.mark.parametrize('text,role,code', [
    ('<td>not below<br/>7</td>', 'rate', 'negated_source_comparator_unsupported'),
    ('<td>above<br/>7</td>', 'rate', 'lower_bound_source_number_unsupported'),
    ('<td>about<br/>7</td>', 'rate', 'approximate_source_number_unsupported'),
    ('<td>SD=<br/>7</td>', 'rate', 'uncertainty_is_not_rate_point'),
    ('<td>±<br/>7</td>', 'rate', 'uncertainty_is_not_rate_point'),
    ('<td>CV=<br/>7</td>', 'spread', 'relative_spread_unit_unsupported'),
    ('<td>7<br/>%</td>', 'spread', 'relative_spread_unit_unsupported'),
    ('<td>from<br/>7 to 9</td>', 'rate', 'interval_source_number_unsupported'),
])
def test_structural_whitespace_does_not_erase_existing_scalar_guards(text, role, code):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, '7', role=role)
    assert caught.value.code == code


@pytest.mark.parametrize('text', ['<td>between<br>1 and<br>2 nM</td>',
    '<td>between 1<br>and 2 nM</td>', '<td>between<p>1 and<p>2 nM</td>'])
@pytest.mark.parametrize('token', ['1', '2'])
@pytest.mark.parametrize('role', ['rate', 'spread', 'condition'])
def test_structural_markup_does_not_manufacture_an_interval_scope_boundary(text, token, role):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, token, role=role)
    assert caught.value.code == 'interval_source_number_unsupported'


@pytest.mark.parametrize('text,token', [
    ('<em>1</em><b>2</b>', '1'), ('<em>1</em><b>2</b>', '2'),
    ('<td><em>1</em><b>2</b></td>', '2'),
    ('<td><em>1.</em><b>2</b></td>', '2'),
    ('<td><em>1.2</em><b>e-3</b></td>', '1.2'),
    ('<td><em>1.2e-</em><b>3</b></td>', '3'),
    ('<td><em>-</em><b>7</b></td>', '7'),
    ('<td><em>+</em><b>7</b></td>', '7'),
    ('<td>identifier<em>7</em></td>', '7'),
])
def test_inline_tags_cannot_manufacture_a_numeric_separator(text, token):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, token)
    assert caught.value.code == 'partial_source_numeric_token'


@pytest.mark.parametrize('role', ['rate', 'spread', 'condition'])
@pytest.mark.parametrize('text,token', [
    ('<td>-<br>7</td>', '7'), ('<td>+<break/>7</td>', '7'),
    ('<td>−<em><br/></em>7</td>', '7'),
    ('<td>1e<br>-3</td>', '-3'), ('<td>1E<break/>+3</td>', '+3'),
    ('<td>1.2e<br>-3</td>', '-3'),
    ('<td>1<em>e</em><br>-3</td>', '-3'),
    ('<td>1<br><em>e</em>-3</td>', '1'),
    ('<td><em>1.</em><b>2e</b><br>-3</td>', '-3'),
    ('<td>1<br><em>.</em>2</td>', '1'),
    ('<td>1<br>.2</td>', '1'), ('<td>1<br>.2</td>', '.2'),
    ('<td>1.<br>2</td>', '1.'), ('<td>1.<br>2</td>', '2'),
    ('<td>1<br>e-3</td>', '1'),
])
def test_soft_breaks_cannot_hide_numeric_sign_decimal_or_exponent_edges(text, token, role):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, token, role=role)
    assert caught.value.code == 'partial_source_numeric_token'


@pytest.mark.parametrize('text,token', [
    ('<td>Label<br>7</td>', '7'), ('<td>Rate<br>7</td>', '7'),
    ('<td>e<br>7</td>', '7'), ('<td>1<br>2</td>', '1'),
    ('<td>Rat<em>e</em><br>7</td>', '7'),
    ('<td>1<br>2</td>', '2'), ('<td>-</td><td>7</td>', '7'),
    ('<td>1e</td><td>-3</td>', '-3'),
    ('<td>1</td><td>.2</td>', '.2'),
    ('<td>- <br>7</td>', '7'), ('<td>1e <br>-3</td>', '-3'),
    ('<td>1<br>Example</td>', '1'),
])
def test_soft_break_guard_preserves_independent_tokens_and_real_whitespace(text, token):
    assert number(text, token)['value'] == float(token)


def test_plusminus_spread_across_a_soft_break_retains_its_allowed_role():
    text = '<td>Mean 7 +/-<br>1</td>'
    assert number(text, '1', role='spread')['value'] == 1
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, '1')
    assert caught.value.code == 'uncertainty_is_not_rate_point'


def test_real_whitespace_and_utf8_source_custody_are_preserved():
    text = 'µ<table><tr><td>Label</td><td><em>1</em> <b>2</b></td></tr></table>'
    selected = selector(text, '2', quote='<b>2</b>')
    original = deepcopy(selected)
    result = read_source_number(selected, sources=sources(text), role='rate')
    assert selected == original
    assert result['selector']['witness'] == {**selected['witness'], 'artifact_ref': ARTIFACT}
    assert result['selector']['witness']['start'] == text.encode().index(b'<b>2</b>')
    assert result['value'] == 2


@pytest.mark.parametrize('raw', ['nmol/min/mg', 'nmol<br/>min<sup>−1</sup> mg<sup>−1</sup>'])
def test_complete_units_in_adjacent_table_cells_keep_their_own_lexical_edges(raw):
    text = '<table><tr><td>Label</td><td>' + raw + '</td><td>per_min</td></tr></table>'
    result = read_source_rate_unit(witness(text, raw), sources=sources(text))
    assert (result['canonical_unit'], result['multiplier']) == ('pmol/min/mg', 1000)
    assert result['raw_unit'] == raw


@pytest.mark.parametrize('raw', ['<td>nmol/min/mg</td>',
    '<TH class="unit">nmol/min/mg</TH>',
    '<td data-label="rate">nmol min<sup>−1</sup> mg<sup>−1</sup></td>',
    '<table><tr><td>nmol<br/>min<sup>−1</sup> mg<sup>−1</sup></td></tr></table>'])
def test_one_complete_unit_can_retain_its_single_cell_wrapper(raw):
    unit = read_source_rate_unit(witness(raw, raw), sources=sources(raw))
    assert (unit['canonical_unit'], unit['multiplier']) == ('pmol/min/mg', 1000)
    observed = number('Rate 0.005', '0.005')
    assert convert_source_number(observed, unit) == 5


@pytest.mark.parametrize('raw', ['nmol</td><td>/min/mg', 'nmol</th><th>/min/mg',
    'nmol</td></tr><tr><td>/min/mg'])
def test_selected_unit_cannot_be_fabricated_by_joining_table_fields(raw):
    text = '<table><tr><td>' + raw + '</td></tr></table>'
    with pytest.raises(ExperimentalContractError) as caught:
        read_source_rate_unit(witness(text, raw), sources=sources(text))
    assert caught.value.code == 'unsupported_source_rate_unit'


def test_spread_unit_scanning_does_not_join_table_cells_or_ignore_same_cell_units():
    for text, expected in [
        ('<td>58</td><td>nmol/min/mg</td><td>pmol/min/mg</td>', None),
        ('<td>58 nmol</td><td>/min/mg</td><td>pmol/min/mg</td>', 'unsupported_explicit_spread_unit'),
        ('<td>58 nmol<br/>min<sup>−1</sup> mg<sup>−1</sup></td><td>pmol/min/mg</td>', 'source_spread_unit_mismatch'),
    ]:
        source = sources(text)
        n = read_source_number(selector(text, '58'), sources=source, role='spread')
        unit = read_source_rate_unit(witness(text, 'pmol/min/mg'), sources=source)
        if expected is None:
            assert validate_source_spread_unit(n, unit, sources=source) is None
        else:
            with pytest.raises(ExperimentalContractError) as caught:
                validate_source_spread_unit(n, unit, sources=source)
            assert caught.value.code == expected


def table_case(path, *, censored=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    text = ('<p>Synthetic subject S; Partner P; product formation; per mg subject; '
        'All nonpartner conditions matched; glutamine; temperature 37 degC.</p>'
        '<table><tr><th>Arm</th><th>Rate</th><th>Spread</th></tr>'
        '<tr><td>Reference preparation</td><td>7</td><td>1 SD</td></tr>'
        '<tr><td>Omitted preparation</td><td>' + ('&lt;<br/>2' if censored else '2') + '</td><td>unreported</td></tr>'
        '<tr><td>Addback preparation</td><td>6</td><td>unreported</td></tr></table>'
        '<p>Rate unit</p><table><tr><td>pmol/min/mg</td><td>per_min</td></tr></table>')
    raw = text.encode()
    artifact = store.artifact(raw, 'text/html')
    paper = store.put('source', {'provider': 'synthetic_structural_scalar_fixture', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
        'version': None, 'retrieved_at': None, 'parent_source_refs': []}, origin='caller')
    ref = paper['id']
    w = lambda quote: witness(text, quote, reference=ref)
    def n(token):
        body = ('&lt;<br/>' if token == '2' and censored else '') + token + (' SD' if token == '1' else '')
        return selector(text, token, quote='<td>' + body + '</td>', reference=ref)
    literals = dict.fromkeys(LITERAL_FIELDS)
    literals.update(subject=w('Synthetic subject S'), partner=w('Partner P'),
        experiment=w('All nonpartner conditions matched'), endpoint=w('product formation'),
        normalization=w('per mg subject'), function=w('product formation'))
    identities = {name: literals[name] for name in ('subject', 'partner', 'endpoint', 'normalization')}
    arms = {}
    for role, label, token in [('reference', 'Reference', '7'), ('omitted', 'Omitted', '2'), ('addback', 'Addback', '6')]:
        arms[role] = {**deepcopy(identities), 'partner_state': 'absent' if role == 'omitted' else 'present',
            'conditions': {'coverage': 'complete', 'factors': [
                {'factor': 'nitrogen', 'level': {'kind': 'literal', 'witness': w('glutamine')}}]},
            'measurement_identity': w(label + ' preparation'), 'origin': 'synthetic',
            'rate': {'value': n(token), 'unit': w('pmol/min/mg'), 'spread': {
                'kind': 'SD' if role == 'reference' else 'unreported',
                'magnitude': n('1') if role == 'reference' else None,
                'unit': None, 'witnesses': [w('SD')] if role == 'reference' else []}}}
    args = {'source_ref': ref, 'data_source_ref': ref, 'source_kind': 'synthetic_fixture',
        'input_mode': 'native_source_spans', 'literals': literals,
        'interpretation_witnesses': [literals['experiment']], 'arms': arms}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [ref], 'requested_partner_components': list(COMPONENTS)}
    context = BindingContext('structural-scalar-run', 'structural-scalar-child', 'literature',
        (('literature', 'synthetic'),), store.validate_scope(), assignment, {}, (ref,))
    return store, context, args, raw


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def check_rows(rows, censored=False):
    assert [row['component'] for row in rows] == list(COMPONENTS)
    assert all(row['source_kind'] == 'synthetic_fixture' for row in rows)
    if censored:
        assert rows[1]['status'] == 'bounded' and rows[1]['upper'] == 2
        assert rows[1]['value'] is None
    else:
        assert [row['value'] for row in rows] == pytest.approx([7, 2, 6, 5, 5/7, 4, .8, 4/7])
    assert rows[0]['arm_metadata']['reference']['spread'] == {'kind': 'SD', 'magnitude': 1}
    assert all(row['partner_necessity'] == 'not_inferred' for row in rows)


@pytest.mark.parametrize('censored', [False, True])
def test_selected_table_population_and_source_free_saved_reconstruction(tmp_path, monkeypatch, censored):
    store, context, args, raw = table_case(tmp_path, censored=censored)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.partner.source.populate', args, 'table'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        form = form_with_facts({}, FORM, binding.facts(current, selected))
        binding.validate_report(current, form, FORM)
        check_rows(form['measurements'], censored)
        repo = LiteraturePartnerRepository(store, context.run_id)
        saved = repo.read(outcome['result']['sheet_ref'])
        native = saved['extraction']['native_evidence']
        assert native['reference']['rate']['value']['raw_number'] == '7'
        assert native['omitted']['rate']['value']['relation'] == ('lt' if censored else 'point')
        assert store.get_artifact(store.get(args['source_ref'])['artifact_ref']) == raw
        descriptor = binding.as_record()
        sheet = store.get(outcome['result']['sheet_ref'])
    # Reopen durable authority after the publishing Store has closed. Only the
    # saved sheet/request artifacts may be read by this reconstructed binding.
    with Store(tmp_path) as reopened:
        allowed = {sheet['artifact_ref'], sheet['request_ref']}
        read = reopened.get_artifact
        def saved_only(ref):
            assert ref in allowed, 'saved replay attempted to reopen original source'
            return read(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved replay attempted native source parsing/calculation')
        monkeypatch.setattr(reopened, 'get_artifact', saved_only)
        import gene_annotation_episode.literature_partner_storage as storage
        import gene_annotation_episode.literature_partner_native_inputs as native_inputs
        import gene_annotation_episode.literature_partner_source_fields as fields
        import gene_annotation_episode.literature_partner_calculations as core
        monkeypatch.setattr(storage, 'read_partner_inputs', forbidden)
        for module, names in (
            (native_inputs, ('read_partner_native_inputs', 'read_source_number', 'read_source_rate_unit',
                'convert_source_number', 'read_defined_rate_unit', 'convert_defined_source_number',
                'validate_defined_spread_unit', 'populate_partner_components')),
            (fields, ('read_source_number', 'read_source_rate_unit', 'validate_source_spread_unit',
                'convert_source_number', '_raw_contexts', '_contexts', '_unit_contexts',
                '_soft_break_numeric_token', '_rate_unit')),
            (core, ('populate_partner_components',)),
        ):
            for name in names:
                monkeypatch.setattr(module, name, forbidden)
        monkeypatch.setattr(_Sources, 'source', forbidden)
        monkeypatch.setattr(_Sources, 'witness', forbidden)
        services = binding_for(reopened, context).services
        restored, = compose_episode_bindings(services, store=reopened,
            journal=Journal(reopened, context.run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        reopened.db.execute('PRAGMA query_only=ON')
        assert asyncio.run(restored.execute(context, 'literature.partner.source.populate', args, 'table')) == outcome
        assert form_with_facts({}, FORM, restored.facts(current, selected)) == form
        restored.validate_report(current, form, FORM)


def test_table_values_cross_the_ordinary_typed_parent_boundary(tmp_path):
    store, context, args, _ = table_case(tmp_path / 'state')
    received = []
    with store:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Read the synthetic partner-removal table',
            'scope': plain(context.scope), 'purpose': 'Return the requested experimental partner components',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.partner.source.populate', 'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            check_rows(form['measurements'])
            references = {row['id']: row for row in inputs['working_state']['references']}
            assert references[form['measurements'][0]['subject_ref']]['label'] == 'Synthetic subject S'
            received.append(form)
            commit = {name: [] for name in store.reasoning_schema()['required']}
            anchor = deepcopy(args['literals']['subject'])
            anchor.pop('representation')
            anchor['artifact_ref'] = store.get(args['source_ref'])['artifact_ref']
            commit['source_subjects'] = [{'alias': 'synthetic_subject', 'reference_type': 'assay',
                'source_ref': args['source_ref'], 'label': 'Synthetic subject S', 'anchor': anchor}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, action, receive]),
            run_dir=tmp_path / 'run', controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1 and result['credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_partner_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
