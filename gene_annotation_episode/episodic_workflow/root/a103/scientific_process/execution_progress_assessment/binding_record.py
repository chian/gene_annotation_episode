"""MonitorBindingRecord"""
from __future__ import annotations
from copy import deepcopy
from .contracts import VERSION

class MonitorBindingRecord:

    def as_record(self):
        return {'version': VERSION, 'binding_id': 'scientific_process/execution_progress_assessment', 'configuration': {'outcome_page_size': self.outcome_page_size, **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)} if self.private_yield_binding else {})}}
