"""Private root annotation axis response contract."""
from __future__ import annotations

class RootRequests:

    def child_return_sources(self, parent, role):
        """This root task's direct scientific return, chosen by its binding."""
        if not self.task_credit or parent.role != 'annotation' or len(parent.path) != 1 or (role != 'scientific_process'):
            return ()
        return ('scientific_process_results', 'committed_record_refs')

    def child_return_form(self, parent, role):
        sources = self.child_return_sources(parent, role)
        if not sources:
            raise ValueError('root_child_return_form_not_bound')
        return {'type': 'object', 'properties': {name: {'$ref': 'episode-fact:' + name} for name in sources}, 'required': list(sources), 'additionalProperties': False}
