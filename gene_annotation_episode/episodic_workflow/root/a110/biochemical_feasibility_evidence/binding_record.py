"""Private A110 scientific binding_record."""
from __future__ import annotations
from .scientific_assignment_contracts import ROLE, VERSION, deepcopy

class ScientificBindingRecord:

    def as_record(self):
        return {'version': VERSION, 'binding_id': ROLE, 'configuration': {'library': deepcopy(self._library_record), 'tool_library': deepcopy(self._tools_record), 'child_roles': list(self._child_roles), **({'tool_retrieval': deepcopy(self.tool_retrieval)} if self.tool_retrieval else {}), **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {}), **({'yield_bindings': deepcopy(self._yield_bindings)} if self._yield_bindings is not None else {})}}
