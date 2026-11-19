"""The A102 monitor's continuation (carried from ``yield_estimator.py`` and ``configuration.py``).

The old private binding ``monitor_information_accumulation_v1`` forecast the next action's information credit
with ``estimate_nonnegative_yield`` and stopped when the predicted upper gain was at or below the cutoff: the
``accumulation`` estimator of ``yield_control``. Its settings are ``{kind: information_accumulation, cutoff >= 0,
uncertainty_alpha in (0, 1)}`` with a positive ``information_unit``. Without them the old binding raised
``monitor_private_yield_binding_not_enabled``; so does this one.
"""
from __future__ import annotations

import math

from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import open_yield_controller
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain

KIND = 'accumulation'
ESTIMATOR_BINDING = {'kind': 'monitor_information_accumulation_v1',
                     'credit': 'newly_informative_received_snapshot_count_times_information_unit',
                     'forecast': 'next_monitor_action_information_credit',
                     'decision': 'predicted_upper_gain_at_or_below_monitor_cutoff'}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def settings(yield_settings, information_unit):
    """The old ``MonitorConfiguration`` checks; returns ``(settings, information_unit)`` or ``(None, None)``."""
    if yield_settings is None:
        return None, None
    value = plain(yield_settings)
    if not isinstance(value, dict) or set(value) != {'kind', 'cutoff', 'uncertainty_alpha'} \
            or value['kind'] != 'information_accumulation':
        raise ValueError('monitor_information_yield_settings_required')
    if not _number(value['cutoff']) or value['cutoff'] < 0 or not _number(value['uncertainty_alpha']) \
            or not 0 < value['uncertainty_alpha'] < 1:
        raise ValueError('monitor_information_yield_values_invalid')
    if not _number(information_unit) or information_unit <= 0:
        raise ValueError('monitor_information_unit_required_for_yield')
    return value, float(information_unit)


def controller(yield_settings, *, epoch, initial_credit):
    """The monitor's information-accumulation controller (old ``yield_controller``)."""
    if yield_settings is None:
        raise ValueError('monitor_private_yield_binding_not_enabled')
    return open_yield_controller(KIND, epoch=epoch, initial_credit=initial_credit, cutoff=yield_settings['cutoff'],
                                 parameters={'uncertainty_alpha': yield_settings['uncertainty_alpha']})


__all__ = ['ESTIMATOR_BINDING', 'KIND', 'controller', 'settings']
