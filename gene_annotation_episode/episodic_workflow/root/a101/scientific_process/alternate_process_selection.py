"""Private scientific alternate process selection."""
from __future__ import annotations
from .scientific_contracts import SELECTION_VERSION, _REVISION_ARGUMENTS, selection_fields, validate_schema

class AlternateProcessSelection:

    def _proposed_selection(self, initial, arguments, version, scope):
        axis_field = selection_fields(initial)[0]
        validate_schema(arguments, _REVISION_ARGUMENTS)
        return self._selection({'version': SELECTION_VERSION, 'evidence_axis': initial[axis_field], 'thought_pattern': arguments['thought_pattern'], 'child_tool_info': self.tool_library.resolve_tool_info(arguments['child_tool_info'], self._information_catalog(scope))})
