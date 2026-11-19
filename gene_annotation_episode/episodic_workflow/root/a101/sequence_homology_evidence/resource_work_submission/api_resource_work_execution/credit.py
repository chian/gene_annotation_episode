"""How A101 ``api_resource_work_execution`` counts its credit (old ``credit.py``).

The credit kind is ``operational``. The old ``credit_view(context, receiver_selection)`` returned the old
services object's ``bound_role_credit``: the credit bound to this role, whose body lived in the deleted shared
root. Every resource adapter this episode is constructed with must expose ``credit_view(context,
receiver_selection)`` (old ``configuration.py``), so the credit is the selected adapter's own credit view, read
over the episode's held references (``receiver_selection`` is ``records.received_records.record_selection`` of
them). The number is used exactly as the adapter measures it: never bounded, clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import record_selection

CREDIT_KIND = 'operational'


def credit_view(adapter, context, held):
    """The selected adapter's credit view over the references this episode holds."""
    view = adapter.credit_view(context, record_selection(list(held)))
    if not isinstance(view, Mapping) or 'credit' not in view:
        raise ValueError('resource_credit_view_requires_credit')
    return view


def credit_binding(adapter):
    """The credit definition shown to the model (old ``source_credit_binding``)."""
    return {'credit_kind': CREDIT_KIND, 'credit_source': 'selected_resource_adapter.credit_view',
            'resource_adapter': adapter.as_record()}
