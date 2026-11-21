"""The commissions of the five child slots, carried from the old ``to_child_*.py`` request assemblers
(``to_child_partner_presence_evidence``, ``to_child_hpc_work_planning``, ``to_child_execution_job_submission``, ``to_child_execution_result_acquisition``) and
``to_child_execution_progress_assessment.prepare_request``.

The old assemblers built an ``EpisodeRequest`` envelope (goal, ``message`` with the scope, the ``initial_report``,
``job_assignment``, ``episode_assignment`` with its ``launch_instructions``, the filled process, the invocation
reference and ``knowledge_inheritance``) and a parent-written report contract. Now the commission is a
``ChildMessage``: the objective, a message (the purpose), the assignment under the names the child's own form
declares (the old ``episode_assignment`` keys, under the same names) and the selection of the fields the child
declares it can return (the old fact-source names, under the same names). Not carried: the envelope, the
``inprocess_completion_order`` stamp, the report-contract declaration check, the invocation reference and the
knowledge inheritance (system custody). Every record the child's code will read is named in its assignment
(``record_refs`` fields); a wrong commission fails (rule 1): an undeclared selection, an unheld record or a missing
key raises where the child is built.

The head fills the child's new fields from its own parent input: the scope, the finding unit and the units. The
model supplies only what the old model supplied (the objective, the purpose, the child's own assignment fields and
the return fields it wants)."""
from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.construction_records import (
    selector_selection)

from .final_to_parent import RETURN_FORM

# What each child declares it can return and the parent may select (read from the children's own
# `messages/final_to_parent.py` RETURN_FORM as data: the fields declared `required=False`, under the same names).
# `credit` and `finding` are always returned and are not selectable.
SELECTABLE = {
    'launch': {
        'execution_handoff_refs': 'Qualified original handoff sources received from the launch children: the job identity, preserv',
        'execution_completed': 'Whether this assignment has actual verified endpoint information (a usable handoff was received',
        'execution_result_refs': 'Qualified actual requested result acquisitions: none, a launch acquires no results',
        'execution_file_source_refs': 'Source references of retained local file streams: none, a launch acquires no results',
        'execution_file_capture_outcomes': 'Recorded selected-file availability: always empty here',
        'execution_result_origin': 'Actual acquisition semantics of retained results: the empty record, a launch retains none',
        'execution_blast_hsps': 'Optional explicitly requested native measurements of acquired HSPs: none for a launch',
        'execution_blast_pairwise_result_refs': 'BLAST pairwise result references: none for a launch',
        'execution_infernal_result_refs': 'Infernal result references: none for a launch',
        'bvbrc_appservice_support_refs': 'Actually received BV-BRC AppService support receipts (no launch child returns any)',
        'execution_hmmer_domain_rows': 'Explicitly selected native numerical rows with exact source and observation bindings. Unbound r',
        'execution_nhmmer_locus_rows': 'Explicitly selected native numerical rows with exact source and observation bindings. Unbound r',
        'execution_hmmalign_sequence_rows': 'Explicitly selected native numerical rows with exact source and observation bindings. Unbound r',
        'execution_blast_standard_database_search_rows': 'Requested frozen search measurements with original identities, units and qualified missingness.',
        'execution_blast_standard_database_search_statistic_rows': 'Requested frozen search_statistic measurements with original identities, units and qualified mi',
        'execution_blast_standard_database_hsp_rows': 'Requested frozen hsp measurements with original identities, units and qualified missingness.',
        'execution_blast_standard_database_sequence_hit_rows': 'Requested frozen sequence_hit measurements with original identities, units and qualified missin',
        'execution_blast_standard_database_sequence_group_rows': 'Requested frozen sequence_group measurements with original identities, units and qualified miss',
        'execution_blast_standard_database_sequence_function_rows': 'Requested frozen sequence_function measurements with original identities, units and qualified m',
        'execution_blast_standard_database_sequence_population_rows': 'Requested frozen sequence_population measurements with original identities, units and qualified',
        'execution_blast_standard_database_sequence_taxonomy_rows': 'Requested frozen sequence_taxonomy measurements with original identities, units and qualified m',
        'execution_blast_standard_database_sequence_quality_rows': 'Requested frozen sequence_quality measurements with original identities, units and qualified mi',
        'execution_blast_standard_database_pssm_matrix_rows': 'Requested frozen pssm_matrix measurements with original identities, units and qualified missing',
        'execution_blast_standard_database_pssm_position_rows': 'Requested frozen pssm_position measurements with original identities, units and qualified missi',
        'execution_blast_standard_database_pssm_cell_rows': 'Requested frozen pssm_cell measurements with original identities, units and qualified missingne',
        'execution_blast_standard_database_sequence_record_quality_rows': 'Requested frozen sequence_record_quality measurements with original identities, units and quali',
        'execution_blast_standard_database_result_refs': 'Frozen standard database result result_refs.',
        'execution_blast_standard_database_failures': 'Frozen standard database result failures.',
        'execution_blast_database_search_rows': 'Selected frozen search numerical components; null and measured zero are distinct. Full native a',
        'execution_blast_database_hsp_rows': 'Selected frozen hsp numerical components; null and measured zero are distinct. Full native asso',
        'execution_blast_database_sequence_hit_rows': 'Selected frozen sequence_hit numerical components; null and measured zero are distinct. Full na',
        'execution_blast_database_sequence_group_rows': 'Selected frozen sequence_group numerical components; null and measured zero are distinct. Full',
        'execution_blast_database_sequence_function_rows': 'Selected frozen sequence_function numerical components; null and measured zero are distinct. Fu',
        'execution_blast_database_sequence_population_rows': 'Selected frozen sequence_population numerical components; null and measured zero are distinct.',
        'execution_blast_database_sequence_taxonomy_rows': 'Selected frozen sequence_taxonomy numerical components; null and measured zero are distinct. Fu',
        'execution_blast_database_sequence_quality_rows': 'Selected frozen sequence_quality numerical components; null and measured zero are distinct. Ful',
        'execution_blast_database_profile_model_rows': 'Selected frozen profile_model numerical components; null and measured zero are distinct. Full n',
        'execution_blast_database_profile_hsp_model_rows': 'Selected frozen profile_hsp_model numerical components; null and measured zero are distinct. Fu',
        'execution_blast_database_profile_overlap_rows': 'Selected frozen profile_overlap numerical components; null and measured zero are distinct. Full',
        'execution_blast_database_pssm_matrix_rows': 'Selected frozen pssm_matrix numerical components; null and measured zero are distinct. Full nat',
        'execution_blast_database_pssm_cell_rows': 'Selected frozen pssm_cell numerical components; null and measured zero are distinct. Full nativ',
        'execution_blast_database_pssm_position_rows': 'Selected frozen pssm_position numerical components; null and measured zero are distinct. Full n',
        'execution_blast_database_iteration_inclusion_rows': 'Selected frozen iteration_inclusion numerical components; null and measured zero are distinct.',
        'execution_blast_database_iteration_convergence_rows': 'Selected frozen iteration_convergence numerical components; null and measured zero are distinct',
        'execution_blast_database_iteration_comparison_rows': 'Selected frozen iteration_comparison numerical components; null and measured zero are distinct.',
        'execution_blast_database_vdb_subject_rows': 'Selected frozen vdb_subject numerical components; null and measured zero are distinct. Full nat',
        'execution_blast_database_vdb_membership_rows': 'Selected frozen vdb_membership numerical components; null and measured zero are distinct. Full',
        'execution_blast_database_vdb_sequence_group_rows': 'Selected frozen vdb_sequence_group numerical components; null and measured zero are distinct. F',
        'execution_blast_database_vdb_sample_rows': 'Selected frozen vdb_sample numerical components; null and measured zero are distinct. Full nati',
        'execution_blast_database_vdb_feature_rows': 'Selected frozen vdb_feature numerical components; null and measured zero are distinct. Full nat',
        'execution_blast_database_vdb_feature_hsp_rows': 'Selected frozen vdb_feature_hsp numerical components; null and measured zero are distinct. Full',
        'execution_blast_database_vdb_taxonomy_rows': 'Selected frozen vdb_taxonomy numerical components; null and measured zero are distinct. Full na',
        'execution_blast_database_vdb_quality_rows': 'Selected frozen vdb_quality numerical components; null and measured zero are distinct. Full nat',
        'execution_blast_database_vdb_population_rows': 'Selected frozen vdb_population numerical components; null and measured zero are distinct. Full',
        'execution_blast_database_vdb_population_function_rows': 'Selected frozen vdb_population_function numerical components; null and measured zero are distin',
        'execution_blast_database_sequence_record_quality_rows': 'Selected frozen sequence_record_quality numerical components; null and measured zero are distin',
        'execution_blast_database_vdb_function_summary_rows': 'Selected frozen vdb_function_summary numerical components; null and measured zero are distinct.',
        'execution_blast_database_vdb_function_rows': 'Selected frozen vdb_function numerical components; null and measured zero are distinct. Full na',
        'execution_blast_database_vdb_function_contribution_rows': 'Selected frozen vdb_function_contribution numerical components; null and measured zero are dist',
        'execution_blast_database_vdb_function_census_rows': 'Selected frozen vdb_function_census numerical components; null and measured zero are distinct.',
        'execution_blast_database_result_refs': 'Frozen selected native database result result_refs.',
        'execution_blast_database_failures': 'Frozen selected native database result failures.',
        'execution_blast_database_vdb_function_saved_inputs': 'Exact admitted immutable VDB function generation available for a separately selected saved calc',
        'execution_hmmer_preparation_rows': 'Requested saved numerical measurements and checks with exact row and artifact associations; gen',
        'execution_hmmer_preparation_artifacts': 'Explicitly requested artifact occurrences and those required by selected rows/checks, preservin',
        'execution_hmmer_preparation_population': 'Decoded saved row and selected artifact accounting; this is not biological completeness.',
        'execution_hmmer_preparation_result_refs': 'Original HMMER preparation result references.',
        'execution_hmmer_preparation_failures': 'Recorded typed acquisition, grading or projection failures with their original handoff and affe',
        'execution_blast_pairwise_hsp_rows': 'Requested native pairwise BLAST numbers in original search/HSP order. Coverage uses explicit fu',
        'execution_blast_pairwise_union_rows': 'Requested native pairwise BLAST numbers in original search/HSP order. Coverage uses explicit fu',
        'execution_rna_structure_summary_rows': 'Exactly requested original RNA quantities and specific qualifications; no annotation confidence',
        'execution_rna_structure_pair_rows': 'Exactly requested original RNA quantities and specific qualifications; no annotation confidence',
        'execution_rna_structure_stem_rows': 'Exactly requested original RNA quantities and specific qualifications; no annotation confidence',
        'execution_rna_structure_region_rows': 'Exactly requested original RNA quantities and specific qualifications; no annotation confidence',
        'execution_rna_structure_failure_rows': 'Exactly requested original RNA quantities and specific qualifications; no annotation confidence',
        'execution_rna_structure_result_refs': 'Requested RNA result sources only; no auxiliary bytes or unrequested numerical rows.',
        'execution_rna_structure_saved_sheet_inputs': 'Explicit original saved-sheet operands for deterministic recalculation; no new acquisition cred',
        'execution_rna_structure_comparison_projections': 'Exactly selected retained RNA comparison facts and required population qualifications; no impli',
        'expression_nmf_measurements': 'Requested native NMF diagnostics or calculated loading, contribution or residual quantities wit',
        'expression_nmf_saved_sheets': 'Explicitly returned retained numerical-sheet identities for later selected calculation; no gran',
        'expression_nmf_failures': 'Recorded located NMF input, capture, calculation and delivery failures; no model-composed findi',
    },
    'results': {
        'execution_handoff_refs': 'The handoff row of the job this episode acquired results of',
        'execution_job_record_refs': 'The latest check row the results episode holds and, once the results were fetched, the closure row of the job',
        'execution_result_refs': 'The result acquisitions the results episode retained: each result record, its information artifact and the fetched files its windows lie in',
        'execution_completed': 'Whether the job finished and every requested byte is retained. Yielding alone is false',
    },
    # The monitor always returns its credit, its finding (whether the job was observed, its state, whether its results
    # are available, when) and its check rows (``check_refs``); its measurements are selectable.
    'monitor': {
        'job_returncode': "The return code of the job's ended command, as {known, value}",
        'job_duration_seconds': "The duration of the job's ended command in seconds, as {known, value}",
        'job_elapsed_seconds': 'The elapsed seconds of the job still running at the latest check, as {known, value}',
        'stdout_bytes': "The size of the job's stdout.log at the latest check, as {known, value}",
        'stderr_bytes': "The size of the job's stderr.log at the latest check, as {known, value}",
        'log_window_refs': 'The log windows the monitor read: each window row and the artifact of its bytes',
        'event_receipt_refs': "The receipts of the job's end event a wait of the monitor brought into custody",
    },
    'hpc': {
        'hpc_credit': 'Signed measured credit; repeated polling adds none',
        'hpc_model_ref': 'Immutable selected prediction model identity',
        'hpc_accepted_obligations': 'Original obligations with accepted actual results',
        'hpc_result_refs': 'Sources containing original result bytes and attempt custody',
        'hpc_result_artifact_refs': 'The artifact of each source named in hpc_result_refs (a returned record does not bring the reco',
    },
}


# The selectable names of this head's own return (the recursive child).
SELECTABLE['partner_presence_evidence'] = {name: field.meaning for name, field in RETURN_FORM.fields.items()
                                           if not field.required}


def present(arguments, names):
    """The optional arguments the model supplied, under the child's field names."""
    return {name: arguments[name] for name in names if arguments.get(name) is not None}


def scientific_task(summary):
    """The old ``services.scientific_parent_task``: the scientific question and the selected tool information."""
    return {'scientific_question': summary['objective'],
            'selected_tool_info': summary['selection']['child_tool_info']}


def assignment_for(slot, arguments, summary):
    if slot == 'partner_presence_evidence':
        assignment = {'selection': selector_selection(arguments['process_selection']),
                      'evidence_refs': arguments['evidence_refs'], 'constraints': arguments['constraints'],
                      'context': arguments['context'], 'scope': summary['scope'],
                      'received_record_refs': summary['held_record_refs'],
                      'finding_unit': summary['finding_unit'],
                      **present(summary, ('handoff_unit', 'acquired_record_unit', 'information_unit')),
                      **present(arguments, ('revision_origin',))}
        if summary['proposed_annotation_ref'] is not None:
            assignment['proposed_annotation_ref'] = [summary['proposed_annotation_ref']]
        return assignment
    if slot == 'launch':
        return {'version': 'execution_launch_assignment_v1', 'requests': arguments['requests'],
                'immutable_input_versions': arguments['immutable_input_versions'],
                'constraints': arguments['constraints'], 'handoff_unit': summary['handoff_unit'],
                'acquired_record_unit': summary['acquired_record_unit'], 'scope': summary['scope'],
                'scientific_task': scientific_task(summary),
                **present(arguments, ('launch_instructions', 'record_refs', 'received_handoff_resources'))}
    if slot == 'results':
        return {'version': 'execution_results_assignment_v1', 'handoff_ref': arguments['handoff_ref'],
                'selector': arguments['selector'], 'target': arguments['target'],
                'acquired_record_unit': summary['acquired_record_unit'],
                **present(arguments, ('record_refs', 'initial_result_refs'))}
    if slot == 'hpc':
        return {'scope': summary['scope'],
                **present(arguments, ('commission_id', 'commission_source_ref', 'tool_request',
                                      'received_record_refs', 'input_refs'))}
    raise LookupError('unsupported_child_slot:' + slot)


def monitor(arguments, summary):
    """The commission of the monitor for one outstanding job (the old ``prepare_request``: this parent requests
    information and never polls). The job is passed as records in custody, never by name: the handoff row of the job
    ledger this episode holds and the check rows of that job it holds (earlier monitors returned them in
    ``check_refs``), as the baseline of the new check. A handoff this episode does not hold as an outstanding job
    fails here with its ``KeyError``. Nothing the model wrote passes: the objective names the job by its handle and
    the message is empty."""
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[arguments['handoff_ref']]
    return ChildMessage(
        objective='Assess the progress of job ' + job['job'] + '.', message={},
        assignment={'version': 'monitor_assignment_v2', 'handoff_refs': [job['handoff_ref']],
                    'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
                    'requested_fields': list(arguments['requested_fields']),
                    'information_unit': summary['information_unit']},
        selection=tuple(arguments['return_fields']))


def msg_to_child(slot, arguments, summary):
    if slot == 'monitor':
        return monitor(arguments, summary)
    return ChildMessage(objective=arguments['objective'],
                        message={'purpose': arguments['purpose']},
                        assignment=assignment_for(slot, arguments, summary),
                        selection=tuple(arguments.get('return_fields', ())))
