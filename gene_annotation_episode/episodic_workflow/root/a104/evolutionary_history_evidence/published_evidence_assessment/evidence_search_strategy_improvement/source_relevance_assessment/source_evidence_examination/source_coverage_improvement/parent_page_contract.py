"""Private A104 from parent."""
from __future__ import annotations
from .contracts import ContractError, REF, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _TEXT, _WINDOW, deepcopy, json, obj, plain, validate_schema

class LiteratureParentPageContract:

    def _parent_page_assignment_schema(self, *, context=None):
        return self._assignment_fields(_PAGE, context=context)

    def _validate_parent_page_assignment(self, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self._parent_page_assignment_schema(context=context))
        page = value
        self._validate_page(page, scope)
        return value
