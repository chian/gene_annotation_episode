"""MonitorConfiguration"""
from __future__ import annotations
import math
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class MonitorConfiguration:

    def __init__(self, services, *, outcome_page_size=32, information_unit=None, yield_settings=None):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_monitor_outcome_page_size_required')
        self.services, self.outcome_page_size = (services, outcome_page_size)
        self.private_yield_binding = yield_settings is not None
        if yield_settings is not None:
            settings = plain(yield_settings)
            if not isinstance(settings, dict) or set(settings) != {'kind', 'cutoff', 'uncertainty_alpha'} or settings['kind'] != 'information_accumulation':
                raise ValueError('monitor_information_yield_settings_required')
            cutoff, alpha = (settings['cutoff'], settings['uncertainty_alpha'])
            if type(cutoff) not in (int, float) or not math.isfinite(cutoff) or cutoff < 0 or (type(alpha) not in (int, float)) or (not math.isfinite(alpha)) or (not 0 < alpha < 1):
                raise ValueError('monitor_information_yield_values_invalid')
            if type(information_unit) not in (int, float) or not math.isfinite(information_unit) or information_unit <= 0:
                raise ValueError('monitor_information_unit_required_for_yield')
            self.yield_settings = settings
            self.information_unit = float(information_unit)
        else:
            self.yield_settings = None
            self.information_unit = None

    @staticmethod
    def _role(role):
        if role != 'monitor':
            raise ValueError('unsupported_monitor_role:' + str(role))
