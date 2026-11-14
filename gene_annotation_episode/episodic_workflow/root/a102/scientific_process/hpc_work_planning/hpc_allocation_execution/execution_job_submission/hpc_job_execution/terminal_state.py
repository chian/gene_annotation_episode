"""Private native terminal state."""
from __future__ import annotations
from .terminal_contracts import PracticalState, assess_validations, digest

class TerminalState:

    def _state_directory(self, context):
        return self.directory / 'practical-execution' / digest({'run_id': context.run_id, 'episode_id': context.episode_id})

    def initialize(self, context):
        assignment = self._assignment(context)
        directory = self._state_directory(context)
        state = PracticalState(directory, context.run_id, context.episode_id, assignment, **{} if (directory / 'assignment.json').is_file() else {'initial_outcome': {'facts': {}}, 'initial_validations': assess_validations(assignment, {'facts': {}}, assignment['initial_context'])})
        self._states[context.episode_id] = state
        return state

    def state(self, context):
        return self._states.get(context.episode_id) or self.initialize(context)
