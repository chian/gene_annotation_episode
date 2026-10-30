"""Selected worksheet integration, using explicit controlled episode choices.

The numerical source selectors reuse the already root-converted AP case. These
tests introduce no new paper interpretation or actual-model science. Ordinary
episode choices, saved facts and original report contracts remain authoritative.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, plain, validate_form,
)
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
from gene_annotation_episode.literature_a105_worksheet import a105_worksheet_template, VERSION, NATIVE, SUMMARY
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, render_literature_experimental_prompt,
)
from gene_annotation_episode.literature_reference_parent_prompt import (
    REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt,
)
from gene_annotation_episode.literature_kinetic_summary_precision_prompt import KINETIC_SUMMARY_PRECISION_TASK
from gene_annotation_episode.literature_task_selection import selected_literature_task_sections
from gene_annotation_episode.literature_kinetic_summary_precision_storage import LiteratureKineticSummaryPrecisionRepository
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_kinetic_summary_precision_binding_251 import setup, block_science, forbid
from test_literature_compiled_assay_185 import readonly
from test_runtime import FixtureController, ScriptedProvider


PRECISION = [
    'source_reported_parameter', 'source_reported_sd',
    'source_independent_preparation_count', 'source_statistical_estimator_count',
    'source_mean_standard_error', 'scenario_mean_variance', 'scenario_mean_standard_error',
]
FORWARDED = ['scenario_mean_standard_error', 'source_reported_sd']


def _context(native, precision, *, narrowed=False):
    def n(quantity='cell_value'):
        return {'field': 'native_parameter', 'sheet_ref': native,
            'component': 'numerator_parameter', 'quantity': quantity}

    def p(component):
        return {'field': 'precision', 'sheet_ref': precision,
            'component': component, 'quantity': 'cell_value'}

    def link(left, right, relation):
        return {'left': left, 'right': right, 'relation': relation, 'support_record_refs': []}

    if narrowed:
        links = [link(n('reported_spread'), p('source_reported_sd'), 'same_reported_spread'),
            link(p('source_reported_sd'), p('scenario_mean_standard_error'), 'conditional_precision_of_report')]
    else:
        links = [link(n(), p('source_reported_parameter'), 'same_reported_parameter'),
            link(n('reported_spread'), p('source_reported_sd'), 'same_reported_spread'),
            link(n('reported_count'), p('source_independent_preparation_count'), 'same_count_report'),
            link(p('source_reported_sd'), p('scenario_mean_variance'), 'conditional_precision_of_report'),
            link(p('source_independent_preparation_count'), p('scenario_mean_variance'), 'conditional_precision_of_report')]
    return {'version': VERSION, 'assertion_refs': [], 'quantity_links': links, 'assertion_links': []}


def _template(precision):
    return a105_worksheet_template([
        {'field': 'native_parameter', 'source': NATIVE, 'components': ['numerator_parameter']},
        {'field': 'precision', 'source': SUMMARY, 'components': precision},
    ])


def _prompt(view):
    if view.get('literature_experimental_work', {}).get('aspect') == 'reference_evidence_parent':
        text = render_reference_evidence_parent_prompt(view, 'Evaluate the received experimental evidence.')
        assert REFERENCE_PARENT_TASK in text
    else:
        text = render_literature_experimental_prompt(view, 'Evaluate the received experimental evidence.')
        assert EXPERIMENTAL_TASK in text
    owns_precision = any(source == SUMMARY for source, _ in selected_literature_task_sections(view))
    assert (KINETIC_SUMMARY_PRECISION_TASK in text) == owns_precision
    assert text.startswith('TASK\n') and '\n\nSTEERING\n' in text
    return text


def _digest_tree(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob('*') if p.is_file()}


@pytest.mark.parametrize('also_admitted,empty_draft', [(False, False), (True, False), (False, True), (True, True)])
def test_current_worksheet_interpretation_omits_host_metadata_and_duplicate_context(also_admitted, empty_draft):
    """Reuse recorded engineering rows, without reexecuting their science."""
    packet = Path(__file__).resolve().parents[1] / 'verification/a105_worksheet_pure_266'
    form = json.loads((packet/'CONSTRUCTED_FORM_001.json').read_text())
    records = json.loads((packet/'RETAINED_PUBLIC_REFERENCES_001.json').read_text())
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
        'aspect': 'source_experimental_evidence'}, 'working_state': {'references': list(records.values())},
        'current_report_update': {'assessment_context': deepcopy(form['assessment_context'])},
        'child_reports': [form] if also_admitted else []}
    if empty_draft:
        for key in ('assertion_refs', 'quantity_links', 'assertion_links'):
            state['current_report_update']['assessment_context'][key] = []
    text = render_literature_experimental_prompt(state, 'Evaluate the assigned source parameter.')
    assert EXPERIMENTAL_TASK in text
    steering = text.split('\n\nSTEERING\n', 1)[1]
    assert steering.count('A105 experimental evidence worksheet') == (0 if empty_draft and not also_admitted else 1)
    assert VERSION not in steering and 'quantity_links[' not in steering
    assert re.search(r'(?:source|artifact|reference)_[a-f0-9]{24,64}', steering) is None


@pytest.mark.parametrize('module', ['literature_a105_worksheet.py', 'literature_a105_worksheet_render.py'])
def test_bound_descriptor_includes_the_worksheet_implementation(monkeypatch, module):
    binding = LiteratureEpisodes(SimpleNamespace(), rate_population=True)
    original = binding.as_record()
    read = Path.read_bytes
    def changed(path):
        content = read(path)
        return content + b'\n# explicit descriptor dependency probe\n' if path.name == module else content
    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert binding.as_record() != original


@pytest.mark.parametrize('variant', ['literal', 'alias', 'duplicate_same_type',
    'changed_type', 'unknown', 'ambiguous', 'nested', 'external', 'alias_sibling', 'purpose'])
def test_repair_authenticates_aliases_against_only_original_frozen_types(variant):
    """Exercise the selected-choice authentication, without a current factory."""
    database = sqlite3.connect(':memory:')
    database.row_factory = sqlite3.Row
    store = SimpleNamespace(db=database)
    repository = LiteratureRateRepository(store, 'run271')
    source = 'literature_rate_cells'
    field_type = {'type': 'array', 'x-source': source, 'items': {'type': 'number'}}
    schema = {'type': 'object', 'properties': {'rates': deepcopy(field_type)},
        'required': ['rates'], 'additionalProperties': False}
    original = {'decision': 'Original numerical return.', 'measurements': {'schema': deepcopy(schema)}}
    original['measurements']['schema']['properties']['context'] = {'type': 'string'}
    original['measurements']['schema']['required'].append('context')
    selected_schema = deepcopy(schema)
    if variant != 'literal':
        selected_schema['properties']['rates'] = {'$ref': 'episode-fact:' + source}
    if variant == 'duplicate_same_type':
        original['measurements']['schema']['properties']['duplicate'] = deepcopy(field_type)
    elif variant == 'changed_type':
        selected_schema['additionalProperties'] = True
    elif variant == 'unknown':
        selected_schema['properties']['rates']['$ref'] = 'episode-fact:not_in_original'
    elif variant == 'ambiguous':
        original['measurements']['schema']['properties']['duplicate'] = {
            **field_type, 'maxItems': 1}
    elif variant == 'nested':
        selected_schema['properties']['rates'] = {'type': 'array', 'items': {
            '$ref': 'episode-fact:' + source}}
    elif variant == 'external':
        selected_schema['properties']['rates']['$ref'] = 'https://example.invalid/type'
    elif variant == 'alias_sibling':
        selected_schema['properties']['rates']['maxItems'] = 1
    repaired = {'decision': 'Numerical facts only.', 'measurements': {'schema': schema}}
    choice = {'kind': 'redeliver_report', 'delivery_ref': 'delivery271',
        'purpose': repaired['decision'], 'schema_json': json.dumps(selected_schema)}
    if variant == 'purpose':
        choice['purpose'] = 'Different request.'
    database.execute('CREATE TABLE runtime_episodes(run_id,episode_id,request)')
    database.execute('CREATE TABLE runtime_report_attempts(run_id,parent_episode_id,decision_index,form,contract,failure,child_episode_id,delivery_ref)')
    database.execute('CREATE TABLE runtime_actions(run_id,episode_id,decision_index,action)')
    database.execute('INSERT INTO runtime_episodes VALUES(?,?,?)', ('run271', 'child271',
        json.dumps({'report_contract': original})))
    database.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)',
        ('run271', 'parent271', 1, None, json.dumps(original), 'unsupported link', 'child271', 'delivery271'))
    database.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)',
        ('run271', 'parent271', 2, json.dumps({'rates': [1.25]}), json.dumps(repaired), None, 'child271', 'delivery271'))
    database.execute('INSERT INTO runtime_actions VALUES(?,?,?,?)',
        ('run271', 'parent271', 2, json.dumps(choice)))
    context = SimpleNamespace(episode_id='parent271')
    try:
        if variant in ('literal', 'alias', 'duplicate_same_type'):
            assert repository._runtime_delivery_cells(context, 'run271:parent271:2:typed_form') == [1.25]
        else:
            with pytest.raises(ContractError, match='literature_delivery_binding_mismatch'):
                repository._runtime_delivery_cells(context, 'run271:parent271:2:typed_form')
    finally:
        database.close()


@pytest.mark.parametrize('mode', ['direct', 'nested', 'repair'])
def test_selected_worksheet_links_forwarding_and_first_cold_reconstruction(tmp_path, monkeypatch, mode):
    """An ordinary interpretation action supplies constrained scientific links.

    It is part of the same iterative episode, not an extra report-composer call.
    Two selected population actions remain two actions; formatting adds none.
    """
    nested, repair = mode == 'nested', mode == 'repair'
    store, original_context, arguments, _, _ = setup(tmp_path/'state', PRECISION, actual_source=True)
    for name in ('molecule', 'construct'):
        witness = arguments['selection']['kinetic_selection']['numerator']['subject'][name]
        arguments['return_context'][name] = [{'start': witness['start'], 'end': witness['end']}]
    native_arguments = deepcopy(arguments['selection']['kinetic_selection'])
    source_refs = list(original_context.received_record_refs)
    child_template = _template(PRECISION)
    outer_template = _template(FORWARDED if nested else PRECISION)
    full_assignment = {**plain(original_context.assignment), **child_template['assignment_rosters']}
    outer_assignment = {**plain(original_context.assignment), **outer_template['assignment_rosters']}
    empty = {'version': VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}
    captured, prompts, selected_outcomes = [], [], []
    native_ref = None

    def commission(role, assignment, template):
        def choose(view):
            requested = view.get('requested_form')
            update = ({'assessment_context': empty} if isinstance(requested, dict)
                and 'assessment_context' in requested.get('properties', {}) else {})
            return {'selection': {'kind': 'episode_child', 'role': role, 'assignment': assignment,
            'goal': 'Evaluate the selected source kinetic parameter and the precision of that same report.',
            'scope': plain(original_context.scope),
            'purpose': 'Return the requested numerical sections and their constrained shared-report relationships.',
            'schema_json': json.dumps(template['submitted_form']),
                'initial_report_json': json.dumps({'assessment_context': empty})}, 'report_update': update}
        return choose

    def native_work(view):
        prompts.append(_prompt(view))
        return {'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
            'arguments': native_arguments}, 'report_update': {'assessment_context': empty}}

    def precision_work(view):
        nonlocal native_ref
        outcome = view['last_local_outcome']
        selected_outcomes.append(deepcopy(outcome))
        native_ref = outcome['result']['sheet_ref']
        prompts.append(_prompt(view))
        return {'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
            'arguments': arguments}, 'report_update': {'assessment_context': empty}}

    def reasoning(view, context):
        # This actual scientific action records the studied construct. It is
        # selected in an ordinary iteration while interpreting the two views.
        commit = {key: [] for key in store.reasoning_schema()['required']}
        witness = native_arguments['numerator']['subject']['construct']
        artifact = store.get(witness['source_ref'])['text_ref']
        commit['source_subjects'] = [{'alias': 'studied_construct271', 'reference_type': 'assay',
            'source_ref': witness['source_ref'], 'label': witness['quote'],
            'anchor': {'source_ref': witness['source_ref'], 'artifact_ref': artifact,
                'start': witness['start'], 'end': witness['end'], 'quote': witness['quote']}}]
        requested = view.get('requested_form')
        update = ({'assessment_context': context} if isinstance(requested, dict)
            and 'assessment_context' in requested.get('properties', {}) else {})
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': update}

    def interpret_selected(view):
        outcome = view['last_local_outcome']
        selected_outcomes.append(deepcopy(outcome))
        prompts.append(_prompt(view))
        context = _context(native_ref, outcome['result']['sheet_ref'])
        if repair:
            context['quantity_links'][0]['relation'] = 'same_count_report'
        return reasoning(view, context)

    def repair_delivery(view):
        assert view['feedback']['reason'] == 'a105_worksheet_link_not_supported'
        assert view['child_reports'] == []
        schema = deepcopy(outer_template['submitted_form'])
        del schema['properties']['assessment_context']
        schema['required'].remove('assessment_context')
        return {'selection': {'kind': 'redeliver_report',
            'delivery_ref': view['feedback']['delivery_ref'],
            'purpose': 'Return the valid original numerical facts without the unsupported saved relationship interpretation.',
            'schema_json': json.dumps(schema)}, 'report_update': {}}

    def integrate(view):
        form, = view['child_reports']
        captured.append(deepcopy(form))
        expected = FORWARDED if nested and len(captured) == 2 else PRECISION
        assert [row['component'] for row in form['precision']] == expected
        assert [row['component'] for row in form['native_parameter']] == ['numerator_parameter']
        if repair:
            assert 'assessment_context' not in form
        else:
            assert len(form['assessment_context']['quantity_links']) == (2 if expected == FORWARDED else 5)
        assert form['native_parameter'][0]['value'] == .000186
        values = {row['component']: row['cell'] for row in form['precision']}
        assert values['source_reported_sd']['value'] == .000006
        if 'source_statistical_estimator_count' in values:
            assert values['source_statistical_estimator_count']['value'] is None
            assert values['source_mean_standard_error']['value'] is None
        assert values['scenario_mean_standard_error']['value'] == pytest.approx(4.242640687119285e-6)
        text = _prompt(view)
        task, steering = text.split('\n\nSTEERING\n', 1)
        # The nested strategy episode still owns precision work on its first
        # return; the receiving scientific parent gets that result in STEERING.
        assert (KINETIC_SUMMARY_PRECISION_TASK in task) == (nested and len(captured) == 1)
        assert 'Requested kinetic summary precision' in steering
        assert steering.count('A105 experimental evidence worksheet') == (0 if repair else 1)
        if not repair:
            assert 'dependent views' in steering
        assert VERSION not in steering
        assert 'quantity_links[' not in steering
        prompts.append(text)
        return reasoning(view, _context(form['native_parameter'][0]['sheet_ref'],
            form['precision'][0]['sheet_ref'], narrowed=nested))

    script = [commission('literature', outer_assignment, outer_template)]
    if nested:
        strategy_assignment = {'version': 'strategy_assignment_v1', 'question_context_refs': [],
            'prior_search_refs': source_refs, **child_template['assignment_rosters']}
        script.append(commission('literature_strategy', strategy_assignment, child_template))
    script += [native_work, precision_work, interpret_selected]
    if repair:
        script.append(repair_delivery)
    script.append(integrate)
    if nested:
        script.append(integrate)
    provider = ScriptedProvider(script)
    progress = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial,
                2 if len(path) == 1 or nested and len(path) == 2 else 3),
            project_credit=progress, binding_definitions={'credit': progress.as_record()},
            initial_known_record_refs=source_refs,
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=source_refs),)))
        assert len(captured) == (2 if nested else 1)
        assert len(selected_outcomes) == 2
        expected_observations = 7 if nested else 5
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == expected_observations
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == expected_observations
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_summary_precision_operations').fetchone()[0] == 1
        if repair:
            attempts = store.db.execute('SELECT form,failure FROM runtime_report_attempts ORDER BY rowid').fetchall()
            assert len(attempts) == 2
            assert json.loads(attempts[0]['failure'])['reason'] == 'a105_worksheet_link_not_supported'
            assert attempts[1]['failure'] is None
            saved_child = store.db.execute('SELECT form,facts FROM runtime_forms WHERE form IS NOT NULL ORDER BY rowid LIMIT 1').fetchone()
            saved_form, saved_facts = json.loads(saved_child['form']), json.loads(saved_child['facts'])
            assert saved_form['assessment_context']['quantity_links'][0]['relation'] == 'same_count_report'
            assert captured[-1]['native_parameter'] == saved_facts[NATIVE]
            assert captured[-1]['precision'] == saved_facts[SUMMARY]
        run_id, receiver_id = store.db.execute('SELECT run_id,episode_id FROM literature_kinetic_summary_precision_received ORDER BY rowid DESC LIMIT 1').fetchone()
        original = captured[-1]
        descriptor = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
        report = store.db.execute('SELECT child_episode_id,contract FROM runtime_report_attempts WHERE failure IS NULL ORDER BY rowid DESC LIMIT 1').fetchone()
        original_schema = json.loads(report['contract'])['measurements']['schema']
        refs = tuple(dict.fromkeys([*source_refs, *(ref for out in selected_outcomes for ref in out['record_refs'])]))
        reporting = replace(original_context, run_id=run_id, episode_id=report['child_episode_id'],
            assignment=outer_assignment, received_record_refs=refs)
        host = SimpleNamespace(store=store, run_id=run_id, tools=None)
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, reference_parent_sources=source_refs)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        before_rows = deepcopy(original)
        changes = store.db.total_changes
        if not repair:
            unsupported = deepcopy(original)
            unsupported['assessment_context']['quantity_links'][0]['relation'] = (
                'same_reported_parameter' if nested else 'same_count_report')
            forged = deepcopy(original)
            forged['assessment_context']['quantity_links'][0]['right']['sheet_ref'] = original['native_parameter'][0]['sheet_ref']
            with pytest.raises(ReportBoundaryError, match='a105_worksheet_link_not_supported'):
                binding.validate_report(reporting, unsupported, original_schema)
            with pytest.raises(ReportBoundaryError, match='a105_worksheet_selector_not_delivered'):
                binding.validate_report(reporting, forged, original_schema)
        binding.validate_report(reporting, original, original_schema)
        assert original == before_rows and store.db.total_changes == changes
        if nested:
            expanded = deepcopy(original)
            expanded['assessment_context']['quantity_links'] = deepcopy(captured[0]['assessment_context']['quantity_links'])
            # Same source identity cannot authorize references to omitted cells.
            with pytest.raises(ReportBoundaryError):
                binding.validate_report(reporting, expanded, original_schema)
        allowed = {store.get(row['sheet_ref'])[key]
            for field in ('native_parameter', 'precision') for row in original[field]
            for key in ('artifact_ref', 'request_ref')}
        receiver = replace(reporting, episode_id=receiver_id, role='annotation',
            path=(('annotation', receiver_id),), assignment={})
        for name, value in [('ORIGINAL_FORM_271.json', original), ('ORIGINAL_SCHEMA_271.json', original_schema),
                ('ORIGINAL_DESCRIPTOR_271.json', descriptor), ('SELECTED_OUTCOMES_271.json', selected_outcomes)]:
            (tmp_path/name).write_text(json.dumps(value, indent=2)+'\n')
        (tmp_path/'RECEIVING_PROMPT_271.txt').write_text(prompts[-1])
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        store.close()
        before = _digest_tree(tmp_path/'state')
        block_science(monkeypatch)
        from gene_annotation_episode import literature_kinetic_storage as native_storage
        from gene_annotation_episode import literature_a105_worksheet as worksheet
        import gene_annotation_episode.communication as communication
        monkeypatch.setattr(native_storage, 'read_kinetic_inputs', forbid)
        monkeypatch.setattr(native_storage, 'populate_kinetic_contrast', forbid)
        monkeypatch.setattr(worksheet, 'a105_worksheet_template', forbid)
        monkeypatch.setattr(worksheet, '_schema', forbid)
        monkeypatch.setattr(worksheet, 'import_module', forbid)
        monkeypatch.setattr(type(provider), 'complete', forbid)
        communication._compiled_schema_content.cache_clear()
        with readonly(tmp_path/'state') as cold:
            cold.db.create_function('library_scope_record', 2, cold._scope_filter_record)
            get = cold.get_artifact
            def saved_only(reference):
                assert reference in allowed, 'Original source acquisition forbidden during first cold read'
                return get(reference)
            monkeypatch.setattr(cold, 'get_artifact', saved_only)
            cold_host = SimpleNamespace(store=cold, run_id=run_id, tools=None)
            restored = compose_episode_bindings(WorkflowServices(cold_host), store=cold,
                journal=SimpleNamespace(store=cold, run_id=run_id), execution_backend=None,
                descriptors=descriptor, job_episodes=None, resource_estimator=None, role_credit_bindings={})
            cold_host.episode_bindings = EpisodeBindingRegistry(restored.bindings)
            reopened, = restored.bindings
            assert reopened.as_record() == descriptor[0]
            facts = reopened.received_report_facts(receiver)
            assert facts[NATIVE] == original['native_parameter']
            assert facts[SUMMARY] == original['precision']
            validate_form(original, original_schema, lambda ref, namespace: reopened.resolve(reporting, ref, namespace))
            reopened.validate_received_report(reporting, original, original_schema)
            assert cold.db.total_changes == 0
        assert before == _digest_tree(tmp_path/'state')
    finally:
        try:
            store.close()
        except Exception:
            pass
