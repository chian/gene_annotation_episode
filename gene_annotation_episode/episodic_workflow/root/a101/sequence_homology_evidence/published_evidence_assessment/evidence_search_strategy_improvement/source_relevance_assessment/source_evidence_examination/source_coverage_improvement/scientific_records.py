"""Private A101 literature_ordered scientific records."""
from __future__ import annotations
from .source_contracts import ContractError

class LiteratureScientificRecords:

    def automatic_score_judgments(self, context):
        return []

    def complete_score_judgment(self, context, judgment_ref, response=None, *, provenance, failure=None):
        raise ContractError('a101_automatic_judgment_unavailable')
