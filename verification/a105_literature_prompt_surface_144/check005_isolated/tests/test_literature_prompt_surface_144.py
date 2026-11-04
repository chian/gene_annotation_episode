"""Synthetic engineering checks of actual literature contract information.

No original papers or configured-model decisions are used. Contracts remain
actual production contracts; fixture returns and source passages are synthetic.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.composition_information import (
    CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE,
)
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.episode_contract_information import (
    operation_contract_information, return_contract_information,
)
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, SAVED_NUMERICAL_RETURN_TASK, render_literature_experimental_prompt,
)
from gene_annotation_episode.literature_reference_parent_prompt import (
    REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt,
)
from test_literature_experimental_prompt_delivery import (
    LiteratureWire, snapshot, complete, SOURCE_TEXT, QUALIFICATION,
)
from test_literature_reference_parent_prompt import state as parent_state


def catalog():
    return [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT}
            for row in _population_catalog()]


def parent():
    value = parent_state()
    value['goal'].pop('result_contract')
    value['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    value['available_report_facts'] = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    value['reference_evidence_parent']['child_population_operations'] = [
        {key: row[key] for key in ('name', 'description')} for row in catalog()]
    return value


def child():
    value = snapshot()
    value['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    value['tools'].extend(catalog())
    return value


@pytest.mark.parametrize('builder,renderer,task_text', [
    (parent, render_reference_evidence_parent_prompt, REFERENCE_PARENT_TASK),
    (child, render_literature_experimental_prompt, EXPERIMENTAL_TASK),
])
def test_complete_scientific_task_recurs_and_unrequested_contract_expansions_are_absent(builder, renderer, task_text):
    value = builder()
    original = deepcopy(value)
    tool = next(row for row in catalog() if row['name'] == 'literature.rate.source.populate')
    operation = operation_contract_information(catalog=catalog(), operation=tool['name'])
    text = renderer(value, 'Evaluate the assigned source experiment iteratively.')
    task, steering = text.split('\n\nSTEERING\n')
    assert task_text in task and SAVED_NUMERICAL_RETURN_TASK in task
    assert 'no-inhibitor reference is not a no-enzyme blank' in task
    assert 'models identify' in task.lower() or 'interpret source meaning' in task.lower()
    assert 'initial annotation' in task or 'initial target annotation' in task
    assert 'Complete requested contract' not in text
    assert 'Declared typed projection for literature_' not in text
    assert 'Operands for literature.' not in text
    for row in catalog():
        assert row['name'] in task and row['description'] in task
    assert 'source_scope_mismatch' not in task
    later = deepcopy(value)
    later['last_local_outcome'] = {'status': 'invalid', 'feedback': {'code': 'source_scope_mismatch'}}
    later['child_reports'] = [{'measurements': [{'component': 'source_presence_index',
        'value': None, 'status': 'unavailable', 'qualification': 'Synthetic endpoint limitation.',
        'unavailable_reason': 'correction_inputs_unreported'}]}]
    for lookups in ((), (operation,)):
        full = renderer(later, 'Evaluate the assigned source experiment iteratively.', lookup_results=lookups)
        recurring, facts = full.split('\n\nSTEERING\n')
        assert task_text in recurring
        assert 'Synthetic endpoint limitation.' in facts
        assert 'correction_inputs_unreported' in facts and 'source_scope_mismatch' in facts
        assert 'Synthetic endpoint limitation.' not in recurring
        if lookups:
            assert 'Requested operation/return information: literature.rate.source.populate' in recurring
            assert operation['result']['text'] in recurring
            assert operation['result']['text'] not in facts
            assert operation['result']['schema_sha256'] not in full
    assert value == original


def test_actual_operation_and_return_contracts_remain_addressable_without_population_or_schema_substitution():
    tools = catalog()
    expected = _population_catalog()
    assert [{key: row[key] for key in ('name', 'description', 'input_schema')} for row in tools] == expected
    facts = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    for row in tools:
        result = operation_contract_information(catalog=tools, operation=row['name'])
        assert result['result']['input_schema'] == row['input_schema']
        assert result['result']['meaning'] == row['description']
        assert result['record_refs'] == result['changed_record_refs'] == []
    for name, row in facts.items():
        result = return_contract_information(facts_by_role={'literature': facts},
            permitted_child_roles=['literature'], role='literature', source=name)
        assert result['result']['report_schema'] == row['report_schema']
        assert result['result']['meaning'] == row['meaning']
        assert result['record_refs'] == result['changed_record_refs'] == []
    selected = 'literature_rate_source_meaning_cells'
    lookup = return_contract_information(facts_by_role={'literature': facts},
        permitted_child_roles=['literature'], role='literature', source=selected)
    rendered = render_reference_evidence_parent_prompt(parent(), 'Evaluate assigned reference evidence.', lookup_results=[lookup])
    task, steering = rendered.split('\n\nSTEERING\n')
    assert lookup['result']['text'] in task
    assert lookup['result']['text'] not in steering
    assert 'Declared typed projection for literature_binding_interaction_model_cells' not in rendered


def test_actual_provider_complete_retains_task_on_own_outcome_return_lookup_and_reconstruction(tmp_path):
    first = child()
    later = deepcopy(first)
    later['last_local_outcome'] = {'status': 'completed', 'result': {'text': SOURCE_TEXT,
        'source_ref': 'source_selected', 'artifact_ref': 'artifact_selected', 'start': 0,
        'end': len(SOURCE_TEXT.encode()), 'qualification': QUALIFICATION}}
    later['child_reports'] = [{'requested_result': {'value': None, 'unavailable_reason': 'Synthetic missing calibration'}}]
    operation = operation_contract_information(catalog=catalog(), operation='literature.rate.source.populate')
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 1, 'exchange_index': 0, 'result': operation,
        'pending_contract_information': [operation]}
    wire = LiteratureWire(tmp_path/'wire')
    restarted = LiteratureWire(tmp_path/'restart')
    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(later, first))
        await complete(wire, lookup)
        restored = state_frame(later)
        restored['restored_public_exchanges'] = [{'lookup_result': operation}]
        restored['restored_pending_decision_index'] = 1
        await complete(restarted, restored)
    asyncio.run(exercise())
    for transport in (wire, restarted):
        for turn in transport.turns_sent():
            task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n')
            assert EXPERIMENTAL_TASK in task
            assert 'Operands for literature.' not in task
            assert first['goal']['objective'] in task
        final = transport.turns_sent()[-1]['input'][0]['text']
        task, steering = final.split('\n\nSTEERING\n')
        assert SOURCE_TEXT in steering and QUALIFICATION in steering
        assert 'Synthetic missing calibration' in steering
        assert operation['result']['text'] in task and operation['result']['schema_sha256'] not in final


def test_fresh_reference_factory_selects_compact_and_explicit_none_retains_legacy_configuration():
    source_refs = ['source_caller_selected']
    fresh = LiteratureEpisodes.reference_evidence(None, source_refs=source_refs)
    assert fresh.rate_population
    assert fresh.reference_parent_sources == tuple(source_refs)
    assert fresh.contract_information_configuration() == CONTRACT_INFORMATION_PROFILE
    record = fresh.as_record()
    assert record['configuration']['contract_information_profile'] == CONTRACT_INFORMATION_PROFILE
    assert LiteratureEpisodes(None, **record['configuration']).as_record() == record
    legacy = LiteratureEpisodes.reference_evidence(None, source_refs=source_refs,
        contract_information_profile=None)
    original = LiteratureEpisodes(None, rate_population=True, reference_parent_sources=source_refs)
    assert legacy.as_record() == original.as_record()
    assert 'contract_information_profile' not in legacy.as_record()['configuration']
    assert LiteratureEpisodes(None, **legacy.as_record()['configuration']).as_record() == legacy.as_record()
    assert LiteratureEpisodes(None).contract_information_configuration() is None
    assert LiteratureEpisodes(None, rate_population=True).contract_information_configuration() is None


def test_fresh_source_only_caller_retains_exact_bytes_configuration_and_source_assignment_without_model(tmp_path, monkeypatch):
    import hashlib
    import importlib.util
    from pathlib import Path
    from gene_annotation_episode.state import Store
    path = Path(__file__).parents[1]/'verification/a105_literature_prompt_surface_144/run_configured_primary_144.py'
    spec = importlib.util.spec_from_file_location('caller_surface_144', path)
    caller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caller)
    source = tmp_path/'synthetic.html'
    raw = b'<html><body>Synthetic engineering source. No measured biology.</body></html>'
    source.write_bytes(raw)
    question = 'Evaluate what the selected source establishes about its measured reference experiment.'
    prepared = caller.prepare(tmp_path/'prepared', source=source,
        source_sha256=hashlib.sha256(raw).hexdigest(), question=question)
    assert prepared['scope'] == {'subject_refs': []}
    assert prepared['scientific_question'] == question
    assert prepared['source_media_type'] == 'text/html'
    assert prepared['decision_protocol'] == 'decision_exchange_v1'
    assert prepared['configuration']['controller']['cost'] == .001
    descriptor = prepared['episode_binding_descriptor']
    assert descriptor['configuration']['reference_parent_sources'] == [prepared['source_ref']]
    assert descriptor['configuration']['contract_information_profile'] == CONTRACT_INFORMATION_PROFILE
    with Store(tmp_path/'prepared/state') as store:
        assert store.problem()['subject_refs'] == []
        assert store.get_artifact(prepared['artifact_ref']) == raw
        assert store.get(prepared['artifact_ref'])['media_type'] == 'text/html'
        assert store.get(prepared['source_ref'])['text_ref'] is None
        assert not store.list('observation') and not store.list('assessment')
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_model_calls'").fetchall()

    captured = {}
    async def capture_only(store, tools, **kwargs):
        captured.update(kwargs)
        return {'engineering_capture_only': True}
    monkeypatch.setattr(caller, 'run_workflow', capture_only)
    asyncio.run(caller.execute(tmp_path/'prepared', prepared))
    assert captured['goal'].startswith(question + '\n\n')
    assert prepared['scientific_scope'] in captured['goal']
    assert 'No annotation target sequence was supplied' in captured['goal']
    assert captured['episode_binding_descriptors'] == [descriptor]
    assert captured['decision_protocol'] == 'decision_exchange_v1'
    assert captured['provider_config'] == prepared['configuration']
    assert captured['initial_known_record_refs'] == [prepared['source_ref']]
    assert not {'provider', 'controller_factory', 'project_credit', 'controller_settings'} & captured.keys()


def test_fresh_factory_default_reaches_actual_runtime_lookup_execution_and_descriptor_reconstruction(tmp_path):
    from functools import partial
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_kinetic_storage import kinetic_cells_schema
    from gene_annotation_episode.runtime import Workflow, TypedReportContract
    from gene_annotation_episode.tools import ToolRegistry
    from test_contract_information_runtime_059 import PresentedProvider, information, populate, run_child
    from test_literature_kinetic_storage import setup
    from test_runtime import FixtureController
    store, seed, args = setup(tmp_path/'state')
    provider = PresentedProvider([])
    try:
        value = Workflow(store, ToolRegistry(store), provider, tmp_path/'run', 'fresh-reference144',
            lambda path, initial: FixtureController(str(path), initial, 1),
            ScientificFindingProgress(FindingProgressPolicy(1)),
            initial_known_record_refs=list(seed.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes.reference_evidence,
                source_refs=[args['source_ref']]),), decision_protocol='decision_exchange_v1')
        root = value.build('annotation', 'root', 'Evaluate supplied synthetic source evidence.', plain(seed.scope))
        child_episode = value.build('literature', 'case', 'Evaluate the selected synthetic reference experiment.',
            plain(seed.scope), parent=root.request.goal, parent_path=root.source.path,
            contract=TypedReportContract('Fixture source investigation',
                obj({'parameters': kinetic_cells_schema()}), lambda *_: True),
            initial={}, episode_assignment=plain(seed.assignment))
        provider.script = iter([information('episode.operation_contract', operation='literature.kinetic.populate'),
            populate(args)])
        result = run_child(child_episode, value)
        assert result.units_consumed == 1
        assert value.contract_information_profile(root.source) == CONTRACT_INFORMATION_PROFILE
        assert value.contract_information_profile(child_episode.source) == CONTRACT_INFORMATION_PROFILE
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0] == 1
        assert len(value.decision_exchanges.rows(child_episode.source.episode_id, 0)) == 2
        assert 'Operands for literature.kinetic.populate' not in provider.rendered[0]
        assert 'Requested operation/return information: literature.kinetic.populate' in provider.rendered[-1]
        descriptors = value.episode_bindings.as_record()
        restored = Workflow(store, ToolRegistry(store), PresentedProvider([]), value.directory, value.run_id,
            lambda path, initial: FixtureController(str(path), initial, 1),
            ScientificFindingProgress(FindingProgressPolicy(1)),
            initial_known_record_refs=value.initial_known_record_refs,
            episode_binding_descriptors=descriptors, decision_protocol='decision_exchange_v1')
        assert restored.episode_bindings.as_record() == descriptors
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()


@pytest.mark.parametrize('configured_registry', [False, True], ids=['original_bare_registry_failure', 'configured_registry_pretransport'])
def test_source_only_owned_model_bootstrap_preserves_default_science_and_declared_failure(tmp_path, monkeypatch, configured_registry):
    """Exercise real run_workflow, default science and descriptor publication.

    Only provider entry is interrupted: neither app-server transport nor any
    model response/action is supplied. The bare registry branch reproduces the
    original missing reconstruction operand without retrying historical runs.
    """
    import hashlib
    import importlib.util
    from pathlib import Path
    from gene_annotation_episode.default_scientific_binding import VERSION as DEFAULT_SCIENCE
    from gene_annotation_episode.providers import ModelConnection
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from method_loop.durable import DurableExecutionError

    path = Path(__file__).parents[1]/'verification/a105_literature_prompt_surface_144/run_configured_primary_144.py'
    spec = importlib.util.spec_from_file_location('caller_bootstrap_surface144', path)
    caller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caller)
    source = tmp_path/'synthetic.html'
    raw = b'<html><body>Synthetic bootstrap fixture; no measured biology.</body></html>'
    source.write_bytes(raw)
    directory = tmp_path/'prepared'
    prepared = caller.prepare(directory, source=source, source_sha256=hashlib.sha256(raw).hexdigest(),
        question='Evaluate the assigned synthetic source experiment.')
    provider_entries = []
    async def before_transport(connection):
        assert type(connection) is ModelConnection
        assert connection.config == prepared['configuration']['models']
        assert connection.workers == {}
        provider_entries.append(connection)
        raise DurableExecutionError('interrupted_execution',
            affected_refs=['controlled_pretransport_boundary'])
    monkeypatch.setattr(ModelConnection, '__aenter__', before_transport)
    if not configured_registry:
        monkeypatch.setattr(caller, 'build_tools', lambda store, configuration: ToolRegistry(store))
    with pytest.raises(DurableExecutionError) as failure:
        asyncio.run(caller.execute(directory, prepared))
    expected = ({'code': 'interrupted_execution', 'affected_refs': ['controlled_pretransport_boundary'],
                 'diagnostic_ref': None, 'partial_record_refs': []} if configured_registry else
                {'code': 'unavailable_binding', 'affected_refs': ['tool_configuration'],
                 'diagnostic_ref': None, 'partial_record_refs': []})
    assert failure.value.failure == expected
    diagnostic = json.loads((directory/'execution_failure.json').read_text())
    assert diagnostic == {'exception_type': 'DurableExecutionError', 'message': expected['code'],
                          'failure': expected}
    assert bool(provider_entries) is configured_registry
    with Store(directory/'state') as store:
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_report_attempts'):
            assert table in tables
            assert store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
        row, = store.db.execute('SELECT settings FROM runtime_runs').fetchall()
        settings = json.loads(row['settings'])
        assert settings['controller'] == prepared['configuration']['controller']
        assert settings['decision_protocol'] == prepared['decision_protocol']
        assert settings['binding_definitions']['credit']['default_entrypoint'] == DEFAULT_SCIENCE
        assert settings['episode_bindings'] == [prepared['episode_binding_descriptor']]
        assert settings['goal'] == caller.assignment_text(prepared)
        assert prepared['scientific_scope'] in settings['goal']
        assert settings['problem']['subject_refs'] == []
        if configured_registry:
            assert settings['tool_configuration'] == prepared['tool_configuration']
            assert (directory/'run/episode-execution-binding.json').exists()
            binding = json.loads((directory/'run/episode-execution-binding.json').read_text())
            assert binding['arguments']['tool_configuration'] == prepared['tool_configuration']
            assert binding['arguments']['kind'] == 'standard_default'
        else:
            assert 'tool_configuration' not in settings
            assert not (directory/'run/episode-execution-binding.json').exists()
