"""Fresh private next/context comparison against authenticated original bodies.

Twenty representatives cover five exact original next bodies and every declared
role; source proofs retain the remaining copies. Both calls use actual private
task constructors and the same explicit controlled information ports. A real
Store supplies the read snapshot and empty action table. No provider, action,
credit projection, continuation or scientific interpretation executes.
"""
import ast
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

BASE = 'gene_annotation_episode.episodic_workflow.root.a104.'
FIXTURE = json.loads((Path(__file__).parent / 'fixtures/organization_boundaries/original_next_roles.json').read_text())
GROUPS = FIXTURE['groups']
assert len(GROUPS) == 20 and sum(len(row['equivalent_homes']) for row in GROUPS) == FIXTURE['homes'] == 60
CASES = [(row, False) for row in GROUPS] + [(row, True) for row in GROUPS if row['role'] in {'scientific_process', 'literature'}]


def own(name):
    return importlib.import_module(BASE + name.replace('/', '.'))


class ContextObserved(Exception):
    pass


def original_next(row):
    raw = row['source'].encode()
    assert hashlib.sha256(raw).hexdigest() == row['source_sha256']
    tree = ast.parse(raw)
    cls, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == row['class']]
    method, = [node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'next']
    # Run the exact defining imports, not another axis's Task or a rewritten
    # model of its behavior. Class bodies and module functions are not executed.
    imports = [deepcopy(node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    package = BASE + row['home'].replace('/', '.')
    namespace = {'__name__': package + '.task', '__package__': package}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[*imports, deepcopy(method)], type_ignores=[])),
        '<authenticated-original-next:' + row['home'] + '>', 'exec'), namespace)
    return namespace['next']


@pytest.mark.parametrize('row,annotation_axes', CASES,
    ids=[row['home'] + (':annotation-vector' if vector else ':scalar') for row, vector in CASES])
def test_fresh_next_context_and_callback_order_match_original(tmp_path, row, annotation_axes):
    runtime = own('runtime')
    task_type = getattr(own(row['home'] + '/task'), row['class'])
    reference = original_next(row)
    path = ((row['role'], 'controlled-context'),)
    observations = []
    with own('state').Store(tmp_path / 'state') as store:
        problem = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        scope = {'subject_refs': list(problem['subject_refs'])}
        journal = own('episode_journal').Journal(store, 'context-boundary')
        for callback in (reference, task_type.next):
            events = []
            def port(name, value):
                def called(*args, **kwargs):
                    events.append(name)
                    return deepcopy(value)
                return called
            scientific = row['role'] == 'scientific_process' or row['role'].startswith('literature')
            credit = {'credit': {'mode': 'annotation_axis_credit'} if annotation_axes else 2.5,
                'axis_components': {'qualified': 0.}, 'retained_finding_count': 0,
                'inactive_dependencies': [], 'detail_pages': [],
                'proposed_annotations': [], 'comparisons': [], 'a104_sheet': {'qualified': 'unresolved'}}
            binding = SimpleNamespace(credit_kind=lambda role: 'scientific' if scientific else 'operational',
                decision_context=port('binding_decision_context', {'original_bound_context': row['role']}))
            workflow = SimpleNamespace(run_id='context-boundary',
                context=SimpleNamespace(require_run_id=lambda: 'context-boundary'),
                grains={row['role']: SimpleNamespace(name=row['role'])},
                journal=SimpleNamespace(row=journal.row, db=journal.db,
                    elapsed_view=port('elapsed_view', {'elapsed_seconds': 0.})), store=store,
                execution_binding=None, inprocess_replay=None,
                working_state=port('working_state', {'original': ['state']}),
                local_outcome_preview=port('local_outcome_preview', {'status': 'unavailable', 'record_refs': [],
                    'feedback': {'code': 'controlled-unavailable'}}),
                source_credit_view=port('source_credit_view', credit), receipt_projection=port('receipt_projection', scientific),
                source_credit_binding=port('source_credit_binding', {'kind': 'declared-controlled-context'}),
                pending_work=port('pending_work', []), delivery_status=port('delivery_status', []),
                controller_binding={'kind': 'controlled-original'}, catalog=port('catalog', []),
                knowledge=SimpleNamespace(context=port('knowledge_context', {})),
                job_episode_options=port('job_episode_options', []), extra_report_sources=port('extra_report_sources', {}),
                annotation_context=port('annotation_context', {'original_scientific_information': 'unresolved'}),
                tools=SimpleNamespace(model_contract_catalog=port('model_contract_catalog', {'original_contract': 'retained'})),
                action_schema=port('action_schema', {'type': 'object'}))
            def specialist(source):
                events.append('specialist')
                return binding
            workflow.specialist = specialist
            workflow.is_job_source = lambda source: row['role'].startswith('job_')
            workflow.is_scientific_source = runtime.Workflow.is_scientific_source.__get__(workflow)
            workflow.binding_context = port('binding_context', {'original_role': row['role']})
            request = runtime.EpisodeRequest(runtime.EpisodeGoal.root(objective='Keep exact controlled input', result_contract={}),
                runtime.Record({'scope': scope, 'initial_report': {}, 'episode_assignment': {}}))
            task = task_type(workflow, path, request, scope)
            task.last_outcome = {'status': 'unavailable', 'record_refs': [], 'feedback': {'code': 'unprojected'}}
            task.last_outcome_index = 2
            task.feedback = task.last_outcome['feedback']
            async def observe(context, schema):
                events.append('call')
                observations.append({'context': deepcopy(context), 'schema': deepcopy(schema), 'events': list(events)})
                raise ContextObserved()
            task.call = observe
            view = SimpleNamespace(units_consumed=0, child_reports=(),
                controller_state={'arms': [], 'annotation_credits': {}, 'root_score': 0., 'decision': {}},
                model_inputs=port('model_inputs', None))
            def model_inputs(context, *, reports):
                events.append('model_inputs')
                assert reports == ()
                return {**deepcopy(context), 'explicit_caller_information': {'original': True}}
            view.model_inputs = model_inputs
            with pytest.raises(ContextObserved):
                asyncio.run(callback(task, view))
        assert len(observations) == 2 and observations[0] == observations[1]
        assert observations[1]['events'][-2:] == ['action_schema', 'call']
        assert observations[1]['context']['explicit_caller_information'] == {'original': True}
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
