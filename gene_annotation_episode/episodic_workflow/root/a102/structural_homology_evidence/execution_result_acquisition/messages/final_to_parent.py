"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
episode's own: whether the requested paths are completely acquired, how many results and windows were acquired,
which requested paths remain uncovered, and what the acquired bytes do and do not establish). Every fact source is
a selectable field; the parent selects the ones it wants in its commission. The file-source and protein-structure
sources are empty here and ``execution_result_origin`` is the empty record when no result has a window."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'completed': Field('boolean', 'Whether every requested path is completely acquired from the exact attempt '
                       'observed as completed with return code 0'),
    'requested_paths': Field('list', 'The requested paths'),
    'results_acquired': Field('integer', 'How many result records this episode acquired'),
    'windows_acquired': Field('integer', 'How many byte windows the results (known and acquired) hold'),
    'acquisition_failures': Field('integer', 'How many requested windows could not be read'),
    'uncovered_paths': Field('list', 'The requested paths whose requested bytes are not completely acquired'),
    'qualification': Field('text', 'What the acquired bytes establish: the current resource filesystem, not an '
                           'atomic snapshot and not proven output of the observed attempt'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the acquisition of the requested results', form=FINDING_FORM),
    'execution_file_source_refs': Field('record_refs', 'Selected local file sources retained by this episode '
                                        '(none)', required=False),
    'execution_file_capture_outcomes': Field('list', 'Selected file availability and custody qualifications '
                                             '(none)', required=False),
    'execution_protein_structure_projections': Field('list', 'Protein structure projection results (none)',
                                                     required=False),
    'execution_protein_structure_saved_sheets': Field('list', 'Saved protein structure sheet descriptors (none)',
                                                      required=False),
    'execution_protein_structure_sequences': Field('list', 'Structure-derived sequence descriptors (none)',
                                                   required=False),
    'execution_protein_structure_failures': Field('list', 'Recorded protein structure result failures (none)',
                                                  required=False),
    'execution_handoff_refs': Field('record_refs', 'The original execution handoff available to this episode',
                                    required=False),
    'execution_result_refs': Field('record_refs', 'Actual requested result acquisitions, each with its windows',
                                   required=False),
    'execution_completed': Field('boolean', 'Whether the requested paths are completely acquired from a '
                                 'successful exact attempt observation', required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of the retained results: current-file '
                                     'windows (the empty record when no result has a window)', required=False),
})


def final_to_parent(summary, completion, selection):
    own = [item for item in summary['results'] if not item['initial']]
    finding = {'completed': summary['completed'], 'requested_paths': list(summary['requested']),
               'results_acquired': len(own),
               'windows_acquired': sum(len(item['windows']) for item in summary['results']),
               'acquisition_failures': sum(item['failures'] for item in own),
               'uncovered_paths': list(summary['uncovered_paths']),
               'qualification': ('every requested path is acquired from the current resource filesystem after a '
                                 'successful exact attempt observation; separate windows are not an atomic '
                                 'snapshot and the attempt is not shown to have produced these bytes'
                                 if summary['completed'] else
                                 'the requested paths are not completely acquired: the uncovered paths are '
                                 'listed; bytes acquired are current-filesystem windows, not an atomic snapshot '
                                 'and not shown to be output of the observed attempt')}
    return {'credit': completion['credit'], 'finding': finding,
            **{name: summary['facts'][name] for name in selection}}
