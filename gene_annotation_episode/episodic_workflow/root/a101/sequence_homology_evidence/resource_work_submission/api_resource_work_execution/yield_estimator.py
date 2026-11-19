"""The continuation of A101 ``api_resource_work_execution`` (old ``yield_estimator.py``).

The old file was "original continuation factory selection; caller settings unchanged": it chose no estimator
itself and handed the episode's initial credit to the caller-configured controller factory, with no task key and
no credit definition because the credit kind is ``operational`` (its ``scientific_child`` branch was never
taken). The caller's configuration therefore still decides: the standard ``continuation`` collaborator holds,
under this binding's path, the declaration of one of the three ``yield_control`` estimators and its settings:

- ``{'kind': 'accumulation', 'cutoff', 'parameters'}``;
- ``{'kind': 'bounded_quality', 'cutoff', 'parameters', 'maximum_credit'}``;
- ``{'kind': 'completion', 'cutoff', 'parameters', 'target'}``.

``parameters`` are the ``yield_control.YieldParameters`` settings. Nothing is defaulted: a missing or
incomplete declaration raises. The epoch is the Episode's journaled identity.
"""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    open_yield_controller)

DECLARATION_FIELDS = {'accumulation': ('cutoff', 'kind', 'parameters'),
                      'bounded_quality': ('cutoff', 'kind', 'maximum_credit', 'parameters'),
                      'completion': ('cutoff', 'kind', 'parameters', 'target')}


def continuation_declaration(binding_path, continuation):
    """The caller's declaration for this binding, checked to name exactly one estimator's settings."""
    if not isinstance(continuation, Mapping) or binding_path not in continuation:
        raise ValueError('resource_episode_continuation_not_configured:' + binding_path)
    declaration = continuation[binding_path]
    if not isinstance(declaration, Mapping) or declaration.get('kind') not in DECLARATION_FIELDS:
        raise ValueError('resource_episode_continuation_kind_required:' + binding_path)
    expected = DECLARATION_FIELDS[declaration['kind']]
    if tuple(sorted(declaration)) != expected:
        raise ValueError('resource_episode_continuation_requires_exactly:' + ','.join(expected))
    return dict(declaration)


def continuation_controller(declaration, *, epoch, initial_credit):
    """The ``yield_control`` controller the caller declared, opened at the episode's initial credit."""
    return open_yield_controller(declaration['kind'], epoch=epoch, initial_credit=initial_credit,
                                 cutoff=declaration['cutoff'], parameters=declaration['parameters'],
                                 maximum_credit=declaration.get('maximum_credit'), target=declaration.get('target'))
