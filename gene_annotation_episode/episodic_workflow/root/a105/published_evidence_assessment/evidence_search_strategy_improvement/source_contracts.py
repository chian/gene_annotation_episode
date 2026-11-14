from __future__ import annotations
'Private assignment contracts and source implementation lookup.'
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a105.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.a105.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import reference_in_context
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
from gene_annotation_episode.episodic_workflow.root.a105.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS
_ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page', 'execution.estimate')
_ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity', 'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset', *EXPERIMENT_DATABASE_TOOLS)

def _implementation_path(name):
    """Resolve this episode's retained implementation file."""
    path = _AXIS_DIRECTORY / name
    if not path.is_file():
        path = _AXIS_DIRECTORY / 'library' / name
        if not path.is_file():
            raise FileNotFoundError(path)
    return path

def _required_grading_logic(repository):
    from gene_annotation_episode.episodic_workflow.root.a105.library import literature_required_grading
    return literature_required_grading
_READ_TOOLS = ('source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records', 'source.xlsx.rows', 'source.pdf.text', 'image.view')
_ROLE_INSTRUCTIONS = {'literature': 'Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.', 'literature_strategy': 'Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.', 'literature_search': 'Investigate which returned sources merit examination for the assigned question. Search results are source-discovery information. Examine original sources and their conditions before asserting biological evidence. A page child can investigate where and how to examine a selected source.', 'literature_page': 'Investigate where and how this exact source should be examined. Choose ordinary source operations or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings, tables and footnotes; retained original bytes remain addressable.', 'literature_table': 'Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.', 'literature_ordered': 'Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.', 'literature_targeted': 'Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.'}
_CATALOG_ORDER = ('literature.concentration_window.populate', 'literature.measurement_comparison.populate', 'literature.rate.populate', 'literature.rate.observations.populate', 'literature.calibration.recovery.populate', 'literature.product_coupling.populate', 'literature.measurement_validation.populate', 'literature.rate.replicates.populate', 'literature.quantity.populate', 'literature.assay.populate', 'literature.ratio.populate', 'literature.binding.populate', 'literature.binding.model.populate', 'literature.transport.response.populate', 'literature.figure.populate', 'literature.rate.source.populate', 'literature.amount.populate', 'literature.optical.populate', 'literature.kinetic.populate', 'literature.kinetic.model.populate', 'literature.binding.interaction.populate', 'literature.binding.interaction.model.populate', 'literature.ion_discrimination.populate', 'literature.channel.populate', 'literature.assay.components.populate', 'literature.assay_grading.populate', 'literature.a105.aggregate', 'literature.product_partition.populate', 'literature.completion_time.populate', 'literature.active_site.populate', 'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate', 'literature.ratio.source.populate', 'literature.controlled_response.source_v3.populate', 'literature.gel.populate')

def _population_catalog(*, assay_grading_population=False, ratio_source_population=False, controlled_response_population=False, gel_population=False, completion_time_population=False, product_partition_population=False, active_site_population=False, parent_depletion_population=False, stoichiometric_balance_population=False, compiled_assay_population=False, channel_population=False, ion_discrimination_population=False):
    """Compose A105's population operations in their established order."""
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_population_catalog import population_catalog as a105_catalog
    result = a105_catalog(assay_grading_population=assay_grading_population, ratio_source_population=ratio_source_population, controlled_response_population=controlled_response_population, gel_population=gel_population, completion_time_population=completion_time_population, product_partition_population=product_partition_population, active_site_population=active_site_population, parent_depletion_population=parent_depletion_population, stoichiometric_balance_population=stoichiometric_balance_population, compiled_assay_population=compiled_assay_population, channel_population=channel_population, ion_discrimination_population=ion_discrimination_population)
    positions = {name: index for index, name in enumerate(_CATALOG_ORDER)}
    result.sort(key=lambda entry: positions[entry['name']])
    return result
_AXIS_DIRECTORY = Path(__file__).resolve().parents[2]

def _binding_source_bytes():
    home = Path(__file__).parent
    paths = list(home.glob('*.py'))
    for name in ('prompts', 'tools', 'grading', 'scoring'):
        paths.extend((home / name).glob('*.py'))
    private = b''.join((path.read_bytes() for path in sorted(paths)))
    return private + (_AXIS_DIRECTORY / 'library' / 'literature_investigation_prompt.py').read_bytes()
