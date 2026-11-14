"""Exact source-span scalar readers for experimental partner components.

The selected spans and their experimental roles are supplied interpretations.
This module verifies bytes, lexical boundaries and supported unit arithmetic;
it establishes no measurement identity, sampling model or biological truth.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_assay_inputs import _witness_schema

def number_selector_schema():
    """Selectors contain offsets, never a supplied scientific number."""
    return obj({'witness': deepcopy(_witness_schema()), 'number_start': {'type': 'integer', 'minimum': 0}, 'number_end': {'type': 'integer', 'minimum': 1}})
