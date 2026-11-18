"""Literature specializations of the application's ordinary Episode loop.

This binding supplies operands, available ordinary operations, source custody,
and the commissioned task's private yield binding when selected. Its own
source task owns decisions, reasoning commits, commissioning and report updates.
In particular, a reading selection is
information for an investigation, never a script that this binding executes.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import inspect
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a104.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError, REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import reference_in_context
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
_CHILDREN = {'literature': ('literature_strategy',), 'literature_strategy': ('literature_search',), 'literature_search': ('literature_page',), 'literature_page': ('literature_table', 'literature_ordered', 'literature_targeted'), 'literature_table': (), 'literature_ordered': (), 'literature_targeted': ()}
from gene_annotation_episode.episodic_workflow.root.a104.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS
_ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page', 'execution.estimate')
_ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity', 'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset', *EXPERIMENT_DATABASE_TOOLS)

def _required_grading_logic(repository):
    from . import evidence_grading
    return evidence_grading
_READ_TOOLS = ('source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'source.xlsx.rows', 'source.pdf.text', 'image.view')

def _population_catalog(*, assay_grading_population=False, ratio_source_population=False, controlled_response_population=False, gel_population=False, completion_time_population=False, product_partition_population=False, active_site_population=False, parent_depletion_population=False, stoichiometric_balance_population=False, compiled_assay_population=False, channel_population=False, ion_discrimination_population=False):
    """Publish A104's retained local assay and source operations."""
    from gene_annotation_episode.episodic_workflow.root.a104.literature_population_catalog import population_catalog
    return population_catalog(assay_grading_population=assay_grading_population, ratio_source_population=ratio_source_population, controlled_response_population=controlled_response_population, gel_population=gel_population, completion_time_population=completion_time_population, product_partition_population=product_partition_population, active_site_population=active_site_population, parent_depletion_population=parent_depletion_population, stoichiometric_balance_population=stoichiometric_balance_population, compiled_assay_population=compiled_assay_population, channel_population=channel_population, ion_discrimination_population=ion_discrimination_population)
