"""Literature specializations of the application's ordinary Episode loop.

This binding supplies operands, available ordinary operations, source custody,
and the commissioned task's private yield binding when selected. The shared
source owns decisions, reasoning commits, commissioning and report updates.
In particular, a reading selection is
information for an investigation, never a script that this binding executes.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import inspect
import json
from gene_annotation_episode.episodic_workflow.root.a102.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a102.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episodic_workflow.root.a102.domain import ContractError, REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.a102.episode_bindings import reference_in_context
VERSION = 'literature_episode_binding_v1'
ROLES = ('literature', 'literature_strategy', 'literature_search', 'literature_page', 'literature_table', 'literature_ordered', 'literature_targeted')
_REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
_REPRESENTATION = {'type': 'string', 'enum': ['text', 'original', 'stdout', 'stderr']}
_NATURAL = {'type': 'integer', 'minimum': 0}
_POSITIVE = {'type': 'integer', 'minimum': 1}
_TEXT = {'type': 'string', 'minLength': 1}
_WINDOW = obj({'source_ref': REF, 'representation': _REPRESENTATION, 'offset': _NATURAL, 'limit': _POSITIVE})
_TABLE = obj({'source_ref': REF, 'sheet_key': _TEXT, 'offset': _NATURAL, 'limit': _NATURAL, 'header_row': {'type': ['integer', 'null'], 'minimum': 1}, 'where': {**obj({'column': {'type': ['string', 'null'], 'pattern': '^[A-Z]+$'}, 'match': {'enum': ['equals', 'contains']}, 'value': _TEXT, 'case_sensitive': {'type': 'boolean'}}), 'type': ['object', 'null']}})
_PAGE = obj({'version': {'const': 'page_assignment_v1'}, 'source_ref': REF, 'representation': _REPRESENTATION, 'artifact_ref': REF, 'question_context_refs': _REFERENCES, 'prior_delivery_refs': _REFERENCES})
from gene_annotation_episode.episodic_workflow.root.a102.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS
_ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page', 'execution.estimate')
_ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity', 'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset', *EXPERIMENT_DATABASE_TOOLS)

_READ_TOOLS = ('source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'source.xlsx.rows', 'source.pdf.text', 'image.view')
_CATALOG_ORDER = ('literature.structure.populate',)

def _population_catalog(**_configuration):
    from gene_annotation_episode.episodic_workflow.root.a102.a102_literature_bindings import population_catalog_entry
    return [population_catalog_entry()]
