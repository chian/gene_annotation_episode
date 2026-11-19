"""The A102 head's task: look up the process and tool-knowledge libraries, use the selected library tools, commit
typed reasoning, write its interpretation, prepare a revision for a new child, wait for native job events, or
commission one of its children. One unit is one such action.

Carried from the old ``task.py``, ``decision_delivery.py``, ``decision_presentation.py``, ``task_instructions.py``,
``child_commissioning.py``, ``child_message_owners.py``, ``operations.py``, ``scientific_commission_catalog.py``,
``task_state.py``, ``task_waiting.py`` and ``goal.py`` (the instruction text) at ``97308b94c``. The task always
offers a unit and never ends the Episode: only the yield controller does. The old ``redeliver_report`` and the
wait on pending in-process children, the report update the model wrote with every action, the decision-exchange
loop (``request_context``), the saved-exchange and execution-context checks, the replay and checkpoint code and the
old report delivery are not carried (the closing interpretation is the ``report`` tool's outcome:
``messages/final_to_parent.py``). The old wait on native job events is the tool ``wait_for_events``.

The old tool names ``process.search``, ``process.entry``, ``process.sources``, ``process.revise``,
``knowledge.search`` and so on are ``process_search``, ``process_entry``, ``process_sources``, ``process_revise``,
``knowledge_search`` ...: a tool name here is a lowercase identifier. A library tool keeps its library name with
its dots as underscores (``source.read`` is ``source_read``).

The tools of the old operation catalogue that read the old runner or the old shared root are not carried:
``episode.history``, ``episode.credit``, ``episode.annotation_score`` and ``episode.monitoring_information`` showed
the Episode its own journal views (they are the summary: ``messages/internal_summary.py``);
``episode.estimate_wait``, ``process.execution`` and ``execution.estimate`` for planning need the estimate table
and the execution-planning catalogue (``execution_estimate`` the library tool is carried; the planning read is
not); ``process.tools`` returned the selectable tool catalogue (the service ``tool_catalog``); and
``shared.request_information``, ``shared.publish_information``, ``shared.resolve_information_need``,
``shared.read_information`` and ``shared.list_information`` were the shared information board between episodes of
the old runner, which has no object any more.

An executed tool that returns an invalid outcome is still one unit, as before. A model answer that is malformed, that
names a record the Episode does not hold, that asks for an empty reasoning commit or that selects too few return
fields of a child is rejected in ``action`` (no unit): that is the validation of a model answer, never a check of a
commission (what ``msg_to_child`` builds is not checked).

Settings this episode reads (``ctx.settings``): ``yield_bindings`` (``yield_estimator.py``);
``process_library_directory`` (the frozen ``StructuralHomologyEvidenceLibrary`` snapshot the old head was
constructed with: the process lookups and the evidence-axis and thought-pattern entries the model is shown);
optionally ``knowledge_library_directory`` and ``launch_instructions_directory`` (the old workflow's tool-knowledge
and launch libraries) and ``tool_registry`` (the old ``ToolRegistry`` configuration); and, for a child that needs its
credit unit from this head, ``handoff_unit`` (execution launch), ``completion_target`` (resource launch),
``acquired_record_unit`` (execution results) and ``information_unit`` (monitor). The literature child's
``credit_unit`` is this head's own ``context.evidence_task.credit_unit``.

BLOCKED-ON-TOOL-CATALOG-SERVICE: the schemas of the library tools the commission selected came from the old
``services.tool_catalog(scope)`` (``ToolRegistry.catalog``, which needs the Store). No service wraps it:
``library_catalog`` and ``resolved_tool_info`` name the service and the call they want and raise where they are
reached (only when the selection names a library tool, or a revision names one). The library tools themselves call
``ToolRegistry`` over ``ctx.store``: library not carried.
"""
from __future__ import annotations

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.configuration.structural_homology_evidence.process_options import (
    StructuralHomologyEvidenceLibrary, catalog as process_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.evidence_axis_instructions import (
    instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.progress_provider import (
    FIELDS as PROGRESS_FIELDS)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.construction_records import (
    CHILD_SELECTION_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest,
    scientific_invocation_ref, validate_child_selection, validate_option_ref, validate_revision_origin)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, RECORD_SCHEMAS, REF, REFS, identity, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_information import (
    RESOURCE_KINDS, make_tool_info, tool_info_selection)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import BINDING_PATH, GOAL
from .messages.final_to_parent import COMMITTED_SOURCE, RESULTS_SOURCE

CHILD_SLOTS = {
    'structural_homology_evidence': BINDING_PATH,
    'literature': BINDING_PATH + '/published_evidence_assessment',
    'execution_launch': BINDING_PATH + '/execution_job_submission',
    'resource_launch': BINDING_PATH + '/resource_work_submission',
    'execution_results': BINDING_PATH + '/execution_result_acquisition',
    'resource_results': BINDING_PATH + '/resource_result_acquisition',
    'hpc': BINDING_PATH + '/hpc_work_planning',
    'monitor': BINDING_PATH + '/execution_progress_assessment',
}
SERVICES = ('tool_catalog', 'native_events')

TRANSPORT_ERROR = 'a102_head_tool_argument_transport_unsupported'
NO_APPLICABLE_EVIDENCE = 'no_applicable_evidence'
TEXT = {'type': 'string', 'minLength': 1}
INTEGER = {'type': 'integer', 'minimum': 0}
OPEN = {'type': 'object'}
LIST = {'type': 'array'}

# ---------------------------------------------------------------------------------------------------------------
# Instruction text (the old ``goal.py`` instruction-entry text, preceded by the merged A102 guidance of
# ``scientific_guidance.py``; ``task_instructions.compose_instructions`` appended the rest).

GUIDANCE = ('A102 owns comparative and experimental structural evidence. Scientific descendants remain A102. Use '
            'either path or both as useful, and return their separate scientific quantities and shared '
            'dependencies.\n\n')
INVESTIGATION = (
    "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start "
    'with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and '
    'known context. No initial candidate annotation or publicly searchable name is required. Possible functions can '
    'emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and '
    'thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and '
    'revise your approach. Selected instructions describe how to investigate; they are not evidence about this '
    'target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of '
    'inference when interpreting evidence. Missing information remains unknown.\n\n'
    'Choose an available tool, commit a scientific interpretation with the reason tool, write your interpretation '
    'with the report tool, commission a scoped child and select the fields of its return you want, or wait for '
    'native job events with wait_for_events when that informs the investigation. Use only the selected actual tools '
    'and their supplied resource instructions; choose callable operands through the declared response contract. '
    "Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from actual "
    'records. Keep inherited information distinct from new findings and completed work distinct from attempts. '
    'Return valid partial findings and specific failures through your report.\n\n'
    'Keep the assigned evidence axis, thought pattern and selected tools for this episode. process_revise prepares a '
    'different thought pattern and/or tool selection for a new child; it does not change this episode or start '
    'that child. To commission that alternative, copy its selection and revision_origin into the assignment of a '
    'separately selected structural_homology_evidence child with its own objective, purpose and constraints. '
    'Children own their iterative choices. The configured controller owns continuation. Waiting and unchanged '
    'observations do not manufacture progress.')
NATIVE_EVENT_GUIDANCE = (
    '\nThe separate native_event_targets input names native notification targets assigned or actually received by '
    'this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event '
    'means the original service exit receipt was committed; the service may still be closing, so this does not '
    'establish result readiness or a child episode return. after_cursor records an event cursor actually received, '
    'initially zero. Select wait_for_events with your own wait condition and subsequent status, monitor or result '
    'work. Request the native_event_targets source in a child return when that handoff is needed. No event '
    'probability, gain or scientific credit follows from registration or passing time alone.')
TAIL_GUIDANCE = ('\nSelect report with your interpretation of the evidence when the outcomes warrant it. Writing it '
                 'can be repeated and the latest one is what is returned; it does not end your work: only the '
                 'numerical controller does.')

PROCESS_REVISE_DESCRIPTION = (
    'Prepare a different thought pattern and/or selected actual tools for a new child investigating the same '
    "evidence axis. Return its selection for a separately selected child commission. Copy result.selection and "
    'revision_origin into that assignment. Changes no current process, starts no child and records no biological '
    'observation. Select the actual tool/resource choices from the tool catalogue for the desired investigation.')
REASON_DESCRIPTION = (
    'Commit one typed scientific reasoning payload about the evidence, using the common reasoning commit schema. A '
    'payload with every section empty is rejected before it runs and creates no unit, unless evidence_processing '
    'declares no_applicable_evidence with its reason and the exact examined byte spans.')
REPORT_DESCRIPTION = (
    'Write your interpretation of the evidence: what the target does within the assigned question, its '
    'qualification, and what stays unresolved. Writing it can be repeated and the latest one is what is returned.')
WAIT_DESCRIPTION = (
    'Wait for native job events named by registered targets this episode owns or received, or until a '
    'reconsideration time. Waiting reports readiness only and earns no credit.')

_REVISION_ARGUMENTS = obj({'thought_pattern': OPEN, 'child_tool_info': {
    'type': 'array', 'items': obj({'name': TEXT, 'resources': {'enum': list(RESOURCE_KINDS)}})}})
_EVENT_CONDITION = obj({'version': {'const': 'event_condition_v1'},
                        'events': {'type': 'array', 'items': obj({'handle': TEXT, 'event': TEXT,
                                                                   'after_cursor': INTEGER})},
                        'reconsider_at': {'type': ['string', 'null']}})
EVIDENCE_PROCESSING = obj({
    'kind': {'const': NO_APPLICABLE_EVIDENCE}, 'reason': TEXT,
    'examined': {'type': 'array', 'minItems': 1, 'items': obj({
        'source_ref': REF, 'representation': {'enum': ['original', 'text']}, 'start': INTEGER,
        'end': {'type': 'integer', 'minimum': 1}})}})
REPORT_SCHEMA = obj({'interpretation': TEXT, 'qualification': TEXT})

# ---------------------------------------------------------------------------------------------------------------
# The children: what the model chooses of each commission (the old ``to_child_*.py``: goal, purpose and the
# assignment; the typed return form the model wrote is now the selection of the child's own declared fields), the
# child's selectable return fields, the fields that must be selected when the head has a proposed annotation
# (the old ``required_return_sources``), and the settings key of each credit unit the child needs.

SELECTION_DESCRIPTION = {
    'structural_homology_evidence': 'the head again, with the selection and revision_origin a process_revise returned',
    'literature': 'published evidence assessment: search and read the literature and examine sources',
    'execution_launch': 'launch a concrete execution request on an explicit resource_id',
    'resource_launch': 'choose and launch an execution approach for a job on a resource',
    'execution_results': 'acquire the results of an already handed-off execution through its handoff',
    'resource_results': 'acquire requested data through the supplied receiving interface',
    'hpc': 'plan, launch, monitor and collect work on an HPC allocation',
    'monitor': 'observe the progress of running work (an execution handle)',
}
CHILD_ASSIGNMENTS = {
    'structural_homology_evidence': obj({'selection': OPEN, 'evidence_refs': REFS, 'constraints': OPEN,
                                         'revision_origin': OPEN}, ['selection', 'evidence_refs', 'constraints']),
    'literature': obj({'question_context_refs': REFS, 'source_refs': REFS, 'literature_task': OPEN,
                       'received_record_refs': REFS},
                      ['question_context_refs', 'source_refs', 'literature_task', 'received_record_refs']),
    'execution_launch': obj({'requests': OPEN, 'immutable_input_versions': LIST, 'constraints': OPEN,
                             'launch_instructions': OPEN, 'input_refs': REFS, 'already_handed_off_resource_ids': LIST,
                             'scientific_task': OPEN}, ['requests', 'immutable_input_versions', 'constraints']),
    'resource_launch': obj({'job_request': OPEN, 'immutable_input_versions': LIST, 'constraints': OPEN,
                            'resource_selection': OPEN, 'software_knowledge_refs': LIST,
                            'resource_knowledge_refs': LIST, 'launch_instructions': OPEN, 'adapter_assignment': OPEN,
                            'input_refs': REFS},
                           ['job_request', 'immutable_input_versions', 'constraints', 'software_knowledge_refs',
                            'resource_knowledge_refs', 'input_refs']),
    'execution_results': obj({'handoff_ref': REFS, 'selector': OPEN, 'resource_kind': {'enum': ['local', 'hpc']},
                              'known_result_refs': REFS}, ['handoff_ref', 'selector', 'resource_kind']),
    'resource_results': obj({'handoff': OPEN, 'requested_data_selector': OPEN}),
    'hpc': obj({'commission_id': TEXT, 'commission_source_ref': REFS, 'tool_request': OPEN, 'input_refs': REFS},
               ['input_refs']),
    'monitor': obj({'target_handle': TEXT, 'requested_fields': {'type': 'array', 'items': {'enum': list(PROGRESS_FIELDS)},
                                                                 'uniqueItems': True},
                    'known_progress_refs': REFS,
                    'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                                         'items': {'enum': sorted(RECORD_SCHEMAS)}}}),
}
EXECUTION_FIELDS = ('execution_handoff_refs', 'execution_result_refs', 'execution_completed',
                    'execution_file_source_refs', 'execution_file_capture_outcomes',
                    'execution_protein_structure_projections', 'execution_protein_structure_saved_sheets',
                    'execution_protein_structure_sequences', 'execution_protein_structure_failures')
RETURN_FIELDS = {
    'structural_homology_evidence': (RESULTS_SOURCE, COMMITTED_SOURCE),
    'literature': ('literature_screening_answers', 'literature_source_lead_dispositions'),
    'execution_launch': EXECUTION_FIELDS,
    'resource_launch': ('execution_handoff', 'execution_handoffs', 'adapter_facts', 'execution_handoff_refs'),
    'execution_results': (*EXECUTION_FIELDS, 'execution_result_origin'),
    'resource_results': ('execution_handoff', 'execution_handoffs', 'adapter_facts', 'interpretation'),
    'hpc': ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs'),
    'monitor': ('monitoring_progress_refs', 'monitoring_target_handle', 'monitoring_execution_state',
                'monitoring_result_available', 'monitoring_observed_at_unix_seconds',
                'monitoring_committed_record_refs', 'monitoring_dependency_handles',
                'monitoring_progress_snapshots'),
}
REQUIRED_WITH_ANNOTATION = {
    'structural_homology_evidence': (RESULTS_SOURCE, COMMITTED_SOURCE),
    'execution_launch': ('execution_handoff_refs',),
    'monitor': ('monitoring_progress_refs', 'monitoring_progress_snapshots'),
}
UNIT_SETTINGS = {'execution_launch': 'handoff_unit', 'resource_launch': 'completion_target',
                 'execution_results': 'acquired_record_unit', 'monitor': 'information_unit'}


def child_arguments(slot):
    """The model's commission of a child: the assignment and the selection, and, for every slot but ``literature``
    (whose objective is fixed and whose message is empty), the goal and purpose."""
    texts = {} if slot == 'literature' else {'goal': TEXT, 'purpose': TEXT}
    return obj({**texts, 'assignment': CHILD_ASSIGNMENTS[slot],
                'selection': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(RETURN_FIELDS[slot])}}})


# ---------------------------------------------------------------------------------------------------------------
# The library tools (the old selected tools of ``selection.child_tool_info``, run through the ``ToolRegistry``).

LIBRARY_TOOLS = ('public.rcsb.entry',
                 'public.rcsb.file',
                 'public.emdb.entry',
                 'public.alphafold.prediction',
                 'public.alphafold.file',
                 'state.query',
                 'source.read',
                 'source.locate',
                 'result.blast.hsp',
                 'image.view',
                 'public.pmc.versions',
                 'public.pmc.files',
                 'public.pmc.asset',
                 'source.archive.members',
                 'source.archive.extract',
                 'source.xlsx.sheets',
                 'source.xlsx.rows',
                 'source.pdf.info',
                 'source.pdf.text',
                 'source.pdf.page',
                 'material.parse',
                 'material.annotations',
                 'material.from_source',
                 'material.read',
                 'material.members',
                 'material.errors',
                 'material.member',
                 'material.header',
                 'library.members',
                 'library.select',
                 'library.read',
                 'reads.inspect',
                 'sequence.inspect',
                 'sequence.view',
                 'translation.codes',
                 'sequence.translate',
                 'reads.align',
                 'reads.map',
                 'sequence.align',
                 'sequence.sites',
                 'public.uniprot.search',
                 'public.uniprot.record',
                 'public.ncbi.search',
                 'public.ncbi.sequence',
                 'public.taxonomy',
                 'public.literature.search',
                 'public.literature.read',
                 'public.search.jobs',
                 'public.blast.search',
                 'public.blast.collect',
                 'public.sabiork.search',
                 'public.sabiork.read',
                 'public.brenda.search',
                 'public.brenda.read',
                 'public.brenda.graph_search',
                 'public.bioassay.search',
                 'public.bioassay.read',
                 'public.chembl.search',
                 'public.chembl.read',
                 'public.mavedb.search',
                 'public.mavedb.read',
                 'source.experimental.records',
                 'public.literature.sequence_identity',
                 'source.sequence.references',
                 'source.sequence.scan',
                 'public.ncbi.entrez',
                 'execution.estimate',
                 'inspect_protein_structure',
                 'extract_protein_structure_sequence',
                 'compare_protein_structures')
LIBRARY_NAMES = {name.replace('.', '_'): name for name in LIBRARY_TOOLS}
# Tools whose reads are bound to the records this Episode holds (the old ``permitted_record_refs``).
HELD_SOURCE_TOOLS = ('source.locate', 'result.blast.hsp', 'source.sequence.scan', 'source.sequence.references',
                     'source.experimental.records', 'inspect_protein_structure', 'extract_protein_structure_sequence',
                     'compare_protein_structures')


def python_name(dotted):
    return dotted.replace('.', '_')


def invalid(operation_ref, error):
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_tool(name, envelope, ctx):
    """Execute one library tool over ``ctx.store``. A failed selected operation is an outcome (the old
    ``record_execution_failure``); a custody error is not."""
    arguments, scope = envelope['arguments'], envelope['scope']
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=permitted)
    except (CustodyError, NotImplementedError):
        raise
    except ContractError as error:
        return invalid(identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}), error)
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


async def public_rcsb_entry(arguments, ctx):
    return await run_tool('public.rcsb.entry', arguments, ctx)


async def public_rcsb_file(arguments, ctx):
    return await run_tool('public.rcsb.file', arguments, ctx)


async def public_emdb_entry(arguments, ctx):
    return await run_tool('public.emdb.entry', arguments, ctx)


async def public_alphafold_prediction(arguments, ctx):
    return await run_tool('public.alphafold.prediction', arguments, ctx)


async def public_alphafold_file(arguments, ctx):
    return await run_tool('public.alphafold.file', arguments, ctx)


async def state_query(arguments, ctx):
    return await run_tool('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_tool('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_tool('source.locate', arguments, ctx)


async def result_blast_hsp(arguments, ctx):
    return await run_tool('result.blast.hsp', arguments, ctx)


async def image_view(arguments, ctx):
    return await run_tool('image.view', arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_tool('public.pmc.versions', arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_tool('public.pmc.files', arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_tool('public.pmc.asset', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_tool('source.archive.members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_tool('source.archive.extract', arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_tool('source.xlsx.sheets', arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_tool('source.xlsx.rows', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_tool('source.pdf.info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_tool('source.pdf.text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_tool('source.pdf.page', arguments, ctx)


async def material_parse(arguments, ctx):
    return await run_tool('material.parse', arguments, ctx)


async def material_annotations(arguments, ctx):
    return await run_tool('material.annotations', arguments, ctx)


async def material_from_source(arguments, ctx):
    return await run_tool('material.from_source', arguments, ctx)


async def material_read(arguments, ctx):
    return await run_tool('material.read', arguments, ctx)


async def material_members(arguments, ctx):
    return await run_tool('material.members', arguments, ctx)


async def material_errors(arguments, ctx):
    return await run_tool('material.errors', arguments, ctx)


async def material_member(arguments, ctx):
    return await run_tool('material.member', arguments, ctx)


async def material_header(arguments, ctx):
    return await run_tool('material.header', arguments, ctx)


async def library_members(arguments, ctx):
    return await run_tool('library.members', arguments, ctx)


async def library_select(arguments, ctx):
    return await run_tool('library.select', arguments, ctx)


async def library_read(arguments, ctx):
    return await run_tool('library.read', arguments, ctx)


async def reads_inspect(arguments, ctx):
    return await run_tool('reads.inspect', arguments, ctx)


async def sequence_inspect(arguments, ctx):
    return await run_tool('sequence.inspect', arguments, ctx)


async def sequence_view(arguments, ctx):
    return await run_tool('sequence.view', arguments, ctx)


async def translation_codes(arguments, ctx):
    return await run_tool('translation.codes', arguments, ctx)


async def sequence_translate(arguments, ctx):
    return await run_tool('sequence.translate', arguments, ctx)


async def reads_align(arguments, ctx):
    return await run_tool('reads.align', arguments, ctx)


async def reads_map(arguments, ctx):
    return await run_tool('reads.map', arguments, ctx)


async def sequence_align(arguments, ctx):
    return await run_tool('sequence.align', arguments, ctx)


async def sequence_sites(arguments, ctx):
    return await run_tool('sequence.sites', arguments, ctx)


async def public_uniprot_search(arguments, ctx):
    return await run_tool('public.uniprot.search', arguments, ctx)


async def public_uniprot_record(arguments, ctx):
    return await run_tool('public.uniprot.record', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_tool('public.ncbi.search', arguments, ctx)


async def public_ncbi_sequence(arguments, ctx):
    return await run_tool('public.ncbi.sequence', arguments, ctx)


async def public_taxonomy(arguments, ctx):
    return await run_tool('public.taxonomy', arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_tool('public.literature.search', arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_tool('public.literature.read', arguments, ctx)


async def public_search_jobs(arguments, ctx):
    return await run_tool('public.search.jobs', arguments, ctx)


async def public_blast_search(arguments, ctx):
    return await run_tool('public.blast.search', arguments, ctx)


async def public_blast_collect(arguments, ctx):
    return await run_tool('public.blast.collect', arguments, ctx)


async def public_sabiork_search(arguments, ctx):
    return await run_tool('public.sabiork.search', arguments, ctx)


async def public_sabiork_read(arguments, ctx):
    return await run_tool('public.sabiork.read', arguments, ctx)


async def public_brenda_search(arguments, ctx):
    return await run_tool('public.brenda.search', arguments, ctx)


async def public_brenda_read(arguments, ctx):
    return await run_tool('public.brenda.read', arguments, ctx)


async def public_brenda_graph_search(arguments, ctx):
    return await run_tool('public.brenda.graph_search', arguments, ctx)


async def public_bioassay_search(arguments, ctx):
    return await run_tool('public.bioassay.search', arguments, ctx)


async def public_bioassay_read(arguments, ctx):
    return await run_tool('public.bioassay.read', arguments, ctx)


async def public_chembl_search(arguments, ctx):
    return await run_tool('public.chembl.search', arguments, ctx)


async def public_chembl_read(arguments, ctx):
    return await run_tool('public.chembl.read', arguments, ctx)


async def public_mavedb_search(arguments, ctx):
    return await run_tool('public.mavedb.search', arguments, ctx)


async def public_mavedb_read(arguments, ctx):
    return await run_tool('public.mavedb.read', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_tool('source.experimental.records', arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_tool('public.literature.sequence_identity', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_tool('source.sequence.references', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_tool('source.sequence.scan', arguments, ctx)


async def public_ncbi_entrez(arguments, ctx):
    return await run_tool('public.ncbi.entrez', arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_tool('execution.estimate', arguments, ctx)


async def inspect_protein_structure(arguments, ctx):
    return await run_tool('inspect_protein_structure', arguments, ctx)


async def extract_protein_structure_sequence(arguments, ctx):
    return await run_tool('extract_protein_structure_sequence', arguments, ctx)


async def compare_protein_structures(arguments, ctx):
    return await run_tool('compare_protein_structures', arguments, ctx)


# ---------------------------------------------------------------------------------------------------------------
# What the tool catalogue service is asked (BLOCKED-ON-TOOL-CATALOG-SERVICE: no such service is built).

def library_catalog(ctx, names):
    """The contracts (description and input schema) of the selected library tools (the old
    ``services.tool_catalog(scope)``).

    BLOCKED-ON-TOOL-CATALOG-SERVICE: tool_catalog; wanted call: ``ctx.services['tool_catalog'].read('catalog')``
    (a recorded read of a decision), which returns ``{dotted name: {'description', 'input_schema', ...}}`` for the
    tools of the configured ``ToolRegistry``. Reached only when the selection names a library tool."""
    if not names:
        return {}
    raise NotImplementedError("BLOCKED-ON-TOOL-CATALOG-SERVICE: tool_catalog; wanted call: ctx.services"
                              "['tool_catalog'].read('catalog')")
    return ctx.services['tool_catalog'].read('catalog')


def resolved_tool_info(ctx, selectors):
    """The tool information of selected tools (the old ``tool_library.resolve_tool_info(selected, catalog)``).

    BLOCKED-ON-TOOL-CATALOG-SERVICE: tool_catalog; wanted call: ``ctx.services['tool_catalog'].catalog()`` (a
    tool is handed the service itself). Reached only when the revision names a tool."""
    if not selectors:
        return []
    raise NotImplementedError("BLOCKED-ON-TOOL-CATALOG-SERVICE: tool_catalog; wanted call: ctx.services"
                              "['tool_catalog'].catalog()")
    catalog = ctx.services['tool_catalog'].catalog()
    return [make_tool_info({'name': row['name'], **catalog[row['name']]}, row['resources']) for row in selectors]


# ---------------------------------------------------------------------------------------------------------------
# The tools.

def process_search(arguments, ctx):
    return StructuralHomologyEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        'process.search', arguments)


def process_entry(arguments, ctx):
    return StructuralHomologyEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        'process.entry', arguments)


def process_sources(arguments, ctx):
    return StructuralHomologyEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        'process.sources', arguments)


def knowledge_search(arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute('knowledge.search', arguments)


def knowledge_entry(arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute('knowledge.entry', arguments)


def knowledge_read(arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute('knowledge.read', arguments)


def process_revise(arguments, ctx):
    """The old ``process.revise``: prepare a different thought pattern and tool selection for a separately
    commissioned child. It changes no current process, starts no child and records no biological observation. The
    thought pattern must be an option of the commission's own library; an invalid request is an ``invalid``
    outcome that enters the iterator, as before."""
    initial = arguments['selection']
    revision = {key: arguments[key] for key in ('thought_pattern', 'child_tool_info')}
    operation_ref = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise', 'arguments': revision})
    try:
        thought = validate_option_ref(revision['thought_pattern'])
        if thought['slot'] != 'thought_pattern' or thought['library_id'] != initial['evidence_axis']['library_id']:
            raise ContractError('scientific_selection_library_mismatch')
        StructuralHomologyEvidenceLibrary(ctx.settings['process_library_directory']).resolve(thought)
        information = resolved_tool_info(ctx, tool_info_selection(revision['child_tool_info']))
        proposed = {'version': SELECTION_VERSION, 'evidence_axis': initial['evidence_axis'],
                    'thought_pattern': thought, 'child_tool_info': information}
        child_selection = validate_child_selection({
            'version': CHILD_SELECTION_VERSION, 'parent_selection_sha256': scientific_digest(initial),
            'selection': proposed})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION,
            'parent_invocation_ref': scientific_invocation_ref(ctx.run_id, ((ctx.binding_path, ctx.episode_id),)),
            'preparation_operation_ref': operation_ref})
    except ValueError as error:
        return invalid(operation_ref, error)
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': child_selection, 'revision_origin': origin, 'feedback': None}


def reason(arguments, ctx):
    """One typed reasoning commit (the old ``reason`` action; the head had no ``execute_reasoning`` of its own).
    The Store commit is receipted as produced by this unit. The ``evidence_processing`` declaration the answer
    carried rides in the outcome."""
    result = dict(ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key))
    if 'evidence_processing' in arguments:
        result['evidence_processing'] = arguments['evidence_processing']
    return result


def report(arguments, ctx):
    """The closing value the model writes: its interpretation. It is this unit's outcome; the summary holds the
    latest one and ``final_to_parent`` returns it as the finding."""
    return {'report': arguments}


async def wait_for_events(arguments, ctx):
    """The old selected wait on native job events (``task_waiting`` and ``jobs.waiting.selected_wait``): it earns
    no credit; an event target the ledger cannot use is a failed outcome that enters the iterator."""
    return await selected_wait(ctx.services['native_events'], arguments['condition'])


TOOLS = {'process_search': process_search, 'process_entry': process_entry, 'process_sources': process_sources,
         'knowledge_search': knowledge_search, 'knowledge_entry': knowledge_entry, 'knowledge_read': knowledge_read,
         'process_revise': process_revise, 'reason': reason, 'report': report, 'wait_for_events': wait_for_events,
         'public_rcsb_entry': public_rcsb_entry,
         'public_rcsb_file': public_rcsb_file,
         'public_emdb_entry': public_emdb_entry,
         'public_alphafold_prediction': public_alphafold_prediction,
         'public_alphafold_file': public_alphafold_file,
         'state_query': state_query,
         'source_read': source_read,
         'source_locate': source_locate,
         'result_blast_hsp': result_blast_hsp,
         'image_view': image_view,
         'public_pmc_versions': public_pmc_versions,
         'public_pmc_files': public_pmc_files,
         'public_pmc_asset': public_pmc_asset,
         'source_archive_members': source_archive_members,
         'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets,
         'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info,
         'source_pdf_text': source_pdf_text,
         'source_pdf_page': source_pdf_page,
         'material_parse': material_parse,
         'material_annotations': material_annotations,
         'material_from_source': material_from_source,
         'material_read': material_read,
         'material_members': material_members,
         'material_errors': material_errors,
         'material_member': material_member,
         'material_header': material_header,
         'library_members': library_members,
         'library_select': library_select,
         'library_read': library_read,
         'reads_inspect': reads_inspect,
         'sequence_inspect': sequence_inspect,
         'sequence_view': sequence_view,
         'translation_codes': translation_codes,
         'sequence_translate': sequence_translate,
         'reads_align': reads_align,
         'reads_map': reads_map,
         'sequence_align': sequence_align,
         'sequence_sites': sequence_sites,
         'public_uniprot_search': public_uniprot_search,
         'public_uniprot_record': public_uniprot_record,
         'public_ncbi_search': public_ncbi_search,
         'public_ncbi_sequence': public_ncbi_sequence,
         'public_taxonomy': public_taxonomy,
         'public_literature_search': public_literature_search,
         'public_literature_read': public_literature_read,
         'public_search_jobs': public_search_jobs,
         'public_blast_search': public_blast_search,
         'public_blast_collect': public_blast_collect,
         'public_sabiork_search': public_sabiork_search,
         'public_sabiork_read': public_sabiork_read,
         'public_brenda_search': public_brenda_search,
         'public_brenda_read': public_brenda_read,
         'public_brenda_graph_search': public_brenda_graph_search,
         'public_bioassay_search': public_bioassay_search,
         'public_bioassay_read': public_bioassay_read,
         'public_chembl_search': public_chembl_search,
         'public_chembl_read': public_chembl_read,
         'public_mavedb_search': public_mavedb_search,
         'public_mavedb_read': public_mavedb_read,
         'source_experimental_records': source_experimental_records,
         'public_literature_sequence_identity': public_literature_sequence_identity,
         'source_sequence_references': source_sequence_references,
         'source_sequence_scan': source_sequence_scan,
         'public_ncbi_entrez': public_ncbi_entrez,
         'execution_estimate': execution_estimate,
         'inspect_protein_structure': inspect_protein_structure,
         'extract_protein_structure_sequence': extract_protein_structure_sequence,
         'compare_protein_structures': compare_protein_structures}


# ---------------------------------------------------------------------------------------------------------------
# Deciding.

def selected_library_names(summary):
    """The library tools this commission selected (``selection.child_tool_info``), by their tool names here."""
    return [python_name(row['name']) for row in summary['selection']['child_tool_info']
            if python_name(row['name']) in LIBRARY_NAMES]


def offered(summary, settings):
    """The tools offered now: the process lookups, the revision, the reasoning commit, the report and the wait,
    the knowledge lookups when a knowledge library is configured, and the selected library tools."""
    names = ['process_search', 'process_entry', 'process_sources', 'process_revise', 'reason', 'report',
             'wait_for_events']
    if settings.get('knowledge_library_directory') is not None:
        names += ['knowledge_search', 'knowledge_entry', 'knowledge_read']
    return {'own': names, 'library': selected_library_names(summary)}


def reason_schema(summary):
    """The reason tool's arguments: the common commit, plus the declaration that the examined evidence contains
    nothing applicable (the old ``reasoning_action_schema`` envelope)."""
    return obj({'commit': summary['reasoning_schema'], 'evidence_processing': EVIDENCE_PROCESSING}, ['commit'])


def catalog(names, summary, contracts):
    """The tools the model is shown: name, description and input schema."""
    own = {entry['name']: entry for entry in (*process_catalog(), *knowledge_catalog())}
    entries = []
    for name in names['own']:
        if name == 'process_revise':
            entries.append({'name': name, 'description': PROCESS_REVISE_DESCRIPTION, 'input_schema': _REVISION_ARGUMENTS})
        elif name == 'reason':
            entries.append({'name': name, 'description': REASON_DESCRIPTION, 'input_schema': reason_schema(summary)})
        elif name == 'report':
            entries.append({'name': name, 'description': REPORT_DESCRIPTION, 'input_schema': REPORT_SCHEMA})
        elif name == 'wait_for_events':
            entries.append({'name': name, 'description': WAIT_DESCRIPTION,
                            'input_schema': obj({'condition': _EVENT_CONDITION})})
        else:
            entry = own[name.replace('_', '.', 1)]
            entries.append({'name': name, 'description': entry['description'], 'input_schema': entry['input_schema']})
    for name in names['library']:
        entry = contracts[LIBRARY_NAMES[name]]
        entries.append({'name': name, 'description': entry['description'], 'input_schema': entry['input_schema']})
    return entries


def selection_schema(names, summary, contracts):
    """What the model answers with: one tool and its arguments, or one child and its commission (the old action
    schema over the tool and child kinds)."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in catalog(names, summary, contracts)]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'arguments': child_arguments(slot)})
                for slot in CHILD_SLOTS]
    return obj({'selection': {'anyOf': tools + children}})


def instructions(*, knowledge, launch_library):
    """The old composition: the merged A102 guidance and instruction-entry text (which replaced the default
    instructions), the reasoning-commit requirement, the tool-knowledge and launch library texts when they are
    offered, and the native-event paragraph. The paragraphs about repairing an undelivered child report, about a
    pending in-process child and about the ``request_context`` exchange describe actions that no longer exist."""
    text = GUIDANCE + INVESTIGATION + '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text + NATIVE_EVENT_GUIDANCE + TAIL_GUIDANCE


def binding_block(summary, settings):
    """The old ``internal_summary.decision_context`` block ``structural_homology_evidence``: the selection, the
    evidence-axis view, the thought pattern, the selected tool information and the assignment. The entries come
    from the frozen library snapshot (immutable files)."""
    library = StructuralHomologyEvidenceLibrary(settings['process_library_directory'])
    selection = summary['selection']
    thought = library.resolve(selection['thought_pattern'])
    fields = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
              'outcome_contingencies', 'boundary')
    return {'selection': {**selection, 'child_tool_info': [{'name': row['name'], 'resources': row['resources']}
                                                            for row in selection['child_tool_info']]},
            'evidence_axis': instruction_view(library.resolve(selection['evidence_axis'])),
            'thought_pattern': {name: thought[name] for name in fields if name in thought},
            'assignment': {key: summary[key] for key in ('selection', 'proposed_annotation_ref', 'evidence_refs',
                                                         'constraints', 'context', 'revision_origin')},
            'permitted_children': list(CHILD_SLOTS)}


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the goal and scope, the working state (interpretation, committed
    records, revisions, children's reports), the held records, the credit and its components, the credit binding,
    the outcomes, the tools and children, the measured time, the yield table and the library listings (the old
    decision state and inputs, over this episode's summary and the recorded service reads)."""
    settings = ctx.settings
    names = offered(summary, settings)
    contracts = library_catalog(ctx, names['library'])
    view = summary['credit_view']
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    context = {
        'goal': {'objective': summary['goal']['objective'], 'detail': GOAL},
        'scope': summary['scope'],
        'working_state': {'interpretation': summary['report'], 'committed_record_refs': summary['committed_record_refs'],
                          'revisions': summary['revisions'], 'children': summary['children']},
        'visible_record_refs': summary['visible_record_refs'],
        'current_credit': view['credit'],
        'current_evidence_vector': view.get('axis_components'),
        'credit_binding': summary['credit_definition'],
        'investigation_progress': {key: view[key] for key in ('retained_finding_count', 'inactive_dependencies',
                                                              'detail_pages') if key in view},
        '_completed_work_axis_results': {key: view[key] for key in ('a102_sheet', 'target_sheets', 'tool_attachments',
                                                                    'source_contributions') if key in view},
        'tools': catalog(names, summary, contracts),
        'child_options': [{'slot': slot, 'description': SELECTION_DESCRIPTION[slot],
                           'return_fields': list(RETURN_FIELDS[slot]),
                           'required_return_fields': list(REQUIRED_WITH_ANNOTATION.get(slot, ()))
                           if summary['proposed_annotation_ref'] else []} for slot in CHILD_SLOTS],
        'time_accounting': time_accounting(ctx.clock.progress_time),
        'last_local_outcome': summary['last_outcome'],
        'outcome_history': summary['outcome_history'],
        'received_progress_snapshots': summary['progress_snapshots'],
        'structural_homology_evidence': binding_block(summary, settings)}
    context['completed_work_axis_results'] = context.pop('_completed_work_axis_results')
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['controller'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context()},
        conflict='initial_binding_context_field_conflict')
    schema = selection_schema(names, summary, contracts)
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, strict_output_schema(schema, open_records_as_text=True,
                                                      argument_transport_error=TRANSPORT_ERROR))


def empty_commit(commit, schema, processing):
    """The old test of ``apply_response``: every section of the commit is empty and the answer is not the
    ``no_applicable_evidence`` declaration (the head had no ``reasoning_has_task_content``)."""
    required = set(schema.get('required', schema['properties']))
    return (required <= set(commit) <= set(schema['properties']) and all(value == [] for value in commit.values())
            and (processing or {}).get('kind') != NO_APPLICABLE_EVIDENCE)


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or child, arguments that do not fit the schema, an empty reasoning commit, a child
    commission is not checked here: msg_to_child builds it and any error in it fails the run.
    A tool is handed no summary, so its call carries the scope (and, for a revision, the selection) it works from.
    The credit units a child needs are the settings of this Episode: a missing one raises (a wrong commission
    fails)."""
    names = offered(summary, ctx.settings)
    schema = selection_schema(names, summary, library_catalog(ctx, names['library']))
    try:
        value = decode_strict_output(response, schema, open_records_as_text=True,
                                     argument_transport_error=TRANSPORT_ERROR)
        validate_schema(value, schema)
        selection = value['selection']
        if selection['kind'] != 'child' and selection['tool'] == 'reason':
            arguments = selection['arguments']
            if empty_commit(arguments['commit'], summary['reasoning_schema'], arguments.get('evidence_processing')):
                raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    arguments = selection['arguments']
    if selection['kind'] == 'child':
        slot = selection['slot']
        units = {}
        if slot in UNIT_SETTINGS:
            units[UNIT_SETTINGS[slot]] = ctx.settings[UNIT_SETTINGS[slot]]
        if slot == 'literature':
            units['credit_unit'] = summary['credit_unit']
        return ChildCall(slot, {**arguments, 'units': units})
    name = selection['tool']
    if name in LIBRARY_NAMES:
        return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})
    if name == 'process_revise':
        return ToolCall(name, {**arguments, 'selection': summary['selection']})
    if name == 'reason':
        return ToolCall(name, {**arguments, 'scope': summary['scope']})
    return ToolCall(name, arguments)
