"""What the parent gives: the original results assignment (the old ``execution_results_assignment_v1`` of
``from_parent.assignment_schema``: ``handoff_ref`` and ``selector``, under the same names) and the records it passes.

This is the only place the assignment is read. The old ``prepare_assignment`` validated the selector against the
target the handoff names (``_selector``) and the native inputs the selector's family names. The target the handoff
names was read by the old runner's progress provider from the handoff record; the parent now copies it into the
assignment (``target``, a new field) and the selector is validated here against it. The checks of the commission
against the parent's Launch form and the old runner's tables (``_recorded_results_assignment``, ``_launch``,
``validate_selected_inputs``, the immutable input versions, the masking / utility / standard / native BLAST database
and BV-BRC input validation against held records) are checks of a commission by its child; a wrong commission fails,
so they are not carried (blocked file).

The family of the target decides which of the old branches of this episode applies (the old ``self.native_*_results``
objects, ``self.api_execution`` and ``self.local_file_sources``). Only the generic native byte-window family
(``native_bytes``) is placed; the other families are named here and raise where their old class would have been
called (``unplaced``): their classes are in no place now."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.native_blast_masking_acquisition import (
    is_native_blast_masking_target)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.profile_model_preparation.evolutionary_history_evidence.native_hmmer_preparation_acquisition import (
    is_native_hmmer_preparation_target)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.evolutionary_history_evidence.native_blast_acquisition import (
    is_native_blast_target)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.evolutionary_history_evidence.native_blast_utility_acquisition import (
    is_native_blast_utility_target)
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.execution_contracts import (
    TEXT, checked, obj, validate_target)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.practical_execution_operations import (
    confined)
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.evolutionary_history_evidence.hmmer_preparation_result_views import (
    validate_preparation_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.evolutionary_history_evidence.sequence_masking_result_views import (
    validate_masking_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_pairwise_result_views import (
    validate_native_blast_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.blast_utility_result_views import (
    validate_blast_utility_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.hmmer_native_result_views import (
    validate_native_hmmer_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_database_result_views import (
    validate_native_blast_database_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.evolutionary_history_evidence.native_blast_standard_database_result_views import (
    validate_standard_blast_database_selector)

RESULTS_VERSION = 'execution_results_assignment_v1'
LOCAL_FILE_SOURCE_VERSION = 'local_file_source_selector_v1'
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT},
                              'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])
MASKING_SELECTOR_VERSION = 'native_blast_masking_result_selector_v1'
UTILITY_SELECTOR_VERSIONS = ('native_blast_utility_result_selector_v1', 'native_blast_utility_result_selector_v2')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', RESULTS_VERSION),
    'handoff_ref': Field('text', 'The original handoff: the execution target whose results are acquired'),
    'selector': Field('record', 'The requested results: local file sources, native byte windows (paths, path, '
                                'offset, limit) or a typed native result selector'),
    # New fields the final form needs (the old code read them from the handoff record and the configuration).
    'target': Field('record', 'The execution target the handoff names (execution_target_v1): the old '
                              'targets.read_target(handoff_ref)'),
    'acquired_record_unit': Field('number', 'The credit of one fully acquired requested selector (the old '
                                            'acquired_record_unit of the configuration)'),
    'record_refs': Field('record_refs', 'Every record the code reads: the handoff and the records the selected '
                                        'native inputs name, passed in custody (the old initial_references)',
                         required=False),
    'initial_result_refs': Field('record_refs', 'The earlier result acquisitions of this handoff that the parent '
                                                'holds (the old initial known records); their artifacts are in '
                                                'record_refs', required=False),
    'scientific_task': Field('record', 'The scientific parent task: scientific_question and selected_tool_info '
                                       '(old services.scientific_parent_task)', required=False),
})


def _jobs(target):
    return target['assignment'].get('requested_job', {}) if isinstance(target.get('assignment'), dict) else {}


def family(target, selector):
    """The family of the original ``_selector`` branches, in the old order."""
    if selector.get('version') == LOCAL_FILE_SOURCE_VERSION:
        return 'local_file_source'
    if selector.get('version') == MASKING_SELECTOR_VERSION or is_native_blast_masking_target(target):
        return 'native_blast_masking'
    if selector.get('version') in UTILITY_SELECTOR_VERSIONS or is_native_blast_utility_target(target):
        return 'native_blast_utility'
    if target['resource_kind'] == 'api':
        return 'api'
    jobs = _jobs(target)
    if 'native_blast_standard_database' in jobs:
        return 'native_blast_standard_database'
    if 'native_blast_database' in jobs:
        return 'native_blast_database'
    if is_native_hmmer_preparation_target(target):
        return 'native_hmmer_preparation'
    if 'native_hmmer' in jobs:
        return 'native_hmmer'
    if is_native_blast_target(target):
        return 'native_blast'
    return 'native_bytes'


def windows(selector):
    """The old ``_windows``: the requested byte windows by path as ``[offset, limit or None]``."""
    values = {path: [0, None] for path in selector.get('paths', [])}
    if 'path' in selector:
        values[selector['path']] = [selector.get('offset', 0), selector.get('limit')]
    return values


def validated_selector(target, selector, kind):
    """The old ``_selector`` of this role over the family ``kind``."""
    jobs = _jobs(target)
    if kind == 'local_file_source':
        raise NotImplementedError('unplaced:LocalFileSourceResults.selector')
    if kind == 'native_blast_masking':
        return validate_masking_result_selector(selector, operation=jobs['native_blast_masking']['operation'])
    if kind == 'native_blast_utility':
        return validate_blast_utility_result_selector(selector, operation=jobs['native_blast_utility']['operation'])
    if kind == 'api':
        raise NotImplementedError('unplaced:api_execution.validate_result_selector')
    if kind == 'native_blast_standard_database':
        return validate_standard_blast_database_selector(
            selector, program=jobs['native_blast_standard_database']['program'])
    if kind == 'native_blast_database':
        return validate_native_blast_database_result_selector(selector, program=jobs['native_blast_database']['program'])
    if kind == 'native_hmmer_preparation':
        job = jobs['native_hmmer_preparation']
        return validate_preparation_result_selector(selector, program=job['program'], mode=job['mode'])
    if kind == 'native_hmmer':
        return validate_native_hmmer_result_selector(selector, program=jobs['native_hmmer']['program'])
    if kind == 'native_blast':
        return validate_native_blast_result_selector(selector, program=jobs['native_blast']['program'])
    value = checked(selector, NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
    paths = list(value.get('paths', []))
    if 'path' in value:
        if value['path'] in paths:
            raise ValueError('ambiguous_execution_results_selector')
        paths.append(value['path'])
    if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
        raise ValueError('execution_results_paths_required')
    for path in paths:
        confined(path, target['assignment']['workspace'])
    return value


def read_from_parent(assignment, message):
    """The validated results assignment as the parent input: the assignment, its target, its family and validated
    selector, the requested byte windows of a native byte family, the credit unit and the records passed."""
    own = {name: assignment[name] for name in ('version', 'handoff_ref', 'selector')}
    own = checked(own, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
    target = validate_target(assignment['target'])
    if target['handle'] != own['handoff_ref']:
        raise ValueError('execution_result_target_conflict')
    unit = assignment['acquired_record_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    kind = family(target, own['selector'])
    selector = validated_selector(target, own['selector'], kind)
    parent_input = {'assignment': own, 'target': target, 'family': kind, 'selector': selector,
                    'requested': windows(selector) if kind == 'native_bytes' else {},
                    'acquired_record_unit': unit, 'record_refs': list(assignment.get('record_refs', [])),
                    'initial_result_refs': list(assignment.get('initial_result_refs', []))}
    if 'scientific_task' in assignment:
        parent_input['scientific_task'] = assignment['scientific_task']
    return parent_input
