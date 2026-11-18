"""Validate the original page of this reader child's explicit parent."""
from __future__ import annotations
from .source_contracts import ContractError, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class OriginalPageAssignment:

    def _parent_page_schema(self, *, context=None):
        schema = _PAGE
        schema = deepcopy(schema)
        return schema

    def _validate_parent_page(self, parent):
        value = plain(parent.assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self._parent_page_schema(context=parent))
        self._validate_page(value, parent.scope)
        return value
