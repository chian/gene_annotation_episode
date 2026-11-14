"""A103's private source-reading episode for gene-context evidence."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a103.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a103.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episodic_workflow.root.a103.domain import ContractError, REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.a103.episode_bindings import reference_in_context
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
_ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page', 'execution.estimate')
_ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity', 'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset')
_READ_TOOLS = ('source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'source.xlsx.rows', 'source.pdf.text', 'image.view')
_ROLE_INSTRUCTIONS = {'literature': 'Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.', 'literature_strategy': 'Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.', 'literature_search': 'Investigate which returned sources merit examination for the assigned question. Search results are source-discovery information. Examine original sources and their conditions before asserting biological evidence. A page child can investigate where and how to examine a selected source.', 'literature_page': 'Investigate where and how this exact source should be examined. Choose ordinary source operations or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings, tables and footnotes; retained original bytes remain addressable.', 'literature_table': 'Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.', 'literature_ordered': 'Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.', 'literature_targeted': 'Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.'}
_AXIS_DIRECTORY = Path(__file__).resolve().parents[3]

def _binding_source_bytes():
    private = b''.join((path.read_bytes() for path in sorted(Path(__file__).parent.glob('*.py'))))
    selected_instructions = (_AXIS_DIRECTORY / 'library/literature_investigation_prompt.py').read_bytes()
    return private + selected_instructions
