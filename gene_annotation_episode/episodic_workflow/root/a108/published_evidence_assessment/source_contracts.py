from __future__ import annotations
"Literature specializations of the application's ordinary Episode loop.\n\nThis binding supplies operands, available ordinary operations, source custody,\nand the commissioned task's private yield binding when selected. The ordinary Episode loop owns decisions, reasoning commits, commissioning and report updates.\nIn particular, a reading selection is\ninformation for an investigation, never a script that this binding executes.\n"
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a108.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError, REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.a108.episode_bindings import reference_in_context
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
_CHILDREN = {'literature': ('literature_strategy',)}
_A108_ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.references', 'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page', 'material.annotations', 'material.parse', 'material.from_source', 'execution.estimate')
_A108_ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity', 'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset', 'public.uniprot.search', 'public.uniprot.record', 'public.taxonomy', 'public.ncbi.sequence')
_A108_NAMESPACES = frozenset(('literature_a108_grading_cells', 'literature_a108_aggregation_cells'))

def _a108_population_catalog():
    from gene_annotation_episode.episodic_workflow.root.a108.library.literature_population_catalog import population_catalog
    return population_catalog()

def _required_grading_logic(repository):
    if repository.provider != 'literature.a108.context_grading':
        raise ContractError('a108_context_grading_required')
    from gene_annotation_episode.episodic_workflow.root.a108.library import literature_required_grading
    return literature_required_grading
_READ_TOOLS = ('source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.xlsx.rows', 'source.pdf.text', 'image.view')
_ROLE_INSTRUCTIONS = {'literature': 'Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.'}
_AXIS_DIRECTORY = Path(__file__).resolve().parents[1]

def _binding_source_bytes():
    private = b''.join((path.read_bytes() for path in sorted(Path(__file__).parent.rglob('*.py')) if 'tests' not in path.relative_to(Path(__file__).parent).parts))
    selected_library = b''.join((path.read_bytes() for path in sorted((_AXIS_DIRECTORY / 'library').rglob('*.py'))))
    return private + selected_library
