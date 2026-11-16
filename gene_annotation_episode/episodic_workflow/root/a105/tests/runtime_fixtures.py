"""Controlled runtime fixtures for A105 tests; no live science."""
from copy import deepcopy
from types import SimpleNamespace

class FixtureController:
    """Test-only continuation seam, not an application action limit."""

    def __init__(self, epoch, initial, stop_after):
        self.epoch, self.initial, self.current, self.stop_after = (epoch, initial, initial, stop_after)
        self.scores = []

    def observe(self, label, value, *, is_root):
        value = value.as_record()['credit']
        self.scores.append(value - self.current)
        self.current = value
        stop = len(self.scores) >= self.stop_after
        return FixtureStep(stop, self.scores[-1])

    def state(self):
        return FixtureState(self.scores, self.current, len(self.scores) >= self.stop_after)

    def transitioned(self, epoch):
        raise AssertionError('no runtime-owned epoch transition')

class FixtureStep:
    requests_transition = False

    def __init__(self, stop, delta):
        self.stop, self.delta = (stop, delta)

    def as_record(self):
        return {'stop': self.stop, 'requests_transition': False, 'delta': self.delta}

class FixtureState:

    def __init__(self, scores, value, stop):
        self.scores, self.value, self.decision = (list(scores), value, SimpleNamespace(stop=stop))

    def as_record(self):
        return {'scores': self.scores, 'credit': self.value, 'decision': {'stop': self.decision.stop}}

class ScriptedProvider:
    """Explicit fixture responses; never a claim of live model behavior."""

    def __init__(self, script):
        self.script, self.contexts, self.released = (iter(script), [], [])

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING'
        assert 'competing explanations' in instructions
        self.contexts.append(deepcopy(context))
        response = next(self.script)
        if isinstance(response, BaseException):
            raise response
        return response(context) if callable(response) else deepcopy(response)

    async def release(self, episode_id):
        self.released.append(episode_id)


def literature_binding_factories(**configuration):
    """Supply the existing seven private source bindings to a controlled workflow."""
    from functools import partial
    from ..published_evidence_assessment.episode import create_binding_tree
    return tuple(partial(type(binding), **deepcopy(configuration))
                 for binding in create_binding_tree(object(), **configuration))


def literature_binding_for_role(binding, role):
    """Build the private literature home that owns ``role`` on the same services.

    The former single literature binding served every literature role; each role
    now has its own home. The configuration is the one the binding records, which
    is what the application itself uses to rebuild a home from a saved descriptor.
    An unknown role raises KeyError.
    """
    from ..published_evidence_assessment.episode import create_binding_tree
    owners = {home.roles[0]: type(home) for home in create_binding_tree(object())}
    return owners[role](binding.services, **deepcopy(binding.as_record()['configuration']))
