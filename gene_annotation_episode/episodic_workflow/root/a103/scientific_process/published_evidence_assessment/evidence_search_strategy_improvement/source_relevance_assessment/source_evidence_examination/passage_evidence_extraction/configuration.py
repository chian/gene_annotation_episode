"""Private A103 literature_targeted configuration."""
from __future__ import annotations

class SourceEpisodeConfiguration:

    def __init__(self, services, *, outcome_page_size=8):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_a103_literature_outcome_page_size_required')
        self.services = services
        self.outcome_page_size = outcome_page_size

    def contract_information_configuration(self):
        return None

    def contract_information_profile(self, context):
        return None
