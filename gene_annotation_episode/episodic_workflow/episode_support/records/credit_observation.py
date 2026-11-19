"""The controller input of one completed unit: the credit measured after it, at its progress receipt.

Every yield controller in ``yield_control`` observes one value per completed unit: the episode's cumulative credit
after that unit and, under ``estimation_context['progress_time']``, the Episode's recorded progress-time receipt for
that unit (``bound.progress.receipt(position)``); the estimator fits each marginal credit at that real time.

* ``credit_observation(credit, progress_time, facts=None)`` returns that controller input as a
  ``method_loop.ClosedRecord`` (what the runner journals). ``credit`` is the episode's own credit on its own scale:
  any finite number, never bounded, clamped or rescaled. ``facts`` is a closed JSON object of the episode's own
  facts about the unit (for example its selection kind, the record references it received, a completion proof);
  the controller ignores them and the binding reads them back on resume.
* ``restore_credit_observation(record)`` rebuilds it from its journaled record (``restore_controller_input``).
"""
from __future__ import annotations

from collections.abc import Mapping
import math

from yield_control import PROGRESS_TIME_VERSION

from gene_annotation_episode.episodic_workflow.episode_support.records.closed_json import closed_record

FIELDS = frozenset({'credit', 'estimation_context', 'facts'})


def _credit(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('credit_observation_credit_must_be_a_finite_number:' + repr(value))
    return value


def _receipt(value):
    if not isinstance(value, Mapping) or value.get('version') != PROGRESS_TIME_VERSION:
        raise ValueError('credit_observation_requires_an_episode_progress_receipt')
    if value.get('point_kind') != 'progress_receipt' or type(value.get('position')) is not int:
        raise ValueError('credit_observation_requires_an_episode_progress_receipt')
    return value


def credit_observation(credit, progress_time, facts=None):
    """The closed controller input of one completed unit (see the module docstring)."""
    facts = {} if facts is None else facts
    if not isinstance(facts, Mapping):
        raise TypeError('credit_observation_facts_must_be_a_mapping')
    return closed_record({'credit': _credit(credit), 'estimation_context': {'progress_time': _receipt(progress_time)},
                          'facts': dict(facts)})


def restore_credit_observation(record):
    """The controller input rebuilt from its journaled record."""
    if not isinstance(record, Mapping) or set(record) != FIELDS:
        raise ValueError('credit_observation_record_requires_credit_estimation_context_facts')
    context = record['estimation_context']
    if not isinstance(context, Mapping) or set(context) != {'progress_time'}:
        raise ValueError('credit_observation_record_requires_its_progress_receipt')
    return credit_observation(record['credit'], context['progress_time'], record['facts'])


__all__ = ['credit_observation', 'restore_credit_observation']
