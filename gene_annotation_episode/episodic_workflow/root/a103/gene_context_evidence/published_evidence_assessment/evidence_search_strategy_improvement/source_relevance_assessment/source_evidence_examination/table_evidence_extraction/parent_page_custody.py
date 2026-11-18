"""Private A103 literature_table from parent."""
from __future__ import annotations
from .source_contracts import ContractError, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class ParentPageCustody:

    def _parent_page_schema(self, role, *, context=None):
        self._role(role)
        schema = _PAGE
        schema = deepcopy(schema)
        return schema

    def _validate_parent_page(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self._parent_page_schema(role, context=context))
        page = value
        self._validate_page(page, scope)
        return value

