"""Actual original scalar/bounded estimator capture; no fabricated callback."""
from copy import deepcopy
from dataclasses import replace

from .api_cases import Case, HOMES, module
from .execution_yield_identity import capture_execution_yield_identity


def test_actual_scalar_api_estimator_capture(tmp_path):
    case = Case(tmp_path, HOMES[2])
    try:
        value = capture_execution_yield_identity(case.binding, case.context, 0., 'original-scalar', [{'credit': 0.}])
        assert value['controller_estimator']['type'].endswith('.ScalarScoreYieldEstimator')
        assert value['controller_estimator']['contextual_callback_declared'] is True
        assert value['controller_estimator']['contextual_callback_present'] is True
        assert any(row['position'] == 'controller' and 'estimator' in row for row in value['callbacks'])
    finally:
        case.close()


def test_actual_launch_bounded_estimator_without_contextual_callback(tmp_path):
    case = Case(tmp_path, HOMES[2])
    try:
        home = case.home.rsplit('/', 1)[0]
        options = {**case.options, 'task_yield_profiles': {**case.options['task_yield_profiles'],
            'launch:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}}}}
        owner = module(home + '/episode').ExecutionEpisode(case.services, **options)
        selected = {'version': 'execution_launch_assignment_v1', 'requests': {'uniprot': deepcopy(case.assignment)},
            'immutable_input_versions': [], 'constraints': {}}
        path = (('launch', 'original-bounded-owner'),)
        identity = module('method_loop.identities').EpisodeRef(case.run_id, path).episode_id
        inheritance = case.receipts.bind(identity)
        case.receipts.receive(identity, case.scope['subject_refs'], kind='initial')
        request = {'message': {'scope': deepcopy(case.scope), 'episode_assignment': selected,
            'knowledge_inheritance': inheritance}}
        runtime = module('runtime')
        case.journal.save('runtime_episodes', {'episode_id': identity, 'path': runtime._json(path),
            'request': runtime._json(request), 'initial_credit': 0., 'state': 'active', 'completion': None, 'archive': None})
        context = module('episode_bindings').BindingContext(case.run_id, identity, 'launch', path, case.scope, selected, request)
        owner.initialize(context)
        value = capture_execution_yield_identity(owner, context, 0., 'original-bounded', [{'credit': 0.}, {'credit': 1.}])
        assert value['controller_estimator']['type'].endswith('.BoundedScoreYieldEstimator')
        assert value['controller_estimator']['contextual_callback_declared'] is False
        assert value['controller_estimator']['contextual_callback_present'] is False
        assert not any(row['position'] == 'controller' for row in value['callbacks'])
        assert any(row['position'] == 'binding.practical_estimator' for row in value['callbacks'])
    finally:
        case.close()
