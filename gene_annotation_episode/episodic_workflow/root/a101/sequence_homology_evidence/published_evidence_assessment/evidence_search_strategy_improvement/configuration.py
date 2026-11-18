"""Private A101 literature_strategy configuration."""
from __future__ import annotations

class LiteratureConfiguration:

    def __init__(self, services, *, outcome_page_size=8):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_a101_literature_outcome_page_size_required')
        self.services = services
        self.outcome_page_size = outcome_page_size
        self._contract_information_profile = None
        self.reference_parent_sources = None
