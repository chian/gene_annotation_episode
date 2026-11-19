"""Offered tools and failed-unit outcomes: plain functions an episode calls with its own registry and Store.

These replace the old runner's ``services.tool_catalog(scope)`` / ``workflow.catalog`` /
``workflow.tools.model_contract_catalog`` (the catalog shown to the model), and ``record_source_failure`` plus
``workflow.archive.store`` (a failed selected operation written into the old journal). On the new runner a
failed unit is an ordinary outcome: the tool returns it, the runner records it with the unit, and it enters the
iterator with the episode's own progress measurement.
"""
from __future__ import annotations

import json
import traceback

from gene_annotation_episode.domain import ContractError


def offered_catalog(catalog, selected=None):
    """The part of a registry ``catalog`` (``{name: contract}``) the episode offers.

    ``selected`` is the commission's ``tools`` subset (a list of names) or ``None`` for the whole catalog. A
    selected name the catalog lacks raises ``offered_tool_not_in_catalog``.
    """
    if not isinstance(catalog, dict):
        raise ContractError('offered_catalog_requires_a_catalog_mapping')
    if selected is None:
        return dict(catalog)
    if isinstance(selected, (str, bytes)) or not isinstance(selected, (list, tuple)):
        raise ContractError('offered_catalog_selection_must_be_a_list')
    missing = sorted(set(selected) - set(catalog))
    if missing:
        raise ContractError('offered_tool_not_in_catalog', detail={'tools': missing})
    return {name: catalog[name] for name in dict.fromkeys(selected)}


def failure_outcome(store, error, *, category, cause_code):
    """A ``failed`` unit outcome for ``error``, with its traceback archived as a Store artifact.

    Call it inside the ``except`` block that caught ``error`` (the traceback is the one being handled) and return
    it from the tool; the runner records it with the unit, so a resumed episode sees it in ``view.outcomes``.
    """
    if not isinstance(error, BaseException):
        raise ContractError('failure_outcome_requires_an_exception')
    for name, value in (('category', category), ('cause_code', cause_code)):
        if type(value) is not str or not value:
            raise ContractError('failure_outcome_' + name + '_required')
    diagnostic = store.artifact(json.dumps({'exception_type': type(error).__name__,
                                            'traceback': traceback.format_exc()}, sort_keys=True),
                                'application/json')
    return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
            'feedback': {'category': category, 'cause_code': cause_code, 'code': str(error) or cause_code,
                         'exception_type': type(error).__name__, 'diagnostic_ref': diagnostic}}


__all__ = ['failure_outcome', 'offered_catalog']
