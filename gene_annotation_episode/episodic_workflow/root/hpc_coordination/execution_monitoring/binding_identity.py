from copy import deepcopy

def as_record(self):
    return {'version': 'root_monitor_private_v1', 'binding_id': 'monitor',
        'configuration': {'outcome_page_size': self.outcome_page_size,
            **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)}
               if self.private_yield_binding else {})}}
