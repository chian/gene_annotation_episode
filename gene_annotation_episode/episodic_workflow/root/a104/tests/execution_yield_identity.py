"""Required test helper: capture actual installed yield callbacks and replay.

Call with a real own-axis binding/context and its original configured profile.
Exceptions are intentionally not caught or replaced. This helper does not make
an absent commissioning context, fabricate completion or project scientific
credit. Full saved-carrier reopen remains a distinct caller-owned test.
"""
from copy import deepcopy
import inspect


def capture_execution_yield_identity(binding, context, initial_credit, epoch, observations):
    from gene_annotation_episode.episodic_workflow.root.a104.practical_yield import PracticalYieldEstimator
    expected_module = binding.__module__.removesuffix('.episode') + '.yield_estimator'
    for name in ('yield_controller', 'practical_estimator'):
        method = getattr(binding, name)
        assert method.__func__.__module__ == expected_module
        assert method.__func__.__qualname__ == 'ExecutionEpisodeYield.' + name
    controllers = [binding.yield_controller(context, initial_credit, epoch) for _ in range(2)]
    initial = controllers[0].state().as_record()
    assert controllers[1].state().as_record() == initial
    callback_records = []
    seen = set()
    def capture(value, position):
        if id(value) in seen: return
        seen.add(id(value))
        if isinstance(value, PracticalYieldEstimator):
            callback_records.append({'position': position, 'estimator': value.as_record()})
            capture(value.verify_completion, position + '.verify_completion')
            return
        if inspect.ismethod(value): value = value.__func__
        if not inspect.isfunction(value): return
        callback_records.append({'position': position, 'function': value.__module__ + '.' + value.__qualname__})
        if value.__module__ == expected_module:
            assert value.__qualname__.startswith('ExecutionEpisodeYield.')
        for name, cell in zip(value.__code__.co_freevars, value.__closure__ or ()):
            selected = cell.cell_contents
            if isinstance(selected, PracticalYieldEstimator) or inspect.isfunction(selected) or inspect.ismethod(selected):
                capture(selected, position + '.' + name)
    actual_estimator = controllers[0].estimator
    contextual_declared = hasattr(actual_estimator, 'estimate_with_context')
    contextual = getattr(actual_estimator, 'estimate_with_context', None)
    estimator_state = actual_estimator.state().as_record()
    if contextual is not None:
        capture(contextual, 'controller')
    practical = binding.practical_estimator(context)
    assert isinstance(practical, PracticalYieldEstimator)
    capture(practical, 'binding.practical_estimator')
    rows = []
    for index, observation in enumerate(observations):
        actual = controllers[0].observe(str(index), deepcopy(observation)).as_record()
        replayed = controllers[1].observe(str(index), deepcopy(observation)).as_record()
        assert replayed == actual
        rows.append(actual)
    assert controllers[0].state().as_record() == controllers[1].state().as_record()
    return {'binding_path': binding.binding_path, 'role': context.role,
        'controller_estimator': {'type': type(actual_estimator).__module__ + '.' + type(actual_estimator).__qualname__,
            'contextual_callback_declared': contextual_declared, 'contextual_callback_present': contextual is not None,
            'initial_state': estimator_state, 'final_state': actual_estimator.state().as_record()},
        'callbacks': callback_records, 'initial_state': initial, 'observations': rows,
        'final_state': controllers[0].state().as_record(),
        'qualification': 'actual installed estimator and original observation replay; full carrier reopen separate'}
