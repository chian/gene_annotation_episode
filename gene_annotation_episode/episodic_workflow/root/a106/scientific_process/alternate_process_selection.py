"""Private scientific alternate process selection."""
from __future__ import annotations
from .scientific_contracts import LEGACY_SELECTION_VERSION, SELECTION_VERSION, _LEGACY_REVISION_ARGUMENTS, _REVISION_ARGUMENTS, selection_fields, validate_schema

class AlternateProcessSelection:

    def _proposed_selection(self, initial, arguments, version, scope):
        axis_field = selection_fields(initial)[0]
        if version == LEGACY_SELECTION_VERSION:
            validate_schema(arguments, _LEGACY_REVISION_ARGUMENTS)
            return self._selection({'version': version, 'annotation_ref': initial[axis_field], 'thought_ref': arguments['thought_ref'], 'tools': arguments['tools']})
        validate_schema(arguments, _REVISION_ARGUMENTS)
        return self._selection({'version': SELECTION_VERSION, 'evidence_axis': initial[axis_field], 'thought_pattern': arguments['thought_pattern'], 'child_tool_info': self.tool_library.resolve_tool_info(arguments['child_tool_info'], self._information_catalog(scope))})
