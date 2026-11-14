"""Private A103 literature_ordered scientific records."""
from __future__ import annotations
from .source_contracts import ContractError

class SourceScientificRecords:

    def automatic_score_judgments(self, context):
        return []

    def complete_score_judgment(self, context, judgment_ref, response=None, *, provenance, failure=None):
        raise ContractError('a103_automatic_judgment_unavailable')
